# 화면 설계 — Streamlit 실습 UI

제조 BOM 변경 영향 분석 에이전트의 Streamlit 화면과 UI–에이전트 인터페이스 설계다. 구현 전 문서이며, **이 문서에서 "(제안)"이 붙은 파일·함수·클래스는 아직 저장소에 없다.** 표기가 없는 이름은 저장소에서 확인한 것이다.

> **구현 상태 (2026-10-25)** — 이 설계대로 구현했다. "(제안)"으로 적힌 이름은 아래 실제 이름으로 반영됐다.
>
> | 설계의 이름 (제안) | 구현 |
> |---|---|
> | `contracts/answer.py` · `contracts/events.py` | 같은 이름. 이벤트에 단계 표시용 `StepNote` 를 추가 |
> | `workflows/bom_agent.py` — `run(request, on_event)` | 같은 이름. MCP 호출 통로는 `workflows/gateway.py` (`MCP_TRANSPORT=http` · `inprocess`) |
> | `ui_state.py` — `RunState`, `new_run_id()`, `get_run()` | `RunState`, `new_run_id()`, `get_runs()`, `add_run()` |
> | `ui.py` — `render_env_tab()` · `render_lab_tab()` · `render_answer()` · `render_timeline()` | 타임라인은 `execute()`(실행 중) 와 `render_answer()`(펼치기) 안에 있다 |
> | `data/golden/examples.yaml` | 같은 이름 |
> | `Settings.demo_mode` · 환경 변수 `DEMO_MODE` | 같은 이름. `canned` 응답은 `scripts/make_canned.py` 로 만든다 |
> | LangGraph 체크포인트 | `MemorySaver` (프로세스 메모리). 화면 프로세스가 재시작되면 대기 중인 되묻기는 사라진다 |

> **사용성 개선 (2026-10-25, 2차)** — 실제로 써 보니 결과와 개발자용 상세가 한꺼번에 보여 판단할 숫자가 묻혔다. 아래처럼 바꿨고, **2.3절의 "네 구역을 세로로, 접지 않고"는 이 내용으로 대체한다.** 근거를 숨기지 않는다는 원칙은 그대로지만, 모두 펼치지 않고 읽는 순서를 나눈다.
>
> | 문제 | 바꾼 것 | 위치 |
> |---|---|---|
> | 긴 제목 · 예시 버튼이 잘림 | 제목 "BOM 변경 영향 분석" + 한 줄 설명, 예시는 짧은 이름(`label`)으로 · 누르면 전체 질문이 입력창에 | `ui.py` `main` · `data/golden/examples.yaml` |
> | 실행 후에도 예시 · 진행 표시가 위를 차지 | 결과가 생기면 예시를 접고, 진행 표시는 실행이 끝나면 지운다. 새 결과가 맨 위, 이전 결과는 제목 목록(접힘) | `render_lab_tab` |
> | 수량 · 금액이 긴 문단과 표에 묻힘 | 첫 문장 답 → 결과 카드(인용 계산값 + 판단 카드) → 확인된 내용 → 추가로 확인할 사항 → 가정 · 기준 | `render_answer_body` · `render_cards` |
> | 계산표 · 경로가 가로로 잘림 | 근거는 오른쪽 탭 4개(계산 근거 · BOM 사용처 · 문서 · 실행 기록). 경로는 업무 문장("로버 1대당 4개"), 전체 표는 접힘 | `render_evidence` · `path_sentence` |
> | 세 방식 비교의 열이 너무 좁음 | 비교 요약표(답 · 핵심 수치 · 근거 수 · 계산 검증) + 고른 방식만 자세히 | `render_compare` |
> | 문서 원문이 그대로 노출 | 답변이 인용한 문서 먼저: 한국어 요약 → 관련 문장(발췌에 실제로 있는 문장만) → 원문(접힘) | `render_docs_tab` · `answer.keep_real_quotes` |
> | "검증 통과"가 답변 전체가 옳다는 뜻으로 읽힘 | "인용 계산값 N건 일치" + 검사 범위(수량 · 금액만, 문서 해석 · 원인 판단은 검사하지 않음) | `trust_line` |
> | 답변 문장이 도구 이름 · 산식 · 가정으로 길어짐 | 답변을 구역(headline · findings · follow_ups · notes · key_facts · doc_notes)으로 받고 산식은 계산 근거 탭으로 | `workflows/answer.py` · `skills/grounded-answer/SKILL.md` |
> | 트레이스 링크가 컨테이너 주소(`langfuse-web:3000`) | 브라우저 주소 `LANGFUSE_PUBLIC_URL` 로 바꿔 만든다 | `config.py` · `bom_agent._public_trace_url` |
>
> | 실행이 끝나면 진행 표시가 사라져 데이터를 찾아간 과정을 다시 볼 수 없음 | 결과 위에 접이식 "데이터를 찾아간 과정"(단계 · 도구 입력 · 결과 · 걸린 시간)을 남긴다. 내부 코드는 업무 용어로 | `render_process` · `event_line` |
> | 실행 방식이 사이드바에 있어 실행 직전에 찾기 어려움 | 질문 위 가로 라디오 하나로: 지식 그래프 + 도구 · RAG · LLM 단독 · 세 방식 비교 | `render_lab_tab` |
>
> | 제목만으로는 어떤 데이터인지 알 수 없음 | "로봇 차량 부품·원가 분석 에이전트"(왼쪽 위 NASA OSR BOM LAB) + 데이터 설명 한 줄. 한글은 단어 단위로 줄바꿈 | `main` |
> | 사이드바에 고르는 것 · 바꾸는 것 · 읽는 것이 섞임 | 사이드바는 "분석 기준"만: 부품 구성 기준(날짜 · 변경 내용으로 선택, 해시는 상세에) + 접힌 "사용 중인 데이터"(자료 확인일 ≠ 가격 적용일) · "용어 안내". 역할 선택은 없앰 | `sidebar` · `load_revisions` |
> | 탭 이름이 하는 일을 설명하지 않음 · 연결 상태가 별도 탭 | 상단 탭을 없애고 연결 상태는 사이드바 맨 아래 "헬스체크"(서비스마다 색깔 점: 초록 연결됨 · 노랑 설정됨 · 빨강 확인 필요, 결과 1분 기억, 다시 확인) | `render_health_sidebar` · `health_rows` |
> | 예시 질문이 짧은 버튼에 압축돼 잘림 | "질문을 선택해 시작하세요": 업무(구매 수량·원가 · 부품 변경·단종 · 고장 점검·교체)를 고르면 그 업무의 카드 1~3장 — 카드 이름 · 전체 질문 · 확인할 내용 · 실습 가정 표시 · 선택됨. 누르면 입력창에 넣고 "답변 확인"으로 실행 | `render_lab_tab` · `data/golden/examples.yaml` (`work` · `shows` · `assumption`) |
> | 도구가 키로만 보임 | "구매 수량 계산(purchase_quantity)"처럼 이름(키), 입력도 "부품=… · 필요 수량(개)=120" | `tool_label` · `inputs_text` |
>
> | 금액이 무엇의 금액인지 모호함 ("로버 100대 소요 원가" = 실제로는 모터 600개 부품비) | 계산 이름에 대상 부품을 넣음(변경 전 · 후 · 추가 모터 부품비, 필요 모터 수량). 답변은 변화량(증가액)을 먼저, 카드 위에 "대상 · 계산 기준"을 한 번만 | `skills._noun` · `answer.py` 규칙 · `render_answer_body` |
> | 비교표 핵심 수치가 질문과 다른 값 · 답 칸이 상세 답변 복사 | 핵심 수치는 차이값을 우선(+$3,869.10), 답 칸은 한 줄 요약(summary, 기준선 방식도 요약을 받음) | `render_compare` · `baseline.py` |
> | 카드 4장 이상이면 좁아져 숫자가 끊김 | 4장 이상은 2 × 2, 같은 줄 높이 맞춤, 금액 · 수량은 한 줄 고정 | `render_cards` · `card_html` |
> | 본문 주의 문구가 길고 반복 | "계산 기준"(2~3개) · "실행 전에 확인할 사항"(1~2개), 가정 · 가격 기준은 접힌 "적용 조건 보기" | `render_answer_body` |
> | 근거 탭 이름이 무엇을 보는지 설명하지 않음 | 계산 내역 · 부품 사용 위치 · 참고 문서 · 처리 과정 + 탭마다 첫 줄 설명, "수량·단가·적용 조건 보기" | `render_evidence` |
> | 질문 카드 높이가 제각각 | 같은 줄 카드는 가장 큰 카드 높이로, 선택 버튼은 카드 맨 아래 | `render_lab_tab` (CSS) |
> | 질문 제목 · 로고 | 결과 위 질문은 큰따옴표로 감싼 검은색 제목. 왼쪽 위에는 글자만 "NASA OSR BOM LAB"(NASA 휘장 · 로고 이미지는 승인 없이 쓸 수 없어 쓰지 않음) | `question_title` · `assets/osr-lab-logo.svg` |
>
> 테마는 `.streamlit/config.toml`(Primary `#2d5bff`, 개발용 Deploy 메뉴 숨김). 화면 캡처: `docs/images/ui/`.

