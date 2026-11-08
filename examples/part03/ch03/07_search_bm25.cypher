// :params와 OPTIONAL MATCH는 별도로 실행. 저장 임베딩 사용, 외부 API 호출 없음.
:params {"example": "Q-RESIST", "q": null, "qvec": null, "mode": "bm25", "k": 3, "target": "EGFR", "source": "paper"}

// CQ-07 질문 Q와 관련된 문헌 근거는? (queries/cq_07_hybrid_papers.cypher)
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
