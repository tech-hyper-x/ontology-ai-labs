MATCH (v:Revision)
WHERE v.revision_id IN ['d6d1fbc','d092d83','886bb13']
RETURN v.revision_id AS revision,toString(v.valid_from) AS valid_from,
 coalesce(toString(v.valid_to),'open') AS valid_to,v.is_latest AS is_latest
ORDER BY valid_from;

// Boundary dates: start inclusive, end exclusive. Repository dates, not production dates.
UNWIND [date('2023-07-17'),date('2023-07-18'),date('2023-07-26')] AS day
MATCH (v:Revision)
WHERE v.valid_from<=day AND (v.valid_to IS NULL OR day<v.valid_to)
RETURN toString(day) AS day,v.revision_id AS revision ORDER BY day;
