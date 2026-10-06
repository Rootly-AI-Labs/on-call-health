-- Age stored error-only failures independently from later status updates.
ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS error_generated_at TIMESTAMP WITH TIME ZONE;

-- Only known failed-run completions can date historical error content.
-- Missing completion dates and errors left on completed rows stay unknown.
UPDATE analyses
SET error_generated_at = completed_at
WHERE error_generated_at IS NULL
  AND status = 'failed'
  AND completed_at IS NOT NULL
  AND error_message IS NOT NULL
  AND error_message <> '';

COMMENT ON COLUMN analyses.error_generated_at IS
'Server timestamp of stored error content, unchanged by status-only updates';
