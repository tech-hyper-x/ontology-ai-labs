# Voyage AI 사용 가이드 — mfg-bom-agent

Voyage AI 는 정비 문서와 질문을 **벡터(숫자 1024개)** 로 바꿔 주는 임베딩 API 다. 이 실습에서는 Ch5 Hybrid Search 의 "뜻으로 찾기"에 쓴다. 문서에 "servo gear"라는 단어가 없어도 "corner wheels will not turn"이라는 증상으로 서보 기어 교체 문서를 찾을 수 있는 이유가 이것이다.

- 대시보드: https://dashboard.voyageai.com
- 이 실습의 모델: `voyage-4` (1024차원)
- 기준: 2026-10-25 확인한 가격 · 한도. 최신 값은 [Pricing](https://docs.voyageai.com/docs/pricing) · [Rate Limits](https://docs.voyageai.com/docs/rate-limits) 문서에서 확인한다.

## 목차

1. [왜 Voyage 인가](#1-왜-voyage-인가)
2. [키 발급과 결제 수단 등록](#2-키-발급과-결제-수단-등록)
3. [무료 사용량과 한도](#3-무료-사용량과-한도)
4. [.env 설정](#4-env-설정)
5. [색인 만들기와 확인](#5-색인-만들기와-확인)
6. [키가 없거나 막혔을 때 (로컬 대체 임베딩)](#6-키가-없거나-막혔을-때-로컬-대체-임베딩)
7. [문제 해결](#7-문제-해결)

## 1. 왜 Voyage 인가

Anthropic(Claude)은 임베딩 API 를 제공하지 않고 Voyage AI 를 안내한다. 그래서 답변 생성은 Claude, 문서 벡터는 Voyage 로 나눠 쓴다.

| 단계 | 하는 일 | 코드 |
|---|---|---|
| 색인 | 문서 534개(정비 문서 청크 · 이슈 · BOM 텍스트)를 `input_type="document"` 로 임베딩해 Neo4j `doc_vector` 인덱스에 넣는다 | `retrieval/hybrid.py` `index_documents()` |
| 검색 | 질문 한 문장을 `input_type="query"` 로 임베딩해 가까운 문서를 찾는다 | `retrieval/hybrid.py` `hybrid_search()` |
| 결합 | 전문 검색(단어 일치) 순위와 벡터 검색 순위를 RRF 로 합친다 | 같은 파일 |

**색인과 검색은 같은 공급자 · 같은 차원을 써야 한다.** 색인할 때 쓴 공급자는 Neo4j 의 `LabMeta.embedding_provider` 에 남고, 검색할 때 이 값을 읽어 같은 공급자로 질문을 임베딩한다.

## 2. 키 발급과 결제 수단 등록

1. https://dashboard.voyageai.com 에 가입 · 로그인한다.
2. 왼쪽 메뉴 **API keys → Create new secret key** 를 누른다. 키(`pa-` 로 시작)는 이때 한 번만 보이므로 바로 복사한다.
3. 왼쪽 메뉴 **Billing → Payment methods** 에서 카드를 등록한다. **꼭 하기를 권한다** (이유는 3절).
4. Billing 화면 위쪽이 **Usage tier 1** 로 바뀌면 끝이다.

> **크레딧은 사지 않아도 된다.** 카드를 등록하면 "Configure payment — Initial credit purchase" 창이 뜨는데, 이 실습에는 필요 없다. **Cancel** 로 닫는다. 자동 충전(automatic recharge)도 켜지 않는다. 결제 수단이 있으면 무료 토큰을 먼저 쓴다.

> **조직(Organization)을 확인한다.** 키와 결제 수단은 조직 단위다. 왼쪽 위 조직 이름이 키를 만든 화면과 카드를 등록한 화면에서 같아야 한도가 올라간다.

## 3. 무료 사용량과 한도

| 항목 | 값 |
|---|---|
| 무료 토큰 | 계정당 **2억 토큰** (voyage-4 · voyage-4-lite · voyage-4-large) |
| 무료 이후 가격 | voyage-4 100만 토큰당 $0.06 (lite $0.02 · large $0.12) |
| 이 실습 전체 색인 1회 | 약 **7만 3천 토큰** → 무료 토큰으로 수천 번 다시 색인할 수 있다 |

비용보다 **속도 한도**가 문제다.

| 상태 | 한도 | 전체 색인 시간 (실측) |
|---|---|---|
| 결제 수단 없음 | 분당 3회 · 분당 1만 토큰 | 약 10분 (429 를 받고 기다렸다 다시 보냄) |
| 결제 수단 등록 (Tier 1) | voyage-4 분당 2,000회 · 수백만 토큰 | **약 15초** |

결제 수단 없이도 실습은 된다. `VoyageEmbedder` 가 요청을 약 8천 토큰씩 나눠 보내고, 429(요청 한도 초과)를 받으면 30초 기다렸다가 다시 보낸다. 다만 시간이 오래 걸리고 아래처럼 출력된다.

```text
  Voyage 요청 한도 초과 — 30초 후 다시 시도 (1/8)
```

## 4. .env 설정

`.env.example` 을 복사한 `.env` 에 넣는다. `.env` 는 커밋하지 않는다.

```dotenv
EMBEDDING_PROVIDER=voyage
EMBEDDING_MODEL=voyage-4
EMBEDDING_API_KEY=pa-...        # 2절에서 복사한 키
EMBEDDING_DIMENSION=1024        # Neo4j 벡터 인덱스 차원과 같아야 한다
```

- `voyage-4` · `voyage-4-lite` · `voyage-4-nano` 는 같은 임베딩 공간을 쓴다. 문서는 `voyage-4` 로 색인하고 질문만 더 싼 `voyage-4-lite` 로 바꿔도 다시 색인할 필요가 없다.
- 차원을 바꾸면 벡터 인덱스를 다시 만들어야 한다 (5절 명령을 다시 실행).

키가 맞는지 값을 출력하지 않고 확인하려면:

```bash
uv run python -c "from mfg_bom_agent.retrieval.embeddings import make_embedder; print(len(make_embedder().embed(['test'], 'query')[0]))"
```

`1024` 가 나오면 정상이다. `Voyage API 키가 무효입니다 (HTTP 401)` 이면 키를 다시 복사한다.

## 5. 색인 만들기와 확인

키를 넣거나 바꾼 뒤에는 색인을 다시 만든다.

```bash
uv run python scripts/build_index.py
```

컨테이너로 실행 중이라면 그래프 적재 · 검증 · 색인을 한 번에 다시 하고, 새 키를 읽도록 mcp · app 을 다시 만든다.

```bash
docker compose --profile init run --rm init
```

```bash
docker compose up -d --force-recreate mcp app
```

정상 출력 예:

```text
검색 색인: 문서 534개 · 임베딩 voyage:voyage-4
확인 검색: 'corner wheels will not turn servo gear'
  0.0325 mechanical/servo_gear_replacement/README.md#1 · 연결 부품 2000-0025-0002
```

어떤 공급자로 색인됐는지는 Neo4j Browser 에서 확인할 수 있다.

```cypher
MATCH (m:LabMeta) RETURN m.embedding_provider, m.embedding_dim, m.embedding_fallback_reason
```

## 6. 키가 없거나 막혔을 때 (로컬 대체 임베딩)

키가 비어 있거나 무효(401 · 403)이면 색인이 멈추지 않고 **로컬 대체 임베딩(`hash:local`)** 으로 넘어간다.

```text
검색 색인: 문서 534개 · 임베딩 hash:local
  ※ 로컬 대체 임베딩 사용 — Voyage API 키가 무효입니다 (HTTP 401)
```

로컬 대체 임베딩은 단어를 해시해 벡터를 만든다. 외부 호출이 없어 흐름은 끝까지 돌지만, **같은 단어가 있어야만 비슷하다고 판단**하므로 의미 검색 품질이 크게 떨어진다. 예를 들어 평가 문항 G43(대체 휠 문서 찾기)은 이 모드에서 실패했다. 키를 고친 뒤에는 5절 명령으로 다시 색인한다.

## 7. 문제 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `HTTP 401` · `키가 무효` | 키 오타, 삭제된 키 | 새 키를 만들어 `.env` 에 다시 넣는다 |
| `429` 와 "You have not yet added your payment method" | 결제 수단 미등록 (분당 3회 · 1만 토큰) | 2절 3단계. 등록 직후 몇 분은 반영이 늦을 수 있다 |
| 카드를 등록했는데 계속 429 | 키를 만든 조직과 카드를 등록한 조직이 다름 | 왼쪽 위 조직 이름을 맞춘다 |
| 컨테이너에서만 예전 키를 씀 | 컨테이너는 만들 때 `.env` 를 읽는다 | `docker compose up -d --force-recreate mcp app` |
| 검색 결과가 이상하게 단어 일치에만 의존 | `hash:local` 로 색인됨 | 5절의 Cypher 로 공급자 확인 후 다시 색인 |
| `vector.dimensions` 불일치 오류 | `EMBEDDING_DIMENSION` 을 바꿈 | 다시 색인하면 인덱스를 새 차원으로 만든다 |
