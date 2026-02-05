-- Migration: Add super admin role for org continuity
-- Date: 2026-02-05
-- Description: Promote first admin in each org to super_admin role to ensure org continuity

-- Step 1: Set first admin in each organization as super_admin
-- This ensures every org has at least one super admin
WITH first_admins AS (
    SELECT DISTINCT ON (organization_id)
        id,
        organization_id
    FROM users
    WHERE
        organization_id IS NOT NULL
        AND role = 'admin'
        AND status = 'active'
    ORDER BY organization_id, created_at ASC
)
UPDATE users
SET role = 'super_admin'
WHERE id IN (SELECT id FROM first_admins);

-- Verification queries
SELECT 'Super admin count per organization:' as info;
SELECT
    o.id as org_id,
    o.name as org_name,
    COUNT(u.id) as super_admin_count,
    ARRAY_AGG(u.email) as super_admin_emails
FROM organizations o
LEFT JOIN users u ON u.organization_id = o.id AND u.role = 'super_admin' AND u.status = 'active'
GROUP BY o.id, o.name
ORDER BY super_admin_count ASC, o.id;

SELECT 'Organizations without super admin (should be empty):' as warning;
SELECT
    o.id as org_id,
    o.name as org_name
FROM organizations o
WHERE NOT EXISTS (
    SELECT 1 FROM users u
    WHERE u.organization_id = o.id
    AND u.role = 'super_admin'
    AND u.status = 'active'
)
ORDER BY o.id;
