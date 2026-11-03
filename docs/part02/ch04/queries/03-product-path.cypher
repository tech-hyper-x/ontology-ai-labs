// Neo4j Browser: 문장 하나씩 선택해 실행합니다. 파라미터 명령 없이 독립 실행됩니다.
WITH '3616-0014-0144' AS requestedPart, null AS requestedRevision
MATCH (v:Revision)
WHERE (requestedRevision IS NULL AND v.is_latest) OR v.revision_id=requestedRevision
MATCH (part:Part) WHERE part.sku=requestedPart OR part.part_id=requestedPart
MATCH p=(prod:Product)-[:HAS_BOM_LINE|REFERS_TO*2..8]->(part)
WHERE all(n IN nodes(p) WHERE NOT n:BOMLine OR n.revision_id=v.revision_id)
RETURN v.revision_id AS revision,p;

// 다음 문장은 Table 보기에서 수량 재료를 확인합니다.
// Neo4j Browser: 문장 하나씩 선택해 실행합니다. 파라미터 명령 없이 독립 실행됩니다.
WITH '3616-0014-0144' AS requestedPart, null AS requestedRevision
MATCH (v:Revision)
WHERE (requestedRevision IS NULL AND v.is_latest) OR v.revision_id=requestedRevision
MATCH (part:Part) WHERE part.sku=requestedPart OR part.part_id=requestedPart
MATCH p=(prod:Product)-[:HAS_BOM_LINE|REFERS_TO*2..8]->(part)
WHERE all(n IN nodes(p) WHERE NOT n:BOMLine OR n.revision_id=v.revision_id)
WITH v,part,prod,p,[n IN nodes(p) WHERE n:BOMLine] AS lines
RETURN v.revision_id AS revision,prod.product_id AS product,part.sku AS sku,
 [n IN nodes(p) WHERE n:Assembly | n.name] AS assemblies,
 [l IN lines | {raw_qty:l.raw_qty_text,pack_size:l.pack_size,qty_each:l.qty_each_text,
 multiplier:l.multiplier,source_ref:l.source_ref}] AS lines,
 reduce(f=1.0,l IN lines | f*l.raw_qty*l.multiplier) AS path_factor;
