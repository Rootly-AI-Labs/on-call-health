"""
Helpers for automated survey recipient selection.

Scheduled Slack surveys run at the organization level, so the selected
recipient list needs an organization-scoped source of truth.
"""
from typing import Optional
import logging

from sqlalchemy.orm import Session

from ..models.rootly_integration import RootlyIntegration
from ..models.slack_workspace_mapping import SlackWorkspaceMapping
from ..models.user import User

logger = logging.getLogger(__name__)


def get_active_workspace_mapping_for_org(
    db: Session,
    organization_id: Optional[int]
) -> Optional[SlackWorkspaceMapping]:
    """Return the most recently registered active Slack workspace for an org."""
    if not organization_id:
        return None

    return (
        db.query(SlackWorkspaceMapping)
        .filter(
            SlackWorkspaceMapping.organization_id == organization_id,
            SlackWorkspaceMapping.status == "active"
        )
        .order_by(
            SlackWorkspaceMapping.registered_at.desc(),
            SlackWorkspaceMapping.id.desc()
        )
        .first()
    )


def get_saved_recipient_ids_for_org(
    db: Session,
    organization_id: Optional[int]
) -> Optional[set[int]]:
    """
    Load the saved automated-survey recipients for an organization.

    New selections are stored on the active Slack workspace mapping. We keep a
    fallback to legacy Rootly integration rows so existing selections continue
    to work until every org saves through the new path.
    """
    if not organization_id:
        return None

    workspace_mapping = get_active_workspace_mapping_for_org(db, organization_id)
    if workspace_mapping and workspace_mapping.survey_recipients is not None:
        recipient_ids = workspace_mapping.survey_recipients or []
        return set(recipient_ids) if recipient_ids else None

    integrations = (
        db.query(RootlyIntegration)
        .join(User, User.id == RootlyIntegration.user_id)
        .filter(
            User.organization_id == organization_id,
            RootlyIntegration.platform == "rootly",
            RootlyIntegration.is_active == True,
            RootlyIntegration.survey_recipients.isnot(None)
        )
        .order_by(
            RootlyIntegration.last_synced_at.desc().nullslast(),
            RootlyIntegration.last_used_at.desc().nullslast(),
            RootlyIntegration.created_at.desc(),
            RootlyIntegration.id.desc()
        )
        .all()
    )

    if not integrations:
        return None

    if len(integrations) > 1:
        logger.info(
            "Found %s legacy integrations with saved survey recipients for org %s; using integration %s",
            len(integrations),
            organization_id,
            integrations[0].id,
        )

    recipient_ids = integrations[0].survey_recipients or []
    return set(recipient_ids) if recipient_ids else None


def save_survey_recipient_ids_for_org(
    db: Session,
    organization_id: Optional[int],
    recipient_ids: Optional[list[int]]
) -> Optional[SlackWorkspaceMapping]:
    """
    Persist the organization-wide automated-survey recipient selection.

    Passing ``None`` resets back to the default behavior of sending to all
    eligible Slack-linked users.
    """
    workspace_mapping = get_active_workspace_mapping_for_org(db, organization_id)
    if not workspace_mapping:
        return None

    workspace_mapping.survey_recipients = recipient_ids if recipient_ids else None
    return workspace_mapping
