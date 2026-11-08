# Part 2 · Ch6 — 수량·원가 계산과 MCP 도구

Ch5에서 찾은 서보 `2000-0025-0002`·rocker bogie 사용처와 문서 출처를 계산 입력으로 이어갑니다. 14강·15강 각20분 계획입니다. 설치·추가 연습 시간은 별도이며 실제 낭독 시간은 리허설로 확인합니다.

## 시작 위치와 준비

모든 Python 명령은 저장소의 `labs/mfg-bom-agent`에서 실행합니다. [설치](../../setup/README.md)와 Ch4 그래프 적재를 마친 상태를 전제로 합니다. Ch6에서는 DB를 재적재하거나 색인을 다시 만들지 않습니다.

```bash
cd ontology-ai-labs/labs/mfg-bom-agent
```

14강 계산·CSV 검산은 DB·API 키 없이 가능합니다. 15강 업무 도구는 Neo4j가 필요하지만 LLM·임베딩 API는 호출하지 않습니다. HTTP 기본 주소는 `http://localhost:8000/mcp`이며 `.env`의 `MCP_URL` 설정을 사용합니다.

## 14강 · 계산 계약 → 작성 → 검산

1. [calc.py](../../../labs/mfg-bom-agent/src/mfg_bom_agent/tools/calc.py)의 수량·팩·금액 계산을 읽습니다. 그래프는 수량과 가격의 재료를 반환하고 Python 함수가 계산합니다.
2. 총소요량은 원천수량×팩크기×배수×생산대수입니다. 같은 부품의 모든 라인 소요량을 합한 뒤 구매 팩 수를 올립니다.
3. 소요 원가는 소요 낱개÷팩크기×팩당 단가입니다. 구매 팩 수는 max(올림(소요 낱개÷팩크기), MOQ)입니다. MOQ는 최소 팩 수이며 MOQ의 정수배로 구매하는 규칙이 아닙니다.
4. 금액은 Decimal로 중간 정밀도를 유지하고 각 출력 합계에서 HALF_UP 센트 반올림합니다. 반올림된 라인 표시값을 다시 합계 입력으로 쓰지 않습니다.

```bash
uv run python ../../examples/part02/ch06/ch06_calculate.py
uv run pytest -q tests/test_calc.py
uv run python ../../examples/part02/ch06/ch06_purchase.py --check
```

마지막 명령은 미작성 상태에서 `NotImplementedError`가 납니다. [작성 파일](../../../examples/part02/ch06/ch06_purchase.py)의 calculate 함수에서 네 값을 작성합니다. `calc.cost_of_each`, `calc.money`, `calc.packs_to_buy`를 사용하세요. 입력 검증·함수 이름·check·기대값은 유지합니다. 작성 후 같은 명령을 다시 실행합니다. [해설](../../../examples/part02/ch06/ch06_purchase_solution.py)은 작성 후 대조합니다.

- 7개·4개입·팩당$10·MOQ1: 소요원가$17.50 / 구매2팩·$20.00 / 잔량1개. 교육용 예시입니다.
- 4개·4개입·팩당$10·MOQ5: 소요원가$10.00 / 구매5팩·$50.00 / 잔량16개.
- 실제 스페이서 7개: 4개입·팩당$3.49·MOQ1 → 구매2팩·$6.98·잔량1개. 소요원가는$6.11입니다.

[계산 기록표](worksheets/calculation-record.csv)에 조건과 단위를 기록합니다. 현재 모델에는 재고·입고 예정량 차감이 없으므로 **BOM 총소요량**이며 순소요량이 아닙니다. 운송비·세금·공임·폐기율도 포함하지 않습니다.

### 기준값과 판 비교

제공 스냅샷 최신 판 `6b2c5a9`: 서보50대200개·소요금액$6,398.00, 모터15% 인상은1대$38.69 /100대$3,869.10 증가. 1대 반올림값×100을 계산하지 않습니다. 기계부품 전체1대 소요원가는$1,330.38입니다.

휠 ECN `ECN-2024-06-18-72edc6e`는 `778fe3d`→`72edc6e`, 각 판의 기계부품 소요원가$1,255.66→$1,300.75로$45.09 증가입니다. 이전 휠5374X는 원천 팩 표기 미확인(pack_size1·배수3), 이후 휠은배수6입니다. **저장된 BOM·각 판의 기록 단가 비교**이며 실물 휠6개의 동등 견적 비교·최신 가격이 아닙니다. ECN도 커밋에서 재구성한 교육용 기록입니다.

