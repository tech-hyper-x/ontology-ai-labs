// Part 3 Ch1: observe alias mapping. Mapping repair is Ch2.
:params {name: "HER1"}
MATCH (g:Gene) WHERE g.symbol=$name OR $name IN g.aliases
MATCH (t:Target {ensembl_id:g.ensembl_id})
RETURN $name AS original_name,g.symbol AS canonical_symbol,g.ensembl_id AS gene_id,t.target_id AS target_id;
