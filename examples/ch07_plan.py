"""Ch7 질문 구조화. 기본은 제한된 rule_plan, --llm일 때만 실제 모델 호출."""
import argparse
import json
from mfg_bom_agent.workflows.plan import rule_plan, llm_plan

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--question", default="모터 5203-2402-0027 단가가 15% 오르면 100대 비용은?")
    p.add_argument("--llm", action="store_true")
    a = p.parse_args()
    plan = (llm_plan if a.llm else rule_plan)(a.question)
    print(json.dumps(dict(mode="real_llm" if a.llm else "rule_plan / LLM 아님", plan=plan.model_dump()), ensure_ascii=False, indent=2))
