-- Allow NULL user_id in user_burnout_reports for team members without accounts
-- Team members can submit surveys without having a logged-in user account
-- Surveys are matched by email, not user_id

ALTER TABLE user_burnout_reports
ALTER COLUMN user_id DROP NOT NULL;
