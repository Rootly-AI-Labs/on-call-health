-- Migration: Add started_at column to analyses table
-- This column tracks when an analysis execution began (status changed to 'running')
-- Used for accurate stuck analysis detection (instead of created_at)

ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN analyses.started_at IS 'Timestamp when analysis execution started (status changed to running)';

-- Create index for efficient stuck analysis queries
CREATE INDEX IF NOT EXISTS idx_analyses_started_at ON analyses(started_at);
