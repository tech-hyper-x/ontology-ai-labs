# 225장 · 유형별 점수와 적재 근거의 조회

Part 3 / Ch3 · [전체 실습 목차](../../hands-on/README.md)

## 시작 전 확인

- 장표와 같은 Part·챕터인지 먼저 확인합니다.

- Neo4j 코드는 Browser 입력창에서, bash 명령은 터미널에서 실행합니다. YAML·JSON·Python 파일 링크는 원문을 읽거나 수정할 대상을 뜻합니다.

- 터미널 명령의 기준 위치는 저장소의 `labs/bio-target-agent`입니다. 명령이 별도 위치를 지정하면 그 위치를 우선합니다.

- 초기화·적재·색인 명령은 기존 데이터에 영향을 줄 수 있습니다. 전용 실습 환경에서 해당 챕터 안내에 따라 실행하고, 조회만 하려면 다시 초기화하지 않습니다.

- 준비된 바이오 DB와 검색 색인이 필요합니다. 제조 DB를 재사용하지 않습니다. 공개본에는 전체 바이오 런타임이 포함되지 않습니다. [실행 전 확인](../../../examples/part03/README.md).

## 1. 05_type_scores.cypher

[파일 원문 열기 · `examples/part03/ch03/05_type_scores.cypher`](../../../examples/part03/ch03/05_type_scores.cypher)

먼저 입력 조건을 한 블록씩 단독 실행합니다.

```cypher
:params {"target": "EGFR", "disease": "MONDO_0005233"}
```

이어서 아래 조회문을 실행합니다. 세미콜론으로 구분된 조회문이 여러 개면 한 문장씩 선택해 실행합니다.

```cypher
// :params와 MATCH는 별도로 실행

// CQ-02 표적 T–질환 D 연관의 근거 유형별 점수는? (queries/cq_02_type_scores.cypher)
MATCH (t:Target)
WHERE t.symbol = $target OR t.target_id = $target OR t.ensembl_id = $target
WITH t
MATCH (t)-[:HAS_ASSOCIATION]->(a:Association)-[:FOR_DISEASE]->(:Disease {mondo_id: $disease})
RETURN t.symbol AS symbol, a.assoc_id AS assoc_id, a.score AS score, a.release AS release,
       [k IN keys(a) WHERE k STARTS WITH 'score_' | {type: substring(k, 6), score: a[k]}] AS type_scores;
```

`MATCH`에서 찾는 대상과 연결 방향을 보고, `WHERE`의 제한 조건과 `RETURN`의 반환 항목을 차례로 읽습니다. `count`는 개수, `ORDER BY`는 정렬 기준, `LIMIT`는 최대 반환 개수를 뜻합니다.

## 2. 06_evidence_groups.cypher

[파일 원문 열기 · `examples/part03/ch03/06_evidence_groups.cypher`](../../../examples/part03/ch03/06_evidence_groups.cypher)

먼저 입력 조건을 한 블록씩 단독 실행합니다.

```cypher
:params {"target": "EGFR", "disease": "MONDO_0005233"}
```

이어서 아래 조회문을 실행합니다. 세미콜론으로 구분된 조회문이 여러 개면 한 문장씩 선택해 실행합니다.

```cypher
// :params와 MATCH는 별도로 실행

// CQ-03 연관 A를 뒷받침하는 근거와 출처는? (queries/cq_03_evidence.cypher)
MATCH (t:Target)
WHERE t.symbol = $target OR t.target_id = $target OR t.ensembl_id = $target
WITH t
MATCH (t)-[:HAS_ASSOCIATION]->(a:Association)-[:FOR_DISEASE]->(:Disease {mondo_id: $disease})
MATCH (a)-[:SUPPORTED_BY]->(e:Evidence)-[:HAS_TYPE]->(ty:EvidenceType)
MATCH (e)-[:FROM_SOURCE]->(s:Source)
WITH t, a, ty, s, e ORDER BY e.score DESC
WITH t, a, ty, s, count(e) AS loaded, collect(e.evidence_id)[0..3] AS top_evidence
RETURN t.symbol AS symbol, a.evidence_total AS evidence_total, a.evidence_counts AS evidence_counts,
       collect({type: ty.code, type_name: ty.name, source: s.source_id, loaded: loaded, top_evidence: top_evidence}) AS groups;
```

`MATCH`에서 찾는 대상과 연결 방향을 보고, `WHERE`의 제한 조건과 `RETURN`의 반환 항목을 차례로 읽습니다. `count`는 개수, `ORDER BY`는 정렬 기준, `LIMIT`는 최대 반환 개수를 뜻합니다.

## 결과 확인과 문제 해결

- 실행 오류가 없는지 먼저 확인하고 장표에서 다룬 입력 조건과 실제 반환값을 대조합니다. 실행 성공만으로 정답이라고 판단하지 않습니다.

- 조회가 비면 파라미터 실행 여부, 입력 식별자, 개정판·질환 등 조건, 데이터 적재 여부, 선택 DB를 차례로 확인합니다.

- 검색은 방식·입력어·필터를 맞추고 본문과 출처를 확인합니다. 서로 다른 검색 점수를 절댓값으로 비교하지 않습니다.

- 모델이나 임베딩 호출 명령은 설정된 API 계정과 사용료가 필요할 수 있습니다. 실제 키는 공유하거나 녹화하지 않습니다.
