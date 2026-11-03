"""교육용 가정 데이터 (Part 2 Ch1-2 공개 데이터와 교육용 재구성 데이터).

공개 원천에는 ERP 정보(대체 공급사, 최소 주문 수량, 리드타임)와 업무 시나리오(단종, 단가 인상)가 없다.
실습 질문에 답하려면 이 값이 필요해서, 아래 표를 "교육용 가정"으로 만들어 쓴다.

규칙
- 무작위로 만들지 않고 표로 고정한다. 누가 실행해도 같은 값이 나와야 정답(Golden Set)이 흔들리지 않는다.
- 모든 행에 origin 을 남긴다: "virtual"(가상 공급사 · 가상 제안) / "assumption"(실습 가정값)
- 화면과 답변은 origin 이 source 가 아닌 값을 "교육용"으로 표시한다.
"""

from __future__ import annotations

from decimal import Decimal

# ─── [Hands-on P2-Ch1-2 NASA 로버 공개 데이터와 교육용 재구성 데이터] 시작 ───
# 아래 표마다 origin(source · virtual · assumption)을 확인하고, 원천에 없는 값이 무엇인지 자료 목록에 적는다.
# 원천에서 확인되는 공급사 + 교육용 가상 공급사
SUPPLIERS = [
    {"supplier_id": "gobilda.com", "name": "goBILDA", "origin": "source"},
    {"supplier_id": "digikey.com", "name": "Digi-Key", "origin": "source"},
    {"supplier_id": "dollarhobbyz.com", "name": "Dollar Hobbyz", "origin": "source"},
    {
        "supplier_id": "alt-robotics",
        "name": "Alt Robotics Supply (교육용 가상)",
        "origin": "virtual",
    },
    {"supplier_id": "maker-depot", "name": "Maker Depot (교육용 가상)", "origin": "virtual"},
]

# 원천 공급사의 구매 조건 기본값. 원천에 없으므로 실습 가정이다.
SOURCE_SUPPLIER_DEFAULTS = {
    "gobilda.com": {"moq_packs": 1, "lead_time_days": 7},
    "digikey.com": {"moq_packs": 1, "lead_time_days": 5},
    "dollarhobbyz.com": {"moq_packs": 1, "lead_time_days": 10},
}

# 가상 공급사의 제안. 단가는 goBILDA 스냅샷 단가에 배율을 곱해 만든다 (배율도 가정).
# 서보(2000-0025-0002)는 일부러 넣지 않는다 — "등록 대체 공급원이 없는 부품" 시나리오가 필요해서다.
VIRTUAL_OFFERS = [
    {
        "part_id": "P-5203-2402-0027",
        "supplier_id": "alt-robotics",
        "price_factor": Decimal("1.06"),
        "moq_packs": 2,
        "lead_time_days": 21,
        "supplier_sku": "AR-YJ-5203-27",
    },
    {
        "part_id": "P-3616-0014-0144",
        "supplier_id": "maker-depot",
        "price_factor": Decimal("0.97"),
        "moq_packs": 4,
        "lead_time_days": 30,
        "supplier_sku": "MD-WW144",
    },
    {
        "part_id": "P-1611-0514-0008",
        "supplier_id": "maker-depot",
        "price_factor": Decimal("0.90"),
        "moq_packs": 5,
        "lead_time_days": 14,
        "supplier_sku": "MD-BRG-8-14",
    },
    {
        "part_id": "P-1604-0043-0032",
        "supplier_id": "alt-robotics",
        "price_factor": Decimal("1.10"),
        "moq_packs": 2,
        "lead_time_days": 21,
        "supplier_sku": "AR-PB-32",
    },
    {
        "part_id": "P-2802-0004-0010",
        "supplier_id": "maker-depot",
        "price_factor": Decimal("0.85"),
        "moq_packs": 10,
        "lead_time_days": 14,
        "supplier_sku": "MD-M4X10-BTN-25",
    },
]

