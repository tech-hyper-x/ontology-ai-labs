"""업무 도구 9종 — 그래프 조회 + 결정론적 계산 (Part 2 Ch6, 설계 덱 40장).

에이전트는 이 함수들을 MCP 로 호출한다 (mcp_server.py). 함수는 Neo4j 드라이버를 받아
조회는 CQ 쿼리(graph/cq.py)로, 계산은 calc.py 의 Decimal 규칙으로 한다.

입력이 틀리면 예외 대신 error · hint 를 채운 결과를 돌려준다. 에이전트가 오류를 읽고
입력을 고쳐 다시 부를 수 있게 하기 위해서다.

계산 도구: bom_explode · purchase_quantity · cost_rollup · revision_diff · change_impact
조회 도구: where_used · supply_risk          검색 도구: find_part · search_docs
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from neo4j import Driver

from mfg_bom_agent.contracts import tools as c
from mfg_bom_agent.graph.cq import run_cq
from mfg_bom_agent.retrieval.hybrid import hybrid_search
from mfg_bom_agent.tools import calc

SNAPSHOT_OBSERVED = date(2026, 10, 22)
PRODUCT = "OSR"
# 한국어 질문에 자주 나오는 부품 이름 → 원천(영어) 별칭. 부품 식별 전에 바꿔 검색한다.
KOREAN_TERMS = {
    "서보": "servo",
    "모터": "motor",
    "휠": "wheel",
    "바퀴": "wheel",
    "베어링": "bearing",
    "스페이서": "spacer",
    "브래킷": "bracket",
    "허브": "hub",
    "나사": "screw",
    "너트": "nut",
    "샤프트": "shaft",
    "축": "shaft",
    "서보블록": "servoblock",
    "서보 블록": "servoblock",
}
_SKU = re.compile(r"\b(\d{4}-\d{4}-\d{4}|[A-Z0-9]{4,}-?[A-Z0-9]*)\b")


# ── 공통 조회 ───────────────────────────────────────────────
def _revision(driver: Driver, revision: str | None) -> dict | None:
    recs, _, _ = driver.execute_query(
        "MATCH (v:Revision) WHERE ($r IS NULL AND v.is_latest) OR v.revision_id = $r "
        "RETURN v.revision_id AS id, v.is_latest AS latest, toString(v.valid_from) AS valid_from",
        r=revision,
    )
    return recs[0].data() if recs else None


def _part(driver: Driver, part: str) -> dict | None:
    recs, _, _ = driver.execute_query(
        "MATCH (p:Part) WHERE p.part_id = $p OR p.sku = $p OR p.part_id = 'P-' + $p "
        "RETURN p.part_id AS part_id, p.sku AS sku, p.name AS name, p.pack_size AS pack_size, "
        "p.pack_basis AS pack_basis, p.in_latest AS in_latest",
        p=(part or "").strip(),
    )
    return recs[0].data() if recs else None


def _lines(driver: Driver, revision: str, scope: str, part_id: str | None = None) -> list[dict]:
    """판의 부품 라인 전체(또는 부품 하나)를 어셈블리 이름과 함께 읽는다."""
    recs, _, _ = driver.execute_query(
        """
        MATCH (a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine {revision_id: $rev})-[:REFERS_TO]->(p:Part)
        WHERE ($scope = 'all' OR a.domain = $scope) AND ($pid IS NULL OR p.part_id = $pid)
        RETURN p.part_id AS part_id, p.sku AS sku, p.name AS name, a.name AS assembly,
               l.raw_qty_text AS raw_qty, l.pack_size AS pack_size, l.pack_basis AS pack_basis,
               l.multiplier AS multiplier, l.unit_price AS unit_price, l.price_observed_at AS observed,
               l.source_ref AS source_ref
        ORDER BY a.name, l.row_no
    """,
        rev=revision,
        scope=scope,
        pid=part_id,
    )
    return [r.data() for r in recs]


def _offers(driver: Driver, part_id: str) -> list[c.Offer]:
    rows = run_cq(driver, "CQ-05", part=part_id)
    return [
        c.Offer(
            supplier_id=r["supplier_id"],
            supplier=r["supplier"],
            supplier_origin=r["supplier_origin"],
            supplier_sku=r["supplier_sku"],
            unit_price=Decimal(r["unit_price"]),
            pack_size=r["pack_size"],
            moq_packs=r["moq_packs"],
            lead_time_days=r["lead_time_days"],
            observed_at=date.fromisoformat(r["observed_at"]),
            terms_origin=r["terms_origin"],
        )
        for r in rows
    ]


def _as_of(rev: dict) -> date:
    """가격 관측일: 최신 판은 스냅샷 관측일, 과거 판은 그 판의 커밋일(원천 parts_list 에 적힌 단가)."""
    return SNAPSHOT_OBSERVED if rev["latest"] else date.fromisoformat(rev["valid_from"])


def _bad_revision(model: type, revision: str | None, **fields) -> c.ToolResult:
    return model(
        error=f"판 {revision!r} 을(를) 찾을 수 없습니다",
        hint="revision 은 커밋 ID(예: 72edc6e) 또는 null(최신 판)",
        **fields,
    )


def _bad_part(model: type, part: str, **fields) -> c.ToolResult:
    return model(
        error=f"부품 {part!r} 을(를) 찾을 수 없습니다",
        hint="find_part 로 먼저 품번을 확인하세요",
        **fields,
    )


# ─── [Hands-on P2-Ch6-2 계산 도구 MCP 연결] 시작 ───
# 도구 하나 = 입력 계약 + 조회 + 계산 + 기준 시점 · 단위 · 가정이 담긴 출력. mcp_server.py 가 이 함수를 등록한다.


def find_part(driver: Driver, query: str, revision: str | None = None) -> c.FindPartResult:
    """이름 · 약칭 · 품번으로 부품을 찾는다. 후보가 여럿이면 ambiguous=True 로 돌려준다 (되묻기용)."""
    q = query.strip()
    for ko, en in sorted(KOREAN_TERMS.items(), key=lambda kv: -len(kv[0])):
        q = q.replace(ko, en)
    rows = run_cq(driver, "CQ-12", name=q)
    cands = [
        c.PartCandidate(
            part_id=r["part_id"],
            sku=r["sku"],
            name=r["part_name"],
            score=r["score"],
            method=r["method"],
            in_latest=bool(r["in_latest"]),
        )
        for r in rows
    ]
    result = c.FindPartResult(query=query, candidates=cands, as_of=SNAPSHOT_OBSERVED)
    if not cands:
        result.error, result.hint = (
            "일치하는 부품이 없습니다",
            "영어 부품명(예: servo, wheel)이나 품번으로 다시 찾으세요",
        )
        return result
    top = cands[0]
    current = [x for x in cands if x.in_latest]
    if top.method in ("exact_id", "alias") and sum(x.method == top.method for x in cands) == 1:
        chosen = top
    elif top.method == "alias" and len([x for x in current if x.method == "alias"]) == 1:
        chosen = next(x for x in current if x.method == "alias")
        result.warnings.append("같은 별칭의 과거 부품이 있어 현재 BOM 부품을 골랐습니다")
    elif len(current) == 1 or (len(current) > 1 and current[0].score >= 2 * current[1].score):
        chosen = current[0]
    else:
        chosen = None
    if chosen:
        chosen.offers = _offers(driver, chosen.part_id)
        result.resolved = chosen
    else:
        result.ambiguous = True
        result.hint = "후보 중 하나를 사용자에게 확인받으세요"
    return result


def where_used(driver: Driver, part: str, revision: str | None = None) -> c.WhereUsedResult:
    """부품이 선택한 판에서 어느 어셈블리 · 제품에 몇 개(원천 수량 · 배수) 쓰이는지 돌려준다."""
    rev = _revision(driver, revision)
    p = _part(driver, part)
    if not rev:
        return _bad_revision(c.WhereUsedResult, revision, part_id="", sku=part, name="")
    if not p:
        return _bad_part(c.WhereUsedResult, part, part_id="", sku=part, name="", revision=rev["id"])
    usage = run_cq(driver, "CQ-02", part=p["part_id"], revision=rev["id"])
    paths = run_cq(driver, "CQ-01", part=p["part_id"], revision=rev["id"])
    out = c.WhereUsedResult(part_id=p["part_id"], sku=p["sku"], name=p["name"], revision=rev["id"])
    out.lines = [
        c.UsageLine(
            assembly=u["assembly"],
            raw_qty=Decimal(u["raw_qty"]),
            pack_size=u["pack_size"],
            qty_each=Decimal(u["qty_each"]),
            multiplier=u["multiplier"],
            each_per_product=calc.qty(
                calc.each_per_product(Decimal(u["raw_qty"]), u["pack_size"], u["multiplier"])
            ),
            unit=u["unit"],
            source_ref=u["source_ref"],
        )
        for u in usage
    ]
    out.paths = [
        c.UsagePath(
            product=x["product"],
            assemblies=x["assemblies"],
            text=" → ".join(["Rover", *x["assemblies"], p["sku"]]),
        )
        for x in paths
    ]
    out.replaced = [
        c.Replacement(
            sku=r["old_sku"], name=r["old_name"], ecn=r["ecn"], effective_date=r["effective_date"]
        )
        for r in run_cq(driver, "CQ-08", part=p["part_id"])
    ]
    recs, _, _ = driver.execute_query(
        "MATCH (n:Part)-[s:SUPERSEDES]->(:Part {part_id: $pid}) RETURN n.sku AS sku, n.name AS name, "
        "s.ecn_id AS ecn, toString(s.effective_date) AS d",
        pid=p["part_id"],
    )
    out.replaced_by = [
        c.Replacement(sku=r["sku"], name=r["name"], ecn=r["ecn"], effective_date=r["d"])
        for r in recs
    ]
    if not out.lines:
        out.warnings.append(f"판 {rev['id']} 의 BOM 에 이 부품이 없습니다")
    return out


def _explode_formula(raw, pack_size: int, multiplier: int, units: int) -> str:
    """수량 산식을 읽기 쉽게 쓴다. 낱개 상품이면 "1개/팩"을 빼고 어셈블리 수로 풀어 쓴다."""
    if pack_size == 1:
        return f"어셈블리당 {raw}개 × 어셈블리 {multiplier}개 × {units}대"
    return f"{raw}팩 × {pack_size}개/팩 × 배수 {multiplier} × {units}대"


def bom_explode(
    driver: Driver,
    product: str = PRODUCT,
    units: int = 1,
    revision: str | None = None,
    part: str | None = None,
    scope: str = "mechanical",
) -> c.BomExplodeResult:
    """BOM 을 전개해 부품별 소요 낱개 수를 계산한다. part 를 주면 그 부품만 계산한다."""
    rev = _revision(driver, revision)
    if not rev:
        return _bad_revision(
            c.BomExplodeResult, revision, product=product, units=units, scope=scope
        )
    if units < 1:
        return c.BomExplodeResult(
            product=product,
            units=units,
            scope=scope,
            revision=rev["id"],
            error="units 는 1 이상이어야 합니다",
            hint="생산 대수를 정수로 넣으세요",
        )
    pid = None
    if part:
        p = _part(driver, part)
        if not p:
            return _bad_part(
                c.BomExplodeResult,
                part,
                product=product,
                units=units,
                scope=scope,
                revision=rev["id"],
            )
        pid = p["part_id"]
    out = c.BomExplodeResult(product=product, units=units, scope=scope, revision=rev["id"])
    for ln in _lines(driver, rev["id"], scope, pid):
        raw = Decimal(ln["raw_qty"])
        per = calc.each_per_product(raw, ln["pack_size"], ln["multiplier"])
        out.items.append(
            c.ExplodedItem(
                part_id=ln["part_id"],
                sku=ln["sku"],
                name=ln["name"],
                assembly=ln["assembly"],
                raw_qty_per_assembly=raw,
                pack_size=ln["pack_size"],
                pack_basis=ln["pack_basis"],
                multiplier=ln["multiplier"],
                each_per_product=calc.qty(per),
                required_each=calc.qty(per * units),
                formula=_explode_formula(raw, ln["pack_size"], ln["multiplier"], units),
            )
        )
        if ln["pack_basis"] == "none" and ln["pack_size"] == 1 and part:
            out.assumptions.append("품명에 포장 표기가 없어 낱개(1개) 상품으로 봄")
    out.total_lines = len(out.items)
    if part and not out.items:
        out.warnings.append(f"판 {rev['id']} 의 BOM 에 이 부품이 없습니다")
    return out


def purchase_quantity(
    driver: Driver,
    part: str,
    required_each: str | None = None,
    units: int | None = None,
    supplier: str | None = None,
    revision: str | None = None,
) -> c.PurchaseQuantityResult:
    """소요 낱개 수를 팩 단위 · MOQ 에 맞춘 구매 수량과 구매 금액으로 바꾼다."""
    p = _part(driver, part)
    empty = {
        "part_id": "",
        "sku": part,
        "supplier_id": supplier or "",
        "required_each": Decimal(0),
        "pack_size": 1,
        "packs_needed": 0,
        "moq_packs": 0,
        "packs_to_buy": 0,
        "unit_price": Decimal(0),
        "purchase_amount": Decimal(0),
        "leftover_each": Decimal(0),
        "formula": "",
    }
    if not p:
        return _bad_part(c.PurchaseQuantityResult, part, **empty)
    if required_each is None:
        if not units:
            return c.PurchaseQuantityResult(
                **empty,
                error="required_each 또는 units 중 하나가 필요합니다",
                hint="소요 낱개 수나 생산 대수를 넣으세요",
            )
        ex = bom_explode(driver, units=units, revision=revision, part=p["part_id"], scope="all")
        req = sum((i.required_each for i in ex.items), Decimal(0))
    else:
        req = Decimal(str(required_each))
    req = calc.qty(req)
    offers = _offers(driver, p["part_id"])
    offer = (
        next((o for o in offers if o.supplier_id == supplier), None)
        if supplier
        else next(
            (o for o in offers if o.supplier_origin == "source"), offers[0] if offers else None
        )
    )
    if not offer:
        return c.PurchaseQuantityResult(
            **{**empty, "part_id": p["part_id"], "sku": p["sku"]},
            error="등록된 구매 조건이 없습니다",
            hint="supply_risk 로 공급사를 확인하세요",
        )
    needed, buy = calc.packs_to_buy(req, offer.pack_size, offer.moq_packs)
    amount = calc.money(buy * offer.unit_price)
    out = c.PurchaseQuantityResult(
        part_id=p["part_id"],
        sku=p["sku"],
        supplier_id=offer.supplier_id,
        required_each=req,
        pack_size=offer.pack_size,
        packs_needed=needed,
        moq_packs=offer.moq_packs,
        packs_to_buy=buy,
        unit_price=offer.unit_price,
        purchase_amount=amount,
        leftover_each=calc.qty(buy * offer.pack_size - req),
        formula=f"max(올림({req} ÷ {offer.pack_size}), MOQ {offer.moq_packs}) = {buy}팩 × ${offer.unit_price}/팩",
        as_of=offer.observed_at,
        revision=(_revision(driver, revision) or {}).get("id"),
    )
    if offer.terms_origin != "source":
        out.assumptions.append(f"MOQ · 리드타임은 교육용 가정값 ({offer.terms_origin})")
    return out


def cost_rollup(
    driver: Driver,
    product: str = PRODUCT,
    units: int = 1,
    revision: str | None = None,
    scope: str = "mechanical",
    items: list[dict] | None = None,
    price_overrides: dict[str, str] | None = None,
) -> c.CostRollupResult:
    """소요 원가를 계산한다 (팩 올림 · MOQ 미반영). items 를 주면 그 부품들만 계산한다 (선택 부품비).

    items: [{"part": 품번, "qty_each": 낱개 수}]   price_overrides: {품번: 팩당 단가} — 단가 변경 비교용
    """
    rev = _revision(driver, revision)
    if not rev:
        return _bad_revision(
            c.CostRollupResult, revision, product=product, units=units, scope=scope
        )
    overrides = {k: Decimal(str(v)) for k, v in (price_overrides or {}).items()}
    out = c.CostRollupResult(
        product=product, units=units, scope=scope, revision=rev["id"], as_of=_as_of(rev)
    )
    total = Decimal(0)
    if items:
        for it in items:
            p = _part(driver, it["part"])
            if not p:
                return _bad_part(
                    c.CostRollupResult, it["part"], product=product, units=units, scope=scope
                )
            offers = _offers(driver, p["part_id"])
            offer = next((o for o in offers if o.supplier_origin == "source"), None)
            price = overrides.get(p["sku"], offer.unit_price if offer else None)
            if price is None:
                out.missing_prices.append(p["sku"])
                continue
            qty = Decimal(str(it["qty_each"]))
            amount = calc.cost_of_each(qty, offer.pack_size if offer else 1, price)
            total += amount
            out.lines.append(
                c.CostLine(
                    part_id=p["part_id"],
                    sku=p["sku"],
                    qty=qty,
                    qty_unit="ea",
                    unit_price=price,
                    price_unit="pack" if (offer and offer.pack_size > 1) else "ea",
                    amount=calc.money(amount),
                    price_overridden=p["sku"] in overrides,
                )
            )
        out.formula = " + ".join(f"{ln.qty}개 × ${ln.unit_price}" for ln in out.lines)
    else:
        by_asm: dict[str, Decimal] = {}
        for ln in _lines(driver, rev["id"], scope):
            price = overrides.get(ln["sku"]) or (
                Decimal(ln["unit_price"]) if ln["unit_price"] else None
            )
            if price is None:
                out.missing_prices.append(ln["sku"])
                continue
            raw = Decimal(ln["raw_qty"])
            amount = calc.requirement_cost(raw, ln["multiplier"], units, price)
            total += amount
            by_asm[ln["assembly"]] = by_asm.get(ln["assembly"], Decimal(0)) + amount
            out.lines.append(
                c.CostLine(
                    part_id=ln["part_id"],
                    sku=ln["sku"],
                    assembly=ln["assembly"],
                    qty=raw * ln["multiplier"] * units,
                    qty_unit="pack" if ln["pack_size"] > 1 else "ea",
                    unit_price=price,
                    price_unit="pack" if ln["pack_size"] > 1 else "ea",
                    amount=calc.money(amount),
                    price_overridden=ln["sku"] in overrides,
                )
            )
        out.by_assembly = {k: calc.money(v) for k, v in by_asm.items()}
        out.formula = f"Σ 원천 수량 × 배수 × {units}대 × 팩당 단가 ({len(out.lines)}라인)"
        out.assumptions.append(f"단가 기준: 판 {rev['id']} 의 parts_list 단가 (관측일 {out.as_of})")
    out.total = calc.money(total)
    if overrides:
        out.assumptions.append(
            f"단가 변경 적용: {', '.join(f'{k}=${v}' for k, v in overrides.items())}"
        )
    out.warnings.append(
        "소요 원가다 — 실제 구매 금액은 팩 올림 · MOQ 때문에 다를 수 있다 (purchase_quantity)"
    )
    return out


def revision_diff(driver: Driver, rev_a: str, rev_b: str) -> c.RevisionDiffResult:
    """두 판의 BOM 라인 차이(추가 · 삭제 · 수량 변경)와 그 사이의 ECN 을 돌려준다."""
    a, b = _revision(driver, rev_a), _revision(driver, rev_b)
    if not a or not b:
        return c.RevisionDiffResult(
            rev_a=rev_a,
            rev_b=rev_b,
            error="판을 찾을 수 없습니다",
            hint="revision_diff 는 커밋 ID 두 개를 받습니다",
        )
    la = {(x["assembly"], x["part_id"]): x for x in _lines(driver, a["id"], "all")}
    lb = {(x["assembly"], x["part_id"]): x for x in _lines(driver, b["id"], "all")}
    out = c.RevisionDiffResult(rev_a=a["id"], rev_b=b["id"], revision=b["id"])
    iv = run_cq(driver, "CQ-14", revision_id=b["id"])[0]
    out.valid_from_b, out.valid_to_b = (
        iv["valid_from"],
        (None if iv["valid_to"] == "현재" else iv["valid_to"]),
    )
    for key in sorted(set(la) | set(lb)):
        x, y = la.get(key), lb.get(key)
        if (
            x
            and y
            and (Decimal(x["raw_qty"]), x["multiplier"]) == (Decimal(y["raw_qty"]), y["multiplier"])
        ):
            continue
        kind = "removed" if x and not y else "added" if y and not x else "qty_changed"
        ref = y or x
        out.changes.append(
            c.LineChange(
                change_type=kind,
                assembly=key[0],
                sku=ref["sku"],
                name=ref["name"],
                before_raw_qty=Decimal(x["raw_qty"]) if x else None,
                after_raw_qty=Decimal(y["raw_qty"]) if y else None,
                before_multiplier=x["multiplier"] if x else None,
                after_multiplier=y["multiplier"] if y else None,
            )
        )
    recs, _, _ = driver.execute_query(
        "MATCH (e:ECN) WHERE e.ecn_date > date($fa) AND e.ecn_date <= date($fb) RETURN e.ecn_id AS id ORDER BY id",
        fa=a["valid_from"],
        fb=b["valid_from"],
    )
    out.ecns = [r["id"] for r in recs]
    return out


def change_impact(
    driver: Driver,
    change_type: str,
    part: str | None = None,
    ecn: str | None = None,
    value: str | None = None,
    units: int = 1,
    revision: str | None = None,
) -> c.ChangeImpactResult:
    """변경의 영향 후보와 금액을 계산한다.

    change_type: "price_percent"(단가 변경률 value%) · "discontinue"(단종 가정) · "ecn"(ECN 전후 원가)
    단종만으로 손실 · 생산 중단 금액을 확정하지 않는다 (extra_cost = "미확인").
    """
    rev = _revision(driver, revision)
    if not rev:
        return _bad_revision(c.ChangeImpactResult, revision, change_type=change_type, units=units)
    if change_type == "ecn":
        # ECN ID · 변경 후 판 ID · 날짜 앞부분(예: "2024-06") 중 무엇으로든 찾는다
        recs, _, _ = driver.execute_query(
            "MATCH (e:ECN) WHERE e.ecn_id = $e OR e.revision_to = $e OR toString(e.ecn_date) STARTS WITH $e "
            "RETURN e.ecn_id AS id, e.revision_from AS a, e.revision_to AS b ORDER BY e.ecn_date",
            e=(ecn or "").strip(),
        )
        if not recs:
            return c.ChangeImpactResult(
                change_type="ecn",
                units=units,
                error=f"ECN {ecn!r} 없음",
                hint="ECN ID(예: ECN-2024-06-18-72edc6e) · 변경 후 판 ID · 날짜(2024-06)",
            )
        if len(recs) > 1:
            return c.ChangeImpactResult(
                change_type="ecn",
                units=units,
                error=f"{ecn!r} 에 해당하는 ECN 이 {len(recs)}건",
                hint="다음 중 하나를 지정하세요: " + ", ".join(r["id"] for r in recs),
            )
        e = recs[0]
        before = cost_rollup(driver, units=units, revision=e["a"])
        after = cost_rollup(driver, units=units, revision=e["b"])
        diff = revision_diff(driver, e["a"], e["b"])
        out = c.ChangeImpactResult(
            change_type="ecn",
            ecn=e["id"],
            units=units,
            revision=e["b"],
            revision_from=e["a"],
            cost_before=before.total,
            cost_after=after.total,
            cost_diff=after.total - before.total,
            as_of=after.as_of,
            formula=f"판 {e['b']} 원가 − 판 {e['a']} 원가 ({units}대, 각 판의 parts_list 단가)",
        )
        changed = sorted({ch.assembly for ch in diff.changes})
        out.impact_candidates = [
            c.ImpactTarget(level="Assembly", target_id=f"{PRODUCT}/{a}", name=a) for a in changed
        ]
        out.assumptions.append("각 판의 원가는 그 판 parts_list 에 적힌 단가로 계산")
        return out

    p = _part(driver, part or "")
    if not p:
        return _bad_part(c.ChangeImpactResult, part or "", change_type=change_type, units=units)
    out = c.ChangeImpactResult(
        change_type=change_type,
        part_id=p["part_id"],
        sku=p["sku"],
        units=units,
        revision=rev["id"],
        as_of=_as_of(rev),
    )
    out.impact_candidates = [
        c.ImpactTarget(level=r["level"], target_id=r["target_id"], name=r["target"])
        for r in run_cq(driver, "CQ-09", part=p["part_id"], revision=rev["id"])
    ]
    ex = bom_explode(driver, units=units, revision=rev["id"], part=p["part_id"], scope="all")
    out.required_each = calc.qty(sum((i.required_each for i in ex.items), Decimal(0)))
    lines = _lines(driver, rev["id"], "all", p["part_id"])
    base = sum(
        (
            calc.requirement_cost(
                Decimal(ln["raw_qty"]), ln["multiplier"], units, Decimal(ln["unit_price"])
            )
            for ln in lines
            if ln["unit_price"]
        ),
        Decimal(0),
    )
    price = Decimal(lines[0]["unit_price"]) if lines and lines[0]["unit_price"] else None
    if change_type == "price_percent":
        if value is None:
            return c.ChangeImpactResult(
                change_type=change_type,
                units=units,
                error="value(변경률 %)가 필요합니다",
                hint="예: value='15'",
            )
        pct = Decimal(str(value))
        after = sum(
            (
                calc.requirement_cost(
                    Decimal(ln["raw_qty"]),
                    ln["multiplier"],
                    units,
                    calc.apply_percent(Decimal(ln["unit_price"]), pct),
                )
                for ln in lines
                if ln["unit_price"]
            ),
            Decimal(0),
        )
        out.cost_before, out.cost_after = calc.money(base), calc.money(after)
        out.cost_diff = calc.money(after - base)
        out.formula = f"(${price} × {pct}%) × {out.required_each}개 = 부품비 차이"
        out.assumptions.append(f"단가 {pct}% 변경은 시나리오 가정")
    elif change_type == "discontinue":
        out.requirement_cost = calc.money(base)
        out.formula = f"{out.required_each}개 × ${price}"
        out.assumptions.append("단종은 교육용 가정 — 추가 비용 · 생산 중단 여부는 확정하지 않음")
    else:
        return c.ChangeImpactResult(
            change_type="discontinue",
            units=units,
            error=f"모르는 change_type {change_type!r}",
            hint="price_percent · discontinue · ecn 중 하나",
        )
    if not lines:
        out.warnings.append(f"판 {rev['id']} 의 BOM 에 이 부품이 없습니다")
    return out


def supply_risk(
    driver: Driver,
    supplier: str | None = None,
    part: str | None = None,
    revision: str | None = None,
    qty_each: str | None = None,
) -> c.SupplyRiskResult:
    """공급사 중단 시 멈추는 부품(등록 공급사 1곳) 또는 부품 하나의 공급 · 대체 현황 (R1).

    part 와 qty_each(필요 낱개 수)를 함께 주면, 가격이 적힌 대체 부품마다 같은 수량의 부품비와
    현재 부품 대비 차이를 계산한다. 재작업 · 설정 변경 공수는 넣지 않는다.
    """
    rev = _revision(driver, revision)
    if not rev:
        return _bad_revision(c.SupplyRiskResult, revision)
    out = c.SupplyRiskResult(revision=rev["id"], supplier_id=supplier, as_of=SNAPSHOT_OBSERVED)
    recs, _, _ = driver.execute_query(
        """
        MATCH (a:Assembly)-[:HAS_BOM_LINE]->(:BOMLine {revision_id: $rev})-[:REFERS_TO]->(p:Part)
        WHERE $pid IS NULL OR p.part_id = $pid
        OPTIONAL MATCH (p)-[:SUPPLIED_BY]->(s:Supplier)
        WITH p, collect(DISTINCT a.name) AS asms, collect(DISTINCT s.supplier_id) AS sups
        WHERE $sup IS NULL OR $sup IN sups
        RETURN p.part_id AS part_id, p.sku AS sku, p.name AS name, asms, sups
        ORDER BY sku
    """,
        rev=rev["id"],
        sup=supplier,
        pid=(_part(driver, part) or {}).get("part_id") if part else None,
    )
    affected: set[str] = set()
    for r in recs:
        single = len(r["sups"]) == 1
        if supplier and not single:
            continue  # 다른 공급사가 등록된 부품은 이 공급사가 멈춰도 구매할 수 있다
        out.parts.append(
            c.SupplyRiskPart(
                sku=r["sku"],
                name=r["name"],
                suppliers=r["sups"],
                single_registered_supplier=single,
                assemblies=r["asms"],
            )
        )
        affected.update(r["asms"])
    out.affected_assemblies = sorted(affected)
    if part:
        p = _part(driver, part)
        if not p:
            return _bad_part(c.SupplyRiskResult, part)
        out.part_sku = p["sku"]
        out.alternates = [
            c.AlternatePart(
                sku=r["alternate_sku"],
                name=r["alternate_name"],
                compatibility=r["compatibility"],
                requires_rework=r["requires_rework"],
                source_doc=r["source_doc"],
                pack_price=Decimal(r["pack_price"]) if r["pack_price"] else None,
                pack_size=r["pack_size"],
                price_note=r["price_note"] or "",
            )
            for r in run_cq(driver, "CQ-10", part=p["part_id"])
            if r["alternate_sku"]
        ]
        if qty_each is not None:
            _alternate_costs(driver, p, Decimal(str(qty_each)), out)
    if any(s != "gobilda.com" for x in out.parts for s in x.suppliers):
        out.assumptions.append("alt-robotics · maker-depot 는 교육용 가상 공급사")
    return out


def _alternate_costs(driver: Driver, p: dict, qty: Decimal, out: c.SupplyRiskResult) -> None:
    """같은 수량을 대체 부품으로 살 때의 부품비 · 차이를 채운다. 현재 부품은 원천 구매처 단가를 쓴다."""
    offer = next((o for o in _offers(driver, p["part_id"]) if o.supplier_origin == "source"), None)
    if not offer:
        out.warnings.append(
            f"{p['sku']} 의 원천 단가가 없어 대체 부품 비용 차이를 계산하지 않았습니다"
        )
        return
    current = calc.money(calc.cost_of_each(qty, offer.pack_size, offer.unit_price))
    for a in out.alternates:
        if a.pack_price is None or not a.pack_size:
            continue
        packs, _ = calc.packs_to_buy(qty, a.pack_size, 1)
        a.required_packs = packs
        a.alternate_cost = calc.money(packs * a.pack_price)
        a.current_cost = current
        a.cost_diff = a.alternate_cost - current
        per = f"{packs}팩({a.pack_size}개/팩)" if a.pack_size > 1 else f"{packs}개"
        a.formula = f"{per} × ${a.pack_price} − {calc.qty(qty)}개 × ${offer.unit_price}"
    out.assumptions.append(
        "대체 부품 가격은 원천 문서(extra_parts.md)에 적힌 값 · 재작업 · 설정 변경 공수는 미포함"
    )


def search_docs(
    driver: Driver, query: str, k: int = 5, source: str | None = None, mode: str = "hybrid"
) -> c.SearchDocsResult:
    """증상 · 키워드로 정비 문서와 이슈를 찾고, 연결된 부품과 사용처를 함께 돌려준다 (영어 검색어 권장).

    mode: hybrid(BM25 + 벡터 → RRF, 기본) · bm25 · vector — 하이브리드 효과를 비교할 때만 바꾼다 (CQ-15).
    """
    if mode not in ("hybrid", "bm25", "vector"):
        return c.SearchDocsResult(
            query=query,
            provider="",
            error=f"알 수 없는 mode: {mode}",
            hint="hybrid · bm25 · vector 중 하나",
        )
    res = hybrid_search(driver, query, k=k, source=source, mode=mode)
    out = c.SearchDocsResult(
        query=query,
        provider=res["provider"],
        mode=mode,
        effective_mode=res["effective_mode"],
        index_provider=res["index_provider"],
        query_provider=res["query_provider"],
        as_of=SNAPSHOT_OBSERVED,
    )
    if res["error"]:
        out.error = res["error"]
        out.hint = "임베딩 API 키 · 연결을 확인하거나 mode=bm25 로 검색하세요"
        return out
    out.hits = [c.DocHit(**h) for h in res["results"]]
    out.warnings += res["warnings"]
    if res["provider"].startswith("hash") and res["effective_mode"] != "bm25":
        out.warnings.append(
            "로컬 대체 임베딩 사용 — 의미 검색 품질이 낮아 단어가 겹치는 문서 위주로 찾는다"
        )
    return out


# ─── [Hands-on P2-Ch6-2] 끝 ───
