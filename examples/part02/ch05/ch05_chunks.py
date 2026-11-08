"""Ch5 원문 한 파일을 메모리에서 청크로 나누고 제공 CSV와 대조합니다."""
from pathlib import Path
import csv
from mfg_bom_agent.retrieval.chunking import chunk_markdown
ROOT=Path(__file__).resolve().parents[3]
name="mechanical/servo_gear_replacement/README.md"
raw=(ROOT/"docs/part02/ch05/source/servo_gear_replacement.md").read_text(encoding="utf-8")
chunks=chunk_markdown(name,raw)
with (ROOT/"labs/mfg-bom-agent/data/processed/quality_document.csv").open(encoding="utf-8",newline="") as f:
    stored={r["doc_id"]:r for r in csv.DictReader(f) if r["path"]==name}
for c in chunks:
    old=stored.get(c["doc_id"])
    same=bool(old and old["text"].replace("\r\n","\n")==c["text"] and int(old["line"])==c["line"])
    print(c["doc_id"],"line",c["line"],c["title"],"CSV일치",same)
    if c["title"]=="Diagnosing an issue":print(c["text"][:400])
print("청크",len(chunks),"개 / 제공 CSV",len(stored),"개. 원본·CSV·DB를 변경하지 않았습니다.")
