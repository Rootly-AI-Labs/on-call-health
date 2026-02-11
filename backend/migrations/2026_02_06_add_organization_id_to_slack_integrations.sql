-- Add organization_id column to slack_integrations table
-- This allows tracking whether a Slack integration is personal (NULL) or organization-owned

ALTER TABLE slack_integrations
ADD COLUMN organization_id INTEGER REFERENCES organizations(id);

-- Create index for faster lookups
CREATE INDEX idx_slack_integrations_organization_id ON slack_integrations(organization_id);

-- Add comment explaining the column
COMMENT ON COLUMN slack_integrations.organization_id IS 'NULL for personal integrations, set for organization-owned integrations';

-- Backfill organization_id for existing Slack integrations
-- Set organization_id based on the user's current organization
UPDATE slack_integrations si
SET organization_id = u.organization_id
FROM users u
WHERE si.user_id = u.id
  AND u.organization_id IS NOT NULL
  AND si.organization_id IS NULL;

-- Log the backfill results
DO $$
DECLARE
    backfilled_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO backfilled_count
    FROM slack_integrations
    WHERE organization_id IS NOT NULL;

    RAISE NOTICE 'Backfilled organization_id for % existing Slack integrations', backfilled_count;
END $$;
