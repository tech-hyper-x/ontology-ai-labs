"""Streamlit 화면 — 환경 점검 탭 + 실습 탭 (docs/UI_DESIGN.md, Part 2 Ch7).

실습 탭은 "채팅 하나 + 근거 패널" 구조다. 질문을 실행하면 에이전트(workflows/bom_agent.run)가
MCP 도구를 부르고, 화면은 에이전트가 돌려준 구조(AnswerResponse)를 그대로 그린다.
화면은 Neo4j · MCP 를 직접 호출하지 않는다 (환경 점검 탭의 생존 확인만 예외).

실행:  uv run streamlit run src/mfg_bom_agent/ui.py
"""

from __future__ import annotations

import csv
import html
import json
import re
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from mfg_bom_agent.config import get_settings
from mfg_bom_agent.contracts.answer import AnswerRequest, AnswerResponse, ResumeInput, RunContext
from mfg_bom_agent.ui_state import RunState, add_run, get_runs, new_run_id
from mfg_bom_agent.workflows.answer import ISSUE_KO

ROOT = Path(__file__).resolve().parents[2]
# 업무 이름 (examples.yaml 의 work). 업무 선택은 예시 질문을 고르는 데만 쓰고 계산 조건에는 영향을 주지 않는다
WORKS = ["구매 수량·원가", "부품 변경·단종", "고장 점검·교체"]
MODES = {"kg_tools": "지식 그래프 + 도구", "rag": "RAG", "llm_only": "LLM 단독"}
SNAPSHOT_AS_OF = date(2026, 10, 22)


def md(text: str) -> str:
    """Streamlit 마크다운은 $...$ 를 수식으로 그린다. 금액의 $ 가 사라지지 않게 이스케이프한다."""
    return (text or "").replace("$", "\\$")


# ── 환경 점검 (기존 기능 유지) ─────────────────────────────────
# 각 점검 함수는 (성공 여부, 화면에 보여줄 한 줄 설명)을 돌려준다.
# 점검 화면은 어떤 오류든 그대로 보여주는 것이 목적이므로 예외를 넓게 잡는다.


def check_neo4j() -> tuple[bool, str]:
    try:
        from mfg_bom_agent.graph.client import server_info

        info = server_info()
        return True, (
            f"연결 확인 · {info.get('name')} {info.get('version')} ({info.get('edition')}), "
            f"노드 {info.get('nodes')}개"
        )
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def check_anthropic() -> tuple[bool, str]:
    """키가 유효하고 설정한 모델 ID가 실제로 존재하는지 Models API로 확인한다. 토큰 비용은 들지 않는다."""
    s = get_settings()
    if not s.anthropic_configured:
        return False, "ANTHROPIC_API_KEY 없음"
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=s.anthropic_api_key.get_secret_value())
        model = client.models.retrieve(s.llm_model)
        return True, f"키 유효 · 모델 확인 {model.id} (메시지 호출은 미확인)"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def check_mcp() -> tuple[bool, str]:
    """MCP 엔드포인트에 GET을 보내 응답이 오는지만 본다.

    Streamable HTTP 서버는 GET에 405나 406을 돌려줄 수 있는데, 그래도 서버가 떠 있다는 뜻이므로 성공으로 본다.
    에이전트가 inprocess 모드면 HTTP 서버 없이도 도구를 부를 수 있으므로 그 사실을 함께 표시한다.
    """
    s = get_settings()
    try:
        import httpx

        r = httpx.get(s.mcp_url, timeout=3)
        return (
            True,
            f"HTTP 응답 {r.status_code} @ {s.mcp_url} · 도구 목록 미확인 · 에이전트 호출 방식 {s.mcp_transport}",
        )
    except Exception as exc:  # noqa: BLE001
        if s.mcp_transport == "inprocess":
            return (
                True,
                f"HTTP 서버 미응답 — 에이전트는 inprocess(메모리) 방식으로 MCP 도구를 부른다 ({exc.__class__.__name__})",
            )
        return False, str(exc)


def check_langfuse() -> tuple[bool | None, str]:
    """Langfuse 서버 응답(/api/public/health)과 키 인증(/api/public/projects)을 확인한다.

    반환: (True=연결 · 인증됨, False=실패, None=키 없음)
    """
    s = get_settings()
    if not s.langfuse_enabled:
        return None, "키 없음 → 트레이스 기록 안 함"
    try:
        import httpx

        base = s.langfuse_host.rstrip("/")
        health = httpx.get(f"{base}/api/public/health", timeout=3)
        if health.status_code != 200:
            return False, f"서버 응답 {health.status_code} @ {base}"
        keys = (s.langfuse_public_key.get_secret_value(), s.langfuse_secret_key.get_secret_value())
        auth = httpx.get(f"{base}/api/public/projects", auth=keys, timeout=3)
        if auth.status_code != 200:
            return False, f"키 인증 실패 (HTTP {auth.status_code}) — LANGFUSE 키 확인"
        version = health.json().get("version", "")
        return True, f"연결 · 키 인증 확인 · Langfuse {version} · {s.langfuse_public_url}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


@st.cache_data(ttl=60, show_spinner=False)
def health_rows() -> list[tuple[str, str, str]]:
    """헬스체크 결과 (이름, 상태, 설명). 화면을 누를 때마다 외부 서비스를 부르지 않게 1분간 기억한다.

    상태: ok(초록, 연결됨) · warn(노랑, 키가 없어 꺼짐) · fail(빨강, 확인 필요)
    """
    rows = []
    for name, check in (
        ("Neo4j", check_neo4j),
        ("Anthropic API", check_anthropic),
        ("MCP 서버", check_mcp),
    ):
        ok, detail = check()
        rows.append((name, "ok" if ok else "fail", detail))
    ok, detail = check_langfuse()
    rows.append(
        ("Langfuse", "warn" if ok is None else ("ok" if ok else "fail"), detail)
    )  # 키 없음 = 노랑
    return rows


def render_health_sidebar() -> None:
    """사이드바 맨 아래 헬스체크: 서비스마다 색깔 점 하나. 자세한 내용은 점에 마우스를 올리면 보인다."""
    s = get_settings()
    st.sidebar.divider()  # 분석 기준(설정)과 헬스체크(상태)를 나눈다
    st.sidebar.markdown("**헬스체크**")
    last = st.session_state.get("last_verified", {})
    color = {"ok": "#16a34a", "warn": "#f59e0b", "fail": "#dc2626"}
    lines = []
    for name, state, detail in health_rows():
        if name == "Langfuse" and state == "ok" and last.get("langfuse"):
            detail += " · 마지막 실행에서 트레이스 확인됨"
        tip = html.escape(detail, quote=True)
        lines.append(
            f'<div title="{tip}" style="display:flex;align-items:center;gap:8px;margin:4px 0;font-size:0.9rem">'
            f'<span style="width:10px;height:10px;border-radius:50%;background:{color[state]};display:inline-block"></span>'
            f"{html.escape(name)}</div>"
        )
    st.sidebar.markdown("".join(lines), unsafe_allow_html=True)
    st.sidebar.caption(f"초록 연결됨 · 노랑 꺼짐(키 없음) · 빨강 확인 필요 · LLM {s.llm_model}")
    if st.sidebar.button("다시 확인", key="health-recheck"):
        health_rows.clear()
        st.rerun()


