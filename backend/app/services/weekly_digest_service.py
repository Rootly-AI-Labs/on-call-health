"""
Weekly email digest service for auto-refresh analyses.
"""
import base64
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import and_, func

from ..core.config import settings
from ..models import Analysis, SessionLocal, User, UserCorrelation, WeeklyDigestLog

logger = logging.getLogger(__name__)


def _ensure_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            data = json.loads(value)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _get_user_timezone(db, user_id: int) -> str:
    correlation = db.query(UserCorrelation).filter(
        UserCorrelation.user_id == user_id,
        UserCorrelation.timezone.isnot(None),
    ).order_by(
        UserCorrelation.last_synced_at.desc().nullslast(),
        UserCorrelation.id.desc()
    ).first()

    tz_name = correlation.timezone if correlation else None
    if not tz_name:
        return "UTC"

    try:
        pytz.timezone(tz_name)
        return tz_name
    except Exception:
        return "UTC"


def _get_week_start_date(local_dt: datetime) -> datetime.date:
    days_since_monday = local_dt.weekday()
    monday = (local_dt - timedelta(days=days_since_monday)).date()
    return monday


def _format_relative_time(then_dt: datetime, now_dt: datetime) -> str:
    delta = now_dt - then_dt
    seconds = max(0, int(delta.total_seconds()))

    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    if days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"
    weeks = days // 7
    return f"{weeks} week{'s' if weeks != 1 else ''} ago"


def _get_week_start_date_key(date_obj: datetime) -> str:
    day_of_week = date_obj.weekday()
    monday = date_obj - timedelta(days=day_of_week)
    return monday.date().isoformat()


