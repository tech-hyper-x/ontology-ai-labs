"""지식 그래프 초기화: 제약 → 적재 → 검증 → 문서 연결 · 색인을 한 번에 실행한다.

    uv run python scripts/init_data.py            (컨테이너: docker compose --profile init run --rm init)

실습 흐름의 "Data Foundation → Knowledge Graph 적재 → Hybrid Search" 단계를 한 명령으로 묶은 것이다
(정의서 5절, 10절). 단계별로 따로 실행하려면 load_graph.py · build_index.py 를 쓴다.

몇 번을 다시 실행해도 결과가 같다 (idempotent). 적재 전에 이전 실습 데이터를 지우고, 제약은 IF NOT EXISTS 로 만든다.
"""

from __future__ import annotations

import sys

from mfg_bom_agent import ontology
from mfg_bom_agent.config import get_settings
from mfg_bom_agent.graph.client import driver_session
from mfg_bom_agent.graph.load import load_all
from mfg_bom_agent.retrieval.hybrid import index_documents
from mfg_bom_agent.retrieval.linking import link_documents


def main() -> int:
    s = get_settings()
    with driver_session() as driver:
        counts = load_all(driver)  # 제약 조건(ontology/schema.yaml 기준) 포함
        print("적재: " + " · ".join(f"{k} {v}" for k, v in counts.items()))
        violations = [r for r in ontology.run_validation(driver) if r["violations"]]
        print(
            f"온톨로지 검증: 검사 {len(ontology.validation_checks())}개 · 위반 {len(violations)}개"
        )
        for r in violations:
            print(f"  위반 {r['violations']} · {r['name']} — {r['description']}")
        links = link_documents(driver)
        print(f"문서-부품 연결: {links['links']}건 (문서 {links['docs_linked']}개)")
        info = index_documents(driver)
        print(f"검색 색인: 문서 {info['documents']}개 · 임베딩 {info['provider']}")
        if info["fallback_reason"]:
            print(f"  ※ 로컬 대체 임베딩 사용 — {info['fallback_reason']}")
        print(f"완료: dataset_version={s.dataset_version}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
