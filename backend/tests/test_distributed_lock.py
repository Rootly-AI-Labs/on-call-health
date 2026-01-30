"""
Unit tests for distributed lock utility.
"""
import asyncio
import unittest
from unittest.mock import Mock, patch, MagicMock
import redis

from app.core.distributed_lock import (
    DistributedLock,
    with_distributed_lock,
    _get_redis_client
)


class TestGetRedisClient(unittest.TestCase):
    """Tests for Redis client creation."""

    @patch('app.core.distributed_lock.redis.from_url')
    @patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379'})
    def test_get_redis_client_success(self, mock_from_url):
        """Test successful Redis client creation."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        client = _get_redis_client()

        self.assertIsNotNone(client)
        mock_from_url.assert_called_once_with('redis://localhost:6379', decode_responses=True)
        mock_client.ping.assert_called_once()

    @patch.dict('os.environ', {}, clear=True)
    def test_get_redis_client_no_url(self):
        """Test Redis client returns None when no URL configured."""
        client = _get_redis_client()
        self.assertIsNone(client)

    @patch('app.core.distributed_lock.redis.from_url')
    @patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379'})
    def test_get_redis_client_connection_error(self, mock_from_url):
        """Test Redis client returns None on connection error."""
        mock_from_url.side_effect = redis.ConnectionError("Connection refused")

        client = _get_redis_client()

        self.assertIsNone(client)


class TestDistributedLock(unittest.TestCase):
    """Tests for DistributedLock class."""

    def _run_async(self, coro):
        """Helper to run async functions in tests."""
        return asyncio.run(coro)

    @patch('app.core.distributed_lock._get_redis_client')
    def test_acquire_success(self, mock_get_client):
        """Test successful lock acquisition."""
        mock_client = Mock()
        mock_client.set.return_value = True
        mock_get_client.return_value = mock_client

        lock = DistributedLock("test:key", ttl_seconds=30, timeout_seconds=5)
        acquired = self._run_async(lock.acquire())

        self.assertTrue(acquired)
        self.assertTrue(lock.acquired)
        mock_client.set.assert_called_once()
        call_args = mock_client.set.call_args
        self.assertEqual(call_args[0][0], "lock:test:key")
        self.assertEqual(call_args[1]['nx'], True)
        self.assertEqual(call_args[1]['ex'], 30)

    @patch('app.core.distributed_lock._get_redis_client')
    def test_acquire_redis_unavailable(self, mock_get_client):
        """Test lock acquisition when Redis unavailable."""
        mock_get_client.return_value = None

        lock = DistributedLock("test:key")
        acquired = self._run_async(lock.acquire())

        self.assertFalse(acquired)
        self.assertFalse(lock.acquired)

    @patch('app.core.distributed_lock._get_redis_client')
    async def test_acquire_timeout(self, mock_get_client):
        """Test lock acquisition timeout."""
        mock_client = Mock()
        mock_client.set.return_value = False  # Lock held by another process
        mock_get_client.return_value = mock_client

        lock = DistributedLock("test:key", timeout_seconds=0.2, poll_interval_seconds=0.05)
        acquired = await lock.acquire()

        self.assertFalse(acquired)
        self.assertFalse(lock.acquired)
        self.assertGreater(mock_client.set.call_count, 1)  # Multiple attempts

    @patch('app.core.distributed_lock._get_redis_client')
    def test_release_success(self, mock_get_client):
        """Test successful lock release."""
        mock_client = Mock()
        mock_client.set.return_value = True
        mock_client.eval.return_value = 1  # Successful delete
        mock_get_client.return_value = mock_client

        lock = DistributedLock("test:key")
        self._run_async(lock.acquire())
        released = self._run_async(lock.release())

        self.assertTrue(released)
        self.assertFalse(lock.acquired)
        mock_client.eval.assert_called_once()

    @patch('app.core.distributed_lock._get_redis_client')
    def test_release_not_acquired(self, mock_get_client):
        """Test release when lock not acquired."""
        lock = DistributedLock("test:key")
        released = self._run_async(lock.release())

        self.assertFalse(released)

    @patch('app.core.distributed_lock._get_redis_client')
    async def test_context_manager_success(self, mock_get_client):
        """Test lock as context manager."""
        mock_client = Mock()
        mock_client.set.return_value = True
        mock_client.eval.return_value = 1
        mock_get_client.return_value = mock_client

        lock = DistributedLock("test:key")

        async with lock:
            self.assertTrue(lock.acquired)

        self.assertFalse(lock.acquired)
        mock_client.eval.assert_called_once()  # Release called

    @patch('app.core.distributed_lock._get_redis_client')
    async def test_context_manager_acquire_fails(self, mock_get_client):
        """Test context manager when lock acquisition fails."""
        mock_get_client.return_value = None

        lock = DistributedLock("test:key")

        with self.assertRaises(RuntimeError) as context:
            async with lock:
                pass

        self.assertIn("Failed to acquire distributed lock", str(context.exception))


class TestWithDistributedLock(unittest.TestCase):
    """Tests for with_distributed_lock context manager."""

    def _run_async(self, coro):
        """Helper to run async functions in tests."""
        return asyncio.run(coro)

    @patch('app.core.distributed_lock._get_redis_client')
    async def test_with_distributed_lock_success(self, mock_get_client):
        """Test successful lock acquisition with context manager."""
        mock_client = Mock()
        mock_client.set.return_value = True
        mock_client.eval.return_value = 1
        mock_get_client.return_value = mock_client

        async with with_distributed_lock("test:key") as acquired:
            self.assertTrue(acquired)

        mock_client.eval.assert_called_once()

    @patch('app.core.distributed_lock._get_redis_client')
    async def test_with_distributed_lock_redis_unavailable(self, mock_get_client):
        """Test context manager when Redis unavailable."""
        mock_get_client.return_value = None

        async with with_distributed_lock("test:key") as acquired:
            self.assertFalse(acquired)

    @patch('app.core.distributed_lock._get_redis_client')
    async def test_with_distributed_lock_timeout(self, mock_get_client):
        """Test context manager with lock timeout."""
        mock_client = Mock()
        mock_client.set.return_value = False  # Lock held
        mock_get_client.return_value = mock_client

        async with with_distributed_lock("test:key", timeout_seconds=0.1) as acquired:
            self.assertFalse(acquired)


if __name__ == '__main__':
    unittest.main()
