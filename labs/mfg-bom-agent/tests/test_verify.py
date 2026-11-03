"""답변 출력 검사 회귀 테스트 (Part 2 Ch7-2). Neo4j · LLM 없이 실행한다.

검토 보고서 F1 의 재현 입력(도구 4개 · 답변 2개 · 인용 없음)을 포함해, 수량 · 단위 · 조건 · 증감 방향 ·
인용 누락 · 식별자 숫자 오검출을 확인한다. 테스트 ID(M-V01 …)는 실행 계획서 6절의 번호다.
"""

from decimal import Decimal

import pytest

from mfg_bom_agent.contracts.answer import CalcResult, GraphPath
from mfg_bom_agent.workflows.answer import AnswerDraft, Cited, verify, withheld_answer

REV = "6b2c5a9"

# 서보 2000-0025-0002: 원천 0.5팩 × 4개입 × 배수 2 = 로버 1대당 4개
SERVO_PATH = GraphPath(
    text="Rover → rocker bogie (배수 ×2) → BOMLine (qty 0.5 4개 팩) → 2000-0025-0002 · 로봇 차량 1대당 4 ea",
    tool="where_used",
    revision=REV,
    detail={
        "assembly": "rocker bogie",
        "multiplier": 2,
        "raw_qty": "0.5",
        "pack_size": 4,
        "each_per_product": "4",
        "sku": "2000-0025-0002",
    },
)


def qty(units: int, value: str) -> CalcResult:
    """서보 소요 낱개 계산 결과 (units 대 기준)."""
    return CalcResult(
        label=f"필요 서보 수량 ({units}대)",
        kind="quantity",
        value=Decimal(value),
        unit="ea",
        tool="bom_explode",
        inputs={"units": units, "part": "2000-0025-0002"},
        revision=REV,
    )


def diff(value: str) -> CalcResult:
    """단가 변경 · 대체 부품의 부품비 차이 (부호 있는 값)."""
    return CalcResult(
        label="추가 모터 부품비 (1대)",
        kind="diff",
        value=Decimal(value),
        unit="USD",
        tool="change_impact",
        formula="변경 후 − 변경 전",
        inputs={"units": 1, "part": "5203-2402-0027"},
        revision=REV,
    )


def run(draft, calcs, units, paths=(SERVO_PATH,)):
    return verify(draft, calcs, REV, units, paths=list(paths), facts={})


def codes(v) -> set[str]:
    return {i.code for i in v.issues}


def test_mv01_correct_quantity_passes():
    c = qty(1, "4")
    d = AnswerDraft(
        headline="서보는 로봇 차량 1대당 4개가 필요합니다.",
        cited=[Cited(label=c.label, value="4", unit="ea")],
    )
    v = run(d, [c], 1)
    assert v.status == "passed" and v.version


def test_mv02_reproduced_wrong_quantity_without_citation_fails():
    """F1 재현: 도구는 4개인데 답변은 2개, 인용 없음 → 예전에는 checks=[] 로 passed 였다."""
    d = AnswerDraft(headline="서보는 로버 1대당 2개입니다.", cited=[])
    v = run(d, [qty(1, "4")], 1)
    assert v.status == "failed"
    assert {"missing_reference", "wrong_value"} <= codes(v)


def test_mv03_calculation_without_any_citation_is_not_passed():
    d = AnswerDraft(headline="서보 수량을 확인했습니다.", cited=[])
    v = run(d, [qty(50, "200")], 50)
    assert v.status == "failed" and "missing_reference" in codes(v)


def test_mv04_wrong_unit_fails():
    c = qty(1, "4")
    d = AnswerDraft(
        headline="서보 4팩이 필요합니다.", cited=[Cited(label=c.label, value="4", unit="pack")]
    )
    v = run(d, [c], 1)
    assert v.status == "failed" and not v.checks[0].unit_ok


