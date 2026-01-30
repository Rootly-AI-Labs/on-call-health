"""MCP server for On-Call Health."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import Session

from app.api.endpoints.analysis import run_analysis_task
from app.mcp.auth import require_user
from app.mcp.serializers import (
    serialize_datetime,
    serialize_github_integration,
    serialize_jira_integration,
    serialize_linear_integration,
    serialize_rootly_integration,
    serialize_slack_integration,
)
from app.models import (
    SessionLocal,
    Analysis,
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
    db = _get_db()
    try:
        user = require_user(ctx, db)
        integration = _get_integration_for_user(db, user.id, integration_id)

        analysis = Analysis(
            user_id=user.id,
            rootly_integration_id=integration.id,
            status="pending",
            config={
                "days_back": days_back,
                "include_weekends": include_weekends,
                "integration_name": integration.name,
                "organization_name": integration.organization_name,
            },
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        task = asyncio.create_task(
            run_analysis_task(
                analysis.id,
                integration.id,
                days_back,
                user.id,
            )
        )
        task.add_done_callback(_handle_task_exception)

        return {
            "analysis_id": analysis.id,
            "status": "started",
            "message": (
                f"Analysis started using '{integration.name}'. "
                f"This usually takes 2-3 minutes for {days_back} days of data."
            ),
        }
    finally:
        db.close()


@mcp_server.tool()
async def analysis_status(ctx: Any, analysis_id: int) -> Dict[str, Any]:
    """Get the status of an analysis."""
    db = _get_db()
    try:
        user = require_user(ctx, db)
        analysis = db.query(Analysis).filter(
            Analysis.id == analysis_id,
            Analysis.user_id == user.id,
        ).first()
        if not analysis:
            raise LookupError("Analysis not found")

        response: Dict[str, Any] = {
            "id": analysis.id,
            "status": analysis.status,
            "created_at": serialize_datetime(analysis.created_at),
            "completed_at": serialize_datetime(analysis.completed_at),
            "config": analysis.config,
        }
        if analysis.error_message:
            response["error"] = analysis.error_message
        if analysis.results:
            team_analysis = analysis.results.get("team_analysis", [])
            response["results_summary"] = {
                "total_users": len(team_analysis),
                "high_risk_count": len(
                    [u for u in team_analysis if u.get("risk_level") == "high"]
                ),
                "team_average_score": analysis.results.get("team_summary", {}).get(
                    "average_score"
                ),
            }
        return response
    finally:
        db.close()


@mcp_server.tool()
async def analysis_results(ctx: Any, analysis_id: int) -> Dict[str, Any]:
    """Get full results for a completed analysis."""
    db = _get_db()
    try:
        user = require_user(ctx, db)
        analysis = db.query(Analysis).filter(
            Analysis.id == analysis_id,
            Analysis.user_id == user.id,
        ).first()
        if not analysis:
            raise LookupError("Analysis not found")
        if analysis.status != "completed":
            raise ValueError(f"Analysis not completed yet (status={analysis.status})")
        return analysis.results or {}
    finally:
        db.close()


@mcp_server.tool()
async def analysis_current(ctx: Any) -> Dict[str, Any]:
    """Get the most recent analysis for the current user."""
    db = _get_db()
    try:
        user = require_user(ctx, db)
        analysis = (
            db.query(Analysis)
            .filter(Analysis.user_id == user.id)
            .order_by(Analysis.created_at.desc())
            .first()
        )
        if not analysis:
            raise LookupError("No analyses found")
        return {
            "id": analysis.id,
            "status": analysis.status,
            "created_at": serialize_datetime(analysis.created_at),
            "completed_at": serialize_datetime(analysis.completed_at),
            "config": analysis.config,
            "error": analysis.error_message,
        }
    finally:
        db.close()


@mcp_server.tool()
async def integrations_list(ctx: Any) -> Dict[str, Any]:
    """List connected integrations for the current user."""
    db = _get_db()
    try:
        user = require_user(ctx, db)
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
