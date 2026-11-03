# 스킬 (Part 2 Ch7-1 질문별 도구 호출 경로)

스킬은 코드가 아니라 **업무 절차 문서**다. 언제 쓰는지, 어떤 도구를 어떤 순서로 부르는지, 언제 멈추고 되묻는지를 적는다.
에이전트(`src/mfg_bom_agent/workflows/`)는 질문 유형에 맞는 스킬을 골라 이 순서대로 도구를 실행하고,
답변을 쓸 때 해당 스킬 문서를 시스템 프롬프트에 넣는다.

| ID | 스킬 | 언제 | 도구 순서 |
|---|---|---|---|
| S1 | bom-question-planning | 모든 질문 | (도구 없음) 유형 분류 · 필요한 값 확인 · 되묻기 |
| S2 | part-identity-resolution | 부품명 · 품번이 나올 때 | find_part |
| S3 | bom-calculation | 수량 · 원가 · 구매 질문 | bom_explode → purchase_quantity → cost_rollup |
| S4 | change-and-supply-risk | ECN · 단종 · 단가 · 공급사 | where_used → revision_diff / change_impact → supply_risk |
| S5 | maintenance-evidence | 증상 문장 | search_docs → find_part → where_used → cost_rollup(items) |
| 공통 | grounded-answer | 모든 답변 | 결론 · 계산 근거 · 그래프 근거 · 출처 · 가정 |