def test_mv05_other_units_condition_fails_and_missing_units_input_is_not_a_match():
    c = qty(50, "200")
    d = AnswerDraft(
        headline="100대에 서보 200개가 필요합니다.",
        cited=[Cited(label=c.label, value="200", unit="ea")],
    )
    v = run(d, [c], 100)
    assert v.status == "failed" and not v.checks[0].condition_ok
    # 생산 대수를 입력으로 받는 계산인데 대수가 비어 있으면 '일치'로 보지 않는다
    blank = c.model_copy(update={"inputs": {"units": None}})
    v2 = run(
        AnswerDraft(headline="서보 200개", cited=[Cited(label=c.label, value="200", unit="ea")]),
        [blank],
        100,
    )
    assert not v2.checks[0].condition_ok


def test_mv06_per_product_and_total_are_different_metrics():
    c = qty(50, "200")
    # 50대 총량 200을 1대당 수량으로 쓴 경우
    d = AnswerDraft(
        headline="서보는 1대당 200개가 필요합니다.",
        cited=[Cited(label=c.label, value="200", unit="ea")],
    )
    assert "wrong_value" in codes(run(d, [c], 50))
    # 1대당 4를 50대 총량으로 쓴 경우
    d2 = AnswerDraft(
        headline="로봇 차량 50대에 서보 4개가 필요합니다.",
        cited=[Cited(label=c.label, value="200", unit="ea")],
    )
    assert "wrong_condition" in codes(run(d2, [c], 50))
    # 둘을 맞게 쓴 문장은 통과
    ok = AnswerDraft(
        headline="로봇 차량 50대에 서보 200개가 필요합니다 (1대당 4개).",
        cited=[Cited(label=c.label, value="200", unit="ea")],
    )
    assert run(ok, [c], 50).status == "passed"


def test_mv07_decrease_written_as_magnitude_or_signed_passes():
    c = diff("-13.98")
    for text in ("모터 부품비가 $13.98 감소합니다.", "부품비 차이는 -$13.98 입니다."):
        d = AnswerDraft(headline=text, cited=[Cited(label=c.label, value="13.98", unit="USD")])
        assert run(d, [c], 1, paths=()).status == "passed", text


def test_mv08_opposite_direction_fails():
    c = diff("-13.98")
    d = AnswerDraft(
        headline="모터 부품비가 $13.98 증가합니다.",
        cited=[Cited(label=c.label, value="13.98", unit="USD")],
    )
    v = run(d, [c], 1, paths=())
    assert v.status == "failed" and "wrong_direction" in codes(v)
    assert not v.checks[0].direction_ok
    # 감소인데 방향을 쓰지 않은 경우도 통과시키지 않는다
    bare = AnswerDraft(
        headline="부품비 차이는 $13.98 입니다.",
        cited=[Cited(label=c.label, value="13.98", unit="USD")],
    )
    assert "wrong_direction" in codes(run(bare, [c], 1, paths=()))


def test_mv09_zero_diff_is_not_forced_into_a_direction():
    c = diff("0.00")
    d = AnswerDraft(
        headline="부품비 변경은 없습니다 ($0.00).",
        cited=[Cited(label=c.label, value="0.00", unit="USD")],
    )
    assert run(d, [c], 1, paths=()).status == "passed"


def test_mv10_unknown_extra_cost_is_not_zero():
    unknown = CalcResult(label="서보 단종 추가 비용", kind="extra_cost", value=None, unit="USD")
    c = qty(1, "4")
    d = AnswerDraft(
        headline="서보는 1대당 4개이며 단종 추가 비용은 $0.00 입니다.",
        cited=[Cited(label=c.label, value="4", unit="ea")],
    )
    v = run(d, [c, unknown], 1)
    assert v.status == "failed" and v.unverified_numbers == ["0.00"]


def test_mv11_identifiers_and_dates_are_not_read_as_quantities():
    c = qty(1, "4")
    d = AnswerDraft(
        headline="서보 2000-0025-0002 는 1대당 4개가 필요합니다.",
        notes=[
            "판 6b2c5a9 · 자료 확인일 2026-10-22 기준",
            "문서 mechanical/servo_gear_replacement/README.md 12행",
        ],
        cited=[Cited(label=c.label, value="4", unit="ea")],
    )
    v = run(d, [c], 1)
    assert v.status == "passed", v.issues


