# Part 2 · Ch1 — 부품 변경 질문과 데이터 이해

2개 강의, 각 15분. Ch3에서 제공 데이터를 초기화한 상태를 사용합니다. 이번 챕터는 원본 관찰과 CQ 작성 Hands-on이며, 정규화·모델링·적재 코드의 구현은 Ch2~4에서 진행합니다.

## 1강 · 변경 영향 질문 정의

|순서|화면|직접 할 일|확인·산출물|
|---|---|---|---|
|1|[업무 질문 9개](../../../labs/mfg-bom-agent/data/golden/examples.yaml)|구매·설계변경·정비 역할을 구분하고 대표 질문 3개 선택|사용처·구매·변경 질문|
|2|[CQ 표](worksheets/cq-catalog.csv)|질문별 부품·개정판·대수·단위를 작성|빠진 조건 표시|
|3|[설계용 CQ 15개](../../../labs/mfg-bom-agent/ontology/schema.yaml)|competency_questions에서 CQ-01·02·05의 질문과 유형 확인|업무 질문과 조회 요구 연결|
|4|[Neo4j Browser](http://localhost:7474)|아래 순서로 제공 조회문 실행|같은 SKU·revision의 조립품과 출처 확인|
|5|CQ 표|질문 하나의 기대 결과와 수용 기준 작성|집합·판·단위·출처를 구분|

### Neo4j 접속과 조회

1. Docker의 Neo4j가 실행 중인지 확인하고 http://localhost:7474 에 접속합니다.
2. 접속 주소는 `bolt://localhost:7687`, 사용자 `neo4j`, 비밀번호는 본인 `.env`의 값입니다. 다른 포트를 설정했다면 해당 주소를 사용합니다.
3. [01-inventory.cypher](queries/01-inventory.cypher)를 복사해 실행합니다. 데이터가 비어 있으면 [Ch3 설치 가이드](../../setup/README.md#8-실습-데이터와-검색-색인-준비)로 돌아갑니다. 연결 성공과 데이터 준비를 구분합니다.
4. [02-wheel-usage.cypher](queries/02-wheel-usage.cypher)를 실행해 `sku / assembly / revision / raw_qty / multiplier / source_ref`를 읽습니다. 최신 판을 명시했으므로 여러 판의 같은 행을 합치지 않습니다.
5. 원천 수량과 차량당 수량을 같은 값으로 쓰지 않습니다. 계산 코드 작성과 경로 쿼리 작성은 Ch4·Ch6에서 진행합니다.

수업용 관찰 예: 스냅샷 a78f9eb, 최신 판 6b2c5a9에서 휠 3616-0014-0144의 사용처는 drive wheel, 원천 수량 1, 배수 6입니다. 수강생은 실제 반환한 판과 값을 먼저 기록합니다. 원천이 바뀌면 기대 결과도 재검토합니다.

### CQ 작성 예

|질문|필수 조건|기대 결과|수용 기준|
|---|---|---|---|
|이 휠은 어디에 쓰이나요?|SKU·개정판|상위 조립품과 출처|같은 판에서 조립품 집합 일치|
|20대 생산에 몇 팩이 필요한가요?|대수·대상 범위·팩 크기·구매 조건|낱개 수량과 구매 팩 수|단위·조건·계산값 일치. 정답 계산은 Ch6|
|이 휠을 교체하면 무엇을 확인하나요?|변경 전후 부품·판·적용 조건|영향 경로·장착 조건·검토 항목|등록된 사실과 담당자 판단 구분|

업무 질문 9개는 화면에서 묻는 질문이고, CQ 15개는 이를 답하기 위해 설계한 조회 요구입니다. 1대1 대응이나 같은 개수를 전제하지 않습니다.

## 2강 · 공개 데이터와 교육용 재구성 데이터

### 원본 파일 직접 열기

고정 커밋의 원본 세 파일을 **내용 변경 없이** 아래에 포함했습니다. [출처·해시](reference/SOURCE.json), [Apache-2.0 라이선스](reference/LICENSE.txt)를 함께 보관합니다. `data/raw/nasa-osr` 전체 저장소가 필요하지 않습니다.

- [부품 구성표 parts_list.csv](reference/parts_list/parts_list.csv): 휠 행의 `part #`, `cost pp `, `# req in assy`, `assembly multiplier`.
- [대체·옵션 부품 extra_parts.md](reference/parts_list/extra_parts.md): `Different wheels` 절. 대체품과 장착 조건이 문서에 있습니다. 상대 이미지 링크는 원천 저장소를 기준으로 하며 이 발췌 폴더에는 이미지·CAD가 포함되지 않습니다.
- [서보 기어 정비 README](reference/mechanical/servo_gear_replacement/README.md): 증상과 정비 근거. 검색·문서 연결 구현은 Ch5에서 진행합니다.

다운로드한 저장소의 `docs/part02/ch01/reference/`에서 같은 파일을 편집기로 열 수 있습니다. 원본 전체를 받아 재구성하는 `build_dataset.py`는 이번 강의의 필수 실행 명령이 아닙니다.

### 가공 자료에서 같은 부품 따라가기

아래는 제조 프로젝트 `labs/mfg-bom-agent/data/processed/` 기준입니다.

|파일|확인할 것|
|---|---|
|[plm_item_master.csv](../../../labs/mfg-bom-agent/data/processed/plm_item_master.csv)|part_id·sku·aliases·origin|
|[plm_ebom_line.csv](../../../labs/mfg-bom-agent/data/processed/plm_ebom_line.csv)|같은 SKU의 최신 revision, raw_qty·pack_size·multiplier·source_ref|
|[erp_supplier_item.csv](../../../labs/mfg-bom-agent/data/processed/erp_supplier_item.csv)|price_origin에 해당하는 origin, terms_origin, observed_at, 빈 price_date|
|[quality_document.csv](../../../labs/mfg-bom-agent/data/processed/quality_document.csv)|문서 경로·행·본문·origin|
|[crosswalk.csv](../../../labs/mfg-bom-agent/data/processed/crosswalk.csv)|같은 휠의 내부 ID·공급사 품번|
|[data_quality_issues.csv](../../../labs/mfg-bom-agent/data/processed/data_quality_issues.csv)|제외한 행과 사유. 지금 임의 값으로 메우지 않음|
|[data_inventory.json](../../../labs/mfg-bom-agent/data/processed/data_inventory.json)|스냅샷·판·자료 규모의 요약. 원천별 필드 전체 명세는 아님|

[virtual.py의 Ch1-2 Hands-on](../../../labs/mfg-bom-agent/src/mfg_bom_agent/foundation/virtual.py)에서 공급사와 구매 조건, 대체품, 고장 정보의 근거를 구분합니다. **파일 이름만 보고 모든 값을 가상 데이터로 분류하지 않습니다.**

### Neo4j에서 출처·시점 비교

[03-wheel-origin.cypher](queries/03-wheel-origin.cypher)를 실행합니다.

- goBILDA: 공급사·가격은 source, 구매 조건은 assumption.
- Maker Depot: 가상 공급사·가격·구매 조건.
- observed_at은 자료 관측 시점입니다. price_date가 null이면 실제 가격 기준일은 미상입니다.
- 공개 가격 이력은 저장소 스냅샷에서 읽은 값이며 실제 기업의 거래 이력이 아닙니다.

### Hands-on과 완료 기준

[데이터 목록 CSV](worksheets/data-inventory.csv)에 부품표·구매 조건·정비 문서를 각각 한 행씩 작성하고, 식별자·시점·출처·비어 있는 값을 기록합니다. 원천·파생·가정은 필요한 경우 필드별로 나눠 적습니다.

- [ ] 질문 하나의 입력·기대 결과·수용 기준을 설명할 수 있다.
- [ ] 휠 한 행을 원본 → 가공 테이블 → Neo4j에서 찾았다.
- [ ] 공개 공급사의 구매 조건도 실습 가정일 수 있음을 구분했다.
- [ ] 팩/낱개·배수·다중 ID·시점·누락 중 실제 문제를 두 가지 기록했다.
- [ ] CQ 표, 데이터 목록, 정리할 문제 목록을 다음 챕터에 넘긴다.

## 설계 방법론과 연결

1단계 도메인 분석: 자료 목록·구조·단절·함정을 관찰합니다. 2단계 CQ 설계: 역할·질문 유형·기대 결과·수용 기준을 작성합니다. 원본을 보며 CQ를 다시 다듬습니다. 개념·관계 확정은 Ch3, 매핑·식별자 정규화는 Ch2, 적재와 경로 쿼리 작성은 Ch4에 연결합니다.

**이번에 하지 않는 것:** 스키마 전체 재설계, 새 데이터 적재, 수량·원가 계산 구현, 검색 색인 구현, 에이전트 코드 작성. 이미 적재한 환경에서 관찰 쿼리만 실행합니다.
