"""실행 이벤트 — 워크플로가 실행 중에 화면으로 보내는 알림 (docs/UI_DESIGN.md 3.3).

타임라인에는 실제로 실행된 도구만 표시한다. ToolStarted 가 와야 줄이 생기고,
ToolFinished · ToolFailed 가 그 줄을 완료 · 오류로 바꾼다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from mfg_bom_agent.contracts.answer import AnswerResponse, ErrorInfo, PendingQuestion


class _Event(BaseModel):
    run_id: str
    ts: datetime = Field(default_factory=datetime.now)


class ToolStarted(_Event):
    type: Literal["tool_started"] = "tool_started"
    call_id: str
    tool: str
    inputs: dict[str, Any]


class ToolFinished(_Event):
    type: Literal["tool_finished"] = "tool_finished"
    call_id: str
    tool: str
    outputs: dict[str, Any]
    elapsed_ms: int
    summary: str = ""


class ToolFailed(_Event):
    type: Literal["tool_failed"] = "tool_failed"
    call_id: str
    tool: str
    error: str
    elapsed_ms: int
    # validation: 도구가 입력 오류(error/hint)로 답함 · transport: 연결 · 시간 초과 · 서버 예외
    kind: Literal["validation", "transport"] = "transport"


class StepNote(_Event):
    """도구가 아닌 단계(질문 계획 · 답변 작성 · 출력 검사)의 진행 표시."""

    type: Literal["step"] = "step"
    step: str
    detail: str = ""


class InputRequested(_Event):
    type: Literal["input_requested"] = "input_requested"
    pending: PendingQuestion


class AnswerReady(_Event):
    type: Literal["answer_ready"] = "answer_ready"
    response: AnswerResponse


class RunFailed(_Event):
    type: Literal["run_failed"] = "run_failed"
    error: ErrorInfo


RunEvent = (
    ToolStarted | ToolFinished | ToolFailed | StepNote | InputRequested | AnswerReady | RunFailed
)
