# Part 2 · Ch8 — 기준 문항 실행과 오류 분석

Ch7에서 남긴 도구 결과와 답변 검사 기록을 기대 답과 대조합니다. 18강 20분 계획이며 설치와 45문항 × 3방식 전체 실행은 별도입니다. [Ch7](../ch07/README.md)과 [환경 안내](../../setup/README.md)를 먼저 확인하세요.

아래 명령은 모두 `ontology-ai-labs/labs/mfg-bom-agent`에서 실행합니다. 기존 데이터·그래프를 재적재하거나 기준 답을 덮어쓰지 않습니다.

## 1. 조건과 기대 답 읽기

```bash
uv run python ../../examples/ch08_reference.py
```

[참조 확인 예제](../../../examples/ch08_reference.py)는 `build_golden.build()`를 호출해 CSV에서 계산한 문항과 배포 문항을 비교합니다. 파일을 저장하는 `main()`은 호출하지 않습니다.

기준은 Golden Set 1.1, snapshot `a78f9eb`, 최신 판 `6b2c5a9`입니다. 문항에 지정된 과거 판·ECN은 그 조건으로 읽습니다. 45문항은 수량 10·원가 10·관계 탐색 10·Revision/ECN 8·문서 근거 7입니다.

- G01: 서보 50대 총소요량 200 ea
- G16: 모터 단가 15% 인상·100대 부품비 증가액 3869.10 USD
- G36: 2023-10-04 ECN 전후 1대 차이 13.98 USD **감소**

[reference.py](../../../labs/mfg-bom-agent/src/mfg_bom_agent/evaluation/reference.py)는 업무 도구와 Neo4j를 쓰지 않지만 같은 processed CSV를 사용합니다. 원천 자료 자체의 정확성은 별도로 확인해야 합니다. `scripts/build_golden.py`의 전체 실행은 기준 파일을 덮어쓰므로 이번 연습에서는 사용하지 않습니다.

## 2. 먼저 예상하고 채점하기

[교육용 사례](worksheets/score-cases.json)에서 두 사례를 골라 예상 판정과 이유를 적습니다. 이어서 기존 [score 함수](../../../labs/mfg-bom-agent/src/mfg_bom_agent/evaluation/scoring.py)를 호출합니다.

```bash
uv run python ../../examples/ch08_score.py
uv run python ../../examples/ch08_score.py --check
uv run pytest -q tests/test_evaluation.py
```

응답 8개는 **채점 연습을 위해 구성한 입력**입니다. 과거 실제 모델 응답 원본이나 현재 45문항 성능 측정 자료가 아닙니다. DB·모델을 호출하지 않습니다. `--check`는 제공 사례의 예상 자동 판정을 확인합니다. 틀린 답을 false로 잡으면 예상대로 동작한 것입니다.

|사례|관찰할 것|
|---|---|
|quantity_correct|정상 답변·도구 결과 일치|
|quantity_wrong_unit|200개를 200팩으로 작성|
|motor_wrong_value|도구 증가액은 맞지만 결론 금액 오류|
|direction_wrong|ECN 감소액을 증가로 표현|
|path_omitted|도구 경로의 drive wheel이 결론에 없음|
|doc_not_cited|문서 목록에는 있지만 답변에서 인용하지 않음|
|quantity_condition_gap|50대 질문에 “100대에 200개”: 현재 자동 채점은 통과|
|doc_path_only_gap|문서 경로만 작성: answer=true, evidence=false|

마지막 두 사례는 `manual_review_required=true`입니다. 자동 통과를 업무적 정답으로 인정하지 말고 조건과 근거를 직접 확인하세요. 입력의 `expected_auto`는 현 채점기의 예상 동작을 기록한 값입니다.

`tool_correct`, `answer_correct`, `evidence_correct`, `verification_status`, `answerability`를 나누어 읽습니다. 이 예제는 Ch7 verify를 실행하지 않아 `verification_status=not_run`입니다. 집합 문항의 도구 정답은 결론도 참고하고, 숫자 문항의 도구 정답은 값·단위 중심이므로 실제 도구 인자와 근거를 함께 보세요.

## 3. 오류 원인을 근거로 적기

기존 [평가 기록](../../../labs/mfg-bom-agent/docs/EVAL_RESULTS.md)에서 G24·G30·G43을 읽고 [오류 기록표](worksheets/error-record.csv)에 두세 건을 작성합니다.

- G24: 조립품 구성 CQ-03은 있지만 조립품 조회 도구·계획 연결이 부족합니다. 부품 식별 실패와 구분합니다.
- G30: 결론에서 `drive wheel` 누락. 도구 경로와 최종 답변을 대조합니다.
- G43: 정답 문서 `parts_list/extra_parts.md` 미검색. 대체 부품·문서 연결과 검색 결과를 확인합니다.

이 세 건은 기존 실행 기록입니다. 교육용 G43 `doc_not_cited`는 문서를 검색한 상태에서 답변 인용을 빠뜨린 별도 사례입니다. 역사적 G43의 미검색과 원인이 다릅니다. G23 공용 부품은 CQ-04로, G24의 CQ-03과 구분합니다.

`missing_item`이나 `no_evidence`는 판정 코드입니다. 근본 원인은 데이터/매핑·온톨로지/관계·도구/계획·연결/검색·답변/검사 중 근거를 보고 고릅니다. 아직 원인을 확정할 수 없으면 확인할 자료를 적으세요.

## 4. 작업본의 한 응답 수정 후 재채점

```bash
cp ../../docs/part02/ch08/worksheets/score-cases.json /tmp/ch08-work.json
```

