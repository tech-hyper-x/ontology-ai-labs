"""문서 · 질문 임베딩 (Part 2 Ch5-2 Hybrid Search).

두 가지 공급자를 쓴다.
- voyage : Voyage AI 임베딩 API (기본). 문서는 input_type="document", 질문은 "query" 로 만든다.
- hash   : 로컬 대체 임베딩. 단어를 해시해 고정 차원 벡터로 만든다. API 키가 없거나 무효일 때
           실습 흐름을 이어가기 위한 것이며, 의미 검색 품질은 Voyage 보다 훨씬 낮다 (같은 단어가 있어야 비슷해진다).

색인에 쓴 공급자와 질문에 쓰는 공급자가 같아야 한다. 그래서 색인할 때 쓴 공급자를 Neo4j 의
LabMeta.embedding_provider 에 남기고, 검색할 때 그 값을 읽어 같은 공급자로 질문을 임베딩한다.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from itertools import pairwise
from typing import Protocol

import httpx

from mfg_bom_agent.config import get_settings

VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"


class EmbeddingUnavailable(RuntimeError):
    """임베딩 API 를 쓸 수 없음 (키 없음 · 무효 · 네트워크 오류)."""


class Embedder(Protocol):
    name: str
    dimension: int

    def embed(self, texts: list[str], input_type: str) -> list[list[float]]: ...


class VoyageEmbedder:
    """Voyage AI 임베딩. 한 번에 최대 128개씩 나눠 보낸다."""

    def __init__(self, model: str | None = None, dimension: int | None = None) -> None:
        s = get_settings()
        self.api_key = s.embedding_api_key.get_secret_value()
        # 색인에 기록된 모델 · 차원이 있으면 그 값을 쓴다 (설정이 바뀌어도 같은 공간으로 질문을 임베딩)
        self.model = model or s.embedding_model or "voyage-4"
        self.dimension = dimension or s.embedding_dimension or 1024
        self.name = f"voyage:{self.model}"
        if not self.api_key:
            raise EmbeddingUnavailable("EMBEDDING_API_KEY 가 비어 있습니다")

    def embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in _batches(texts):
            data = sorted(self._post(batch, input_type)["data"], key=lambda d: d["index"])
            vectors.extend(d["embedding"] for d in data)
        return vectors

    def _post(self, batch: list[str], input_type: str) -> dict:
        """한 묶음을 보낸다. 요청 한도 초과(429)면 기다렸다가 다시 보낸다."""
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            try:
                r = httpx.post(
                    VOYAGE_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "input": batch,
                        "model": self.model,
                        "input_type": input_type,
                        "output_dimension": self.dimension,
                    },
                    timeout=60,
                )
            except httpx.HTTPError as exc:
                raise EmbeddingUnavailable(f"Voyage 연결 실패: {exc}") from exc
            if r.status_code in (401, 403):
                raise EmbeddingUnavailable(f"Voyage API 키가 무효입니다 (HTTP {r.status_code})")
            if r.status_code == 429 and attempt < RATE_LIMIT_RETRIES:
                # 결제 수단이 없는 무료 계정은 분당 3회 · 1만 토큰으로 제한된다 → 1분 창이 지나길 기다린다
                wait = float(r.headers.get("retry-after") or RATE_LIMIT_WAIT)
                print(
                    f"  Voyage 요청 한도 초과 — {wait:.0f}초 후 다시 시도 ({attempt + 1}/{RATE_LIMIT_RETRIES})"
                )
                time.sleep(wait)
                continue
            if (
                r.status_code >= 400
            ):  # 요청 오류 · 서버 장애(5xx)도 "임베딩을 만들 수 없음"으로 알린다
                raise EmbeddingUnavailable(f"Voyage 요청 실패 (HTTP {r.status_code})")
            return r.json()
        raise EmbeddingUnavailable("Voyage 요청 한도 초과가 계속됩니다 (HTTP 429)")


# 무료 계정 한도(분당 1만 토큰) 안에 들도록 한 요청을 약 8천 토큰 · 128개 이하로 나눈다
BATCH_MAX_TEXTS = 128
BATCH_MAX_TOKENS = 8000
RATE_LIMIT_RETRIES = 8
RATE_LIMIT_WAIT = 30.0


def _batches(texts: list[str]) -> list[list[str]]:
    """토큰 수(대략 글자 수 / 4)와 개수 기준으로 묶는다."""
    batches: list[list[str]] = [[]]
    tokens = 0
    for text in texts:
        est = len(text) // 4 + 1
        if batches[-1] and (tokens + est > BATCH_MAX_TOKENS or len(batches[-1]) >= BATCH_MAX_TEXTS):
            batches.append([])
            tokens = 0
        batches[-1].append(text)
        tokens += est
    return [b for b in batches if b]


class HashEmbedder:
    """로컬 대체 임베딩 (feature hashing). 외부 호출 없이 결정적으로 같은 벡터를 만든다."""

    def __init__(self, dimension: int | None = None) -> None:
        self.dimension = dimension or get_settings().embedding_dimension or 1024
        self.name = "hash:local"

    def embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * self.dimension
        tokens = re.findall(r"[a-z0-9]+|[가-힣]+", text.lower())
        # 단어와 인접 단어쌍을 함께 넣어 "corner servo" 같은 짧은 구도 반영한다
        features = tokens + [f"{a}_{b}" for a, b in pairwise(tokens)]
        for feat in features:
            h = int(hashlib.md5(feat.encode()).hexdigest(), 16)
            vec[h % self.dimension] += 1.0 if (h >> 64) & 1 else -1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def make_embedder(provider: str | None = None, dimension: int | None = None) -> Embedder:
    """공급자 이름으로 임베더를 만든다. name 형식: "voyage:<model>" · "voyage" · "hash:local" · "hash".

    "voyage:<model>" 처럼 모델이 적혀 있으면 그 모델을, dimension 을 주면 그 차원을 쓴다.
    """
    name, _, model = (provider or get_settings().embedding_provider or "hash").partition(":")
    if name == "voyage":
        return VoyageEmbedder(model=model or None, dimension=dimension)
    return HashEmbedder(dimension)
