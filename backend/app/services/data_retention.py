"""Organization retention policy storage and validation.

This module configures policies only. Cleanup and collection-window enforcement
are separate implementation steps; saving a policy does not run deletion.
"""
import logging
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..models.organization import Organization
from ..models.user import User

logger = logging.getLogger(__name__)

# A separate null state disables retention; zero is never interpreted as delete all.
RetentionDays = Annotated[int, Field(strict=True, ge=1, le=3650)]
POLICY_SETTINGS_KEY = "data_retention"


class RetentionPolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retention_days: RetentionDays | None
    confirm_deletion: StrictBool = False


class RetentionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retention_days: RetentionDays | None = None
    age_basis: Literal["event"] = "event"
    updated_at: datetime | None = None
    updated_by_user_id: int | None = None


class RetentionPolicyResponse(BaseModel):
    organization_id: int
    retention_days: int | None
    enabled: bool
    age_basis: Literal["event"] = "event"
    scope: list[Literal["analyses", "survey_responses"]]
    updated_at: datetime | None


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
    # Existing organizations have no policy and therefore start disabled.
    return RetentionPolicy.model_validate(stored) if stored is not None else RetentionPolicy()


def retention_policy_response(organization: Organization) -> RetentionPolicyResponse:
    policy = read_retention_policy(organization)
    return RetentionPolicyResponse(
        organization_id=organization.id,
        retention_days=policy.retention_days,
        enabled=policy.retention_days is not None,
        scope=["analyses", "survey_responses"],
        updated_at=policy.updated_at,
    )


def update_retention_policy(
    db: Session, user: User, update: RetentionPolicyUpdate
) -> RetentionPolicyResponse:
    organization = get_retention_organization(db, user, for_update=True)
    previous = read_retention_policy(organization)
    days = update.retention_days
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

    # Return unchanged state on repeated saves, preserving original audit metadata.
    if days == previous.retention_days:
        return retention_policy_response(organization)

    policy = RetentionPolicy(
        retention_days=days,
        updated_at=datetime.now(timezone.utc),
        updated_by_user_id=user.id,
    )
    organization.settings = {
        **(organization.settings or {}),
        POLICY_SETTINGS_KEY: policy.model_dump(mode="json"),
    }
    db.commit()
    db.refresh(organization)
    logger.info(
        "Organization %s retention changed by user %s: %s -> %s days (event age)",
        organization.id, user.id, previous.retention_days, days,
    )
    return retention_policy_response(organization)
