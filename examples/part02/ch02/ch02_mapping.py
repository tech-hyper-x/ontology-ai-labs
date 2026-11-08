"""Ch2 한 행 매핑 관찰. 제조 프로젝트 루트에서 uv run python ../../examples/part02/ch02/ch02_mapping.py.
현재 작업본의 매핑 함수를 호출하며 파일·DB를 변경하지 않습니다.
"""
from pathlib import Path
import csv
import json
from mfg_bom_agent.foundation.normalize import map_parts_row, supplier_from_url

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "docs/part02/ch01/reference/parts_list/parts_list.csv"
DATA = ROOT / "labs/mfg-bom-agent/data/processed"

def read(name):
    with (DATA / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def main():
    with RAW.open(encoding="utf-8", newline="") as f:
        raw = next(r for r in csv.DictReader(f) if r["part #"] == "3616-0014-0144")
    common = map_parts_row(raw)
    part = next(r for r in read("plm_item_master.csv") if r["sku"] == common["sku"])
    crosswalk = next(r for r in read("crosswalk.csv") if r["part_id"] == part["part_id"])
    offers = [r for r in read("erp_supplier_item.csv") if r["part_id"] == part["part_id"]]
    assert common["raw_qty"] == "1" and common["multiplier"] == "6"
    assert crosswalk["sku"] == common["sku"]
    result = {"raw": raw, "common": common, "supplier_from_url": supplier_from_url(common["url"]),
              "identity": {"part_id": part["part_id"], "sku": part["sku"], "mpn": part["mpn"],
                           "aliases": crosswalk["aliases"], "supplier_skus": crosswalk["supplier_skus"]},
              "offers": [{k: o[k] for k in ["supplier_id", "supplier_sku", "unit_price", "pack_size", "origin", "terms_origin"]} for o in offers]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("확인: 같은 휠의 원본 SKU와 내부 ID 대응 일치")

if __name__ == "__main__":
    main()
