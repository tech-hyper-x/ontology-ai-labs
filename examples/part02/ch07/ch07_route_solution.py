"""Ch7 호출 분기 해설. 실제 runtime 전체를 대체하지 않는 작은 연습."""
from ch07_route import check


def execute(gateway, plan, revision):
    if plan["intent"] == "cost":
        return gateway.call("cost_rollup", units=plan["units"], revision=revision)
    if plan["intent"] == "price_change":
        gateway.call("where_used", part=plan["part"], revision=revision)
        return gateway.call("change_impact", change_type="price_percent", part=plan["part"],
                            value=plan["percent"], units=plan["units"], revision=revision)
    raise ValueError("이 연습은 cost·price_change의 준비된 계획만 받습니다")


if __name__ == "__main__":
    check(execute)
