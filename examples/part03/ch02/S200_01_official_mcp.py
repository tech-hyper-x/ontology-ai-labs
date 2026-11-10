"""Open Targets official MCP read-only demo. Run from the provided labs/bio-target-agent.

  uv run python ../../examples/part03/ch02/S200_01_official_mcp.py list
  uv run python ../../examples/part03/ch02/S200_01_official_mcp.py query

Official endpoint and query verified on 2026-11-10. Does not update the local snapshot or DB.
Source: https://platform-docs.opentargets.org/data-access/model-context-protocol
Requires fastmcp from the provided bio project; this file is not the complete bio environment.
"""
import argparse
import asyncio
import json
from fastmcp import Client

URL = "https://mcp.platform.opentargets.org/mcp"
QUERY = """query($d:String!){
  meta { dataVersion { year month } }
  disease(efoId:$d) { id name associatedTargets(page:{index:0,size:50}) {
    rows { score target { id approvedSymbol } }
  } }
}"""


async def main(action):
    async with Client(URL, timeout=30) as client:
        tools = await client.list_tools()
        if action == "list":
            for tool in tools:
                schema = getattr(tool, "input_schema", None)
                if schema is None:
                    schema = getattr(tool, "inputSchema", None)
                print(json.dumps({"name": tool.name, "description": tool.description,
                                  "input_schema": schema}, ensure_ascii=False))
            return
        name = "query_open_targets_graphql"
        if name not in {t.name for t in tools}:
            raise RuntimeError("Query tool changed. Inspect the current list and input schema first.")
        response = await client.call_tool(name, {
            "query_string": QUERY, "variables": {"d": "MONDO_0005233"}})
        if response.is_error:
            raise RuntimeError("Official MCP returned an error; keep the fixed snapshot unchanged.")
        payload = response.structured_content
        if not isinstance(payload, dict) or payload.get("status") != "success":
            raise RuntimeError("Unexpected response format; inspect the official response.")
        data = payload["data"]
        disease = data["disease"]
        rows = disease["associatedTargets"]["rows"]
        egfr = next((r for r in rows if r["target"]["approvedSymbol"] == "EGFR"), None)
        print(json.dumps({"release": data["meta"]["dataVersion"],
                          "disease": disease["id"], "target": "EGFR",
                          "association_score": egfr["score"] if egfr else None,
                          "scope": "first 50 associated targets",
                          "target_found_in_scope": egfr is not None}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["list", "query"])
    args = parser.parse_args()
    asyncio.run(main(args.action))
