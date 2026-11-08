"""Ch7 작성 과제: 검증된 계획의 호출 분기. FakeGateway이며 MCP·DB 실제 호출 아님."""


def execute(gateway, plan, revision):
    # cost는 cost_rollup만, price_change는 where_used → change_impact.
    # 변경률을 value에 전달하고 같은 revision과 units를 유지하세요.
    raise NotImplementedError("질문 유형별 호출 분기를 작성하세요")


class FakeGateway:
    def __init__(self):
        self.calls = []

    def call(self, tool, **args):
        self.calls.append((tool, args))
        return {"fixture": True, "tool": tool}


def check(fn):
    revision = "6b2c5a9"
    motor = dict(intent="price_change", part="5203-2402-0027", units=100, percent="15")
    cost = dict(intent="cost", units=1)
    g = FakeGateway()
    fn(g, motor, revision)
    assert g.calls == [
        ("where_used", dict(part=motor["part"], revision=revision)),
        ("change_impact", dict(change_type="price_percent", part=motor["part"], value="15", units=100, revision=revision)),
    ], g.calls
    print("통과: 단가 변경의 도구 순서·변경률·대수·판", g.calls)
    g = FakeGateway()
    fn(g, cost, revision)
    assert g.calls == [("cost_rollup", dict(units=1, revision=revision))], g.calls
    print("통과: 전체 원가에서 find_part·search_docs 생략", g.calls)
    print("연습용 호출 기록 검사 통과. 실제 MCP 성공을 뜻하지 않습니다.")


if __name__ == "__main__":
    check(execute)
