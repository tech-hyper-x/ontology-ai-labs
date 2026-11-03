# mfg-bom-agent — 제조 BOM 변경 영향 분석 에이전트

온톨로지로 만드는 엔터프라이즈 AI 강의의 **제조 실습** 저장소다. NASA JPL Open Source Rover 공개 BOM 을 교육용 PLM·ERP·품질 데이터로 재구성하고, "부품 하나를 바꾸면 어떤 조립품에 영향이 가고 로버 1대 원가가 얼마나 달라지는가"에 근거와 함께 답하는 에이전트를 만든다.

- 바이오 실습은 별도 저장소 `bio-target-agent` (추후 배포)에 있다.
- 설계 기준은 강의 자료의 `개발환경_정의서.md`.
- 현재 상태: **실습 전체 구현 완료.** 데이터 재구성 → 온톨로지 · 그래프 적재 → Hybrid Search → MCP 계산 도구 9종 → LangGraph 에이전트 · 스킬 → Streamlit 화면 → Golden Set 평가.
- 커리큘럼 Clip 별 실습 구간은 **[HANDS_ON.md](HANDS_ON.md)** (코드 안 `[Hands-on P2-ChX-Y]` 주석).

## 스택

Python 3.12 · uv · LangGraph · Neo4j 5.26 Community (그래프 + 벡터 + 전문 검색) · FastMCP · Streamlit · Claude Haiku 5.5 (`claude-haiku-5-5`) · Langfuse (Docker 설치형) · pytest

소프트웨어별 정확한 버전·용도·라이선스·메모리 사용량은 **[docs/SOFTWARE.md](docs/SOFTWARE.md)** 에 정리되어 있다.

컨테이너 구성: `compose.yaml`(neo4j, mcp, app, init) + `compose.langfuse.yaml`(langfuse-web, langfuse-worker, postgres, clickhouse, redis, minio). 두 파일은 `include`로 합쳐져 `docker compose` 한 명령으로 함께 올라간다.

## 설치

**처음 실행한다면 [INSTALL.md](INSTALL.md) 에서 운영체제를 고른 뒤 해당 가이드를 따른다** ([Windows](docs/install/windows.md) · [macOS](docs/install/macos.md) · [Linux](docs/install/linux.md)). 도구 설치부터 `.env` 설정, 컨테이너 기동, 브라우저 확인, 문제 해결까지 단계마다 "성공 화면"과 함께 안내한다.

아래 설정·실행 절은 설치를 마친 뒤 다시 볼 때 쓰는 요약이다.

## 설정

```bash
cp .env.example .env
```

`.env`에서 최소 세 값을 채운다: `NEO4J_PASSWORD`(임의 문자열), `ANTHROPIC_API_KEY`, `LANGFUSE_INIT_USER_PASSWORD`(Langfuse 화면 로그인용). `.env`는 커밋하지 않는다.

`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`는 예시값 그대로 써도 된다. 설치형 Langfuse는 첫 기동 때 이 값으로 프로젝트 키를 자동 생성하므로 화면에서 따로 발급받을 필요가 없다.

## 실행 — 개발 모드 (인프라만 컨테이너, 앱·MCP는 로컬)

```bash
uv sync --all-extras
```

```bash
docker compose up -d neo4j langfuse-web
```

`langfuse-web`을 지정하면 의존하는 postgres·clickhouse·redis·minio·langfuse-worker가 함께 뜬다. 첫 기동은 이미지 다운로드와 DB 마이그레이션으로 2~3분 걸린다.

Langfuse 없이 가볍게 돌리려면 `docker compose up -d neo4j`만 올리고 `.env`의 `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`를 비운다.

그래프 적재 · 온톨로지 검증 · 문서 연결 · 검색 색인을 한 번에 실행한다 (`data/processed` 는 저장소에 들어 있다).

```bash
uv run python scripts/init_data.py
```

```bash
uv run python scripts/check_env.py
```

화면을 띄운다. 에이전트는 기본값(`MCP_TRANSPORT=inprocess`)으로 같은 프로세스의 MCP 서버 객체에 연결하므로 MCP 서버를 따로 띄우지 않아도 된다.

```bash
uv run streamlit run src/mfg_bom_agent/ui.py
```

MCP 서버를 HTTP 로 따로 띄워 확인하려면 (`.env` 에 `MCP_TRANSPORT=http`):

```bash
uv run python -m mfg_bom_agent.mcp_server
```

API 키 없이 화면만 확인하려면 `DEMO_MODE=fixed_llm`(LLM 응답만 규칙 기반으로 고정, 도구는 실제 실행) 또는 `DEMO_MODE=canned`(저장된 화면 예시)를 `.env` 에 넣는다.

