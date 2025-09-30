-- SQL script to fix organization status issue
-- Run this on Railway PostgreSQL if /burnout-survey shows "Organization is not active"

-- Step 1: Check organization status
SELECT
    id,
    name,
    domain,
    status,
    created_at
FROM organizations;

-- Step 2: If status is not 'active', update it
-- UPDATE organizations SET status = 'active' WHERE id = 1;

-- Step 3: Verify the fix
SELECT
    o.id,
    o.name,
    o.status,
    swm.workspace_id,
    swm.workspace_name
FROM organizations o
LEFT JOIN slack_workspace_mappings swm ON swm.organization_id = o.id;