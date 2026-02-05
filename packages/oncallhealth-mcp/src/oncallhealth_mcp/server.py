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


# Helper functions for validation
def _validate_analysis_id(analysis_id: int) -> None:
    """Validate that analysis_id is positive.

    Args:
        analysis_id: The analysis ID to validate

    Raises:
        ValueError: If analysis_id is not positive
    """
    if analysis_id <= 0:
        raise ValueError(f"analysis_id must be positive, got {analysis_id}")


def _validate_api_key(ctx: Any) -> str:
    """Extract and validate API key from context.

    Args:
        ctx: MCP context containing request metadata

    Returns:
        str: The extracted API key

    Raises:
        PermissionError: If API key is missing
    """
    api_key = extract_api_key_header(ctx)
    if not api_key:
        raise PermissionError("Missing API key. Provide X-API-Key header.")
    return api_key


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

    if days_back <= 0:
        raise ValueError(f"days_back must be positive, got {days_back}")
    if days_back > 365:
        raise ValueError(f"days_back cannot exceed 365 days, got {days_back}")
    if integration_id is not None and integration_id <= 0:
        raise ValueError(f"integration_id must be positive, got {integration_id}")

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

    if analysis_id <= 0:
        raise ValueError(f"analysis_id must be positive, got {analysis_id}")

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

    if analysis_id <= 0:
        raise ValueError(f"analysis_id must be positive, got {analysis_id}")

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
    api_key = _validate_api_key(ctx)
    _validate_analysis_id(analysis_id)

    async with OnCallHealthClient(api_key=api_key) as client:
        try:
            response = await client.get(f"/analyses/{analysis_id}")
            data = response.json()
            if data.get("status") != "completed":
                raise ValueError(f"Analysis not completed yet (status={data['status']})")

            # Extract analysis_data
            analysis_data = data.get("analysis_data") or {}
            members = analysis_data.get("team_analysis", {}).get("members", [])

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


@mcp_server.tool()
async def get_at_risk_users(
    ctx: Any,
    analysis_id: int,
    min_och_score: float = 50.0,
    include_risk_levels: Optional[str] = "medium,high"
) -> Dict[str, Any]:
    """Get users at or above burnout threshold with their external IDs.

    Use this to identify at-risk responders and correlate with external
    systems (Rootly, PagerDuty, Slack) using their platform-specific IDs.

    Args:
        analysis_id: The analysis to query
        min_och_score: Minimum OCH score threshold (default: 50.0)
        include_risk_levels: Comma-separated risk levels to include (default: "medium,high").
                            Risk levels are case-insensitive.

    Returns:
        - total_at_risk: count of users at or above threshold (och_score >= min_och_score)
        - users: list of {user_name, och_score, risk_level, burnout_score,
                         incident_count, rootly_user_id, pagerduty_user_id,
                         slack_user_id, github_username}

    Example:
        >>> result = await get_at_risk_users(ctx, 1226, min_och_score=60)
        >>> print(f"Found {result['total_at_risk']} at-risk users")
    """
    api_key = _validate_api_key(ctx)
    _validate_analysis_id(analysis_id)
    if min_och_score < 0:
        raise ValueError(f"min_och_score must be non-negative, got {min_och_score}")

    async with OnCallHealthClient(api_key=api_key) as client:
        try:
            response = await client.get(f"/analyses/{analysis_id}")
            data = response.json()
            if data.get("status") != "completed":
                raise ValueError(f"Analysis not completed yet (status={data['status']})")

            # Extract members from team_analysis
            analysis_data = data.get("analysis_data") or {}
            members = analysis_data.get("team_analysis", {}).get("members", [])

            # Parse risk levels filter
            risk_levels = None
            if include_risk_levels:
                risk_levels = set(level.strip().lower() for level in include_risk_levels.split(","))

            # Filter users above threshold
            at_risk_users = []
            for member in members:
                och_score = member.get("och_score", 0)
                risk_level = member.get("risk_level", "").lower()

                # Apply OCH score filter
                if och_score < min_och_score:
                    continue

                # Apply risk level filter if specified
                if risk_levels and risk_level not in risk_levels:
                    continue

                # Build compact user object with external IDs
                at_risk_users.append({
                    "user_name": member.get("user_name", "Unknown"),
                    "och_score": och_score,
                    "risk_level": member.get("risk_level", "unknown"),
                    "burnout_score": member.get("burnout_score", 0),
                    "incident_count": member.get("incident_count", 0),
                    "rootly_user_id": member.get("rootly_user_id"),
                    "pagerduty_user_id": member.get("pagerduty_user_id"),
                    "slack_user_id": member.get("slack_user_id"),
                    "github_username": member.get("github_username"),
                })

            # Sort by OCH score descending (highest risk first)
            at_risk_users.sort(key=lambda u: u["och_score"], reverse=True)

            return {
                "total_at_risk": len(at_risk_users),
                "users": at_risk_users,
            }
        except NotFoundError:
            raise LookupError("Analysis not found")


