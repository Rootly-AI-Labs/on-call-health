-- Add email column to user_burnout_reports for proper team member identification
-- This allows surveys to be matched by email instead of user_id

ALTER TABLE user_burnout_reports
ADD COLUMN IF NOT EXISTS email VARCHAR(255);

-- Create index for email lookups
CREATE INDEX IF NOT EXISTS idx_user_burnout_reports_email ON user_burnout_reports(email);

-- Backfill email from users table for existing records
UPDATE user_burnout_reports ubr
SET email = u.email
FROM users u
WHERE ubr.user_id = u.id AND ubr.email IS NULL;
