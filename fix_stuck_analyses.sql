-- Fix stuck analyses that completed but status wasn't updated
-- Run this on Railway PostgreSQL

-- First, let's see what analyses are stuck
SELECT
    id,
    status,
    created_at,
    EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600 as hours_old
FROM analyses
WHERE status = 'running'
ORDER BY created_at DESC;

-- Mark old stuck analyses as failed (older than 1 hour)
UPDATE analyses
SET
    status = 'failed',
    error_message = 'Analysis timed out - status was not updated. This is a known bug that has been fixed.',
    completed_at = NOW()
WHERE
    status = 'running'
    AND created_at < NOW() - INTERVAL '1 hour';

-- For analysis 1156 specifically (if it has results, mark as completed)
-- You'll need to check if it has results first
SELECT id, status, results IS NOT NULL as has_results
FROM analyses
WHERE id = 1156;

-- If it has results, mark as completed:
-- UPDATE analyses SET status = 'completed', completed_at = NOW() WHERE id = 1156 AND results IS NOT NULL;

-- If no results, mark as failed:
-- UPDATE analyses SET status = 'failed', error_message = 'Completed but results were not saved', completed_at = NOW() WHERE id = 1156 AND results IS NULL;