# ── 실습 탭 ────────────────────────────────────────────────
@st.cache_data
def load_examples() -> list[dict]:
    return yaml.safe_load((ROOT / "data" / "golden" / "examples.yaml").read_text(encoding="utf-8"))[
        "examples"
    ]


@st.cache_data
def load_revisions() -> list[dict]:
    """부품 구성(BOM 판) 목록. 적재에 쓴 processed CSV 에서 읽는다 (화면이 Neo4j 를 직접 조회하지 않기 위해).

    선택지는 커밋 해시보다 날짜와 변경 내용을 먼저 보여 준다. 변경 내용은 그 판을 만든 교육용 ECN 의
    변경 라인에서 만든다 (같은 부품이 추가 · 제거되면 "교체").
    """
    data = ROOT / "data" / "processed"
    with (data / "plm_revision.csv").open(encoding="utf-8") as f:
        revs = list(csv.DictReader(f))
    with (data / "plm_ecn.csv").open(encoding="utf-8") as f:
        ecn_of = {r["revision_to"]: r["ecn_id"] for r in csv.DictReader(f)}
    with (data / "plm_ecn_line.csv").open(encoding="utf-8") as f:
        lines = list(csv.DictReader(f))
    for r in revs:
        changes: dict[str, set] = {}
        for ln in lines:
            if ln["ecn_id"] == ecn_of.get(r["revision_id"]):
                changes.setdefault(ln["short_name"], set()).add(ln["change_type"])
        words = []
        for name, kinds in changes.items():
            kind = (
                "교체"
                if {"added", "removed"} <= kinds
                else {"added": "추가", "removed": "제거"}.get(next(iter(kinds)), "수량 변경")
            )
            words.append(f"{name} {kind}")
        r["summary"] = (
            " · ".join(words[:2]) + (f" 외 {len(words) - 2}건" if len(words) > 2 else "")
            or "최초 등록"
        )
        r["date"] = r["valid_from"].replace("-", ".")
    return list(reversed(revs))


def sidebar() -> dict:
    """사이드바는 '분석 기준'만 둔다. 바꿀 수 있는 것(부품 구성 기준)과 읽기만 하는 것(데이터 · 용어)을 나눈다."""
    s = get_settings()
    st.sidebar.header("분석 기준")
    st.sidebar.caption("기본 설정을 그대로 두고 질문해도 됩니다.")
    revs = load_revisions()
    latest = revs[0]
    labels = {f"최신 등록 구성 · {latest['date']}": None} | {
        f"{r['date']} 구성 · {r['summary']}": r["revision_id"] for r in revs[1:]
    }
    rev_label = st.sidebar.selectbox("부품 구성 기준", list(labels))
    st.sidebar.caption(
        "어떤 부품 목록과 수량으로 계산할지 선택합니다. 과거 구성도 조회할 수 있습니다. "
        "'최신'은 실습 데이터에 등록된 최신 구성이며, 현재 판매 중인 제품 구성을 뜻하지 않습니다."
    )
    chosen = next((r for r in revs if r["revision_id"] == labels[rev_label]), latest)
    with st.sidebar.expander("사용 중인 데이터"):
        st.markdown(
            f"**부품 구성**  \n{chosen['date']} 등록 구성 · {md(chosen['summary'])}  \n"
            f"식별자 `{chosen['revision_id']}` (NASA JPL 오픈소스 로버 저장소의 커밋)\n\n"
            "**가격 자료**  \n실습용 BOM 에 기록된 단가를 사용합니다.\n\n"
            f"**자료 확인일: {SNAPSHOT_AS_OF:%Y.%m.%d}**  \n"
            "이날 확인한 자료에 적힌 가격입니다. 가격이 이날 변경됐다는 의미는 아닙니다.\n\n"
            "**가격 적용일**  \n원본 자료에 표시돼 있지 않습니다.\n\n"
            "**원천**  \nNASA JPL Open Source Rover 저장소 스냅샷 `a78f9eb` · 공급사 · 대체 부품 · 단종은 교육용 가정"
        )
    with st.sidebar.expander("용어 안내"):
        st.markdown(
            "- **부품 구성표(BOM)** — 로버 한 대를 만드는 데 필요한 부품과 수량 목록\n"
            "- **부품 구성 기준** — 어느 시점의 부품 구성표로 계산할지. 저장소 커밋으로 재구성한 판\n"
            "- **팩** — 여러 개를 묶어 파는 판매 단위. 수량은 낱개로 바꿔 계산합니다\n"
            "- **배수** — 같은 어셈블리가 로버에 들어가는 개수 (예: 바퀴 6개)\n"
            "- **자료 확인일** — 가격 자료를 확인한 날\n"
            "- **가격 적용일** — 그 가격이 실제로 적용되기 시작한 날 (원본에 없음)"
        )
    render_health_sidebar()
    if s.demo_mode != "none":
        st.sidebar.info(
            {
                "fixed_llm": "데모 모드 · LLM 응답 고정 · 계산 도구 실제 실행",
                "canned": "화면 예시 · 실제 실행 아님 · 검증 미실행",
            }[s.demo_mode]
        )
    return {"revision": labels[rev_label], "revision_label": rev_label.split(" · ")[0]}


def make_request(question: str, cond: dict, mode: str) -> AnswerRequest:
    s = get_settings()
    ctx = RunContext(
        role=cond.get("work") or "업무 미선택",
        revision=cond["revision"],
        as_of=SNAPSHOT_AS_OF,
        dataset_version=s.dataset_version,
        llm_model=s.llm_model,
        demo_mode=s.demo_mode,
    )
    return AnswerRequest(run_id=new_run_id(), question=question, context=ctx, mode=mode)


# 도구는 "이름(키)"로 보여 준다. 키는 코드 · 트레이스에서 찾을 때, 이름은 화면만 보고 이해할 때 쓴다
TOOL_KO = {
    "find_part": "부품 찾기",
    "where_used": "사용처 조회",
    "bom_explode": "BOM 전개",
    "purchase_quantity": "구매 수량 계산",
    "cost_rollup": "원가 합산",
    "revision_diff": "판 비교",
    "change_impact": "변경 영향 계산",
    "supply_risk": "공급 리스크 조회",
    "search_docs": "정비 문서 검색",
}
INPUT_KO = {
    "part": "부품",
    "units": "생산 대수",
    "revision": "판",
    "scope": "범위",
    "required_each": "필요 수량(개)",
    "query": "검색어",
    "k": "검색 개수",
    "items": "품목",
    "supplier": "공급사",
    "change_type": "변경 종류",
    "ecn": "ECN",
    "percent": "변경률(%)",
    "rev_a": "비교 전 판",
    "rev_b": "비교 후 판",
    "name": "이름",
    "as_of": "기준일",
    "price_overrides": "단가 변경",
}


def tool_label(key: str | None) -> str:
    if not key:
        return "—"
    return f"{TOOL_KO.get(key, key)}(`{key}`)"


