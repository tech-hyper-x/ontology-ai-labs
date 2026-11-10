"""수강생 오류 수정 과제 확인기 — data/exercises/<과제>/ 의 시작본 · 작업본을 검사한다 (실행 계획서 W8, HANDS_ON.md).

    uv run python scripts/check_exercise.py alias          # P3 Ch2-2 HER1/EGFR 별칭 정리
    uv run python scripts/check_exercise.py from_source    # P3 Ch4-1 출처(FROM_SOURCE) 누락
    uv run python scripts/check_exercise.py met_context    # P3 Ch5-1 met / MET 문맥 연결
    uv run python scripts/check_exercise.py report_review  # P3 Ch7-2 인용 · 수치 검토
    uv run python scripts/check_exercise.py semantic       # P3 Ch5-2 · Ch8-1 CLM-006 의미 판정 기록
    --start  를 붙이면 작업본(work.*)이 있어도 시작본을 검사한다 (시작 상태가 실패하는지 확인)

작업본이 있으면 작업본을, 없으면 시작본을 검사한다. DB · LLM · 실행 중인 서버를 쓰지 않는다 (메모리 안에서만 확인).
통과하면 0, 실패하면 1 로 끝난다. 복구: 작업본을 지우면 시작본 상태로 돌아간다.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "data" / "exercises"
FOLDER = {"alias": "alias_her1", "from_source": "from_source", "met_context": "met_context",
          "report_review": "report_review", "semantic": "semantic_clm006"}


def _pick(folder: Path, start_only: bool) -> Path:
    """작업본(work.*) → 없으면 시작본(start.*)."""
    start = next(folder.glob("start.*"))
    work = folder / f"work{start.suffix}"
    return start if start_only or not work.exists() else work


def check_alias(path: Path) -> list[str]:
    """사내 과제 표기 → 표준 심볼. build.py 와 같이 별칭 사전으로만 확정하고, 못 찾으면 연결하지 않는다."""
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    got = {p["project_id"]: d["aliases"].get(p["target_symbol"]) for p in d["projects"]}
    errors = [f"{pid}: {got[pid] or '확정 실패 (검토 목록으로 빠짐)'} ≠ 정답 {exp}" for pid, exp in d["expected"].items() if got.get(pid) != exp]
    print("  연결 결과:", got)
    return errors


def check_from_source(path: Path) -> list[str]:
    """근거마다 FROM_SOURCE 가 정확히 1개이고, 그 출처가 sources 에 있어야 한다 (ontology.py cardinality:Evidence.Source)."""
    d = json.loads(path.read_text(encoding="utf-8"))
    sources = {s["source_id"] for s in d["sources"]}
    errors = []
    for e in d["evidence"]:
        links = [r["source"] for r in d["from_source"] if r["evidence"] == e["evidence_id"]]
        if len(links) != 1:
            errors.append(f"{e['evidence_id']}: FROM_SOURCE {len(links)}개 (정확히 1개여야 함)")
        elif links[0] not in sources:
            errors.append(f"{e['evidence_id']}: 없는 출처 {links[0]}")
        elif not links[0].startswith(e["datasource"] + "@"):
            errors.append(f"{e['evidence_id']}: datasource {e['datasource']} 와 출처 {links[0]} 가 다름")
    return errors


def check_met_context(path: Path) -> list[str]:
    """실제 연결 규칙(_link_genes)으로 문장마다 MET 연결 여부를 구하고, overrides 를 적용해 사람 정답(gold)과 비교한다."""
    from bio_target_agent.foundation.build import _link_genes

    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    aliases = {"MET": "MET", "c-Met": "MET", "HGFR": "MET", "EGFR": "EGFR"}
    removed = {o["id"] for o in d.get("overrides") or [] if o.get("remove") == "MET"}
    errors = []
    for s in d["sentences"]:
        links = [m for m in _link_genes(s["text"], aliases) if m["symbol"] == "MET"]
        linked = bool(links) and s["id"] not in removed
        mark = "연결" if linked else "연결 안 함"
        print(f"  {s['id']}: {mark}{' (교정)' if s['id'] in removed else ''} · 정답 {'MET' if s['gold'] else '아님'} — {s['text']}")
        if linked != s["gold"]:
            errors.append(f"{s['id']}: 규칙은 '{mark}', 사람 정답은 '{'MET' if s['gold'] else '영어 단어'}'")
    return errors


def check_report_review(path: Path) -> list[str]:
    """workflows/report.py 의 review 를 그대로 돌린다 (근거 경로 도구는 부르지 않는 입력)."""
    from bio_target_agent.contracts.tools import TargetScore
    from bio_target_agent.workflows import report as rp

    class _NoGateway:
        def call(self, tool, **kw):
            raise RuntimeError("이 과제는 근거 ID 를 쓰지 않는다 (정책 점수 참조만)")

    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    ranking = [TargetScore(**r) for r in d["ranking"]]
    _, refs = rp.facts_payload("과제", "compare", [], ranking, [], {"policy": "v1"})
    draft = rp.ReportDraft(headline=d["headline"], findings=[rp.ClaimDraft(**f) for f in d["findings"]])
    claims, rv = rp.review(_NoGateway(), draft, refs, [], ranking, [], policy="v1")
    for c in claims:
        print(f"  {c.claim_id} [{c.status}] {c.text}" + (f" — {c.issue_codes} {c.reason}" if c.status != "verified" else ""))
    errors = [f"{i.where}: [{i.code}] {i.message}" for i in rv.issues]
    print(f"  검토 상태: {rv.status} · 확인 {rv.verified}")
    if rv.status != "passed" and not errors:
        errors.append(f"검토 상태 {rv.status}")
    return errors


def check_semantic(path: Path) -> list[str]:
    """사람 의미 판정 행이 다 채워졌는지 (라벨 · 원문 구간 · 이유 · 판정자 · 날짜). 내용의 옳고 그름은 강사가 확인한다."""
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    errors = []
    for r in rows:
        if r["semantic_label"] not in ("supported", "mismatch", "insufficient"):
            errors.append(f"{r['claim_id']}: 의미 판정이 비어 있음 ({r['semantic_label']}) — supported · mismatch · insufficient 중 하나")
        for col in ("source_span", "reason", "reviewer", "reviewed_at"):
            if not (r.get(col) or "").strip():
                errors.append(f"{r['claim_id']}: {col} 를 채우세요")
    return errors


CHECKS = {"alias": check_alias, "from_source": check_from_source, "met_context": check_met_context,
          "report_review": check_report_review, "semantic": check_semantic}


def main() -> int:
    ap = argparse.ArgumentParser(description="수강생 오류 수정 과제 확인")
    ap.add_argument("exercise", choices=sorted(CHECKS))
    ap.add_argument("--start", action="store_true", help="작업본이 있어도 시작본을 검사")
    args = ap.parse_args()
    path = _pick(EX / FOLDER[args.exercise], args.start)
    print(f"[{args.exercise}] {path.relative_to(ROOT)}")
    errors = CHECKS[args.exercise](path)
    if errors:
        print("FAIL")
        for e in errors:
            print("  -", e)
        if path.name.startswith("start"):
            print(f"  → 시작본을 복사해 고치세요: cp {path.relative_to(ROOT)} {path.with_name('work' + path.suffix).relative_to(ROOT)}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
