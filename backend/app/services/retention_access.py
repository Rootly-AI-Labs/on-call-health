"""Retention lookups shared by HTTP readers and background workers."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models import Organization
from .data_retention import read_retention_policy


class RetentionOrganizationMissing(ValueError):
    """The record names an organization that no longer exists."""


def organization_retention_cutoff(
    db: Session, organization_id: int | None, *, lock: bool = False,
    now: datetime | None = None,
) -> datetime | None:
    if organization_id is None:
        return None
    query = db.query(Organization).filter(Organization.id == organization_id).populate_existing()
    if lock:
        query = query.with_for_update(read=True)
    organization = query.first()
    if organization is None:
        raise RetentionOrganizationMissing("Analysis organization no longer exists")
    days = read_retention_policy(organization).retention_days
    return (now or datetime.now(timezone.utc)) - timedelta(days=days) if days is not None else None
