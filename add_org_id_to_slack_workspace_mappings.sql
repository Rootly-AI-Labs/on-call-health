-- Add organization_id to slack_workspace_mappings table
-- This fixes: column slack_workspace_mappings.organization_id does not exist error

BEGIN;

-- Add organization_id column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'slack_workspace_mappings'
        AND column_name = 'organization_id'
    ) THEN
        ALTER TABLE slack_workspace_mappings
        ADD COLUMN organization_id INTEGER;

        -- Add foreign key constraint
        ALTER TABLE slack_workspace_mappings
        ADD CONSTRAINT slack_workspace_mappings_organization_id_fkey
        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;

        -- Add index
        CREATE INDEX idx_slack_workspace_mappings_organization_id
        ON slack_workspace_mappings(organization_id);

        RAISE NOTICE 'Added organization_id column to slack_workspace_mappings';
    ELSE
        RAISE NOTICE 'organization_id column already exists';
    END IF;
END $$;

-- Update existing mappings to have organization_id based on owner_user_id
UPDATE slack_workspace_mappings swm
SET organization_id = u.organization_id
FROM users u
WHERE swm.owner_user_id = u.id
AND swm.organization_id IS NULL
AND u.organization_id IS NOT NULL;

-- Show results
SELECT
    'Updated slack_workspace_mappings:' as status,
    COUNT(*) as total_mappings,
    COUNT(organization_id) as mappings_with_org_id
FROM slack_workspace_mappings;

COMMIT;
