"""Read-only result-generation eligibility shared by preview and cleanup.

A report can contain any requested historical window. Its stored snapshot expires
N days after generation; survey responses retain their separate submission age.
"""
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models import (
    Analysis, IntegrationMapping, Organization, RootlyIntegration, SurveyPeriod, User,
    UserBurnoutReport, UserNotification, WeeklyDigestLog,
)
from .data_retention import RetentionDays, read_retention_policy
from .retention_legacy import (
    LegacyAnalysisEntry, create_legacy_preview_receipt,
    fingerprint_analysis_result, pending_legacy_entries,
)

SAMPLE_LIMIT = 100
QUERY_BATCH_SIZE = 500
Disposition = Literal["expired", "retained", "unverifiable", "deferred", "empty", "excluded"]
_DATE_KEY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class RetentionPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    retention_days: RetentionDays | None = None
    clear_unverifiable_analyses: StrictBool = False


class AnalysisPreviewCounts(BaseModel):
    total: int = 0
    excluded: int = 0
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
    generation_at: datetime | None
    reason: str
    is_saved: bool
    is_auto_refresh: bool
    will_clear_as_legacy: bool = False


class LegacyCleanupPreview(BaseModel):
    requested: bool = False
    analysis_candidates: int = 0
    pending_analyses: int = 0
    unverifiable_surveys: int = 0
    preview_token: str | None = None
    preview_expires_at: datetime | None = None


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
    legacy_cleanup: LegacyCleanupPreview = Field(default_factory=LegacyCleanupPreview)


@dataclass(frozen=True)
class AnalysisEligibility:
    disposition: Disposition
    generation_at: datetime | None
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


def result_generation_time(analysis: Analysis) -> datetime | None:
    """Trust the stored snapshot stamp, with successful legacy completion fallback.

    Never infer report generation from row creation, source events or JSON fields.
    A failed run's completion timestamp cannot renew an older result snapshot.
    """
    value = getattr(analysis, "results_generated_at", None)
    if value is None and analysis.status == "completed":
        value = analysis.completed_at
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        return None
    return value.astimezone(timezone.utc)


def is_retention_exempt_demo(analysis: Analysis) -> bool:
    """Identify server-created sample reports, never real integrated results.

    Deliberate local retention fixtures remain eligible to exercise cleanup.
    Do not trust display names, source JSON or truthy values as demo markers.
    """
    config = getattr(analysis, "config", None)
    return (
        isinstance(config, dict)
        and config.get("is_demo") is True
        and getattr(analysis, "rootly_integration_id", None) is None
        and not config.get("local_retention_demo")
    )


def error_generation_time(analysis: Analysis) -> datetime | None:
    """Use only the stored error-content stamp, independent of run attempts."""
    value = getattr(analysis, "error_generated_at", None)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        return None
    return value.astimezone(timezone.utc)


def is_manually_saved_analysis(analysis: Analysis) -> bool:
    """Manual saved reports expire completely; recurring setup must survive."""
    return getattr(analysis, "is_saved", False) is True and getattr(analysis, "is_auto_refresh", False) is False


