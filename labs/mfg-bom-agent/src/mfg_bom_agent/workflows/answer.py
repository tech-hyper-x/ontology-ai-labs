"""답변 작성과 출력 검사 — 스킬 grounded-answer (Part 2 Ch7-2 답변 근거 검증).

1. draft_answer: LLM 이 도구 결과(계산 결과 · 경로 · 문서)를 읽고 답변을 쓴다.
   답변은 읽는 순서대로 나눠 받는다: 첫 문장 답(headline) → 확인된 내용(findings) →
   추가로 확인할 사항(follow_ups) → 가정 · 기준(notes). 도구 이름 · 산식은 문장에 넣지 않는다
   (화면의 "계산 근거"가 cited 로 계산 결과를 찾아 산식 · 도구 · 입력값을 보여 준다).
   답변에 쓴 수량 · 금액은 cited 목록에 label · value · unit 으로 따로 적게 한다.
2. verify: cited 를 계산 결과와 대조한다. 문자열이 아니라 항목 · 값 · 단위 · 계산 조건 · 증감 방향을 본다.
   답변 문장 속 금액 · 수량 · 생산 대수도 그 문맥(1대당 · N대 총량 · 팩 크기)에 맞는 도구 값과 대조한다.
   계산 결과가 있는데 인용이 하나도 없으면 통과시키지 않는다.
3. 검사에 실패하면 무엇이 틀렸는지 알려 주고 한 번 다시 쓰게 한다 (bom_agent.py).
   다시 써도 실패하면 LLM 문장을 내리고, 코드가 계산 결과로 만든 문장(withheld_answer)만 보여 준다.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, field_validator

from mfg_bom_agent.contracts.answer import (
    VERIFY_VERSION,
    CalcResult,
    CheckItem,
    DocNote,
    Issue,
    KeyFact,
    Verification,
)
from mfg_bom_agent.workflows.llm import chat_model, skill_text


class Cited(BaseModel):
    label: str = Field(description="계산 결과의 label 을 글자 그대로")
    value: str = Field(description="답변에 쓴 값 (숫자만, 예: '6398.00')")
    unit: str = Field(description="USD · ea · pack · parts 중 하나")


class AnswerDraft(BaseModel):
    headline: str = Field(description="첫 문장. 질문에 바로 답한다 (도구 이름 · 산식 없이)")
    summary: str = Field(
        "", description="비교표용 한 줄 요약 20자 안팎 (예: 모터 부품비 $3,869.10 증가)"
    )
    highlights: list[str] = Field(
        default_factory=list,
        description="headline 에서 강조할 핵심 키워드 1~2개 (headline 에 글자 그대로 있는 말)",
    )
    subject: str = Field(
        "", description="계산 대상 부품 · 범위 (예: 모터 · 5203-2402-0027, 로봇 차량 전체)"
    )
    basis: str = Field(
        "",
        description="계산 기준 (예: 로봇 차량 100대). 판 ID · 리비전은 쓰지 않는다 (화면에 따로 표시)",
    )
    findings: list[str] = Field(
        default_factory=list, description="확인된 내용 2~4개. 한 항목에 한 가지 사실"
    )
    follow_ups: list[str] = Field(
        default_factory=list,
        description="추가로 확인할 사항 0~3개. 무엇을 확인해야 하는지 구체적으로",
    )
    notes: list[str] = Field(
        default_factory=list, description="가정 · 기준 0~2개 (교육용 가정, 가격 관측일)"
    )
    key_facts: list[KeyFact] = Field(
        default_factory=list,
        description="결과 카드로 보여 줄 판단 결과 0~2개 (예: 대체 부품 = 등록 없음)",
    )
    doc_notes: list[DocNote] = Field(default_factory=list, description="답변에 실제로 인용한 문서")
    cited: list[Cited] = Field(default_factory=list, description="답변에 쓴 모든 수량 · 금액")

    @field_validator(
        "findings",
        "follow_ups",
        "notes",
        "key_facts",
        "doc_notes",
        "cited",
        "highlights",
        mode="before",
    )
    @classmethod
    def _list_from_text(cls, v):
        """모델이 목록을 JSON 문자열로 돌려주는 경우가 있다 ('["a", "b"]'). 풀어서 받고, 아니면 줄 단위로 나눈다."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else [parsed]
            except json.JSONDecodeError:
                return [s.strip("-• ").strip() for s in v.splitlines() if s.strip()]
        return v

    @field_validator("basis", "subject")
    @classmethod
    def _drop_revision_id(cls, v: str) -> str:
        """계산 기준 · 대상에서 판 ID("판 구성 6b2c5a9 기준", "리비전 6b2c5a9")를 뺀다. 화면이 부품 구성으로 따로 보여 준다."""
        v = re.sub(r"[,·]?\s*(?:판 구성|부품 구성|리비전|판)\s*[0-9a-f]{7}(?:\s*기준)?", "", v)
        v = re.sub(r"\(\s*[,·]?\s*\)", "", v)  # 비어 버린 괄호
        return re.sub(r"\(\s*[,·]\s*", "(", v).strip(" ,·")

    def text(self) -> str:
        """화면 · 평가 · 기록에 쓰는 전체 답변 (구역을 이어 붙인 마크다운)."""
        out = [self.headline, self.summary]
        if self.findings:
            out.append("확인된 내용\n" + "\n".join(f"- {f}" for f in self.findings))
        if self.follow_ups:
            out.append("추가로 확인할 사항\n" + "\n".join(f"- {f}" for f in self.follow_ups))
        if self.notes:
            out.append("\n".join(self.notes))
        out += [f"{k.label}: {k.value}" for k in self.key_facts]
        return "\n\n".join(x for x in out if x)


