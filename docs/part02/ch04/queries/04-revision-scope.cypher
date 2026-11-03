// 이전 모터가 실제로 쓰인 판 목록. 결과가 많아도 무판 경로 전체를 펼치지 않습니다.
// Neo4j Browser: 문장 하나씩 선택해 실행합니다. 파라미터 명령 없이 독립 실행됩니다.
WITH '5202-2402-0027' AS requestedPart, null AS requestedRevision
MATCH (v:Revision)
WHERE true
MATCH (part:Part) WHERE part.sku=requestedPart OR part.part_id=requestedPart
MATCH p=(prod:Product)-[:HAS_BOM_LINE|REFERS_TO*2..8]->(part)
WHERE all(n IN nodes(p) WHERE NOT n:BOMLine OR n.revision_id=v.revision_id)
RETURN DISTINCT v.revision_id AS revision,v.valid_from AS valid_from ORDER BY valid_from;

// 같은 모터를 최신 판에서 조회하면 빈 결과가 정상일 수 있습니다.
// Neo4j Browser: 문장 하나씩 선택해 실행합니다. 파라미터 명령 없이 독립 실행됩니다.
WITH '5202-2402-0027' AS requestedPart, null AS requestedRevision
MATCH (v:Revision)
WHERE (requestedRevision IS NULL AND v.is_latest) OR v.revision_id=requestedRevision
MATCH (part:Part) WHERE part.sku=requestedPart OR part.part_id=requestedPart
MATCH p=(prod:Product)-[:HAS_BOM_LINE|REFERS_TO*2..8]->(part)
WHERE all(n IN nodes(p) WHERE NOT n:BOMLine OR n.revision_id=v.revision_id)
RETURN v.revision_id AS revision,p;
