"""The Slack token exchange must send the redirect URI registered for this deployment."""
import asyncio
from unittest.mock import MagicMock, patch

from app.api.endpoints import slack


class RecordingClient:
    posts = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, data=None, **kwargs):
        RecordingClient.posts.append(data)
        response = MagicMock()
        response.json.return_value = {"ok": False, "error": "invalid_code"}
        return response


def test_token_exchange_uses_configured_backend_url(monkeypatch):
    RecordingClient.posts = []
    monkeypatch.setattr(slack.settings, "BACKEND_URL", "https://api.example.test")
    monkeypatch.setattr(slack.settings, "SLACK_CLIENT_ID", "client-id-1234")
    monkeypatch.setattr(slack.settings, "SLACK_CLIENT_SECRET", "client-secret")

    with patch("httpx.AsyncClient", RecordingClient):
        asyncio.run(slack.slack_oauth_callback(code="auth-code", error=None, state=None, db=MagicMock()))

    assert RecordingClient.posts[0]["redirect_uri"] == "https://api.example.test/integrations/slack/oauth/callback"
