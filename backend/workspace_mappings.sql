-- Create slack_workspace_mappings table for multi-org support
CREATE TABLE IF NOT EXISTS slack_workspace_mappings (
    id SERIAL PRIMARY KEY,

    -- Slack workspace identification
    workspace_id VARCHAR(20) NOT NULL UNIQUE,  -- T01234567 (Slack team ID)
    workspace_name VARCHAR(255),               -- "Acme Corp"
    workspace_domain VARCHAR(255),             -- "acme-corp.slack.com"

    -- Organization mapping
    owner_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_domain VARCHAR(255),          -- "company.com"

    -- Registration tracking
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    registered_via VARCHAR(20) DEFAULT 'oauth',  -- 'oauth', 'manual', 'admin'

    -- Status and management
    status VARCHAR(20) DEFAULT 'active',       -- 'active', 'suspended', 'pending'

    -- Constraints
    CONSTRAINT unique_workspace_id UNIQUE(workspace_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_slack_workspace_mappings_owner_user_id ON slack_workspace_mappings(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_slack_workspace_mappings_workspace_id ON slack_workspace_mappings(workspace_id);
CREATE INDEX IF NOT EXISTS idx_slack_workspace_mappings_status ON slack_workspace_mappings(status);
CREATE INDEX IF NOT EXISTS idx_slack_workspace_mappings_domain ON slack_workspace_mappings(organization_domain);

-- Future-proofing: trigger function for updated_at column
CREATE OR REPLACE FUNCTION update_slack_workspace_mappings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Migrate existing slack_integrations to workspace mappings
INSERT INTO slack_workspace_mappings (
    workspace_id,
    workspace_name,
    owner_user_id,
    registered_via,
    status
)
SELECT DISTINCT
    si.workspace_id,
    'Legacy Workspace' as workspace_name,
    si.user_id as owner_user_id,
    'legacy' as registered_via,
    'active' as status
FROM slack_integrations si
WHERE si.workspace_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM slack_workspace_mappings swm
      WHERE swm.workspace_id = si.workspace_id
  );