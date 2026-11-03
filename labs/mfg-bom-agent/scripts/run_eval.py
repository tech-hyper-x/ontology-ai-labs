"""Golden Set 으로 세 실행 방식을 채점하고 오류를 분석한다 (Part 2 Ch8).

    uv run python scripts/run_eval.py                         # 45문항 × 3방식
    uv run python scripts/run_eval.py --modes kg_tools        # 한 방식만
    uv run python scripts/run_eval.py --ids G01,G28 --modes kg_tools,rag
    uv run python scripts/run_eval.py --rescore outputs/eval/20261025-225054   # 저장된 답변을 새 규칙으로 다시 채점

결과: outputs/eval/<시각>/  results.csv · responses.jsonl · report.md · meta.json
기존 결과 폴더는 덮어쓰지 않는다 (다시 채점해도 새 폴더에 저장).
최종 답변 정답(answer_correct)과 도구 정답(tool_correct) · 보류(answerability)를 따로 집계한다.
Claude Haiku 5.5 호출 비용은 45문항 × 3방식 기준 약 $0.3 이하다 (Langfuse 에서 실제 비용 확인).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import yaml

from mfg_bom_agent.config import get_settings
from mfg_bom_agent.contracts.answer import AnswerRequest, AnswerResponse, RunContext
from mfg_bom_agent.evaluation.scoring import SCORING_VERSION, score
from mfg_bom_agent.workflows.bom_agent import run

ROOT = Path(__file__).resolve().parents[1]
MODES = ["kg_tools", "rag", "llm_only"]
# 보고서에 쓰는 이름 (내부 키 kg_tools 는 명령 옵션 · 결과 파일에만 쓴다)
MODE_NAMES = {"kg_tools": "지식 그래프 + 도구", "rag": "RAG", "llm_only": "LLM 단독"}


def one(item: dict, mode: str, tag: str) -> dict:
    req = AnswerRequest(
        run_id=f"eval-{tag}-{item['id']}-{mode}",
        question=item["question"],
        mode=mode,
        context=RunContext(role="평가", demo_mode=get_settings().demo_mode),
    )
    started = time.perf_counter()
    resp = run(req)
    return row(item, mode, resp, round(time.perf_counter() - started, 1))


def row(item: dict, mode: str, resp: AnswerResponse, seconds: float | None) -> dict:
    """채점 결과 한 줄. 정답 채점과 출력 검사 판정 · 보류 여부를 따로 남긴다."""
    result = score(item, resp)
    return {
        "id": item["id"],
        "category": item["category"],
        "mode": mode,
        "question": item["question"],
        "passed": result["passed"],
        "answer_correct": result["answer_correct"],
        "tool_correct": result["tool_correct"],
        "evidence_correct": result["evidence_correct"],
        "answerability": result["answerability"],
        "precision": result["precision"],
        "recall": result["recall"],
        "reason": result["reason"],
        "detail": result["detail"],
        "verification": resp.verification.status,
        "scoring_version": result["scoring_version"],
        "tool_calls": resp.tool_calls,
        "intent": resp.intent,
        "seconds": seconds,
        "conclusion": resp.conclusion,
        "_response": resp.model_dump(mode="json"),
    }


def report(rows: list[dict], out: Path, meta: dict | None = None) -> str:
    cats = sorted(
        {r["category"] for r in rows},
        key=lambda c: ["수량", "원가", "관계 탐색", "Revision · ECN", "문서 근거"].index(c),
    )
    modes = [m for m in MODES if any(r["mode"] == m for r in rows)]
    acc = defaultdict(lambda: [0, 0])
    for r in rows:
        acc[(r["category"], r["mode"])][1] += 1
        acc[(r["category"], r["mode"])][0] += r["passed"]
        acc[("전체", r["mode"])][1] += 1
        acc[("전체", r["mode"])][0] += r["passed"]
    lines = [
        "# Golden Set 평가 결과",
        "",
        f"- 실행: {out.name} · 문항 {len({r['id'] for r in rows})}개 · 방식 {', '.join(MODE_NAMES[m] for m in modes)}",
        (
            f"- 채점 규칙 v{SCORING_VERSION}: 최종 답변 기준 (단위 · 증감 방향 · 집합 정확 일치). "
            "v1(숫자 크기 · 텍스트 포함) 결과와 직접 비교하지 않는다"
        ),
    ]
    if meta:
        lines += [
            "- 실행 조건: "
            + " · ".join(f"{k} {v}" for k, v in meta.items() if k != "scoring_version")
        ]
    lines += [
        "",
        "범주별 최종 답변 정답 (answer_correct)",
        "",
        "| 범주 | " + " | ".join(MODE_NAMES[m] for m in modes) + " |",
        "|---|" + "---|" * len(modes),
    ]
    for c in cats + ["전체"]:
        cells = [
            f"{acc[(c, m)][0]}/{acc[(c, m)][1]} ({acc[(c, m)][0] / max(1, acc[(c, m)][1]):.0%})"
            for m in modes
        ]
        lines.append(f"| {c} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "| 지표 | " + " | ".join(MODE_NAMES[m] for m in modes) + " |",
        "|---|" + "---|" * len(modes),
    ]
    for name, key, val in (
        ("최종 답변 정답", "answer_correct", True),
        ("도구 · 검색 결과 정답", "tool_correct", True),  # RAG 는 문서 문항의 검색 근거만 센다
        ("답변함", "answerability", "answered"),
        ("보류(근거 부족)", "answerability", "abstained"),
        ("되묻기", "answerability", "needs_input"),
        ("실행 실패", "answerability", "failed"),
    ):
        cells = []
        for m in modes:
            rs = [r for r in rows if r["mode"] == m and r[key] is not None]
            cells.append(
                f"{sum(r[key] == val for r in rs)}/{len(rs)}" if rs else "—"
            )  # 분모를 숨기지 않는다
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    kg = [r for r in rows if r["mode"] == "kg_tools"]
    if kg:
        v = defaultdict(int)
        for r in kg:
            v[r["verification"]] += 1
        lines += [
            "",
            "지식 그래프 + 도구 출력 검사: " + ", ".join(f"{k} {n}" for k, n in v.items()),
        ]
    lines += [
        "",
        "## 실패 사례 (오류 분석용)",
        "",
        "| 문항 | 방식 | 원인 | 내용 |",
        "|---|---|---|---|",
    ]
    for r in rows:
        if not r["passed"]:
            lines.append(
                f"| {r['id']} {r['question'][:40]} | {MODE_NAMES[r['mode']]} | {r['reason']} | {r['detail'][:120]} |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--ids", default="")
    ap.add_argument("--concurrency", type=int, default=get_settings().max_concurrency)
    ap.add_argument(
        "--rescore", default="", help="저장된 결과 폴더의 responses.jsonl 을 새 규칙으로 다시 채점"
    )
    args = ap.parse_args()
    golden = yaml.safe_load(
        (ROOT / "data" / "golden" / "golden_set.yaml").read_text(encoding="utf-8")
    )
    items = golden["items"]
    if args.ids:
        wanted = set(args.ids.split(","))
        items = [i for i in items if i["id"] in wanted]
    modes = args.modes.split(",")
    tag = datetime.now().strftime("%Y%m%d-%H%M%S")
    s = get_settings()
    meta = {
        "scoring_version": SCORING_VERSION,
        "golden_version": golden.get("version"),
        "demo_mode": s.demo_mode,
        "llm_model": RunContext().llm_model,
        "embedding_provider": s.embedding_provider,
        "git_commit": _git_commit(),
    }
    if args.rescore:
        src = (
            (ROOT / args.rescore).resolve()
            if not Path(args.rescore).is_absolute()
            else Path(args.rescore)
        )
        tag += f"-rescore-{src.name}"
        meta |= {
            "rescored_from": src.name,
            "note": "저장된 답변을 다시 채점 (LLM · 도구 재실행 없음)",
        }
    out = ROOT / "outputs" / "eval" / tag
    out.mkdir(parents=True, exist_ok=False)  # 기존 결과를 덮어쓰지 않는다
    rows = []
    if args.rescore:
        by_id = {i["id"]: i for i in items}
        for line in (src / "responses.jsonl").read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec["id"] in by_id and rec["mode"] in modes:
                rows.append(
                    row(by_id[rec["id"]], rec["mode"], AnswerResponse(**rec["response"]), None)
                )
        print(f"다시 채점: {src.name} → {len(rows)}건")
    else:
        jobs = [(i, m) for i in items for m in modes]
        print(
            f"Golden Set {len(items)}문항 × {len(modes)}방식 = {len(jobs)}회 실행 (동시 {args.concurrency})"
        )
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            for n, r in enumerate(pool.map(lambda j: one(j[0], j[1], tag), jobs), start=1):
                rows.append(r)
                print(
                    f"  [{n:3}/{len(jobs)}] {r['id']} {r['mode']:9} {'O' if r['passed'] else 'X'} {r['reason']}"
                )
    rows.sort(key=lambda r: (r["id"], MODES.index(r["mode"])))
    with (out / "results.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=[k for k in rows[0] if not k.startswith("_")], extrasaction="ignore"
        )
        w.writeheader()
        w.writerows(rows)
    with (out / "responses.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(
                json.dumps(
                    {"id": r["id"], "mode": r["mode"], "response": r["_response"]},
                    ensure_ascii=False,
                )
                + "\n"
            )
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    text = report(rows, out, meta)
    (out / "report.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"결과 저장: {out.relative_to(ROOT)}")
    return 0


def _git_commit() -> str:
    """평가한 코드 버전 (커밋 + 작업 중 변경 여부)."""
    import subprocess

    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()
        return sha + ("+변경" if dirty else "")
    except OSError:
        return "unknown"


if __name__ == "__main__":
    sys.exit(main())
