// 읽기 전용 / 아래 Cypher만 실행
MATCH (t:Target {symbol:'EGFR'})-[:HAS_ASSOCIATION]->(a:Association)-[:FOR_DISEASE]->(d:Disease {mondo_id:'MONDO_0005233'})
MATCH (a)-[:SUPPORTED_BY]->(e:Evidence {evidence_id: '048e2957de9143f53700a8f7197d8bf28f0dc098'})
MATCH (e)-[:HAS_TYPE]->(ty:EvidenceType)
MATCH (e)-[:FROM_SOURCE]->(s:Source)
RETURN t.symbol AS target,d.mondo_id AS disease,a.release AS release,e.evidence_id AS evidence,e.score AS score,ty.code AS type,s.source_id AS source,e.retrieved_at AS retrieved_at;
