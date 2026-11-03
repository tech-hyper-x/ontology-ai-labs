"""Hybrid Search: 전문 검색 + 벡터 검색 + 그래프 경로 (Part 2 Ch5-2 Hybrid Search와 그래프 경로 결합).

증상 문장("corner wheels will not turn")으로 정비 문서를 찾고, 찾은 문서에 연결된 부품과
그 부품의 사용처(그래프 경로)를 함께 돌려준다.

1. BM25 키워드 검색(doc_fulltext): 단어가 그대로 일치하는 문서 — 품번 · 고유 명칭에 강하다.
   Neo4j 전문 색인은 Lucene 이라 점수가 BM25 로 매겨진다
2. 벡터 검색(doc_vector)  : 뜻이 비슷한 문서 — 표현이 달라도 찾는다
3. RRF(Reciprocal Rank Fusion)로 두 순위를 합친다: score = Σ 1 / (60 + 순위)
4. 상위 문서의 DESCRIBED_IN 으로 부품을 찾고, 부품의 상위 어셈블리 경로를 붙인다

1~4 는 Cypher 한 개(queries/cq_15_hybrid_docs.cypher, CQ-15)로 실행한다. Neo4j Browser 에서도
같은 쿼리를 돌려 볼 수 있게, 예시 질문의 검색어 · 임베딩을 (:SearchExample) 노드로 저장해 둔다.

색인 만들기: index_documents() — scripts/build_index.py 가 호출한다.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from neo4j import Driver

from mfg_bom_agent.graph.cq import lucene_escape, run_cq
from mfg_bom_agent.retrieval.embeddings import EmbeddingUnavailable, HashEmbedder, make_embedder

RRF_K = 60  # RRF 상수 (CQ-15 쿼리 안의 60 과 같은 값)
EXAMPLES_PATH = Path(__file__).resolve().parents[3] / "data" / "golden" / "search_examples.yaml"


def index_documents(driver: Driver, provider: str | None = None) -> dict:
    """문서 임베딩을 만들어 저장하고 전문 · 벡터 색인을 만든다. 키가 무효면 로컬 대체 임베딩으로 바꾼다."""
    docs = [
        r.data()
        for r in driver.execute_query(
            "MATCH (d:Document) RETURN d.doc_id AS doc_id, d.title + '\n' + d.text AS text"
        ).records
    ]
    try:
        embedder = make_embedder(provider)
        vectors = embedder.embed([d["text"][:4000] for d in docs], input_type="document")
        fallback_reason = ""
    except EmbeddingUnavailable as exc:
        embedder = HashEmbedder()
        vectors = embedder.embed([d["text"] for d in docs], input_type="document")
        fallback_reason = str(exc)
    rows = [{"doc_id": d["doc_id"], "v": v} for d, v in zip(docs, vectors)]
    for i in range(0, len(rows), 200):
        driver.execute_query(
            "UNWIND $rows AS r MATCH (d:Document {doc_id: r.doc_id}) "
            "CALL db.create.setNodeVectorProperty(d, 'embedding', r.v)",
            rows=rows[i : i + 200],
        )
    driver.execute_query("DROP INDEX doc_vector IF EXISTS")
    driver.execute_query(
        "CREATE VECTOR INDEX doc_vector IF NOT EXISTS FOR (d:Document) ON d.embedding "
        "OPTIONS {indexConfig: {`vector.dimensions`: $dim, `vector.similarity_function`: 'cosine'}}",
        dim=embedder.dimension,
    )
    driver.execute_query(
        "CREATE FULLTEXT INDEX doc_fulltext IF NOT EXISTS FOR (d:Document) ON EACH [d.title, d.text]"
    )
    driver.execute_query("CALL db.awaitIndexes(300)")
    examples = index_search_examples(driver, embedder)
    driver.execute_query(
        "MERGE (m:LabMeta {project: 'mfg-bom-agent'}) SET m.embedding_provider = $p, m.embedding_dim = $d, "
        "m.embedding_fallback_reason = $r",
        p=embedder.name,
        d=embedder.dimension,
        r=fallback_reason,
    )
    return {
        "documents": len(rows),
        "examples": examples,
        "provider": embedder.name,
        "fallback_reason": fallback_reason,
    }


def index_search_examples(driver: Driver, embedder) -> int:
    """CQ-15 실습 예시 질문의 검색어 · 질문 임베딩을 (:SearchExample) 로 저장한다 (Neo4j Browser 실행용)."""
    examples = yaml.safe_load(EXAMPLES_PATH.read_text(encoding="utf-8"))["examples"]
    vectors = embedder.embed([e["query_en"] for e in examples], input_type="query")
    driver.execute_query("MATCH (e:SearchExample) DETACH DELETE e")
    driver.execute_query(
        "UNWIND $rows AS r CREATE (e:SearchExample) SET e = r",
        rows=[
            {
                **{k: str(v) for k, v in e.items()},
                "lucene": lucene_query(e["query_en"]),
                "embedding": v,
            }
            for e, v in zip(examples, vectors)
        ],
    )
    return len(examples)


def index_meta(driver: Driver) -> tuple[str, int | None]:
    """색인할 때 쓴 임베딩 공급자 이름과 차원. 검색할 때 같은 공급자 · 모델 · 차원을 써야 한다 (읽기만 한다)."""
    records, _, _ = driver.execute_query(
        "MATCH (m:LabMeta {project: 'mfg-bom-agent'}) RETURN m.embedding_provider AS p, m.embedding_dim AS d"
    )
    if not records:
        return "hash:local", None
    return records[0]["p"] or "hash:local", records[0]["d"]


def index_provider(driver: Driver) -> str:
    """색인할 때 쓴 임베딩 공급자 이름. 검색할 때 같은 공급자를 써야 한다."""
    return index_meta(driver)[0]


# ─── [Hands-on P2-Ch5-2 Hybrid Search와 그래프 경로 결합] 시작 ───
def lucene_query(query: str) -> str:
    """BM25 검색어. 단어를 OR 로 묶고, 품번처럼 하이픈이 있는 값은 따옴표로 묶어 한 단어로 찾는다."""
    terms = [
        f'"{t}"' if "-" in t else lucene_escape(t)
        for t in re.findall(r"[\w-]+", query)
        if len(t) > 1
    ]
    return " OR ".join(terms) or "__empty__"


def query_vector(driver: Driver, query: str) -> list[float]:
    """질문 임베딩. 문서를 색인할 때와 같은 공급자 · 모델 · 차원으로 만들어야 벡터를 비교할 수 있다.

    질문 임베딩을 만들 수 없으면 다른 공급자(hash)로 바꾸지 않고 EmbeddingUnavailable 을 그대로 올린다.
    Voyage 로 만든 문서 벡터와 hash 질문 벡터는 차원이 같아도 같은 의미 공간이 아니기 때문이다.
    """
    provider, dim = index_meta(driver)
    embedder = make_embedder(provider, dim)
    if embedder.name.split(":")[0] != provider.split(":")[0]:
        raise EmbeddingUnavailable(
            f"색인 공급자 {provider} 와 질문 임베더 {embedder.name} 가 다릅니다"
        )
    vec = embedder.embed([query], input_type="query")[0]
    if dim and len(vec) != dim:
        raise EmbeddingUnavailable(f"질문 벡터 차원 {len(vec)} 이 색인 차원 {dim} 과 다릅니다")
    return vec


def hybrid_search(
    driver: Driver, query: str, k: int = 5, source: str | None = None, mode: str = "hybrid"
) -> dict:
    """증상 · 키워드로 문서를 찾고, 연결된 부품과 그 부품의 사용처 경로를 함께 돌려준다 (CQ-15 한 번 실행).

    mode  : "hybrid"(BM25 + 벡터 → RRF, 기본) · "bm25"(키워드만) · "vector"(의미만) — 순위 비교 실습용
    source: "readme"(정비 · 조립 문서) · "issue"(GitHub 이슈) · None(둘 다)
            · "all"(BOM 표 텍스트까지 — RAG 비교 실행 전용. 에이전트는 BOM 을 그래프로 조회한다)
    반환: {provider, mode, effective_mode, index_provider, query_provider, warnings, error,
           results: [{doc_id, path, title, line, excerpt, score, rank, ranks, scores, parts}]}
    질문 임베딩을 만들 수 없으면 hybrid 는 BM25 만 실행하고(effective_mode="bm25" + 경고),
    vector 는 결과 없이 error 를 돌려준다. 다른 공급자의 벡터로 몰래 바꾸지 않는다.
    """
    provider = index_provider(driver)
    warnings: list[str] = []
    effective, qvec, query_provider = mode, None, None
    if mode != "bm25":  # BM25 만 쓰면 임베딩 API 를 부르지 않는다
        try:
            qvec = query_vector(driver, query)
            query_provider = provider
        except EmbeddingUnavailable as exc:
            if mode == "vector":
                # 벡터만 요청했으면 조용히 다른 검색으로 바꾸지 않고 실패로 알린다
                return {
                    "provider": provider,
                    "mode": mode,
                    "effective_mode": None,
                    "index_provider": provider,
                    "query_provider": None,
                    "warnings": [],
                    "results": [],
                    "error": f"질문 임베딩을 만들 수 없음: {exc}",
                }
            effective = "bm25"
            warnings.append(
                f"질문 임베딩을 만들 수 없어 키워드(BM25) 검색만 했습니다 ({exc}). "
                "임베딩 키 · 연결을 확인하세요 (색인은 그대로 둡니다)"
            )
    rows = run_cq(
        driver,
        "CQ-15",
        q=lucene_query(query),
        qvec=qvec,
        mode=effective,
        k=k,
        source=source,
        example=None,
    )
    if effective == "hybrid" and rows and all(r["vector_rank"] is None for r in rows):
        # 문서 임베딩이 지워진 경우(그래프만 다시 적재) 벡터 검색이 아무것도 돌려주지 않는다
        warnings.append(
            "벡터 검색 결과가 없어 BM25 결과만 썼습니다 — scripts/build_index.py 로 임베딩을 다시 만드세요"
        )
    results = []
    for rank, r in enumerate(rows, start=1):
        ranks = {m: r[f"{m}_rank"] for m in ("bm25", "vector") if r[f"{m}_rank"] is not None}
        results.append(
            {
                "doc_id": r["doc_id"],
                "path": r["path"],
                "title": r["title"],
                "line": r["line"],
                "source": r["source"],
                "excerpt": _excerpt(r["text"], query),
                "score": r["score"],
                "rank": rank,
                "ranks": ranks,
                "scores": {m: r[f"{m}_score"] for m in ranks},
                "parts": [p for p in r["parts"] if p],
            }
        )
    return {
        "provider": provider,  # 이전 호환: 색인 공급자
        "mode": mode,  # 요청한 검색 방식
        "effective_mode": effective,  # 실제로 실행한 검색 방식 (임베딩 장애면 bm25)
        "index_provider": provider,
        "query_provider": query_provider,  # 질문 임베딩 공급자 (BM25 만 썼으면 None)
        "warnings": warnings,
        "results": results,
        "error": None,
    }


def compare_search(driver: Driver, query: str, k: int = 5, source: str | None = None) -> dict:
    """같은 질문을 BM25만 · 벡터만 · 결합으로 각각 찾아 순위를 나란히 돌려준다 (하이브리드 효과 설명용)."""
    return {
        m: hybrid_search(driver, query, k, source, m)["results"]
        for m in ("bm25", "vector", "hybrid")
    }


# ─── [Hands-on P2-Ch5-2] 끝 ───


def _excerpt(text: str, query: str, width: int = 280) -> str:
    """질문 단어가 가장 많이 모인 구간을 잘라 근거 발췌로 쓴다.

    처음 나오는 단어 위치만 보면 흔한 단어(servo 등)에 걸려 정작 필요한 문장을 놓친다.
    단어가 나오는 자리마다 창(width)을 대 보고, 서로 다른 질문 단어가 가장 많이 들어가는 창을 고른다.
    """
    lower = text.lower()
    words = set(re.findall(r"\w{4,}", query.lower()))
    hits = sorted((m.start(), w) for w in words for m in re.finditer(re.escape(w), lower))
    if not hits:
        return text[:width].replace("\n", " ").strip()
    best, best_n = 0, -1
    for pos, _ in hits:
        start = max(0, pos - 60)
        n = len({w for p2, w in hits if start <= p2 < start + width})
        if n > best_n:
            best, best_n = start, n
    return text[best : best + width].replace("\n", " ").strip()
