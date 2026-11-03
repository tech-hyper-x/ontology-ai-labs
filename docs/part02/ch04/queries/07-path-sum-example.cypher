// 가상 경로 2개. DB에 노드나 관계를 만들지 않습니다. 실제 휠의 경로 수가 아닙니다.
UNWIND [{path:'A',qty_each:2,multiplier:2},{path:'B',qty_each:1,multiplier:3}] AS row
RETURN collect({path:row.path,each:row.qty_each*row.multiplier}) AS paths,
 sum(row.qty_each*row.multiplier) AS total_each;
