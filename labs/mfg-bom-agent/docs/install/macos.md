# 설치 및 첫 실행 가이드 — macOS (Apple Silicon · Intel)

**mfg-bom-agent** (제조 실습) · 다른 운영체제: [Windows 10/11](windows.md) · [Linux (Ubuntu 22.04 / 24.04)](linux.md) · [운영체제 선택으로 돌아가기](../../INSTALL.md)

이 문서는 아무것도 설치되지 않은 macOS PC 에서 시작해 **제조 실습 환경이 브라우저에 뜨는 것까지** 한 단계씩 안내한다.
단계마다 "이렇게 나오면 성공"을 적어 두었으니, 결과가 다르면 다음 단계로 넘어가지 말고 [문제 해결](#문제-해결)을 먼저 본다.

## 전체 흐름

| 단계 | 하는 일 | 처음 한 번만 | 소요 시간 |
|---|---|---|---|
| [1](#1-도구-설치) | Docker · uv · Git 설치 | ✅ | 15~30분 |
| [2](#2-프로젝트-폴더-준비) | 실습 폴더 준비 | ✅ | 1분 |
| [3](#3-env-설정) | `.env` 설정 (API 키 등) | ✅ | 3분 |
| [4](#4-python-패키지-설치) | Python 패키지 설치 | ✅ | 1~2분 |
| [5](#5-neo4j-와-langfuse-띄우기) | Neo4j · Langfuse 컨테이너 띄우기 | | 첫 실행 3~5분, 이후 30초 |
| [6](#6-그래프-초기화와-환경-점검) | 그래프 초기화 · 환경 점검 | | 10초 |
| [7](#7-mcp-서버와-화면-실행) | MCP 서버 · Streamlit 화면 실행 | | 10초 |
| [8](#8-브라우저에서-확인) | 브라우저에서 확인 | | 2분 |
| [9](#9-끝내기와-다시-시작하기) | 끝내기 · 다시 시작하기 | | |

### 준비물

| 항목 | 기준 |
|---|---|
| 메모리 | 16GB 이상 권장. Docker 에 8GB 이상 (Neo4j 약 3GB + Langfuse 묶음 약 2~3GB) |
| 디스크 | 여유 20GB 이상 (Docker 이미지 + 데이터) |
| 계정 | Anthropic API 키 (https://console.anthropic.com → API Keys) |
| 네트워크 | 첫 실행 때 이미지·패키지 다운로드 (약 3GB) |

설치하는 도구는 세 가지다.

| 도구 | 용도 |
|---|---|
| Docker (Compose v2 포함) | Neo4j · Langfuse · 앱 컨테이너 실행 |
| uv | Python 패키지·가상환경 관리. **Python 3.12 도 uv 가 알아서 내려받으므로 Python 을 따로 설치하지 않는다** |
| Git | 저장소 내려받기 |

### uv 란?

**uv 는 Python 프로젝트의 패키지 관리자**다. Node.js 의 `npm` 처럼 "이 프로젝트에 필요한 Python 과 라이브러리를 정해진 버전 그대로 설치해 주는 도구"라고 보면 된다. Rust 로 만들어져 매우 빠르고, Python 개발에 쓰던 여러 도구의 역할을 하나로 합쳤다.

| 하던 일 | 예전 방식 | uv |
|---|---|---|
| Python 버전 설치 | pyenv, python.org 설치 파일 | 자동 (`.python-version` 을 보고 내려받음) |
| 가상환경 만들기 | `python -m venv .venv` | `uv sync` 가 자동으로 만듦 |
| 라이브러리 설치 | `pip install ...` | `uv sync` |
| 버전 고정 | `requirements.txt` | `uv.lock` (자동 생성) |
| 가상환경 안에서 실행 | `source .venv/bin/activate` 후 `python ...` | `uv run python ...` |

이 실습이 uv 를 쓰는 이유:

- **Python 을 따로 설치하지 않아도 된다.** PC 에 Python 이 없거나 버전이 달라도, uv 가 실습에 필요한 3.12 를 프로젝트 전용으로 내려받는다.
- **모든 수강생이 같은 버전을 쓴다.** `uv.lock` 에 라이브러리의 정확한 버전이 기록되어 "제 PC 에서는 안 돼요" 문제가 줄어든다.
- **빠르다.** pip 보다 훨씬 빨라 수업 중 다 같이 설치해도 오래 기다리지 않는다.
- **실수가 적다.** 가상환경 활성화를 잊을 일이 없다. 이 가이드의 명령은 모두 `uv run ...` 이라 항상 가상환경 안에서 실행된다.

Docker 와 나눠 보면, **Docker 는 Neo4j · Langfuse 같은 서버 프로그램**을, **uv 는 우리가 작성하는 Python 코드의 실행 환경**을 맡는다.

---

## 1. 도구 설치

### 1-1. Homebrew 설치 (없으면)

**터미널** 앱(응용 프로그램 → 유틸리티 → 터미널)을 열고 입력한다. 중간에 Mac 로그인 비밀번호를 묻는다.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

설치가 끝나면 `brew` 명령을 쓸 수 있게 PATH 에 추가한다. 칩 종류에 따라 한 줄을 고른다 ( → 이 Mac에 관하여 → 칩).

Apple Silicon (M1~M4):

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile && eval "$(/opt/homebrew/bin/brew shellenv)"
```

Intel:

```bash
echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile && eval "$(/usr/local/bin/brew shellenv)"
```

✅ 성공 확인: `brew --version` 이 버전을 출력한다.

> macOS 버전이 최신이 아니면 `brew` 실행 때 "You are using macOS 14. We do not provide support..." 같은 경고가 나온다. 이 가이드에서 Homebrew 는 Docker 앱(`--cask`) 설치에만 쓰므로 무시해도 된다.

### 1-2. Docker 설치

Docker Desktop 또는 OrbStack 중 **하나만** 설치한다. 둘 다 `docker compose` 명령을 제공한다.

Docker Desktop:

```bash
brew install --cask docker
```

**응용 프로그램 → Docker** 를 실행하고 약관에 동의한다. 로그인 화면은 **Skip** 해도 된다. 메뉴 막대의 고래 아이콘을 눌러 **"Docker Desktop is running"** 이 보일 때까지 기다린다. 그다음 **Settings → Resources → Memory** 가 8GB 이상인지 확인하고, 작으면 올린 뒤 **Apply & restart** 한다.

OrbStack (가볍고 빠른 대안):

```bash
brew install --cask orbstack
```

### 1-3. uv 설치

uv 는 **공식 설치 스크립트**로 설치한다. 미리 빌드된 실행 파일 하나를 내려받기 때문에 1분 안에 끝난다.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

설치 스크립트가 `~/.local/bin` 을 PATH 에 추가하므로 셸 설정을 다시 읽는다 (또는 터미널을 새로 연다).

```bash
source ~/.zshrc
```

> ⚠ `brew install uv` 는 쓰지 않는다. Homebrew 는 최신 macOS 가 아닌 버전(예: macOS 14 Sonoma)에서는 미리 빌드된 패키지(bottle)를 제공하지 않아 uv 를 Rust·LLVM·Python 까지 소스에서 컴파일하려 한다. 수십 분이 걸리고 컴파일 오류로 실패하는 경우가 많다. Docker Desktop · OrbStack 같은 `--cask` 앱은 빌드된 앱을 내려받으므로 영향이 없다.

#### 이미 `brew install uv` 를 실행해 실패했다면

로그에 아래 같은 줄이 보이면 이 경우다.

```text
Warning: You are using macOS 14.
Homebrew no longer builds bottles for this configuration.
...
==> Installing uv dependency: python@3.15
...
error: "This compiler does not have support for efficient tail calling."
make: *** [profile-run-stamp] Error 2
```

**왜 실패하나**: Homebrew 는 최신 macOS 가 아닌 버전용으로는 미리 빌드된 패키지(bottle)를 더 이상 만들지 않는다. 그래서 uv 를 설치하려고 Rust · LLVM · Python 까지 소스에서 컴파일하다가, macOS 14 의 기본 컴파일러가 지원하지 않는 기능 때문에 Python 빌드 단계에서 멈춘다. **uv 나 PC 의 문제가 아니다.**

**해결**:

1. 진행 중이면 `Ctrl + C` 로 중단한다.
2. 실패한 빌드는 설치되지 않으므로 지울 것은 없다. 내려받다 만 파일(Rust · LLVM 소스 등, 1~2GB)만 정리한다.

```bash
brew cleanup
```

3. 위의 공식 설치 스크립트로 uv 를 설치하고 `uv --version` 으로 확인한다.

Docker Desktop · OrbStack 은 `--cask` 로 완성된 앱을 내려받으므로 이 문제와 무관하다.

#### Git

Git 은 macOS 에 기본으로 들어 있다 (Xcode Command Line Tools). `git --version` 을 처음 실행했을 때 설치 창이 뜨면 **설치** 를 누른다.

Apple Silicon 에서도 실습에 쓰는 이미지(Neo4j, Langfuse, ClickHouse, Postgres, Redis, MinIO, Python)는 모두 arm64 를 지원하므로 별도 설정이 필요 없다.

### 설치 확인

터미널에서 하나씩 실행한다.

```bash
docker --version
```

```bash
docker compose version
```

```bash
uv --version
```

```bash
git --version
```

네 명령 모두 버전 번호를 출력하면 된다. 마지막으로 Docker 데몬과 권한을 확인한다.

```bash
docker run --rm hello-world
```

✅ 성공: `Hello from Docker!` 로 시작하는 메시지가 나온다.

---

## 2. 프로젝트 폴더 준비

**응용 프로그램 → 유틸리티 → 터미널** 을 연다. 작업 폴더를 만들고 그 안에 실습 코드를 둔다. **경로에 한글을 넣지 않는다.** `~/Documents/강의/...` 처럼 한글 폴더 아래에 두면 컨테이너 이미지를 빌드할 때(`docker compose build`) 권한 오류가 난다 ([문제 해결](#문제-해결) 참고). `~/work` 처럼 영문 경로를 쓴다.

```bash
mkdir -p ~/work && cd ~/work
```

실습 코드를 받는 방법은 둘 중 하나다.

**Git 저장소로 받는 경우** — 강의에서 안내한 주소를 넣는다.

```bash
git clone <강의에서 안내한 저장소 주소> mfg-bom-agent
```

**압축 파일(zip)로 받은 경우** — 다운로드 폴더의 zip 을 작업 폴더에 푼다.

```bash
unzip ~/Downloads/mfg-bom-agent.zip -d ~/work
```

Finder 에서 zip 을 더블클릭해 풀었다면, 풀린 폴더를 `~/work` (홈 폴더 아래 work) 로 옮겨도 된다.

이후 모든 명령은 프로젝트 폴더 안에서 실행한다.

```bash
cd ~/work/mfg-bom-agent
```

✅ 성공 확인: `ls` 를 실행했을 때 `compose.yaml`, `pyproject.toml`, `src` 가 보인다.

---

## 3. `.env` 설정

API 키 같은 개인 설정은 `.env` 파일에 둔다. 예시 파일을 복사해서 만든다.

```bash
cp .env.example .env
```

`.env` 를 편집기로 연다. 편한 방법 하나를 고른다.

| 방법 | 명령 |
|---|---|
| VS Code | `code .env` |
| macOS 텍스트 편집기 | `open -e .env` |
| 터미널 편집기 | `nano .env` |

`nano` 는 수정 후 `Ctrl + O` → `Enter` 로 저장하고 `Ctrl + X` 로 나간다.

> Finder 에서는 `.` 으로 시작하는 파일이 숨겨져 있다. `Cmd + Shift + .` 을 누르면 보인다. 텍스트 편집기로 열었다면 **포맷 → 일반 텍스트로 만들기** 상태인지 확인한다.

**반드시 바꿀 값 3개**:

| 변수 | 넣을 값 | 설명 |
|---|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` 로 시작하는 본인 키 | https://console.anthropic.com → API Keys 에서 발급 |
| `NEO4J_PASSWORD` | 8자 이상 아무 문자열 | Neo4j 가 처음 뜰 때 이 값으로 비밀번호가 정해진다 |
| `LANGFUSE_INIT_USER_PASSWORD` | 아무 문자열 | Langfuse 화면 로그인 비밀번호 |

**그대로 두어도 되는 값**:

| 변수 | 이유 |
|---|---|
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | 앱이 트레이스를 보낼 Langfuse 프로젝트를 식별하는 키다. 설치형 Langfuse 는 첫 기동 때 이 값으로 프로젝트 키를 자동 생성하므로 화면에서 발급받을 필요가 없다 |
| `HOST_*_PORT` | 다른 프로그램과 포트가 겹칠 때만 바꾼다 ([문제 해결](#문제-해결) 참고) |
| `LLM_MODEL` | 기본 `claude-haiku-5-5` |
| `LANGFUSE_*_PASSWORD`, `SALT`, `ENCRYPTION_KEY` 등 | Langfuse 내부용. 로컬 실습은 기본값으로 충분하다 |
| `EMBEDDING_*` | 임베딩 단계에서 안내한다. 지금은 비워 둔다 |

> ⚠ `.env` 에는 API 키가 들어 있다. 다른 사람에게 폴더를 압축해 보낼 때는 `.env` 를 빼고 보낸다. Git 에는 `.gitignore` 로 제외되어 있다.

---

## 4. Python 패키지 설치

```bash
uv sync --all-extras
```

uv 가 Python 3.12 를 내려받고 프로젝트 안에 `.venv` 가상환경을 만든 뒤 패키지를 설치한다. `uv.lock` 이 없으면 이때 함께 만들어진다.

✅ 성공: 마지막에 `Installed NN packages` 비슷한 줄이 나오고 오류 없이 끝난다. 프로젝트 폴더에 `.venv` 폴더가 생긴다.

> 가상환경을 직접 활성화(`source .venv/bin/activate`)할 필요는 없다. 이 문서의 명령은 모두 `uv run ...` 으로 가상환경 안에서 실행된다.

---

## 5. Neo4j 와 Langfuse 띄우기

메뉴 막대의 고래 아이콘(OrbStack 은 OrbStack 아이콘)을 눌러 **실행 중(running)** 인지 확인한다.

```bash
docker compose up -d neo4j langfuse-web
```

`langfuse-web` 을 지정하면 Langfuse 가 필요로 하는 postgres · clickhouse · redis · minio · langfuse-worker 가 함께 뜬다. **첫 실행은 이미지 다운로드(약 3GB) 때문에 3~5분** 걸린다.

상태를 확인한다.

```bash
docker compose ps
```

✅ 성공: 아래처럼 7개 컨테이너가 보이고, `mfg-neo4j` 의 STATUS 가 `(healthy)` 다. 처음 1분 정도는 `(health: starting)` 이니 잠시 후 다시 확인한다.

```text
NAME                  IMAGE                        STATUS
mfg-clickhouse        clickhouse/clickhouse-server Up (healthy)
mfg-langfuse-web      langfuse/langfuse:4          Up
mfg-langfuse-worker   langfuse/langfuse-worker:4   Up
mfg-minio             chainguard/minio             Up (healthy)
mfg-neo4j             neo4j:5.26-community         Up (healthy)
mfg-postgres          postgres:17                  Up (healthy)
mfg-redis             redis:7                      Up (healthy)
```

(출력 형식은 Docker 버전에 따라 조금 다르다. 이름과 STATUS 만 보면 된다.)

> 메모리가 부족한 PC 는 Langfuse 없이 `docker compose up -d neo4j` 만 띄우고, `.env` 의 `LANGFUSE_PUBLIC_KEY` 와 `LANGFUSE_SECRET_KEY` 를 빈 값으로 바꾼다. 실습은 트레이싱 화면만 빼고 그대로 진행된다.

---

## 6. 그래프 초기화와 환경 점검

Neo4j 에 제조 온톨로지의 유일성 제약을 만든다. 여러 번 실행해도 안전하다.

```bash
uv run python scripts/init_data.py
```

✅ 성공:

```text
constraint ok  :Product(product_id)
constraint ok  :Assembly(assembly_id)
constraint ok  :BOMLine(bomline_id)
constraint ok  :Part(part_id)
constraint ok  :Supplier(supplier_id)
constraint ok  :Revision(revision_id)
constraint ok  :ECN(ecn_id)
constraint ok  :DocumentChunk(chunk_id)
LabMeta ok     dataset_version=mfg-0.1
```

환경 전체를 점검한다.

```bash
uv run python scripts/check_env.py
```

✅ 성공 (Neo4j 패치 버전 숫자는 다를 수 있다):

```text
OK   Neo4j      5.26.32 community nodes=1
OK   Anthropic  claude-haiku-5-5 (Claude Haiku 5.5)
FAIL  MCP        ConnectError: ... (서버 미기동이면 정상)
OK   Langfuse   http://localhost:3000
```

**Neo4j 와 Anthropic 이 `OK` 면 통과**다. MCP 는 다음 단계에서 띄우므로 지금은 `FAIL` 이 정상이다.

---

## 7. MCP 서버와 화면 실행

MCP 서버와 Streamlit 화면은 계속 켜져 있어야 하는 프로그램이라 **터미널이 2개 더** 필요하다. 터미널 창을 하나 더 연다 (`Cmd + T` 로 새 탭도 된다).

**터미널 2 — MCP 서버**

```bash
cd ~/work/mfg-bom-agent && uv run python -m mfg_bom_agent.mcp_server
```

✅ 성공: 아래처럼 출력되고 프롬프트로 돌아오지 않은 채 대기한다.

```text
INFO     Starting MCP server 'mfg-bom-agent' with transport 'http' on http://127.0.0.1:8000/mcp
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**터미널 3 — Streamlit 화면**

```bash
cd ~/work/mfg-bom-agent && uv run streamlit run src/mfg_bom_agent/ui.py
```

✅ 성공: `Local URL: http://localhost:8501` 이 출력된다. (처음 실행하면 이메일을 물어볼 수 있는데 `Enter` 로 넘어가면 된다.)

---

## 8. 브라우저에서 확인

Safari · Chrome 어느 브라우저든 된다.

| 주소 | 로그인 | 확인할 것 |
|---|---|---|
| http://localhost:8501 | 없음 | 환경 점검 화면. **Neo4j · Anthropic API · MCP 서버 · Langfuse 네 줄이 모두 초록색** |
| http://localhost:7474 | 사용자 `neo4j` / `.env` 의 `NEO4J_PASSWORD` | Neo4j Browser. 위쪽 입력창에 `SHOW CONSTRAINTS` 를 실행하면 제약 8개가 보인다 |
| http://localhost:3000 | `.env` 의 `LANGFUSE_INIT_USER_EMAIL` / `LANGFUSE_INIT_USER_PASSWORD` | Langfuse. 로그인 후 프로젝트 **제조 BOM 변경 영향 에이전트** 가 자동으로 만들어져 있다 |

세 화면이 모두 확인되면 실습 환경 준비가 끝났다. 🎉

Neo4j Browser 화면 구성과 쿼리 실행 방법은 [Neo4j Browser 사용 가이드](../NEO4J_BROWSER.md) 에 캡처와 함께 정리되어 있다.

Langfuse 화면 읽는 법과 데모 트레이스 만들기(`scripts/langfuse_demo.py`)는 [Langfuse 사용 가이드](../LANGFUSE.md) 에 정리되어 있다.

---

## 9. 끝내기와 다시 시작하기

### 끝내기

1. 터미널 2(MCP)와 터미널 3(Streamlit)에서 `Ctrl + C` 를 눌러 끈다.
2. 컨테이너를 내린다. **데이터는 그대로 남는다.**

```bash
docker compose down
```

### 다음에 다시 시작하기

1~4단계는 다시 할 필요가 없다. 프로젝트 폴더에서 5단계부터 하면 된다.

```bash
cd ~/work/mfg-bom-agent && docker compose up -d neo4j langfuse-web
```

그다음 7단계처럼 MCP 서버와 Streamlit 을 각각의 터미널에서 띄운다.

### 데이터까지 완전히 지우고 처음부터

Neo4j 그래프와 Langfuse 트레이스를 모두 삭제한다. 되돌릴 수 없다.

```bash
docker compose down -v
```

이후 5단계부터 다시 하면 처음 상태로 돌아간다. (`.env` 의 `NEO4J_PASSWORD` 를 바꿨다면 이 방법으로 지워야 새 비밀번호가 적용된다.)

로그 보기 · 설정 변경 반영 · 이미지 다시 빌드 · Neo4j 만 초기화하기 같은 Docker 사용법은 [Docker 사용 가이드](../DOCKER.md) 에 정리되어 있다.

---

## 문제 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `brew: command not found` | Homebrew PATH 설정(1-1 마지막 줄)을 건너뛰었다 | 1-1 의 칩 종류에 맞는 `eval ...` 줄을 실행한다 |
| `brew install uv` 가 오래 걸리다 `make` 오류로 실패 | Homebrew 가 이 macOS 버전용 빌드 패키지를 제공하지 않아 소스 컴파일을 시도했다 | 중단(`Ctrl + C`)하고 1-3 의 공식 설치 스크립트로 설치한다. 내려받다 만 파일은 `brew cleanup` 으로 지운다 |
| `Cannot connect to the Docker daemon` | Docker Desktop(OrbStack)이 실행 중이 아니다 | 응용 프로그램에서 Docker 를 실행하고 running 이 될 때까지 기다린다 |
| Docker Desktop 과 OrbStack 을 둘 다 설치함 | 두 프로그램이 `docker` 명령을 서로 가져간다 | 하나만 실행한다. 쓰지 않는 쪽은 종료하거나 삭제 |
| Neo4j·ClickHouse 가 자꾸 재시작 | Docker 메모리 할당 부족 | Docker Desktop → Settings → Resources → Memory 를 8GB 이상으로 올린다 |
| `uv: command not found` | 설치 직후 PATH 가 반영되지 않았다 | `source ~/.zshrc` 또는 터미널 재시작 |
| `NEO4J_PASSWORD를 .env에 설정하세요` | `.env` 가 없거나 값이 비었다 | 3단계를 다시 확인한다. `.env` 는 프로젝트 폴더 바로 아래에 있어야 한다 |
| `LANGFUSE_INIT_USER_PASSWORD를 .env에 설정하세요` | 위와 같다 | `.env` 에 해당 줄이 있는지, 값이 비어 있지 않은지 확인 |
| `port is already allocated` / `address already in use` | 다른 프로그램(또는 바이오 실습(bio-target-agent))이 같은 포트를 쓰고 있다 | `.env` 의 `HOST_*_PORT` 를 바꾸고, 같은 포트를 쓰는 `NEO4J_URI` · `MCP_PORT` · `MCP_URL` · `LANGFUSE_HOST` 도 함께 바꾼다 |
| `mfg-neo4j` 가 계속 `health: starting` | 아직 시작 중이거나 메모리 부족 | 1~2분 더 기다린다. 계속되면 `docker compose logs neo4j` 로 원인을 본다 |
| check_env 에서 Neo4j `AuthError` | 예전에 다른 비밀번호로 Neo4j 를 띄운 볼륨이 남아 있다 | `docker compose down -v` 로 볼륨을 지우고 5단계부터 다시 |
| check_env 에서 Anthropic `AuthenticationError` | API 키가 틀렸거나 앞뒤에 공백이 있다 | `.env` 의 `ANTHROPIC_API_KEY` 를 다시 붙여 넣는다 |
| check_env 에서 Anthropic `NotFoundError` | `LLM_MODEL` 철자가 틀렸다 | `claude-haiku-5-5` 인지 확인 |
| Langfuse 화면이 안 열림 | 첫 기동 시 DB 마이그레이션 중 | 2~3분 기다린 뒤 `curl http://localhost:3000/api/public/health` 가 `{"status":"OK"...}` 를 돌려주면 접속한다 |
| Streamlit 화면에서 MCP 가 노란색 | MCP 서버(터미널 2)가 꺼져 있다 | 7단계의 MCP 서버를 다시 띄운다 |
| `docker compose build` 가 `additional privileges requested: pass "--allow=fs.read=..."` 로 멈춤 | 프로젝트 경로에 한글이 있다. macOS 는 한글 파일명을 분해된 유니코드로 저장하는데, Docker 빌드 도구(buildx bake)가 이 경로를 프로젝트 밖으로 오인해 추가 권한을 요구한다 | 프로젝트를 `~/work` 같은 영문 경로로 옮긴다. 당장 옮기기 어려우면 `BUILDX_BAKE_ENTITLEMENTS_FS=0 docker compose build` 처럼 앞에 붙여 실행한다 |

그래도 해결되지 않으면 아래 세 가지 출력을 함께 질문한다.

```bash
docker compose ps
```

```bash
docker compose logs --tail 50
```

```bash
uv run python scripts/check_env.py
```
