// CQ-08 부품 X가 교체한 이전 부품은? (사실 조회) — 대체 이력을 끝까지 따라간다
MATCH (part:Part) WHERE part.part_id = $part OR part.sku = $part
MATCH p = (part)-[:SUPERSEDES*1..5]->(old:Part)
WITH part, old, last(relationships(p)) AS s, length(p) AS hops
RETURN part.sku AS sku, old.sku AS old_sku, old.name AS old_name, s.ecn_id AS ecn,
       toString(s.effective_date) AS effective_date, hops
ORDER BY hops
