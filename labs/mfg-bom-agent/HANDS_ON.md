# Hands-on 구간 안내 (Part 2 제조 실습)

코드 안의 `[Hands-on P2-ChX-Y 제목] 시작` ~ `[Hands-on P2-ChX-Y] 끝` 주석이 커리큘럼 Clip 하나의 실습 범위다.
수강생 배포판에서는 이 구간을 비우거나 일부를 빈칸으로 바꾸고, 아래 "확인 방법"으로 결과를 검증한다.

구간 목록을 다시 뽑으려면:

```bash
grep -rn "Hands-on P2-" src scripts queries data/golden
```

## 전체 실행 순서

| 단계 | 명령 | 결과 |
|---|---|---|
| 1. 원천 → 교육용 테이블 | `uv run python scripts/build_dataset.py` | `data/processed/*.csv` (원천이 있을 때만. 배포판에는 결과가 이미 들어 있다) |
| 2. 그래프 적재 + 온톨로지 검증 | `uv run python scripts/load_graph.py` | Neo4j 노드 · 관계, 검증 31개 위반 0 |
| 3. 문서 연결 + 검색 색인 | `uv run python scripts/build_index.py` | DESCRIBED_IN 연결, 전문 · 벡터 색인 |
| 4. 테스트 | `uv run pytest -q` | 계산 · CQ · 도구 · 에이전트 테스트 |
| 5. 화면 | `uv run streamlit run src/mfg_bom_agent/ui.py` | 예시 질문 9개 실행 |
| 6. 평가 | `uv run python scripts/run_eval.py` | `outputs/eval/<시각>/report.md` |

2~3단계는 `uv run python scripts/init_data.py` 한 번으로도 된다 (컨테이너: `docker compose --profile init run --rm init`).

## Clip 별 구간

