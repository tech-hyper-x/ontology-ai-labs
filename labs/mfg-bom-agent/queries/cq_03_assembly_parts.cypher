// CQ-03 어셈블리 A의 구성 부품은? (사실 조회)
WITH v
MATCH (a:Assembly) WHERE a.assembly_id = $assembly OR a.name = toLower($assembly)
MATCH (a)-[:HAS_BOM_LINE]->(l:BOMLine {revision_id: v.revision_id})-[:REFERS_TO]->(part:Part)
RETURN v.revision_id AS revision, a.name AS assembly, part.sku AS sku, part.name AS part_name,
       l.raw_qty_text AS raw_qty, l.pack_size AS pack_size, l.multiplier AS multiplier
ORDER BY l.row_no