기본 방향은 "채팅 하나 + 근거 패널"이다. 사용자가 업무 질문을 입력하면 에이전트가 그래프 조회와 계산 도구를 실행하고, 화면은 결론 · 계산 결과 · 그래프 경로 · 출처 · 가정을 구조화된 형태로 보여 준다. 설계 근거는 설계 덱 03-B(에이전트 입력·출력 35장, 하네스 구성 36장, 도구 명세 40장, 스킬 41장)와 개발환경 정의서 2절(화면: 질문 입력, 영향 경로, 근거 카드, 결과 비교)이다.

---

## 1. 현재 코드에서 재사용할 부분과 새로 필요한 부분

### 1.1 재사용

| 파일 | 재사용 대상 | 화면에서의 용도 |
|---|---|---|
| `src/mfg_bom_agent/ui.py` | `check_neo4j()`, `check_anthropic()`, `check_mcp()`, `main()` | 환경 점검 탭. 네 항목의 확인 방식이 서로 다르므로 1.3의 표기 규칙으로 구분해서 보여 준다 |
| `src/mfg_bom_agent/config.py` | `Settings`, `get_settings()` · `dataset_version`, `llm_model`, `langfuse_enabled`, `langfuse_host`, `mcp_url`, `max_tool_calls`, `request_timeout_seconds` | 답변마다 보존할 실행 조건(데이터 버전, 모델), Langfuse 링크 생성, 실행 상한 |
| `src/mfg_bom_agent/graph/client.py` | `server_info()` | 환경 점검 탭의 Neo4j 항목. 실습 탭은 Neo4j를 직접 호출하지 않는다 |
| `src/mfg_bom_agent/mcp_server.py` | `ping`, `neo4j_status` | MCP 서버 생존 확인. 업무 도구는 `TODO(제조-구현)` 주석에 이름만 있다(`bom_explode`, `purchase_quantity`, `cost_rollup`, `where_used`, `change_impact`) |
| `scripts/langfuse_demo.py` | `MockLLM`, `mock_llm()`, `build_agent()`, `DEMO_BOM`, `change_impact()`, `where_used()`, `expected_answer()` | 데모 모드의 선례. LLM 응답만 고정하고 계산 함수는 실제로 실행하는 방식(7절) |
| `scripts/init_data.py` | `CONSTRAINTS` | 화면이 표시하는 개체 종류(Product, Assembly, BOMLine, Part, Supplier, Revision, ECN, DocumentChunk)의 식별자 이름 |
| `tests/test_smoke.py` | `Settings(_env_file=None)` 패턴 | 화면 상태·계약 테스트에서 설정을 만드는 방법 |

