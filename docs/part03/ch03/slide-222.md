# 222장 · 인용 경로와 문장의 대상 일치

Part 3 / Ch3 · [전체 실습 목차](../../hands-on/README.md)

## 시작 전 확인

- 장표와 같은 Part·챕터인지 먼저 확인합니다.

- Neo4j 코드는 Browser 입력창에서, bash 명령은 터미널에서 실행합니다. YAML·JSON·Python 파일 링크는 원문을 읽거나 수정할 대상을 뜻합니다.

- 터미널 명령의 기준 위치는 저장소의 `labs/bio-target-agent`입니다. 명령이 별도 위치를 지정하면 그 위치를 우선합니다.

- 초기화·적재·색인 명령은 기존 데이터에 영향을 줄 수 있습니다. 전용 실습 환경에서 해당 챕터 안내에 따라 실행하고, 조회만 하려면 다시 초기화하지 않습니다.

- 준비된 바이오 DB와 검색 색인이 필요합니다. 제조 DB를 재사용하지 않습니다. 공개본에는 전체 바이오 런타임이 포함되지 않습니다. [실행 전 확인](../../../examples/part03/README.md).

## 1. 04_claim_paths.cypher

[파일 원문 열기 · `examples/part03/ch03/04_claim_paths.cypher`](../../../examples/part03/ch03/04_claim_paths.cypher)

이어서 아래 조회문을 실행합니다. 세미콜론으로 구분된 조회문이 여러 개면 한 문장씩 선택해 실행합니다.

```cypher
// 전체 평가용 Claim과 인용 근거의 대상 비교
MATCH (c:Claim)
OPTIONAL MATCH (c)-[:CITES]->(e:Evidence)<-[:SUPPORTED_BY]-(a:Association)<-[:HAS_ASSOCIATION]-(t:Target)
OPTIONAL MATCH (a)-[:FOR_DISEASE]->(d:Disease)
RETURN c.claim_id AS claim,c.target AS expected,c.text AS text,c.label AS example_label,
collect(DISTINCT {evidence:e.evidence_id,target:t.symbol,disease:d.mondo_id}) AS links ORDER BY claim;

// CLM-004는 DB에 적재되지 않음. 원본 claims.yaml의 없는 ID를 직접 검사
OPTIONAL MATCH (e:Evidence {evidence_id:'ev_does_not_exist_0001'})
RETURN e IS NOT NULL AS evidence_exists;
```

`MATCH`에서 찾는 대상과 연결 방향을 보고, `WHERE`의 제한 조건과 `RETURN`의 반환 항목을 차례로 읽습니다. `count`는 개수, `ORDER BY`는 정렬 기준, `LIMIT`는 최대 반환 개수를 뜻합니다.

## 2. claims.yaml

[파일 원문 열기 · `labs/bio-target-agent/data/golden/claims.yaml`](../../../examples/part03/reference/labs/bio-target-agent/data/golden/claims.yaml)

파일에서 장표에 나온 입력·조건·반환값을 확인합니다. 소스 파일 전체를 Neo4j나 터미널에 붙여 넣지 않습니다.

## 결과 확인과 문제 해결

- 실행 오류가 없는지 먼저 확인하고 장표에서 다룬 입력 조건과 실제 반환값을 대조합니다. 실행 성공만으로 정답이라고 판단하지 않습니다.

- 조회가 비면 파라미터 실행 여부, 입력 식별자, 개정판·질환 등 조건, 데이터 적재 여부, 선택 DB를 차례로 확인합니다.

- 검색은 방식·입력어·필터를 맞추고 본문과 출처를 확인합니다. 서로 다른 검색 점수를 절댓값으로 비교하지 않습니다.

- 모델이나 임베딩 호출 명령은 설정된 API 계정과 사용료가 필요할 수 있습니다. 실제 키는 공유하거나 녹화하지 않습니다.
