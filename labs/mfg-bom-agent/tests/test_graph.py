"""온톨로지 검증 · CQ · 도구 통합 테스트 (Part 2 Ch3-2 · Ch4-2 · Ch6). 적재된 Neo4j 가 필요하다.

Neo4j 에 연결할 수 없으면 건너뛴다. 먼저 scripts/load_graph.py · scripts/build_index.py 를 실행한다.
기대값은 evaluation/reference.py 가 CSV 에서 독립적으로 계산한 값이다.
"""

from decimal import Decimal

import pytest

from mfg_bom_agent import ontology
from mfg_bom_agent.evaluation import reference as R
from mfg_bom_agent.graph.cq import run_cq
from mfg_bom_agent.tools import bom_tools as t


@pytest.fixture(scope="module")
def driver():
    from mfg_bom_agent.graph.client import make_driver

    d = make_driver()
    try:
        d.verify_connectivity()
        if not d.execute_query("MATCH (p:Part) RETURN count(p) AS n").records[0]["n"]:
            pytest.skip("그래프가 비어 있음 — scripts/load_graph.py 먼저 실행")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Neo4j 연결 불가: {exc}")
    yield d
    d.close()


def test_ontology_validation_has_no_violations(driver):
    failed = [r for r in ontology.run_validation(driver) if r["violations"]]
    assert failed == []


def test_cq01_where_used(driver):
    rows = run_cq(driver, "CQ-01", part="2000-0025-0002")
    assert {a for r in rows for a in r["assemblies"]} == R.where_used("2000-0025-0002")


def test_cq04_shared_parts(driver):
    assert {r["sku"] for r in run_cq(driver, "CQ-04")} == R.shared_parts()


def test_cq08_supersedes(driver):
    assert {r["old_sku"] for r in run_cq(driver, "CQ-08", part="5203-2402-0027")} == {
        "5202-2402-0027"
    }


def test_cq14_revision_interval(driver):
    row = run_cq(driver, "CQ-14", revision_id="72edc6e")[0]
    assert (row["valid_from"], row["valid_to"]) == R.revision_interval("72edc6e")


def test_cost_rollup_matches_reference(driver):
    res = t.cost_rollup(driver)
    assert res.total == R.cost(1) == Decimal("1330.38")
    assert res.by_assembly["drive wheel"] == R.cost(1, assembly="drive wheel")


def test_servo_discontinue_scenario(driver):
    res = t.change_impact(driver, "discontinue", part="2000-0025-0002", units=50)
    assert res.required_each == 200 and res.requirement_cost == Decimal("6398.00")
    assert res.extra_cost == "미확인"


def test_motor_price_change(driver):
    res = t.change_impact(driver, "price_percent", part="5203-2402-0027", value="15", units=100)
    assert res.cost_diff == R.price_change_diff("5203-2402-0027", "15", 100) == Decimal("3869.10")


def test_tool_reports_errors_instead_of_raising(driver):
    res = t.where_used(driver, "9999-9999-9999")
    assert res.error and res.hint


def test_find_part_asks_when_ambiguous(driver):
    assert t.find_part(driver, "spacer").ambiguous
    assert t.find_part(driver, "서보").resolved.sku == "2000-0025-0002"


def _cq15(driver, mode: str) -> list[dict]:
    """CQ-15 를 Neo4j Browser 와 같은 방식(저장된 예시 질문 CQ-11 의 검색어 · 벡터)으로 실행한다."""
    return run_cq(driver, "CQ-15", example="CQ-11", q=None, qvec=None, mode=mode, k=10, source=None)


def test_cq15_hybrid_search_combines_bm25_and_vector(driver):
    """CQ-15: '코너 바퀴가 돌지 않음' 은 BM25 5위 · 벡터 3위인 서보 기어 교체 문서를 RRF 결합으로 1위에 올린다."""
    meta = driver.execute_query("MATCH (m:LabMeta) RETURN m.embedding_provider AS p").records[0][
        "p"
    ]
    if not (meta or "").startswith("voyage"):
        pytest.skip(
            "Voyage 임베딩으로 색인했을 때의 순위다 — scripts/build_index.py 를 Voyage 키로 실행"
        )
    want = "mechanical/servo_gear_replacement/README.md"

    def pos(rows):
        return next(i for i, r in enumerate(rows, 1) if r["path"] == want)

    bm25, vector, hybrid = (_cq15(driver, m) for m in ("bm25", "vector", "hybrid"))
    assert pos(hybrid) == 1 and pos(hybrid) < pos(bm25) and pos(hybrid) < pos(vector)
    top = hybrid[0]
    # 두 검색이 모두 기여했다: 1위 문서에 BM25 순위와 벡터 순위가 함께 있다
    assert top["bm25_rank"] is not None and top["vector_rank"] is not None
    # 그래프 확장: 문서에 연결된 부품(서보)과 그 사용 어셈블리까지 따라온다
    servo = next(p for p in top["parts"] if p["sku"] == "2000-0025-0002")
    assert servo["assemblies"]


def test_cq15_modes_use_only_their_search(driver):
    """mode 가 bm25 · vector 면 그 검색의 순위만 나온다 (하이브리드 효과를 비교할 때 쓴다)."""
    assert all(r["vector_rank"] is None for r in _cq15(driver, "bm25"))
    assert all(r["bm25_rank"] is None for r in _cq15(driver, "vector"))
