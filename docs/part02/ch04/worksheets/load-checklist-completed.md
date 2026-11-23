# 적재 확인 기록 · 작성 예시

강의에서 제공한 스냅샷의 결과를 적는 예시입니다. 실행 전 확인 항목은 본인 환경에서 확인한 뒤 체크합니다.

| 확인 항목 | 작성 예시 |
|---|---|
| 실행 위치와 대상 | `labs/mfg-bom-agent` · 제조 전용 실습 Neo4j Browser `http://localhost:7474` |
| 실행 준비 | 전용 DB인지, 앱 질의가 중단됐는지, 적재 대응표의 Part·Assembly·Revision·BOMLine 키가 맞는지 로컬에서 확인 |
| 재적재 기록 | `scripts/load_graph.py` · 강의 시연의 종료 코드 0 · 입력 처리 건수는 실행 출력에서 확인해 기록 |
| 검증 결과 | 제공 DB 시연 기준 31개 검사에서 위반 0건 · 노드·관계의 실제 건수는 `01-load-inventory.cypher`와 `ch04_audit.py`로 대조 |
| 개정판 대조 | `d6d1fbc`의 `5202-2402-0027` → `d092d83`의 `5203-2402-0027` · `drive wheel` 확인 |
| 검색 상태 | 기존 색인과 연결이 초기화됐으므로 Ch5에서 `build_index.py`로 검색을 준비 |

[빈 체크리스트](load-checklist.md) · [Ch4 적재 가이드](../README.md#10강--적재-흐름)
