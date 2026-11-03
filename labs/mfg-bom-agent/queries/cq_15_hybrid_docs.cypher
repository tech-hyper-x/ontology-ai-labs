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
