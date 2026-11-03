"""CQ(Competency Question) 쿼리 실행기 (Part 2 Ch4-2).

queries/cq_XX_*.cypher 파일을 읽어 파라미터와 함께 실행한다. CQ 하나 = 쿼리 하나 = 테스트 하나.
쿼리가 "WITH v" 로 시작하면 조회 기준 판을 고르는 공통 조각(_revision.cypher)을 앞에 붙인다.

도구(tools/)와 테스트(tests/test_cq.py)가 모두 이 함수를 통해 그래프를 조회한다.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from neo4j import Driver

from mfg_bom_agent.ontology import load_schema

QUERY_DIR = Path(__file__).resolve().parents[3] / "queries"

# Lucene 문법에서 특별한 뜻이 있는 문자. 사용자 입력을 전문 검색에 넣기 전에 이스케이프한다.
_LUCENE_SPECIAL = re.compile(r'([+\-!(){}\[\]^"~*?:\\/]|&&|\|\|)')


def lucene_escape(text: str) -> str:
    """전문 검색어에서 Lucene 특수문자를 이스케이프한다. 빈 값은 매칭되지 않는 단어로 바꾼다."""
    cleaned = _LUCENE_SPECIAL.sub(r"\\\1", (text or "").strip())
    return cleaned or "__empty__"


def _strip_comments(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("//"))


@lru_cache
def _query_text(cq_id: str) -> str:
    entry = next(q for q in load_schema()["competency_questions"] if q["id"] == cq_id)
    body = (QUERY_DIR / entry["query"]).read_text(encoding="utf-8")
    code = _strip_comments(body)
    if code.lstrip().startswith("WITH v"):
        code = (
            _strip_comments((QUERY_DIR / "_revision.cypher").read_text(encoding="utf-8"))
            + "\n"
            + code
        )
    # 맨 앞에 CQ 번호 · 질문을 주석으로 단다. 화면의 처리 과정에서 어느 CQ 쿼리인지 보이게 하기 위해서다
    return f"// {cq_id} {entry['question']} (queries/{entry['query']})\n{code.strip()}"


def run_cq(driver: Driver, cq_id: str, **params: Any) -> list[dict[str, Any]]:
    """CQ 쿼리를 실행해 결과 행을 dict 목록으로 돌려준다.

    공통 파라미터 기본값: revision=None(최신 판), domain=None.
    name 이 있으면 전문 검색용 lucene 파라미터를 자동으로 만든다.
    """
    params.setdefault("revision", None)
    params.setdefault("domain", None)
    for key in ("part", "assembly", "ecn", "name", "revision_id"):
        params.setdefault(key, None)
    if params.get("name") is not None:
        params["lucene"] = lucene_escape(params["name"])
    else:
        params.setdefault("lucene", "__empty__")
    records, _, _ = driver.execute_query(_query_text(cq_id), params)
    return [r.data() for r in records]
