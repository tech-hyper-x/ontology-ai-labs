"""data/processed/graph → Neo4j 적재 후 온톨로지 검증까지 실행한다 (설계 덱 31 · 33장).

    uv run python scripts/load_graph.py

검증 위반이 하나라도 있으면 종료 코드 1 로 끝난다. 문헌 색인은 build_index.py 로 따로 만든다.
"""

from __future__ import annotations

import sys

from bio_target_agent.graph.client import driver_session
from bio_target_agent.graph.load import load_all
from bio_target_agent.ontology import run_validation


def main() -> int:
    with driver_session() as driver:
        r = load_all(driver)
        print({**r["nodes"], **r["rels"], "claims": r["claims"]})
        results = run_validation(driver)
    bad = [c for c in results if c["violations"]]
    for c in results:
        print(f"{'✗' if c['violations'] else '✓'} {c['name']:45} {c['violations']}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
