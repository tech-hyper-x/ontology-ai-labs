"""실제 runtime 실행. 되묻기 응답은 같은 프로세스·run_id에서 전달한다."""
import argparse
import json
import uuid
from mfg_bom_agent.contracts.answer import AnswerRequest, ResumeInput, RunContext
from mfg_bom_agent.workflows.bom_agent import run


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--question", default="모터 5203-2402-0027 단가가 15% 오르면 100대 비용은?")
    p.add_argument("--revision", default="6b2c5a9")
    p.add_argument("--demo-mode", choices=["fixed_llm", "none"], default="fixed_llm")
    p.add_argument("--answer", help="첫 되묻기에 전달할 값; 없으면 터미널에서 입력")
    a = p.parse_args()
    req = AnswerRequest(run_id="ch07-"+uuid.uuid4().hex[:12],question=a.question,
                        context=RunContext(revision=a.revision,demo_mode=a.demo_mode))

    def on_event(e):
        if e.type in ("tool_started", "tool_finished", "tool_failed", "input_requested", "step_note"):
            print(json.dumps(e.model_dump(mode="json"), ensure_ascii=False, default=str))

    resp = run(req, on_event)
    while resp.status == "needs_input":
        print(resp.pending_question.prompt)
        value = a.answer if a.answer is not None else input("응답: ")
        a.answer = None
        req = req.model_copy(update={"resume": ResumeInput(field=resp.pending_question.field,value=value)})
        resp = run(req, on_event)
    print(json.dumps(resp.model_dump(mode="json"),ensure_ascii=False,indent=2))
    if resp.status == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
