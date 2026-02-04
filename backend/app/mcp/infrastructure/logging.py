"""Structured logging for MCP infrastructure events.

Provides consistent logging for MCP connection lifecycle and limit violations.
Log levels follow user decisions:
- DEBUG: Normal operations (connection open/close, cleanup completed)
- WARNING: Limit violations (connection limit hit, rate limit hit)
- ERROR: Failures (cleanup failed)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("app.mcp.infrastructure")


class MCPEvent:
    """MCP infrastructure event types for structured logging."""

    CONNECTION_OPEN = "connection_open"
    CONNECTION_CLOSE = "connection_close"
    CONNECTION_LIMIT_HIT = "connection_limit_hit"
    RATE_LIMIT_HIT = "rate_limit_hit"
    CLEANUP_COMPLETED = "cleanup_completed"
    CLEANUP_FAILED = "cleanup_failed"


# Events that should log at DEBUG level (normal operations)
_DEBUG_EVENTS = {
    MCPEvent.CONNECTION_OPEN,
    MCPEvent.CONNECTION_CLOSE,
    MCPEvent.CLEANUP_COMPLETED,
}

# Events that should log at WARNING level (limit violations)
_WARNING_EVENTS = {
    MCPEvent.CONNECTION_LIMIT_HIT,
    MCPEvent.RATE_LIMIT_HIT,
}

# Events that should log at ERROR level (failures)
_ERROR_EVENTS = {
    MCPEvent.CLEANUP_FAILED,
}


def truncate_api_key(api_key: Optional[str]) -> str:
    """Truncate API key for safe logging.

    Shows only the last 4 characters with prefix "och_***" to allow
    identification without exposing the full key.

    Args:
        api_key: The full API key string, or None

    Returns:
        Truncated key string, e.g., "och_***abcd" or "N/A" if None/empty
    """
    if not api_key:
        return "N/A"
    if len(api_key) < 4:
        return "och_***"
    return f"och_***{api_key[-4:]}"


def log_mcp_event(
    event: str,
    api_key_id: Optional[int] = None,
    **kwargs,
) -> None:
    """Log an MCP infrastructure event with structured data.

    Automatically determines log level based on event type:
    - DEBUG: connection_open, connection_close, cleanup_completed
    - WARNING: connection_limit_hit, rate_limit_hit
    - ERROR: cleanup_failed

    Args:
        event: Event type from MCPEvent constants
        api_key_id: Database ID of the API key (optional)
        **kwargs: Additional structured fields to include in the log
    """
    extra = {
        "mcp_event": event,
        "api_key_id": api_key_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **kwargs,
    }

    message = f"MCP: {event}"

    if event in _DEBUG_EVENTS:
        logger.debug(message, extra=extra)
    elif event in _WARNING_EVENTS:
        logger.warning(message, extra=extra)
    elif event in _ERROR_EVENTS:
        logger.error(message, extra=extra)
    else:
        # Unknown event type, default to debug
        logger.debug(message, extra=extra)


def log_connection_open(api_key_id: int, connection_id: str) -> None:
    """Log a new MCP connection opened.

    Args:
        api_key_id: Database ID of the API key
        connection_id: Unique identifier for this connection
    """
    log_mcp_event(
        MCPEvent.CONNECTION_OPEN,
        api_key_id=api_key_id,
        connection_id=connection_id,
    )


def log_connection_close(api_key_id: int, connection_id: str) -> None:
    """Log an MCP connection closed.

    Args:
        api_key_id: Database ID of the API key
        connection_id: Unique identifier for this connection
    """
    log_mcp_event(
        MCPEvent.CONNECTION_CLOSE,
        api_key_id=api_key_id,
        connection_id=connection_id,
    )


def log_connection_limit_hit(api_key_id: int) -> None:
    """Log when connection limit is exceeded for an API key.

    Args:
        api_key_id: Database ID of the API key
    """
    log_mcp_event(
        MCPEvent.CONNECTION_LIMIT_HIT,
        api_key_id=api_key_id,
    )


def log_rate_limit_hit(api_key_id: int, tool_name: str, limit: str) -> None:
    """Log when rate limit is exceeded for a tool.

    Args:
        api_key_id: Database ID of the API key
        tool_name: Name of the MCP tool that was rate limited
        limit: The rate limit that was exceeded (e.g., "5/minute")
    """
    log_mcp_event(
        MCPEvent.RATE_LIMIT_HIT,
        api_key_id=api_key_id,
        tool_name=tool_name,
        limit=limit,
    )


def log_cleanup_completed(cleaned_count: int) -> None:
    """Log successful cleanup of stale connections.

    Args:
        cleaned_count: Number of stale connections removed
    """
    log_mcp_event(
        MCPEvent.CLEANUP_COMPLETED,
        cleaned_count=cleaned_count,
    )


def log_cleanup_failed(error: str) -> None:
    """Log cleanup task failure.

    Args:
        error: Description of the error that occurred
    """
    log_mcp_event(
        MCPEvent.CLEANUP_FAILED,
        error=error,
    )
