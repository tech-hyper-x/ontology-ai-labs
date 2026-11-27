# Ontology AI Labs

강의 화면에 나온 파일을 열고 명령을 실행한 뒤, 자신의 결과를 강사의 화면과 비교할 수 있는 보조 자료입니다.

필요한 문서를 빠르게 찾으려면 **[가이드 전체 지도 · SITEMAP](SITEMAP.md)**을 열어 주세요.

Part 1 Ch3은 제조 환경 준비와 휠 사용처 확인, Part 2는 제조 설계 실습, Part 3은 바이오 예제를 다룹니다. 강의에서 안내하는 Part와 챕터의 자료를 여세요.

**지금 보는 장표로 이동:** [Part 1 Ch3 · 31–41장 촬영 순서](docs/part01/ch03/README.md) · [Part별 실습 장표 목차](docs/hands-on/README.md)

## 시작하기

[제조 실습 진행 순서](docs/setup/README.md)를 열고 **“이 휠은 어느 조립품에 쓰일까요?”**라는 질문을 따라가세요.

1. **환경 준비** — 운영체제에 맞는 도구를 설치하고, 내려받은 저장소의 `labs/mfg-bom-agent`에서 접속 정보와 패키지를 준비합니다.
2. **서비스와 데이터 준비** — Neo4j와 Langfuse를 실행하고 제조 부품표와 정비 문서 검색 색인을 준비합니다.
3. **휠 사용처와 정비 문서 확인** — MCP와 앱을 띄운 뒤 [그래프에서 사용처 직접 조회](docs/ch03-run-guide.md#5-그래프에서-사용처-직접-조회)부터 진행합니다. 휠의 사용처와 정비 문서 검색 결과를 에이전트의 답변과 대조합니다.

Windows에서는 WSL Ubuntu 터미널을, Mac에서는 기본 터미널을 사용합니다. 조회문 문법은 [Cypher 문법 참고](docs/neo4j-cypher-basics.md)에서 확인할 수 있습니다.

## 폴더

```text
docs/ch03-run-guide.md          Ch3 개발 환경 구성·실행 순서
examples/part01/ch03/ch03_call.py           사용처 조회·문서 검색 MCP 예제
examples/part01/ch03/ch03_where_used.cypher 그래프 사용처 조회 예제
labs/mfg-bom-agent/             제조 실습 런타임·데이터·테스트
DISTRIBUTION.json              배포본의 원본 코드 커밋
```

제조 프로젝트의 전체 런타임은 Ch3에서 에이전트 화면까지 실행하는 데 필요합니다. 수량·원가 계산 구현, 검색 조정, 에이전트 작성·평가는 이후 제조 강의에서 단계별로 다룹니다. 바이오 프로젝트는 이 배포본에 포함하지 않았습니다.

## 개발 모드 실행 요약

아래 명령은 `labs/mfg-bom-agent` 폴더에서 실행합니다. Docker는 서버 프로그램을, uv는 로컬 Python과 패키지를 준비합니다.

```bash
cp -n .env.example .env
uv sync --all-extras
```

`.env`에 본인의 Neo4j 비밀번호, LLM API 키, 임베딩 API 키, Langfuse 초기 로그인 값을 입력합니다. 이 강의에서는 별도 MCP 서버를 사용하므로 다음 값도 설정합니다.

```dotenv
MCP_TRANSPORT=http
MCP_URL=http://localhost:8000/mcp
DEMO_MODE=none
```

서비스를 실행합니다. 이미 제조 데이터를 적재한 환경에서는 데이터 초기화 명령을 건너뜁니다.

```bash
docker compose up -d neo4j langfuse-web
docker compose ps
# 처음 준비하는 제조 실습 전용 DB에서만 실행
uv run python scripts/init_data.py
uv run python scripts/check_env.py
```

초기화는 전용 실습 DB에 데이터를 다시 적재하고 검사·문서 연결·색인을 실행합니다. 작업 중인 다른 데이터베이스에 연결하지 않습니다.

별도 터미널에서 MCP 서버를 실행합니다.

```bash
uv run python -m mfg_bom_agent.mcp_server
```

다른 터미널에서 앱을 실행합니다.

```bash
uv run streamlit run src/mfg_bom_agent/ui.py
```

- 실습 앱: http://localhost:8501
- Neo4j Browser: http://localhost:7474
- MCP: http://localhost:8000/mcp
- Langfuse: http://localhost:3000

## 예제 실행

제공된 부품표에서 휠 `3616-0014-0144`의 사용처를 개정판 `6b2c5a9`로 조회합니다. 다른 판을 조회했다면 결과표의 개정판 ID를 사용하세요.

```bash
uv run python ../../examples/part01/ch03/ch03_call.py where_used --part 3616-0014-0144 --revision 6b2c5a9
uv run python ../../examples/part01/ch03/ch03_call.py search_docs --mode hybrid
```

사용처의 `sku / revision / lines / paths`와 검색의 `mode / effective_mode / hits`를 확인합니다. 언어 모델 API와 임베딩 API는 별도 설정입니다.

| 실행 모드 | 확인할 범위 |
|---|---|
| `none` | 실제 LLM 호출과 도구 실행 |
| `fixed_llm` | LLM 응답 고정, 도구는 실제 실행 |
| `canned` | 저장된 화면 예시. 현재 연결 성공의 증거로 사용하지 않음 |

실제 LLM·임베딩 호출에는 사용 중인 공급자의 요금이 적용될 수 있습니다. `fixed_llm`도 임베딩 API까지 대체하지는 않습니다.

## 문서와 코드의 기준

Ch3의 설치·초기화·실행은 [Ch3 실행 안내](docs/ch03-run-guide.md)와 [공통 상세 설치 가이드](docs/setup/README.md)를 기준으로 진행합니다. OS별 설치 문서에도 공개 저장소 경로와 같은 초기화·MCP 연결 설정을 안내합니다. 성공 여부는 실제 스크립트 출력으로 확인합니다.

문서의 화면 캡처와 개발 과정의 실행 기록은 이 공개 배포본에서 제외했습니다. 정상 여부는 실제 도구 반환값과 앱의 처리 과정으로 확인합니다.

## 데이터와 출처

부품·정비 문서 데이터의 원천은 NASA JPL Open Source Rover입니다. 실습용 가상 공급사·가격 이력·변경 조건은 공개 사실과 구분해 사용합니다.

- [원천 데이터와 스냅샷](labs/mfg-bom-agent/data/raw/SOURCES.md)
- [외부 자료 출처](THIRD_PARTY_NOTICES.md)
- [NASA JPL Open Source Rover 라이선스](labs/mfg-bom-agent/third_party/nasa-jpl-open-source-rover/LICENSE.txt)

개인 `.env`, API 키, 개발 저장소의 Git 이력, 실행 로그, 내부 캡처는 포함하지 않습니다. 설정값 예시는 `.env.example`에서 확인합니다.

## Part 2 · Ch1 — 부품 변경 질문과 데이터 이해

[강의별 Hands-on 안내](docs/part02/ch01/README.md): 업무 질문·CQ 작성 → Neo4j 관찰 조회 → 원본과 가공 데이터 대조 → 출처·가정·시점 기록. 조회문 3개와 작성용 CSV 표를 제공합니다.

## Part 2 · Ch2 — 부품 데이터 연결과 정리

[매핑·정규화 Hands-on 안내](docs/part02/ch02/README.md): 한 행 실행 예제, 매핑표·단위 규칙 표, 오류 수정 과제, 읽기 전용 Neo4j 조회문.

## Part 2 · Ch3 실습 자료

[제조 온톨로지와 변경 모델 · 원본 diff · Neo4j 조회 · 작성 표](docs/part02/ch03/README.md)

## Part 2 · Ch4 — 지식 그래프 적재와 경로 조회

[적재 코드·Neo4j 조회·Hands-on·작성 표](docs/part02/ch04/README.md): 전용 DB 재적재 → 실제 건수·규칙 검증 → 같은 판 사용처 → 수량 재료 대조.

## Part 2 · Ch5 — 정비 문서와 Hybrid Search

[원문·청크·개체 연결·BM25/벡터/RRF·그래프 경로 실습](docs/part02/ch05/README.md)

## Part 2 · Ch6 — 수량·원가 계산과 MCP 도구

[계산 작성 과제·CSV 검산·MCP 호출·도구 계약표](docs/part02/ch06/README.md)

## Part 2 · Ch7 — 계산·검증 에이전트

[질문 계획·호출 분기·되묻기·Langfuse·답변 오류 검사](docs/part02/ch07/README.md)

## Part 2 · Ch8 — 기준 문항 평가와 오류 분석

[실제 오류 수정·12문항 회귀·새 질문 설계](docs/part02/ch08/README.md)

## Part 1~3 실행 예제 찾기

[examples 전체 목차](examples/README.md)에서 Part와 Chapter별 파일·실행 위치를 확인합니다. [Part 1](examples/part01/) · [Part 2](examples/part02/) · [Part 3](examples/part03/)
