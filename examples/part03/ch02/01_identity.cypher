// Read only. Execute :params and the query separately.
:params {name: "HER1"}
MATCH (g:Gene) WHERE g.symbol=$name OR $name IN g.aliases
MATCH (t:Target {ensembl_id:g.ensembl_id})
OPTIONAL MATCH (g)-[:ENCODES]->(p:Protein)-[:ACTS_AS]->(t)
RETURN $name AS original,g.symbol AS symbol,g.ensembl_id AS gene_id,p.uniprot_id AS protein_id,t.target_id AS target_id;
