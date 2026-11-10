# 117장 · 검색 조건 변경과 원문 근거 대조

Part 2 / Ch5 · [전체 실습 목차](../../hands-on/README.md)

## 시작 전 확인

- 장표와 같은 Part·챕터인지 먼저 확인합니다.

- Neo4j 코드는 Browser 입력창에서, bash 명령은 터미널에서 실행합니다. YAML·JSON·Python 파일 링크는 원문을 읽거나 수정할 대상을 뜻합니다.

- 터미널 명령의 기준 위치는 저장소의 `labs/mfg-bom-agent`입니다. 명령이 별도 위치를 지정하면 그 위치를 우선합니다.

- 초기화·적재·색인 명령은 기존 데이터에 영향을 줄 수 있습니다. 전용 실습 환경에서 해당 챕터 안내에 따라 실행하고, 조회만 하려면 다시 초기화하지 않습니다.

- [공통 실행 안내](../../ch03-run-guide.md)에 따라 서비스와 데이터를 준비합니다.

## 1. 09-search-template.cypher

[파일 원문 열기 · `docs/part02/ch05/queries/09-search-template.cypher`](queries/09-search-template.cypher)

먼저 입력 조건을 한 블록씩 단독 실행합니다.

```cypher
:params {"example": "CQ-11", "q": null, "qvec": null, "mode": "hybrid", "k": 5, "source": null}
```

이어서 아래 조회문을 실행합니다. 세미콜론으로 구분된 조회문이 여러 개면 한 문장씩 선택해 실행합니다.

```cypher
// 작성 과제: 아래 JSON에서 한 번에 한 조건만 바꿉니다.
// A. example=CQ-11 고정, mode를 bm25 / vector / hybrid로 변경
// B. source를 null / readme / issue로 변경하고 검색 범위를 기록
// C. k=3 또는 5. 후보 풀 20개와 반환 개수 k를 구분
// 새 질문 글자만 바꾸면 저장된 벡터와 달라집니다. 기존 example ID를 사용하세요.

// CQ-15 증상 · 키워드 S로 찾은 근거 문서와 연결 부품은? (하이브리드 검색: BM25 + 벡터 → RRF → 그래프)
// 1) BM25 키워드 검색 (doc_fulltext 전문 색인, Lucene BM25 점수) 상위 20건
// 2) 벡터 검색 (doc_vector 색인, 코사인 유사도) 상위 20건
// 3) RRF 결합: 문서마다 Σ 1 / (60 + 순위). 한쪽에만 나온 문서도 점수를 받는다
// 4) 상위 k건 문서 → DESCRIBED_IN → 부품(고장 모드 경유 포함) → 최신 판에서 쓰이는 어셈블리
// 파라미터: q(Lucene 검색어) · qvec(질문 임베딩) · mode(hybrid · bm25 · vector) · k · source · example
// Neo4j Browser 에서는 질문 임베딩을 만들 수 없으므로, 미리 저장한 예시 질문(SearchExample)의 검색어 · 벡터를 쓴다:
//   :params {example: "CQ-11", q: null, qvec: null, mode: "hybrid", k: 5, source: null}
OPTIONAL MATCH (ex:SearchExample {id: $example})
WITH coalesce($q, ex.lucene) AS q, coalesce($qvec, ex.embedding) AS v, coalesce($mode, 'hybrid') AS mode
CALL (q, v, mode) {
  WITH q WHERE mode IN ['hybrid', 'bm25'] AND q IS NOT NULL  // 이 검색을 쓰지 않으면 건너뛴다
  CALL db.index.fulltext.queryNodes('doc_fulltext', q, {limit: 20}) YIELD node, score
  WHERE ($source = 'all' OR ($source IS NULL AND node.source <> 'bom_text') OR node.source = $source)
  WITH collect({doc: node, score: score}) AS hits
  UNWIND range(0, size(hits) - 1) AS i
  RETURN hits[i].doc AS doc, 'bm25' AS method, i + 1 AS rank, hits[i].score AS score
  UNION ALL
  WITH v WHERE mode IN ['hybrid', 'vector'] AND v IS NOT NULL
  CALL db.index.vector.queryNodes('doc_vector', 20, v) YIELD node, score
  WHERE ($source = 'all' OR ($source IS NULL AND node.source <> 'bom_text') OR node.source = $source)
  WITH collect({doc: node, score: score}) AS hits
  UNWIND range(0, size(hits) - 1) AS i
  RETURN hits[i].doc AS doc, 'vector' AS method, i + 1 AS rank, hits[i].score AS score
}
WITH doc, collect({method: method, rank: rank, score: score}) AS hits
WITH doc, hits,
     reduce(s = 0.0, h IN hits | s + 1.0 / (60 + h.rank)) AS rrf,
     reduce(b = 999, h IN hits | CASE WHEN h.rank < b THEN h.rank ELSE b END) AS best
ORDER BY rrf DESC, best, doc.doc_id
LIMIT $k
OPTIONAL MATCH (x)-[l:DESCRIBED_IN]->(doc) WHERE x:Part OR x:FailureMode
OPTIONAL MATCH (fp:Part)-[:HAS_FAILURE_MODE]->(x)
WITH doc, hits, rrf, best, coalesce(fp, x) AS part, l, x
OPTIONAL MATCH (rev:Revision {is_latest: true})
OPTIONAL MATCH (a:Assembly)-[:HAS_BOM_LINE]->(:BOMLine {revision_id: rev.revision_id})-[:REFERS_TO]->(part)
WITH doc, hits, rrf, best, part, l, x, collect(DISTINCT a.name) AS assemblies
WITH doc, hits, rrf, best,
     collect(DISTINCT CASE WHEN part IS NULL THEN null ELSE
       {part_id: part.part_id, sku: part.sku, name: part.name, method: l.method, confidence: l.confidence,
        via: CASE WHEN x:FailureMode THEN x.fm_id ELSE 'direct' END, assemblies: assemblies} END) AS parts
RETURN doc.doc_id AS doc_id, doc.path AS path, doc.title AS title, doc.line AS line, doc.source AS source,
       doc.text AS text, round(rrf, 4) AS score,
       [h IN hits WHERE h.method = 'bm25' | h.rank][0] AS bm25_rank,
       [h IN hits WHERE h.method = 'vector' | h.rank][0] AS vector_rank,
       [h IN hits WHERE h.method = 'bm25' | round(h.score, 3)][0] AS bm25_score,
       [h IN hits WHERE h.method = 'vector' | round(h.score, 3)][0] AS vector_score,
       parts
ORDER BY rrf DESC, best, doc_id
```

