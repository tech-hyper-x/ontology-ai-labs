// :params를 먼저 실행한 뒤 아래 MATCH 조회문을 별도로 실행
:params {"evidence": "048e2957de9143f53700a8f7197d8bf28f0dc098"}

// CQ-04 근거 E의 원문 논문(PMID)과 초록은? (queries/cq_04_evidence_paper.cypher)
MATCH (e:Evidence {evidence_id: $evidence})
OPTIONAL MATCH (e)-[:FROM_SOURCE]->(p:Paper)
OPTIONAL MATCH (e)-[:HAS_TYPE]->(ty:EvidenceType)
RETURN e.evidence_id AS evidence_id, ty.code AS type, e.datasource AS datasource, e.score AS score,
       collect({pmid: p.pmid, title: p.title, year: p.year, has_abstract: coalesce(p.has_abstract, false),
                abstract: left(p.abstract, 600)}) AS papers;
