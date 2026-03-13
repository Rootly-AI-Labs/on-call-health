"""
Helpers for matching survey responses to members and time windows.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional


def normalize_survey_email(email: Optional[str]) -> str:
    """Normalize survey email keys for dedupe/matching."""
    return (email or "").strip().lower()


def get_utc_day_bounds(reference: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Return the UTC start/end bounds for the reference day."""
    now = reference.astimezone(timezone.utc) if reference else datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1) - timedelta(microseconds=1)
    return day_start, day_end


def extract_analysis_member_emails(results: Optional[dict]) -> list[str]:
    """
    Extract normalized member emails from analysis results.

    Surveys should apply only to analyses that actually include the member, so we
    derive the email set from the analysis team roster instead of the whole org.
    """
    if not results or not isinstance(results, dict):
        return []

    team_analysis = results.get("team_analysis", {})
    if isinstance(team_analysis, dict):
        members = team_analysis.get("members", []) or []
    elif isinstance(team_analysis, list):
        members = team_analysis
    else:
        members = []

    emails: list[str] = []
    seen: set[str] = set()

    for member in members:
        if not isinstance(member, dict):
            continue
        email = normalize_survey_email(member.get("user_email") or member.get("email"))
        if email and email not in seen:
            seen.add(email)
            emails.append(email)

    return emails
