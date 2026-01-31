"""
Integration tests for API key management endpoints.

Tests cover:
- POST /api/api-keys (create)
- GET /api/api-keys (list)
- DELETE /api/api-keys/{key_id} (revoke)

All endpoints require JWT authentication and use TestClient for
end-to-end testing of the request/response cycle.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.endpoints.api_keys import router, CreateApiKeyRequest
from app.auth.dependencies import get_current_active_user
from app.models import get_db, User


# Create test app with api_keys router
# Router already has prefix="/api-keys", so mount at "/api" to get "/api/api-keys"
test_app = FastAPI()
test_app.include_router(router, prefix="/api")


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = Mock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_user2():
    """Create a second mock user for ownership tests."""
    user = Mock(spec=User)
    user.id = 2
    user.email = "other@example.com"
    return user


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def client(mock_user, mock_db):
    """Create test client with JWT auth mocked."""
    test_app.dependency_overrides[get_current_active_user] = lambda: mock_user
    test_app.dependency_overrides[get_db] = lambda: mock_db

    with TestClient(test_app) as client:
        yield client

    # Clean up overrides
    test_app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(mock_db):
    """Create test client without JWT auth (should fail with 401)."""
    # Don't override get_current_active_user - let it require auth
    test_app.dependency_overrides[get_db] = lambda: mock_db

    with TestClient(test_app, raise_server_exceptions=False) as client:
        yield client

    test_app.dependency_overrides.clear()


class TestCreateApiKeyEndpoint:
    """Tests for POST /api/api-keys endpoint."""

    def test_create_api_key_returns_201_with_full_key(self, client, mock_db):
        """Create endpoint returns 201 with full key shown once."""
        mock_api_key = Mock()
        mock_api_key.id = 42
        mock_api_key.name = "Test Key"
        mock_api_key.masked_key = "och_live_...abcd"
        mock_api_key.scope = "full_access"
        mock_api_key.created_at = datetime.now(timezone.utc)
        mock_api_key.expires_at = None

        with patch('app.api.endpoints.api_keys.APIKeyService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.create_key.return_value = (mock_api_key, "och_live_full_key_value_here")

            response = client.post(
                "/api/api-keys",
                json={"name": "Test Key"}
            )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 42
        assert data["name"] == "Test Key"
        assert data["key"] == "och_live_full_key_value_here"
        assert data["masked_key"] == "och_live_...abcd"
        assert data["scope"] == "full_access"

    def test_create_api_key_with_expiration(self, client, mock_db):
        """Create endpoint accepts expiration date in the future."""
        future_date = datetime.now(timezone.utc) + timedelta(days=90)

        mock_api_key = Mock()
        mock_api_key.id = 43
        mock_api_key.name = "Expiring Key"
        mock_api_key.masked_key = "och_live_...efgh"
        mock_api_key.scope = "full_access"
        mock_api_key.created_at = datetime.now(timezone.utc)
        mock_api_key.expires_at = future_date

        with patch('app.api.endpoints.api_keys.APIKeyService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.create_key.return_value = (mock_api_key, "och_live_another_key")

            response = client.post(
                "/api/api-keys",
                json={
                    "name": "Expiring Key",
                    "expires_at": future_date.isoformat()
                }
            )

        assert response.status_code == 201
        data = response.json()
        assert data["expires_at"] is not None

    def test_create_api_key_duplicate_name_returns_400(self, client, mock_db):
        """Create endpoint returns 400 for duplicate key name."""
        with patch('app.api.endpoints.api_keys.APIKeyService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.create_key.side_effect = ValueError("API key with name 'Duplicate' already exists")

            response = client.post(
                "/api/api-keys",
                json={"name": "Duplicate"}
            )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_api_key_empty_name_returns_422(self, client, mock_db):
        """Create endpoint returns 422 for empty name."""
        response = client.post(
            "/api/api-keys",
            json={"name": ""}
        )

        assert response.status_code == 422

    def test_create_api_key_whitespace_name_returns_422(self, client, mock_db):
        """Create endpoint returns 422 for whitespace-only name."""
        response = client.post(
            "/api/api-keys",
            json={"name": "   "}
        )

        assert response.status_code == 422

    def test_create_api_key_past_expiration_returns_422(self, client, mock_db):
        """Create endpoint returns 422 for expiration in the past."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)

        response = client.post(
            "/api/api-keys",
            json={
                "name": "Invalid Key",
                "expires_at": past_date.isoformat()
            }
        )

        assert response.status_code == 422

    def test_create_api_key_requires_auth(self, mock_db):
        """Create endpoint returns 401 without JWT token."""
        # Create a client without auth override - dependency will fail
        test_app.dependency_overrides[get_db] = lambda: mock_db
        # Don't override get_current_active_user

        with TestClient(test_app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/api-keys",
                json={"name": "Test Key"}
            )

        test_app.dependency_overrides.clear()

        # Should fail with 401 or 403 (no credentials)
        assert response.status_code in [401, 403]


