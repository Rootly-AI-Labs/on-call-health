"""Transactional organization cleanup; scheduling is intentionally separate.

The caller supplies a dedicated session: this operation commits on success and
rolls back on failure. Organization locks serialize policy changes, result writes,
and cleanup. Unknown-age data is skipped unless an admin explicitly approved an
unchanged analysis snapshot; survey age remains independent of that approval.
No application endpoint invokes this service yet.
"""
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import (
    Analysis, IntegrationMapping, Organization, SurveyPeriod,
    UserBurnoutReport, UserNotification, WeeklyDigestLog,
)
from .data_retention import read_retention_policy
from .retention_preview import (
    _batches, _event_time, _related_counts, classify_analysis_result, is_manually_saved_analysis,
)
from .retention_legacy import (
    finish_legacy_cleanup, fingerprint_analysis_result, pending_legacy_entries,
)
from .retention_status import policy_and_legacy_revision, record_cleanup_success

logger = logging.getLogger(__name__)


class RetentionScopeConflict(RuntimeError):
    """A dependency cannot safely be attributed to the target organization."""


@dataclass
class RetentionCleanupResult:
    organization_id: int
    enabled: bool
    cutoff_at: datetime | None
    policy_updated_at: datetime | None
    analysis_results_expired: int = 0
    legacy_analysis_results_cleared: int = 0
    legacy_analyses_skipped: int = 0
    legacy_analyses_deferred: int = 0
    survey_responses_deleted: int = 0
    survey_links_cleared: int = 0
    survey_period_links_cleared: int = 0
    mappings_deleted: int = 0
    notifications_deleted: int = 0
    digest_links_cleared: int = 0
    analyses_unverifiable: int = 0
    analyses_deferred: int = 0
    surveys_unverifiable: int = 0


