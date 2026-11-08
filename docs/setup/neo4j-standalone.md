# 독립 Neo4j 설치·초기화 가이드

강의용 제조·바이오 DB와 분리해 Cypher 기초를 연습합니다. Docker가 설치·실행 중이어야 합니다. 설치가 처음이라면 [Docker 설치 안내](README.md#2-docker와-기본-도구-설치)를 먼저 따릅니다. 아래 파일은 저장소 바깥의 새 빈 폴더에 만드세요.

## 1. 새 연습 환경 파일 만들기

`neo4j-practice` 같은 새 폴더에 `compose.yaml`을 만들고 아래 내용을 저장합니다.

```yaml
name: cypher-practice
services:
  neo4j:
    image: neo4j:5.26-community
    ports:
      - "127.0.0.1:7476:7474"
      - "127.0.0.1:7689:7687"
    environment:
      NEO4J_AUTH: "neo4j/${NEO4J_PASSWORD:?Set NEO4J_PASSWORD in .env}"
      NEO4J_initial_dbms_default__database: practice
      NEO4J_server_bolt_advertised__address: localhost:7689
    volumes:
      - practice-data:/data
volumes:
  practice-data:
```

같은 폴더에 `.env` 파일을 만들고 본인의 초기 비밀번호를 설정합니다. 아래 값은 예시 자리이며, 직접 정한 8자 이상의 영문·숫자 비밀번호로 바꾸세요. `.env`는 Git에 올리지 않습니다.

```dotenv
NEO4J_PASSWORD=REPLACE_WITH_YOUR_PASSWORD
```

DB 이름은 **practice**, 초기 사용자 이름은 **neo4j**입니다. 두 이름은 별개입니다. Community에서는 초기 사용자 이름을 `NEO4J_AUTH`로 임의 변경할 수 없습니다. 새 사용자가 필요하면 초기 로그인 후 생성합니다.

## 2. 서버 시작과 초기화 확인

이 폴더의 터미널에서 실행합니다.

```bash
docker compose up -d
```

```bash
docker compose logs --tail=50 neo4j
```

시작 완료를 확인합니다. 최초 시작 때 이미지 다운로드와 DB 초기화에 시간이 걸릴 수 있습니다. 호스트 포트가 이미 사용 중이면 충돌이 발생하므로 포트 매핑과 advertised 주소를 함께 조정합니다.

처음 쓰는 빈 볼륨이면 Neo4j가 **practice DB, system DB, 기본 neo4j 사용자**를 초기화합니다. 이 과정은 Docker가 DB 명령을 실행하는 것이 아니라, 컨테이너 안의 Neo4j가 초기 설정을 읽는 과정입니다.

## 3. Browser로 접속

[독립 연습용 Browser](http://localhost:7476/browser/)를 엽니다.

- 연결 주소: `bolt://localhost:7689`
- 사용자: `neo4j`
- 비밀번호: `.env`에 직접 설정한 값

입력창에서 아래 블록을 각각 따로 실행합니다.

```cypher
SHOW DATABASES;
```

```text
:use practice
```

```cypher
CALL db.info() YIELD name
RETURN name AS currentDatabase;
```

결과가 `practice`인지 확인합니다. 이 서버에는 일반 DB `practice`와 관리용 DB `system`이 있으며, 일반 DB 이름이 `neo4j`일 필요는 없습니다.

## 4. CLI로 같은 DB에 접속

같은 폴더의 터미널에서 실행한 후 비밀번호를 입력합니다.

```bash
docker compose exec neo4j cypher-shell -u neo4j -d practice
```

```cypher
RETURN '연습 DB 접속 성공' AS message;
```

```text
:exit
```

## 5. Cypher 기초 실습으로 이동

[기본 Cypher 가이드](../neo4j-cypher-basics.md#2-그래프와-패턴-읽기)의 2절부터 진행하세요. 이후 가이드의 `:use neo4j`는 **`:use practice`**로 바꿔 실행합니다. 노드·관계 예제 자체는 그대로 사용합니다. CLI는 위의 Compose 명령을 사용합니다.

사용자 생성 방법은 [기본 가이드의 관리 명령 설명](../neo4j-cypher-basics.md#17-docker-최초-실행과-관리-명령의-차이)을 참고합니다. DB 이름이 달라도 사용자 권한의 Community 제한은 같습니다.

## 6. 종료와 재시작

```bash
docker compose stop
```

```bash
docker compose start
```

데이터는 전용 볼륨에 보존됩니다. 기존 볼륨을 사용하는 동안 `.env`의 초기 비밀번호나 초기 DB 이름만 바꿔도 기존 계정·DB가 변경되지는 않습니다.

공식 문서: [Docker 설치](https://neo4j.com/docs/operations-manual/current/docker/introduction/) · [Docker 설정 변수](https://neo4j.com/docs/operations-manual/current/docker/ref-settings/)
