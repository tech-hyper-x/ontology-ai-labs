// 먼저 실행 가능한 시작점입니다. Part 노드와 선택한 판까지만 반환합니다.
// 1. 아래 MATCH를 Assembly → BOMLine → Part로 확장하세요.
// 2. 투입 내역의 revision_id가 v.revision_id와 같다는 조건을 추가하세요.
// 3. RETURN에 assembly, 원천 수량, pack_size, qty_each, multiplier, source_ref를 넣으세요.
// 4. 휠 SKU를 스페이서로 바꾸고 수량 단위를 설명하세요.
// Neo4j Browser: 문장 하나씩 선택해 실행합니다. 파라미터 명령 없이 독립 실행됩니다.
WITH '3616-0014-0144' AS requestedPart, null AS requestedRevision
MATCH (v:Revision)
WHERE (requestedRevision IS NULL AND v.is_latest) OR v.revision_id=requestedRevision
MATCH (part:Part) WHERE part.sku=requestedPart OR part.part_id=requestedPart
RETURN v.revision_id AS revision,part.sku AS sku,part.name AS part_name;
