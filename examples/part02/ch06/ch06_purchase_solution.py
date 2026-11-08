"""Ch6 구매 계산 해설. 작성 과제와 동일한 수용 기준으로 검사한다."""
from decimal import Decimal
from mfg_bom_agent.tools import calc
from ch06_purchase import check


def calculate(required_each: Decimal, pack_size: int, pack_price: Decimal, moq_packs: int) -> dict:
    if required_each <= 0 or pack_size < 1 or pack_price < 0 or moq_packs < 1:
        raise ValueError("양수 소요량·팩 크기·MOQ와 0 이상 단가를 입력하세요")
    _, buy = calc.packs_to_buy(required_each, pack_size, moq_packs)
    return dict(
        requirement_cost=calc.money(calc.cost_of_each(required_each, pack_size, pack_price)),
        packs_to_buy=buy,
        purchase_amount=calc.money(Decimal(buy) * pack_price),
        leftover_each=Decimal(buy * pack_size) - required_each,
    )


if __name__ == "__main__":
    check(calculate)
