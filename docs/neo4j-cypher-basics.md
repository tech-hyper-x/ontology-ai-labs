# Neo4j 초보자를 위한 기본 Cypher 문법 가이드

Cypher(사이퍼)는 Neo4j에서 그래프 데이터를 찾고, 만들고, 수정하는 질의 언어입니다. 이 문서는 **사람과 수강 강좌** 예제로 문법을 익힌 뒤 강의의 제조·바이오 그래프 조회로 넘어가도록 구성했습니다.

- 대상: Neo4j와 Cypher를 처음 사용하는 학습자
- 기준 환경: 이 저장소의 **Neo4j 5.26 Community / Cypher 5**, APOC 등 추가 플러그인 불필요
- 실행 위치: Neo4j Browser의 질의 입력창. 코드 블록을 한 개씩 실행합니다.
- 독립 설치부터 시작하려면: [별도 practice DB로 설치·로그인·CLI 접속](setup/neo4j-standalone.md)
- 준비: [공통 설치 가이드](setup/README.md) · [Browser 사용법](../labs/mfg-bom-agent/docs/NEO4J_BROWSER.md)

> 먼저 1~3절을 순서대로 실행하세요. 4~10절은 조회, 11~12절은 데이터 변경입니다. 예상 결과는 3절의 초기 데이터만 있는 상태를 기준으로 합니다. 예제 전용 `CypherGuide` 라벨로 강의 데이터와 구분하며, 데이터 변경은 개인 실습 DB에서 진행합니다.

## 목차

