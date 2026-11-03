CALL { MATCH (l:BOMLine) WITH l,COUNT { (l)-[:REFERS_TO]->() } AS n
 WHERE n<>1 RETURN count(l) AS violations }
RETURN 'REFERS_TO cardinality' AS check,violations
UNION ALL
CALL { MATCH (p)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(c)
 WITH p,c,l.revision_id AS rev,count(l) AS n WHERE n>1 RETURN count(*) AS violations }
RETURN 'duplicate BOMLine' AS check,violations
UNION ALL
CALL { MATCH (p:Part)-[:SUPERSEDES*1..10]->(p) RETURN count(DISTINCT p) AS violations }
RETURN 'SUPERSEDES cycle' AS check,violations
UNION ALL
MATCH (r:Revision {is_latest:true}) WITH count(r) AS n
RETURN 'latest Revision' AS check,CASE WHEN n=1 THEN 0 ELSE 1 END AS violations;
