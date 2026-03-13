"""
Weekly digest API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...auth.dependencies import get_current_active_user
from ...core.config import settings
from ...core.rate_limiting import digest_rate_limit
from ...models import User, WeeklyDigestLog, get_db
from ...services.weekly_digest_service import (
    _get_latest_auto_refresh_analysis,
    _get_next_digest_time,
    _get_user_timezone,
    send_weekly_digest_test,
    verify_unsubscribe_token,
)

router = APIRouter(
    prefix="/digests",
    tags=["digests"]
)


class DigestPreferenceUpdate(BaseModel):
    enabled: bool


@router.get("/weekly/preference")
async def get_weekly_digest_preference(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    analysis = _get_latest_auto_refresh_analysis(db, current_user)
    has_auto_refresh = analysis is not None

    last_log = (
        db.query(WeeklyDigestLog)
        .filter(WeeklyDigestLog.user_id == current_user.id)
        .order_by(WeeklyDigestLog.sent_at.desc())
        .first()
    )
    last_sent_at = last_log.sent_at.isoformat() if last_log and last_log.sent_at else None

    next_send_at = None
    if has_auto_refresh and current_user.weekly_digest_enabled:
        tz_name = _get_user_timezone(db, current_user.id)
        next_send_at = _get_next_digest_time(tz_name)

    return {
        "enabled": current_user.weekly_digest_enabled,
        "has_auto_refresh": has_auto_refresh,
        "last_sent_at": last_sent_at,
        "next_send_at": next_send_at,
    }


@router.patch("/weekly/preference")
async def update_weekly_digest_preference(
    body: DigestPreferenceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    current_user.weekly_digest_enabled = body.enabled
    db.commit()
    db.refresh(current_user)
    return {"enabled": current_user.weekly_digest_enabled}


@router.get("/weekly/unsubscribe")
@digest_rate_limit("digest_unsubscribe")
async def unsubscribe_weekly_digest(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    if not token or len(token) < 20 or len(token) > 512:
        return HTMLResponse(
            content="<p style='font-family:Arial;text-align:center;padding:40px;'>Invalid or expired unsubscribe link.</p>",
            status_code=400
        )

    # Basic character whitelist to avoid non-url-safe input
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")
    if any(ch not in allowed for ch in token):
        return HTMLResponse(
            content="<p style='font-family:Arial;text-align:center;padding:40px;'>Invalid or expired unsubscribe link.</p>",
            status_code=400
        )

    user_id = verify_unsubscribe_token(token)
    if not user_id:
        return HTMLResponse(
            content="<p style='font-family:Arial;text-align:center;padding:40px;'>Invalid or expired unsubscribe link.</p>",
            status_code=400
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return HTMLResponse(
            content="<p style='font-family:Arial;text-align:center;padding:40px;'>User not found.</p>",
            status_code=404
        )

    user.weekly_digest_enabled = False
    db.commit()

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Unsubscribed &mdash; On-Call Health</title></head>
<body style="font-family:Arial,sans-serif;text-align:center;padding:60px 20px;color:#111827;max-width:480px;margin:0 auto;">
  <div style="border-left:4px solid #7c3aed;padding-left:16px;text-align:left;margin-bottom:32px;">
    <h2 style="margin:0 0 4px;color:#111827;">Unsubscribed</h2>
    <p style="margin:0;color:#6b7280;font-size:14px;">On-Call Health</p>
  </div>
  <p style="font-size:15px;color:#374151;">
    You've been unsubscribed from weekly digest emails.
  </p>
  <p style="font-size:14px;color:#6b7280;margin-top:16px;">
    You can re-enable them at any time from
    <strong>Account Settings &rarr; Weekly Digest</strong>.
  </p>
  <a href="{settings.FRONTEND_URL}"
     style="display:inline-block;margin-top:24px;background:#7c3aed;color:white;
            text-decoration:none;padding:10px 20px;border-radius:6px;font-size:14px;font-weight:600;">
    Return to On-Call Health
  </a>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.post("/weekly/test")
async def send_weekly_digest_test_email(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    result = await send_weekly_digest_test(db, current_user.id)

    if not result.get("sent"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to send weekly digest test"))

    return result
