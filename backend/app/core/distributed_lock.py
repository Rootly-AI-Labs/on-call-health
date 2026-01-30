"""
Distributed lock utility using Redis.

Provides distributed locking mechanism to coordinate token refresh operations
across multiple application instances. Uses Redis SETNX pattern with automatic
expiry to prevent deadlocks.
"""
import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import redis

logger = logging.getLogger(__name__)


def _get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client. Returns None if Redis is unavailable."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    try:
        client = redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}")
        return None


class DistributedLock:
    """
    Distributed lock using Redis.

    Uses SET NX EX pattern for atomic lock acquisition with TTL.
    Automatically releases lock on context manager exit.
    """

    def __init__(
        self,
        key: str,
        ttl_seconds: int = 30,
        timeout_seconds: float = 10,
        poll_interval_seconds: float = 0.5
    ):
        """
        Initialize distributed lock.

        Args:
            key: Lock key (will be prefixed with 'lock:')
            ttl_seconds: Lock auto-expiry time (prevents deadlocks)
            timeout_seconds: Max time to wait for lock acquisition
            poll_interval_seconds: Polling interval when waiting for lock
        """
        self.key = f"lock:{key}"
        self.ttl_seconds = ttl_seconds
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.lock_value = str(uuid.uuid4())  # Unique value to identify lock owner
        self.acquired = False
        self.client: Optional[redis.Redis] = None

    async def acquire(self) -> bool:
        """
        Acquire the distributed lock.

        Attempts to acquire lock, polling until timeout if lock is held by another process.

        Returns:
            True if lock acquired, False if Redis unavailable or timeout
        """
        self.client = _get_redis_client()
        if not self.client:
            logger.warning(f"Redis unavailable, cannot acquire distributed lock: {self.key}")
            return False

        start_time = time.time()

        while True:
            try:
                # SET NX EX: Set if Not eXists with EXpiry
                # Returns True if key was set (lock acquired), False if key already exists
                acquired = self.client.set(
                    self.key,
                    self.lock_value,
                    nx=True,  # Only set if key doesn't exist
                    ex=self.ttl_seconds  # Auto-expire after TTL
                )

                if acquired:
                    self.acquired = True
                    logger.debug(f"Acquired distributed lock: {self.key} (TTL: {self.ttl_seconds}s)")
                    return True

                # Lock held by another process, check timeout
                elapsed = time.time() - start_time
                if elapsed >= self.timeout_seconds:
                    logger.warning(
                        f"Timeout waiting for distributed lock: {self.key} "
                        f"(waited {elapsed:.1f}s)"
                    )
                    return False

                # Poll: wait and retry
                await asyncio.sleep(self.poll_interval_seconds)

            except Exception as e:
                logger.warning(f"Error acquiring distributed lock: {self.key}, error: {e}")
                return False

    async def release(self) -> bool:
        """
        Release the distributed lock.

        Only releases if this instance owns the lock (checks lock_value).

        Returns:
            True if lock released successfully
        """
        if not self.acquired or not self.client:
            return False

        try:
            # Lua script for atomic check-and-delete
            # Only delete if lock_value matches (prevents releasing other process's lock)
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            result = self.client.eval(lua_script, 1, self.key, self.lock_value)

            if result:
                logger.debug(f"Released distributed lock: {self.key}")
                self.acquired = False
                return True
            else:
                logger.warning(f"Lock already expired or owned by another process: {self.key}")
                return False

        except Exception as e:
            logger.warning(f"Error releasing distributed lock: {self.key}, error: {e}")
            return False

    async def __aenter__(self):
        """Context manager entry."""
        acquired = await self.acquire()
        if not acquired:
            raise RuntimeError(f"Failed to acquire distributed lock: {self.key}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.release()
        return False


@asynccontextmanager
async def with_distributed_lock(
    key: str,
    ttl_seconds: int = 30,
    timeout_seconds: float = 10
) -> AsyncIterator[bool]:
    """
    Context manager for distributed lock.

    Yields True if lock acquired, False if Redis unavailable.
    Caller should check return value and fall back to alternative locking if needed.

    Example:
        async with with_distributed_lock("token:refresh:user:123") as acquired:
            if acquired:
                # Lock acquired, perform operation
                await refresh_token()
            else:
                # Redis unavailable, use fallback locking
                await refresh_token_with_db_lock()

    Args:
        key: Lock key (will be prefixed with 'lock:')
        ttl_seconds: Lock auto-expiry time
        timeout_seconds: Max time to wait for lock

    Yields:
        True if lock acquired, False if Redis unavailable or timeout
    """
    lock = DistributedLock(key, ttl_seconds, timeout_seconds)
    acquired = await lock.acquire()

    try:
        yield acquired
    finally:
        if acquired:
            await lock.release()
