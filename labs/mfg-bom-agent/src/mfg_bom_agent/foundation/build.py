"""원천 → data/processed/ 교육용 테이블 생성 (Part 2 Ch2 · Ch3).

실행: uv run python scripts/build_dataset.py

만드는 테이블 (모든 행에 origin: source 원천 그대로 / derived 원천에서 파생 / virtual · assumption 교육용)
  PLM   plm_revision · plm_assembly · plm_item_master · plm_ebom_line · plm_ecn · plm_ecn_line
        plm_supersedes · plm_alternate
  ERP   erp_supplier · erp_supplier_item · erp_price_history · scenario_parameters
  품질  quality_document · quality_failure_mode
  공통  crosswalk (식별자 대응표) · data_inventory.json (자료 목록)

data/processed/ 는 git 에 함께 올린다. 수강생은 원천을 내려받지 않고도 Ch4 적재부터 시작할 수 있다.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from decimal import Decimal

from mfg_bom_agent.foundation import ecn as ecn_mod
from mfg_bom_agent.foundation import normalize as nz
from mfg_bom_agent.foundation import sources as src
from mfg_bom_agent.foundation import virtual
from mfg_bom_agent.retrieval.chunking import chunk_issue, chunk_markdown

PROCESSED_DIR = src.PROJECT_ROOT / "data" / "processed"
PRODUCT_ID = "OSR"
PRODUCT_NAME = "NASA JPL Open Source Rover"
ELECTRONICS = "electronics"


def _write(name: str, rows: list[dict], fields: list[str]) -> None:
    path = PROCESSED_DIR / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in fields})
    print(f"  {name:22} {len(rows):5}행 → {path.relative_to(src.PROJECT_ROOT)}")


def _bom_text_chunks(rows: list[dict], revision: str, size: int = 10) -> list[dict]:
    """최신 판 BOM 을 표 텍스트 청크로 만든다. RAG 비교 실행에서 "문서로만 BOM 을 읽는" 조건을 위한 것이다.

    에이전트(지식 그래프 + 도구)는 이 청크를 쓰지 않는다 — BOM 은 그래프에서 구조로 조회한다.
    """
    header = "assembly | short name | part # | cost pp (USD per item/pack) | # req in assy | assembly multiplier"
    chunks = []
    for i in range(0, len(rows), size):
        body = "\n".join(
            f"{r['assembly']} | {r['short name']} | {r['part #']} | {r['cost pp '].strip()} | "
            f"{r['# req in assy']} | {r['assembly multiplier']}  ({r['long name']})"
            for r in rows[i : i + size]
        )
        chunks.append(
            {
                "doc_id": f"{src.PARTS_LIST}@{revision}#rows{i + 1}-{i + len(rows[i : i + size])}",
                "source": "bom_text",
                "path": src.PARTS_LIST,
                "title": f"parts_list rows {i + 1}+",
                "line": i + 2,
                "text": f"{header}\n{body}",
            }
        )
    return chunks


def build() -> dict:
    """원천을 읽어 모든 교육용 테이블을 만들고 자료 목록(inventory)을 돌려준다."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    raw_revisions = src.list_parts_revisions()
    revisions = ecn_mod.revision_intervals([(r.commit, r.committed_at) for r in raw_revisions])
    for rev, raw in zip(revisions, raw_revisions):
        rev.update(committed_at=raw.committed_at, message=raw.message, origin="source")
    latest = revisions[-1]["revision_id"]

    items: dict[str, dict] = {}
    assemblies: dict[str, dict] = {}
    ebom: list[dict] = []
    price_history: list[dict] = []
    lines_by_revision: dict[str, dict[tuple[str, str], dict]] = {}

    # 1) 기계 BOM — 판마다 모든 행을 정규화해 BOM 라인으로 만든다
    quality_issues: list[dict] = []
    for rev in revisions:
        rid = rev["revision_id"]
        lines: dict[tuple[str, str], dict] = {}
        for row_no, raw_row in enumerate(src.read_csv_at(rid, src.PARTS_LIST), start=1):
            try:
                row = nz.map_parts_row(raw_row)
            except nz.MalformedRow as exc:
                quality_issues.append(
                    {
                        "revision_id": rid,
                        "row_no": row_no,
                        "issue": str(exc),
                        "short_name": raw_row.get("short name", ""),
                        "action": "행 제외",
                    }
                )
                continue
            if not row["assembly_name"]:
                continue
            asm_id = nz.assembly_id(PRODUCT_ID, row["assembly_name"])
            assemblies.setdefault(
                asm_id,
                {
                    "assembly_id": asm_id,
                    "product_id": PRODUCT_ID,
                    "name": row["assembly_name"].strip().lower(),
                    "domain": "mechanical",
                    "origin": "source",
                },
            )
            part_id = nz.make_part_id(row["sku"], row["long_name"], row["url"])
            pack_size, pack_basis = nz.extract_pack_size(row["long_name"], row["short_name"])
            raw_qty = nz.parse_qty(row["raw_qty"])
            price = nz.parse_price(row["unit_price_raw"])
            supplier_id = nz.supplier_from_url(row["url"])
            item = items.setdefault(
                part_id,
                {
                    "part_id": part_id,
                    "sku": nz.display_sku(row["sku"], part_id),
                    "name": row["long_name"],
                    "aliases": set(),
                    "domain": "mechanical",
                    "mpn": "",
                    "pack_size": pack_size,
                    "pack_basis": pack_basis,
                    "first_seen": rid,
                    "origin": "source",
                },
            )
            item["aliases"].add(row["short_name"].strip().lower())
            item["last_seen"] = rid
            if rid == latest:
                item.update(
                    name=row["long_name"],
                    pack_size=pack_size,
                    pack_basis=pack_basis,
                    supplier_id=supplier_id,
                    url=row["url"],
                    unit_price=price,
                )
            key = (asm_id, part_id)
            if key in lines:  # 같은 판 · 같은 어셈블리에 같은 부품이 두 번 나오면 수량을 합친다
                lines[key]["raw_qty"] = str(Decimal(lines[key]["raw_qty"]) + raw_qty)
                continue
            line = {
                "bomline_id": f"{rid}:{asm_id}:{part_id}",
                "revision_id": rid,
                "parent_type": "Assembly",
                "parent_id": asm_id,
                "child_type": "Part",
                "child_id": part_id,
                "row_no": row_no,
                "short_name": row["short_name"],
                "raw_qty": str(raw_qty),
                "pack_size": pack_size,
                "pack_basis": pack_basis,
                "qty_each": str(raw_qty * pack_size),
                "multiplier": int(row["multiplier"]),
                "unit": "pack" if pack_size > 1 else "ea",
                "origin": "source",
                "unit_price": str(price) if price is not None else "",
                "price_observed_at": rev["valid_from"],
                "source_ref": f"{src.PARTS_LIST}@{rid}#row{row_no}",
            }
            lines[key] = line
            if price is not None:
                price_history.append(
                    {
                        "part_id": part_id,
                        "supplier_id": supplier_id,
                        "unit_price": str(price),
                        "currency": "USD",
                        "pack_size": pack_size,
                        "observed_at": rev["valid_from"],
                        "revision_id": rid,
                        "origin": "source",
                    }
                )
        lines_by_revision[rid] = lines
        ebom.extend(lines.values())
        # 원천에는 "어셈블리가 제품에 들어간다"는 행이 없다. 판마다 제품 → 어셈블리 라인을 파생해 만든다.
        # 수량 · 배수는 1 이다. 배수는 부품 라인에만 두어 한 번만 곱해지게 한다 (설계 덱 28장 매핑 계약).
        for asm_id in sorted({k[0] for k in lines}):
            ebom.append(
                {
                    "bomline_id": f"{rid}:{PRODUCT_ID}:{asm_id}",
                    "revision_id": rid,
                    "parent_type": "Product",
                    "parent_id": PRODUCT_ID,
                    "child_type": "Assembly",
                    "child_id": asm_id,
                    "row_no": 0,
                    "short_name": asm_id.split("/")[-1],
                    "raw_qty": "1",
                    "pack_size": 1,
                    "pack_basis": "derived",
                    "qty_each": "1",
                    "multiplier": 1,
                    "unit": "ea",
                    "origin": "derived",
                    "source_ref": "derived:assembly-membership",
                }
            )

    # 2) 전장 BOM — Digi-Key 주문서는 스냅샷 하나뿐이라 최신 판에만 붙인다
    elec_id = nz.assembly_id(PRODUCT_ID, ELECTRONICS)
    assemblies[elec_id] = {
        "assembly_id": elec_id,
        "product_id": PRODUCT_ID,
        "name": ELECTRONICS,
        "domain": "electrical",
        "origin": "source",
    }
    for row_no, row in enumerate(src.read_digikey_bom(), start=1):
        mpn = (row.get("Manufacturer Part Number") or "").strip()
        if not mpn:
            continue
        part_id = f"E-{mpn}"
        price = nz.parse_price(row.get("Unit Price") or "")
        items[part_id] = {
            "part_id": part_id,
            "sku": mpn,
            "name": (row.get("Description") or "").strip(),
            "aliases": {(row.get("Description") or "").strip().lower()},
            "domain": "electrical",
            "mpn": mpn,
            "pack_size": 1,
            "pack_basis": "none",
            "first_seen": latest,
            "last_seen": latest,
            "origin": "source",
            "supplier_id": "digikey.com",
            "supplier_sku": (row.get("Part Number") or "").strip(),
            "unit_price": price,
            "url": f"https://www.digikey.com/en/products/result?keywords={row.get('Part Number', '')}",
        }
        ebom.append(
            {
                "bomline_id": f"{latest}:{elec_id}:{part_id}",
                "revision_id": latest,
                "parent_type": "Assembly",
                "parent_id": elec_id,
                "child_type": "Part",
                "child_id": part_id,
                "row_no": row_no,
                "short_name": items[part_id]["name"][:40],
                "raw_qty": row["Quantity"].strip(),
                "pack_size": 1,
                "pack_basis": "none",
                "qty_each": row["Quantity"].strip(),
                "multiplier": 1,
                "unit": "ea",
                "unit_price": str(price) if price is not None else "",
                "price_observed_at": src.SNAPSHOT_DATE,
                "origin": "source",
                "source_ref": f"{src.DIGIKEY_BOM}@{src.SNAPSHOT_COMMIT}#row{row_no}",
            }
        )
    ebom.append(
        {
            "bomline_id": f"{latest}:{PRODUCT_ID}:{elec_id}",
            "revision_id": latest,
            "parent_type": "Product",
            "parent_id": PRODUCT_ID,
            "child_type": "Assembly",
            "child_id": elec_id,
            "row_no": 0,
            "short_name": ELECTRONICS,
            "raw_qty": "1",
            "pack_size": 1,
            "pack_basis": "derived",
            "qty_each": "1",
            "multiplier": 1,
            "unit": "ea",
            "origin": "derived",
            "source_ref": "derived:assembly-membership",
        }
    )

    # 문서에만 나오는 대체 후보 부품 (BOM 에는 없음)
    for p in virtual.DOC_ONLY_PARTS:
        items.setdefault(
            p["part_id"],
            {
                "part_id": p["part_id"],
                "sku": p["sku"],
                "name": p["name"],
                "aliases": set(p["aliases"].split("|")),
                "domain": "mechanical",
                "mpn": "",
                "pack_size": 1,
                "pack_basis": "none",
                "first_seen": "",
                "last_seen": "",
                "origin": "source:extra_parts.md",
            },
        )

    # 3) 변경 이력 — 연속한 판의 차이로 교육용 ECN · 대체 관계를 만든다
    ecns = ecn_mod.build_ecns(revisions, lines_by_revision)
    ecn_rows = [
        {
            "ecn_id": e.ecn_id,
            "revision_from": e.revision_from,
            "revision_to": e.revision_to,
            "ecn_date": e.ecn_date,
            "title": e.title,
            "line_count": len(e.lines),
            "reason": "커밋 메시지 기반 교육용 ECN (실제 승인 문서 아님)",
            "origin": "derived",
        }
        for e in ecns
    ]
    ecn_lines = [{"ecn_id": e.ecn_id, **ln} for e in ecns for ln in e.lines]
    supersedes = [{**s, "origin": "derived"} for e in ecns for s in e.supersedes]

    # 4) 공급 조건 — 원천 공급사(가격은 원천, MOQ · 리드타임은 가정)와 가상 공급사의 제안
    offers = []
    for item in items.values():
        if item["last_seen"] != latest or item.get("unit_price") is None:
            continue
        sid = item["supplier_id"]
        defaults = virtual.SOURCE_SUPPLIER_DEFAULTS.get(sid, {"moq_packs": 1, "lead_time_days": 7})
        offers.append(
            {
                "part_id": item["part_id"],
                "supplier_id": sid,
                "supplier_sku": item.get("supplier_sku") or item["sku"],
                "pack_size": item["pack_size"],
                "unit_price": str(item["unit_price"]),
                "currency": "USD",
                **defaults,
                "observed_at": src.SNAPSHOT_DATE,
                "price_date": "",
                "url": item.get("url", ""),
                "origin": "source",
                "terms_origin": "assumption",
            }
        )
    base_price = {o["part_id"]: Decimal(o["unit_price"]) for o in offers}
    for v in virtual.VIRTUAL_OFFERS:
        offers.append(
            {
                "part_id": v["part_id"],
                "supplier_id": v["supplier_id"],
                "supplier_sku": v["supplier_sku"],
                "pack_size": items[v["part_id"]]["pack_size"],
                "unit_price": str(
                    (base_price[v["part_id"]] * v["price_factor"]).quantize(Decimal("0.01"))
                ),
                "currency": "USD",
                "moq_packs": v["moq_packs"],
                "lead_time_days": v["lead_time_days"],
                "observed_at": src.SNAPSHOT_DATE,
                "price_date": "",
                "url": "",
                "origin": "virtual",
                "terms_origin": "virtual",
            }
        )

    # 5) 품질 — 문서 청크(README · 이슈)와 고장 모드
    documents = []
    for path, text in src.list_markdown_docs():
        documents.extend(chunk_markdown(path, text))
    for issue in src.read_issues():
        documents.append(chunk_issue(issue))
    documents.extend(_bom_text_chunks(src.read_csv_at(latest, src.PARTS_LIST), latest))
    for doc in documents:
        doc["origin"] = "source"

    # 6) 식별자 대응표 — 같은 부품을 가리키는 원천 식별자 · 별칭 · 공급사 품번
    offer_skus = defaultdict(set)
    for o in offers:
        offer_skus[o["part_id"]].add(f"{o['supplier_id']}:{o['supplier_sku']}")
    for item in items.values():
        item["aliases"] = "|".join(sorted(a for a in item["aliases"] if a))
        item["in_latest"] = item["last_seen"] == latest
    crosswalk = [
        {
            "part_id": i["part_id"],
            "sku": i["sku"],
            "mpn": i["mpn"],
            "aliases": i["aliases"],
            "supplier_skus": "|".join(sorted(offer_skus[i["part_id"]])),
        }
        for i in items.values()
    ]

    print("data/processed 생성")
    _write(
        "plm_revision",
        revisions,
        ["revision_id", "committed_at", "valid_from", "valid_to", "is_latest", "message", "origin"],
    )
    _write(
        "plm_assembly",
        list(assemblies.values()),
        ["assembly_id", "product_id", "name", "domain", "origin"],
    )
    _write(
        "plm_item_master",
        list(items.values()),
        [
            "part_id",
            "sku",
            "name",
            "aliases",
            "domain",
            "mpn",
            "pack_size",
            "pack_basis",
            "first_seen",
            "last_seen",
            "in_latest",
            "origin",
        ],
    )
    _write(
        "plm_ebom_line",
        ebom,
        [
            "bomline_id",
            "revision_id",
            "parent_type",
            "parent_id",
            "child_type",
            "child_id",
            "row_no",
            "short_name",
            "raw_qty",
            "pack_size",
            "pack_basis",
            "qty_each",
            "multiplier",
            "unit",
            "unit_price",
            "price_observed_at",
            "origin",
            "source_ref",
        ],
    )
    _write(
        "plm_ecn",
        ecn_rows,
        [
            "ecn_id",
            "revision_from",
            "revision_to",
            "ecn_date",
            "title",
            "line_count",
            "reason",
            "origin",
        ],
    )
    _write(
        "plm_ecn_line",
        ecn_lines,
        [
            "ecn_id",
            "change_type",
            "assembly_id",
            "part_id",
            "short_name",
            "before_raw_qty",
            "after_raw_qty",
            "before_multiplier",
            "after_multiplier",
        ],
    )
    _write(
        "plm_supersedes",
        supersedes,
        ["new_part_id", "old_part_id", "ecn_id", "assembly_id", "effective_date", "origin"],
    )
    _write(
        "plm_alternate",
        [{**a, "source_date": src.SNAPSHOT_DATE, "origin": "source"} for a in virtual.ALTERNATES],
        [
            "part_id",
            "alternate_part_id",
            "compatibility",
            "requires_rework",
            "source_doc",
            "source_section",
            "source_date",
            "origin",
            "pack_price",
            "pack_size",
            "price_note",
        ],
    )
    _write("erp_supplier", virtual.SUPPLIERS, ["supplier_id", "name", "origin"])
    _write(
        "erp_supplier_item",
        offers,
        [
            "part_id",
            "supplier_id",
            "supplier_sku",
            "pack_size",
            "unit_price",
            "currency",
            "moq_packs",
            "lead_time_days",
            "observed_at",
            "price_date",
            "url",
            "origin",
            "terms_origin",
        ],
    )
    _write(
        "erp_price_history",
        price_history,
        [
            "part_id",
            "supplier_id",
            "unit_price",
            "currency",
            "pack_size",
            "observed_at",
            "revision_id",
            "origin",
        ],
    )
    _write(
        "scenario_parameters",
        [{**s, "origin": "assumption"} for s in virtual.SCENARIO_PARAMETERS],
        ["scenario_id", "parameter", "value", "description", "origin"],
    )
    _write(
        "quality_document",
        documents,
        ["doc_id", "source", "path", "title", "line", "text", "origin"],
    )
    _write(
        "quality_failure_mode",
        [{**f, "origin": "derived"} for f in virtual.FAILURE_MODES],
        ["fm_id", "part_id", "severity", "name", "symptom", "doc_path", "doc_line", "origin"],
    )
    _write("crosswalk", crosswalk, ["part_id", "sku", "mpn", "aliases", "supplier_skus"])
    _write(
        "data_quality_issues",
        quality_issues,
        ["revision_id", "row_no", "short_name", "issue", "action"],
    )

    latest_mech = [
        ln
        for ln in ebom
        if ln["revision_id"] == latest
        and ln["parent_type"] == "Assembly"
        and not ln["parent_id"].endswith(ELECTRONICS)
    ]
    inventory = {
        "snapshot": {"commit": src.SNAPSHOT_COMMIT, "date": src.SNAPSHOT_DATE},
        "latest_revision": latest,
        "revisions": len(revisions),
        "ecns": len(ecns),
        "parts_total": len(items),
        "mechanical_lines_latest": len(latest_mech),
        "documents": {
            "readme_chunks": sum(d["source"] == "readme" for d in documents),
            "issues": sum(d["source"] == "issue" for d in documents),
        },
        "suppliers": {s["supplier_id"]: s["origin"] for s in virtual.SUPPLIERS},
    }
    (PROCESSED_DIR / "data_inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2)
    )
    print(
        f"  data_inventory.json   판 {inventory['revisions']}개 · ECN {inventory['ecns']}건 · 부품 {len(items)}종"
    )
    return inventory
