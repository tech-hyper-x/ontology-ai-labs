"""Langfuse 트레이싱 데모: 같은 질문을 "LLM 단독"과 "LangGraph + 계산 도구"로 각각 실행해 비교한다.

    uv run python scripts/langfuse_demo.py

실습 데이터와 실제 업무 도구를 만들기 전에, Langfuse 화면(트레이스 · 세션 · 점수 · 비용)을 미리 채워 보고
"LLM 은 해석만, 계산은 도구가"라는 강의 메시지를 트레이스로 확인하기 위한 스크립트다 (정의서 7.2, 11절).

- 질문은 하나: 모터 단가가 오르면 로버 1대 원가가 얼마나 늘어나는가
- 조건 A (llm-only): Claude 에게 그냥 묻는다. 데이터가 없으니 정확한 금액을 낼 수 없다
- 조건 B (graph+tools): LangGraph 에이전트가 계산 도구를 호출하고, 금액은 도구가 계산한다
- 두 트레이스를 같은 세션으로 묶고, 정답 금액이 답에 들어 있는지 점수(score)로 남긴다

도구와 BOM 값은 데모용 고정값이다. 실제 도구는 src/mfg_bom_agent/tools/ 에 구현한다.
Claude Haiku 5.5 를 3~4번 호출한다 (비용 1센트 미만).

    uv run python scripts/langfuse_demo.py --mock

--mock 은 API 크레딧 없이 Langfuse 화면을 확인하는 모드다. LLM 답변만 미리 정해 둔 문장으로 바꾸고
(모델 이름 mock-llm, 태그 mock), LangGraph 흐름 · 도구 호출 · 금액 계산 · 점수는 실제로 실행한다.
실제 모델을 부르지 않으므로 토큰 비용은 0 으로 기록된다.
"""

from __future__ import annotations

import sys
import uuid
from decimal import ROUND_HALF_UP, Decimal

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langfuse import Langfuse, propagate_attributes
from langfuse.langchain import CallbackHandler
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from mfg_bom_agent.config import get_settings

QUESTION = "Yellow Jacket 모터(부품번호 5203) 단가가 15% 오르면 로버 1대 원가는 얼마나 늘어나?"

# 데모용 고정 BOM: 로버 1대에 Drive Wheel 조립품 6개, 조립품마다 모터 1개.
# 단가는 NASA OSR parts_list.csv 의 실제 값이다 (5203-2402-0027, $42.99, 스냅샷 a78f9eb 2026-10-22).
DEMO_BOM = {
    "5203": {"name": "Yellow Jacket Motor", "unit_price": Decimal("42.99"), "qty_per_rover": 6}
}


@tool
def where_used(part_id: str) -> dict:
    """부품이 로버 1대에 몇 개 쓰이는지 돌려준다 (데모용 고정 BOM)."""
    part = DEMO_BOM.get(part_id)
    if part is None:
        return {"error": f"part_id {part_id} 없음"}
    return {
        "part_id": part_id,
        "name": part["name"],
        "qty_per_rover": part["qty_per_rover"],
        "path": "Open Source Rover → Drive Wheel ×6 → Yellow Jacket Motor ×1",
    }


@tool
def change_impact(part_id: str, price_change_percent: float) -> dict:
    """단가 변경률(%)을 받아 로버 1대 원가 증가액(USD)을 계산한다. 금액은 Decimal 로 계산해 센트 단위로 반올림한다."""
    part = DEMO_BOM.get(part_id)
    if part is None:
        return {"error": f"part_id {part_id} 없음"}
    delta_unit = part["unit_price"] * Decimal(str(price_change_percent)) / Decimal(100)
    delta_rover = (delta_unit * part["qty_per_rover"]).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return {
        "part_id": part_id,
        "old_unit_price": str(part["unit_price"]),
        "qty_per_rover": part["qty_per_rover"],
        "delta_per_rover_usd": str(delta_rover),
        "assumption": "가격 기준일 2026-10-22, NASA OSR parts_list.csv 공개 단가",
    }


def expected_answer() -> str:
    """점수 매기기용 정답. 도구와 같은 함수를 쓰므로 계산 규칙이 한 곳에만 있다."""
    return change_impact.invoke({"part_id": "5203", "price_change_percent": 15})[
        "delta_per_rover_usd"
    ]


class MockLLM(GenericFakeChatModel):
    """--mock 모드용 가짜 모델. 정해 둔 AIMessage 를 순서대로 돌려준다. 도구 연결(bind_tools)은 그대로 통과시킨다."""

    # Langfuse 가 이 값을 generation 의 모델 이름으로 기록한다. 실제 모델과 헷갈리지 않게 mock 임을 드러낸다.
    model: str = "mock-llm"

    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self) -> str:
        return "mock-llm"


