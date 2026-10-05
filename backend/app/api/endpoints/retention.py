"""Read, configure, and preview the current organization's retention policy."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...auth.dependencies import get_current_active_user
from ...models import User, get_db
from ...services.data_retention import (
    RetentionPolicyResponse,
    RetentionPolicyUpdate,
    get_retention_organization,
    retention_policy_response,
    update_retention_policy,
)
from ...services.retention_preview import (
    RetentionPreviewRequest, RetentionPreviewResponse, build_retention_preview,
)

router = APIRouter()


def retention_preview_now() -> datetime:
    """Keep the preview clock injectable without allowing clients to change it."""
    return datetime.now(timezone.utc)


@router.get("", response_model=RetentionPolicyResponse)
def get_organization_retention(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Members may view the policy for their own active organization."""
    return retention_policy_response(get_retention_organization(db, current_user))


@router.put("", response_model=RetentionPolicyResponse)
def put_organization_retention(
    update: RetentionPolicyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Admins configure event-age retention; null disables the policy.

    Enabling or shortening the period requires confirm_deletion=true.
    This endpoint saves configuration; it does not execute cleanup.
    """
    return update_retention_policy(db, current_user, update)


@router.post("/preview", response_model=RetentionPreviewResponse)
def preview_organization_retention(
    request: RetentionPreviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    now: datetime = Depends(retention_preview_now),
):
    """Preview saved or proposed event-age retention without saving or deleting data.

    An empty object uses the saved policy. Explicit retention_days previews that
    proposed policy, including null for disabled. Only organization admins may preview.
    """
    with db.no_autoflush:
        organization = get_retention_organization(db, current_user, require_admin=True)
        return build_retention_preview(db, organization, request, now=now)