ANSWER_SYSTEM = """너는 제조 BOM 변경 영향 분석 에이전트의 답변 작성 단계다.
아래 도구 결과만 근거로 질문에 답한다. 새로운 숫자를 계산하거나 지어내지 않는다.

{grounded}

{skill}

출력 규칙
- headline: 한 문장으로 질문에 바로 답한다. 질문이 "얼마나 늘어나나"면 증가액을, "몇 개"면 수량을 먼저 쓴다.
  금액은 무엇의 금액인지 정확히 쓴다. 한 부품만 계산했으면 "로봇 차량 원가"가 아니라 "{{부품}} 부품비"다.
  예: "모터 단가가 15% 오르면, 로봇 차량 100대에 필요한 모터 부품비가 $3,869.10 증가합니다."
  질문이 여러 가지를 물으면(몇 개 · 얼마 · 대신 쓸 부품) headline 에서 모두 짧게 답한다. 부품 이름을 한 번만 쓴다.
  예: "로봇 차량 50대에는 휠 300개($7,497.00)가 필요하고, 대신 쓸 수 있는 휠은 2종입니다."
- 문서를 찾는 질문이면 headline 에 문서 이름(어떤 내용의 문서인지)과 경로를 쓰고 행 번호는 쓰지 않는다 — 행 번호는 화면 참고 문서 탭에 나온다.
  예: "코너 바퀴가 돌지 않을 때는 서보 기어 교체 정비 문서(mechanical/servo_gear_replacement/README.md)를 참고하면 됩니다."
- 문장에서 제품은 "로봇 차량"이라고 쓴다 ("로버" 대신). 품번은 줄이지 않고 원래 형태(3616-0014-0192)로 쓴다.
- highlights: headline 에서 강조할 핵심 키워드 1~2개를 headline 에 있는 글자 그대로 (예: "모터 부품비", "drive wheel"). 숫자는 화면이 따로 강조하므로 넣지 않는다.
- summary: 비교표에 넣을 20자 안팎 요약. 예: "모터 부품비 $3,869.10 증가", "서보 200개 · $6,398.00", "53종 단일 공급".
- subject: 계산 대상. 예: "모터 · 5203-2402-0027", "로봇 차량 전체 (기계 BOM)". basis: 계산 기준. 예: "로봇 차량 100대". 판 ID(6b2c5a9) · "리비전"은 쓰지 않는다 — 화면에 부품 구성으로 따로 나온다.
- findings: "계산 기준" 2~3개. 한 항목에 한 사실, 짧게. 예: "로봇 차량 1대에 모터 6개가 필요합니다.", "기존 단가 $42.99에 15% 인상을 적용했습니다."
  headline 의 숫자를 반복하지 않는다. 어셈블리 경로 설명(어느 어셈블리를 거쳐 들어가는지)은 쓰지 않는다 — 화면의 BOM 사용처에 있다.
  조회 결과와 판단을 구분한다 ("현재 데이터에 등록된 대체 부품은 없습니다").
- follow_ups: "실행 전에 확인할 사항" 1~2개. 무엇을 누구에게 확인해야 하는지 구체적으로, 한 문장씩.
  예: "공급사에 인상 단가와 적용일을 확인해야 합니다."
  대체 부품이 등록돼 있으면 "대체 부품 확보 가능성" 같은 일반 문장 대신, 그 대체 부품의 장착 조건을 누구에게 확인할지 쓴다.
- notes: 적용 조건 1~2개 (화면에서 접혀 있다). 금액이 있으면: "실습 자료의 단가로 계산한 금액입니다(자료 확인일 {as_of}). 실제 가격 적용일은 확인되지 않았습니다."
  교육용 가정(단종 · 공급 중단 · 단가 인상 · MOQ · 가상 공급사)과 계산에서 뺀 것(다른 부품비 · 공정비 · 공임)을 적는다.
- 문장에 도구 이름(cost_rollup 등) · 산식 · 계산식(200개 × $31.99) · 내부 용어(ALTERNATE_OF, BOMLine, ea, 리비전 해시)를 쓰지 않는다.
  산식은 화면의 계산 근거에 따로 나온다. 단위는 업무 용어로: ea → 개, pack → 팩, parts → 종.
- key_facts: 숫자가 아닌 판단 결과 중 결과 카드로 보여 줄 것 0~1개. label 은 2~6자, value 는 12자 안팎
  (예: 대체 부품 = 등록 없음, 공급사 = goBILDA 1곳, 점검 부품 = 코너 서보). 계산 결과에 이미 있는 값은 넣지 않는다.
- doc_notes: 문서를 근거로 썼다면 그 문서마다 한국어 한 문장 요약(summary_ko)과, 발췌(excerpt)에서 글자 그대로 가져온 관련 문장(quote).
- cited: 답변(headline · summary · findings · follow_ups · notes · key_facts)에 쓴 모든 수량 · 금액을 빠짐없이 적는다. label 은 계산 결과의 label 을 그대로 복사한다.
- 계산 결과에 value 가 null 인 항목은 "미계산" 또는 "미확인"이라고 쓰고 cited 에 넣지 않는다."""


