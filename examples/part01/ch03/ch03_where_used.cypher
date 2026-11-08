// Neo4j Browser: 파라미터 설정을 먼저 별도로 실행한 뒤 조회문을 실행합니다.

:params {part: '3616-0014-0144', revision: null}

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
ORDER BY assembly
