"""단위와 식별자 정규화 (Part 2 Ch2 부품 데이터 연결과 정리).

parts_list.csv 의 한 행은 "어셈블리 하나에 이 상품을 몇 개 사서 넣는가"를 적는다.
여기서 상품은 낱개일 수도, 2개 · 4개 · 25개 묶음(pack)일 수도 있다. 가격도 상품(팩) 단위다.
계산을 정확히 하려면 원천 값을 보존한 채 다음을 분리해야 한다.

- raw_qty     원천 수량 (팩 단위, 0.5 같은 소수 포함)
- pack_size   한 상품에 든 낱개 수 (품명의 "2 Pack" · "25-pack" 에서 추출, 표기 없으면 1)
- qty_each    낱개로 환산한 수량 = raw_qty × pack_size
- unit_price  상품(팩) 하나의 가격

원가는 raw_qty × unit_price × 배수 로 계산하면 원천 합계($1,330.38)와 같고,
낱개 수량은 qty_each × 배수 로 계산한다. 두 값을 섞지 않는 것이 이 모듈의 목적이다.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

# ─── [Hands-on P2-Ch2-1 부품·구매 데이터 매핑] 시작 ───
# 원천 열 이름 → 교육용 공통 필드 이름. 원천 열 "cost pp " 는 끝에 공백이 있다.
# 공백을 지우지 않고 그대로 매핑해야 원천이 바뀌었을 때 매핑 오류를 바로 알아챌 수 있다.
PARTS_LIST_COLUMNS = {
    "assembly": "assembly_name",
    "short name": "short_name",
    "part #": "sku",
    "long name": "long_name",
    "link": "url",
    "cost pp ": "unit_price_raw",
    "# req in assy": "raw_qty",
    "assembly multiplier": "multiplier",
}


class MalformedRow(ValueError):
    """열 개수가 머리글과 다른 행. 품명 안의 쉼표 때문에 칸이 밀린 경우가 대표적이다."""


def map_parts_row(row: dict[str, str]) -> dict[str, str]:
    """parts_list.csv 한 행을 공통 필드 이름으로 바꾼다.

    - 머리글보다 칸이 많은 행(csv 모듈이 남는 칸을 None 키에 담는다)은 MalformedRow 로 알린다.
      실제로 2023-06-25 판(07a4405)에 이런 행이 4개 있고, 다음 커밋에서 원저자가 고쳤다.
      값을 추측해 고치지 않고 품질 이슈로 기록한 뒤 건너뛴다.
    - 매핑에 없는 열 이름이 오면 원천 형식이 바뀐 것이므로 바로 실패한다.
    """
    if None in row:
        raise MalformedRow(f"열 개수 불일치 (남는 칸 {row[None]})")
    if any(
        v is None for v in row.values()
    ):  # 칸이 모자라면 csv 모듈이 뒤쪽 열 값을 None 으로 채운다
        raise MalformedRow("열 개수 불일치 (모자란 칸)")
    unknown = set(row) - set(PARTS_LIST_COLUMNS)
    if unknown:
        raise KeyError(f"매핑에 없는 원천 열: {sorted(unknown)}")
    return {PARTS_LIST_COLUMNS[k]: (v or "").strip() for k, v in row.items()}


def supplier_from_url(url: str) -> str:
    """구매 링크 도메인을 공급사 ID 로 쓴다. 원천에 공급사 열이 따로 없기 때문이다.

    예: https://www.gobilda.com/... → "gobilda.com"
    """
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.") or "unknown"


# ─── [Hands-on P2-Ch2-1] 끝 ───


# ─── [Hands-on P2-Ch2-2 단위와 식별자 정규화] 시작 ───
# 품명에 들어 있는 포장 단위 표기. "2 Pack", "- 4 Pack", "25-pack", "2pack" 을 모두 잡는다.
_PACK_PATTERN = re.compile(r"(\d+)\s*-?\s*pack\b", re.IGNORECASE)
# SKU 가 비어 있는 행에서 상품 번호를 찾는 패턴 (예: "Traxxas 5374X Talon Tires" → 5374X)
_MODEL_NO_PATTERN = re.compile(r"\b(\d{3,5}[A-Z])\b")


def parse_price(text: str) -> Decimal | None:
    """ "$31.99" · "1,234.50" 같은 가격 문자열을 Decimal 로 바꾼다. 비어 있으면 None.

    돈은 float 로 다루지 않는다. 0.1 + 0.2 처럼 이진 소수 오차가 생기기 때문이다.
    """
    cleaned = text.replace("$", "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"가격 형식을 읽을 수 없습니다: {text!r}") from exc


def parse_qty(text: str) -> Decimal:
    """원천 수량(팩 단위)을 Decimal 로 바꾼다. 0.5 같은 소수를 그대로 보존한다."""
    return Decimal(text.strip())


def extract_pack_size(long_name: str, short_name: str = "") -> tuple[int, str]:
    """상품 하나에 든 낱개 수와 그 근거를 돌려준다.

    반환: (pack_size, basis)
      basis = "name"  품명에서 "N Pack" 표기를 찾았다
              "none"  표기가 없어 낱개 판매로 본다 (교육용 가정, 화면에 표시한다)

    long name 을 먼저 본다. short name 에는 포장 표기가 빠진 경우가 많다
    (예: short name "8mm ID Spacer" 의 long name 은 "... - 4 Pack").
    """
    for text in (long_name, short_name):
        match = _PACK_PATTERN.search(text or "")
        if match:
            return int(match.group(1)), "name"
    return 1, "none"


def make_part_id(sku: str, long_name: str, url: str) -> str:
    """내부 부품 ID 를 만든다. 원천 SKU 는 그대로 두고, 그래프 안에서만 쓰는 키를 따로 둔다.

    - SKU 가 있으면 "P-" + SKU (예: P-2000-0025-0002)
    - SKU 가 없으면 품명에서 상품 번호를 찾는다 (예: Traxxas 5374X → P-5374X)
    - 그래도 없으면 링크 경로의 마지막 조각을 쓴다
    """
    if sku:
        return f"P-{sku}"
    match = _MODEL_NO_PATTERN.search(long_name or "")
    if match:
        return f"P-{match.group(1)}"
    slug = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    return f"P-{slug[:40]}" if slug else "P-UNKNOWN"


def display_sku(sku: str, part_id: str) -> str:
    """화면 · 답변에 보여 줄 품번. 원천 SKU 가 없으면 내부 ID 에서 접두어를 뗀 값을 쓴다."""
    return sku or part_id.removeprefix("P-")


def assembly_id(product_id: str, assembly_name: str) -> str:
    """어셈블리 ID. 같은 이름의 어셈블리가 다른 제품에 생겨도 겹치지 않게 제품 ID 를 앞에 붙인다."""
    return f"{product_id}/{assembly_name.strip().lower()}"


# ─── [Hands-on P2-Ch2-2] 끝 ───
