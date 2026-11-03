// Ch1 제공 조회문: 작성은 Ch4에서 진행. 최신 판만 선택합니다.
MATCH (v:Revision {is_latest: true})
MATCH (a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(p:Part)
WHERE p.sku = '3616-0014-0144' AND l.revision_id = v.revision_id
RETURN p.sku AS sku, a.name AS assembly, v.revision_id AS revision,
       l.raw_qty_text AS raw_qty, l.pack_size AS pack_size,
       l.multiplier AS multiplier, l.source_ref AS source_ref, l.origin AS origin;
