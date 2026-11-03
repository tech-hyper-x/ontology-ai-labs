// CQ-07 ECN E로 바뀐 BOM 라인은? (관계 탐색)
// $ecn 은 ECN ID 또는 변경 후 판(커밋) ID 를 받는다.
MATCH (e:ECN) WHERE e.ecn_id = $ecn OR e.revision_to = $ecn
MATCH (l:BOMLine)-[c:CHANGED_BY]->(e)
MATCH (l)-[:REFERS_TO]->(part:Part)
MATCH (a:Assembly)-[:HAS_BOM_LINE]->(l)
RETURN e.ecn_id AS ecn, toString(e.ecn_date) AS ecn_date, e.title AS title, c.change_type AS change_type,
       a.name AS assembly, part.sku AS sku, part.name AS part_name,
       c.before_raw_qty AS before_qty, c.after_raw_qty AS after_qty
ORDER BY change_type, assembly, sku
