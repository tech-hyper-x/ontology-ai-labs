# 189장 · 동일 질문의 키워드·벡터·결합 검색

Part 3 / Ch1 · [전체 실습 목차](../../hands-on/README.md)

## 시작 전 확인

- 장표와 같은 Part·챕터인지 먼저 확인합니다.

- Neo4j 코드는 Browser 입력창에서, bash 명령은 터미널에서 실행합니다. YAML·JSON·Python 파일 링크는 원문을 읽거나 수정할 대상을 뜻합니다.

- 터미널 명령의 기준 위치는 저장소의 `labs/bio-target-agent`입니다. 명령이 별도 위치를 지정하면 그 위치를 우선합니다.

- 초기화·적재·색인 명령은 기존 데이터에 영향을 줄 수 있습니다. 전용 실습 환경에서 해당 챕터 안내에 따라 실행하고, 조회만 하려면 다시 초기화하지 않습니다.

- 준비된 바이오 DB와 검색 색인이 필요합니다. 제조 DB를 재사용하지 않습니다. 공개본에는 전체 바이오 런타임이 포함되지 않습니다. [실행 전 확인](../../../examples/part03/README.md).

## 1. 04_search_modes.cypher

[파일 원문 열기 · `examples/part03/ch01/04_search_modes.cypher`](../../../examples/part03/ch01/04_search_modes.cypher)

먼저 입력 조건을 한 블록씩 단독 실행합니다.

```cypher
:params {example: "Q-G12C", q: null, qvec: null, mode: "bm25", k: 5, target: null, source: null}
```

이어서 아래 조회문을 실행합니다. 세미콜론으로 구분된 조회문이 여러 개면 한 문장씩 선택해 실행합니다.

