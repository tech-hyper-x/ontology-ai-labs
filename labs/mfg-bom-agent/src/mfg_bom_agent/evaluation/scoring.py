"""Golden Set 채점 (Part 2 Ch8 기준 문항 실행과 오류 분석).

세 실행 방식(지식 그래프 + 도구 · RAG · LLM 단독)을 같은 기준으로 채점한다.
정답 여부는 화면에 보이는 최종 답변(conclusion)으로 판정한다. 계산 패널에 정답이 있어도
결론이 틀리면 오답이다 — 두 결과를 tool_correct · answer_correct 로 따로 남긴다.

- number : 결론에 정답과 같은 단위의 값이 허용 오차 안에서 있어야 한다.
           차이(metric: diff)는 크기와 증가 · 감소 방향을 함께 본다 ("$13.98 증가"는 -13.98 의 오답)
- set    : 결론에 정답 항목이 모두 있고(recall), 같은 종류의 다른 항목이 없어야(precision) exact 정답
- doc    : 결론 또는 답변이 인용한 문서에 정답 경로가 있어야 정답 (검색 결과에만 있으면 evidence_correct)

결과 필드
  passed            answer_correct 와 같다 (이전 결과 파일과 같은 열 이름)
  answer_correct    최종 답변이 정답인가
  tool_correct      구조화된 도구 결과(계산 · 경로 · 문서)가 정답을 담았는가. 도구가 없는 방식은 None
  evidence_correct  정답 문서가 근거 문서 목록에 있는가 (doc 문항만)
  answerability     answered · abstained · needs_input · failed — 보류를 오답 생성과 구분한다
  reason            오류 분류: not_answered · abstained · wrong_value · wrong_unit · wrong_condition ·
                    wrong_direction · no_value · missing_item · extra_item · no_evidence
  precision · recall  집합 문항만
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from mfg_bom_agent.contracts.answer import AnswerResponse

SCORING_VERSION = (
    "2"  # 1: 숫자 크기만 · 텍스트 포함 여부 (2026-10-25 평가) → 2: 단위 · 방향 · 결론 기준
)

_ID_GUARD = r"(?<![A-Za-z0-9.\-/_#])"  # 품번 · 판 ID · 날짜 속 숫자는 값으로 읽지 않는다
_NUM = r"(\d[\d,]*(?:\.\d+)?)"
_UNIT_PATTERNS = {  # 결론은 소문자로 바꿔 채점하므로 대소문자를 가리지 않는다
    "USD": [
        re.compile(rf"([-−]?)\s?\$\s?([-−]?){_NUM}"),
        re.compile(rf"(?<![A-Za-z0-9./_#$-])([-−]?)(){_NUM}\s*(?:USD|달러)", re.IGNORECASE),
    ],
    "ea": [
        re.compile(rf"{_ID_GUARD}()(){_NUM}\s*(?:개(?!입(?!니)|들이|월| ?팩)|ea\b)", re.IGNORECASE)
    ],
    "pack": [re.compile(rf"{_ID_GUARD}()(){_NUM}\s*(?:팩|pack)", re.IGNORECASE)],
    "parts": [
        re.compile(
            rf"{_ID_GUARD}()(){_NUM}\s*(?:종|개(?!입(?!니)|들이|월| ?팩)|parts\b|가지)",
            re.IGNORECASE,
        )
    ],
}
_UP = re.compile(r"증가|늘어|늘며|늘고|늘었|늘어나|오르|올라|상승|비싸")
_DOWN = re.compile(r"감소|줄어|줄며|줄고|줄었|낮아|내려|하락|절감|저렴")
_ABSTAIN = re.compile(
    r"알 수 없|확인할 수 없|판단할 수 없|정보가 없|데이터가 없|답할 수 없|제공되지 않"
)

ASSEMBLIES = {"body", "corner", "drive wheel", "general", "rocker bogie"}
_SET_KINDS = {
    "part": re.compile(r"(?<![\w-])(?:\d{4}-\d{4}-\d{4}|\d{4}X)(?![\w-])", re.IGNORECASE),
    "date": re.compile(r"\d{4}-\d{2}-\d{2}"),
    "domain": re.compile(r"\b[a-z0-9-]+\.(?:com|net|org|io)\b"),
}


def _dec(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(",", ""))
    except InvalidOperation:
        return None


def _mentions(text: str) -> list[tuple[str, Decimal, int, str]]:
    """결론 속 (단위, 값, 부호(-1 · 0), 주변 문맥) 목록. 부호는 '-$13.98' 처럼 직접 쓴 경우만 -1."""
    out = []
    for unit, patterns in _UNIT_PATTERNS.items():
        for p in patterns:
            for m in p.finditer(text):
                value = _dec(m.group(3))
                if value is None:
                    continue
                sign = -1 if (m.group(1) or m.group(2)) else 0
                # 방향 낱말은 금액 뒤 같은 절(쉼표 · 마침표 전)이나 바로 앞 몇 글자에 온다 ("증가액은 $38.69")
                after = re.split(r"[,.。\n]\s", text[m.end() :], maxsplit=1)[0]
                out.append(
                    (unit, value, sign, text[max(0, m.start() - 12) : m.start()] + " " + after)
                )
    return out


def _direction(sign: int, context: str) -> str:
    if sign < 0:
        return "decrease"
    up, down = bool(_UP.search(context)), bool(_DOWN.search(context))
    return "increase" if up and not down else "decrease" if down and not up else "unstated"


def _other_units(text: str, units: int) -> bool:
    """결론이 질문의 생산 대수 대신 다른 대수만 말하는지 ("1대당"의 1은 대수가 아니다)."""
    said = {int(n) for n in re.findall(r"(?<!\d)(\d+)\s*대(?![체상당])", text)} - {1}
    return bool(said) and units not in said


def _answerability(resp: AnswerResponse) -> str:
    if resp.status == "needs_input":
        return "needs_input"
    if resp.status != "completed":
        return "failed"
    if _ABSTAIN.search(resp.conclusion or "") and not _mentions(resp.conclusion or ""):
        return "abstained"
    return "answered"


def _score_number(exp: dict, resp: AnswerResponse, text: str) -> dict:
    target, tol, unit = Decimal(exp["value"]), Decimal(exp["tol"]), exp["unit"]
    is_diff = exp.get("metric") == "diff"
    want_dir = exp.get("direction")
    close = lambda v: abs(v - target) <= tol  # 크기 비교 (차이는 방향을 따로 본다)
    mentions = _mentions(text)
    same_unit = [m for m in mentions if m[0] == unit and close(m[1])]
    correct = False
    reason = ""
    if same_unit and not is_diff:
        correct = True
    elif same_unit:
        dirs = [_direction(m[2], m[3]) for m in same_unit]
        # 방향을 쓰지 않은 증가액("차이는 $38.69")은 증가로 읽는다. 감소는 방향이나 부호를 써야 한다
        correct = any(d == want_dir or (d == "unstated" and want_dir == "increase") for d in dirs)
        reason = "" if correct else "wrong_direction"
    elif any(close(m[1]) for m in mentions):
        reason = "wrong_unit"
    elif exp.get("units") and _other_units(text, int(exp["units"])):
        reason = "wrong_condition"  # 질문의 생산 대수와 다른 대수로 답함
    elif any(m[0] == unit for m in mentions):
        reason = "wrong_value"
    else:
        reason = "no_value"
    tool = None
    if resp.mode == "kg_tools":
        signed = -target if want_dir == "decrease" else target
        tool = any(
            c.value is not None
            and c.unit == unit
            and (abs(c.value - signed) <= tol if is_diff else abs(abs(c.value) - target) <= tol)
            for c in resp.calculations
        )
    got = sorted({f"{m[1]} {m[0]}" for m in mentions})[:8]
    want = f"{target} {unit}" + (f" ({want_dir})" if is_diff else "")
    return {
        "answer_correct": correct,
        "tool_correct": tool,
        "reason": "" if correct else reason,
        "detail": f"정답 {want} · 결론의 값 {got}",
    }


def _set_kind(values: list[str]) -> str | None:
    vals = [str(v) for v in values]
    if all(v.lower() in ASSEMBLIES for v in vals):
        return "assembly"
    for kind, p in _SET_KINDS.items():
        if all(p.fullmatch(v) for v in vals):
            return kind
    return None  # 종류를 정할 수 없으면 추가 항목은 세지 않는다 (recall 만)


def _found_items(kind: str, text: str) -> set[str]:
    if kind == "assembly":
        return {a for a in ASSEMBLIES if re.search(rf"\b{re.escape(a)}\b", text)}
    return {m.group(0).lower() for m in _SET_KINDS[kind].finditer(text)}


def _score_set(exp: dict, item: dict, resp: AnswerResponse, text: str) -> dict:
    expected = {str(v).lower() for v in exp["values"]}
    missing = sorted(v for v in expected if v not in text)
    extra: list[str] = []
    kind = _set_kind(exp["values"])
    if kind:
        asked = item[
            "question"
        ].lower()  # 질문에 나온 항목(예: 대체 부품을 묻는 원래 휠)은 추가 항목이 아니다
        extra = sorted(v for v in _found_items(kind, text) - expected if v not in asked)
    found = len(expected) - len(missing)
    precision = found / (found + len(extra)) if found + len(extra) else None
    exact = not missing and not extra
    tool = None
    if resp.mode == "kg_tools":
        panels = "\n".join(
            [p.text for p in resp.graph_paths]
            + [f"{c.label} {c.formula}" for c in resp.calculations]
            + [f"{d.doc_path} {' '.join(d.linked_parts)}" for d in resp.documents]
        ).lower()
        tool = all(v in panels or v in text for v in expected) if expected else None
    detail = "모두 포함" if not missing else f"빠진 값 {missing}"
    if extra:
        detail += f" · 추가 항목 {extra}"
    return {
        "answer_correct": exact,
        "tool_correct": tool,
        "reason": "" if exact else ("missing_item" if missing else "extra_item"),
        "detail": detail,
        "precision": precision,
        "recall": found / len(expected) if expected else None,
    }


def _score_doc(exp: dict, resp: AnswerResponse, text: str) -> dict:
    path = exp["path"].lower()
    cited = text + "\n" + "\n".join(n.doc_path.lower() for n in resp.doc_notes)
    in_docs = any(path in d.doc_path.lower() for d in resp.documents)
    correct = path in cited
    return {
        "answer_correct": correct,
        "tool_correct": in_docs if resp.mode != "llm_only" else None,
        "evidence_correct": in_docs,
        "reason": "" if correct else ("no_evidence" if not in_docs else "wrong_value"),
        "detail": f"정답 문서 {exp['path']} · 근거 목록 {'있음' if in_docs else '없음'}",
    }


# ─── [Hands-on P2-Ch8-1 기준 문항 실행과 오류 분석] 시작 ───
def score(item: dict, resp: AnswerResponse) -> dict:
    """문항 하나를 채점한다. 반환: {passed, answer_correct, tool_correct, answerability, reason, detail, …}"""
    exp = item["expected"]
    base = {
        "scoring_version": SCORING_VERSION,
        "answerability": _answerability(resp),
        "verification_status": resp.verification.status,  # 출력 검사 판정 — 정답 채점과 따로 남긴다
        "tool_correct": None,
        "evidence_correct": None,
        "precision": None,
        "recall": None,
    }
    if resp.status != "completed":
        why = (
            resp.error.message
            if resp.error
            else (resp.pending_question.prompt if resp.pending_question else "")
        )
        return base | {
            "passed": False,
            "answer_correct": False,
            "reason": "not_answered",
            "detail": f"{resp.status}: {why}"[:200],
        }
    text = (resp.conclusion or "").lower()
    if exp["type"] == "number":
        r = _score_number(exp, resp, text)
    elif exp["type"] == "set":
        r = _score_set(exp, item, resp, text)
    elif exp["type"] == "doc":
        r = _score_doc(exp, resp, text)
    else:
        raise ValueError(f"모르는 정답 형식 {exp['type']}")
    if not r["answer_correct"] and base["answerability"] == "abstained":
        r["reason"] = "abstained"  # 근거 부족으로 답을 보류한 경우는 틀린 값을 낸 경우와 따로 센다
    return base | r | {"passed": r["answer_correct"]}


# ─── [Hands-on P2-Ch8-1] 끝 ───
