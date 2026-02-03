"""
Connection pool health monitoring for OnCallHealth REST API client.

Provides background monitoring of httpx client connection pool health
and automatic client recreation when degradation is detected.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import OnCallHealthClient

logger = logging.getLogger(__name__)


class ConnectionPoolMonitor:
    """Monitor httpx client connection pool health.

    Runs a background task that periodically checks the health of the
    connection pool and triggers client recreation if degradation is
    detected (e.g., too many pending connections for consecutive checks).

    Attributes:
        client: The OnCallHealthClient to monitor
        check_interval: Seconds between health checks
    """

    def __init__(
        self,
        client: "OnCallHealthClient",
        check_interval: int = 60,
    ):
        """Initialize the connection pool monitor.

        Args:
            client: OnCallHealthClient instance to monitor
            check_interval: Seconds between health checks (default: 60)
        """
        self.client = client
        self.check_interval = check_interval
        self._monitor_task: asyncio.Task | None = None
        self._consecutive_warnings = 0
        self._warning_threshold = 3
        self._pending_threshold = 10

    async def start(self) -> None:
        """Start background health monitoring.

        Creates an asyncio task that runs _monitor_loop indefinitely
        until stop() is called.
        """
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("Connection pool health monitor started")

    async def stop(self) -> None:
        """Stop health monitoring.

        Cancels the background task and waits for it to complete.
        """
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
            logger.info("Connection pool health monitor stopped")

    async def _monitor_loop(self) -> None:
        """Periodically check connection pool health.

        Runs until cancelled, sleeping for check_interval seconds between
        health checks.
        """
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _check_health(self) -> None:
        """Check pool metrics and trigger recreation if degraded.

        Monitors the connection pool for signs of degradation such as
        excessive pending requests. If degradation is detected for
        consecutive checks exceeding the warning threshold, triggers
        client recreation.
        """
        if self.client._client is None:
            self._consecutive_warnings = 0
            return

        # Access internal pool state (may vary by httpx version)
        # httpx AsyncClient uses httpcore for connection pooling
        try:
            # Check if the underlying transport exists
            transport = getattr(self.client._client, "_transport", None)
            if transport is None:
                logger.debug("No transport available for health check")
                return

            # Try to get pool info from httpcore transport
            pool = getattr(transport, "_pool", None)
            if pool is None:
                logger.debug("No pool available for health check")
                return

            # Get connection stats if available
            connections = getattr(pool, "_connections", [])
            num_connections = len(connections)

            # Count pending/idle connections
            pending_count = 0
            idle_count = 0

            for conn in connections:
                if hasattr(conn, "is_idle"):
                    if conn.is_idle():
                        idle_count += 1
                    else:
                        pending_count += 1

            logger.debug(
                f"Pool health: {num_connections} connections "
                f"({idle_count} idle, {pending_count} pending)"
            )

            # Check for degradation: too many pending connections
            if pending_count > self._pending_threshold:
                self._consecutive_warnings += 1
                logger.warning(
                    f"Connection pool degradation detected: "
                    f"{pending_count} pending connections "
                    f"(warning {self._consecutive_warnings}/{self._warning_threshold})"
                )

                if self._consecutive_warnings >= self._warning_threshold:
                    logger.warning(
                        "Connection pool health degraded for "
                        f"{self._consecutive_warnings} consecutive checks. "
                        "Triggering client recreation."
                    )
                    await self.client._recreate_client()
                    self._consecutive_warnings = 0
            else:
                # Reset warning counter on healthy check
                if self._consecutive_warnings > 0:
                    logger.info("Connection pool health recovered")
                self._consecutive_warnings = 0

        except Exception as e:
            logger.debug(f"Could not access pool metrics: {e}")

    @property
    def is_running(self) -> bool:
        """Check if the monitor is currently running.

        Returns:
            True if the monitor task is active and not done
        """
        return self._monitor_task is not None and not self._monitor_task.done()
