"""
Survey dispatch claim model: one row per scheduled survey job occurrence.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.sql import func
from .base import Base


class SurveyDispatchClaim(Base):
    __tablename__ = "survey_dispatch_claims"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    job_kind = Column(String(20), nullable=False)
    fire_time = Column(DateTime(timezone=True), nullable=False)
    claimed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("uq_survey_dispatch_claim", "organization_id", "job_kind", "fire_time", unique=True),
        Index("idx_survey_dispatch_claims_claimed_at", "claimed_at"),
    )
