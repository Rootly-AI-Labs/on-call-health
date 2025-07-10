"""
User model for authentication and user management.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)  # Primary email
    name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)  # NULL for OAuth users
    
    # Legacy fields for backward compatibility - will be deprecated
    provider = Column(String(50), nullable=True)  # 'google', 'github', or NULL
    provider_id = Column(String(255), nullable=True)  # OAuth provider user ID
    
    is_verified = Column(Boolean, default=False)  # TRUE for OAuth users
    rootly_token = Column(Text, nullable=True)  # Encrypted Rootly API token
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    analyses = relationship("Analysis", back_populates="user")
    rootly_integrations = relationship("RootlyIntegration", back_populates="user")
    oauth_providers = relationship("OAuthProvider", back_populates="user", cascade="all, delete-orphan")
    emails = relationship("UserEmail", back_populates="user", cascade="all, delete-orphan")
    github_integrations = relationship("GitHubIntegration", back_populates="user", cascade="all, delete-orphan")
    slack_integrations = relationship("SlackIntegration", back_populates="user", cascade="all, delete-orphan")
    user_correlations = relationship("UserCorrelation", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', providers={len(self.oauth_providers)})>"
    
    @property
    def primary_oauth_provider(self):
        """Get the primary OAuth provider for this user."""
        for provider in self.oauth_providers:
            if provider.is_primary:
                return provider
        return self.oauth_providers[0] if self.oauth_providers else None
    
    @property
    def all_emails(self):
        """Get all verified emails for this user."""
        return [email.email for email in self.emails if email.is_verified]
    
    def has_provider(self, provider_name: str) -> bool:
        """Check if user has a specific OAuth provider linked."""
        return any(p.provider == provider_name for p in self.oauth_providers)
    
    @property
    def github_integration(self):
        """Get the GitHub integration for this user."""
        return self.github_integrations[0] if self.github_integrations else None
    
    @property
    def slack_integration(self):
        """Get the Slack integration for this user."""
        return self.slack_integrations[0] if self.slack_integrations else None
    
    @property
    def primary_correlation(self):
        """Get the primary user correlation for this user."""
        return self.user_correlations[0] if self.user_correlations else None
    
    def has_github_integration(self) -> bool:
        """Check if user has GitHub integration set up."""
        return len(self.github_integrations) > 0
    
    def has_slack_integration(self) -> bool:
        """Check if user has Slack integration set up."""
        return len(self.slack_integrations) > 0
    
    @property
    def connected_platforms(self) -> list:
        """Get list of all connected platforms for this user."""
        platforms = []
        if self.rootly_integrations:
            platforms.append("rootly")
        if self.github_integrations:
            platforms.append("github")
        if self.slack_integrations:
            platforms.append("slack")
        # Check for PagerDuty through correlations
        if self.user_correlations and any(c.pagerduty_user_id for c in self.user_correlations):
            platforms.append("pagerduty")
        return platforms