| Clip | 실습 내용 | 파일 (구간) | 확인 방법 |
|---|---|---|---|
| Ch1-1 변경 영향 질문 정의 | 업무 질문 9개(하이브리드 검색 질문 2개 포함)와 답에 필요한 수량 · 가격 · 개정 시점 | `data/golden/examples.yaml` | 화면 예시 질문 버튼 |
| Ch1-2 공개 데이터와 교육용 재구성 | 원천(source) · 파생(derived) · 교육용 가정(virtual · assumption) 구분 | `src/mfg_bom_agent/foundation/virtual.py` | `data/processed/data_inventory.json` |
| Ch2-1 부품 · 구매 데이터 매핑 | 원천 열 → 공통 필드, 구매 링크 → 공급사 | `foundation/normalize.py` (`map_parts_row`, `supplier_from_url`) | `data/processed/crosswalk.csv` |
| Ch2-2 단위와 식별자 정규화 | 팩 크기 추출, 내부 부품 ID, 가격 Decimal. 수량 예외(0.5팩 · 4개입) 확인 | `foundation/normalize.py` (`extract_pack_size`, `make_part_id`) | `tests/test_calc.py`, `data/processed/data_quality_issues.csv`, 과제 `scripts/exercise.py ch2_2_pack` |
| Ch3-1 BOM 변경 사례 모델링 | 커밋 → BOM 판 · 적용 구간 · 교육용 ECN · 대체(SUPERSEDES) | `foundation/ecn.py` | `data/processed/plm_ecn.csv` (모터 5202→5203, 스페이서 단종 대체 #469) |
| Ch3-2 제조 온톨로지와 검증 규칙 | 필수 속성 · Domain/Range · 카디널리티 · 순환 · 중복 검사 | `ontology/schema.yaml`, `src/mfg_bom_agent/ontology.py` | `scripts/load_graph.py` 의 "위반 0" |
| Ch4-1 부품 그래프 적재 | processed 테이블 → 노드 · 관계 (파라미터 쿼리) | `graph/load.py` | Neo4j Browser, `tests/test_graph.py` |
| Ch4-2 영향 경로 Cypher 작성 | 부품 → 어셈블리 → 제품 경로와 경로별 수량 곱 | `queries/cq_01_where_used.cypher` (CQ 15개 전체: `queries/`) | `tests/test_graph.py::test_cq01_where_used` |
| Ch5-1 정비 문서 인덱스 연결 | 문서 청크(경로 · 절 · 행), 부품 별칭 연결, 잘못된 연결 고치기 | `retrieval/chunking.py`, `retrieval/linking.py` (`LINK_OVERRIDES`, `apply_overrides`) | `scripts/build_index.py` 출력, 과제 `scripts/exercise.py ch5_1_link` |
| Ch5-2 Hybrid Search와 그래프 경로 결합 | 전문 + 벡터 RRF, 문서 → 부품 → 어셈블리. 질문 임베딩을 만들 수 없으면 hybrid → BM25 로 바꾸고 경고 (다른 공급자 벡터로 몰래 바꾸지 않음) | `retrieval/hybrid.py` (`query_vector`, `hybrid_search`) | "corner wheels will not turn" 검색, `tests/test_retrieval.py` (임베딩 장애 주입) |
| Ch6-1 결정론적 원가 계산 | 낱개 · 소요 원가 · 구매 팩 수 · 반올림 1회 | `tools/calc.py` | `tests/test_calc.py` ($6,398.00, $38.69) |
| Ch6-2 계산 도구 MCP 연결 | 도구 9종 입력 · 출력 계약, 오류 · 기준 시점 · 단위 | `tools/bom_tools.py`, `mcp_server.py` | MCP 클라이언트로 `cost_rollup` 호출 |
| Ch7-1 질문별 도구 호출 경로 | 질문 유형 → 스킬 → 도구 순서, 불필요한 호출 제거 | `workflows/skills.py`, `skills/*/SKILL.md` | 화면 타임라인 |
| Ch7-2 답변 근거 검증 | 답변을 구역으로 나눠 쓰기(첫 문장 답 · 확인된 내용 · 확인할 사항 · 가정). 인용 값의 항목 · 값 · 단위 · 조건 · 증감 방향 대조, 인용 0건 실패, 문장 속 수량(1대당 · N대 총량 · 팩)도 도구 값과 대조. 실패 시 한 번 재작성, 그래도 실패하면 LLM 문장을 내리고 계산 결과만 표시 | `workflows/answer.py` (`verify`, `withheld_answer`) | `tests/test_verify.py`, 과제 `scripts/exercise.py ch7_2_answer` |
| Ch7-3 실행 화면과 근거 패널 | 첫 문장 답 · 결과 카드 · 근거 탭(계산 근거 · BOM 사용처 · 문서 · 실행 기록), 세 방식 비교 요약표 | `ui.py` (`render_answer`, `render_compare`) | 화면 (`docs/images/ui/`) |
| Ch8-1 기준 문항 실행과 오류 분석 | Golden Set 45문항 채점(채점 규칙 v2: 최종 답변 기준 · 단위 · 증감 방향 · 집합 정확 일치), 도구 정답과 답변 정답 · 보류를 나눠 집계, 실패 원인 분류 | `evaluation/scoring.py`, `scripts/run_eval.py` (`--rescore`) | `outputs/eval/*/report.md`, `tests/test_evaluation.py`, `docs/EVAL_RESULTS.md` |

## Ch8 오류 분석 예시 (실제 평가에서 나온 실패)

| 문항 | 실패 원인 | 수정 방향 |
|---|---|---|
| G23 공용 부품 · G24 corner 구성 부품 | CQ-03 · CQ-04 는 그래프로 답할 수 있지만 **에이전트 도구가 없다** (온톨로지 ↔ 하네스 역방향 확인 실패) | `bom_structure(assembly, shared)` 도구를 추가하고 스킬에 연결 |
| (수정 전) 원가 질문 4건 | 질문 계획이 "로버"를 부품으로 보고 find_part 를 불러 실패 | 부품을 특정하지 않는 질문 유형은 부품 식별을 건너뜀 (`PART_INTENTS`) |
| (수정 전) 교체 이력 2건 | SUPERSEDES 를 돌려주는 도구가 없었음 (CQ-08) | `where_used` 출력에 `replaced` · `replaced_by` 추가 |
| (수정 전) "2024-11 ECN 원가 차이" | 질문 계획이 원가(cost)로 분류 | 계획 프롬프트에 "ECN · 날짜가 있으면 revision_change" 규칙 추가 |
| (수정 전) 코너 휠 증상 답변 "서보는 로버에 2개" | 경로의 라인 수량(qty 2)을 로버당 수량으로 잘못 옮김. 실제는 2 × 배수 2 = 4개. 출력 검사는 금액만 대조해 놓침 (Ch7-2 사례) | where_used 가 로버당 수량(each_per_product)을 계산해 경로에 표시. 출력 검사 v2 가 문장 속 "1대당 N개"를 로버당 수량과 대조해 이 답을 실패로 잡는다 (`scripts/exercise.py ch7_2_answer`) |
| (2차 개선) 답변 형식 변경 후 G29 실패 | 모델이 목록 칸(findings)을 JSON 문자열로 돌려줘 스키마 검증 실패 → 실행 중단 | `AnswerDraft` 에서 문자열 목록을 풀어 받음 + 회귀 테스트 (`tests/test_agent.py`) |

## 직접 고쳐 보기 (오류 한 건 수정 과제)

완성본을 실행하고 끝내지 않고, 틀린 입력 한 건을 재현 → 수정 → 확인 → 되돌리기까지 해 본다.
입력은 `data/exercises/exercises.yaml` 의 작은 예시뿐이고 Neo4j · LLM 을 쓰지 않는다. 실행 중인 그래프는 바뀌지 않는다.

| 과제 | 시작 입력 (재현) | 고칠 곳 | 확인 명령 | 고치기 전 → 후 |
|---|---|---|---|---|
| Ch2-2 포장 단위 | 품명 "8mm ID Spacer … (Pack of 4)", 원천 0.5팩 · 배수 2 | `foundation/normalize.py` `_PACK_PATTERN` (Hands-on P2-Ch2-2 구간) — "Pack of N" 표기도 잡기 | `uv run python scripts/exercise.py ch2_2_pack` | 팩 크기 1 · 1대당 1개 (실패) → 팩 크기 4 · 1대당 4개 (통과). 기존 "25-pack" 행도 그대로 통과해야 한다 |
| Ch5-1 잘못된 문서 연결 | 바퀴 배선 문서가 "servo" 를 두 번 언급해 서보 P-2000-0025-0002 에 자동 연결 | `retrieval/linking.py` `LINK_OVERRIDES` 에 `("exercise/wheel_wiring.md#1", "P-2000-0025-0002", "remove")` | `uv run python scripts/exercise.py ch5_1_link` | 서보 연결 남음 (실패) → 서보 연결 제거 · 휠 연결 유지 (통과) |
| Ch7-2 틀린 답변 잡기 | 도구는 1대당 4개인데 "서보는 로버 1대당 2개입니다", 인용 없음 (검토 보고서 F1) · 감소를 "증가"로 쓴 답 · 낱개를 팩으로 쓴 답 | `workflows/answer.py` `verify` (Hands-on P2-Ch7-2 구간). 배포판에서 이 구간을 비우면 처음에는 실패한다 | `uv run python scripts/exercise.py ch7_2_answer` | 틀린 답 3건이 모두 failed, 맞는 답은 passed |

- 되돌리기: `git checkout -- src/` (고친 코드를 처음 상태로). 과제 입력 파일은 바꾸지 않는다.
- 실제 그래프에 반영해 보려면(선택) 고친 뒤 `uv run python scripts/build_index.py` — 강사 PC 의 공용 DB 대신 각자 실행한 Neo4j 에서만 한다.
- Ch7-2 출력 검사의 범위: 수량 · 금액 · 생산 대수 · 증감 방향의 숫자 대조다. 문장 전체의 뜻이 맞는지 자동으로 보증하지 않는다.

## 실패 표시와 감사 기록

| 상황 | 화면 · 응답 |
|---|---|
| 출력 검사 실패 → 한 번 다시 써서 통과 | "✅ 인용 계산값 N건 일치 (한 번 고쳐 씀)" |
| 다시 써도 실패 | LLM 문장을 내리고 계산 결과만 표시. "⚠️ 답변 검증 실패 — 계산 결과만 표시", 실행 기록 탭에 문제 코드(인용 누락 · 값 · 단위 · 조건 · 증감 방향) |
| 인용 0건 · 계산값 없음 | 녹색으로 표시하지 않음 ("⚪ 대조한 계산값 없음") |
| 질문 임베딩 장애 | 문서 검색을 BM25 만으로 실행, 경고 표시. 검색 순위 표의 벡터 열은 "미실행" |
| 단종 질문의 정비 문서 조회 실패 | 계산은 끝까지 돌려주고 "정비 문서 조회 실패 — 문서가 없다는 뜻이 아님"을 적용 조건에 남김 |
| 모든 실행 | `outputs/runs/<run_id>.jsonl` 에 시작 · 도구 성공/실패 · 검사 · 종료 기록 (Langfuse 와 별개, 키 · 암호 미기록). role 은 화면에서 고른 설명이며 인증된 사용자가 아니다 (`authenticated: false`) |

MCP 업무 도구 실패는 자동으로 다시 부르지 않는다 (입력 오류는 다시 불러도 같고, 연결 오류는 시간만 늘린다). LLM 호출만 전송 재시도 2회(`max_retries=2`)가 있고, 답변 재작성 1회와는 따로 센다.
