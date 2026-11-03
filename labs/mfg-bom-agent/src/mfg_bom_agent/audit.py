"""로컬 감사 기록 (Part 4 Ch1-1 권한 · 계보 · 감사 필드 설계).

요청 하나(run_id)의 시작 · 도구 성공/실패 · 검사 · 종료를 outputs/runs/<run_id>.jsonl 에 한 줄씩 남긴다.
Langfuse 키가 없거나 서버가 꺼져 있어도, 고정 답변 모드(fixed_llm)여도 항상 기록한다 (개발환경 정의서의 로그 계약).

기록하지 않는 것: API 키 · 암호 · 인증 헤더 (값처럼 보이는 비밀은 지운다), 도구 출력 전체 (요약만).
role 은 화면에서 고른 설명 문자열이다. 인증된 사용자가 아니므로 authenticated=false 로 함께 적는다.
기록에 실패해도 업무 결과는 그대로 돌려주고, 응답의 audit_ok=False 로 "기록 실패"를 알린다.
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from mfg_bom_agent.config import get_settings

SCHEMA_VERSION = "1"
AUDIT_DIR = Path(
    os.environ.get("AUDIT_DIR") or Path(__file__).resolve().parents[2] / "outputs" / "runs"
)

# 같은 파일에 여러 스레드가 동시에 쓰면 줄이 섞인다 → 파일마다 잠금 하나
_LOCKS: dict[Path, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()

_SECRET = re.compile(
    r"(sk-[A-Za-z0-9_\-]{8,}|pk-lf-[A-Za-z0-9\-]{6,}|sk-lf-[A-Za-z0-9\-]{6,}|pa-[A-Za-z0-9_\-]{16,}"
    r"|Bearer\s+\S+|(?:api[_-]?key|password|secret|token)\s*[=:]\s*\S+)",
    re.IGNORECASE,
)
# 도구 입력 중 감사에 필요한 조건만 남긴다 (질문 · 검색어는 앞부분만)
_INPUT_KEYS = {
    "part",
    "units",
    "revision",
    "mode",
    "k",
    "source",
    "percent",
    "value",
    "change_type",
    "supplier",
    "from_rev",
    "to_rev",
    "scope",
    "query",
    "required_each",
    "qty_each",
}


def redact(text: Any, limit: int = 300) -> str:
    """비밀처럼 보이는 값을 지우고 길이를 줄인다."""
    return _SECRET.sub("[비공개]", str(text))[:limit]


def _safe_name(run_id: str) -> str:
    """run_id 를 파일 이름으로 쓸 수 있게 바꾼다 (경로 구분자 · 특수문자 제거)."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", run_id)[:120] or "run"


class RunAudit:
    """요청 하나의 감사 기록기. write_event 는 여러 스레드에서 불러도 안전하다."""

    def __init__(self, run_id: str, directory: Path | None = None) -> None:
        self.run_id = run_id
        self.path = (directory or AUDIT_DIR) / f"{_safe_name(run_id)}.jsonl"
        self.ok = True  # 한 번이라도 쓰기에 실패하면 False
        self.error = ""
        with _LOCKS_GUARD:
            self._lock = _LOCKS.setdefault(self.path, threading.Lock())

    def write_event(self, event: str, **fields: Any) -> None:
        row = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "event_id": uuid.uuid4().hex[:12],
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "event": event,
            **fields,
        }
        line = json.dumps(row, ensure_ascii=False, default=str)
        try:
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except OSError as exc:  # 기록 실패는 업무 실패가 아니다 — 상태만 남긴다
            self.ok = False
            self.error = redact(f"{type(exc).__name__}: {exc}", 200)

    def start(self, request) -> None:
        """요청 시작: 누가(역할 · 인증 여부) · 무엇을 · 어떤 데이터 판 · 모델로."""
        ctx = request.context
        self.write_event(
            "run_started",
            actor={
                "role": ctx.role,
                "authenticated": False,
            },  # 화면에서 고른 역할 — 인증 사용자 아님
            mode=request.mode,
            question=redact(request.question),
            resumed_field=request.resume.field if request.resume else None,
            lineage={
                "dataset_version": ctx.dataset_version,
                "snapshot": ctx.snapshot,
                "revision": ctx.revision,
                "as_of": ctx.as_of,
                "llm_model": ctx.llm_model,
                "demo_mode": ctx.demo_mode,
                "embedding_provider": get_settings().embedding_provider,
            },
        )

    def wrap(self, emit: Callable) -> Callable:
        """실행 이벤트 콜백을 감싸 감사 기록을 남긴 뒤 원래 콜백(화면)으로 넘긴다."""

        def on_event(e) -> None:
            self.record(e)
            emit(e)

        return on_event

    def record(self, e) -> None:
        """실행 이벤트 하나 → 감사 행. 도구 출력 전체 대신 요약만 남긴다."""
        t = getattr(e, "type", "")
        if t == "tool_started":
            inputs = {
                k: redact(v, 120) for k, v in e.inputs.items() if k in _INPUT_KEYS and v is not None
            }
            self.write_event("tool_started", call_id=e.call_id, tool=e.tool, inputs=inputs)
        elif t == "tool_finished":
            self.write_event(
                "tool_finished",
                call_id=e.call_id,
                tool=e.tool,
                result_status="ok",
                summary=redact(e.summary, 120),
                elapsed_ms=e.elapsed_ms,
                revision=e.outputs.get("revision"),
                as_of=e.outputs.get("as_of"),
                index_provider=e.outputs.get("index_provider"),
                effective_mode=e.outputs.get("effective_mode"),
            )
        elif t == "tool_failed":
            self.write_event(
                "tool_failed",
                call_id=e.call_id,
                tool=e.tool,
                result_status="failed",
                error_kind=getattr(e, "kind", "transport"),
                error=redact(e.error, 200),
                elapsed_ms=e.elapsed_ms,
            )
        elif t == "step":
            self.write_event("step", step=e.step, detail=redact(e.detail, 300))
        elif t == "input_requested":
            self.write_event("input_requested", field=e.pending.field)
        elif t == "answer_ready":
            r = e.response
            v = r.verification
            self.write_event(
                "run_finished",
                status=r.status,
                intent=r.intent,
                tool_calls=r.tool_calls,
                verification={
                    "status": v.status,
                    "version": v.version,
                    "rewrites": v.rewrites,
                    "withheld": v.withheld,
                    "codes": sorted({i.code for i in v.issues}),
                },
                cited_sources=sorted({d.doc_path for d in r.documents})[:20],
            )
        elif t == "run_failed":
            self.write_event(
                "run_failed",
                status="failed",
                error_kind=e.error.kind,
                error=redact(e.error.message, 200),
            )
