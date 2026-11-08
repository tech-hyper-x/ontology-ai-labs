// 전체 평가용 Claim과 인용 근거의 대상 비교
MATCH (c:Claim)
OPTIONAL MATCH (c)-[:CITES]->(e:Evidence)<-[:SUPPORTED_BY]-(a:Association)<-[:HAS_ASSOCIATION]-(t:Target)
OPTIONAL MATCH (a)-[:FOR_DISEASE]->(d:Disease)
RETURN c.claim_id AS claim,c.target AS expected,c.text AS text,c.label AS example_label,
collect(DISTINCT {evidence:e.evidence_id,target:t.symbol,disease:d.mondo_id}) AS links ORDER BY claim;

// CLM-004는 DB에 적재되지 않음. 원본 claims.yaml의 없는 ID를 직접 검사
OPTIONAL MATCH (e:Evidence {evidence_id:'ev_does_not_exist_0001'})
RETURN e IS NOT NULL AS evidence_exists;
