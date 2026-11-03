"""화면의 Cypher 실행기 — 읽기 전용 (처리 과정 탭 "실행한 Cypher 쿼리").

도구가 보낸 쿼리를 화면에서 그대로 다시 실행하거나, 고쳐서 실행해 결과를 비교해 보는 용도다.
에이전트는 계속 MCP 도구로만 그래프에 접근한다. 이 모듈은 환경 점검처럼 화면이 직접 쓰는 예외이며, 읽기만 한다.

읽기 전용을 두 번 지킨다.
1. 쓰기 · 관리 명령(CREATE · MERGE · SET · DELETE · DROP · LOAD CSV · 쓰기 프로시저 등)은 보내기 전에 막는다
2. 읽기 트랜잭션(READ_ACCESS)으로 실행한다 — 1을 빠져나간 쓰기도 Neo4j 서버가 거부한다
결과는 최대 MAX_ROWS 행, 쿼리 하나는 TIMEOUT_S 초 안에 끝나야 한다.
"""

from __future__ import annotations

import re
import time
from typing import Any

import neo4j
from neo4j import Driver
from neo4j.graph import Node, Path, Relationship

MAX_ROWS = 100
TIMEOUT_S = 10

# 주석 · 문자열을 지운 뒤 찾는다 ("description: 'set up'" 같은 값에 걸리지 않게)
_WRITE = re.compile(
    r"\b(CREATE|MERGE|SET|DELETE|DETACH|REMOVE|DROP|FOREACH|LOAD\s+CSV|GRANT|DENY|REVOKE|ALTER|"
    r"START\s+DATABASE|STOP\s+DATABASE|TERMINATE)\b"
    r"|\bdb\.create\.|\bdb\.index\.fulltext\.(create|drop)|\bapoc\.(create|merge|refactor|periodic)",
    re.IGNORECASE,
)


def _strip(query: str) -> str:
    """주석과 문자열 값을 지운다. 쓰기 명령 검사용."""
    query = re.sub(r"//[^\n]*|/\*.*?\*/", " ", query, flags=re.DOTALL)
    return re.sub(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|`[^`]*`", "''", query)


def write_keyword(query: str) -> str | None:
    """쿼리에 쓰기 · 관리 명령이 있으면 그 낱말을 돌려준다. 없으면 None."""
    m = _WRITE.search(_strip(query))
    return m.group(0).upper() if m else None


def _value(v: Any) -> Any:
    """표로 보여 줄 수 있게 바꾼다. 노드 · 관계는 속성으로, 긴 벡터는 길이만."""
    if isinstance(v, Node):
        props = {k: _value(x) for k, x in v.items()}
        return {"labels": sorted(v.labels), **props}
    if isinstance(v, Relationship):
        return {"type": v.type, **{k: _value(x) for k, x in v.items()}}
    if isinstance(v, Path):
        return " → ".join(
            (n.get("name") or n.get("sku") or n.get("symbol") or next(iter(n.labels), "?"))
            for n in v.nodes
        )
    if isinstance(v, list):
        if len(v) > 20 and all(isinstance(x, (int, float)) for x in v):
            return f"[숫자 {len(v)}개]"  # 임베딩 벡터
        return [_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _value(x) for k, x in v.items()}
    if hasattr(v, "iso_format"):  # Neo4j 날짜 · 시각
        return v.iso_format()
    return v


def run_readonly(driver: Driver, query: str, params: dict | None = None) -> dict:
    """쿼리 하나를 읽기 전용으로 실행한다.

    반환: {ok, columns, rows, truncated, elapsed_ms, error}
    rows 는 [{열: 값}] — 노드는 속성 사전, 긴 벡터는 "[숫자 1024개]" 로 줄인다.
    """
    query = query.strip().rstrip(";").strip()
    if not query:
        return {"ok": False, "error": "실행할 쿼리가 비어 있습니다"}
    if ";" in _strip(query):
        return {"ok": False, "error": "쿼리는 한 번에 하나만 실행합니다 (; 로 나뉜 여러 문장)"}
    if word := write_keyword(query):
        return {
            "ok": False,
            "error": f"읽기 전용 실행기입니다. 쓰기 · 관리 명령({word})은 실행하지 않습니다",
        }

    @neo4j.unit_of_work(timeout=TIMEOUT_S)  # 오래 걸리는 쿼리는 서버가 끊는다
    def work(tx):
        result = tx.run(query, params or {})
        rows, truncated = [], False
        for i, record in enumerate(result):
            if i >= MAX_ROWS:
                truncated = True
                break
            rows.append({k: _value(v) for k, v in record.items()})
        return list(result.keys()), rows, truncated

    started = time.perf_counter()
    try:
        with driver.session(default_access_mode=neo4j.READ_ACCESS) as session:
            columns, rows, truncated = session.execute_read(work)
    except neo4j.exceptions.Neo4jError as exc:
        msg = exc.message or str(exc)
        if exc.code and "AccessMode" in exc.code:
            msg = "읽기 전용 실행기입니다. 그래프를 바꾸는 쿼리는 서버가 거부했습니다"
        return {"ok": False, "error": f"{msg} ({exc.code})"}
    except Exception as exc:  # noqa: BLE001 — 연결 오류 등도 화면에 그대로 보여 준다
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": True,
        "columns": columns,
        "rows": rows,
        "truncated": truncated,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "error": None,
    }
