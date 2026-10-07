"""Organization retention policy storage and validation.

This module configures policies only. Cleanup and result-age enforcement
are separate implementation steps; saving a policy does not run deletion.
"""
import logging
import hmac
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..models.organization import Organization
from ..models.user import User
from .retention_legacy import (
    LegacyCleanupAuthorization, LegacyCleanupStatus, LegacyReceiptUse, cancel_legacy_authorization,
    collect_unverifiable_snapshot, legacy_cleanup_status, read_legacy_authorization,
    save_legacy_authorization, snapshot_fingerprint, validate_legacy_preview_receipt,
)
from .retention_status import RetentionCleanupStatus, cleanup_status_response

logger = logging.getLogger(__name__)

# A separate null state disables retention; zero is never interpreted as delete all.
RetentionDays = Annotated[int, Field(strict=True, ge=1, le=3650)]
POLICY_SETTINGS_KEY = "data_retention"


class RetentionPolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retention_days: RetentionDays | None
    confirm_deletion: StrictBool = False
    clear_unverifiable_analyses: StrictBool = False
    confirm_legacy_deletion: StrictBool = False
    legacy_preview_token: str | None = Field(default=None, max_length=4096)
    expected_policy_version: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class RetentionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retention_days: RetentionDays | None = None
    age_basis: Literal["analysis_generation"] = "analysis_generation"
    survey_age_basis: Literal["submission"] = "submission"
    updated_at: datetime | None = None
    updated_by_user_id: int | None = None


class RetentionPolicyResponse(BaseModel):
    organization_id: int
    policy_version: str
    retention_days: int | None
    enabled: bool
    age_basis: Literal["analysis_generation"] = "analysis_generation"
    survey_age_basis: Literal["submission"] = "submission"
    scope: list[Literal["analyses", "survey_responses"]]
    updated_at: datetime | None
    legacy_cleanup: LegacyCleanupStatus
    cleanup_status: RetentionCleanupStatus


def get_retention_organization(
    db: Session, user: User, *, for_update: bool = False, require_admin: bool = False
) -> Organization:
    """Resolve ownership from the authenticated user, never a request parameter."""
    if user.status != "active":
        raise HTTPException(status_code=403, detail="An active account is required")
    if user.organization_id is None:
        raise HTTPException(status_code=400, detail="You must be part of an organization")
    if (for_update or require_admin) and user.role != "admin":
        raise HTTPException(
            status_code=403, detail="Only organization admins can change data retention"
        )

    query = db.query(Organization).filter(Organization.id == user.organization_id)
    if for_update:
        # Preserve settings written concurrently by another policy/settings request.
        query = query.populate_existing().with_for_update()
    organization = query.first()
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if organization.status != "active":
        raise HTTPException(status_code=403, detail="An active organization is required")
    return organization


def read_retention_policy(organization: Organization) -> RetentionPolicy:
    settings = organization.settings or {}
    stored = settings.get(POLICY_SETTINGS_KEY)
    # Policies saved by the earlier event-age draft retain their configured
    # period, but follow the explicitly approved result-generation semantics.
    if isinstance(stored, dict) and stored.get("age_basis") == "event":
        stored = {**stored, "age_basis": "analysis_generation", "survey_age_basis": "submission"}
    # Existing organizations have no policy and therefore start disabled.
    return RetentionPolicy.model_validate(stored) if stored is not None else RetentionPolicy()