def facts_payload(
    question: str,
    intent: str,
    calcs: list[CalcResult],
    paths: list,
    docs: list,
    assumptions: list[str],
    facts: dict,
    context: dict,
) -> str:
    """LLM 에게 줄 도구 결과 요약(JSON)."""
    return json.dumps(
        {
            "question": question,
            "intent": intent,
            "context": context,
            "calculations": [c.model_dump(mode="json", exclude={"inputs"}) for c in calcs],
            "graph_paths": [p.text for p in paths],
            "documents": [
                {
                    "path": d.doc_path,
                    "line": d.line,
                    "title": d.title,
                    "excerpt": d.excerpt,
                    "linked_parts": d.linked_parts,
                }
                for d in docs
            ],
            "assumptions": assumptions,
            "tool_facts": facts,
        },
        ensure_ascii=False,
        default=str,
        indent=1,
    )


def draft_answer(
    skill: str, payload: str, feedback: str | None = None, as_of: str = "2026-10-22"
) -> AnswerDraft:
    model = chat_model("report").with_structured_output(AnswerDraft)
    msgs = [
        SystemMessage(
            ANSWER_SYSTEM.format(
                grounded=skill_text("grounded-answer"), skill=skill_text(skill), as_of=as_of
            )
        ),
        HumanMessage(payload),
    ]
    if feedback:
        msgs.append(
            HumanMessage(f"이전 답변이 출력 검사에서 실패했다. 고쳐서 다시 써라:\n{feedback}")
        )
    return model.invoke(msgs)


def template_answer(calcs: list[CalcResult], paths: list, docs: list) -> AnswerDraft:
    """DEMO_MODE=fixed_llm 용 고정 답변. 계산 결과를 정해진 문장 틀에 넣는다 (LLM 호출 없음)."""
    findings, follow_ups, cited = [], [], []
    for c in calcs[:4]:
        if c.value is None:
            follow_ups.append(f"{c.label}: {'미확인' if c.kind == 'extra_cost' else '미계산'}")
            continue
        findings.append(f"{c.label}: {_display(c.value, c.unit)}")
        cited.append(Cited(label=c.label, value=str(c.value), unit=c.unit))
    if paths:
        findings.append(f"사용처: {paths[0].text}")
    notes = [f"근거 문서: {docs[0].doc_path} {docs[0].line}행"] if docs else []
    return AnswerDraft(
        headline=findings[0] if findings else "조회 결과가 없습니다.",
        findings=findings[1:],
        follow_ups=follow_ups,
        notes=notes,
        cited=cited,
    )