### 1.2 새로 필요한 것

| 위치 | 이름 (제안) | 역할 |
|---|---|---|
| `src/mfg_bom_agent/contracts/` | `answer.py` — `AnswerRequest`, `AnswerResponse`, `CalcResult`, `GraphPath`, `DocEvidence`, `Verification`, `RunContext` | 3절의 UI–에이전트 계약. Pydantic 모델 |
| `src/mfg_bom_agent/contracts/` | `events.py` — `RunEvent`와 하위 이벤트 | 4절·6절의 실행 이벤트 |
| `src/mfg_bom_agent/workflows/` | `bom_agent.py` — `run(request, on_event)` | LangGraph 에이전트 진입점. UI가 호출하는 유일한 함수 |
| `src/mfg_bom_agent/tools/` | 도구 9종 (덱 40장) | 에이전트가 MCP로 호출. UI는 호출하지 않는다 |
| `src/mfg_bom_agent/ui.py` | `render_env_tab()`, `render_lab_tab()`, `render_answer()`, `render_timeline()` 등 | 2절의 화면 구성. 기존 `check_*` 함수는 그대로 둔다 |
| `src/mfg_bom_agent/ui_state.py` | `RunState`, `new_run_id()`, `get_run()` | 5절·6절의 세션 상태 |
| `data/golden/examples.yaml` | 예시 질문 9개와 역할 | 2.2의 예시 질문 버튼 |

### 1.3 환경 점검 탭의 표기 규칙

현재 `ui.py`는 네 항목을 모두 `st.success`/`st.warning`으로 같은 모양으로 보여 준다. 확인 범위가 다르므로 다음과 같이 구분해 표기한다.

| 항목 | 현재 함수가 확인하는 것 | 표기 |
|---|---|---|
| Neo4j | `server_info()`가 Bolt로 접속해 버전·노드 수를 읽는다 | "연결 확인 · 노드 N개" |
| Anthropic API | `client.models.retrieve(s.llm_model)` — 키가 유효하고 모델 ID가 존재하는지. 메시지 호출은 하지 않는다 | "키 유효 · 모델 확인 (호출 미확인)" |
| MCP 서버 | `httpx.get(s.mcp_url)` — HTTP 응답 여부만. 405·406도 성공으로 본다 | "HTTP 응답 · 도구 목록 미확인" |
| Langfuse | `s.langfuse_enabled` — 키 두 개가 설정에 있는지만 | "키 설정됨 · 접속 미확인" |

"미확인"은 확인하지 않았다는 뜻이지 실패가 아니다. 실습 탭에서 첫 질문을 실행하면 MCP 도구 호출과 Langfuse 기록이 실제로 일어나므로, 그 결과를 환경 점검 탭에 "마지막 실행에서 확인됨"으로 갱신한다(제안).

---

## 2. 화면 구성과 주요 사용자 흐름

### 2.1 레이아웃

단일 페이지, 상단 탭 두 개("환경 점검", "실습"). 실습 탭은 사이드바와 메인 영역으로 나눈다. `st.navigation`의 다중 페이지 구조는 쓰지 않는다. 그래프 시각화 라이브러리와 원천 데이터 편집 기능도 넣지 않는다.

```
┌ 사이드바 ────────────────┐ ┌ 메인 (실습 탭) ────────────────────────────────┐
│ 역할                      │ │ 예시 질문 9개 (선택한 역할의 질문 강조)             │
│  ○ 생산계획·구매           │ │ [질문 입력란]                                   │
│  ○ 설계변경 엔지니어        │ │                                                │
│  ○ 정비·품질               │ │ ── 답변 1 ───────────────────────────────────── │
│                           │ │ 실행 조건: 역할 · 리비전 · 관측일 · 데이터 버전 · 방식 │
│ 기준 시점                  │ │ 결론                                            │
│  리비전  [최신 판 ▾]        │ │ 계산 결과 (항목 · 값 · 단위 · 도구 · 산식)          │
│  가격 관측일 [2026-10-22]   │ │ 그래프 경로 (텍스트)                             │
│  실제 가격 기준일: 미상      │ │ 문서 근거                                       │
│                           │ │ 출처 · 가정                                      │
│ 실행 방식                  │ │ 검증: 통과 3 / 미실행 0 / 불일치 0                 │
│  ◉ 지식 그래프 + 도구               │ │ ▸ 도구 호출 타임라인 (펼치기)                     │
│  ○ RAG                    │ │ ▸ 도구 입력·출력 상세 (펼치기)                     │
│  ○ LLM 단독               │ │ [Langfuse 트레이스 ↗]  ← 후속 단계                 │
│                           │ │                                                │
│ 실행 선택                  │ │ ── 추가 질문 (대기 중) ───────────────────────── │
│  ◉ 선택한 방식 실행         │ │ "servo" 후보 2개: ○ 2000-0025-0002 ○ 3202-0001-2501│
│  ○ 세 방식 비교            │ │ [선택 후 계속]                                   │
└───────────────────────────┘ └────────────────────────────────────────────────┘
```

### 2.2 예시 질문 9개와 역할별 강조

설계 덱 34장의 시나리오를 `data/golden/examples.yaml`(제안)에 둔다. 사이드바에서 역할을 고르면 그 역할의 질문이 앞에 오고 나머지는 흐리게 표시한다. 버튼을 누르면 질문 입력란에 채워지며, 실행은 사용자가 "실행"을 눌렀을 때만 한다.

