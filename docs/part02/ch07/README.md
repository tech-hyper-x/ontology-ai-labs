# Part 2 · Ch7 — 계산·검증 에이전트 구현

Ch6에서 직접 호출한 계산 도구를 질문별 실행으로 연결합니다. 16강은 질문 구조화·되묻기·호출 분기, 17강은 답변 근거와 수치 검사입니다. 각각 20분·15분 계획이며, 설치와 추가 연습은 별도입니다.

모든 명령은 `ontology-ai-labs/labs/mfg-bom-agent`에서 실행합니다. [환경 안내](../../setup/README.md)와 [Ch6](../ch06/README.md)를 먼저 확인하세요. Ch7에서는 DB를 재적재하거나 색인을 다시 만들지 않습니다.

## 16강 · 질문에서 도구 실행까지

### 1. 질문을 계산 조건으로 바꾸기

```bash
uv run python ../../examples/ch07_plan.py
uv run python ../../examples/ch07_plan.py --question "서보 2000-0025-0002 단종 시 대체 후보는?"
uv run python ../../examples/ch07_plan.py --question "2024-06 원가 차이는?"
```

기본 해석기는 `rule_plan`입니다. 모터 질문에서 `price_change`, 품번 `5203-2402-0027`, 100대, 변경률 15를 추출하는지 확인합니다. 서보 질문의 `units`는 `null`입니다. 날짜만 있는 마지막 질문은 현재 규칙에서 `cost`로 분류됩니다.

실제 모델의 계획은 다음 선택 명령으로 확인합니다. 본인의 API 설정과 사용료가 필요하며, 규칙 해석 결과와 다를 수 있습니다.

```bash
uv run python ../../examples/ch07_plan.py --llm
```

유형과 조건은 `QuestionPlan`, 일반 조회 판은 `RunContext.revision`에 있습니다. 계획의 `change_ref`는 ECN·판 변경 비교를 위한 참조입니다.

### 2. 질문별 경로를 코드와 대조하기

[plan.py](../../../labs/mfg-bom-agent/src/mfg_bom_agent/workflows/plan.py), [skills.py](../../../labs/mfg-bom-agent/src/mfg_bom_agent/workflows/skills.py), [bom_agent.py](../../../labs/mfg-bom-agent/src/mfg_bom_agent/workflows/bom_agent.py)를 읽고 [경로 기록표](worksheets/route-record.csv)를 작성합니다.

|질문|현재 주요 MCP 호출|
|---|---|
|제품 전체 원가|cost_rollup|
|모터 단가 변경|find_part → where_used → change_impact|
|서보 단종|find_part → where_used → bom_explode → supply_risk → cost_rollup → search_docs|
|코너 휠 증상|search_docs → where_used → cost_rollup|

LLM은 유형과 조건을 구조화하고, Python 분기는 도구 순서를 결정합니다. 스킬 문서는 계획·답변의 업무 기준이며, 문서만 고쳐도 호출 코드가 바뀌는 것은 아닙니다. 스킬 내용은 캐시되므로 문서를 수정한 뒤 실행 프로세스를 재시작합니다. 문서의 요약과 호출 순서가 다르면 실제 코드를 기준으로 기록합니다.

### 3. 호출 분기 두 개 작성하기

```bash
uv run python ../../examples/ch07_route.py
```

[작성 파일](../../../examples/ch07_route.py)의 `execute`는 처음에 `NotImplementedError`를 냅니다. 준비된 계획을 받아 다음 두 분기를 구현하세요.

- `cost`: `cost_rollup(units, revision)`만 호출합니다.
- `price_change`: `where_used(part, revision)` 다음에 `change_impact(change_type="price_percent", part, value=percent, units, revision)`를 호출합니다.

AI에게 구현을 요청할 때도 호출 목록과 인자를 명시하세요. 기대 목록과 검사기를 유지하고 함수만 수정합니다. 같은 명령으로 검사한 뒤 [해설](../../../examples/ch07_route_solution.py)과 비교합니다.

이 연습의 `FakeGateway`는 호출 순서와 인자만 기록합니다. 품번 식별과 입력 확인이 끝난 계획을 사용하는 작은 연습입니다. 실제 연결은 다음 단계에서 확인합니다.

### 4. 실제 실행과 되묻기 확인하기

