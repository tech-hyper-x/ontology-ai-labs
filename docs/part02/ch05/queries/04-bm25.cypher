// CQ-11 또는 G44로 바꿉니다. 같은 example과 문서 범위로 벡터 검색과 대조합니다.
MATCH (e:SearchExample {id:'CQ-11'})
CALL db.index.fulltext.queryNodes('doc_fulltext',e.lucene,{limit:20}) YIELD node,score
WHERE node.source <> 'bom_text'
RETURN e.query_en AS query,node.doc_id AS doc_id,node.title AS title,node.path AS path,node.line AS line,
 score AS bm25_score,node.text AS text
ORDER BY bm25_score DESC LIMIT 5;
