"""
AI Usage integration endpoints — connect/status/test/disconnect for OpenAI and Anthropic.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import logging
import base64
from cryptography.fernet import Fernet

from ...models import get_db, User, AIUsageIntegration
from ...auth.dependencies import get_current_user
from ...core.config import settings
from ...services.ai_usage_collector import collect_ai_usage

router = APIRouter(prefix="/ai-usage", tags=["ai-usage-integration"])
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Encryption (same pattern as github.py)
# --------------------------------------------------------------------------- #

def _get_fernet() -> Fernet:
    key = settings.JWT_SECRET_KEY.encode()
    key = base64.urlsafe_b64encode(key[:32].ljust(32, b"\0"))
    return Fernet(key)


def _encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    return _get_fernet().decrypt(value.encode()).decode()


# --------------------------------------------------------------------------- #
#  Request / response models
# --------------------------------------------------------------------------- #

class AIUsageConnectRequest(BaseModel):
    openai_api_key: Optional[str] = None
    openai_org_id: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    anthropic_workspace_id: Optional[str] = None


class AIUsageStatusResponse(BaseModel):
    connected: bool
    openai_enabled: bool
    anthropic_enabled: bool
    openai_org_id: Optional[str] = None
    anthropic_workspace_id: Optional[str] = None


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _get_integration(user: User, db: Session) -> Optional[AIUsageIntegration]:
    return db.query(AIUsageIntegration).filter(
        AIUsageIntegration.organization_id == user.organization_id
    ).first()


# --------------------------------------------------------------------------- #
#  Endpoints
# --------------------------------------------------------------------------- #

@router.get("/status", response_model=AIUsageStatusResponse)
async def get_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    integration = _get_integration(current_user, db)
    if not integration:
        return AIUsageStatusResponse(connected=False, openai_enabled=False, anthropic_enabled=False)
    return AIUsageStatusResponse(
        connected=integration.is_connected,
        openai_enabled=integration.openai_enabled,
        anthropic_enabled=integration.anthropic_enabled,
        openai_org_id=integration.openai_org_id,
        anthropic_workspace_id=integration.anthropic_workspace_id,
    )


@router.post("/connect")
async def connect(
    request: AIUsageConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    integration = _get_integration(current_user, db)
    if not integration:
        integration = AIUsageIntegration(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
        )
        db.add(integration)

    if request.openai_api_key:
        integration.openai_api_key = _encrypt(request.openai_api_key)
        integration.openai_org_id = request.openai_org_id.strip() if request.openai_org_id and request.openai_org_id.strip() else None
        integration.openai_enabled = True

    if request.anthropic_api_key:
        integration.anthropic_api_key = _encrypt(request.anthropic_api_key)
        integration.anthropic_workspace_id = request.anthropic_workspace_id.strip() if request.anthropic_workspace_id and request.anthropic_workspace_id.strip() else None
        integration.anthropic_enabled = True

    db.commit()
    db.refresh(integration)
    return {"success": True, "openai_enabled": integration.openai_enabled, "anthropic_enabled": integration.anthropic_enabled}


@router.post("/test")
async def test_connection(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import httpx
    from datetime import date, timedelta
    from ...services.ai_usage_collector import _date_to_unix

    integration = _get_integration(current_user, db)
    if not integration or not integration.is_connected:
        raise HTTPException(status_code=404, detail="No AI usage integration configured")

    results = {}

    # --- Test OpenAI ---
    if integration.has_openai:
        openai_key = _decrypt(integration.openai_api_key)
        end = date.today()
        start = end - timedelta(days=1)
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json",
        }
        if integration.openai_org_id and integration.openai_org_id.strip():
            headers["OpenAI-Organization"] = integration.openai_org_id.strip()
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/organization/usage/completions",
                    headers=headers,
                    params={
                        "start_time": _date_to_unix(start),
                        "bucket_width": "1d",
                    },
                )
            if resp.status_code == 200:
                results["openai"] = {"success": True}
            elif resp.status_code == 401:
                raise HTTPException(status_code=400, detail="OpenAI key is invalid or expired. Please check your API key.")
            elif resp.status_code == 403:
                raise HTTPException(status_code=400, detail="OpenAI key does not have Admin access. The usage API requires an Admin-level API key — standard keys are not supported.")
            elif resp.status_code == 429:
                raise HTTPException(status_code=400, detail="OpenAI rate limit hit during test. The key is valid but you've exceeded the request limit.")
            else:
                body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                msg = body.get("error", {}).get("message", f"Unexpected response: HTTP {resp.status_code}")
                raise HTTPException(status_code=400, detail=f"OpenAI test failed: {msg}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not reach OpenAI API: {str(e)}")

    # --- Test Anthropic ---
    if integration.has_anthropic:
        from datetime import datetime, timezone
        anthropic_key = _decrypt(integration.anthropic_api_key)
        headers = {
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01",
        }
        yesterday = date.today() - timedelta(days=1)
        test_params: dict = {
            "starting_at": datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=timezone.utc).isoformat(),
            "ending_at": datetime(date.today().year, date.today().month, date.today().day, tzinfo=timezone.utc).isoformat(),
            "bucket_width": "1d",
            "limit": 2,
        }
        if integration.anthropic_workspace_id and integration.anthropic_workspace_id.strip():
            test_params["workspace_ids[]"] = integration.anthropic_workspace_id.strip()
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.anthropic.com/v1/organizations/usage_report/messages",
                    headers=headers,
                    params=test_params,
                )
            if resp.status_code == 200:
                results["anthropic"] = {"success": True}
            elif resp.status_code == 401:
                raise HTTPException(status_code=400, detail="Anthropic key is invalid or expired. Please check your API key.")
            elif resp.status_code == 403:
                raise HTTPException(status_code=400, detail="Anthropic key does not have Admin access. The usage API requires an Admin-level API key — standard keys are not supported.")
            else:
                body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                msg = body.get("error", {}).get("message", f"Unexpected response: HTTP {resp.status_code}")
                raise HTTPException(status_code=400, detail=f"Anthropic test failed: {msg}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not reach Anthropic API: {str(e)}")

    return {"success": True, **results}


@router.delete("/disconnect")
async def disconnect(
    provider: Optional[str] = None,  # 'openai', 'anthropic', or None (both)
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    integration = _get_integration(current_user, db)
    if not integration:
        raise HTTPException(status_code=404, detail="No integration found")

    if provider == "openai" or provider is None:
        integration.openai_api_key = None
        integration.openai_org_id = None
        integration.openai_enabled = False

    if provider == "anthropic" or provider is None:
        integration.anthropic_api_key = None
        integration.anthropic_workspace_id = None
        integration.anthropic_enabled = False

    if not integration.is_connected:
        db.delete(integration)

    db.commit()
    return {"success": True}


@router.get("/usage")
async def get_usage(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return daily AI token usage for the current org (up to 90 days)."""
    days = min(max(days, 1), 90)
    integration = _get_integration(current_user, db)
    if not integration or not integration.is_connected:
        return {"usage": {}}

    openai_key = _decrypt(integration.openai_api_key) if integration.has_openai else None
    anthropic_key = _decrypt(integration.anthropic_api_key) if integration.has_anthropic else None

    data = await collect_ai_usage(
        openai_api_key=openai_key,
        openai_org_id=integration.openai_org_id,
        anthropic_api_key=anthropic_key,
        anthropic_workspace_id=integration.anthropic_workspace_id,
        days=days,
    )
    return {"usage": data}
