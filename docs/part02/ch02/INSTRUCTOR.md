# Ch2 강사용 수정·확인 안내

수강생 개인 작업본의 `foundation/normalize.py`만 수정합니다. 입력 fixture, 제공 processed CSV, 실행 중인 DB는 수정하지 않습니다. 배포 원본과 개인 수정본을 구분하고, 되돌릴 때는 해당 파일의 diff를 먼저 확인합니다.

## 바이브코딩 요청 예

> extract_pack_size에서 `Pack of N` 표기를 추가해 주세요. 현재 `N Pack`, `N-pack`, `Npack` 표기도 유지해야 합니다. long_name을 먼저 읽고 short_name으로 보완하는 순서, (정수 팩 크기, 근거 문자열) 반환 형식, 표기가 없을 때 (1, "none")을 유지하세요. 정규식과 캡처 그룹을 읽는 부분을 함께 확인해 주세요. 과제 입력과 기대값은 바꾸지 마세요.

## 검토할 변경

현재 함수는 `match.group(1)`을 사용합니다. 대안 패턴에 캡처 그룹을 추가했다면 어떤 그룹에서 숫자를 읽을지도 수정해야 합니다. 새 표기만 통과하고 기존 표기가 실패하지 않는지 확인합니다.

## 확인 순서

1. 변경 전 `uv run python scripts/exercise.py ch2_2_pack` 실행: Pack of 4 실패, 25-pack 통과.
2. 코드 수정 후 같은 명령: Pack of 4는 팩 크기 4·차량당 4개, 25-pack은 팩 크기 25·차량당 100개.
3. `uv run pytest -q tests/test_calc.py -k "pack_size or identifiers or half_pack"` 실행.
4. 일반 부품명의 숫자 `25-2`를 포장 수량으로 잘못 읽지 않는지 확인.
5. 코드 수정으로 기존 DB가 갱신되지 않았음을 설명한 뒤 제공 조회문으로 원본·가공 값 대조.

build_dataset.py는 원본 전체와 이력·이슈 자료를 읽는 갱신용 스크립트입니다. 이 강의의 필수 실행 경로에 넣지 않습니다. 전체 DB 초기화도 실행하지 않습니다.
