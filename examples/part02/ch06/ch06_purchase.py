"""Ch6 작성용: 소요 원가와 실제 구매 금액. DB·LLM·파일 변경 없음."""
from decimal import Decimal
import argparse
from mfg_bom_agent.tools import calc


def calculate(required_each: Decimal, pack_size: int, pack_price: Decimal, moq_packs: int) -> dict:
    if required_each <= 0 or pack_size < 1 or pack_price < 0 or moq_packs < 1:
        raise ValueError("양수 소요량·팩 크기·MOQ와 0 이상 단가를 입력하세요")
    # Hands-on: 아래 네 계산을 작성하세요. 기대값이나 입력을 바꾸지 않습니다.
    raise NotImplementedError("소요 원가, 구매 팩 수, 구매 금액, 잔량을 작성하세요")


def check(fn):
    cases = [
        ("나누어짐", "8", 4, "10", 1, "20.00", 2, "20.00", "0"),
        ("팩 올림", "7", 4, "10", 1, "17.50", 2, "20.00", "1"),
        ("MOQ 적용", "4", 4, "10", 5, "10.00", 5, "50.00", "16"),
    ]
    for label, req, size, price, moq, cost, packs, amount, left in cases:
        out = fn(Decimal(req), size, Decimal(price), moq)
        expected = dict(requirement_cost=Decimal(cost), packs_to_buy=packs,
                        purchase_amount=Decimal(amount), leftover_each=Decimal(left))
        assert out == expected, f"{label}: {out} != {expected}"
        print(f"통과: {label} {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    if args.check:
        check(calculate)
    else:
        print(calculate(Decimal("7"), 4, Decimal("10"), 1))