class TestListApiKeysEndpoint:
    """Tests for GET /api/api-keys endpoint."""

    def test_list_api_keys_returns_200_with_masked_keys(self, client, mock_db, mock_user):
        """List endpoint returns 200 with masked keys."""
        mock_key1 = Mock()
        mock_key1.id = 1
        mock_key1.name = "Key One"
        mock_key1.masked_key = "och_live_...1111"
        mock_key1.scope = "full_access"
        mock_key1.is_active = True
        mock_key1.created_at = datetime.now(timezone.utc)
        mock_key1.last_used_at = None
        mock_key1.expires_at = None

        mock_key2 = Mock()
        mock_key2.id = 2
        mock_key2.name = "Key Two"
        mock_key2.masked_key = "och_live_...2222"
        mock_key2.scope = "full_access"
        mock_key2.is_active = True
        mock_key2.created_at = datetime.now(timezone.utc)
        mock_key2.last_used_at = datetime.now(timezone.utc)
        mock_key2.expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        with patch('app.api.endpoints.api_keys.APIKeyService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.list_user_keys.return_value = [mock_key1, mock_key2]

            response = client.get("/api/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
        assert len(data["keys"]) == 2

        # Verify masked keys are returned (not full keys)
        assert data["keys"][0]["masked_key"] == "och_live_...1111"
        assert data["keys"][1]["masked_key"] == "och_live_...2222"

        # Verify no "key" field with full key
        assert "key" not in data["keys"][0]
        assert "key" not in data["keys"][1]

    def test_list_api_keys_excludes_revoked(self, client, mock_db, mock_user):
        """List endpoint excludes revoked keys by default."""
        mock_active_key = Mock()
        mock_active_key.id = 1
        mock_active_key.name = "Active Key"
        mock_active_key.masked_key = "och_live_...aaaa"
        mock_active_key.scope = "full_access"
        mock_active_key.is_active = True
        mock_active_key.created_at = datetime.now(timezone.utc)
        mock_active_key.last_used_at = None
        mock_active_key.expires_at = None

        with patch('app.api.endpoints.api_keys.APIKeyService') as mock_service_class:
            mock_service = mock_service_class.return_value
            # Service is called with include_revoked=False
            mock_service.list_user_keys.return_value = [mock_active_key]

            response = client.get("/api/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert len(data["keys"]) == 1

        # Verify service was called with correct params
        mock_service.list_user_keys.assert_called_once_with(
            user_id=1, include_revoked=False
        )

    def test_list_api_keys_returns_empty_list(self, client, mock_db, mock_user):
        """List endpoint returns empty list when no keys exist."""
        with patch('app.api.endpoints.api_keys.APIKeyService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.list_user_keys.return_value = []

            response = client.get("/api/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert data["keys"] == []

    def test_list_api_keys_requires_auth(self, mock_db):
        """List endpoint returns 401 without JWT token."""
        test_app.dependency_overrides[get_db] = lambda: mock_db

        with TestClient(test_app, raise_server_exceptions=False) as client:
            response = client.get("/api/api-keys")

        test_app.dependency_overrides.clear()

        assert response.status_code in [401, 403]


class TestRevokeApiKeyEndpoint:
    """Tests for DELETE /api/api-keys/{key_id} endpoint."""

    def test_revoke_api_key_returns_204(self, client, mock_db, mock_user):
        """Revoke endpoint returns 204 on success."""
        with patch('app.api.endpoints.api_keys.APIKeyService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.revoke_key.return_value = True

            response = client.delete("/api/api-keys/42")

        assert response.status_code == 204
        mock_service.revoke_key.assert_called_once_with(key_id=42, user_id=1)

    def test_revoke_api_key_not_found_returns_404(self, client, mock_db, mock_user):
        """Revoke endpoint returns 404 for non-existent key."""
        with patch('app.api.endpoints.api_keys.APIKeyService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.revoke_key.return_value = False

            response = client.delete("/api/api-keys/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_revoke_api_key_wrong_user_returns_404(self, client, mock_db, mock_user):
        """Revoke endpoint returns 404 for another user's key."""
        # Service returns False when key belongs to different user
        with patch('app.api.endpoints.api_keys.APIKeyService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.revoke_key.return_value = False  # User mismatch causes False

            response = client.delete("/api/api-keys/123")

        assert response.status_code == 404
        # Should not reveal whether key exists but belongs to another user
        assert "not found" in response.json()["detail"].lower()

    def test_revoke_already_revoked_returns_404(self, client, mock_db, mock_user):
        """Revoke endpoint returns 404 for already revoked key."""
        with patch('app.api.endpoints.api_keys.APIKeyService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.revoke_key.return_value = False

            response = client.delete("/api/api-keys/50")

        assert response.status_code == 404
        assert "already revoked" in response.json()["detail"].lower()

    def test_revoke_api_key_requires_auth(self, mock_db):
        """Revoke endpoint returns 401 without JWT token."""
        test_app.dependency_overrides[get_db] = lambda: mock_db

        with TestClient(test_app, raise_server_exceptions=False) as client:
            response = client.delete("/api/api-keys/42")

        test_app.dependency_overrides.clear()

        assert response.status_code in [401, 403]


class TestCreateApiKeyRequestValidation:
    """Tests for CreateApiKeyRequest Pydantic model validation."""

    def test_valid_name_passes(self):
        """Valid name passes validation."""
        request = CreateApiKeyRequest(name="My API Key")
        assert request.name == "My API Key"

    def test_name_strips_whitespace(self):
        """Name validator strips leading/trailing whitespace."""
        request = CreateApiKeyRequest(name="  Trimmed Name  ")
        assert request.name == "Trimmed Name"

    def test_name_max_length_enforced(self):
        """Name exceeding 100 characters fails validation."""
        with pytest.raises(ValueError):
            CreateApiKeyRequest(name="a" * 101)

    def test_future_expires_at_passes(self):
        """Future expiration date passes validation."""
        future = datetime.now(timezone.utc) + timedelta(days=30)
        request = CreateApiKeyRequest(name="Key", expires_at=future)
        assert request.expires_at >= datetime.now(timezone.utc)

    def test_naive_datetime_gets_utc(self):
        """Naive datetime gets UTC timezone applied."""
        # Create a naive datetime that's definitely in the future
        future_naive = datetime.now() + timedelta(days=30)
        request = CreateApiKeyRequest(name="Key", expires_at=future_naive)
        assert request.expires_at.tzinfo is not None
