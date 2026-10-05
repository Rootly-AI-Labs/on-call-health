"""Read-only event-age eligibility shared by retention previews and future cleanup.

An old event is sufficient to expire a whole result. Recent sampled events alone
are insufficient to prove that its aggregate scores contain no older inputs.
"""
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models import (
    Analysis, IntegrationMapping, Organization, RootlyIntegration, SurveyPeriod, User,
    UserBurnoutReport, UserNotification, WeeklyDigestLog,
)
from .data_retention import RetentionDays, read_retention_policy

SAMPLE_LIMIT = 100
QUERY_BATCH_SIZE = 500
Disposition = Literal["expired", "retained", "unverifiable", "deferred", "empty"]
_DATE_KEY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EVENT_CONTAINERS = {
    "raw_incident_data", "incidents", "commits", "messages", "daily_trends",
    "survey_responses", "surveys", "responses",
}
_EVENT_KEYS = {
    "created_at", "started_at", "occurred_at", "committed_at", "submitted_at",
    "timestamp", "date", "ts",
}
_UNVERIFIED_SOURCE_FLAGS = (
    "include_github", "include_slack", "include_jira", "include_linear", "include_ai_usage",
)
_ENRICHMENT_PAYLOAD_KEYS = {
    "jira_tickets", "linear_issues", "jira_metrics", "linear_metrics",
    "github_activity", "slack_activity", "github_metrics", "slack_metrics",
    "github_burnout_breakdown", "github_insights", "slack_insights",
    "openai_usage", "anthropic_usage", "openai_usage_per_user",
}


class RetentionPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    retention_days: RetentionDays | None = None


class AnalysisPreviewCounts(BaseModel):
    total: int = 0
    expired: int = 0
    retained: int = 0
    unverifiable: int = 0
    deferred: int = 0
    empty: int = 0
    regeneration_candidates: int = 0


class SurveyPreviewCounts(BaseModel):
    total: int = 0
    expired: int = 0
    retained: int = 0
    unverifiable: int = 0


class RelatedPreviewCounts(BaseModel):
    analysis_mappings: int = 0
    analysis_notifications: int = 0
    survey_links_to_clear: int = 0
    survey_period_links_to_clear: int = 0
    digest_links_to_clear: int = 0
    references_requiring_review: int = 0


class AnalysisPreviewSample(BaseModel):
    analysis_id: int
    disposition: Disposition
    oldest_event_at: datetime | None
    reason: str
    is_saved: bool
    is_auto_refresh: bool


class RetentionPreviewResponse(BaseModel):
    organization_id: int
    preview_only: Literal[True] = True
    policy_source: Literal["saved", "proposed"]
    retention_days: int | None
    enabled: bool
    evaluated_at: datetime
    cutoff_at: datetime | None
    policy_updated_at: datetime | None
    analyses: AnalysisPreviewCounts
    survey_responses: SurveyPreviewCounts
    related_records: RelatedPreviewCounts
    samples: list[AnalysisPreviewSample]
    samples_truncated: bool
    warnings: list[str]


@dataclass(frozen=True)
class AnalysisEligibility:
    disposition: Disposition
    oldest_event_at: datetime | None
    reason: str


def _event_time(value) -> datetime | None:
    """Accept ISO dates/aware timestamps; never guess a naive timestamp's zone."""
    try:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, date):
            # Local day buckets can start as early as UTC+14. Use that earliest
            # possible instant rather than falsely retaining an overlapping bucket.
            parsed = datetime.combine(value, time.min, tzinfo=timezone.utc) - timedelta(hours=14)
        elif isinstance(value, str) and _DATE_KEY.fullmatch(value):
            parsed = datetime.combine(date.fromisoformat(value), time.min, tzinfo=timezone.utc) - timedelta(hours=14)
        elif isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            return None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _collect_event_evidence(results: dict) -> tuple[list[datetime], bool, bool]:
    """Return known event bounds, verified primary coverage, and uncertainty.

    Coverage ranges and event collections are recognized explicitly. User profile
    timestamps, analysis timestamps and ticket due dates are not event-age evidence.
    Date-keyed metrics use the earliest possible local day start as a lower bound.
    """
    evidence: list[datetime] = []
    uncertain = False
    primary_coverage = False

    def add(value, *, slack_ts=False):
        nonlocal uncertain
        if slack_ts:
            try:
                if isinstance(value, bool):
                    raise ValueError("A boolean is not a Slack event timestamp")
                parsed = datetime.fromtimestamp(float(value), tz=timezone.utc)
            except (TypeError, ValueError, OverflowError, OSError):
                parsed = None
        else:
            parsed = _event_time(value)
        if parsed is None:
            uncertain = True
        else:
            evidence.append(parsed)
        return parsed

    def walk(value, path=()):
        nonlocal uncertain, primary_coverage
        if isinstance(value, list):
            for entry in value:
                walk(entry, path)
            return
        if not isinstance(value, dict):
            return

        # Read each event's own fields/attributes, avoiding nested user timestamps.
        if path and path[-1] in _EVENT_CONTAINERS:
            attrs = value.get("attributes")
            event = attrs if isinstance(attrs, dict) else value
            found = False
            for key in _EVENT_KEYS:
                if key in event and event[key] is not None:
                    add(event[key], slack_ts=key == "ts")
                    found = True
            if not found:
                uncertain = True

        for key, entry in value.items():
            if key == "date_range":
                if isinstance(entry, dict):
                    start = _event_time(entry.get("start", entry.get("start_date")))
                    end = _event_time(entry.get("end", entry.get("end_date")))
                    valid = start is not None and end is not None and start <= end
                    if not valid:
                        uncertain = True
                    else:
                        evidence.append(start)
                        if path in (("metadata",), ("partial_data", "metadata")):
                            primary_coverage = True
                else:
                    uncertain = True
            elif path == ("metadata",) and key == "alerts" and isinstance(entry, dict):
                start = _event_time(entry.get("start"))
                end = _event_time(entry.get("end"))
                if start is not None and end is not None and start <= end:
                    evidence.append(start)
                elif entry.get("start") is not None or entry.get("end") is not None:
                    uncertain = True
            elif isinstance(key, str) and _DATE_KEY.fullmatch(key):
                add(key)
            # Preserve the container context only for an event's own attributes;
            # arbitrary fields such as nested responders are traversed separately.
            walk(entry, path + (key,))

    walk(results)
    return evidence, primary_coverage, uncertain