1. [첫 질의 실행](#1-첫-질의-실행)
2. [그래프와 패턴 읽기](#2-그래프와-패턴-읽기)
3. [실습 데이터 준비](#3-실습-데이터-준비)
4. [MATCH와 RETURN: 찾고 보여주기](#4-match와-return-찾고-보여주기)
5. [WHERE: 조건으로 거르기](#5-where-조건으로-거르기)
6. [정렬·개수 제한·중복 제거](#6-정렬개수-제한중복-제거)
7. [관계와 경로 탐색](#7-관계와-경로-탐색)
8. [OPTIONAL MATCH와 null](#8-optional-match와-null)
9. [집계와 WITH](#9-집계와-with)
10. [파라미터와 UNWIND](#10-파라미터와-unwind)
11. [CREATE·MERGE·SET·REMOVE](#11-createmergesetremove)
12. [DELETE와 실습 데이터 정리](#12-delete와-실습-데이터-정리)
13. [제약 조건과 인덱스](#13-제약-조건과-인덱스)
14. [자주 하는 실수](#14-자주-하는-실수)
15. [연습 문제와 정답](#15-연습-문제와-정답)
16. [문법 요약과 다음 단계](#16-문법-요약과-다음-단계)

## 1. 첫 질의 실행

### 1.1 서버에 접속하기

설치를 마쳤다면 로컬 환경의 [Neo4j Browser](http://localhost:7474)에 접속하고 로그인합니다. 접속 주소·비밀번호는 본인의 설정을 사용하세요.

**서버 접속 → 사용할 데이터베이스 선택 → 선택 확인 → 질의 실행** 순서로 진행합니다. Browser에 로그인하는 것과, 그 서버 안에서 사용할 데이터베이스를 선택하는 것은 서로 다른 단계입니다.

### 1.2 데이터베이스 이해하고 목록 확인하기

Neo4j에도 **데이터베이스(Database)**가 있습니다. 노드와 관계는 선택한 데이터베이스 안에 저장됩니다.

| MySQL에서 익숙한 개념 | 이 실습의 Neo4j에서 대응하는 개념 |
|---|---|
| MySQL 서버에 접속 | Neo4j 서버(DBMS)에 접속 |
| 사용할 데이터베이스 선택. MySQL에서는 스키마라고도 부름 | 사용할 데이터베이스 선택 |
| 테이블·컬럼·외래 키로 데이터 구조 정의 | 노드·라벨·속성·관계로 그래프 구조 표현 |

MySQL의 `USE 데이터베이스명`과 Neo4j Browser의 데이터베이스 선택은 목적이 비슷하지만, 명령은 다릅니다. 아래 블록을 실행해 접근 가능한 데이터베이스를 확인합니다.

```cypher
SHOW DATABASES;
```

이 저장소의 기본 Neo4j 5.26 Community 환경에서는 다음 두 데이터베이스를 구분합니다.

- **`neo4j`**: 실습의 노드와 관계를 저장하고 조회하는 일반 데이터베이스입니다.
- **`system`**: DBMS 관리 정보를 다루는 시스템 데이터베이스입니다. 이 가이드의 실습 데이터는 여기에 넣지 않습니다.

Community Edition은 일반 데이터베이스 하나와 관리용 `system` 데이터베이스를 사용합니다. 이 실습에서는 새 데이터베이스를 만드는 대신 이미 준비된 `neo4j`를 선택합니다. 이름을 별도로 설정한 환경이라면 목록에서 실제 일반 데이터베이스 이름을 확인하세요.

### 1.3 사용할 데이터베이스 선택하기

Browser 입력창에 아래 명령을 **단독으로** 입력하고 실행합니다.

```text
:use neo4j
```

`:use`는 Neo4j Browser의 명령이며, Cypher 질의 자체가 아닙니다. 다른 Cypher 코드와 한 블록으로 합쳐 실행하지 않습니다. Browser의 데이터베이스 선택 메뉴에서도 같은 대상을 선택할 수 있습니다.

선택한 데이터베이스는 이후 Browser에서 실행하는 조회·생성·수정·삭제의 대상이 됩니다. 서버 주소가 같아도 선택한 데이터베이스가 다르면 보이는 데이터가 달라질 수 있습니다.

### 1.4 현재 데이터베이스 확인하기

선택한 일반 데이터베이스에서 아래 질의를 실행합니다.

```cypher
CALL db.info() YIELD name
RETURN name AS currentDatabase;
```

`currentDatabase`가 **`neo4j`**이면 이 실습의 대상이 선택된 것입니다. `system`에서 실행해 오류가 나면 앞의 `:use neo4j`를 먼저 실행하세요.

이 데이터베이스에는 이미 제조 강의 데이터가 있을 수 있습니다. 3절에서 만드는 예제는 `CypherGuide` 라벨로 구분합니다. **이 라벨은 별도의 데이터베이스나 격리 공간을 만드는 기능이 아닙니다.** 같은 DB 안에 예제 데이터가 추가됩니다. 완전히 분리해 연습하려면 별도의 개인 실습용 Neo4j 인스턴스를 사용하세요.

공식 설명: [Neo4j 5 데이터베이스 관리](https://neo4j.com/docs/operations-manual/5/database-administration/) · [Browser 명령](https://neo4j.com/docs/browser/legacy/reference-commands/)

### 1.5 첫 질의 실행하기

```cypher
RETURN '안녕하세요, Cypher!' AS message;
```

`message` 열에 문자열이 보이면 질의를 실행할 준비가 된 것입니다. `AS`는 결과 열에 별명을 붙입니다. Browser에서는 실행 버튼이나 `Ctrl+Enter`로 실행합니다.

Cypher 키워드는 보통 대문자로 쓰고, 각 절은 줄을 나눕니다. 변수·라벨·관계 타입·속성 이름은 대소문자를 구분합니다. `//` 뒤는 한 줄 주석입니다.

### 1.6 CLI로 접속하기: Cypher Shell

Neo4j에는 MySQL의 `mysql` 클라이언트에 해당하는 **Cypher Shell**이 있습니다. Browser를 열지 않아도 터미널에서 로그인할 수 있습니다. CLI에서도 사용자명·비밀번호로 인증해야 합니다.

| 구분 | 역할 | 기본 포트 |
|---|---|---|
| Browser 웹 접속 | 브라우저에 Neo4j 화면 제공 | HTTP `7474` |
| Bolt 연결 | Cypher Shell·드라이버·Browser가 질의를 서버로 전달 | `7687` |

**7687은 셸 전용 포트가 아닙니다.** Browser도 웹 화면은 7474로 열지만, 질의 실행에는 Bolt 연결을 사용합니다.

이 저장소의 제조 실습 컨테이너를 사용한다면 **운영체제 터미널**에서 실행합니다.

```bash
docker exec -it mfg-neo4j cypher-shell -u neo4j -d neo4j
```

비밀번호는 안내가 나오면 입력합니다. 컨테이너에 도구가 포함되어 있어 호스트에 Cypher Shell을 별도 설치하지 않아도 됩니다. 접속 후에는 다음처럼 Cypher를 실행합니다.

```cypher
RETURN 'CLI 접속 성공' AS message;
```

종료하려면 아래 명령을 단독 실행합니다.

```text
:exit
```

Browser와 CLI는 같은 서버·데이터베이스를 지정하면 같은 데이터를 봅니다. CLI에서는 결과를 표·텍스트로 확인하며 그래프 그림은 표시하지 않습니다.

### 1.7 Docker 최초 실행과 관리 명령의 차이

Docker는 Neo4j를 실행하는 환경입니다. **빈 데이터 저장소로 Neo4j를 처음 시작할 때** Neo4j가 초기 일반 데이터베이스, 관리용 `system` 데이터베이스, 기본 사용자 `neo4j`를 준비합니다.

- `NEO4J_AUTH=neo4j/직접_정한_비밀번호`: 기본 사용자의 초기 비밀번호 설정입니다. 임의의 새 사용자 계정을 만드는 옵션은 아닙니다.
- `NEO4J_initial_dbms_default__database=practice`: 최초 생성할 일반 데이터베이스의 이름을 정합니다. 생략하면 기본 이름은 `neo4j`입니다.
- 데이터 볼륨을 재사용하면 기존 데이터와 계정이 유지됩니다. 환경 변수 변경만으로 기존 비밀번호나 DB 이름이 바뀌지는 않습니다.

즉 **최초 환경 준비**와 **실행 중 관리 명령으로 사용자·DB를 추가하는 작업**은 구분합니다. 사용자 추가는 Browser나 Cypher Shell 어느 쪽에서도 가능합니다.

다음은 **선택적인 사용자 생성 예시**입니다. 기본 실습에는 새 사용자가 필요하지 않습니다. 각 블록을 따로 실행하고, 비밀번호는 본인이 정한 값으로 바꿉니다.

```text
:use system
```

```cypher
CREATE USER learner
SET PASSWORD '직접_정한_새_비밀번호'
CHANGE REQUIRED;
```

```cypher
SHOW USERS;
```

새 사용자는 첫 로그인에서 비밀번호를 변경해야 합니다. Community Edition에서는 모든 사용자가 관리자 수준 권한을 가지므로, 사용자 생성이 읽기 전용 권한 분리를 의미하지 않습니다.

반면 현재 Community 환경에서는 `CREATE DATABASE`로 일반 데이터베이스를 추가할 수 없습니다. Enterprise에서는 권한이 있는 사용자가 관리 명령으로 추가할 수 있습니다. 학습을 위해 Enterprise로 바꿀 필요는 없습니다.

관리 예제를 마쳤다면 실습 DB로 돌아옵니다.

```text
:use neo4j
```

강의 DB와 완전히 분리하고 이름도 다르게 시작하려면 **[독립 Neo4j 설치·초기화 가이드](setup/neo4j-standalone.md)**를 따르세요. 이 경우 Browser와 CLI에서 선택할 DB 이름은 `practice`입니다.

공식 설명: [Cypher Shell](https://neo4j.com/docs/operations-manual/current/cypher-shell/) · [사용자 관리](https://neo4j.com/docs/operations-manual/current/authentication-authorization/manage-users/) · [초기 DB 이름 설정](https://neo4j.com/docs/operations-manual/current/configuration/configuration-settings/#config_initial.dbms.default_database)

## 2. 그래프와 패턴 읽기

| 구성 요소 | 의미 | 예시 |
|---|---|---|
| 노드(Node) | 사람·강좌 같은 개체 | `(p)` |
| 라벨(Label) | 노드의 분류. 한 노드에 여러 개 가능 | `:Person`, `:CypherGuide` |
| 관계(Relationship) | 두 노드 사이의 연결. 타입과 방향을 가짐 | `-[:ENROLLED_IN]->` |
| 속성(Property) | 노드·관계에 저장한 값 | `{name: '민수', age: 29}` |
| 변수 | 이번 질의에서 노드·관계 등을 가리키는 이름 | `p`, `r`, `c` |

```text
(p:Person:CypherGuide {id: 'p1', name: '민수'})
  -[r:ENROLLED_IN {since: 2025}]->
(c:Course:CypherGuide {id: 'c1', title: 'Neo4j 입문'})
```

“민수가 2025년부터 Neo4j 입문 강좌를 수강한다”라는 뜻입니다. `()`는 노드, `[]`는 관계, `{}`는 속성을 표현합니다. `p`는 DB에 저장된 이름이 아니라 질의 안에서 쓰는 변수입니다. `since`는 이 예제에서 정수입니다.

패턴을 글로 읽는 습관부터 들이면 좋습니다.

| 패턴 | 읽는 방법 |
|---|---|
| `(p:Person)` | Person 라벨을 가진 노드 |
| `(p:Person:CypherGuide)` | 두 라벨을 모두 가진 노드 |
| `(p {id: 'p1'})` | id가 p1인 노드 |
| `(p)-[r:KNOWS]->(q)` | p에서 q로 향하는 KNOWS 관계 |
| `(p)<-[:KNOWS]-(q)` | q에서 p로 향하는 KNOWS 관계 |
| `(p)-[:KNOWS]-(q)` | 조회할 때 방향을 구분하지 않는 KNOWS 관계 |

관계는 저장할 때 항상 방향을 가집니다. 방향 없는 패턴은 조회 시 양쪽 방향을 찾는 표현입니다.

## 3. 실습 데이터 준비

다음 **네 블록을 위에서 아래로 각각 실행**합니다. 식별자만 `MERGE`에 넣고 나머지는 `SET`으로 설정하므로, 같은 데이터를 다시 준비할 수 있습니다.

### 3.1 사람 3명

```cypher
UNWIND [
  {id: 'p1', name: '민수', age: 29, city: '서울'},
  {id: 'p2', name: '지영', age: 34, city: '부산'},
  {id: 'p3', name: '서연', age: 24, city: '서울'}
] AS row
MERGE (p:Person:CypherGuide {id: row.id})
SET p.name = row.name, p.age = row.age, p.city = row.city;
```

### 3.2 강좌 2개

```cypher
UNWIND [
  {id: 'c1', title: 'Neo4j 입문'},
  {id: 'c2', title: '온톨로지 기초'}
] AS row
MERGE (c:Course:CypherGuide {id: row.id})
SET c.title = row.title;
```

### 3.3 수강 관계 3개

```cypher
UNWIND [
  {personId: 'p1', courseId: 'c1', since: 2025},
  {personId: 'p2', courseId: 'c1', since: 2024},
  {personId: 'p2', courseId: 'c2', since: 2025}
] AS row
MATCH (p:Person:CypherGuide {id: row.personId})
MATCH (c:Course:CypherGuide {id: row.courseId})
MERGE (p)-[r:ENROLLED_IN]->(c)
SET r.since = row.since;
```

### 3.4 지인 관계 2개

```cypher
MATCH (a:Person:CypherGuide {id: 'p1'})
MATCH (b:Person:CypherGuide {id: 'p2'})
MATCH (c:Person:CypherGuide {id: 'p3'})
MERGE (a)-[:KNOWS]->(b)
MERGE (b)-[:KNOWS]->(c);
```

연결 구조는 다음과 같습니다. 서연은 아직 수강 강좌가 없습니다.

```text
민수 ──KNOWS──> 지영 ──KNOWS──> 서연
 │               ├──ENROLLED_IN──> Neo4j 입문
 └──ENROLLED_IN──> Neo4j 입문
                 └──ENROLLED_IN──> 온톨로지 기초
```

노드·관계 개수를 각각 확인합니다. 다른 강의 데이터가 있어도 예제 라벨만 셉니다.

```cypher
MATCH (n:CypherGuide)
RETURN count(n) AS nodeCount;
```

```cypher
MATCH (:CypherGuide)-[r]->(:CypherGuide)
RETURN count(r) AS relationshipCount;
```

초기 예상값은 **노드 5개, 관계 5개**입니다. 반복·동시 적재에서 식별자 중복까지 막으려면 13절의 고유성 제약 조건도 사용합니다.

## 4. MATCH와 RETURN: 찾고 보여주기

기본 틀은 `MATCH 패턴 → WHERE 조건 → RETURN 결과`입니다. `WHERE`는 필요할 때만 넣습니다.

```cypher
MATCH (p:Person:CypherGuide)
RETURN p;
```

노드 자체를 반환하면 Browser에서 그래프로 확인할 수 있습니다. 속성만 반환하면 표로 읽기 좋습니다.

```cypher
MATCH (p:Person:CypherGuide)
RETURN p.name AS name, p.age AS age, p.city AS city
ORDER BY p.id;
```

| name | age | city |
|---|---:|---|
| 민수 | 29 | 서울 |
| 지영 | 34 | 부산 |
| 서연 | 24 | 서울 |

특정 노드를 찾을 때는 패턴에 속성 조건을 넣을 수 있습니다.

```cypher
MATCH (p:Person:CypherGuide {id: 'p1'})
RETURN p.name AS name;
```

## 5. WHERE: 조건으로 거르기

```cypher
MATCH (p:Person:CypherGuide)
WHERE p.age >= 25 AND p.city = '서울'
RETURN p.name AS name, p.age AS age;
```

결과는 `민수 / 29`입니다.

| 표현 | 뜻 | 예시 |
|---|---|---|
| `=`, `<>` | 같음, 다름 | `p.city <> '부산'` |
| `>`, `>=`, `<`, `<=` | 크기 비교 | `p.age < 30` |
| `AND`, `OR`, `NOT` | 조건 조합 | `NOT (p.city = '부산')` |
| `IN` | 목록에 포함 | `p.city IN ['서울', '부산']` |
| `CONTAINS` | 문자열 일부 포함 | `p.name CONTAINS '영'` |
| `STARTS WITH`, `ENDS WITH` | 문자열 시작·끝 검사 | `p.name STARTS WITH '민'` |
| `IS NULL`, `IS NOT NULL` | 값 없음·있음 | `p.email IS NULL` |

문자열은 따옴표로 감싸고 숫자는 감싸지 않습니다. `29`와 `'29'`는 서로 다른 타입입니다. 문자열 비교는 대소문자를 구분합니다.

## 6. 정렬·개수 제한·중복 제거

나이 내림차순으로 정렬한 뒤 처음 두 명을 반환합니다. 동점일 때 순서를 정하도록 id도 넣습니다.

```cypher
MATCH (p:Person:CypherGuide)
RETURN p.name AS name, p.age AS age
ORDER BY age DESC, p.id ASC
LIMIT 2;
```

결과는 `지영 / 34`, `민수 / 29` 순서입니다. `ASC`는 오름차순이며 기본값입니다.

`SKIP`은 앞의 행을 건너뜁니다. 페이지 단위로 조회할 때는 정렬 조건을 함께 지정합니다.

```cypher
MATCH (p:Person:CypherGuide)
RETURN p.name AS name
ORDER BY p.id
SKIP 1
LIMIT 2;
```

`DISTINCT`는 **반환하는 값 조합**의 중복을 제거합니다.

```cypher
MATCH (p:Person:CypherGuide)
RETURN DISTINCT p.city AS city
ORDER BY city;
```

서울에 두 사람이 있어도 도시는 `부산`, `서울` 두 행만 나옵니다. `ORDER BY`가 없으면 결과 순서는 보장되지 않습니다.

## 7. 관계와 경로 탐색

### 7.1 누가 무엇을 수강하는가

```cypher
MATCH (p:Person:CypherGuide)-[r:ENROLLED_IN]->(c:Course:CypherGuide)
RETURN p.name AS person, c.title AS course, r.since AS since
ORDER BY p.id, c.id;
```

결과는 수강 관계마다 한 행씩, 총 3행입니다. 지영은 두 강좌를 수강하므로 두 번 등장합니다.

### 7.2 연결된 그래프 자체 보기

```cypher
MATCH path = (p:Person:CypherGuide)-[:ENROLLED_IN]->(c:Course:CypherGuide)
RETURN path;
```

`path`는 경로 전체를 담는 변수입니다. `RETURN p, r, c`처럼 노드와 관계를 따로 반환해도 됩니다. 이 경우 패턴에 `[r:ENROLLED_IN]`으로 관계 변수를 선언합니다.

### 7.3 1~2단계 지인 찾기

```cypher
MATCH path = (:Person:CypherGuide {id: 'p1'})-[:KNOWS*1..2]->(friend:Person:CypherGuide)
RETURN friend.name AS name, length(path) AS hops
ORDER BY hops, name;
```

지영은 1단계, 서연은 2단계입니다. `*1..2`는 관계를 최소 1번, 최대 2번 따라갑니다. 이 문서는 Cypher 5의 가변 길이 패턴을 사용합니다. 처음에는 상한 없는 `*` 대신 범위를 지정하세요. `LIMIT`만으로 탐색 비용 전체가 제한되는 것은 아닙니다.

## 8. OPTIONAL MATCH와 null

일반 `MATCH`는 패턴이 없는 행을 남기지 않습니다. 수강하지 않는 사람도 보려면 `OPTIONAL MATCH`를 사용합니다.

```cypher
MATCH (p:Person:CypherGuide)
OPTIONAL MATCH (p)-[:ENROLLED_IN]->(c:Course:CypherGuide)
RETURN p.name AS person, coalesce(c.title, '미수강') AS course
ORDER BY p.id, course;
```

민수 1행, 지영 2행, 서연의 `미수강` 1행으로 총 4행입니다. `coalesce()`는 인수 중 처음으로 `null`이 아닌 값을 돌려줍니다.

`null`은 값이 없거나 알 수 없다는 뜻입니다. 속성이 없을 때도 속성 접근 결과가 `null`입니다. `p.email = null` 대신 `p.email IS NULL`로 검사합니다. `OPTIONAL MATCH`에 붙인 `WHERE`는 선택적 패턴의 조건입니다. 이후 `WITH ... WHERE`로 `null` 행을 거르면 해당 사람도 결과에서 빠질 수 있습니다.

공식 설명: [OPTIONAL MATCH](https://neo4j.com/docs/cypher-manual/5/clauses/optional-match/) · [null 처리](https://neo4j.com/docs/cypher-manual/5/values-and-types/working-with-null/)

## 9. 집계와 WITH

### 9.1 도시별 인원수와 평균 나이

```cypher
MATCH (p:Person:CypherGuide)
RETURN p.city AS city, count(*) AS people, avg(p.age) AS averageAge
ORDER BY city;
```

집계하지 않은 `city`가 그룹 기준이 됩니다. 부산은 1명·34.0세, 서울은 2명·26.5세입니다.

### 9.2 수강하지 않는 사람까지 포함해 세기

```cypher
MATCH (p:Person:CypherGuide)
OPTIONAL MATCH (p)-[:ENROLLED_IN]->(c:Course:CypherGuide)
RETURN p.name AS person, count(c) AS courseCount, collect(c.title) AS courses
ORDER BY person;
```

`count(*)`는 행 수, `count(c)`는 c가 `null`이 아닌 행 수입니다. 서연의 `count(c)`는 0이며 `collect(c.title)`은 빈 목록 `[]`입니다. `collect()`는 값을 목록으로 모으고 `null`은 제외합니다. 목록 내부 순서는 별도로 정렬하지 않으면 보장되지 않습니다.

### 9.3 WITH로 중간 결과 전달하고 거르기

```cypher
MATCH (p:Person:CypherGuide)-[:ENROLLED_IN]->(c:Course:CypherGuide)
WITH p, count(c) AS courseCount
WHERE courseCount >= 2
RETURN p.name AS person, courseCount;
```

결과는 `지영 / 2`입니다. `WITH`는 중간 결과를 다음 절로 넘깁니다. 위 질의에서 다음 단계에 남는 변수는 `p`, `courseCount`입니다. `c`도 필요하다면 `WITH`에 명시해야 합니다.

공식 설명: [WITH](https://neo4j.com/docs/cypher-manual/5/clauses/with/) · [집계 함수](https://neo4j.com/docs/cypher-manual/5/functions/aggregating/)

## 10. 파라미터와 UNWIND

### 10.1 파라미터로 값을 전달하기

Neo4j Browser 입력창에서 아래 명령을 **각각 따로** 실행합니다. `:param`은 Browser 명령이며 Cypher 문법 자체는 아닙니다.

```text
:param minAge => 25
```

```cypher
MATCH (p:Person:CypherGuide)
WHERE p.age >= $minAge
RETURN p.name AS name, p.age AS age
ORDER BY age DESC;
```

`$minAge`는 전달된 값을 참조합니다. Python·JavaScript 등에서는 드라이버의 파라미터 인수로 값을 넘깁니다. 사용자 입력을 문자열로 이어 붙여 질의를 만드는 대신 파라미터를 사용합니다.

### 10.2 UNWIND로 목록을 행으로 펼치기

```cypher
UNWIND ['서울', '부산'] AS city
MATCH (p:Person:CypherGuide {city: city})
RETURN city, p.name AS name
ORDER BY city, name;
```

`UNWIND`는 목록의 각 원소를 행으로 바꿉니다. 3절에서는 사람 목록과 수강 목록을 같은 방식으로 처리했습니다. `UNWIND`만으로 행 순서는 보장되지 않습니다.

공식 설명: [파라미터](https://neo4j.com/docs/cypher-manual/5/syntax/parameters/) · [UNWIND](https://neo4j.com/docs/cypher-manual/5/clauses/unwind/)

## 11. CREATE·MERGE·SET·REMOVE

이 절부터 데이터를 변경합니다. 아래 예제는 새 사람 `p4`로 진행합니다.

### 11.1 CREATE: 새 노드 만들기

```cypher
CREATE (p:Person:CypherGuide {id: 'p4', name: '도윤', age: 31})
RETURN p;
```

`CREATE`는 매 실행마다 새로 만듭니다. 위 블록은 한 번만 실행하세요. 같은 id의 고유성 제약 조건이 있다면 두 번째 실행은 오류가 됩니다.

### 11.2 MERGE: 패턴이 있으면 사용하고 없으면 만들기

```cypher
MERGE (p:Person:CypherGuide {id: 'p4'})
ON CREATE SET p.name = '도윤', p.age = 31
ON MATCH SET p.lastSeen = date()
RETURN p;
```

앞의 `CREATE`를 실행했다면 기존 노드에 `lastSeen`이 설정됩니다. `CREATE`를 건너뛰었다면 노드를 만들고 이름·나이를 설정합니다. `ON CREATE`는 새로 만들었을 때, `ON MATCH`는 기존 패턴을 찾았을 때 실행합니다.

`MERGE`는 지정한 **전체 패턴**을 기준으로 찾습니다. `MERGE (p:Person {id: 'p4', age: 32})`처럼 변하는 값까지 넣으면 기존 age가 31인 노드와 일치하지 않습니다. 안정적인 id로 찾고 나머지는 `SET`으로 갱신하세요. 동시 쓰기에서 노드 식별자 고유성을 보장하려면 제약 조건을 함께 사용합니다.

공식 설명: [CREATE](https://neo4j.com/docs/cypher-manual/5/clauses/create/) · [MERGE](https://neo4j.com/docs/cypher-manual/5/clauses/merge/)

### 11.3 기존 노드 사이에 관계 만들기

```cypher
MATCH (p:Person:CypherGuide {id: 'p4'})
MATCH (c:Course:CypherGuide {id: 'c2'})
MERGE (p)-[r:ENROLLED_IN]->(c)
SET r.since = 2026
RETURN p, r, c;
```

끝점 노드를 먼저 찾은 뒤 관계를 만듭니다. 두 `MATCH` 중 하나라도 노드를 찾지 못하면 뒤의 `MERGE`는 실행할 행이 없어 관계도 생기지 않습니다.

### 11.4 SET: 속성과 라벨 변경

```cypher
MATCH (p:Person:CypherGuide {id: 'p4'})
SET p.age = 32, p.city = '대전', p:CypherGuideLearner
RETURN p;
```

여러 속성을 맵으로 갱신할 수도 있습니다.

```cypher
MATCH (p:Person:CypherGuide {id: 'p4'})
SET p += {city: '서울', email: 'doyun@example.com'}
RETURN p;
```

`+=`는 지정한 속성을 추가·갱신하고 나머지를 유지합니다. `SET p = {...}`는 **기존 속성 전체를 교체**하므로 id도 지울 수 있습니다.

### 11.5 REMOVE: 속성과 라벨 제거

```cypher
MATCH (p:Person:CypherGuide {id: 'p4'})
REMOVE p.email, p:CypherGuideLearner
RETURN p;
```

`REMOVE`는 노드 자체를 지우지 않습니다. `SET p.email = null`도 email 속성을 제거합니다.

## 12. DELETE와 실습 데이터 정리

### 12.1 관계만 삭제

먼저 대상이 맞는지 조회한 뒤 삭제합니다.

```cypher
MATCH (p:Person:CypherGuide {id: 'p4'})-[r:ENROLLED_IN]->(c:Course:CypherGuide {id: 'c2'})
RETURN p.name, type(r), c.title;
```

```cypher
MATCH (:Person:CypherGuide {id: 'p4'})-[r:ENROLLED_IN]->(:Course:CypherGuide {id: 'c2'})
DELETE r;
```

### 12.2 관계 없는 노드 삭제

앞에서 수강 관계를 삭제했으므로 도윤 노드를 삭제할 수 있습니다.

```cypher
MATCH (p:Person:CypherGuide {id: 'p4'})
DELETE p;
```

관계가 남아 있는 노드를 `DELETE`로 지우면 오류가 납니다. 연결 관계도 함께 지우려면 `DETACH DELETE`를 사용합니다.

### 12.3 이 가이드 데이터 전체 정리 — 실습을 마친 뒤에만 실행

```cypher
MATCH (n:CypherGuide)
RETURN n;
```

대상을 확인한 뒤 아래를 실행합니다. **CypherGuide 노드와 그 노드에 붙은 모든 관계가 삭제됩니다.** 다른 라벨의 노드에 연결한 관계도 함께 삭제되므로 실제 업무 데이터와 연결하지 마세요.

```cypher
MATCH (n:CypherGuide)
DETACH DELETE n;
```

다시 연습하려면 3절의 네 블록을 실행합니다. 라벨 조건을 빼고 전체 DB를 삭제하지 마세요.

## 13. 제약 조건과 인덱스

### 13.1 id 중복 방지

```cypher
CREATE CONSTRAINT cypher_guide_id_unique IF NOT EXISTS
FOR (n:CypherGuide) REQUIRE n.id IS UNIQUE;
```

`CypherGuide` 라벨 안에서 id 값이 중복되지 않게 합니다. 이미 중복 데이터가 있으면 생성이 실패합니다. 고유성 제약 조건은 id의 **존재 자체**를 강제하지 않으며, 해당 속성 조회를 지원하는 인덱스도 함께 만듭니다.

### 13.2 자주 찾는 속성에 인덱스 만들기

```cypher
CREATE INDEX cypher_guide_city IF NOT EXISTS
FOR (n:CypherGuide) ON (n.city);
```

```cypher
SHOW INDEXES;
```

인덱스는 조건 조회의 탐색 비용을 줄일 수 있지만, 작은 데이터에서는 성능 차이가 거의 없을 수 있습니다. 인덱스가 있다고 결과 정렬이 자동으로 보장되지는 않습니다.

질의 앞에 `EXPLAIN`을 붙이면 실행하지 않고 계획을 확인합니다.

```cypher
EXPLAIN
MATCH (p:Person:CypherGuide {city: '서울'})
RETURN p;
```

`PROFILE`은 실제로 질의를 실행하며 처리 행 수 등도 보여줍니다. 쓰기 질의에 붙이면 데이터도 변경됩니다.

12절에서 노드를 삭제해도 제약 조건·인덱스는 남습니다. 이 가이드에서 만든 스키마도 정리하려면 다음을 각각 실행합니다.

```cypher
DROP INDEX cypher_guide_city IF EXISTS;
```

```cypher
DROP CONSTRAINT cypher_guide_id_unique IF EXISTS;
```

공식 설명: [제약 조건](https://neo4j.com/docs/cypher-manual/5/constraints/managing-constraints/) · [검색 인덱스](https://neo4j.com/docs/cypher-manual/5/indexes/search-performance-indexes/managing-indexes/)

## 14. 자주 하는 실수

| 증상 | 확인할 내용 |
|---|---|
| 결과가 0행 | 3절 데이터 적재 여부, 현재 DB, 라벨·속성·값·관계 방향 확인 |
| `Variable ... not defined` | 해당 변수를 패턴에서 선언했는지, `WITH`에서 전달했는지 확인 |
| 같은 사람이 여러 행에 나옴 | 관계·경로마다 한 행일 수 있음. 필요한 결과에 따라 `DISTINCT`나 집계 사용 |
| 연결 관계 수보다 결과가 많음 | 연결 없는 `(a), (b)` 패턴은 두 결과의 모든 조합을 만들 수 있음 |
| 속성이 없는 노드가 필터에서 빠짐 | `null` 비교는 true가 아님. `IS NULL`로 별도 처리 |
| `MERGE` 후 중복 노드가 생김 | 변하는 속성을 매칭 패턴에 넣었는지, id 고유성 제약 조건이 있는지 확인 |
| 노드를 삭제할 수 없음 | 연결 관계를 먼저 삭제하거나 범위를 확인한 뒤 `DETACH DELETE` 사용 |
| 파라미터 오류 | Browser에서 `:param`을 따로 실행했는지, `$minAge` 이름이 같은지 확인 |

전체 그래프를 무제한 조회하기보다 **라벨·id·관계 타입·깊이**로 범위를 줄입니다. 강의 DB를 처음 살펴볼 때도 아래처럼 제한합니다.

```cypher
MATCH (n)
RETURN labels(n) AS labels, count(*) AS nodes
ORDER BY nodes DESC
LIMIT 20;
```

이 질의는 읽기 전용이지만 노드 전체를 집계하므로 큰 DB에서는 실행 비용을 고려해야 합니다.

## 15. 연습 문제와 정답

3절 초기 데이터로 풀어보세요. 12절에서 정리했다면 다시 적재합니다.

1. 서울에 사는 사람의 이름을 나이 오름차순으로 조회하세요.
2. Neo4j 입문 강좌를 수강하는 사람의 이름을 조회하세요.
3. 사람별 수강 강좌 수를 구하되, 미수강자도 포함하세요.
4. 민수에서 시작해 KNOWS 방향으로 정확히 2단계 떨어진 사람을 찾으세요.

<details>
<summary>정답 펼치기</summary>

**1번 — 서연(24), 민수(29)**

```cypher
MATCH (p:Person:CypherGuide {city: '서울'})
RETURN p.name AS name, p.age AS age
ORDER BY age, p.id;
```

**2번 — 민수, 지영**

```cypher
MATCH (p:Person:CypherGuide)-[:ENROLLED_IN]->(:Course:CypherGuide {id: 'c1'})
RETURN p.name AS name
ORDER BY name;
```

**3번 — 민수 1개, 서연 0개, 지영 2개**

```cypher
MATCH (p:Person:CypherGuide)
OPTIONAL MATCH (p)-[:ENROLLED_IN]->(c:Course:CypherGuide)
RETURN p.name AS name, count(c) AS courseCount
ORDER BY name;
```

**4번 — 서연**

```cypher
MATCH (:Person:CypherGuide {id: 'p1'})-[:KNOWS*2]->(p:Person:CypherGuide)
RETURN DISTINCT p.name AS name;
```

</details>

## 16. 문법 요약과 다음 단계

| 하고 싶은 일 | 사용할 문법 |
|---|---|
| 패턴 찾기 | `MATCH (n:Label)` |
| 결과 반환 | `RETURN n.property AS name` |
| 조건 지정 | `WHERE n.property = $value` |
| 정렬·페이지 조회 | `ORDER BY ... SKIP ... LIMIT ...` |
| 중복 제거 | `RETURN DISTINCT ...` |
| 관계 조회 | `(a)-[r:TYPE]->(b)` |
| 여러 단계 조회 | `(a)-[:TYPE*1..3]->(b)` |
| 연결이 없어도 원래 행 유지 | `OPTIONAL MATCH` |
| 집계 | `count()`, `sum()`, `avg()`, `min()`, `max()`, `collect()` |
| 중간 결과 전달 | `WITH` |
| 목록을 행으로 펼치기 | `UNWIND ... AS ...` |
| 새로 생성 | `CREATE` |
| 패턴이 있으면 사용·없으면 생성 | `MERGE` |
| 속성·라벨 변경 | `SET`, `REMOVE` |
| 관계·노드 삭제 | `DELETE`, `DETACH DELETE` |

이제 [사용처 조회 예제](../examples/part01/ch03/ch03_where_used.cypher)를 열고 **어느 노드에서 시작하는지 → 어떤 관계를 몇 단계 따라가는지 → 어떤 값을 반환하는지** 순서로 읽어보세요. 이후 [Part 2 Ch4 · 적재와 경로 조회](part02/ch04/README.md)에서 제조 그래프에 적용할 수 있습니다.

추가 학습 자료:

- [Neo4j 공식 Cypher 시작 튜토리얼](https://neo4j.com/docs/getting-started/cypher/intro-tutorial/)
- [Cypher 5 절별 문법](https://neo4j.com/docs/cypher-manual/5/clauses/)
- [Cypher 5 치트시트](https://neo4j.com/docs/cypher-manual/5/cheat-sheet/)
- [Cypher 5 패턴 문법](https://neo4j.com/docs/cypher-manual/5/patterns/)

최신 매뉴얼에는 Cypher 25 전용 기능도 포함되므로, 이 저장소의 Neo4j 5.26에서는 위의 `/5/` 문서와 예제를 기준으로 학습하세요.
