MATCH (v:Revision)
WHERE ($revision IS NULL AND v.is_latest)
   OR v.revision_id = $revision
MATCH path = (a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(p:Part)
WHERE (p.sku = $part OR p.part_id = $part)
  AND l.revision_id = v.revision_id
RETURN path;
