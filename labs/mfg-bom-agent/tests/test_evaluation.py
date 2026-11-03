"""Golden Set 채점 회귀 테스트 (Part 2 Ch8-1). Neo4j · LLM 없이 실행한다.

검토 보고서 F2: 정답 -13.98 USD 에 "$13.98 증가"가 정답 처리되던 문제와 단위 · 집합 채점.
테스트 ID(M-E01 …)는 실행 계획서 6절의 번호다.
"""

from decimal import Decimal

from mfg_bom_agent.contracts.answer import AnswerResponse, CalcResult, GraphPath, RunContext
from mfg_bom_agent.evaluation.scoring import score

ECN_DIFF = {  # G36: 2023-10-04 ECN 전후 로버 1대 원가 차이 = -13.98 USD
    "id": "G36",
    "question": "2023-10-04 ECN 전후 로버 1대 원가 차이는?",
    "expected": {
        "type": "number",
        "value": "13.98",
        "unit": "USD",
        "tol": "0.01",
        "metric": "diff",
        "direction": "decrease",
        "units": 1,
    },
}


def resp(
    conclusion: str, mode: str = "kg_tools", calcs=(), paths=(), status="completed"
) -> AnswerResponse:
    return AnswerResponse(
        run_id="t",
        status=status,
        mode=mode,
        conclusion=conclusion,
        calculations=list(calcs),
        graph_paths=list(paths),
        context=RunContext(),
    )


def diff_calc(value: str) -> CalcResult:
    return CalcResult(label="ECN 원가 차이 (1대)", kind="diff", value=Decimal(value), unit="USD")


def test_me01_opposite_direction_is_wrong():
    r = score(ECN_DIFF, resp("원가가 $13.98 증가합니다.", calcs=[diff_calc("-13.98")]))
    assert r["passed"] is False and r["reason"] == "wrong_direction"
    for ok in ("원가가 $13.98 감소합니다.", "원가 차이는 -$13.98 입니다."):
        assert score(ECN_DIFF, resp(ok))["passed"] is True, ok


def test_me01b_decrease_without_direction_is_not_accepted():
    assert score(ECN_DIFF, resp("원가 차이는 $13.98 입니다."))["reason"] == "wrong_direction"


def test_me02_wrong_unit():
    item = {**ECN_DIFF, "expected": {**ECN_DIFF["expected"], "metric": None, "direction": None}}
    r = score(item, resp("13.98개입니다."))
    assert r["passed"] is False and r["reason"] == "wrong_unit"


def test_me03_panel_correct_but_conclusion_wrong():
    """계산 패널에는 정답이 있지만 결론이 틀렸으면 tool_correct=True · answer_correct=False."""
    r = score(ECN_DIFF, resp("원가가 $13.98 늘어납니다.", calcs=[diff_calc("-13.98")]))
    assert r["tool_correct"] is True and r["answer_correct"] is False
    # 도구가 없는 방식은 tool_correct 를 비워 둔다
    assert score(ECN_DIFF, resp("원가가 $13.98 감소합니다.", mode="rag"))["tool_correct"] is None


def test_me03b_quantity_needs_matching_unit_and_condition():
    item = {
        "id": "G01",
        "question": "로버 50대를 만들 때 서보 2000-0025-0002 은(는) 낱개로 몇 개 필요한가?",
        "expected": {"type": "number", "value": "200", "unit": "ea", "tol": "0", "units": 50},
    }
    assert score(item, resp("로봇 차량 50대에 서보 200개가 필요합니다."))["passed"] is True
    assert (
        score(item, resp("로봇 차량 100대에 서보 400개가 필요합니다."))["reason"]
        == "wrong_condition"
    )
    # 품번 속 숫자(2000)는 수량으로 읽지 않는다
    assert score(item, resp("서보 2000-0025-0002 는 4개입 팩입니다."))["passed"] is False


def test_me04_set_missing_extra_exact():
    item = {
        "id": "G22",
        "question": "부품 1120-0002-0072 가 쓰이는 어셈블리를 모두 알려줘",
        "expected": {"type": "set", "values": ["body", "drive wheel"]},
    }
    exact = score(item, resp("body 와 drive wheel 에 쓰입니다."))
    missing = score(item, resp("body 에 쓰입니다."))
    extra = score(item, resp("body · drive wheel · corner 에 쓰입니다."))
    assert exact["passed"] and exact["precision"] == 1.0
    assert missing["reason"] == "missing_item" and missing["recall"] == 0.5
    assert extra["reason"] == "extra_item" and extra["recall"] == 1.0 and extra["precision"] < 1


def test_me04b_part_in_question_is_not_an_extra_item():
    item = {
        "id": "G28",
        "question": "휠 3616-0014-0144 대신 쓸 수 있는 대체 부품은?",
        "expected": {"type": "set", "values": ["3616-0014-0192", "5374X"]},
    }
    r = score(item, resp("휠 3616-0014-0144 대신 3616-0014-0192 와 5374X 를 쓸 수 있습니다."))
    assert r["passed"] is True


def test_me05_answerability_is_separated():
    item = {**ECN_DIFF}
    assert score(item, resp("", status="needs_input"))["answerability"] == "needs_input"
    assert score(item, resp("", status="failed"))["answerability"] == "failed"
    r = score(item, resp("주어진 정보로는 알 수 없습니다.", mode="llm_only"))
    assert r["answerability"] == "abstained" and r["reason"] == "abstained" and not r["passed"]


def test_doc_answer_vs_evidence():
    from mfg_bom_agent.contracts.answer import DocEvidence

    item = {
        "id": "G40",
        "question": "q",
        "expected": {"type": "doc", "path": "mechanical/servo_gear_replacement/README.md"},
    }
    doc = DocEvidence(
        doc_path="mechanical/servo_gear_replacement/README.md", doc_id="d", title="t", excerpt=""
    )
    r0 = resp("관련 문서를 찾지 못했습니다.")
    r0.documents = [doc]
    r = score(item, r0)
    assert r["evidence_correct"] is True and r["answer_correct"] is False
    assert GraphPath  # 경로 패널은 집합 문항의 tool_correct 에만 쓴다
