// Ch1 데이터 관찰: 전체 라벨 분포. LabMeta·SearchExample은 업무 개념과 구분합니다.
MATCH (n)
UNWIND labels(n) AS label
RETURN label, count(*) AS count
ORDER BY label;