def inputs_text(inputs: dict) -> str:
    """도구 입력을 읽을 수 있는 문장으로. 예: 부품=1506-0032-0006 · 필요 수량(개)=120 · 판=dd6c2ba"""
    parts = []
    for k, v in inputs.items():
        if v in (None, "", [], {}):
            continue
        if isinstance(v, list):
            v = ", ".join(
                " ".join(f"{INPUT_KO.get(a, a)} {b}" for a, b in x.items())
                if isinstance(x, dict)
                else str(x)
                for x in v
            )
        parts.append(f"{INPUT_KO.get(k, k)}={v}")
    return " · ".join(parts)


def event_line(e) -> str | None:
    """진행 기록 한 줄. 실행 중 표시와 완료 후 "진행 과정"이 같은 문장을 쓴다."""
    if e.type == "tool_started":
        return f"⏳ {tool_label(e.tool)} 실행 — {md(inputs_text(e.inputs)[:180])}"
    if e.type == "tool_finished":
        return f"✅ {tool_label(e.tool)} 완료 · {md(e.summary)} · {e.elapsed_ms}ms"
    if e.type == "tool_failed":
        return f"❌ {tool_label(e.tool)} 오류 · {md(e.error)}"
    if e.type == "step":
        detail = " · ".join(
            STEP_KO.get(w.strip(), w.strip()) for w in str(e.detail).split("·") if w.strip()
        )
        return f"• {md(e.step)} — {md(detail)}" if detail else f"• {md(e.step)}"
    return None


# 진행 기록에 나오는 내부 코드(질문 유형 · 스킬 · 검사 결과)를 업무 용어로 바꾼다
STEP_KO = {
    "purchase_quantity": "유형: 구매 수량",
    "cost": "유형: 원가",
    "price_change": "유형: 단가 변경",
    "discontinue": "유형: 단종",
    "revision_change": "유형: 판 변경(ECN)",
    "supply_disruption": "유형: 공급 중단",
    "symptom": "유형: 고장 증상",
    "required_quantity": "유형: BOM 총소요량",
    "part_info": "유형: 부품 정보",
    "other": "유형: 기타",
    "bom-calculation": "절차: 수량/원가 계산",
    "change-and-supply-risk": "절차: 변경/공급 리스크",
    "maintenance-evidence": "절차: 정비 문서 근거",
    "part-identity-resolution": "절차: 부품 식별",
    "grounded-answer": "절차: 근거 답변",
    "passed": "인용 계산값 일치",
    "failed": "불일치 → 다시 작성",
    "not_run": "대조할 계산값 없음",
}


def render_process(state: RunState) -> None:
    """완료 후에도 데이터를 찾아간 과정을 접이식으로 남긴다 (실행 중에 보인 기록을 그대로 다시 그린다)."""
    lines = [x for x in (event_line(e) for e in state.events) if x]
    if not lines:
        return
    tools = sum(e.type == "tool_finished" for e in state.events)
    secs = (
        f" · {(state.finished_at - state.started_at).total_seconds():.1f}초"
        if state.started_at is not None and state.finished_at is not None
        else ""
    )
    label = {"completed": "완료", "failed": "실패", "waiting_input": "입력 대기"}.get(
        state.status, "진행"
    )
    with st.status(
        f"데이터를 찾아간 과정 · {label} · 도구 {tools}회{secs} · {MODES[state.request.mode]}",
        state="error" if state.status == "failed" else "complete",
        expanded=False,
    ):
        for line in lines:
            st.markdown(line)


def execute(state: RunState, resume: ResumeInput | None = None) -> None:
    """queued 인 실행만 에이전트를 부른다. 호출 직전에 running 으로 바꿔 재실행 때 중복 호출을 막는다."""
    from mfg_bom_agent.workflows.bom_agent import run

    state.status = "running"
    state.started_at = state.started_at or pd.Timestamp.now()
    state.attempts += 1
    with st.status(f"실행 중 · {MODES[state.request.mode]}", expanded=True) as box:

        def on_event(e) -> None:
            state.events.append(e)
            line = event_line(e)
            if line:
                box.write(line)

        req = state.request.model_copy(update={"resume": resume})
        resp = run(req, on_event)
        box.update(
            label=f"{'완료' if resp.status == 'completed' else '입력 대기' if resp.status == 'needs_input' else '실패'}"
            f" · {MODES[state.request.mode]}",
            state="complete" if resp.status != "failed" else "error",
            expanded=False,
        )
    state.response = resp
    state.status = {"completed": "completed", "needs_input": "waiting_input", "failed": "failed"}[
        resp.status
    ]
    state.finished_at = pd.Timestamp.now() if state.status in ("completed", "failed") else None
    if resp.trace:
        st.session_state.setdefault("last_verified", {})["langfuse"] = True


def condition_line(resp_ctx: RunContext, mode: str) -> str:
    rev = resp_ctx.revision or "최신 등록 구성"
    demo = {
        "none": "",
        "fixed_llm": " · 데모 모드 · LLM 응답 고정 · 계산 도구 실제 실행",
        "canned": " · 화면 예시 · 실제 실행 아님",
    }[resp_ctx.demo_mode]
    return (
        f"{resp_ctx.role} · 부품 구성 {rev} · 자료 확인일 {resp_ctx.as_of} · 가격 적용일 미표시 · "
        f"{resp_ctx.dataset_version} · {MODES[mode]}{demo}"
    )


# ─── [Hands-on P2-Ch7-3 실행 화면과 근거 패널] 시작 ───
# 화면은 두 층으로 나눈다.
#   답변(왼쪽): 사용자가 판단할 결과 — 첫 문장 답 · 결과 카드 · 확인된 내용 · 추가로 확인할 사항 · 가정
#   근거(오른쪽 탭): 필요할 때 확인할 상세 — 계산 근거 · BOM 사용처 · 문서 · 실행 기록
# 근거를 숨기지는 않지만 한꺼번에 펼치지도 않는다. 좁은 화면에서는 근거가 답변 아래로 내려간다.
UNIT_KO = {"ea": "개", "pack": "팩", "parts": "종"}


def fmt_value(value, unit: str) -> str:
    """계산값을 업무 표기로. USD → $1,234.00 · ea → 200개 · pack → 60팩"""
    if value is None:
        return "미계산"
    if unit == "USD":  # 음수는 부호를 $ 앞에 둔다 ($-2,254.50 → -$2,254.50)
        return f"-${-value:,.2f}" if value < 0 else f"${value:,.2f}"
    num = f"{value:,.2f}".rstrip("0").rstrip(".")
    return f"{num}{UNIT_KO.get(unit, ' ' + unit)}"


