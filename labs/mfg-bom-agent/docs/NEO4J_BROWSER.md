# Neo4j Browser 사용 가이드 — mfg-bom-agent

Neo4j Browser 는 지식 그래프를 **눈으로 보고, Cypher 로 묻고, 결과를 확인하는** 웹 화면이다. 실습 중 데이터가 제대로 들어갔는지, 온톨로지 설계대로 연결됐는지 확인할 때 쓴다.

- 주소: http://localhost:7474 (바이오 실습은 http://localhost:7475)
- 계정: 사용자 `neo4j` / 비밀번호는 프로젝트 `.env` 의 `NEO4J_PASSWORD`
- 기준: Neo4j 5.26.32 Community, 2026-10-25 캡처. Neo4j Browser 는 버전에 따라 메뉴 위치가 조금씩 바뀔 수 있다.

Neo4j 가 아직 떠 있지 않다면 [INSTALL.md](../INSTALL.md) 의 5단계(Neo4j 와 Langfuse 띄우기)를 먼저 한다.

## 목차

1. [접속하기](#1-접속하기)
2. [화면 구성](#2-화면-구성)
3. [데이터베이스 개요](#3-데이터베이스-개요)
4. [쿼리 실행](#4-쿼리-실행)
5. [그래프 보기](#5-그래프-보기)
6. [노드 상세](#6-노드-상세)
7. [Graph · Table · Raw 보기 전환](#7-graph--table--raw-보기-전환)
8. [히스토리와 Cypher 레퍼런스](#8-히스토리와-cypher-레퍼런스)
9. [실습에서 자주 쓰는 명령](#9-실습에서-자주-쓰는-명령)
10. [자주 막히는 곳](#10-자주-막히는-곳)

---

## 1. 접속하기

처음 열면 접속 창이 뜬다.

（화면 캡처는 강의 자료에서 확인합니다.）

| 단계 | 항목 | 넣을 값 |
|---|---|---|
| 1 | 주소 열기 | 브라우저에서 http://localhost:7474 (바이오 실습은 7475) |
| 2 | Protocol | `neo4j://` 그대로 둔다 |
| 3 | Connection URL | `localhost:7687` (바이오 실습은 `localhost:7688`) |
| 4 | Database user | `neo4j` |
| 5 | Password | 프로젝트 `.env` 파일의 `NEO4J_PASSWORD` 값 |
| 6 | Connect | 결과 영역에 `Connected to neo4j://localhost:7687` 이 보이면 성공 |

**Connect with SSO** 는 쓰지 않는다. 로컬 실습은 사용자 이름과 비밀번호로 접속한다.

---

## 2. 화면 구성

화면은 다섯 구역으로 나뉜다.

（화면 캡처는 강의 자료에서 확인합니다.）

| 번호 | 구역 | 설명 |
|---|---|---|
| ① | 연결 바 | 접속한 인스턴스 · 데이터베이스 · 사용자. 초록 점이면 연결된 상태다 |
| ② | 사이드바 탭 | 왼쪽부터 데이터베이스 개요 · 저장한 쿼리(Queries) · 히스토리 · Cypher 레퍼런스 · 파라미터 · 설정 |
| ③ | 쿼리 편집기 | Cypher 를 입력하고 오른쪽 **Run** 으로 실행한다 |
| ④ | 결과 스트림 | 실행할 때마다 결과 프레임이 위에서부터 쌓인다 |
| ⑤ | 사이드 패널 | ②에서 고른 탭의 내용이 여기에 열린다 |

처음 접속하면 "Work in tabs" 같은 새 기능 안내 창이 뜰 수 있다. **Dismiss** 를 누르면 닫힌다.

---

## 3. 데이터베이스 개요

그래프에 무엇이 있는지 먼저 본다. 사이드바 첫 번째 탭(데이터베이스 아이콘)을 누르면 열린다.

（화면 캡처는 강의 자료에서 확인합니다.）

| 영역 | 내용 |
|---|---|
| **Nodes** | 그래프에 있는 노드 라벨 목록. 괄호 안 숫자는 전체 노드 수 |
| **Relationships** | 관계 타입 목록. 적재 후에는 BOM·부품·문서 연결 관계가 보인다 |
| **Property keys** | 노드와 관계에 쓰인 속성 이름 목록. 온톨로지의 속성 설계가 그대로 보인다 |

> `scripts/init_data.py`는 제약 생성뿐 아니라 실습 데이터 적재·검증·문서 연결·검색 색인까지 실행한다. 초기화 완료 후 업무 노드와 관계가 보여야 한다. `LabMeta` 1개만 보이거나 관계가 없다면 적재 로그와 접속한 DB를 확인한다.

---

## 4. 쿼리 실행

편집기에 Cypher 를 입력하고 실행한다.

| 키 | 동작 |
|---|---|
| `Enter` | 한 줄 쿼리를 바로 실행 |
| `Shift` + `Enter` | 줄 바꿈 — 여러 줄로 작성 |
| `⌘` + `Enter` (Windows · Linux 는 `Ctrl` + `Enter`) | 여러 줄 쿼리 실행 |
| **Run** 버튼 | 편집기 오른쪽. 키보드 대신 눌러도 된다 |

> macOS 에서 직접 눌러 확인한 동작이다. Windows · Linux 의 `Ctrl` + `Enter` 는 같은 편집기 규칙을 따르지만 아직 확인하지 않았다.

예시: 지금 DB 에 만든 유일성 제약 보기

```cypher
SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties
```

（화면 캡처는 강의 자료에서 확인합니다.）

노드가 아닌 결과는 표(Table)로 나온다. 제약 이름과 대상 라벨·속성을 `ontology/schema.yaml`의 정의와 대조한다. 적재 여부는 노드와 관계도 함께 확인한다.

| 조작 | 동작 |
|---|---|
| `:clear` | 결과 프레임을 모두 지운다. 화면이 복잡해지면 쓴다 (Browser 명령, Cypher 아님) |
| 프레임 오른쪽 위 **✕** | 그 결과 하나만 닫는다 |
| 프레임 오른쪽 위 **Run** | 같은 쿼리를 다시 실행한다 |

---

## 5. 그래프 보기

노드와 관계가 들어 있는 결과는 그래프로 그려진다.

（화면 캡처는 강의 자료에서 확인합니다.）

| 번호 | 구역 | 설명 |
|---|---|---|
| ① | Graph · Table · Raw | 결과 보기 방식 전환 ([7절](#7-graph--table--raw-보기-전환)) |
| ② | 그래프 캔버스 | 원 = 노드, 화살표 = 관계. 색은 라벨마다 다르다. 드래그로 옮기고 스크롤로 확대 |
| ③ | Results overview | 결과에 들어 있는 라벨 · 관계 타입별 개수 |
| ④ | 도구 막대 | 확대 · 축소 · 화면에 맞추기 · 레이아웃 변경 |
| ⑤ | PNG 내려받기 | 보이는 그래프를 이미지로 저장 |

> **예시 그래프는 DB 에 저장되지 않는다.** 아직 실습 데이터를 적재하기 전이라, 위 화면은 APOC 가상 노드(`apoc.create.vNode`, `apoc.create.vRelationship`)로 제조 BOM 모양(로버 → 조립품 → 부품 → 공급사)을 화면에만 그린 것이다. 직접 해 보려면 아래 쿼리를 그대로 실행한다. 아무것도 저장되지 않는다.

```cypher
WITH apoc.create.vNode(['Product'], {name:'Open Source Rover', product_id:'OSR-1'}) AS rover
WITH rover, apoc.create.vNode(['Assembly'], {name:'Drive Wheel'}) AS wheel,
     apoc.create.vNode(['Assembly'], {name:'Corner'}) AS corner
WITH rover, wheel, corner,
     apoc.create.vNode(['Part'], {name:'Yellow Jacket Motor', part_id:'5203'}) AS motor,
     apoc.create.vNode(['Part'], {name:'Servo 25kg', part_id:'2000-0025-0002'}) AS servo,
     apoc.create.vNode(['Part'], {name:'Flanged Bearing', part_id:'1611-0014-4008'}) AS bearing,
     apoc.create.vNode(['Supplier'], {name:'goBILDA'}) AS gobilda
RETURN rover, wheel, corner, motor, servo, bearing, gobilda,
  apoc.create.vRelationship(rover, 'HAS_ASSEMBLY', {qty:6}, wheel) AS r1,
  apoc.create.vRelationship(rover, 'HAS_ASSEMBLY', {qty:4}, corner) AS r2,
  apoc.create.vRelationship(wheel, 'USES_PART', {qty:1}, motor) AS r3,
  apoc.create.vRelationship(wheel, 'USES_PART', {qty:2}, bearing) AS r4,
  apoc.create.vRelationship(corner, 'USES_PART', {qty:1}, servo) AS r5,
  apoc.create.vRelationship(motor, 'SUPPLIED_BY', {}, gobilda) AS r6,
  apoc.create.vRelationship(servo, 'SUPPLIED_BY', {}, gobilda) AS r7,
  apoc.create.vRelationship(bearing, 'SUPPLIED_BY', {}, gobilda) AS r8
```

수량·부품번호는 화면 예시용 값이다. 실제 BOM 은 실습 데이터 적재 단계에서 다룬다.

---

## 6. 노드 상세

그래프에서 노드를 누르면 오른쪽에 속성이 보인다.

（화면 캡처는 강의 자료에서 확인합니다.）

| 항목 | 설명 |
|---|---|
| 라벨 칩 | 노드의 라벨(타입). 위 예시는 `Product` |
| Key · Value | 노드에 저장된 속성 목록. `<id>` 는 Neo4j 내부 ID 라 업무 키로 쓰지 않는다 — 업무 키는 `product_id`, `part_id` 처럼 온톨로지에서 정한 속성을 쓴다 |
| 복사 아이콘 | 값 하나를 바로 복사한다. 쿼리 조건을 만들 때 편하다 |

---

## 7. Graph · Table · Raw 보기 전환

같은 결과를 세 가지로 볼 수 있다. 결과 프레임 왼쪽 위 탭으로 바꾼다.

（화면 캡처는 강의 자료에서 확인합니다.）

| 보기 | 쓰는 때 |
|---|---|
| **Graph** | 노드 · 관계가 있는 결과의 기본 보기. 연결 구조를 눈으로 확인할 때 |
| **Table** | 행 · 열 표. 노드는 라벨 색 칩으로 나온다. 노드가 아닌 결과(`SHOW CONSTRAINTS` 등)는 Table 과 Raw 만 있다 |
| **Raw** | 드라이버가 받은 원본 레코드. 값이나 타입을 정확히 확인할 때 |

---

## 8. 히스토리와 Cypher 레퍼런스

（화면 캡처는 강의 자료에서 확인합니다.） （화면 캡처는 강의 자료에서 확인합니다.）

| 탭 | 설명 |
|---|---|
| **History** | 실행한 쿼리가 시간순으로 남는다. 지난번에 쓴 쿼리를 다시 찾을 때 본다. 위쪽 아이콘으로 지우기 · 내려받기 · 검색 |
| **Cypher reference** | `MATCH` · `WHERE` · `CREATE` · `MERGE` 같은 문법을 예시와 함께 찾아본다. 위쪽 검색창으로 바로 찾는다 |
| 나머지 탭 | **Queries** — 저장한 쿼리 모음 · **Parameters** — 쿼리에 넣을 `$파라미터` 값 · **Settings** — 화면 설정 |

---

## 9. 실습에서 자주 쓰는 명령

| 명령 | 용도 |
|---|---|
| `MATCH (n) RETURN n LIMIT 25` | 노드를 25개까지만 본다. 처음 볼 때는 항상 `LIMIT` 을 붙인다 |
| `MATCH (n) RETURN labels(n) AS label, count(*) AS cnt` | 라벨별 노드 수. 데이터가 제대로 들어갔는지 확인 |
| `SHOW CONSTRAINTS` | 유일성 제약 목록. `ontology/schema.yaml`의 라벨·속성과 대조 |
| `CALL db.schema.visualization()` | 라벨과 관계 타입의 구조(스키마)를 그래프로 본다 |
| `MATCH (a)-[:USES_PART]->(p:Part {part_id:'5203'}) RETURN a, p` | 특정 부품을 쓰는 조립품 찾기 — 실습 데이터 적재 후 |
| `:clear` | 결과 프레임을 모두 지운다 (Browser 명령, Cypher 아님) |

복사해서 쓰기 좋게 한 번 더:

```cypher
MATCH (n) RETURN n LIMIT 25
```

```cypher
MATCH (n) RETURN labels(n) AS label, count(*) AS cnt
```

```cypher
SHOW CONSTRAINTS
```

```cypher
CALL db.schema.visualization()
```

---

## 10. 자주 막히는 곳

| 증상 | 원인과 해결 | 확인 명령 (터미널) |
|---|---|---|
| 접속이 안 돼요 | Neo4j 컨테이너가 떠 있는지 확인한다. `mfg-neo4j` 가 `(healthy)` 여야 한다. 바이오 실습은 주소 7475 · Bolt 7688 | `docker compose ps` |
| 비밀번호가 틀렸대요 | `.env` 의 `NEO4J_PASSWORD` 를 확인한다. Neo4j 를 처음 띄운 뒤 비밀번호를 바꿨다면 데이터를 지우고 다시 띄워야 적용된다 | `docker compose down -v` (데이터 삭제 주의) |
| 화면이 느려지거나 멈춰요 | 결과가 너무 크다. 그래프는 노드 수백 개만 넘어도 무거워진다. 쿼리 끝에 `LIMIT` 을 붙인다 | `... RETURN n LIMIT 25` |
| 데이터를 지울까 걱정돼요 | `DELETE` · `DETACH DELETE` 는 되돌릴 수 없다. 실습 중에는 조회(`MATCH` · `SHOW`)만 쓰고, 다시 만들 때는 적재 스크립트를 쓴다 | `uv run python scripts/init_data.py` |

---

### 이미지 파일

공개 배포본에는 화면 캡처를 포함하지 않습니다. 화면 구성은 강의 자료와 실제 실행 화면에서 확인합니다.

Docker 로 이 실습을 켜고 끄고 초기화하는 방법은 [DOCKER.md](DOCKER.md) 를 본다.
