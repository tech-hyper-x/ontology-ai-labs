// CQ-13 기계 · 전장 BOM 은 어떤 제품에 연결되는가? (관계 탐색)
// 두 BOM 사이에는 공통 키가 없다. 같은 Product 아래의 서로 다른 어셈블리로만 만난다.
WITH v
MATCH (prod:Product)-[:HAS_BOM_LINE]->(:BOMLine {revision_id: v.revision_id})-[:REFERS_TO]->(a:Assembly)
OPTIONAL MATCH (a)-[:HAS_BOM_LINE]->(l:BOMLine {revision_id: v.revision_id})
RETURN v.revision_id AS revision, prod.product_id AS product, a.domain AS domain,
       collect(DISTINCT a.name) AS assemblies, count(l) AS lines
ORDER BY domain
