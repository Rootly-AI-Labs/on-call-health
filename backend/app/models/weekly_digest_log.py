"""
Weekly digest log model for tracking email sends.
"""
from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.sql import func
from .base import Base


class WeeklyDigestLog(Base):
    __tablename__ = "weekly_digest_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="SET NULL"), nullable=True)
    week_start_date = Column(Date, nullable=False, index=True)
    timezone = Column(String(50), nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("uq_weekly_digest_user_week", "user_id", "week_start_date", unique=True),
        Index("idx_weekly_digest_user_sent_at", "user_id", "sent_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<WeeklyDigestLog(id={self.id}, user_id={self.user_id}, "
            f"week_start_date={self.week_start_date})>"
        )
