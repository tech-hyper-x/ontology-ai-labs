// CQ-11 증상 S의 원인 후보 부품과 근거 문서는? (관계 탐색 + 검색)
// 증상 문장 → 문서 검색은 CQ-15(하이브리드 검색)가 맡고, 이 쿼리는 부품 → 고장 모드 → 근거 문서 경로를 돌려준다.
MATCH (part:Part)-[h:HAS_FAILURE_MODE]->(f:FailureMode)
WHERE $part IS NULL OR part.part_id = $part OR part.sku = $part
OPTIONAL MATCH (f)-[d:DESCRIBED_IN]->(doc:Document)
RETURN part.sku AS sku, part.name AS part_name, f.fm_id AS fm_id, f.name AS failure_mode,
       f.symptom AS symptom, h.severity AS severity, doc.doc_id AS doc_id, doc.path AS doc_path,
       d.line AS line
ORDER BY severity
