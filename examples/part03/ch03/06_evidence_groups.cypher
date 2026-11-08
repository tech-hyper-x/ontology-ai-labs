// :params와 MATCH는 별도로 실행
:params {"target": "EGFR", "disease": "MONDO_0005233"}

// CQ-03 연관 A를 뒷받침하는 근거와 출처는? (queries/cq_03_evidence.cypher)
MATCH (t:Target)
WHERE t.symbol = $target OR t.target_id = $target OR t.ensembl_id = $target
WITH t
MATCH (t)-[:HAS_ASSOCIATION]->(a:Association)-[:FOR_DISEASE]->(:Disease {mondo_id: $disease})
MATCH (a)-[:SUPPORTED_BY]->(e:Evidence)-[:HAS_TYPE]->(ty:EvidenceType)
MATCH (e)-[:FROM_SOURCE]->(s:Source)
WITH t, a, ty, s, e ORDER BY e.score DESC
WITH t, a, ty, s, count(e) AS loaded, collect(e.evidence_id)[0..3] AS top_evidence
RETURN t.symbol AS symbol, a.evidence_total AS evidence_total, a.evidence_counts AS evidence_counts,
       collect({type: ty.code, type_name: ty.name, source: s.source_id, loaded: loaded, top_evidence: top_evidence}) AS groups;