Neo4j·MCP 설정과 Ch4~6 데이터가 필요합니다. `MCP_TRANSPORT=http`이면 별도 서버를 실행하고, `inprocess`이면 같은 서버 객체를 사용합니다.

```bash
uv run python ../../examples/ch07_run.py
uv run python ../../examples/ch07_run.py --question "서보 2000-0025-0002 단종 시 대체 후보는?" --answer 50
```

첫 명령은 모터 질문의 호출 이벤트와 최종 응답을 출력합니다. 제공 판 `6b2c5a9`·100대·15% 조건의 기대 부품비 증가액은 **$3,869.10**입니다. 실제 출력의 조건·경로·금액을 기록표에 남깁니다.

두 번째 명령은 `needs_input`을 확인하고 같은 프로세스·같은 `run_id`에서 생산 대수 50을 응답합니다. 직접 입력하려면 `--answer`를 생략하세요. `MemorySaver`는 메모리에 있으므로 프로그램을 종료하면 체크포인트도 사라집니다.

기본 `fixed_llm`은 규칙 계획·정형 답변을 사용하며 도구는 실제 실행합니다. 단종·증상 경로의 `search_docs`는 임베딩 API를 호출할 수 있습니다. 실제 모델의 계획·답변은 `--demo-mode none`으로 확인합니다. `canned`는 런타임의 저장 예시이며 이 CLI의 선택에서는 제외했습니다. 연결 실패는 실패로 기록하고, 저장 예시를 현재 연결 성공의 증거로 사용하지 않습니다.

현재 정책에서 `cost`·`price_change`·`revision_change`는 생산 대수 기본값 1을 사용합니다. `discontinue`·`purchase_quantity`에서는 생산 대수가 필수입니다. 계획의 유형을 먼저 읽고, 되물은 항목과 기본값으로 사용한 항목을 구분해 기록하세요.

### 5. Langfuse에서 같은 실행 추적하기

Ch3에서 연결한 Langfuse를 실제 실행 기록과 연결합니다. 위 기본 명령의 `fixed_llm`은 실제 도구를 호출하지만 **Langfuse 트레이스는 생성하지 않습니다**. `audit_path`의 로컬 JSONL과 구분하세요.

본인의 모델 API와 [Langfuse 프로젝트 설정](../../setup/README.md)이 준비되면 같은 모터 질문을 실제 모델 모드로 실행합니다. API 사용료가 발생합니다.

```bash
uv run python ../../examples/ch07_run.py --demo-mode none
```

1. 최종 응답의 `run_id`와 `trace.url`을 확인하고 URL을 새 창에서 엽니다. 앱에서는 **Langfuse 트레이스 열기 ↗**를 사용할 수 있습니다.
2. 트레이스 metadata의 `run_id`가 방금 실행과 같은지 확인합니다.
3. 질문 해석, 도구 호출, 답변 생성의 실제 관측 기록을 펼쳐 입력·출력과 소요시간을 읽습니다. 표시 이름과 순서는 실제 실행에 따라 확인합니다.
4. `plan`의 출력에서 `intent=price_change`, 품번·100대·15%를 확인하고, `act`의 출력 `skill_out.calculations`에서 입력 조건·판·반환 금액을 대조합니다. 같은 조건의 기대 증가액은 `3869.10 USD`입니다. 개별 `change_impact` 항목의 입력·출력이 비어 있으면 이 상위 단계와 터미널 `tool_started`/`tool_finished`를 함께 봅니다. 원래 도구 인자의 변경률 키는 `value`, 계산 결과의 `inputs`에는 `percent`로 기록됩니다.
5. 답변이 이 결과를 어떻게 인용했는지 확인하고 실행 번호·트레이스 주소·지연 단계·대조 결과를 경로 기록표에 남깁니다.

중첩 계측으로 같은 이름의 도구·모델 항목이 두 겹 보일 수 있습니다. 실제 호출 수는 응답의 `tool_calls`와 이벤트 `call_id`로 확인하고, 부모·자식 항목의 토큰이나 비용을 중복 합산하지 않습니다. 2026-11-08 모터 예제 실제 모델 실행에서는 도구 3회, 답변 검사 통과, 증가액 `3869.10 USD`, 동일 실행 번호의 Langfuse 저장까지 확인했습니다. 이 단일 사례를 전체 정답률로 해석하지 않습니다.

