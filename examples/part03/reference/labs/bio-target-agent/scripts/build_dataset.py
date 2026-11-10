"""Data Foundation: 원천 스냅샷 수집(선택) → 사내 가상 데이터 생성 → 정규화 (설계 덱 06~12장 · 26~28장).

    uv run python scripts/build_dataset.py            # 저장된 스냅샷(data/raw)으로 정규화만
    uv run python scripts/build_dataset.py --fetch    # 공개 API 에서 스냅샷을 다시 받은 뒤 정규화

결과: data/processed/graph/*.json · crosswalk.csv · review_queue.json · data_inventory.json
"""

from __future__ import annotations

import argparse
import json
import sys

from bio_target_agent.foundation.build import build
from bio_target_agent.foundation.internal import build_internal
from bio_target_agent.foundation.sources import fetch_all


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="Open Targets · PubMed · ChEMBL · PubChem 스냅샷을 다시 받는다")
    ap.add_argument("--refresh-pubmed", action="store_true", help="초록도 새로 받는다 (설계 덱 30장 예시와 달라질 수 있음)")
    args = ap.parse_args()
    if args.fetch:
        print("fetch  ", fetch_all(refresh_pubmed=args.refresh_pubmed))
    print("internal", build_internal())
    inv = build()
    print("build  ", json.dumps(inv, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
