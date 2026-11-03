"""에이전트 → MCP 도구 호출 통로 (Part 2 Ch7).

에이전트는 도구 함수를 직접 import 하지 않고 반드시 MCP 로 부른다 (정의서 4절: 앱은 MCP 를 통해서만 데이터 접근).
- http      : MCP 서버(Settings.mcp_url)에 Streamable HTTP 로 접속 — 컨테이너 실행 기본값
- inprocess : 같은 프로세스의 FastMCP 서버 객체를 메모리로 연결 — 테스트 · 로컬 실행용 (서버를 띄우지 않아도 된다)

호출마다 ToolStarted → ToolFinished/ToolFailed 이벤트를 보낸다. 화면 타임라인은 이 이벤트만 그린다.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable
from typing import Any

from fastmcp import Client

from mfg_bom_agent.config import get_settings
from mfg_bom_agent.contracts.events import RunEvent, ToolFailed, ToolFinished, ToolStarted


class ToolCallError(RuntimeError):
    def __init__(self, tool: str, message: str, result: dict | None = None) -> None:
        super().__init__(f"{tool}: {message}")
        self.tool, self.result = tool, result or {}


class ToolGateway:
    def __init__(
        self,
        run_id: str,
        on_event: Callable[[RunEvent], None] | None = None,
        transport: str | None = None,
    ) -> None:
        s = get_settings()
        self.run_id = run_id
        self.on_event = on_event or (lambda e: None)
        self.transport = transport or s.mcp_transport
        self.max_calls = s.max_tool_calls
        self.calls: list[dict] = []

    def _target(self):
        if self.transport == "inprocess":
            from mfg_bom_agent.mcp_server import mcp  # 순환 import 를 피하려고 필요할 때만 불러온다

            return mcp
        return get_settings().mcp_url

    def call(self, tool: str, **arguments: Any) -> dict:
        """도구를 호출하고 구조화된 결과(dict)를 돌려준다. 도구가 error 를 채우면 ToolCallError 를 던진다."""
        if len(self.calls) >= self.max_calls:
            raise ToolCallError(tool, f"도구 호출 상한({self.max_calls}회)을 넘었습니다")
        args = {k: v for k, v in arguments.items() if v is not None}
        call_id = uuid.uuid4().hex[:8]
        self.on_event(ToolStarted(run_id=self.run_id, call_id=call_id, tool=tool, inputs=args))
        started = time.perf_counter()
        try:
            result = asyncio.run(self._call(tool, args))
        except Exception as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            self.on_event(
                ToolFailed(
                    run_id=self.run_id,
                    call_id=call_id,
                    tool=tool,
                    error=str(exc),
                    elapsed_ms=elapsed,
                )
            )
            raise ToolCallError(tool, str(exc)) from exc
        elapsed = int((time.perf_counter() - started) * 1000)
        self.calls.append({"tool": tool, "inputs": args, "outputs": result, "elapsed_ms": elapsed})
        if result.get("error"):
            self.on_event(
                ToolFailed(
                    run_id=self.run_id,
                    call_id=call_id,
                    tool=tool,
                    error=f"{result['error']} — {result.get('hint') or ''}",
                    elapsed_ms=elapsed,
                    kind="validation",
                )
            )
            raise ToolCallError(tool, result["error"], result)
        self.on_event(
            ToolFinished(
                run_id=self.run_id,
                call_id=call_id,
                tool=tool,
                outputs=result,
                elapsed_ms=elapsed,
                summary=_summary(tool, result),
            )
        )
        return result

    async def _call(self, tool: str, args: dict) -> dict:
        async with Client(self._target(), timeout=get_settings().request_timeout_seconds) as client:
            res = await client.call_tool(tool, args, raise_on_error=True)
            return res.structured_content or {}


def _summary(tool: str, r: dict) -> str:
    """타임라인 한 줄 요약. 도구 출력의 핵심 값만 보여 준다."""
    if tool == "find_part":
        return (
            f"확정 {r['resolved']['sku']}"
            if r.get("resolved")
            else f"후보 {len(r.get('candidates', []))}개"
        )
    if tool == "where_used":
        return f"경로 {len(r.get('paths', []))}개"
    if tool == "bom_explode":
        items = r.get("items", [])
        return f"{items[0]['required_each']} ea" if len(items) == 1 else f"{len(items)}개 품목"
    if tool == "cost_rollup":
        return f"{r.get('total')} USD"
    if tool == "purchase_quantity":
        return f"{r.get('packs_to_buy')}팩 · {r.get('purchase_amount')} USD"
    if tool == "change_impact":
        val = r.get("cost_diff") or r.get("requirement_cost")
        return f"후보 {len(r.get('impact_candidates', []))}곳 · {val} USD" if val else "완료"
    if tool == "supply_risk":
        return f"부품 {len(r.get('parts', []))}개 · 대체품 {len(r.get('alternates', []))}개"
    if tool == "revision_diff":
        return f"변경 라인 {len(r.get('changes', []))}개"
    if tool == "search_docs":
        # 실제로 실행한 검색 방식을 함께 보여 준다 (임베딩 장애로 BM25 만 쓴 경우를 숨기지 않는다)
        eff = r.get("effective_mode") or r.get("mode")
        how = {"hybrid": "BM25+벡터", "bm25": "BM25만", "vector": "벡터만"}.get(eff, "검색 실패")
        return f"문서 {len(r.get('hits', []))}개 · {how}"
    return "완료"
