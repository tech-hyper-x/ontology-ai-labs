"""BOM 변경 영향 분석 에이전트 — LangGraph 워크플로 (Part 2 Ch7, 설계 덱 39장).

화면(ui.py)이 부르는 유일한 함수는 run(request, on_event) 이다.

실행 흐름 (실행 방식 kg_tools)
  plan    질문 계획 (S1)       — LLM 이 유형과 계산에 필요한 값을 구조화
  resolve 부품 식별 (S2)       — find_part. 후보가 여럿이거나 값이 빠지면 ask 로
  ask     되묻기              — LangGraph interrupt 로 멈추고, 사용자의 답을 받아 resolve 로 돌아간다
  act     도구 실행 (S3~S5)    — 유형별 스킬의 도구 순서대로 MCP 도구를 부른다
  answer  답변 조립 + 출력 검사 — 결론의 인용 값이 계산 결과와 맞는지 검사, 실패하면 한 번 다시 쓴다
실행 방식 rag · llm_only 는 baseline 노드 하나로 처리한다 (비교용).

같은 run_id 로 다시 부르면 체크포인트에서 이어서 실행한다 (되묻기 응답). 이미 끝난 도구는 다시 부르지 않는다.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from mfg_bom_agent.audit import RunAudit
from mfg_bom_agent.config import get_settings
from mfg_bom_agent.contracts.answer import (
    AnswerRequest,
    AnswerResponse,
    CalcResult,
    DocEvidence,
    ErrorInfo,
    GraphPath,
    PendingQuestion,
    SourceInfo,
    TraceInfo,
    Verification,
)
from mfg_bom_agent.contracts.events import (
    AnswerReady,
    InputRequested,
    RunEvent,
    RunFailed,
    StepNote,
)
from mfg_bom_agent.workflows import answer as ans
from mfg_bom_agent.workflows.baseline import llm_only_answer, rag_answer
from mfg_bom_agent.workflows.gateway import ToolCallError, ToolGateway
from mfg_bom_agent.workflows.llm import LLMUnavailable
from mfg_bom_agent.workflows.plan import QuestionPlan, llm_plan, rule_plan
from mfg_bom_agent.workflows.skills import (
    ASK_PROMPT,
    REQUIRED,
    SKILL_OF_INTENT,
    run_skill,
)

# 부품을 특정해야 하는 질문 유형. 원가(제품 전체) · 증상(문서로 부품을 찾음) · 공급 중단 · ECN 은 부품 식별을 하지 않는다.
PART_INTENTS = {"purchase_quantity", "price_change", "discontinue", "part_info"}
_SKU_TERM = re.compile(r"\d{4}-\d{4}-\d{4}|[A-Z]?-?\d{3,5}[A-Z]")
CANNED_DIR = Path(__file__).resolve().parents[3] / "data" / "golden" / "canned"
KG_TOOLS = [
    "find_part",
    "where_used",
    "bom_explode",
    "purchase_quantity",
    "cost_rollup",
    "revision_diff",
    "change_impact",
    "supply_risk",
    "search_docs",
]
DATA_USED = {
    "kg_tools": ["Neo4j 그래프 (BOM · 판 · ECN · 공급)", "정비 문서 · 이슈 검색"],
    "rag": ["문서 조각 검색 (정비 문서 · 이슈 · BOM 표 텍스트)"],
    "llm_only": ["없음 (질문만)"],
}
TOOLS_OF_MODE = {"kg_tools": KG_TOOLS, "rag": ["search_docs"], "llm_only": []}


class State(TypedDict, total=False):
    request: dict
    plan: dict
    parts: list[dict]
    pending: dict | None
    skill_out: dict
    draft: dict
    verification: dict
    answer_text: str
    answer_summary: str
    documents: list[dict]
    error: dict | None


def _cfg(config: RunnableConfig) -> tuple[ToolGateway, Callable[[RunEvent], None]]:
    c = config["configurable"]
    return c["gateway"], c["on_event"]


def _note(config: RunnableConfig, req: dict, step: str, detail: str = "") -> None:
    _cfg(config)[1](StepNote(run_id=req["run_id"], step=step, detail=detail))


# ── 노드 ──────────────────────────────────────────────────
def plan_node(state: State, config: RunnableConfig) -> State:
    req = state["request"]
    demo = req["context"]["demo_mode"] == "fixed_llm"
    plan = rule_plan(req["question"]) if demo else llm_plan(req["question"])
    _note(
        config,
        req,
        "질문 계획",
        f"{plan.intent} · {SKILL_OF_INTENT[plan.intent]}"
        + (" (규칙 기반 · LLM 응답 고정)" if demo else ""),
    )
    return {"plan": plan.model_dump(), "parts": [], "pending": None}


def resolve_node(state: State, config: RunnableConfig) -> State:
    """필요한 값 확인 + 부품 식별. 빠진 값이나 모호한 부품이 있으면 pending 을 채운다."""
    gw, _ = _cfg(config)
    plan = QuestionPlan(**state["plan"])
    parts = list(state.get("parts", []))
    needs = REQUIRED[plan.intent]
    # 기본값이 있는 값은 채우고 가정으로 남긴다
    if "units" in needs and plan.units is None and needs["units"] is not None:
        plan.units = needs["units"]
    if plan.intent == "symptom" and not plan.search_query_en:
        plan.search_query_en = state["request"]["question"]
    # 부품 식별 (S2) — 아직 확정하지 않은 이름만. 증상 질문은 문서 검색으로 부품을 찾으므로 건너뛴다.
    # 품번이 있으면 품번만 쓴다 ("서보 2000-0025-0002" 처럼 이름과 품번이 함께 나오면 같은 부품을 두 번 찾지 않게).
    known = {p["term"] for p in parts}
    terms = plan.part_terms if plan.intent in PART_INTENTS else []
    skus = [x for x in terms if _SKU_TERM.fullmatch(x.strip())]
    terms = skus or terms[:1]
    for term in terms:
        if term in known:
            continue
        try:
            r = gw.call("find_part", query=term, revision=state["request"]["context"]["revision"])
        except ToolCallError as exc:  # 못 찾은 부품은 실패로 끝내지 않고 품번을 되묻는다
            pending = PendingQuestion(
                kind="missing_value",
                field=f"part:{term}",
                prompt=f"“{term}” 부품을 찾지 못했습니다. 품번(예: 2000-0025-0002)을 알려 주세요. "
                f"({exc.result.get('error', '')})",
            )
            return {"plan": plan.model_dump(), "parts": parts, "pending": pending.model_dump()}
        if r.get("resolved"):
            parts.append({"term": term, **r["resolved"]})
        elif r.get("ambiguous"):
            pending = PendingQuestion(
                kind="choose_candidate",
                field=f"part:{term}",
                prompt=f"“{term}”에 해당하는 부품이 {len(r['candidates'])}개입니다. 어느 부품인가요?",
                candidates=[
                    {
                        "id": c["sku"],
                        "name": c["name"],
                        "detail": "현재 BOM" if c["in_latest"] else "과거 부품",
                    }
                    for c in r["candidates"]
                ],
            )
            return {"plan": plan.model_dump(), "parts": parts, "pending": pending.model_dump()}
    for key in needs:
        missing = (key == "part" and not parts) or (
            key != "part" and getattr(plan, key, None) in (None, "")
        )
        if missing:
            pending = PendingQuestion(kind="missing_value", field=key, prompt=ASK_PROMPT[key])
            return {"plan": plan.model_dump(), "parts": parts, "pending": pending.model_dump()}
    return {"plan": plan.model_dump(), "parts": parts, "pending": None}


def ask_node(state: State, config: RunnableConfig) -> State:
    """사용자에게 되묻고 멈춘다. 답을 받으면 그 값을 계획에 넣고 resolve 로 돌아간다."""
    gw, _ = _cfg(config)
    pending = state["pending"]
    answer: dict = interrupt(
        pending
    )  # ← 여기서 실행이 멈추고, 같은 run_id 로 다시 부르면 답이 들어온다
    plan = QuestionPlan(**state["plan"])
    parts = list(state.get("parts", []))
    field, value = pending["field"], str(answer["value"]).strip()
    if field.startswith("part"):
        term = field.split(":", 1)[1] if ":" in field else value
        r = gw.call("find_part", query=value, revision=state["request"]["context"]["revision"])
        if r.get("resolved"):
            parts.append({"term": term, **r["resolved"]})
        if term not in plan.part_terms:
            plan.part_terms.append(term)
    elif field == "units":
        plan.units = int("".join(ch for ch in value if ch.isdigit()) or 0) or None
    else:
        setattr(plan, field, value)
    return {"plan": plan.model_dump(), "parts": parts, "pending": None}


def act_node(state: State, config: RunnableConfig) -> State:
    gw, _ = _cfg(config)
    plan = QuestionPlan(**state["plan"])
    from mfg_bom_agent.contracts.answer import RunContext

    ctx = RunContext(**state["request"]["context"])
    out = run_skill(gw, plan, ctx, state.get("parts", []))
    return {
        "skill_out": {
            "calculations": [c.model_dump(mode="json") for c in out.calculations],
            "graph_paths": [p.model_dump(mode="json") for p in out.graph_paths],
            "documents": [d.model_dump(mode="json") for d in out.documents],
            "assumptions": out.assumptions,
            "facts": json.loads(json.dumps(out.facts, default=str)),
            "revision": out.revision,
            "as_of": str(out.as_of) if out.as_of else None,
        }
    }


def answer_node(state: State, config: RunnableConfig) -> State:
    """결론 작성 → 출력 검사 → (실패 시) 한 번 다시 작성."""
    req, plan, so = state["request"], QuestionPlan(**state["plan"]), state["skill_out"]
    calcs = [CalcResult(**c) for c in so["calculations"]]
    paths = [GraphPath(**p) for p in so["graph_paths"]]
    docs = [DocEvidence(**d) for d in so["documents"]]
    skill = SKILL_OF_INTENT[plan.intent]
    if req["context"]["demo_mode"] == "fixed_llm":
        draft = ans.template_answer(calcs, paths, docs)
    else:
        payload = ans.facts_payload(
            req["question"],
            plan.intent,
            calcs,
            paths,
            docs,
            so["assumptions"],
            so["facts"],
            {
                "revision": so["revision"],
                "units": plan.units,
                "as_of": so["as_of"],
                "price_date": "미상",
            },
        )
        _note(config, req, "답변 작성", skill)
        draft = ans.draft_answer(skill, payload, as_of=str(so["as_of"] or req["context"]["as_of"]))

    def check(d: ans.AnswerDraft):
        # 인용 목록뿐 아니라 문장 속 수량도 도구 사실(경로의 1대당 수량 · 요청 대수 · 비율)과 대조한다
        return ans.verify(
            d,
            calcs,
            so["revision"],
            plan.units,
            paths=paths,
            facts={**so["facts"], "assumptions": so["assumptions"]},
            percent=plan.percent,
        )

    verification = check(draft)
    rewrites = 0
    if verification.status == "failed" and req["context"]["demo_mode"] != "fixed_llm":
        _note(config, req, "출력 검사 실패 → 다시 작성", ans.feedback_of(verification))
        draft = ans.draft_answer(
            skill,
            payload,
            ans.feedback_of(verification),
            as_of=str(so["as_of"] or req["context"]["as_of"]),
        )
        rewrites = 1
        verification = check(draft)
    verification.rewrites = rewrites
    if verification.status == "failed":
        # 다시 써도 틀린 문장은 내보내지 않는다. 검사 결과(무엇이 틀렸는지)는 그대로 남기고,
        # 답변은 검증된 계산 결과로 코드가 만든 문장으로 바꾼다
        draft = ans.withheld_answer(calcs, paths, docs)
        verification.withheld = True
    _note(config, req, "출력 검사", verification.status)
    draft = ans.keep_real_quotes(draft, docs)
    return {
        "draft": draft.model_dump(mode="json") | {"text": draft.text()},
        "verification": verification.model_dump(),
    }


def baseline_node(state: State, config: RunnableConfig) -> State:
    gw, _ = _cfg(config)
    req = state["request"]
    if req["mode"] == "rag":
        text, docs, summary = rag_answer(req["question"], gw)
        return {
            "answer_text": text,
            "answer_summary": summary,
            "documents": [d.model_dump(mode="json") for d in docs],
        }
    text, summary = llm_only_answer(req["question"])
    return {"answer_text": text, "answer_summary": summary, "documents": []}


# ── 그래프 ────────────────────────────────────────────────
@lru_cache
def build_graph():
    g = StateGraph(State)
    g.add_node("plan", plan_node)
    g.add_node("resolve", resolve_node)
    g.add_node("ask", ask_node)
    g.add_node("act", act_node)
    g.add_node("answer", answer_node)
    g.add_node("baseline", baseline_node)
    g.add_conditional_edges(
        START, lambda s: "plan" if s["request"]["mode"] == "kg_tools" else "baseline"
    )
    g.add_edge("plan", "resolve")
    g.add_conditional_edges("resolve", lambda s: "ask" if s.get("pending") else "act")
    g.add_edge("ask", "resolve")
    g.add_edge("act", "answer")
    g.add_edge("answer", END)
    g.add_edge("baseline", END)
    return g.compile(checkpointer=MemorySaver())


def _public_trace_url(url: str | None) -> str | None:
    """트레이스 링크의 호스트를 브라우저에서 열 수 있는 주소(LANGFUSE_PUBLIC_URL)로 바꾼다."""
    s = get_settings()
    if url and url.startswith(s.langfuse_host.rstrip("/")):
        return s.langfuse_public_url.rstrip("/") + url[len(s.langfuse_host.rstrip("/")) :]
    return url


def _first_sentence(text: str) -> str:
    """비교 화면 요약표에 쓸 첫 문장. 기준선 방식(RAG · LLM 단독)은 답변을 구역으로 나누지 않는다."""
    m = re.match(r"(.+?[.!?。])(\s|$)", (text or "").strip(), re.DOTALL)
    return (m.group(1) if m else (text or "")[:120]).strip()


def _response(req: AnswerRequest, state: dict, gw: ToolGateway) -> AnswerResponse:
    """그래프 최종 상태 → 화면 계약(AnswerResponse)."""
    ctx = req.context
    mode = req.mode
    if mode != "kg_tools":
        return AnswerResponse(
            run_id=req.run_id,
            status="completed",
            mode=mode,
            headline=_first_sentence(state.get("answer_text", "")),
            summary=state.get("answer_summary", ""),
            conclusion=state.get("answer_text", ""),
            documents=[DocEvidence(**d) for d in state.get("documents", [])],
            context=ctx,
            verification=Verification(status="not_run", reason="계산 도구를 쓰지 않는 실행 방식"),
            sources=SourceInfo(
                snapshot=ctx.snapshot,
                revision=ctx.revision,
                as_of=ctx.as_of,
                data_used=DATA_USED[mode],
                tools_available=TOOLS_OF_MODE[mode],
                assumptions=["계산은 LLM 이 직접 함 — 도구 검증 없음"] if mode == "rag" else [],
            ),
            tool_calls=len(gw.calls),
        )
    so = state["skill_out"]
    plan = state["plan"]
    d = state["draft"]
    exclusions = (
        ["재고 · 공임 · 운송비 제외"]
        if plan["intent"] in ("discontinue", "symptom", "purchase_quantity")
        else []
    )
    return AnswerResponse(
        run_id=req.run_id,
        status="completed",
        mode=mode,
        intent=plan["intent"],
        headline=d["headline"],
        summary=d.get("summary", ""),
        highlights=d.get("highlights", []),
        subject=d.get("subject", ""),
        basis=d.get("basis", ""),
        findings=d["findings"],
        follow_ups=d["follow_ups"],
        notes=d["notes"],
        key_facts=d["key_facts"],
        doc_notes=d["doc_notes"],
        cited_labels=[c["label"] for c in d["cited"]],
        conclusion=d["text"],
        calculations=[CalcResult(**c) for c in so["calculations"]],
        graph_paths=[GraphPath(**p) for p in so["graph_paths"]],
        documents=[DocEvidence(**d) for d in so["documents"]],
        sources=SourceInfo(
            snapshot=ctx.snapshot,
            revision=so["revision"],
            as_of=so["as_of"],
            assumptions=so["assumptions"],
            exclusions=exclusions,
            data_used=DATA_USED[mode],
            tools_available=KG_TOOLS,
        ),
        verification=Verification(**state["verification"]),
        context=ctx,
        tool_calls=len(gw.calls),
    )


def run(
    request: AnswerRequest, on_event: Callable[[RunEvent], None] | None = None
) -> AnswerResponse:
    """질문 하나를 실행한다. 되묻기가 필요하면 status="needs_input" 과 pending_question 을 돌려준다.

    모든 실행 이벤트는 로컬 감사 기록(audit.py)에도 남는다 — Langfuse 연결 여부와 상관없다.
    """
    audit = RunAudit(request.run_id)
    audit.start(request)
    emit = audit.wrap(on_event or (lambda e: None))
    response = _run(request, emit)
    response.audit_path, response.audit_ok = str(audit.path), audit.ok
    return response


def _run(request: AnswerRequest, emit: Callable[[RunEvent], None]) -> AnswerResponse:
    if request.context.demo_mode == "canned":
        return _canned(request, emit)
    gw = ToolGateway(request.run_id, emit)
    config: dict[str, Any] = {
        "configurable": {"thread_id": request.run_id, "gateway": gw, "on_event": emit}
    }
    graph_input: Any = (
        Command(resume=request.resume.model_dump())
        if request.resume
        else {"request": request.model_dump(mode="json")}
    )
    trace = None
    try:
        with _tracing(request, config) as tr:
            result = build_graph().invoke(graph_input, config)
            trace = tr.get("trace")
    except ToolCallError as exc:
        return _failed(request, emit, "tool_error", str(exc), gw)
    except LLMUnavailable as exc:
        return _failed(request, emit, "llm_error", str(exc), gw)
    except Exception as exc:  # noqa: BLE001 — 화면에 원인을 보여 주고 실패 상태로 끝낸다
        return _failed(request, emit, "internal", f"{type(exc).__name__}: {exc}", gw)

    if result.get("__interrupt__"):
        pending = PendingQuestion(**result["__interrupt__"][0].value)
        emit(InputRequested(run_id=request.run_id, pending=pending))
        return AnswerResponse(
            run_id=request.run_id,
            status="needs_input",
            mode=request.mode,
            intent=result.get("plan", {}).get("intent"),
            context=request.context,
            pending_question=pending,
            tool_calls=len(gw.calls),
        )
    response = _response(request, result, gw)
    response.trace = trace
    emit(AnswerReady(run_id=request.run_id, response=response))
    return response


def _failed(req: AnswerRequest, emit, kind: str, message: str, gw: ToolGateway) -> AnswerResponse:
    err = ErrorInfo(kind=kind, message=message)
    emit(RunFailed(run_id=req.run_id, error=err))
    return AnswerResponse(
        run_id=req.run_id,
        status="failed",
        mode=req.mode,
        context=req.context,
        error=err,
        tool_calls=len(gw.calls),
    )


def _canned(req: AnswerRequest, emit) -> AnswerResponse:
    """DEMO_MODE=canned: 저장된 화면 예시를 돌려준다. 실제 실행이 아니므로 검사는 미실행으로 바꾼다."""
    for path in sorted(CANNED_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("question") == req.question:
            resp = AnswerResponse(**data["response"])
            resp.run_id, resp.context = req.run_id, req.context
            resp.verification = Verification(status="not_run", reason="화면 예시 — 실제 실행 아님")
            for e in data.get("events", []):
                emit(
                    StepNote(
                        run_id=req.run_id, step=f"[예시] {e['step']}", detail=e.get("detail", "")
                    )
                )
            emit(AnswerReady(run_id=req.run_id, response=resp))
            return resp
    return _failed(
        req,
        emit,
        "internal",
        "이 질문의 저장된 화면 예시가 없습니다 (예시 질문 7개만 있음)",
        ToolGateway(req.run_id),
    )


@lru_cache
def _langfuse():
    """Langfuse 클라이언트. 키는 .env 를 읽은 Settings 에서 넘긴다 (환경변수로 내보내지 않기 때문)."""
    from langfuse import Langfuse

    s = get_settings()
    return Langfuse(
        public_key=s.langfuse_public_key.get_secret_value(),
        secret_key=s.langfuse_secret_key.get_secret_value(),
        host=s.langfuse_host,
    )


class _tracing:
    """Langfuse 트레이스로 감싼다. 키가 없거나 서버에 닿지 않으면 트레이스 없이 그대로 실행한다."""

    def __init__(self, req: AnswerRequest, config: dict) -> None:
        self.req, self.config, self.stack, self.info = req, config, [], {}

    def __enter__(self) -> dict:
        s = get_settings()
        if not s.langfuse_enabled or self.req.context.demo_mode != "none":
            return self.info
        try:
            from langfuse import propagate_attributes
            from langfuse.langchain import CallbackHandler

            client = _langfuse()
            attrs = propagate_attributes(
                trace_name=f"bom-agent · {self.req.mode}",
                session_id=self.req.run_id.split(":")[0],
                tags=["bom-agent", self.req.mode],
                metadata={"run_id": self.req.run_id, "dataset_version": s.dataset_version},
            )
            self.stack = [
                attrs,
                client.start_as_current_observation(
                    name="bom-agent", as_type="agent", input=self.req.question
                ),
            ]
            for cm in self.stack:
                cm.__enter__()
            self.config["callbacks"] = [
                CallbackHandler(public_key=s.langfuse_public_key.get_secret_value())
            ]
            trace_id = client.get_current_trace_id()
            self.info["trace"] = TraceInfo(
                trace_id=trace_id,
                url=_public_trace_url(client.get_trace_url(trace_id=trace_id)),
                session_id=self.req.run_id.split(":")[0],
            )
            self.client = client
        except Exception:  # noqa: BLE001 — 관측 도구 장애가 업무 실행을 막지 않게 한다
            self.stack = []
        return self.info

    def __exit__(self, *exc) -> None:
        for cm in reversed(self.stack):
            try:
                cm.__exit__(*exc)
            except Exception:  # noqa: BLE001, S110 — 트레이스 정리 실패는 답변 결과에 영향을 주지 않는다
                pass
        if self.stack:
            try:
                self.client.flush()
            except Exception:  # noqa: BLE001, S110 — Langfuse 전송 실패는 답변 결과에 영향을 주지 않는다
                pass
