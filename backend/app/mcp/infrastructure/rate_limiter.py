"""MCP-specific rate limiting with per-tool limits.

This module provides rate limiting for MCP tool invocations, separate from
the main /api/* endpoint rate limits. Different tools have different limits
based on their resource consumption:
- Expensive operations (analysis_start): lower limits
- Cheap operations (status checks): higher limits

Uses the existing SlowAPI infrastructure from app.core.rate_limiting.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.rate_limiting import limiter

logger = logging.getLogger(__name__)

# Per-tool rate limits for MCP endpoints
# Limits based on resource consumption from research analysis
MCP_RATE_LIMITS = {
    # Expensive operations (creates background job, queries multiple APIs)
    "analysis_start": "5/minute",
    "integrations_list": "20/minute",
    # Cheap operations (single DB query)
    "analysis_status": "60/minute",
    "analysis_results": "60/minute",
    "analysis_current": "30/minute",
    # Default fallback for unknown tools
    "default": "100/minute",
}


def get_mcp_rate_limit_key(api_key_id: int, tool_name: str) -> str:
    """Generate unique rate limit key for MCP tool invocation.

    Uses unique namespace to prevent collision with /api/* limits.

    Args:
        api_key_id: The API key's database ID
        tool_name: Name of the MCP tool being invoked

    Returns:
        Rate limit key in format "mcp:{api_key_id}:{tool_name}"
    """
    return f"mcp:{api_key_id}:{tool_name}"


def extract_tool_name(request: Request) -> Optional[str]:
    """Extract tool name from MCP request body.

    MCP tools/call requests have the format:
    {"method": "tools/call", "params": {"name": "tool_name", ...}}

    Args:
        request: Starlette request object

    Returns:
        Tool name if this is a tool call, None otherwise
    """
    # Body is read asynchronously, so we need to check if it's cached
    # The body should be cached by the middleware before calling this
    body_bytes = getattr(request.state, "_cached_body", None)
    if body_bytes is None:
        return None

    try:
        body = json.loads(body_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    # Check if this is an MCP tools/call request
    method = body.get("method")
    if method != "tools/call":
        return None

    # Extract tool name from params
    params = body.get("params", {})
    tool_name = params.get("name")
    if isinstance(tool_name, str):
        return tool_name

    return None


async def check_rate_limit(
    request: Request, api_key_id: int, tool_name: str
) -> Optional[JSONResponse]:
    """Check rate limit for MCP tool invocation.

    Uses SlowAPI's internal rate limiting mechanism with MCP-specific limits.

    Args:
        request: Starlette request object
        api_key_id: The API key's database ID
        tool_name: Name of the MCP tool being invoked

    Returns:
        None if within rate limit
        JSONResponse with 429 status if rate limit exceeded
    """
    limit_str = MCP_RATE_LIMITS.get(tool_name, MCP_RATE_LIMITS["default"])
    rate_key = get_mcp_rate_limit_key(api_key_id, tool_name)

    # Use SlowAPI's test method to check limit without raising
    # Parse the limit string (e.g., "5/minute" -> 5 requests per 60 seconds)
    try:
        count_str, period = limit_str.split("/")
        limit_count = int(count_str)
    except (ValueError, AttributeError):
        limit_count = 100  # Fallback

    # SlowAPI uses its internal storage to track request counts
    # We use a custom key function for MCP-specific rate limiting
    # Check current usage via limiter's internal state
    try:
        # Get the limiter's storage backend
        storage = limiter._storage

        # Calculate the window key
        if "minute" in limit_str:
            window_seconds = 60
        elif "hour" in limit_str:
            window_seconds = 3600
        else:
            window_seconds = 60

        # Get current count from storage
        # The key format varies by storage backend
        from time import time

        current_window = int(time()) // window_seconds
        storage_key = f"LIMITER/{rate_key}/{current_window}"

        # Try to get current count
        current_count = storage.get(storage_key)
        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)

        # Check if limit would be exceeded
        if current_count >= limit_count:
            retry_after = window_seconds - (int(time()) % window_seconds)
            logger.warning(
                "MCP rate limit exceeded: api_key_id=%d, tool=%s, limit=%s",
                api_key_id,
                tool_name,
                limit_str,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": f"Rate limit exceeded for tool '{tool_name}': {limit_str}",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit_count),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Increment the counter
        storage.incr(storage_key, window_seconds)

        # Add rate limit headers to request state for response
        remaining = max(0, limit_count - current_count - 1)
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = limit_count

    except Exception as e:
        # If rate limiting fails, log and allow the request
        # Better to allow than to incorrectly block
        logger.warning(
            "MCP rate limit check failed (allowing request): %s", str(e)
        )

    return None
