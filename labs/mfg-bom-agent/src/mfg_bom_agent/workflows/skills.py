"""스킬 실행 — 질문 유형별 도구 호출 경로 (Part 2 Ch7-1 질문별 도구 호출 경로).

skills/*/SKILL.md 에 적은 순서를 코드로 옮긴 것이다. 질문 유형(intent)마다 정해진 도구만 부르고,
필요 없는 호출은 하지 않는다. 결과는 화면 · 출력 검사가 그대로 쓰는 구조(CalcResult 등)로 정리한다.

모든 숫자는 도구 출력에서 온다. 이 모듈은 계산하지 않고, 도구 출력을 라벨 · 단위 · 산식과 함께 옮겨 담는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from mfg_bom_agent.contracts.answer import CalcResult, DocEvidence, GraphPath, RunContext
from mfg_bom_agent.foundation.virtual import SUPPLIERS
from mfg_bom_agent.tools.bom_tools import KOREAN_TERMS
from mfg_bom_agent.workflows.gateway import ToolCallError, ToolGateway
from mfg_bom_agent.workflows.plan import QuestionPlan

SKILL_OF_INTENT = {
    "purchase_quantity": "bom-calculation",
    "cost": "bom-calculation",
    "price_change": "change-and-supply-risk",
    "discontinue": "change-and-supply-risk",
    "revision_change": "change-and-supply-risk",
    "supply_disruption": "change-and-supply-risk",
    "symptom": "maintenance-evidence",
    "part_info": "part-identity-resolution",
    "other": "grounded-answer",
}

# 유형별로 꼭 필요한 값과, 없을 때 쓰는 기본값. 기본값이 None 이면 사용자에게 되묻는다.
REQUIRED = {
    "purchase_quantity": {"units": None},
    "cost": {"units": 1},
    "price_change": {"part": None, "percent": None, "units": 1},
    "discontinue": {"part": None, "units": None},
    "revision_change": {"change_ref": None, "units": 1},
    "supply_disruption": {"supplier": None},
    "symptom": {},
    "part_info": {"part": None},
    "other": {},
}
ASK_PROMPT = {
    "units": "몇 대 기준으로 계산할까요? (생산 대수)",
    "percent": "단가를 몇 % 바꾸는 조건인가요? (인상은 15, 인하는 -10)",
    "change_ref": "어떤 변경인가요? ECN ID, 커밋 ID 또는 날짜(예: 2024-06)를 알려 주세요.",
    "supplier": "어느 공급사인가요? (예: goBILDA)",
    "part": "어느 부품인가요? 부품 이름이나 품번(예: 2000-0025-0002)을 알려 주세요.",
}
SUPPLIER_ALIASES = {"gobilda": "gobilda.com", "digikey": "digikey.com", "digi-key": "digikey.com"}


@dataclass
class SkillOutput:
    calculations: list[CalcResult] = field(default_factory=list)
    graph_paths: list[GraphPath] = field(default_factory=list)
    documents: list[DocEvidence] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)  # 답변 작성 단계에 주는 도구 결과 요약
    revision: str | None = None
    as_of: date | None = None


def _d(v: Any) -> Decimal | None:
    return None if v in (None, "") else Decimal(str(v))


def _date(v: Any) -> date | None:
    return date.fromisoformat(v) if v else None


def _collect(out: SkillOutput, result: dict) -> None:
    out.revision = out.revision or result.get("revision")
    out.as_of = out.as_of or _date(result.get("as_of"))
    for a in result.get("assumptions", []):
        if a not in out.assumptions:
            out.assumptions.append(a)
    # 문서 검색이 요청과 다른 방식(임베딩 장애 → BM25)으로 실행됐으면 화면 · 답변에 그 사실을 남긴다
    if result.get("effective_mode") and result["effective_mode"] != result.get("mode"):
        for w in result.get("warnings", []):
            if w not in out.assumptions:
                out.assumptions.append(w)


def _history(out: SkillOutput, wu: dict) -> None:
    """교체 이력(SUPERSEDES)을 경로로 남긴다. 예: 5203-2402-0027 -SUPERSEDES-> 5202-2402-0027 (ECN, 날짜)"""
    for r in wu.get("replaced", []):
        out.graph_paths.append(
            GraphPath(
                text=f"{wu['sku']} -SUPERSEDES-> {r['sku']} · {r['ecn']} · {r['effective_date']}",
                tool="where_used",
                revision=wu.get("revision"),
            )
        )
    for r in wu.get("replaced_by", []):
        out.graph_paths.append(
            GraphPath(
                text=f"{r['sku']} -SUPERSEDES-> {wu['sku']} · {r['ecn']} · {r['effective_date']}",
                tool="where_used",
                revision=wu.get("revision"),
            )
        )


def _paths(out: SkillOutput, wu: dict) -> None:
    for line in wu.get("lines", []):
        unit = "ea" if line["pack_size"] == 1 else f"{line['pack_size']}개 팩"
        out.graph_paths.append(
            GraphPath(
                # 라인 수량만 보여 주면 LLM 이 "로버에 2개"처럼 잘못 읽는다. 로버당 수량(도구 계산값)을 함께 쓴다.
                text=f"Rover → {line['assembly']} (배수 ×{line['multiplier']}) → BOMLine (qty {line['raw_qty']} {unit}) "
                f"→ {wu['sku']} · 로봇 차량 1대당 {line['each_per_product']} ea",
                tool="where_used",
                revision=wu.get("revision"),
                # 화면은 detail 로 업무 문장("로버 1대에 4개")을 만든다. text 는 LLM · 기록용
                detail={
                    "source_ref": line["source_ref"],
                    "assembly": line["assembly"],
                    "multiplier": line["multiplier"],
                    "raw_qty": str(line["raw_qty"]),
                    "pack_size": line["pack_size"],
                    "each_per_product": str(line["each_per_product"]),
                    "sku": wu["sku"],
                    "name": wu.get("name", ""),
                },
            )
        )


# ─── [Hands-on P2-Ch7-1 질문별 도구 호출 경로] 시작 ───
def _doc_evidence(h: dict) -> DocEvidence:
    """search_docs 결과 한 건 → 화면 계약의 문서 근거."""
    return DocEvidence(
        doc_path=h["path"],
        doc_id=h["doc_id"],
        title=h["title"],
        line=h["line"],
        excerpt=h["excerpt"],
        linked_parts=sorted({p["sku"] for p in h["parts"]}),
        confidence=max((p.get("confidence") or 0 for p in h["parts"]), default=None),
        method="hybrid(RRF)",
        rank=h.get("rank"),
        ranks=h.get("ranks") or {},
    )


# 등록 공급사가 한 곳뿐일 때 붙이는 설명. 실습 데이터의 공급사 목록은 원천 부품표의 구매 링크와
# 교육용 가상 공급사(foundation/virtual.py)뿐이라, "1곳"이 실제 시장의 공급처 수를 뜻하지 않는다.
VIRTUAL_SUPPLIERS = {s["supplier_id"] for s in SUPPLIERS if s["origin"] != "source"}

SINGLE_SUPPLIER_NOTE = (
    "등록 공급사는 실습 데이터 기준이다. 원천 부품표의 구매 링크와 교육용 가상 공급사만 등록돼 있어, "
    "'다른 공급처 없음'은 실습 가정이며 실제 시장의 공급처 수가 아니다"
)


def _noun(plan: QuestionPlan, part: dict | None) -> str:
    """계산 결과 이름에 쓸 부품 이름. 질문에 나온 한글 이름(모터 · 서보)을 먼저, 없으면 품번을 쓴다.

    "소요 원가"처럼 쓰면 로버 전체 원가로 읽힌다. 금액이 어느 부품의 것인지 이름에 넣는다.
    """
    for term in plan.part_terms:
        # "휠(3616-0014-0144)"처럼 품번이 붙어 있으면 앞의 한글 이름만 쓴다
        m = re.match(r"\s*([가-힣][가-힣 ]*)", term)
        if m:
            return m.group(1).strip()
    # 질문에 품번만 있으면 부품 영문명에서 한글 이름을 찾는다 (Wasteland Wheel → 휠)
    for ko, en in KOREAN_TERMS.items():
        if part and re.search(rf"\b{en}\b", part.get("name", ""), re.IGNORECASE):
            return ko
    return part["sku"] if part else "부품"


def run_skill(
    gw: ToolGateway, plan: QuestionPlan, ctx: RunContext, parts: list[dict]
) -> SkillOutput:
    """질문 유형에 맞는 스킬을 실행한다. parts 는 부품 식별(S2)로 확정한 부품 목록이다."""
    out = SkillOutput()
    rev = ctx.revision
    units = plan.units
    part = parts[0] if parts else None

    if plan.intent == "cost":
        r = gw.call("cost_rollup", units=units, revision=rev)
        _collect(out, r)
        out.calculations.append(
            CalcResult(
                label=f"로봇 차량 기계 부품 원가 ({units}대)",
                kind="requirement",
                value=_d(r["total"]),
                unit="USD",
                tool="cost_rollup",
                formula=r["formula"],
                inputs={"units": units},
                revision=r["revision"],
                as_of=_date(r["as_of"]),
                source="parts_list.csv",
            )
        )
        for asm, amount in sorted(r["by_assembly"].items(), key=lambda kv: -Decimal(kv[1])):
            out.calculations.append(
                CalcResult(
                    label=f"{asm} 어셈블리 원가 ({units}대)",
                    kind="requirement",
                    value=_d(amount),
                    unit="USD",
                    tool="cost_rollup",
                    formula="Σ 원천 수량 × 배수 × 대수 × 팩당 단가",
                    inputs={"units": units},
                    revision=r["revision"],
                    as_of=_date(r["as_of"]),
                    source="parts_list.csv",
                )
            )
        out.facts = {
            "total": r["total"],
            "by_assembly": r["by_assembly"],
            "warnings": r["warnings"],
        }

    elif plan.intent == "purchase_quantity":
        targets: list[dict] = []
        if part:
            targets = [{"part": part["sku"], "name": part["name"]}]
        elif plan.pack_filter:
            ex = gw.call("bom_explode", units=units, revision=rev, scope="all")
            _collect(out, ex)
            # 같은 부품이 여러 어셈블리에 쓰이면 소요 낱개를 합쳐서 한 번에 구매 수량을 계산한다
            agg: dict[str, dict] = {}
            for i in ex["items"]:
                if i["pack_size"] == plan.pack_filter:
                    row = agg.setdefault(
                        i["sku"], {"part": i["sku"], "name": i["name"], "required_each": Decimal(0)}
                    )
                    row["required_each"] += Decimal(i["required_each"])
            targets = [{**r, "required_each": str(r["required_each"])} for r in agg.values()]
        rows = []
        for t in targets:
            r = gw.call(
                "purchase_quantity",
                part=t["part"],
                units=None if t.get("required_each") else units,
                required_each=t.get("required_each"),
                revision=rev,
            )
            _collect(out, r)
            short = t["name"][:38]
            out.calculations += [
                CalcResult(
                    label=f"{t['part']} 소요 낱개 ({units}대)",
                    kind="quantity",
                    value=_d(r["required_each"]),
                    unit="ea",
                    tool="bom_explode",
                    formula=f"원천 수량 × 팩 크기 × 배수 × {units}대",
                    inputs={"units": units, "part": t["part"]},
                    revision=r["revision"],
                    source=short,
                ),
                CalcResult(
                    label=f"{t['part']} 구매 팩 수 ({units}대)",
                    kind="purchase",
                    value=Decimal(r["packs_to_buy"]),
                    unit="pack",
                    tool="purchase_quantity",
                    formula=r["formula"],
                    inputs={
                        "units": units,
                        "part": t["part"],
                        "pack_size": r["pack_size"],
                        "moq_packs": r["moq_packs"],
                    },
                    revision=r["revision"],
                    as_of=_date(r["as_of"]),
                    source=short,
                ),
                CalcResult(
                    label=f"{t['part']} 구매 금액 ({units}대)",
                    kind="purchase",
                    value=_d(r["purchase_amount"]),
                    unit="USD",
                    tool="purchase_quantity",
                    formula=f"{r['packs_to_buy']}팩 × ${r['unit_price']}/팩",
                    inputs={"units": units, "part": t["part"]},
                    revision=r["revision"],
                    as_of=_date(r["as_of"]),
                    source=short,
                ),
            ]
            rows.append(
                {
                    k: r[k]
                    for k in (
                        "sku",
                        "required_each",
                        "pack_size",
                        "packs_to_buy",
                        "moq_packs",
                        "unit_price",
                        "purchase_amount",
                    )
                }
            )
        out.facts = {"purchase_rows": rows, "pack_filter": plan.pack_filter}

    elif plan.intent == "price_change":
        wu = gw.call("where_used", part=part["sku"], revision=rev)
        _paths(out, wu)
        r = gw.call(
            "change_impact",
            change_type="price_percent",
            part=part["sku"],
            value=plan.percent,
            units=units,
            revision=rev,
        )
        _collect(out, r)
        base = {
            "tool": "change_impact",
            "inputs": {"units": units, "part": part["sku"], "percent": plan.percent},
            "revision": r["revision"],
            "as_of": _date(r["as_of"]),
            "source": "parts_list.csv",
        }
        out.calculations += [
            CalcResult(
                label=f"변경 전 {_noun(plan, part)} 부품비 ({units}대)",
                kind="requirement",
                value=_d(r["cost_before"]),
                unit="USD",
                formula=f"{r['required_each']}개 × 현재 단가",
                **base,
            ),
            CalcResult(
                label=f"변경 후 {_noun(plan, part)} 부품비 ({units}대)",
                kind="requirement",
                value=_d(r["cost_after"]),
                unit="USD",
                formula=f"{r['required_each']}개 × 단가 {plan.percent}% 변경",
                **base,
            ),
            CalcResult(
                label=f"필요 {_noun(plan, part)} 수량 ({units}대)",
                kind="quantity",
                value=_d(r["required_each"]),
                unit="ea",
                formula=f"1대당 수량 × {units}대",
                **base,
            ),
            CalcResult(
                label=f"추가 {_noun(plan, part)} 부품비 ({units}대)",
                kind="diff",
                value=_d(r["cost_diff"]),
                unit="USD",
                formula=r["formula"],
                **base,
            ),
        ]
        out.facts = {
            "impact_candidates": r["impact_candidates"],
            "required_each": r["required_each"],
        }

    elif plan.intent == "discontinue":
        wu = gw.call("where_used", part=part["sku"], revision=rev)
        _paths(out, wu)
        ex = gw.call("bom_explode", units=units, part=part["sku"], revision=rev, scope="all")
        _collect(out, ex)
        req = sum((Decimal(i["required_each"]) for i in ex["items"]), Decimal(0))
        # 필요 수량을 함께 넘겨, 문서에 가격이 적힌 대체 부품의 부품비 · 차이도 도구가 계산하게 한다
        sr = gw.call("supply_risk", part=part["sku"], revision=rev, qty_each=str(req))
        cr = gw.call(
            "cost_rollup", items=[{"part": part["sku"], "qty_each": str(req)}], revision=rev
        )
        _collect(out, cr)
        formula = " + ".join(i["formula"] for i in ex["items"])
        out.calculations += [
            CalcResult(
                label=f"필요 {_noun(plan, part)} 수량 ({units}대)",
                kind="quantity",
                value=req,
                unit="ea",
                tool="bom_explode",
                formula=formula,
                inputs={"units": units, "part": part["sku"]},
                revision=ex["revision"],
                source="parts_list.csv",
            ),
            CalcResult(
                label=f"{_noun(plan, part)} 소요 금액 ({units}대)",
                kind="requirement",
                value=_d(cr["total"]),
                unit="USD",
                tool="cost_rollup",
                formula=cr["formula"],
                inputs={"units": units, "part": part["sku"]},
                revision=cr["revision"],
                as_of=_date(cr["as_of"]),
                source="parts_list.csv",
            ),
            CalcResult(
                label=f"{_noun(plan, part)} 구매 금액 (팩 · MOQ)",
                kind="purchase",
                value=None,
                unit="USD",
                note="구매 질문이 아니므로 산정하지 않음 (purchase_quantity 로 계산 가능)",
            ),
            CalcResult(
                label=f"{_noun(plan, part)} 단종 추가 비용",
                kind="extra_cost",
                value=None,
                unit="USD",
                note="재작업 · 설정 변경 · 재설계 공수 조건이 없어 미확인 (대체 부품 가격 차이는 따로 계산)",
            ),
        ]
        alts = sr["alternates"]
        for a in alts:
            if a.get("cost_diff") is None:
                continue
            common = {
                "unit": "USD",
                "tool": "supply_risk",
                "inputs": {"units": units, "part": part["sku"], "alternate": a["sku"]},
                "revision": sr["revision"],
                "source": a["source_doc"],
            }
            out.calculations += [
                CalcResult(
                    label=f"대체 {_noun(plan, part)} {a['sku']} 부품비 ({units}대)",
                    kind="requirement",
                    value=_d(a["alternate_cost"]),
                    formula=a["formula"].split(" − ")[0],
                    note=a["price_note"],
                    **common,
                ),
                CalcResult(
                    label=f"대체 {_noun(plan, part)} {a['sku']} 비용 차이 ({units}대)",
                    kind="diff",
                    value=_d(a["cost_diff"]),
                    formula=f"{a['formula']} = 부품비 차이",
                    note=a["price_note"],
                    **common,
                ),
            ]
        suppliers = sr["parts"][0]["suppliers"] if sr["parts"] else []
        out.graph_paths.append(
            GraphPath(
                # 화면에 그대로 나가는 문장이라 관계 이름(ALTERNATE_OF) 대신 업무 용어를 쓴다
                text=f"등록된 대체 부품: {', '.join(a['sku'] for a in alts) or '없음'} · 등록 공급사: "
                f"{', '.join(suppliers) or '없음'}{' (단일 공급)' if len(suppliers) == 1 else ''}",
                tool="supply_risk",
                revision=sr["revision"],
            )
        )
        out.facts = {
            "alternates": alts,
            "suppliers": suppliers,
            "assemblies": [ln["assembly"] for ln in wu["lines"]],
        }
        out.assumptions.append("단종은 교육용 가정")
        if len(suppliers) == 1:
            out.assumptions.append(SINGLE_SUPPLIER_NOTE)
        virtual = [s for s in suppliers if s in VIRTUAL_SUPPLIERS]
        if virtual:  # 가상 공급사를 실제 공급처처럼 말하지 않게 한다
            real = [s for s in suppliers if s not in VIRTUAL_SUPPLIERS]
            note = f"{', '.join(virtual)} 은(는) 교육용 가상 공급사 (원천 데이터에 없음)"
            if real:  # 실제 구매처까지 가상으로 읽히지 않게 함께 적는다
                note += f". {', '.join(real)} 은(는) 원천 부품표의 구매처"
            out.assumptions.append(note)
        # 정비 문서: 단종 뒤에도 이미 만든 차량을 유지보수할 방법(기어 세트 · 샤프트 같은 부분 교체)이
        # 있는지 찾는다. 이 부품에 연결된 문서만 근거로 쓴다. 새 생산의 대체 부품과는 구분한다.
        # 선택 조회: 실패해도 단종 계산은 끝까지 돌려준다. 단, "문서 없음"이 아니라 "조회 실패"로 남긴다
        try:
            sd = gw.call(
                "search_docs",
                query=f"{part.get('name') or part['sku']} repair replacement gearset instead of new",
                k=5,
            )
        except ToolCallError as exc:
            sd = {"hits": []}
            out.facts["maintenance_docs"] = "조회 실패"
            out.assumptions.append(
                f"정비 문서 조회 실패 ({str(exc)[:80]}) — 유지보수 문서가 없다는 뜻이 아닙니다"
            )
        _collect(out, sd)
        docs = [
            _doc_evidence(h) for h in sd["hits"] if part["sku"] in {p["sku"] for p in h["parts"]}
        ]
        out.documents += docs
        # 이 부품의 문서에 부분 교체 안내가 실제로 있을 때만 답변에 쓰게 알려 준다 (다른 부품 사례를 따라 쓰지 않게)
        out.facts.setdefault("maintenance_docs", [])
        if out.facts["maintenance_docs"] != "조회 실패":
            out.facts["maintenance_docs"] = [
                {"path": d.doc_path, "line": d.line}
                for d in docs
                if re.search(
                    r"replace the|replacement (gear|shaft|part)|instead of purchasing",
                    d.excerpt,
                    re.IGNORECASE,
                )
            ]

    elif plan.intent == "revision_change":
        ci = gw.call("change_impact", change_type="ecn", ecn=plan.change_ref, units=units)
        _collect(out, ci)
        ecn = ci["ecn"]
        diff = gw.call("revision_diff", rev_a=ci["revision_from"], rev_b=ci["revision"])
        out.revision = ci["revision"]
        base = {
            "tool": "change_impact",
            "inputs": {"units": units, "ecn": ecn},
            "revision": ci["revision"],
            "as_of": _date(ci["as_of"]),
            "source": "parts_list.csv (각 판)",
        }
        out.calculations += [
            CalcResult(
                label=f"변경 전 로봇 차량 원가 ({units}대)",
                kind="requirement",
                value=_d(ci["cost_before"]),
                unit="USD",
                formula="변경 전 판 Σ 원천 수량 × 배수 × 단가",
                **base,
            ),
            CalcResult(
                label=f"변경 후 로봇 차량 원가 ({units}대)",
                kind="requirement",
                value=_d(ci["cost_after"]),
                unit="USD",
                formula="변경 후 판 Σ 원천 수량 × 배수 × 단가",
                **base,
            ),
            CalcResult(
                label=f"로봇 차량 원가 차이 ({units}대)",
                kind="diff",
                value=_d(ci["cost_diff"]),
                unit="USD",
                formula=ci["formula"],
                **base,
            ),
        ]
        for ch in diff["changes"]:
            before = (
                f"{ch['before_raw_qty']}×{ch['before_multiplier']}" if ch["before_raw_qty"] else "-"
            )
            after = (
                f"{ch['after_raw_qty']}×{ch['after_multiplier']}" if ch["after_raw_qty"] else "-"
            )
            out.graph_paths.append(
                GraphPath(
                    text=f"{ch['change_type']}: {ch['assembly']} · {ch['sku']} ({before} → {after})",
                    tool="revision_diff",
                    revision=ci["revision"],
                    detail={"name": ch["name"]},
                )
            )
        out.graph_paths.append(
            GraphPath(
                text=f"판 {diff['rev_a']} → 판 {diff['rev_b']} · 판 {diff['rev_b']} 저장소상 적용 구간 "
                f"{diff['valid_from_b']} ~ {diff['valid_to_b'] or '현재'}",
                tool="revision_diff",
                revision=diff["rev_b"],
            )
        )
        out.facts = {
            "ecn": ecn,
            "changes": diff["changes"],
            "rev_a": diff["rev_a"],
            "rev_b": diff["rev_b"],
            "rev_b_interval": [diff["valid_from_b"], diff["valid_to_b"] or "현재"],
        }

    elif plan.intent == "supply_disruption":
        sup = SUPPLIER_ALIASES.get((plan.supplier or "").lower(), plan.supplier)
        sr = gw.call("supply_risk", supplier=sup, revision=rev)
        _collect(out, sr)
        out.calculations.append(
            CalcResult(
                label=f"{sup} 단독 공급 부품 수",
                kind="quantity",
                value=Decimal(len(sr["parts"])),
                unit="parts",
                tool="supply_risk",
                formula="선택 판 BOM 부품 중 등록 공급사가 이 회사뿐인 부품 (R1)",
                inputs={"supplier": sup},
                revision=sr["revision"],
                source="erp_supplier_item",
            )
        )
        out.graph_paths.append(
            GraphPath(
                text=f"영향 어셈블리: {', '.join(sr['affected_assemblies']) or '없음'} → Rover",
                tool="supply_risk",
                revision=sr["revision"],
            )
        )
        out.facts = {
            "parts": [p["sku"] for p in sr["parts"]],
            "affected_assemblies": sr["affected_assemblies"],
        }
        out.assumptions.append(f"{sup} 공급 중단은 교육용 가정")
        out.assumptions.append(SINGLE_SUPPLIER_NOTE)

    elif plan.intent == "symptom":
        sd = gw.call("search_docs", query=plan.search_query_en or "", k=5)
        _collect(out, sd)
        candidates: dict[str, dict] = {}
        for h in sd["hits"]:
            out.documents.append(_doc_evidence(h))
            for p in h["parts"]:
                c = candidates.setdefault(
                    p["sku"], {"sku": p["sku"], "name": p["name"], "via_fm": False, "hits": 0}
                )
                c["hits"] += 1
                c["via_fm"] |= p["via"] != "direct"
        ranked = sorted(candidates.values(), key=lambda c: (not c["via_fm"], -c["hits"]))
        if ranked:
            top = ranked[0]
            wu = gw.call("where_used", part=top["sku"], revision=rev)
            _paths(out, wu)
            cr = gw.call("cost_rollup", items=[{"part": top["sku"], "qty_each": "1"}], revision=rev)
            _collect(out, cr)
            # 가격이 없는 부품(단종돼 최신 BOM 에서 빠진 부품 등)은 합계가 0 으로 나온다. 0 을 금액으로 쓰지 않는다
            priced = top["sku"] not in cr.get("missing_prices", [])
            out.calculations.append(
                CalcResult(
                    label="교체 부품비 (1개)",
                    kind="requirement",
                    value=_d(cr["total"]) if priced else None,
                    unit="USD",
                    tool="cost_rollup",
                    formula=cr["formula"],
                    inputs={"part": top["sku"], "qty_each": 1},
                    revision=cr["revision"],
                    as_of=_date(cr["as_of"]),
                    source="parts_list.csv",
                    note="부품비만 — 공임 · 운송비 제외"
                    if priced
                    else "가격 자료 없음 — 선택한 판의 부품표에 단가가 없어 계산하지 않음",
                )
            )
            out.facts = {"candidates": ranked[:3], "top_part": top["sku"]}
        else:
            out.facts = {"candidates": []}

    elif plan.intent == "part_info" and part:
        wu = gw.call("where_used", part=part["sku"], revision=rev)
        _paths(out, wu)
        _history(out, wu)
        sr = gw.call("supply_risk", part=part["sku"], revision=rev)
        _collect(out, sr)
        offers = part.get("offers", [])
        for o in offers:
            out.calculations.append(
                CalcResult(
                    label=f"{part['sku']} 팩당 단가 · {o['supplier']}",
                    kind="reference",
                    value=_d(o["unit_price"]),
                    unit="USD",
                    tool="find_part",
                    formula=f"팩 {o['pack_size']}개 · MOQ {o['moq_packs']}팩",
                    inputs={"part": part["sku"]},
                    as_of=_date(o["observed_at"]),
                    source=o["supplier_id"],
                )
            )
        for a in sr["alternates"]:
            out.graph_paths.append(
                GraphPath(
                    text=f"{part['sku']} -ALTERNATE_OF-> {a['sku']} · {a['compatibility']} "
                    f"· 근거 {a['source_doc']}",
                    tool="supply_risk",
                    revision=sr["revision"],
                )
            )
        suppliers = sr["parts"][0]["suppliers"] if sr["parts"] else []
        out.graph_paths.append(
            GraphPath(
                text=f"등록 공급사: {', '.join(suppliers) or '없음'} · 대체 부품: "
                f"{', '.join(a['sku'] for a in sr['alternates']) or '없음'}",
                tool="supply_risk",
                revision=sr["revision"],
            )
        )
        out.facts = {
            "lines": wu["lines"],
            "suppliers": suppliers,
            "alternates": sr["alternates"],
            "replaced": wu["replaced"],
            "replaced_by": wu["replaced_by"],
        }
    return out


# ─── [Hands-on P2-Ch7-1] 끝 ───