WSL/Linux/macOS 터미널 기준입니다. 작업본의 `case="path_omitted"`에서 `response.conclusion`만 `영향 어셈블리는 drive wheel입니다.`로 수정합니다. 기대 답인 Golden Set과 채점 코드는 그대로 둡니다.

```bash
uv run python ../../examples/ch08_score.py --cases /tmp/ch08-work.json
```

G30의 `tool_correct=true`, `answer_correct=true`, `recall=1`을 확인합니다. 작업본에는 수정 전의 `expected_auto`가 남아 있으므로 이 명령에는 `--check`를 붙이지 않습니다. 수정 전후 응답과 이유를 저장합니다. 이 연습은 한 응답을 고친 것이며 에이전트 코드가 개선됐다는 증거는 아닙니다. 실제 코드를 고쳤다면 새 실행과 관련 문항 회귀 확인이 추가로 필요합니다.

## 5. 대표 세 문항 실제 실행과 재채점 — 본 실습

준비된 Neo4j·MCP 환경에서 수량 G01, 원가 G16, 관계 G30을 실제 실행합니다. 기본 연습은 `fixed_llm`으로 모델 응답을 고정하고 실제 도구를 호출합니다. 현재 터미널에서만 환경변수를 지정하세요.

```bash
# macOS / Linux / WSL
DEMO_MODE=fixed_llm uv run python scripts/run_eval.py --ids G01,G16,G30 --modes kg_tools

# Windows PowerShell
$env:DEMO_MODE="fixed_llm"
uv run python scripts/run_eval.py --ids G01,G16,G30 --modes kg_tools
```

실행 결과는 새 `outputs/eval/<실행ID>/` 아래 `results.csv`, `responses.jsonl`, `report.md`, `meta.json`으로 저장됩니다. 자신의 실제 결과 폴더를 사용해 다음과 같이 재채점할 수 있습니다.

```bash
uv run python scripts/run_eval.py --rescore outputs/eval/본인의실행ID --ids G01,G16,G30 --modes kg_tools
```

경로는 실제 생성된 폴더명으로 바꿔야 합니다. 재채점은 모델·도구를 다시 부르지 않습니다. 현재 배포본에는 과거 전체 응답 원본이 없습니다. 기존 기록의 폴더명을 복사해 실행하지 마세요. 교육용 사례는 이 실제 실행 폴더와 별도로 관리합니다.

세 문항의 `tool_correct`, `answer_correct`, `verification`을 나누어 기록합니다. G01은 50대 총소요량 200 ea, G16은 3869.10 USD 증가, G30은 `drive wheel`을 기대합니다. 틀린 문항은 `responses.jsonl`의 intent·계산값·경로와 원 질문을 대조하세요.

2026-11-08 검수에서는 고정 모드 실제 도구 실행에서 G01이 `part_info`로 분류되어 1대 사용량 4 ea와 단가를 답하고, 50대 총량 200 ea를 답하지 못했습니다. 출력 검사는 passed였지만 Golden 평가는 wrong_value였습니다. G16·G30은 통과했습니다. **이는 기록된 특정 실행이며 수강생의 현재 결과나 실제 모델 품질을 보장하지 않습니다.** G01의 `rule_plan` → `part_info` 분기와 수량 계산 호출의 부재를 확인하고 같은 문항을 새 실행해 재현 여부를 기록하세요. 코드 수정 없는 재실행은 재현 확인이며 개선 증거가 아닙니다. 코드 수정 후에는 G01과 관련 수량 문항을 같은 조건으로 새로 실행해야 합니다.

고정 모드는 도구·경로 점검입니다. 실제 모델의 질문 해석과 답변 품질은 API 준비 후 `DEMO_MODE=none`으로 별도 실행합니다. PowerShell에서는 `$env:DEMO_MODE="none"`으로 바꿉니다. 모델명 필드가 있어도 고정 모드 결과를 실제 모델 평가로 발표하지 않습니다.

### 전체 평가 — 선택 실습

전체 선택 실행은 `uv run python scripts/run_eval.py`로 45문항 × 3방식을 실행합니다. RAG·LLM 단독은 실제 모델을 호출하며 `fixed_llm`이 전체 세 방식을 오프라인으로 바꾸지는 않습니다. 지식 그래프 고정 모드의 검색도 임베딩 API를 사용할 수 있습니다.

비교 결과에는 제공 데이터·도구·시스템 지시를 함께 적습니다. 현재 LLM 단독 지시에는 추정 수치 요청이 있어 일반 모델의 최선 성능 비교로 확대할 수 없습니다. v1과 v2 채점 결과를 직접 비교하지 않습니다. 최신 출력 검사와 함께 45문항을 새로 실행한 성능을 기존 보고서 수치로 대신하지 않습니다.

[실행 기록표](worksheets/run-record.csv)에 데이터·판·Golden·채점 버전·실행 모드·모델·코드 버전을 남깁니다. 재채점 meta는 현재 설정도 기록하므로 원본 meta와 응답의 context/sources도 보존하세요. 전체 정답률과 보류율의 분모를 남기고, 도구 지표가 없는 방식의 null을 오답으로 세지 않습니다.

## 산출물

예상·실제 판정 비교, 오류 2~3건의 근거와 수정 계획, 한 응답의 수정 전후 결과, 관련 회귀 문항을 저장합니다. Part 3에서는 이 절차를 주장·근거·출처 연결에 적용합니다. 실제 권한·계보·감사 설계는 Part 4에서 다룹니다.
