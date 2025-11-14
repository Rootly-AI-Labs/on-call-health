# app/api/endpoints/jira.py
"""
Jira integration API endpoints for OAuth and data collection.

- Uses OAuth 2.0 (3LO) flow with FRONTEND_URL redirect.
- Migrates all searches to the enhanced JQL API: GET /rest/api/3/search/jql
- Test endpoint logs per-assignee workload: ticket count, priority mix, earliest deadline.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone as dt_timezone, date
import logging
import base64
import secrets
import traceback

from cryptography.fernet import Fernet

from ...models import get_db, User, JiraIntegration, JiraWorkspaceMapping, UserCorrelation
from ...auth.dependencies import get_current_user
from ...auth.integration_oauth import jira_integration_oauth
from ...core.config import settings

router = APIRouter(prefix="/jira", tags=["jira-integration"])
logger = logging.getLogger(__name__)


# -------------------------------
# Small helpers
# -------------------------------
def _short(s: Optional[str], n: int = 12) -> str:
    if not s:
        return "None"
    return f"{s[:n]}…({len(s)})"


REQUESTED_SCOPES = [
    "read:jira-work",
    "read:jira-user",
    "offline_access",
]


# -------------------------------
# Encryption helpers
# -------------------------------
def get_encryption_key() -> bytes:
    key = settings.JWT_SECRET_KEY.encode()
    # Ensure 32 bytes for Fernet
    return base64.urlsafe_b64encode(key[:32].ljust(32, b"\0"))


def encrypt_token(token: str) -> str:
    return Fernet(get_encryption_key()).encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    return Fernet(get_encryption_key()).decrypt(encrypted_token.encode()).decode()


# -------------------------------
# Token freshness helper
# -------------------------------
def needs_refresh(expires_at: Optional[datetime], skew_minutes: int = 5) -> bool:
    if not expires_at:
        return False
    now = datetime.now(dt_timezone.utc)
    return expires_at <= now + timedelta(minutes=skew_minutes)


# -------------------------------
# Connect (start OAuth)
# -------------------------------
@router.post("/connect")
async def connect_jira(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not settings.JIRA_CLIENT_ID or not settings.JIRA_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jira OAuth is not configured. Please contact your administrator to set up Jira integration.",
        )
    state = secrets.token_urlsafe(32)
    auth_url = jira_integration_oauth.get_authorization_url(state=state)
    logger.info("[Jira] OAuth init by user=%s, org=%s", current_user.id, current_user.organization_id)
    return {"authorization_url": auth_url, "state": state}


# -------------------------------
# Core callback handler
# -------------------------------
async def _process_callback(code: str, state: Optional[str], db: Session, current_user: User) -> Response:
    try:
        logger.info("[Jira] Processing callback code=%s state=%s", _short(code), _short(state))

        user = current_user
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = user.id
        organization_id = user.organization_id

        # 1) Exchange code
        try:
            token_data = await jira_integration_oauth.exchange_code_for_token(code)
        except HTTPException as ex:
            msg = str(ex.detail or "")
            if "invalid_grant" in msg or "authorization code" in msg.lower():
                logger.warning("[Jira] Code already used; treating as idempotent success.")
                existing = db.query(JiraIntegration).filter(JiraIntegration.user_id == user_id).first()
                if existing:
                    return RedirectResponse(
                        url=f"{settings.FRONTEND_URL}/integrations?jira_connected=true&reuse=1",
                        status_code=status.HTTP_302_FOUND,
                    )
            raise

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get access token from Jira")

        # 2) Sites
        accessible_resources = await jira_integration_oauth.get_accessible_resources(access_token)
        if not accessible_resources:
            raise HTTPException(status_code=400, detail="No Jira sites found for this account")

        primary = accessible_resources[0]
        jira_cloud_id = primary.get("id")
        jira_site_url = primary.get("url", "").replace("https://", "")
        jira_site_name = primary.get("name")

        # 3) User info
        try:
            me = await jira_integration_oauth.get_user_info(access_token, jira_cloud_id)
            jira_account_id = me.get("accountId")
            jira_display_name = me.get("displayName")
            jira_email = me.get("emailAddress")
        except Exception as e:
            logger.warning("[Jira] /myself failed: %s", e)
            jira_account_id = jira_display_name = jira_email = None

        token_expires_at = datetime.now(dt_timezone.utc) + timedelta(seconds=expires_in)
        enc_access = encrypt_token(access_token)
        enc_refresh = encrypt_token(refresh_token) if refresh_token else None

        # 4) Upsert integration
        integration = db.query(JiraIntegration).filter(JiraIntegration.user_id == user_id).first()
        now = datetime.now(dt_timezone.utc)

        if integration:
            integration.access_token = enc_access
            integration.refresh_token = enc_refresh
            integration.jira_cloud_id = jira_cloud_id
            integration.jira_site_url = jira_site_url
            # optional name column if you add later:
            setattr(integration, "jira_site_name", jira_site_name)
            integration.jira_account_id = jira_account_id
            integration.jira_display_name = jira_display_name
            integration.jira_email = jira_email
            integration.accessible_resources = accessible_resources
            integration.token_source = "oauth"
            integration.token_expires_at = token_expires_at
            integration.updated_at = now
            logger.info("[Jira] Updated integration for user %s", user_id)
        else:
            integration = JiraIntegration(
                user_id=user_id,
                access_token=enc_access,
                refresh_token=enc_refresh,
                jira_cloud_id=jira_cloud_id,
                jira_site_url=jira_site_url,
                jira_account_id=jira_account_id,
                jira_display_name=jira_display_name,
                jira_email=jira_email,
                accessible_resources=accessible_resources,
                token_source="oauth",
                token_expires_at=token_expires_at,
                created_at=now,
                updated_at=now,
            )
            db.add(integration)
            logger.info("[Jira] Created integration for user %s", user_id)

        # 5) Workspace mapping
        if organization_id:
            mapping = db.query(JiraWorkspaceMapping).filter(
                JiraWorkspaceMapping.jira_cloud_id == jira_cloud_id,
                JiraWorkspaceMapping.organization_id == organization_id,
            ).first()
            if not mapping:
                mapping = JiraWorkspaceMapping(
                    jira_cloud_id=jira_cloud_id,
                    jira_site_url=jira_site_url,
                    jira_site_name=jira_site_name,
                    owner_user_id=user_id,
                    organization_id=organization_id,
                    registered_via="oauth",
                    status="active",
                    collection_enabled=True,
                    workload_metrics_enabled=True,
                )
                db.add(mapping)
                logger.info("[Jira] Created workspace mapping for org %s", organization_id)

        # 6) Correlate user
        if jira_email and jira_account_id and organization_id:
            corr = db.query(UserCorrelation).filter(
                UserCorrelation.organization_id == organization_id,
                UserCorrelation.email == jira_email,
            ).first()
            if corr:
                corr.jira_account_id = jira_account_id
                corr.jira_email = jira_email
            else:
                db.add(
                    UserCorrelation(
                        user_id=user_id,
                        organization_id=organization_id,
                        email=jira_email,
                        name=jira_display_name,
                        jira_account_id=jira_account_id,
                        jira_email=jira_email,
                    )
                )

        db.commit()

        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/integrations?jira_connected=true",
            status_code=status.HTTP_302_FOUND,
        )

    except HTTPException as he:
        logger.error("[Jira] OAuth callback HTTPException: status=%s detail=%s", he.status_code, he.detail)
        raise
    except Exception as e:
        logger.error("[Jira] OAuth callback error: %s", e, exc_info=True)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/integrations?jira_error={str(e)}",
            status_code=status.HTTP_302_FOUND,
        )


@router.get("/callback")
async def jira_oauth_callback_get(
    code: str = Query(...),
    state: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await _process_callback(code, state, db, current_user)


@router.post("/callback")
async def jira_oauth_callback_post(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    code: Optional[str] = None
    state: Optional[str] = None

    ctype = request.headers.get("content-type", "")
    logger.info("[Jira] POST /callback ctype=%s", ctype)

    if ctype.startswith("application/json"):
        try:
            body = await request.json()
            code = body.get("code")
            state = body.get("state")
            logger.info("[Jira] JSON body code=%s state=%s", _short(code), _short(state))
        except Exception:
            logger.warning("[Jira] JSON parse failed:\n%s", traceback.format_exc())

    if not code or state is None:
        try:
            form = await request.form()
            code = code or form.get("code")
            state = state if state is not None else form.get("state")
            if code or state:
                logger.info("[Jira] FORM body code=%s state=%s", _short(code), _short(state))
        except Exception:
            pass

    if not code or state is None:
        q = request.query_params
        code = code or q.get("code")
        state = state if state is not None else q.get("state")
        if code or state:
            logger.info("[Jira] QUERY params code=%s state=%s", _short(code), _short(state))

    if not code:
        logger.error("[Jira] Missing code in callback")
        raise HTTPException(status_code=400, detail="Missing code")

    return await _process_callback(code, state, db, current_user)


# -------------------------------
# Status / Test / Disconnect
# -------------------------------
@router.get("/status")
async def get_jira_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    integration = db.query(JiraIntegration).filter(JiraIntegration.user_id == current_user.id).first()

    if not integration:
        return {"connected": False, "integration": None}

    token_preview = None
    try:
        if integration.access_token:
            dec = decrypt_token(integration.access_token)
            token_preview = f"...{dec[-4:]}" if dec else None
    except Exception:
        pass

    workspace_mapping = None
    if current_user.organization_id:
        workspace_mapping = db.query(JiraWorkspaceMapping).filter(
            JiraWorkspaceMapping.jira_cloud_id == integration.jira_cloud_id,
            JiraWorkspaceMapping.organization_id == current_user.organization_id,
        ).first()

    response = {
        "connected": True,
        "integration": {
            "id": integration.id,
            "jira_cloud_id": integration.jira_cloud_id,
            "jira_site_url": integration.jira_site_url,
            "jira_site_name": getattr(integration, "jira_site_name", None),
            "jira_account_id": integration.jira_account_id,
            "jira_display_name": integration.jira_display_name,
            "jira_email": integration.jira_email,
            "token_source": integration.token_source,
            "is_oauth": integration.token_source == "oauth",
            "supports_refresh": (integration.token_source == "oauth") and bool(integration.refresh_token),
            "token_expires_at": integration.token_expires_at.isoformat() if integration.token_expires_at else None,
            "updated_at": integration.updated_at.isoformat() if integration.updated_at else None,
            "accessible_sites_count": len(getattr(integration, "accessible_resources", []) or []),
            "token_preview": token_preview,
        },
    }

    if workspace_mapping:
        response["workspace"] = {
            "id": workspace_mapping.id,
            "project_keys": workspace_mapping.project_keys,
            "collection_enabled": workspace_mapping.collection_enabled,
            "workload_metrics_enabled": workspace_mapping.workload_metrics_enabled,
            "last_collection_at": workspace_mapping.last_collection_at.isoformat()
            if workspace_mapping.last_collection_at
            else None,
        }

    return response


def _parse_due(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    try:
        # Jira duedate is YYYY-MM-DD (no time)
        return datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        return None


@router.post("/test")
async def test_jira_integration(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    - Refresh token if needed
    - Permissions smoke test
    - Fetch up to ~1000 “active” issues and log per-responder workload:
        * ticket count
        * priority distribution
        * earliest deadline (duedate)
    """
    integration = db.query(JiraIntegration).filter(JiraIntegration.user_id == current_user.id).first()
    if not integration:
        raise HTTPException(
            status_code=404,
            detail="Jira integration not found. Please connect your Jira account first.",
        )

    try:
        # Refresh if needed
        if needs_refresh(integration.token_expires_at) and integration.refresh_token:
            logger.info("[Jira] Refreshing access token for user %s", current_user.id)
            refresh_token = decrypt_token(integration.refresh_token)
            token_data = await jira_integration_oauth.refresh_access_token(refresh_token)
            new_access_token = token_data.get("access_token")
            new_refresh_token = token_data.get("refresh_token") or refresh_token
            expires_in = token_data.get("expires_in", 3600)

            if not new_access_token:
                raise HTTPException(status_code=400, detail="Failed to refresh Jira access token")

            integration.access_token = encrypt_token(new_access_token)
            integration.refresh_token = encrypt_token(new_refresh_token)
            integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(seconds=expires_in)
            integration.updated_at = datetime.now(dt_timezone.utc)
            db.commit()
            access_token = new_access_token
            refreshed = True
        else:
            access_token = decrypt_token(integration.access_token)
            refreshed = False

        # Permissions
        permissions = await jira_integration_oauth.test_permissions(access_token, integration.jira_cloud_id)
        me = await jira_integration_oauth.get_user_info(access_token, integration.jira_cloud_id)

        logger.info(
            "[Jira/Test] Result user=%s cloud_id=%s refreshed=%s supports_refresh=%s expires_at=%s",
            current_user.id,
            integration.jira_cloud_id,
            refreshed,
            (integration.token_source == "oauth") and bool(integration.refresh_token),
            integration.token_expires_at.isoformat() if integration.token_expires_at else None,
        )
        logger.info("[Jira/Test] Permissions: %s", permissions)
        logger.info(
            "[Jira/Test] User info: account_id=%s display_name=%s email=%s",
            me.get("accountId"),
            me.get("displayName"),
            me.get("emailAddress"),
        )

        # ---- Workload preview (per responder)
        # “Active” issues: assigned, not Done, recently touched. Tune as needed.
        jql = "assignee is not EMPTY AND statusCategory != Done AND updated >= -30d ORDER BY priority DESC, duedate ASC"
        fields = ["assignee", "priority", "duedate", "key"]

        total_issues = 0
        next_token: Optional[str] = None
        max_pages = 10  # up to ~1000 issues @ 100/page
        page = 0

        # aggregate: accountId -> metrics
        per: Dict[str, Dict[str, Any]] = {}
        while page < max_pages:
            res = await jira_integration_oauth.search_issues(
                access_token,
                integration.jira_cloud_id,
                jql=jql,
                fields=fields,
                max_results=100,
                next_page_token=next_token,
            )
            issues = (res or {}).get("issues") or []
            total_issues += len(issues)

            for it in issues:
                f = it.get("fields") or {}
                asg = (f.get("assignee") or {})
                acc = asg.get("accountId") or "unknown"
                name = asg.get("displayName") or acc

                if acc not in per:
                    per[acc] = {
                        "assignee_account_id": acc,
                        "assignee_name": name,
                        "count": 0,
                        "priorities": {},  # name -> count
                        "earliest_due": None,  # date
                        "issue_keys": [],
                    }
                per[acc]["count"] += 1
                p = (f.get("priority") or {}).get("name") or "Unspecified"
                per[acc]["priorities"][p] = per[acc]["priorities"].get(p, 0) + 1
                due = _parse_due(f.get("duedate"))
                if due:
                    ed = per[acc]["earliest_due"]
                    per[acc]["earliest_due"] = min(ed, due) if ed else due
                k = it.get("key")
                if k:
                    if len(per[acc]["issue_keys"]) < 10:  # avoid massive logs
                        per[acc]["issue_keys"].append(k)

            # pagination (enhanced API)
            is_last = bool(res.get("isLast"))
            next_token = res.get("nextPageToken")
            if is_last or not next_token:
                break
            page += 1

        # Log a readable summary
        logger.info("[Jira/Test] Workload summary: total_issues=%d", total_issues)
        for acc, m in per.items():
            prios = " ".join([f"{k}:{v}" for k, v in sorted(m["priorities"].items(), key=lambda kv: (-kv[1], kv[0]))])
            logger.info(
                "[Jira/Test] Responder %s (%s): tickets=%d, priorities=[%s], earliest_due=%s, samples=%s",
                m["assignee_name"],
                acc,
                m["count"],
                prios or "none",
                m["earliest_due"].isoformat() if m["earliest_due"] else "None",
                ",".join(m["issue_keys"]),
            )

        # Return a compact preview (optional, keeps frontend stable)
        preview = sorted(per.values(), key=lambda m: (-m["count"], m["assignee_name"]))[:20]
        for row in preview:
            # make priorities stable for JSON
            row["priorities"] = dict(sorted(row["priorities"].items(), key=lambda kv: (-kv[1], kv[0])))
            if isinstance(row.get("earliest_due"), date):
                row["earliest_due"] = row["earliest_due"].isoformat()

        return {
            "success": True,
            "message": "Jira integration is working correctly",
            "permissions": permissions,
            "user_info": {
                "account_id": me.get("accountId"),
                "display_name": me.get("displayName"),
                "email": me.get("emailAddress"),
            },
            "workload_preview": {
                "total_issues": total_issues,
                "per_responder": preview,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Jira] integration test failed: %s", e, exc_info=True)
        return {"success": False, "message": f"Jira integration test failed: {str(e)}", "permissions": None}


@router.delete("/disconnect")
async def disconnect_jira(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    integration = db.query(JiraIntegration).filter(JiraIntegration.user_id == current_user.id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Jira integration not found")

    try:
        if integration.jira_account_id and current_user.organization_id:
            correlations = db.query(UserCorrelation).filter(
                UserCorrelation.organization_id == current_user.organization_id,
                UserCorrelation.jira_account_id == integration.jira_account_id,
            ).all()
            for c in correlations:
                c.jira_account_id = None
                c.jira_email = None

        db.delete(integration)
        db.commit()
        logger.info("[Jira] Disconnected Jira integration for user %s", current_user.id)
        return {"success": True, "message": "Jira integration disconnected successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to disconnect Jira: {str(e)}")
