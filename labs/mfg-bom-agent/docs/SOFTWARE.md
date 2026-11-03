# 소프트웨어 구성 — mfg-bom-agent

제조 실습에 쓰이는 모든 소프트웨어를 **어디에 설치되는지** 기준으로 정리한다. 설치 절차는 [INSTALL.md](../INSTALL.md) 에서 운영체제별 가이드를 따른다.

아래 버전은 **2026-10-25 이 저장소를 실제로 띄워 확인한 값**이다 (검증 환경: macOS 14.6.1 (Apple Silicon, arm64), Docker Desktop 29.9.2).

## 한눈에 보기

```text
내 PC
├── Docker Desktop / OrbStack / Docker Engine   ← 컨테이너 실행
├── uv                                         ← Python 3.12 · 패키지 관리
├── Git
└── 웹 브라우저

Docker 컨테이너 (docker compose 로 실행)
├── mfg-neo4j            Neo4j 5.26 Community          지식 그래프 + 벡터 + 전문 검색
├── mfg-mcp              실습 코드 (Python 3.12)        업무 도구를 MCP 로 노출
├── mfg-app              실습 코드 (Python 3.12)        Streamlit 화면 + LangGraph
├── mfg-init             실습 코드 (일회성)              제약·인덱스 생성, 데이터 적재
└── Langfuse 묶음          web · worker · postgres · clickhouse · redis · minio

외부 서비스 (인터넷)
└── Anthropic API          claude-haiku-5-5
```

---

## 1. 내 PC 에 설치하는 소프트웨어

수강생이 직접 설치하는 것은 이것뿐이다. Python 은 설치하지 않는다 (uv 가 프로젝트 전용으로 내려받는다).

| 소프트웨어 | 검증 버전 | 최소 요구 | 용도 | 역할 설명 | 설치 방법 | 비용·라이선스 |
|---|---|---|---|---|---|---|
| Docker Desktop (Windows · macOS) | 29.9.2 | Compose v2 포함 버전 | 컨테이너 실행 | Neo4j · Langfuse · 실습 앱을 각각 독립된 "상자(컨테이너)"에 담아 실행한다. 덕분에 DB 나 서버를 PC 에 직접 설치하지 않고, 모든 수강생이 같은 버전을 같은 설정으로 쓴다. Windows · macOS 에서는 Linux 가상 머신을 대신 관리해 준다 | Windows: winget · macOS: `brew install --cask docker` | 개인·교육·소규모 사업자(직원 250명 미만이고 연매출 1천만 달러 미만) 무료, 그 외 기업은 유료 구독 필요 — 회사 PC 라면 사내 정책 확인 |
| OrbStack (macOS, Docker Desktop 대안) | — | | 컨테이너 실행 | Docker Desktop 과 같은 역할을 하는 macOS 전용 앱. 더 가볍고 빨라 메모리가 넉넉하지 않은 Mac 에 유리하다. 둘 중 하나만 설치한다 | `brew install --cask orbstack` | 개인 비상업 무료, 업무용은 유료 라이선스 |
| Docker Engine + Compose 플러그인 (Linux) | — | Compose v2 | 컨테이너 실행 | Linux 에서는 가상 머신 없이 컨테이너를 바로 실행하는 Docker 본체만 설치하면 된다. Docker Desktop 의 Linux 판 역할 | Docker 공식 apt 저장소 | 무료 (Apache 2.0) |
| Docker Compose | v5.6.1 | v2 이상 (`docker compose` 명령) | 서비스 묶음 실행 | 이 실습은 컨테이너 9개가 서로 연결되어 동작한다. Compose 는 `compose.yaml` 에 적힌 순서·연결·포트·설정대로 이들을 한 명령(`docker compose up`)으로 띄우고 내린다 | Docker 에 포함 | 무료 |
| Docker Buildx | v0.38.1 | | 이미지 빌드 | 실습 코드(MCP 서버 · Streamlit 앱)를 컨테이너 이미지로 만드는 빌드 도구. `docker compose build` 가 내부에서 사용한다. 개발 모드(앱을 로컬에서 실행)에서는 쓰지 않는다 | Docker 에 포함 | 무료 |
| uv | 0.13.5 | 0.13 이상 권장 | Python 설치·가상환경·패키지 관리 | 실습에 필요한 Python 3.12 를 내려받고, 프로젝트 전용 가상환경(`.venv`)을 만들고, `uv.lock` 에 적힌 정확한 버전으로 라이브러리를 설치한다. PC 에 Python 이 없거나 다른 버전이 있어도 영향을 받지 않는다 | 공식 설치 스크립트 (macOS 는 `brew install uv` 금지 — macOS 가이드 참고) | 무료 (MIT / Apache 2.0) |
| Git | 2.56.0 | 2.x | 저장소 내려받기 | 강의 저장소를 내려받고(`git clone`), 강의 중 코드가 갱신되면 최신으로 받아온다. zip 으로 받는 경우에는 없어도 된다 | macOS 기본 · Ubuntu `apt` | 무료 (GPLv2) |
| WSL2 + Ubuntu 24.04 (Windows 만) | — | Windows 10 21H2 / 11 | Linux 실행 환경 | Windows 안에서 진짜 Linux(Ubuntu)를 실행한다. 실습 명령은 모두 이 Ubuntu 터미널에서 실행하며, Docker Desktop 도 WSL2 위에서 컨테이너를 돌린다. 강의 화면의 명령어를 운영체제와 상관없이 그대로 쓰기 위해서다 | `wsl --install -d Ubuntu-24.04` | 무료 |
| VS Code (선택) | — | | 코드 편집 | 실습 코드와 `.env` 를 열어 보고 수정하는 편집기. 터미널을 여러 개 띄우기도 편하다. Windows 는 WSL 확장을 설치하면 Ubuntu 안의 파일을 바로 연다 | code.visualstudio.com | 무료 |

