# Part 3 Ch2 · 실습 안내

이 챕터의 조회문은 강의에서 제공한 바이오 프로젝트·DB·저장 벡터가 준비된 상태에서 실행합니다. 공개 저장소에는 바이오 전체 실행 환경이 포함되어 있지 않습니다.

실행 위치는 제공 프로젝트의 `labs/bio-target-agent`, Neo4j Browser는 `http://localhost:7475`, Bolt는 `localhost:7688`입니다. `:params`와 조회문은 따로 실행합니다.

## 장표 번호별 실습

- [192장 · 스냅샷과 식별자 정리](slide-192.md)
- [206장 · HER1 누락의 실패 재현](slide-206.md)
- [207장 · 작업본 수정과 심볼 대응 재검사](slide-207.md)

## 작성표와 조회문

- [스냅샷 기준표](../../../examples/part03/ch02/snapshot_manifest.csv)
- [식별자 매핑 작성표](../../../examples/part03/ch02/identifier_mapping.csv)
- [동일성·과제·미연결·별칭 검색·질환 조회](../../../examples/part03/ch02/)

과제의 FAIL은 시작본의 의도된 실패입니다. 작업본 검사 통과와 기존 DB 연결 확인을 나누어 기록합니다.

## 200장 · 공식 MCP 선택 시연

[공식 조회 예제](../../../examples/part03/ch02/S200_01_official_mcp.py)를 제공 프로젝트의 `labs/bio-target-agent`에서 실행합니다.

```bash
uv run python ../../examples/part03/ch02/S200_01_official_mcp.py list
uv run python ../../examples/part03/ch02/S200_01_official_mcp.py query
```

목록의 입력 형식을 먼저 확인합니다. 질환의 연관 상위 50개 중 EGFR과 응답 릴리스를 읽으며, 로컬 스냅샷은 수정하지 않습니다. 공식 서버 인터페이스가 달라졌거나 연결되지 않으면 고정 자료로 돌아갑니다.
