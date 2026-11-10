# 84장 · Neo4j의 모델 위반 조회와 해석

Part 2 / Ch3 · [전체 실습 목차](../../hands-on/README.md)

## 시작 전 확인

- 장표와 같은 Part·챕터인지 먼저 확인합니다.

- Neo4j 코드는 Browser 입력창에서, bash 명령은 터미널에서 실행합니다. YAML·JSON·Python 파일 링크는 원문을 읽거나 수정할 대상을 뜻합니다.

- 터미널 명령의 기준 위치는 저장소의 `labs/mfg-bom-agent`입니다. 명령이 별도 위치를 지정하면 그 위치를 우선합니다.

- 초기화·적재·색인 명령은 기존 데이터에 영향을 줄 수 있습니다. 전용 실습 환경에서 해당 챕터 안내에 따라 실행하고, 조회만 하려면 다시 초기화하지 않습니다.

- [공통 실행 안내](../../ch03-run-guide.md)에 따라 서비스와 데이터를 준비합니다.

## 1. 05-validation-checks.cypher

[파일 원문 열기 · `docs/part02/ch03/queries/05-validation-checks.cypher`](queries/05-validation-checks.cypher)

이어서 아래 조회문을 실행합니다. 세미콜론으로 구분된 조회문이 여러 개면 한 문장씩 선택해 실행합니다.

```cypher
CALL { MATCH (l:BOMLine) WITH l,COUNT { (l)-[:REFERS_TO]->() } AS n
 WHERE n<>1 RETURN count(l) AS violations }
RETURN 'REFERS_TO cardinality' AS check,violations
UNION ALL
CALL { MATCH (p)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(c)
 WITH p,c,l.revision_id AS rev,count(l) AS n WHERE n>1 RETURN count(*) AS violations }
RETURN 'duplicate BOMLine' AS check,violations
UNION ALL
CALL { MATCH (p:Part)-[:SUPERSEDES*1..10]->(p) RETURN count(DISTINCT p) AS violations }
RETURN 'SUPERSEDES cycle' AS check,violations
UNION ALL
MATCH (r:Revision {is_latest:true}) WITH count(r) AS n
RETURN 'latest Revision' AS check,CASE WHEN n=1 THEN 0 ELSE 1 END AS violations;
```

`MATCH`에서 찾는 대상과 연결 방향을 보고, `WHERE`의 제한 조건과 `RETURN`의 반환 항목을 차례로 읽습니다. `count`는 개수, `ORDER BY`는 정렬 기준, `LIMIT`는 최대 반환 개수를 뜻합니다.

## 결과 확인과 문제 해결

- 실행 오류가 없는지 먼저 확인하고 장표에서 다룬 입력 조건과 실제 반환값을 대조합니다. 실행 성공만으로 정답이라고 판단하지 않습니다.

- 조회가 비면 파라미터 실행 여부, 입력 식별자, 개정판·질환 등 조건, 데이터 적재 여부, 선택 DB를 차례로 확인합니다.

- 검색은 방식·입력어·필터를 맞추고 본문과 출처를 확인합니다. 서로 다른 검색 점수를 절댓값으로 비교하지 않습니다.

- 모델이나 임베딩 호출 명령은 설정된 API 계정과 사용료가 필요할 수 있습니다. 실제 키는 공유하거나 녹화하지 않습니다.
