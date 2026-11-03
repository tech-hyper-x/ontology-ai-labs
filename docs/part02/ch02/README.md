# Part 2 · Ch2 — 부품 데이터 연결과 정리

두 강의, 각 15분. Ch1의 CQ·자료 목록을 받아 매핑 명세, 식별자 대응표, 수량·단위 규칙으로 정리합니다. 방법론의 **데이터 매핑** 단계에 해당하며, 다음 Ch3 모델링에서 초안을 다시 검토합니다.

실행 위치는 내려받은 저장소의 `labs/mfg-bom-agent`입니다. Ch3에서 준비한 패키지·Neo4j·데이터를 사용합니다. 이번 장에서는 DB 초기화나 전체 데이터 재생성을 실행하지 않습니다.

## 1강 · 부품·구매 데이터 매핑

|순서|화면|수강생이 할 일|완료 기준|
|---|---|---|---|
|1|Ch1 CQ·자료 목록 → [매핑표](worksheets/mapping-spec.csv)|질문에 필요한 열을 선택|원본 필드와 필요한 값 구분|
|2|[원본 부품표](../ch01/reference/parts_list/parts_list.csv)|휠 3616-0014-0144 행·머리글 읽기|`cost pp `의 뒤쪽 공백까지 확인|
|3|[normalize.py](../../../labs/mfg-bom-agent/src/mfg_bom_agent/foundation/normalize.py)|PARTS_LIST_COLUMNS·map_parts_row·supplier_from_url 읽기|열 이름 변환과 공급사 식별 역할 설명|
|4|[부품 마스터](../../../labs/mfg-bom-agent/data/processed/plm_item_master.csv) · [BOM](../../../labs/mfg-bom-agent/data/processed/plm_ebom_line.csv) · [구매 조건](../../../labs/mfg-bom-agent/data/processed/erp_supplier_item.csv)|같은 부품 ID로 대조|부품·투입 내역·구매 조건의 역할 구분|
|5|[한 행 실행 예제](../../../examples/ch02_mapping.py)|아래 명령 실행 + 매핑표 네 행 작성|원본 값·공통 필드·식별자가 연결됨|
|6|[Neo4j Browser](http://localhost:7474)|[식별자 조회문](queries/01-identifiers.cypher) 실행|CSV와 part_id·supplier_sku 대조|

```bash
uv run python ../../examples/ch02_mapping.py
```

예제는 현재 작업본의 매핑 함수를 호출합니다. 파일·그래프를 변경하지 않습니다. `raw → common → identity → offers`를 읽습니다. 공개 SKU와 내부 ID, 가상 공급사 품번을 같은 문자열로 만들지 말고 대응표로 연결합니다.

Crosswalk는 **같은 부품의 서로 다른 식별자를 기록한 대응표**입니다. [crosswalk.csv](../../../labs/mfg-bom-agent/data/processed/crosswalk.csv)에서 원천 SKU, 내부 part_id, 공급사 품번을 대조합니다. 빈 MPN은 실제 제조사 품번을 확인하지 못한 상태이며 0으로 채우지 않습니다.

매핑표의 `unit_price`는 최종 숫자 필드입니다. `map_parts_row()`는 먼저 가격 원문을 `unit_price_raw`로 옮기며, 숫자 변환은 다음 강의의 `parse_price()`에서 설명합니다. 도메인에서 공급사를 식별했다는 사실만으로 상품의 동일성이 검증된 것은 아닙니다.

## 2강 · 단위와 식별자 정규화

1. [단위 규칙 표](worksheets/unit-contract.csv)를 엽니다. `raw_qty`는 원천 상품/팩 수, `pack_size`는 상품당 낱개 수, `qty_each=raw_qty×pack_size`는 조립품당 낱개 수, `multiplier`는 조립품 배수입니다.
2. 스페이서 1522-0010-0060의 최신 판 예는 `0.5 × 4 = 2개`, 차량 한 대는 `2 × 2 = 4개`입니다. 팩당 가격을 낱개 가격과 혼용하지 않습니다.
3. normalize.py의 `extract_pack_size`, `make_part_id`, `parse_price`를 읽습니다. `pack_basis=none`은 포장 표기가 없어 1로 읽은 근거 표시입니다. 원천 값을 확인했다는 의미로 바꾸지 않습니다. 가격 원문은 Decimal로 읽고 빈 가격은 None으로 남깁니다.
4. [과제 입력](../../../labs/mfg-bom-agent/data/exercises/exercises.yaml)의 `ch2_2_pack`을 실행합니다.

```bash
uv run python scripts/exercise.py ch2_2_pack
```

처음에는 `Pack of 4`를 팩 크기 1로 읽어 **차량당 1개**가 나오는 의도된 실패가 있습니다. `25-pack`은 이미 통과합니다. 개인 작업본의 `_PACK_PATTERN`과 `extract_pack_size`를 수정한 뒤 같은 명령을 실행합니다. 기대 결과는 각각 **4개 / 100개**이며 입력 fixture는 바꾸지 않습니다.

```bash
uv run pytest -q tests/test_calc.py -k "pack_size or identifiers or half_pack"
```

[AI 수정 요청과 강사용 검토](INSTRUCTOR.md)를 참고합니다. 결과가 달라졌을 때 이전 표기, 포장 근거, 반환 타입이 유지되는지 확인합니다.

5. [02-units.cypher](queries/02-units.cypher)를 Neo4j Browser에서 실행합니다. 같은 revision에서 `raw_qty_text / pack_size / qty_each_text / multiplier / each_per_product / source_ref`를 CSV와 대조합니다.
6. [03-normalization-check.cypher](queries/03-normalization-check.cypher)로 수량 필드 누락·환산 불일치·포장 근거를 확인합니다. 제공 스냅샷 예는 최신 100행, 수량 필드 누락 0, 환산 불일치 0, pack_basis=none 63행입니다. 실제 반환한 판과 값을 우선 기록합니다.

**과제 수정과 DB 갱신은 별개입니다.** 과제는 작은 입력 예제만 검사하고 DB·LLM을 사용하지 않습니다. 실제 원본의 `4 Pack` 표기는 기존 함수가 읽을 수 있어, 제공 그래프에는 스페이서가 이미 정상 수량으로 들어 있습니다. 과제 수정으로 DB가 바뀌었다고 설명하지 않습니다. 실제 적재 구현은 Ch4에서 진행합니다.

## Neo4j 접속

http://localhost:7474 에서 접속합니다. 기본 Bolt 주소는 `bolt://localhost:7687`, 사용자 이름은 `neo4j`, 암호는 본인 `.env` 설정입니다. 포트를 변경했다면 해당 주소를 사용합니다. 제공 조회문은 모두 읽기 전용입니다. 데이터가 비었다면 [초기 설치 안내](../../setup/README.md#8-실습-데이터와-검색-색인-준비)를 확인합니다.

## 이번 챕터에서 남길 결과

- 원본 필드 → 대상 테이블·필드·변환·누락 처리·확인 기준을 적은 매핑표
- 내부 ID와 원천 식별자를 연결한 Crosswalk 확인 기록
- 낱개·팩·배수·가격 단위와 미상값을 구분한 단위 규칙
- 과제의 두 입력 결과와 실제 Neo4j 조회를 구분한 검증 기록

원가 계산·구매 팩 올림·MOQ·반올림의 상세 구현은 Ch6, 관계와 개정판 모델은 Ch3, 그래프 적재 구현은 Ch4로 연결합니다.