def _display(value: Decimal, unit: str) -> str:
    """화면 · 고정 답변용 값 표기. 내부 단위를 업무 용어로 바꾼다."""
    if unit == "USD":
        return f"${value:,.2f}"
    return f"{value:,} {UNIT_KO.get(unit, unit)}"


UNIT_KO = {"ea": "개", "pack": "팩", "parts": "종"}


def keep_real_quotes(draft: AnswerDraft, docs: list) -> AnswerDraft:
    """doc_notes 의 quote 가 실제 발췌에 없으면 비운다 (LLM 이 원문을 지어내지 못하게)."""
    excerpts = {(d.doc_path, d.line): d.excerpt for d in docs}
    for n in draft.doc_notes:
        ex = excerpts.get((n.doc_path, n.line)) or " ".join(
            d.excerpt for d in docs if d.doc_path == n.doc_path
        )
        if n.quote and n.quote.strip() not in ex:
            n.quote = ""
    return draft


# ─── [Hands-on P2-Ch7-2 답변 근거 검증] 시작 ───
_MONEY = re.compile(r"\$\s?([\d,]+\.\d{2})|(?<![\w.$-])-?([\d,]+\.\d{2})\s*(?:USD|달러)")
# 문장 속 수량 표현. 품번(2000-0025-0002) · 판 ID · 날짜의 숫자는 앞뒤가 하이픈 · 영숫자라 잡히지 않는다
_QTY = re.compile(
    r"(?<![A-Za-z0-9.\-/_#$])(\d[\d,]*(?:\.\d+)?)\s*(개입(?!니)|개들이|개 ?팩|개|ea|팩|pack|종|대|%)(?![A-Za-z])"
)
# "60개 라인" · "2곳" 처럼 행 · 문서 · 장소를 센 말은 부품 수량이 아니다
_COUNT_NOUN = re.compile(r"\s*(라인|행|줄|건|곳|문서|어셈블리|공급사|단계|판|항목)")
_PER_PRODUCT = re.compile(r"(?<!\d)1\s*대\s*(당|에|기준)|한\s*대(당|에)")
_UP = re.compile(r"증가|늘어|늘며|늘고|늘었|오르|올라|상승|비싸")
_DOWN = re.compile(r"감소|줄어|줄며|줄고|줄었|낮아|내려|하락|절감|저렴|싸집|싸져")


def _num(text: str) -> Decimal | None:
    try:
        return Decimal(str(text).replace(",", "").replace("$", "").strip())
    except InvalidOperation:
        return None


def _sentences(text: str) -> list[str]:
    """문장 단위로 나눈다. 수량의 문맥(1대당 · N대)은 같은 문장 안에서만 본다."""
    return [s.strip() for s in re.split(r"(?<=[.!?。])\s+|\n+", text) if s.strip()]


def _fact_numbers(obj) -> set[Decimal]:
    """도구 결과(facts)에 들어 있는 모든 숫자와 목록 길이 (예: 대체 부품 2종, 공급사 1곳)."""
    out: set[Decimal] = set()
    if isinstance(obj, dict):
        for v in obj.values():
            out |= _fact_numbers(v)
    elif isinstance(obj, (list, tuple)):
        out.add(Decimal(len(obj)))
        for v in obj:
            out |= _fact_numbers(v)
    elif isinstance(obj, (int, float, Decimal)) and not isinstance(obj, bool):
        out.add(Decimal(str(obj)))
    elif isinstance(obj, str):
        # 도구가 만든 문장(가정 · 공급 조건)에 든 숫자도 근거가 있는 값이다 (예: "MOQ 4팩")
        out |= {
            n
            for m in re.findall(r"(?<![\w.\-])\d[\d,]*(?:\.\d+)?", obj)
            if (n := _num(m)) is not None
        }
    return out


