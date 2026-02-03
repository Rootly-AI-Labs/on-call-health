"""
Unit tests for API key authentication dependency.

Tests cover:
- Valid API key authentication
- Expired key rejection with date
- Revoked key rejection
- Invalid key format rejection
- JWT rejection with helpful error
- Missing key handling
- Background task scheduling for last_used_at
"""
import pytest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import HTTPException

from app.auth.api_key_auth import (
    get_current_user_from_api_key,
    api_key_header,
    _update_last_used_background,
)


class TestApiKeyHeader:
    """Tests for API key header scheme."""

    def test_api_key_header_name(self):
        """API key header should use X-API-Key."""
        assert api_key_header.model.name == "X-API-Key"

    def test_api_key_header_auto_error_false(self):
        """API key header should not auto-error for custom messages."""
        # auto_error is an attribute of the APIKeyHeader instance, not the model
        assert api_key_header.auto_error is False


class TestMissingApiKey:
    """Tests for missing API key scenarios."""

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_401(self):
        """Missing API key should return 401 with helpful message."""
        request = Mock()
        request.headers = {}
        request.state = SimpleNamespace()
        background_tasks = Mock()
        db = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_api_key(
                request=request,
                background_tasks=background_tasks,
                api_key=None,
                db=db
            )

        assert exc_info.value.status_code == 401
        assert "Missing API key" in exc_info.value.detail
        assert "X-API-Key" in exc_info.value.detail


class TestJwtRejection:
    """Tests for JWT token rejection."""

    @pytest.mark.asyncio
    async def test_jwt_token_rejected_with_400(self):
        """JWT token in Authorization header should return 400."""
        request = Mock()
        request.headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
        request.state = SimpleNamespace()
        background_tasks = Mock()
        db = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_api_key(
                request=request,
                background_tasks=background_tasks,
                api_key="och_live_test123",
                db=db
            )

        assert exc_info.value.status_code == 400
        assert "API key authentication" in exc_info.value.detail
        assert "Bearer token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_bearer_with_api_key_not_rejected(self):
        """Bearer header starting with och_live_ should not be rejected as JWT."""
        request = Mock()
        request.headers = {"Authorization": "Bearer och_live_not_real_but_prefix_ok"}
        request.state = SimpleNamespace()
        background_tasks = Mock()

        # Mock database - key not found
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        db = Mock()
        db.query.return_value = mock_query

        with patch('app.auth.api_key_auth.compute_sha256_hash', return_value="test_sha256"):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_from_api_key(
                    request=request,
                    background_tasks=background_tasks,
                    api_key="och_live_test1234567890abcdef1234567890abcdef",
                    db=db
                )

        # Should get to key validation, not JWT rejection
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail


class TestInvalidKeyFormat:
    """Tests for invalid key format."""

    @pytest.mark.asyncio
    async def test_wrong_prefix_rejected(self):
        """Key without och_live_ prefix should be rejected."""
        request = Mock()
        request.headers = {}
        request.state = SimpleNamespace()
        background_tasks = Mock()
        db = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_api_key(
                request=request,
                background_tasks=background_tasks,
                api_key="sk_live_invalid_prefix",
                db=db
            )

        assert exc_info.value.status_code == 401
        assert "och_live_" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_empty_prefix_rejected(self):
        """Key with empty prefix should be rejected."""
        request = Mock()
        request.headers = {}
        request.state = SimpleNamespace()
        background_tasks = Mock()
        db = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_api_key(
                request=request,
                background_tasks=background_tasks,
                api_key="some_random_key_no_prefix",
                db=db
            )

        assert exc_info.value.status_code == 401
        assert "och_live_" in exc_info.value.detail


class TestRevokedKey:
    """Tests for revoked key handling."""

    @pytest.mark.asyncio
    async def test_revoked_key_rejected(self):
        """Revoked key should return 401 with specific message."""
        request = Mock()
        request.headers = {}
        request.state = SimpleNamespace()
        background_tasks = Mock()

        # Mock API key model with revoked_at set
        mock_api_key = Mock()
        mock_api_key.id = 1
        mock_api_key.revoked_at = datetime.now(timezone.utc)
        mock_api_key.expires_at = None
        mock_api_key.key_hash_argon2 = "test_hash"

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_api_key
        db = Mock()
        db.query.return_value = mock_query

        with patch('app.auth.api_key_auth.compute_sha256_hash', return_value="test_sha256"):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_from_api_key(
                    request=request,
                    background_tasks=background_tasks,
                    api_key="och_live_test1234567890abcdef1234567890abcdef",
                    db=db
                )

        assert exc_info.value.status_code == 401
        assert "revoked" in exc_info.value.detail.lower()


