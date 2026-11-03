"""기존 가상 오연결 과제의 수정 전후를 메모리에서 비교합니다. 파일·DB를 바꾸지 않습니다."""
from pathlib import Path
import yaml
from mfg_bom_agent.retrieval.linking import apply_overrides, LINK_OVERRIDES
root=Path(__file__).resolve().parents[1]
x=yaml.safe_load((root/"labs/mfg-bom-agent/data/exercises/exercises.yaml").read_text(encoding="utf-8"))["ch5_1_link"]
fix=(x["doc_id"],x["must_remove"][0],"remove")
for label,rules in [("현재 규칙",LINK_OVERRIDES),("remove 보정 후",LINK_OVERRIDES+[fix])]:
    rows=apply_overrides([dict(r) for r in x["auto_links"]],rules)
    kept={r["part_id"] for r in rows if r["doc_id"]==x["doc_id"]}
    print(label,sorted(kept),"서보 제거",all(p not in kept for p in x["must_remove"]),"휠 유지",all(p in kept for p in x["must_keep"]))
