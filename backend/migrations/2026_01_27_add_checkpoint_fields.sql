-- Add checkpoint/resume fields to analyses table for deployment resilience
-- These fields enable analysis tasks to save progress and resume after container restarts

-- Add last_checkpoint column to track which phase was last completed (0-7)
ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS last_checkpoint INTEGER DEFAULT 0;

-- Add checkpoint_data column to store intermediate analysis results
ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS checkpoint_data JSON;

-- Add arq_job_id column to track ARQ background job ID
ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS arq_job_id VARCHAR(255);

-- Add attempt_count column to track number of resume attempts
ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 0;

-- Add updated_at column to track staleness of analyses
ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;

-- Create index on arq_job_id for faster job lookups
CREATE INDEX IF NOT EXISTS idx_analyses_arq_job_id ON analyses(arq_job_id);

-- Create index on last_checkpoint for filtering interrupted analyses
CREATE INDEX IF NOT EXISTS idx_analyses_last_checkpoint ON analyses(last_checkpoint);

-- Create index on status and updated_at for stale task detection
CREATE INDEX IF NOT EXISTS idx_analyses_status_updated_at ON analyses(status, updated_at);

-- Backfill updated_at for existing analyses (use created_at as initial value)
UPDATE analyses
SET updated_at = created_at
WHERE updated_at IS NULL;

-- Add comments for documentation
COMMENT ON COLUMN analyses.last_checkpoint IS 'Last completed checkpoint (0-7) for resume capability';
COMMENT ON COLUMN analyses.checkpoint_data IS 'Intermediate analysis data (users, incidents, results) for resume';
COMMENT ON COLUMN analyses.arq_job_id IS 'ARQ background job ID for tracking and duplicate prevention';
COMMENT ON COLUMN analyses.attempt_count IS 'Number of times analysis was resumed (for retry limiting)';
COMMENT ON COLUMN analyses.updated_at IS 'Last update timestamp for stale task detection';