def _has_enrichment_payload(value) -> bool:
    """Missing inclusion flags do not prove that legacy results lack enrichment."""
    def populated(entry):
        if isinstance(entry, dict):
            return any(populated(item) for item in entry.values())
        if isinstance(entry, list):
            return any(populated(item) for item in entry)
        return entry is not None and entry != "" and entry != 0 and entry is not False

    if isinstance(value, list):
        return any(_has_enrichment_payload(entry) for entry in value)
    if isinstance(value, dict):
        return any(
            (key in _ENRICHMENT_PAYLOAD_KEYS and populated(entry)) or _has_enrichment_payload(entry)
            for key, entry in value.items()
        )
    return False


def classify_analysis_result(analysis: Analysis, cutoff: datetime) -> AnalysisEligibility:
    """Evaluate a complete result without using its database creation timestamp."""
    if analysis.status in ("pending", "running"):
        return AnalysisEligibility("deferred", None, "active_analysis")
    results = analysis.results
    if results is None or results == {} or results == "":
        return AnalysisEligibility("empty", None, "no_result_data")
    if isinstance(results, str):
        try:
            results = json.loads(results)
        except (ValueError, TypeError):
            return AnalysisEligibility("unverifiable", None, "invalid_result_data")
    if not isinstance(results, dict):
        return AnalysisEligibility("unverifiable", None, "invalid_result_data")
    if not results:
        return AnalysisEligibility("empty", None, "no_result_data")

    evidence, primary_coverage, uncertain = _collect_event_evidence(results)
    oldest = min(evidence) if evidence else None
    if oldest is not None and oldest < cutoff:
        return AnalysisEligibility("expired", oldest, "event_before_cutoff")

    # Legacy enrichment collectors do not reliably record aggregate provenance.
    metadata = results.get("metadata") or {}
    config = analysis.config or {}
    enrichment = any(
        isinstance(source, dict) and any(source.get(flag) for flag in _UNVERIFIED_SOURCE_FLAGS)
        for source in (metadata, config)
    )
    if enrichment or _has_enrichment_payload(results):
        return AnalysisEligibility("unverifiable", oldest, "unverified_source_coverage")
    if uncertain:
        return AnalysisEligibility("unverifiable", oldest, "invalid_event_timestamp")
    if not primary_coverage:
        return AnalysisEligibility("unverifiable", oldest, "missing_event_coverage")
    return AnalysisEligibility("retained", oldest, "within_event_window")


def _batches(ids):
    for offset in range(0, len(ids), QUERY_BATCH_SIZE):
        yield ids[offset:offset + QUERY_BATCH_SIZE]