def _invalidate_retention_caches(db: Session, organization_id: int, analysis_ids: list[int]) -> None:
    """Evict scoped result copies before committing; cache failure aborts cleanup.

    Clear every scoped key, including stale keys for already-empty results. API
    response caches contain current integration rosters, not historical events.
    Retention-enabled analysis reads bypass Redis and check persisted eligibility,
    preventing an in-flight cache writer from making expired results accessible.
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return
    import redis

    client = redis.from_url(redis_url, socket_connect_timeout=5, socket_timeout=5)
    client.ping()
    batch = []
    for (analysis_id,) in db.query(Analysis.id).filter(
        Analysis.organization_id == organization_id
    ).yield_per(100):
        batch.append(f"analysis_data:{analysis_id}")
        if len(batch) == 100:
            client.delete(*batch)
            batch = []
    if batch:
        client.delete(*batch)


def _lock_retention_dependencies(db, analysis_ids, response_ids):
    """Keep ownership checks stable even if an existing reference is repaired.

    Parent row locks already prevent new foreign-key references. Explicit child
    locks also prevent organization IDs from changing between check and delete.
    Digest links follow the parent analysis's organization, independently of
    the recipient's current membership.
    """
    for batch in _batches(analysis_ids):
        for model in (IntegrationMapping, UserNotification, UserBurnoutReport):
            query = db.query(model.id).filter(model.analysis_id.in_(batch)).order_by(model.id).with_for_update()
            for _ in query.yield_per(100):
                pass
        query = db.query(WeeklyDigestLog.id).filter(
            WeeklyDigestLog.analysis_id.in_(batch)
        ).order_by(WeeklyDigestLog.id).with_for_update()
        for _ in query.yield_per(100):
            pass
    for batch in _batches(response_ids):
        query = db.query(SurveyPeriod.id).filter(SurveyPeriod.response_id.in_(batch)).order_by(
            SurveyPeriod.id,
        ).with_for_update()
        for _ in query.yield_per(100):
            pass


def cleanup_organization_data(
    db: Session, organization_id: int, *, now: datetime, invalidate_cache=None, completion_clock=None,
) -> RetentionCleanupResult:
    """Apply the saved policy atomically, deleting expired manual saved rows.

    Unknown-age analyses clear only under a snapshot-bound admin approval. Active
    unchanged approved snapshots remain pending. Unknown-age surveys remain.
    Built-in sample reports are excluded by the shared classifier, including
    from prior unknown-date approvals; deliberate retention test fixtures are not.
    Auto-refresh and unsaved configurations survive result expiry. Prior legacy
    approvals authorize content clearing only, not deletion of configuration.
    References with missing or different ownership abort the whole organization
    transaction. Cache eviction can precede a rollback, which is harmless; no
    successful outcome is reported before the database commit succeeds.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Retention cleanup requires a timezone-aware clock")
    now = now.astimezone(timezone.utc)
    try:
        organization = db.query(Organization).populate_existing().filter(
            Organization.id == organization_id, Organization.status == "active",
        ).with_for_update().one_or_none()
        if organization is None:
            raise ValueError("Active retention organization not found")
        policy = read_retention_policy(organization)
        policy_version, legacy_request_id = policy_and_legacy_revision(organization)
        cutoff = now - timedelta(days=policy.retention_days) if policy.retention_days is not None else None
        result = RetentionCleanupResult(
            organization_id=organization_id, enabled=cutoff is not None,
            cutoff_at=cutoff, policy_updated_at=policy.updated_at,
        )
        if cutoff is None:
            db.commit()
            return result

        expired_analysis_ids = []
        expired_saved_analysis_ids = []
        legacy_analysis_ids = []
        pending_entries = pending_legacy_entries(organization)
        remaining_entries = []
        seen_approved_ids = set()
        for analysis in db.query(Analysis).populate_existing().filter(
            Analysis.organization_id == organization_id
        ).order_by(Analysis.id).with_for_update().yield_per(1):
            eligibility = classify_analysis_result(analysis, cutoff)
            if eligibility.disposition == "expired":
                expired_analysis_ids.append(analysis.id)
                if is_manually_saved_analysis(analysis):
                    expired_saved_analysis_ids.append(analysis.id)
            elif eligibility.disposition == "unverifiable":
                result.analyses_unverifiable += 1
            elif eligibility.disposition == "deferred":
                result.analyses_deferred += 1

            approved_entry = pending_entries.get(analysis.id)
            if approved_entry is None:
                continue
            seen_approved_ids.add(analysis.id)
            if fingerprint_analysis_result(analysis) != approved_entry.result_fingerprint:
                result.legacy_analyses_skipped += 1
            elif eligibility.disposition == "deferred":
                remaining_entries.append(approved_entry)
                result.legacy_analyses_deferred += 1
            elif eligibility.disposition == "unverifiable":
                legacy_analysis_ids.append(analysis.id)
            else:
                # Normal result-generation expiry needs no legacy authorization. Results
                # now retained/empty similarly fall outside this one-time clear.
                result.legacy_analyses_skipped += 1
        result.legacy_analyses_skipped += len(set(pending_entries) - seen_approved_ids)

        expired_response_ids = []
        for response_id, submitted_at in db.query(
            UserBurnoutReport.id, UserBurnoutReport.submitted_at
        ).filter(UserBurnoutReport.organization_id == organization_id).with_for_update().yield_per(100):
            submitted = _event_time(submitted_at)
            if submitted is None:
                result.surveys_unverifiable += 1
            elif submitted < cutoff:
                expired_response_ids.append(response_id)

        affected_analysis_ids = expired_analysis_ids + legacy_analysis_ids
        _lock_retention_dependencies(db, affected_analysis_ids, expired_response_ids)
        related = _related_counts(db, organization_id, affected_analysis_ids, expired_response_ids, cutoff)
        if related.references_requiring_review:
            raise RetentionScopeConflict("Retention dependencies have missing or different organization ownership")
        (invalidate_cache or _invalidate_retention_caches)(db, organization_id, affected_analysis_ids)

        for batch in _batches(affected_analysis_ids):
            # Every surviving response, including an unknown-age response, keeps
            # its content and loses only the expired result link.
            result.survey_links_cleared += db.query(UserBurnoutReport).filter(
                UserBurnoutReport.organization_id == organization_id,
                UserBurnoutReport.analysis_id.in_(batch),
                or_(UserBurnoutReport.submitted_at >= cutoff, UserBurnoutReport.submitted_at.is_(None)),
            ).update({UserBurnoutReport.analysis_id: None}, synchronize_session="fetch")
            result.mappings_deleted += db.query(IntegrationMapping).filter(
                IntegrationMapping.organization_id == organization_id,
                IntegrationMapping.analysis_id.in_(batch),
            ).delete(synchronize_session="fetch")
            result.notifications_deleted += db.query(UserNotification).filter(
                UserNotification.organization_id == organization_id,
                UserNotification.analysis_id.in_(batch),
            ).delete(synchronize_session="fetch")
            scoped_analysis_ids = db.query(Analysis.id).filter(Analysis.organization_id == organization_id)
            result.digest_links_cleared += db.query(WeeklyDigestLog).filter(
                WeeklyDigestLog.analysis_id.in_(scoped_analysis_ids), WeeklyDigestLog.analysis_id.in_(batch),
            ).update({WeeklyDigestLog.analysis_id: None}, synchronize_session="fetch")
            db.query(Analysis).filter(
                Analysis.organization_id == organization_id, Analysis.id.in_(batch),
            ).update({Analysis.results: None, Analysis.error_message: None,
                      Analysis.error_generated_at: None}, synchronize_session="fetch")

        result.analysis_results_expired = len(expired_analysis_ids)
        result.legacy_analysis_results_cleared = len(legacy_analysis_ids)

        for batch in _batches(expired_response_ids):
            result.survey_period_links_cleared += db.query(SurveyPeriod).filter(
                SurveyPeriod.organization_id == organization_id, SurveyPeriod.response_id.in_(batch),
            ).update({SurveyPeriod.response_id: None}, synchronize_session="fetch")
            result.survey_responses_deleted += db.query(UserBurnoutReport).filter(
                UserBurnoutReport.organization_id == organization_id, UserBurnoutReport.id.in_(batch),
            ).delete(synchronize_session="fetch")
        # Old linked surveys must be deleted before their parent rows, while
        # newer/undated surveys and digest history have already been detached.
        # All writes, including full saved-record deletion, share one transaction.
        for batch in _batches(expired_saved_analysis_ids):
            db.query(Analysis).filter(
                Analysis.organization_id == organization_id, Analysis.id.in_(batch),
                Analysis.is_saved.is_(True), Analysis.is_auto_refresh.is_(False),
            ).delete(synchronize_session="fetch")
        finish_legacy_cleanup(
            organization, remaining_entries=remaining_entries,
            cleared_count=result.legacy_analysis_results_cleared,
            skipped_count=result.legacy_analyses_skipped, now=now,
        )
        record_cleanup_success(
            organization, result, started_at=now,
            finished_at=completion_clock() if completion_clock else now,
            policy_version=policy_version, legacy_request_id=legacy_request_id,
        )
        db.commit()
        logger.info(
            "Retention cleanup org=%s analysis_results=%s legacy_cleared=%s legacy_skipped=%s legacy_deferred=%s surveys=%s unverified_analyses=%s deferred=%s",
            organization_id, result.analysis_results_expired,
            result.legacy_analysis_results_cleared, result.legacy_analyses_skipped,
            result.legacy_analyses_deferred, result.survey_responses_deleted,
            result.analyses_unverifiable, result.analyses_deferred,
        )
        return result
    except Exception:
        db.rollback()
        raise
