"""
ARQ Worker Configuration.

Provides configuration and pool management for ARQ background workers.
Handles graceful startup/shutdown and Redis connection pooling.
"""
import logging
from typing import Optional
from urllib.parse import urlparse

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from arq.worker import Worker

from ..core.config import settings

logger = logging.getLogger(__name__)

# Global ARQ pool instance (reused across requests)
_arq_pool: Optional[ArqRedis] = None

# Default Redis connection values
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 6379
DEFAULT_DATABASE = 1


def get_redis_settings() -> RedisSettings:
    """
    Get Redis connection settings for ARQ from application config.

    Returns:
        RedisSettings configured with connection parameters

    Security:
        - Uses separate Redis database (db=1) to avoid key collisions
        - Connection timeout prevents hanging on network issues
    """
    redis_url = settings.ARQ_REDIS_URL
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    database = DEFAULT_DATABASE

    try:
        parsed = urlparse(redis_url)
        if parsed.scheme == "redis":
            host = parsed.hostname or DEFAULT_HOST
            port = parsed.port or DEFAULT_PORT
            # Path is like "/1" for database 1, strip leading slash
            if parsed.path and len(parsed.path) > 1:
                db_str = parsed.path.lstrip("/").split("/")[0]
                if db_str.isdigit():
                    database = int(db_str)
    except Exception as e:
        logger.error(f"Failed to parse ARQ_REDIS_URL '{redis_url}': {e}. Using defaults.")

    return RedisSettings(
        host=host,
        port=port,
        database=database,
        conn_timeout=settings.ARQ_TIMEOUT,
        conn_retries=3,
        conn_retry_delay=1,
    )


async def get_arq_pool() -> ArqRedis:
    """
    Get or create ARQ Redis pool for enqueuing jobs.

    Returns:
        ArqRedis pool instance (singleton)

    Note:
        Pool is created once and reused across requests for efficiency.
        Call shutdown_arq_pool() on application shutdown to cleanup.

    Raises:
        ConnectionError: If Redis connection fails after retries
    """
    global _arq_pool

    if _arq_pool is not None:
        return _arq_pool

    redis_settings = get_redis_settings()

    try:
        _arq_pool = await create_pool(redis_settings)
        logger.info(
            f"ARQ pool created: {redis_settings.host}:{redis_settings.port}/{redis_settings.database}"
        )
    except Exception as e:
        logger.error(f"Failed to create ARQ pool: {e}")
        raise ConnectionError(f"ARQ Redis connection failed: {e}") from e

    return _arq_pool


async def shutdown_arq_pool() -> None:
    """
    Shutdown ARQ Redis pool gracefully.

    Call this on application shutdown to release connections.
    """
    global _arq_pool

    if _arq_pool is None:
        return

    try:
        await _arq_pool.close(close_connection_pool=True)
        logger.info("ARQ pool closed")
    except Exception as e:
        logger.error(f"Error closing ARQ pool: {e}")
    finally:
        _arq_pool = None


async def startup(ctx: dict) -> None:
    """
    ARQ worker startup function.

    Called when ARQ worker starts. Used to:
    - Register SIGTERM handler for graceful shutdown
    - Resume interrupted analyses
    - Set up monitoring

    Args:
        ctx: ARQ worker context dictionary
    """
    logger.info("ARQ worker starting up")

    # Register SIGTERM handler for graceful shutdown
    from .signal_handler import register_signal_handlers
    register_signal_handlers()

    # Import here to avoid circular dependency
    from .tasks import resume_interrupted_analyses

    try:
        await resume_interrupted_analyses()
        logger.info("ARQ worker startup complete")
    except Exception as e:
        logger.error(f"Error during ARQ worker startup: {e}")
        # Don't fail startup - worker can still process new jobs


async def shutdown(ctx: dict) -> None:
    """
    ARQ worker shutdown function.

    Called when ARQ worker receives SIGTERM (deployment).
    Allows graceful completion of in-progress jobs.

    Args:
        ctx: ARQ worker context dictionary
    """
    logger.info("ARQ worker shutting down gracefully")


class WorkerSettings:
    """
    ARQ Worker configuration settings.

    Defines how the ARQ worker processes jobs:
    - Queue name and Redis connection
    - Job timeout and retry behavior
    - Concurrency and resource limits
    - Startup/shutdown hooks
    """
    # Import task functions (must be done at class level for ARQ)
    from .tasks import cleanup_stale_analyses, run_analysis_with_checkpoints

    # Task functions to register with the worker
    functions = [run_analysis_with_checkpoints, cleanup_stale_analyses]

    # Redis connection
    redis_settings = get_redis_settings()

    # Worker behavior
    queue_name = "analysis_queue"
    max_jobs = 10
    job_timeout = 600  # 10 minutes (analyses typically take 2-5 min)
    keep_result = settings.ARQ_KEEP_RESULT

    # Retry configuration
    max_tries = 3
    retry_jobs = settings.ARQ_RETRY_JOBS

    # Health check configuration
    health_check_interval = 60

    # Startup/shutdown hooks
    on_startup = startup
    on_shutdown = shutdown

    # Logging
    log_results = True

    # Worker identification
    worker_name = "analysis_worker"


def create_worker() -> Worker:
    """
    Create an ARQ worker instance.

    Used by the ARQ CLI to start worker processes.

    Returns:
        Worker instance configured with WorkerSettings

    Example:
        arq app.workers.arq_worker.WorkerSettings
    """
    return Worker(
        functions=WorkerSettings.functions,
        redis_settings=WorkerSettings.redis_settings,
        queue_name=WorkerSettings.queue_name,
        max_jobs=WorkerSettings.max_jobs,
        job_timeout=WorkerSettings.job_timeout,
        keep_result=WorkerSettings.keep_result,
        on_startup=WorkerSettings.on_startup,
        on_shutdown=WorkerSettings.on_shutdown,
    )


__all__ = ["WorkerSettings", "get_arq_pool", "shutdown_arq_pool"]
