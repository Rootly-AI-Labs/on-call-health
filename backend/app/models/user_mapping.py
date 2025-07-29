"""
User mapping model for manual platform correlations.
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class UserMapping(Base):
    __tablename__ = "user_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Source platform identification (where the user comes from)
    source_platform = Column(String(50), nullable=False)  # "rootly", "pagerduty"
    source_identifier = Column(String(255), nullable=False)  # email, name, user_id
    
    # Target platform mapping (where we want to map to)
    target_platform = Column(String(50), nullable=False)  # "github", "slack"
    target_identifier = Column(String(255), nullable=False)  # username, user_id, handle
    
    # Mapping metadata
    mapping_type = Column(String(50), default="manual")  # "manual", "auto_detected", "verified"
    confidence_score = Column(Float, nullable=True)  # For auto-detected mappings (0.0-1.0)
    last_verified = Column(DateTime, nullable=True)  # When mapping was last verified to work
    
    # Audit trail
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="user_mappings_owned")
    creator = relationship("User", foreign_keys=[created_by], back_populates="user_mappings_created")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('ix_user_mapping_source', 'user_id', 'source_platform', 'source_identifier'),
        Index('ix_user_mapping_target', 'user_id', 'target_platform'),
        Index('ix_user_mapping_lookup', 'source_platform', 'source_identifier', 'target_platform'),
    )
    
    def __repr__(self):
        return f"<UserMapping({self.source_platform}:{self.source_identifier} -> {self.target_platform}:{self.target_identifier})>"
    
    @property
    def mapping_key(self) -> str:
        """Unique key for this mapping."""
        return f"{self.source_platform}:{self.source_identifier} -> {self.target_platform}"
    
    @property
    def is_verified(self) -> bool:
        """Check if mapping has been verified recently (within 30 days)."""
        if not self.last_verified:
            return False
        from datetime import datetime, timedelta
        return self.last_verified > datetime.now() - timedelta(days=30)
    
    @property
    def status(self) -> str:
        """Get human-readable status."""
        if self.mapping_type == "manual":
            return "verified" if self.is_verified else "manual"
        elif self.mapping_type == "auto_detected":
            if self.is_verified:
                return "verified"
            elif self.confidence_score and self.confidence_score > 0.8:
                return "high_confidence"
            elif self.confidence_score and self.confidence_score > 0.5:
                return "medium_confidence"
            else:
                return "low_confidence"
        return "unknown"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "source_platform": self.source_platform,
            "source_identifier": self.source_identifier,
            "target_platform": self.target_platform,
            "target_identifier": self.target_identifier,
            "mapping_type": self.mapping_type,
            "confidence_score": self.confidence_score,
            "last_verified": self.last_verified.isoformat() if self.last_verified else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status": self.status,
            "is_verified": self.is_verified,
            "mapping_key": self.mapping_key
        }
    
    @classmethod
    def create_manual_mapping(
        cls,
        user_id: int,
        source_platform: str,
        source_identifier: str,
        target_platform: str,
        target_identifier: str,
        created_by: int
    ):
        """Create a new manual mapping."""
        return cls(
            user_id=user_id,
            source_platform=source_platform,
            source_identifier=source_identifier,
            target_platform=target_platform,
            target_identifier=target_identifier,
            mapping_type="manual",
            created_by=created_by,
            last_verified=func.now()  # Manual mappings are considered verified on creation
        )
    
    @classmethod
    def create_auto_detected_mapping(
        cls,
        user_id: int,
        source_platform: str,
        source_identifier: str,
        target_platform: str,
        target_identifier: str,
        confidence_score: float,
        created_by: int
    ):
        """Create a new auto-detected mapping."""
        return cls(
            user_id=user_id,
            source_platform=source_platform,
            source_identifier=source_identifier,
            target_platform=target_platform,
            target_identifier=target_identifier,
            mapping_type="auto_detected",
            confidence_score=confidence_score,
            created_by=created_by
        )