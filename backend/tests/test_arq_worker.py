"""
Unit tests for ARQ worker configuration and pool management.

Tests cover:
- Redis connection settings parsing
- ARQ pool creation and cleanup
- Worker configuration
- Error handling and edge cases
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from app.workers.arq_worker import (
    WorkerSettings,
    get_arq_pool,
    get_redis_settings,
    shutdown_arq_pool,
)


class TestRedisSettings:
    """Test Redis connection settings parsing."""

    @patch('app.workers.arq_worker.settings')
    def test_parse_redis_url_basic(self, mock_settings):
        """Test parsing basic Redis URL."""
        mock_settings.ARQ_REDIS_URL = "redis://localhost:6379"
        mock_settings.ARQ_TIMEOUT = 30

        redis_settings = get_redis_settings()

        assert redis_settings.host == "localhost"
        assert redis_settings.port == 6379
        assert redis_settings.database == 1  # Default for ARQ
        assert redis_settings.conn_timeout == 30

    @patch('app.workers.arq_worker.settings')
    def test_parse_redis_url_with_database(self, mock_settings):
        """Test parsing Redis URL with database number."""
        mock_settings.ARQ_REDIS_URL = "redis://localhost:6379/2"
        mock_settings.ARQ_TIMEOUT = 30

        redis_settings = get_redis_settings()

        assert redis_settings.host == "localhost"
        assert redis_settings.port == 6379
        assert redis_settings.database == 2

    @patch('app.workers.arq_worker.settings')
    def test_parse_redis_url_custom_host_port(self, mock_settings):
        """Test parsing Redis URL with custom host and port."""
        mock_settings.ARQ_REDIS_URL = "redis://redis.example.com:7000/1"
        mock_settings.ARQ_TIMEOUT = 30

        redis_settings = get_redis_settings()

        assert redis_settings.host == "redis.example.com"
        assert redis_settings.port == 7000
        assert redis_settings.database == 1

    @patch('app.workers.arq_worker.settings')
    def test_parse_redis_url_no_port(self, mock_settings):
        """Test parsing Redis URL without port (uses default 6379)."""
        mock_settings.ARQ_REDIS_URL = "redis://localhost"
        mock_settings.ARQ_TIMEOUT = 30

        redis_settings = get_redis_settings()

        assert redis_settings.host == "localhost"
        assert redis_settings.port == 6379  # Default

    @patch('app.workers.arq_worker.settings')
    def test_parse_invalid_redis_url_uses_defaults(self, mock_settings):
        """Test that invalid Redis URL falls back to defaults."""
        mock_settings.ARQ_REDIS_URL = "invalid://not-a-url"
        mock_settings.ARQ_TIMEOUT = 30

        redis_settings = get_redis_settings()

        # Should fall back to defaults without raising exception
        assert redis_settings.host == "localhost"
        assert redis_settings.port == 6379
        assert redis_settings.database == 1

    @patch('app.workers.arq_worker.settings')
    def test_redis_settings_includes_retries(self, mock_settings):
        """Test that Redis settings include retry configuration."""
        mock_settings.ARQ_REDIS_URL = "redis://localhost:6379"
        mock_settings.ARQ_TIMEOUT = 30

        redis_settings = get_redis_settings()

        assert redis_settings.conn_retries == 3
        assert redis_settings.conn_retry_delay == 1


class TestARQPool:
    """Test ARQ pool creation and management."""

    @pytest_asyncio.fixture
    async def cleanup_pool(self):
        """Cleanup pool after each test."""
        yield
        # Reset global pool
        import app.workers.arq_worker as worker_module
        worker_module._arq_pool = None

    @pytest.mark.asyncio
    async def test_get_arq_pool_creates_pool(self, cleanup_pool):
        """Test that get_arq_pool creates a new pool."""
        with patch('app.workers.arq_worker.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            pool = await get_arq_pool()

            assert pool == mock_pool
            mock_create_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_arq_pool_reuses_existing_pool(self, cleanup_pool):
        """Test that get_arq_pool reuses existing pool (singleton)."""
        with patch('app.workers.arq_worker.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            # First call creates pool
            pool1 = await get_arq_pool()
            # Second call reuses pool
            pool2 = await get_arq_pool()

            assert pool1 == pool2
            mock_create_pool.assert_called_once()  # Only called once

    @pytest.mark.asyncio
    async def test_get_arq_pool_connection_error(self, cleanup_pool):
        """Test error handling when Redis connection fails."""
        with patch('app.workers.arq_worker.create_pool') as mock_create_pool:
            mock_create_pool.side_effect = ConnectionError("Redis connection failed")

            with pytest.raises(ConnectionError, match="ARQ Redis connection failed"):
                await get_arq_pool()

    @pytest.mark.asyncio
    async def test_shutdown_arq_pool_closes_pool(self, cleanup_pool):
        """Test that shutdown_arq_pool closes the pool."""
        with patch('app.workers.arq_worker.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            # Create pool
            await get_arq_pool()

            # Shutdown pool
            await shutdown_arq_pool()

            mock_pool.close.assert_called_once_with(close_connection_pool=True)

    @pytest.mark.asyncio
    async def test_shutdown_arq_pool_no_pool(self, cleanup_pool):
        """Test that shutdown_arq_pool handles missing pool gracefully."""
        # Should not raise exception when pool is None
        await shutdown_arq_pool()

    @pytest.mark.asyncio
    async def test_shutdown_arq_pool_error_handling(self, cleanup_pool):
        """Test error handling during pool shutdown."""
        with patch('app.workers.arq_worker.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_pool.close.side_effect = Exception("Close failed")
            mock_create_pool.return_value = mock_pool

            await get_arq_pool()

            # Should not raise exception, just log error
            await shutdown_arq_pool()

            # Pool should be None after shutdown attempt
            import app.workers.arq_worker as worker_module
            assert worker_module._arq_pool is None


class TestWorkerSettings:
    """Test ARQ worker configuration."""

    def test_worker_settings_has_tasks(self):
        """Test that WorkerSettings includes task functions."""
        assert len(WorkerSettings.functions) > 0
        assert hasattr(WorkerSettings.functions[0], '__name__')

    def test_worker_settings_queue_name(self):
        """Test that queue name is configured."""
        assert WorkerSettings.queue_name == "analysis_queue"

    def test_worker_settings_job_timeout(self):
        """Test that job timeout is appropriate for long-running analyses."""
        # Analyses take 2-5 minutes, timeout should be generous
        assert WorkerSettings.job_timeout >= 300  # At least 5 minutes

    def test_worker_settings_max_tries(self):
        """Test that retry configuration is reasonable."""
        assert WorkerSettings.max_tries >= 1
        assert WorkerSettings.max_tries <= 5  # Not too many retries

    def test_worker_settings_has_startup_hook(self):
        """Test that startup hook is configured."""
        assert WorkerSettings.on_startup is not None
        assert callable(WorkerSettings.on_startup)

    def test_worker_settings_has_shutdown_hook(self):
        """Test that shutdown hook is configured."""
        assert WorkerSettings.on_shutdown is not None
        assert callable(WorkerSettings.on_shutdown)

    def test_worker_settings_uses_config(self):
        """Test that WorkerSettings uses configuration from settings."""
        from app.core.config import settings

        # Worker settings should match config
        assert WorkerSettings.keep_result == settings.ARQ_KEEP_RESULT
        assert WorkerSettings.retry_jobs == settings.ARQ_RETRY_JOBS


class TestWorkerLifecycle:
    """Test worker startup and shutdown hooks."""

    def teardown_method(self):
        """Cleanup signal handlers after each test."""
        try:
            from app.workers.signal_handler import unregister_signal_handlers
            unregister_signal_handlers()
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_startup_calls_resume_analyses(self):
        """Test that startup hook calls resume_interrupted_analyses."""
        with patch('app.workers.tasks.resume_interrupted_analyses') as mock_resume:
            mock_resume.return_value = AsyncMock()

            from app.workers.arq_worker import startup
            await startup({})

            mock_resume.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_handles_resume_error(self):
        """Test that startup continues even if resume fails."""
        with patch('app.workers.tasks.resume_interrupted_analyses') as mock_resume:
            mock_resume.side_effect = Exception("Resume failed")

            from app.workers.arq_worker import startup
            # Should not raise exception
            await startup({})

    @pytest.mark.asyncio
    async def test_shutdown_completes_successfully(self):
        """Test that shutdown hook completes without error."""
        from app.workers.arq_worker import shutdown

        # Should complete without exception
        await shutdown({})


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest_asyncio.fixture
    async def cleanup_pool(self):
        """Cleanup pool after each test."""
        yield
        # Reset global pool
        import app.workers.arq_worker as worker_module
        worker_module._arq_pool = None

    @pytest.mark.asyncio
    async def test_concurrent_pool_creation(self, cleanup_pool):
        """Test that concurrent get_arq_pool calls are safe."""
        with patch('app.workers.arq_worker.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            # Simulate concurrent calls
            import asyncio
            results = await asyncio.gather(
                get_arq_pool(),
                get_arq_pool(),
                get_arq_pool()
            )

            # All should return same pool
            assert results[0] == results[1] == results[2]
            # Pool should only be created once
            assert mock_create_pool.call_count == 1

    @patch('app.workers.arq_worker.settings')
    def test_redis_url_with_query_params(self, mock_settings):
        """Test parsing Redis URL with query parameters."""
        mock_settings.ARQ_REDIS_URL = "redis://localhost:6379/1?password=secret"
        mock_settings.ARQ_TIMEOUT = 30

        redis_settings = get_redis_settings()

        # Should strip query params but parse host/port/db
        assert redis_settings.host == "localhost"
        assert redis_settings.port == 6379
        assert redis_settings.database == 1
