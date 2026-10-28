import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.token_encryption import decrypt_token
from app.models import OAuthProvider
from app.services.account_linking import AccountLinkingService

ACCESS_TOKEN = "ya29.test-access-token"
REFRESH_TOKEN = "1//test-refresh-token"


def _service_with_existing_link(existing_oauth):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing_oauth
    return AccountLinkingService(db), db


def test_new_oauth_link_stores_encrypted_tokens():
    service, db = _service_with_existing_link(None)
    user = SimpleNamespace(id=1, name="Test User", oauth_providers=[])

    service._link_provider_to_user(user, "google", "google-123", ACCESS_TOKEN, REFRESH_TOKEN, {})

    oauth_provider = db.add.call_args.args[0]
    assert oauth_provider.access_token != ACCESS_TOKEN
    assert oauth_provider.refresh_token != REFRESH_TOKEN
    assert decrypt_token(oauth_provider.access_token) == ACCESS_TOKEN
    assert decrypt_token(oauth_provider.refresh_token) == REFRESH_TOKEN


def test_existing_oauth_link_update_stores_encrypted_tokens():
    existing_oauth = SimpleNamespace(user_id=1, access_token="old", refresh_token="old", updated_at=None)
    service, _ = _service_with_existing_link(existing_oauth)
    user = SimpleNamespace(id=1, name="Test User", oauth_providers=[existing_oauth])

    service._link_provider_to_user(user, "google", "google-123", ACCESS_TOKEN, REFRESH_TOKEN, {})

    assert decrypt_token(existing_oauth.access_token) == ACCESS_TOKEN
    assert decrypt_token(existing_oauth.refresh_token) == REFRESH_TOKEN


def test_missing_refresh_token_stays_none():
    service, db = _service_with_existing_link(None)
    user = SimpleNamespace(id=1, name="Test User", oauth_providers=[])

    service._link_provider_to_user(user, "github", "github-123", ACCESS_TOKEN, None, {})

    assert db.add.call_args.args[0].refresh_token is None


def test_relink_from_another_user_stores_encrypted_tokens():
    existing_oauth = SimpleNamespace(user_id=2, access_token="old", refresh_token="old", updated_at=None)
    service, _ = _service_with_existing_link(existing_oauth)
    user = SimpleNamespace(id=1, name="Test User", oauth_providers=[])

    service._link_provider_to_user(user, "google", "google-123", ACCESS_TOKEN, REFRESH_TOKEN, {})

    assert existing_oauth.user_id == 1
    assert decrypt_token(existing_oauth.access_token) == ACCESS_TOKEN
    assert decrypt_token(existing_oauth.refresh_token) == REFRESH_TOKEN


def _added_oauth_providers(db):
    return [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], OAuthProvider)]


def _assert_all_encrypted(oauth_providers):
    assert oauth_providers
    for oauth_provider in oauth_providers:
        assert decrypt_token(oauth_provider.access_token) == ACCESS_TOKEN
        assert decrypt_token(oauth_provider.refresh_token) == REFRESH_TOKEN


def test_new_user_signup_stores_encrypted_tokens():
    db = MagicMock()
    service = AccountLinkingService(db)

    with patch.object(AccountLinkingService, "_assign_user_to_organization"):
        service._create_new_user("user@example.com", "Test User", "google", "google-123", ACCESS_TOKEN, REFRESH_TOKEN)

    _assert_all_encrypted(_added_oauth_providers(db))


def test_new_user_signup_after_organization_failure_stores_encrypted_tokens():
    db = MagicMock()
    service = AccountLinkingService(db)

    with patch.object(AccountLinkingService, "_assign_user_to_organization", side_effect=RuntimeError("org lookup failed")):
        service._create_new_user("user@example.com", "Test User", "google", "google-123", ACCESS_TOKEN, REFRESH_TOKEN)

    oauth_providers = _added_oauth_providers(db)
    assert len(oauth_providers) == 2
    _assert_all_encrypted(oauth_providers)
