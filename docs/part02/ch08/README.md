# Part 2 · Ch8 — 기준 문항 실행과 오류 분석

Ch7에서 남긴 도구 결과와 답변 검사 기록을 기대 답과 대조합니다. 18강 20분 계획이며 설치와 45문항 × 3방식 전체 실행은 별도입니다. [Ch7](../ch07/README.md)과 [환경 안내](../../setup/README.md)를 먼저 확인하세요.

아래 명령은 모두 `ontology-ai-labs/labs/mfg-bom-agent`에서 실행합니다. 기존 데이터·그래프를 재적재하거나 기준 답을 덮어쓰지 않습니다.

## 1. 조건과 기대 답 읽기

```bash
uv run python ../../examples/part02/ch08/ch08_reference.py
```

[참조 확인 예제](../../../examples/part02/ch08/ch08_reference.py)는 `build_golden.build()`를 호출해 CSV에서 계산한 문항과 배포 문항을 비교합니다. 파일을 저장하는 `main()`은 호출하지 않습니다.

기준은 Golden Set 1.1, snapshot `a78f9eb`, 최신 판 `6b2c5a9`입니다. 문항에 지정된 과거 판·ECN은 그 조건으로 읽습니다. 45문항은 수량 10·원가 10·관계 탐색 10·Revision/ECN 8·문서 근거 7입니다.

- G01: 서보 50대 총소요량 200 ea
- G16: 모터 단가 15% 인상·100대 부품비 증가액 3869.10 USD
- G36: 2023-10-04 ECN 전후 1대 차이 13.98 USD **감소**

[reference.py](../../../labs/mfg-bom-agent/src/mfg_bom_agent/evaluation/reference.py)는 업무 도구와 Neo4j를 쓰지 않지만 같은 processed CSV를 사용합니다. 원천 자료 자체의 정확성은 별도로 확인해야 합니다. `scripts/build_golden.py`의 전체 실행은 기준 파일을 덮어쓰므로 이번 연습에서는 사용하지 않습니다.

## 2. 먼저 예상하고 채점하기

[교육용 사례](worksheets/score-cases.json)에서 두 사례를 골라 예상 판정과 이유를 적습니다. 이어서 기존 [score 함수](../../../labs/mfg-bom-agent/src/mfg_bom_agent/evaluation/scoring.py)를 호출합니다.

```bash
uv run python ../../examples/part02/ch08/ch08_score.py
uv run python ../../examples/part02/ch08/ch08_score.py --check
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

## 4. 실제 런타임의 분류·계산 경로 수정

이전 고정 모드의 G01은 `part_info`로 분류되어 50대 총소요량 대신 제품 1대의 사용량과 단가를 답했습니다. 기대 답 200 ea는 그대로 유지하고, 질문 분류와 계산 경로를 고칩니다. 현재 배포 런타임에는 해결 코드가 반영돼 있습니다.

연습용 명령은 **별도의 실제 런타임 복사본**을 만들고 두 수정 지점을 미완성으로 둡니다. 원본 프로젝트·DB·Golden Set은 변경하지 않으며 `.env`·API 키·가상환경은 복사하지 않습니다. 이미 있는 폴더는 덮어쓰지 않습니다.

```bash
uv run python ../../examples/part02/ch08/ch08_quantity_exercise.py prepare --workspace ~/ontology-ch08-work
uv run python ../../examples/part02/ch08/ch08_quantity_exercise.py check --workspace ~/ontology-ch08-work
```

macOS/Linux/WSL/PowerShell에서 같은 인자를 사용합니다. `~`는 본인의 홈 폴더입니다. 원본 프로젝트의 HTTP MCP 서버를 별도 터미널에서 실행해 두세요. 다른 포트이면 `check`에 `--mcp-url http://localhost:변경포트/mcp`를 지정합니다.

첫 검사는 미수정 상태의 실패를 보여줍니다. G01~G06이 `wrong_value`인 것이 출발점입니다. 그다음 **복사본**의 다음 두 실제 모듈만 편집합니다.

1. `src/mfg_bom_agent/workflows/plan.py`: TODO 분류에서 `required_quantity`와 질문의 `units`를 보존합니다. 구매 팩·단종·단가 변경 유형의 우선순위는 유지합니다.
2. `src/mfg_bom_agent/workflows/skills.py`: TODO 경로에서 `where_used` → `bom_explode(part, units, revision, scope="all")`를 호출하고 모든 투입 내역의 `required_each`를 합칩니다. 값·단위 ea·인자·판·산식을 `CalcResult`에 담습니다. 해당 판에 내역이 없으면 0으로 확정하지 않습니다.

유형 선언·필수 입력·스킬 대응·부품 식별 등록은 복사본에 준비돼 있습니다. 생산 대수가 없으면 되묻도록 유지합니다. 새 유형의 배포 구현 전체는 [plan.py](../../../labs/mfg-bom-agent/src/mfg_bom_agent/workflows/plan.py), [skills.py](../../../labs/mfg-bom-agent/src/mfg_bom_agent/workflows/skills.py), [bom_agent.py](../../../labs/mfg-bom-agent/src/mfg_bom_agent/workflows/bom_agent.py)에서 대조합니다.

