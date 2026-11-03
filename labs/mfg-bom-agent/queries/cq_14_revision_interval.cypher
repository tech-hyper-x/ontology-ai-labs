// CQ-14 BOM 판 R의 저장소상 적용 구간은? (사실 조회) — [valid_from, valid_to), 실제 생산 적용일이 아니다
MATCH (r:Revision) WHERE r.revision_id = $revision_id
RETURN r.revision_id AS revision, toString(r.valid_from) AS valid_from,
       coalesce(toString(r.valid_to), '현재') AS valid_to, r.is_latest AS is_latest, r.message AS message
