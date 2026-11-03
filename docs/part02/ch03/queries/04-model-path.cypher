MATCH path=(p:Product)-[:HAS_BOM_LINE]->(pl:BOMLine)-[:REFERS_TO]->(a:Assembly)
 -[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(part:Part {sku:'5203-2402-0027'})
MATCH (v:Revision {is_latest:true})
WHERE pl.revision_id=v.revision_id AND l.revision_id=v.revision_id
MATCH rv=(l)-[:IN_REVISION]->(v)
RETURN path,rv;
