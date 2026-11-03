// Synthetic inputs only. No DB writes. First run: inspect every row.
// Then write a WHERE condition to return invalid cases only. INSTRUCTOR.md has a reference.
UNWIND [
 {id:'normal',ref_count:1,rev_count:1,stored_revision:'R1',linked_revision:'R1'},
 {id:'missing_part',ref_count:0,rev_count:1,stored_revision:'R1',linked_revision:'R1'},
 {id:'two_parts',ref_count:2,rev_count:1,stored_revision:'R1',linked_revision:'R1'},
 {id:'wrong_revision',ref_count:1,rev_count:1,stored_revision:'R1',linked_revision:'R2'}
] AS row
WITH row
// Add WHERE here. Do not change the initial inputs to match your prediction.
RETURN row.id AS id,row.ref_count AS ref_count,row.rev_count AS rev_count,
 row.stored_revision AS stored_revision,row.linked_revision AS linked_revision;
