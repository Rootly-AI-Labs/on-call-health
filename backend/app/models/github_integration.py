"""
GitHub integration model for storing GitHub OAuth tokens and user mappings.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class GitHubIntegration(Base):
    __tablename__ = "github_integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    github_token = Column(Text, nullable=True)  # Encrypted GitHub token
    github_username = Column(String(100), nullable=False, index=True)
    organizations = Column(JSON, default=list)  # List of GitHub organizations
    token_source = Column(String(20), default="oauth")  # 'oauth' or 'manual'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="github_integrations")
    
    def __repr__(self):
        return f"<GitHubIntegration(id={self.id}, user_id={self.user_id}, username='{self.github_username}')>"
    
    @property
    def has_token(self) -> bool:
        """Check if this integration has a valid token."""
        return self.github_token is not None and len(self.github_token) > 0
    
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
    def organization_names(self) -> list:
        """Get list of organization names."""
        if isinstance(self.organizations, list):
            return self.organizations
        return []
    
    def add_organization(self, org_name: str):
        """Add an organization to the list."""
        if not isinstance(self.organizations, list):
            self.organizations = []
        if org_name not in self.organizations:
            self.organizations.append(org_name)
    
    def remove_organization(self, org_name: str):
        """Remove an organization from the list."""
        if isinstance(self.organizations, list) and org_name in self.organizations:
            self.organizations.remove(org_name)