| # | 역할 | 질문 | 조회 항목 | 계산 항목 |
|---|---|---|---|---|
| 1 | 생산계획·구매 | 로버 20대에 필요한 2-pack 부품의 구매 수량은? | BOM 라인 수량·배수, pack_size, MOQ | 소요 낱개 수, 구매 팩 수 |
| 2 | 생산계획·구매 | 로버 1대의 기계 BOM 원가와 어셈블리별 원가는? | 라인 단가·수량·배수 | 소요 원가(어셈블리별 합계) |
| 3 | 설계변경 | 커밋으로 재구성한 교육용 ECN 전후 차이는? | 두 리비전의 라인 | 추가·삭제·변경 라인 |
| 4 | 설계변경 | 서보 단종 가정 시 50대 소요량·금액·대체 후보는? | 사용처 경로, 수량·배수, 단가, ALTERNATE_OF | 소요 수량, 소요 금액 |
| 5 | 생산계획·구매 | goBILDA 공급 중단 가정 시 검토할 부품과 제품은? | 등록 공급사, 사용처 | — (목록) |
| 6 | 생산계획·구매 | 모터 단가 15% 인상 → 100대 원가 차이는? | 단가, 수량·배수 | 변경 전후 원가, 차이 |
| 7 | 정비·품질 | 코너 휠이 돌지 않을 때 점검할 부품과 교체 부품비는? | 문서 검색, 고장 모드, 부품 식별 | 선택 부품비(공임 제외) |

### 2.3 답변 영역 — 네 구역을 세로로 배치 (2차 개선으로 대체됨, 맨 위 표 참고)

결론 · 계산 근거 · 그래프 근거 · 출처·가정의 네 구역을 유지하되, 가로 네 칸으로 고정하지 않는다. 각 구역은 내용 길이만큼 세로로 이어지며 접지 않는다.

**결론** — 두세 문장. 수량·금액이 들어가면 그 옆에 도구 이름과 산식을 함께 쓴다.

> 단종 가정 시 50대에 서보 200개가 필요합니다. **소요 금액 $6,398.00 — `cost_rollup` 계산 · 200개 × $31.99/개.** 등록 대체품은 없습니다.

**계산 결과** — 표. 한 줄이 `CalcResult` 하나다(3.2). 소요 금액, 구매 금액, 변경에 따른 추가 비용은 항목명을 다르게 해서 섞이지 않게 한다.

| 항목 | 값 | 단위 | 도구 | 산식 | 리비전 | 관측일 |
|---|---|---|---|---|---|---|
| 서보 소요 수량 (50대) | 200 | ea | bom_explode | 2 × 2 × 50 | 최신 판 | — |
| 서보 소요 금액 | 6,398.00 | USD | cost_rollup | 200 × 31.99 | 최신 판 | 2026-10-22 |
| 구매 금액 | 미계산 | — | — | 구매 질문이 아니므로 산정하지 않음 | — | — |
| 단종 추가 비용 | 미확인 | — | — | 대체품·재작업 조건 없음 | — | — |

**그래프 경로** — 텍스트 경로와 라인 속성. 그래프 그림은 그리지 않는다.

> Rover → rocker bogie (배수 ×2) → BOMLine (qty 2 ea) → servo 2000-0025-0002 · `where_used`
> ALTERNATE_OF: 없음 · `supply_risk`

**문서 근거** — 검색 결과가 있을 때만 표시. 문서 경로, 절 위치, 발췌, 연결 신뢰도.

**출처 · 가정** — 데이터 스냅샷, 관측일, 실제 가격 기준일, 교육용 가정, 제외 항목.

> 스냅샷 a78f9eb · 관측일 2026-10-22 · 실제 가격 기준일 미상 · 단종은 교육용 가정 · 재고·공임 제외

**검증 배지** — 네 구역 위에 작게 표시. "통과 N · 미실행 N · 불일치 N". 기준은 3.4.

**펼치기 영역** — 도구 호출 타임라인(실행된 순서, 도구 이름, 소요 시간, 성공·오류), 도구별 입력·출력 JSON. 기본은 접혀 있고, 결론과 계산 결과는 항상 펼쳐져 있다.

### 2.4 주요 사용자 흐름

1. 실습 탭을 열면 환경 점검 요약 한 줄(연결 N/4)과 예시 질문 9개가 보인다.
2. 역할을 고르고 예시 질문을 누르거나 직접 입력한 뒤 "실행"을 누른다.
3. 사이드바의 리비전 · 관측일 · 실행 방식이 그 순간 복사되어 실행 조건이 된다(5절).
4. 실행 중에는 타임라인이 도구 하나가 끝날 때마다 한 줄씩 늘어난다.
5. 에이전트가 값을 되물으면 답변 자리에 "추가 질문" 블록이 나타나고, 사용자가 답하거나 후보를 고르면 같은 실행이 이어진다(4.3).
6. 완료되면 답변 영역이 채워지고, 이전 답변은 위로 밀려 그대로 남는다.
7. "세 방식 비교"를 고르고 실행하면 같은 조건으로 세 번 실행한 결과가 나란히 표시된다(2.5).

### 2.5 실행 방식과 비교 보기

실행 방식과 실행 선택은 별개의 설정이다.

| 설정 | 선택지 | 뜻 |
|---|---|---|
| 실행 방식 | 지식 그래프 + 도구 / RAG / LLM 단독 | 에이전트에 제공하는 데이터와 도구의 범위 |
| 실행 선택 | 선택한 방식 실행 / 세 방식 비교 | 한 번 실행할지, 같은 질문을 세 방식으로 각각 실행할지 |

