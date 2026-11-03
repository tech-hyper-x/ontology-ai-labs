// Browser는 이 파일에서 임베딩 API를 부르지 않고 저장된 질문 벡터를 사용합니다.
MATCH (e:SearchExample {id:'CQ-11'})
CALL db.index.vector.queryNodes('doc_vector',20,e.embedding) YIELD node,score
WHERE node.source <> 'bom_text'
RETURN e.query_en AS query,node.doc_id AS doc_id,node.title AS title,node.path AS path,node.line AS line,
 score AS vector_score,node.text AS text
ORDER BY vector_score DESC LIMIT 5;
