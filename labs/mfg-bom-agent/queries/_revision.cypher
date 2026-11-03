// 공통 조각: 조회 기준 판. $revision 이 null 이면 최신 판을 쓴다.
// 각 CQ 파일 맨 앞에 이 조각이 붙어서 실행된다 (graph/cq.py).
MATCH (v:Revision)
WHERE ($revision IS NULL AND v.is_latest) OR v.revision_id = $revision
