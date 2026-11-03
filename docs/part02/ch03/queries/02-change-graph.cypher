MATCH path=(a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(p:Part)
MATCH vr=(l)-[:IN_REVISION]->(v:Revision)
WHERE v.revision_id IN ['d6d1fbc','d092d83']
AND p.sku IN ['5202-2402-0027','5203-2402-0027']
RETURN path,vr;

// Run this statement separately: replacement history and educational ECN.
MATCH (n:Part {sku:'5203-2402-0027'})-[s:SUPERSEDES]->(o:Part)
MATCH (e:ECN {ecn_id:s.ecn_id})
RETURN n.sku AS new_part,o.sku AS old_part,e.revision_from AS before_revision,
 e.revision_to AS after_revision,e.origin AS origin;
