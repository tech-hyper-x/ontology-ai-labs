MATCH (v:Revision)
WHERE ($revision IS NULL AND v.is_latest)
   OR v.revision_id = $revision
MATCH (a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(p:Part)
WHERE (p.sku = $part OR p.part_id = $part)
  AND l.revision_id = v.revision_id
RETURN p.sku AS sku, a.name AS assembly,
       v.revision_id AS revision,
       l.raw_qty_text AS raw_qty,
       l.qty_each_text AS qty_each
ORDER BY assembly;
