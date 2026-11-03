# Part 2 · Ch5 — 정비 문서와 Hybrid Search

Ch4의 사용처 그래프에 문서 근거를 연결합니다. 12강은 문서 연결·오류 수정·색인 준비, 13강은 BM25·벡터·RRF 비교와 그래프 경로 확인입니다. 각 목표 15분이며 최초 설치·임베딩 대기와 추가 연습은 별도입니다.

## 12강 · 원문에서 검색 준비까지

1. [정비 원문 스냅샷](source/servo_gear_replacement.md)의 Diagnosing an issue 절과 [출처](source/SOURCES.md)를 읽습니다.
2. `labs/mfg-bom-agent`에서 아래 명령을 실행해 제목 기준 청크와 제공 CSV를 대조합니다.

```bash
uv run python ../../examples/ch05_chunks.py
```

`data/processed/quality_document.csv`의 청크는 Ch4에서 이미 `Document`로 적재했습니다. `build_index.py`는 원본을 청크로 다시 만드는 스크립트가 아닙니다. 원문·가공·적재·색인을 구분합니다. [문서 조회](queries/01-document-source.cypher)와 [연결 조회](queries/02-document-links.cypher)를 Browser에서 실행하고 [연결 검수표](worksheets/link-review.csv)에 기록합니다.

### 오연결 수정

[가상 바퀴 배선 예제](source/wheel_wiring.md)를 읽고 기존 `data/exercises/exercises.yaml`의 기대 조건을 확인합니다.

```bash
uv run python scripts/exercise.py ch5_1_link
```

초기 상태에서는 불필요한 서보 연결이 남아 실패합니다. `src/mfg_bom_agent/retrieval/linking.py`의 `LINK_OVERRIDES`에 다음 한 줄을 추가합니다. 기존 검수 항목은 유지합니다.

```python
("exercise/wheel_wiring.md#1", "P-2000-0025-0002", "remove"),
```

다시 과제를 실행해 서보 연결 제거·휠 연결 유지가 모두 통과하는지 확인합니다. `uv run python ../../examples/ch05_linking.py`는 파일을 바꾸지 않고 수정 전후 기대 결과를 메모리에서 비교합니다.

이 과제는 작은 fixture만 검사하며 실제 DB의 관계를 바꾸지 않습니다. `exercise/wheel_wiring.md#1`은 제공 DB의 실제 청크가 아닙니다. 실제 청크의 검수 규칙을 수정했다면 연결 작업을 재실행하고 DB에서 확인합니다. 검수 이유는 코드 tuple 자체에 자동 저장되지 않으므로 [검수표](worksheets/link-review.csv)에 따로 남깁니다.

### 색인 구성

```bash
uv run python scripts/build_index.py
```

이 스크립트는 문서 연결 → 문서 임베딩 → 전문·벡터 색인 → SearchExample 질문 벡터를 준비합니다. 기존 연결과 벡터 색인을 다시 구성하므로 전용 실습 환경에서 진행합니다. 임베딩 API 계정·비용·생성 대기는 별도입니다. 출력의 실제 공급자와 대체 이유를 읽고 [03 준비 조회](queries/03-index-readiness.cypher), [확인표](worksheets/index-checklist.md)로 점검합니다. `hash:local`을 의미 검색 성공으로 설명하지 않습니다.

## 13강 · 같은 질문으로 세 검색 비교

1. [검색 질문](../../../labs/mfg-bom-agent/data/golden/search_examples.yaml)에서 CQ-11(증상)과 G44(품번 단종)를 선택합니다.
2. [04 BM25](queries/04-bm25.cypher), [05 벡터](queries/05-vector.cypher)를 같은 example·문서 범위로 실행합니다.
3. [06 결합 검색](queries/06-hybrid.cypher)은 **:params 명령과 아래 Cypher를 각각 따로 실행**합니다. mode를 bm25/vector/hybrid로 바꿉니다. parameters: example,q,qvec,mode,k,source.
4. [비교표](worksheets/search-comparison.csv)에 원점수와 순위를 각각 기록합니다. CQ-15의 `score`는 단독 검색에서도 RRF 값입니다. 원점수는 `bm25_score`, `vector_score`로 읽습니다.
5. [07 문서-부품 경로](queries/07-document-part-path.cypher)에서 직접 연결과 FailureMode 경유를 구분합니다. CQ-15는 연결 Part와 최신 판의 직접 Assembly를 반환합니다.
6. [08 제품 경로](queries/08-product-path.cypher)를 별도로 실행해 Ch4의 모든 BOMLine 판 조건을 재사용합니다.
7. [09 작성 과제](queries/09-search-template.cypher)에서 한 번에 한 조건을 바꾸고 원문·부품·사용처를 대조합니다.

```bash
uv run python ../../examples/ch05_compare.py --example CQ-11 --k 5
uv run python ../../examples/ch05_compare.py --example G44 --source issue --k 3
uv run pytest -q tests/test_retrieval.py
```

예제는 저장된 질문 벡터만 사용하므로 외부 임베딩 API를 호출하지 않습니다. 새 질문은 문서와 같은 모델·차원의 질문 벡터가 필요합니다. 질문 텍스트만 바꾸지 않습니다. 원문은 영어 스냅샷이며 영어 검색식을 사용합니다. 한국어 검색 품질은 이 비교로 검증한 것이 아닙니다.

### 점수와 결과 해석

- 키워드 관련도·벡터 점수·RRF·연결 confidence는 서로 다른 값입니다. 정답 확률로 읽지 않습니다.
- 현재 Voyage 색인에서는 진단 청크 #2가 BM25 5위·벡터 3위·결합 1위였습니다. `1/65+1/63≈0.0313`입니다. 입력·모델이 바뀌면 실제 결과를 우선합니다.
- G44의 이슈 469는 두 검색 모두 1위였습니다. 벡터가 항상 품번에 약하다고 단정하지 않습니다.
- 후보는 각 검색 상위20개이며 source 필터는 이 후보를 가져온 뒤 적용됩니다. k는 최종 문서 수입니다. 범위를 제한하면 결과가 k보다 적을 수 있습니다.
- 원문은 전기 연결과 기어 문제를 모두 설명합니다. 검색 순위로 고장 원인을 확정하지 않습니다.
- 구형 품번은 문서·Part가 있어도 최신 판 사용처가 비어 있을 수 있습니다.
- `hybrid_search()`에서 질문 임베딩이 실패하면 hybrid는 경고와 함께 BM25로 전환하고 vector 전용은 오류를 반환합니다. `mode/effective_mode/warnings`를 확인합니다. 이 Browser 파일은 미리 저장된 벡터를 쓰므로 그 API 장애 분기와 구분합니다.

[강사용 진행 메모](INSTRUCTOR.md)