`MATCH`에서 찾는 대상과 연결 방향을 보고, `WHERE`의 제한 조건과 `RETURN`의 반환 항목을 차례로 읽습니다. `count`는 개수, `ORDER BY`는 정렬 기준, `LIMIT`는 최대 반환 개수를 뜻합니다.

## 2. ch05_compare.py

[파일 원문 열기 · `examples/part02/ch05/ch05_compare.py`](../../../examples/part02/ch05/ch05_compare.py)

파일에서 장표에 나온 입력·조건·반환값을 확인합니다. 소스 파일 전체를 Neo4j나 터미널에 붙여 넣지 않습니다.

## 3. 터미널 실행 명령

실행·입력 위치: **프로젝트 폴더의 터미널**.

자리표시자나 개인 설정이 있으면 먼저 실제 값으로 바꿉니다. 앞 단계의 서버 실행이 필요한 명령은 서버가 켜진 상태에서 실행합니다.

```bash
uv run python ../../examples/part02/ch05/ch05_compare.py
```

## 결과 확인과 문제 해결

- 실행 오류가 없는지 먼저 확인하고 장표에서 다룬 입력 조건과 실제 반환값을 대조합니다. 실행 성공만으로 정답이라고 판단하지 않습니다.

- 조회가 비면 파라미터 실행 여부, 입력 식별자, 개정판·질환 등 조건, 데이터 적재 여부, 선택 DB를 차례로 확인합니다.

- 검색은 방식·입력어·필터를 맞추고 본문과 출처를 확인합니다. 서로 다른 검색 점수를 절댓값으로 비교하지 않습니다.

- 모델이나 임베딩 호출 명령은 설정된 API 계정과 사용료가 필요할 수 있습니다. 실제 키는 공유하거나 녹화하지 않습니다.