## 15강 · 계약 → MCP 호출 → 결과 대조

한 터미널에서 서버를 실행합니다. 이미 같은 포트의 서버가 실행 중이면 중복 실행하지 않습니다.

```bash
uv run python -m mfg_bom_agent.mcp_server
```

다른 터미널도 `labs/mfg-bom-agent`에서 실행합니다.

```bash
uv run python ../../examples/part02/ch06/ch06_mcp.py list
uv run python ../../examples/part02/ch06/ch06_mcp.py usage --revision 6b2c5a9
uv run python ../../examples/part02/ch06/ch06_mcp.py explode --revision 6b2c5a9
uv run python ../../examples/part02/ch06/ch06_mcp.py servo --revision 6b2c5a9
uv run python ../../examples/part02/ch06/ch06_mcp.py purchase --revision 6b2c5a9
uv run python ../../examples/part02/ch06/ch06_mcp.py motor --revision 6b2c5a9
uv run python ../../examples/part02/ch06/ch06_mcp.py wheel
```

`list`는 상태2개+업무9개=11개 도구의 설명·입력 스키마를 출력하고 ping을 호출합니다. ping 성공은 Neo4j 연결 성공의 증거가 아닙니다. usage 등 실제 업무 호출도 확인합니다. `--transport inprocess`는 서버 객체에 메모리로 연결하며 HTTP 검증과 구분합니다.

### 직접 요청 작성

[tool-request.json](worksheets/tool-request.json)을 열어 `units`만100→1로 바꾸고 실행합니다.

```bash
uv run python ../../examples/part02/ch06/ch06_mcp.py custom --input ../../docs/part02/ch06/worksheets/tool-request.json
```

100대$3,869.10 /1대$38.69를 비교합니다. 입력·출력·판을 [도구 계약표](worksheets/tool-contract.csv)에 기록하고, 값을 되돌립니다. 바이브코딩 요청 예: "기존 클라이언트와 계약을 유지하고 이 요청의 생산 대수만 1로 바꿔 주세요. 금액을 직접 계산하거나 기대값을 수정하지 말고 호출 인자와 도구 반환값을 보여 주세요."

### 정상 0건·업무 오류·전송 오류 구분

```bash
uv run python ../../examples/part02/ch06/ch06_mcp.py missing
uv run python ../../examples/part02/ch06/ch06_mcp.py absent --revision 6b2c5a9
uv run python ../../examples/part02/ch06/ch06_mcp.py invalid-units
uv run python ../../examples/part02/ch06/ch06_mcp.py missing-value
```

없는 품번은 error/hint, 존재하나 최신 판에 없는 구형 모터는 빈lines와warnings, 대수0은입력오류, 변경률누락은value필요 오류입니다. `protocol_error=false`여도 structured_content.error를 읽어야 합니다. 연결 자체가 실패하면 네트워크·서버 예외가 발생하며 업무 0건과 구분합니다. 모든 잘못된 입력이 구조화 오류로 처리되는 구현은 아닙니다.

## 결과 해석과 Ch7 인계

- `revision`: 조회한 BOM 판. null 입력은 최신 판 선택.
- `as_of`: 가격 관측 기준. 최신 판은2026-10-22 스냅샷, 과거 판은 코드가 커밋일을 관측 기준으로 사용합니다. 실제 거래가격 적용일이 아닙니다.
- `price_date`: 실제 가격 적용일 미상(null).
- `assumptions`: 단종·인상 시나리오, 교육용 MOQ 등의 가정.
- `warnings`: 구매금액과 소요원가 차이, 판에 없는 부품 등.
- 수량 단위ea·팩과 금액USD를 대조합니다. 현재 모든 응답에 currency·원천행이 자동 포함되는 것은 아닙니다. where_used.lines.source_ref와 원천 CSV를 함께 기록합니다.

서보 단종 가정의$6,398.00는 기존 부품 소요금액입니다. 단종 손실·교체 추가비용은 아니며 extra_cost는미확인입니다. 조회·계산은 도구가 수행하고 교체 결정은 담당자가 합니다.

Ch7에는 ① 계산기록표 ② 작성한구매함수 ③ 정상·오류호출 결과 ④ 질문↔도구표를 넘깁니다. 자동 도구선택·답변작성·인용검사는Ch7, Golden Set 전체평가는Ch8에서 진행합니다. CQ-03·04의전용도구누락도 Ch8 개선사례로 남깁니다.

[강사용 진행 메모](INSTRUCTOR.md)