def trust_line(resp: AnswerResponse) -> tuple[str, str]:
    """검증 표시. "검증 통과"가 답변 전체가 옳다는 뜻으로 읽히지 않게 실제 검사 범위를 쓴다."""
    v = resp.verification
    n = len(v.checks)
    if resp.mode != "kg_tools":
        return (
            "⚪ 계산 검증 없음",
            "이 방식은 계산 도구를 쓰지 않아 수량 · 금액을 대조할 기준이 없습니다.",
        )
    if v.status == "passed" and n:
        head = f"✅ 인용 계산값 {n}건 일치"
        if v.rewrites:
            head += " (한 번 고쳐 씀)"
    elif v.status == "passed":
        # 인용 0건은 검사한 것이 없다는 뜻이다 — 성공(녹색)으로 보여 주지 않는다
        head = "⚪ 대조한 계산값 없음"
    elif v.status == "failed" and v.withheld:
        head = f"⚠️ 답변 검증 실패 {v.summary['failed']}건 — 계산 결과만 표시"
    elif v.status == "failed":
        head = f"⚠️ 계산값 불일치 {v.summary['failed']}건"
    else:
        head = "⚪ 대조할 계산값 없음"
    return head, (
        "검사 범위: 답변에 쓴 수량 · 금액 · 생산 대수 · 증감 방향. 문서 해석 · 원인 판단은 검사하지 않습니다."
    )


def cited_calcs(resp: AnswerResponse) -> list:
    by_label = {c.label: c for c in resp.calculations}
    seen, out = set(), []
    for label in resp.cited_labels:
        if label in by_label and label not in seen:
            seen.add(label)
            out.append(by_label[label])
    return out


def path_sentence(p) -> str:
    """경로를 업무 문장으로. detail 이 없으면(ECN 비교 등) 도구가 준 문장을 그대로 쓴다."""
    d = p.detail or {}
    if "assembly" not in d:
        return md(p.text)
    unit = "개" if d["pack_size"] == 1 else f"팩({d['pack_size']}개입)"
    name = d.get("name") or d["sku"]
    return (
        f"로버 → **{d['assembly']}** (로버에 {d['multiplier']}개) → {md(name)} `{d['sku']}` "
        f"{d['raw_qty']}{unit}씩 → **로봇 차량 1대당 {d['each_per_product']}개**"
    )


def signed_value(c) -> str:
    """차이 값에는 +/- 를 붙인다 (예: +$3,869.10)."""
    v = fmt_value(c.value, c.unit)
    if c.kind != "diff" or c.value is None or c.value == 0:
        return v
    return f"⬆️ +{v}" if c.value > 0 else f"⬇️ {v}"


def short_label(label: str) -> str:
    """카드 제목은 짧게: 앞의 품번을 뗀다. "2000-0025-0002 소요 금액 (50대)" → "소요 금액 (50대)" """
    return re.sub(r"^[0-9A-Za-z]+(-[0-9A-Za-z]+)+\s+", "", label)


def card_html(label: str, value: str, sub: str = "") -> str:
    """결과 카드. st.metric 은 긴 값을 자르므로 줄바꿈되는 HTML 카드를 쓴다 ($ 는 수식으로 읽히지 않게 엔티티로)."""
    esc = lambda s: html.escape(s).replace("$", "&#36;")
    # 금액 · 수량은 중간에서 끊기지 않게 한 줄로 (글자 값은 단어 단위로 줄바꿈)
    # 품번(5203-2402-0027)처럼 긴 글자 값은 칸 안에서 줄을 바꾼다
    is_amount = re.fullmatch(r"[+-]?\$?[\d,]+(\.\d+)?\s?[가-힣%]{0,2}", value.strip())
    nowrap = "white-space:nowrap" if is_amount else "overflow-wrap:anywhere"
    return (
        '<div style="border:1px solid #e2e5ea;border-radius:12px;padding:14px 16px;background:#fff;height:calc(100% - 12px);margin-bottom:12px">'
        f'<div style="color:#6b7280;font-size:0.82rem;font-weight:600">{esc(label)}</div>'
        f'<div style="color:#111827;font-size:1.25rem;font-weight:700;line-height:1.3;margin-top:6px;word-break:keep-all;{nowrap}">{esc(value)}</div>'
        + (
            f'<div style="color:#9aa1ad;font-size:0.78rem;margin-top:4px">{esc(sub)}</div>'
            if sub
            else ""
        )
        + "</div>"
    )


def render_cards(resp: AnswerResponse) -> None:
    # 변화량을 묻는 질문(단가 변경 · 판 비교)은 차이를 맨 앞에 둔다. 단종처럼 수량 · 금액을 먼저 묻는
    # 질문은 답변에 인용한 순서(수량 → 금액 → 대체 부품 차이)를 그대로 따른다
    calcs = cited_calcs(resp)
    if resp.intent in ("price_change", "revision_change"):
        calcs = sorted(calcs, key=lambda c: c.kind != "diff")
    calcs = calcs[:4]
    cards = [
        (
            short_label(c.label),
            signed_value(c),
            c.label if short_label(c.label) != c.label else "",
        )
        for c in calcs
    ]
    shown = {v for _, v, _ in cards}
    facts = [
        (k.label, k.value, "") for k in resp.key_facts if k.value not in shown
    ]  # 같은 값을 두 번 보여 주지 않는다
    cards += facts[: max(0, 4 - len(cards))]
    if not cards:
        return
    # 4장 이상이면 2 × 2 로 놓아 카드 폭을 넓힌다. 같은 줄 카드는 높이를 맞춘다
    st.markdown(
        "<style>"
        "[class*='st-key-result-cards'] [data-testid='stColumn'] [data-testid='stElementContainer'],"
        "[class*='st-key-result-cards'] [data-testid='stMarkdown'],"
        "[class*='st-key-result-cards'] [data-testid='stMarkdownContainer'],"
        "[class*='st-key-result-cards'] [data-testid='stMarkdownContainer'] > div { height: 100%; }"
        "</style>",
        unsafe_allow_html=True,
    )
    per_row = 2 if len(cards) >= 4 else len(cards)
    box = st.container(key=f"result-cards-{resp.run_id}")
    for start in range(0, len(cards), per_row):
        row = cards[start : start + per_row]
        for col, (label, value, sub) in zip(box.columns(per_row), row):
            col.markdown(
                card_html(label, value, sub.split(" ")[0] if sub else ""), unsafe_allow_html=True
            )
    st.write("")


# 첫 문장에서 강조할 계산 결과: 금액 · 수량 · 비율 (예: $1,330.38 · 200개 · 60팩 · 15%)
_RESULT = re.compile(r"[+-]?\$[\d,]+(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?(?:개|팩|종|%|건)")


# 변화 방향을 한눈에: 늘어나는 표현에는 ⬆️, 줄어드는 표현에는 ⬇️ (결과 쪽 첫 표현에만)
_UP = re.compile(r"증가|늘어|상승|오릅|올라|인상됩")
_DOWN = re.compile(r"감소|줄어|하락|내려|절감|인하됩")


