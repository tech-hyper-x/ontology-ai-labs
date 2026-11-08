"""Read provided files only. Run from labs/bio-target-agent."""
from pathlib import Path
import json,hashlib
p=Path('data/raw/opentargets/snapshot.json');s=json.loads(p.read_text())
i=json.loads(Path('data/processed/data_inventory.json').read_text())
print(json.dumps({'release':s['meta']['dataVersion'],'retrieved_at':s['retrieved_at'],'disease':s['disease']['id'],'gene':s['targets']['EGFR']['id'],'proteins':s['targets']['EGFR']['proteinIds'],'papers_total':i['papers_total'],'papers_with_abstract':i['papers_with_abstract'],'snapshot_sha256':hashlib.sha256(p.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
