// CQ-09 부품 X 변경 시 영향 후보 범위는? (규칙 추론 R2 ChangeImpactCandidate)
// 포함 관계로 찾은 "검토 후보"다. 실제 영향 여부는 변경 내용과 호환 조건을 보고 담당자가 판단한다.
WITH v
MATCH (part:Part) WHERE part.part_id = $part OR part.sku = $part
MATCH p = (up)-[:HAS_BOM_LINE|REFERS_TO*2..8]->(part)
WHERE (up:Assembly OR up:Product)
  AND all(n IN nodes(p) WHERE NOT n:BOMLine OR n.revision_id = v.revision_id)
WITH v, part, up, min(length(p)) AS depth
RETURN v.revision_id AS revision, part.sku AS sku, labels(up)[0] AS level,
       coalesce(up.assembly_id, up.product_id) AS target_id, coalesce(up.name, up.product_id) AS target,
       depth, 'R2 ChangeImpactCandidate' AS rule, true AS inferred
ORDER BY depth
