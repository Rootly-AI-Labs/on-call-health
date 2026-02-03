"""MCP server for On-Call Health."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import Session

from app.mcp.auth import extract_api_key_header, require_user_api_key
from app.mcp.client import NotFoundError, OnCallHealthClient
from app.mcp.normalizers import (
    normalize_analysis_response,
    normalize_analysis_start_response,
)
from app.mcp.serializers import (
    serialize_github_integration,
    serialize_jira_integration,
    serialize_linear_integration,
    serialize_rootly_integration,
    serialize_slack_integration,
)
from app.models import (
    SessionLocal,
    RootlyIntegration,
    GitHubIntegration,
    SlackIntegration,
    JiraIntegration,
    LinearIntegration,
)

logger = logging.getLogger(__name__)

mcp_server = FastMCP("On-Call Health")


def _resolve_asgi_app(server: Any) -> Any:
    if hasattr(server, "app"):
        return server.app
    if hasattr(server, "asgi_app"):
        return server.asgi_app()
    raise RuntimeError("FastMCP does not expose an ASGI app")


mcp_app = _resolve_asgi_app(mcp_server)


def _get_db() -> Session:
    return SessionLocal()


def _handle_task_exception(task: asyncio.Task) -> None:
    """Log exceptions from background tasks to prevent silent failures."""
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error("Background analysis task failed: %s", exc, exc_info=exc)


def _get_integration_for_user(
    db: Session,
    user_id: int,
    integration_id: Optional[int],
) -> RootlyIntegration:
    if integration_id:
        integration = db.query(RootlyIntegration).filter(
            RootlyIntegration.id == integration_id,
            RootlyIntegration.user_id == user_id,
            RootlyIntegration.is_active == True,  # noqa: E712
        ).first()
        if not integration:
            raise LookupError("Integration not found")
        return integration

    integration = db.query(RootlyIntegration).filter(
        RootlyIntegration.user_id == user_id,
        RootlyIntegration.is_active == True,  # noqa: E712
        RootlyIntegration.is_default == True,  # noqa: E712
    ).first()
    if integration:
        return integration

    integration = db.query(RootlyIntegration).filter(
        RootlyIntegration.user_id == user_id,
        RootlyIntegration.is_active == True,  # noqa: E712
    ).first()
    if integration:
        return integration

    raise ValueError("No active Rootly integration found")


@mcp_server.tool()
async def analysis_start(
    ctx: Any,
    days_back: int = 30,
    include_weekends: bool = True,
    integration_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Start a new burnout analysis."""
    api_key = extract_api_key_header(ctx)
    if not api_key:
        raise PermissionError("Missing API key. Provide X-API-Key header.")

    async with OnCallHealthClient(api_key=api_key) as client:
        # Build request body for /analyses/run
        request_body: Dict[str, Any] = {
            "time_range": days_back,
            "include_weekends": include_weekends,
        }
        # Only include integration_id if explicitly provided
        if integration_id is not None:
            request_body["integration_id"] = integration_id

        try:
            response = await client.post("/analyses/run", json=request_body)
            data = response.json()
            # Get integration name from response or config
            integration_name = (
                data.get("integration_name")
                or data.get("config", {}).get("integration_name", "integration")
            )
            return normalize_analysis_start_response(data, integration_name, days_back)
        except NotFoundError:
            raise LookupError("Integration not found")


@mcp_server.tool()
async def analysis_status(ctx: Any, analysis_id: int) -> Dict[str, Any]:
    """Get the status of an analysis."""
    api_key = extract_api_key_header(ctx)
    if not api_key:
        raise PermissionError("Missing API key. Provide X-API-Key header.")

    async with OnCallHealthClient(api_key=api_key) as client:
        try:
            response = await client.get(f"/analyses/{analysis_id}")
            data = response.json()
            return normalize_analysis_response(data)
        except NotFoundError:
            raise LookupError("Analysis not found")


@mcp_server.tool()
async def analysis_results(ctx: Any, analysis_id: int) -> Dict[str, Any]:
    """Get full results for a completed analysis."""
    api_key = extract_api_key_header(ctx)
    if not api_key:
        raise PermissionError("Missing API key. Provide X-API-Key header.")

    async with OnCallHealthClient(api_key=api_key) as client:
        try:
            response = await client.get(f"/analyses/{analysis_id}")
            data = response.json()
            if data.get("status") != "completed":
                raise ValueError(f"Analysis not completed yet (status={data['status']})")
            # Return full results from analysis_data
            return data.get("analysis_data") or {}
        except NotFoundError:
            raise LookupError("Analysis not found")


@mcp_server.tool()
async def analysis_current(ctx: Any) -> Dict[str, Any]:
    """Get the most recent analysis for the current user."""
    api_key = extract_api_key_header(ctx)
    if not api_key:
        raise PermissionError("Missing API key. Provide X-API-Key header.")

    async with OnCallHealthClient(api_key=api_key) as client:
        # Get list with limit=1, sorted by created_at desc (server default)
        response = await client.get("/analyses", params={"limit": 1})
        data = response.json()
        analyses = data.get("analyses", [])
        if not analyses:
            raise LookupError("No analyses found")
        return normalize_analysis_response(analyses[0])


@mcp_server.tool()
async def integrations_list(ctx: Any) -> Dict[str, Any]:
    """List connected integrations for the current user."""
    db = _get_db()
    try:
        user = require_user_api_key(ctx, db)
        rootly = (
            db.query(RootlyIntegration)
            .filter(RootlyIntegration.user_id == user.id)
            .all()
        )
        github = (
            db.query(GitHubIntegration)
            .filter(GitHubIntegration.user_id == user.id)
            .all()
        )
        slack = (
            db.query(SlackIntegration)
            .filter(SlackIntegration.user_id == user.id)
            .all()
        )
        jira = (
            db.query(JiraIntegration)
            .filter(JiraIntegration.user_id == user.id)
            .all()
        )
        linear = (
            db.query(LinearIntegration)
            .filter(LinearIntegration.user_id == user.id)
            .all()
        )

        return {
            "rootly": [serialize_rootly_integration(item) for item in rootly],
            "github": [serialize_github_integration(item) for item in github],
            "slack": [serialize_slack_integration(item) for item in slack],
            "jira": [serialize_jira_integration(item) for item in jira],
            "linear": [serialize_linear_integration(item) for item in linear],
        }
    finally:
        db.close()


@mcp_server.resource("oncallhealth://methodology")
def methodology_resource() -> str:
    """Provide a short methodology description."""
    return (
        "On-Call Health measures overwork risk using a two-dimensional model inspired by the "
        "Copenhagen Burnout Inventory. It combines objective workload signals (incidents, "
        "communications, commits) with self-reported data to surface risk patterns without "
        "providing medical diagnosis."
    )


@mcp_server.prompt()
def weekly_brief(team_name: str) -> str:
    """Prompt template for a weekly on-call health brief."""
    return (
        f"Create a weekly on-call health brief for the team named '{team_name}'. "
        "Summarize overall risk trends, identify any high-risk responders, "
        "and suggest two concrete follow-up actions for managers."
    )
