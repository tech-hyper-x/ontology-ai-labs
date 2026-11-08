// Read only. MONDO is the primary key in this lab; EFO is a cross-reference.
MATCH (d:Disease {mondo_id:'MONDO_0005233'})
RETURN d.mondo_id AS disease_id,d.name AS name,d.xrefs AS cross_references;
