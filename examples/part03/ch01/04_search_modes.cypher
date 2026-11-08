// Run each statement separately in Neo4j Browser. Read-only.
// Check provider before calling this a semantic-search comparison.
SHOW INDEXES YIELD name,state WHERE name IN ['chunk_fulltext','chunk_vector'] RETURN name,state;
MATCH (m:LabMeta {project:'bio-target-agent'}) RETURN m.embedding_provider AS provider,m.embedding_dim AS dimension;
// hash:local is a lexical fallback, not an equivalent semantic embedding.
// Start with bm25, then change ONLY mode to vector and hybrid.
:params {example: "Q-G12C", q: null, qvec: null, mode: "bm25", k: 5, target: null, source: null}

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
