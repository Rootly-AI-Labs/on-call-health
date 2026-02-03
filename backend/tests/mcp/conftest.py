"""Pytest configuration for MCP tests.

Provides utilities for transport tests that need the real FastMCP.
"""
import sys
import importlib


# Store reference to real mcp modules before they might be mocked
_real_mcp_imported = False


def _ensure_real_mcp():
    """Ensure real MCP modules are available in sys.modules."""
    global _real_mcp_imported
    if _real_mcp_imported:
        return

    # Check if mcp is a mock (by checking for MagicMock attributes)
    mcp_mod = sys.modules.get("mcp")
    is_mocked = mcp_mod is not None and hasattr(mcp_mod, "_mock_name")

    if is_mocked or mcp_mod is None:
        # Remove ALL mcp-related mocks and reimport from scratch
        modules_to_clear = [k for k in list(sys.modules.keys())
                           if k.startswith("mcp")]
        for mod in modules_to_clear:
            del sys.modules[mod]

        # Import real modules using importlib to bypass any caching issues
        spec = importlib.util.find_spec("mcp")
        if spec is None:
            raise ImportError("Cannot find real mcp package")

        # Now normal import should work
        import mcp
        import mcp.server
        import mcp.server.fastmcp

    _real_mcp_imported = True


def create_fresh_transport_app():
    """Create a fresh MCP transport app for testing.

    This function:
    1. Ensures real MCP modules are loaded (not mocks)
    2. Clears cached app.mcp imports
    3. Creates a fresh transport app instance

    Each call returns a fresh app, avoiding issues with session manager reuse.
    """
    # Ensure real MCP is available
    _ensure_real_mcp()

    # Clear only app.mcp modules to get fresh transport/server instances
    app_mcp_modules = [k for k in list(sys.modules.keys())
                      if k.startswith("app.mcp")]
    for mod in app_mcp_modules:
        del sys.modules[mod]

    # Now import fresh and create app
    from app.mcp.transport import _create_mcp_http_app

    return _create_mcp_http_app()