def highlight_html(text: str, keywords: list[str]) -> str:
    """계산 결과와 핵심 키워드를 파란색으로, 증가 · 감소 표현 앞에는 아이콘을 붙인다."""
    blue = '<span style="color:#2d5bff">{}</span>'
    spans = [(m.start(), m.end()) for m in _RESULT.finditer(text)]
    for kw in keywords[:3]:
        i = text.find(kw) if kw else -1
        if i >= 0 and not any(a < i + len(kw) and i < b for a, b in spans):
            spans.append((i, i + len(kw)))
    out, pos = [], 0
    for a, b in sorted(spans):
        if a < pos:
            continue
        out += [html.escape(text[pos:a]), blue.format(html.escape(text[a:b]))]
        pos = b
    out.append(html.escape(text[pos:]))
    result = "".join(out)
    # 결과 쪽 변화 표현(문장 뒤쪽에 오는 것)에 아이콘을 붙인다. 조건절("가격이 오르면")은 건너뛴다
    matches = [m for m in re.finditer(f"{_UP.pattern}|{_DOWN.pattern}", result)]
    target = next(
        (
            m
            for m in matches
            if not result[m.end() : m.end() + 2].startswith(("면", "르면", "으면"))
        ),
        None,
    )
    if target:
        icon = "⬆️" if _UP.fullmatch(target.group(0)) else "⬇️"
        result = result[: target.start()] + f"{icon} " + result[target.start() :]
    return result.replace("$", "&#36;")


def render_answer_body(resp: AnswerResponse) -> None:
    head, scope = trust_line(resp)
    headline = highlight_html(resp.headline or resp.conclusion, resp.highlights)
    st.markdown(
        '<div style="color:#111827;font-size:1.6rem;font-weight:700;line-height:1.4;'
        f'margin:0.2rem 0 0.4rem;word-break:keep-all">{headline}</div>',
        unsafe_allow_html=True,
    )
    if resp.subject or resp.basis:  # 카드마다 품번을 반복하지 않고 대상 · 기준을 한 번만 보여 준다
        st.caption(
            " · ".join(
                x
                for x in (
                    f"대상: {md(resp.subject)}" if resp.subject else "",
                    f"계산 기준: {md(resp.basis)}" if resp.basis else "",
                )
                if x
            )
        )
    render_cards(resp)
    if resp.findings:
        st.markdown("**계산 기준**" if resp.calculations else "**확인된 내용**")
        st.markdown("\n".join(f"- {md(f)}" for f in resp.findings))
    if resp.follow_ups:
        st.markdown("**실행 전에 확인할 사항**")
        st.markdown("\n".join(f"- {md(f)}" for f in resp.follow_ups))
    if not resp.findings and resp.conclusion and resp.conclusion != resp.headline:
        st.markdown(md(resp.conclusion))  # 기준선 방식은 답변을 구역으로 나누지 않는다
    if resp.notes:  # 가정 · 가격 기준 · 제외 항목은 접어 두고 필요할 때 연다
        with st.expander("적용 조건 보기"):
            st.markdown("\n".join(f"- {md(n)}" for n in resp.notes))
    st.caption(f"{head} · {scope}")


def render_calc_tab(resp: AnswerResponse) -> None:
    st.caption("어떤 수량과 단가로 계산했는지 확인합니다.")
    if not resp.calculations:
        st.caption(
            "이 실행 방식은 계산 도구를 쓰지 않았습니다."
            if resp.mode != "kg_tools"
            else "계산 없음"
        )
        return
    cited = cited_calcs(resp)
    for c in cited or resp.calculations[:3]:
        with st.container(border=True):
            plus = (
                "+" if c.kind == "diff" and c.value and c.value > 0 else ""
            )  # 증가액은 + 를 붙인다
            st.markdown(f"**{md(plus + fmt_value(c.value, c.unit))}** · {md(c.label)}")
            if c.formula:
                st.markdown(md(c.formula))
            st.caption(
                f"계산 도구 {tool_label(c.tool)} · 부품 구성 {c.revision or '—'}"
                + (f" · 자료 확인일 {c.as_of}" if c.as_of else "")
                + (f" · {md(c.note)}" if c.note else "")
            )
            if c.inputs:
                with st.expander("수량·단가·적용 조건 보기"):
                    st.json(c.inputs, expanded=True)
    rest = [c for c in resp.calculations if c not in cited]
    if rest:
        with st.expander(f"전체 계산 결과 {len(resp.calculations)}건"):
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "항목": c.label,
                            "값": fmt_value(c.value, c.unit),
                            "산식": c.formula or (c.note or ""),
                            "도구": f"{TOOL_KO.get(c.tool, c.tool)} ({c.tool})" if c.tool else "—",
                        }
                        for c in resp.calculations
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )


def render_paths_tab(resp: AnswerResponse) -> None:
    st.caption("이 부품이 어떤 조립품과 제품에 사용되는지 확인합니다.")
    if not resp.graph_paths:
        st.caption("이 질문은 BOM 사용처를 조회하지 않았습니다.")
        return
    for p in resp.graph_paths:
        st.markdown(f"- {path_sentence(p)}")
    st.caption(
        f"부품 구성 {resp.graph_paths[0].revision or '—'} · 도구 {', '.join(tool_label(x) for x in sorted({p.tool for p in resp.graph_paths}))}"
    )


def rank_text(d) -> str:
    """하이브리드 검색 순위 한 줄. 두 검색 중 어느 쪽이 이 문서를 찾았는지 보여 준다."""
    if not d.ranks:
        return ""
    parts = [f"결합 {d.rank}위"] if d.rank else []
    parts += [
        f"{name} {d.ranks[key]}위" if key in d.ranks else f"{name} 20위 밖"
        for key, name in (("bm25", "키워드(BM25)"), ("vector", "벡터"))
    ]
    return "검색 순위: " + " · ".join(parts)


def bm25_only(resp: AnswerResponse) -> bool:
    """임베딩 장애로 문서 검색이 키워드(BM25)만으로 실행됐는지 (검색 도구가 남긴 경고로 판단)."""
    return bool(resp.sources) and any("BM25) 검색만" in a for a in resp.sources.assumptions)


def render_search_ranks(resp: AnswerResponse) -> None:
    """같은 질문의 키워드(BM25) · 벡터 · 결합 순위를 나란히 보여 준다. 두 검색이 모두 기여했는지 확인하는 표."""
    docs = sorted((d for d in resp.documents if d.ranks), key=lambda d: d.rank or 99)
    if not docs:
        return
    only = bm25_only(resp)
    title = (
        "검색 순위 · 키워드(BM25)만 — 벡터 검색 미실행"
        if only
        else "검색 순위 비교 · 키워드(BM25) · 벡터 · 결합(RRF)"
    )
    with st.expander(title):
        if only:
            st.warning(
                "질문 임베딩을 만들 수 없어 이번 검색은 키워드(BM25)만 썼습니다. 벡터 순위는 비교할 수 없습니다."
            )
        st.caption(
            "키워드 검색과 벡터 검색이 각각 상위 20건을 찾고, 문서마다 1 / (60 + 순위)를 더해 다시 줄 세웁니다. "
            "두 검색에 모두 나온 문서가 위로 올라갑니다."
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "결합": d.rank,
                        "키워드(BM25)": d.ranks.get("bm25", "20위 밖"),
                        "벡터": "미실행" if only else d.ranks.get("vector", "20위 밖"),
                        # 긴 경로 · 이슈 URL 은 끝 두 마디만 (servo_gear_replacement/README.md · issues/469)
                        "문서": "/".join(d.doc_path.rstrip("/").split("/")[-2:])
                        + (f" · {d.line}행" if d.line else ""),
                    }
                    for d in docs
                ]
            ).astype(str),
            hide_index=True,
            use_container_width=True,
        )


