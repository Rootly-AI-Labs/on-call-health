-- Fix rootly.com organization and users
-- This fixes:
--   1. Users showing as "Member" instead of "Admin"
--   2. "Organization required to sync Slack user IDs" error

BEGIN;

-- 1. Create rootly.com organization if it doesn't exist
INSERT INTO organizations (name, domain, slug, status, plan_type, max_users, max_analyses_per_month, created_at, updated_at, settings)
SELECT 'Rootly', 'rootly.com', 'rootly', 'active', 'free', 50, 5, NOW(), NOW(), '{}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM organizations WHERE domain = 'rootly.com');

-- 2. Update all @rootly.com users to have the organization and correct role
UPDATE users
SET
    organization_id = (SELECT id FROM organizations WHERE domain = 'rootly.com'),
    role = 'org_admin',
    joined_org_at = COALESCE(joined_org_at, NOW()),
    updated_at = NOW()
WHERE email LIKE '%@rootly.com'
  AND (organization_id IS NULL OR role != 'org_admin');

-- 3. Verify the changes
SELECT 'After Fix - Rootly.com Users:' as status;
SELECT
    u.id,
    u.name,
    u.email,
    u.role,
    u.organization_id,
    o.name as org_name,
    CASE
        WHEN u.organization_id IS NULL THEN '❌ NO ORG'
        WHEN u.role != 'org_admin' THEN '❌ WRONG ROLE'
        ELSE '✅ FIXED'
    END as status
FROM users u
LEFT JOIN organizations o ON u.organization_id = o.id
WHERE u.email LIKE '%@rootly.com'
ORDER BY u.id;

COMMIT;

-- Show final summary
SELECT
    COUNT(*) as total_rootly_users,
    COUNT(CASE WHEN organization_id IS NOT NULL THEN 1 END) as users_with_org,
    COUNT(CASE WHEN role = 'org_admin' THEN 1 END) as users_with_correct_role
FROM users
WHERE email LIKE '%@rootly.com';