비교 실행은 사용자가 "세 방식 비교"를 명시적으로 고른 뒤 "실행"을 눌렀을 때만 한다. 비교 실행에서는 질문 · 리비전 · 가격 관측일 · 데이터 버전을 한 번 복사해 세 실행에 똑같이 넘긴다.

세 결과는 가로 세 칸으로 나란히 두고, 칸마다 맨 위에 **제공한 데이터와 사용 가능한 도구**를 표시한다.

| 방식 | 제공 데이터 | 사용 가능한 도구 |
|---|---|---|
| 지식 그래프 + 도구 | Neo4j 그래프 · 벡터·전문 검색 | 9종 전부 |
| RAG | 문서 조각 검색만 | `search_docs`만 |
| LLM 단독 | 없음 (질문만) | 없음 |

근거 구역의 표시 규칙:
- 그 방식에서 쓸 수 없는 근거(예: LLM 단독의 그래프 경로)는 **"미사용"**.
- 쓸 수 있었지만 확인하지 못한 근거(예: RAG에서 검색 결과 없음)는 **"미확인"**.
- 빈 구역을 채우려고 에이전트가 근거를 생성하지 않는다. `AnswerResponse`에 해당 항목이 비어 있으면 화면도 비워 두고 위 표시만 붙인다.

---

## 3. UI–에이전트 요청 · 응답 · 이벤트 데이터 구조

모두 `src/mfg_bom_agent/contracts/`(제안)의 Pydantic 모델이다. UI는 자유 텍스트를 파싱해 답변 카드를 채우지 않는다. 에이전트가 아래 구조를 그대로 반환한다.

### 3.1 요청 — `AnswerRequest` (제안)

| 필드 | 타입 | 설명 |
|---|---|---|
| `run_id` | str | UI가 발급한 실행 ID. 재실행 중복 방지(6절) |
| `question` | str | 사용자 질문 원문 |
| `context` | `RunContext` | 실행 조건(아래) |
| `mode` | `"kg_tools" \| "rag" \| "llm_only"` | 실행 방식 |
| `resume` | `ResumeInput \| None` | 되묻기에 대한 답. 최초 요청은 None |

**`RunContext`** (제안) — 답변마다 보존하는 실행 조건

| 필드 | 타입 | 출처 |
|---|---|---|
| `role` | str | 사이드바 역할 |
| `revision` | str | 리비전 ID(커밋 해시) 또는 `"latest"` |
| `as_of` | date | 가격 관측일. 기본 2026-10-22(스냅샷) |
| `price_date_known` | bool | 실제 가격 기준일 존재 여부. 원천에 없으므로 False |
| `dataset_version` | str | `Settings.dataset_version` |
| `snapshot` | str | 원천 스냅샷 커밋 (a78f9eb) |
| `llm_model` | str | `Settings.llm_model` |
| `demo_mode` | `"none" \| "fixed_llm" \| "canned"` | 7절 |

### 3.2 응답 — `AnswerResponse` (제안)

| 필드 | 타입 | 화면 구역 |
|---|---|---|
| `run_id` | str | — |
| `status` | `"completed" \| "needs_input" \| "failed"` | 4.3 |
| `conclusion` | str | 결론 |
| `calculations` | list[`CalcResult`] | 계산 결과 표 |
| `graph_paths` | list[`GraphPath`] | 그래프 경로 |
| `documents` | list[`DocEvidence`] | 문서 근거 |
| `sources` | `SourceInfo` | 출처 · 가정 |
| `verification` | `Verification` | 검증 배지 |
| `trace` | `TraceInfo \| None` | Langfuse 트레이스 ID·URL (후속 단계) |
| `context` | `RunContext` | 실행 조건 표시 |
| `pending_question` | `PendingQuestion \| None` | `status == "needs_input"`일 때 |
| `error` | `ErrorInfo \| None` | `status == "failed"`일 때 |

**`CalcResult`** (제안) — 계산 결과 한 줄

| 필드 | 타입 | 예 |
|---|---|---|
| `label` | str | "서보 소요 금액" |
| `kind` | `"requirement" \| "purchase" \| "extra_cost" \| "diff"` | 소요 / 구매 / 추가 비용 / 변경 전후 차이 |
| `value` | Decimal \| None | 6398.00 (미계산이면 None) |
| `unit` | str | "USD", "ea", "pack" |
| `tool` | str | "cost_rollup" |
| `formula` | str | "200 × 31.99" |
| `inputs` | dict | `{"part_id": "2000-0025-0002", "qty_each": 200, "unit_price": "31.99"}` |
| `revision` | str | 적용 리비전 |
| `as_of` | date \| None | 가격 관측일 |
| `source` | str | "parts_list.csv@a78f9eb" |
| `note` | str \| None | "구매 질문이 아니므로 산정하지 않음" |

**`GraphPath`** (제안) — `nodes: list[{label, key, name}]`, `edges: list[{type, props}]`, `tool: str`, `revision: str`

**`DocEvidence`** (제안) — `doc_path`, `section`, `excerpt`, `linked_part_id`, `confidence`, `method`

**`SourceInfo`** (제안) — `snapshot`, `as_of`, `price_date_known`, `assumptions: list[str]`, `exclusions: list[str]`

**`Verification`** (제안) — 3.4

**`TraceInfo`** (제안) — `trace_id`, `url`(`Settings.langfuse_host` 기준), `session_id`

### 3.3 이벤트 — `RunEvent` (제안)

워크플로가 실행 중 UI에 보내는 이벤트. 모두 `run_id`와 `ts`를 가진다.

