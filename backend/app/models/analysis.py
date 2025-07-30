"""
Analysis model for storing burnout analysis results.
"""
import uuid
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    # uuid = Column(String(36), unique=True, index=True, nullable=True, default=lambda: str(uuid.uuid4()))  # Commented until Railway migration
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rootly_integration_id = Column(Integer, ForeignKey("rootly_integrations.id"), nullable=True)
    time_range = Column(Integer, default=30)  # Time range in days
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    config = Column(JSON, nullable=True)  # Analysis configuration (additional settings)
    results = Column(JSON, nullable=True)  # Analysis results (team scores, member details)
    error_message = Column(Text, nullable=True)  # Error details if failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="analyses")
    rootly_integration = relationship("RootlyIntegration", back_populates="analyses")
    integration_mappings = relationship("IntegrationMapping", back_populates="analysis")
    
    def __repr__(self):
        return f"<Analysis(id={self.id}, user_id={self.user_id}, status='{self.status}')>"