-- Make email required (NOT NULL) in user_burnout_reports
-- Email is now the primary identifier for team members, so it must be present

ALTER TABLE user_burnout_reports
ALTER COLUMN email SET NOT NULL;
