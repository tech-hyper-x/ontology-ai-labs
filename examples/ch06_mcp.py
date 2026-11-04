"""Ch6 MCP 실제 호출: HTTP·inprocess 선택. DB 쓰기·LLM·임베딩 호출 없음."""
import argparse
import asyncio
import json
from pathlib import Path
from fastmcp import Client
from mfg_bom_agent.config import get_settings

CASES = {
    "usage": ("where_used", {"part": "2000-0025-0002"}),
    "explode": ("bom_explode", {"part": "2000-0025-0002", "units": 50}),
    "servo": ("change_impact", {"change_type": "discontinue", "part": "2000-0025-0002", "units": 50}),
    "motor": ("change_impact", {"change_type": "price_percent", "part": "5203-2402-0027", "value": "15", "units": 100}),
    "purchase": ("purchase_quantity", {"part": "1522-0010-0060", "required_each": "7"}),
    "cost": ("cost_rollup", {"units": 1, "scope": "mechanical"}),
    "wheel": ("change_impact", {"change_type": "ecn", "ecn": "ECN-2024-06-18-72edc6e", "units": 1}),
    "missing": ("where_used", {"part": "9999-9999-9999"}),
    "absent": ("where_used", {"part": "5202-2402-0027"}),
    "invalid-units": ("bom_explode", {"part": "2000-0025-0002", "units": 0}),
    "missing-value": ("change_impact", {"change_type": "price_percent", "part": "5203-2402-0027", "units": 100}),
}


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("case", choices=["list", "custom", *CASES])
    p.add_argument("--transport", choices=["http", "inprocess"], default="http")
    p.add_argument("--revision")
    p.add_argument("--input", type=Path, help="custom의 {tool,arguments} JSON")
    args = p.parse_args()
    if args.transport == "inprocess":
        from mfg_bom_agent.mcp_server import mcp
        target = mcp
    else:
        target = get_settings().mcp_url
    if args.case == "custom":
        if args.input is None:
            p.error("custom에는 --input이 필요합니다")
        custom = json.loads(args.input.read_text(encoding="utf-8"))
        tool, inputs = custom["tool"], dict(custom["arguments"])
    elif args.case != "list":
        tool, predefined = CASES[args.case]
        inputs = dict(predefined)
    if args.case != "list" and args.revision:
        inputs["revision"] = args.revision
    async with Client(target, timeout=get_settings().request_timeout_seconds) as client:
        if args.case == "list":
            tools = await client.list_tools()
            print(json.dumps([dict(name=t.name, description=t.description, inputSchema=t.input_schema)
                              for t in tools], ensure_ascii=False, indent=2))
            result = await client.call_tool("ping", {}, raise_on_error=False)
        else:
            print(json.dumps(dict(tool=tool, arguments=inputs), ensure_ascii=False, indent=2))
            result = await client.call_tool(tool, inputs, raise_on_error=False)
        print(json.dumps(dict(protocol_error=result.is_error, structured_content=result.structured_content,
                              content=[c.model_dump(mode="json") for c in result.content]),
                         ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
