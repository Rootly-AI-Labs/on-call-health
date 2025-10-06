-- Add organization_id to user_correlations for multi-tenancy support
-- This allows multiple organizations to sync the same team members from shared beta tokens

-- Step 1: Add organization_id column (nullable initially)
ALTER TABLE user_correlations
ADD COLUMN IF NOT EXISTS organization_id INTEGER;

-- Step 2: Add foreign key constraint
ALTER TABLE user_correlations
ADD CONSTRAINT fk_user_correlations_organization
FOREIGN KEY (organization_id) REFERENCES organizations(id);

-- Step 3: Create index on organization_id for better query performance
CREATE INDEX IF NOT EXISTS idx_user_correlations_organization_id
ON user_correlations(organization_id);

-- Step 4: Backfill organization_id from existing user_id relationships
-- This ensures existing data continues to work
UPDATE user_correlations uc
SET organization_id = u.organization_id
FROM users u
WHERE uc.user_id = u.id
AND uc.organization_id IS NULL
AND u.organization_id IS NOT NULL;

-- Step 5: Create composite index on (organization_id, email) for fast lookups
-- This is the key index for multi-tenancy queries
CREATE INDEX IF NOT EXISTS idx_user_correlations_org_email
ON user_correlations(organization_id, email);

-- Step 6: Create composite index on (organization_id, slack_user_id) for Slack surveys
CREATE INDEX IF NOT EXISTS idx_user_correlations_org_slack
ON user_correlations(organization_id, slack_user_id)
WHERE slack_user_id IS NOT NULL;

-- Verification query: Check if migration worked
-- SELECT
--     COUNT(*) as total_correlations,
--     COUNT(organization_id) as with_org_id,
--     COUNT(*) - COUNT(organization_id) as missing_org_id
-- FROM user_correlations;
