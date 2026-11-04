"""원본을 덮어쓰지 않고 CSV 참조 계산과 배포 Golden Set을 대조한다."""
from collections import Counter
import importlib.util
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / 'labs/mfg-bom-agent'

if __name__ == '__main__':
    spec = importlib.util.spec_from_file_location('ch08_build_golden', LAB / 'scripts/build_golden.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    saved = yaml.safe_load((LAB / 'data/golden/golden_set.yaml').read_text(encoding='utf-8'))
    rebuilt = mod.build()  # main()은 호출하지 않아 파일을 덮어쓰지 않는다.
    assert rebuilt == saved['items'], '참조 계산과 배포 문항이 다릅니다. 버전·조건을 확인하세요.'
    print('일치:', len(rebuilt), '문항', dict(Counter(i['category'] for i in rebuilt)))
    print('Golden', saved['version'], '/ snapshot', saved['snapshot'])
    for i in rebuilt:
        if i['id'] in {'G01', 'G16', 'G36'}:
            print(i['id'], i['expected'])