## 실행 — 컨테이너 모드 (전부 Docker)

`uv.lock`이 있어야 이미지가 빌드된다 (`uv sync`가 만든다).

프로젝트 경로에 한글이 있으면 빌드가 `additional privileges requested` 오류로 멈춘다. 영문 경로(`~/work`)로 옮기거나, 빌드 명령 앞에 `BUILDX_BAKE_ENTITLEMENTS_FS=0` 을 붙인다.

```bash
docker compose build
```

```bash
docker compose up -d neo4j langfuse-web
```

```bash
docker compose --profile init run --rm init
```

```bash
docker compose up -d mcp app
```

## 접속 주소와 포트

| 서비스 | 주소 | `.env` 변수 |
|---|---|---|
| Streamlit 실습 화면 | http://localhost:8501 | `HOST_APP_PORT` |
| Neo4j Browser | http://localhost:7474 (neo4j / `.env` 비밀번호) | `HOST_NEO4J_HTTP_PORT` |
| Neo4j Bolt | bolt://localhost:7687 | `HOST_NEO4J_BOLT_PORT` |
| MCP 엔드포인트 | http://localhost:8000/mcp | `HOST_MCP_PORT` |
| Langfuse | http://localhost:3000 (`LANGFUSE_INIT_USER_EMAIL` / `PASSWORD`) | `HOST_LANGFUSE_PORT` |
| MinIO (Langfuse 미디어) | http://localhost:9090 | `HOST_MINIO_PORT` |

Neo4j Browser 사용법(접속 · 화면 구성 · 쿼리 실행 · 그래프 보기)은 **[docs/NEO4J_BROWSER.md](docs/NEO4J_BROWSER.md)** 에 캡처와 함께 정리되어 있다.
Langfuse 사용법(트레이스 · 세션 · 점수 · 에러 추적)은 **[docs/LANGFUSE.md](docs/LANGFUSE.md)** 에 정리되어 있다.
Voyage AI 키 발급 · 결제 수단 · 한도 · 재색인은 **[docs/VOYAGE.md](docs/VOYAGE.md)** 에 정리되어 있다.
Docker 명령(켜기 · 끄기 · 로그 · 설정 반영 · 초기화)은 **[docs/DOCKER.md](docs/DOCKER.md)** 에 정리되어 있다.

Langfuse 내부 서비스(postgres, clickhouse, redis, worker)는 호스트 포트를 열지 않는다. 바이오 실습과 동시에 띄워도 포트가 충돌하지 않도록 바이오 쪽 기본 포트는 다르게 잡혀 있다.

## 정리

```bash
docker compose down
```

데이터까지 지우려면 `docker compose down -v` (Neo4j·Langfuse 볼륨 삭제). 자세한 내용은 [docs/DOCKER.md](docs/DOCKER.md).

## Langfuse 데모 트레이스

Langfuse 화면(트레이스 · 세션 · 점수)을 채워 보는 데모. 같은 질문을 LLM 단독과 LangGraph + 계산 도구로 실행해 비교한다.

```bash
uv run python scripts/langfuse_demo.py
```

화면 읽는 법은 [docs/LANGFUSE.md](docs/LANGFUSE.md). Anthropic API 크레딧 없이 화면만 확인하려면 `--mock` 을 붙인다. LLM 답변만 미리 정한 문장으로 바뀌고 도구 호출 · 계산 · 점수는 실제로 실행된다.

```bash
uv run python scripts/langfuse_demo.py --mock
```

## 테스트

```bash
uv run pytest
```

`tests/test_smoke.py` · `tests/test_calc.py` 와 출력 검사 테스트는 Neo4j · API 없이 통과한다(CI 첫 단계). `tests/test_graph.py` · 에이전트 워크플로 테스트는 적재된 Neo4j 가 있을 때만 돌고, 없으면 건너뛴다. 에이전트 테스트는 `DEMO_MODE=fixed_llm` 으로 LLM 없이 돈다.

## 평가 (Golden Set)

```bash
uv run python scripts/run_eval.py
```

45문항(수량 · 원가 · 관계 탐색 · Revision · ECN · 문서 근거)을 지식 그래프 + 도구 · RAG · LLM 단독 세 방식으로 채점한다. 정답은 `scripts/build_golden.py` 가 도구와 독립된 참조 계산(`evaluation/reference.py`)으로 만든다. 결과는 `outputs/eval/<시각>/report.md`.

## 폴더