def retention_policy_version(organization: Organization) -> str:
    """Bind a reviewed policy to its organization and complete audit revision.

    This digest is a conditional-save identifier, not an authorization token.
    Keep unrelated organization settings and all integration secrets out of it.
    """
    encoded = json.dumps({
        "organization_id": organization.id,
        "policy": read_retention_policy(organization).model_dump(mode="json"),
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def retention_policy_response(organization: Organization) -> RetentionPolicyResponse:
    policy = read_retention_policy(organization)
    return RetentionPolicyResponse(
        organization_id=organization.id,
        policy_version=retention_policy_version(organization),
        retention_days=policy.retention_days,
        enabled=policy.retention_days is not None,
        scope=["analyses", "survey_responses"],
        updated_at=policy.updated_at,
        legacy_cleanup=legacy_cleanup_status(organization),
        cleanup_status=cleanup_status_response(organization),
    )


def update_retention_policy(
    db: Session, user: User, update: RetentionPolicyUpdate, *, now: datetime | None = None,
) -> RetentionPolicyResponse:
    organization = get_retention_organization(db, user, for_update=True)
    previous = read_retention_policy(organization)
    if update.expected_policy_version is not None and not hmac.compare_digest(
        update.expected_policy_version, retention_policy_version(organization),
    ):
        # Check under the org lock before staging policy or legacy cleanup changes.
        raise HTTPException(status_code=409, detail={
            "code": "retention_policy_changed",
            "message": "Your organization or retention policy changed. Refresh settings and review a new preview.",
        })
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Retention policy updates require a timezone-aware clock")
    now = now.astimezone(timezone.utc)
    days = update.retention_days
    if update.clear_unverifiable_analyses:
        if days is None:
            raise HTTPException(status_code=422, detail="Legacy history cleanup requires enabled retention")
        if not update.confirm_legacy_deletion:
            raise HTTPException(status_code=409, detail={
                "code": "legacy_confirmation_required",
                "message": "Separately confirm clearing analysis results whose generation dates cannot be verified.",
            })
        if not update.legacy_preview_token:
            raise HTTPException(status_code=409, detail={
                "code": "legacy_preview_required",
                "message": "Review a legacy cleanup preview before confirming this one-time clear.",
            })
    elif update.confirm_legacy_deletion or update.legacy_preview_token is not None:
        raise HTTPException(status_code=422, detail="Legacy confirmation requires clear_unverifiable_analyses=true")
    needs_confirmation = days is not None and (
        previous.retention_days is None or days < previous.retention_days
    )
    if needs_confirmation and not update.confirm_deletion:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "retention_confirmation_required",
                "message": (
                    "Enabling or shortening retention can permanently delete existing "
                    "analysis results and survey responses. Confirm this policy change."
                ),
            },
        )

    legacy_changed = False
    if update.clear_unverifiable_analyses:
        receipt = validate_legacy_preview_receipt(
            update.legacy_preview_token, organization, days, previous.updated_at, now=now,
        )
        pending = read_legacy_authorization(organization)
        if pending is not None and pending.state == "pending":
            raise HTTPException(status_code=409, detail={
                "code": "legacy_cleanup_pending",
                "message": "A confirmed legacy cleanup is already pending. Complete or cancel it before confirming another.",
            })
        entries = collect_unverifiable_snapshot(
            db, organization.id, receipt.evaluated_at - timedelta(days=days),
        )
        if len(entries) != receipt.analysis_count or not hmac.compare_digest(
            snapshot_fingerprint(entries), receipt.snapshot_fingerprint,
        ):
            raise HTTPException(status_code=409, detail={
                "code": "legacy_preview_stale",
                "message": "The analysis history changed since the preview. Review a new preview before clearing it.",
            })
        save_legacy_authorization(organization, LegacyCleanupAuthorization(
            state="pending" if entries else "completed", request_id=receipt.request_id,
            approved_at=now, approved_by_user_id=user.id, requested_count=len(entries),
            entries=entries, finished_at=None if entries else now,
            used_preview_receipts=[
                use for use in (pending.used_preview_receipts if pending is not None else [])
                if use.expires_at > now
            ] + [LegacyReceiptUse(request_id=receipt.request_id, expires_at=receipt.expires_at)],
        ))
        legacy_changed = True
    elif days is None:
        legacy_changed = cancel_legacy_authorization(organization, now=now)

    # Repeated ordinary saves preserve the policy's original audit metadata.
    if days == previous.retention_days and not legacy_changed:
        return retention_policy_response(organization)
    if days != previous.retention_days:
        policy = RetentionPolicy(
            retention_days=days, updated_at=now, updated_by_user_id=user.id,
        )
        organization.settings = {
            **(organization.settings or {}),
            POLICY_SETTINGS_KEY: policy.model_dump(mode="json"),
        }
    db.commit()
    db.refresh(organization)
    logger.info(
        "Organization %s retention changed by user %s: %s -> %s days (result generation age); legacy_action=%s",
        organization.id, user.id, previous.retention_days, days, legacy_changed,
    )
    return retention_policy_response(organization)