---

## 2. Docker 컨테이너로 실행되는 소프트웨어

`docker compose up` 이 이미지를 내려받아 실행한다. 직접 설치하지 않는다.

### 2-1. 실습 서비스 (`compose.yaml`)

| 컨테이너 | 이미지 (태그) | 실제 버전 | 역할 | 호스트 포트 | 메모리 (측정) | 라이선스 |
|---|---|---|---|---|---|---|
| `mfg-neo4j` | `neo4j:5.26-community` | 5.26.32 | 지식 그래프 · 벡터 인덱스 · 전문 인덱스 | 7474 (Browser), 7687 (Bolt) | 약 1.5GB | GPLv3 (Community) |
| `mfg-mcp` | 이 저장소에서 빌드 (`docker/mcp.Dockerfile`) | Python 3.12.15, uv 0.13.5 | 업무 도구 MCP 서버 (Streamable HTTP) | 8000 | 약 170MB | 실습 코드 |
| `mfg-app` | 이 저장소에서 빌드 (`docker/app.Dockerfile`) | Python 3.12.15, uv 0.13.5 | Streamlit 화면 + LangGraph | 8501 | 약 80MB (대기 시) | 실습 코드 |
| `mfg-init` | `mfg-mcp` 와 같은 이미지 | — | 제약·인덱스 생성 (실행 후 종료) | 없음 | — | 실습 코드 |

실습 이미지의 베이스는 `python:3.12-slim` 이고, uv 는 `ghcr.io/astral-sh/uv:0.13.5` 이미지에서 복사한다. 이미지 크기는 약 1.3GB 다 (pyarrow · scipy · pandas 가 절반 이상 — streamlit 과 neo4j-graphrag 가 의존).

### 2-2. Langfuse 묶음 (`compose.langfuse.yaml`)

트레이싱 화면을 위한 6개 컨테이너다. 실습 코드는 `langfuse-web` 에만 접속한다.

| 컨테이너 | 이미지 (태그) | 실제 버전 | 역할 | 호스트 포트 | 메모리 (측정) | 라이선스 |
|---|---|---|---|---|---|---|
| `mfg-langfuse-web` | `docker.langfuse.com/langfuse/langfuse:4` | 4.70.0 | 화면 + 트레이스 수집 API | 3000 | 약 690MB | MIT (코어) |
| `mfg-langfuse-worker` | `docker.langfuse.com/langfuse/langfuse-worker:4` | 4.70.0 | 트레이스를 ClickHouse 에 적재 | 없음 | 약 680MB | MIT (코어) |
| `mfg-clickhouse` | `clickhouse/clickhouse-server:25.12` | 25.12.11.4 | 트레이스 저장 (분석용 컬럼 DB) | 없음 | 약 1.5GB | Apache 2.0 |
| `mfg-postgres` | `postgres:17` | 17.11 | 사용자 · 프로젝트 · 설정 | 없음 | 약 130MB | PostgreSQL License |
| `mfg-redis` | `redis:7` | 7.4.11 | web ↔ worker 작업 큐 | 없음 | 약 30MB | RSALv2 / SSPLv1 (7.4 부터) |
| `mfg-minio` | `cgr.dev/chainguard/minio:latest` | RELEASE.2026-10-23 | 이벤트 · 미디어 저장 (S3 호환) | 9090 | 약 100MB | AGPLv3 |

> 라이선스는 이 강의처럼 **로컬 PC 에서 교육용으로 실행**하는 데는 문제가 없다. 실습 구성을 회사 서버에 그대로 올려 서비스할 계획이라면 Neo4j(GPLv3), Redis(RSAL/SSPL), MinIO(AGPLv3) 조건을 사내 법무와 검토한다.

### 2-3. 자원 사용량 (측정)

