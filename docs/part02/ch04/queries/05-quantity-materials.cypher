// 학습용 수치 대조입니다. 최종 정밀 계산 도구 구현은 Ch6에서 다룹니다.
WITH null AS requestedRevision
MATCH (v:Revision) WHERE (requestedRevision IS NULL AND v.is_latest) OR v.revision_id=requestedRevision
MATCH (part:Part) WHERE part.sku IN ['3616-0014-0144','1522-0010-0060']
MATCH p=(prod:Product)-[:HAS_BOM_LINE|REFERS_TO*2..8]->(part)
WHERE all(n IN nodes(p) WHERE NOT n:BOMLine OR n.revision_id=v.revision_id)
WITH v,part,p,[n IN nodes(p) WHERE n:BOMLine] AS lines
RETURN v.revision_id AS revision,part.sku AS sku,
 [l IN lines | {raw:l.raw_qty_text,pack:l.pack_size,each:l.qty_each_text,multiplier:l.multiplier}] AS materials,
 reduce(f=1.0,l IN lines | f*l.raw_qty*l.multiplier) AS path_factor,
 reduce(f=1.0,l IN lines | f*l.qty_each*l.multiplier) AS each_per_product
ORDER BY sku;
