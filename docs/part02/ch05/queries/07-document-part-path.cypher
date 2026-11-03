// 진단 청크는 제공 FailureMode를 경유합니다. 두 관계 이름과 방향을 Graph로 읽습니다.
MATCH p=(part:Part)-[:HAS_FAILURE_MODE]->(:FailureMode)-[:DESCRIBED_IN]->(doc:Document {doc_id:'mechanical/servo_gear_replacement/README.md#2'})
RETURN p;

// 직접 부품 연결도 따로 확인합니다.
MATCH p=(part:Part)-[:DESCRIBED_IN]->(doc:Document {doc_id:'mechanical/servo_gear_replacement/README.md#1'})
RETURN p;
