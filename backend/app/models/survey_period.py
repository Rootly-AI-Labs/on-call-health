"""
Survey period model for tracking survey delivery and follow-up reminders.
"""
from datetime import date, datetime
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class SurveyPeriod(Base):
    """
    Tracks survey periods for follow-up reminders.

    Each period represents the timeframe a user has to respond to a survey:
    - Daily: period is a single day
    - Weekday: period is Monday-Friday of current week
    - Weekly: period is 7 days starting from the schedule's day_of_week
    """
    __tablename__ = "survey_periods"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_correlation_id = Column(Integer, ForeignKey("user_correlations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    email = Column(String(255), nullable=False)

    # Period configuration
    frequency_type = Column(String(20), nullable=False)  # 'daily', 'weekday', 'weekly'
    period_start_date = Column(Date, nullable=False)
    period_end_date = Column(Date, nullable=False)

    # Status tracking
    status = Column(String(20), default='pending', nullable=False)  # 'pending', 'completed', 'expired'
    initial_sent_at = Column(DateTime(timezone=True), nullable=False)
    last_reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    reminder_count = Column(Integer, default=0)

    # Response linking
    response_id = Column(Integer, ForeignKey("user_burnout_reports.id"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", backref="survey_periods")
    user_correlation = relationship("UserCorrelation", backref="survey_periods")
    user = relationship("User", backref="survey_periods")
    response = relationship("UserBurnoutReport", backref="survey_period")

    def mark_completed(self, response_id: int) -> None:
        """Mark this period as completed with the given response."""
        self.status = 'completed'
        self.response_id = response_id
        self.completed_at = datetime.utcnow()

    def mark_expired(self) -> None:
        """Mark this period as expired (user didn't respond in time)."""
        self.status = 'expired'
        self.expired_at = datetime.utcnow()

    def record_reminder_sent(self) -> None:
        """Record that a follow-up reminder was sent."""
        self.last_reminder_sent_at = datetime.utcnow()
        self.reminder_count = (self.reminder_count or 0) + 1

    @property
    def is_active(self) -> bool:
        """Check if this period is still active (pending and within date range)."""
        if self.status != 'pending':
            return False
        today = date.today()
        return self.period_start_date <= today <= self.period_end_date

    @property
    def is_expired(self) -> bool:
        """Check if this period has passed its end date."""
        return date.today() > self.period_end_date

    @property
    def days_remaining(self) -> int:
        """Days left in the period (0 if expired or completed)."""
        if self.status != 'pending':
            return 0
        today = date.today()
        if today > self.period_end_date:
            return 0
        return (self.period_end_date - today).days

    @property
    def period_name(self) -> str:
        """Human-readable period name for messages ('day' or 'week')."""
        if self.frequency_type == 'daily':
            return 'day'
        if self.frequency_type in ('weekday', 'weekly'):
            return 'week'
        return 'period'

    @property
    def frequency_display(self) -> str:
        """Human-readable frequency for messages."""
        return self.frequency_type or 'daily'

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'user_correlation_id': self.user_correlation_id,
            'user_id': self.user_id,
            'email': self.email,
            'frequency_type': self.frequency_type,
            'period_start_date': self.period_start_date.isoformat() if self.period_start_date else None,
            'period_end_date': self.period_end_date.isoformat() if self.period_end_date else None,
            'status': self.status,
            'initial_sent_at': self.initial_sent_at.isoformat() if self.initial_sent_at else None,
            'last_reminder_sent_at': self.last_reminder_sent_at.isoformat() if self.last_reminder_sent_at else None,
            'reminder_count': self.reminder_count,
            'response_id': self.response_id,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'expired_at': self.expired_at.isoformat() if self.expired_at else None,
            'is_active': self.is_active,
            'days_remaining': self.days_remaining,
            'period_name': self.period_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<SurveyPeriod(id={self.id}, email='{self.email}', "
            f"status='{self.status}', frequency='{self.frequency_type}', "
            f"period={self.period_start_date} to {self.period_end_date})>"
        )
