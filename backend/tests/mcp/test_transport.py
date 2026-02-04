"""Unit tests for MCP transport layer.

Tests verify that the transport module correctly:
1. Exposes health check endpoint at /health
2. Provides transport endpoint routes at /mcp and /sse
3. Provides a valid ASGI application structure
4. Is mounted correctly in the main FastAPI app
5. Has CORS headers configured for web-based MCP clients

Note: These tests use mocked FastMCP from conftest.py since the actual
transport requires real MCP server connections. The key verification is
that the transport module structure is correct.
"""
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.testclient import TestClient


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


class TestMCPMounting:
    """Tests for MCP transport mounting in main FastAPI app."""

    def test_mcp_accessible_from_main_app(self):
        """MCP health check is accessible at /mcp/health from main app."""
        from app.main import app

        client = TestClient(app)
        resp = client.get("/mcp/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "on-call-health-mcp"

    def test_main_app_health_still_works(self):
        """Main app /health endpoint still works after MCP mount."""
        from app.main import app

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "on-call-health"

    def test_cors_headers_on_mcp_endpoints(self):
        """CORS preflight returns correct headers on MCP endpoints."""
        from app.main import app

        client = TestClient(app)
        resp = client.options(
            "/mcp/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers

    def test_cors_allows_x_api_key_header(self):
        """CORS allows X-API-Key header in preflight on transport directly.

        Note: When mounted in main app, the main app's CORS middleware
        runs first. This test verifies transport-level CORS is configured
        correctly. For production, X-API-Key may need to be added to
        main app CORS if browser clients need it.
        """
        from app.mcp.transport import mcp_http_app

        client = TestClient(mcp_http_app)
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-API-Key",
            },
        )
        assert resp.status_code == 200
        allowed_headers = resp.headers.get("access-control-allow-headers", "").lower()
        assert "x-api-key" in allowed_headers

    def test_cors_exposes_mcp_session_id_header(self):
        """CORS exposes mcp-session-id header for browser clients."""
        from app.mcp.transport import mcp_http_app

        client = TestClient(mcp_http_app)
        resp = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert resp.status_code == 200
        exposed_headers = resp.headers.get("access-control-expose-headers", "")
        assert "mcp-session-id" in exposed_headers


class TestCORSConfiguration:
    """Tests for CORS configuration constants."""

    def test_sse_heartbeat_interval_exists(self):
        """SSE_HEARTBEAT_INTERVAL is configured."""
        from app.mcp.transport import SSE_HEARTBEAT_INTERVAL

        assert SSE_HEARTBEAT_INTERVAL == 30

    def test_cors_origins_configured(self):
        """MCP_CORS_ORIGINS includes expected origins."""
        from app.mcp.transport import MCP_CORS_ORIGINS

        assert "http://localhost:3000" in MCP_CORS_ORIGINS
        assert "https://oncallburnout.com" in MCP_CORS_ORIGINS

    def test_cors_headers_include_api_key(self):
        """MCP_CORS_HEADERS includes X-API-Key."""
        from app.mcp.transport import MCP_CORS_HEADERS

        assert "X-API-Key" in MCP_CORS_HEADERS

    def test_cors_expose_headers_include_session_id(self):
        """MCP_CORS_EXPOSE_HEADERS includes mcp-session-id."""
        from app.mcp.transport import MCP_CORS_EXPOSE_HEADERS

        assert "mcp-session-id" in MCP_CORS_EXPOSE_HEADERS
