"""에이전트 워크플로 · 출력 검사 테스트 (Part 2 Ch7). LLM 대신 규칙 기반 데모 모드(fixed_llm)로 돈다.

출력 검사(verify)는 Neo4j 없이, 워크플로 테스트는 적재된 Neo4j 가 있을 때만 실행한다.
"""

from decimal import Decimal

import pytest

from mfg_bom_agent.contracts.answer import AnswerRequest, CalcResult, ResumeInput, RunContext
from mfg_bom_agent.workflows.answer import AnswerDraft, Cited, verify

CALC = CalcResult(
    label="2000-0025-0002 소요 금액 (50대)",
    kind="requirement",
    value=Decimal("6398.00"),
    unit="USD",
    tool="cost_rollup",
    formula="200개 × $31.99",
    inputs={"units": 50},
    revision="6b2c5a9",
)


def test_verify_passes_when_item_value_unit_condition_match():
    draft = AnswerDraft(
        headline="소요 금액 $6,398.00 (cost_rollup · 200개 × $31.99)",
        cited=[Cited(label=CALC.label, value="6398.00", unit="USD")],
    )
    assert verify(draft, [CALC], "6b2c5a9", 50).status == "passed"


def test_verify_fails_on_wrong_value_or_unit_or_condition():
    wrong = AnswerDraft(
        headline="소요 금액 $6,400.00",
        cited=[Cited(label=CALC.label, value="6400.00", unit="USD")],
    )
    v = verify(wrong, [CALC], "6b2c5a9", 50)
    assert v.status == "failed" and v.unverified_numbers == ["6,400.00"]
    other_units = AnswerDraft(
        headline="소요 금액 $6,398.00",
        cited=[Cited(label=CALC.label, value="6398.00", unit="USD")],
    )
    assert (
        verify(other_units, [CALC], "6b2c5a9", 100).status == "failed"
    )  # 100대 질문에 50대 계산 인용


def test_verify_not_run_without_calculations():
    assert verify(AnswerDraft(headline="답", cited=[]), [], None, None).status == "not_run"


@pytest.fixture
def demo(monkeypatch):
    from mfg_bom_agent.graph.client import make_driver

    try:
        make_driver().verify_connectivity()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Neo4j 연결 불가: {exc}")
    monkeypatch.setenv("MCP_TRANSPORT", "inprocess")
    return RunContext(demo_mode="fixed_llm")


def test_workflow_servo_scenario(demo):
    from mfg_bom_agent.workflows.bom_agent import run

    events = []
    resp = run(
        AnswerRequest(
            run_id="test-servo",
            question="서보 2000-0025-0002 단종 가정 시 50대 소요량·금액·대체 후보는?",
            context=demo,
        ),
        events.append,
    )
    assert resp.status == "completed" and resp.verification.status == "passed"
    by = {c.label: c for c in resp.calculations}
    assert by[next(k for k in by if k.endswith("소요 금액 (50대)"))].value == Decimal("6398.00")
    tools = [e.tool for e in events if e.type == "tool_finished"]
    assert tools == [
        "find_part",
        "where_used",
        "bom_explode",
        "supply_risk",
        "cost_rollup",
        "search_docs",
    ]
    # 단종 뒤 유지보수 근거(기어 세트 교체 문서)와 단일 공급이 실습 가정이라는 설명이 함께 나온다
    assert any("servo_gear_replacement" in d.doc_path for d in resp.documents)
    assert any("실습 가정" in a for a in resp.sources.assumptions)


def test_workflow_asks_and_resumes(demo):
    from mfg_bom_agent.workflows.bom_agent import run

    q = "서보 2000-0025-0002 단종 시 대체 후보는?"
    first = run(AnswerRequest(run_id="test-resume", question=q, context=demo))
    assert first.status == "needs_input" and first.pending_question.field == "units"
    second = run(
        AnswerRequest(
            run_id="test-resume",
            question=q,
            context=demo,
            resume=ResumeInput(field="units", value="50"),
        )
    )
    assert second.status == "completed"


