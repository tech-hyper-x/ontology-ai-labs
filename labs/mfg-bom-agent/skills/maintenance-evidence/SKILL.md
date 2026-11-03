---
name: maintenance-evidence
id: S5
when: 증상 문장 (정비 · 품질)
tools: [search_docs, find_part, where_used, cost_rollup]
---
# 정비 근거

1. search_docs 로 증상에 맞는 정비 문서를 찾는다 (영어 검색어).
2. 문서에 연결된 부품 중 고장 모드(FailureMode)로 연결된 부품을 원인 후보로 고른다.
3. where_used 로 그 부품이 쓰인 어셈블리를 확인한다.
4. 교체 부품비는 cost_rollup(items=[{part, qty_each: 1}]) 로 1개 기준 부품비만 계산한다 (공임 · 운송비 제외).
5. 답변에는 근거 문서 경로와 줄 번호를 넣는다. 문서가 원인을 확정하지 않으면 "점검 후보"로 쓴다.
