"""업무 함수를 MCP 도구로 노출하는 서버 (Part 2 Ch6-2 계산 도구 MCP 연결).

실습 구조에서 MCP는 "에이전트(LLM)가 호출할 수 있는 검증된 함수 목록"이다.
수량·원가 계산은 LLM이 아니라 여기 등록된 Python 함수가 수행하고, LLM은 어떤 도구를
부를지 고르고 결과를 설명만 한다. 이 분리가 실습의 핵심 메시지다 (정의서 7.1).

도구 11개: 상태 확인 2개(ping, neo4j_status) + 업무 도구 9개(tools/bom_tools.py, 설계 덱 40장)
전송 방식은 Streamable HTTP이며 경로는 /mcp 다 (정의서 4절).
에이전트는 같은 서버 객체를 메모리 안에서 바로 부를 수도 있다 (workflows/gateway.py 의 inprocess 모드).

실행:  uv run python -m mfg_bom_agent.mcp_server
"""

from __future__ import annotations

from functools import lru_cache

from fastmcp import FastMCP
from neo4j import Driver

from mfg_bom_agent.config import get_settings
from mfg_bom_agent.contracts import tools as c
from mfg_bom_agent.graph.client import QueryRecorder, make_driver, server_info
from mfg_bom_agent.tools import bom_tools as t

mcp = FastMCP("mfg-bom-agent")


@lru_cache
def _driver() -> Driver:
    """도구 호출마다 연결을 새로 맺지 않도록 드라이버 하나를 재사용한다 (드라이버가 연결 풀을 관리한다)."""
    return make_driver()


def _traced(fn, *args):
    """업무 도구를 부르고, 그 호출이 실행한 Cypher 를 결과의 queries 에 담는다 (화면 처리 과정에서 복사용)."""
    rec = QueryRecorder(_driver())
    out = fn(rec, *args)
    out.queries = [c.CypherQuery(**q) for q in rec.log]
    return out


@mcp.tool
def ping() -> dict[str, str]:
    """서버 생존 확인. 설정이 제대로 읽혔는지 데이터 버전과 함께 돌려준다."""
    s = get_settings()
    return {"status": "ok", "dataset_version": s.dataset_version, "app_env": s.app_env}


@mcp.tool
def neo4j_status() -> dict:
    """MCP 서버에서 Neo4j까지 연결되는지 확인한다. 버전·에디션·노드 수를 돌려준다."""
    return server_info()


# ─── [Hands-on P2-Ch6-2 계산 도구 MCP 연결] 시작 ───
# 도구 설명(docstring)은 에이전트가 도구를 고를 때 읽는 문장이다. 입력 단위와 기준 시점을 분명히 적는다.


@mcp.tool
def find_part(query: str, revision: str | None = None) -> c.FindPartResult:
    """부품 이름 · 약칭 · 품번(SKU)으로 부품을 찾는다. 후보가 여럿이면 ambiguous=true 와 후보 목록을 돌려준다.
    resolved 에는 공급사별 팩당 단가 · 팩 크기 · MOQ · 관측일이 함께 들어 있다."""
    return _traced(t.find_part, query, revision)


@mcp.tool
def where_used(part: str, revision: str | None = None) -> c.WhereUsedResult:
    """부품(품번)이 선택한 BOM 판에서 어느 어셈블리 · 제품에 쓰이는지와 라인별 원천 수량 · 팩 크기 · 배수를 돌려준다.
    revision 이 null 이면 최신 판."""
    return _traced(t.where_used, part, revision)


@mcp.tool
def bom_explode(
    units: int = 1,
    part: str | None = None,
    revision: str | None = None,
    scope: str = "mechanical",
    product: str = "OSR",
) -> c.BomExplodeResult:
    """BOM 을 전개해 생산 대수(units)만큼의 부품별 소요 낱개 수를 계산한다.
    낱개 수 = 원천 수량 × 팩 크기 × 어셈블리 배수 × 대수. part 를 주면 그 부품만. scope: mechanical · electrical · all"""
    return _traced(t.bom_explode, product, units, revision, part, scope)


