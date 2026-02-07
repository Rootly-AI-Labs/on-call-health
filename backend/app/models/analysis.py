"""
Analysis model for storing burnout analysis results.
"""
import uuid as uuid_module
from sqlalchemy import Column, Index, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid_module.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    rootly_integration_id = Column(Integer, ForeignKey("rootly_integrations.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    
    # NEW: Store integration details directly to avoid complex matching
    integration_name = Column(String(255), nullable=True)  # "PagerDuty (Beta Access)", "Failwhale Tales", etc.
    platform = Column(String(50), nullable=True)  # "rootly", "pagerduty"
    
    time_range = Column(Integer, default=30)  # Time range in days
    status = Column(String(50), default="pending", index=True)  # pending, running, completed, failed
    config = Column(JSON, nullable=True)  # Analysis configuration (additional settings)
    results = Column(JSON, nullable=True)  # Analysis results (team scores, member details)
    error_message = Column(Text, nullable=True)  # Error details if failed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index('idx_analyses_user_created', 'user_id', created_at.desc()),
        Index('idx_analyses_org_status_created', 'organization_id', 'status', created_at.desc()),
    )

    # Relationships
    user = relationship("User", back_populates="analyses")
    organization = relationship("Organization", back_populates="analyses")
    rootly_integration = relationship("RootlyIntegration", back_populates="analyses")
    integration_mappings = relationship("IntegrationMapping", back_populates="analysis")
    
    def __repr__(self):
        return f"<Analysis(id={self.id}, user_id={self.user_id}, status='{self.status}')>"