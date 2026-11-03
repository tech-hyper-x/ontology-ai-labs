// 원본 파일의 진단 절과 path/title/line/text를 대조합니다.
MATCH (d:Document) WHERE d.path='mechanical/servo_gear_replacement/README.md'
RETURN d.doc_id AS doc_id,d.path AS path,d.title AS title,d.line AS line,d.text AS text
ORDER BY line;
