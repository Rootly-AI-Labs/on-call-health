"""
Jira workspace mapping model for correlating Jira sites to organizations.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class JiraWorkspaceMapping(Base):
    """
    Maps Jira sites (cloud instances) to specific organizations/users.
    Ensures multi-tenant isolation for Jira data collection.
    """
    __tablename__ = "jira_workspace_mappings"

    id = Column(Integer, primary_key=True, index=True)

    # Jira site info
    jira_cloud_id = Column(String(100), nullable=False, unique=True)  # Unique Jira cloud ID
    jira_site_url = Column(String(255), nullable=False)  # e.g., "mycompany.atlassian.net"
    jira_site_name = Column(String(255), nullable=True)  # Friendly name of the Jira site

    # Organization mapping
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who connected
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)  # Organization reference

    # Project configuration - which projects to monitor
    project_keys = Column(JSON, default=list)  # e.g., ["ENG", "OPS", "PRODUCT"]
    monitored_boards = Column(JSON, default=list)  # Optional: specific board IDs to monitor

    # Registration tracking
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    registered_via = Column(String(20), default="oauth")  # "oauth", "manual", "admin"

    # Status
    status = Column(String(20), default="active")  # "active", "suspended", "pending"

    # Feature flags - what capabilities are enabled for this workspace
    collection_enabled = Column(Boolean, default=True)  # Enable data collection
    workload_metrics_enabled = Column(Boolean, default=True)  # Calculate workload metrics
    sprint_tracking_enabled = Column(Boolean, default=False)  # Track sprint data

    # OAuth scopes granted
    granted_scopes = Column(String(500), nullable=True)  # Space-separated list of OAuth scopes

    # Last collection metadata
    last_collection_at = Column(DateTime(timezone=True), nullable=True)
    last_collection_status = Column(String(50), nullable=True)  # "success", "partial", "failed"

    # Relationships
    owner = relationship("User", back_populates="owned_jira_workspaces")
    organization = relationship("Organization", back_populates="jira_workspace_mappings")

    # Constraints
    __table_args__ = (
        UniqueConstraint('jira_cloud_id', name='unique_jira_cloud_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'jira_cloud_id': self.jira_cloud_id,
            'jira_site_url': self.jira_site_url,
            'jira_site_name': self.jira_site_name,
            'owner_user_id': self.owner_user_id,
            'organization_id': self.organization_id,
            'project_keys': self.project_keys,
            'registered_at': self.registered_at.isoformat() if self.registered_at else None,
            'status': self.status,
            'collection_enabled': self.collection_enabled,
            'workload_metrics_enabled': self.workload_metrics_enabled,
            'sprint_tracking_enabled': self.sprint_tracking_enabled,
            'granted_scopes': self.granted_scopes,
            'last_collection_at': self.last_collection_at.isoformat() if self.last_collection_at else None,
            'last_collection_status': self.last_collection_status
        }

    @property
    def is_active(self) -> bool:
        return self.status == 'active'

    @property
    def has_projects_configured(self) -> bool:
        """Check if projects are configured for monitoring."""
        return isinstance(self.project_keys, list) and len(self.project_keys) > 0

    def add_project(self, project_key: str):
        """Add a project key to monitor."""
        if not isinstance(self.project_keys, list):
            self.project_keys = []
        if project_key.upper() not in [pk.upper() for pk in self.project_keys]:
            self.project_keys.append(project_key.upper())

    def remove_project(self, project_key: str):
        """Remove a project key from monitoring."""
        if isinstance(self.project_keys, list):
            self.project_keys = [pk for pk in self.project_keys if pk.upper() != project_key.upper()]

    def __repr__(self):
        return f"<JiraWorkspaceMapping(jira_cloud_id='{self.jira_cloud_id}', site='{self.jira_site_url}', owner_user_id={self.owner_user_id})>"