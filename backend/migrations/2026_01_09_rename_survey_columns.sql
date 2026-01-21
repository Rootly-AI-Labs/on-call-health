-- Rename user_burnout_reports columns to match current code expectations
-- Old schema: self_reported_score, energy_level
-- New schema: feeling_score, workload_score
-- This migration is idempotent - safe to run multiple times

-- Rename columns (only if old column exists and new column doesn't)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_burnout_reports' AND column_name = 'self_reported_score')
    AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_burnout_reports' AND column_name = 'workload_score') THEN
        ALTER TABLE user_burnout_reports RENAME COLUMN self_reported_score TO workload_score;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_burnout_reports' AND column_name = 'energy_level')
    AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_burnout_reports' AND column_name = 'feeling_score') THEN
        ALTER TABLE user_burnout_reports RENAME COLUMN energy_level TO feeling_score;
    END IF;
END $$;

-- Update constraints
ALTER TABLE user_burnout_reports
  DROP CONSTRAINT IF EXISTS user_burnout_reports_self_reported_score_check;

ALTER TABLE user_burnout_reports
  DROP CONSTRAINT IF EXISTS user_burnout_reports_energy_level_check;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_burnout_reports_feeling_score_check') THEN
        ALTER TABLE user_burnout_reports
        ADD CONSTRAINT user_burnout_reports_feeling_score_check
        CHECK (feeling_score >= 1 AND feeling_score <= 5);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_burnout_reports_workload_score_check') THEN
        ALTER TABLE user_burnout_reports
        ADD CONSTRAINT user_burnout_reports_workload_score_check
        CHECK (workload_score >= 1 AND workload_score <= 5);
    END IF;
END $$;
