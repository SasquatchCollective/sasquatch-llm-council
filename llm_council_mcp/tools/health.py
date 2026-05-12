"""Health and provider testing MCP tools."""

from __future__ import annotations

import json

import httpx

from ..client import CouncilClient


def register(server, base_url: str) -> None:
    """Register health and testing tools on the MCP server."""

    @server.tool(description=(
        "Check if the LLM Council++ backend is reachable and which providers are configured. "
        "Returns backend status and a summary of configured API keys and features."
    ))
    async def check_health() -> str:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            # Check backend reachability
            try:
                resp = await http_client.get(f"{base_url}/api/health")
                backend_ok = resp.status_code == 200
                backend_msg = "reachable" if backend_ok else f"error {resp.status_code}"
            except httpx.RequestError as e:
                return json.dumps({
                    "backend": "unreachable",
                    "error": str(e),
                    "base_url": base_url,
                })

        async with CouncilClient(base_url) as client:
            try:
                settings = await client.get_settings()
            except Exception as e:
                return json.dumps({"backend": backend_msg, "settings_error": str(e)})

        configured = []
        for key in ("openrouter", "openai", "anthropic", "google", "mistral", "deepseek", "groq",
                    "tavily", "brave", "serper", "tinyfish"):
            if settings.get(f"{key}_api_key_set"):
                configured.append(key)

        custom_name = settings.get("custom_endpoint_name")
        custom_url = settings.get("custom_endpoint_url")
        if custom_name or custom_url or settings.get("custom_endpoint_api_key_set"):
            configured.append(f"custom ({custom_name or custom_url or 'unnamed'})")

        return json.dumps({
            "backend": backend_msg,
            "base_url": base_url,
            "council_models": settings.get("council_models", []),
            "chairman_model": settings.get("chairman_model"),
            "execution_mode": settings.get("execution_mode"),
            "search_provider": settings.get("search_provider"),
            "configured_providers": configured,
            "ollama_url": settings.get("ollama_base_url"),
            "custom_endpoint": {
                "name": custom_name,
                "url": custom_url,
                "key_set": bool(settings.get("custom_endpoint_api_key_set")),
            } if (custom_name or custom_url) else None,
        }, indent=2)

    @server.tool(description=(
        "Test a specific LLM provider connection to verify the API key is valid. "
        "Supported providers: openrouter, openai, anthropic, google, mistral, deepseek, groq, ollama. "
        "Returns success/failure and a message from the provider. "
        "Optionally provide api_key to test without saving it first."
    ))
    async def test_provider(provider: str, api_key: str | None = None) -> str:
        async with CouncilClient(base_url) as client:
            try:
                result = await client.test_provider(provider, api_key)
            except Exception as e:
                return json.dumps({"success": False, "message": str(e)})
        return json.dumps(result, indent=2)
