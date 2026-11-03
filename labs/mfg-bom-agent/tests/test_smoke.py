"""외부 서비스 없이 통과해야 하는 최소 테스트.

Neo4j도 API 키도 없는 CI 첫 단계에서 "패키지가 설치되고 설정이 읽힌다"를 보장한다.
`Settings(_env_file=None)`은 개발자의 .env 파일을 무시하고 환경변수만 읽게 한다.
"""

from mfg_bom_agent.config import Settings


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    s = Settings(_env_file=None)

    assert s.llm_model == "claude-haiku-5-5"
    assert s.llm_effort == "medium"
    assert s.langfuse_enabled is False
    assert s.anthropic_configured is False


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    s = Settings(_env_file=None)

    assert s.langfuse_enabled is True
    assert s.anthropic_configured is True


def test_empty_values_use_defaults(monkeypatch):
    """.env 에 값 없이 남긴 줄(EMBEDDING_DIMENSION=)이 오류 없이 기본값으로 처리되는지 확인한다."""
    monkeypatch.setenv("EMBEDDING_DIMENSION", "")
    monkeypatch.setenv("LLM_MODEL", "")
    s = Settings(_env_file=None)

    assert s.embedding_dimension is None
    assert s.llm_model == "claude-haiku-5-5"
