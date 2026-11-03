// 입력 행 수와 별도로 실제 노드 건수를 확인합니다.
MATCH (n) UNWIND labels(n) AS label
RETURN label,count(*) AS nodes ORDER BY label;

MATCH ()-[r]->() RETURN type(r) AS relationship,count(*) AS relationships ORDER BY relationship;

MATCH (v:Revision) WHERE v.is_latest
RETURN v.revision_id AS revision,v.valid_from AS valid_from,v.valid_to AS valid_to;
