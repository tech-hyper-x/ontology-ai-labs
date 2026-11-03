"""원천 파일을 읽는 함수 모음 (Part 2 Ch1-2 공개 데이터와 교육용 재구성 데이터).

원천은 data/raw/SOURCES.md 의 명령으로 받은 NASA OSR 저장소(git 스냅샷)와 GitHub 이슈 덤프다.
이 모듈은 파일을 "있는 그대로" 읽기만 하고, 단위 변환이나 식별자 정리는 normalize.py 가 맡는다.
원천을 고치지 않고 읽기만 해야 같은 스냅샷에서 언제나 같은 결과가 나온다.

주의: 내려받은 저장소 안의 스크립트는 실행하지 않는다. git 명령으로 파일 내용만 꺼낸다.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OSR_DIR = RAW_DIR / "nasa-osr"
ISSUES_JSON = RAW_DIR / "nasa-osr-github" / "issues.json"

# 실습이 기준으로 삼는 저장소 스냅샷. SOURCES.md 에 기록된 커밋과 같아야 한다.
SNAPSHOT_COMMIT = "a78f9eb"
SNAPSHOT_DATE = "2026-10-22"

PARTS_LIST = "parts_list/parts_list.csv"
DIGIKEY_BOM = "parts_list/digikey_bom.csv"
EXTRA_PARTS = "parts_list/extra_parts.md"


@dataclass(frozen=True)
class RawRevision:
    """parts_list.csv 를 바꾼 커밋 하나. 교육용 BOM 판(Revision)의 원재료다."""

    commit: str  # 짧은 해시 (7자리)
    committed_at: str  # ISO 날짜 YYYY-MM-DD
    message: str
    content_hash: str  # 파일 내용 해시. 내용이 같은 merge 커밋을 걸러내는 데 쓴다


def _git(*args: str) -> str:
    """원천 저장소에서 git 명령을 실행해 표준 출력을 돌려준다."""
    if not (OSR_DIR / ".git").exists():
        raise FileNotFoundError(
            f"원천 저장소가 없습니다: {OSR_DIR}\ndata/raw/SOURCES.md 의 명령으로 먼저 내려받으세요."
        )
    result = subprocess.run(
        ["git", "-C", str(OSR_DIR), *args], capture_output=True, text=True, check=True
    )
    return result.stdout


def read_file_at(commit: str, path: str) -> str:
    """특정 커밋 시점의 파일 내용을 읽는다. 작업 트리가 아니라 git 객체에서 꺼낸다."""
    text = _git("show", f"{commit}:{path}")
    return text.lstrip("﻿")  # 일부 CSV 앞의 BOM(바이트 순서 표시)을 떼어 낸다


def read_csv_at(commit: str, path: str) -> list[dict[str, str]]:
    """특정 커밋의 CSV 를 행 목록으로 읽는다. 열 이름은 원천 그대로 둔다 (끝 공백 포함)."""
    return list(csv.DictReader(io.StringIO(read_file_at(commit, path))))


def _first_parent_log(start: str) -> list[tuple[str, str, str, list[str]]]:
    """start 에서 첫 번째 부모만 따라간 parts_list.csv 변경 커밋을 오래된 순서로 돌려준다."""
    out = _git(
        "log", "--first-parent", "--reverse", "--format=%h|%cs|%p|%s", start, "--", PARTS_LIST
    )
    rows = []
    for line in out.strip().splitlines():
        commit, date, parents, message = line.split("|", 3)
        rows.append((commit, date, message.strip(), parents.split()))
    return rows


def _branch_subjects(merge_commit: str) -> list[str]:
    """merge 커밋이 가져온 브랜치 커밋들의 제목. ECN 제목을 사람이 읽을 수 있게 만드는 데 쓴다."""
    out = _git(
        "log", "--reverse", "--format=%s", f"{merge_commit}^1..{merge_commit}^2", "--", PARTS_LIST
    )
    return [s.strip() for s in out.strip().splitlines() if s.strip()]


def list_parts_revisions() -> list[RawRevision]:
    """parts_list.csv 의 "릴리스 이력"을 오래된 순서로 돌려준다.

    저장소 이력은 브랜치가 갈라졌다 합쳐지는 그래프라서, 커밋을 날짜순으로 줄 세우면
    서로 다른 브랜치의 판이 번갈아 나와 "바퀴가 바뀌었다 되돌아갔다" 같은 가짜 변경이 생긴다.
    그래서 메인 라인(첫 번째 부모)만 판으로 본다. PR 브랜치의 중간 커밋은 검토 중인 설계안이고,
    merge 커밋이 그 변경을 승인 · 반영한 시점이다 (PLM 의 ECN 승인과 같은 의미로 쓴다).

    예외: parts_list.csv 는 v2 브랜치에서 처음 만들어져 merge(85078c2)로 메인에 들어왔다.
    메인 라인의 첫 판이 이런 merge 라면, 파일을 만든 브랜치의 첫 번째 부모 이력을 앞에 붙인다.

    바로 앞 판과 내용이 똑같은 커밋은 제외한다. 같은 내용의 판이 둘이면 적용 구간이 모호해진다.
    """
    main = _first_parent_log(SNAPSHOT_COMMIT)
    first_commit, _, _, first_parents = main[0]
    if len(first_parents) == 2:
        try:
            read_file_at(first_parents[0], PARTS_LIST)
        except (
            subprocess.CalledProcessError
        ):  # 메인 쪽 부모에는 파일이 없다 → 브랜치에서 만들어진 파일
            main = _first_parent_log(f"{first_commit}^2") + main

    revisions: list[RawRevision] = []
    previous_hash = None
    for commit, date, message, parents in main:
        digest = hashlib.sha1(read_file_at(commit, PARTS_LIST).encode()).hexdigest()[:12]
        if digest == previous_hash:
            continue
        if len(parents) == 2:  # merge 커밋이면 브랜치에서 한 일을 제목 뒤에 붙인다
            message = f"{message} — " + "; ".join(_branch_subjects(commit))
        revisions.append(RawRevision(commit, date, message, digest))
        previous_hash = digest
    return revisions


def read_digikey_bom() -> list[dict[str, str]]:
    """전장 부품 주문서(Digi-Key)를 스냅샷 기준으로 읽는다."""
    return read_csv_at(SNAPSHOT_COMMIT, DIGIKEY_BOM)


def list_markdown_docs() -> list[tuple[str, str]]:
    """스냅샷의 Markdown 문서를 (경로, 본문) 목록으로 돌려준다. 정비 · 조립 문서의 원천이다."""
    paths = _git("ls-tree", "-r", "--name-only", SNAPSHOT_COMMIT).splitlines()
    docs = []
    for path in sorted(paths):
        # .github 아래 기여 안내 문서는 정비 · 조립 내용이 아니어서 뺀다.
        if path.lower().endswith(".md") and not path.startswith(".github/"):
            docs.append((path, read_file_at(SNAPSHOT_COMMIT, path)))
    return docs


def read_issues() -> list[dict]:
    """GitHub 이슈 덤프를 읽어 PR 을 뺀 이슈만 돌려준다. 현장 이슈 · 증상 문서의 원천이다."""
    if not ISSUES_JSON.exists():
        raise FileNotFoundError(f"이슈 덤프가 없습니다: {ISSUES_JSON} (SOURCES.md 참고)")
    items = json.loads(ISSUES_JSON.read_text(encoding="utf-8"))["items"]
    return [item for item in items if not item["is_pull_request"]]
