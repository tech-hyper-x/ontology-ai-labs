"""Read-only execution of the existing ontology checks. Never loads or resets data."""
import json
from mfg_bom_agent import ontology
from mfg_bom_agent.graph.client import driver_session
def main():
    with driver_session() as driver:rows=ontology.run_validation(driver)
    print(json.dumps(rows,ensure_ascii=False,indent=2))
    failed=[r for r in rows if r['violations']]
    print(f"검사 {len(rows)}개 · 위반이 있는 검사 {len(failed)}개")
    return 1 if failed else 0
if __name__=='__main__':raise SystemExit(main())