| 항목 | 값 | 비고 |
|---|---|---|
| 메모리 (전체 대기 상태) | 약 4.8GB | ClickHouse 1.5GB + Neo4j 1.5GB + Langfuse web·worker 1.4GB + 나머지 |
| 메모리 (Langfuse 없이) | 약 1.7GB | Neo4j + mcp + app |
| 이미지 디스크 | 약 7.8GB | Langfuse 묶음 5.5GB, Neo4j 1.0GB, 실습 이미지 1.3GB |
| 데이터 볼륨 (초기) | 약 0.7GB | Neo4j 540MB 가 대부분. 실습 데이터 적재 후 늘어난다 |

Docker 에 메모리 8GB 이상, 디스크 여유 20GB 이상을 권장하는 근거다.

---

## 3. Python 런타임과 패키지

| 항목 | 값 |
|---|---|
| Python | 3.12 (`.python-version`). 검증 버전 3.12.15 — uv 가 내려받는다 |
| 패키지 목록 | `pyproject.toml` |
| 버전 고정 | `uv.lock` — 의존성 포함 139개 패키지의 정확한 버전 |
| 가상환경 | 로컬: 프로젝트의 `.venv` / 컨테이너: `/opt/venv` |

실습 코드가 직접 쓰는 패키지 (버전은 `uv.lock` 기준):

| 패키지 | 버전 | 용도 |
|---|---|---|
| `anthropic` | 1.17.0 | Claude API 공식 SDK |
| `langchain-anthropic` | 1.7.6 | LangGraph 에서 Claude 를 쓰기 위한 연결 |
| `langchain-core` | 1.7.0 | LangGraph 의 메시지·도구 기본 타입 |
| `langgraph` | 1.2.17 | 에이전트 워크플로(노드·상태) 오케스트레이션 |
| `neo4j` | 6.4.1 | Neo4j 공식 Python 드라이버 (Bolt) |
| `neo4j-graphrag` | 1.22.0 | Neo4j 벡터·전문·Hybrid 검색 도우미 |
| `fastmcp` | 4.1.3 | 업무 함수를 MCP 도구로 노출하는 서버 |
| `mcp` | 2.3.0 | MCP 프로토콜 기본 라이브러리 (fastmcp 가 사용) |
| `langfuse` | 5.0.4 | LLM 호출·도구 호출 트레이싱 |
| `streamlit` | 1.66.1 | 실습 화면 |
| `pydantic` | 2.14.1 | 도구 입력·출력 데이터 계약 |
| `pydantic-settings` | 2.16.1 | .env 설정 읽기 |
| `httpx` | 0.28.1 | HTTP 호출 (환경 점검) |
| `python-dotenv` | 1.2.4 | .env 파일 읽기 |
| `pytest` | 9.1.1 | 테스트 (개발용, 이미지에는 미포함) |
| `ruff` | 0.17.2 | 코드 검사 (개발용, 이미지에는 미포함) |

전체 목록과 의존 관계는 프로젝트 폴더에서 확인한다.

```bash
uv tree --depth 1
```

```bash
uv pip list
```

---

## 4. 외부 서비스

| 서비스 | 사용 값 | 용도 | 비용 |
|---|---|---|---|
| Anthropic API | `claude-haiku-5-5` (`LLM_MODEL`) | 질문 해석 · 도구 선택 · 답변 작성 | 입력 $0.10 / 출력 $0.50 (100만 토큰당, 프롬프트 10만 토큰 이하). 환경 점검(Models API 조회)은 비용 없음 |
| 임베딩 API | 미정 (`EMBEDDING_PROVIDER`) | 문서 청크 벡터화 | 공급자 확정 후 추가 |

Langfuse 는 설치형이라 외부로 트레이스를 보내지 않는다.

---

## 5. 버전 관리 원칙

| 대상 | 고정 방법 | 바꾸는 방법 |
|---|---|---|
| Python 패키지 | `uv.lock` (`uv sync --locked` 로 설치) | `uv lock --upgrade-package <이름>` → 테스트 → 커밋 |
| Python 버전 | `.python-version` | 파일 수정 후 `uv sync` |
| uv (컨테이너) | Dockerfile 의 `ghcr.io/astral-sh/uv:0.13.5` | 태그 수정 후 이미지 재빌드 |
| 인프라 이미지 | compose 파일의 태그 (`neo4j:5.26-community`, `langfuse:4`, `postgres:17` …) | 태그 수정 후 `docker compose pull` |

`langfuse:4`, `redis:7`, `postgres:17` 처럼 메이저 버전 태그는 `docker compose pull` 할 때 같은 메이저의 최신 패치로 바뀐다. 녹화·배포 시점에는 위 "실제 버전" 열의 값으로 태그를 고정하는 것을 권장한다 (`개발환경_정의서.md` 12절).

현재 설치된 버전을 다시 확인하려면:

```bash
docker compose images
```

```bash
docker exec mfg-neo4j neo4j --version
```

Docker 로 이 실습을 켜고 끄고 초기화하는 방법은 [DOCKER.md](DOCKER.md) 를 본다.
