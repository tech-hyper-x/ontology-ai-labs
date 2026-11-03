"""Ch4: CSV 입력·DB 건수·온톨로지 규칙·CQ 사용처를 읽기 전용으로 대조합니다.
실행 위치: labs/mfg-bom-agent / uv run python ../../examples/ch04_audit.py
"""
from __future__ import annotations
import csv
from pathlib import Path
from mfg_bom_agent import ontology
from mfg_bom_agent.graph.client import driver_session
from mfg_bom_agent.graph.cq import run_cq
from mfg_bom_agent.evaluation import reference


def main() -> int:
    processed = Path("data/processed")
    expected = {}
    for filename, label in [("plm_item_master", "Part"), ("plm_assembly", "Assembly"),
                            ("plm_revision", "Revision"), ("plm_ebom_line", "BOMLine")]:
        with (processed / (filename + ".csv")).open(encoding="utf-8", newline="") as f:
            expected[label] = sum(1 for _ in csv.DictReader(f))
    failed = 0
    with driver_session() as driver:
        for label, rows in expected.items():
            records, _, _ = driver.execute_query(f"MATCH (n:{label}) RETURN count(n) AS n")
            actual = records[0]["n"]
            print(f"{label}: CSV={rows}, DB={actual}, 일치={rows == actual}")
            failed += int(rows != actual)
        checks = ontology.run_validation(driver)
        bad = [c for c in checks if c["violations"]]
        print(f"검사 {len(checks)}개 / 위반 검사 {len(bad)}개")
        failed += len(bad)
        for sku in ["3616-0014-0144", "1522-0010-0060"]:
            rows = run_cq(driver, "CQ-01", part=sku, revision=None)
            actual = {a for row in rows for a in row["assemblies"]}
            expected_asms = reference.where_used(sku)
            ok = actual == expected_asms
            print(f"{sku}: CSV 사용처={sorted(expected_asms)}, DB={sorted(actual)}, 일치={ok}")
            failed += int(not ok)
    return int(failed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
