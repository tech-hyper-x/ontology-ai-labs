# 검색 준비 확인 · 작성 예시

강의에서 사용하는 Voyage 구성의 기록 예시입니다. 실행 환경이 다르면 실제 조회값으로 기록합니다.

| 확인 항목 | 작성 예시 |
|---|---|
| 실습 DB | Ch4 제조 전용 DB · 제공 `Document` 청크 유지 |
| 출처 대조 | 정비 README의 `Diagnosing an issue` → `quality_document.csv` → 적재 Document ID를 두고 대조 |
| 색인 준비 | `build_index.py` 실행 후 `doc_fulltext`·`doc_vector`가 `ONLINE`인지 확인 |
| 공급자·모델·차원 | 수업 설정 `voyage:voyage-4` · 1024차원 · `LabMeta`의 실제 공급자와 대체 이유를 기록 |
| 문서와 질문 벡터 | `03-index-readiness.cypher`로 양쪽 벡터 유무와 차원을 확인 · 실제 건수는 출력에서 기록 |
| 저장 질문 | `CQ-11`의 저장 벡터를 같은 질문 비교에 사용 |
| 대체 임베딩 | `hash:local`이 반환되면 연결 점검으로 기록하고 의미 검색 비교는 별도로 진행 |

[빈 체크리스트](index-checklist.md) · [Ch5 검색 준비 가이드](../README.md#12강--원문에서-검색-준비까지)
