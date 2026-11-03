// Ch2 관찰용 · 읽기 전용
MATCH (p:Part {sku:'3616-0014-0144'})-[o:SUPPLIED_BY]->(s:Supplier) RETURN p.part_id AS part_id,p.sku AS sku,p.aliases AS aliases,p.mpn AS mpn,s.supplier_id AS supplier,o.supplier_sku AS supplier_sku,o.origin AS price_origin,o.terms_origin AS terms_origin ORDER BY supplier;
