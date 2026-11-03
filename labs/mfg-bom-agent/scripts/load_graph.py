"""data/processed → Neo4j 적재 후 온톨로지 검증까지 실행한다 (Part 2 Ch4-1 · Ch3-2).

    uv run python scripts/load_graph.py

검증 위반이 하나라도 있으면 종료 코드 1 로 끝난다. 적재 결과가 온톨로지 정의를 지키는지
매번 확인하기 위해서다.
"""

from __future__ import annotations

import sys

from mfg_bom_agent import ontology
from mfg_bom_agent.graph.client import driver_session
from mfg_bom_agent.graph.load import load_all


def main() -> int:
    with driver_session() as driver:
        counts = load_all(driver)
        print("적재 완료")
        for k, v in counts.items():
            print(f"  {k:14} {v:6}")
        print("온톨로지 검증")
        failed = 0
        for r in ontology.run_validation(driver):
            mark = "통과" if r["violations"] == 0 else f"위반 {r['violations']}"
            if r["violations"]:
                failed += 1
                print(f"  {mark:8} {r['name']} — {r['description']}")
        print(f"  검사 {len(ontology.validation_checks())}개 중 위반 {failed}개")
    # 적재는 기존 노드를 지우고 다시 만든다. 문서 임베딩 · 문서-부품 연결 · 검색 예시도 함께 지워진다
    print("※ 문서 임베딩 · 문서-부품 연결이 지워졌습니다. 검색(CQ-15)을 쓰려면 이어서 실행하세요:")
    print("    uv run python scripts/build_index.py   (한 번에: scripts/init_data.py)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
