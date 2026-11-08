// Part 3 Ch1: one complete Browser query; no WITH t prefix is needed.
:params {target: "EGFR", disease: "MONDO_0005233", release: "26.09"}
MATCH p=(t:Target {symbol:$target})-[:HAS_ASSOCIATION]->(a:Association)-[:SUPPORTED_BY]->(e:Evidence)-[:FROM_SOURCE]->(s:Source)
MATCH (a)-[:FOR_DISEASE]->(d:Disease {mondo_id:$disease})
WHERE a.release=$release
RETURN p,d,e.datasource AS datasource,e.evidence_id AS evidence_id,a.release AS release
LIMIT 12;

// Table view: distinguish source-wide counts and loaded evidence.
MATCH (t:Target {symbol:$target})-[:HAS_ASSOCIATION]->(a:Association)-[:FOR_DISEASE]->(:Disease {mondo_id:$disease})
MATCH (a)-[:SUPPORTED_BY]->(e:Evidence)-[:HAS_TYPE]->(ty:EvidenceType)
MATCH (e)-[:FROM_SOURCE]->(s:Source)
WHERE a.release=$release
RETURN t.symbol AS symbol,a.evidence_total AS source_total,ty.code AS evidence_type,s.source_id AS source,count(DISTINCT e) AS loaded_evidence
ORDER BY loaded_evidence DESC;
