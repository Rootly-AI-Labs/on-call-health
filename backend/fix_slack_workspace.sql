-- SQL script to diagnose and fix Slack workspace registration issue
-- Run this on your Railway PostgreSQL database

-- Step 1: Check current state
SELECT 'Checking SlackWorkspaceMapping records...' as step;
SELECT
    id,
    workspace_id,
    workspace_name,
    organization_id,
    owner_user_id,
    status,
    created_at
FROM slack_workspace_mappings;

-- Step 2: Check SlackIntegration records
SELECT 'Checking SlackIntegration records...' as step;
SELECT
    id,
    user_id,
    workspace_id,
    token_source,
    connected_at
FROM slack_integrations;

-- Step 3: Check Users
SELECT 'Checking Users...' as step;
SELECT
    id,
    email,
    organization_id
FROM users;

-- Step 4: If no workspace_mappings exist, create one
-- MANUAL ACTION REQUIRED:
-- Uncomment the INSERT below and fill in the actual values from Steps 2 & 3

/*
INSERT INTO slack_workspace_mappings
(workspace_id, workspace_name, organization_id, owner_user_id, status, created_at, updated_at)
VALUES
(
    'YOUR_WORKSPACE_ID_FROM_SLACK_INTEGRATIONS',  -- From slack_integrations.workspace_id
    'Your Workspace Name',                        -- Any friendly name
    1,                                            -- Your organization_id from users table (or NULL if none)
    1,                                            -- Your user.id from users table
    'active',
    NOW(),
    NOW()
);
*/

-- Step 5: Verify the mapping was created
SELECT 'Verifying workspace mapping...' as step;
SELECT
    workspace_id,
    workspace_name,
    organization_id,
    owner_user_id,
    status
FROM slack_workspace_mappings;