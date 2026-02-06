-- Add organization_id column to slack_integrations table
-- This allows tracking whether a Slack integration is personal (NULL) or organization-owned

ALTER TABLE slack_integrations
ADD COLUMN organization_id INTEGER REFERENCES organizations(id);

-- Create index for faster lookups
CREATE INDEX idx_slack_integrations_organization_id ON slack_integrations(organization_id);

-- Add comment explaining the column
COMMENT ON COLUMN slack_integrations.organization_id IS 'NULL for personal integrations, set for organization-owned integrations';
