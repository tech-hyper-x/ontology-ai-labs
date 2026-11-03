"""Golden Set 정답을 만드는 참조 계산 (Part 2 Ch8).

정답은 에이전트 · 도구 코드와 독립적으로 만들어야 한다. 도구가 틀리면 정답도 같이 틀려서
평가가 아무것도 잡아내지 못하기 때문이다. 그래서 이 모듈은 Neo4j 도 tools/ 도 쓰지 않고
data/processed CSV 를 직접 읽어 Decimal 로 다시 계산한다.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path

PROCESSED = Path(__file__).resolve().parents[3] / "data" / "processed"
CENT = Decimal("0.01")


@lru_cache
def table(name: str) -> tuple[dict, ...]:
    with (PROCESSED / f"{name}.csv").open(encoding="utf-8") as f:
        return tuple(csv.DictReader(f))


def latest() -> str:
    return next(r["revision_id"] for r in table("plm_revision") if r["is_latest"] == "True")


def part_lines(revision: str | None = None, mechanical_only: bool = True) -> list[dict]:
    rev = revision or latest()
    rows = [
        r
        for r in table("plm_ebom_line")
        if r["revision_id"] == rev and r["parent_type"] == "Assembly"
    ]
    if mechanical_only:
        rows = [r for r in rows if not r["parent_id"].endswith("electronics")]
    return rows


def sku(part_id: str) -> str:
    return next(r["sku"] for r in table("plm_item_master") if r["part_id"] == part_id)


def money(v: Decimal) -> Decimal:
    return v.quantize(CENT, rounding=ROUND_HALF_UP)


def required_each(part_sku: str, units: int, revision: str | None = None) -> Decimal:
    return sum(
        (
            Decimal(r["qty_each"]) * int(r["multiplier"]) * units
            for r in part_lines(revision, False)
            if sku(r["child_id"]) == part_sku
        ),
        Decimal(0),
    )


def offer(part_sku: str, supplier: str | None = None) -> dict:
    rows = [o for o in table("erp_supplier_item") if sku(o["part_id"]) == part_sku]
    return next(
        o for o in rows if (o["supplier_id"] == supplier if supplier else o["origin"] == "source")
    )


def purchase_packs(part_sku: str, units: int) -> tuple[int, Decimal]:
    o = offer(part_sku)
    need = math.ceil(required_each(part_sku, units) / int(o["pack_size"]))
    packs = max(need, int(o["moq_packs"]))
    return packs, money(packs * Decimal(o["unit_price"]))


def cost(
    units: int = 1,
    revision: str | None = None,
    assembly: str | None = None,
    overrides: dict[str, Decimal] | None = None,
) -> Decimal:
    total = Decimal(0)
    for r in part_lines(revision):
        if assembly and r["parent_id"] != f"OSR/{assembly}":
            continue
        price = (overrides or {}).get(sku(r["child_id"])) or Decimal(r["unit_price"])
        total += Decimal(r["raw_qty"]) * int(r["multiplier"]) * units * price
    return money(total)


def price_change_diff(part_sku: str, percent: str, units: int) -> Decimal:
    before = sum(
        (
            Decimal(r["raw_qty"]) * int(r["multiplier"]) * units * Decimal(r["unit_price"])
            for r in part_lines()
            if sku(r["child_id"]) == part_sku
        ),
        Decimal(0),
    )
    after = before * (Decimal(100) + Decimal(percent)) / Decimal(100)
    return money(after) - money(before)


def where_used(part_sku: str, revision: str | None = None) -> set[str]:
    return {
        r["parent_id"].split("/", 1)[1]
        for r in part_lines(revision, False)
        if sku(r["child_id"]) == part_sku
    }


def shared_parts() -> set[str]:
    by = defaultdict(set)
    for r in part_lines():
        by[sku(r["child_id"])].add(r["parent_id"])
    return {k for k, v in by.items() if len(v) > 1}


def assembly_parts(assembly: str) -> set[str]:
    return {sku(r["child_id"]) for r in part_lines() if r["parent_id"] == f"OSR/{assembly}"}


def suppliers_of(part_sku: str) -> set[str]:
    return {o["supplier_id"] for o in table("erp_supplier_item") if sku(o["part_id"]) == part_sku}


def single_supplier_parts(supplier: str | None = None) -> set[str]:
    parts = {sku(r["child_id"]) for r in part_lines()}
    return {
        p
        for p in parts
        if len(suppliers_of(p)) == 1 and (supplier is None or suppliers_of(p) == {supplier})
    }


def alternates(part_sku: str) -> set[str]:
    return {
        sku(a["alternate_part_id"]) for a in table("plm_alternate") if sku(a["part_id"]) == part_sku
    }


def superseded_by(part_sku: str) -> set[str]:
    return {
        sku(s["old_part_id"]) for s in table("plm_supersedes") if sku(s["new_part_id"]) == part_sku
    }


def ecn_by_date(prefix: str) -> dict:
    rows = [e for e in table("plm_ecn") if e["ecn_date"].startswith(prefix)]
    assert len(rows) == 1, f"{prefix} 에 해당하는 ECN 이 {len(rows)}건"
    return rows[0]


def ecn_changed_parts(ecn_id: str) -> set[str]:
    return {sku(r["part_id"]) for r in table("plm_ecn_line") if r["ecn_id"] == ecn_id}


def ecn_cost_diff(ecn_id: str) -> Decimal:
    e = next(r for r in table("plm_ecn") if r["ecn_id"] == ecn_id)
    return cost(1, e["revision_to"]) - cost(1, e["revision_from"])


def revision_interval(revision: str) -> tuple[str, str]:
    r = next(x for x in table("plm_revision") if x["revision_id"] == revision)
    return r["valid_from"], r["valid_to"] or "현재"