class _Known:
    """답변 문장에 써도 되는 수량을 문맥별로 모은다. 숫자만 같다고 다른 항목의 값으로 인정하지 않는다."""

    def __init__(self, calcs: list[CalcResult], paths: list, facts: dict | None, units, percent):
        self.units = units
        d = [p.detail or {} for p in paths]
        per = {_num(x["each_per_product"]) for x in d if "each_per_product" in x}
        if len(per) > 1:  # 여러 어셈블리에 쓰이면 1대당 합계도 맞는 값이다
            per.add(sum(per))
        per |= {c.value for c in calcs if c.unit in ("ea", "pack") and c.inputs.get("units") == 1}
        # 생산 대수 총량에서 1대당 수량을 되짚는다 (예: 50대 200개 → 1대당 4개). 경로가 없는 구매 질문용
        per |= {
            c.value / c.inputs["units"]
            for c in calcs
            if c.kind == "quantity"
            and c.unit == "ea"
            and c.value is not None
            and c.inputs.get("units")
        }
        self.per_product = {v for v in per if v is not None}
        self.pack_size = {Decimal(x["pack_size"]) for x in d if "pack_size" in x}
        self.pack_size |= {Decimal(c.inputs["pack_size"]) for c in calcs if "pack_size" in c.inputs}
        self.total = {
            c.value for c in calcs if c.value is not None and c.unit in ("ea", "pack", "parts")
        }
        # 산식에 적힌 수량(예: "200개 × $31.99")도 도구가 계산한 값이다
        self.total |= {
            n
            for c in calcs
            for m in re.findall(r"([\d,.]+)\s*개(?!입)", c.formula)
            if (n := _num(m)) is not None
        }
        if units:
            self.total |= {v * units for v in self.per_product}
        self.packs = {c.value for c in calcs if c.value is not None and c.unit == "pack"}
        self.packs |= {_num(x["raw_qty"]) for x in d if "raw_qty" in x}
        self.packs |= {Decimal(c.inputs["moq_packs"]) for c in calcs if "moq_packs" in c.inputs}
        # 산식 · 공급 조건에 적힌 팩 수 (예: "팩 4개 · MOQ 4팩")
        self.packs |= {
            n
            for c in calcs
            for m in re.findall(r"([\d,.]+)\s*팩", c.formula)
            if (n := _num(m)) is not None
        }
        self.facts = _fact_numbers(facts or {})
        self.general = self.per_product | self.pack_size | self.total | self.packs | self.facts
        self.multipliers = {Decimal(x["multiplier"]) for x in d if "multiplier" in x}
        # 어셈블리 1개에 들어가는 수량 = 1대당 수량 ÷ 배수 (예: rocker bogie 1개에 서보 2개)
        self.per_assembly = {
            _num(x["each_per_product"]) / Decimal(x["multiplier"])
            for x in d
            if x.get("multiplier") and "each_per_product" in x
        }
        self.assemblies = {str(x["assembly"]).lower() for x in d if x.get("assembly")}
        self.general |= self.multipliers | self.per_assembly
        pct = _num(str(percent).rstrip("%")) if percent else None
        # "10% 인하"는 -10 의 크기로 쓴다
        self.percent = {pct, abs(pct)} if pct is not None else set()

    def check(self, sentence: str) -> list[Issue]:
        """한 문장의 수량 표현을 문맥에 맞는 값과 대조한다."""
        issues = []
        for m in _QTY.finditer(sentence):
            value, unit = _num(m.group(1)), m.group(2).replace(" ", "")
            before = sentence[max(0, m.start() - 16) : m.start()]
            target = m.group(0).strip()
            if value is None or sentence[m.end() : m.end() + 1] in ("체", "상", "월"):
                continue  # "대체" · "대상" · "개월"은 수량이 아니다
            if unit in ("개", "ea", "종") and _COUNT_NOUN.match(sentence, m.end()):
                continue
            if unit == "대":
                # 생산 대수: 이번 요청의 대수이거나 "1대당"의 1이어야 한다
                if self.units and value not in (Decimal(self.units), Decimal(1)):
                    issues.append(
                        Issue(
                            code="wrong_condition",
                            target=target,
                            detail=f"요청 생산 대수는 {self.units}대",
                        )
                    )
            elif unit == "%":
                if value not in self.percent | self.facts:
                    issues.append(
                        Issue(code="wrong_value", target=target, detail="요청 · 도구에 없는 비율")
                    )
            elif unit in ("개입", "개들이", "개팩"):
                if value not in self.pack_size:
                    issues.append(Issue(code="wrong_value", target=target, detail="팩 크기와 다름"))
            elif unit in ("팩", "pack"):
                # 구매 팩 수 · 원천 팩 수량 · MOQ 등 공급 조건의 팩 수(도구 결과 facts)
                if value not in self.packs | self.facts:
                    issues.append(
                        Issue(
                            code="wrong_unit" if value in self.total else "wrong_value",
                            target=target,
                            detail="구매 팩 수 · 원천 팩 수량과 다름",
                        )
                    )
            elif _PER_PRODUCT.search(before):
                # "1대당 N개" 는 로버 1대당 수량 (where_used 의 each_per_product).
                # 같은 절에 어셈블리가 나오면 어셈블리 개수 · 어셈블리당 수량일 수 있다
                # ("rocker bogie 는 로버 1대에 2개") — 배수와 어셈블리당 수량까지 허용한다
                clause = re.split(r"[,，]", sentence[: m.start()])[-1].lower()
                allowed = set(self.per_product)
                if "어셈블리" in clause or any(a in clause for a in self.assemblies):
                    allowed |= self.multipliers | self.per_assembly
                if value not in allowed:
                    want = ", ".join(sorted(str(v) for v in self.per_product)) or "없음"
                    issues.append(
                        Issue(
                            code="wrong_value", target=target, detail=f"도구의 1대당 수량은 {want}"
                        )
                    )
            elif self.units and self.units != 1 and re.search(rf"(?<!\d){self.units}\s*대", before):
                # "50대에 N개" 는 생산 대수 전체의 총량
                if value not in self.total:
                    code = "wrong_condition" if value in self.per_product else "wrong_value"
                    issues.append(
                        Issue(code=code, target=target, detail=f"{self.units}대 총량과 다름")
                    )
            elif value not in self.general:
                issues.append(
                    Issue(code="wrong_value", target=target, detail="도구 결과에 없는 수량")
                )
        return issues


