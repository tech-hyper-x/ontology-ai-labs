// CQ-12 이름 · 약칭 N이 가리키는 부품은? (사실 조회) — 품번 정확 일치를 먼저, 그다음 전문 검색
CALL () {
  MATCH (p:Part) WHERE p.sku = $name OR p.part_id = $name
  RETURN p, 100.0 AS score, 'exact_id' AS method
  UNION
  MATCH (p:Part) WHERE toLower($name) IN p.aliases
  RETURN p, 50.0 AS score, 'alias' AS method
  UNION
  CALL db.index.fulltext.queryNodes('part_search', $lucene) YIELD node AS p, score
  RETURN p, score, 'fulltext' AS method
}
WITH p, max(score) AS score, collect(method)[0] AS method
RETURN p.part_id AS part_id, p.sku AS sku, p.name AS part_name, p.aliases AS aliases,
       p.in_latest AS in_latest, score, method
ORDER BY score DESC
LIMIT 5
