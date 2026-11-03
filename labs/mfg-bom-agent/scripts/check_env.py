"""터미널용 환경 점검.

    uv run python scripts/check_env.py

ui.py의 점검 화면과 같은 항목을 터미널에 표로 찍는다. CI나 수강생 안내에서 "이 명령이 OK면 준비 완료"로 쓴다.
Neo4j 또는 Anthropic이 실패하면 종료 코드 1을 돌려주고, MCP와 Langfuse는 선택 항목이라 결과에 영향을 주지 않는다.
"""

from __future__ import annotations

import sys

from mfg_bom_agent.config import get_settings

# 이 두 항목이 없으면 실습을 진행할 수 없다. 나머지는 없어도 앱이 동작한다.
REQUIRED = ("Neo4j", "Anthropic")


def main() -> int:
    s = get_settings()
    results: list[tuple[str, bool, str]] = []

    try:
        from mfg_bom_agent.graph.client import server_info

        info = server_info()
        results.append(
            (
                "Neo4j",
                True,
                f"{info.get('version')} {info.get('edition')} nodes={info.get('nodes')}",
            )
        )
    except Exception as exc:  # noqa: BLE001
        results.append(("Neo4j", False, f"{type(exc).__name__}: {exc}"))

    if s.anthropic_configured:
        try:
            from anthropic import Anthropic

            # Models API 조회는 토큰 비용이 없다. 키 유효성과 모델 ID 존재를 함께 확인한다.
            model = Anthropic(api_key=s.anthropic_api_key.get_secret_value()).models.retrieve(
                s.llm_model
            )
            results.append(("Anthropic", True, f"{model.id} ({model.display_name})"))
        except Exception as exc:  # noqa: BLE001
            results.append(("Anthropic", False, f"{type(exc).__name__}: {exc}"))
    else:
        results.append(("Anthropic", False, "ANTHROPIC_API_KEY 없음"))

    try:
        import httpx

        r = httpx.get(s.mcp_url, timeout=3)
        results.append(("MCP", True, f"HTTP {r.status_code} @ {s.mcp_url}"))
    except Exception as exc:  # noqa: BLE001
        results.append(("MCP", False, f"{type(exc).__name__}: {exc} (서버 미기동이면 정상)"))

    langfuse_detail = s.langfuse_host if s.langfuse_enabled else "비활성 (키 없음 → JSON 로그만)"
    results.append(("Langfuse", True, langfuse_detail))

    width = max(len(name) for name, _, _ in results)
    for name, ok, detail in results:
        print(f"{'OK ' if ok else 'FAIL'}  {name.ljust(width)}  {detail}")

    failed_required = [name for name, ok, _ in results if not ok and name in REQUIRED]
    return 1 if failed_required else 0


if __name__ == "__main__":
    sys.exit(main())
