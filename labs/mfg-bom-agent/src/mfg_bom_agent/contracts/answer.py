"""UI ↔ 에이전트 요청 · 응답 계약 (docs/UI_DESIGN.md 3절, Part 2 Ch7).

화면은 자유 텍스트를 파싱하지 않는다. 에이전트가 결론 · 계산 결과 · 그래프 경로 · 문서 근거 ·
출처 · 검증 결과를 이 구조로 돌려주고, 화면은 구조를 그대로 그린다.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

Mode = Literal["kg_tools", "rag", "llm_only"]
DemoMode = Literal["none", "fixed_llm", "canned"]


class RunContext(BaseModel):
    """질문을 실행한 순간의 조건. 답변마다 복사해 보존한다 (사이드바를 바꿔도 이전 답변은 그대로)."""

    role: str = "설계변경 엔지니어"
    revision: str | None = None  # None = 최신 판
    as_of: date = date(2026, 10, 22)  # 가격 관측일 (스냅샷)
    price_date_known: bool = False  # 실제 가격 기준일 — 원천에 없다
    dataset_version: str = "mfg-0.1"
    snapshot: str = "a78f9eb"
    llm_model: str = "claude-haiku-5-5"
    demo_mode: DemoMode = "none"


class ResumeInput(BaseModel):
    """되묻기에 대한 사용자 답. field 는 PendingQuestion.field 와 같다."""

    field: str
    value: str


class AnswerRequest(BaseModel):
    run_id: str
    question: str
    context: RunContext = Field(default_factory=RunContext)
    mode: Mode = "kg_tools"
    resume: ResumeInput | None = None


class CalcResult(BaseModel):
    """계산 결과 한 줄. 화면의 계산 결과 표 한 행이자 출력 검사의 기준값이다."""

    label: str  # 예: "서보 소요 금액 (50대)"
    kind: Literal["requirement", "purchase", "extra_cost", "diff", "quantity", "reference"]
    value: Decimal | None  # None = 미계산 · 미확인
    unit: str  # "USD" · "ea" · "pack"
    tool: str | None = None
    formula: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    revision: str | None = None
    as_of: date | None = None
    source: str = ""
    note: str | None = None


class GraphPath(BaseModel):
    text: str  # "Rover → rocker bogie (×2) → servo 2000-0025-0002"
    tool: str
    revision: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class DocEvidence(BaseModel):
    doc_path: str
    doc_id: str
    title: str
    line: int | None = None
    excerpt: str
    linked_parts: list[str] = Field(default_factory=list)
    confidence: float | None = None
    method: str = ""
    rank: int | None = None  # 하이브리드 결합 순위
    ranks: dict[str, int] = Field(default_factory=dict)  # 검색별 순위 {"bm25": 5, "vector": 3}


class KeyFact(BaseModel):
    """결과 카드 한 장 (계산값이 아닌 판단 결과). 예: label="대체 부품", value="등록 없음" """

    label: str
    value: str


class DocNote(BaseModel):
    """답변이 실제로 인용한 문서. 화면은 한국어 요약 → 관련 문장 → 원문 순서로 보여 준다."""

    doc_path: str
    line: int | None = None
    summary_ko: str  # 한국어 한 문장 요약
    quote: str = ""  # 원문에서 그대로 가져온 관련 문장 (검색된 발췌에 없으면 비운다)


class SourceInfo(BaseModel):
    snapshot: str
    revision: str | None
    as_of: date | None
    price_date_known: bool = False
    assumptions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    data_used: list[str] = Field(default_factory=list)  # 이 실행 방식이 쓴 데이터
    tools_available: list[str] = Field(default_factory=list)


class CheckItem(BaseModel):
    target: str
    cited_value: str
    item_ok: bool
    value_ok: bool
    unit_ok: bool
    condition_ok: bool
    direction_ok: bool = True  # 차이 값의 증가 · 감소 방향 (차이가 아닌 값은 항상 True)

    @property
    def passed(self) -> bool:
        return (
            self.item_ok
            and self.value_ok
            and self.unit_ok
            and self.condition_ok
            and self.direction_ok
        )


# 검사 문제 코드. 화면 문구와 분리한 기계용 이름이다 (평가 · 로그에서 집계한다)
IssueCode = Literal[
    "missing_reference",  # 계산 결과가 있는데 답변이 인용한 값이 없음
    "wrong_value",  # 문장의 수량이 같은 항목의 도구 값과 다름
    "wrong_unit",
    "wrong_condition",  # 생산 대수 · 판이 이번 요청과 다름
    "wrong_direction",  # 차이 값의 증가 · 감소를 반대로 쓰거나 방향 없이 씀
]


class Issue(BaseModel):
    """인용 항목(CheckItem) 밖, 답변 문장에서 찾은 문제 하나."""

    code: IssueCode
    target: str  # 문제가 된 표현 (예: "1대당 2개")
    detail: str = ""


VERIFY_VERSION = "2"  # 검사 규칙 버전. 비어 있으면 이전 규칙으로 검사한 결과다


class Verification(BaseModel):
    """출력 검사. 결론이 인용한 수량 · 금액이 계산 결과와 항목 · 값 · 단위 · 조건 모두 맞는지 본다."""

    status: Literal["passed", "failed", "not_run"] = "not_run"
    checks: list[CheckItem] = Field(default_factory=list)
    unverified_numbers: list[str] = Field(
        default_factory=list
    )  # 결론에 있지만 계산 결과에 없는 금액
    issues: list[Issue] = Field(default_factory=list)  # 문장 속 수량 · 대수 · 방향 문제
    reason: str = ""
    version: str = ""  # 검사 규칙 버전 (빈 값 = 이전 버전 결과)
    rewrites: int = 0  # 검사 실패로 답변을 다시 쓴 횟수
    withheld: bool = False  # 다시 써도 실패해 LLM 문장을 내리고 검증된 계산 결과만 보여 줌

    @property
    def summary(self) -> dict[str, int]:
        passed = sum(c.passed for c in self.checks)
        return {
            "passed": passed,
            "failed": len(self.checks) - passed + len(self.unverified_numbers) + len(self.issues),
            "not_run": 1 if self.status == "not_run" else 0,
        }


class TraceInfo(BaseModel):
    trace_id: str
    url: str | None = None
    session_id: str | None = None


class PendingQuestion(BaseModel):
    kind: Literal["missing_value", "choose_candidate"]
    prompt: str
    field: str
    candidates: list[dict[str, str]] | None = None


class ErrorInfo(BaseModel):
    kind: Literal["tool_error", "llm_error", "timeout", "cancelled", "refusal", "internal"]
    message: str


class AnswerResponse(BaseModel):
    run_id: str
    status: Literal["completed", "needs_input", "failed"]
    mode: Mode
    intent: str | None = None
    # 답변은 읽는 순서대로 나눠 담는다: 첫 문장 답 → 확인된 내용 → 추가로 확인할 사항 → 가정 · 기준
    headline: str = ""
    summary: str = ""  # 비교표에 쓰는 짧은 요약 (예: "모터 부품비 $3,869.10 증가")
    highlights: list[str] = Field(
        default_factory=list
    )  # 첫 문장에서 강조할 핵심 키워드 (예: "모터 부품비")
    subject: str = ""  # 계산 대상 (예: "모터 · 5203-2402-0027")
    basis: str = ""  # 계산 기준 (예: "로버 100대")
    findings: list[str] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    key_facts: list[KeyFact] = Field(default_factory=list)
    doc_notes: list[DocNote] = Field(default_factory=list)
    cited_labels: list[str] = Field(
        default_factory=list
    )  # 답변이 인용한 계산 결과 — 결과 카드로 쓴다
    conclusion: str = ""  # 위 구역을 이어 붙인 전체 답변 (평가 · 기록용)
    calculations: list[CalcResult] = Field(default_factory=list)
    graph_paths: list[GraphPath] = Field(default_factory=list)
    documents: list[DocEvidence] = Field(default_factory=list)
    sources: SourceInfo | None = None
    verification: Verification = Field(default_factory=Verification)
    trace: TraceInfo | None = None
    context: RunContext
    pending_question: PendingQuestion | None = None
    error: ErrorInfo | None = None
    tool_calls: int = 0
    audit_path: str | None = None  # 로컬 감사 기록 파일 (outputs/runs/<run_id>.jsonl)
    audit_ok: bool | None = None  # False = 감사 기록 쓰기 실패 (업무 결과와 별개)