def _direction_issues(sentences: list[str], calcs: list[CalcResult]) -> list[Issue]:
    """차이 값을 쓴 문장이 증가 · 감소 방향을 맞게 썼는지 본다 (금액 크기만 같으면 통과시키지 않는다)."""
    issues = []
    for c in calcs:
        if c.kind != "diff" or c.value is None or c.value == 0:
            continue  # 0 은 "변경 없음" — 증가 · 감소로 강제하지 않는다
        amount = f"{abs(c.value):,.2f}"
        for s in sentences:
            plain = re.escape(f"{abs(c.value):.2f}")
            pattern = rf"([-−]?)\s?\$\s?([-−]?){re.escape(amount)}|([-−]?)(?:{re.escape(amount)}|{plain})\s*(?:USD|달러)"
            for m in re.finditer(pattern, s):
                if m.group(1) or m.group(2) or m.group(3):  # 부호를 붙여 썼으면 부호로 판단
                    stated = -1
                else:
                    clause = re.split(r"[,，]", s[m.end() :], maxsplit=1)[0]
                    up, down = bool(_UP.search(clause)), bool(_DOWN.search(clause))
                    stated = 1 if up and not down else -1 if down and not up else 0
                if stated == 0 and c.value > 0:
                    continue  # 방향 없이 쓴 양수 차이("차이 $3,869.10")는 증가로 읽힌다
                if stated != (1 if c.value > 0 else -1):
                    want = "증가" if c.value > 0 else "감소"
                    issues.append(
                        Issue(
                            code="wrong_direction",
                            target=m.group(0).strip(),
                            detail=f"{c.label}: 도구 값 {c.value} USD ({want})",
                        )
                    )
    return issues


