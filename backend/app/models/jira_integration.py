"""
Jira integration model for storing Jira OAuth tokens and user mappings.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class JiraIntegration(Base):
    __tablename__ = "jira_integrations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # OAuth tokens (encrypted)
    access_token = Column(Text, nullable=True)  # Encrypted Jira access token
    refresh_token = Column(Text, nullable=True)  # Encrypted Jira refresh token (required - 1hr expiry)

    # Jira site info
    jira_cloud_id = Column(String(100), nullable=False, index=True)  # e.g., "f9a1b2c3-d4e5-6789-a012-bcdef3456789"
    jira_site_url = Column(String(255), nullable=False)  # e.g., "mycompany.atlassian.net"
    jira_account_id = Column(String(100), nullable=True, index=True)  # Jira user accountId
    jira_display_name = Column(String(255), nullable=True)  # User's display name in Jira
    jira_email = Column(String(255), nullable=True)  # User's email in Jira

    # Multi-site support (user can have access to multiple Jira instances)
    accessible_resources = Column(JSON, default=list)  # List of all Jira sites user has access to

    # Token metadata
    token_source = Column(String(20), default="oauth")  # 'oauth' or 'manual'
    token_expires_at = Column(DateTime(timezone=True), nullable=True)  # When access token expires

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="jira_integrations")

    def __repr__(self):
        return f"<JiraIntegration(id={self.id}, user_id={self.user_id}, site='{self.jira_site_url}')>"

    @property
    def has_token(self) -> bool:
        """Check if this integration has a valid token."""
        return self.access_token is not None and len(self.access_token) > 0

    @property
    def has_refresh_token(self) -> bool:
        """Check if this integration has a refresh token."""
        return self.refresh_token is not None and len(self.refresh_token) > 0

    @property
    def is_oauth(self) -> bool:
        """Check if this integration uses OAuth tokens."""
        return self.token_source == "oauth"

    @property
    def is_manual(self) -> bool:
        """Check if this integration uses manual tokens."""
        return self.token_source == "manual"

    @property
    def supports_refresh(self) -> bool:
        """Check if this integration supports token refresh."""
        return self.is_oauth and self.has_refresh_token

    @property
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (within 5 minutes of expiry)."""
        if not self.token_expires_at:
            return False
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        # Refresh if less than 5 minutes until expiry
        return (self.token_expires_at - now).total_seconds() < 300

    @property
    def accessible_sites(self) -> list:
        """Get list of accessible Jira sites."""
        if isinstance(self.accessible_resources, list):
            return self.accessible_resources
        return []

    def add_accessible_site(self, site_info: dict):
        """Add an accessible Jira site."""
        if not isinstance(self.accessible_resources, list):
            self.accessible_resources = []
        # Check if site already exists
        existing = next((s for s in self.accessible_resources if s.get('id') == site_info.get('id')), None)
        if not existing:
            self.accessible_resources.append(site_info)