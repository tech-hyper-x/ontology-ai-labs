# Part 2 · Ch3 — 제조 온톨로지와 변경 모델

1강 15분 + 2강 20분. Ch2의 매핑·식별자·단위 규칙을 받아, 방법론의 개념 모델링과 관계·규칙 설계로 이어갑니다. Part 1 Ch3에서 초기화한 DB와 패키지를 그대로 사용합니다. 실행 위치는 `labs/mfg-bom-agent`입니다.

## 1강 · BOM 변경 사례 모델링

1. [원본 두 판과 diff](reference/)를 열어 모터 5202→5203 변경을 찾습니다. 원본은 고정된 두 커밋의 내용을 변경 없이 보관했습니다. 전체 NASA 저장소를 새로 받을 필요가 없습니다.
2. [개정판 조회](queries/03-revision-interval.cypher)로 시작 포함·종료 제외 구간과 경계일을 확인합니다. 날짜는 저장소 반영일이며 실제 생산 적용일이 아닙니다. 같은 날짜 여러 판은 커밋 ID로 구분합니다.
3. [변경 전후 표 조회](queries/01-before-after.cypher), [그래프와 교체 이력](queries/02-change-graph.cypher)을 Neo4j Browser에서 각각 실행합니다. 파일에 여러 문장이 있으면 한 문장씩 선택해 실행합니다.
4. [ecn.py](../../../labs/mfg-bom-agent/src/mfg_bom_agent/foundation/ecn.py)의 revision_intervals → diff_revisions → pair_supersedes를 읽습니다. ECN은 파생된 교육용 변경 기록입니다. SUPERSEDES는 새 부품→이전 부품 방향의 이력이고, 조건부 대체 관계 ALTERNATE_OF와 구분합니다.
5. [변경 기록 표](worksheets/change-record.csv)를 작성하고 아래 예제로 모터 한 쌍을 대조합니다.

```bash
uv run python ../../examples/part02/ch03/ch03_change.py
```

예제는 현재 작업본의 기존 함수에 실제 두 원본 행을 전달합니다. DB·파일을 변경하지 않습니다. 전체 diff의 6개 변경 행과 모터 한 쌍의 2개 행은 범위가 다릅니다. 예제의 판 구간 입력은 3개만 발췌했으므로 마지막 판을 실제 최신 판이라고 해석하지 않습니다. 실제 기간은 plm_revision.csv·Neo4j와 대조합니다.

## 2강 · 제조 온톨로지와 검증 규칙

1. [schema.yaml](../../../labs/mfg-bom-agent/ontology/schema.yaml)의 reuse·classes·relations·cq를 읽고 [관계 명세](worksheets/relation-contract.csv)를 작성합니다. 정의 차용·정렬은 외부 온톨로지 전체를 불러오는 것과 다릅니다.
2. [제품→조립품→부품 경로](queries/04-model-path.cypher)를 Graph 보기로 펼칩니다. 두 구간 모두 BOMLine이 있고, 각 라인은 Revision을 참조합니다.
3. Domain은 시작 대상의 종류, Range는 끝 대상의 종류, 카디널리티는 연결 개수입니다. REFERS_TO와 IN_REVISION은 라인마다 각각 하나입니다.
4. [ontology.py](../../../labs/mfg-bom-agent/src/mfg_bom_agent/ontology.py)에서 고유성 제약·필수 값·Domain/Range·관계 속성·연결 개수·중복·순환 검사의 구현 위치를 찾습니다. [대표 검사](queries/05-validation-checks.cypher)와 아래 명령은 읽기 전용입니다.

```bash
uv run python ../../examples/part02/ch03/ch03_validate.py
```

검토 시점의 제공 DB는 31개 검사 모두 위반 0건입니다. 실제 반환값을 우선 기록합니다. 이 결과는 구현된 검사 범위만 의미합니다. 현재 필수 값 검사는 null 여부이며, 모든 빈 문자열·기간 오류·업무 타당성까지 검사하지 않습니다. [판 속성과 연결의 일치 검사](queries/06-revision-consistency.cypher)는 별도로 제안하는 추가 검사입니다.

5. [작은 오류 예제](queries/07-error-cases.cypher)를 먼저 실행해 4행을 읽습니다. WHERE 조건을 직접 추가해 3개 오류 행만 반환하도록 작성합니다. 정상 행은 제외돼야 합니다. 입력 한 곳을 정상으로 고쳐 위반 행이 줄어드는지도 확인합니다. [강사용 안내](INSTRUCTOR.md)와 [검증 명세표](worksheets/validation-contract.csv)를 사용합니다. 이 예제는 UNWIND 입력으로만 실행되며 DB를 바꾸지 않습니다.
6. schema의 R1·R2는 등록 공급사·영향 후보를 도출하는 규칙입니다. 관계 무결성 검사나 최종 교체 승인과 구분합니다. schema 파일만으로 OWL 추론기가 실행되지는 않습니다.

## 남길 결과와 다음 단계

변경 기록 한 건, 개체·관계 명세, 오류 검사 조건, 수정한 Ch2 매핑표를 남깁니다. 모델을 구체화하면서 매핑 초안을 다시 검토하는 반복 설계입니다. 전체 적재와 영향 경로 쿼리 작성은 Part 2 Ch4, 원가 계산은 Ch6에서 진행합니다.

Neo4j Browser: http://localhost:7474 · 본인 .env의 접속 설정 사용. 이번 챕터는 `init_data.py`, `build_dataset.py`, `load_graph.py`를 실행하지 않습니다.
