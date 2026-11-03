---
name: bom-question-planning
id: S1
when: 모든 질문
tools: []
---
# 질문 계획

1. 질문 유형을 하나로 정한다: purchase_quantity(구매 수량) · cost(원가) · price_change(단가 변경) · discontinue(단종) ·
   revision_change(BOM 판 · ECN 변경) · supply_disruption(공급 중단) · symptom(증상 · 정비) · part_info(부품 정보) · other
2. 계산에 필요한 값을 질문에서 꺼낸다: 부품 이름 · 품번, 생산 대수, 변경률(%), 판 · ECN · 날짜, 공급사, 증상 문장
3. 증상 문장은 영어 검색어로 바꾼다 (원천 문서가 영어다). 예: "코너 휠이 안 돌아요" → "corner wheels will not turn servo"
4. 꼭 필요한 값이 없으면 추측하지 않고 되묻는다. 생산 대수가 없는 원가 질문은 1대로 계산하고 그 가정을 밝힌다.
5. 시점이 없으면 최신 BOM 판 · 스냅샷 관측일(2026-10-22)을 쓰고 답변에 밝힌다.
