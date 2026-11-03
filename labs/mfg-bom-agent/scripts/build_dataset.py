"""원천(data/raw) → 교육용 테이블(data/processed) 을 만든다 (Part 2 Ch2 · Ch3).

    uv run python scripts/build_dataset.py

원천이 없으면(data/raw/SOURCES.md 의 내려받기를 안 했으면) 실패한다.
수강생 배포판에는 data/processed 가 이미 들어 있으므로 이 스크립트는 강사 · 데이터 갱신용이다.
"""

from __future__ import annotations

import sys

from mfg_bom_agent.foundation.build import build


def main() -> int:
    inventory = build()
    print(
        f"완료: 최신 판 {inventory['latest_revision']} · 스냅샷 {inventory['snapshot']['commit']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
