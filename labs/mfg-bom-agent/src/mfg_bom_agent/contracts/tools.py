"""MCP 도구의 입력 · 출력 계약 (Part 2 Ch6, 설계 덱 40장).

모든 도구 출력은 다음을 공통으로 담는다.
- revision    : 조회 기준 BOM 판 (커밋 ID)
- as_of       : 가격 관측일. 원천에 실제 가격 기준일이 없어 price_date 는 항상 None("미상")
- assumptions : 계산에 쓴 가정 (교육용 MOQ, 단종 가정 등)
- warnings    : 결과를 해석할 때 주의할 점 (팩 표기 없음, 관측일 불일치 등)
- error/hint  : 입력 오류일 때만 채운다. 예외를 던지지 않고 에이전트가 다시 시도할 수 있게 돌려준다

금액 · 수량은 Decimal 이다. JSON 으로 나갈 때 문자열("6398.00")이 되어 소수 오차 없이 전달된다.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class CypherQuery(BaseModel):
    """도구가 Neo4j 에 실제로 보낸 쿼리. 화면의 처리 과정에서 복사해 Neo4j Browser 로 다시 실행해 볼 수 있다."""

    query: str
    params: dict = Field(default_factory=dict)
    calls: int = 1  # 같은 쿼리 · 같은 파라미터로 여러 번 부른 횟수


class ToolResult(BaseModel):
    revision: str | None = None
    as_of: date | None = None
    price_date: date | None = None  # 실제 가격 기준일 — 원천에 없어 항상 None
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    hint: str | None = None
    queries: list[CypherQuery] = Field(default_factory=list)  # 이 호출이 실행한 Cypher (실행 순서)


# ── find_part ──────────────────────────────────────────────
class Offer(BaseModel):
    supplier_id: str
    supplier: str
    supplier_origin: str
    supplier_sku: str
    unit_price: Decimal  # 팩당
    pack_size: int
    moq_packs: int
    lead_time_days: int
    observed_at: date
    terms_origin: str


class PartCandidate(BaseModel):
    part_id: str
    sku: str
    name: str
    score: float
    method: str
    in_latest: bool
    offers: list[Offer] = Field(default_factory=list)


class FindPartResult(ToolResult):
    query: str
    resolved: PartCandidate | None = None
    candidates: list[PartCandidate] = Field(default_factory=list)
    ambiguous: bool = False


# ── where_used ─────────────────────────────────────────────
class UsageLine(BaseModel):
    assembly: str
    raw_qty: Decimal  # 원천 수량 (팩 단위일 수 있음)
    pack_size: int
    qty_each: Decimal  # 낱개 환산 = raw_qty × pack_size
    multiplier: int
    each_per_product: Decimal  # 제품 1대당 낱개 수 = qty_each × multiplier (도구가 계산)
    unit: str
    source_ref: str


class UsagePath(BaseModel):
    product: str
    assemblies: list[str]
    text: str  # 화면용 텍스트 경로


class Replacement(BaseModel):
    sku: str
    name: str
    ecn: str
    effective_date: str


class WhereUsedResult(ToolResult):
    part_id: str
    sku: str
    name: str
    lines: list[UsageLine] = Field(default_factory=list)
    paths: list[UsagePath] = Field(default_factory=list)
    replaced: list[Replacement] = Field(
        default_factory=list
    )  # 이 부품이 대체한 이전 부품 (SUPERSEDES, CQ-08)
    replaced_by: list[Replacement] = Field(default_factory=list)  # 이 부품을 대체한 새 부품


# ── bom_explode ────────────────────────────────────────────
class ExplodedItem(BaseModel):
    part_id: str
    sku: str
    name: str
    assembly: str
    raw_qty_per_assembly: Decimal
    pack_size: int
    pack_basis: str
    multiplier: int
    each_per_product: Decimal  # 제품 1대당 낱개 수 = raw_qty × pack_size × multiplier
    required_each: Decimal  # 생산 대수 반영
    formula: str


class BomExplodeResult(ToolResult):
    product: str
    units: int
    scope: str
    items: list[ExplodedItem] = Field(default_factory=list)
    total_lines: int = 0


# ── purchase_quantity ──────────────────────────────────────
class PurchaseQuantityResult(ToolResult):
    part_id: str
    sku: str
    supplier_id: str
    required_each: Decimal
    pack_size: int
    packs_needed: int  # 올림(소요 낱개 ÷ 팩 크기)
    moq_packs: int
    packs_to_buy: int  # max(packs_needed, MOQ)
    unit_price: Decimal  # 팩당
    purchase_amount: Decimal
    leftover_each: Decimal  # 사고 남는 낱개
    formula: str


# ── cost_rollup ────────────────────────────────────────────
class CostLine(BaseModel):
    part_id: str
    sku: str
    assembly: str | None = None
    qty: Decimal
    qty_unit: Literal["pack", "ea"]
    unit_price: Decimal
    price_unit: Literal["pack", "ea"]
    amount: Decimal
    price_overridden: bool = False


class CostRollupResult(ToolResult):
    product: str
    units: int
    scope: str
    basis: Literal["requirement"] = "requirement"  # 소요 원가 (팩 올림 · MOQ 미반영)
    by_assembly: dict[str, Decimal] = Field(default_factory=dict)
    lines: list[CostLine] = Field(default_factory=list)
    total: Decimal = Decimal(0)
    missing_prices: list[str] = Field(default_factory=list)
    formula: str = ""


# ── revision_diff ──────────────────────────────────────────
class LineChange(BaseModel):
    change_type: Literal["added", "removed", "qty_changed"]
    assembly: str
    sku: str
    name: str
    before_raw_qty: Decimal | None = None
    after_raw_qty: Decimal | None = None
    before_multiplier: int | None = None
    after_multiplier: int | None = None


class RevisionDiffResult(ToolResult):
    rev_a: str
    rev_b: str
    valid_from_b: str | None = None  # rev_b 의 저장소상 적용 구간 [시작, 종료)
    valid_to_b: str | None = None  # None = 현재 유효
    ecns: list[str] = Field(default_factory=list)
    changes: list[LineChange] = Field(default_factory=list)


# ── change_impact ──────────────────────────────────────────
class ImpactTarget(BaseModel):
    level: str
    target_id: str
    name: str


class ChangeImpactResult(ToolResult):
    part_id: str | None = None
    sku: str | None = None
    ecn: str | None = None
    revision_from: str | None = None  # ECN 비교일 때 변경 전 판
    change_type: Literal["price_percent", "discontinue", "ecn"]
    units: int
    impact_candidates: list[ImpactTarget] = Field(default_factory=list)
    required_each: Decimal | None = None
    requirement_cost: Decimal | None = None  # 소요 금액 (단가 × 소요 수량)
    cost_before: Decimal | None = None
    cost_after: Decimal | None = None
    cost_diff: Decimal | None = None
    extra_cost: str = "미확인"  # 단종 · 교체에 따른 추가 비용은 조건이 없어 계산하지 않는다
    formula: str = ""


# ── supply_risk ────────────────────────────────────────────
class AlternatePart(BaseModel):
    sku: str
    name: str
    compatibility: str
    requires_rework: bool
    source_doc: str
    # 문서에 적힌 대체 부품 가격 (BOM 밖 부품이라 부품표 단가가 없다). 없으면 None
    pack_price: Decimal | None = None
    pack_size: int | None = None
    price_note: str = ""
    # qty_each 를 주면 채운다: 같은 수량을 대체 부품으로 살 때의 부품비와 현재 부품 대비 차이
    required_packs: int | None = None
    alternate_cost: Decimal | None = None
    current_cost: Decimal | None = None
    cost_diff: Decimal | None = None
    formula: str = ""


class SupplyRiskPart(BaseModel):
    sku: str
    name: str
    suppliers: list[str]
    single_registered_supplier: bool
    assemblies: list[str]


class SupplyRiskResult(ToolResult):
    supplier_id: str | None = None
    part_sku: str | None = None
    parts: list[SupplyRiskPart] = Field(default_factory=list)
    alternates: list[AlternatePart] = Field(default_factory=list)
    affected_assemblies: list[str] = Field(default_factory=list)
    rule: str = "R1 RegisteredSingleSupplier"


# ── search_docs ────────────────────────────────────────────
class DocHit(BaseModel):
    doc_id: str
    path: str
    title: str
    line: int | None
    source: str
    excerpt: str
    score: float  # RRF 결합 점수
    rank: int | None = None  # 결합 순위 (mode 가 bm25 · vector 면 그 검색의 순위)
    ranks: dict[str, int]  # 검색별 순위 {"bm25": 5, "vector": 3} — 한쪽에만 나오면 그쪽만
    scores: dict[str, float] = Field(
        default_factory=dict
    )  # 검색별 원 점수 (BM25 점수 · 코사인 유사도)
    parts: list[dict]


class SearchDocsResult(ToolResult):
    query: str
    provider: str  # 색인 공급자 (이전 호환)
    mode: str = "hybrid"  # 요청한 검색 방식
    effective_mode: str | None = None  # 실제로 실행한 검색 방식 (임베딩 장애면 bm25, 실패면 None)
    index_provider: str | None = None
    query_provider: str | None = None  # 질문 임베딩 공급자 (BM25 만 썼으면 None)
    hits: list[DocHit] = Field(default_factory=list)
