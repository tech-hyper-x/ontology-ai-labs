# 제조 실습 환경 준비와 에이전트 실행

## 제조 실습 진행 순서

이번 실습에서는 **“이 휠은 어느 조립품에 쓰일까요?”**라는 질문을 따라갑니다. 제조 부품표에서 휠의 사용처를 조회하고 정비 문서를 검색한 뒤, 같은 자료로 에이전트가 작성한 답을 확인합니다.

| 단계 | 할 일 | 확인할 결과 |
|---|---|---|
| 환경 준비 | Docker와 uv 준비 → GitHub 프로젝트 다운로드 → 제조 폴더에서 접속 정보·API 키·패키지 설정 | Docker 테스트가 성공하고 Compose 서비스 목록이 보입니다. |
| 서비스와 데이터 준비 | 이미지 다운로드 → Neo4j와 Langfuse 접속 → 제조 부품표 적재와 정비 문서 검색 색인 확인 | Neo4j 첫 조회가 성공하고, 제조 데이터와 문서 검색 색인이 준비됩니다. |
| 휠 사용처와 정비 문서 확인 | MCP 서버와 앱 실행 → 휠의 사용처 조회 → 정비 문서 검색 → 에이전트 답변 대조 | 답변에 나온 조립품과 출처를 직접 조회한 결과에서 찾을 수 있습니다. |

아래 순서대로 진행하세요. Mac 기준 화면을 사용하며, Windows와 Linux의 도구 설치 방법은 **Docker와 기본 도구 설치**에서 안내합니다.

이 문서의 실행 경로와 포트는 **제조 프로젝트** 기준입니다. 바이오 실습은 해당 프로젝트의 설치·챕터 안내를 따르며, 제조 DB를 대상으로 바이오 초기화 명령을 실행하지 않습니다. 전체 자료의 출발점은 [가이드 지도](../../SITEMAP.md)입니다.

아래 **바이브 코딩** 상자는 실습할 컴퓨터의 Claude Code나 Codex 대화창에 붙여넣는 질문입니다. 필요한 단계에서 상자 오른쪽 위의 복사 버튼을 누르세요.