def classify_analysis_result(analysis: Analysis, cutoff: datetime) -> AnalysisEligibility:
    """Expire a whole stored result by generation age, independent of its inputs."""
    if is_retention_exempt_demo(analysis):
        return AnalysisEligibility("excluded", None, "mock_demo_analysis")
    if analysis.status in ("pending", "running"):
        return AnalysisEligibility("deferred", None, "active_analysis")
    results = analysis.results
    if results is None or results == {} or results == "":
        if getattr(analysis, "error_message", None):
            error_at = error_generation_time(analysis)
            if error_at is None:
                return AnalysisEligibility("unverifiable", None, "missing_error_generation_time")
            if error_at < cutoff:
                return AnalysisEligibility("expired", error_at, "error_generated_before_cutoff")
            return AnalysisEligibility("retained", error_at, "within_error_retention_period")
        # Earlier cleanup kept the row and its canonical snapshot timestamp.
        # Remove that expired saved entry too, without assigning an age to
        # configurations that never generated a result.
        if is_manually_saved_analysis(analysis) and getattr(analysis, "results_generated_at", None) is not None:
            generated = result_generation_time(analysis)
            if generated is not None and generated < cutoff:
                return AnalysisEligibility("expired", generated, "cleared_saved_result_before_cutoff")
        return AnalysisEligibility("empty", None, "no_result_data")
    generated = result_generation_time(analysis)
    if generated is None:
        return AnalysisEligibility("unverifiable", None, "missing_result_generation_time")
    if generated < cutoff:
        return AnalysisEligibility("expired", generated, "result_generated_before_cutoff")
    return AnalysisEligibility("retained", generated, "within_result_retention_period")


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
    if request.clear_unverifiable_analyses and cutoff is None:
        raise HTTPException(status_code=422, detail="Legacy analysis cleanup requires an enabled retention period")
    analysis_counts = AnalysisPreviewCounts()
    survey_counts = SurveyPreviewCounts()
    samples = []
    expired_analysis_ids = []
    legacy_analysis_ids = []
    legacy_preview_entries = []
    pending_entries = pending_legacy_entries(organization) if cutoff is not None else {}
    legacy_preview = LegacyCleanupPreview(
        requested=request.clear_unverifiable_analyses,
        pending_analyses=len(pending_entries),
    )
    expired_response_ids = []
    analyses = db.query(Analysis).filter(Analysis.organization_id == organization.id)
    surveys = db.query(UserBurnoutReport).filter(UserBurnoutReport.organization_id == organization.id)

    # Result JSON can exceed 30 MB; disabled previews need only identity/config.
    preview_analyses = analyses if cutoff is not None else analyses.with_entities(
        Analysis.id, Analysis.config, Analysis.rootly_integration_id,
    )
    for analysis in preview_analyses.order_by(Analysis.id).yield_per(1):
        if is_retention_exempt_demo(analysis):
            analysis_counts.excluded += 1
            continue
        analysis_counts.total += 1
        if cutoff is not None:
            eligibility = classify_analysis_result(analysis, cutoff)
            name = eligibility.disposition
            setattr(analysis_counts, name, getattr(analysis_counts, name) + 1)
            if name == "expired":
                expired_analysis_ids.append(analysis.id)
            will_clear_as_legacy = False
            if name == "unverifiable" and (
                request.clear_unverifiable_analyses or analysis.id in pending_entries
            ):
                fingerprint = fingerprint_analysis_result(analysis)
                entry = pending_entries.get(analysis.id)
                if request.clear_unverifiable_analyses or (
                    entry is not None and entry.result_fingerprint == fingerprint
                ):
                    will_clear_as_legacy = True
                    legacy_analysis_ids.append(analysis.id)
                if request.clear_unverifiable_analyses:
                    legacy_preview_entries.append(LegacyAnalysisEntry(
                        analysis_id=analysis.id, result_fingerprint=fingerprint,
                    ))
            if len(samples) < SAMPLE_LIMIT:
                samples.append(AnalysisPreviewSample(
                    analysis_id=analysis.id, disposition=name,
                    generation_at=eligibility.generation_at, reason=eligibility.reason,
                    is_saved=bool(analysis.is_saved), is_auto_refresh=bool(analysis.is_auto_refresh),
                    will_clear_as_legacy=will_clear_as_legacy,
                ))
    if cutoff is None:
        survey_counts.total = surveys.count()
    else:
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

    legacy_preview.analysis_candidates = len(legacy_analysis_ids)
    legacy_preview.unverifiable_surveys = survey_counts.unverifiable
    if request.clear_unverifiable_analyses:
        legacy_preview.preview_token, legacy_preview.preview_expires_at = create_legacy_preview_receipt(
            organization, days, policy.updated_at, legacy_preview_entries, now=now,
        )
    affected_analysis_ids = expired_analysis_ids + legacy_analysis_ids
    for batch in _batches(affected_analysis_ids):
        analysis_counts.regeneration_candidates += db.query(Analysis).join(
            RootlyIntegration, RootlyIntegration.id == Analysis.rootly_integration_id
        ).filter(
            Analysis.id.in_(batch),
            or_(Analysis.is_saved.is_(False), Analysis.is_auto_refresh.is_(True),
                Analysis.id.in_(legacy_analysis_ids)),
            RootlyIntegration.user_id == Analysis.user_id,
            RootlyIntegration.is_active.is_(True),
            func.length(func.trim(RootlyIntegration.api_token)) > 0,
        ).count()
    related = _related_counts(db, organization.id, affected_analysis_ids, expired_response_ids, cutoff)
    warnings = []
    if cutoff is not None:
        warnings.append("Entire expired results include imported activity, historical metrics, scores and insights. Regeneration starts a new retention period and can use the requested historical window.")
        warnings.append("Expired manually saved analyses are deleted, including their configuration and metadata. Auto-refresh configuration is preserved.")
        if analysis_counts.regeneration_candidates:
            warnings.append("Regeneration candidates have an active integration configured; provider access and regeneration are not guaranteed.")
    if analysis_counts.unverifiable or survey_counts.unverifiable:
        warnings.append("Some analysis generation dates or survey submission dates cannot be verified. Ordinary retention preserves those records rather than guessing their age.")
    if request.clear_unverifiable_analyses:
        warnings.append("Legacy cleanup clears only the unchanged analysis results in this preview after explicit confirmation; it does not authorize future unknown-age results.")
    elif legacy_preview.analysis_candidates:
        warnings.append("Previously approved unchanged legacy analysis results are included in cleanup; new or changed unknown-age results remain outside that approval.")
    if legacy_preview.unverifiable_surveys:
        warnings.append("Survey responses without reliable submission dates are preserved. Newer responses survive and lose only their links to cleared results.")
    if analysis_counts.deferred:
        warnings.append("Running or pending analyses are deferred; newly stored results start their retention period when generated.")
    if related.references_requiring_review:
        warnings.append("Linked records have missing or different organization ownership and require review before deletion.")
    return RetentionPreviewResponse(
        organization_id=organization.id, policy_source="proposed" if proposed else "saved",
        retention_days=days, enabled=days is not None, evaluated_at=now, cutoff_at=cutoff,
        policy_updated_at=policy.updated_at, analyses=analysis_counts, survey_responses=survey_counts,
        related_records=related, samples=samples,
        samples_truncated=cutoff is not None and analysis_counts.total > SAMPLE_LIMIT,
        warnings=warnings,
        legacy_cleanup=legacy_preview,
    )
