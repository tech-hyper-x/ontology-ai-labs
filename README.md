# Ontology AI Labs

온톨로지 기반 기업 AI 강의의 실습 코드와 실행 안내입니다.

필요한 문서를 빠르게 찾으려면 **[가이드 전체 지도 · SITEMAP](SITEMAP.md)**을 열어 주세요.

현재 학습 안내는 **Part 1 Ch3 공통 환경과 Part 2 Ch1~Ch4 제조 설계 실습**까지 포함합니다. 제조 실습 프로젝트를 이용해 개발 환경 구성, 그래프 사용처 조회, 문서 검색, MCP 직접 호출, 에이전트 답변 대조를 진행합니다.

## 시작하기

**Docker 설치부터 Neo4j·Langfuse 첫 접속까지:** [상세 설치 가이드](docs/setup/README.md) · [설치 시연 체크리스트](docs/setup/RECORDING.md)

```bash
git clone https://github.com/tech-hyper-x/ontology-ai-labs.git
cd ontology-ai-labs/labs/mfg-bom-agent
```

1. [OS별 설치 안내](labs/mfg-bom-agent/INSTALL.md)에서 본인 환경을 선택합니다.
2. [Ch3 실행 안내](docs/ch03-run-guide.md)에 따라 개인 설정·서비스·데이터·앱을 준비합니다.
3. [사용처 조회문](examples/ch03_where_used.cypher)을 Neo4j Browser에서 실행합니다.
4. [MCP 호출 예제](examples/ch03_call.py)로 같은 부품과 개정판을 조회합니다.
5. 실습 앱의 처리 과정과 최종 답변을 도구 반환 결과와 비교합니다.

Windows 명령은 WSL Ubuntu 터미널에서 실행합니다. Mac은 터미널을 사용합니다. 최초 도구 설치와 다운로드 시간은 강의의 설명·시연 배분과 별도입니다.

## 폴더

```text
docs/ch03-run-guide.md          Ch3 개발 환경 구성·실행 순서
examples/ch03_call.py           사용처 조회·문서 검색 MCP 예제
examples/ch03_where_used.cypher 그래프 사용처 조회 예제
labs/mfg-bom-agent/             제조 실습 런타임·데이터·테스트
DISTRIBUTION.json              배포본의 원본 코드 커밋
```

제조 프로젝트의 전체 런타임은 Ch3에서 에이전트 화면까지 실행하는 데 필요합니다. 수량·원가 계산 구현, 검색 조정, 에이전트 작성·평가는 이후 제조 강의에서 단계별로 다룹니다. 바이오 프로젝트는 이 배포본에 포함하지 않았습니다.

## 개발 모드 실행 요약

아래 명령은 `labs/mfg-bom-agent` 폴더에서 실행합니다. Docker는 서버 프로그램을, uv는 로컬 Python과 패키지를 준비합니다.

```bash
cp .env.example .env
uv sync --all-extras
```

`.env`에 본인의 Neo4j 비밀번호, LLM API 키, 임베딩 API 키, Langfuse 초기 로그인 값을 입력합니다. 이 강의에서는 별도 MCP 서버를 사용하므로 다음 값도 설정합니다.

```dotenv
MCP_TRANSPORT=http
MCP_URL=http://localhost:8000/mcp
DEMO_MODE=none
```

서비스 실행과 초기화:

```bash
docker compose up -d neo4j langfuse-web
docker compose ps
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

그래프에서 확인한 개정판 ID로 `확인한_ID`를 바꿉니다.

```bash
uv run python ../../examples/ch03_call.py where_used --revision "확인한_ID"
uv run python ../../examples/ch03_call.py search_docs --mode hybrid
```

사용처의 `sku / revision / lines / paths`와 검색의 `mode / effective_mode / hits`를 확인합니다. 언어 모델 API와 임베딩 API는 별도 설정입니다.

| 실행 모드 | 확인할 범위 |
|---|---|
| `none` | 실제 LLM 호출과 도구 실행 |
| `fixed_llm` | LLM 응답 고정, 도구는 실제 실행 |
| `canned` | 저장된 화면 예시. 현재 연결 성공의 증거로 사용하지 않음 |

실제 LLM·임베딩 호출에는 사용 중인 공급자의 요금이 적용될 수 있습니다. `fixed_llm`도 임베딩 API까지 대체하지는 않습니다.

## 문서와 코드의 기준

기존 OS 설치 문서 일부의 “임베딩은 나중에 설정”, “초기화는 제약 생성만 수행” 설명은 현재 코드와 차이가 있습니다. **Ch3에서는 [Ch3 실행 안내](docs/ch03-run-guide.md)와 실제 스크립트 출력을 기준으로 진행합니다.** OS별 도구 설치 절차는 각 설치 문서를 참고합니다.

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