def test_answer_draft_accepts_list_as_json_text():
    """모델이 목록 칸을 JSON 문자열로 돌려줘도 실행이 실패하지 않는다 (평가 G29 에서 발생)."""
    draft = AnswerDraft.model_validate(
        {"headline": "답", "findings": '["사실 하나", "사실 둘"]', "notes": "가정 하나\n가정 둘"}
    )
    assert draft.findings == ["사실 하나", "사실 둘"]
    assert draft.notes == ["가정 하나", "가정 둘"]


def test_workflow_wheel_alternate_cost(demo):
    """휠 단종: 원천 문서에 가격이 적힌 대체 휠 2종의 부품비 차이를 도구가 계산한다."""
    from mfg_bom_agent.workflows.bom_agent import run

    resp = run(
        AnswerRequest(
            run_id="test-wheel",
            question="휠(3616-0014-0144)이 단종되면 50대 생산에 필요한 수량 · 비용 · 대체 부품은?",
            context=demo,
        )
    )
    assert resp.status == "completed"
    by = {c.label: c.value for c in resp.calculations}
    diff = {k: v for k, v in by.items() if "비용 차이" in k}
    # 192mm 휠: 300개 × ($39.99 − $24.99) = +$4,500 (문서의 "1대당 $90 추가" × 50대)
    assert diff[next(k for k in diff if "3616-0014-0192" in k)] == Decimal("4500.00")
    # 5374X: 2개 1쌍 $34.95 → 150쌍 $5,242.50 − $7,497.00
    assert diff[next(k for k in diff if "5374X" in k)] == Decimal("-2254.50")


def test_verify_accepts_magnitude_of_negative_diff():
    """감소액은 "…$2,254.50 줄어듭니다"처럼 크기만 쓴다. 차이 값의 크기는 근거 있는 금액으로 본다."""
    diff = CalcResult(
        label="대체 휠 5374X 비용 차이 (50대)",
        kind="diff",
        value=Decimal("-2254.50"),
        unit="USD",
        tool="supply_risk",
        formula="150팩(2개/팩) × $34.95 − 300개 × $24.99 = 부품비 차이",
        inputs={"units": 50},
        revision="6b2c5a9",
    )
    draft = AnswerDraft(
        headline="5374X로 바꾸면 부품비가 $2,254.50 줄어듭니다.",
        cited=[Cited(label=diff.label, value="2254.50", unit="USD")],
    )
    assert verify(draft, [diff], "6b2c5a9", 50).status == "passed"


def test_answer_draft_drops_revision_id_from_basis():
    """계산 기준에 판 ID 가 섞여 나와도 화면에는 업무 기준만 남긴다."""
    cases = {
        "판 구성 6b2c5a9 기준, 기준일 2026-10-22": "기준일 2026-10-22",
        "로봇 차량 50대 (1대당 휠 6개, 리비전 6b2c5a9)": "로봇 차량 50대 (1대당 휠 6개)",
        "로봇 차량 100대": "로봇 차량 100대",
    }
    for raw, want in cases.items():
        assert AnswerDraft(headline="답", basis=raw).basis == want


def test_query_recorder_keeps_used_params_and_counts_repeats():
    """처리 과정에 보여 줄 Cypher 기록: 쓰인 파라미터만 남기고, 같은 쿼리 반복은 횟수로 묶는다."""
    from mfg_bom_agent.graph.client import QueryRecorder

    class FakeDriver:
        def execute_query(self, *args, **kwargs):
            return [], None, None

    rec = QueryRecorder(FakeDriver())
    for _ in range(2):
        rec.execute_query("MATCH (p:Part {sku: $sku}) RETURN p", {"sku": "A", "domain": None})
    rec.execute_query("MATCH (n) RETURN count(n)", database_="neo4j")
    assert rec.log == [
        {"query": "MATCH (p:Part {sku: $sku}) RETURN p", "params": {"sku": "A"}, "calls": 2},
        {"query": "MATCH (n) RETURN count(n)", "params": {}, "calls": 1},
    ]


def test_workflow_part_info_completes(demo):
    """부품 정보 질문이 끝까지 실행된다 (단종 경로의 변경이 다른 경로에 섞이지 않았는지 확인)."""
    from mfg_bom_agent.workflows.bom_agent import run

    resp = run(
        AnswerRequest(
            run_id="test-info", question="서보 2000-0025-0002 부품 정보 알려줘", context=demo
        )
    )
    assert resp.status == "completed" and resp.intent == "part_info"
