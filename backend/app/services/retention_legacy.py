"""Explicit, snapshot-bound authorization for clearing unverifiable history.

Preview receipts contain counts and an aggregate fingerprint, never result data.
Confirmed entries are stored separately from the rolling retention policy. They
authorize only those unchanged results, not future unknown-age analysis data.
"""
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from ..core.config import settings
from ..models import Analysis, Organization

LEGACY_SETTINGS_KEY = "data_retention_legacy_cleanup"
PREVIEW_LIFETIME = timedelta(minutes=15)
Count = Annotated[StrictInt, Field(ge=0)]
Fingerprint = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
RequestId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]


class LegacyAnalysisEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_id: Annotated[StrictInt, Field(ge=1)]
    result_fingerprint: Fingerprint


class LegacyReceiptUse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: RequestId
    expires_at: datetime


class LegacyCleanupAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["pending", "completed", "cancelled"]
    request_id: RequestId
    approved_at: datetime
    approved_by_user_id: Annotated[StrictInt, Field(ge=1)]
    requested_count: Count
    entries: list[LegacyAnalysisEntry] = Field(default_factory=list)
    cleared_count: Count = 0
    skipped_count: Count = 0
    cancelled_count: Count = 0
    finished_at: datetime | None = None
    used_preview_receipts: list[LegacyReceiptUse] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_authorization(self):
        _utc(self.approved_at)
        if self.finished_at is not None:
            _utc(self.finished_at)
        ids = [entry.analysis_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("Legacy authorization contains duplicate analyses")
        accounted = len(ids) + self.cleared_count + self.skipped_count + self.cancelled_count
        if accounted > self.requested_count:
            raise ValueError("Legacy authorization counts exceed the reviewed snapshot")
        if self.state == "pending" and (not ids or accounted != self.requested_count or self.finished_at is not None):
            raise ValueError("Pending legacy authorization has inconsistent entries")
        if self.state != "pending" and (ids or self.finished_at is None):
            raise ValueError("Finished legacy authorization must have no remaining entries")
        if self.state == "completed" and accounted != self.requested_count:
            raise ValueError("Completed legacy authorization has inconsistent counts")
        if self.state != "cancelled" and self.cancelled_count:
            raise ValueError("Only cancelled legacy authorization can have cancelled entries")
        if self.state == "cancelled" and accounted != self.requested_count:
            raise ValueError("Cancelled legacy authorization has inconsistent counts")
        receipt_ids = [receipt.request_id for receipt in self.used_preview_receipts]
        if len(receipt_ids) != len(set(receipt_ids)):
            raise ValueError("Legacy authorization contains duplicate preview receipts")
        for receipt in self.used_preview_receipts:
            _utc(receipt.expires_at)
        return self


class LegacyCleanupStatus(BaseModel):
    state: Literal["none", "pending", "completed", "cancelled"] = "none"
    requested_count: int = 0
    pending_count: int = 0
    cleared_count: int = 0
    skipped_count: int = 0
    cancelled_count: int = 0
    approved_at: datetime | None = None
    finished_at: datetime | None = None


class LegacyPreviewReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purpose: Literal["organization_retention_legacy_preview"]
    request_id: RequestId
    organization_id: Annotated[StrictInt, Field(ge=1)]
    retention_days: Annotated[StrictInt, Field(ge=1, le=3650)]
    policy_updated_at: str | None
    evaluated_at: datetime
    snapshot_fingerprint: Fingerprint
    analysis_count: Count
    expires_at: datetime


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Legacy cleanup requires a timezone-aware clock")
    return value.astimezone(timezone.utc)


def _version_time(value):
    if isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None:
        value = value.astimezone(timezone.utc)
    return value.isoformat() if isinstance(value, datetime) else value


def fingerprint_analysis_result(analysis: Analysis) -> str:
    """Include generation timestamps so a regenerated result is never approved.

    Status is deliberately excluded: a running job may still carry an unchanged
    old snapshot, which must be deferred rather than treating it as a new result.
    Configuration is preserved and is not authorized for deletion.
    """
    payload = {
        "retention_basis": "analysis_generation_v2",
        "results": analysis.results,
        "error_message": analysis.error_message,
        "created_at": _version_time(analysis.created_at),
        "completed_at": _version_time(analysis.completed_at),
        "results_generated_at": _version_time(getattr(analysis, "results_generated_at", None)),
    }
    # Preserve existing receipts for unchanged snapshots with no error stamp.
    # A newly dated/replaced error must invalidate approval of the old content.
    error_at = getattr(analysis, "error_generated_at", None)
    if error_at is not None:
        payload["error_generated_at"] = _version_time(error_at)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def snapshot_fingerprint(entries: list[LegacyAnalysisEntry]) -> str:
    digest = hashlib.sha256()
    for entry in sorted(entries, key=lambda item: item.analysis_id):
        digest.update(f"{entry.analysis_id}:{entry.result_fingerprint}\n".encode("ascii"))
    return digest.hexdigest()


def read_legacy_authorization(organization: Organization) -> LegacyCleanupAuthorization | None:
    stored = (organization.settings or {}).get(LEGACY_SETTINGS_KEY)
    return LegacyCleanupAuthorization.model_validate(stored) if stored is not None else None


def legacy_cleanup_status(organization: Organization) -> LegacyCleanupStatus:
    authorization = read_legacy_authorization(organization)
    if authorization is None:
        return LegacyCleanupStatus()
    return LegacyCleanupStatus(
        state=authorization.state, requested_count=authorization.requested_count,
        pending_count=len(authorization.entries) if authorization.state == "pending" else 0,
        cleared_count=authorization.cleared_count, skipped_count=authorization.skipped_count,
        cancelled_count=authorization.cancelled_count,
        approved_at=authorization.approved_at, finished_at=authorization.finished_at,
    )


def pending_legacy_entries(organization: Organization) -> dict[int, LegacyAnalysisEntry]:
    authorization = read_legacy_authorization(organization)
    if authorization is None or authorization.state != "pending":
        return {}
    return {entry.analysis_id: entry for entry in authorization.entries}


def _signing_key() -> str:
    # Separate these receipts from authentication tokens even when the app uses
    # the same underlying deployment secret.
    return hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        b"on-call-health:organization-retention-generation-preview:v2", hashlib.sha256,
    ).hexdigest()


