"""복사한 실제 런타임에서 G01 분류·계산 경로를 고치고 로컬 MCP로 회귀 확인."""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[3] / "labs/mfg-bom-agent"
IDS = "G01,G02,G03,G04,G05,G06,G07,G08,G09,G10,G16,G30"


def prepare(workspace: Path) -> None:
    if workspace.exists():
        raise SystemExit(
            "이미 있는 폴더는 덮어쓰지 않습니다. 새 실습 폴더를 지정하세요."
        )
    if LAB.resolve() == workspace or LAB.resolve() in workspace.parents:
        raise SystemExit("원본 프로젝트 밖의 새 폴더를 지정하세요.")
    workspace.mkdir(parents=True)
    for relative in [
        "src",
        "skills",
        "ontology",
        "data/golden",
        "data/processed",
        "scripts",
    ]:
        shutil.copytree(
            LAB / relative,
            workspace / relative,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    for filename in ["pyproject.toml", "uv.lock"]:
        shutil.copy2(LAB / filename, workspace / filename)
    plan = workspace / "src/mfg_bom_agent/workflows/plan.py"
    code = plan.read_text()
    pattern = r'(intent="required_quantity",\s*part_terms=parts,\s*units=)units'
    code, count = re.subn(
        pattern,
        lambda m: (
            "# TODO: 총소요량 유형과 생산 대수를 보존하세요.\n            "
            + m[1].replace('intent="required_quantity"', 'intent="part_info"')
            + "None"
        ),
        code,
    )
    if count != 1:
        raise SystemExit("배포 코드가 바뀌었습니다. 연습 템플릿과 버전을 확인하세요.")
    plan.write_text(code)
    route = workspace / "src/mfg_bom_agent/workflows/skills.py"
    code = route.read_text()
    start = code.index('    elif plan.intent == "required_quantity":')
    end = code.index('    elif plan.intent == "purchase_quantity":', start)
    route.write_text(
        code[:start] + '    elif plan.intent == "required_quantity":\n'
        "        # TODO: 사용처·BOM 전개 → 모든 투입 내역 합산 → CalcResult\n"
        '        raise NotImplementedError("총소요량 경로를 작성하세요")\n\n'
        + code[end:]
    )
    print("준비:", workspace)
    print("수정할 실제 모듈:", plan, route, sep="\n")
    print(
        "원본·DB·Golden Set은 변경하지 않았습니다. .env와 API 키도 복사하지 않습니다."
    )


def check(workspace: Path, mcp_url: str) -> None:
    if not (workspace / "scripts/run_eval.py").is_file():
        raise SystemExit("prepare로 만든 실습 폴더를 지정하세요.")
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("ANTHROPIC_", "EMBEDDING_", "LANGFUSE_", "NEO4J_"))
    }
    env.update(
        PYTHONPATH=str(workspace / "src"),
        PYTHONDONTWRITEBYTECODE="1",
        DEMO_MODE="fixed_llm",
        MCP_TRANSPORT="http",
        MCP_URL=mcp_url,
    )
    outputs = workspace / "outputs/eval"
    before = set(outputs.glob("*"))
    result = subprocess.run(
        [sys.executable, "scripts/run_eval.py", "--ids", IDS, "--modes", "kg_tools"],
        cwd=workspace,
        env=env,
        check=False,
    )
    if result.returncode:
        raise SystemExit(result.returncode)
    created = set(outputs.glob("*")) - before
    if len(created) != 1:
        raise SystemExit("이번 실행의 결과 폴더를 확인하세요.")
    folder = created.pop()
    with (folder / "results.csv").open() as f:
        rows = list(csv.DictReader(f))
    failed = [
        r["id"]
        for r in rows
        if any(
            str(r.get(k)).lower() != "true" for k in ["tool_correct", "answer_correct"]
        )
    ]
    if len(rows) != 12 or failed:
        raise SystemExit(
            f"미통과: {failed}; 실제 결과 {folder}. 기대 답을 바꾸지 말고 분류·호출 경로를 확인하세요."
        )
    print(
        "통과: 실제 도구·답변 12/12. 고정 모드의 회귀 확인이며 실제 모델 전체 성능 평가가 아닙니다."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "check"])
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--mcp-url", default="http://localhost:8000/mcp")
    args = parser.parse_args()
    workspace = args.workspace.expanduser().resolve()
    if args.action == "prepare":
        prepare(workspace)
    else:
        check(workspace, args.mcp_url)


if __name__ == "__main__":
    main()