```
compose.yaml           neo4j · mcp · app · init
compose.langfuse.yaml  Langfuse 설치형 6개 서비스 (compose.yaml 이 include)
INSTALL.md             운영체제 선택 → docs/install/{windows,macos,linux}.md
docs/SOFTWARE.md       소프트웨어 구성·버전·라이선스
docs/NEO4J_BROWSER.md  Neo4j Browser 사용 가이드
docs/LANGFUSE.md       Langfuse 사용 가이드
docs/VOYAGE.md         Voyage AI 임베딩 사용 가이드 (키 · 한도 · 재색인)
docs/DOCKER.md         Docker 사용 가이드 (구성 · 명령 · 초기화 · 문제 해결)
docs/UI_DESIGN.md      Streamlit 실습 화면 설계 (화면 구성 · UI–에이전트 계약 · 세션 상태 · 데모 모드)
docker/                app · mcp 이미지
HANDS_ON.md            커리큘럼 Clip 별 실습 구간 · 실행 순서 · 오류 분석 예시
ontology/schema.yaml   온톨로지 정의 (클래스 · 관계 · 추론 규칙 · CQ 카탈로그) — 의미의 원본
queries/               CQ 15개 Cypher (CQ 하나 = 쿼리 하나 = 테스트 하나)
skills/                에이전트 스킬 문서 6종 (S1~S5 + grounded-answer)
src/mfg_bom_agent/
  config.py            설정 (pydantic-settings)
  foundation/          원천 → 교육용 PLM · ERP · 품질 테이블 (Ch1~3)
  ontology.py          스키마 로드 · 제약 · 검증 쿼리 (Ch3)
  graph/               Neo4j 드라이버 · 적재 · CQ 실행기 (Ch4)
  retrieval/           문서 청크 · 개체 연결 · 임베딩 · Hybrid Search (Ch5)
  tools/               계산 규칙(calc) · 업무 도구 9종 (Ch6)
  mcp_server.py        FastMCP 서버 (상태 2 + 업무 도구 9)
  contracts/           도구 · UI–에이전트 · 이벤트 계약 (Pydantic)
  workflows/           LangGraph 에이전트 · 스킬 실행 · 답변 검증 · 비교 기준선 (Ch7)
  evaluation/          참조 계산 · 채점 (Ch8)
  ui.py · ui_state.py  Streamlit 화면 · 세션 상태 (Ch7)
scripts/build_dataset.py  원천 → data/processed (원천이 있을 때)
scripts/load_graph.py     적재 + 온톨로지 검증
scripts/build_index.py    문서 연결 + 검색 색인
scripts/init_data.py      load_graph + build_index 한 번에 (컨테이너 init)
scripts/build_golden.py   Golden Set 정답 생성
scripts/run_eval.py       세 방식 평가 · 오류 분석
scripts/make_canned.py    화면 예시(canned) 응답 저장
scripts/check_env.py      환경 점검
scripts/langfuse_demo.py  Langfuse 데모 트레이스 (LLM 단독 vs 그래프+도구, --mock 은 크레딧 없이)
data/raw/              원천 (git 제외, SOURCES.md 로 재현)
data/processed/        교육용 테이블 (git 포함)
data/golden/           예시 질문 · Golden Set · 화면 예시
```

## 코드 주석 규칙

이 저장소의 코드는 수강생에게 그대로 공유된다. 강사 설명 없이 파일만 읽어도 역할과 의도가 보이도록 아래 규칙을 지킨다.

| 규칙 | 내용 |
|---|---|
| 모듈 docstring | 첫 줄에 반드시 둔다. 순서: 무엇을 하는지 → 실습 흐름에서의 위치 → 관련 정의서 절 |
| 함수 docstring | 한 줄 요약. 인자·반환은 이름만으로 알기 어려울 때만 설명 |
| 인라인 주석 | "왜"만 쓴다. 코드가 이미 보여주는 "무엇"은 반복하지 않는다 |
| 언어 | 한국어. 기술 용어(Cypher, MCP, Streamable HTTP, Bolt 등)는 영어 그대로 |
| 설계 의도 | LLM이 아닌 도구가 계산하는 이유처럼 강의 메시지와 연결되는 결정은 주석에 남긴다 |
| 다음 단계 | `TODO(제조-구현): ...` 형식. 어디에 무엇을 추가할지 적는다 |
| 금지 | 주석 처리된 코드, 임시 디버그 출력, 작성자 이름·날짜 |

설정 파일(compose.yaml, Dockerfile, .env.example)도 같은 기준으로 주석을 붙인다.

## 다음 단계

1. CI/CD: `uv sync` → `ruff` → `pytest` → `docker compose build`
2. Ch8 오류 분석에서 찾은 도구 공백(공용 부품 · 어셈블리 구성 조회) 보완 — HANDS_ON.md 참고
3. 수강생 배포판: Hands-on 구간 발췌 · 빈칸 처리