def render_docs_tab(resp: AnswerResponse) -> None:
    st.caption("답변에 사용한 문서와 해당 내용을 확인합니다.")
    if not resp.documents:
        st.caption("이 질문은 문서 검색을 쓰지 않았습니다.")
        return
    render_search_ranks(resp)
    used = set()
    for n in resp.doc_notes:  # 답변이 실제 인용한 문서 먼저: 한국어 요약 → 관련 문장 → 원문
        doc = next(
            (
                d
                for d in resp.documents
                if d.doc_path == n.doc_path and (n.line is None or d.line == n.line)
            ),
            None,
        )
        used.add((n.doc_path, n.line))
        with st.container(border=True):
            st.markdown(f"**{md(n.summary_ko)}**")
            st.caption(
                f"{n.doc_path}"
                + (f" · {n.line}행" if n.line else "")
                + (f" · {rank_text(doc)}" if doc and doc.ranks else "")
            )
            if n.quote:
                st.markdown(f"> {md(n.quote)}")
            if doc:
                with st.expander("원문 보기"):
                    st.markdown(md(doc.excerpt))
    others = [d for d in resp.documents if (d.doc_path, d.line) not in used]
    if others:
        with st.expander(f"검색된 다른 문서 {len(others)}건", expanded=not resp.doc_notes):
            for d in others:
                st.markdown(
                    f"**{md(d.title)}** · {d.doc_path}" + (f" {d.line}행" if d.line else "")
                )
                if d.ranks:
                    st.caption(rank_text(d))
                st.caption(md(d.excerpt[:300]))


def cypher_text(q: dict) -> str:
    """Neo4j Browser 에 그대로 붙여 넣을 수 있는 형태: 파라미터(:params) → 쿼리 순서, 문장마다 ; 로 끝낸다."""
    params = ", ".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in q["params"].items())
    head = (
        f"// 이 도구 호출에서 {q['calls']}번 실행 (파라미터 같음)\n"
        if q.get("calls", 1) > 1
        else ""
    )
    vectors = [k for k, v in q["params"].items() if isinstance(v, list) and len(v) > 20]
    if vectors:  # 질문 임베딩 전체가 :params 에 들어 있어 첫 줄이 길다 (가로로 스크롤)
        head += f"// {', '.join(vectors)} = 질문 임베딩 {len(q['params'][vectors[0]])}차원 (앱이 만든 값 그대로)\n"
    return f"{head}:params {{{params}}};\n\n{q['query'].rstrip(';')};"


def render_cypher(tool_events: list) -> None:
    """도구가 지식 그래프에 보낸 Cypher 를 호출 순서대로 보여 준다. 코드 블록 오른쪽 위 버튼으로 복사한다."""
    calls = [e for e in tool_events if e.type == "tool_finished" and e.outputs.get("queries")]
    if not calls:
        return
    total = sum(len(e.outputs["queries"]) for e in calls)
    with st.expander(
        f"실행한 Cypher 쿼리 {total}개 · 여기서 다시 실행하거나 Neo4j Browser 에서 실행"
    ):
        st.caption(
            "도구가 지식 그래프에 실제로 보낸 쿼리와 파라미터입니다. ▶ 실행으로 이 화면에서 바로 결과를 보거나, "
            "Neo4j Browser(http://localhost:7474)에 붙여 넣어 같은 결과를 확인할 수 있습니다. "
            "이 화면의 실행기는 읽기 전용입니다."
        )
        for i, e in enumerate(calls, 1):
            qs = e.outputs["queries"]
            st.markdown(f"**{i}. {tool_label(e.tool)}** · 쿼리 {len(qs)}개")
            for j, q in enumerate(qs):
                st.code(cypher_text(q), language="cypher")
                key = f"cypher-{e.call_id}-{j}"
                if st.button("▶ 실행 (읽기 전용)", key=f"{key}-run"):
                    st.session_state[key] = run_cypher(q["query"], q["params"])
                show_cypher_result(st.session_state.get(key))
        last = calls[-1].outputs["queries"][-1]
        render_cypher_editor(f"cypher-edit-{calls[0].run_id}", last["query"], last["params"])


@st.cache_resource
def _graph_driver():
    """화면의 Cypher 실행기가 쓰는 드라이버 (앱 실행 동안 하나를 재사용)."""
    from mfg_bom_agent.graph.client import make_driver

    return make_driver()


def run_cypher(query: str, params: dict | None) -> dict:
    """읽기 전용으로 실행한다 (graph/explore.py). 쓰기 쿼리는 실행 전에 막고 서버도 거부한다."""
    from mfg_bom_agent.graph.explore import run_readonly

    return run_readonly(_graph_driver(), query, params)


def show_cypher_result(res: dict | None) -> None:
    """실행 결과 표. 노드 · 관계 같은 중첩 값은 JSON 문자열로 보여 준다."""
    if not res:
        return
    if not res["ok"]:
        st.error(res["error"])
        return
    rows = [
        {
            k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
            for k, v in r.items()
        }
        for r in res["rows"]
    ]
    more = f" · 처음 {len(rows)}행만 표시" if res["truncated"] else ""
    st.caption(f"결과 {len(rows)}행 · {res['elapsed_ms']}ms{more}")
    if rows:
        st.dataframe(
            pd.DataFrame(rows, columns=res["columns"]).astype(str),
            hide_index=True,
            use_container_width=True,
        )


def render_cypher_editor(key: str, query: str, params: dict) -> None:
    """쿼리 · 파라미터를 고쳐서 직접 실행해 본다 (예: 품번 · 생산 대수를 바꿔 결과 비교)."""
    st.markdown("**직접 실행** · 쿼리나 파라미터를 고쳐 실행해 보세요 (읽기 전용 · 최대 100행)")
    short = {
        k: (f"[숫자 {len(v)}개 — 앱이 만든 값]" if isinstance(v, list) and len(v) > 20 else v)
        for k, v in params.items()
    }
    q = st.text_area("Cypher", value=query.strip(), height=200, key=f"{key}-q")
    p = st.text_area(
        "파라미터 (JSON)",
        value=json.dumps(short, ensure_ascii=False, indent=1),
        height=90,
        key=f"{key}-p",
    )
    if st.button("▶ 실행", key=f"{key}-run"):
        try:
            parsed = json.loads(p or "{}")
            # 긴 벡터는 화면에서 줄여 보여 주므로, 그대로 두면 원래 값으로 되돌려 실행한다
            parsed = {
                k: params[k] if isinstance(v, str) and v.startswith("[숫자 ") and k in params else v
                for k, v in parsed.items()
            }
            st.session_state[key] = run_cypher(q, parsed)
        except json.JSONDecodeError as exc:
            st.session_state[key] = {"ok": False, "error": f"파라미터 JSON 형식 오류: {exc}"}
    show_cypher_result(st.session_state.get(key))


