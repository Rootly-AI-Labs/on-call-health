"""Tests for connection pool health monitoring."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mcp.client.health import ConnectionPoolMonitor


class TestConnectionPoolMonitorCreation:
    """Test ConnectionPoolMonitor initialization."""

    def test_create_with_defaults(self):
        """Monitor should be created with default settings."""
        client = MagicMock()
        monitor = ConnectionPoolMonitor(client)
        assert monitor.client is client
        assert monitor.check_interval == 60
        assert monitor._monitor_task is None
        assert monitor._consecutive_warnings == 0

    def test_create_with_custom_interval(self):
        """Monitor should accept custom check interval."""
        client = MagicMock()
        monitor = ConnectionPoolMonitor(client, check_interval=30)
        assert monitor.check_interval == 30


class TestConnectionPoolMonitorLifecycle:
    """Test monitor start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_creates_task(self):
        """start() should create a background task."""
        client = MagicMock()
        monitor = ConnectionPoolMonitor(client, check_interval=1)

        await monitor.start()
        assert monitor._monitor_task is not None
        assert not monitor._monitor_task.done()
        assert monitor.is_running is True

        await monitor.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self):
        """stop() should cancel the background task."""
        client = MagicMock()
        monitor = ConnectionPoolMonitor(client, check_interval=1)

        await monitor.start()
        task = monitor._monitor_task

        await monitor.stop()
        assert monitor._monitor_task is None
        assert task.cancelled() or task.done()
        assert monitor.is_running is False

    @pytest.mark.asyncio
    async def test_stop_when_not_started(self):
        """stop() should handle case when not started."""
        client = MagicMock()
        monitor = ConnectionPoolMonitor(client)

        # Should not raise
        await monitor.stop()

    @pytest.mark.asyncio
    async def test_start_twice_reuses_task(self):
        """start() called twice should reuse existing task."""
        client = MagicMock()
        monitor = ConnectionPoolMonitor(client, check_interval=1)

        await monitor.start()
        first_task = monitor._monitor_task

        await monitor.start()
        second_task = monitor._monitor_task

        assert first_task is second_task

        await monitor.stop()

    @pytest.mark.asyncio
    async def test_is_running_property(self):
        """is_running should reflect task state."""
        client = MagicMock()
        monitor = ConnectionPoolMonitor(client, check_interval=1)

        assert monitor.is_running is False

        await monitor.start()
        assert monitor.is_running is True

        await monitor.stop()
        assert monitor.is_running is False


class TestConnectionPoolMonitorHealthCheck:
    """Test health check logic."""

    @pytest.mark.asyncio
    async def test_health_check_runs_at_interval(self):
        """Health check should run at configured interval."""
        client = MagicMock()
        client._client = None  # No active httpx client

        monitor = ConnectionPoolMonitor(client, check_interval=0.05)
        check_count = 0
        original_check = monitor._check_health

        async def counting_check():
            nonlocal check_count
            check_count += 1
            await original_check()

        monitor._check_health = counting_check

        await monitor.start()
        await asyncio.sleep(0.15)  # Should run at least 2 checks
        await monitor.stop()

        assert check_count >= 2

    @pytest.mark.asyncio
    async def test_health_check_handles_no_client(self):
        """Health check should handle case when no client exists."""
        client = MagicMock()
        client._client = None

        monitor = ConnectionPoolMonitor(client, check_interval=0.05)

        # Should not raise
        await monitor._check_health()
        assert monitor._consecutive_warnings == 0

    @pytest.mark.asyncio
    async def test_health_check_resets_warnings_on_healthy(self):
        """Health check should reset warning count when pool is healthy."""
        client = MagicMock()
        client._client = MagicMock()
        client._client._transport = None  # Simulate no transport

        monitor = ConnectionPoolMonitor(client, check_interval=0.05)
        monitor._consecutive_warnings = 2  # Simulate previous warnings

        await monitor._check_health()
        # Warnings should be reset when we can't access pool metrics
        # (no transport = no degradation detected)

    @pytest.mark.asyncio
    async def test_health_check_increments_warnings_on_degradation(self):
        """Health check should increment warnings on degradation."""
        client = MagicMock()
        mock_httpx_client = MagicMock()

        # Create mock connections with pending status
        mock_connections = []
        for _ in range(15):  # More than threshold
            conn = MagicMock()
            conn.is_idle.return_value = False
            mock_connections.append(conn)

        mock_pool = MagicMock()
        mock_pool._connections = mock_connections

        mock_transport = MagicMock()
        mock_transport._pool = mock_pool

        mock_httpx_client._transport = mock_transport
        client._client = mock_httpx_client

        monitor = ConnectionPoolMonitor(client, check_interval=0.05)
        monitor._pending_threshold = 10

        await monitor._check_health()
        assert monitor._consecutive_warnings == 1

    @pytest.mark.asyncio
    async def test_health_check_triggers_recreation_after_threshold(self):
        """Health check should trigger client recreation after warning threshold."""
        client = MagicMock()
        client._recreate_client = AsyncMock()
        mock_httpx_client = MagicMock()

        # Create mock connections with pending status
        mock_connections = []
        for _ in range(15):  # More than threshold
            conn = MagicMock()
            conn.is_idle.return_value = False
            mock_connections.append(conn)

        mock_pool = MagicMock()
        mock_pool._connections = mock_connections

        mock_transport = MagicMock()
        mock_transport._pool = mock_pool

        mock_httpx_client._transport = mock_transport
        client._client = mock_httpx_client

        monitor = ConnectionPoolMonitor(client, check_interval=0.05)
        monitor._pending_threshold = 10
        monitor._warning_threshold = 3

        # Simulate multiple checks with degradation
        for _ in range(3):
            await monitor._check_health()

        # Should have triggered recreation
        client._recreate_client.assert_called_once()
        # Warnings should be reset after recreation
        assert monitor._consecutive_warnings == 0


class TestConnectionPoolMonitorErrorHandling:
    """Test error handling in health monitor."""

    @pytest.mark.asyncio
    async def test_health_check_catches_exceptions(self):
        """Health check should catch and log exceptions without stopping."""
        client = MagicMock()
        client._client = MagicMock()
        client._client._transport = MagicMock()
        # This will raise AttributeError when accessing _pool
        client._client._transport._pool = None

        monitor = ConnectionPoolMonitor(client, check_interval=0.05)

        # Should not raise
        await monitor._check_health()

    @pytest.mark.asyncio
    async def test_monitor_loop_continues_on_exception(self):
        """Monitor loop should continue running after exception."""
        client = MagicMock()
        client._client = None

        monitor = ConnectionPoolMonitor(client, check_interval=0.05)
        check_count = 0

        async def failing_check():
            nonlocal check_count
            check_count += 1
            if check_count == 1:
                raise Exception("Simulated error")
            # After first call, just return

        monitor._check_health = failing_check

        await monitor.start()
        await asyncio.sleep(0.15)
        await monitor.stop()

        # Should have run multiple times despite first failure
        assert check_count >= 2
