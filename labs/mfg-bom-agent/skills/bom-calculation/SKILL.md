---
name: bom-calculation
id: S3
when: 수량 · 원가 · 구매 질문
tools: [bom_explode, purchase_quantity, cost_rollup]
---
# BOM 계산

- 숫자는 도구 출력만 쓴다. 곱셈 · 반올림을 직접 하지 않는다.
- 총소요 낱개 질문(required_quantity): 부품 식별 → where_used → bom_explode. 같은 부품의 모든 투입 내역을 합친다. 생산 대수가 없으면 되묻고, 판에 내역이 없으면 수량을 0으로 단정하지 않는다.
- 소요 수량: bom_explode — 낱개 수 = 원천 수량 × 팩 크기 × 어셈블리 배수 × 생산 대수
- 구매 수량: purchase_quantity — 구매 팩 수 = max(올림(소요 낱개 ÷ 팩 크기), MOQ). MOQ 는 교육용 가정값이다.
- 원가: cost_rollup — 소요 원가(팩 올림 · MOQ 미반영). 구매 금액과 다르다는 것을 구분해서 쓴다.
- 금액은 USD, 가격은 스냅샷 관측일 기준이며 실제 가격 기준일은 미상이다.
