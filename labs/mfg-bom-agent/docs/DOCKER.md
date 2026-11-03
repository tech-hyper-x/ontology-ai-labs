# Docker 사용 가이드 — mfg-bom-agent

이 실습은 Neo4j · Langfuse · 실습 앱을 Docker 컨테이너로 띄운다. 이 문서는 **처음 Docker 를 쓰는 사람도 이 프로젝트를 켜고 끄고, 상태를 보고, 문제를 고칠 수 있도록** 필요한 만큼만 설명한다.

- Docker 설치: [INSTALL.md](../INSTALL.md) 에서 운영체제별 가이드
- 각 컨테이너의 버전 · 메모리 · 라이선스: [SOFTWARE.md](SOFTWARE.md)
- 설계 근거: 강의 자료 `개발환경_정의서.md` 4절(서비스 구성), 11.1절(Langfuse 설치형)

모든 명령은 **프로젝트 폴더 안에서** 실행한다. `docker compose` 는 현재 폴더의 `compose.yaml` 을 읽기 때문이다.

## 목차

1. [먼저 알아 둘 개념 5가지](#1-먼저-알아-둘-개념-5가지)
2. [이 프로젝트의 컨테이너 구성](#2-이-프로젝트의-컨테이너-구성)
3. [두 가지 실행 방식](#3-두-가지-실행-방식)
4. [매일 쓰는 명령](#4-매일-쓰는-명령)
5. [상태 확인과 로그](#5-상태-확인과-로그)
6. [컨테이너 안에서 명령 실행](#6-컨테이너-안에서-명령-실행)
7. [설정(.env)을 바꿨을 때](#7-설정env을-바꿨을-때)
8. [코드를 바꿨을 때 — 이미지 다시 빌드](#8-코드를-바꿨을-때--이미지-다시-빌드)
9. [데이터 보존과 초기화](#9-데이터-보존과-초기화)
10. [자원 사용량과 디스크 정리](#10-자원-사용량과-디스크-정리)
11. [compose 파일 구조 읽기](#11-compose-파일-구조-읽기)
12. [자주 막히는 곳](#12-자주-막히는-곳)
13. [명령 요약](#13-명령-요약)

---

## 1. 먼저 알아 둘 개념 5가지

| 개념 | 한 줄 설명 | 이 프로젝트에서 |
|---|---|---|
| **이미지 (image)** | 프로그램과 실행 환경을 통째로 담은 설치 파일 | `neo4j:5.26-community`, `mfg-bom-agent-mcp` 등 |
| **컨테이너 (container)** | 이미지를 실행한 것. 서로 격리된 작은 컴퓨터 | `mfg-neo4j`, `mfg-mcp` 등 9개 |
| **볼륨 (volume)** | 컨테이너를 지워도 남는 데이터 저장소 | `mfg-bom-agent_neo4j_data` 등 7개 |
| **네트워크 (network)** | 컨테이너끼리 이름으로 서로 찾는 내부 망 | `mfg-bom-agent_default` |
| **Compose** | 여러 컨테이너를 설정 파일 하나로 같이 띄우고 내리는 도구 | `compose.yaml` + `compose.langfuse.yaml` |

비유하면 이미지는 **앱 설치 파일**, 컨테이너는 **실행 중인 앱**, 볼륨은 **앱을 지워도 남는 문서 폴더**다.

---

## 2. 이 프로젝트의 컨테이너 구성

```text
내 브라우저 / 내 터미널 (호스트)
   │  localhost:8501      localhost:7474·7687     localhost:3000
   ▼                       ▼                        ▼
┌──────────── Docker 네트워크: mfg-bom-agent_default ─────────────┐
│                                                                   │
│  mfg-app ──────► mfg-mcp ──────► mfg-neo4j                        │
│  Streamlit       FastMCP          그래프 · 벡터 · 전문 검색          │
│  + LangGraph     업무 도구                                         │
│     │               │                                              │
│     └───────┬───────┘   트레이스                                    │
│             ▼                                                      │
│  mfg-langfuse-web ──► mfg-langfuse-worker                          │
│        │                    │                                      │
│        └── postgres · clickhouse · redis · minio (Langfuse 저장소)  │
│                                                                   │
│  mfg-init (일회성) ──► mfg-neo4j   제약 · 인덱스 생성 후 종료        │
└───────────────────────────────────────────────────────────────────┘
```

| 컨테이너 | 역할 | 이미지 | 호스트 포트 | 정의 파일 |
|---|---|---|---|---|
| `mfg-neo4j` | 지식 그래프 · 벡터 · 전문 검색 | `neo4j:5.26-community` | 7474 (Browser), 7687 (Bolt) | `compose.yaml` |
| `mfg-mcp` | 업무 도구를 MCP 로 노출 | 이 저장소에서 빌드 (`docker/mcp.Dockerfile`) | 8000 | `compose.yaml` |
| `mfg-app` | Streamlit 화면 + LangGraph | 이 저장소에서 빌드 (`docker/app.Dockerfile`) | 8501 | `compose.yaml` |
| `mfg-init` | 제약 · 인덱스 생성, 데이터 적재 (실행 후 종료) | `mfg-mcp` 와 같은 이미지 | 없음 | `compose.yaml` (profile `init`) |
| `mfg-langfuse-web` | Langfuse 화면 + 트레이스 수집 API | `langfuse:4` | 3000 | `compose.langfuse.yaml` |
| `mfg-langfuse-worker` | 트레이스를 ClickHouse 에 저장 | `langfuse-worker:4` | 없음 | `compose.langfuse.yaml` |
| `mfg-postgres` | Langfuse 사용자 · 프로젝트 · 설정 | `postgres:17` | 없음 | `compose.langfuse.yaml` |
| `mfg-clickhouse` | Langfuse 트레이스 저장 | `clickhouse-server:25.12` | 없음 | `compose.langfuse.yaml` |
| `mfg-redis` | Langfuse web ↔ worker 작업 큐 | `redis:7` | 없음 | `compose.langfuse.yaml` |
| `mfg-minio` | Langfuse 이벤트 · 미디어 파일 | `chainguard/minio` | 9090 | `compose.langfuse.yaml` |

> `mfg-postgres` 는 **Langfuse 전용**이다. 실습 데이터를 넣는 곳이 아니다.

### 주소가 두 가지인 이유

같은 서비스라도 **어디서 접속하느냐**에 따라 주소가 다르다.

| 접속하는 쪽 | Neo4j | Langfuse | MCP |
|---|---|---|---|
| 내 PC (브라우저, `uv run`) | `bolt://localhost:7687` | `http://localhost:3000` | `http://localhost:8000/mcp` |
| 다른 컨테이너 안 | `bolt://neo4j:7687` | `http://langfuse-web:3000` | `http://mcp:8000/mcp` |

컨테이너 안에서 `localhost` 는 **그 컨테이너 자신**이다. 그래서 `compose.yaml` 이 `.env` 의 localhost 주소를 서비스 이름 주소로 덮어쓴다 (`environment:` 블록).

---

## 3. 두 가지 실행 방식

| | 개발 모드 | 컨테이너 모드 |
|---|---|---|
| 컨테이너로 띄우는 것 | Neo4j · Langfuse 만 | 전부 |
| MCP · Streamlit | 내 터미널에서 `uv run` | `mfg-mcp`, `mfg-app` 컨테이너 |
| 코드 수정 반영 | 프로그램만 다시 실행 | 이미지 다시 빌드 ([8절](#8-코드를-바꿨을-때--이미지-다시-빌드)) |
| 언제 | **코드를 고치며 실습할 때** | 수강생 배포판처럼 그냥 돌려 볼 때 |

두 방식은 같은 포트(8000, 8501)를 쓰므로 **동시에 쓰지 않는다.** 개발 모드로 바꿀 때는 컨테이너 쪽을 먼저 멈춘다.

```bash
docker compose stop mcp app
```

---

## 4. 매일 쓰는 명령

### 켜기

개발 모드 (인프라만):

```bash
docker compose up -d neo4j langfuse-web
```

컨테이너 모드 (전부):

```bash
docker compose up -d neo4j langfuse-web mcp app
```

- `-d` 는 백그라운드 실행. 터미널을 계속 쓸 수 있다
- `langfuse-web` 을 지정하면 의존하는 worker · postgres · clickhouse · redis · minio 가 함께 뜬다
- 첫 실행은 이미지 다운로드로 3~5분 걸린다. 이후는 수십 초

준비가 끝날 때까지 기다렸다가 돌아오게 하려면 `--wait` 를 붙인다 (healthcheck 가 통과할 때까지 기다린다).

```bash
docker compose up -d --wait neo4j langfuse-web
```

### 그래프 초기화 (처음 한 번, 그리고 데이터 적재 코드가 바뀔 때)

```bash
docker compose --profile init run --rm init
```

`init` 은 평소에 뜨지 않도록 profile 로 분리되어 있다. `--rm` 은 끝나면 컨테이너를 지운다는 뜻이다. 여러 번 실행해도 안전하다. 개발 모드에서는 `uv run python scripts/init_data.py` 로 같은 일을 한다.

### 끄기

```bash
docker compose down
```

컨테이너와 네트워크를 지운다. **볼륨(데이터)은 남는다.** 다음에 `up` 하면 그대로 이어진다.

잠깐 멈추기만 하려면 (컨테이너를 지우지 않음):

```bash
docker compose stop
```

```bash
docker compose start
```

### 하나만 다시 시작

```bash
docker compose restart mcp
```

---

## 5. 상태 확인과 로그

### 상태

```bash
docker compose ps
```

```text
NAME                  STATUS
mfg-app               Up 5 minutes
mfg-clickhouse        Up 2 hours (healthy)
mfg-langfuse-web      Up 5 minutes
mfg-langfuse-worker   Up 5 minutes
mfg-mcp               Up 5 minutes
mfg-minio             Up 2 hours (healthy)
mfg-neo4j             Up 2 hours (healthy)
mfg-postgres          Up 2 hours (healthy)
mfg-redis             Up 2 hours (healthy)
```

| STATUS | 뜻 |
|---|---|
| `Up … (healthy)` | 실행 중이고 상태 점검(healthcheck) 통과 |
| `Up … (health: starting)` | 아직 준비 중. 1~2분 기다린다 |
| `Up … (unhealthy)` | 실행은 되지만 점검 실패. 로그를 본다 |
| `Up …` (괄호 없음) | 실행 중. 이 컨테이너에는 점검이 정의되지 않았다 |
| `Restarting` / `Exited` | 계속 죽고 있거나 멈췄다. 로그를 본다 |

실습 환경 전체 점검은 이 명령 하나로 한다 (Neo4j · Anthropic · MCP · Langfuse):

```bash
uv run python scripts/check_env.py
```

### 로그

전체 최근 로그:

```bash
docker compose logs --tail 50
```

서비스 하나를 실시간으로 따라가기 (`Ctrl + C` 로 빠져나온다):

```bash
docker compose logs -f neo4j
```

최근 5분만:

```bash
docker compose logs --since 5m mcp
```

### 이미지와 버전

```bash
docker compose images
```

---

## 6. 컨테이너 안에서 명령 실행

`docker compose exec <서비스> <명령>` 은 실행 중인 컨테이너 안에서 명령을 실행한다.

Neo4j 에 Cypher 직접 실행 (비밀번호를 묻는다 — `.env` 의 `NEO4J_PASSWORD`):

```bash
docker compose exec neo4j cypher-shell -u neo4j
```

종료는 `:exit`. 한 줄짜리 쿼리는 비밀번호 입력 없이 이렇게도 된다 (컨테이너 안의 `NEO4J_AUTH` 값을 쓴다):

```bash
docker compose exec neo4j sh -c 'cypher-shell -u neo4j -p "${NEO4J_AUTH#neo4j/}" "MATCH (n) RETURN count(n) AS nodes"'
```

MCP 컨테이너 안에서 환경 점검 (컨테이너가 보는 주소 · 키로 확인한다):

```bash
docker compose exec mcp uv run python scripts/check_env.py
```

컨테이너에 쉘로 들어가기 (나올 때는 `exit`):

```bash
docker compose exec mcp sh
```

---

## 7. 설정(.env)을 바꿨을 때

컨테이너는 **시작할 때** `.env` 를 읽는다. 값을 바꿨으면 다시 띄운다.

```bash
docker compose up -d
```

Compose 가 **설정이 바뀐 컨테이너만** 골라 다시 만든다. 데이터베이스처럼 바뀐 게 없는 컨테이너는 그대로 둔다.

```text
Container mfg-langfuse-web  Recreated     ← 설정이 바뀌어 다시 만듦
Container mfg-neo4j         Running       ← 그대로
```

| 바꾼 값 | 다시 만들어지는 컨테이너 | 개발 모드(`uv run`)에서는 |
|---|---|---|
| `ANTHROPIC_API_KEY`, `LLM_*`, `EMBEDDING_*` | mcp, app | 프로그램만 다시 실행 |
| `LANGFUSE_PUBLIC_KEY` · `SECRET_KEY` · `INIT_*` · `ENCRYPTION_KEY` 등 | langfuse-web, langfuse-worker (+ mcp, app) | 같음 (Langfuse 는 항상 컨테이너) |
| `HOST_*_PORT` | 해당 포트를 쓰는 컨테이너 | 같음 |
| `NEO4J_PASSWORD` | neo4j — **단, 비밀번호는 처음 만든 볼륨에 이미 저장돼 있어 바뀌지 않는다** | [9절](#9-데이터-보존과-초기화)의 초기화 필요 |

주의할 값:

- **`NEO4J_PASSWORD`** — Neo4j 는 처음 뜰 때만 비밀번호를 정한다. 나중에 바꾸려면 볼륨을 지우고 다시 띄워야 한다.
- **`LANGFUSE_ENCRYPTION_KEY`** — Langfuse 화면에 저장한 비밀값(LLM 연결 키 등)을 암호화한다. 그런 값을 저장한 뒤에 바꾸면 읽을 수 없게 되므로 **한 번 정하면 바꾸지 않는다.**
- **`LANGFUSE_SALT`** — 프로젝트 API 키 검증에 쓴다. 바꾸면 기존 키가 맞지 않게 된다.

---

## 8. 코드를 바꿨을 때 — 이미지 다시 빌드

컨테이너 모드의 `mcp` · `app` 은 **빌드할 때의 코드**가 이미지 안에 들어 있다. 코드를 고쳤으면 이미지를 다시 만든다.

```bash
docker compose --profile init build
```

```bash
docker compose up -d mcp app
```

- `--profile init` 을 붙이면 `init` 이미지도 함께 다시 만든다
- 패키지 의존성(`pyproject.toml`, `uv.lock`)이 그대로면 설치 단계는 캐시를 써서 빠르다. 패키지를 바꿨으면 먼저 `uv lock` 으로 잠금 파일을 갱신한다
- 개발 모드에서는 빌드할 필요가 없다 — 프로그램만 다시 실행하면 된다

> **프로젝트 경로에 한글이 있으면 빌드가 `additional privileges requested: pass "--allow=fs.read=..."` 오류로 멈춘다.** macOS 가 한글 파일명을 분해된 유니코드로 저장하는데, Docker 빌드 도구가 이 경로를 프로젝트 밖으로 오인하기 때문이다. 영문 경로(`~/work`)로 옮기는 것이 가장 좋고, 당장은 명령 앞에 변수를 붙여 우회한다.
>
> ```bash
> BUILDX_BAKE_ENTITLEMENTS_FS=0 docker compose --profile init build
> ```

인프라 이미지(Neo4j, Langfuse 등)를 같은 태그의 최신 패치로 받으려면:

```bash
docker compose pull
```

녹화 · 배포 직전에는 버전이 바뀌지 않도록 하는 편이 안전하다. 고정 방법은 [SOFTWARE.md 5절](SOFTWARE.md#5-버전-관리-원칙).

---

## 9. 데이터 보존과 초기화

데이터는 **볼륨**에 있다. 볼륨 이름 앞에는 compose 프로젝트 이름(`mfg-bom-agent_`)이 붙어 바이오 실습과 섞이지 않는다.

```bash
docker volume ls --filter name=mfg-bom-agent
```

| 볼륨 | 담긴 것 |
|---|---|
| `mfg-bom-agent_neo4j_data` · `_neo4j_logs` | 지식 그래프, Neo4j 로그 |
| `mfg-bom-agent_langfuse_postgres_data` | Langfuse 계정 · 프로젝트 · 설정 |
| `mfg-bom-agent_langfuse_clickhouse_data` · `_logs` | 트레이스 · 점수 |
| `mfg-bom-agent_langfuse_minio_data` | 트레이스 원본 이벤트 |
| `mfg-bom-agent_langfuse_redis_data` | 작업 큐 |

| 하고 싶은 것 | 명령 | 데이터 |
|---|---|---|
| 끄기 | `docker compose down` | **남는다** |
| 전부 처음 상태로 | `docker compose down -v` | **모두 삭제** (그래프 + Langfuse 트레이스 · 계정) |
| Neo4j 만 처음 상태로 | 아래 두 줄 | Neo4j 만 삭제 |

```bash
docker compose rm -sf neo4j
```

```bash
docker volume rm mfg-bom-agent_neo4j_data
```

그다음 `docker compose up -d neo4j` 와 [init](#그래프-초기화-처음-한-번-그리고-데이터-적재-코드가-바뀔-때)을 다시 한다. Langfuse 는 첫 기동 때 `.env` 의 `LANGFUSE_INIT_*` 로 계정 · 프로젝트 · 키를 다시 만든다.

> `down -v` 와 `volume rm` 은 **되돌릴 수 없다.** 실습 중에는 쓰지 않는다.

---

## 10. 자원 사용량과 디스크 정리

컨테이너별 메모리 · CPU (`Ctrl + C` 로 종료, 한 번만 보려면 `--no-stream`):

```bash
docker stats --no-stream
```

측정값 (대기 상태): 전체 약 4.8GB — ClickHouse 1.5GB, Neo4j 1.5GB, Langfuse web · worker 1.4GB, 나머지. Langfuse 없이 띄우면 약 1.7GB.

**메모리가 부족한 PC** 는 Langfuse 를 빼고 띄운다.

```bash
docker compose up -d neo4j
```

그리고 `.env` 의 `LANGFUSE_PUBLIC_KEY` · `LANGFUSE_SECRET_KEY` 를 비우면 트레이싱만 꺼지고 실습은 그대로 된다. 더 줄이려면 `compose.yaml` 의 `include:` 줄을 주석 처리한다.

디스크 사용량:

```bash
docker system df
```

이 실습의 이미지는 약 7.8GB 다. 다 쓴 뒤 공간을 비우려면 프로젝트 폴더에서 컨테이너 · 볼륨 · 이 프로젝트가 빌드한 이미지를 함께 지운다 (**데이터 삭제**):

```bash
docker compose down -v --rmi local
```

> `docker system prune -a` 는 **이 실습과 상관없는 다른 프로젝트의 이미지까지** 지운다. 무엇이 지워지는지 확인하고 쓴다.

---

## 11. compose 파일 구조 읽기

```text
compose.yaml              실습 서비스: neo4j · mcp · app · init
 └─ include:
     compose.langfuse.yaml  Langfuse 6개 서비스
.env                      비밀번호 · 키 · 포트 (compose 가 읽어 값으로 채운다)
docker/
 ├─ mcp.Dockerfile        mcp · init 이미지
 └─ app.Dockerfile        app 이미지
```

`compose.yaml` 에서 자주 보는 항목:

| 항목 | 뜻 | 예 |
|---|---|---|
| `name:` | compose 프로젝트 이름. 컨테이너 · 볼륨 · 네트워크 이름 앞에 붙는다 | `mfg-bom-agent` |
| `image:` | 받아서 쓰는 이미지 | `neo4j:5.26-community` |
| `build:` | 이 저장소에서 직접 만드는 이미지 | `dockerfile: docker/mcp.Dockerfile` |
| `ports:` | `호스트:컨테이너` 포트 연결 | `"${HOST_NEO4J_BOLT_PORT:-7687}:7687"` |
| `env_file:` | `.env` 를 통째로 환경변수로 넘긴다 | `.env` |
| `environment:` | 특정 값을 덮어쓴다 (컨테이너용 주소 등) | `NEO4J_URI: bolt://neo4j:7687` |
| `volumes:` | 데이터를 볼륨에 보존 | `neo4j_data:/data` |
| `depends_on:` | 먼저 떠 있어야 하는 서비스 | `neo4j: condition: service_healthy` |
| `healthcheck:` | "준비 완료"를 판단하는 점검 명령 | Neo4j 는 실제 Cypher `RETURN 1` |
| `profiles:` | 지정할 때만 뜨는 서비스 | `init` |

`${HOST_NEO4J_BOLT_PORT:-7687}` 은 ".env 에 값이 있으면 그 값, 없으면 7687" 이라는 뜻이다. `${NEO4J_PASSWORD:?…}` 는 ".env 에 값이 없으면 멈추고 메시지를 보여라" 라는 뜻이다.

Compose 가 `.env` 를 채워 넣은 최종 설정을 보려면 (비밀값이 출력되므로 화면 공유 중에는 쓰지 않는다):

```bash
docker compose config
```

문법 오류만 확인하려면:

```bash
docker compose config --quiet
```

---

## 12. 자주 막히는 곳

| 증상 | 원인 | 해결 |
|---|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop(OrbStack)이 꺼져 있다 | 앱을 실행하고 running 상태가 될 때까지 기다린다. Linux 는 `sudo systemctl start docker` |
| `no configuration file provided: not found` | 프로젝트 폴더 밖에서 실행했다 | `cd` 로 `compose.yaml` 이 있는 폴더로 이동 |
| `NEO4J_PASSWORD를 .env에 설정하세요` | `.env` 가 없거나 값이 비었다 | `cp .env.example .env` 후 값 채우기 |
| `port is already allocated` | 같은 포트를 다른 프로그램(또는 바이오 실습, 개발 모드의 `uv run`)이 쓰고 있다 | 그 프로그램을 끄거나 `.env` 의 `HOST_*_PORT` 를 바꾼다 |
| `mfg-neo4j` 가 `(health: starting)` 에서 안 넘어감 | 아직 시작 중이거나 메모리 부족 | 1~2분 기다린다. 계속되면 `docker compose logs neo4j` |
| Neo4j `AuthError` (비밀번호 틀림) | `.env` 비밀번호를 볼륨을 만든 뒤에 바꿨다 | [9절](#9-데이터-보존과-초기화)로 Neo4j 만 초기화 |
| Langfuse 화면이 안 열림 | 첫 기동 시 DB 마이그레이션 중 | 2~3분 뒤 `curl http://localhost:3000/api/public/health` 가 OK 면 접속 |
| 코드를 고쳤는데 컨테이너에 반영이 안 됨 | 이미지를 다시 빌드하지 않았다 | [8절](#8-코드를-바꿨을-때--이미지-다시-빌드) |
| `.env` 를 고쳤는데 반영이 안 됨 | 컨테이너를 다시 만들지 않았다 | `docker compose up -d` ([7절](#7-설정env을-바꿨을-때)) |
| 빌드가 `additional privileges requested` 로 멈춤 | 프로젝트 경로에 한글이 있다 | 영문 경로로 옮기거나 `BUILDX_BAKE_ENTITLEMENTS_FS=0` 을 붙인다 |
| 컨테이너가 `Restarting` 반복 | 시작하자마자 오류로 죽는다 | `docker compose logs --tail 100 <서비스>` 로 마지막 오류를 본다 |
| 디스크가 가득 참 | 이미지 · 빌드 캐시 누적 | `docker system df` 확인 후 [10절](#10-자원-사용량과-디스크-정리) |

막히면 아래 세 출력을 함께 질문한다.

```bash
docker compose ps
```

```bash
docker compose logs --tail 50
```

```bash
uv run python scripts/check_env.py
```

---

## 13. 명령 요약

| 하고 싶은 것 | 명령 |
|---|---|
| 인프라만 켜기 (개발 모드) | `docker compose up -d neo4j langfuse-web` |
| 전부 켜기 (컨테이너 모드) | `docker compose up -d neo4j langfuse-web mcp app` |
| 그래프 초기화 | `docker compose --profile init run --rm init` |
| 상태 보기 | `docker compose ps` |
| 실습 환경 점검 | `uv run python scripts/check_env.py` |
| 로그 따라가기 | `docker compose logs -f <서비스>` |
| 컨테이너 안에서 실행 | `docker compose exec <서비스> <명령>` |
| `.env` 변경 반영 | `docker compose up -d` |
| 코드 변경 반영 (컨테이너 모드) | `docker compose --profile init build` → `docker compose up -d mcp app` |
| 하나만 재시작 | `docker compose restart <서비스>` |
| 끄기 (데이터 유지) | `docker compose down` |
| 전부 초기화 (데이터 삭제) | `docker compose down -v` |
| 메모리 · CPU 보기 | `docker stats --no-stream` |
| 디스크 보기 | `docker system df` |
