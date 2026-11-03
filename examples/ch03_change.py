"""Ch3 motor-change example. Reads two bundled original snapshots; no file or DB writes."""
from pathlib import Path
import csv,json
from mfg_bom_agent.foundation.normalize import map_parts_row,make_part_id,assembly_id
from mfg_bom_agent.foundation.ecn import diff_revisions,pair_supersedes,revision_intervals
ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'docs/part02/ch03/reference'
def motor_lines(name):
    with (REF/name).open(encoding='utf-8-sig',newline='') as f:
        raw=next(r for r in csv.DictReader(f) if r['assembly']=='drive wheel' and r['short name']=='motor')
    row=map_parts_row(raw)
    key=(assembly_id('OSR',row['assembly_name']),make_part_id(row['sku'],row['long_name'],row['url']))
    return {key:dict(raw_qty=row['raw_qty'],multiplier=int(row['multiplier']),short_name=row['short_name'])}
def main():
    changes=diff_revisions(motor_lines('before_parts_list.csv'),motor_lines('after_parts_list.csv'))
    pairs=pair_supersedes(changes)
    assert {x['change_type'] for x in changes}=={'added','removed'}
    assert len(pairs)==1 and pairs[0]['old_part_id']=='P-5202-2402-0027' and pairs[0]['new_part_id']=='P-5203-2402-0027'
    print(json.dumps(dict(changes=changes,supersedes=pairs,intervals=revision_intervals([('d6d1fbc','2023-07-17'),('d092d83','2023-07-18'),('886bb13','2023-07-26')])),ensure_ascii=False,indent=2))
    print('확인: 모터 한 쌍만 비교. 전체 diff는 변경 행 6개. 마지막 구간은 이 예제 입력의 끝이며 실제 최신 판이 아닙니다.')
if __name__=='__main__':main()
