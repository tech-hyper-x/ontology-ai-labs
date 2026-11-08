// Read only. Missing a link does not mean the target does not exist.
MATCH (p:InternalProject) WHERE NOT (p)-[:TARGETS]->(:Target)
RETURN p.project_id AS project,p.target_label AS original,p.indication AS indication,p.resolved_symbol AS resolved;