def mock_llm(condition: str, expected: str) -> MockLLM:
    """조건별 시나리오. llm-only 는 데이터 없이 추측하고, graph+tools 는 도구 두 개를 부른 뒤 도구 값으로 답한다."""
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    if condition == "llm-only":
        script = [
            AIMessage(
                "모터의 현재 단가와 로버 1대에 들어가는 수량 정보가 없어 정확한 금액은 계산할 수 없습니다. "
                "일반적인 소형 DC 모터 단가를 30달러, 수량을 4개로 가정하면 약 18달러가 늘어납니다.",
                usage_metadata=usage,
            )
        ]
    else:
        script = [
            AIMessage(
                "",
                tool_calls=[
                    {"name": "where_used", "args": {"part_id": "5203"}, "id": "call_where_used"},
                    {
                        "name": "change_impact",
                        "args": {"part_id": "5203", "price_change_percent": 15},
                        "id": "call_change_impact",
                    },
                ],
                usage_metadata=usage,
            ),
            AIMessage(
                f"로버 1대 원가는 ${expected} 늘어납니다. Yellow Jacket 모터(5203)는 Drive Wheel 조립품 6개에 1개씩, "
                f"로버 1대에 6개가 쓰이고 기존 단가는 $42.99 입니다. 계산은 change_impact 도구 결과이며 "
                "가격 기준일 2026-10-22, NASA OSR parts_list.csv 공개 단가를 기준으로 했습니다.",
                usage_metadata=usage,
            ),
        ]
    return MockLLM(messages=iter(script))


def build_agent(llm):
    """질문 → (도구 호출 → 결과) 반복 → 답변 으로 이어지는 가장 작은 LangGraph 에이전트."""
    tools = [where_used, change_impact]
    model = llm.bind_tools(tools)
    system = SystemMessage(
        "너는 제조 BOM 분석 도우미다. 수량과 금액은 절대 직접 계산하지 말고 반드시 도구를 호출해서 얻는다. "
        "답변에는 도구가 준 금액과 계산 가정을 그대로 밝힌다."
    )

    def call_model(state: MessagesState):
        return {"messages": [model.invoke([system, *state["messages"]])]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


def answer_text(message) -> str:
    """AIMessage 의 content 블록 중 text 만 이어 붙인다 (thinking 블록 제외)."""
    if isinstance(message.content, str):
        return message.content
    return "".join(
        b.get("text", "")
        for b in message.content
        if isinstance(b, dict) and b.get("type") == "text"
    )


def main() -> int:
    s = get_settings()
    mock = "--mock" in sys.argv[1:]
    if not s.langfuse_enabled or not (mock or s.anthropic_configured):
        print(
            "LANGFUSE_* 키가 .env 에 있어야 한다. 실제 모델로 실행하려면 ANTHROPIC_API_KEY 도 필요하다."
        )
        return 1

    langfuse = Langfuse(
        public_key=s.langfuse_public_key.get_secret_value(),
        secret_key=s.langfuse_secret_key.get_secret_value(),
        host=s.langfuse_host,
    )
    if not langfuse.auth_check():
        print(f"Langfuse 인증 실패: {s.langfuse_host} 와 .env 의 키를 확인한다.")
        return 1

    handler = CallbackHandler(public_key=s.langfuse_public_key.get_secret_value())
    session_id = f"demo-{'mock-' if mock else ''}{uuid.uuid4().hex[:8]}"
    expected = expected_answer()
    runs = []

    # 같은 질문을 두 조건으로 실행한다. 조건 이름은 태그와 메타데이터에 남겨 Langfuse 에서 필터링한다.
    for condition in ["llm-only", "graph+tools"]:
        llm = (
            mock_llm(condition, expected)
            if mock
            else ChatAnthropic(
                model=s.llm_model,
                api_key=s.anthropic_api_key.get_secret_value(),
                max_tokens=2048,
                effort=s.llm_effort,
            )
        )
        request_id = uuid.uuid4().hex[:12]
        # propagate_attributes 가 먼저 열려야 그 안에서 만든 모든 관측(observation)에 세션·태그가 붙는다.
        trace_attrs = propagate_attributes(
            trace_name=f"bom-question · {condition}",
            session_id=session_id,
            user_id="demo-student",
            tags=["demo", condition] + (["mock"] if mock else []),
            metadata={
                "request_id": request_id,
                "condition": condition,
                "mock": mock,
                "dataset_version": s.dataset_version,
                "lab": "mfg-bom-agent",
            },
        )
        with (
            trace_attrs,
            langfuse.start_as_current_observation(
                name=condition, as_type="agent", input=QUESTION
            ) as root,
        ):
            if condition == "llm-only":
                reply = llm.invoke([HumanMessage(QUESTION)], config={"callbacks": [handler]})
            else:
                result = build_agent(llm).invoke(
                    {"messages": [HumanMessage(QUESTION)]}, config={"callbacks": [handler]}
                )
                reply = result["messages"][-1]
            text = answer_text(reply)
            root.update(output=text)
            trace_id = langfuse.get_current_trace_id()

        # 점수: 정답 금액이 답에 들어 있으면 1. Langfuse 의 Scores 화면과 트레이스 상세에서 보인다.
        correct = expected in text
        langfuse.create_score(
            trace_id=trace_id,
            name="correct_amount",
            value=1.0 if correct else 0.0,
            data_type="NUMERIC",
            comment=f"정답 ${expected} 포함 여부",
        )
        runs.append((condition, correct, langfuse.get_trace_url(trace_id=trace_id)))

    langfuse.flush()
    print(f"session: {session_id}   expected: ${expected}")
    for condition, correct, url in runs:
        print(f"{condition:12} correct_amount={int(correct)}  {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