@mcp_server.tool()
async def get_safe_responders(
    ctx: Any,
    analysis_id: int,
    max_och_score: float = 30.0,
    limit: int = 10
) -> Dict[str, Any]:
    """Get users with low burnout risk suitable for additional on-call.

    Use this to find replacement responders when removing at-risk users
    from schedules.

    Args:
        analysis_id: The analysis to query
        max_och_score: Maximum OCH score threshold (default: 30.0)
        limit: Maximum users to return (default: 10)

    Returns:
        - total_safe: count of users at or below threshold (och_score <= max_och_score)
        - users: list of {user_name, och_score, risk_level,
                         rootly_user_id, slack_user_id}
                 sorted by och_score ascending (healthiest first)

    Example:
        >>> result = await get_safe_responders(ctx, 1226, max_och_score=30, limit=5)
        >>> print(f"Found {result['total_safe']} safe responders")
    """
    api_key = _validate_api_key(ctx)
    _validate_analysis_id(analysis_id)
    if max_och_score < 0:
        raise ValueError(f"max_och_score must be non-negative, got {max_och_score}")
    if limit <= 0:
        raise ValueError(f"limit must be positive, got {limit}")

    async with OnCallHealthClient(api_key=api_key) as client:
        try:
            response = await client.get(f"/analyses/{analysis_id}")
            data = response.json()
            if data.get("status") != "completed":
                raise ValueError(f"Analysis not completed yet (status={data['status']})")

            # Extract members from team_analysis
            analysis_data = data.get("analysis_data") or {}
            members = analysis_data.get("team_analysis", {}).get("members", [])

            # Filter users below threshold
            safe_users = []
            for member in members:
                och_score = member.get("och_score", 0)

                # Apply OCH score filter
                if och_score > max_och_score:
                    continue

                # Build compact user object
                safe_users.append({
                    "user_name": member.get("user_name", "Unknown"),
                    "och_score": och_score,
                    "risk_level": member.get("risk_level", "unknown"),
                    "rootly_user_id": member.get("rootly_user_id"),
                    "slack_user_id": member.get("slack_user_id"),
                })

            # Sort by OCH score ascending (healthiest first)
            safe_users.sort(key=lambda u: u["och_score"])

            # Apply limit
            limited_users = safe_users[:limit]

            return {
                "total_safe": len(safe_users),
                "users": limited_users,
            }
        except NotFoundError:
            raise LookupError("Analysis not found")


@mcp_server.tool()
async def check_users_risk(
    ctx: Any,
    analysis_id: int,
    rootly_user_ids: str,
    min_och_score: float = 50.0
) -> Dict[str, Any]:
    """Check burnout risk for specific users by their Rootly user IDs.

    Use this after fetching a schedule from Rootly to check if any
    scheduled responders are at risk.

    Args:
        analysis_id: The analysis to query
        rootly_user_ids: Comma-separated Rootly user IDs (e.g., "2381,94178,27965")
        min_och_score: Minimum OCH score threshold for at-risk classification (default: 50.0)

    Returns:
        - checked: number of IDs checked
        - found: number matched in analysis
        - at_risk: list of users with och_score >= min_och_score or risk_level in [medium, high]
        - healthy: list of users with low risk
        - not_found: list of rootly_user_ids not in analysis

    Example:
        >>> result = await check_users_risk(ctx, 1226, "2381,94178,27965")
        >>> print(f"{len(result['at_risk'])} users are at risk")
    """
    api_key = _validate_api_key(ctx)
    _validate_analysis_id(analysis_id)
    if min_och_score < 0:
        raise ValueError(f"min_och_score must be non-negative, got {min_och_score}")
    if not rootly_user_ids or not rootly_user_ids.strip():
        raise ValueError("rootly_user_ids cannot be empty")

    async with OnCallHealthClient(api_key=api_key) as client:
        try:
            response = await client.get(f"/analyses/{analysis_id}")
            data = response.json()
            if data.get("status") != "completed":
                raise ValueError(f"Analysis not completed yet (status={data['status']})")

            # Extract members from team_analysis
            analysis_data = data.get("analysis_data") or {}
            members = analysis_data.get("team_analysis", {}).get("members", [])

            # Parse input IDs
            requested_ids = set()
            for id_str in rootly_user_ids.split(","):
                id_str = id_str.strip()
                if id_str:
                    try:
                        user_id = int(id_str)
                        # Validate positive integer within reasonable bounds
                        # Using 64-bit limit to support modern ID systems (Rootly, PagerDuty, etc.)
                        if user_id <= 0 or user_id > 9223372036854775807:  # Max 64-bit signed int
                            raise ValueError(f"Invalid rootly_user_id: {id_str}")
                        requested_ids.add(user_id)
                    except ValueError:
                        raise ValueError(f"Invalid rootly_user_id: {id_str}")

            # Build lookup by rootly_user_id
            members_by_rootly_id = {}
            for member in members:
                rootly_id = member.get("rootly_user_id")
                if rootly_id is not None:
                    members_by_rootly_id[rootly_id] = member

            # Categorize users
            at_risk = []
            healthy = []
            not_found = []

            for rootly_id in requested_ids:
                member = members_by_rootly_id.get(rootly_id)

                if member is None:
                    not_found.append(rootly_id)
                    continue

                # Check if at risk
                och_score = member.get("och_score", 0)
                risk_level = member.get("risk_level", "").lower()

                user_info = {
                    "rootly_user_id": rootly_id,
                    "user_name": member.get("user_name", "Unknown"),
                    "och_score": och_score,
                    "risk_level": member.get("risk_level", "unknown"),
                }

                if och_score >= min_och_score or risk_level in ["medium", "high"]:
                    at_risk.append(user_info)
                else:
                    healthy.append(user_info)

            return {
                "checked": len(requested_ids),
                "found": len(at_risk) + len(healthy),
                "at_risk": at_risk,
                "healthy": healthy,
                "not_found": not_found,
            }
        except NotFoundError:
            raise LookupError("Analysis not found")


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
