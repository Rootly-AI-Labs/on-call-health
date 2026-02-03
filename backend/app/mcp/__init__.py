"""MCP server package."""


def __getattr__(name: str):
    """Lazy import of server components to avoid eager database initialization."""
    if name in ("mcp_app", "mcp_server"):
        from .server import mcp_app, mcp_server
        return {"mcp_app": mcp_app, "mcp_server": mcp_server}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["mcp_app", "mcp_server"]
