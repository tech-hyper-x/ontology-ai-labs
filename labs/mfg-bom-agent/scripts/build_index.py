"""문서-부품 연결 + 임베딩 + 검색 색인을 만든다 (Part 2 Ch5).

    uv run python scripts/build_index.py            # .env 의 EMBEDDING_PROVIDER 사용 (voyage)
    uv run python scripts/build_index.py --hash     # 로컬 대체 임베딩으로 강제

Voyage 키가 비었거나 무효면 자동으로 로컬 대체 임베딩(hash:local)을 쓰고 이유를 출력한다.
어떤 공급자를 썼는지는 Neo4j 의 LabMeta 에 남아 검색할 때 같은 공급자를 쓴다.
"""

from __future__ import annotations

import sys

from mfg_bom_agent.graph.client import driver_session
from mfg_bom_agent.retrieval.hybrid import hybrid_search, index_documents
from mfg_bom_agent.retrieval.linking import link_documents


def main() -> int:
    provider = "hash" if "--hash" in sys.argv[1:] else None
    with driver_session() as driver:
        links = link_documents(driver)
        print(f"문서-부품 연결: {links}")
        info = index_documents(driver, provider)
        print(
            f"임베딩 · 색인: 문서 {info['documents']}개 · 검색 예시 {info['examples']}개 · 공급자 {info['provider']}"
        )
        if info["fallback_reason"]:
            print(f"  ※ 로컬 대체 임베딩 사용 — 이유: {info['fallback_reason']}")
        demo = hybrid_search(driver, "corner wheels will not turn", k=3)
        print(
            "확인 검색 (CQ-15): 'corner wheels will not turn' — 결합 순위 · BM25 순위 · 벡터 순위"
        )
        for r in demo["results"]:
            parts = ", ".join(sorted({p["sku"] for p in r["parts"]})) or "-"
            rk = r["ranks"]
            print(
                f"  {r['rank']}위 {r['score']:.4f} BM25 {rk.get('bm25', '-')} · 벡터 {rk.get('vector', '-')}"
                f" · {r['doc_id']} · 연결 부품 {parts}"
            )
        for w in demo["warnings"]:
            print(f"  ※ {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
