"""MCP transport layer with Streamable HTTP and SSE endpoints.

This module creates an ASGI application that exposes the MCP server via:
- /mcp: Streamable HTTP transport (modern MCP clients)
- /sse: Server-Sent Events transport (legacy backward compatibility)
- /health: Health check endpoint for AWS ALB integration

Stateless mode is enabled for horizontal scaling behind load balancers.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

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
    streamable_http = mcp_server.streamable_http_app()
    sse_transport = mcp_server.sse_app()

    # Create composite Starlette app with all routes
    app = Starlette(
        routes=[
            Route("/health", health_check, methods=["GET"]),
            Mount("/mcp", app=streamable_http),
            Mount("/sse", app=sse_transport),
        ]
    )

    logger.info(
        "MCP transport initialized: /health, /mcp (streamable HTTP), /sse (legacy)"
    )

    return app


# Create the ASGI application
# This is the main export for mounting in FastAPI main.py
mcp_http_app = _create_mcp_http_app()
