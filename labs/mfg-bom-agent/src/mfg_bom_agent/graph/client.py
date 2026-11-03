"""Neo4j 연결을 만드는 유일한 장소.

지식 그래프(Neo4j)에 접근하는 코드는 모두 이 모듈의 드라이버를 쓴다.
적재 스크립트(scripts/init_data.py), MCP 도구, 환경 점검이 같은 연결 설정을 공유하므로
접속 정보가 바뀌어도 고칠 곳은 config.py 한 곳이다.

정의서 4절: 앱은 MCP를 통해 데이터에 접근하고, 적재·점검 스크립트만 드라이버를 직접 쓴다.
"""

from __future__ import annotations

import re
import textwrap
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from neo4j import Driver, GraphDatabase

from mfg_bom_agent.config import get_settings


def make_driver() -> Driver:
    """설정값으로 Bolt 드라이버를 만든다. 연결은 첫 쿼리 때 맺어진다."""
    s = get_settings()
    # notifications_min_severity="OFF": "값이 비어 있는 속성 키" 같은 서버 안내 메시지가 실습 출력을
    #   덮지 않게 끈다. 쿼리 문제를 찾을 때는 "WARNING" 으로 바꿔 확인한다.
    return GraphDatabase.driver(
        s.neo4j_uri,
        auth=(s.neo4j_username, s.neo4j_password.get_secret_value()),
        connection_timeout=10,
        notifications_min_severity="OFF",
    )


class QueryRecorder:
    """드라이버를 감싸 execute_query 로 보낸 Cypher 와 파라미터를 기록한다 (그 밖의 기능은 그대로 넘긴다).

    도구 한 번을 부를 때마다 새로 만들어, 그 호출이 실행한 쿼리만 결과에 담는다 (mcp_server.py).
    """

    def __init__(self, driver: Driver) -> None:
        self._driver = driver
        self.log: list[dict[str, Any]] = []

    def execute_query(self, query, parameters_=None, *args, **kwargs):
        # 드라이버 설정 인자(database_ · routing_ 등)는 이름이 _ 로 끝난다. 나머지가 쿼리 파라미터다
        params = {**(parameters_ or {}), **{k: v for k, v in kwargs.items() if not k.endswith("_")}}
        text = textwrap.dedent(str(query)).strip()
        # 쿼리에 실제로 쓰인 파라미터만 남긴다 (CQ 실행기는 공통 기본값을 모두 넘긴다)
        params = {k: v for k, v in params.items() if re.search(rf"\${k}\b", text)}
        for q in self.log:
            if q["query"] == text and q["params"] == _printable(params):
                q["calls"] += 1
                break
        else:
            self.log.append({"query": text, "params": _printable(params), "calls": 1})
        return self._driver.execute_query(query, parameters_, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._driver, name)


def _printable(params: dict[str, Any]) -> dict[str, Any]:
    """화면에 보여 줄 파라미터. 임베딩 벡터도 그대로 남겨, 복사한 쿼리가 같은 결과를 내게 한다.

    벡터는 소수 6자리로 줄인다 (1024개 숫자를 다 적어도 순위는 그대로이고 글자 수는 절반 가까이 준다).
    """
    out = {}
    for k, v in params.items():
        if isinstance(v, list) and len(v) > 20 and all(isinstance(x, float) for x in v[:5]):
            out[k] = [round(x, 6) for x in v]
        elif isinstance(v, (str, int, float, bool, type(None), list, dict)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


@contextmanager
def driver_session() -> Iterator[Driver]:
    """`with driver_session() as driver:` 블록 안에서 드라이버를 쓰고 끝나면 닫는다.

    `verify_connectivity()`를 먼저 호출해 DB가 아직 준비되지 않았으면 쿼리 전에 바로 실패하게 한다.
    """
    driver = make_driver()
    try:
        driver.verify_connectivity()
        yield driver
    finally:
        driver.close()


def server_info() -> dict[str, Any]:
    """DB 버전·에디션·전체 노드 수를 돌려준다. 환경 점검 화면과 MCP `neo4j_status` 도구가 쓴다."""
    with driver_session() as driver:
        records, _, _ = driver.execute_query(
            "CALL dbms.components() YIELD name, versions, edition "
            "RETURN name, versions[0] AS version, edition"
        )
        components = records[0].data() if records else {}

        count_records, _, _ = driver.execute_query("MATCH (n) RETURN count(n) AS nodes")
        nodes = count_records[0]["nodes"] if count_records else 0

        return {**components, "nodes": nodes}
