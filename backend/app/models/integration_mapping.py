"""
Integration mapping model for tracking successful and failed user mapping attempts.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class IntegrationMapping(Base):
    __tablename__ = "integration_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)  # Track which analysis this was from
    
    # Source platform (where we got the identifier from)
    source_platform = Column(String(50), nullable=False)  # "rootly", "pagerduty"
    source_identifier = Column(String(255), nullable=False)  # email, name, etc.
    
    # Target platform (what we're trying to map to)
    target_platform = Column(String(50), nullable=False)  # "github", "slack"
    target_identifier = Column(String(255), nullable=True)  # username, user_id if successful
    
    # Mapping result
    mapping_successful = Column(Boolean, nullable=False, default=False)
    mapping_method = Column(String(100), nullable=True)  # "manual_mapping", "api_search", "email_lookup", etc.
    error_message = Column(Text, nullable=True)  # Error details if failed
    
    # Metadata
    data_collected = Column(Boolean, nullable=False, default=False)  # Whether we successfully collected data
    data_points_count = Column(Integer, nullable=True)  # Number of data points collected (commits, messages, etc.)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="integration_mappings")
    analysis = relationship("Analysis", back_populates="integration_mappings")
    
    def __repr__(self):
        status = "✓" if self.mapping_successful else "✗"
        return f"<IntegrationMapping({status} {self.source_platform}:{self.source_identifier} -> {self.target_platform}:{self.target_identifier})>"
    
    @property
    def mapping_key(self) -> str:
        """Unique key for this mapping attempt."""
        return f"{self.source_platform}:{self.source_identifier} -> {self.target_platform}"
    
    @property
    def success_rate_key(self) -> str:
        """Key for calculating success rates."""
        return f"{self.source_platform} -> {self.target_platform}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "source_platform": self.source_platform,
            "source_identifier": self.source_identifier,
            "target_platform": self.target_platform,
            "target_identifier": self.target_identifier,
            "mapping_successful": self.mapping_successful,
            "mapping_method": self.mapping_method,
            "error_message": self.error_message,
            "data_collected": self.data_collected,
            "data_points_count": self.data_points_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "mapping_key": self.mapping_key
        }