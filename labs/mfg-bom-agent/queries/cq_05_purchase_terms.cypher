// CQ-05 부품 X의 공급사 · 단가 · 팩 · MOQ · 관측일은? (사실 조회)
// unit_price 는 팩당 가격이다. price_date(실제 가격 기준일)는 원천에 없어 null 이다 — "미상"으로 답한다.
MATCH (part:Part) WHERE part.part_id = $part OR part.sku = $part
MATCH (part)-[o:SUPPLIED_BY]->(s:Supplier)
RETURN part.sku AS sku, s.supplier_id AS supplier_id, s.name AS supplier, s.origin AS supplier_origin,
       o.supplier_sku AS supplier_sku, o.unit_price AS unit_price, o.currency AS currency,
       o.pack_size AS pack_size, o.moq_packs AS moq_packs, o.lead_time_days AS lead_time_days,
       toString(o.observed_at) AS observed_at, o.price_date AS price_date,
       o.origin AS price_origin, o.terms_origin AS terms_origin
ORDER BY supplier_origin DESC, supplier_id
