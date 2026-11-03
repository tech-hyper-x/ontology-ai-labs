"""data/processed 테이블 → Neo4j 지식 그래프 적재 (Part 2 Ch4-1 부품 그래프 적재).

실행: uv run python scripts/load_graph.py   (컨테이너: docker compose --profile init run --rm init)

적재 순서: 기존 실습 데이터 삭제 → 제약 조건 → 노드(제품 · 어셈블리 · 부품 · 판 · 공급사 · 문서 · 고장 모드)
          → BOM 라인과 관계 → 변경 · 대체 · 고장 관계 → 검증(ontology.run_validation)

모든 쿼리는 값을 파라미터($rows)로 넘긴다. 라벨 · 관계 이름은 코드 상수에서만 온다 (Cypher 주입 방지).
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from neo4j import Driver

from mfg_bom_agent import ontology
from mfg_bom_agent.config import get_settings

PROCESSED_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"
BATCH = 500


def read_table(name: str) -> list[dict[str, str]]:
    """processed CSV 하나를 읽는다."""
    with (PROCESSED_DIR / f"{name}.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _batches(rows: list[dict], size: int = BATCH) -> Iterable[list[dict]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def _run(driver: Driver, cypher: str, rows: list[dict]) -> int:
    for chunk in _batches(rows):
        driver.execute_query(cypher, rows=chunk)
    return len(rows)


def _bool(v: str) -> bool:
    return str(v).strip().lower() in {"true", "1", "yes"}


def clear_lab_data(driver: Driver) -> None:
    """이전 적재분을 지운다. LabMeta(적재 기록)는 남긴다. 큰 그래프도 메모리 부족 없이 지우도록 나눠서 지운다."""
    # CALL { } IN TRANSACTIONS 는 자동 커밋(implicit) 트랜잭션에서만 돌아서 session.run 으로 실행한다.
    with driver.session() as session:
        session.run(
            "MATCH (n) WHERE NOT n:LabMeta CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 5000 ROWS"
        ).consume()


# ─── [Hands-on P2-Ch4-1 부품 그래프 적재] 시작 ───
def load_all(driver: Driver) -> dict[str, int]:
    """processed 테이블 전체를 그래프로 적재하고 노드 · 관계 건수를 돌려준다."""
    counts: dict[str, int] = {}
    clear_lab_data(driver)
    for stmt in ontology.constraint_statements():
        driver.execute_query(stmt)

    driver.execute_query(
        "MERGE (p:Product {product_id: 'OSR'}) "
        "SET p.name = 'NASA JPL Open Source Rover', p.origin = 'source'"
    )
    counts["Assembly"] = _run(
        driver,
        """
        UNWIND $rows AS r
        MERGE (a:Assembly {assembly_id: r.assembly_id})
        SET a.name = r.name, a.domain = r.domain, a.product_id = r.product_id, a.origin = r.origin
    """,
        read_table("plm_assembly"),
    )

    parts = read_table("plm_item_master")
    for p in parts:
        p["aliases"] = [a for a in p["aliases"].split("|") if a]
        p["pack_size"] = int(p["pack_size"])
        p["in_latest"] = _bool(p["in_latest"])
    counts["Part"] = _run(
        driver,
        """
        UNWIND $rows AS r
        MERGE (p:Part {part_id: r.part_id})
        SET p.sku = r.sku, p.name = r.name, p.aliases = r.aliases, p.domain = r.domain,
            p.mpn = r.mpn, p.pack_size = r.pack_size, p.pack_basis = r.pack_basis,
            p.in_latest = r.in_latest, p.origin = r.origin,
            p.search_text = r.sku + ' ' + r.name + ' ' + reduce(s = '', a IN r.aliases | s + ' ' + a)
    """,
        parts,
    )
    # 부품 이름 · 약칭 검색용 전문 색인 (CQ-12, find_part 도구). 품번 정확 일치는 고유성 제약 색인이 맡는다.
    driver.execute_query(
        "CREATE FULLTEXT INDEX part_search IF NOT EXISTS FOR (p:Part) ON EACH [p.search_text]"
    )

    revisions = read_table("plm_revision")
    for r in revisions:
        r["is_latest"] = _bool(r["is_latest"])
    counts["Revision"] = _run(
        driver,
        """
        UNWIND $rows AS r
        MERGE (v:Revision {revision_id: r.revision_id})
        SET v.committed_at = date(r.committed_at), v.valid_from = date(r.valid_from),
            v.valid_to = CASE r.valid_to WHEN '' THEN null ELSE date(r.valid_to) END,
            v.is_latest = r.is_latest, v.message = r.message, v.origin = r.origin
    """,
        revisions,
    )

    # BOM 라인: 수량은 계산용 숫자(raw_qty 등)와 원천 문자열(raw_qty_text)을 함께 둔다.
    # 금액 · 수량 계산은 도구가 문자열을 Decimal 로 바꿔서 하므로 부동소수 오차가 생기지 않는다.
    lines = read_table("plm_ebom_line")
    for ln in lines:
        ln["raw_qty_text"], ln["qty_each_text"] = ln["raw_qty"], ln["qty_each"]
        ln["raw_qty"], ln["qty_each"] = float(ln["raw_qty"]), float(ln["qty_each"])
        ln["pack_size"], ln["multiplier"], ln["row_no"] = (
            int(ln["pack_size"]),
            int(ln["multiplier"]),
            int(ln["row_no"]),
        )
    parent_label = {"Product": ("Product", "product_id"), "Assembly": ("Assembly", "assembly_id")}
    child_label = {"Assembly": ("Assembly", "assembly_id"), "Part": ("Part", "part_id")}
    for ptype, (plabel, pkey) in parent_label.items():
        for ctype, (clabel, ckey) in child_label.items():
            subset = [
                ln for ln in lines if ln["parent_type"] == ptype and ln["child_type"] == ctype
            ]
            if not subset:
                continue
            _run(
                driver,
                f"""
                UNWIND $rows AS r
                MATCH (p:{plabel} {{{pkey}: r.parent_id}})
                MATCH (c:{clabel} {{{ckey}: r.child_id}})
                MATCH (v:Revision {{revision_id: r.revision_id}})
                MERGE (l:BOMLine {{bomline_id: r.bomline_id}})
                SET l.revision_id = r.revision_id, l.row_no = r.row_no, l.short_name = r.short_name,
                    l.raw_qty = r.raw_qty, l.raw_qty_text = r.raw_qty_text, l.pack_size = r.pack_size,
                    l.pack_basis = r.pack_basis, l.qty_each = r.qty_each, l.qty_each_text = r.qty_each_text,
                    l.multiplier = r.multiplier, l.unit = r.unit, l.origin = r.origin, l.source_ref = r.source_ref,
                    l.unit_price = r.unit_price, l.price_observed_at = r.price_observed_at
                MERGE (p)-[:HAS_BOM_LINE]->(l)
                MERGE (l)-[:REFERS_TO]->(c)
                MERGE (l)-[:IN_REVISION]->(v)
            """,
                subset,
            )
    counts["BOMLine"] = len(lines)

    counts["Supplier"] = _run(
        driver,
        """
        UNWIND $rows AS r MERGE (s:Supplier {supplier_id: r.supplier_id}) SET s.name = r.name, s.origin = r.origin
    """,
        read_table("erp_supplier"),
    )
    offers = read_table("erp_supplier_item")
    for o in offers:
        o["pack_size"], o["moq_packs"], o["lead_time_days"] = (
            int(o["pack_size"]),
            int(o["moq_packs"]),
            int(o["lead_time_days"]),
        )
    counts["SUPPLIED_BY"] = _run(
        driver,
        """
        UNWIND $rows AS r
        MATCH (p:Part {part_id: r.part_id}) MATCH (s:Supplier {supplier_id: r.supplier_id})
        MERGE (p)-[o:SUPPLIED_BY]->(s)
        SET o.supplier_sku = r.supplier_sku, o.unit_price = r.unit_price, o.currency = r.currency,
            o.pack_size = r.pack_size, o.moq_packs = r.moq_packs, o.lead_time_days = r.lead_time_days,
            o.observed_at = date(r.observed_at), o.price_date = null, o.url = r.url,
            o.origin = r.origin, o.terms_origin = r.terms_origin
    """,
        offers,
    )

    counts["ECN"] = _run(
        driver,
        """
        UNWIND $rows AS r
        MERGE (e:ECN {ecn_id: r.ecn_id})
        SET e.revision_from = r.revision_from, e.revision_to = r.revision_to, e.ecn_date = date(r.ecn_date),
            e.title = r.title, e.reason = r.reason, e.origin = r.origin
    """,
        read_table("plm_ecn"),
    )
    ecn_lines = read_table("plm_ecn_line")
    ecn_rev = {e["ecn_id"]: e for e in read_table("plm_ecn")}
    for ln in ecn_lines:
        e = ecn_rev[ln["ecn_id"]]
        # 삭제된 라인은 이전 판에, 추가 · 변경된 라인은 새 판에 있다
        rev = e["revision_from"] if ln["change_type"] == "removed" else e["revision_to"]
        ln["bomline_id"] = f"{rev}:{ln['assembly_id']}:{ln['part_id']}"
    counts["CHANGED_BY"] = _run(
        driver,
        """
        UNWIND $rows AS r
        MATCH (l:BOMLine {bomline_id: r.bomline_id}) MATCH (e:ECN {ecn_id: r.ecn_id})
        MERGE (l)-[c:CHANGED_BY]->(e)
        SET c.change_type = r.change_type, c.before_raw_qty = r.before_raw_qty, c.after_raw_qty = r.after_raw_qty,
            c.before_multiplier = r.before_multiplier, c.after_multiplier = r.after_multiplier
    """,
        ecn_lines,
    )
    counts["SUPERSEDES"] = _run(
        driver,
        """
        UNWIND $rows AS r
        MATCH (n:Part {part_id: r.new_part_id}) MATCH (o:Part {part_id: r.old_part_id})
        MERGE (n)-[s:SUPERSEDES]->(o)
        SET s.ecn_id = r.ecn_id, s.assembly_id = r.assembly_id, s.effective_date = date(r.effective_date),
            s.origin = r.origin
    """,
        read_table("plm_supersedes"),
    )
    alternates = read_table("plm_alternate")
    for a in alternates:
        a["requires_rework"] = _bool(a["requires_rework"])
    counts["ALTERNATE_OF"] = _run(
        driver,
        """
        UNWIND $rows AS r
        MATCH (p:Part {part_id: r.part_id}) MATCH (a:Part {part_id: r.alternate_part_id})
        MERGE (p)-[x:ALTERNATE_OF]->(a)
        SET x.compatibility = r.compatibility, x.requires_rework = r.requires_rework,
            x.source_doc = r.source_doc, x.source_section = r.source_section,
            x.source_date = date(r.source_date), x.origin = r.origin,
            x.pack_price = r.pack_price, x.pack_size = toInteger(r.pack_size),
            x.price_note = r.price_note
    """,
        alternates,
    )

    docs = read_table("quality_document")
    for d in docs:
        d["line"] = int(d["line"])
    counts["Document"] = _run(
        driver,
        """
        UNWIND $rows AS r
        MERGE (d:Document {doc_id: r.doc_id})
        SET d.source = r.source, d.path = r.path, d.title = r.title, d.line = r.line,
            d.text = r.text, d.origin = r.origin
    """,
        docs,
    )

    # 고장 모드는 근거 문서의 "그 줄을 포함하는 절"에 연결한다
    fms = read_table("quality_failure_mode")
    for fm in fms:
        candidates = [
            d for d in docs if d["path"] == fm["doc_path"] and d["line"] <= int(fm["doc_line"])
        ]
        fm["doc_id"] = max(candidates, key=lambda d: d["line"])["doc_id"] if candidates else None
    counts["FailureMode"] = _run(
        driver,
        """
        UNWIND $rows AS r
        MERGE (f:FailureMode {fm_id: r.fm_id})
        SET f.name = r.name, f.symptom = r.symptom, f.severity = r.severity, f.origin = r.origin
        WITH f, r
        MATCH (p:Part {part_id: r.part_id})
        MERGE (p)-[h:HAS_FAILURE_MODE]->(f) SET h.severity = r.severity
        WITH f, r
        MATCH (d:Document {doc_id: r.doc_id})
        MERGE (f)-[x:DESCRIBED_IN]->(d) SET x.method = 'curated', x.confidence = 1.0, x.line = toInteger(r.doc_line)
    """,
        fms,
    )

    s = get_settings()
    driver.execute_query(
        "MERGE (m:LabMeta {project: 'mfg-bom-agent'}) "
        "SET m.dataset_version = $v, m.loaded_at = datetime(), m.counts = $c",
        v=s.dataset_version,
        c=[f"{k}={v}" for k, v in counts.items()],
    )
    return counts


# ─── [Hands-on P2-Ch4-1] 끝 ───