| 이벤트 | 필드 | 화면 반응 |
|---|---|---|
| `ToolStarted` | `tool`, `inputs` | 타임라인에 "실행 중" 줄 추가 |
| `ToolFinished` | `tool`, `outputs`, `elapsed_ms` | 같은 줄을 "완료"로 갱신 |
| `ToolFailed` | `tool`, `error` | 같은 줄을 "오류"로 갱신, 상세는 펼치기 |
| `InputRequested` | `PendingQuestion` | 추가 질문 블록 표시, 상태를 `waiting_input`으로 |
| `AnswerReady` | `AnswerResponse` | 답변 영역 채움, 상태를 `completed`로 |
| `RunFailed` | `ErrorInfo` | 오류 표시, 상태를 `failed`로 |

타임라인에는 `ToolStarted`/`ToolFinished`/`ToolFailed`로 실제 실행된 도구만 표시한다. 계획 단계에서 언급만 된 도구는 표시하지 않는다.

**`PendingQuestion`** (제안) — `kind: "missing_value" | "choose_candidate"`, `prompt`, `field`, `candidates: list[{id, name, detail}] | None`

### 3.4 검증 기준 — `Verification` (제안)

출력 검사(설계 덱 39장 `check` 노드)는 답변 문장 속 숫자와 도구 출력의 **문자열 일치**로 판정하지 않는다. 결론 문장이 인용한 각 수량·금액에 대해 다음 네 가지가 `CalcResult`와 일치하는지 본다.

| 검사 항목 | 통과 조건 |
|---|---|
| 항목 | 결론이 말하는 대상(예: 서보 소요 금액)이 `label`과 같다 |
| 값 | 결론의 숫자가 `value`와 같다(Decimal 비교, 센트 단위) |
| 단위 | 결론의 단위(개, 팩, USD)가 `unit`과 같다 |
| 계산 조건 | 결론이 전제한 리비전·관측일·대수가 `revision`, `as_of`, `inputs`와 같다 |

`Verification` 필드: `status: "passed" | "failed" | "not_run"`, `checks: list[{target, item_ok, value_ok, unit_ok, condition_ok}]`, `summary: {passed, failed, not_run}`.

`not_run`은 검사를 실행하지 않은 상태(LLM 단독 방식, 데모 canned 모드, 검사 노드 오류)다. 화면 배지는 통과와 미실행을 다른 색과 글자로 구분하고, 미실행을 통과로 보이게 하지 않는다.

---

## 4. 세션 상태와 되묻기 · 재시도 처리 방식

### 4.1 호출 경계

- UI는 `workflows/bom_agent.py`(제안)의 `run(request: AnswerRequest, on_event: Callable[[RunEvent], None]) -> AnswerResponse`만 호출한다.
- MCP 도구 호출은 에이전트(LangGraph의 `act` 노드)가 한다. UI는 `Settings.mcp_url`로 직접 요청하지 않는다. 환경 점검 탭의 `check_mcp()`는 생존 확인만 하며 도구를 호출하지 않는다.
- Neo4j도 UI가 직접 조회하지 않는다. 환경 점검의 `server_info()`는 예외로 둔다(정의서 4절: 적재·점검 스크립트만 드라이버 직접 사용).

### 4.2 세션 상태 — `RunState` (제안)

`st.session_state`에 대화 기록(문자열 목록)만 두지 않고, 실행 단위로 상태 객체를 둔다.

| 키 | 타입 | 내용 |
|---|---|---|
| `runs` | dict[run_id, `RunState`] | 실행별 상태 |
| `run_order` | list[run_id] | 화면 표시 순서 |
| `active_run_id` | str \| None | 지금 실행 중이거나 입력 대기 중인 실행 |
| `sidebar` | dict | 사이드바 현재 선택(다음 실행에만 쓰인다) |

**`RunState`**

| 필드 | 설명 |
|---|---|
| `run_id` | 발급 시각 + 난수. `new_run_id()`(제안) |
| `status` | `"queued" \| "running" \| "waiting_input" \| "completed" \| "failed"` |
| `request` | 실행 시점에 복사한 `AnswerRequest` (조건 고정) |
| `events` | list[`RunEvent`] — 타임라인 원본 |
| `response` | `AnswerResponse \| None` |
| `compare_group` | str \| None — 비교 실행이면 같은 그룹 ID |
| `started_at`, `finished_at` | 시각 |

실행 조건은 `request.context`에 복사돼 있으므로, 이후 사이드바를 바꿔도 이전 `RunState`는 변하지 않는다. 화면은 항상 `RunState.request.context`를 표시하고 사이드바 값을 다시 읽지 않는다.

### 4.3 되묻기(추가 입력)

1. 워크플로가 `InputRequested`를 보내면 UI는 `RunState.status = "waiting_input"`, `pending = PendingQuestion`으로 바꾸고 추가 질문 블록을 그린다.
2. 사용자가 값을 입력하거나 후보를 고르면 UI는 **같은 `run_id`**로 `AnswerRequest(resume=ResumeInput(field, value))`를 만들어 `run()`을 다시 호출한다. `question`과 `context`는 처음 복사한 값 그대로다.
3. 워크플로는 LangGraph 체크포인트(`thread_id = run_id`)에서 이어서 실행한다(제안). 이미 끝난 도구는 다시 호출하지 않는다.
4. 후보 선택 예: `find_part`가 "servo"에 대해 2000-0025-0002(servo)와 3202-0001-2501(servoblock)을 돌려주면 `choose_candidate` 질문이 되고, 사용자가 고른 `part_id`가 `resume.value`로 들어간다.

### 4.4 재실행 중복 방지

Streamlit은 입력이 바뀔 때마다 스크립트를 처음부터 다시 실행한다. 다음 규칙으로 같은 질문이 두 번 실행되는 것을 막는다.