`trace=null`이거나 화면에 기록이 없으면 성공으로 처리하지 않습니다. 실제 키는 노출하지 말고 프로젝트 키·주소·수집 상태를 점검하세요. 로컬 `audit_path`에서는 도구 입력과 출력을 확인할 수 있습니다. `scripts/langfuse_demo.py --mock`은 별도의 계측 데모이며 실제 에이전트 실행 트레이스를 대신하지 않습니다.

## 17강 · 답변에 오류를 넣어 검사하기

```bash
uv run python ../../examples/ch07_verify.py
uv run python scripts/exercise.py ch7_2_answer
uv run pytest -q tests/test_verify.py tests/test_agent.py -k 'not workflow'
```

첫 예제는 실제 [verify 함수](../../../labs/mfg-bom-agent/src/mfg_bom_agent/workflows/answer.py)를 작은 입력으로 검사합니다. DB·LLM 없이 실행하며 원천 데이터와 그래프를 수정하지 않습니다. 정답 1건과 오류 6건의 `expected`·`actual`·`checks`·`issues`를 읽습니다.

|오류|입력한 답변|
|---|---|
|값|1대당 4개를 2개로 작성|
|단위|낱개 200개를 200팩으로 작성|
|조건|50대 계산을 100대 요청에 인용|
|방향|검사용 -13.98달러 차이를 증가라고 작성|
|미확인 값|추가 비용 null을 0달러로 작성|
|인용 누락|계산값은 있지만 cited가 없음|

`-13.98`은 별도의 검사용 가상 값이며 Ch6 모터 인상액과 무관합니다. 서보 경로의 검사 입력은 조립품당 2개·팩 크기 1·배수 2로, 제품당 4개입니다.

[사례 파일](worksheets/answer-cases.json)을 복사해 새 문장 하나를 추가하세요. 예상 판정과 이유를 [검사 기록표](worksheets/verification-record.csv)에 먼저 적고 실행합니다.

```bash
cp ../../docs/part02/ch07/worksheets/answer-cases.json /tmp/ch07-my-cases.json
uv run python ../../examples/ch07_verify.py --cases /tmp/ch07-my-cases.json
```

WSL/Linux/macOS 터미널 기준입니다. 기존 기대값과 런타임 검사기는 유지합니다. 잘못된 답변을 `failed`로 탐지하면 과제 검사는 통과한 것입니다. 추가한 문장에서 예상과 다르면 어떤 표현을 검사하지 못했는지 기록하세요.

## 재작성·보류와 검사 범위

실제 `none` 모드에서는 검사 실패 → 오류 피드백으로 1회 재작성 → 같은 기준으로 재검사를 진행합니다. 계속 실패하면 `withheld`로 LLM 문장을 내리고 도구 계산 결과를 중심으로 표시합니다. `fixed_llm`에서는 실제 모델 재작성을 하지 않습니다. `ch07_verify.py`는 검사 함수만 실행하므로 전체 재작성 흐름의 통합 검증은 아닙니다.

`passed`는 검사 범위 내 일치, `failed`는 불일치, `not_run`은 계산 결과 등 대조 대상이 없음을 뜻합니다. 계산값이 있는데 인용이 0건이면 실패입니다. `keep_real_quotes`는 인용문이 제공 발췌에 없으면 비우지만 문서의 의미를 검증하지는 않습니다. 수치 검사와 별도로 고장 원인·교체 적합성을 검토해야 합니다. 판 미지정을 허용하는 등 현재 계약의 한계도 함께 기록합니다.

앱의 계산 내역·부품 사용 위치·참고 문서·처리 과정으로 돌아가 근거를 확인하세요. 역할 선택은 실제 인증·인가 구현이 아니며 권한 설계는 Part 4에서 다룹니다.

## Ch8에 넘길 결과

계획·호출 경로표, 되묻기·재개 기록, 작성한 호출 분기, 오류 사례·검사 기록을 저장합니다. Ch8에서는 GoldenSet 45문항과 독립 reference를 사용해 데이터·온톨로지·도구/스킬·답변/검사 오류를 나눕니다. CQ-03/04의 전용 도구 누락도 개선 대상으로 남깁니다.

[강사용 진행 메모](INSTRUCTOR.md)
