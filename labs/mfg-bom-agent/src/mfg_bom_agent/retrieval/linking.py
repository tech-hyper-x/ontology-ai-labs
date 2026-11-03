"""문서 속 부품 언급 → Part 연결 (Part 2 Ch5-1 정비 문서 인덱스 연결, 방법론 5.1 Entity Linking).

정비 문서 23개 중 품번을 적은 문서는 3개뿐이다. 나머지는 "servo" 같은 이름으로 부품을 말한다.
이 모듈은 문서 청크마다 부품 후보를 찾고, 근거(방법 · 신뢰도 · 언급 문구)와 함께 연결을 만든다.

후보 규칙과 신뢰도
  sku     품번 패턴(예: 2000-0025-0002)이 그대로 있다                  → 1.0
  phrase  두 단어 이상의 별칭(예: "corner servo")이 있다                → 0.8
  word    한 단어 별칭(예: "servo")이 청크에 두 번 이상, 또는 절 제목에 있다 → 0.7
          한 번만 나오면 연결하지 않는다 (흔한 단어라 오연결이 많다)
같은 별칭이 여러 부품을 가리키면 현재 BOM 에 있는 부품을 고르고, 그래도 둘 이상이면 연결하지 않는다.
"""

from __future__ import annotations

import re
from collections import Counter

from neo4j import Driver

MIN_CONFIDENCE = 0.7
_SKU = re.compile(r"\b\d{4}-\d{4}-\d{4}\b")
# 너무 흔해서 부품을 특정하지 못하는 별칭. 연결 후보에서 뺀다.
GENERIC_ALIASES = {
    "wheel",
    "motor",
    "hub",
    "spacer",
    "bracket",
    "plate",
    "beam",
    "screw",
    "nut",
    "washer",
    "bearing",
    "shaft",
    "rod",
    "mount",
    "channel",
    "gorail",
    "standoff",
    "standoffs",
}

# ─── [Hands-on P2-Ch5-1 정비 문서 인덱스 연결] 시작 ───
# 검수에서 찾은 잘못된 연결을 바로잡는 표. (doc_id, part_id, 조치) — 조치: "remove" 또는 "add"
# 예: 바퀴 조립 문서가 "servo" 를 언급하지만 서보 교체 절차가 아니라 배선 안내라면 remove 로 뺀다.
LINK_OVERRIDES: list[tuple[str, str, str]] = [
    ("mechanical/servo_gear_replacement/README.md#1", "P-2000-0025-0002", "add"),
]


def build_alias_index(parts: list[dict]) -> dict[str, list[dict]]:
    """별칭(소문자) → 부품 목록. 부품명에서 "Servo" 같은 핵심 단어도 별칭으로 넣는다."""
    index: dict[str, list[dict]] = {}
    for p in parts:
        names = set(p["aliases"])
        for alias in names:
            alias = alias.strip().lower()
            if len(alias) >= 4 and alias not in GENERIC_ALIASES:
                index.setdefault(alias, []).append(p)
    return index


def find_links(
    chunk: dict, alias_index: dict[str, list[dict]], sku_index: dict[str, dict]
) -> list[dict]:
    """청크 하나에서 부품 연결 후보를 찾아 신뢰도 기준을 넘는 것만 돌려준다."""
    text = chunk["text"].lower()
    title = (chunk.get("title") or "").lower()
    links: dict[str, dict] = {}

    for sku in set(_SKU.findall(chunk["text"])):
        if sku in sku_index:
            links[sku_index[sku]["part_id"]] = {"method": "sku", "confidence": 1.0, "mention": sku}

    for alias, parts in alias_index.items():
        count = len(re.findall(rf"\b{re.escape(alias)}\b", text))
        if not count:
            continue
        if " " in alias:
            conf = 0.8
        elif count >= 2 or re.search(rf"\b{re.escape(alias)}\b", title):
            conf = 0.7
        else:
            continue  # 한 단어 별칭이 한 번만 나오면 오연결 위험이 커서 건너뛴다
        candidates = parts if len(parts) == 1 else [p for p in parts if p["in_latest"]]
        if len(candidates) != 1:
            continue  # 별칭이 여러 부품을 가리키면 고르지 않는다 (미연결로 남겨 검토)
        pid = candidates[0]["part_id"]
        if pid not in links or links[pid]["confidence"] < conf:
            links[pid] = {
                "method": "phrase" if " " in alias else "word",
                "confidence": conf,
                "mention": alias,
            }
    return [{"part_id": k, **v} for k, v in links.items() if v["confidence"] >= MIN_CONFIDENCE]


def apply_overrides(
    rows: list[dict], overrides: list[tuple[str, str, str]] | None = None
) -> list[dict]:
    """자동 연결 결과에 검수 보정표를 적용한다. remove 는 그 연결을 빼고, add 는 검수 연결로 넣는다."""
    for doc_id, part_id, action in LINK_OVERRIDES if overrides is None else overrides:
        rows = [r for r in rows if not (r["doc_id"] == doc_id and r["part_id"] == part_id)]
        if action == "add":
            rows.append(
                {
                    "doc_id": doc_id,
                    "part_id": part_id,
                    "method": "override",
                    "confidence": 1.0,
                    "mention": "검수 추가",
                    "line": None,
                }
            )
    return rows


def link_documents(driver: Driver) -> dict[str, int]:
    """모든 문서 청크에 부품 연결(DESCRIBED_IN)을 만든다. 이전 자동 연결은 지우고 다시 만든다."""
    parts = [
        r.data()
        for r in driver.execute_query(
            "MATCH (p:Part) RETURN p.part_id AS part_id, p.sku AS sku, p.aliases AS aliases, p.in_latest AS in_latest"
        ).records
    ]
    alias_index = build_alias_index(parts)
    sku_index = {p["sku"]: p for p in parts}
    docs = [
        r.data()
        for r in driver.execute_query(
            "MATCH (d:Document) RETURN d.doc_id AS doc_id, d.title AS title, d.text AS text, d.line AS line"
        ).records
    ]

    rows = []
    for doc in docs:
        for link in find_links(doc, alias_index, sku_index):
            rows.append({"doc_id": doc["doc_id"], "line": doc["line"], **link})
    rows = apply_overrides(rows)

    driver.execute_query(
        "MATCH (:Part)-[x:DESCRIBED_IN]->(:Document) WHERE x.method <> 'curated' DELETE x"
    )
    driver.execute_query(
        """
        UNWIND $rows AS r
        MATCH (p:Part {part_id: r.part_id}) MATCH (d:Document {doc_id: r.doc_id})
        MERGE (p)-[x:DESCRIBED_IN]->(d)
        SET x.method = r.method, x.confidence = r.confidence, x.mention = r.mention,
            x.line = coalesce(r.line, d.line)
    """,
        rows=rows,
    )
    methods = Counter(r["method"] for r in rows)
    return {"links": len(rows), "docs_linked": len({r["doc_id"] for r in rows}), **methods}


# ─── [Hands-on P2-Ch5-1] 끝 ───