def create_legacy_preview_receipt(
    organization: Organization, retention_days: int, policy_updated_at: datetime | None,
    entries: list[LegacyAnalysisEntry], *, now: datetime,
) -> tuple[str, datetime]:
    now = _utc(now)
    receipt = LegacyPreviewReceipt(
        purpose="organization_retention_legacy_preview", request_id=uuid4().hex,
        organization_id=organization.id, retention_days=retention_days,
        policy_updated_at=_version_time(policy_updated_at), evaluated_at=now,
        snapshot_fingerprint=snapshot_fingerprint(entries), analysis_count=len(entries),
        expires_at=now + PREVIEW_LIFETIME,
    )
    return jwt.encode(receipt.model_dump(mode="json"), _signing_key(), algorithm="HS256"), receipt.expires_at


def _confirmation_error(code, message):
    return HTTPException(status_code=409, detail={"code": code, "message": message})


def validate_legacy_preview_receipt(
    token: str, organization: Organization, retention_days: int,
    policy_updated_at: datetime | None, *, now: datetime,
) -> LegacyPreviewReceipt:
    now = _utc(now)
    try:
        payload = jwt.decode(token, _signing_key(), algorithms=["HS256"])
        receipt = LegacyPreviewReceipt.model_validate(payload)
        evaluated, expires = _utc(receipt.evaluated_at), _utc(receipt.expires_at)
    except (JWTError, ValueError, TypeError) as exc:
        raise _confirmation_error("legacy_preview_invalid", "The legacy cleanup preview is invalid. Review a new preview.") from exc
    if now < evaluated or now >= expires or expires - evaluated != PREVIEW_LIFETIME:
        raise _confirmation_error("legacy_preview_expired", "The legacy cleanup preview expired. Review a new preview.")
    previous = read_legacy_authorization(organization)
    if previous is not None and (
        previous.request_id == receipt.request_id or any(
            use.request_id == receipt.request_id and _utc(use.expires_at) > now
            for use in previous.used_preview_receipts
        )
    ):
        raise _confirmation_error("legacy_preview_already_used", "This legacy cleanup preview has already been confirmed.")
    if (
        receipt.organization_id != organization.id or receipt.retention_days != retention_days
        or receipt.policy_updated_at != _version_time(policy_updated_at)
    ):
        raise _confirmation_error("legacy_preview_stale", "The organization or retention policy changed. Review a new preview.")
    return receipt


def collect_unverifiable_snapshot(db, organization_id: int, cutoff: datetime) -> list[LegacyAnalysisEntry]:
    from .retention_preview import classify_analysis_result

    entries = []
    for analysis in db.query(Analysis).populate_existing().filter(
        Analysis.organization_id == organization_id,
    ).order_by(Analysis.id).with_for_update().yield_per(1):
        if classify_analysis_result(analysis, cutoff).disposition == "unverifiable":
            entries.append(LegacyAnalysisEntry(
                analysis_id=analysis.id, result_fingerprint=fingerprint_analysis_result(analysis),
            ))
    return entries


def save_legacy_authorization(organization: Organization, authorization: LegacyCleanupAuthorization):
    authorization = LegacyCleanupAuthorization.model_validate(authorization.model_dump())
    organization.settings = {
        **(organization.settings or {}),
        LEGACY_SETTINGS_KEY: authorization.model_dump(mode="json"),
    }


def cancel_legacy_authorization(organization: Organization, *, now: datetime) -> bool:
    authorization = read_legacy_authorization(organization)
    if authorization is None or authorization.state != "pending":
        return False
    save_legacy_authorization(organization, authorization.model_copy(update={
        "state": "cancelled", "entries": [], "finished_at": _utc(now),
        "cancelled_count": len(authorization.entries),
    }))
    return True


def finish_legacy_cleanup(
    organization: Organization, *, remaining_entries: list[LegacyAnalysisEntry],
    cleared_count: int, skipped_count: int, now: datetime,
):
    """Stage consumption inside cleanup's database transaction, never commit here."""
    authorization = read_legacy_authorization(organization)
    if authorization is None or authorization.state != "pending":
        return
    if type(cleared_count) is not int or type(skipped_count) is not int or min(cleared_count, skipped_count) < 0:
        raise ValueError("Legacy cleanup progress counts must be nonnegative integers")
    approved = {entry.analysis_id: entry.result_fingerprint for entry in authorization.entries}
    if any(approved.get(entry.analysis_id) != entry.result_fingerprint for entry in remaining_entries):
        raise ValueError("Legacy cleanup cannot expand the approved snapshot")
    if cleared_count + skipped_count != len(authorization.entries) - len(remaining_entries):
        raise ValueError("Legacy cleanup progress must account for each consumed entry")
    save_legacy_authorization(organization, authorization.model_copy(update={
        "entries": remaining_entries,
        "state": "pending" if remaining_entries else "completed",
        "cleared_count": authorization.cleared_count + cleared_count,
        "skipped_count": authorization.skipped_count + skipped_count,
        "finished_at": None if remaining_entries else _utc(now),
    }))
