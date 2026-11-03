// Ch1 출처 관찰: 공개 공급사의 구매 조건도 가정일 수 있습니다.
MATCH (p:Part {sku: '3616-0014-0144'})-[o:SUPPLIED_BY]->(s:Supplier)
RETURN s.name AS supplier, s.origin AS supplier_origin,
       o.unit_price AS price, o.pack_size AS pack_size, o.moq_packs AS moq,
       o.origin AS price_origin, o.terms_origin AS terms_origin,
       toString(o.observed_at) AS observed_at, o.price_date AS price_date
ORDER BY supplier;
