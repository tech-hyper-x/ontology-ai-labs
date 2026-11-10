# 220장 · 근거 한 건의 유형·출처·논문 조회

Part 3 / Ch3 · [전체 실습 목차](../../hands-on/README.md)

## 시작 전 확인

- 장표와 같은 Part·챕터인지 먼저 확인합니다.

- Neo4j 코드는 Browser 입력창에서, bash 명령은 터미널에서 실행합니다. YAML·JSON·Python 파일 링크는 원문을 읽거나 수정할 대상을 뜻합니다.

- 터미널 명령의 기준 위치는 저장소의 `labs/bio-target-agent`입니다. 명령이 별도 위치를 지정하면 그 위치를 우선합니다.

- 초기화·적재·색인 명령은 기존 데이터에 영향을 줄 수 있습니다. 전용 실습 환경에서 해당 챕터 안내에 따라 실행하고, 조회만 하려면 다시 초기화하지 않습니다.

- 준비된 바이오 DB와 검색 색인이 필요합니다. 제조 DB를 재사용하지 않습니다. 공개본에는 전체 바이오 런타임이 포함되지 않습니다. [실행 전 확인](../../../examples/part03/README.md).

## 1. 01_evidence_path.cypher

[파일 원문 열기 · `examples/part03/ch03/01_evidence_path.cypher`](../../../examples/part03/ch03/01_evidence_path.cypher)

이어서 아래 조회문을 실행합니다. 세미콜론으로 구분된 조회문이 여러 개면 한 문장씩 선택해 실행합니다.

```cypher
// 읽기 전용 / 아래 Cypher만 실행
MATCH (t:Target {symbol:'EGFR'})-[:HAS_ASSOCIATION]->(a:Association)-[:FOR_DISEASE]->(d:Disease {mondo_id:'MONDO_0005233'})
MATCH (a)-[:SUPPORTED_BY]->(e:Evidence {evidence_id: '048e2957de9143f53700a8f7197d8bf28f0dc098'})
MATCH (e)-[:HAS_TYPE]->(ty:EvidenceType)
MATCH (e)-[:FROM_SOURCE]->(s:Source)
RETURN t.symbol AS target,d.mondo_id AS disease,a.release AS release,e.evidence_id AS evidence,e.score AS score,ty.code AS type,s.source_id AS source,e.retrieved_at AS retrieved_at;
```

`MATCH`에서 찾는 대상과 연결 방향을 보고, `WHERE`의 제한 조건과 `RETURN`의 반환 항목을 차례로 읽습니다. `count`는 개수, `ORDER BY`는 정렬 기준, `LIMIT`는 최대 반환 개수를 뜻합니다.

## 2. 02_evidence_papers.cypher

[파일 원문 열기 · `examples/part03/ch03/02_evidence_papers.cypher`](../../../examples/part03/ch03/02_evidence_papers.cypher)

먼저 입력 조건을 한 블록씩 단독 실행합니다.

```cypher
:params {"evidence": "048e2957de9143f53700a8f7197d8bf28f0dc098"}
```

이어서 아래 조회문을 실행합니다. 세미콜론으로 구분된 조회문이 여러 개면 한 문장씩 선택해 실행합니다.

```cypher
// :params를 먼저 실행한 뒤 아래 MATCH 조회문을 별도로 실행

// CQ-04 근거 E의 원문 논문(PMID)과 초록은? (queries/cq_04_evidence_paper.cypher)
MATCH (e:Evidence {evidence_id: $evidence})
OPTIONAL MATCH (e)-[:FROM_SOURCE]->(p:Paper)
OPTIONAL MATCH (e)-[:HAS_TYPE]->(ty:EvidenceType)
RETURN e.evidence_id AS evidence_id, ty.code AS type, e.datasource AS datasource, e.score AS score,
       collect({pmid: p.pmid, title: p.title, year: p.year, has_abstract: coalesce(p.has_abstract, false),
                abstract: left(p.abstract, 600)}) AS papers;
```

`MATCH`에서 찾는 대상과 연결 방향을 보고, `WHERE`의 제한 조건과 `RETURN`의 반환 항목을 차례로 읽습니다. `count`는 개수, `ORDER BY`는 정렬 기준, `LIMIT`는 최대 반환 개수를 뜻합니다.

## 결과 확인과 문제 해결

- 실행 오류가 없는지 먼저 확인하고 장표에서 다룬 입력 조건과 실제 반환값을 대조합니다. 실행 성공만으로 정답이라고 판단하지 않습니다.

- 조회가 비면 파라미터 실행 여부, 입력 식별자, 개정판·질환 등 조건, 데이터 적재 여부, 선택 DB를 차례로 확인합니다.

- 검색은 방식·입력어·필터를 맞추고 본문과 출처를 확인합니다. 서로 다른 검색 점수를 절댓값으로 비교하지 않습니다.

- 모델이나 임베딩 호출 명령은 설정된 API 계정과 사용료가 필요할 수 있습니다. 실제 키는 공유하거나 녹화하지 않습니다.