- "실행" 버튼이 눌린 재실행에서만 `new_run_id()`를 발급하고 `RunState(status="queued")`를 만든다.
- 실제 `run()` 호출은 `status == "queued"`인 실행에 대해서만 하고, 호출 직전에 `status = "running"`으로 바꾼다. 재실행이 다시 와도 `running`이면 호출하지 않는다.
- 이벤트는 `on_event` 콜백에서 `RunState.events`에 쌓고, 화면은 `st.status` 컨테이너 안에서 `events`를 다시 그린다.
- `request_timeout_seconds`를 넘기면 `RunFailed(error.kind="timeout")`로 끝내고 `failed`로 둔다.

### 4.5 재시도

- `failed` 실행에는 "같은 조건으로 다시 실행" 버튼을 둔다. 새 `run_id`를 발급하되 `request.context`는 복사한다. 원래 실행은 지우지 않고 남긴다.
- `waiting_input`에서 사용자가 "취소"를 누르면 `failed(error.kind="cancelled")`로 닫는다.
- 비교 실행 중 한 방식이 실패해도 나머지 두 결과는 표시하고, 실패한 칸만 오류와 재시도 버튼을 보여 준다.

---

## 5. 첫 데모 범위와 후속 구현 범위

### 5.1 첫 데모 범위

| 항목 | 포함 내용 | 의존 |
|---|---|---|
| 예시 질문 7개 · 역할별 강조 | `examples.yaml`(제안), 사이드바 역할 | 없음 |
| 질문 입력과 네 구역 답변 | `AnswerResponse` → `render_answer()`(제안) | `contracts/answer.py` |
| 실제 계산 결과 · 도구 · 단위 표시 | `CalcResult` 표, 결론 속 산식 | 도구 `bom_explode`, `cost_rollup`, `where_used`, `find_part`, `supply_risk` |
| 도구 호출 타임라인 · 텍스트 그래프 경로 | `RunEvent` → `render_timeline()`(제안), `GraphPath` | `contracts/events.py`, `workflows/bom_agent.py` |
| 답변별 실행 조건 표시 | `RunContext` 고정 | `ui_state.py`(제안) |
| 환경 점검 탭 | 기존 `check_*` + 1.3 표기 | 없음 |

데모 시나리오는 4번(서보 단종)과 6번(모터 단가 15%)을 기준으로 한다. 두 질문은 `find_part` → `where_used` → `bom_explode` → `cost_rollup` 네 도구로 끝난다.

### 5.2 후속 구현 범위

| 항목 | 이유 |
|---|---|
| 세 방식 비교 보기 | Golden Set과 RAG 경로(`search_docs`, 벡터 인덱스)가 먼저 있어야 한다 |
| Langfuse 트레이스 링크 | `TraceInfo`를 채우려면 워크플로에 Langfuse 콜백이 붙어야 한다. 환경 점검의 "접속 미확인"도 그때 갱신 |
| 상세 출력 검사(`Verification`) | `check` 노드 구현 후. 그 전까지 배지는 항상 `not_run` |
| 되묻기 중 후보 선택 | `find_part`가 후보와 점수를 돌려준 뒤 |
| 시나리오 1·3·5·7 | `purchase_quantity`, `revision_diff`, `search_docs` 구현 후 |

### 5.3 넣지 않는 것

그래프 시각화 라이브러리(pyvis, graphviz 등), 원천 데이터 편집·발주 기능, `st.navigation` 다중 페이지, UI에서의 MCP·Neo4j 직접 호출.

---

## 6. 대표 사례 — "서보 단종 가정 시 50대 소요량 · 금액 · 대체 후보"

실행 조건: 역할 설계변경 엔지니어 · 리비전 최신 판(a78f9eb) · 가격 관측일 2026-10-22 · 실제 가격 기준일 미상 · 데이터 버전 mfg-0.1 · 방식 지식 그래프 + 도구 · 데모 모드 없음.

원천 값(`parts_list.csv`@a78f9eb): rocker bogie 어셈블리에 servo 2000-0025-0002가 라인 수량 2, 어셈블리 배수 2, 단가 $31.99, 팩 표기 없음(낱개 1로 가정).

### 6.1 화면 표시

**실행 조건** (답변 상단 한 줄)
`설계변경 · 리비전 a78f9eb(최신) · 관측일 2026-10-22 · 실제 기준일 미상 · mfg-0.1 · 지식 그래프 + 도구`

**검증** `통과 2 · 미실행 0 · 불일치 0`

**결론**
> 단종을 가정하면 50대 생산에 서보 2000-0025-0002가 **200개** 필요합니다 — `bom_explode` 계산 · 2개 × 배수 2 × 50대.
> 스냅샷 단가 기준 **소요 금액 $6,398.00** — `cost_rollup` 계산 · 200개 × $31.99/개.
> 등록된 대체품은 없습니다. 단종에 따른 추가 비용과 생산 중단 여부는 이 조회로 확정되지 않습니다.

**계산 결과**

| 항목 | 값 | 단위 | 도구 | 산식 | 리비전 | 관측일 |
|---|---|---|---|---|---|---|
| 서보 소요 수량 (50대) | 200 | ea | bom_explode | 2 × 2 × 50 | a78f9eb | — |
| 서보 소요 금액 | 6,398.00 | USD | cost_rollup | 200 × 31.99 | a78f9eb | 2026-10-22 |
| 구매 금액 (팩·MOQ) | 미계산 | — | — | 구매 질문 아님 · 팩 1 · MOQ 1(교육용) 가정 시 소요 금액과 같음 | — | — |
| 단종 추가 비용 | 미확인 | — | — | 대체품 · 재작업 조건 없음 | — | — |

