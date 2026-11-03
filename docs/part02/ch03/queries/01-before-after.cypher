MATCH (a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(p:Part)
WHERE l.revision_id IN ['d6d1fbc','d092d83']
AND p.sku IN ['5202-2402-0027','5203-2402-0027']
RETURN l.revision_id AS revision,a.name AS assembly,p.sku AS sku,
 l.raw_qty AS raw_qty,l.qty_each AS qty_each,l.multiplier AS multiplier
ORDER BY revision,sku;
