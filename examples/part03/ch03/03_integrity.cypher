// 아래 3개 조회문을 각각 실행. 데이터 변경 없음.
MATCH (a:Association {candidate:true}) WHERE NOT (a)-[:SUPPORTED_BY]->() RETURN count(a) AS missing_candidate_evidence;

MATCH (e:Evidence) WITH e, COUNT { (e)-[:FROM_SOURCE]->(:Source) } AS source_count WHERE source_count <> 1 RETURN e.evidence_id AS evidence, source_count;

MATCH (e:Evidence) WITH e, COUNT { (e)-[:HAS_TYPE]->() } AS type_count WHERE type_count <> 1 RETURN e.evidence_id AS evidence, type_count;
