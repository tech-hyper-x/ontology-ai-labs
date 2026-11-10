# Part 3 Ch3 · 표적 주장과 근거의 관계 설계

[바이오 실행 전 확인](../README.md). 준비된 바이오 Neo4j에서 읽기 전용으로 실행합니다. 적재·초기화·색인 생성은 수행하지 않습니다.

1. `relation_worksheet.csv`에 관계의 방향·필수 연결·CQ를 작성하고 `relation_answers.csv`와 대조합니다.
2. `01_evidence_path.cypher`, `02_evidence_papers.cypher`: 고정 Evidence의 유형·출처·PMID와 초록 보유 여부를 확인합니다.
3. `03_integrity.cypher`: 후보 근거·Source·유형 누락을 각각 검사합니다.
4. `04_claim_paths.cypher`: 인용 대상과 표적·질환 경로를 확인합니다. CLM-004는 없는 근거 ID를 인용하여 DB Claim 적재에서 제외된 입력 예제입니다.
5. `05_type_scores.cypher`, `06_evidence_groups.cypher`: 유형별 집계 점수와 실제 적재 근거 건수를 구분합니다.
6. `interpretation_worksheet.csv`에 사실과 추가 확인 사항을 작성합니다.
7. `07_search_bm25.cypher`, `08_search_vector.cypher`, `09_search_hybrid.cypher`: 같은 Q-RESIST·EGFR·paper·k3 조건으로 비교하고 `search_observation.csv`에 기록합니다.

`:params`와 조회문은 별도로 실행합니다. 조회문은 `_target.cypher` 공통 조각을 포함한 완성문입니다. 검색 색인과 저장 SearchExample 임베딩이 준비되어 있어야 하며, 방식별 상위20개 후 필터 조건입니다. 문헌 하나에 여러 표적의 근거가 연결될 수 있습니다. 순위와 문장의 사실 지지는 별도 검토합니다.


[장표 번호별 실습 안내](../../../docs/part03/ch03/README.md#장표-번호별-실습)
