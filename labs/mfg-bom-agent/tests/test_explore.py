"""화면 Cypher 실행기 테스트 (처리 과정 탭). 쓰기 차단은 DB 없이, 실제 실행은 Neo4j 가 있을 때만 확인한다."""

from pathlib import Path

import pytest

from mfg_bom_agent.graph.explore import run_readonly, write_keyword

QUERIES = Path(__file__).resolve().parents[1] / "queries"


def test_write_commands_are_blocked_before_sending():
    for q in (
        "CREATE (n:X) RETURN n",
        "MATCH (p:Part) SET p.name = 'x'",
        "MATCH (n) DETACH DELETE n",
        "LOAD CSV FROM 'file:///a.csv' AS r RETURN r",
        "CALL db.create.setNodeVectorProperty(n, 'e', [1])",
        "DROP INDEX doc_vector",
    ):
        assert write_keyword(q), q
        assert run_readonly(None, q)["ok"] is False  # 드라이버까지 가지 않는다


def test_read_queries_and_words_inside_strings_are_allowed():
    assert write_keyword("MATCH (d:Document) WHERE d.text CONTAINS 'set screw' RETURN d") is None
    assert write_keyword("// 주석의 CREATE 는 괜찮다\nMATCH (n) RETURN n LIMIT 1") is None
    for f in QUERIES.glob("cq_*.cypher"):  # 실습의 CQ 쿼리는 모두 읽기 쿼리다
        assert write_keyword(f.read_text(encoding="utf-8")) is None, f.name


def test_multiple_statements_are_rejected():
    assert "하나만" in run_readonly(None, "MATCH (n) RETURN n; MATCH (m) RETURN m")["error"]


@pytest.fixture
def driver():
    from mfg_bom_agent.graph.client import make_driver

    d = make_driver()
    try:
        d.verify_connectivity()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Neo4j 연결 불가: {exc}")
    return d


def test_runs_read_query_and_truncates(driver):
    r = run_readonly(
        driver, "MATCH (p:Part {sku: $sku}) RETURN p, p.sku AS sku", {"sku": "2000-0025-0002"}
    )
    assert r["ok"] and r["columns"] == ["p", "sku"] and r["rows"][0]["sku"] == "2000-0025-0002"
    assert "Part" in r["rows"][0]["p"]["labels"]
    big = run_readonly(driver, "UNWIND range(1, 500) AS i RETURN i")
    assert big["ok"] and len(big["rows"]) == 100 and big["truncated"]


def test_hidden_write_is_rejected_by_server(driver):
    """문자열 안에 숨긴 쓰기는 낱말 검사를 지나가도 읽기 트랜잭션이라 서버가 거부한다."""
    q = "CALL apoc.cypher.doIt('CREATE (x:__probe)', {}) YIELD value RETURN value"
    assert run_readonly(driver, q)["ok"] is False
    assert driver.execute_query("MATCH (n:__probe) RETURN count(n) AS c").records[0]["c"] == 0
