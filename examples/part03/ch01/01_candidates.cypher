// Part 3 Ch1: same disease/release; no writes.
:params {disease: "MONDO_0005233", release: "26.09"}
MATCH (t:Target)-[:HAS_ASSOCIATION]->(a:Association)-[:FOR_DISEASE]->(d:Disease {mondo_id:$disease})
WHERE t.symbol IN ['EGFR','KRAS','MET'] AND a.release=$release
RETURN t.symbol AS symbol,t.target_id AS target_id,a.score AS association_score,a.rank AS overall_rank,a.release AS release,a.types AS evidence_types
ORDER BY association_score DESC;
