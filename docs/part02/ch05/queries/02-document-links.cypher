// 직접 연결: method/confidence/mention과 원문 위치.
MATCH (p:Part)-[r:DESCRIBED_IN]->(d:Document)
WHERE d.path='mechanical/servo_gear_replacement/README.md'
RETURN d.doc_id AS doc,p.sku AS sku,r.method AS method,r.confidence AS confidence,r.mention AS mention,r.line AS line
ORDER BY doc,sku;

// 제공 고장 지식을 거치는 연결. direct와 구분합니다.
MATCH (p:Part)-[:HAS_FAILURE_MODE]->(f:FailureMode)-[r:DESCRIBED_IN]->(d:Document)
WHERE d.path='mechanical/servo_gear_replacement/README.md'
RETURN d.doc_id AS doc,p.sku AS sku,f.fm_id AS via,r.method AS method,r.confidence AS confidence,r.line AS line;