def verify(
    draft: AnswerDraft,
    calcs: list[CalcResult],
    revision: str | None,
    units: int | None,
    paths: list | None = None,
    facts: dict | None = None,
    percent: str | None = None,
) -> Verification:
    """결론이 인용한 수량 · 금액이 계산 결과와 항목 · 값 · 단위 · 계산 조건 · 방향 모두 맞는지 검사한다.

    paths · facts · percent 를 주면 인용 목록 밖, 답변 문장 속 수량(1대당 · N대 총량 · 팩)도 대조한다.
    """
    if not calcs:
        return Verification(
            status="not_run", reason="계산 결과가 없어 검사할 대상이 없음", version=VERIFY_VERSION
        )
    by_label = {c.label: c for c in calcs if c.value is not None}
    checks = []
    for cited in draft.cited:
        calc = by_label.get(cited.label)
        value = _num(cited.value)
        item_ok = calc is not None
        # 차이 값은 문장에서 "줄어듭니다 · 늘어납니다"로 방향을 쓰고 크기만 적을 수 있다 (−$2,254.50 → $2,254.50).
        # 크기만 적은 경우의 방향은 아래 _direction_issues 가 문장에서 따로 확인한다
        value_ok = bool(
            calc
            and value is not None
            and (value == calc.value or (calc.kind == "diff" and value == abs(calc.value)))
        )
        unit_ok = bool(calc and cited.unit.lower() == calc.unit.lower())
        # 계산 조건: 그 계산이 이번 실행의 판 · 생산 대수로 계산된 값인지.
        # 생산 대수를 입력으로 받는 계산인데 대수가 비어 있으면 일치로 보지 않는다
        condition_ok = bool(
            calc
            and (revision is None or calc.revision in (None, revision))
            and (units is None or "units" not in calc.inputs or calc.inputs["units"] == units)
        )
        checks.append(
            CheckItem(
                target=cited.label,
                cited_value=cited.value,
                item_ok=item_ok,
                value_ok=value_ok,
                unit_ok=unit_ok,
                condition_ok=condition_ok,
            )
        )
    # 계산 결과 값과, 산식에 들어간 입력 단가(예: $31.99/개)는 근거가 있는 금액으로 본다
    known = {c.value for c in calcs if c.value is not None and c.unit == "USD"}
    known |= {_num(m) for c in calcs for m in re.findall(r"\$\s?([\d,]+\.\d{2})", c.formula)}
    known |= {abs(c.value) for c in calcs if c.kind == "diff" and c.value is not None}
    text = draft.text()
    amounts = [a or b for a, b in _MONEY.findall(text)]  # "$1,330.38" · "1330.38 USD" 두 표기
    unverified = [m for m in amounts if _num(m) not in known]

    issues: list[Issue] = []
    sentences = _sentences(text)
    # 값이 있는 계산 결과가 있는데 인용이 0건이면 검사한 것이 없다 — 통과로 표시하지 않는다
    if not draft.cited and any(c.value is not None and c.kind != "reference" for c in calcs):
        issues.append(
            Issue(
                code="missing_reference",
                target="cited",
                detail="계산 결과가 있는데 답변이 인용한 값이 없음",
            )
        )
    known_qty = _Known(calcs, paths or [], facts, units, percent)
    for s in sentences:
        issues += known_qty.check(s)
    issues += _direction_issues(sentences, calcs)
    for c in checks:  # 인용한 차이 값의 방향 문제를 해당 인용 항목에도 표시한다
        if any(i.code == "wrong_direction" and i.detail.startswith(c.target + ":") for i in issues):
            c.direction_ok = False

    ok = all(c.passed for c in checks) and not unverified and not issues
    return Verification(
        status="passed" if ok else "failed",
        checks=checks,
        unverified_numbers=unverified,
        issues=issues,
        reason=""
        if ok
        else "인용 값 · 문장 속 수량 · 금액 · 증감 방향이 계산 결과와 다르거나, 인용이 없음",
        version=VERIFY_VERSION,
    )


ISSUE_KO = {
    "missing_reference": "인용 누락",
    "wrong_value": "값 불일치",
    "wrong_unit": "단위 불일치",
    "wrong_condition": "조건(대수 · 판) 불일치",
    "wrong_direction": "증감 방향 오류",
}


def feedback_of(v: Verification) -> str:
    lines = [
        f"- {c.target}: 항목 {c.item_ok} · 값 {c.value_ok} · 단위 {c.unit_ok} · 조건 {c.condition_ok}"
        f" · 방향 {c.direction_ok}"
        for c in v.checks
        if not c.passed
    ]
    lines += [f"- 계산 결과에 없는 금액: ${m}" for m in v.unverified_numbers]
    lines += [f"- {ISSUE_KO[i.code]}: '{i.target}' ({i.detail})" for i in v.issues]
    return "\n".join(lines)


def withheld_answer(calcs: list[CalcResult], paths: list, docs: list) -> AnswerDraft:
    """다시 써도 검사에 실패했을 때 보여 줄 답변. LLM 문장 대신 검증된 계산 결과를 코드가 문장으로 만든다."""
    draft = template_answer(calcs, paths, docs)
    draft.findings = ([draft.headline] if draft.cited else []) + draft.findings
    draft.headline = "자동 답변 검증에 실패해, 도구가 계산한 결과만 표시합니다."
    draft.summary = "답변 검증 실패 · 계산 결과만 표시"
    return draft


# ─── [Hands-on P2-Ch7-2] 끝 ───
