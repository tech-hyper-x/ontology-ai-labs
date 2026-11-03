# Part 01 · Ch3 — 개발 환경 구성과 공통 흐름 실행

처음 설치한다면 [Docker → Neo4j → Langfuse 상세 가이드](setup/README.md)를 먼저 진행합니다. 강사의 화면 시연 순서는 [체크리스트](setup/RECORDING.md)에 있습니다.

강의 기준: 제조 프로젝트 `실습코드/mfg-bom-agent`의 현재 코드. 20분은 설명과 준비된 환경의 시연 배분이며 최초 다운로드·설치 대기 시간은 별도입니다.

## 1. 운영체제와 실행 방식

- [운영체제 선택](../labs/mfg-bom-agent/INSTALL.md): [macOS](../labs/mfg-bom-agent/docs/install/macos.md), [Windows WSL2](../labs/mfg-bom-agent/docs/install/windows.md), [Linux](../labs/mfg-bom-agent/docs/install/linux.md).
- 개발 모드로 통일합니다. Docker는 Neo4j·Langfuse, 로컬 uv는 Python 앱·MCP 서버를 실행합니다.
- Windows의 아래 명령은 WSL Ubuntu 안에서 실행합니다. 프로젝트도 Ubuntu 파일시스템에 둡니다.
- 설치 문서에 따라 영문 작업 경로를 사용합니다. 모든 명령은 `mfg-bom-agent` 폴더 안에서 실행합니다.
- Docker·Compose·uv·Git의 설치 확인 명령은 각각 `docker --version`, `docker compose version`, `uv --version`, `git --version`입니다.
- 편집기는 익숙한 도구를 사용합니다. 바이브코딩으로 수정한 코드도 실행 결과와 함께 검토합니다.

## 2. 개인 설정과 패키지 준비

```bash
cp .env.example .env
uv sync --all-extras
```

`.env`에서 설정할 항목:

| 항목 | 설정 기준 |
|---|---|
| `NEO4J_PASSWORD` | 로컬 실습 DB 비밀번호 |
| `ANTHROPIC_API_KEY` | 실제 LLM 호출용 본인 키 |
| `EMBEDDING_API_KEY` | 문서·질문 임베딩용 본인 키. LLM API 키와 별도 |
| `EMBEDDING_PROVIDER / MODEL / DIMENSION` | 배포된 `.env.example` 값 유지. 색인과 질문의 규격을 함께 맞춤 |
| `MCP_TRANSPORT=http` | 이 강의에서는 별도로 실행한 MCP 서버에 앱도 연결 |
| `MCP_URL` | 기본 `http://localhost:8000/mcp` |
| `LANGFUSE_INIT_USER_PASSWORD` | Langfuse 초기 로그인 비밀번호 |
| `DEMO_MODE=none` | 실제 LLM 호출. 필요하면 아래 모드 구분 참고 |

실제 키를 화면에 공개하거나 자료에 저장하지 않습니다. 설정을 바꾼 뒤에는 실행 중인 앱·MCP 서버를 재시작합니다. Langfuse를 생략할 경우 README 안내에 따라 Neo4j만 실행하고 `LANGFUSE_PUBLIC_KEY`와 `LANGFUSE_SECRET_KEY`를 비웁니다.

현재 OS 설치 문서의 “임베딩은 비워 두기”, “초기화는 제약 생성만 수행”이라는 설명은 최신 코드와 차이가 있습니다. Ch3에서 검색을 확인하려면 임베딩 설정과 실제 `init_data.py` 출력을 기준으로 준비합니다.

## 3. 기반 서비스와 데이터 초기화 — 터미널 1

```bash
docker compose up -d neo4j langfuse-web
docker compose ps
uv run python scripts/init_data.py
uv run python scripts/check_env.py
```

- Neo4j의 상태를 확인한 뒤 초기화합니다.
- `init_data.py`는 데이터 재적재 → 온톨로지 검사 → 문서 연결 → 검색 색인을 실행합니다. 기존 실습 데이터를 다시 적재하므로 전용 실습 DB에서 사용합니다.
- 적재 수, 검사 결과, 문서 연결, 검색 색인 공급자를 실제 출력에서 확인합니다. 초기화 출력 예시나 성공 건수를 임의로 만들지 않습니다.
- `check_env.py`는 현재 Neo4j와 Anthropic을 필수로 검사합니다. `fixed_llm`이어도 Anthropic 검사를 자동으로 생략하지 않습니다.
- MCP 항목은 HTTP 응답 여부를 확인합니다. 응답 코드가 표시되는 것만으로 `where_used`가 성공했다고 판단하지 않습니다.

## 4. MCP와 앱 실행 — 별도 터미널 두 개

터미널 2:

```bash
uv run python -m mfg_bom_agent.mcp_server
```

터미널 3:

```bash
uv run streamlit run src/mfg_bom_agent/ui.py
```

| 화면/서비스 | 기본 주소 |
|---|---|
| 실습 앱 | http://localhost:8501 |
| Neo4j Browser | http://localhost:7474 |
| Neo4j 드라이버 | bolt://localhost:7687 |
| MCP | http://localhost:8000/mcp |
| Langfuse | http://localhost:3000 |

포트를 바꿨다면 `.env`의 해당 접속값도 맞춥니다. 앱과 MCP 서버를 실행한 터미널은 유지합니다.

서비스 준비 단계에서는 앱 접속까지만 확인합니다. 질문과 실행 기록 확인은 아래 7절에서 진행합니다.

## 5. 그래프에서 사용처 직접 조회

