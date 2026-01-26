-- Migration: Add last_modified tracking to survey_schedules table
-- Date: 2026-01-26
-- Description: Adds last_modified_by_user_id and last_modified_at columns to track who last configured the automated survey schedule

-- Add last_modified_by_user_id column (nullable, references users table)
ALTER TABLE survey_schedules
ADD COLUMN last_modified_by_user_id INTEGER;

-- Add foreign key constraint
ALTER TABLE survey_schedules
ADD CONSTRAINT fk_survey_schedules_last_modified_by
FOREIGN KEY (last_modified_by_user_id) REFERENCES users(id) ON DELETE SET NULL;

-- Add last_modified_at column with default to current timestamp
ALTER TABLE survey_schedules
ADD COLUMN last_modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Create index on last_modified_by_user_id for faster lookups
CREATE INDEX idx_survey_schedules_last_modified_by ON survey_schedules(last_modified_by_user_id);

-- Backfill existing records: Set last_modified_at to current time
-- Note: last_modified_by_user_id will remain NULL for existing records since we can't determine who created them
UPDATE survey_schedules
SET last_modified_at = CURRENT_TIMESTAMP
WHERE last_modified_at IS NULL;
