# 32장 · 부품번호·개정판 기준 사용처 조회

Part 1 / Ch3 · [장표별 실습 목차](../../hands-on/README.md) · [Ch3 전체 실행 안내](../../ch03-run-guide.md)

## 무엇을 확인하나요?

휠 부품이 어느 조립품에 사용되는지 조회합니다. 먼저 결과를 표로 보고, 같은 조회문을 직접 수정해 조립품 → 투입 내역 → 부품의 연결을 그래프로 확인합니다. 원가나 구매 팩 수를 계산하는 실습은 아닙니다.

## 시작 전 준비

- [설치·서비스·데이터 준비](../../ch03-run-guide.md)를 마칩니다. Docker 설치만 끝낸 상태와 데이터가 적재된 상태는 다릅니다.
- [Neo4j Browser 열기](http://localhost:7474/browser/). 포트를 변경했다면 본인 접속 주소를 사용합니다.
- 연결된 DB가 **제조 실습용 `neo4j`**인지 확인합니다. 바이오 DB에서 실행하지 않습니다.
- 이 실습은 읽기 전용입니다. 이미 준비한 DB를 다시 초기화하지 않습니다.
- 코드는 Browser **상단 쿼리 입력창**에 넣습니다. 터미널에 붙여 넣지 않습니다. 실행은 입력창의 실행 버튼 또는 `Ctrl+Enter`로 진행합니다.

## 1. 부품번호와 조회 기준 입력

[입력 조건 파일](../../../examples/part01/ch03/slide-032/00-params.cypher)

아래 코드 블록만 복사해서 입력창에 붙여 넣고 **단독 실행**합니다.

```cypher
:params {part: '3616-0014-0144', revision: null}
```

| 항목 | 의미 |
|---|---|
| `part` | 이번에 찾을 휠 부품의 SKU인 `3616-0014-0144` |
| `revision` | 조회할 부품 구성의 개정판 |
| `null` | 이 예제에서 최신 개정판을 선택하기 위한 입력값 |

`:params`는 입력값을 저장하는 Browser 명령입니다. 아직 사용처를 조회한 것이 아닙니다. 다음 `MATCH` 코드와 한꺼번에 실행하지 않습니다. 새 Browser 연결에서는 다시 설정해야 합니다.

## 2. 사용처를 표로 조회

[표 조회 파일](../../../examples/part01/ch03/slide-032/01-table.cypher)

입력 조건 실행이 끝나면 입력창을 아래 코드로 바꾸고 실행합니다. 앞에서 저장한 입력 조건은 유지됩니다.

```cypher
MATCH (v:Revision)
WHERE ($revision IS NULL AND v.is_latest)
   OR v.revision_id = $revision
MATCH (a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(p:Part)
WHERE (p.sku = $part OR p.part_id = $part)
  AND l.revision_id = v.revision_id
RETURN p.sku AS sku, a.name AS assembly,
       v.revision_id AS revision,
       l.raw_qty_text AS raw_qty,
       l.qty_each_text AS qty_each
ORDER BY assembly;
```

### 코드를 위에서부터 읽어보기

| 코드 | 하는 일 |
|---|---|
| `MATCH (v:Revision)` | 부품 구성의 개정판을 찾습니다. `v`는 이 조회문에서 사용할 개정판의 이름입니다. |
| `$revision IS NULL AND v.is_latest` | 입력값이 `null`이면 최신 개정판을 고릅니다. |
| `OR v.revision_id = $revision` | 개정판 ID를 직접 넣었다면 그 ID에 해당하는 개정판을 고릅니다. |
| `(a:Assembly)` | 조립품입니다. |
| `-[:HAS_BOM_LINE]->(l:BOMLine)` | 조립품의 투입 내역으로 이동합니다. |
| `-[:REFERS_TO]->(p:Part)` | 그 투입 내역에서 사용하는 부품으로 이동합니다. |
| `p.sku = $part OR p.part_id = $part` | 입력한 값이 부품의 SKU 또는 내부 부품 ID와 같은지 확인합니다. |
| `l.revision_id = v.revision_id` | 선택한 개정판에 속한 투입 내역만 남깁니다. |
| `RETURN ... AS ...` | 표에 보여줄 값을 정하고 열 이름을 붙입니다. |
| `ORDER BY assembly` | 조립품 이름 순서로 정렬합니다. |

괄호 `( )`는 노드를, 화살표 사이의 `[ ]`는 관계를 표현합니다. `$part`와 `$revision`은 1단계에서 저장한 입력값을 읽습니다.

### 결과 확인

| 표의 열 | 확인할 내용 |
|---|---|
| `sku` | 내가 입력한 휠 부품번호인지 |
| `assembly` | 이 휠 부품을 직접 사용하는 조립품 |
| `revision` | 이번 조회에서 실제로 선택된 개정판 ID |
| `raw_qty` | 원본 자료에 적힌 수량 표기 |
| `qty_each` | 낱개 단위로 정리한 수량 표기 |

부품번호·조립품·개정판을 함께 확인합니다. 수량은 투입 내역의 값이며, 원본 표기와 낱개 수량을 같은 뜻으로 읽지 않습니다. 데이터가 바뀌면 행 수와 값도 달라질 수 있습니다. 반환된 개정판은 다음 MCP 실습에서 같은 조건을 지정할 때 사용합니다.

## 3. 같은 조회문을 그래프 반환 방식으로 직접 수정

먼저 2단계 코드를 입력창에서 직접 고쳐봅니다.

1. `MATCH (a:Assembly)`를 `MATCH path = (a:Assembly)`로 바꿉니다. 연결 경로에 `path`라는 이름을 붙이는 것입니다.
2. `RETURN p.sku ...`부터 마지막 `ORDER BY assembly;`까지 지웁니다.
3. 그 자리에 `RETURN path;`를 입력합니다.
4. 부품번호·개정판 필터는 유지한 채 실행합니다.
5. 결과의 **Graph 보기**를 선택합니다.

수정할 핵심 부분은 다음과 같습니다.

```diff
-MATCH (a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(p:Part)
+MATCH path = (a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(p:Part)
```

반환 부분은 여러 열과 정렬문 전체를 지우고 `RETURN path;` 하나로 교체합니다. 표 조회 결과는 문자·숫자를 반환하므로 보기 버튼만 바꿔서는 연결 그림이 나오지 않습니다.

### 수정 후 전체 코드

[그래프 조회 파일](../../../examples/part01/ch03/slide-032/02-graph.cypher)

직접 수정하다 막히면 아래 완성본을 복사해서 이어갈 수 있습니다. 새 연결에서 실행한다면 1단계 입력 조건부터 다시 실행합니다.

```cypher
MATCH (v:Revision)
WHERE ($revision IS NULL AND v.is_latest)
   OR v.revision_id = $revision
MATCH path = (a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(p:Part)
WHERE (p.sku = $part OR p.part_id = $part)
  AND l.revision_id = v.revision_id
RETURN path;
```

## 4. 투입 내역을 선택해 수량과 개정판 확인

- 그래프에서 **Assembly → BOMLine → Part** 순서로 연결을 따라갑니다.
- 가운데 `BOMLine` 노드를 클릭해 속성 패널을 엽니다.
- `qty_each`와 `revision_id`를 확인합니다.
- 화면에 `raw_qty_text`와 `pack_size`가 있다면 원본 수량 표기와 묶음 크기도 함께 봅니다.
- 노드에 표시되는 이름은 화면 설정에 따라 다를 수 있습니다. 노드를 선택한 뒤 라벨과 속성으로 확인합니다.

같은 부품도 조립품마다 필요한 수량이 다를 수 있습니다. 그래서 부품 자체의 정보와 조립품별 투입 내역을 구분하고, 투입 내역에 수량과 개정판을 남깁니다.

## 결과가 나오지 않는다면

1. `ParameterMissing`이면 1단계 `:params`를 **같은 Browser 연결에서** 먼저 실행했는지 봅니다.
2. 결과가 0행이면 부품번호 오타, 개정판 조건, 제조 데이터 적재 여부, 선택한 DB를 확인합니다. 바로 사용처가 없다고 결론 내리지 않습니다.
3. 그래프가 보이지 않으면 `RETURN path;`인지 확인합니다. 기존 `ORDER BY assembly`는 지워야 합니다.
4. 연결 자체가 실패하면 [공통 실행 안내](../../ch03-run-guide.md)에서 서비스 상태와 접속 설정을 확인합니다. 개인 비밀번호와 API 키를 공유하지 않습니다.

## 다음 실습

같은 부품번호와 표에서 실제 반환된 개정판으로 [MCP 도구를 호출](../../../examples/part01/ch03/README.md)해 결과를 비교합니다. 32장 샘플 촬영은 투입 내역의 수량·개정판 확인과 정리에서 마칠 수 있습니다.
