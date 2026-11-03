"""git 이력 → 교육용 BOM 판(Revision)과 변경 통지(ECN) (Part 2 Ch3-1 BOM 변경 사례 모델링).

원천에는 "ECN 문서"가 없다. 있는 것은 parts_list.csv 를 바꾼 커밋들뿐이다.
그래서 커밋 하나를 BOM 판 하나로 보고, 바로 앞 판과 비교한 차이를 교육용 ECN 으로 만든다.

- Revision: 커밋 해시가 ID, 커밋일이 적용 시작일, 다음 판 커밋일이 적용 종료일(미포함)
- ECN     : 연속한 두 판의 차이(추가 · 삭제 · 수량 변경 라인)
- SUPERSEDES: 같은 ECN · 같은 어셈블리에서 같은 역할(short name)의 부품이 빠지고 새로 들어오면
              "새 부품이 이전 부품을 대체했다"로 본다 (예: 2023-07-18 모터 5202 → 5203)

주의: 커밋일은 저장소에 반영된 날이지 실제 생산 적용일이 아니다. 화면과 답변에서 "저장소상 적용 구간"으로 부른다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from itertools import pairwise


@dataclass
class LineKey:
    """판과 판을 비교할 때 같은 라인으로 보는 기준: 어셈블리 + 부품."""

    assembly_id: str
    part_id: str

    def as_tuple(self) -> tuple[str, str]:
        return (self.assembly_id, self.part_id)


@dataclass
class EcnRecord:
    ecn_id: str
    revision_from: str
    revision_to: str
    ecn_date: str
    title: str
    lines: list[dict] = field(default_factory=list)
    supersedes: list[dict] = field(default_factory=list)


# ─── [Hands-on P2-Ch3-1 BOM 변경 사례 모델링] 시작 ───
def revision_intervals(revisions: list[tuple[str, str]]) -> list[dict]:
    """(커밋, 커밋일) 목록에서 판별 적용 구간을 만든다. 마지막 판은 종료일이 없다(현재 유효).

    구간은 [시작, 종료) — 시작일은 포함, 종료일은 포함하지 않는다. 같은 날 두 판이 있으면
    뒤 판이 그날부터 유효하다.
    """
    rows = []
    for i, (commit, date) in enumerate(revisions):
        valid_to = revisions[i + 1][1] if i + 1 < len(revisions) else ""
        rows.append(
            {
                "revision_id": commit,
                "valid_from": date,
                "valid_to": valid_to,
                "is_latest": i == len(revisions) - 1,
            }
        )
    return rows


def diff_revisions(
    before: dict[tuple[str, str], dict],
    after: dict[tuple[str, str], dict],
) -> list[dict]:
    """두 판의 BOM 라인을 비교해 추가 · 삭제 · 수량 변경 라인을 돌려준다.

    before/after: {(assembly_id, part_id): 라인 정보} — 라인 정보에는 raw_qty, multiplier, short_name 이 있다.
    단가 변경은 BOM 구조 변경이 아니므로 ECN 에 넣지 않는다 (가격 이력은 ERP 쪽에서 따로 관리).
    """
    changes = []
    for key in sorted(set(before) | set(after)):
        b, a = before.get(key), after.get(key)
        if b and not a:
            kind = "removed"
        elif a and not b:
            kind = "added"
        elif (Decimal(b["raw_qty"]), b["multiplier"]) != (Decimal(a["raw_qty"]), a["multiplier"]):
            kind = "qty_changed"
        else:
            continue
        changes.append(
            {
                "change_type": kind,
                "assembly_id": key[0],
                "part_id": key[1],
                "short_name": (a or b)["short_name"],
                "before_raw_qty": b["raw_qty"] if b else "",
                "after_raw_qty": a["raw_qty"] if a else "",
                "before_multiplier": b["multiplier"] if b else "",
                "after_multiplier": a["multiplier"] if a else "",
            }
        )
    return changes


def pair_supersedes(changes: list[dict]) -> list[dict]:
    """같은 어셈블리에서 같은 역할(short name)의 부품이 빠지고 들어온 쌍을 대체 관계로 묶는다.

    short name 이 다르면(예: "D-Hub clamp" → "REX bore hub") 자동으로 묶지 않는다.
    억지로 묶으면 틀린 대체 관계가 그래프에 들어가므로, 확실한 경우만 남긴다.
    """
    removed = {
        (c["assembly_id"], c["short_name"].lower()): c
        for c in changes
        if c["change_type"] == "removed"
    }
    pairs = []
    for c in changes:
        if c["change_type"] != "added":
            continue
        old = removed.get((c["assembly_id"], c["short_name"].lower()))
        if old and old["part_id"] != c["part_id"]:
            pairs.append(
                {
                    "new_part_id": c["part_id"],
                    "old_part_id": old["part_id"],
                    "assembly_id": c["assembly_id"],
                }
            )
    return pairs


# ─── [Hands-on P2-Ch3-1] 끝 ───


def build_ecns(
    revisions: list[dict],
    lines_by_revision: dict[str, dict[tuple[str, str], dict]],
) -> list[EcnRecord]:
    """연속한 판마다 ECN 하나를 만든다. 차이가 없는 판 쌍은 건너뛴다."""
    ecns: list[EcnRecord] = []
    for prev, cur in pairwise(revisions):
        changes = diff_revisions(
            lines_by_revision[prev["revision_id"]], lines_by_revision[cur["revision_id"]]
        )
        if not changes:
            continue
        ecn_id = f"ECN-{cur['valid_from']}-{cur['revision_id']}"
        record = EcnRecord(
            ecn_id=ecn_id,
            revision_from=prev["revision_id"],
            revision_to=cur["revision_id"],
            ecn_date=cur["valid_from"],
            title=cur["message"],
            lines=changes,
        )
        for pair in pair_supersedes(changes):
            record.supersedes.append(
                {**pair, "ecn_id": ecn_id, "effective_date": cur["valid_from"]}
            )
        ecns.append(record)
    return ecns
