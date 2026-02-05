-- Migration: Convert is_super_admin flag to super_admin role
-- Date: 2026-02-05
-- Description: Migrate from is_super_admin boolean column to role-based approach

-- Step 1: Convert users with is_super_admin=true to role='super_admin'
UPDATE users
SET role = 'super_admin'
WHERE is_super_admin = TRUE AND status = 'active';

-- Step 2: Drop the is_super_admin column
ALTER TABLE users DROP COLUMN IF EXISTS is_super_admin;

-- Step 3: Drop the index if it exists
DROP INDEX IF EXISTS idx_users_super_admin;

-- Verification
SELECT 'Super admin role count:' as info;
SELECT COUNT(*) as super_admin_count
FROM users
WHERE role = 'super_admin' AND status = 'active';

SELECT 'Super admins per organization:' as info;
SELECT
    o.id as org_id,
    o.name as org_name,
    COUNT(u.id) as super_admin_count,
    ARRAY_AGG(u.email) as super_admin_emails
FROM organizations o
LEFT JOIN users u ON u.organization_id = o.id AND u.role = 'super_admin' AND u.status = 'active'
GROUP BY o.id, o.name
ORDER BY super_admin_count ASC, o.id;
