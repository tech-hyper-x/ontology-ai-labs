"""실행 설정을 한곳에서 읽는다.

모든 모듈은 환경변수나 .env 파일을 직접 읽지 않고 `get_settings()`를 통해 설정을 가져온다.
그래야 수강생이 "어떤 값을 어디서 바꾸면 되는지"를 이 파일 하나로 파악할 수 있다.

값의 의미와 기본값은 .env.example, 설계 근거는 개발환경_정의서 8절을 본다.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경변수 → 타입이 있는 설정 객체.

    필드 이름이 곧 환경변수 이름이다 (대소문자 무관). 예: `neo4j_uri` ← `NEO4J_URI`.
    비밀값은 SecretStr로 감싸서 로그나 화면에 실수로 찍히지 않게 한다.
    """

    # env_ignore_empty: .env 에 `EMBEDDING_DIMENSION=` 처럼 값 없이 남긴 줄은 "설정 안 함"으로 보고 기본값을 쓴다.
    #   이게 없으면 빈 문자열을 숫자로 바꾸려다 실패한다.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_ignore_empty=True, extra="ignore"
    )

    app_env: Literal["development", "classroom"] = "development"

    # Neo4j — 로컬 실행은 localhost, 컨테이너 실행은 compose가 서비스 이름(neo4j)으로 덮어쓴다
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("")

    # MCP — host/port는 서버가 바인딩할 주소, url은 앱이 접속할 주소
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000
    mcp_url: str = "http://localhost:8000/mcp"
    # 에이전트가 MCP 도구를 부르는 방식. http = mcp_url 서버로 접속(컨테이너 기본),
    #   inprocess = 같은 프로세스의 MCP 서버 객체에 메모리로 연결(로컬 · 테스트). 둘 다 MCP 프로토콜을 쓴다.
    mcp_transport: Literal["http", "inprocess"] = "inprocess"

    # 화면 데모 모드 (docs/UI_DESIGN.md 7절). none = 실제 실행,
    #   fixed_llm = LLM 응답만 규칙 기반으로 고정하고 도구는 실제 실행, canned = 저장된 화면 예시 표시
    demo_mode: Literal["none", "fixed_llm", "canned"] = "none"

    # LLM — 기본은 모든 노드가 Haiku 5.5. 리포트 생성 노드만 별도 모델로 올릴 수 있다 (정의서 2.1)
    anthropic_api_key: SecretStr = SecretStr("")
    llm_model: str = "claude-haiku-5-5"
    llm_model_report: str = "claude-haiku-5-5"
    llm_effort: Literal["low", "medium", "high"] = "medium"

    # Langfuse — 설치형(compose.langfuse.yaml)이 기본. 키가 비어 있으면 트레이싱을 끄고 JSON 로그만 남긴다 (정의서 11.1)
    langfuse_public_key: SecretStr = SecretStr("")
    langfuse_secret_key: SecretStr = SecretStr("")
    langfuse_host: str = "http://localhost:3000"
    # 화면에 띄우는 트레이스 링크 주소. 컨테이너 안의 langfuse_host(http://langfuse-web:3000)는 사용자 브라우저에서 열리지 않는다
    langfuse_public_url: str = "http://localhost:3000"

    # 임베딩 — Anthropic은 임베딩 API가 없어 별도 공급자를 쓴다. 공급자·차원은 정의서 6.3 확정 후 채운다
    embedding_provider: str = ""
    embedding_model: str = ""
    embedding_api_key: SecretStr = SecretStr("")
    embedding_dimension: int | None = None

    # 데이터 버전과 실행 상한 — 결과 재현과 비용 통제를 위해 설정으로 뺀다
    dataset_version: str = "mfg-0.1"
    max_concurrency: int = Field(default=3, ge=1)
    max_tool_calls: int = Field(default=20, ge=1)
    request_timeout_seconds: int = Field(default=120, ge=1)

    @property
    def langfuse_enabled(self) -> bool:
        """공개키·비밀키가 둘 다 있을 때만 트레이싱을 켠다."""
        return bool(
            self.langfuse_public_key.get_secret_value()
            and self.langfuse_secret_key.get_secret_value()
        )

    @property
    def anthropic_configured(self) -> bool:
        return bool(self.anthropic_api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    """설정은 프로세스당 한 번만 읽는다. 테스트에서는 `Settings(_env_file=None)`로 직접 만든다."""
    return Settings()
