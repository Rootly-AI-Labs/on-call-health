-- Migration: Repair false-positive migration 040_add_survey_periods
-- Description: This migration detects and repairs a scenario where migration 040 was
--              marked as complete without actually running (due to a bug in the migration
--              runner that marked migrations complete even when SQL files failed to load).
--
-- Background: The migration runner had a bug where if load_sql_file() returned an empty
--             list (due to FileNotFoundError or other issues), the migration would still
--             be marked as "completed" because the for loop didn't execute but
--             mark_migration_applied() still ran. This caused silent failures where
--             migrations appeared to succeed but no schema changes were applied.
--
-- This migration is idempotent - it checks if columns/tables exist before creating them.

-- ============================================================================
-- Step 1: Remove false migration record if columns don't exist
-- ============================================================================
DO $$
BEGIN
    -- Check if migration 040 is marked as complete but columns don't exist
    IF EXISTS (SELECT 1 FROM migrations WHERE name = '040_add_survey_periods' AND status = 'completed')
       AND NOT EXISTS (
           SELECT 1 FROM information_schema.columns
           WHERE table_name = 'survey_schedules'
           AND column_name = 'follow_up_reminders_enabled'
       ) THEN
        -- Remove the false migration record so it will be properly re-run
        DELETE FROM migrations WHERE name = '040_add_survey_periods';
        RAISE NOTICE 'Removed false-positive migration record for 040_add_survey_periods';
    END IF;
END $$;

-- ============================================================================
-- Step 2: Re-apply the schema changes (idempotent - uses IF NOT EXISTS)
-- ============================================================================

-- Add new columns to survey_schedules
ALTER TABLE survey_schedules
ADD COLUMN IF NOT EXISTS follow_up_reminders_enabled BOOLEAN DEFAULT TRUE;

ALTER TABLE survey_schedules
ADD COLUMN IF NOT EXISTS follow_up_message_template VARCHAR(500);

-- Create survey_periods table
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

-- Indexes for survey_periods
CREATE INDEX IF NOT EXISTS idx_survey_periods_org_status
ON survey_periods(organization_id, status);

CREATE INDEX IF NOT EXISTS idx_survey_periods_email_status
ON survey_periods(email, status);

CREATE INDEX IF NOT EXISTS idx_survey_periods_period_dates
ON survey_periods(period_start_date, period_end_date);

CREATE INDEX IF NOT EXISTS idx_survey_periods_user_correlation
ON survey_periods(user_correlation_id, status);

-- Unique constraint for pending periods
CREATE UNIQUE INDEX IF NOT EXISTS uq_survey_periods_pending_user_org
ON survey_periods(organization_id, user_correlation_id)
WHERE status = 'pending';

-- Add CHECK constraints (idempotent)
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
