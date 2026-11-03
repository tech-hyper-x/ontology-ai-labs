"""LLM 과 스킬 문서를 불러오는 곳 (Part 2 Ch7).

모델 ID · effort 는 config.py 에서만 읽는다 (정의서 2.1). 구조화 출력은 Pydantic 모델로 받는다.
스킬 문서(skills/*/SKILL.md)는 답변 단계의 시스템 프롬프트에 넣는다.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from langchain_anthropic import ChatAnthropic

from mfg_bom_agent.config import get_settings

SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"


class LLMUnavailable(RuntimeError):
    """API 키가 없거나 데모 모드라서 실제 모델을 쓸 수 없음."""


@lru_cache
def chat_model(purpose: str = "default") -> ChatAnthropic:
    """노드별 모델. 답변 작성(report)만 LLM_MODEL_REPORT 로 바꿀 수 있다 (정의서 2.1)."""
    s = get_settings()
    if not s.anthropic_configured:
        raise LLMUnavailable(
            "ANTHROPIC_API_KEY 가 없습니다 — DEMO_MODE=fixed_llm 으로 실행할 수 있습니다"
        )
    model = s.llm_model_report if purpose == "report" else s.llm_model
    # 질문 구조화(plan)는 짧고 정형적이라 effort 를 낮춘다. 답변 작성은 설정값(medium)을 쓴다.
    effort = "low" if purpose == "plan" else s.llm_effort
    return ChatAnthropic(
        model=model,
        api_key=s.anthropic_api_key.get_secret_value(),
        max_tokens=4096,
        effort=effort,
        timeout=s.request_timeout_seconds,
        max_retries=2,
    )


@lru_cache
def skill_text(name: str) -> str:
    """스킬 문서 본문(앞부분 메타데이터 제외)."""
    text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
    return text.split("---", 2)[-1].strip() if text.startswith("---") else text
