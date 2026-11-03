"""온톨로지 정의(ontology/schema.yaml)를 읽고, 제약 조건과 검증 쿼리를 만든다 (Part 2 Ch3-2).

그래프에 관계가 들어 있다고 그것이 곧 온톨로지는 아니다. 의미 정의(schema.yaml)가 따로 있고,
데이터가 그 정의를 지키는지 검사할 수 있어야 한다. 이 모듈이 그 검사를 맡는다.

- constraint_statements(): 클래스별 ID 고유성 제약 (Neo4j CONSTRAINT)
- validation_checks()    : 중복 · 순환 · 누락 · Domain/Range 위반을 찾는 Cypher 목록
- run_validation()       : 검사를 실행해 위반 건수를 돌려준다 (0 이면 통과)
- schema_brief()         : 에이전트 프롬프트에 넣을 짧은 스키마 설명
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from neo4j import Driver

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "ontology" / "schema.yaml"


@lru_cache
def load_schema() -> dict:
    """schema.yaml 을 읽는다. 프로세스당 한 번만 읽는다."""
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


def constraint_statements() -> list[str]:
    """클래스마다 ID 고유성 제약을 만드는 Cypher. 라벨 · 속성 이름은 schema.yaml 에서만 온다."""
    stmts = []
    for label, spec in load_schema()["classes"].items():
        key = spec["id"]
        stmts.append(
            f"CREATE CONSTRAINT {label.lower()}_{key}_unique IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.{key} IS UNIQUE"
        )
    return stmts


@dataclass(frozen=True)
class Check:
    name: str
    description: str
    cypher: str  # 위반 건수를 violations 라는 이름으로 돌려준다


# ─── [Hands-on P2-Ch3-2 제조 온톨로지와 검증 규칙] 시작 ───
def validation_checks() -> list[Check]:
    """schema.yaml 에서 검증 쿼리를 만든다. 쿼리마다 위반 건수(violations)를 센다."""
    schema = load_schema()
    checks: list[Check] = []

    # 1) 필수 속성 누락 — 클래스 정의의 required 속성이 비어 있는 노드
    for label, spec in schema["classes"].items():
        cond = " OR ".join(f"n.{p} IS NULL" for p in spec["required"])
        checks.append(
            Check(
                f"required:{label}",
                f"{label} 필수 속성 누락",
                f"MATCH (n:{label}) WHERE {cond} RETURN count(n) AS violations",
            )
        )

    # 2) Domain/Range 위반 — 관계의 시작 · 끝 노드 라벨이 정의와 다른 경우
    for rel, spec in schema["relations"].items():
        dom = " OR ".join(f"a:{d}" for d in spec["domain"])
        rng = " OR ".join(f"b:{r}" for r in spec["range"])
        checks.append(
            Check(
                f"domain_range:{rel}",
                f"{rel} 의 시작 · 끝 노드 종류 위반",
                f"MATCH (a)-[:{rel}]->(b) WHERE NOT ({dom}) OR NOT ({rng}) "
                "RETURN count(*) AS violations",
            )
        )
        if "required" in spec:
            cond = " OR ".join(f"r.{p} IS NULL" for p in spec["required"])
            checks.append(
                Check(
                    f"rel_required:{rel}",
                    f"{rel} 관계 필수 속성 누락",
                    f"MATCH ()-[r:{rel}]->() WHERE {cond} RETURN count(r) AS violations",
                )
            )

    # 3) 카디널리티 — BOM 라인은 하위 품목 · 판을 정확히 하나씩 가진다
    checks.append(
        Check(
            "cardinality:BOMLine.REFERS_TO",
            "REFERS_TO 가 1개가 아닌 BOM 라인",
            "MATCH (l:BOMLine) WITH l, COUNT { (l)-[:REFERS_TO]->() } AS c "
            "WHERE c <> 1 RETURN count(l) AS violations",
        )
    )
    checks.append(
        Check(
            "cardinality:BOMLine.IN_REVISION",
            "IN_REVISION 이 1개가 아닌 BOM 라인",
            "MATCH (l:BOMLine) WITH l, COUNT { (l)-[:IN_REVISION]->() } AS c "
            "WHERE c <> 1 RETURN count(l) AS violations",
        )
    )

    # 4) 값 범위 — 수량은 0보다 크고, 배수는 1 이상의 정수
    checks.append(
        Check(
            "value:BOMLine.qty",
            "수량 0 이하 또는 배수 1 미만",
            "MATCH (l:BOMLine) WHERE l.raw_qty <= 0 OR l.multiplier < 1 "
            "RETURN count(l) AS violations",
        )
    )

    # 5) 순환 · 자기 참조 — 대체 관계가 돌고 돌면 "최신 부품"을 정할 수 없다
    checks.append(
        Check(
            "cycle:SUPERSEDES",
            "SUPERSEDES 자기 참조 또는 순환",
            "MATCH (p:Part)-[:SUPERSEDES*1..10]->(p) RETURN count(DISTINCT p) AS violations",
        )
    )
    checks.append(
        Check(
            "cycle:BOM",
            "BOM 구성 순환 (상위가 자기 하위에 다시 나타남)",
            "MATCH (a:Assembly)-[:HAS_BOM_LINE|REFERS_TO*2..12]->(a) "
            "RETURN count(DISTINCT a) AS violations",
        )
    )

    # 6) 중복 — 같은 판 · 같은 상위 · 같은 하위의 라인이 둘 이상
    checks.append(
        Check(
            "duplicate:BOMLine",
            "같은 판 · 상위 · 하위 조합의 중복 라인",
            "MATCH (p)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(c) "
            "WITH p, c, l.revision_id AS rev, count(l) AS n WHERE n > 1 "
            "RETURN count(*) AS violations",
        )
    )
    # 7) 판마다 최신 판은 정확히 하나
    checks.append(
        Check(
            "latest:Revision",
            "최신 판(is_latest)이 1개가 아님",
            "MATCH (r:Revision {is_latest: true}) WITH count(r) AS n "
            "RETURN CASE WHEN n = 1 THEN 0 ELSE 1 END AS violations",
        )
    )
    return checks


# ─── [Hands-on P2-Ch3-2] 끝 ───


def run_validation(driver: Driver) -> list[dict]:
    """검증 쿼리를 모두 실행한다. 반환: [{name, description, violations}]"""
    results = []
    for check in validation_checks():
        records, _, _ = driver.execute_query(check.cypher)
        results.append(
            {
                "name": check.name,
                "description": check.description,
                "violations": records[0]["violations"],
            }
        )
    return results


def schema_brief() -> str:
    """에이전트 시스템 프롬프트에 넣을 스키마 요약. 정의가 바뀌면 프롬프트도 같이 바뀐다."""
    schema = load_schema()
    lines = ["[온톨로지 클래스]"]
    lines += [f"- {k}: {v['definition']}" for k, v in schema["classes"].items()]
    lines.append("[관계]")
    for k, v in schema["relations"].items():
        lines.append(
            f"- ({'|'.join(v['domain'])})-[:{k}]->({'|'.join(v['range'])}): {v['definition']}"
        )
    return "\n".join(lines)
