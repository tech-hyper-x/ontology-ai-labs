"""계산 규칙 단위 테스트 (Part 2 Ch6-1). Neo4j · LLM 없이 돈다."""

from decimal import Decimal

from mfg_bom_agent.foundation.normalize import (
    extract_pack_size,
    make_part_id,
    parse_price,
    supplier_from_url,
)
from mfg_bom_agent.tools import calc


def test_each_per_product_handles_half_pack():
    # 0.5팩 × 4개/팩 × 배수 2 = 4개 (8mm 스페이서 1522-0010-0060)
    assert calc.each_per_product(Decimal("0.5"), 4, 2) == 4


def test_requirement_cost_uses_pack_price():
    # 서보: 2개 × 배수 2 × 50대 × $31.99 = $6,398.00
    assert calc.money(calc.requirement_cost(Decimal(2), 2, 50, Decimal("31.99"))) == Decimal(
        "6398.00"
    )


def test_purchase_packs_ceiling_and_moq():
    assert calc.packs_to_buy(Decimal(5), 2, 1) == (3, 3)  # 5개 ÷ 2개/팩 → 3팩 (올림)
    assert calc.packs_to_buy(Decimal(4), 4, 5) == (1, 5)  # MOQ 5팩이 더 크다


def test_rounding_happens_once_at_the_end():
    # 모터 $42.99 × 15% × 6개 = 38.691 → $38.69 (한 개씩 반올림하면 6 × 6.45 = 38.70 으로 틀린다)
    diff = calc.apply_percent(Decimal("42.99"), Decimal(15)) * 6 - Decimal("42.99") * 6
    assert calc.money(diff) == Decimal("38.69")


def test_pack_size_comes_from_long_name():
    assert extract_pack_size(
        "1522 Series 8mm ID Spacer (10mm OD, 6mm Length) - 4 Pack - goBILDA", "8mm ID Spacer"
    ) == (4, "name")
    assert extract_pack_size("M4x6 Button Screw 25-pack") == (25, "name")
    assert extract_pack_size("2000 Series Dual Mode Servo (25-2, Torque) - goBILDA") == (1, "none")


def test_identifiers():
    assert make_part_id("2000-0025-0002", "", "") == "P-2000-0025-0002"
    assert (
        make_part_id("", "Traxxas 5374X Talon Tires, Gemini Wheels", "https://x/5374x") == "P-5374X"
    )
    assert parse_price("$1,234.50") == Decimal("1234.50")
    assert supplier_from_url("https://www.gobilda.com/x/") == "gobilda.com"
