# Langfuse 사용 가이드 — mfg-bom-agent

Langfuse 는 에이전트가 **무엇을 묻고, 어떤 도구를 부르고, 얼마가 들었는지** 기록하고 보는 화면이다. Neo4j Browser 가 데이터를 보는 창이라면, Langfuse 는 에이전트의 행동을 보는 창이다. 이 실습에서는 "LLM 은 해석만, 계산은 도구가"라는 설계가 실제로 지켜졌는지 확인하는 데 쓴다.

- 주소: http://localhost:3000 (바이오 실습은 http://localhost:3100)
- 계정: `.env` 의 `LANGFUSE_INIT_USER_EMAIL` / `LANGFUSE_INIT_USER_PASSWORD`
- 기준: Langfuse 4.70.0 설치형(self-host), 2026-10-25 캡처

Langfuse 가 아직 떠 있지 않다면 [INSTALL.md](../INSTALL.md) 의 5단계(Neo4j 와 Langfuse 띄우기)를 먼저 한다. 설치형 구성의 설계 근거는 강의 자료 `개발환경_정의서.md` 11.1절.

> **이 문서의 캡처는 `--mock` 데모로 만든 데이터다.** 캡처 당시 Anthropic API 크레딧이 없어 LLM 답변만 미리 정한 문장으로 바꿔 실행했다. LangGraph 흐름 · 도구 호출 · 금액 계산 · 점수는 실제로 실행된 결과이고, 비용이 $0 으로 보이는 이유도 이 때문이다. 자세한 내용은 [4절](#4-기본-세팅과-데모-트레이스).

## 목차

1. [Langfuse 가 기록하는 것](#1-langfuse-가-기록하는-것)
2. [로그인](#2-로그인)
3. [미리 해 둔 기본 세팅](#3-미리-해-둔-기본-세팅)
4. [기본 세팅과 데모 트레이스](#4-기본-세팅과-데모-트레이스)
5. [홈 대시보드](#5-홈-대시보드)
6. [Tracing — 실행 기록 찾기](#6-tracing--실행-기록-찾기)
7. [트레이스 상세](#7-트레이스-상세)
8. [도구 호출 들여다보기](#8-도구-호출-들여다보기)
9. [Graph 탭](#9-graph-탭)
10. [같은 질문, 다른 결과](#10-같은-질문-다른-결과)
11. [Sessions 와 Scores](#11-sessions-와-scores)
12. [실패한 호출 추적](#12-실패한-호출-추적)
13. [자주 막히는 곳](#13-자주-막히는-곳)

---

## 1. Langfuse 가 기록하는 것

질문 하나가 처리되는 동안 일어난 일 전체를 기록한다.

```text
질문 → 에이전트(LangGraph) → LLM 호출 (Claude Haiku 5.5)
                           → 도구 호출 (where_used · change_impact) → 답변
└──────────────────── 트레이스(Trace) 하나 ────────────────────┘
```

| 용어 | 뜻 | 비유 |
|---|---|---|
| **Trace** | 질문 하나에 대한 전체 기록. 목록에서 한 행이 트레이스 하나 | 택배 한 건의 배송 조회 화면 |
| **Observation** | 트레이스 안의 각 단계. LLM 호출은 Generation, 도구는 Tool, 나머지는 Span | 집하 → 이동 → 배달 같은 각 구간 |
| **Session** | 여러 트레이스를 묶는 단위. 한 사람의 대화나 같은 실험을 모아 본다 | 한 사람이 보낸 택배 모음 |
| **Score** | 트레이스에 매긴 점수. 이 실습은 "정답 금액이 들어 있나"를 0 · 1 로 남긴다 | 점수표 |

실습 코드는 LangGraph 실행에 Langfuse `CallbackHandler` 를 붙여 이 기록을 자동으로 보낸다 (정의서 7.2).

---

## 2. 로그인

설치형이라 내 PC 에서 바로 열린다. 외부 계정이 필요 없고 데이터도 밖으로 나가지 않는다.

（화면 캡처는 강의 자료에서 확인합니다.）

| 단계 | 항목 | 넣을 값 |
|---|---|---|
| 1 | 주소 열기 | http://localhost:3000 (바이오 실습은 3100) |
| 2 | Email | `.env` 의 `LANGFUSE_INIT_USER_EMAIL` (`.env.example` 기본값 `admin@mfg-bom-agent.local`) |
| 3 | Password | `.env` 의 `LANGFUSE_INIT_USER_PASSWORD` |
| 4 | Sign in | 프로젝트 "제조 BOM 변경 영향 에이전트" 홈으로 바로 간다 |

**Sign up(회원가입)은 하지 않는다.** 계정 · 조직 · 프로젝트 · API 키는 Langfuse 가 처음 뜰 때 `.env` 값으로 자동 생성된다.

---

## 3. 미리 해 둔 기본 세팅

수강생이 따로 설정할 것은 없다. `docker compose up -d langfuse-web` 한 줄로 아래가 모두 준비된다.

| 항목 | 내용 |
|---|---|
| 설치형 6개 컨테이너 | langfuse-web · langfuse-worker · postgres · clickhouse · redis · minio (`compose.langfuse.yaml`) |
| 조직 · 프로젝트 · 계정 자동 생성 | Ontology Lecture / 제조 BOM 변경 영향 에이전트 / admin |
| API 키 = `.env` 값 | 앱이 트레이스를 보낼 때 쓰는 키. 화면에서 따로 발급하지 않는다 |
| Claude Haiku 5.5 가격 내장 | Langfuse 기본 모델 목록에 `claude-haiku-5-5` 토큰 단가(입력 $0.10 / 출력 $0.50, 100만 토큰당)가 이미 들어 있어 비용이 자동 계산된다 |

**Settings → API Keys** 를 열면 `.env` 의 공개 키가 "Provisioned API Key" 로 등록되어 있다. 비밀 키는 가려져 보인다.

（화면 캡처는 강의 자료에서 확인합니다.）

> 화면의 `.env` 예시는 `LANGFUSE_BASE_URL` 이라는 이름을 쓰지만, 이 저장소는 `LANGFUSE_HOST` 를 읽어 클라이언트에 직접 넘긴다. `.env.example` 그대로 두면 된다.

---

## 4. 기본 세팅과 데모 트레이스

새로 띄운 Langfuse 는 비어 있다. 화면을 채워 보려면 데모 스크립트 [`scripts/langfuse_demo.py`](../scripts/langfuse_demo.py) 를 실행한다.

```bash
uv run python scripts/langfuse_demo.py
```

| 단계 | 하는 일 |
|---|---|
| 질문 | "Yellow Jacket 모터(부품번호 5203) 단가가 15% 오르면 로버 1대 원가는 얼마나 늘어나?" |
| 조건 A `llm-only` | Claude 에게 그냥 묻는다. 데이터가 없으니 정확한 금액을 낼 수 없다 |
| 조건 B `graph+tools` | LangGraph 에이전트가 `where_used` · `change_impact` 도구를 부르고, 금액은 도구가 Decimal 로 계산한다 |
| 기록 | 두 트레이스를 같은 세션으로 묶고, 태그(`demo`, 조건 이름) · 메타데이터(request_id, dataset_version)를 붙인다 |
| 점수 | 정답 금액($38.69)이 답에 들어 있으면 `correct_amount` = 1 |

Claude Haiku 5.5 를 3~4번 호출한다 (비용 1센트 미만). 도구와 BOM 값은 데모용 고정값이다 (모터 단가 $42.99 는 parts_list.csv 실제 값) — 실제 도구는 `src/mfg_bom_agent/tools/` 에 구현한다.

### API 크레딧 없이 화면만 확인하기

```bash
uv run python scripts/langfuse_demo.py --mock
```

`--mock` 은 LLM 답변만 미리 정한 문장으로 바꾼다 (모델 이름 `mock-llm`, 태그 `mock`). LangGraph 흐름 · 도구 호출 · 금액 계산 · 점수는 실제로 실행된다. 실제 모델을 부르지 않으므로 토큰 · 비용은 0 으로 기록된다.

실행이 끝나면 세션 ID 와 트레이스 주소가 출력된다.

```text
session: demo-mock-27baf412   expected: $38.69
llm-only     correct_amount=0  http://localhost:3000/project/mfg-bom-agent/traces/...
graph+tools  correct_amount=1  http://localhost:3000/project/mfg-bom-agent/traces/...
```

---

## 5. 홈 대시보드

로그인하면 처음 보는 화면이다. 전체 상황을 한눈에 보는 계기판.

（화면 캡처는 강의 자료에서 확인합니다.）

| 번호 | 영역 | 설명 |
|---|---|---|
| ① | Traces | 기록된 트레이스 수와 이름별 개수 |
| ② | Model costs | 모델별 토큰 수와 비용(USD) |
| ③ | Scores | 점수 이름별 개수와 평균 |
| ④ | Observations by level | 단계 수 추이. ERROR 가 있으면 여기서 먼저 보인다 |
| ⑤ | Model usage | 시간대별 비용 · 토큰 사용량 |
| ⑥ | 기간 선택 | Past 1 day 처럼 보고 싶은 기간을 바꾼다. 데이터가 안 보이면 여기부터 확인 |

캡처 화면 읽는 법:

- 트레이스 5건 = 데모 `--mock` 두 번(4건) + 크레딧 부족으로 실패한 실제 호출 1건
- 비용 $0.00 = mock 은 실제 모델을 부르지 않았고, 실패한 호출은 토큰을 쓰지 않았다
- `correct_amount` 평균 0.5 = 네 번 중 두 번(graph+tools)만 정답
- ERROR 3 = 실패한 호출의 단계들 ([12절](#12-실패한-호출-추적))

---

## 6. Tracing — 실행 기록 찾기

사이드바 **Tracing** 을 누르면 열린다. 실습 중 가장 오래 보는 화면이다.

（화면 캡처는 강의 자료에서 확인합니다.）

| 번호 | 영역 | 설명 |
|---|---|---|
| ① | 필터 | 이름 · 태그 · 세션 · 사용자로 좁힌다. Name 에서 `llm-only` / `graph+tools` 를 체크해 비교 |
| ② | 트레이스 목록 | 한 행이 질문 하나. 시간 · 이름 · 타입이 보인다 |
| ③ | Input · Output | 질문과 최종 답을 목록에서 바로 미리 본다 |
| ④ | 기간 · 새로고침 | 방금 실행한 결과가 안 보이면 몇 초 기다리고 새로고침 — worker 가 저장하는 데 조금 걸린다 |

---

## 7. 트레이스 상세

목록에서 행을 누르면 트레이스가 열린다. 단계가 나무(트리)처럼 보인다.

（화면 캡처는 강의 자료에서 확인합니다.）

| 번호 | 영역 | 설명 |
|---|---|---|
| ① | 관측 트리 | 위에서 아래로 실행 순서. graph+tools → LangGraph → agent → 모델 → tools → where_used · change_impact → agent |
| ② | 요약 배지 | 걸린 시간 · 세션 · 사용자 · 점수(`correct_amount: 1.00`) · 태그 |
| ③ | Tree · Timeline · Graph | 같은 기록을 나무 · 시간 막대 · 흐름도로 본다 |
| ④ | 선택한 단계의 내용 | 트리에서 고른 단계의 Input · Output · Attributes · Scores |

트리 아이콘으로 단계 종류를 구분한다: 모델 호출(Generation), 도구(Tool), 나머지(Span).

---

## 8. 도구 호출 들여다보기

트리에서 `change_impact` (Tool) 단계를 누르면 도구의 입력과 출력이 그대로 보인다.

（화면 캡처는 강의 자료에서 확인합니다.）

| | 값 | 의미 |
|---|---|---|
| Input | `part_id: 5203`, `price_change_percent: 15` | LLM 이 질문에서 뽑아낸 인자 |
| Output | `delta_per_rover_usd: 38.69` | 도구가 Decimal 로 계산한 값 |

계산: 단가 $42.99 × 15% × 로버 1대당 6개 = $38.691 → 센트 반올림 **$38.69**

> 이 문서의 스크린샷은 단가를 실제 값으로 바로잡기 전($44.99, 정답 $40.49)에 찍었다. 화면 구성은 같고 금액만 다르다.

**LLM 은 해석만, 계산은 도구가.** 답변의 $38.69 는 이 출력에서 왔다. 모델은 어떤 도구를 부를지 고르고, 결과를 문장으로 옮겼을 뿐이다. 답이 틀리면 이 화면에서 "도구 계산이 틀렸는지, 모델이 인자를 잘못 뽑았는지, 옮기다 틀렸는지"를 바로 가를 수 있다.

---

## 9. Graph 탭

트레이스 상세에서 **Graph** 탭을 누르면 LangGraph 흐름이 그대로 그려진다.

（화면 캡처는 강의 자료에서 확인합니다.）

| 노드 | 뜻 |
|---|---|
| `__start__` | 질문이 들어오는 시작점 |
| `agent (2/2)` | 모델을 부르는 노드. 괄호는 이 트레이스에서 두 번 실행됐다는 뜻 — 도구를 고를 때 한 번, 답을 쓸 때 한 번 |
| `tools` | 도구를 실행하는 노드. agent 와 왕복한다 |
| `__end__` | 도구가 더 필요 없으면 끝난다 |

노드 이름은 코드의 `add_node` 이름과 같다. 설계한 흐름대로 돌았는지 바로 확인할 수 있다.

```python
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(tools))
graph.add_conditional_edges("agent", tools_condition)
graph.add_edge("tools", "agent")
```

**Aggregated / Expanded** 로 반복 실행을 묶어 보거나 펼쳐 볼 수 있다.

---

## 10. 같은 질문, 다른 결과

두 트레이스의 Output 을 나란히 놓으면 차이가 분명하다.

**LLM 단독** — `correct_amount` 0

（화면 캡처는 강의 자료에서 확인합니다.）

데이터가 없으니 단가 30달러 · 수량 4개를 추측해 약 18달러라고 답했다.

**그래프 + 도구** — `correct_amount` 1

（화면 캡처는 강의 자료에서 확인합니다.）

`where_used` · `change_impact` 를 불러 $38.69 와 계산 가정을 밝혔다.

점수가 0 · 1 로 자동 기록되므로 문항을 늘리면 정확도를 숫자로 비교할 수 있다. 실습 후반 Golden Set 평가가 이 모양을 그대로 키운 것이다.

> 위 캡처는 `--mock` 실행분이라 LLM 답변 문장은 미리 정해 둔 것이다. 도구 호출 · 계산 · 점수는 실제로 실행됐다. 크레딧이 있으면 `--mock` 없이 다시 실행해 실제 Haiku 답변으로 확인한다.

---

## 11. Sessions 와 Scores

**Sessions** — 같은 `session_id` 를 가진 트레이스 묶음. 데모는 실행할 때마다 세션 하나에 llm-only · graph+tools 두 트레이스가 들어간다.

（화면 캡처는 강의 자료에서 확인합니다.）

세 번째 세션(`demo-745d2464`)은 크레딧 부족으로 실패한 실제 호출이다 (트레이스 1개).

**Scores** — 트레이스마다 매긴 점수 목록. 이름 · 값 · 설명(정답 $38.69 포함 여부) · 연결된 트레이스가 보인다.

（화면 캡처는 강의 자료에서 확인합니다.）

코드에서 남기는 법 ([`scripts/langfuse_demo.py`](../scripts/langfuse_demo.py) 참고):

| 남길 것 | 함수 |
|---|---|
| 세션 · 사용자 · 태그 · 메타데이터 · 트레이스 이름 | `propagate_attributes(...)` |
| 최상위 단계(에이전트 실행) | `langfuse.start_as_current_observation(name=..., as_type="agent")` |
| LangChain · LangGraph 호출 자동 기록 | `CallbackHandler()` 를 `config={"callbacks": [handler]}` 로 전달 |
| 점수 | `langfuse.create_score(trace_id=..., name=..., value=...)` |

---

## 12. 실패한 호출 추적

실패한 호출도 어느 단계에서, 어떤 입력으로, 무슨 메시지로 실패했는지 남는다.

（화면 캡처는 강의 자료에서 확인합니다.）

데모를 실제 모델로 처음 실행했을 때 Anthropic API 가 400 오류를 돌려줬다. 트리의 `llm-only` → `ChatAnthropic` → `anthropic.messages.create` 가 모두 빨간 **Error** 로 표시되고, 오른쪽에 메시지가 그대로 보인다.

```text
invalid_request_error: Your credit balance is too low to access the Anthropic API.
```

**찾는 법:** 홈의 Observations by level 에서 ERROR 개수 확인 → Tracing 목록에서 해당 트레이스 열기 → 트리의 빨간 Error 단계를 눌러 메시지 확인

| 자주 보는 오류 | 원인 |
|---|---|
| 400 `credit balance is too low` | Anthropic 계정 잔액 부족 |
| 401 | API 키 오류 |
| 404 | 모델 이름 오타 (`claude-haiku-5-5` 인지 확인) |
| 429 | 짧은 시간에 너무 많은 요청 |

> `scripts/check_env.py` 의 Anthropic 확인은 비용이 없는 Models API 조회라 키 유효성만 본다. 크레딧 부족은 실제 메시지 호출에서만 드러난다.

---

## 13. 자주 막히는 곳

| 증상 | 원인과 해결 | 확인 명령 (터미널) |
|---|---|---|
| 화면이 안 열려요 | 첫 기동은 DB 준비로 2~3분 걸린다. 아래 주소가 OK 를 돌려주면 접속한다 | `curl http://localhost:3000/api/public/health` |
| 트레이스가 안 보여요 | `.env` 의 `LANGFUSE_PUBLIC_KEY` · `LANGFUSE_SECRET_KEY` · `LANGFUSE_HOST` 를 확인한다. 키 하나라도 비면 트레이싱이 꺼진다. 기간 필터와 새로고침도 확인 | `uv run python scripts/check_env.py` |
| 비용이 $0 이에요 | `--mock` 실행이거나 호출이 실패한 경우다. 실제 모델로 실행하면 Haiku 5.5 단가로 자동 계산된다 | `uv run python scripts/langfuse_demo.py` |
| 데모 기록을 지우고 싶어요 | Langfuse 볼륨까지 지우면 처음 상태로 돌아간다. **Neo4j 데이터도 함께 지워진다** | `docker compose down -v` |

---

### 이미지 파일

공개 배포본에는 화면 캡처를 포함하지 않습니다. 화면 구성은 강의 자료와 실제 실행 화면에서 확인합니다.

Docker 로 이 실습을 켜고 끄고 초기화하는 방법은 [DOCKER.md](DOCKER.md) 를 본다.
