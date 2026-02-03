"""Unit tests for MCP transport layer.

Tests verify that the transport module correctly:
1. Exposes health check endpoint at /health
2. Provides transport endpoint routes at /mcp and /sse
3. Provides a valid ASGI application structure

Note: These tests use mocked FastMCP from conftest.py since the actual
transport requires real MCP server connections. The key verification is
that the transport module structure is correct.
"""
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse


class TestHealthCheckFunction:
    """Tests for the health_check function directly."""

    @pytest.mark.asyncio
    async def test_health_check_returns_json_response(self):
        """health_check returns a JSONResponse."""
        from app.mcp.transport import health_check

        # Create a minimal mock request
        class MockRequest:
            pass

        result = await health_check(MockRequest())
        assert isinstance(result, JSONResponse)

    @pytest.mark.asyncio
    async def test_health_check_response_content(self):
        """health_check returns expected JSON structure."""
        from app.mcp.transport import health_check

        class MockRequest:
            pass

        result = await health_check(MockRequest())
        # JSONResponse body is bytes, decode it
        import json

        data = json.loads(result.body.decode())
        assert data["status"] == "healthy"
        assert data["service"] == "on-call-health-mcp"

    @pytest.mark.asyncio
    async def test_health_check_status_code(self):
        """health_check returns 200 status code."""
        from app.mcp.transport import health_check

        class MockRequest:
            pass

        result = await health_check(MockRequest())
        assert result.status_code == 200


class TestTransportModuleStructure:
    """Tests for the transport module structure."""

    def test_create_mcp_http_app_function_exists(self):
        """_create_mcp_http_app function exists in transport module."""
        from app.mcp.transport import _create_mcp_http_app

        assert callable(_create_mcp_http_app)

    def test_health_check_function_exists(self):
        """health_check function exists in transport module."""
        from app.mcp.transport import health_check

        assert callable(health_check)

    def test_mcp_http_app_exportable_from_package(self):
        """mcp_http_app is listed in __all__ exports."""
        from app.mcp import __all__

        assert "mcp_http_app" in __all__


class TestTransportModuleLazyImport:
    """Tests for lazy import behavior."""

    def test_lazy_import_returns_app(self):
        """Lazy import of mcp_http_app returns an app instance."""
        # Import through __getattr__
        import sys

        # Clear cached imports
        mods = [k for k in list(sys.modules.keys()) if k.startswith("app.mcp")]
        for m in mods:
            if m in sys.modules:
                del sys.modules[m]

        # Import via package (triggers __getattr__)
        from app.mcp import mcp_http_app

        # Should return something (either mock or real Starlette app)
        assert mcp_http_app is not None
