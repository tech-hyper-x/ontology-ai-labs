# 85장 · 모터 교체 이력의 작성과 대조

Part 2 / Ch3 · [전체 실습 목차](../../hands-on/README.md)

## 시작 전 확인

- 장표와 같은 Part·챕터인지 먼저 확인합니다.

- Neo4j 코드는 Browser 입력창에서, bash 명령은 터미널에서 실행합니다. YAML·JSON·Python 파일 링크는 원문을 읽거나 수정할 대상을 뜻합니다.

- 터미널 명령의 기준 위치는 저장소의 `labs/mfg-bom-agent`입니다. 명령이 별도 위치를 지정하면 그 위치를 우선합니다.

- 초기화·적재·색인 명령은 기존 데이터에 영향을 줄 수 있습니다. 전용 실습 환경에서 해당 챕터 안내에 따라 실행하고, 조회만 하려면 다시 초기화하지 않습니다.

- [공통 실행 안내](../../ch03-run-guide.md)에 따라 서비스와 데이터를 준비합니다.

## 1. 변경 기록표 작성

[빈 작성표](worksheets/change-record.csv)를 복사합니다. A2~C2의 두 개정판과 조립품을 확인하고, D2·E2에 이전 모터 `5202-2402-0027`과 새 모터 `5203-2402-0027`을 적습니다. F2·G2 수량은 각각 `1`, H2 배수는 `6`입니다.

I2·J2에는 81장에서 확인한 `d092d83`의 시작일 `2023-07-18`과 종료일 `2023-07-26`을 넣습니다. K2에는 `reference/change.diff 및 plm_revision.csv`를 적고, L2의 `derived`를 확인합니다.

## 2. 터미널에서 예제 실행

[변경 계산 예제](../../../examples/part02/ch03/ch03_change.py)를 확인하고, 터미널의 `labs/mfg-bom-agent`에서 실행합니다.

```bash
uv run python ../../examples/part02/ch03/ch03_change.py
```

## 3. 결과와 작성표 대조

`changes`의 `removed`와 `added`를 작성한 두 품번과 대조합니다. `supersedes`는 새 모터에서 이전 모터를 가리킵니다. `intervals`의 `d092d83` 시작일과 종료일도 확인한 뒤 [완성 예시](worksheets/change-record-completed.csv)와 비교합니다.

`intervals`의 `is_latest`는 예제에 넣은 세 판 중 마지막 판을 표시합니다. 실제 개정판 구간은 [81장 Neo4j 조회](slide-073.md)에서 확인합니다. 제공 데이터에서 `886bb13`의 실제 종료일은 `2023-10-04`입니다.