```cypher
// Run each statement separately in Neo4j Browser. Read-only.
// Check provider before calling this a semantic-search comparison.
SHOW INDEXES YIELD name,state WHERE name IN ['chunk_fulltext','chunk_vector'] RETURN name,state;
MATCH (m:LabMeta {project:'bio-target-agent'}) RETURN m.embedding_provider AS provider,m.embedding_dim AS dimension;
// hash:local is a lexical fallback, not an equivalent semantic embedding.
// Start with bm25, then change ONLY mode to vector and hybrid.

// CQ-07 질문 Q와 관련된 문헌 근거는? (비정형 근거 — Hybrid: BM25 + 벡터 → RRF → 그래프, 설계 덱 29~30장)
// 1) BM25 키워드 검색 (chunk_fulltext, Lucene) 상위 20건
// 2) 벡터 검색 (chunk_vector, 코사인) 상위 20건
// 3) RRF 결합: 문서마다 Σ 1 / (60 + 순위). 한쪽에만 나온 문서도 점수를 받는다
// 4) 상위 k건 → 논문을 인용한 근거(Evidence) → 연관(Association) → 표적, 초록이 언급한 개체(MENTIONS)
// 파라미터: q(Lucene 검색어) · qvec(질문 임베딩) · mode(hybrid · bm25 · vector) · k · target(표적 심볼 필터) · source(paper · internal)
// Neo4j Browser 에서는 질문 임베딩을 만들 수 없으므로 저장한 예시 질문(SearchExample)을 쓴다:
//   :params {example: "Q-RESIST", q: null, qvec: null, mode: "hybrid", k: 5, target: null, source: null}
OPTIONAL MATCH (ex:SearchExample {id: $example})
WITH coalesce($q, ex.lucene) AS q, coalesce($qvec, ex.embedding) AS v, coalesce($mode, 'hybrid') AS mode
CALL (q, v, mode) {
  WITH q WHERE mode IN ['hybrid', 'bm25'] AND q IS NOT NULL  // 이 검색을 쓰지 않으면 건너뛴다
  CALL db.index.fulltext.queryNodes('chunk_fulltext', q, {limit: 20}) YIELD node, score
  WHERE ($source IS NULL OR node.source = $source)
  WITH collect({doc: node, score: score}) AS hits
  UNWIND range(0, size(hits) - 1) AS i
  RETURN hits[i].doc AS doc, 'bm25' AS method, i + 1 AS rank, hits[i].score AS score
  UNION ALL
  WITH v WHERE mode IN ['hybrid', 'vector'] AND v IS NOT NULL
  CALL db.index.vector.queryNodes('chunk_vector', 20, v) YIELD node, score
  WHERE ($source IS NULL OR node.source = $source)
  WITH collect({doc: node, score: score}) AS hits
  UNWIND range(0, size(hits) - 1) AS i
  RETURN hits[i].doc AS doc, 'vector' AS method, i + 1 AS rank, hits[i].score AS score
}
WITH doc, collect({method: method, rank: rank, score: score}) AS hits
WITH doc, hits,
     reduce(s = 0.0, h IN hits | s + 1.0 / (60 + h.rank)) AS rrf,
     reduce(b = 999, h IN hits | CASE WHEN h.rank < b THEN h.rank ELSE b END) AS best
WHERE $target IS NULL OR $target IN coalesce(doc.targets, [])
ORDER BY rrf DESC, best, doc.chunk_id
LIMIT $k
OPTIONAL MATCH (e:Evidence)-[:FROM_SOURCE]->(doc)
OPTIONAL MATCH (tt:Target)-[:HAS_ASSOCIATION]->(:Association)-[:SUPPORTED_BY]->(e)
WITH doc, hits, rrf, best, collect(DISTINCT {evidence_id: e.evidence_id, target: tt.symbol}) AS ev
OPTIONAL MATCH (doc)-[mn:MENTIONS]->(x)
WITH doc, hits, rrf, best, ev,
     collect(DISTINCT CASE WHEN x IS NULL THEN null ELSE {kind: labels(x)[0], name: coalesce(x.symbol, x.label, x.name, x.mondo_id), confidence: mn.confidence} END) AS mentions
RETURN doc.chunk_id AS chunk_id, doc.pmid AS pmid, doc.title AS title, doc.year AS year, doc.source AS source,
       doc.text AS text, round(rrf, 4) AS score,
       [h IN hits WHERE h.method = 'bm25' | h.rank][0] AS bm25_rank,
       [h IN hits WHERE h.method = 'vector' | h.rank][0] AS vector_rank,
       [h IN hits WHERE h.method = 'bm25' | round(h.score, 3)][0] AS bm25_score,
       [h IN hits WHERE h.method = 'vector' | round(h.score, 3)][0] AS vector_score,
       [x IN ev WHERE x.evidence_id IS NOT NULL] AS evidence,
       [m IN mentions WHERE m IS NOT NULL] AS mentions
ORDER BY rrf DESC, best, chunk_id;


// Inspect one paper; zero Evidence links do not prove the paper is irrelevant.
MATCH (p:Paper {pmid:'34759319'})
OPTIONAL MATCH (p)-[:MENTIONS]->(g:Gene)
WITH p,collect(DISTINCT g.symbol) AS mentions
OPTIONAL MATCH (e:Evidence)-[:FROM_SOURCE]->(p)
RETURN p.pmid AS pmid,p.title AS title,p.abstract AS abstract,mentions,count(DISTINCT e) AS linked_evidence;
```

`MATCH`에서 찾는 대상과 연결 방향을 보고, `WHERE`의 제한 조건과 `RETURN`의 반환 항목을 차례로 읽습니다. `count`는 개수, `ORDER BY`는 정렬 기준, `LIMIT`는 최대 반환 개수를 뜻합니다.

## 결과 확인과 문제 해결

- 실행 오류가 없는지 먼저 확인하고 장표에서 다룬 입력 조건과 실제 반환값을 대조합니다. 실행 성공만으로 정답이라고 판단하지 않습니다.

- 조회가 비면 파라미터 실행 여부, 입력 식별자, 개정판·질환 등 조건, 데이터 적재 여부, 선택 DB를 차례로 확인합니다.

- 검색은 방식·입력어·필터를 맞추고 본문과 출처를 확인합니다. 서로 다른 검색 점수를 절댓값으로 비교하지 않습니다.

- 모델이나 임베딩 호출 명령은 설정된 API 계정과 사용료가 필요할 수 있습니다. 실제 키는 공유하거나 녹화하지 않습니다.
