"""
Tests for integration validation service.
"""
import unittest
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
import httpx
import asyncio

from app.services.integration_validator import (
    IntegrationValidator,
    get_cached_validation,
    set_validation_cache,
    invalidate_validation_cache,
    _validation_cache,
    _cache_lock,
    VALIDATION_CACHE_TTL_SECONDS,
    MAX_CACHE_SIZE,
    needs_refresh,
)
from app.models import GitHubIntegration, LinearIntegration, JiraIntegration


class TestIntegrationValidator(unittest.TestCase):
    """Test suite for IntegrationValidator service."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=Session)
        self.validator = IntegrationValidator(self.mock_db)

    def _run_async(self, coro):
        """Helper to run async functions in tests."""
        return asyncio.run(coro)

    # GitHub Validation Tests

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_success(self, mock_decrypt):
        """Test successful GitHub validation."""
        # Setup
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.user_id = 1
        mock_integration.github_token = "encrypted_token"

        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        # Mock httpx response
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            # Execute
            result = self._run_async(self.validator._validate_github(user_id=1))

        # Assert
        self.assertTrue(result["valid"])
        self.assertIsNone(result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_expired_token(self, mock_decrypt):
        """Test GitHub validation with expired token (401)."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "expired_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("expired or invalid", result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_forbidden(self, mock_decrypt):
        """Test GitHub validation with forbidden token (403)."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "forbidden_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("lacks required permissions", result["error"])

    def test_validate_github_no_integration(self):
        """Test GitHub validation when no integration exists."""
        self.mock_db.query().filter().first.return_value = None

        result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertIsNone(result)

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_timeout(self, mock_decrypt):
        """Test GitHub validation with timeout."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("timed out", result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_network_error(self, mock_decrypt):
        """Test GitHub validation with network error."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.NetworkError("Network error")
            )

            result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("Cannot reach", result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_decryption_error(self, mock_decrypt):
        """Test GitHub validation with decryption error."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.side_effect = Exception("Decryption failed")

        result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("decryption failed", result["error"].lower())

    # Linear Validation Tests

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_linear_success(self, mock_decrypt):
        """Test successful Linear validation."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(hours=12)
        mock_integration.refresh_token = None
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": {"viewer": {"id": "123"}}}
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_linear(user_id=1))

        self.assertTrue(result["valid"])
        self.assertIsNone(result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_linear_graphql_error(self, mock_decrypt):
        """Test Linear validation with GraphQL unauthorized error."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(hours=12)
        mock_integration.refresh_token = None
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "invalid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"errors": [{"message": "Unauthorized"}]}
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_linear(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("expired or invalid", result["error"])

    def test_validate_linear_no_integration(self):
        """Test Linear validation when no integration exists."""
        self.mock_db.query().filter().first.return_value = None

        result = self._run_async(self.validator._validate_linear(user_id=1))

        self.assertIsNone(result)

    # Jira Validation Tests

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_jira_success(self, mock_decrypt):
        """Test successful Jira validation."""
        mock_integration = Mock(spec=JiraIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.jira_cloud_id = "test-cloud-id"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_jira(user_id=1))

        self.assertTrue(result["valid"])
        self.assertIsNone(result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_jira_expired_token(self, mock_decrypt):
        """Test Jira validation with expired token (401)."""
        mock_integration = Mock(spec=JiraIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.jira_cloud_id = "test-cloud-id"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "expired_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_jira(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("expired or invalid", result["error"])

    def test_validate_jira_no_integration(self):
        """Test Jira validation when no integration exists."""
        self.mock_db.query().filter().first.return_value = None

        result = self._run_async(self.validator._validate_jira(user_id=1))

        self.assertIsNone(result)


class TestValidationCache(unittest.TestCase):
    """Test suite for validation caching functions."""

    def setUp(self):
        """Clear cache before each test."""
        _validation_cache.clear()

    def tearDown(self):
        """Clear cache after each test."""
        _validation_cache.clear()

    def test_set_and_get_cached_validation(self):
        """Test setting and retrieving cached validation results."""
        user_id = 1
        results = {
            "github": {"valid": True, "error": None},
            "linear": {"valid": False, "error": "Token expired"}
        }

        set_validation_cache(user_id, results)
        cached = get_cached_validation(user_id)

        self.assertEqual(cached, results)

    def test_get_cached_validation_not_exists(self):
        """Test getting cache for non-existent user returns None."""
        cached = get_cached_validation(999)
        self.assertIsNone(cached)

    def test_get_cached_validation_expired(self):
        """Test that expired cache returns None."""
        user_id = 1
        results = {"github": {"valid": True, "error": None}}

        # Set cache with old timestamp
        _validation_cache[user_id] = {
            "results": results,
            "timestamp": datetime.now(dt_timezone.utc) - timedelta(seconds=VALIDATION_CACHE_TTL_SECONDS + 10)
        }

        cached = get_cached_validation(user_id)
        self.assertIsNone(cached)

    def test_invalidate_validation_cache(self):
        """Test invalidating cache for a user."""
        user_id = 1
        results = {"github": {"valid": True, "error": None}}

        set_validation_cache(user_id, results)
        self.assertIsNotNone(get_cached_validation(user_id))

        invalidate_validation_cache(user_id)
        self.assertIsNone(get_cached_validation(user_id))

    def test_invalidate_validation_cache_nonexistent_user(self):
        """Test invalidating cache for non-existent user does not raise."""
        invalidate_validation_cache(999)

    def test_cache_expired_entry_removed(self):
        """Test that expired cache entry is removed on access."""
        user_id = 1
        results = {"github": {"valid": True, "error": None}}

        # Set cache with old timestamp directly
        with _cache_lock:
            _validation_cache[user_id] = {
                "results": results,
                "timestamp": datetime.now(dt_timezone.utc) - timedelta(seconds=VALIDATION_CACHE_TTL_SECONDS + 10)
            }

        # Access should return None and remove the entry
        cached = get_cached_validation(user_id)
        self.assertIsNone(cached)

        # Entry should be removed
        with _cache_lock:
            self.assertNotIn(user_id, _validation_cache)

    def test_cache_eviction_when_full(self):
        """Test that oldest entries are evicted when cache is full."""
        # Fill the cache to MAX_CACHE_SIZE
        base_time = datetime.now(dt_timezone.utc) - timedelta(hours=1)

        with _cache_lock:
            for i in range(MAX_CACHE_SIZE):
                _validation_cache[i] = {
                    "results": {"github": {"valid": True, "error": None}},
                    "timestamp": base_time + timedelta(seconds=i)
                }

        # Adding a new entry should trigger eviction
        set_validation_cache(MAX_CACHE_SIZE + 1, {"github": {"valid": True, "error": None}})

        # Cache should now be smaller than MAX_CACHE_SIZE + 1
        with _cache_lock:
            self.assertLess(len(_validation_cache), MAX_CACHE_SIZE + 1)
            # New entry should exist
            self.assertIn(MAX_CACHE_SIZE + 1, _validation_cache)


class TestNeedsRefresh(unittest.TestCase):
    """Test suite for needs_refresh function."""

    def test_needs_refresh_no_expiry(self):
        """Test that None expiry returns False."""
        self.assertFalse(needs_refresh(None))

    def test_needs_refresh_expired(self):
        """Test that expired token returns True."""
        expired = datetime.now(dt_timezone.utc) - timedelta(minutes=10)
        self.assertTrue(needs_refresh(expired))

    def test_needs_refresh_within_buffer(self):
        """Test that token expiring within buffer returns True."""
        expiring_soon = datetime.now(dt_timezone.utc) + timedelta(minutes=30)
        self.assertTrue(needs_refresh(expiring_soon, skew_minutes=60))

    def test_needs_refresh_not_needed(self):
        """Test that token with plenty of time returns False."""
        far_future = datetime.now(dt_timezone.utc) + timedelta(hours=12)
        self.assertFalse(needs_refresh(far_future))


class TestLinearTokenRefresh(unittest.TestCase):
    """Test suite for Linear token refresh functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=Session)
        self.validator = IntegrationValidator(self.mock_db)

    def _run_async(self, coro):
        """Helper to run async functions in tests."""
        return asyncio.run(coro)

    @patch('app.services.integration_validator.decrypt_token')
    def test_get_valid_linear_token_no_refresh_needed(self, mock_decrypt):
        """Test getting token when no refresh is needed."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(hours=12)
        mock_integration.refresh_token = "encrypted_refresh"
        mock_decrypt.return_value = "valid_token"

        token = self._run_async(self.validator._get_valid_linear_token(mock_integration))

        self.assertEqual(token, "valid_token")
        mock_decrypt.assert_called_once_with("encrypted_token")

    @patch('app.services.integration_validator.encrypt_token')
    @patch('app.services.integration_validator.decrypt_token')
    def test_get_valid_linear_token_refresh_success(self, mock_decrypt, mock_encrypt):
        """Test successful token refresh."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.user_id = 1
        mock_integration.access_token = "old_encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) - timedelta(minutes=10)
        mock_integration.refresh_token = "encrypted_refresh"
        mock_decrypt.return_value = "refresh_token_value"
        mock_encrypt.return_value = "new_encrypted_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 86400
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            token = self._run_async(self.validator._get_valid_linear_token(mock_integration))

        self.assertEqual(token, "new_access_token")
        self.mock_db.commit.assert_called_once()

    @patch('app.services.integration_validator.decrypt_token')
    def test_get_valid_linear_token_no_refresh_token(self, mock_decrypt):
        """Test getting token when no refresh token is available."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) - timedelta(minutes=10)
        mock_integration.refresh_token = None
        mock_decrypt.return_value = "valid_token"

        token = self._run_async(self.validator._get_valid_linear_token(mock_integration))

        self.assertEqual(token, "valid_token")

    @patch('app.services.integration_validator.decrypt_token')
    def test_get_valid_linear_token_refresh_fails_token_not_expired(self, mock_decrypt):
        """Test fallback to existing token when refresh fails but token not yet expired."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.user_id = 1
        mock_integration.access_token = "old_encrypted_token"
        # Token expires in 30 minutes (within refresh window but not yet expired)
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(minutes=30)
        mock_integration.refresh_token = "encrypted_refresh"
        mock_decrypt.side_effect = ["refresh_token_value", "old_token"]

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            token = self._run_async(self.validator._get_valid_linear_token(mock_integration))

        self.assertEqual(token, "old_token")

    @patch('app.services.integration_validator.decrypt_token')
    def test_get_valid_linear_token_refresh_fails_token_expired(self, mock_decrypt):
        """Test that refresh failure raises exception when token is already expired."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.user_id = 1
        mock_integration.access_token = "old_encrypted_token"
        # Token already expired 10 minutes ago
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) - timedelta(minutes=10)
        mock_integration.refresh_token = "encrypted_refresh"
        mock_decrypt.return_value = "refresh_token_value"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with self.assertRaises(ValueError) as context:
                self._run_async(self.validator._get_valid_linear_token(mock_integration))

        self.assertIn("expired", str(context.exception))

    def test_get_valid_linear_token_no_access_token(self):
        """Test that missing access_token raises ValueError."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.access_token = None
        mock_integration.token_expires_at = None
        mock_integration.refresh_token = None

        with self.assertRaises(ValueError) as context:
            self._run_async(self.validator._get_valid_linear_token(mock_integration))

        self.assertIn("No access token available", str(context.exception))


class TestValidateAllIntegrations(unittest.TestCase):
    """Test suite for validate_all_integrations with caching."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=Session)
        self.validator = IntegrationValidator(self.mock_db)
        _validation_cache.clear()

    def tearDown(self):
        """Clear cache after each test."""
        _validation_cache.clear()

    def _run_async(self, coro):
        """Helper to run async functions in tests."""
        return asyncio.run(coro)

    def test_validate_all_uses_cache(self):
        """Test that validate_all_integrations uses cached results."""
        user_id = 1
        cached_results = {
            "github": {"valid": True, "error": None}
        }
        set_validation_cache(user_id, cached_results)

        result = self._run_async(self.validator.validate_all_integrations(user_id, use_cache=True))

        self.assertEqual(result, cached_results)

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_all_bypasses_cache(self, mock_decrypt):
        """Test that validate_all_integrations bypasses cache when use_cache=False."""
        user_id = 1
        cached_results = {"github": {"valid": True, "error": None}}
        set_validation_cache(user_id, cached_results)

        self.mock_db.query().filter().first.return_value = None

        result = self._run_async(self.validator.validate_all_integrations(user_id, use_cache=False))

        self.assertEqual(result, {})

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_all_caches_results(self, mock_decrypt):
        """Test that validate_all_integrations caches fresh results."""
        user_id = 1
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        mock_decrypt.return_value = "valid_token"

        def query_side_effect():
            mock_query = Mock()
            mock_filter = Mock()
            mock_filter.first.return_value = mock_integration
            mock_query.filter.return_value = mock_filter
            return mock_query

        self.mock_db.query.side_effect = query_side_effect

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": {"viewer": {"id": "123"}}}
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            self._run_async(self.validator.validate_all_integrations(user_id, use_cache=False))

        cached = get_cached_validation(user_id)
        self.assertIsNotNone(cached)


if __name__ == '__main__':
    unittest.main()
