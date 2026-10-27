import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.token_encryption import decrypt_token
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
