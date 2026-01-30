from datetime import datetime

from app.mcp.serializers import (
    serialize_rootly_integration,
    serialize_github_integration,
    serialize_slack_integration,
    serialize_jira_integration,
    serialize_linear_integration,
)
from app.models import RootlyIntegration, GitHubIntegration, SlackIntegration, JiraIntegration, LinearIntegration


def test_serialize_rootly_integration_hides_token():
    integration = RootlyIntegration(
        id=1,
        user_id=10,
        name="Rootly",
        organization_name="Rootly Inc",
        api_token="secret",
        platform="rootly",
        is_default=True,
        is_active=True,
        total_users=5,
        created_at=datetime.utcnow(),
    )
    data = serialize_rootly_integration(integration)
    assert "api_token" not in data
    assert data["name"] == "Rootly"


def test_serialize_github_integration_hides_token():
    integration = GitHubIntegration(
        id=2,
        user_id=10,
        github_username="octocat",
        github_token="secret",
        organizations=["rootly"],
        token_source="oauth",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    data = serialize_github_integration(integration)
    assert "github_token" not in data
    assert data["username"] == "octocat"


def test_serialize_slack_integration_hides_token():
    integration = SlackIntegration(
        id=3,
        user_id=10,
        slack_token="secret",
        slack_user_id="U123",
        workspace_id="T123",
        token_source="oauth",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    data = serialize_slack_integration(integration)
    assert "slack_token" not in data
    assert data["workspace_id"] == "T123"


def test_serialize_jira_integration_hides_token():
    integration = JiraIntegration(
        id=4,
        user_id=10,
        access_token="secret",
        refresh_token="refresh",
        jira_cloud_id="cloud",
        jira_site_url="example.atlassian.net",
        jira_display_name="Jane",
        token_source="oauth",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    data = serialize_jira_integration(integration)
    assert "access_token" not in data
    assert "refresh_token" not in data
    assert data["site_url"] == "example.atlassian.net"


def test_serialize_linear_integration_hides_token():
    integration = LinearIntegration(
        id=5,
        user_id=10,
        access_token="secret",
        refresh_token="refresh",
        workspace_id="org",
        workspace_name="Rootly",
        workspace_url_key="rootly",
        token_source="oauth",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    data = serialize_linear_integration(integration)
    assert "access_token" not in data
    assert "refresh_token" not in data
    assert data["workspace_id"] == "org"
