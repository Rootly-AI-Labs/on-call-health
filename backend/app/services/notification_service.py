"""
Service for creating and managing user notifications.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from ..models import UserNotification, User, OrganizationInvitation, Analysis, Organization

class NotificationService:
    """Service for creating and managing notifications."""

    def __init__(self, db: Session):
        self.db = db

    def create_invitation_notification(self, invitation: OrganizationInvitation) -> UserNotification:
        """Create notification for organization invitation."""

        # Try to find existing user by email
        user = self.db.query(User).filter(User.email == invitation.email).first()

        notification = UserNotification(
            user_id=user.id if user else None,
            email=invitation.email,
            organization_id=invitation.organization_id,
            type='invitation',
            title=f"Invitation to join {invitation.organization.name}",
            message=f"You've been invited to join {invitation.organization.name} as a {invitation.role}.",
            action_url=f"/invitations/accept/{invitation.id}",
            action_text="Accept Invitation",
            organization_invitation_id=invitation.id,
            priority='high',
            expires_at=invitation.expires_at
        )

        self.db.add(notification)
        self.db.commit()
        return notification

    def create_invitation_accepted_notification(self, invitation: OrganizationInvitation, accepted_by: User) -> List[UserNotification]:
        """Notify org admins that someone accepted an invitation."""
        notifications = []

        # Notify org admins
        org_admins = self.db.query(User).filter(
            User.organization_id == invitation.organization_id,
            User.role.in_(['org_admin', 'super_admin'])
        ).all()

        for admin in org_admins:
            if admin.id != accepted_by.id:  # Don't notify if they accepted their own invite
                notification = UserNotification(
                    user_id=admin.id,
                    organization_id=invitation.organization_id,
                    type='integration',
                    title=f"{accepted_by.name or accepted_by.email} joined your organization",
                    message=f"{accepted_by.email} accepted the invitation and joined {invitation.organization.name}.",
                    action_url=f"/organization/members",
                    action_text="View Members",
                    priority='normal'
                )
                notifications.append(notification)
                self.db.add(notification)

        self.db.commit()
        return notifications

    def create_survey_submitted_notification(self, survey_response, analysis: Analysis) -> List[UserNotification]:
        """Notify org admins when someone submits a survey."""
        notifications = []

        # Get org admins for the analysis organization
        org_admins = self.db.query(User).filter(
            User.organization_id == analysis.organization_id,
            User.role.in_(['org_admin', 'super_admin'])
        ).all()

        for admin in org_admins:
            notification = UserNotification(
                user_id=admin.id,
                organization_id=analysis.organization_id,
                type='survey',
                title="New survey response received",
                message=f"A team member submitted their burnout survey response.",
                action_url=f"/analyses/{analysis.id}/responses",
                action_text="View Responses",
                analysis_id=analysis.id,
                priority='normal'
            )
            notifications.append(notification)
            self.db.add(notification)

        self.db.commit()
        return notifications

    def create_analysis_complete_notification(self, analysis: Analysis) -> List[UserNotification]:
        """Notify organization members when analysis is complete."""
        notifications = []

        # Notify all organization members
        org_members = self.db.query(User).filter(
            User.organization_id == analysis.organization_id
        ).all()

        for member in org_members:
            notification = UserNotification(
                user_id=member.id,
                organization_id=analysis.organization_id,
                type='analysis',
                title="Team burnout analysis complete",
                message=f"Your team's latest burnout analysis is ready to view.",
                action_url=f"/analyses/{analysis.id}",
                action_text="View Results",
                analysis_id=analysis.id,
                priority='high'
            )
            notifications.append(notification)
            self.db.add(notification)

        self.db.commit()
        return notifications

    def create_slack_connected_notification(self, user: User, workspace_name: str) -> UserNotification:
        """Notify when Slack workspace is connected."""
        notification = UserNotification(
            user_id=user.id,
            organization_id=user.organization_id,
            type='integration',
            title="Slack workspace connected",
            message=f"Successfully connected {workspace_name} to your organization.",
            action_url="/integrations",
            action_text="View Integrations",
            priority='normal'
        )

        self.db.add(notification)
        self.db.commit()
        return notification

    def create_survey_reminder_notification(self, user: User, analysis: Analysis) -> UserNotification:
        """Create reminder for pending survey."""
        notification = UserNotification(
            user_id=user.id,
            organization_id=user.organization_id,
            type='reminder',
            title="Complete your burnout survey",
            message=f"Your team's burnout analysis is waiting for your input.",
            action_url=f"/surveys/{analysis.id}",
            action_text="Take Survey",
            analysis_id=analysis.id,
            priority='high',
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )

        self.db.add(notification)
        self.db.commit()
        return notification

    def get_user_notifications(self, user: User, limit: int = 20) -> List[UserNotification]:
        """Get notifications for a user."""
        notifications = self.db.query(UserNotification).filter(
            ((UserNotification.user_id == user.id) |
             (UserNotification.email == user.email)),
            UserNotification.status != 'dismissed'
        ).order_by(
            UserNotification.priority.desc(),
            UserNotification.created_at.desc()
        ).limit(limit).all()

        return notifications

    def get_unread_count(self, user: User) -> int:
        """Get count of unread notifications for a user."""
        return self.db.query(UserNotification).filter(
            ((UserNotification.user_id == user.id) |
             (UserNotification.email == user.email)),
            UserNotification.status == 'unread'
        ).count()

    def mark_as_read(self, notification_id: int, user: User) -> bool:
        """Mark notification as read."""
        notification = self.db.query(UserNotification).filter(
            UserNotification.id == notification_id,
            ((UserNotification.user_id == user.id) |
             (UserNotification.email == user.email))
        ).first()

        if notification:
            notification.mark_as_read()
            self.db.commit()
            return True

        return False

    def mark_all_as_read(self, user: User) -> int:
        """Mark all notifications as read for a user."""
        notifications = self.db.query(UserNotification).filter(
            ((UserNotification.user_id == user.id) |
             (UserNotification.email == user.email)),
            UserNotification.status == 'unread'
        ).all()

        for notification in notifications:
            notification.mark_as_read()

        self.db.commit()
        return len(notifications)

    def dismiss_notification(self, notification_id: int, user: User) -> bool:
        """Dismiss notification."""
        notification = self.db.query(UserNotification).filter(
            UserNotification.id == notification_id,
            ((UserNotification.user_id == user.id) |
             (UserNotification.email == user.email))
        ).first()

        if notification:
            notification.status = 'dismissed'
            self.db.commit()
            return True

        return False

    def cleanup_expired_notifications(self):
        """Clean up expired notifications."""
        expired = self.db.query(UserNotification).filter(
            UserNotification.expires_at < datetime.now(timezone.utc)
        ).all()

        for notification in expired:
            notification.status = 'expired'

        self.db.commit()
        return len(expired)