def render_log_tab(resp: AnswerResponse, events: list) -> None:
    st.caption("질문에 답하기 위해 조회하고 계산한 순서를 확인합니다.")
    st.caption(condition_line(resp.context, resp.mode))
    if resp.audit_path:  # Langfuse 와 별개로 항상 남는 로컬 감사 기록
        state = "기록됨" if resp.audit_ok else "⚠️ 기록 실패 — 업무 결과는 그대로입니다"
        st.caption(f"감사 기록: `{Path(resp.audit_path).name}` ({state})")
    v = resp.verification
    if v.checks:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "인용 항목": c.target,
                        "값": c.cited_value,
                        "항목": "✓" if c.item_ok else "✗",
                        "값 일치": "✓" if c.value_ok else "✗",
                        "단위": "✓" if c.unit_ok else "✗",
                        "조건": "✓" if c.condition_ok else "✗",
                        "증감 방향": "✓" if c.direction_ok else "✗",
                    }
                    for c in v.checks
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    if v.unverified_numbers:
        st.warning("계산 결과에 없는 금액: " + ", ".join(f"\\${m}" for m in v.unverified_numbers))
    for i in v.issues:  # 인용 목록 밖, 문장 속 수량 · 대수 · 방향 문제
        st.warning(f"{ISSUE_KO[i.code]}: '{md(i.target)}' — {md(i.detail)}")
    if v.withheld:
        st.info("다시 써도 검사에 실패해, LLM 이 쓴 답변 대신 도구가 계산한 결과만 표시했습니다.")
    tool_events = [e for e in events if e.type in ("tool_finished", "tool_failed")]
    st.markdown(f"**도구 호출 {len(tool_events)}건**")
    for i, e in enumerate(tool_events, 1):
        mark = "완료" if e.type == "tool_finished" else "오류"
        st.markdown(
            f"{i}. {tool_label(e.tool)} · {mark} · {md(getattr(e, 'summary', '') or getattr(e, 'error', ''))} · {e.elapsed_ms}ms"
        )
    render_cypher(tool_events)
    with st.expander("도구 입력 · 출력 상세"):
        starts = {e.call_id: e.inputs for e in events if e.type == "tool_started"}
        for e in tool_events:
            st.markdown(f"{tool_label(e.tool)} 입력")
            st.json(starts.get(e.call_id, {}), expanded=False)
            if e.type == "tool_finished":
                st.markdown("출력")
                st.json(e.outputs, expanded=False)
    s = resp.sources
    if s:
        lines = [
            f"스냅샷 {s.snapshot} · 부품 구성 {s.revision or '최신 등록 구성'} · 자료 확인일 {s.as_of or '—'} · 가격 적용일은 원본 자료에 없음"
        ]
        lines += [f"가정: {a}" for a in s.assumptions] + [f"제외: {e}" for e in s.exclusions]
        lines.append(f"제공 데이터: {', '.join(s.data_used)}")
        st.markdown("\n".join(f"- {md(x)}" for x in lines))
    if resp.trace and resp.trace.url:
        st.markdown(f"[Langfuse 트레이스 열기 ↗]({resp.trace.url})")


def render_evidence(resp: AnswerResponse, events: list) -> None:
    tabs = st.tabs(["계산 내역", "부품 사용 위치", "참고 문서", "처리 과정"])
    with tabs[0]:
        render_calc_tab(resp)
    with tabs[1]:
        render_paths_tab(resp)
    with tabs[2]:
        render_docs_tab(resp)
    with tabs[3]:
        render_log_tab(resp, events)


def render_answer(resp: AnswerResponse, events: list) -> None:
    """답변(왼쪽)과 근거 탭(오른쪽). 좁은 화면에서는 근거가 아래로 내려간다."""
    left, right = st.columns([3, 2], gap="large")
    with left:
        render_answer_body(resp)
    with right:
        render_evidence(resp, events)


def render_compare(group: list[RunState]) -> None:
    """세 방식 비교: 요약표로 한눈에 보고, 고른 방식만 자세히 본다."""
    rows = []
    for g in group:
        r = g.response
        if not r or g.status != "completed":
            rows.append(
                {
                    "방식": MODES[g.request.mode],
                    "답": {"running": "실행 중", "waiting_input": "입력 대기"}.get(
                        g.status, "실패"
                    ),
                    "핵심 수치": "—",
                    "근거": "—",
                    "계산 검증": "—",
                }
            )
            continue
        # 핵심 수치는 첫 문장(답)에 나온 계산값을 고른다
        cited = cited_calcs(r)
        # 핵심 수치는 첫 문장(답)에서 가장 먼저 나온 계산값 — 보통 질문이 묻는 값이다
        head_text = r.headline or ""
        mentioned = [c for c in cited if fmt_value(c.value, c.unit) in head_text]
        mentioned.sort(
            key=lambda c: (c.kind != "diff", head_text.index(fmt_value(c.value, c.unit)))
        )
        top = mentioned[:1] or sorted(cited, key=lambda c: c.kind != "diff")[:1]
        rows.append(
            {
                "방식": MODES[g.request.mode],
                "답": md(
                    r.summary or r.headline or r.conclusion[:120]
                ),  # 표 안의 $ 가 수식으로 읽히지 않게
                "핵심 수치": signed_value(top[0]) if top else "계산 없음",
                "근거": f"계산 {len(r.calculations)} · 사용처 {len(r.graph_paths)} · 문서 {len(r.documents)}",
                "계산 검증": trust_line(r)[0],
            }
        )
    st.table(pd.DataFrame(rows).set_index("방식"))
    pick = st.segmented_control(
        "자세히 볼 방식",
        [g.run_id for g in group],
        format_func=lambda rid: MODES[next(g for g in group if g.run_id == rid).request.mode],
        default=group[0].run_id,
        key=f"pick-{group[0].compare_group}",
    )
    chosen = next((g for g in group if g.run_id == pick), group[0])
    render_run(chosen)


# ─── [Hands-on P2-Ch7-3] 끝 ───


def render_run(state: RunState) -> None:
    resp = state.response
    render_process(state)
    if state.status == "waiting_input" and resp and resp.pending_question:
        pq = resp.pending_question
        st.warning(f"**추가 질문** — {md(pq.prompt)}")
        key = f"resume-{state.run_id}-{state.attempts}"
        if pq.kind == "choose_candidate" and pq.candidates:
            choice = st.radio(
                "후보",
                [c["id"] for c in pq.candidates],
                key=key,
                format_func=lambda cid: next(
                    f"{c['id']} · {c['name']} · {c['detail']}"
                    for c in pq.candidates
                    if c["id"] == cid
                ),
            )
        else:
            choice = st.text_input("답", key=key)
        c1, c2 = st.columns([1, 1])
        if c1.button("선택 후 계속", key=f"go-{key}") and choice:
            execute(state, ResumeInput(field=pq.field, value=str(choice)))
            st.rerun()
        if c2.button("취소", key=f"cancel-{key}"):
            state.status = "failed"
            st.rerun()
    elif state.status == "failed":
        msg = resp.error.message if resp and resp.error else "사용자가 취소함"
        st.error(f"실패 · {msg}")
        if st.button("같은 조건으로 다시 실행", key=f"retry-{state.run_id}"):
            new = add_run(
                st.session_state,
                state.request.model_copy(update={"run_id": new_run_id(), "resume": None}),
            )
            execute(new)
            st.rerun()
    elif state.status == "completed" and resp:
        render_answer(resp, state.events)


