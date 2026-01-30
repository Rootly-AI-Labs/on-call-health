"""
Unit tests for token refresh coordinator.
"""
import asyncio
import json
import unittest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from app.services.token_refresh_coordinator import (
    refresh_token_with_lock,
    invalidate_token_cache,
    _get_redis_client,
    _build_lock_key,
    _build_cache_key,
    _get_cached_token,
    _cache_token,
)


class TestHelperFunctions(unittest.TestCase):
    """Tests for helper functions."""

    def test_build_lock_key(self):
        """Test lock key generation."""
        key = _build_lock_key("linear", 123)
        self.assertEqual(key, "token:refresh:linear:123")

    def test_build_cache_key(self):
        """Test cache key generation."""
        key = _build_cache_key("github", 456)
        self.assertEqual(key, "token:cache:github:456")

    @patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379'})
    @patch('app.services.token_refresh_coordinator.redis.from_url')
    def test_get_redis_client_success(self, mock_from_url):
        """Test successful Redis client creation."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        client = _get_redis_client()

        self.assertIsNotNone(client)
        mock_from_url.assert_called_once()

    @patch.dict('os.environ', {}, clear=True)
    def test_get_redis_client_no_url(self):
        """Test Redis client returns None when no URL."""
        client = _get_redis_client()
        self.assertIsNone(client)


class TestTokenCaching(unittest.TestCase):
    """Tests for token caching functions."""

    def _run_async(self, coro):
        """Helper to run async functions in tests."""
        return asyncio.run(coro)

    @patch('app.services.token_refresh_coordinator._get_redis_client')
    def test_get_cached_token_success(self, mock_get_client):
        """Test retrieving cached token."""
        mock_client = Mock()
        token_data = {"access_token": "cached_token"}
        mock_client.get.return_value = json.dumps(token_data)
        mock_get_client.return_value = mock_client

        token = self._run_async(_get_cached_token("linear", 123))

        self.assertEqual(token, "cached_token")
        mock_client.get.assert_called_once_with("token:cache:linear:123")

    @patch('app.services.token_refresh_coordinator._get_redis_client')
    def test_get_cached_token_not_found(self, mock_get_client):
        """Test retrieving cached token when not present."""
        mock_client = Mock()
        mock_client.get.return_value = None
        mock_get_client.return_value = mock_client

        token = self._run_async(_get_cached_token("linear", 123))

        self.assertIsNone(token)

    @patch('app.services.token_refresh_coordinator._get_redis_client')
    def test_get_cached_token_redis_unavailable(self, mock_get_client):
        """Test retrieving cached token when Redis unavailable."""
        mock_get_client.return_value = None

        token = self._run_async(_get_cached_token("linear", 123))

        self.assertIsNone(token)

    @patch('app.services.token_refresh_coordinator._get_redis_client')
    def test_cache_token_success(self, mock_get_client):
        """Test caching token."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        self._run_async(_cache_token("linear", 123, "new_token"))

        mock_client.setex.assert_called_once()
        call_args = mock_client.setex.call_args
        self.assertEqual(call_args[0][0], "token:cache:linear:123")
        self.assertEqual(call_args[0][1], 60)  # TTL
        cached_data = json.loads(call_args[0][2])
        self.assertEqual(cached_data["access_token"], "new_token")

    @patch('app.services.token_refresh_coordinator._get_redis_client')
    def test_cache_token_redis_unavailable(self, mock_get_client):
        """Test caching token when Redis unavailable."""
        mock_get_client.return_value = None

        # Should not raise error
        self._run_async(_cache_token("linear", 123, "new_token"))

    @patch('app.services.token_refresh_coordinator._get_redis_client')
    def test_invalidate_token_cache(self, mock_get_client):
        """Test invalidating cached token."""
        mock_client = Mock()
        mock_client.delete.return_value = 1
        mock_get_client.return_value = mock_client

        self._run_async(invalidate_token_cache("linear", 123))

        mock_client.delete.assert_called_once_with("token:cache:linear:123")