class TestExpiredKey:
    """Tests for expired key handling."""

    @pytest.mark.asyncio
    async def test_expired_key_rejected_with_date(self):
        """Expired key should return 401 with expiration date."""
        request = Mock()
        request.headers = {}
        request.state = SimpleNamespace()
        background_tasks = Mock()

        # Mock API key model with expired date
        expiry_date = datetime(2026, 1, 15, tzinfo=timezone.utc)
        mock_api_key = Mock()
        mock_api_key.id = 1
        mock_api_key.revoked_at = None
        mock_api_key.expires_at = expiry_date
        mock_api_key.key_hash_argon2 = "test_hash"

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_api_key
        db = Mock()
        db.query.return_value = mock_query

        with patch('app.auth.api_key_auth.compute_sha256_hash', return_value="test_sha256"):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_from_api_key(
                    request=request,
                    background_tasks=background_tasks,
                    api_key="och_live_test1234567890abcdef1234567890abcdef",
                    db=db
                )

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
        assert "2026-01-15" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_not_yet_expired_key_passes_expiry_check(self):
        """Key with future expiry date should pass expiration check."""
        request = Mock()
        request.headers = {}
        request.state = SimpleNamespace()
        background_tasks = Mock()

        # Mock API key model with future expiry date
        future_expiry = datetime.now(timezone.utc) + timedelta(days=30)
        mock_api_key = Mock()
        mock_api_key.id = 42
        mock_api_key.revoked_at = None
        mock_api_key.expires_at = future_expiry
        mock_api_key.key_hash_argon2 = "test_hash"
        mock_api_key.user_id = 1
        mock_api_key.name = "Test Key"

        # Mock user
        mock_user = Mock()
        mock_user.id = 1

        # Mock database - need to handle multiple query() calls
        def mock_query_side_effect(model):
            mock_query = Mock()
            if model.__name__ == 'APIKey':
                mock_query.filter.return_value.first.return_value = mock_api_key
            elif model.__name__ == 'User':
                mock_query.filter.return_value.first.return_value = mock_user
            return mock_query

        db = Mock()
        db.query.side_effect = mock_query_side_effect

        with patch('app.auth.api_key_auth.compute_sha256_hash', return_value="test_sha256"):
            with patch('app.auth.api_key_auth.asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = True  # Argon2 verification passes

                user = await get_current_user_from_api_key(
                    request=request,
                    background_tasks=background_tasks,
                    api_key="och_live_test1234567890abcdef1234567890abcdef",
                    db=db
                )

        assert user == mock_user


class TestKeyNotFound:
    """Tests for key not found in database."""

    @pytest.mark.asyncio
    async def test_unknown_key_rejected(self):
        """Unknown key should return 401 with generic message."""
        request = Mock()
        request.headers = {}
        request.state = SimpleNamespace()
        background_tasks = Mock()

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        db = Mock()
        db.query.return_value = mock_query

        with patch('app.auth.api_key_auth.compute_sha256_hash', return_value="test_sha256"):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_from_api_key(
                    request=request,
                    background_tasks=background_tasks,
                    api_key="och_live_test1234567890abcdef1234567890abcdef",
                    db=db
                )

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail


class TestArgon2Verification:
    """Tests for Argon2 verification phase."""

    @pytest.mark.asyncio
    async def test_argon2_verification_failure_rejected(self):
        """Failed Argon2 verification should return 401."""
        request = Mock()
        request.headers = {}
        request.state = SimpleNamespace()
        background_tasks = Mock()

        # Mock API key found in SHA-256 lookup
        mock_api_key = Mock()
        mock_api_key.id = 1
        mock_api_key.revoked_at = None
        mock_api_key.expires_at = None
        mock_api_key.key_hash_argon2 = "test_hash"

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_api_key
        db = Mock()
        db.query.return_value = mock_query

        with patch('app.auth.api_key_auth.compute_sha256_hash', return_value="test_sha256"):
            with patch('app.auth.api_key_auth.asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = False  # Argon2 verification fails

                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user_from_api_key(
                        request=request,
                        background_tasks=background_tasks,
                        api_key="och_live_test1234567890abcdef1234567890abcdef",
                        db=db
                    )

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail


class TestUserNotFound:
    """Tests for orphaned API key (user deleted)."""

    @pytest.mark.asyncio
    async def test_orphaned_key_rejected(self):
        """API key with deleted user should return 401."""
        request = Mock()
        request.headers = {}
        request.state = SimpleNamespace()
        background_tasks = Mock()

        # Mock valid API key
        mock_api_key = Mock()
        mock_api_key.id = 1
        mock_api_key.revoked_at = None
        mock_api_key.expires_at = None
        mock_api_key.key_hash_argon2 = "test_hash"
        mock_api_key.user_id = 999

        # Mock database - APIKey found, User not found
        def mock_query_side_effect(model):
            mock_query = Mock()
            if model.__name__ == 'APIKey':
                mock_query.filter.return_value.first.return_value = mock_api_key
            elif model.__name__ == 'User':
                mock_query.filter.return_value.first.return_value = None  # User not found
            return mock_query

        db = Mock()
        db.query.side_effect = mock_query_side_effect

        with patch('app.auth.api_key_auth.compute_sha256_hash', return_value="test_sha256"):
            with patch('app.auth.api_key_auth.asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = True  # Argon2 passes

                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user_from_api_key(
                        request=request,
                        background_tasks=background_tasks,
                        api_key="och_live_test1234567890abcdef1234567890abcdef",
                        db=db
                    )

        assert exc_info.value.status_code == 401
        assert "owner not found" in exc_info.value.detail.lower()


class TestValidApiKey:
    """Tests for valid API key authentication."""

    @pytest.mark.asyncio
    async def test_valid_key_returns_user(self):
        """Valid API key should return authenticated user."""
        request = Mock()
        request.headers = {}
        request.state = SimpleNamespace()
        background_tasks = Mock()

        # Mock valid API key
        mock_api_key = Mock()
        mock_api_key.id = 42
        mock_api_key.revoked_at = None
        mock_api_key.expires_at = None
        mock_api_key.key_hash_argon2 = "test_hash"
        mock_api_key.user_id = 1
        mock_api_key.name = "Test Key"

        # Mock user
        mock_user = Mock()
        mock_user.id = 1

        # Mock database - need to handle multiple query() calls
        def mock_query_side_effect(model):
            mock_query = Mock()
            if model.__name__ == 'APIKey':
                mock_query.filter.return_value.first.return_value = mock_api_key
            elif model.__name__ == 'User':
                mock_query.filter.return_value.first.return_value = mock_user
            return mock_query

        db = Mock()
        db.query.side_effect = mock_query_side_effect

        with patch('app.auth.api_key_auth.compute_sha256_hash', return_value="test_sha256"):
            with patch('app.auth.api_key_auth.asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = True  # Argon2 verification passes

                user = await get_current_user_from_api_key(
                    request=request,
                    background_tasks=background_tasks,
                    api_key="och_live_test1234567890abcdef1234567890abcdef",
                    db=db
                )

        assert user == mock_user
        assert request.state.api_key_id == 42
        background_tasks.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_valid_key_stores_api_key_id_in_request_state(self):
        """Valid API key should store key ID in request.state for rate limiting."""
        request = Mock()
        request.headers = {}
        request.state = SimpleNamespace()
        background_tasks = Mock()

        mock_api_key = Mock()
        mock_api_key.id = 123
        mock_api_key.revoked_at = None
        mock_api_key.expires_at = None
        mock_api_key.key_hash_argon2 = "test_hash"
        mock_api_key.user_id = 1
        mock_api_key.name = "Rate Limited Key"

        mock_user = Mock()
        mock_user.id = 1

        def mock_query_side_effect(model):
            mock_query = Mock()
            if model.__name__ == 'APIKey':
                mock_query.filter.return_value.first.return_value = mock_api_key
            elif model.__name__ == 'User':
                mock_query.filter.return_value.first.return_value = mock_user
            return mock_query

        db = Mock()
        db.query.side_effect = mock_query_side_effect

        with patch('app.auth.api_key_auth.compute_sha256_hash', return_value="test_sha256"):
            with patch('app.auth.api_key_auth.asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = True

                await get_current_user_from_api_key(
                    request=request,
                    background_tasks=background_tasks,
                    api_key="och_live_test1234567890abcdef1234567890abcdef",
                    db=db
                )

        assert request.state.api_key_id == 123


class TestBackgroundTaskLastUsed:
    """Tests for background last_used_at update."""

    def test_update_last_used_background_creates_session(self):
        """Background task should create its own session."""
        with patch('app.auth.api_key_auth.SessionLocal') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value = mock_session

            _update_last_used_background(42)

            mock_session_factory.assert_called_once()
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    def test_update_last_used_background_handles_exception(self):
        """Background task should handle exceptions gracefully."""
        with patch('app.auth.api_key_auth.SessionLocal') as mock_session_factory:
            mock_session = Mock()
            mock_session.execute.side_effect = Exception("Database error")
            mock_session_factory.return_value = mock_session

            # Should not raise, just log and rollback
            _update_last_used_background(42)

            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_background_task_scheduled_on_success(self):
        """Background task should be scheduled on successful authentication."""
        request = Mock()
        request.headers = {}
        request.state = SimpleNamespace()
        background_tasks = Mock()

        mock_api_key = Mock()
        mock_api_key.id = 77
        mock_api_key.revoked_at = None
        mock_api_key.expires_at = None
        mock_api_key.key_hash_argon2 = "test_hash"
        mock_api_key.user_id = 1
        mock_api_key.name = "Test Key"

        mock_user = Mock()
        mock_user.id = 1

        def mock_query_side_effect(model):
            mock_query = Mock()
            if model.__name__ == 'APIKey':
                mock_query.filter.return_value.first.return_value = mock_api_key
            elif model.__name__ == 'User':
                mock_query.filter.return_value.first.return_value = mock_user
            return mock_query

        db = Mock()
        db.query.side_effect = mock_query_side_effect

        with patch('app.auth.api_key_auth.compute_sha256_hash', return_value="test_sha256"):
            with patch('app.auth.api_key_auth.asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = True

                await get_current_user_from_api_key(
                    request=request,
                    background_tasks=background_tasks,
                    api_key="och_live_test1234567890abcdef1234567890abcdef",
                    db=db
                )

        # Verify background task was scheduled with correct key ID
        background_tasks.add_task.assert_called_once()
        call_args = background_tasks.add_task.call_args
        assert call_args[0][0] == _update_last_used_background
        assert call_args[0][1] == 77
