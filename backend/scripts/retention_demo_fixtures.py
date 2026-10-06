"""Create synthetic retention examples inside a caller-owned local transaction.

The local demo CLI owns database safeguards and organization/account setup.
This module only inserts fixtures and flushes their IDs; it never commits,
invokes integration providers, enables retention, or runs cleanup.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Analysis, Organization, User, UserBurnoutReport, UserCorrelation


def _result_payload(
    mock_users: Sequence[User], *, case: str, now: datetime
) -> dict[str, Any]:
    """Build small dashboard-compatible results with explicit UTC source ages."""
    old = now - timedelta(days=120)
    recent = now - timedelta(days=10)
    if case in {"old", "saved_old", "running"}:
        start, end = old, now - timedelta(days=110)
        incident_times = [old + timedelta(days=index) for index in range(len(mock_users))]
    elif case in {"mixed", "recent"}:
        start, end = old, now
        incident_times = [old] + [recent + timedelta(days=index) for index in range(len(mock_users) - 1)]
    else:
        start, end = recent, now
        incident_times = [recent + timedelta(days=index) for index in range(len(mock_users))]

    members = []
    incidents = []
    for index, (user, event_at) in enumerate(zip(mock_users, incident_times)):
        score = 32 + index * 8
        members.append({
            "user_id": str(user.id),
            "user_name": user.name or f"Mock Teammate {index + 1}",
            "user_email": user.email,
            "cbi_score": score,
            "risk_score_100": score,
            "risk_level": "medium",
            "incident_count": 1,
            "after_hours_incidents": 0,
            "weekend_incidents": 0,
            "total_activities": 1,
            "factors": {
                "workload": 2,
                "after_hours": 0,
                "weekend_work": 0,
                "incident_load": 1,
                "response_time": 1,
            },
            "metrics": {
                "avg_response_time_minutes": 5,
                "after_hours_percentage": 0,
                "weekend_percentage": 0,
            },
            "key_metrics": {
                "incidents_per_week": 0.25,
                "after_hours_percentage": 0,
                "avg_resolution_hours": 0.5,
            },
            "recommendations": [],
        })
        incidents.append({
            "id": f"local-retention-{case}-{index + 1}",
            "title": f"Synthetic retention example {index + 1}",
            "created_at": event_at.isoformat(),
            "acknowledged_at": (event_at + timedelta(minutes=5)).isoformat(),
            "resolved_at": (event_at + timedelta(minutes=30)).isoformat(),
        })

    mean_score = sum(member["cbi_score"] for member in members) / len(members)
    distribution = {"low": 0, "medium": len(members), "high": 0, "critical": 0}
    metadata: dict[str, Any] = {
        "is_demo": True,
        "total_incidents": len(incidents),
        "demo_note": "Synthetic local data for testing organization retention.",
    }
    # Source dates do not determine result retention. The legacy example is
    # unknown because its persisted result-generation timestamp is absent.
    if case != "legacy":
        metadata["date_range"] = {"start": start.isoformat(), "end": end.isoformat()}

    result = {
        "data_sources": {"incident_data": True, "github_data": False, "slack_data": False},
        "team_health": {
            "overall_score": mean_score,
            "risk_score_100": mean_score,
            "risk_distribution": distribution,
            "health_status": "fair",
        },
        "team_summary": {
            "total_users": len(members),
            "average_score": mean_score,
            "highest_score": max(member["cbi_score"] for member in members),
            "risk_distribution": distribution,
            "users_at_risk": 0,
        },
        "team_analysis": {"members": members},
        "total_incidents": len(incidents),
        "insights": [],
        "recommendations": [],
        "daily_trends": [],
        "metadata": metadata,
    }
    if case != "legacy":
        result["raw_incident_data"] = incidents
    return result


def create_fixture_data(
    db: Session,
    organization: Organization,
    owner: User,
    mock_users: Sequence[User],
    *,
    now: datetime,
    instance: str,
) -> dict[str, Any]:
    """Insert seven analyses, four surveys, and a roster; leave commit to caller.

    At a 90-day cutoff the analysis preview is 3 expired, 1 retained,
    1 unverifiable, 1 deferred, and 1 empty. Surveys are 1 expired, 2 retained,
    and 1 unverifiable. Two preserved survey links point to expired analyses.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Local retention fixtures require a timezone-aware clock")
    now = now.astimezone(timezone.utc)
    if not instance or not isinstance(instance, str):
        raise ValueError("Local retention fixtures require a non-empty instance marker")
    if len(mock_users) != 3:
        raise ValueError("Local retention fixtures require exactly three mock teammates")
    if organization.id is None or owner.id is None or any(user.id is None for user in mock_users):
        raise ValueError("Persist the organization and demo users before creating fixtures")
    if any(user.organization_id != organization.id for user in [owner, *mock_users]):
        raise ValueError("Every demo account must belong to the fixture organization")
    if len({user.id for user in [owner, *mock_users]}) != len(mock_users) + 1:
        raise ValueError("The owner and mock teammates must be distinct accounts")
    if any(not user.email.endswith((".test", ".invalid")) for user in mock_users):
        raise ValueError("Synthetic teammates must use reserved .test or .invalid email addresses")

    cases = {
        "old": "Result generated 120 days ago",
        "recent": "Fresh four-month report; old source data retained",
        "mixed": "Old generated result with historical activity",
        "legacy": "Legacy result with unknown generation date",
        "saved_old": "Saved old result; delete expired record",
        "running": "Running result; cleanup deferred",
        "empty": "Empty completed result",
    }
    analyses: dict[str, Analysis] = {}
    for index, (case, label) in enumerate(cases.items()):
        analysis = Analysis(
            organization_id=organization.id,
            user_id=owner.id,
            integration_name=f"Retention Demo · {label}",
            platform="demo",
            time_range=130 if case in {"old", "recent", "mixed", "saved_old", "running"} else 30,
            status="running" if case == "running" else "completed",
            is_saved=True,
            is_auto_refresh=False,
            auto_refresh_interval=None,
            config={
                "is_demo": True,
                "local_retention_demo": instance,
                "fixture_case": case,
            },
            results=None if case == "empty" else _result_payload(mock_users, case=case, now=now),
            created_at=now if case == "recent" else now - timedelta(hours=index + 1),
            completed_at=(now - timedelta(days=120) if case in {"old", "mixed", "saved_old"}
                          else None if case in {"running", "legacy"} else now),
            results_generated_at=(now - timedelta(days=120) if case in {"old", "mixed", "saved_old"}
                                  else now if case == "recent" else None),
        )
        db.add(analysis)
        analyses[case] = analysis
    db.flush()

    old = now - timedelta(days=120)
    recent = now - timedelta(days=10)
    survey_cases = {
        "old_linked_old": (mock_users[0], old, analyses["old"]),
        "recent_linked_mixed": (mock_users[1], recent, analyses["mixed"]),
        "unknown_linked_old": (mock_users[2], now, analyses["old"]),
        "recent_linked_recent": (mock_users[0], now - timedelta(days=5), analyses["recent"]),
    }
    surveys: dict[str, UserBurnoutReport] = {}
    for case, (user, submitted_at, analysis) in survey_cases.items():
        survey = UserBurnoutReport(
            user_id=user.id,
            organization_id=organization.id,
            email=user.email,
            email_domain=user.email.rsplit("@", 1)[-1],
            analysis_id=analysis.id,
            feeling_score=3,
            workload_score=4,
            stress_factors=["incident_volume"],
            personal_circumstances="no",
            additional_comments=f"Synthetic local retention example: {case} ({instance}).",
            submitted_via="web",
            is_anonymous=False,
            submitted_at=submitted_at,
            updated_at=now,
        )
        db.add(survey)
        surveys[case] = survey
    db.flush()
    # Explicit SQL NULL prevents the model's server-default timestamp from
    # silently turning the intentionally undated example into recent data.
    unknown = surveys["unknown_linked_old"]
    db.execute(
        update(UserBurnoutReport)
        .where(UserBurnoutReport.id == unknown.id)
        .values(submitted_at=None)
    )

    correlations = []
    for user in [owner, *mock_users]:
        correlation = UserCorrelation(
            organization_id=organization.id,
            user_id=user.id,
            name=user.name,
            email=user.email,
            email_domain=user.email.rsplit("@", 1)[-1],
            timezone="UTC",
            integration_ids=[],
            is_active=1,
            created_at=now,
            last_synced_at=now,
        )
        db.add(correlation)
        correlations.append(correlation)
    db.flush()

    return {
        "analysis_ids": {case: analysis.id for case, analysis in analyses.items()},
        "survey_ids": {case: survey.id for case, survey in surveys.items()},
        "correlation_ids": [correlation.id for correlation in correlations],
    }
