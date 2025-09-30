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

-- Step 2: Fix organizations with NULL status (shows as 'None' in Python)
UPDATE organizations
SET status = 'active'
WHERE status IS NULL;

-- Alternative: Fix specific organization by ID
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

-- Step 4: Check if any users are in this organization
SELECT
    u.id,
    u.email,
    u.organization_id,
    o.name as org_name,
    o.status as org_status
FROM users u
JOIN organizations o ON u.organization_id = o.id;