"""로컬 감사 기록 · 부분 실패 테스트 (Part 4 Ch1-1 · Part 2 Ch6-2). Neo4j · LLM 없이 실행한다.

테스트 ID(A01 …)는 실행 계획서 6절의 번호다.
"""

import json
import threading
from datetime import datetime

from mfg_bom_agent.audit import RunAudit, redact
from mfg_bom_agent.contracts.answer import AnswerRequest, RunContext
from mfg_bom_agent.contracts.events import StepNote, ToolFailed, ToolFinished, ToolStarted


def rows(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_a01_records_without_langfuse(tmp_path):
    a = RunAudit("run-1", tmp_path)
    a.start(
        AnswerRequest(
            run_id="run-1", question="서보 수량?", context=RunContext(demo_mode="fixed_llm")
        )
    )
    seen = []
    emit = a.wrap(seen.append)
    emit(
        ToolStarted(
            run_id="run-1", call_id="c1", tool="where_used", inputs={"part": "2000-0025-0002"}
        )
    )
    emit(
        ToolFinished(
            run_id="run-1",
            call_id="c1",
            tool="where_used",
            outputs={"revision": "6b2c5a9"},
            elapsed_ms=5,
            summary="경로 1개",
        )
    )
    emit(StepNote(run_id="run-1", step="출력 검사", detail="passed"))
    got = rows(a.path)
    assert [r["event"] for r in got] == ["run_started", "tool_started", "tool_finished", "step"]
    assert got[0]["actor"] == {"role": "설계변경 엔지니어", "authenticated": False}
    assert got[0]["lineage"]["demo_mode"] == "fixed_llm" and got[2]["revision"] == "6b2c5a9"
    assert len(seen) == 3 and a.ok  # 화면 콜백도 그대로 받는다


def test_a02_failed_tool_is_recorded_as_failure(tmp_path):
    a = RunAudit("run-2", tmp_path)
    a.record(
        ToolFailed(
            run_id="run-2", call_id="c1", tool="search_docs", error="timeout", elapsed_ms=30000
        )
    )
    a.record(
        ToolFailed(
            run_id="run-2",
            call_id="c2",
            tool="find_part",
            error="없는 품번",
            elapsed_ms=3,
            kind="validation",
        )
    )
    got = rows(a.path)
    assert [r["result_status"] for r in got] == ["failed", "failed"]
    assert [r["error_kind"] for r in got] == ["transport", "validation"]


def test_a03_parallel_writes_keep_lines_intact(tmp_path):
    a = RunAudit("run-3", tmp_path)

    def work(n):
        for i in range(50):
            a.write_event("step", step=f"agent-{n}", detail="x" * 200, i=i)

    threads = [threading.Thread(target=work, args=(n,)) for n in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    got = rows(a.path)  # 줄이 섞였으면 json 해석에서 실패한다
    assert len(got) == 150 and len({r["event_id"] for r in got}) == 150


def test_a04_secrets_are_not_written(tmp_path):
    a = RunAudit("../../etc/run-4", tmp_path)  # 경로 조작도 막는다
    assert a.path.parent == tmp_path
    a.record(
        ToolFailed(
            run_id="x",
            call_id="c",
            tool="search_docs",
            elapsed_ms=1,
            error="Authorization: Bearer pa-abcdefghijklmnopqrstu api_key=sk-ant-123456789",
        )
    )
    text = a.path.read_text(encoding="utf-8")
    assert "pa-abcdefghijklmnopqrstu" not in text and "sk-ant-123456789" not in text
    assert "[비공개]" in redact("LANGFUSE_SECRET_KEY=sk-lf-abcdef123")


def test_a05_write_failure_is_reported_not_raised(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("")
    a = RunAudit("run-5", blocker)  # 디렉터리 자리에 파일이 있어 쓸 수 없다
    a.write_event("step", step="x", ts_check=datetime.now())
    assert a.ok is False and a.error


def test_optional_doc_search_failure_is_not_zero_documents():
    """단종 질문의 정비 문서 검색이 실패해도 계산은 끝까지 하고, '문서 없음'이 아니라 '조회 실패'로 남긴다."""
    from mfg_bom_agent.workflows.gateway import ToolCallError
    from mfg_bom_agent.workflows.plan import QuestionPlan
    from mfg_bom_agent.workflows.skills import run_skill

    class Gw:
        def call(self, tool, **kw):
            if tool == "search_docs":
                raise ToolCallError(tool, "timeout")
            return {
                "where_used": {"sku": "P", "lines": [], "revision": "r"},
                "bom_explode": {"items": [{"required_each": "4", "formula": "4"}], "revision": "r"},
                "supply_risk": {"alternates": [], "parts": [{"suppliers": ["s"]}], "revision": "r"},
                "cost_rollup": {"total": "10.00", "formula": "f", "revision": "r", "as_of": None},
            }[tool]

    out = run_skill(
        Gw(),
        QuestionPlan(intent="discontinue", part_terms=["P"], units=1),
        RunContext(),
        [{"sku": "P", "name": "servo"}],
    )
    assert out.facts["maintenance_docs"] == "조회 실패"
    assert any("조회 실패" in a for a in out.assumptions) and out.calculations
