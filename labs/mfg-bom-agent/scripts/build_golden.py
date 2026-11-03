"""Golden Set(기준 문항 45개)을 만든다 (Part 2 Ch8 계산 결과 평가와 오류 분석).

    uv run python scripts/build_golden.py   →  data/golden/golden_set.yaml

정답(expected)은 evaluation/reference.py 가 processed CSV 에서 도구와 독립적으로 계산한다.
문항 구성: 수량 10 · 원가 10 · 관계 탐색 10 · Revision · ECN 8 · 문서 근거 7

정답 형식
  number  {value, unit, tol, units?}   최종 답변에 같은 단위로 tol 안의 값이 있으면 정답
          {metric: diff, direction}     차이 값은 크기(value)와 방향(increase · decrease · none)을 함께 본다
  set     {values}            최종 답변에 정답 항목이 모두 있고, 같은 종류의 다른 항목이 없으면 정답(exact)
  doc     {path}              최종 답변(문서 인용 포함)에 이 경로가 나오면 정답
채점 규칙은 evaluation/scoring.py (SCORING_VERSION). 도구 정답 · 최종 답변 정답을 따로 기록한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from mfg_bom_agent.evaluation import reference as R

OUT = Path(__file__).resolve().parents[1] / "data" / "golden" / "golden_set.yaml"


def num(v, unit: str, tol: str = "0.01", **extra) -> dict:
    """숫자 정답. extra 에 계산 조건(units: 생산 대수)을 함께 적는다."""
    return {"type": "number", "value": str(v), "unit": unit, "tol": tol, **extra}


def change(v, units: int, tol: str = "0.01") -> dict:
    """차이 정답. 크기와 방향을 나눠 적는다 (−13.98 → 13.98 · decrease). 방향이 반대면 오답이다."""
    v = R.Decimal(v)
    direction = "increase" if v > 0 else "decrease" if v < 0 else "none"
    return num(abs(v), "USD", tol, metric="diff", direction=direction, units=units)


def sset(values) -> dict:
    return {"type": "set", "values": sorted(values)}


def build() -> list[dict]:
    q: list[dict] = []

    def add(cat: str, question: str, expected: dict, note: str = "") -> None:
        q.append(
            {
                "id": f"G{len(q) + 1:02d}",
                "category": cat,
                "question": question,
                "expected": expected,
                "note": note,
            }
        )

    # ── 수량 10 ─────────────────────────────────────────────
    for part, units, name in [
        ("2000-0025-0002", 50, "서보"),
        ("5203-2402-0027", 20, "모터"),
        ("3616-0014-0144", 10, "휠"),
        ("1522-0010-0060", 20, "8mm ID 스페이서(6mm)"),
        ("1137-0001-0001", 30, "90도 스틸 브래킷"),
        ("1611-0514-0008", 15, "플랜지 베어링"),
    ]:
        add(
            "수량",
            f"로버 {units}대를 만들 때 {name} {part} 은(는) 낱개로 몇 개 필요한가?",
            num(R.required_each(part, units), "ea", "0", units=units),
            "낱개 = 원천 수량 × 팩 크기 × 배수 × 대수",
        )
    for part, units, name in [
        ("1522-0010-0060", 20, "8mm ID 스페이서(6mm, 4개입)"),
        ("1137-0001-0001", 20, "90도 스틸 브래킷(2개입)"),
        ("1611-0514-0008", 7, "플랜지 베어링(2개입)"),
        ("2000-0025-0002", 12, "서보"),
    ]:
        packs, _ = R.purchase_packs(part, units)
        add(
            "수량",
            f"로버 {units}대 생산 시 {name} {part} 은(는) 몇 팩을 구매해야 하나?",
            num(packs, "pack", "0", units=units),
            "구매 팩 수 = max(올림(소요 낱개 ÷ 팩 크기), MOQ)",
        )

    # ── 원가 10 ─────────────────────────────────────────────
    add("원가", "로버 1대의 기계 BOM 원가는?", num(R.cost(1), "USD", units=1))
    add("원가", "로버 10대의 기계 BOM 소요 원가는?", num(R.cost(10), "USD", units=10))
    for asm in ["drive wheel", "rocker bogie", "body"]:
        add(
            "원가",
            f"로버 1대 기준 {asm} 어셈블리 원가는?",
            num(R.cost(1, assembly=asm), "USD", units=1),
        )
    add(
        "원가",
        "모터 5203-2402-0027 단가가 15% 오르면 로버 100대 원가는 얼마나 늘어나나?",
        change(R.price_change_diff("5203-2402-0027", "15", 100), 100),
    )
    add(
        "원가",
        "모터 단가 15% 인상 시 로버 1대 원가 증가액은?",
        change(R.price_change_diff("5203-2402-0027", "15", 1), 1),
    )
    add(
        "원가",
        "서보 2000-0025-0002 단가가 10% 오르면 50대 원가 차이는?",
        change(R.price_change_diff("2000-0025-0002", "10", 50), 50),
    )
    add(
        "원가",
        "휠 3616-0014-0144 단가가 5% 내리면 로버 20대 원가는 얼마나 줄어드나?",
        change(R.price_change_diff("3616-0014-0144", "-5", 20), 20),
        "감소 방향 · 감소액 크기로 채점",
    )
    add(
        "원가",
        "서보 2000-0025-0002 단종 가정 시 50대 생산에 필요한 서보의 소요 금액은?",
        num(
            R.required_each("2000-0025-0002", 50)
            * R.Decimal(R.offer("2000-0025-0002")["unit_price"]),
            "USD",
            units=50,
        ),
    )

    # ── 관계 탐색 10 ─────────────────────────────────────────
    add(
        "관계 탐색",
        "서보 2000-0025-0002 는 어느 어셈블리에 쓰이나?",
        sset(R.where_used("2000-0025-0002")),
    )
    add(
        "관계 탐색",
        "부품 1120-0002-0072 가 쓰이는 어셈블리를 모두 알려줘",
        sset(R.where_used("1120-0002-0072")),
    )
    add(
        "관계 탐색",
        "현재 BOM 에서 두 개 이상의 어셈블리에 함께 쓰이는 공용 부품은?",
        sset(R.shared_parts()),
    )
    add("관계 탐색", "corner 어셈블리의 구성 부품 품번은?", sset(R.assembly_parts("corner")))
    add(
        "관계 탐색",
        "모터 5203-2402-0027 를 공급하는 등록 공급사는?",
        sset(R.suppliers_of("5203-2402-0027")),
    )
    add(
        "관계 탐색",
        "goBILDA 공급 중단 가정 시 다른 공급처가 없는 부품은 몇 개인가?",
        num(len(R.single_supplier_parts("gobilda.com")), "parts", "0"),
    )
    add(
        "관계 탐색",
        "goBILDA 공급 중단 가정 시 영향받는 어셈블리는?",
        sset({a for p in R.single_supplier_parts("gobilda.com") for a in R.where_used(p)}),
    )
    add(
        "관계 탐색",
        "휠 3616-0014-0144 대신 쓸 수 있는 대체 부품은?",
        sset(R.alternates("3616-0014-0144")),
    )
    add(
        "관계 탐색",
        "서보 2000-0025-0002 의 등록 대체 부품이 있나? 등록 공급사는?",
        sset({"gobilda.com"}),
        "대체 부품 없음 · 공급사 goBILDA 하나",
    )
    add(
        "관계 탐색",
        "모터 5203-2402-0027 가 바뀌면 영향 검토가 필요한 어셈블리는?",
        sset(R.where_used("5203-2402-0027")),
    )

    # ── Revision · ECN 8 ───────────────────────────────────
    e = R.ecn_by_date("2024-06")
    add(
        "Revision · ECN",
        "2024-06 교육용 ECN 으로 바뀐 BOM 라인의 부품은?",
        sset(R.ecn_changed_parts(e["ecn_id"])),
    )
    add(
        "Revision · ECN",
        "2024-06 ECN 전후 로버 1대 원가 차이는?",
        change(R.ecn_cost_diff(e["ecn_id"]), 1),
    )
    add(
        "Revision · ECN",
        "모터 5203-2402-0027 이 교체한 이전 부품은?",
        sset(R.superseded_by("5203-2402-0027")),
    )
    add(
        "Revision · ECN",
        "스페이서 1522-0010-0060 은 어떤 부품을 대체했나?",
        sset(R.superseded_by("1522-0010-0060")),
    )
    e = R.ecn_by_date("2023-10-04")
    add(
        "Revision · ECN",
        "2023-10-04 ECN 에서 수량이 바뀐 부품은?",
        sset(R.ecn_changed_parts(e["ecn_id"])),
    )
    add(
        "Revision · ECN",
        "2023-10-04 ECN 전후 로버 1대 원가 차이는?",
        change(R.ecn_cost_diff(e["ecn_id"]), 1),
        "41-hole beam 6개 → 4개로 감소 (음수)",
    )
    e = R.ecn_by_date("2024-11")
    add(
        "Revision · ECN",
        "2024-11 ECN 전후 로버 1대 원가 차이는?",
        change(R.ecn_cost_diff(e["ecn_id"]), 1),
    )
    vf, vt = R.revision_interval("72edc6e")
    add("Revision · ECN", "BOM 판 72edc6e 의 저장소상 적용 구간은?", sset({vf, vt}))

    # ── 문서 근거 7 ─────────────────────────────────────────
    add("문서 근거", "코너 휠이 돌지 않을 때 점검할 부품은?", sset({"2000-0025-0002"}))
    add(
        "문서 근거",
        "코너 휠이 돌지 않을 때 근거가 되는 정비 문서는?",
        {"type": "doc", "path": "mechanical/servo_gear_replacement/README.md"},
    )
    add(
        "문서 근거",
        "코너 휠이 돌지 않을 때 교체 부품비(서보 1개, 공임 제외)는?",
        num(R.Decimal(R.offer("2000-0025-0002")["unit_price"]), "USD"),
    )
    add(
        "문서 근거",
        "서보 기어가 부서졌을 때 교체 절차가 있는 문서는?",
        {"type": "doc", "path": "mechanical/servo_gear_replacement/README.md"},
    )
    add(
        "문서 근거",
        "휠 대체 부품의 가공 조건이 적힌 문서는?",
        {"type": "doc", "path": "parts_list/extra_parts.md"},
    )
    add(
        "문서 근거",
        "goBILDA 스페이서 1514-0010-0060 단종을 다룬 이슈는?",
        {"type": "doc", "path": "issues/469"},
    )
    add(
        "문서 근거",
        "구동 모터 기어가 부서지는 문제를 다룬 이슈는?",
        {"type": "doc", "path": "issues/178"},
    )
    return q


def main() -> int:
    items = build()
    counts: dict[str, int] = {}
    for it in items:
        counts[it["category"]] = counts.get(it["category"], 0) + 1
    OUT.write_text(
        yaml.safe_dump(
            {"version": "1.1", "snapshot": "a78f9eb", "items": items},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    print(f"Golden Set {len(items)}문항 → {OUT.relative_to(OUT.parents[2])}  {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
