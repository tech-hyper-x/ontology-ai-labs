// CQ-01 부품 X가 쓰이는 어셈블리 · 제품은? (관계 탐색)
// ─── [Hands-on P2-Ch4-2 영향 경로 Cypher 작성] 시작 ───
// 부품에서 위로 올라가며 같은 판의 BOM 라인만 따라간다. 경로마다 수량이 어떻게 늘어나는지
// path_factor(원천 수량 × 배수의 곱)로 보여 준다. 금액 · 수량의 최종 계산은 도구(bom_explode)가 한다.
WITH v
MATCH (part:Part) WHERE part.part_id = $part OR part.sku = $part
MATCH p = (prod:Product)-[:HAS_BOM_LINE|REFERS_TO*2..8]->(part)
WHERE all(n IN nodes(p) WHERE NOT n:BOMLine OR n.revision_id = v.revision_id)
WITH v, part, prod, p, [n IN nodes(p) WHERE n:BOMLine] AS lines, [n IN nodes(p) WHERE n:Assembly] AS asms
RETURN v.revision_id AS revision, prod.product_id AS product, part.sku AS sku, part.name AS part_name,
       [a IN asms | a.name] AS assemblies,
       [l IN lines | {bomline_id: l.bomline_id, raw_qty: l.raw_qty_text, pack_size: l.pack_size,
                      qty_each: l.qty_each_text, multiplier: l.multiplier, unit: l.unit}] AS lines,
       reduce(f = 1.0, l IN lines | f * l.raw_qty * l.multiplier) AS path_factor
ORDER BY assemblies
// ─── [Hands-on P2-Ch4-2] 끝 ───
