-- Migration: Add survey_periods table for daily follow-up reminders
-- Description: Creates survey_periods table to track when surveys are pending/completed/expired
--              and adds follow-up reminder settings to survey_schedules

-- ============================================================================
-- Add new columns to survey_schedules
-- ============================================================================
ALTER TABLE survey_schedules
ADD COLUMN IF NOT EXISTS follow_up_reminders_enabled BOOLEAN DEFAULT TRUE;

ALTER TABLE survey_schedules
ADD COLUMN IF NOT EXISTS follow_up_message_template VARCHAR(500);

COMMENT ON COLUMN survey_schedules.follow_up_reminders_enabled IS 'Whether to send daily follow-up reminders until user responds';
COMMENT ON COLUMN survey_schedules.follow_up_message_template IS 'Custom message template for follow-up reminders';

-- ============================================================================
-- Create survey_periods table
-- ============================================================================
CREATE TABLE IF NOT EXISTS survey_periods (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    user_correlation_id INTEGER NOT NULL REFERENCES user_correlations(id),
    user_id INTEGER REFERENCES users(id),
    email VARCHAR(255) NOT NULL,

    -- Period configuration
    frequency_type VARCHAR(20) NOT NULL,  -- 'daily', 'weekday', 'weekly'
    period_start_date DATE NOT NULL,
    period_end_date DATE NOT NULL,

    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,  -- 'pending', 'completed', 'expired'
    initial_sent_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_reminder_sent_at TIMESTAMP WITH TIME ZONE,
    reminder_count INTEGER DEFAULT 0,

    -- Response linking
    response_id INTEGER REFERENCES user_burnout_reports(id),
    completed_at TIMESTAMP WITH TIME ZONE,
    expired_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes for survey_periods
-- ============================================================================

-- For querying pending periods by organization
CREATE INDEX IF NOT EXISTS idx_survey_periods_org_status
ON survey_periods(organization_id, status);

-- For querying pending periods by email
CREATE INDEX IF NOT EXISTS idx_survey_periods_email_status
ON survey_periods(email, status);

-- For date-based queries
CREATE INDEX IF NOT EXISTS idx_survey_periods_period_dates
ON survey_periods(period_start_date, period_end_date);

-- For finding periods by user correlation
CREATE INDEX IF NOT EXISTS idx_survey_periods_user_correlation
ON survey_periods(user_correlation_id, status);

-- Unique constraint: only one pending period per user per organization at a time
-- This prevents duplicate pending periods
CREATE UNIQUE INDEX IF NOT EXISTS uq_survey_periods_pending_user_org
ON survey_periods(organization_id, user_correlation_id)
WHERE status = 'pending';

-- Add CHECK constraint for status values
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'check_survey_period_status'
    ) THEN
        ALTER TABLE survey_periods
        ADD CONSTRAINT check_survey_period_status
        CHECK (status IN ('pending', 'completed', 'expired'));
    END IF;
END $$;

-- Add CHECK constraint for frequency_type values
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'check_survey_period_frequency_type'
    ) THEN
        ALTER TABLE survey_periods
        ADD CONSTRAINT check_survey_period_frequency_type
        CHECK (frequency_type IN ('daily', 'weekday', 'weekly'));
    END IF;
END $$;

COMMENT ON TABLE survey_periods IS 'Tracks survey periods for follow-up reminders. Each period represents the timeframe a user has to respond (daily, weekday, or weekly).';
