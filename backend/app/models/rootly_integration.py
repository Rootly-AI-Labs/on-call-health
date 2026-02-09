from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class RootlyIntegration(Base):
    __tablename__ = "rootly_integrations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # User-defined name or auto-generated
    organization_name = Column(String(255), nullable=True)  # From API
    api_token = Column(Text, nullable=False)  # Encrypted API token (Rootly or PagerDuty)
    platform = Column(String(50), nullable=False, default="rootly", index=True)  # "rootly" or "pagerduty"
    total_users = Column(Integer, nullable=True)  # From API metadata
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    survey_recipients = Column(JSON, nullable=True)  # Array of UserCorrelation IDs who should receive surveys
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    cached_permissions = Column(JSON, nullable=True)  # Cached permission check results
    permissions_checked_at = Column(DateTime(timezone=True), nullable=True)  # When permissions were last checked
    last_synced_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # User who last synced
    last_synced_at = Column(DateTime(timezone=True), nullable=True)  # When last synced

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="rootly_integrations")
    synced_by_user = relationship("User", foreign_keys=[last_synced_by])
    analyses = relationship("Analysis", back_populates="rootly_integration")
    
    def __repr__(self):
        return f"<RootlyIntegration(id={self.id}, name='{self.name}', organization='{self.organization_name}')>"