def _aggregate_to_weekly(daily_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    dates = sorted(daily_data.keys())
    if not dates:
        return []

    weekly_buckets: Dict[str, List[float]] = {}
    for date_str in dates:
        try:
            date_obj = datetime.fromisoformat(date_str)
        except Exception:
            continue
        day_data = daily_data.get(date_str, {}) if isinstance(daily_data.get(date_str), dict) else {}
        day_score = day_data.get("health_score") or 0
        week_key = _get_week_start_date_key(date_obj)
        weekly_buckets.setdefault(week_key, []).append(day_score)

    weekly_data = []
    for week_start, scores in weekly_buckets.items():
        avg_score = sum(scores) / len(scores) if scores else 0
        weekly_data.append({"weekStart": week_start, "score": avg_score})

    return sorted(weekly_data, key=lambda x: x["weekStart"])


def _calculate_user_trend(
    user_email: str,
    individual_daily_data: Optional[Dict[str, Dict[str, Any]]]
) -> str:
    default_trend = "stable"
    if not individual_daily_data or not user_email:
        return default_trend

    user_data = individual_daily_data.get(user_email) or individual_daily_data.get(user_email.lower())
    if not user_data:
        return default_trend

    weekly_data = _aggregate_to_weekly(user_data)
    if len(weekly_data) < 2:
        return default_trend

    num_weeks_to_compare = min(2, len(weekly_data) // 2)
    if num_weeks_to_compare <= 0:
        return default_trend

    first_weeks_avg = sum(w["score"] for w in weekly_data[:num_weeks_to_compare]) / num_weeks_to_compare
    last_weeks_avg = sum(w["score"] for w in weekly_data[-num_weeks_to_compare:]) / num_weeks_to_compare

    both_low = first_weeks_avg < 10 and last_weeks_avg < 10
    abs_diff = last_weeks_avg - first_weeks_avg

    if both_low:
        if abs_diff <= -5:
            return "significantly_improving"
        if abs_diff <= -2:
            return "improving"
        if abs_diff >= 5:
            return "significantly_worsening"
        if abs_diff >= 2:
            return "worsening"
        return "stable"

    baseline = first_weeks_avg if first_weeks_avg != 0 else 1
    change = ((last_weeks_avg - first_weeks_avg) / baseline) * 100

    if change <= -30:
        return "significantly_improving"
    if change <= -15:
        return "improving"
    if change >= 30:
        return "significantly_worsening"
    if change >= 15:
        return "worsening"
    return "stable"


def _extract_members(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    team_analysis = results.get("team_analysis", {})
    if isinstance(team_analysis, list):
        return team_analysis
    if isinstance(team_analysis, dict):
        return team_analysis.get("members", []) or []
    return []


def _build_member_lists(
    members: List[Dict[str, Any]],
    individual_daily_data: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    critical_trend = []
    worsening_trend = []

    for member in members:
        email = member.get("user_email") or ""
        if not email:
            continue
        trend = _calculate_user_trend(email, individual_daily_data)
        if trend == "significantly_worsening":
            critical_trend.append(member)
        elif trend == "worsening":
            worsening_trend.append(member)

    return critical_trend, worsening_trend


def _format_member_item(member: Dict[str, Any]) -> str:
    name = member.get("user_name") or member.get("user_email") or "Unknown"
    email = member.get("user_email") or ""
    risk_level = member.get("risk_level") or "unknown"
    score = member.get("och_score")
    score_str = f"{round(score)}" if isinstance(score, (int, float)) else "n/a"
    return f"{name} ({email}) - Risk: {risk_level}, Score: {score_str}"


def _get_risk_summary(members: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(members)
    # Match dashboard logic: use och_score thresholds, only on-call members (incident_count > 0)
    oncall = [m for m in members if (m.get("incident_count") or 0) > 0]
    at_risk = sum(
        1 for m in oncall
        if isinstance(m.get("och_score"), (int, float)) and m["och_score"] >= 25
    )
    scores = [
        m["och_score"] for m in members
        if isinstance(m.get("och_score"), (int, float))
    ]
    avg_score = round(sum(scores) / len(scores)) if scores else None
    return {"total": total, "at_risk": at_risk, "avg_score": avg_score}


def _generate_unsubscribe_token(user_id: int) -> str:
    ts = int(time.time())
    payload = f"{user_id}:{ts}"
    secret = settings.JWT_SECRET_KEY.encode("utf-8")
    sig = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    raw = f"{payload}:{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_unsubscribe_token(token: str) -> Optional[str]:
    if not token:
        return None

    # Basic length guard to reduce brute-force surface and input abuse.
    # Expected payload is small; allow some slack for future extensions.
    if len(token) < 20 or len(token) > 512:
        return None

    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.b64decode(padded.encode(), altchars=b"-_", validate=True)
        return raw.decode()
    except Exception:
        return None


def verify_unsubscribe_token(token: str) -> Optional[int]:
    try:
        raw = _decode_unsubscribe_token(token)
        if not raw:
            return None

        last_colon = raw.rfind(":")
        if last_colon == -1:
            return None
        payload = raw[:last_colon]
        sig_hex = raw[last_colon + 1:]
        if len(sig_hex) != 64:
            return None

        try:
            sig = bytes.fromhex(sig_hex)
        except ValueError:
            return None

        secret = settings.JWT_SECRET_KEY.encode("utf-8")
        expected = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        parts = payload.split(":")
        if len(parts) != 2:
            return None
        if not parts[0].isdigit() or not parts[1].isdigit():
            return None
        uid, ts = int(parts[0]), int(parts[1])
        if uid <= 0:
            return None
        now = int(time.time())
        # Reject tokens far in the future (clock skew guard).
        if ts > now + 300:
            return None
        if now - ts > 90 * 24 * 3600:  # 90-day expiry
            return None
        return uid
    except Exception:
        return None


def _get_next_digest_time(tz_name: str) -> str:
    """Returns the next Monday at 10am in the given timezone, as UTC ISO string."""
    tz = pytz.timezone(tz_name)
    now = datetime.now(tz)
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0 and now.hour >= 10:
        days_until_monday = 7
    next_monday = now + timedelta(days=days_until_monday)
    next_10am = next_monday.replace(hour=10, minute=0, second=0, microsecond=0)
    return next_10am.astimezone(timezone.utc).isoformat()


def _build_email_content(
    user: User,
    analysis: Analysis,
    results: Dict[str, Any],
    local_now: datetime,
    tz_name: str,
    unsubscribe_url: str = "",
) -> Dict[str, str]:
    members = _extract_members(results)
    individual_daily_data = results.get("individual_daily_data") or {}
    if not isinstance(individual_daily_data, dict):
        individual_daily_data = {}

    critical_trend, worsening_trend = _build_member_lists(members, individual_daily_data)
    risk = _get_risk_summary(members)

    completed_at = analysis.completed_at
    if completed_at and completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)

    local_completed = completed_at.astimezone(local_now.tzinfo) if completed_at else None
    last_updated_relative = _format_relative_time(local_completed, local_now) if local_completed else "unknown"
    last_updated_absolute = local_completed.strftime("%b %d, %Y %I:%M %p %Z") if local_completed else "unknown"

    integration_name = analysis.integration_name or analysis.platform or "your integration"
    time_range = analysis.time_range or 30
    dashboard_url = f"{settings.FRONTEND_URL}/dashboard"

    blocked = _ensure_dict(analysis.config).get("auto_refresh_blocked") if analysis.config else None
    blocked_note_text = ""
    blocked_note_html = ""
    if isinstance(blocked, dict):
        provider = blocked.get("provider", "primary integration")
        reason = blocked.get("reason", "Token expired or invalid.")
        blocked_note_text = (
            f"\n\nNote: Auto-refresh is paused because your {provider} token is expired or invalid. "
            f"Reason: {reason}. Please reconnect in Integrations."
        )
        blocked_note_html = f"""
  <p style="margin: 16px 0 0; background: #fef3c7; border: 1px solid #fbbf24; border-radius: 6px; padding: 12px; color: #92400e; font-size: 13px;">
    <strong>Auto-refresh paused:</strong> Your {provider} token is expired or invalid &mdash; {reason}
    Please reconnect in Integrations. This email uses the last successful auto-refresh.
  </p>"""

    def format_list_text(items: List[Dict[str, Any]]) -> str:
        if not items:
            return "  None"
        return "\n".join([f"  - {_format_member_item(item)}" for item in items])

    _risk_colors = {
        "critical": "#ef4444",
        "high": "#f97316",
        "medium": "#eab308",
        "low": "#22c55e",
    }
    _trend_badges = {
        "significantly_worsening": ("&#8600;&#8600; Critical", "#fee2e2", "#ef4444"),
        "worsening":               ("&#8600; Worsening",       "#fff7ed", "#f97316"),
    }

    def format_list_html(items: List[Dict[str, Any]], trend: str) -> str:
        if not items:
            return '<li style="color: #6b7280;">None</li>'
        badge_text, badge_bg, badge_color = _trend_badges.get(
            trend, ("&#8600; Worsening", "#fff7ed", "#f97316")
        )
        rows = []
        for item in items:
            name = item.get("user_name") or item.get("user_email") or "Unknown"
            email = item.get("user_email") or ""
            risk_level_raw = (item.get("risk_level") or "unknown").lower()
            risk_color = _risk_colors.get(risk_level_raw, "#6b7280")
            score = item.get("och_score")
            score_str = f"{round(score)}" if isinstance(score, (int, float)) else "n/a"
            email_part = (
                f' <span style="color: #9ca3af; font-size: 12px;">({email})</span>'
                if email and email != name else ""
            )
            rows.append(
                f'<li style="margin-bottom: 10px; list-style: none; padding: 8px 10px;'
                f' background: #fafafa; border-radius: 6px; border: 1px solid #f3f4f6;">'
                f'<div style="font-size: 14px; margin-bottom: 5px;">'
                f'<strong style="color: #111827;">{name}</strong>{email_part}'
                f'</div>'
                f'<span style="display: inline-block; padding: 2px 10px; border-radius: 99px;'
                f' background: {badge_bg}; color: {badge_color}; font-size: 12px; font-weight: 700;'
                f' margin-right: 8px;">{badge_text}</span>'
                f'<span style="display: inline-block; padding: 2px 10px; border-radius: 99px;'
                f' background: #f9fafb; border: 1px solid #e5e7eb;'
                f' color: {risk_color}; font-size: 12px; font-weight: 600;">'
                f'&#9679; {risk_level_raw.capitalize()} &middot; {score_str}</span>'
                f'</li>'
            )
        return "\n".join(rows)

    subject = "On-Call Health Weekly Digest"

    # ── Plain-text body ──────────────────────────────────────────────────────
    text_lines = [
        "On-Call Health Weekly Digest",
        "",
        f"Integration: {integration_name} ({time_range}-day window)",
        f"Last updated: {last_updated_relative} ({last_updated_absolute})",
        f"Timezone: {tz_name}",
        "",
        "Team Overview",
        f"  Total members:   {risk['total']}",
        f"  At risk:         {risk['at_risk']}",
        f"  Worsening trend: {len(worsening_trend) + len(critical_trend)}",
    ]
    if risk["avg_score"] is not None:
        text_lines.append(f"  Avg OCH score:   {risk['avg_score']}")
    text_lines += [
        "",
        "Critical Trend",
        format_list_text(critical_trend),
        "",
        "Worsening Trend",
        format_list_text(worsening_trend),
        "",
        f"View full report: {dashboard_url}",
    ]
    if blocked_note_text:
        text_lines.append(blocked_note_text)
    if unsubscribe_url:
        text_lines += ["", f"Unsubscribe: {unsubscribe_url}"]
    text_body = "\n".join(text_lines)

    # ── Metrics table HTML ───────────────────────────────────────────────────
    avg_td = ""
    if risk["avg_score"] is not None:
        avg_td = f"""
        <td style="padding: 16px; text-align: center; border-left: 1px solid #e5e7eb;">
          <div style="font-size: 26px; font-weight: 700; color: #111827; line-height: 1;">{risk['avg_score']}</div>
          <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">Avg OCH Score</div>
        </td>"""

    unsubscribe_html = (
        f'<a href="{unsubscribe_url}" style="color: #9ca3af; text-decoration: underline; font-size: 12px;">'
        f'Unsubscribe from weekly digests</a>'
        if unsubscribe_url else ""
    )

    html_body = f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #111827;">

  <div style="border-left: 4px solid #7c3aed; padding-left: 16px; margin-bottom: 20px;">
    <h2 style="margin: 0 0 4px; font-size: 22px; color: #111827;">Weekly Digest</h2>
    <p style="margin: 0; color: #6b7280; font-size: 14px;">{integration_name} &middot; {time_range}-day window</p>
  </div>

  <p style="color: #6b7280; font-size: 14px; margin: 0 0 20px;">
    Last updated {last_updated_relative} ({last_updated_absolute}) &middot; {tz_name}
  </p>

  <table style="width: 100%; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; border-collapse: collapse; margin-bottom: 24px;">
    <tr>
      <td style="padding: 16px; text-align: center;">
        <div style="font-size: 26px; font-weight: 700; color: #111827; line-height: 1;">{risk['total']}</div>
        <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">Total Members</div>
      </td>
      <td style="padding: 16px; text-align: center; border-left: 1px solid #e5e7eb;">
        <div style="font-size: 26px; font-weight: 700; color: #ef4444; line-height: 1;">{risk['at_risk']}</div>
        <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">At Risk</div>
      </td>
      <td style="padding: 16px; text-align: center; border-left: 1px solid #e5e7eb;">
        <div style="font-size: 26px; font-weight: 700; color: #f59e0b; line-height: 1;">{len(worsening_trend) + len(critical_trend)}</div>
        <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">Worsening Trend</div>
      </td>
      {avg_td}
    </tr>
  </table>

  <h3 style="margin: 0 0 8px; font-size: 15px; color: #ef4444;">Critical Trend</h3>
  <ul style="margin: 0 0 20px; padding-left: 0; font-size: 14px; line-height: 1.7;">
    {format_list_html(critical_trend, "significantly_worsening")}
  </ul>

  <h3 style="margin: 0 0 8px; font-size: 15px; color: #f59e0b;">Worsening Trend</h3>
  <ul style="margin: 0 0 24px; padding-left: 0; font-size: 14px; line-height: 1.7;">
    {format_list_html(worsening_trend, "worsening")}
  </ul>

  <a href="{dashboard_url}"
     style="display: inline-block; background: #7c3aed; color: white; text-decoration: none;
            padding: 10px 20px; border-radius: 6px; font-size: 14px; font-weight: 600; margin-bottom: 24px;">
    View Full Report &rarr;
  </a>

{blocked_note_html}

  <div style="border-top: 1px solid #e5e7eb; margin-top: 32px; padding-top: 16px; color: #9ca3af;">
    {unsubscribe_html}
  </div>

</div>"""

    return {"subject": subject, "text": text_body, "html": html_body}


async def _send_resend_email(
    to_email: str,
    to_name: Optional[str],
    subject: str,
    text_body: str,
    html_body: str
) -> bool:
    if not settings.RESEND_API_KEY or not settings.RESEND_FROM_EMAIL:
        logger.warning("Weekly digest disabled: missing RESEND_API_KEY or RESEND_FROM_EMAIL")
        return False

    from_name = settings.RESEND_FROM_NAME.strip() if settings.RESEND_FROM_NAME else ""
    from_email = settings.RESEND_FROM_EMAIL.strip()
    from_value = f"{from_name} <{from_email}>" if from_name else from_email

    payload = {
        "from": from_value,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
        "html": html_body
    }

    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post("https://api.resend.com/emails", json=payload, headers=headers)
        if resp.status_code in (200, 201, 202):
            return True
        logger.error(f"Resend error {resp.status_code}: {resp.text}")
        return False
    except Exception as e:
        logger.error(f"Resend request failed: {e}")
        return False


def _get_latest_auto_refresh_analysis(db, user: User) -> Optional[Analysis]:
    return db.query(Analysis).filter(
        Analysis.user_id == user.id,
        Analysis.organization_id == user.organization_id,
        Analysis.is_auto_refresh == True,
        Analysis.status == "completed",
        Analysis.completed_at.isnot(None),
    ).order_by(Analysis.completed_at.desc()).first()


async def send_weekly_digest_test(db, user_id: int) -> Dict[str, Any]:
    """
    Send a test weekly digest email for the current user.
    Skips scheduler time checks and idempotency logging.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.status == "active"
    ).first()

    if not user or not user.email or not user.organization_id:
        return {"sent": False, "message": "User not found or missing organization"}

    analysis = _get_latest_auto_refresh_analysis(db, user)
    if not analysis:
        return {"sent": False, "message": "No completed auto-refresh analysis found"}

    config = _ensure_dict(analysis.config)
    if config.get("is_demo") is True:
        return {"sent": False, "message": "Demo analyses are excluded from weekly digests"}

    results = _ensure_dict(analysis.results)
    if not results:
        return {"sent": False, "message": "Analysis results are missing"}

    tz_name = _get_user_timezone(db, user.id)
    tz = pytz.timezone(tz_name)
    local_now = datetime.now(tz)

    unsubscribe_token = _generate_unsubscribe_token(user.id)
    unsubscribe_url = f"{settings.API_BASE_URL}/api/digests/weekly/unsubscribe?token={unsubscribe_token}"

    content = _build_email_content(
        user=user,
        analysis=analysis,
        results=results,
        local_now=local_now,
        tz_name=tz_name,
        unsubscribe_url=unsubscribe_url,
    )

    sent = await _send_resend_email(
        to_email=user.email,
        to_name=user.name,
        subject=content["subject"],
        text_body=content["text"],
        html_body=content["html"]
    )

    if not sent:
        return {"sent": False, "message": "Failed to send email - check Resend settings"}

    return {
        "sent": True,
        "message": "Weekly digest test email sent",
        "analysis_id": analysis.id,
        "last_updated_at": analysis.completed_at.isoformat() if analysis.completed_at else None
    }


async def check_and_send_weekly_digests() -> None:
    if not settings.WEEKLY_DIGEST_ENABLED:
        logger.debug("Weekly digest scheduler disabled (WEEKLY_DIGEST_ENABLED=false)")
        return

    db = SessionLocal()
    try:
        # Latest completed auto-refresh analysis per user
        subquery = db.query(
            Analysis.user_id.label("user_id"),
            func.max(Analysis.completed_at).label("latest_completed")
        ).filter(
            Analysis.is_auto_refresh == True,
            Analysis.status == "completed",
            Analysis.completed_at.isnot(None)
        ).group_by(Analysis.user_id).subquery()

        analyses = db.query(Analysis).join(
            subquery,
            and_(
                Analysis.user_id == subquery.c.user_id,
                Analysis.completed_at == subquery.c.latest_completed
            )
        ).all()

        for analysis in analyses:
            try:
                user = db.query(User).filter(
                    User.id == analysis.user_id,
                    User.status == "active"
                ).first()

                if not user or not user.email:
                    continue

                if not analysis.organization_id or not user.organization_id:
                    continue

                if analysis.organization_id != user.organization_id:
                    continue

                # Skip users who have opted out
                if not user.weekly_digest_enabled:
                    continue

                config = _ensure_dict(analysis.config)
                if config.get("is_demo") is True:
                    continue

                tz_name = _get_user_timezone(db, user.id)
                tz = pytz.timezone(tz_name)
                local_now = datetime.now(tz)

                # Monday at 10am local time
                if local_now.weekday() != 0:
                    continue
                if local_now.hour != 10:
                    continue

                week_start_date = _get_week_start_date(local_now)

                existing_log = db.query(WeeklyDigestLog).filter(
                    WeeklyDigestLog.user_id == user.id,
                    WeeklyDigestLog.week_start_date == week_start_date
                ).first()

                if existing_log:
                    continue

                results = _ensure_dict(analysis.results)
                if not results:
                    continue

                unsubscribe_token = _generate_unsubscribe_token(user.id)
                unsubscribe_url = f"{settings.API_BASE_URL}/api/digests/weekly/unsubscribe?token={unsubscribe_token}"

                content = _build_email_content(
                    user=user,
                    analysis=analysis,
                    results=results,
                    local_now=local_now,
                    tz_name=tz_name,
                    unsubscribe_url=unsubscribe_url,
                )

                sent = await _send_resend_email(
                    to_email=user.email,
                    to_name=user.name,
                    subject=content["subject"],
                    text_body=content["text"],
                    html_body=content["html"]
                )

                if not sent:
                    continue

                log_entry = WeeklyDigestLog(
                    user_id=user.id,
                    analysis_id=analysis.id,
                    week_start_date=week_start_date,
                    timezone=tz_name
                )
                db.add(log_entry)
                db.commit()

                logger.info(
                    f"Weekly digest sent to {user.email} for week starting {week_start_date}"
                )

            except Exception as per_user_error:
                logger.error(
                    f"Weekly digest failed for analysis {analysis.id}: {per_user_error}",
                    exc_info=True
                )
                db.rollback()

    except Exception as e:
        logger.error(f"Weekly digest scheduler error: {e}", exc_info=True)
    finally:
        db.close()


class WeeklyDigestScheduler:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        if self.scheduler.running:
            return
        self.scheduler.add_job(
            check_and_send_weekly_digests,
            trigger=CronTrigger(minute="*/10"),
            id="weekly_digest",
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("Weekly digest scheduler started (every 10 minutes)")


weekly_digest_scheduler = WeeklyDigestScheduler()
