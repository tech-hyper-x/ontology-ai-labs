SHOW INDEXES YIELD name,type,state,labelsOrTypes,properties
WHERE name IN ['doc_fulltext','doc_vector'] RETURN name,type,state,labelsOrTypes,properties;

MATCH (m:LabMeta {project:'mfg-bom-agent'})
RETURN m.embedding_provider AS provider,m.embedding_dim AS dimension,m.embedding_fallback_reason AS fallback_reason;

MATCH (d:Document) RETURN d.source AS source,count(*) AS documents,count(d.embedding) AS with_vector;

MATCH (e:SearchExample) RETURN e.id AS example,e.query_en AS query,size(e.embedding) AS dimensions;
