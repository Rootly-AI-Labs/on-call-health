"""Starlette middleware combining connection tracking and rate limiting.

This middleware protects the MCP endpoint from resource exhaustion by:
1. Limiting concurrent connections per API key
2. Rate limiting tool invocations per API key

Applied to mcp_http_app before CORS middleware.
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.mcp.infrastructure.connection_tracker import (
    connection_tracker,
    MAX_CONNECTIONS_PER_KEY,
)
from app.mcp.infrastructure.rate_limiter import (
    check_rate_limit,
    extract_tool_name,
    MCP_RATE_LIMITS,
)
from app.mcp.infrastructure.logging import (
    log_connection_open,
    log_connection_close,
    log_connection_limit_hit,
    log_rate_limit_hit,
)
from app.services.api_key_service import compute_sha256_hash
from app.models import APIKey, SessionLocal

logger = logging.getLogger(__name__)


class MCPInfrastructureMiddleware(BaseHTTPMiddleware):
    """Middleware for MCP connection limits and rate limiting.

    Applies infrastructure safeguards to MCP endpoints:
    - Connection limit: Max concurrent connections per API key
    - Rate limit: Per-tool request limits based on resource consumption

    Health check endpoint is exempt from all limits.
    """

    async def dispatch(
        self, request: Request, call_next
    ) -> Response:
        """Process request with infrastructure checks.

        Args:
            request: Starlette request object
            call_next: Next middleware/handler in chain

        Returns:
            Response from handler or 429 error if limits exceeded
        """
        # Skip health check - must always be available for ALB
        if request.url.path.endswith("/health"):
            return await call_next(request)

        # Extract API key from header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            # No API key - pass through, auth middleware handles rejection
            return await call_next(request)

        # Look up API key ID
        api_key_id = await self._get_api_key_id(api_key)
        if api_key_id is None:
            # Invalid key - pass through, auth middleware handles rejection
            return await call_next(request)

        # Generate unique connection ID for this request
        connection_id = f"{api_key_id}:{uuid.uuid4().hex[:8]}"

        # Check connection limit
        can_connect = await connection_tracker.add_connection(
            api_key_id, connection_id
        )
        if not can_connect:
            log_connection_limit_hit(api_key_id)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "connection_limit_exceeded",
                    "detail": f"Maximum concurrent connections reached ({MAX_CONNECTIONS_PER_KEY}). Close idle connections and retry.",
                    "retry_after": 60,
                },
                headers={"Retry-After": "60"},
            )

        # Log successful connection open
        log_connection_open(api_key_id, connection_id)

        try:
            # Cache request body for rate limit extraction
            # This allows extract_tool_name to access the body
            body = await request.body()
            request.state._cached_body = body

            # Extract tool name and check rate limit (only for tool calls)
            tool_name = extract_tool_name(request)
            if tool_name:
                rate_limit_response = await check_rate_limit(
                    request, api_key_id, tool_name
                )
                if rate_limit_response is not None:
                    # Log rate limit violation
                    limit = MCP_RATE_LIMITS.get(tool_name, MCP_RATE_LIMITS["default"])
                    log_rate_limit_hit(api_key_id, tool_name, limit)
                    return rate_limit_response

            # Update activity timestamp
            await connection_tracker.update_activity(connection_id)

            # Process the request
            response = await call_next(request)

            # Update activity timestamp on successful completion
            await connection_tracker.update_activity(connection_id)

            return response

        finally:
            # Always clean up connection on request completion
            await connection_tracker.remove_connection(api_key_id, connection_id)
            log_connection_close(api_key_id, connection_id)

    async def _get_api_key_id(self, api_key: str) -> Optional[int]:
        """Look up API key ID from database.

        Uses SHA-256 hash for fast indexed lookup, same pattern as auth.

        Args:
            api_key: The full API key string

        Returns:
            API key database ID if valid, None otherwise
        """
        # Validate prefix
        if not api_key.startswith("och_live_"):
            return None

        # Compute SHA-256 hash for fast lookup
        sha256_hash = compute_sha256_hash(api_key)

        # Query database
        db = SessionLocal()
        try:
            api_key_model = (
                db.query(APIKey.id)
                .filter(
                    APIKey.key_hash_sha256 == sha256_hash,
                    APIKey.revoked_at.is_(None),
                )
                .first()
            )
            return api_key_model[0] if api_key_model else None
        finally:
            db.close()
