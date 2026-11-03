"""Hybrid Search 임베딩 장애 회귀 테스트 (Part 2 Ch5-2). Neo4j · 임베딩 API 없이 실행한다.

검토 보고서 F5: 색인은 Voyage 인데 질문 임베딩이 실패하면 질문만 hash 벡터로 바꾸던 문제.
테스트 ID(R01 …)는 실행 계획서 6절의 번호다.
"""

import pytest

from mfg_bom_agent.retrieval import hybrid
from mfg_bom_agent.retrieval.embeddings import EmbeddingUnavailable, HashEmbedder


class FakeResult(list):
    """driver.execute_query 결과 흉내 (records, summary, keys)."""


class FakeDriver:
    """LabMeta 조회만 돌려주는 가짜 드라이버."""

    def __init__(self, provider: str, dim: int):
        self.meta = [{"p": provider, "d": dim}]

    def execute_query(self, query, *args, **kwargs):
        return self.meta, None, None


@pytest.fixture
def cq_calls(monkeypatch):
    """CQ-15 실행을 가로채 어떤 방식 · 벡터로 불렸는지 기록한다."""
    calls = []

    def fake_run_cq(driver, cq, **params):
        calls.append(params)
        return [
            {
                "doc_id": "D1",
                "path": "a/README.md",
                "title": "t",
                "line": 1,
                "source": "readme",
                "text": "corner servo",
                "score": 0.1,
                "parts": [],
                "bm25_rank": 1,
                "vector_rank": 1 if params["qvec"] else None,
                "bm25_score": 1.0,
                "vector_score": 0.9 if params["qvec"] else None,
            }
        ]

    monkeypatch.setattr(hybrid, "run_cq", fake_run_cq)
    return calls


class Ok:
    """정상 임베더 (이름 · 차원 지정)."""

    def __init__(self, name="voyage:voyage-4", dim=1024):
        self.name, self.dimension = name, dim

    def embed(self, texts, input_type):
        return [[0.0] * self.dimension for _ in texts]


def broken(*args, **kwargs):
    raise EmbeddingUnavailable("Voyage API 키가 무효입니다 (HTTP 401)")


def test_r01_normal_voyage_hybrid(monkeypatch, cq_calls):
    monkeypatch.setattr(hybrid, "make_embedder", lambda p, d=None: Ok())
    res = hybrid.hybrid_search(FakeDriver("voyage:voyage-4", 1024), "corner servo")
    assert res["effective_mode"] == "hybrid" and res["query_provider"] == "voyage:voyage-4"
    assert cq_calls[0]["mode"] == "hybrid" and cq_calls[0]["qvec"] is not None
    assert not res["warnings"]


def test_r02_embedding_failure_falls_back_to_bm25_without_hash(monkeypatch, cq_calls):
    monkeypatch.setattr(hybrid, "make_embedder", broken)
    hashed = []
    monkeypatch.setattr(HashEmbedder, "embed", lambda self, *a, **k: hashed.append(1) or [[0.0]])
    res = hybrid.hybrid_search(FakeDriver("voyage:voyage-4", 1024), "corner servo")
    assert res["mode"] == "hybrid" and res["effective_mode"] == "bm25"
    assert cq_calls[0]["mode"] == "bm25" and cq_calls[0]["qvec"] is None
    assert hashed == []  # 다른 공간의 hash 질문 벡터를 만들지 않는다
    assert res["query_provider"] is None and "BM25" in res["warnings"][0]
    assert res["provider"] == "voyage:voyage-4"  # 이전 호환 필드는 색인 공급자 그대로


def test_r03_vector_mode_failure_is_explicit(monkeypatch, cq_calls):
    monkeypatch.setattr(hybrid, "make_embedder", broken)
    res = hybrid.hybrid_search(FakeDriver("voyage:voyage-4", 1024), "corner servo", mode="vector")
    assert res["error"] and res["results"] == [] and res["effective_mode"] is None
    assert cq_calls == []  # 조용히 BM25 로 바꿔 실행하지 않는다


def test_r04_bm25_mode_never_calls_embedding(monkeypatch, cq_calls):
    monkeypatch.setattr(hybrid, "make_embedder", lambda *a, **k: pytest.fail("임베딩 호출"))
    res = hybrid.hybrid_search(FakeDriver("voyage:voyage-4", 1024), "corner servo", mode="bm25")
    assert res["effective_mode"] == "bm25" and not res["warnings"]


def test_r05_dimension_or_provider_mismatch_is_detected(monkeypatch, cq_calls):
    monkeypatch.setattr(hybrid, "make_embedder", lambda p, d=None: Ok(dim=512))
    res = hybrid.hybrid_search(FakeDriver("voyage:voyage-4", 1024), "corner servo")
    assert res["effective_mode"] == "bm25" and "차원" in res["warnings"][0]
    monkeypatch.setattr(hybrid, "make_embedder", lambda p, d=None: Ok(name="hash:local"))
    res = hybrid.hybrid_search(FakeDriver("voyage:voyage-4", 1024), "corner servo")
    assert res["effective_mode"] == "bm25" and "공급자" in res["warnings"][0]


def test_r06_hash_index_with_hash_query_is_allowed(cq_calls):
    res = hybrid.hybrid_search(FakeDriver("hash:local", 1024), "corner servo")
    assert res["effective_mode"] == "hybrid" and res["query_provider"] == "hash:local"
    assert len(cq_calls[0]["qvec"]) == 1024


def test_make_embedder_keeps_stored_model_and_dimension(monkeypatch):
    from mfg_bom_agent.retrieval import embeddings

    monkeypatch.setattr(
        embeddings.get_settings().embedding_api_key, "get_secret_value", lambda: "k"
    )
    e = embeddings.make_embedder("voyage:voyage-3", 512)
    assert e.name == "voyage:voyage-3" and e.dimension == 512
