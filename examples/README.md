# 커리큘럼별 실행 예제

파일은 `part01`(공통 흐름), `part02`(제조), `part03`(바이오) 아래 챕터별로 찾습니다.
Python 명령의 실행 위치는 예제 파일 폴더가 아니라 해당 `labs` 프로젝트 루트입니다.

|Part|실습 범위|예제|
|---|---|---|
|[Part 1](part01/)|Ch3 공통 환경·MCP·문서 검색|사용처 Cypher, MCP 호출|
|[Part 2](part02/)|Ch2~Ch8 제조 실습|매핑·변경·검증·검색·계산·에이전트·평가|
|[Part 3](part03/)|현재 Ch1~Ch3 바이오 조회·설계|후보·식별자·근거·검색 비교·작성표|

Part1 Ch1~Ch2와 Part2 Ch1은 개념·원본 자료 확인 중심이며 별도 실행 예제가 없습니다. 제조 원본 자료와 작성표는 [docs/part02](../docs/part02/)에서 확인합니다.

```text
examples/
  part01/ch03/          공통 환경 확인·MCP 호출
  part02/ch02/          매핑
  part02/ch03/          변경 모델·검증
  part02/ch04/          적재 결과 대조
  part02/ch05/          문서·검색
  part02/ch06/          수량·원가·MCP
  part02/ch07/          계획·호출 분기·답변 검증
  part02/ch08/          평가·실제 오류 수정
  part03/ch01/          후보·별칭·근거 경로·검색 비교
  part03/ch02/          스냅샷·식별자
  part03/ch03/          근거 관계·유형·검색 관찰
```

## 실행 예

제조 프로젝트 `labs/mfg-bom-agent`에서:

```bash
uv run python ../../examples/part01/ch03/ch03_call.py search_docs --mode hybrid
uv run python ../../examples/part02/ch02/ch02_mapping.py
uv run python ../../examples/part02/ch06/ch06_purchase.py --check
```

`*_solution.py`는 작성 과제의 해설입니다. 미작성 과제의 `NotImplementedError`는 의도된 시작 상태입니다.

바이오 Cypher는 해당 실습의 고정 데이터·검색 색인이 준비된 Neo4j에서 실행합니다. 조회문만으로 DB나 벡터 색인을 생성하지 않습니다. 현재 공개 저장소에는 바이오 전체 실행 환경·고정 데이터가 아직 포함되어 있지 않으므로, 강의에서 제공한 바이오 프로젝트로 준비한 DB를 사용합니다.
