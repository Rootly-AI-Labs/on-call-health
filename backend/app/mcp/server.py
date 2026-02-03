"""MCP server for On-Call Health."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from fastmcp import FastMCP

from app.mcp.client import NotFoundError, OnCallHealthClient
from app.mcp.context import get_api_key
from app.mcp.normalizers import (
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


def _resolve_asgi_app(server: Any) -> Any:
    """Resolve ASGI app from FastMCP server, supporting multiple API versions."""
    # Try modern FastMCP 2.x+ API first
    if hasattr(server, "http_app"):
        return server.http_app()
    # Legacy FastMCP 1.x API (deprecated)
    if hasattr(server, "app"):
        return server.app
    if hasattr(server, "asgi_app"):
        return server.asgi_app()
    if hasattr(server, "streamable_http_app"):
        return server.streamable_http_app()
    if hasattr(server, "sse_app"):
        return server.sse_app()
    raise RuntimeError("FastMCP does not expose an ASGI app")


mcp_app = _resolve_asgi_app(mcp_server)


@mcp_server.tool()
async def analysis_start(
    days_back: int = 30,
    include_weekends: bool = True,
    integration_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Start a new burnout analysis."""
    api_key = get_api_key()
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
async def analysis_status(analysis_id: int) -> Dict[str, Any]:
    """Get the status of an analysis."""
    api_key = get_api_key()
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
async def analysis_results(analysis_id: int) -> Dict[str, Any]:
    """Get full results for a completed analysis."""
    api_key = get_api_key()
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
async def analysis_current() -> Dict[str, Any]:
    """Get the most recent analysis for the current user."""
    api_key = get_api_key()
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
async def integrations_list() -> Dict[str, Any]:
    """List connected integrations for the current user."""
    api_key = get_api_key()
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
