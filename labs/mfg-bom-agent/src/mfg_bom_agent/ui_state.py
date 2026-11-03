"""화면 세션 상태 — 실행 단위로 상태를 관리한다 (docs/UI_DESIGN.md 4.2 · 4.4).

Streamlit 은 버튼 · 입력이 바뀔 때마다 스크립트를 처음부터 다시 실행한다.
대화 기록(문자열)만 두면 "이미 실행한 질문"을 구분할 수 없어 같은 질문이 두 번 실행된다.
그래서 실행마다 run_id 와 상태(queued → running → waiting_input / completed / failed)를 두고,
queued 인 실행만 에이전트를 호출한다. 실행 조건은 실행 순간 요청(AnswerRequest)에 복사해 고정한다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from mfg_bom_agent.contracts.answer import AnswerRequest, AnswerResponse
from mfg_bom_agent.contracts.events import RunEvent

Status = Literal["queued", "running", "waiting_input", "completed", "failed"]


def new_run_id() -> str:
    """실행 ID: 시각 + 난수. 같은 초에 두 번 실행해도 겹치지 않는다."""
    return f"{datetime.now():%H%M%S}-{uuid.uuid4().hex[:6]}"


@dataclass
class RunState:
    run_id: str
    request: AnswerRequest
    status: Status = "queued"
    events: list[RunEvent] = field(default_factory=list)
    response: AnswerResponse | None = None
    compare_group: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    attempts: int = 0  # 되묻기 응답으로 이어 실행한 횟수


def get_runs(session) -> dict[str, RunState]:
    session.setdefault("runs", {})
    session.setdefault("run_order", [])
    return session["runs"]


def add_run(session, request: AnswerRequest, group: str | None = None) -> RunState:
    runs = get_runs(session)
    state = RunState(run_id=request.run_id, request=request, compare_group=group)
    runs[state.run_id] = state
    session["run_order"].append(state.run_id)
    return state
