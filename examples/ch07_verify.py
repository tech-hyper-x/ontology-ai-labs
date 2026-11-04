"""실제 verify로 작은 답변 fixture 검사. DB·LLM 없음; 실패 예상 사례의 탐지를 확인."""
import argparse
import json
from decimal import Decimal
from pathlib import Path
from mfg_bom_agent.contracts.answer import CalcResult, GraphPath
from mfg_bom_agent.workflows.answer import AnswerDraft, Cited, verify

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases", type=Path, default=ROOT / "docs/part02/ch07/worksheets/answer-cases.json")
    a = p.parse_args()
    calcs = [
        CalcResult(label="서보 소요량 (50대)", kind="quantity", value=Decimal(200), unit="ea",
                   inputs={"units": 50, "part": "2000-0025-0002"}, revision="6b2c5a9"),
        CalcResult(label="검사용 모터 부품비 차이", kind="diff", value=Decimal("-13.98"), unit="USD",
                   inputs={"units": 50}, revision="6b2c5a9", note="검사용 가상 값; Ch6 15% 인상 결과와 무관"),
        CalcResult(label="단종 추가 비용", kind="extra_cost", value=None, unit="USD"),
    ]
    path = GraphPath(text="Rover → rocker bogie → servo", tool="where_used", revision="6b2c5a9",
                     detail=dict(assembly="rocker bogie", multiplier=2, raw_qty="2", pack_size=1,
                                 each_per_product="4", sku="2000-0025-0002"))
    for c in json.loads(a.cases.read_text(encoding="utf-8")):
        cited = [Cited(label=c["label"], value=c["value"], unit=c["unit"])] if "label" in c else []
        draft = AnswerDraft(headline=c["headline"], cited=cited)
        v = verify(draft, calcs, "6b2c5a9", c.get("requested_units", 50), paths=[path])
        print(json.dumps(dict(case=c["id"],expected=c["expected"],actual=v.status,
                              issues=[i.model_dump() for i in v.issues],
                              checks=[x.model_dump() for x in v.checks],unverified_numbers=v.unverified_numbers),
                         ensure_ascii=False, default=str))
        assert v.status == c["expected"], c["id"]
    print("모든 사례가 예상 판정과 일치했습니다. 답변 전체의 의미 검증을 뜻하지 않습니다.")


if __name__ == "__main__":
    main()
