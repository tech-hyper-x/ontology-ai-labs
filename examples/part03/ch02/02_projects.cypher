// Read only. Preserves two source projects, one canonical Target.
MATCH path=(p:InternalProject)-[r:TARGETS]->(t:Target {symbol:'EGFR'})
RETURN path,p.project_id AS project,p.target_label AS original,r.alias_used AS alias,r.method AS method,t.target_id AS target_id
ORDER BY project;
