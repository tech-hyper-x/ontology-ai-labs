// CQ-06 등록 데이터 기준 단일 공급사 부품은? (규칙 추론 R1 RegisteredSingleSupplier)
// 선택한 판의 BOM 에 쓰이는 부품 중 등록된 서로 다른 공급사가 1곳뿐인 부품. 결과는 추론값이다.
WITH v
MATCH (:BOMLine {revision_id: v.revision_id})-[:REFERS_TO]->(part:Part)
WITH DISTINCT v, part
MATCH (part)-[:SUPPLIED_BY]->(s:Supplier)
WITH v, part, collect(DISTINCT s.supplier_id) AS suppliers
WHERE size(suppliers) = 1 AND ($domain IS NULL OR part.domain = $domain)
RETURN v.revision_id AS revision, part.sku AS sku, part.name AS part_name, suppliers[0] AS supplier,
       'R1 RegisteredSingleSupplier' AS rule, true AS inferred
ORDER BY sku
