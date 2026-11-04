"""Ch8: 구성한 교육용 응답을 기존 score로 채점. 실제 모델 실행 아님."""
import argparse
import json
from pathlib import Path
import yaml
from mfg_bom_agent.contracts.answer import AnswerResponse
from mfg_bom_agent.evaluation.scoring import score

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cases', type=Path, default=ROOT / 'docs/part02/ch08/worksheets/score-cases.json')
    p.add_argument('--check', action='store_true', help='배포 사례의 예상 자동 판정 회귀 확인')
    a = p.parse_args()
    golden = yaml.safe_load((ROOT / 'labs/mfg-bom-agent/data/golden/golden_set.yaml').read_text(encoding='utf-8'))
    by_id = {i['id']: i for i in golden['items']}
    pack = json.loads(a.cases.read_text(encoding='utf-8'))
    for c in pack['records']:
        r = score(by_id[c['id']], AnswerResponse.model_validate(c['response']))
        out = dict(case=c['case'], id=c['id'], source=c['source'], expected_auto=c['expected_auto'],
                   manual_review_required=c['manual_review_required'], **r)
        print(json.dumps(out, ensure_ascii=False, default=str))
        if a.check:
            for k, expected in c['expected_auto'].items():
                assert r[k] == expected, (c['case'], k, r[k], expected)
    print('교육용 응답 채점 완료. 자동 통과와 업무적 정답·근거 충실성은 따로 검토합니다.')


if __name__ == '__main__':
    main()
