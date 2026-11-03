"""수강생 오류 수정 과제 확인 (Part 2 Ch2-2 · Ch5-1 · Ch7-2).

    uv run python scripts/exercise.py ch2_2_pack     # 포장 단위 정규화
    uv run python scripts/exercise.py ch5_1_link     # 잘못된 문서 연결 빼기
    uv run python scripts/exercise.py ch7_2_answer   # 틀린 답변을 출력 검사가 잡는지

입력은 data/exercises/exercises.yaml 의 작은 예시뿐이다. Neo4j · LLM · 원천 파일을 쓰지 않으므로
실행 중인 그래프를 깨뜨리지 않는다. 처음 실행하면 ch2_2 · ch5_1 은 실패한다 — 코드를 고친 뒤 다시 실행한다.
되돌리기: git checkout -- src/   (고친 코드를 처음 상태로)
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import yaml

from mfg_bom_agent.contracts.answer import CalcResult, GraphPath
from mfg_bom_agent.foundation.normalize import extract_pack_size
from mfg_bom_agent.retrieval.linking import apply_overrides
from mfg_bom_agent.tools.calc import each_per_product
from mfg_bom_agent.workflows.answer import AnswerDraft, Cited, verify

ROOT = Path(__file__).resolve().parents[1]
EXERCISES = yaml.safe_load(
    (ROOT / "data" / "exercises" / "exercises.yaml").read_text(encoding="utf-8")
)


def ch2_2_pack(ex: dict) -> bool:
    """품명에서 포장 단위를 읽어 1대당 낱개 수를 맞게 계산하는지 본다."""
    ok = True
    for r in ex["rows"]:
        size, basis = extract_pack_size(r["long_name"], r["short_name"])
        each = each_per_product(Decimal(r["raw_qty"]), size, r["multiplier"])
        good = size == r["expected_pack_size"] and each == Decimal(r["expected_each_per_product"])
        ok &= good
        print(f"  {'통과' if good else '실패'}  {r['long_name']}")
        print(
            f"        팩 크기 {size} ({basis}) · 1대당 {each}개  ← 기대 {r['expected_pack_size']} · {r['expected_each_per_product']}개"
        )
    if not ok:
        print(
            "\n  고칠 곳: src/mfg_bom_agent/foundation/normalize.py 의 _PACK_PATTERN · extract_pack_size"
        )
    return ok


def ch5_1_link(ex: dict) -> bool:
    """검수 보정표(LINK_OVERRIDES)가 잘못된 자동 연결을 빼는지 본다."""
    rows = apply_overrides([dict(r) for r in ex["auto_links"]])
    linked = {r["part_id"] for r in rows if r["doc_id"] == ex["doc_id"]}
    removed = all(p not in linked for p in ex["must_remove"])
    kept = all(p in linked for p in ex["must_keep"])
    print(f"  {ex['doc_id']} 연결 부품: {sorted(linked)}")
    print(f"  {'통과' if removed else '실패'}  잘못된 연결 제거 {ex['must_remove']}")
    print(f"  {'통과' if kept else '실패'}  맞는 연결 유지 {ex['must_keep']}")
    if not removed:
        print(
            '\n  고칠 곳: src/mfg_bom_agent/retrieval/linking.py 의 LINK_OVERRIDES 에 (doc_id, part_id, "remove") 추가'
        )
    return removed and kept


def ch7_2_answer(ex: dict) -> bool:
    """틀린 답변은 실패, 맞는 답변은 통과시키는지 본다."""
    calcs = [
        CalcResult(
            label="필요 서보 수량 (1대)",
            kind="quantity",
            value=Decimal(4),
            unit="ea",
            inputs={"units": 1, "part": "2000-0025-0002"},
            revision="6b2c5a9",
        ),
        CalcResult(
            label="추가 모터 부품비 (1대)",
            kind="diff",
            value=Decimal("-13.98"),
            unit="USD",
            inputs={"units": 1, "part": "5203-2402-0027"},
            revision="6b2c5a9",
        ),
    ]
    path = GraphPath(
        text="Rover → rocker bogie → 2000-0025-0002 · 로봇 차량 1대당 4 ea",
        tool="where_used",
        detail={
            "assembly": "rocker bogie",
            "multiplier": 2,
            "raw_qty": "0.5",
            "pack_size": 4,
            "each_per_product": "4",
            "sku": "2000-0025-0002",
        },
    )
    ok = True
    for c in ex["cases"]:
        draft = AnswerDraft(headline=c["headline"], cited=[Cited(**x) for x in c["cited"]])
        v = verify(draft, calcs, "6b2c5a9", 1, paths=[path], facts={})
        good = v.status == c["expected"]
        ok &= good
        why = ", ".join(f"{i.code} '{i.target}'" for i in v.issues) or ", ".join(
            c2.target for c2 in v.checks if not c2.passed
        )
        print(
            f"  {'통과' if good else '실패'}  {c['name']}: 검사 {v.status} (기대 {c['expected']}) {why}"
        )
    if not ok:
        print(
            "\n  고칠 곳: src/mfg_bom_agent/workflows/answer.py 의 verify (Hands-on P2-Ch7-2 구간)"
        )
    return ok


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in EXERCISES:
        print(f"과제 ID: {', '.join(EXERCISES)}")
        return 2
    ex = EXERCISES[name]
    print(f"[{ex['clip']}] {name}")
    ok = globals()[name](ex)
    print("\n결과:", "통과" if ok else "실패 — 안내에 따라 코드를 고친 뒤 다시 실행하세요")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