def render_result(state: RunState, runs: dict) -> set[str]:
    """실행 하나(또는 비교 묶음)를 그린다. 그린 run_id 를 돌려준다."""
    if state.compare_group:
        group = [
            runs[r]
            for r in st.session_state["run_order"]
            if runs[r].compare_group == state.compare_group
        ]
        st.caption(
            "세 방식 비교 — 질문 · 부품 구성 · 자료 확인일 · 데이터 버전을 고정하고 각각 실행했습니다."
        )
        render_compare(group)
        return {g.run_id for g in group}
    render_run(state)
    return {state.run_id}


def question_title(question: str) -> str:
    """결과 위 질문 제목: 큰따옴표로 감싸 사용자가 물은 문장임을 바로 알 수 있게 한다."""
    text = html.escape(question).replace("$", "&#36;")
    # 질문은 작게, 답변 첫 문장을 크게 — 눈이 답에 먼저 가게 한다
    return (
        '<div style="color:#4b5563;font-size:1.1rem;font-weight:600;line-height:1.5;'
        f'margin:0.4rem 0 0.6rem;word-break:keep-all">“{text}”</div>'
    )


def render_lab_tab(cond: dict) -> None:
    examples = load_examples()
    runs = get_runs(st.session_state)
    has_runs = bool(st.session_state["run_order"])
    # 질문 입력: 결과가 생기면 예시를 접어 새 결과가 화면 위쪽에 오게 한다
    with st.expander("질문을 선택해 시작하세요", expanded=not has_runs):
        st.caption(
            "부품 변경, 구매 수량, 원가에 대해 질문하세요. 아래 질문을 선택하거나, 직접 질문을 입력할 수 있습니다."
        )
        work = (
            st.segmented_control(
                "업무", WORKS, key="work", default=WORKS[0], label_visibility="collapsed"
            )
            or WORKS[0]
        )
        cards = [e for e in examples if e["work"] == work]
        # 같은 줄 카드는 가장 큰 카드 높이에 맞추고, 선택 버튼은 카드 맨 아래에 둔다
        st.markdown(
            "<style>"
            # 열 안에서 카드를 감싼 칸(stLayoutWrapper)이 열 높이만큼 늘어나게 한다
            ".st-key-card-row [data-testid='stLayoutWrapper']:has(> [class*='st-key-card-box-'])"
            " { flex: 1 1 auto; }"
            "[class*='st-key-card-box-'] { height: 100%; }"
            "[class*='st-key-card-box-'] > div:last-child { margin-top: auto; }"
            "</style>",
            unsafe_allow_html=True,
        )
        row = st.container(key="card-row")
        for col, ex in zip(row.columns(3), cards):
            selected = st.session_state.get("question") == ex["question"]
            with col.container(border=True, key=f"card-box-{ex['id']}"):
                head = f"**{ex['label']}**" + ("  `실습 가정`" if ex.get("assumption") else "")
                st.markdown(head)
                st.markdown(md(ex["question"]))
                st.caption(f"확인할 내용: {ex['shows']}")
                if st.button(
                    "✓ 선택됨" if selected else "이 질문 선택",
                    key=f"card-{ex['id']}",
                    type="primary" if selected else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["question"] = ex[
                        "question"
                    ]  # 입력창에 넣고, 수정한 뒤 실행한다
                    st.rerun()
    cond = cond | {"work": work if not has_runs else st.session_state.get("work")}
    # 실행 방식은 질문 바로 위에 가로로 둔다 (사이드바보다 실행 직전에 고르기 쉽다)
    choice = st.radio(
        "실행 방식",
        [*MODES, "compare"],
        format_func=lambda m: MODES.get(m, "세 방식 비교"),
        horizontal=True,
        key="run_mode",
        help="세 방식 비교: 같은 질문 · 부품 구성 · 자료 확인일로 지식 그래프 + 도구, RAG, LLM 단독을 함께 실행",
    )
    cond = cond | {
        "mode": "kg_tools" if choice == "compare" else choice,
        "compare": choice == "compare",
    }
    q_col, b_col = st.columns([6, 1], vertical_alignment="bottom")
    question = q_col.text_input(
        "질문을 입력하거나 수정하세요",
        key="question",
        placeholder="예: 서보 2000-0025-0002가 단종되면 로버 50대 생산에 몇 개가 필요한가요?",
    )
    if b_col.button(
        "답변 확인", type="primary", disabled=not question.strip(), use_container_width=True
    ):
        modes = list(MODES) if cond["compare"] else [cond["mode"]]
        group = new_run_id() if cond["compare"] else None
        for m in modes:
            add_run(st.session_state, make_request(question.strip(), cond, m), group)

    queued = [r for r in runs.values() if r.status == "queued"]
    for state in queued:  # 이번 실행에서 새로 만든 실행만 에이전트를 부른다
        execute(state)
    if queued:
        st.rerun()  # 진행 표시를 지우고 새 결과를 맨 위에 그린다

    order = list(reversed(st.session_state["run_order"]))
    if not order:
        return
    latest = runs[order[0]]
    st.divider()
    st.markdown(question_title(latest.request.question), unsafe_allow_html=True)
    shown = render_result(latest, runs)
    previous = [rid for rid in order if rid not in shown]
    if previous:
        st.divider()
        st.markdown("**이전 결과**")
    for rid in previous:
        if rid in shown:
            continue
        state = runs[rid]
        label = f"{state.request.question} · {'세 방식 비교' if state.compare_group else MODES[state.request.mode]} · {state.run_id[:6]}"
        with st.expander(label):
            shown |= render_result(state, runs)


def main() -> None:
    assets = Path(__file__).parent / "assets"
    st.set_page_config(
        page_title="로봇 차량 부품·원가 분석 에이전트 · NASA OSR BOM LAB",
        page_icon="🧭",
        layout="wide",
    )
    st.logo(str(assets / "osr-lab-logo.svg"), size="large")  # 왼쪽 위 이름 표기 (글자만)
    # 한글이 글자 중간("에이전/트")에서 끊기지 않게 단어 단위로 줄을 바꾼다
    st.markdown(
        "<style>h1, h2, h3, h4, h5, p, li, td { word-break: keep-all; }</style>",
        unsafe_allow_html=True,
    )
    st.title("로봇 차량 부품·원가 분석 에이전트")  # 왼쪽 위에 NASA OSR 이 있어 본문 제목은 짧게
    st.caption(
        "NASA JPL 오픈소스 로버(OSR)의 부품표(BOM) · 변경 이력 · 정비 문서를 지식 그래프로 연결해, "
        "부품 변경 · 단종 · 단가 인상이 로버 수량과 원가에 주는 영향을 근거와 함께 계산합니다."
    )
    cond = sidebar()
    render_lab_tab(cond)


if __name__ == "__main__":
    main()