# 업무 시나리오의 가정. 원천에서 확인된 사실이 아니라 질문을 만들기 위한 조건이다.
SCENARIO_PARAMETERS = [
    {
        "scenario_id": "S4-servo-discontinued",
        "parameter": "discontinued_part_id",
        "value": "P-2000-0025-0002",
        "description": "서보 2000-0025-0002 단종 가정",
    },
    {
        "scenario_id": "S5-gobilda-disruption",
        "parameter": "disrupted_supplier_id",
        "value": "gobilda.com",
        "description": "goBILDA 공급 중단 가정",
    },
    {
        "scenario_id": "S6-motor-price-up",
        "parameter": "price_change_percent",
        "value": "15",
        "description": "모터 5203-2402-0027 단가 15% 인상 가정",
    },
]

# 대체 가능 관계. 스냅샷의 parts_list/extra_parts.md "Different wheels" 절에서 옮긴 것이다 (원천 문서 기반).
# pack_price · pack_size 는 문서에 적힌 대체 부품 가격이다. BOM 에 없는 부품이라 부품표 단가 대신 이 값을 쓴다.
ALTERNATES = [
    {
        "part_id": "P-3616-0014-0144",
        "alternate_part_id": "P-5374X",
        "compatibility": "모터 허브에 맞추려면 드릴 가공 필요",
        "requires_rework": True,
        "source_doc": "parts_list/extra_parts.md",
        "source_section": "Different wheels",
        # 문서: "$34.95 per pair of two" — 2개 1쌍 가격이다
        "pack_price": "34.95",
        "pack_size": 2,
        "price_note": "문서에 적힌 2개 1쌍 가격 (DollarHobbyz). 문서의 '약 $135 절감'은 휠 단가로 계산한 차이와 달라 휠 가격만 비교",
    },
    {
        "part_id": "P-3616-0014-0144",
        "alternate_part_id": "P-3616-0014-0192",
        "compatibility": "가공 없이 장착, 직경이 커서 소프트웨어 휠 크기 설정 변경",
        "requires_rework": False,
        "source_doc": "parts_list/extra_parts.md",
        "source_section": "Different wheels",
        # 문서: 기본 휠보다 "adds $90 total" (1대 6개) → 1개 $24.99 + $15 = $39.99.
        # 품번 · 가격은 문서가 링크한 goBILDA 상품 페이지에서 확인했다 (2026-10-25, $39.99).
        "pack_price": "39.99",
        "pack_size": 1,
        "price_note": "문서의 '1대당 $90 추가'와 goBILDA 상품 페이지 가격 $39.99 (2026-10-25 확인)",
    },
]

# 대체 후보 중 릴리스 BOM 에 한 번도 들어간 적 없는 부품. 문서에 적힌 정보로 부품 노드를 만든다.
DOC_ONLY_PARTS = [
    {
        "part_id": "P-3616-0014-0192",
        "sku": "3616-0014-0192",
        "name": "Wasteland Wheel (192mm Diameter, 72mm Width)",
        "aliases": "bigger wasteland wheel|192mm wheel",
        "url": "https://www.gobilda.com/wasteland-wheel-192mm-diameter-72mm-width/",
    },
]

# 고장 모드. 정비 문서의 문장을 근거로 만든 파생 데이터다 (문서 경로 · 행 번호를 함께 남긴다).
FAILURE_MODES = [
    {
        "fm_id": "FM-SERVO-GEARSET",
        "part_id": "P-2000-0025-0002",
        "severity": "high",
        "name": "서보 기어 세트 파손 (중앙 축 전단 · 출력 기어 이 빠짐)",
        "symptom": "코너 휠이 돌지 않음 (조향 불가)",
        "doc_path": "mechanical/servo_gear_replacement/README.md",
        "doc_line": 3,
    },
    {
        "fm_id": "FM-SERVO-CONNECTION",
        "part_id": "P-2000-0025-0002",
        "severity": "medium",
        "name": "서보 전기 연결 불량 (느슨한 커넥터)",
        "symptom": "코너 휠이 돌지 않음 (조향 불가)",
        "doc_path": "mechanical/servo_gear_replacement/README.md",
        "doc_line": 18,
    },
]

# ─── [Hands-on P2-Ch1-2] 끝 ───
