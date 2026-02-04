"""Thread-safe connection state tracking per API key.

This module provides in-memory connection tracking for MCP endpoints.
Ensures no single API key can monopolize server resources by enforcing
a maximum number of concurrent connections per key.

Uses asyncio.Lock for thread-safe operations in async code.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Maximum concurrent connections per API key
# Conservative limit: allows 3-4 Claude Desktop windows + buffer
# Based on typical MCP client usage patterns
MAX_CONNECTIONS_PER_KEY = 5


@dataclass
class ConnectionState:
    """Tracks active connections per API key.

    Thread-safe via asyncio.Lock. All operations that modify state
    must acquire the lock first.

    Attributes:
        connections: Maps API key ID to set of active connection IDs
        last_activity: Maps connection ID to last activity timestamp
    """

    connections: Dict[int, Set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    last_activity: Dict[str, datetime] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def add_connection(self, api_key_id: int, connection_id: str) -> bool:
        """Add a connection for an API key.

        Atomically checks the connection limit and adds the connection if
        under the limit. The lock is held for the entire check-and-add
        operation to prevent race conditions.

        Args:
            api_key_id: The API key's database ID
            connection_id: Unique identifier for this connection

        Returns:
            True if connection was added successfully
            False if connection limit exceeded
        """
        async with self._lock:
            current_count = len(self.connections[api_key_id])
            if current_count >= MAX_CONNECTIONS_PER_KEY:
                logger.debug(
                    "Connection limit check: api_key_id=%d has %d connections (limit=%d)",
                    api_key_id,
                    current_count,
                    MAX_CONNECTIONS_PER_KEY,
                )
                return False

            self.connections[api_key_id].add(connection_id)
            self.last_activity[connection_id] = datetime.now(timezone.utc)

            logger.debug(
                "Connection added: api_key_id=%d, connection_id=%s, total=%d",
                api_key_id,
                connection_id,
                len(self.connections[api_key_id]),
            )
            return True

    async def remove_connection(
        self, api_key_id: int, connection_id: str
    ) -> None:
        """Remove a connection on disconnect.

        Cleans up the connection from tracking state. Also removes empty
        API key entries to prevent unbounded memory growth.

        Args:
            api_key_id: The API key's database ID
            connection_id: Unique identifier for this connection
        """
        async with self._lock:
            self.connections[api_key_id].discard(connection_id)
            self.last_activity.pop(connection_id, None)

            # Clean up empty sets to prevent memory growth
            if not self.connections[api_key_id]:
                del self.connections[api_key_id]

            logger.debug(
                "Connection removed: api_key_id=%d, connection_id=%s",
                api_key_id,
                connection_id,
            )

    async def update_activity(self, connection_id: str) -> None:
        """Update last activity timestamp for a connection.

        Used for staleness tracking to identify connections that can be
        cleaned up.

        Args:
            connection_id: Unique identifier for this connection
        """
        async with self._lock:
            if connection_id in self.last_activity:
                self.last_activity[connection_id] = datetime.now(timezone.utc)

    async def get_stale_connections(
        self, cutoff: datetime
    ) -> List[Tuple[int, str]]:
        """Get connections with no activity since cutoff time.

        Used by cleanup task to identify stale connections that should
        be removed.

        Args:
            cutoff: Datetime threshold - connections with last_activity
                before this time are considered stale

        Returns:
            List of (api_key_id, connection_id) tuples for stale connections
        """
        stale: List[Tuple[int, str]] = []

        async with self._lock:
            for connection_id, last_active in self.last_activity.items():
                if last_active < cutoff:
                    # Find which API key owns this connection
                    for api_key_id, conn_set in self.connections.items():
                        if connection_id in conn_set:
                            stale.append((api_key_id, connection_id))
                            break

        return stale

    async def get_connection_count(self, api_key_id: int) -> int:
        """Get current connection count for an API key.

        Args:
            api_key_id: The API key's database ID

        Returns:
            Number of active connections for this API key
        """
        async with self._lock:
            return len(self.connections.get(api_key_id, set()))


# Module-level singleton instance
connection_tracker = ConnectionState()
