// CQ-15 결과의 연결 SKU를 입력으로 사용합니다. 모든 투입 내역을 최신 판으로 제한합니다.
MATCH (v:Revision {is_latest:true})
MATCH (part:Part {sku:'2000-0025-0002'})
MATCH p=(prod:Product)-[:HAS_BOM_LINE|REFERS_TO*2..8]->(part)
WHERE all(n IN nodes(p) WHERE NOT n:BOMLine OR n.revision_id=v.revision_id)
RETURN v.revision_id AS revision,p;