**그래프 경로**
> `where_used` · 리비전 a78f9eb
> Rover → HAS_BOM_LINE → rocker bogie (multiplier 2) → HAS_BOM_LINE → BOMLine (qty 2 ea) → REFERS_TO → servo 2000-0025-0002
> `supply_risk` · ALTERNATE_OF: 없음 · 등록 공급사: goBILDA 1곳 (단일 공급 표시)

**문서 근거** — 이 질문은 문서 검색을 쓰지 않았다. "미사용"

**출처 · 가정**
> parts_list.csv @ a78f9eb · 관측일 2026-10-22 · 실제 가격 기준일 미상 · 단종은 교육용 가정 · 팩 1 · MOQ 1은 교육용 가정 · 재고 · 공임 · 운송비 제외

**▸ 도구 호출 타임라인** (펼치기)

| 순서 | 도구 | 상태 | 소요 |
|---|---|---|---|
| 1 | find_part | 완료 · 후보 1 (2000-0025-0002) | 0.3s |
| 2 | where_used | 완료 · 경로 1 | 0.2s |
| 3 | bom_explode | 완료 · 200 ea | 0.1s |
| 4 | supply_risk | 완료 · 대체품 0 · 공급사 1 | 0.2s |
| 5 | cost_rollup | 완료 · 6,398.00 USD | 0.1s |

**▸ 도구 입력 · 출력 상세** (펼치기) — 각 도구의 `inputs`/`outputs` JSON.

### 6.2 같은 질문의 되묻기 예

질문을 "서보 단종 가정 시 50대 …"가 아니라 "**servo** 단종 시 50대 …"로 입력하면 `find_part`가 후보 2개를 돌려준다.

> **추가 질문** — "servo"에 해당하는 부품이 2개입니다. 어느 부품인가요?
> ○ 2000-0025-0002 · servo · rocker bogie · $31.99
> ○ 3202-0001-2501 · servoblock · rocker bogie · $29.99
> [선택 후 계속]

선택하면 같은 `run_id`로 이어지고, 타임라인 1번 줄(`find_part`)은 그대로 둔 채 2번부터 추가된다. 실행 조건 줄은 바뀌지 않는다.

### 6.3 데모 모드일 때의 표시

7절의 `fixed_llm` 모드로 같은 질문을 실행하면 실행 조건 줄 끝에 다음 표시가 붙는다.

`데모 모드 · LLM 응답 고정 · 계산 도구 실제 실행 · Neo4j 미사용 (데모 BOM)`

이때 계산 결과 표의 `source`는 `DEMO_BOM`이 되고, 그래프 경로 구역은 "미사용 (데모 BOM은 경로를 갖지 않음)"으로 표시한다.

---

## 7. 데모 모드의 범위와 설정 방식

### 7.1 현재 `--mock`의 동작

`scripts/langfuse_demo.py`의 `main()`은 `"--mock" in sys.argv[1:]`로 모드를 정한다. `mock_llm()`이 `MockLLM`(정해 둔 `AIMessage`를 순서대로 반환)을 만들고, `build_agent()`로 만든 LangGraph가 `where_used()`·`change_impact()` 도구를 **실제로 호출**한다. 데이터는 `DEMO_BOM`(모터 5203 · $42.99 · 로버당 6개) 하나이며 Neo4j는 쓰지 않는다. Langfuse에는 모델 이름 `mock-llm`, 태그 `mock`으로 기록된다.

### 7.2 화면의 데모 모드 두 가지

| 모드 | LLM | 계산 도구 | 데이터 | Neo4j · MCP | 화면 표시 |
|---|---|---|---|---|---|
| `fixed_llm` | 고정 응답(`MockLLM` 방식) | 실제 실행 | `DEMO_BOM` 또는 적재된 그래프 | 적재된 그래프가 있으면 사용, 없으면 미사용 | "데모 모드 · LLM 응답 고정 · 계산 도구 실제 실행 · (Neo4j 사용/미사용)" |
| `canned` | 호출 안 함 | 실행 안 함 | 미리 저장한 `AnswerResponse` JSON | 미사용 | "화면 예시 · 실제 실행 아님 · 검증 미실행" |

`canned`는 화면 구성만 보여 주는 용도다. 타임라인은 저장된 이벤트를 "예시"로 표시하고 소요 시간은 보여 주지 않는다. `Verification.status`는 항상 `not_run`이다.

### 7.3 설정 방식 (제안)

실행 인자와 환경 변수를 혼용하지 않는다. 화면은 `Settings`에 `demo_mode: Literal["none", "fixed_llm", "canned"] = "none"` 필드를 추가해 **환경 변수 `DEMO_MODE`** 하나로만 정한다. `scripts/langfuse_demo.py`의 `--mock`은 스크립트 전용으로 그대로 두고, 화면이 그 스크립트를 호출하지는 않는다.

데모 모드 값은 `RunContext.demo_mode`에 복사되어 답변마다 남는다. 실제 Neo4j·MCP·LLM을 쓰지 않은 실행은 환경 점검 탭의 "마지막 실행에서 확인됨" 갱신에 반영하지 않는다.

---

## 부록 — 구현 순서 (제안)

1. `contracts/answer.py`, `contracts/events.py` — 3절 모델과 테스트(`tests/test_contracts.py`)
2. `ui_state.py` — `RunState`, 중복 실행 방지, 조건 고정 테스트
3. `workflows/bom_agent.py` — `run()` 골격. 처음엔 `canned` 모드로 저장된 응답을 돌려줘 화면을 먼저 완성
4. `ui.py` — 탭 분리, 예시 질문, 답변 네 구역, 타임라인
5. 도구 4종(`find_part`, `where_used`, `bom_explode`, `cost_rollup`)과 `fixed_llm` 모드 연결
6. 시나리오 4·6 실제 실행 확인 → 첫 데모 완료
