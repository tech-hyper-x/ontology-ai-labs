// CQ-10 부품 X의 대체 가능 부품과 조건은? (사실 조회) — 방향이 있다: X 대신 쓸 수 있는 부품
MATCH (part:Part) WHERE part.part_id = $part OR part.sku = $part
OPTIONAL MATCH (part)-[x:ALTERNATE_OF]->(alt:Part)
RETURN part.sku AS sku, alt.sku AS alternate_sku, alt.name AS alternate_name,
       x.compatibility AS compatibility, x.requires_rework AS requires_rework,
       x.source_doc AS source_doc, x.source_section AS source_section,
       x.pack_price AS pack_price, x.pack_size AS pack_size, x.price_note AS price_note
ORDER BY alternate_sku