def test_mv11b_pack_size_and_raw_pack_quantity_are_known():
    c = qty(1, "4")
    d = AnswerDraft(
        headline="서보는 1대당 4개입니다.",
        findings=["원천 BOM 에는 4개입 팩 0.5팩으로 적혀 있습니다."],
        cited=[Cited(label=c.label, value="4", unit="ea")],
    )
    assert run(d, [c], 1).status == "passed"
    wrong = d.model_copy(update={"findings": ["원천 BOM 에는 6개입 팩 0.5팩으로 적혀 있습니다."]})
    assert run(wrong, [c], 1).status == "failed"


@pytest.mark.parametrize("packing", ["2개씩 묶어 판매", "2개씩 포장", "2개씩 판매", "2개/팩", "팩당 2개", "한 팩에 2개", "2개입"])
def test_pack_description_is_not_the_production_total(packing):
    c = qty(20, "120").model_copy(update={"inputs": {"units": 20, "pack_size": 2}})
    d = AnswerDraft(
        headline=f"20대 생산에 필요한 {packing} 부품을 확인했습니다.",
        cited=[Cited(label=c.label, value="120", unit="ea")],
    )
    assert run(d, [c], 20, paths=()).status == "passed"


@pytest.mark.parametrize("text", [
    "20대 생산에 필요한 부품은 4개씩 묶어 판매합니다.",
    "20대 생산에 필요한 부품은 팩당 4개입니다.",
    "20대에 부품 2개가 필요합니다.",
    "20대에 부품 2개씩 필요합니다.",
    "부품은 1대당 2개가 필요합니다.",
])
def test_packing_recognition_does_not_accept_wrong_pack_or_required_quantity(text):
    c = qty(20, "120").model_copy(update={"inputs": {"units": 20, "pack_size": 2}})
    d = AnswerDraft(headline=text, cited=[Cited(label=c.label, value="120", unit="ea")])
    assert run(d, [c], 20, paths=()).status == "failed"


def test_mv13_withheld_answer_uses_only_verified_values():
    """두 번 모두 실패하면 LLM 문장을 내리고, 계산 결과로 만든 문장만 남긴다."""
    c = qty(50, "200")
    d = withheld_answer([c], [SERVO_PATH], [])
    assert "검증에 실패" in d.headline
    assert any("200" in f for f in d.findings)
    assert "2개" not in d.text()


def test_usd_suffix_amounts_are_checked_too():
    """ "-13.98 USD" 처럼 $ 없이 쓴 금액도 금액 · 방향 검사 대상이다."""
    c = diff("-13.98")
    ok = AnswerDraft(
        headline="원가 차이는 -13.98 USD(감소)입니다.",
        cited=[Cited(label=c.label, value="-13.98", unit="USD")],
    )
    assert run(ok, [c], 1, paths=()).status == "passed"
    wrong = AnswerDraft(
        headline="원가가 13.98 USD 증가합니다.",
        cited=[Cited(label=c.label, value="13.98", unit="USD")],
    )
    assert "wrong_direction" in codes(run(wrong, [c], 1, paths=()))
    unknown = AnswerDraft(
        headline="원가는 1500.00 USD 입니다.",
        cited=[Cited(label=c.label, value="-13.98", unit="USD")],
    )
    assert run(unknown, [c], 1, paths=()).unverified_numbers == ["1500.00"]


@pytest.mark.parametrize("amount", ["$2,000", "2000 USD", "2000달러", "$2000.0"])
def test_unverified_money_without_two_decimal_places_is_also_blocked(amount):
    c = qty(20, "120")
    d = AnswerDraft(
        headline=f"구매 금액은 약 {amount} 수준입니다.",
        cited=[Cited(label=c.label, value="120", unit="ea")],
    )
    v = run(d, [c], 20, paths=())
    assert v.status == "failed" and v.unverified_numbers
