-- A failed rerun must not renew the lifetime of an older stored result.
ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS results_generated_at TIMESTAMP WITH TIME ZONE;

-- Successful historical completions supply a trustworthy generation time.
-- Keep missing dates and failed/partial legacy snapshots unknown for review.
UPDATE analyses
SET results_generated_at = completed_at
WHERE results_generated_at IS NULL
  AND status = 'completed'
  AND completed_at IS NOT NULL
  AND results IS NOT NULL;

COMMENT ON COLUMN analyses.results_generated_at IS
'Server timestamp of the stored result generation, unchanged by status-only failures';
