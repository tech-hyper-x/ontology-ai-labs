"""비교 실행 방식: RAG · LLM 단독 (Part 2 Ch8 평가, docs/UI_DESIGN.md 2.5).

같은 질문을 지식 그래프 + 도구 에이전트와 비교하기 위한 기준선이다.
- rag      : 문서 조각 검색(search_docs, BOM 표 텍스트 포함)만 쓰고, 계산은 LLM 이 직접 한다
- llm_only : 데이터 없이 질문만 준다

두 방식 모두 계산 도구가 없으므로 출력 검사는 "미실행"이다. 그래프 경로 · 계산 결과 구역은
"미사용"으로 비워 두고, 빈칸을 채우려고 근거를 만들지 않는다.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from mfg_bom_agent.contracts.answer import DocEvidence
from mfg_bom_agent.workflows.gateway import ToolGateway
from mfg_bom_agent.workflows.llm import chat_model


class FreeAnswer(BaseModel):
    conclusion: str = Field(description="한국어 답변 2~5문장. 수량 · 금액을 구했다면 숫자로 쓴다")
    summary: str = Field(
        "",
        description="비교표용 한 줄 요약 25자 안팎 (예: 모터 부품비 $3,869.10 증가, 단가 · 수량이 없어 계산하지 못함)",
    )


class SearchQuery(BaseModel):
    query_en: str = Field(
        description="질문을 원천 문서(영어) 검색용 키워드로 바꾼 것. 품번은 그대로"
    )


RAG_SYSTEM = """너는 제조 BOM 질문에 답하는 도우미다. 아래 검색된 문서 조각만 근거로 답한다.
BOM 표 조각의 열: assembly | short name | part # | cost pp(팩 또는 개당 USD) | # req in assy | assembly multiplier.
계산이 필요하면 직접 계산해서 결과 숫자를 쓴다. 근거가 부족하면 부족하다고 쓴다."""

LLM_ONLY_SYSTEM = """너는 제조 BOM 질문에 답하는 도우미다. NASA JPL Open Source Rover 에 대해 아는 범위에서 답한다.
수량 · 금액을 물으면 추정이라도 숫자로 답하고, 근거가 없으면 추정이라고 밝힌다."""


def rag_answer(question: str, gw: ToolGateway) -> tuple[str, list[DocEvidence], str]:
    q = (
        chat_model("plan")
        .with_structured_output(SearchQuery)
        .invoke([SystemMessage("질문을 검색 키워드로 바꾼다."), HumanMessage(question)])
        .query_en
    )
    res = gw.call("search_docs", query=q, k=8, source="all")
    docs = [
        DocEvidence(
            doc_path=h["path"],
            doc_id=h["doc_id"],
            title=h["title"],
            line=h["line"],
            excerpt=h["excerpt"],
            method="hybrid(RRF)",
        )
        for h in res["hits"]
    ]
    context = "\n\n".join(f"[{h['doc_id']}]\n{h['excerpt']}" for h in res["hits"])
    full = "\n\n".join(f"[{h['doc_id']}] {h['title']}" for h in res["hits"])
    answer = (
        chat_model("report")
        .with_structured_output(FreeAnswer)
        .invoke(
            [
                SystemMessage(RAG_SYSTEM),
                HumanMessage(f"질문: {question}\n\n검색 결과:\n{full}\n\n발췌:\n{context}"),
            ]
        )
    )
    return answer.conclusion, docs, answer.summary


def llm_only_answer(question: str) -> tuple[str, str]:
    answer = (
        chat_model("report")
        .with_structured_output(FreeAnswer)
        .invoke([SystemMessage(LLM_ONLY_SYSTEM), HumanMessage(question)])
    )
    return answer.conclusion, answer.summary
