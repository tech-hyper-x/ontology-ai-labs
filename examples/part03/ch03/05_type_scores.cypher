// :params와 MATCH는 별도로 실행
:params {"target": "EGFR", "disease": "MONDO_0005233"}

// CQ-02 표적 T–질환 D 연관의 근거 유형별 점수는? (queries/cq_02_type_scores.cypher)
MATCH (t:Target)
WHERE t.symbol = $target OR t.target_id = $target OR t.ensembl_id = $target
WITH t
MATCH (t)-[:HAS_ASSOCIATION]->(a:Association)-[:FOR_DISEASE]->(:Disease {mondo_id: $disease})
RETURN t.symbol AS symbol, a.assoc_id AS assoc_id, a.score AS score, a.release AS release,
       [k IN keys(a) WHERE k STARTS WITH 'score_' | {type: substring(k, 6), score: a[k]}] AS type_scores;
