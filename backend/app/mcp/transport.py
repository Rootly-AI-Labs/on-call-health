"""MCP transport layer with Streamable HTTP and SSE endpoints.

This module creates an ASGI application that exposes the MCP server via:
- /mcp: Streamable HTTP transport (modern MCP clients)
- /sse: Server-Sent Events transport (legacy backward compatibility)
- /health: Health check endpoint for AWS ALB integration

Stateless mode is enabled for horizontal scaling behind load balancers.

CORS is configured for web-based MCP clients (MCP Inspector, browser tools).
SSE heartbeat interval prevents proxy timeouts on long-lived connections.
"""
from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

# SSE heartbeat interval (seconds) - prevents proxy timeout
# ALB default idle timeout is 60s, most proxies are 30-120s
# 30s keeps connections alive without excessive overhead
#
# Note: FastMCP's SSE transport doesn't expose ping_interval configuration.
# For Streamable HTTP (stateless mode), heartbeat is less critical since
# each request is independent. SSE long-polling is where heartbeat matters.
#
# Custom heartbeat implementation options:
# 1. SSE comment format: ": heartbeat\n\n" (transparent to MCP protocol)
# 2. Use ALB idle timeout > 30s to avoid premature connection close
# 3. Configure proxy keep-alive settings at infrastructure level
#
# Current approach: Rely on infrastructure-level keep-alive (Phase 9).
# For production, configure ALB target group idle timeout to 120s.
SSE_HEARTBEAT_INTERVAL = 30

# CORS configuration for web-based MCP clients
# Note: Applied at transport level, not main app level (avoids FastMCP conflicts)
MCP_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "https://oncallhealth.ai",
    "https://www.oncallburnout.com",
    "https://oncallburnout.com",
]

MCP_CORS_HEADERS = [
    "mcp-protocol-version",
    "mcp-session-id",
    "Authorization",
    "Content-Type",
    "X-API-Key",  # Required for MCP API key authentication
]

MCP_CORS_METHODS = ["GET", "POST", "DELETE", "OPTIONS"]

# Headers exposed to browser clients (mcp-session-id critical for session tracking)
MCP_CORS_EXPOSE_HEADERS = ["mcp-session-id"]

cors_middleware = Middleware(
    CORSMiddleware,
    allow_origins=MCP_CORS_ORIGINS,
    allow_methods=MCP_CORS_METHODS,
    allow_headers=MCP_CORS_HEADERS,
    expose_headers=MCP_CORS_EXPOSE_HEADERS,
    allow_credentials=True,
)

if TYPE_CHECKING:
    from starlette.requests import Request

logger = logging.getLogger(__name__)


async def health_check(request: "Request") -> JSONResponse:
    """Health check endpoint for AWS ALB.

    Returns 200 OK with service status. No authentication required.
    ALB should be configured with:
    - Path: /health
    - HealthCheckIntervalSeconds: 30
    - HealthyThresholdCount: 2
    - UnhealthyThresholdCount: 2
    """
    return JSONResponse({"status": "healthy", "service": "on-call-health-mcp"})


def _create_mcp_http_app() -> Starlette:
    """Create composite ASGI app with MCP transport endpoints.

    Returns:
        Starlette application with /health, /mcp, and /sse routes.
    """
    # Import mcp_server locally to avoid circular imports
    # and maintain lazy loading pattern from __init__.py
    from app.mcp.server import mcp_server

    # Get transport apps from FastMCP
    # mcp 1.x provides streamable_http_app() and sse_app() methods
    # These apps define their own routes at /mcp and /sse respectively
    streamable_http = mcp_server.streamable_http_app()
    sse_transport = mcp_server.sse_app()

    # Create lifespan that initializes the session managers
    # The streamable HTTP transport requires a task group to be running
    # Access session_manager from mcp_server (created lazily by streamable_http_app())
    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Initialize MCP transport session managers."""
        logger.info("Starting MCP transport session managers")
        # Get the session manager from mcp_server (public property)
        session_manager = mcp_server.session_manager
        async with session_manager.run():
            logger.info("MCP transport ready")
            yield
        logger.info("MCP transport shut down")

    # Create composite Starlette app by combining routes from all transports
    # Extract routes from each transport app and include in main app
    # This ensures all routes are properly matched at the top level
    routes = [
        Route("/health", health_check, methods=["GET"]),
    ]
    # Add routes from streamable HTTP transport (provides /mcp)
    routes.extend(streamable_http.routes)
    # Add routes from SSE transport (provides /sse and /messages)
    routes.extend(sse_transport.routes)

    app = Starlette(
        routes=routes,
        lifespan=lifespan,
        middleware=[cors_middleware],
    )

    logger.info(
        "MCP transport initialized: /health, /mcp (streamable HTTP), /sse (legacy)"
    )

    return app


# Create the ASGI application
# This is the main export for mounting in FastAPI main.py
mcp_http_app = _create_mcp_http_app()
