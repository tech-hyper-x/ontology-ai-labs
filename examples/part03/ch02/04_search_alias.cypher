// Read only. Same index and exact input; count Chunk records, not only papers.
SHOW INDEXES YIELD name,state WHERE name IN ['chunk_fulltext','chunk_vector'] RETURN name,state;

UNWIND ['HER1','EGFR'] AS input
CALL db.index.fulltext.queryNodes('chunk_fulltext',input,{limit:1000}) YIELD node,score
RETURN input,count(node) AS chunks,collect(DISTINCT node.source) AS sources
ORDER BY input;

// Inspect the sources instead of assuming all hits are papers.
UNWIND ['HER1','EGFR'] AS input
CALL db.index.fulltext.queryNodes('chunk_fulltext',input,{limit:1000}) YIELD node,score
RETURN input,node.source AS source,count(node) AS chunks ORDER BY input,source;
