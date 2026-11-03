// CQ-04 여러 어셈블리에 쓰이는 공용 부품은? (관계 탐색)
WITH v
MATCH (a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine {revision_id: v.revision_id})-[:REFERS_TO]->(part:Part)
WITH v, part, collect(DISTINCT a.name) AS assemblies
WHERE size(assemblies) > 1
RETURN v.revision_id AS revision, part.sku AS sku, part.name AS part_name, assemblies
ORDER BY sku
