"""MCP server setup for LLM Council Plus."""

from mcp.server.fastmcp import FastMCP


def create_server(
    base_url: str = "http://localhost:8001",
    host: str = "0.0.0.0",
    port: int = 8002,
) -> FastMCP:
    """Create and configure the LLM Council Plus MCP server.

    Args:
        base_url: Base URL of the LLM Council Plus backend REST API.
        host: Host to bind when running in SSE transport mode.
        port: Port to bind when running in SSE transport mode.

    Returns:
        Configured FastMCP instance with base_url stored as an attribute.
    """
    server = FastMCP(
        name="llm-council-plus",
        instructions=(
            "LLM Council Plus — a 3-stage multi-LLM deliberation system. "
            "Use the council tools to run deliberations, inspect conversations, "
            "and check system health."
        ),
        host=host,
        port=port,
    )

    # Attach base_url so tool modules can retrieve it via server.base_url
    server.base_url = base_url  # type: ignore[attr-defined]

    return server


async def run_stdio(server: FastMCP) -> None:
    """Run the MCP server using stdio transport (for Claude Code / Gemini CLI)."""
    await server.run_stdio_async()


async def run_sse(server: FastMCP, host: str = "0.0.0.0", port: int = 8002) -> None:
    """Run the MCP server using SSE transport (HTTP server mode).

    Note: host and port must be set at create_server() time because FastMCP
    reads them from its settings object at startup.  If the caller passes
    different values here they are ignored; this function signature exists
    for API symmetry with __main__.py — pass host/port to create_server().
    """
    await server.run_sse_async()
