"""화면 예시(DEMO_MODE=canned)용 응답을 만든다 (docs/UI_DESIGN.md 7절).

    uv run python scripts/make_canned.py      →  data/golden/canned/Q1.json … Q7.json

예시 질문 7개를 실제로(지식 그래프 + 도구, Claude) 한 번 실행해 응답과 단계 기록을 저장한다.
canned 모드는 이 파일을 보여 줄 뿐 실제로 실행하지 않으므로, 화면에 "화면 예시 · 실제 실행 아님"으로 표시된다.
API 키 · Neo4j 가 없는 환경에서 화면 구성을 먼저 보여 줄 때 쓴다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from mfg_bom_agent.contracts.answer import AnswerRequest
from mfg_bom_agent.workflows.bom_agent import run

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "golden" / "canned"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    examples = yaml.safe_load(
        (ROOT / "data" / "golden" / "examples.yaml").read_text(encoding="utf-8")
    )
    for ex in examples["examples"]:
        events: list = []
        resp = run(
            AnswerRequest(run_id=f"canned-{ex['id']}", question=ex["question"]), events.append
        )
        steps = [
            {
                "step": e.tool if e.type == "tool_finished" else e.step,
                "detail": getattr(e, "summary", "") or getattr(e, "detail", ""),
            }
            for e in events
            if e.type in ("tool_finished", "step")
        ]
        data = {
            "question": ex["question"],
            "response": resp.model_dump(mode="json"),
            "events": steps,
        }
        (OUT / f"{ex['id']}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(
            f"{ex['id']} {resp.status} · 검사 {resp.verification.status} · 도구 {resp.tool_calls}회"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
