// CQ-02 부품 X는 제품 1대에 어떤 수량 · 배수로 들어가나? (관계 탐색)
// 계산 재료(원천 수량 · 팩 크기 · 낱개 수량 · 배수)까지만 돌려준다. 곱셈은 bom_explode 가 한다.
WITH v
MATCH (part:Part) WHERE part.part_id = $part OR part.sku = $part
MATCH (a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine {revision_id: v.revision_id})-[:REFERS_TO]->(part)
RETURN v.revision_id AS revision, part.sku AS sku, a.name AS assembly, l.raw_qty_text AS raw_qty,
       l.pack_size AS pack_size, l.qty_each_text AS qty_each, l.multiplier AS multiplier, l.unit AS unit,
       l.source_ref AS source_ref
ORDER BY assembly
