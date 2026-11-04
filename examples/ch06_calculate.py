"""Ch6 CSV 독립 검산. Neo4j·LLM 없이 제공 스냅샷의 기준값을 출력한다."""
from decimal import Decimal
import json
from mfg_bom_agent.tools import calc
from mfg_bom_agent.evaluation import reference as ref


def main():
    wheel = ref.ecn_by_date("2024-06")
    result = {
        "kind": "CSV reference / MCP 실호출 아님",
        "revision": ref.latest(),
        "spacer_each_per_product": calc.each_per_product(Decimal("0.5"), 4, 2),
        "servo_50_required_each": ref.required_each("2000-0025-0002", 50),
        "servo_50_requirement_cost": calc.money(calc.requirement_cost(Decimal(2), 2, 50, Decimal("31.99"))),
        "motor_15pct_1unit": ref.price_change_diff("5203-2402-0027", "15", 1),
        "motor_15pct_100units": ref.price_change_diff("5203-2402-0027", "15", 100),
        "mechanical_1unit": ref.cost(),
        "wheel_revision_from": wheel["revision_from"],
        "wheel_revision_to": wheel["revision_to"],
        "wheel_cost_before": ref.cost(1, wheel["revision_from"]),
        "wheel_cost_after": ref.cost(1, wheel["revision_to"]),
        "wheel_cost_diff": ref.ecn_cost_diff(wheel["ecn_id"]),
    }
    assert result["servo_50_required_each"] == 200
    assert result["servo_50_requirement_cost"] == Decimal("6398.00")
    assert result["motor_15pct_1unit"] == Decimal("38.69")
    assert result["motor_15pct_100units"] == Decimal("3869.10")
    assert result["wheel_cost_diff"] == Decimal("45.09")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
