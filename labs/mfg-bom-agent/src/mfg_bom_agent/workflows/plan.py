"""질문 계획 — 스킬 S1 bom-question-planning (Part 2 Ch7-1 질문별 도구 호출 경로).

LLM 은 질문을 해석해 "유형 + 계산에 필요한 값"을 구조화한다. 도구 호출 순서는 LLM 이 아니라
유형별 스킬(workflows/skills.py)이 정한다. 그래야 같은 유형의 질문이 언제나 같은 경로로 처리된다.

데모 모드(fixed_llm)에서는 LLM 대신 규칙 기반 해석기(rule_plan)를 쓴다.
"""

from __future__ import annotations

import re
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from mfg_bom_agent.workflows.llm import chat_model, skill_text

Intent = Literal[
    "purchase_quantity",
    "cost",
    "price_change",
    "discontinue",
    "revision_change",
    "supply_disruption",
    "symptom",
    "part_info",
    "other",
]


class QuestionPlan(BaseModel):
    """질문을 구조화한 결과. 값이 질문에 없으면 null 로 둔다 (추측하지 않는다)."""

    intent: Intent = Field(description="질문 유형 하나")
    part_terms: list[str] = Field(
        default_factory=list,
        description="질문에 나온 부품 이름 · 약칭 · 품번 (원문 그대로, 예: '서보', '2000-0025-0002')",
    )
    units: int | None = Field(None, description="생산 대수 (예: 50대 → 50)")
    percent: str | None = Field(
        None, description="단가 변경률 % (예: 15% 인상 → '15', 10% 인하 → '-10')"
    )
    change_ref: str | None = Field(
        None, description="ECN ID · 커밋 ID · 날짜(YYYY-MM 또는 YYYY-MM-DD)"
    )
    supplier: str | None = Field(
        None, description="공급사 이름 또는 도메인 (예: goBILDA → 'gobilda.com')"
    )
    pack_filter: int | None = Field(
        None, description="'2-pack 부품'처럼 포장 크기로 고른 경우 그 크기"
    )
    search_query_en: str | None = Field(
        None, description="증상 · 정비 질문이면 원천 문서 검색용 영어 키워드"
    )
    reasoning: str = Field("", description="유형을 고른 이유 한 줄")


PLAN_SYSTEM = """너는 제조 BOM 변경 영향 분석 에이전트의 질문 계획 단계다.
질문을 해석해 유형과 계산에 필요한 값만 구조화한다. 계산하거나 답하지 않는다.

{skill}

유형 정의:
- purchase_quantity: 몇 개 · 몇 팩을 사야 하는지 (구매 수량)
- cost: 원가 · 어셈블리별 원가 (단가 변경 없음)
- price_change: 단가가 몇 % 오르거나 내릴 때 원가 차이
- discontinue: 부품 단종 · 공급 종료 가정 시 소요량 · 금액 · 대체 후보 (특정 부품)
- revision_change: BOM 판 · ECN · 설계 변경 전후 차이
- supply_disruption: 특정 공급사가 공급을 못 할 때 (공급사 단위)
- symptom: 고장 증상 · 정비 · 수리, 또는 정비 문서 · 이슈(문서 근거)를 찾는 질문 (예: 휠이 안 돌아요, ~를 다룬 이슈는?)
- part_info: 부품의 사용처 · 공급사 · 대체품 · 교체 이력(무엇을 대체했나) 같은 정보
- other: 위에 없는 질문

판단 규칙
- 질문에 ECN · 판 · 리비전 · 커밋 · "전후" · 날짜(2024-06)가 있으면 revision_change 다 (원가 차이를 물어도). change_ref 에 날짜 · ID 를 넣는다.
- "어떤 문서/이슈" 를 찾는 질문은 단종 · 고장 단어가 있어도 symptom 이다. search_query_en 에 품번과 영어 키워드를 넣는다.
- "로버" · "기계 BOM" 은 부품이 아니다. part_terms 에는 실제 부품 이름 · 품번만 넣는다."""


def llm_plan(question: str) -> QuestionPlan:
    model = chat_model("plan").with_structured_output(QuestionPlan)
    return model.invoke(
        [
            SystemMessage(PLAN_SYSTEM.format(skill=skill_text("bom-question-planning"))),
            HumanMessage(question),
        ]
    )


# ─── 규칙 기반 해석기 (DEMO_MODE=fixed_llm) ─────────────────────────────
_UNITS = re.compile(r"(\d+)\s*대")
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_SKU = re.compile(r"\b\d{4}-\d{4}-\d{4}\b")
_PACK = re.compile(r"(\d+)\s*-?\s*pack", re.IGNORECASE)
_KNOWN = ["서보블록", "서보", "모터", "휠", "바퀴", "베어링", "스페이서", "servo", "motor", "wheel"]


def rule_plan(question: str) -> QuestionPlan:
    """LLM 없이 질문을 해석하는 고정 규칙. 실습 예시 질문 7개를 처리할 수 있는 수준이다."""
    q = question
    units = int(m.group(1)) if (m := _UNITS.search(q)) else None
    pct = m.group(1) if (m := _PCT.search(q)) else None
    if pct and re.search(r"인하|내리|감소", q):
        pct = f"-{pct}"
    parts = _SKU.findall(q) or [k for k in _KNOWN if k in q][:1]
    pack = int(m.group(1)) if (m := _PACK.search(q)) else None
    change = m.group(0) if (m := re.search(r"\b[0-9a-f]{7}\b|\d{4}-\d{2}(?:-\d{2})?", q)) else None
    if re.search(r"안 돌|돌지 않|고장|증상|수리|점검", q):
        intent, query = (
            "symptom",
            "corner wheels will not turn servo gear" if "코너" in q else "servo gear failure",
        )
        return QuestionPlan(
            intent=intent, part_terms=[], units=units, search_query_en=query, reasoning="증상 단어"
        )
    if re.search(r"공급 ?중단|공급이 막|공급 ?불가", q):
        sup = "gobilda.com" if re.search(r"gobilda", q, re.IGNORECASE) else None
        return QuestionPlan(
            intent="supply_disruption", supplier=sup, units=units, reasoning="공급 중단"
        )
    if re.search(r"단종", q):
        return QuestionPlan(intent="discontinue", part_terms=parts, units=units, reasoning="단종")
    if pct and re.search(r"단가|가격|인상|인하", q):
        return QuestionPlan(
            intent="price_change", part_terms=parts, units=units, percent=pct, reasoning="단가 변경"
        )
    if re.search(r"ECN|판|리비전|revision|변경 전후|교체 전후", q, re.IGNORECASE):
        return QuestionPlan(
            intent="revision_change", change_ref=change, units=units, reasoning="판 변경"
        )
    if re.search(r"몇 ?팩|구매 ?수량|사야", q):
        return QuestionPlan(
            intent="purchase_quantity",
            part_terms=parts if not pack else [],
            units=units,
            pack_filter=pack,
            reasoning="구매 수량",
        )
    if re.search(r"원가|비용|금액", q):
        return QuestionPlan(intent="cost", units=units, reasoning="원가")
    if parts:
        return QuestionPlan(intent="part_info", part_terms=parts, reasoning="부품 정보")
    return QuestionPlan(intent="other", reasoning="규칙에 맞는 유형 없음")