class TestRefreshTokenWithLock(unittest.TestCase):
    """Tests for refresh_token_with_lock function."""

    def _run_async(self, coro):
        """Helper to run async functions in tests."""
        return asyncio.run(coro)

    @patch('app.services.token_refresh_coordinator.with_distributed_lock')
    @patch('app.services.token_refresh_coordinator._cache_token')
    def test_refresh_with_lock_acquired(self, mock_cache, mock_lock):
        """Test token refresh when lock acquired."""
        # Mock successful lock acquisition
        mock_lock.return_value.__aenter__ = AsyncMock(return_value=True)
        mock_lock.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_cache.return_value = None

        async def mock_refresh():
            return "new_token"

        async def run_test():
            return await refresh_token_with_lock(
                provider="linear",
                integration_id=123,
                user_id=456,
                refresh_func=mock_refresh
            )

        token = self._run_async(run_test())
        self.assertEqual(token, "new_token")

    @patch('app.services.token_refresh_coordinator.with_distributed_lock')
    @patch('app.services.token_refresh_coordinator._get_cached_token')
    def test_refresh_with_cached_token_on_timeout(self, mock_get_cached, mock_lock):
        """Test using cached token when lock times out."""
        # Mock lock timeout
        mock_lock.return_value.__aenter__ = AsyncMock(return_value=False)
        mock_lock.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_get_cached.return_value = "cached_token"

        async def mock_refresh():
            return "new_token"

        async def run_test():
            return await refresh_token_with_lock(
                provider="linear",
                integration_id=123,
                user_id=456,
                refresh_func=mock_refresh
            )

        token = self._run_async(run_test())
        self.assertEqual(token, "cached_token")
        mock_get_cached.assert_called_once_with("linear", 123)

    @patch('app.services.token_refresh_coordinator.with_distributed_lock')
    @patch('app.services.token_refresh_coordinator._get_cached_token')
    def test_refresh_with_fallback(self, mock_get_cached, mock_lock):
        """Test fallback when lock unavailable and no cached token."""
        # Mock lock unavailable
        mock_lock.return_value.__aenter__ = AsyncMock(return_value=False)
        mock_lock.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_get_cached.return_value = None

        async def mock_refresh():
            return "new_token"

        async def mock_fallback():
            return "fallback_token"

        async def run_test():
            return await refresh_token_with_lock(
                provider="linear",
                integration_id=123,
                user_id=456,
                refresh_func=mock_refresh,
                fallback_func=mock_fallback
            )

        token = self._run_async(run_test())
        self.assertEqual(token, "fallback_token")

    @patch('app.services.token_refresh_coordinator.with_distributed_lock')
    @patch('app.services.token_refresh_coordinator._get_cached_token')
    def test_refresh_no_fallback_raises_error(self, mock_get_cached, mock_lock):
        """Test error when lock unavailable, no cache, no fallback."""
        # Mock lock unavailable
        mock_lock.return_value.__aenter__ = AsyncMock(return_value=False)
        mock_lock.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_get_cached.return_value = None

        async def mock_refresh():
            return "new_token"

        async def run_test():
            return await refresh_token_with_lock(
                provider="linear",
                integration_id=123,
                user_id=456,
                refresh_func=mock_refresh,
                fallback_func=None
            )

        with self.assertRaises(RuntimeError) as context:
            self._run_async(run_test())

        self.assertIn("Failed to acquire lock", str(context.exception))

    @patch('app.services.token_refresh_coordinator.with_distributed_lock')
    @patch('app.services.token_refresh_coordinator._cache_token')
    def test_refresh_func_exception_propagates(self, mock_cache, mock_lock):
        """Test exceptions from refresh_func propagate correctly."""
        # Mock successful lock acquisition
        mock_lock.return_value.__aenter__ = AsyncMock(return_value=True)
        mock_lock.return_value.__aexit__ = AsyncMock(return_value=False)

        async def mock_refresh():
            raise ValueError("Refresh failed")

        async def run_test():
            return await refresh_token_with_lock(
                provider="linear",
                integration_id=123,
                user_id=456,
                refresh_func=mock_refresh
            )

        with self.assertRaises(ValueError) as context:
            self._run_async(run_test())

        self.assertEqual(str(context.exception), "Refresh failed")


if __name__ == '__main__':
    unittest.main()
