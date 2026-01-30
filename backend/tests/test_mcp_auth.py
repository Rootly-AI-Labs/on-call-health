from types import SimpleNamespace

from app.mcp.auth import extract_bearer_token, _parse_bearer_token


def test_parse_bearer_token():
    assert _parse_bearer_token("Bearer test-token") == "test-token"
    assert _parse_bearer_token("bearer test-token") == "test-token"
    assert _parse_bearer_token("test-token") is None
    assert _parse_bearer_token("") is None


def test_extract_bearer_token_from_request_headers():
    ctx = SimpleNamespace(request_headers={"Authorization": "Bearer header-token"})
    assert extract_bearer_token(ctx) == "header-token"


def test_extract_bearer_token_from_headers():
    ctx = SimpleNamespace(headers={"authorization": "Bearer headers-token"})
    assert extract_bearer_token(ctx) == "headers-token"


def test_extract_bearer_token_from_request_object():
    class DummyRequest:
        headers = {"Authorization": "Bearer request-token"}

    ctx = SimpleNamespace(request=DummyRequest())
    assert extract_bearer_token(ctx) == "request-token"


def test_extract_bearer_token_missing():
    ctx = SimpleNamespace()
    assert extract_bearer_token(ctx) is None
