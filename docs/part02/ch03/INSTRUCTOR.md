# Ch3 강사용 Hands-on 확인

## 변경 모델

모터: 이전 d6d1fbc / 5202-2402-0027, 이후 d092d83 / 5203-2402-0027. 둘 다 raw_qty=1, multiplier=6. 새 판의 구간은 [2023-07-18, 2023-07-26). 실제 생산 적용일이나 승인된 ECN 문서로 소개하지 않습니다. diff의 허브 역할 이름이 바뀐 경우 pair_supersedes가 자동으로 짝짓지 않는 이유도 확인합니다.

## 오류 조건 작성

AI 요청 예: “투입 내역은 하위 품목 연결과 개정판 연결이 각각 정확히 하나여야 합니다. 저장한 revision ID와 연결한 revision ID도 같아야 합니다. 제공 UNWIND 예제에서 위반 행만 찾는 WHERE 조건을 작성해 주세요. 입력과 DB는 변경하지 마세요.”

07-error-cases.cypher의 WITH row 다음에 추가합니다.

```cypher
WHERE row.ref_count <> 1 OR row.rev_count <> 1
   OR row.stored_revision <> row.linked_revision
```

초기 위반: missing_part, two_parts, wrong_revision 3행. 정상 행은 제외합니다. ref_count=0을 1로 고친 복사본에서는 2행이 반환됩니다. 실제 그래프 검사 성공과 작은 입력 예제의 성공은 구분합니다.

06-revision-consistency.cypher는 기존 31개 검사에 포함되지 않은 추가 제안입니다. 이 조건을 기존 시스템이 이미 검사한다고 설명하지 않습니다. 순환 검사는 코드의 경로 깊이 범위 안에서 수행됩니다. 검사 0건을 모든 업무 오류가 없다는 뜻으로 해석하지 않습니다.