Neo4j Browser에서 아래 파라미터를 먼저 실행합니다. 부품번호는 현재 제조 예제의 휠 SKU입니다. `revision: null`은 최신 판을 선택합니다.

```cypher
:params {part: '3616-0014-0144', revision: null}
```

이어서 조회합니다.

```cypher
MATCH (v:Revision)
WHERE ($revision IS NULL AND v.is_latest)
   OR v.revision_id = $revision
MATCH (a:Assembly)-[:HAS_BOM_LINE]->(l:BOMLine)-[:REFERS_TO]->(p:Part)
WHERE (p.sku = $part OR p.part_id = $part)
  AND l.revision_id = v.revision_id
RETURN p.sku AS sku, a.name AS assembly,
       v.revision_id AS revision,
       l.raw_qty_text AS raw_qty,
       l.qty_each_text AS qty_each
ORDER BY assembly
```

SKU·조립품·반환된 revision을 기록합니다. 이후 MCP 호출에는 이 revision을 명시합니다. 이 쿼리는 직접 연결된 투입 내역을 보는 입문용입니다. 제품까지 이어지는 전체 경로는 `queries/cq_01_where_used.cypher`를 공통 개정판 조각과 함께 사용하는 실습 코드에서 확인합니다. 원천 수량·낱개 수·제품당 환산 수량을 같은 항목처럼 비교하지 않습니다.

## 6. MCP 직접 호출과 검색

먼저 `where_used`로 앞의 그래프 조회를 대조한 뒤, 같은 호출 방법으로 `search_docs`를 실행합니다.

호출 예제는 `examples/ch03_call.py`에 포함했습니다. 제조 프로젝트 폴더에서 `uv run python ../../examples/ch03_call.py`로 실행합니다. 아래 코드와 동일합니다.

```python
import argparse
import asyncio
import json

from fastmcp import Client
from mfg_bom_agent.config import get_settings

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["where_used", "search_docs"])
    parser.add_argument("--part", default="3616-0014-0144")
    parser.add_argument("--revision")
    parser.add_argument("--mode", choices=["hybrid", "bm25", "vector"], default="hybrid")
    args = parser.parse_args()
    async with Client(get_settings().mcp_url) as client:
        tools = await client.list_tools()
        print("도구 목록:", ", ".join(t.name for t in tools))
        if args.action == "where_used":
            inputs = {"part": args.part, "revision": args.revision}
        else:
            inputs = {
                "query": "corner wheels will not turn servo gear",
                "k": 3,
                "mode": args.mode,
            }
        result = await client.call_tool(args.action, inputs, raise_on_error=True)
        print(json.dumps(result.structured_content, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

그래프에서 기록한 개정판 ID로 `확인한_ID`를 바꾼 뒤 실행합니다.

```bash
uv run python ../../examples/ch03_call.py where_used --revision "확인한_ID"
uv run python ../../examples/ch03_call.py search_docs --mode hybrid
```

- 사용처 도구: `sku / revision / lines / paths`와 오류·힌트를 확인합니다.
- 검색 도구: `mode / effective_mode / hits`를 확인하고 문서 본문·연결된 부품·출처를 읽습니다.
- 검색 질문은 “코너 바퀴가 돌지 않을 때 참고할 정비 문서는 무엇인가요?”입니다. 직접 호출은 현재 도구 설명에서 권장하는 영어 검색어를 사용합니다.
- `effective_mode`가 `bm25`라면 벡터·결합 검색 성공으로 설명하지 않습니다. 빈 결과와 실행 오류도 구분합니다.
- 도구가 반환한 실제 값만 사용하며 성공 건수·경로·원가를 미리 만들어 두지 않습니다.

## 7. 에이전트에서 같은 조건 비교

앱에 질문을 입력하기 전에 현재 실행 모드를 확인하고 수강생에게 알립니다. `canned`에서는 실제 도구 실행을 비교하지 않습니다.

| 모드 | 실행 범위 |
|---|---|
| `none` | 실제 LLM 호출과 도구 실행 |
| `fixed_llm` | LLM 응답 고정, 도구 실제 실행. 모델 이해 성능 평가는 아님 |
| `canned` | 저장된 예시 응답. 현재 연결·계산 성공의 증거가 아님 |

질문: “휠 부품 3616-0014-0144는 어느 조립품에 쓰이나요?”

그래프·도구를 활용하는 실행 방식을 선택한 뒤 처리 과정에서 실제 도구명과 입력 SKU·revision을 확인합니다. 직접 호출과 다른 개정판을 썼다면 조건을 맞춘 뒤 비교합니다. 도구의 사용처·경로가 답변에 정확히 전달됐는지 확인하며, 도구 조회에 없는 설명은 별도 근거가 있는지 검토합니다.

`fixed_llm`은 임베딩 API를 대체하지 않습니다. 그래프·검색·모델 연결은 각각 확인합니다.

방금 실행한 질문의 Langfuse Tracing 기록을 열어 도구 입력·출력과 오류 여부를 확인합니다. 기록이 없다면 수집 설정과 반영 지연부터 점검합니다.

## 8. 완료 기준

- [ ] 프로젝트 위치와 Docker·uv 역할을 구분한다.
- [ ] .env 설정 후 서비스·초기화·앱 실행 순서를 안다.
- [ ] 같은 SKU와 revision으로 그래프와 MCP 사용처를 조회한다.
- [ ] 검색 결과의 출처와 실제 검색 방식을 확인한다.
- [ ] 도구 결과와 에이전트 답변을 대조한다.

정밀 수량·원가 계산, 검색 색인 구현, 에이전트 코드 작성, 평가 세트 실행은 이후 제조·바이오 강의에서 진행합니다.
