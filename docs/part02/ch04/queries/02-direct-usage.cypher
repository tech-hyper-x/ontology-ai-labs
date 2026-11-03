// Neo4j Browser: 문장 하나씩 선택해 실행합니다. 파라미터 명령 없이 독립 실행됩니다.
WITH '3616-0014-0144' AS requestedPart, null AS requestedRevision
MATCH (v:Revision)
WHERE (requestedRevision IS NULL AND v.is_latest) OR v.revision_id=requestedRevision
MATCH (a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(part:Part)
WHERE (part.sku=requestedPart OR part.part_id=requestedPart)
  AND l.revision_id=v.revision_id
RETURN v.revision_id AS revision,part.sku AS sku,a.name AS assembly,
 l.raw_qty_text AS raw_qty,l.pack_size AS pack_size,l.qty_each_text AS qty_each,
 l.multiplier AS multiplier,l.source_ref AS source_ref
ORDER BY assembly;
