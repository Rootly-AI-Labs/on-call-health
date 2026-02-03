"""MCP infrastructure safeguards module.

Provides connection tracking and rate limiting for the hosted MCP endpoint
to protect against resource exhaustion and abuse.
"""
from app.mcp.infrastructure.connection_tracker import (
    connection_tracker,
    ConnectionState,
    MAX_CONNECTIONS_PER_KEY,
)

__all__ = [
    "connection_tracker",
    "ConnectionState",
    "MAX_CONNECTIONS_PER_KEY",
]
