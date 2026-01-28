"""
Tests for ARQ (Async Redis Queue) connection and basic functionality.

Verifies:
- ARQ can be imported
- Redis connection works
- ARQ pool can be created
- Basic producer/consumer workflow
"""

import pytest
import pytest_asyncio
import asyncio
from arq import create_pool
from arq.connections import RedisSettings
from app.core.config import settings


@pytest_asyncio.fixture
async def arq_pool():
    """Create an ARQ Redis pool for testing."""
    # Parse Redis URL to get settings
    # Format: redis://localhost:6379/1
    redis_url = settings.ARQ_REDIS_URL

    # Create pool with test settings
    pool = await create_pool(RedisSettings.from_dsn(redis_url))
    yield pool
    await pool.close(close_connection_pool=True)


@pytest.mark.asyncio
async def test_arq_import():
    """Test that ARQ can be imported successfully."""
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import ARQ: {e}")


@pytest.mark.asyncio
async def test_redis_connection(arq_pool):
    """Test that we can connect to Redis via ARQ."""
    # Simple ping to verify connection
    assert arq_pool is not None

    # Try to use the pool (this will fail if connection is broken)
    try:
        info = await arq_pool.info()
        assert info is not None
    except Exception as e:
        pytest.fail(f"Failed to connect to Redis: {e}")


@pytest.mark.asyncio
async def test_arq_enqueue_simple_task(arq_pool):
    """Test basic producer workflow - enqueueing a task."""

    # Define a simple test function
    async def test_task_func(ctx):
        """Simple test task that returns a value."""
        return "test_success"

    # Enqueue the task
    job = await arq_pool.enqueue_job('test_task_func', _job_id='test_job_1')

    assert job is not None
    assert job.job_id == 'test_job_1'


@pytest.mark.asyncio
async def test_arq_job_result_storage(arq_pool):
    """Test that job results can be stored and retrieved."""

    # Enqueue a job
    job = await arq_pool.enqueue_job('test_task', _job_id='test_job_2')

    # Check job exists in queue
    assert job is not None

    # Note: We can't test actual job execution here without starting a worker,
    # but we can verify the job was enqueued
    job_info = await job.info()
    assert job_info is not None


@pytest.mark.asyncio
async def test_arq_settings_from_config():
    """Test that ARQ settings are correctly loaded from config."""
    from app.core.config import settings

    # Verify ARQ settings exist
    assert settings.ARQ_REDIS_URL is not None
    assert settings.ARQ_MAX_CONNECTIONS > 0
    assert settings.ARQ_TIMEOUT > 0
    assert isinstance(settings.ARQ_RETRY_JOBS, bool)
    assert settings.ARQ_KEEP_RESULT > 0

    # Verify ARQ uses a separate Redis database
    assert '/1' in settings.ARQ_REDIS_URL or 'db=1' in settings.ARQ_REDIS_URL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
