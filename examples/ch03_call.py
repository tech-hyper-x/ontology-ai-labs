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
