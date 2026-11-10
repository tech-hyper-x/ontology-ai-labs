# Part 2 · Ch4 — 지식 그래프 적재와 경로 조회

Ch3에서 정한 개체·관계·판별 투입 내역을 Neo4j에 구현하고, 같은 판의 사용처를 조회합니다. **두 강의 각 15분**의 설명·실행 확인 배분입니다. 최초 설치·다운로드·수강생별 실행 대기 시간은 별도입니다.

|강의|흐름|남길 결과|
|---|---|---|
|10 부품 그래프 적재|가공 CSV → 적재 코드 → 전용 DB 재적재 → 건수·규칙 대조|적재 대응표·확인 기록|
|11 영향 경로 Cypher 작성|품번·판 선택 → 직접 사용처 → 제품 경로 → 수량 재료 → 직접 작성|조회문·결과 기록|

## 시작 위치와 사전 조건

Part 1 Ch3에서 Docker·uv·Neo4j 환경을 준비하고 Part 2 Ch2~Ch3에서 매핑·정규화·변경 모델을 확인합니다. 새로 받는 경우 루트의 [설치 가이드](../../setup/README.md)를 먼저 따릅니다.

```bash
cd ontology-ai-labs/labs/mfg-bom-agent
uv sync --all-extras
docker compose up -d neo4j
```

`.env`의 `NEO4J_URI`, 사용자명, 비밀번호를 본인 전용 실습 DB에 맞춥니다. 암호를 화면에 표시하지 않습니다. 다른 업무 데이터가 들어 있는 DB에서는 다음 명령을 실행하지 않습니다.

## 10강 · 적재 흐름

1. `data/processed/plm_item_master.csv`, `plm_assembly.csv`, `plm_revision.csv`, `plm_ebom_line.csv`를 열어 [적재 대응표](worksheets/load-map.csv)에 개체·키·관계를 적습니다.
2. [적재 구현](../../../labs/mfg-bom-agent/src/mfg_bom_agent/graph/load.py)을 읽습니다. 경로는 저장소 루트 기준 `labs/mfg-bom-agent/src/mfg_bom_agent/graph/load.py`입니다. `UNWIND $rows`, `MERGE`, `SET`, `MATCH` 순서와 BOMLine의 세 관계를 확인합니다.
3. [실행 체크리스트](worksheets/load-checklist.md)를 읽고 전용 DB에서 실행합니다.

```bash
uv run python scripts/load_graph.py
uv run python ../../examples/part02/ch04/ch04_audit.py
```

`load_graph.py`는 LabMeta를 제외한 기존 노드를 지우고 재생성합니다. MERGE가 있어도 **증분 적재가 아닙니다**. 여러 배치·쿼리로 진행하며, 전체 적재를 단일 원자적 트랜잭션으로 취급하지 않습니다. 출력 `counts`에는 입력 행 수가 포함되므로 실제 노드·관계 수와 따로 대조합니다.

4. [DB 건수·현재 판 조회](queries/01-load-inventory.cypher)와 [Ch3 모터 비교](../ch03/queries/)를 Neo4j Browser에서 실행합니다. 이전 판 `d6d1fbc`의 `5202-2402-0027`와 이후 판 `d092d83`의 `5203-2402-0027`를 확인합니다.
5. Ch2에서 함수를 수정한 것과 제공 가공 CSV가 바뀐 것은 별개입니다. 이 강의는 **배포된 CSV를 적재**합니다. 원천 전체를 재수집하는 `build_dataset.py`를 필수 단계로 실행하지 않습니다.

### 재적재 후 검색 상태

문서 노드·임베딩·문서-부품 연결·검색 예시가 초기화됩니다. 이 챕터의 완료 기준은 그래프·개정판·검증 확인입니다. 앱 검색 성공까지 요구하지 않습니다. Ch5에서 `uv run python scripts/build_index.py`로 문서 연결과 검색 색인을 다시 만듭니다. 이때 임베딩 서비스 계정·사용료가 필요할 수 있습니다.

## 11강 · Neo4j Browser에서 순서대로

Browser는 [Neo4j 사용 안내](../../../labs/mfg-bom-agent/docs/NEO4J_BROWSER.md)를 참고합니다. 각 파일은 **세미콜론으로 구분된 문장 하나씩** 실행합니다. Graph는 연결, Table은 필드·수량·출처를 읽는 용도입니다.

1. [02 직접 사용처](queries/02-direct-usage.cypher): 품번·판을 정하고 Assembly → BOMLine → Part를 읽습니다.
2. [03 완제품 경로](queries/03-product-path.cypher): Graph로 경로를 펼친 뒤 Table에서 모든 투입 내역의 판·수량 재료를 확인합니다.
3. [04 판 범위](queries/04-revision-scope.cypher): 이전 모터의 사용 판과 최신 판의 빈 결과를 대조합니다.
4. [05 수량 재료](queries/05-quantity-materials.cypher): 휠의 계수/낱개 6/6, 스페이서 1/4를 확인합니다. 입력 버전이 달라지면 실제 결과를 우선합니다.
5. [06 작성 템플릿](queries/06-usage-template.cypher)의 관계·판 조건·반환 필드를 직접 완성합니다. AI에게도 품번·판·반환값을 명시합니다.
6. [07 여러 경로 합산](queries/07-path-sum-example.cypher)은 DB를 수정하지 않는 **가상 예제**입니다. 2×2+1×3=7을 확인합니다. 실제 휠·스페이서는 이 데이터에서 각각 한 경로입니다.
7. [조회 기록표](worksheets/query-record.csv)에 조건·결과·단위를 남기고 [독립 확인 예제](../../../examples/part02/ch04/ch04_audit.py)를 대조합니다.

`queries/cq_01_where_used.cypher`는 `WITH v`로 시작하며 런타임이 `_revision.cypher`를 붙여 실행합니다. 이를 Browser에 단독으로 붙이지 말고 이 폴더의 독립 실행 조회문을 사용합니다. 경로 **모든 BOMLine**에 같은 판 조건을 적용합니다. `path_factor`에는 팩 크기가 없고 `qty_each`에는 이미 반영되어 있으므로 중복 계산하지 않습니다.

이 조회는 등록된 구성의 사용처입니다. 실제 생산 영향 판단·최종 정밀 원가 계산·MCP 도구 작성은 이후 챕터에서 다룹니다.

[강사용 진행 메모·완성 예](INSTRUCTOR.md)

## 장표 번호별 실습

- [90장 · CSV 행의 파라미터 기반 적재](slide-090.md)
- [91장 · 판별 투입 내역과 관계의 적재](slide-091.md)
- [92장 · 전용 실습 DB의 데이터 재적재](slide-092.md)
- [93장 · 적재 건수와 실제 연결의 검증](slide-093.md)
- [94장 · 그래프 적재와 검색 준비의 구분](slide-094.md)
- [96장 · 사용처 조회의 부품·개정판 조건](slide-096.md)
- [97장 · 투입 내역 기반 직접 사용처 조회](slide-097.md)
- [98장 · 부품에서 완제품까지의 경로 탐색](slide-098.md)
- [99장 · 경로 전체의 개정판 조건 적용](slide-099.md)
- [100장 · 경로 계수와 낱개 수량의 구분](slide-100.md)
- [101장 · 동일 개정판의 사용처 조회문 작성](slide-101.md)
- [102장 · 동일 입력 기준 경로·수량 대조](slide-102.md)
