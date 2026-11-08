# Part 1 Ch3 · 공통 환경 확인

- `ch03_where_used.cypher`: Neo4j Browser 사용처 조회
- `ch03_call.py`: 같은 사용처와 문서 검색을 MCP로 호출

`labs/mfg-bom-agent`에서 실행합니다.

```bash
uv run python ../../examples/part01/ch03/ch03_call.py where_used --revision "확인한_ID"
uv run python ../../examples/part01/ch03/ch03_call.py search_docs --mode bm25
uv run python ../../examples/part01/ch03/ch03_call.py search_docs --mode vector
uv run python ../../examples/part01/ch03/ch03_call.py search_docs --mode hybrid
```

[설치·실행 가이드](../../../docs/ch03-run-guide.md)를 먼저 완료합니다.