@mcp.tool
def purchase_quantity(
    part: str,
    required_each: str | None = None,
    units: int | None = None,
    supplier: str | None = None,
    revision: str | None = None,
) -> c.PurchaseQuantityResult:
    """소요 낱개 수(required_each) 또는 생산 대수(units)를 받아 구매 팩 수와 구매 금액을 계산한다.
    구매 팩 수 = max(올림(소요 낱개 ÷ 팩 크기), MOQ). 소요 원가와 구분되는 실제 구매 금액이다."""
    return _traced(t.purchase_quantity, part, required_each, units, supplier, revision)


@mcp.tool
def cost_rollup(
    units: int = 1,
    revision: str | None = None,
    scope: str = "mechanical",
    items: list[dict] | None = None,
    price_overrides: dict[str, str] | None = None,
    product: str = "OSR",
) -> c.CostRollupResult:
    """소요 원가(팩 올림 · MOQ 미반영)를 계산한다. 기본은 제품 전체와 어셈블리별 합계.
    items=[{"part": 품번, "qty_each": 낱개 수}] 를 주면 선택 부품비만 계산한다 (교체 부품비 · 단종 부품 소요 금액).
    price_overrides={품번: 팩당 단가} 로 단가를 바꿔 비교할 수 있다."""
    return _traced(t.cost_rollup, product, units, revision, scope, items, price_overrides)


@mcp.tool
def revision_diff(rev_a: str, rev_b: str) -> c.RevisionDiffResult:
    """두 BOM 판(커밋 ID)의 라인 차이(추가 · 삭제 · 수량 변경)와 그 사이의 교육용 ECN 목록을 돌려준다."""
    return _traced(t.revision_diff, rev_a, rev_b)


@mcp.tool
def change_impact(
    change_type: str,
    part: str | None = None,
    ecn: str | None = None,
    value: str | None = None,
    units: int = 1,
    revision: str | None = None,
) -> c.ChangeImpactResult:
    """변경 영향 계산. change_type:
    - "price_percent": part 의 단가를 value% 바꿨을 때 units 대 기준 소요 원가 전후 · 차이
    - "discontinue"  : part 단종 가정 시 영향 후보(상위 어셈블리 · 제품), 소요 수량, 소요 금액 (추가 비용은 미확인)
    - "ecn"          : ecn(ECN ID 또는 변경 후 판 ID) 전후 판의 원가 차이와 바뀐 어셈블리"""
    return _traced(t.change_impact, change_type, part, ecn, value, units, revision)


@mcp.tool
def supply_risk(
    supplier: str | None = None,
    part: str | None = None,
    revision: str | None = None,
    qty_each: str | None = None,
) -> c.SupplyRiskResult:
    """공급 리스크. supplier 를 주면 그 공급사가 멈출 때 살 곳이 없는 부품(등록 공급사 1곳)과 영향 어셈블리,
    part 를 주면 그 부품의 등록 공급사 · 단일 공급 여부 · 대체 가능 부품과 호환 조건을 돌려준다 (규칙 R1).
    part 와 qty_each(필요 낱개 수)를 함께 주면 대체 부품마다 같은 수량의 부품비와 현재 부품 대비 차이도 계산한다."""
    return _traced(t.supply_risk, supplier, part, revision, qty_each)


@mcp.tool
def search_docs(
    query: str, k: int = 5, source: str | None = None, mode: str = "hybrid"
) -> c.SearchDocsResult:
    """정비 · 조립 문서와 GitHub 이슈를 BM25 키워드 + 벡터 검색(RRF 결합)으로 찾고, 문서에 연결된 부품과
    사용 어셈블리를 돌려준다 (CQ-15). 결과마다 검색별 순위(ranks: bm25 · vector)가 있다.
    query 는 영어 키워드가 좋다 (예: "corner wheels will not turn servo gear"). source: readme · issue · null
    mode: hybrid(기본) · bm25 · vector — 두 검색을 따로 비교할 때만 바꾼다."""
    return _traced(t.search_docs, query, k, source, mode)


# ─── [Hands-on P2-Ch6-2] 끝 ───


def main() -> None:
    s = get_settings()
    mcp.run(transport="http", host=s.mcp_host, port=s.mcp_port, path="/mcp")


if __name__ == "__main__":
    main()
