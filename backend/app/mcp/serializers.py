"""Serialization helpers for MCP tool outputs."""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.models import RootlyIntegration, GitHubIntegration, SlackIntegration, JiraIntegration, LinearIntegration


def serialize_datetime(value) -> Optional[str]:
    if value is None:
        return None
    try:
        return value.isoformat()
    except AttributeError:
        return str(value)


def serialize_rootly_integration(integration: RootlyIntegration) -> Dict[str, Any]:
    return {
        "id": integration.id,
        "name": integration.name,
        "platform": integration.platform,
        "organization_name": integration.organization_name,
        "is_default": integration.is_default,
        "is_active": integration.is_active,
        "total_users": integration.total_users,
        "last_used_at": serialize_datetime(integration.last_used_at),
        "created_at": serialize_datetime(integration.created_at),
    }


def serialize_github_integration(integration: GitHubIntegration) -> Dict[str, Any]:
    return {
        "id": integration.id,
        "username": integration.github_username,
        "organizations": integration.organization_names,
        "has_token": integration.has_token,
        "token_source": integration.token_source,
        "created_at": serialize_datetime(integration.created_at),
        "updated_at": serialize_datetime(integration.updated_at),
    }


def serialize_slack_integration(integration: SlackIntegration) -> Dict[str, Any]:
    return {
        "id": integration.id,
        "workspace_id": integration.workspace_id,
        "slack_user_id": integration.slack_user_id,
        "has_token": integration.has_token,
        "token_source": integration.token_source,
        "created_at": serialize_datetime(integration.created_at),
        "updated_at": serialize_datetime(integration.updated_at),
    }


def serialize_jira_integration(integration: JiraIntegration) -> Dict[str, Any]:
    return {
        "id": integration.id,
        "cloud_id": integration.jira_cloud_id,
        "site_url": integration.jira_site_url,
        "display_name": integration.jira_display_name,
        "has_token": integration.has_token,
        "token_source": integration.token_source,
        "created_at": serialize_datetime(integration.created_at),
        "updated_at": serialize_datetime(integration.updated_at),
    }


def serialize_linear_integration(integration: LinearIntegration) -> Dict[str, Any]:
    return {
        "id": integration.id,
        "workspace_id": integration.workspace_id,
        "workspace_name": integration.workspace_name,
        "workspace_url_key": integration.workspace_url_key,
        "has_token": integration.has_token,
        "token_source": integration.token_source,
        "created_at": serialize_datetime(integration.created_at),
        "updated_at": serialize_datetime(integration.updated_at),
    }
