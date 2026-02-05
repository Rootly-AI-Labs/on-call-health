"""MCP server for On-Call Health."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from oncallhealth_mcp.auth import extract_api_key_header
from oncallhealth_mcp.client import NotFoundError, OnCallHealthClient
from oncallhealth_mcp.normalizers import (
    normalize_analysis_response,
    normalize_analysis_start_response,
    normalize_github_status,
    normalize_jira_status,
    normalize_linear_status,
    normalize_rootly_integration,
    normalize_slack_status,
)

logger = logging.getLogger(__name__)

mcp_server = FastMCP("On-Call Health")


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
    """Get full results for a completed analysis.

    WARNING: Returns complete data for 80+ members with ~40 fields each.
    May overwhelm AI context windows. Consider using analysis_summary() instead
    for high-level overview, or when you don't need all member details.
    """
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
async def analysis_summary(ctx: Any, analysis_id: int) -> Dict[str, Any]:
    """Get condensed summary of analysis results (optimized for AI agents).

    Returns high-level overview instead of full 80+ member details to prevent
    context overflow. Use analysis_results() when you need complete data.
    """
    api_key = extract_api_key_header(ctx)
    if not api_key:
        raise PermissionError("Missing API key. Provide X-API-Key header.")

    async with OnCallHealthClient(api_key=api_key) as client:
        try:
            response = await client.get(f"/analyses/{analysis_id}")
            data = response.json()
            if data.get("status") != "completed":
                raise ValueError(f"Analysis not completed yet (status={data['status']})")

            # Extract analysis_data
            analysis_data = data.get("analysis_data") or {}
            members = analysis_data.get("members", [])

            # Calculate summary statistics
            total_members = len(members)

            # Sort by OCH score (higher = more at risk)
            sorted_by_score = sorted(
                members,
                key=lambda m: m.get("och_score", 0),
                reverse=True
            )

            # Top 5 at risk (highest scores)
            top_at_risk = [
                {
                    "user_name": m.get("user_name", "Unknown"),
                    "och_score": m.get("och_score", 0),
                    "risk_level": m.get("risk_level", "unknown"),
                }
                for m in sorted_by_score[:5]
            ]

            # Top 5 healthiest (lowest scores)
            top_healthy = [
                {
                    "user_name": m.get("user_name", "Unknown"),
                    "och_score": m.get("och_score", 0),
                    "risk_level": m.get("risk_level", "unknown"),
                }
                for m in sorted_by_score[-5:][::-1]  # Reverse to show lowest first
            ]

            # Risk level distribution
            risk_distribution = {}
            for member in members:
                risk_level = member.get("risk_level", "unknown")
                risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1

            # Team averages
            if total_members > 0:
                avg_och_score = sum(m.get("och_score", 0) for m in members) / total_members
                avg_workload = sum(m.get("workload_score", 0) for m in members) / total_members
                avg_exhaustion = sum(m.get("exhaustion_score", 0) for m in members) / total_members
            else:
                avg_och_score = avg_workload = avg_exhaustion = 0

            return {
                "analysis_id": analysis_id,
                "total_members": total_members,
                "team_averages": {
                    "och_score": round(avg_och_score, 2),
                    "workload_score": round(avg_workload, 2),
                    "exhaustion_score": round(avg_exhaustion, 2),
                },
                "risk_distribution": risk_distribution,
                "top_at_risk": top_at_risk,
                "top_healthy": top_healthy,
                "note": "This is a condensed summary. Use analysis_results() for complete member data.",
            }
        except NotFoundError:
            raise LookupError("Analysis not found")


@mcp_server.tool()
async def analysis_current(ctx: Any) -> Dict[str, Any]:
    """Get the most recent analysis for the current user.

    Returns normalized metadata only (status, timestamps, configuration).
    Does not include full member data. Use analysis_summary() for team overview
    or analysis_results() for complete member details.
    """
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
    api_key = extract_api_key_header(ctx)
    if not api_key:
        raise PermissionError("Missing API key. Provide X-API-Key header.")

    async with OnCallHealthClient(api_key=api_key) as client:
        # Parallel fetch all integration types
        results = await asyncio.gather(
            client.get("/rootly/integrations"),
            client.get("/integrations/github/status"),
            client.get("/integrations/slack/status"),
            client.get("/integrations/jira/status"),
            client.get("/integrations/linear/status"),
            return_exceptions=True,
        )

        integrations: Dict[str, Any] = {
            "rootly": [],
            "github": [],
            "slack": [],
            "jira": [],
            "linear": [],
        }

        # Process results, handling partial failures gracefully
        endpoint_names = ["rootly", "github", "slack", "jira", "linear"]

        for idx, (name, result) in enumerate(zip(endpoint_names, results)):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch {name} integrations: {result}")
                integrations[name] = []
            else:
                try:
                    data = result.json()
                    if name == "rootly":
                        # Rootly returns a list directly
                        integrations[name] = [
                            normalize_rootly_integration(item) for item in data
                        ]
                    elif name == "github":
                        integrations[name] = normalize_github_status(data)
                    elif name == "slack":
                        integrations[name] = normalize_slack_status(data)
                    elif name == "jira":
                        integrations[name] = normalize_jira_status(data)
                    elif name == "linear":
                        integrations[name] = normalize_linear_status(data)
                except Exception as e:
                    logger.warning(f"Failed to normalize {name} response: {e}")
                    integrations[name] = []

        return integrations


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
