"""총소요량 질문의 조건 보존·다중 투입 내역·기존 경로 회귀. DB·LLM 불필요."""

from decimal import Decimal

import pytest

from mfg_bom_agent.contracts.answer import RunContext
from mfg_bom_agent.workflows.bom_agent import resolve_node
from mfg_bom_agent.workflows.plan import QuestionPlan, rule_plan
from mfg_bom_agent.workflows.skills import run_skill


@pytest.mark.parametrize(
    "question,intent,units",
    [
        (
            "로버 50대를 만들 때 서보 2000-0025-0002 은(는) 낱개로 몇 개 필요한가?",
            "required_quantity",
            50,
        ),
        ("모터 5203-2402-0027 20대 총소요량은?", "required_quantity", 20),
        ("스페이서 30대 생산에 필요한 수량은?", "required_quantity", 30),
        ("서보 소요량은?", "required_quantity", None),
        ("로버 20대에 서보를 몇 팩 사야 하나요?", "purchase_quantity", 20),
        ("서보 단종 시 50대 소요량은?", "discontinue", 50),
        ("모터 단가 15% 인상 시 100대 수량과 비용은?", "price_change", 100),
        ("모터 5203-2402-0027은 어느 조립품에 쓰이나요?", "part_info", None),
        ("서보 낱개 단가 알려줘", "part_info", None),
        ("서보는 몇 개입 팩인가요?", "part_info", None),
    ],
)
def test_quantity_question_preserves_scope_and_other_intents(question, intent, units):
    plan = rule_plan(question)
    assert (plan.intent, plan.units) == (intent, units)


class Gateway:
    def __init__(self, items):
        self.items, self.calls = items, []

    def call(self, tool, **args):
        self.calls.append((tool, args))
        if tool == "where_used":
            return {"lines": [], "sku": args["part"], "revision": "test-rev"}
        assert tool == "bom_explode", "총소요량에 구매·위험·문서 도구를 호출하지 않는다"
        return {"items": self.items, "revision": "test-rev", "warnings": []}


def test_all_usage_lines_are_combined_and_conditions_reach_tool():
    gateway = Gateway(
        [
            {"required_each": "120", "formula": "4 × 30"},
            {"required_each": "180", "formula": "6 × 30"},
        ]
    )
    plan = QuestionPlan(intent="required_quantity", units=30, part_terms=["서보"])
    out = run_skill(gateway, plan, RunContext(revision="test-rev"), [{"sku": "servo"}])
    assert gateway.calls == [
        ("where_used", {"part": "servo", "revision": "test-rev"}),
        ("bom_explode", {"units": 30, "part": "servo", "revision": "test-rev", "scope": "all"}),
    ]
    calc = out.calculations[0]
    assert (calc.value, calc.unit, calc.revision) == (Decimal(300), "ea", "test-rev")
    assert calc.inputs == {"units": 30, "part": "servo"}


def test_missing_bom_is_not_presented_as_zero_required_quantity():
    out = run_skill(
        Gateway([]),
        QuestionPlan(intent="required_quantity", units=30),
        RunContext(revision="test-rev"),
        [{"sku": "old-servo"}],
    )
    assert not out.calculations
    assert any("산정하지 않음" in s for s in out.assumptions)


@pytest.mark.parametrize(
    "parts,units,field",
    [
        ([{"term": "서보", "sku": "servo"}], None, "units"),
        ([], 50, "part"),
    ],
)
def test_required_quantity_asks_for_missing_inputs(parts, units, field):
    plan = QuestionPlan(
        intent="required_quantity", units=units, part_terms=["서보"] if parts else []
    )
    state = {
        "request": {"context": {"revision": "test-rev"}},
        "plan": plan.model_dump(),
        "parts": parts,
    }
    result = resolve_node(
        state, {"configurable": {"gateway": Gateway([]), "on_event": lambda e: None}}
    )
    assert result["pending"]["field"] == field
