"""
Slack integration model for storing Slack OAuth tokens and workspace mappings.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class SlackIntegration(Base):
    __tablename__ = "slack_integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    slack_token = Column(Text, nullable=True)  # Encrypted Slack token
    slack_user_id = Column(String(20), nullable=True)  # Slack user ID (e.g., U01234567) - nullable for bot tokens
    workspace_id = Column(String(20), nullable=False)  # Slack workspace/team ID
    webhook_url = Column(Text, nullable=True)  # Slack webhook URL for posting messages
    token_source = Column(String(20), default="oauth")  # 'oauth' or 'manual'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="slack_integrations")
    
    def __repr__(self):
        return f"<SlackIntegration(id={self.id}, user_id={self.user_id}, slack_user_id='{self.slack_user_id}', workspace='{self.workspace_id}')>"
    
    @property
    def has_token(self) -> bool:
        """Check if this integration has a valid token."""
        return self.slack_token is not None and len(self.slack_token) > 0
    
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
        return self.is_oauth  # Only OAuth tokens can be refreshed
    
    @property
    def slack_mention(self) -> str:
        """Get the Slack mention format for this user."""
        return f"<@{self.slack_user_id}>"