"""Exercise the Slack payload without sending messages to Slack."""

import asyncio
import json

import httpx
import pytest

from app.services.slack_dm_sender import SlackDMSender


@pytest.mark.parametrize("message", [None, "A custom weekly check-in greeting."])
@pytest.mark.parametrize("user_id", [42, None])
def test_checkin_notice_survives_custom_messages_and_roster_only_recipients(
    monkeypatch, message, user_id
):
    requests = []

    def handle_request(request):
        requests.append(request)
        if request.url.path == "/api/conversations.open":
            return httpx.Response(200, json={"ok": True, "channel": {"id": "D123"}})
        assert request.url.path == "/api/chat.postMessage"
        return httpx.Response(200, json={"ok": True, "ts": "123.456"})

    async_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.services.slack_dm_sender.httpx.AsyncClient",
        lambda: async_client(transport=httpx.MockTransport(handle_request)),
    )

    assert asyncio.run(
        SlackDMSender().send_survey_dm(
            slack_token="test-slack-token",
            slack_user_id="U123",
            user_id=user_id,
            organization_id=7,
            message=message,
            user_email="responder@example.com",
        )
    )

    assert len(requests) == 2
    assert json.loads(requests[0].content) == {"users": "U123"}
    payload = json.loads(requests[1].content)
    assert payload["channel"] == "D123"

    sections = [block["text"]["text"] for block in payload["blocks"] if block["type"] == "section"]
    greeting, notice = sections
    if message:
        assert greeting == message
    else:
        assert "recovery after busy shifts" in greeting

    for text in (notice, payload["text"]):
        assert "spot overload early and share the load" in text
        assert "People with access to your team's analyses" in text
        assert "check-in responses linked to your name or email" in text
        assert "Where the Rootly MCP health-risk integration is enabled" in text
        assert "existing individual scores" in text
        assert "Claude or Codex" in text
        assert (
            "https://github.com/Rootly-AI-Labs/On-Call-Health/blob/main/"
            "RESPONDER_WORKLOAD_NOTICE.md"
        ) in text
    assert greeting in payload["text"]

    # The notice is visible before the original, still-functional check-in button.
    actions = payload["blocks"][-1]
    assert actions["type"] == "actions"
    button = actions["elements"][0]
    assert button["action_id"] == "open_burnout_survey"
    assert button["value"] == f"{user_id}|7|responder@example.com"