[도구와 버전](#ai-tool-check) · [개인 설정](#ai-env) · [서비스 상태](#ai-services) · [검색 색인](#ai-index) · [사용처 비교](#ai-where-used)

## 1. 무엇을 설치하나요?

|소프트웨어|강의에서 하는 일|준비 방법|
|---|---|---|
|Docker Desktop / Docker Engine|서버 프로그램을 컨테이너로 실행|PC에 설치|
|uv|Python과 프로젝트 라이브러리를 준비|PC에 설치|
|Git|실습 코드 내려받기·버전 관리|PC에 설치. ZIP으로도 다운로드 가능|
|Neo4j|부품·조립품·투입 내역을 저장하고 관계 조회|프로젝트 Compose가 이미지 다운로드·실행|
|Langfuse|모델·도구 호출 순서, 입력·출력, 지연을 확인|프로젝트 Compose가 관련 서비스와 함께 실행|

Neo4j Desktop이나 Langfuse Cloud 계정을 별도로 만드는 방식은 사용하지 않습니다. 이 가이드에서는 프로젝트에 포함된 compose.yaml과 compose.langfuse.yaml을 사용합니다. 앱과 MCP는 로컬 uv로 실행하는 개발 모드입니다.

## 2. Docker와 기본 도구 설치

| 도구 | 이 실습에서 확인할 기준 |
|---|---|
| Docker와 Compose | Docker 엔진이 실행 중이어야 합니다. 프로젝트가 두 설정 파일을 합치는 `include`를 사용하므로 **Compose 2.20.0 이상**이 필요합니다. 33장에서 `docker compose version`으로 확인합니다. |
| Python | 제조 앱의 실행 범위는 **3.12.x**입니다. 34장에서 패키지를 준비하고 프로젝트 폴더에서 `uv run python --version`으로 확인합니다. PC의 기본 Python 버전은 달라도 됩니다. |
| uv와 Git | 저장소가 두 도구의 버전을 지정하지 않습니다. uv는 제공된 잠금 파일을 읽고 패키지를 설치할 수 있어야 합니다. Git은 저장소를 복제할 때 사용하며 ZIP으로 받으면 생략합니다. |
| Neo4j와 Langfuse | 35장에서 Compose가 지정한 이미지 태그 **Neo4j 5.26-community**, **Langfuse 웹·워커 4**를 사용합니다. |

기준 파일은 [Python 프로젝트 설정](../../labs/mfg-bom-agent/pyproject.toml), [잠금 파일](../../labs/mfg-bom-agent/uv.lock), [제조 서비스 설정](../../labs/mfg-bom-agent/compose.yaml), [Langfuse 서비스 설정](../../labs/mfg-bom-agent/compose.langfuse.yaml)입니다. [Docker의 include 버전 기준](https://docs.docker.com/reference/compose-file/include/)도 확인할 수 있습니다.

<a name="ai-tool-check"></a>

### 바이브 코딩 · 도구 설치와 버전 확인

```text
내 컴퓨터에서 제조 실습에 쓸 도구를 확인하고, 빠졌거나 호환되지 않는 도구는 공식 방법으로 설치를 도와주세요.
아직 강의 저장소를 내려받기 전이어도 됩니다.

1. 운영체제와 터미널을 확인해 주세요. Windows는 WSL2 Ubuntu와 Docker Desktop 연동을 확인해 주세요.
   원격 환경이면 내 PC에서 직접 확인할 명령을 알려주세요.
2. docker --version, docker compose version, uv --version을 각각 실행해 주세요.
   Compose는 설정 파일의 include를 사용하므로 2.20.0 이상이어야 합니다.
   Git으로 복제할 때만 git --version을 확인하고, ZIP으로 받을 때는 생략해 주세요.
3. docker info로 엔진 연결을 확인한 뒤 docker run --rm hello-world를 실행해 주세요.
   실패하면 설치 누락, 엔진 중지, 이미지 다운로드 오류 중 어디서 막혔는지 짚어 주세요.
4. 제조 앱의 Python은 3.12.x입니다. 아직 프로젝트를 받지 않았다면 ‘34장에서 확인’으로 표시해 주세요.
   패키지를 준비했다면 제조 폴더에서 uv run --no-sync python --version으로 확인해 주세요.
   시스템 Python은 그대로 사용합니다. uv와 Git은 고정 버전이 없고, uv는 제공된 uv.lock을 읽을 수 있어야 합니다.
   Neo4j 5.26-community와 Langfuse 4는 35장에서 Compose가 준비합니다.
5. 설치나 업데이트가 필요하면 내 운영체제에 맞게 진행하고, 내가 직접 승인하거나 실행할 단계는 알려주세요.
   설치한 도구를 다시 확인한 뒤 ‘도구 | 실습 기준 | 내 버전 | 다음 행동’ 표로 정리해 주세요.
```

### macOS: Docker Desktop 설치

1. Apple 메뉴 → 이 Mac에 관하여에서 칩을 확인합니다.
2. [Docker 공식 Mac 설치 페이지](https://docs.docker.com/desktop/setup/install/mac-install/)를 엽니다.
3. Apple Silicon 또는 Intel에 맞는 설치 파일을 내려받습니다.
4. Docker.dmg를 열고 Docker 앱을 Applications로 옮깁니다.
5. 응용 프로그램의 Docker를 실행합니다. 처음 실행할 때 필요한 설정은 공식 설치 안내에 따라 진행합니다.
6. Docker Desktop이 실행 중 상태가 될 때까지 기다립니다.
7. Settings → Resources의 메모리 설정을 확인합니다. 이 실습의 Neo4j·Langfuse를 함께 실행하는 경우 기존 강의 설치 안내의 8GB 할당 권장을 기준으로 PC 여유를 확인합니다. WSL·가상화 방식에 따라 설정 위치가 다를 수 있습니다.

터미널에서 각각 확인합니다.

```bash
docker --version
docker compose version
docker info
docker run --rm hello-world
```

확인할 결과: 버전이 표시되고, docker info가 서버 정보를 반환하며, hello-world가 실행됩니다. 설치 파일을 받은 것과 Docker 엔진이 실행 중인 것은 구분합니다.

### uv와 Git

uv는 [공식 설치 안내](https://docs.astral.sh/uv/getting-started/installation/)의 독립 설치 프로그램을 사용합니다.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

설치가 끝나면 새 터미널을 열고 확인합니다.

```bash
uv --version
git --version
```

Mac에서 Git이 없다는 설치 창이 뜨면 Command Line Tools 설치를 완료합니다. Python은 프로젝트의 .python-version과 uv 설정에 따라 준비하므로 별도 시스템 Python을 먼저 설치할 필요는 없습니다.

### 다른 운영체제

- [Windows 설치](../../labs/mfg-bom-agent/docs/install/windows.md): WSL2 Ubuntu와 Docker Desktop의 WSL 통합을 준비합니다. 이후 명령은 Ubuntu 터미널에서 실행합니다.
- [Linux 설치](../../labs/mfg-bom-agent/docs/install/linux.md): Docker Engine·Compose 플러그인·uv·Git을 준비합니다.
- [기존 Mac 상세 문서](../../labs/mfg-bom-agent/docs/install/macos.md): 도구 설치와 OS 문제 해결 참고.

도구 설치를 마치면 아래의 **GitHub 프로젝트 다운로드**로 이어갑니다. 초기화·임베딩·서버 연결에 관한 설명은 이 가이드를 기준으로 합니다.

## 3. GitHub 프로젝트 다운로드

저장소: https://github.com/tech-hyper-x/ontology-ai-labs

### Git으로 받기

```bash
mkdir -p ~/work
cd ~/work
git clone https://github.com/tech-hyper-x/ontology-ai-labs.git
cd ontology-ai-labs/labs/mfg-bom-agent
```

### ZIP으로 받기

1. 저장소의 Code → Download ZIP을 누릅니다.
2. ZIP을 풀고 영문 작업 경로로 옮깁니다.
3. 압축을 푼 폴더의 labs/mfg-bom-agent로 이동합니다.
4. 터미널도 이 폴더 안에서 엽니다. ZIP의 최상위 폴더명에는 -main이 붙을 수 있습니다.

현재 폴더를 확인합니다.

```bash
pwd
ls
```

compose.yaml, compose.langfuse.yaml, pyproject.toml, src 폴더가 보여야 합니다. 이후 명령은 이 폴더에서 실행합니다.

## 4. .env와 Python 패키지 준비

```bash
cp .env.example .env
```

이미 `.env`가 있다면 복사 명령을 건너뛰고 기존 파일을 편집합니다. 기존 비밀번호·API 키를 예시값으로 덮어쓰지 않습니다.

편집기로 .env를 열어 다음 항목을 설정합니다.

|설정|입력할 내용|
|---|---|
|NEO4J_PASSWORD|본인의 로컬 실습 DB 비밀번호|
|LANGFUSE_INIT_USER_EMAIL|Langfuse 초기 로그인 이메일. 예시값 유지 가능|
|LANGFUSE_INIT_USER_PASSWORD|Langfuse 초기 로그인 비밀번호|
|LANGFUSE_PUBLIC_KEY / SECRET_KEY|제공된 로컬 프로젝트 설정값. 앱과 초기 프로젝트에 같은 값 사용|
|ANTHROPIC_API_KEY|실제 모델 호출에 사용할 본인 API 키|
|EMBEDDING_API_KEY|문서·질문 벡터화에 사용할 별도 API 키|
|EMBEDDING_PROVIDER / MODEL / DIMENSION|배포된 예시 설정값 유지|

<a name="ai-env"></a>

### 바이브 코딩 · 개인 설정 항목 확인

```text
제조 폴더의 .env.example과 강의 가이드의 설정표를 보고, 내가 입력할 항목을 정리해 주세요.
개인 .env는 열지 말고 예시 파일의 항목명만 사용해 주세요.
그래프 접속, 답변 생성, 문서 임베딩으로 나눠서 내가 발급받을 키와 예시값을 유지할 항목을 알려주세요.
패키지 준비 후 프로젝트 Python이 3.12.x인지 확인할 명령도 알려주세요.
```

### 답변 생성과 문서 검색에 쓸 API 키 준비

에이전트가 답변을 작성할 때는 Anthropic 키를, 정비 문서와 검색 질문을 벡터로 바꿀 때는 Voyage 키를 사용합니다.

1. Anthropic: [공식 API 키 안내](https://platform.claude.com/docs/en/get-api-key)를 따라 Claude Console에 로그인하고 API keys에서 키를 생성합니다. [키 관리 화면](https://platform.claude.com/settings/keys)에서 만든 값을 `.env`의 `ANTHROPIC_API_KEY`에 입력합니다.
2. Voyage: [공식 키 발급 안내](https://docs.voyageai.com/docs/api-key-and-installation)에 따라 [Voyage 대시보드](https://dashboard.voyageai.com)에 로그인하고 API keys에서 새 키를 생성합니다. 이 프로젝트에서는 `.env`의 `EMBEDDING_API_KEY`에 입력합니다. 모델·차원은 배포 예시 설정을 유지합니다.
3. 발급·사용 한도·임베딩 확인은 [프로젝트 Voyage 안내](../../labs/mfg-bom-agent/docs/VOYAGE.md)를 참고합니다. 안내의 가격·한도는 작성 시점 기준이므로 현재 제공 조건은 공급자 화면에서 확인합니다.

두 키는 용도가 다릅니다. Anthropic 키는 답변 생성, Voyage 키는 문서·질문 임베딩에 사용합니다. 실제 API 호출에는 공급자별 이용 조건과 과금이 적용됩니다. 키는 `.env`에만 저장하고 화면·Git에 노출하지 않습니다.

추가로 다음을 설정합니다.

```dotenv
MCP_TRANSPORT=http
MCP_URL=http://localhost:8000/mcp
DEMO_MODE=none
```

실제 API 키와 비밀번호는 녹화에 노출하지 않습니다. 설명 화면에는 .env.example을 보여주고, 실제 값 입력은 별도 화면에서 진행합니다.

패키지를 준비합니다.

```bash
uv sync --all-extras
uv run python --version
```

마지막 줄이 `Python 3.12.x`인지 확인하세요.

Compose 설정을 검사합니다. 아래 명령은 실제 비밀값을 출력하지 않습니다.

```bash
docker compose config --quiet
docker compose config --services
```

확인할 결과: 누락 변수·YAML 오류 없이 끝나고 neo4j, langfuse-web, langfuse-worker 등의 서비스 이름이 표시됩니다. 이 단계에서 Neo4j와 Langfuse 설정을 함께 확인합니다.

## 5. 이미지 다운로드

처음 실행할 때는 제조 실습에 쓸 서비스 이미지를 함께 내려받습니다.

```bash
docker compose pull neo4j langfuse-web langfuse-worker postgres clickhouse redis minio
```

확인할 결과: 다운로드가 완료되고 오류가 없습니다. 다운로드 시간은 네트워크와 PC에 따라 달라집니다. 강의 20분의 설명·핵심 시연 시간과 최초 설치 대기 시간을 구분합니다.

## 6. Neo4j 설치·실행 확인

```bash
docker compose up -d neo4j
docker compose ps
docker compose logs --tail=50 neo4j
```

Docker Desktop의 Containers에서도 제조 프로젝트를 펼쳐 neo4j 상태를 확인할 수 있습니다. 시작 중이면 준비될 때까지 기다립니다.

### 첫 접속

1. 브라우저에서 http://localhost:7474 를 엽니다.
2. 접속 주소는 bolt://localhost:7687 또는 화면이 요구하는 localhost:7687을 입력합니다.
3. 사용자 이름은 neo4j입니다.
4. 비밀번호는 .env의 NEO4J_PASSWORD 값입니다.
5. Connect를 눌러 연결합니다.
6. 연결한 뒤 아래 순서로 사용할 데이터베이스를 선택·확인하고 첫 질의를 실행합니다.

### 데이터베이스와 사용자 구분·선택

기본 사용자 이름과 일반 데이터베이스 이름은 모두 `neo4j`지만 서로 다른 항목입니다. 사용자는 로그인 계정이고, 데이터베이스는 노드·관계가 저장되는 대상입니다.

이 프로젝트는 **Neo4j 5.26 Community**를 사용합니다. 서버 하나에 일반 DB 하나와 관리용 `system` DB가 있습니다. 기본 `neo4j` DB와 기존 사용자로 실습하며 새 DB·사용자는 만들지 않습니다. 이는 Docker의 제한이 아니라 에디션의 제한입니다.

입력창에서 아래 블록을 **각각 따로** 실행합니다.

```cypher
SHOW DATABASES;
```

```text
:use neo4j
```

`:use`는 Browser 명령으로, 다른 Cypher 질의와 합쳐 실행하지 않습니다. 관리용 `system`을 선택한 상태에서 기초 데이터를 넣지 않습니다.

```cypher
CALL db.info() YIELD name
RETURN name AS currentDatabase;
```

결과가 `neo4j`인지 확인한 뒤 첫 질의를 실행합니다.

```cypher
RETURN 1 AS connection_ok;
```

확인할 결과: connection_ok가 1로 표시됩니다. 이것은 DB 접속과 질의 실행 확인이며, 실습 데이터 적재 완료를 뜻하지는 않습니다. 아직 초기화 전이라 그래프에 업무 데이터가 없어도 됩니다.

이미 생성된 DB 볼륨의 비밀번호는 .env만 바꾼다고 자동 변경되지 않습니다. 로그인이 안 되면 기존 비밀번호와 연결 주소부터 확인합니다.

### 터미널에서 접속하기: Cypher Shell

MySQL의 `mysql` 클라이언트에 해당하는 도구가 **Cypher Shell**입니다. Browser에 로그인하지 않아도 CLI에서 사용자·비밀번호로 직접 인증해 접속할 수 있습니다. 이 프로젝트 폴더의 운영체제 터미널에서 실행하고, 안내가 나오면 `.env`에 설정한 비밀번호를 입력합니다.

```bash
docker compose exec neo4j cypher-shell -u neo4j -d neo4j
```

접속 후에는 위의 `RETURN 1 AS connection_ok;`를 실행할 수 있습니다. 종료할 때는 다음을 단독 실행합니다.

```text
:exit
```

| 포트 | 역할 |
|---|---|
| `7474` | Browser 웹 화면을 여는 HTTP 포트 |
| `7687` | CLI·Browser·프로그램 드라이버가 질의에 사용하는 Bolt 포트. 셸 전용 포트가 아님 |

같은 서버·DB를 선택하면 Browser와 CLI가 보는 데이터는 같습니다. CLI 결과는 표·텍스트이며 그래프 그림은 표시하지 않습니다.

첫 질의에서 `connection_ok`가 1이면 다음 단계인 **Langfuse 설치·실행 확인**으로 이동합니다. 잠시 뒤 제조 데이터를 준비한 후 이 Browser에서 휠의 사용처를 조회합니다. 조회문을 읽을 때 필요한 문법은 [Cypher 문법 참고](../neo4j-cypher-basics.md)에서 찾아볼 수 있습니다.

## 7. Langfuse 설치·실행 확인

```bash
docker compose up -d langfuse-web
docker compose ps
docker compose logs --tail=50 langfuse-web langfuse-worker
```

프로젝트 Compose는 Langfuse 화면뿐 아니라 worker·PostgreSQL·ClickHouse·Redis·MinIO도 함께 실행합니다. 각 저장소를 PC에 직접 설치하지 않습니다. 초기 DB 준비와 마이그레이션이 끝날 때까지 기다립니다.

<a name="ai-services"></a>

### 바이브 코딩 · 서비스 실행 상태 확인

```text
Neo4j와 Langfuse를 실행했는데 접속 화면이 열리지 않습니다.
제조 폴더에서 docker compose ps -a를 실행해 neo4j와 langfuse-web의 상태와 실제 호스트 포트를 확인해 주세요.
아직 시작 중인지, 종료됐는지, 실행 중이면 어느 주소를 열어야 하는지 알려주세요.
지금은 서비스 재시작이나 데이터 초기화 없이 다음에 확인할 항목 하나만 짚어 주세요.
```

### 첫 로그인과 프로젝트 확인

1. http://localhost:3000 을 엽니다.
2. .env의 LANGFUSE_INIT_USER_EMAIL과 LANGFUSE_INIT_USER_PASSWORD로 로그인합니다.
3. 초기 조직·프로젝트가 표시되는지 확인합니다.
4. 제조 프로젝트를 엽니다.
5. Tracing 화면으로 이동합니다.

현재 Compose는 LANGFUSE_INIT_* 값으로 사용자·조직·프로젝트·프로젝트 키를 처음에 생성하도록 구성돼 있습니다. 따라서 이 강의에서는 Cloud 가입이나 프로젝트 키 수동 발급을 먼저 진행하지 않습니다.

처음 Tracing 목록이 비어 있는 것은 아직 실행 기록을 보내지 않았기 때문일 수 있습니다. 화면이 열린 것과 기록이 수집된 것을 구분합니다. 기존 볼륨이 있으면 .env의 초기 사용자 값을 바꿔도 기존 계정이 새로 만들어지는 것은 아닙니다.

## 8. 실습 데이터와 검색 색인 준비

**아래 초기화는 기존 데이터를 삭제하고 제조 데이터를 다시 적재합니다.** `init_data.py`가 호출하는 적재 코드는 현재 연결한 DB에서 `LabMeta` 라벨을 제외한 모든 노드를 관계와 함께 삭제합니다. 같은 DB에 만든 `CypherGuide` 기초 예제나 개인 노드도 삭제 대상입니다. 새 사용자 생성이나 비밀번호 변경 작업은 아닙니다.

- 초기화하기 전에 `.env`의 `NEO4J_URI`가 제조 전용 로컬 서버를 가리키는지 확인합니다. 기본값은 `bolt://localhost:7687`입니다.
- 보존할 개인 데이터가 있다면 먼저 백업하고 초기화를 진행하지 않습니다. 제조 실습 DB에 업무 데이터를 함께 보관하지 않습니다.
- 이미 적재를 마친 환경은 매번 초기화하지 않습니다. 임베딩 설정만 고쳤다면 아래의 `build_index.py` 안내를 따릅니다.

처음 준비하는 제조 실습 전용 DB에서만 아래 초기화를 실행합니다. 이미 적재한 환경에서는 첫 명령을 건너뛰고 환경 점검부터 진행합니다.

```bash
uv run python scripts/init_data.py
uv run python scripts/check_env.py
```

init_data.py는 실습 데이터를 다시 적재하고 온톨로지 검사·문서 연결·검색 색인을 실행합니다. 다른 업무 데이터가 있는 DB 대신 이 프로젝트의 전용 실습 DB를 사용합니다.

확인할 결과:

- 적재 단계가 오류 없이 끝나는가?
- 검사 결과에 위반이 표시되는가?
- 문서 연결과 검색 색인 단계가 완료되는가?
- 실제 임베딩 공급자와 대체 사용 여부가 무엇인가?
- 환경 점검의 Neo4j·Anthropic 결과는 무엇인가?

의미 기반 벡터 검색을 비교할 때는 초기화 로그와 검색 결과의 `index_provider`·`query_provider`를 함께 확인합니다. `hash:local`은 연결 점검용 대체 방식입니다. 이 상태를 의미 검색 성공으로 설명하지 않습니다. 키·모델 설정을 바로잡았다면 전용 실습 환경에서 `uv run python scripts/build_index.py`로 문서 연결과 검색 색인만 다시 구성합니다. 기존 실습 DB 전체 초기화는 반복하지 않습니다.

현재 check_env.py의 MCP 항목은 HTTP 응답 확인입니다. Langfuse 항목도 설정 상태 표시이므로, 이 표만으로 도구 호출·실행 기록 수집 성공을 판단하지 않습니다.

<a name="ai-index"></a>

### 바이브 코딩 · 데이터와 검색 색인 점검

```text
아래는 내 실습에서 이미 실행한 결과입니다. 데이터 재적재나 API 호출 없이 이 출력만 읽어 주세요.
부품 데이터 적재, 정비 문서 색인 생성, 실제 임베딩 사용 중 어디까지 확인됐나요?
index_provider나 query_provider에 hash:local이 보이면 어떤 검색을 확인할 수 있는지도 알려주세요.
출력에서 판단할 수 없는 항목은 미확인으로 남겨 주세요.

내 실행 결과(키와 비밀번호 제외): [여기에 붙여넣기]
```

## 9. MCP와 앱 실행

터미널 2에서 실행하고 유지합니다.

```bash
uv run python -m mfg_bom_agent.mcp_server
```

터미널 3에서 실행하고 유지합니다.

```bash
uv run streamlit run src/mfg_bom_agent/ui.py
```

1. http://localhost:8501 에서 앱이 열리는지 확인하고, 서버 터미널 두 개를 계속 실행해 둡니다.
2. [그래프에서 사용처 직접 조회](../ch03-run-guide.md#5-그래프에서-사용처-직접-조회)로 이동해 Neo4j Browser에서 휠이 들어가는 조립품과 개정판을 기록합니다.
3. 이어지는 **MCP 직접 호출과 검색**에서 같은 부품을 조회하고 휠 정비 문서의 근거 구간을 확인합니다.
4. **에이전트에서 같은 조건 비교**에서 앱의 답변에 나온 조립품과 문서 출처를 두 도구의 결과와 대조합니다.

Part 1 Ch3의 완료 기준은 직접 찾은 사용처와 문서 근거를 앱의 답변에서 확인하는 것입니다. Langfuse는 이 장에서 프로젝트 접속을 확인하고, 실행 기록의 상세 해석은 Part 2에서 이어갑니다.

<a name="ai-where-used"></a>

### 바이브 코딩 · 휠 사용처 결과 비교

```text
36장에서 조회한 표와 37장의 where_used 응답을 붙이겠습니다.
먼저 부품번호와 개정판이 같은지 확인해 주세요. 일치하면 조립품별로 두 결과의 수량을 나란히 보여주세요.
값이 다르거나 한쪽에만 있는 행을 짚고, 비교에 필요한 값이 빠졌다면 해당 필드명을 알려주세요.

36장 조회 표: [내 표 붙여넣기]
37장 도구 응답: [내 응답 붙여넣기]
```

Langfuse 확인용 별도 예제가 필요하면 데이터 준비 후 다음을 활용할 수 있습니다.

```bash
uv run python scripts/langfuse_demo.py --mock
```

이 옵션은 LLM 답변을 고정하는 데 사용하며, 실제 모델의 질문 이해 성능을 확인하는 결과로 해석하지 않습니다. 임베딩 API 연결까지 대체하는 옵션도 아닙니다.

## 10. 종료와 다음 실행

앱과 MCP 터미널은 Ctrl+C로 종료합니다. 컨테이너는 다음으로 종료합니다.

```bash
docker compose down
```

다음 실습에서는 Docker를 먼저 실행하고 다음 순서로 진행합니다.

```bash
docker compose up -d neo4j langfuse-web
```

이후 MCP와 앱을 각 터미널에서 실행합니다. 데이터가 그대로 남아 있다면 매번 초기화할 필요는 없습니다. 볼륨 삭제 옵션은 기본 종료 명령에 넣지 않습니다.

## 11. 자주 막히는 곳

|증상|먼저 확인할 것|
|---|---|
|docker 명령은 있지만 서버 연결 실패|Docker Desktop이 실제 실행 중인지|
|Compose 변수 누락|프로젝트 위치와 .env, Langfuse 필수 값|
|포트 사용 중|7474·7687·3000·8501·8000을 사용하는 기존 프로그램|
|Neo4j 로그인 실패|기존 DB 볼륨의 비밀번호와 현재 접속 주소|
|Langfuse 로그인 실패|초기 생성 시 계정, 기존 볼륨, web 로그|
|Langfuse 목록이 비어 있음|실제 실행을 했는지, 앱의 프로젝트 키·주소, worker 상태|
|검색 방식이 예상과 다름|임베딩 키·공급자·모델·차원과 effective_mode|
|MCP 도구 호출 실패|MCP 서버 터미널, MCP_TRANSPORT=http, 입력 ID·개정판|

## 공식 참고 자료

- [Docker Desktop Mac 설치](https://docs.docker.com/desktop/setup/install/mac-install/)
- [uv 설치](https://docs.astral.sh/uv/getting-started/installation/)
- [Neo4j Docker 시작](https://neo4j.com/docs/operations-manual/current/docker/introduction/)
- [Langfuse Compose 설치](https://langfuse.com/self-hosting/deployment/docker-compose)
- [Langfuse 초기 사용자·프로젝트 설정](https://langfuse.com/self-hosting/administration/headless-initialization)
