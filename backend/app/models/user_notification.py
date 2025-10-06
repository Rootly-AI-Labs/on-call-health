"""
User notification model for organization invites, survey updates, and integration events.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime, timezone

class UserNotification(Base):
    """
    Notifications for users about invitations, surveys, integrations, etc.
    Displayed in the top-right notifications panel on integrations page.
    """
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True, index=True)

    # User targeting
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for email-only notifications
    email = Column(String(255), nullable=True)  # For unregistered users
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    # Notification content
    type = Column(String(50), nullable=False)  # 'invitation', 'survey', 'integration', 'analysis'
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)

    # Action button
    action_url = Column(String(500), nullable=True)
    action_text = Column(String(100), nullable=True)  # "Accept Invite", "Take Survey", "View Results"

    # Related records
    organization_invitation_id = Column(Integer, ForeignKey("organization_invitations.id"), nullable=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)

    # Status and priority
    status = Column(String(20), default="unread")  # 'unread', 'read', 'dismissed', 'acted'
    priority = Column(String(20), default="normal")  # 'high', 'normal', 'low'

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")
    organization = relationship("Organization")
    invitation = relationship("OrganizationInvitation")
    analysis = relationship("Analysis")

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'action_url': self.action_url,
            'action_text': self.action_text,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'organization_name': self.organization.name if self.organization else None,
            'is_expired': self.is_expired,
            'is_unread': self.is_unread
        }

    @property
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_unread(self) -> bool:
        """Check if notification is unread and not expired."""
        return self.status == 'unread' and not self.is_expired

    @property
    def icon(self) -> str:
        """Get icon name for notification type."""
        icons = {
            'invitation': '🏢',
            'survey': '📊',
            'integration': '🔗',
            'analysis': '📈',
            'welcome': '🎉',
            'reminder': '⏰'
        }
        return icons.get(self.type, '📌')

    def mark_as_read(self):
        """Mark notification as read."""
        self.status = 'read'
        self.read_at = datetime.now(timezone.utc)

    def mark_as_acted(self):
        """Mark notification as acted upon (e.g., invitation accepted)."""
        self.status = 'acted'
        self.read_at = datetime.now(timezone.utc)

    def __repr__(self):
        return f"<UserNotification(id={self.id}, type='{self.type}', user_id={self.user_id}, status='{self.status}')>"