// An additional proposed check, separate from ontology.py's existing 31 checks.
MATCH (l:BOMLine)-[:IN_REVISION]->(v:Revision)
WHERE l.revision_id IS NULL OR l.revision_id<>v.revision_id
RETURN l.bomline_id AS line,l.revision_id AS stored_revision,v.revision_id AS linked_revision;