def _related_counts(db, org_id, analysis_ids, response_ids, cutoff):
    counts = RelatedPreviewCounts()
    for batch in _batches(analysis_ids):
        for model, name in (
            (IntegrationMapping, "analysis_mappings"),
            (UserNotification, "analysis_notifications"),
        ):
            query = db.query(model).filter(model.analysis_id.in_(batch))
            setattr(counts, name, getattr(counts, name) + query.filter(model.organization_id == org_id).count())
            counts.references_requiring_review += query.filter(
                or_(model.organization_id.is_(None), model.organization_id != org_id)
            ).count()
        surveys = db.query(UserBurnoutReport).filter(UserBurnoutReport.analysis_id.in_(batch))
        counts.survey_links_to_clear += surveys.filter(
            UserBurnoutReport.organization_id == org_id,
            or_(UserBurnoutReport.submitted_at >= cutoff, UserBurnoutReport.submitted_at.is_(None)),
        ).count()
        counts.references_requiring_review += surveys.filter(
            or_(UserBurnoutReport.organization_id.is_(None), UserBurnoutReport.organization_id != org_id)
        ).count()
        digests = db.query(WeeklyDigestLog).join(User, WeeklyDigestLog.user_id == User.id).filter(
            WeeklyDigestLog.analysis_id.in_(batch)
        )
        counts.digest_links_to_clear += digests.filter(User.organization_id == org_id).count()
        counts.references_requiring_review += digests.filter(
            or_(User.organization_id.is_(None), User.organization_id != org_id)
        ).count()
    for batch in _batches(response_ids):
        periods = db.query(SurveyPeriod).filter(SurveyPeriod.response_id.in_(batch))
        counts.survey_period_links_to_clear += periods.filter(SurveyPeriod.organization_id == org_id).count()
        counts.references_requiring_review += periods.filter(SurveyPeriod.organization_id != org_id).count()
    return counts


def build_retention_preview(
    db: Session, organization: Organization, request: RetentionPreviewRequest, *, now: datetime
) -> RetentionPreviewResponse:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Retention preview requires a timezone-aware clock")
    now = now.astimezone(timezone.utc)
    policy = read_retention_policy(organization)
    proposed = "retention_days" in request.model_fields_set
    days = request.retention_days if proposed else policy.retention_days
    cutoff = now - timedelta(days=days) if days is not None else None
    analysis_counts = AnalysisPreviewCounts()
    survey_counts = SurveyPreviewCounts()
    samples = []
    expired_analysis_ids = []
    expired_response_ids = []
    analyses = db.query(Analysis).filter(Analysis.organization_id == organization.id)
    surveys = db.query(UserBurnoutReport).filter(UserBurnoutReport.organization_id == organization.id)

    if cutoff is None:
        analysis_counts.total = analyses.count()
        survey_counts.total = surveys.count()
    else:
        # Result JSON can exceed 30 MB; never prefetch 100 payloads at once.
        for analysis in analyses.order_by(Analysis.id).yield_per(1):
            eligibility = classify_analysis_result(analysis, cutoff)
            analysis_counts.total += 1
            name = eligibility.disposition
            setattr(analysis_counts, name, getattr(analysis_counts, name) + 1)
            if name == "expired":
                expired_analysis_ids.append(analysis.id)
            if len(samples) < SAMPLE_LIMIT:
                samples.append(AnalysisPreviewSample(
                    analysis_id=analysis.id, disposition=name,
                    oldest_event_at=eligibility.oldest_event_at, reason=eligibility.reason,
                    is_saved=bool(analysis.is_saved), is_auto_refresh=bool(analysis.is_auto_refresh),
                ))
        for response_id, submitted_at in surveys.with_entities(
            UserBurnoutReport.id, UserBurnoutReport.submitted_at
        ).yield_per(100):
            survey_counts.total += 1
            event_at = _event_time(submitted_at)
            if event_at is None:
                survey_counts.unverifiable += 1
            elif event_at < cutoff:
                survey_counts.expired += 1
                expired_response_ids.append(response_id)
            else:
                survey_counts.retained += 1

    for batch in _batches(expired_analysis_ids):
        analysis_counts.regeneration_candidates += db.query(Analysis).join(
            RootlyIntegration, RootlyIntegration.id == Analysis.rootly_integration_id
        ).filter(
            Analysis.id.in_(batch),
            RootlyIntegration.user_id == Analysis.user_id,
            RootlyIntegration.is_active.is_(True),
            func.length(func.trim(RootlyIntegration.api_token)) > 0,
        ).count()
    related = _related_counts(db, organization.id, expired_analysis_ids, expired_response_ids, cutoff)
    warnings = []
    if cutoff is not None:
        warnings.append("Entire expired results include their scores and insights; regeneration must use only retained events.")
        warnings.append("Date-only buckets use the earliest possible local day start (UTC+14); overlapping days can expire conservatively.")
        if analysis_counts.regeneration_candidates:
            warnings.append("Regeneration candidates have an active integration configured; provider access and regeneration are not guaranteed.")
    if analysis_counts.unverifiable or survey_counts.unverifiable:
        warnings.append("Some event ages or source coverage cannot be verified; these records require review before enforcement.")
    if analysis_counts.deferred:
        warnings.append("Running or pending analyses are deferred; their results must respect retention when stored.")
    if related.references_requiring_review:
        warnings.append("Linked records have missing or different organization ownership and require review before deletion.")
    return RetentionPreviewResponse(
        organization_id=organization.id, policy_source="proposed" if proposed else "saved",
        retention_days=days, enabled=days is not None, evaluated_at=now, cutoff_at=cutoff,
        policy_updated_at=policy.updated_at, analyses=analysis_counts, survey_responses=survey_counts,
        related_records=related, samples=samples,
        samples_truncated=cutoff is not None and analysis_counts.total > SAMPLE_LIMIT,
        warnings=warnings,
    )
