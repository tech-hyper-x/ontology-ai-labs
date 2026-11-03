"""결정론적 수량 · 원가 계산 규칙 (Part 2 Ch6-1 결정론적 원가 계산).

LLM 은 이 계산을 하지 않는다. 같은 입력이면 언제나 같은 값이 나오는 순수 함수로 두고,
pytest 로 고정 정답(로버 1대 원가 $1,330.38 등)을 검증한다.

계산 규칙 (설계 덱 28장 매핑 계약)
- 낱개 수량  = 원천 수량 × 팩 크기 × 배수 × 생산 대수
- 소요 원가  = 원천 수량(팩) × 배수 × 생산 대수 × 팩당 단가
             = 낱개 수량 ÷ 팩 크기 × 팩당 단가   (두 식은 같다)
- 구매 팩 수 = max(올림(소요 낱개 ÷ 팩 크기), MOQ 팩 수)
- 구매 금액  = 구매 팩 수 × 팩당 단가   (소요 원가와 다르다: 팩 올림 · MOQ 때문)
- 반올림     = 모든 항목을 Decimal 로 더한 뒤 마지막에 센트 단위 HALF_UP 한 번
"""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def qty(value: Decimal) -> Decimal:
    """수량 표시를 정리한다. 40.0 → 40, 2.50 → 2.5 (값은 그대로, 뒤쪽 0만 지운다)."""
    return value.quantize(Decimal(1)) if value == value.to_integral_value() else value.normalize()


def money(value: Decimal) -> Decimal:
    """금액을 센트 단위로 반올림한다 (0.5 센트는 올림). 합계를 낸 뒤 마지막에 한 번만 쓴다."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


# ─── [Hands-on P2-Ch6-1 결정론적 원가 계산] 시작 ───
def each_per_product(raw_qty: Decimal, pack_size: int, multiplier: int) -> Decimal:
    """제품 1대에 들어가는 낱개 수. 예: 0.5팩 × 4개/팩 × 배수 2 = 4개"""
    return raw_qty * pack_size * multiplier


def required_each(raw_qty: Decimal, pack_size: int, multiplier: int, units: int) -> Decimal:
    """생산 대수만큼의 소요 낱개 수."""
    return each_per_product(raw_qty, pack_size, multiplier) * units


def requirement_cost(raw_qty: Decimal, multiplier: int, units: int, pack_price: Decimal) -> Decimal:
    """소요 원가(반올림 전). 원천 수량이 팩 단위이므로 팩당 단가를 그대로 곱한다."""
    return raw_qty * multiplier * units * pack_price


def cost_of_each(qty_each: Decimal, pack_size: int, pack_price: Decimal) -> Decimal:
    """낱개 수량의 원가(반올림 전). 선택 부품비 · 교체 부품비에 쓴다. 팩 올림은 하지 않는다."""
    return qty_each / pack_size * pack_price


def packs_to_buy(required_each_qty: Decimal, pack_size: int, moq_packs: int) -> tuple[int, int]:
    """(필요 팩 수, 실제 구매 팩 수). 필요 팩 수는 올림, 구매 팩 수는 MOQ 를 반영한다."""
    needed = int((required_each_qty / pack_size).to_integral_value(rounding=ROUND_CEILING))
    return needed, max(needed, moq_packs)


def apply_percent(price: Decimal, percent: Decimal) -> Decimal:
    """단가에 변경률(%)을 적용한다. 반올림은 하지 않는다 (합계 후 한 번만)."""
    return price * (Decimal(100) + percent) / Decimal(100)


# ─── [Hands-on P2-Ch6-1] 끝 ───