AI 요청 예: “실습 복사본의 두 TODO만 수정해 주세요. 총소요량과 구매 팩을 구분하고 생산 대수·판을 도구에 그대로 전달합니다. 같은 부품의 모든 투입 내역을 합치고, 내역이 없을 때 0개로 답하지 않습니다. Golden Set과 채점기·다른 질문 경로는 바꾸지 마세요.”

강의 시간은 강사의 수정·확인 시연 기준입니다. 수강생의 코드 작성은 일시정지 후 완료합니다. [해결 코드의 회귀 테스트](../../../labs/mfg-bom-agent/tests/test_quantity_route.py)는 대수 누락 되묻기, 다중 라인 합산, 내역 없음, 구매·단종·단가 변경·사용처 경로 유지를 확인합니다.

## 5. 수정 후 새 실행과 관련 문항 회귀 — 본 실습

```bash
uv run python ../../examples/part02/ch08/ch08_quantity_exercise.py check --workspace ~/ontology-ch08-work
```

복사본의 실제 워크플로가 실행됩니다. `fixed_llm`으로 모델 응답을 고정하고 기존 로컬 MCP 도구를 호출하므로 이 과제는 모델 API를 호출하지 않습니다. 단순 fixture 채점이나 저장 응답 재채점이 아닙니다.

검사 문항은 수량 G01~G10과 원가 G16·관계 G30입니다. `tool_correct`와 `answer_correct`가 모두 맞아야 명령이 통과합니다. 2026-11-08 검수에서는 동일 실습 복사본이 **미수정 6/12 → 해결 코드 적용 후 12/12**, G01은 `part_info`/대수 누락에서 `required_quantity`/50대·200 ea로 바뀌었습니다. 고정 모드의 이 12문항 결과이며 실제 모델 전체 성능이나 45문항 전체 정답률은 아닙니다.

각 새 실행은 복사본의 `outputs/eval/<실행ID>/`에 `results.csv`, `responses.jsonl`, `report.md`, `meta.json`을 남깁니다. [실행 기록표](worksheets/run-record.csv)에 수정 전후 폴더·코드 변경·입력·판·도구/답변 판정을 기록하고, G01을 고친 뒤 구매·원가·관계 질문도 유지되는지 확인합니다. 원본 서버를 변경한 것이 아니라 복사본의 에이전트 경로를 수정한 실습입니다.

### 저장 응답 재채점 — 별도 확인

`--rescore`는 저장된 답변을 다시 채점하며 모델·도구를 새로 실행하지 않습니다. 복사본에서 생성한 본인 결과를 재채점하려면 복사본 프로젝트에서 아래 명령을 실행합니다. 새 실행·재채점 폴더는 따로 보관합니다.

```bash
uv run python scripts/run_eval.py --rescore outputs/eval/본인의실행ID --ids G01,G16,G30 --modes kg_tools
```

## 6. 새로운 질문 한 개를 직접 설계하기

[작성 표](worksheets/transfer-question.md)에 부품·생산 대수·판 중 한 조건을 바꾼 질문을 적습니다. 필요한 자료·개체/관계·도구/인자·기대 결과를 먼저 정하고 Neo4j 조회와 도구 반환값을 같은 조건으로 대조합니다. “표 조회로 충분한지, 관계와 이력을 추적해야 하는지”를 설명하세요. 지원하지 않는 질문이면 필요한 설계와 검증 계획을 남깁니다. 수강생 작성·추가 실행은 일시정지 후 진행합니다.

응답 작업본의 `path_omitted` 문장을 편집하는 기존 연습은 선택 보충으로 활용할 수 있습니다. 한 응답의 편집을 실제 런타임 개선으로 설명하지 않습니다.

### 전체 평가 — 선택 실습

전체 선택 실행은 `uv run python scripts/run_eval.py`로 45문항 × 3방식을 실행합니다. RAG·LLM 단독은 실제 모델을 호출하며 `fixed_llm`이 전체 세 방식을 오프라인으로 바꾸지는 않습니다. 지식 그래프 고정 모드의 검색도 임베딩 API를 사용할 수 있습니다.

비교 결과에는 제공 데이터·도구·시스템 지시를 함께 적습니다. 현재 LLM 단독 지시에는 추정 수치 요청이 있어 일반 모델의 최선 성능 비교로 확대할 수 없습니다. v1과 v2 채점 결과를 직접 비교하지 않습니다. 최신 출력 검사와 함께 45문항을 새로 실행한 성능을 기존 보고서 수치로 대신하지 않습니다.

[실행 기록표](worksheets/run-record.csv)에 데이터·판·Golden·채점 버전·실행 모드·모델·코드 버전을 남깁니다. 재채점 meta는 현재 설정도 기록하므로 원본 meta와 응답의 context/sources도 보존하세요. 전체 정답률과 보류율의 분모를 남기고, 도구 지표가 없는 방식의 null을 오답으로 세지 않습니다.

## 산출물

예상·실제 판정 비교, 오류 원인, 실제 런타임 수정본과 회귀 결과, 새로운 질문 설계 표를 저장합니다. Part 3에서는 이 절차를 주장·근거·출처 연결에 적용합니다. 실제 권한·계보·감사 설계는 Part 4에서 다룹니다.
