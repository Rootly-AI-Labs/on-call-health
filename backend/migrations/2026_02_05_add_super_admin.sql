-- Migration: Add super admin role for org continuity
-- Date: 2026-02-05
-- Description: Add is_super_admin flag to ensure at least one admin can't leave without transferring responsibility

-- Step 1: Add is_super_admin column to users table
ALTER TABLE users
ADD COLUMN is_super_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- Step 2: Set first admin in each organization as super admin
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
SET is_super_admin = TRUE
WHERE id IN (SELECT id FROM first_admins);

-- Step 3: Create index for performance
CREATE INDEX idx_users_super_admin ON users(is_super_admin) WHERE is_super_admin = TRUE;

-- Verification queries
SELECT 'Super admin count per organization:' as info;
SELECT
    o.id as org_id,
    o.name as org_name,
    COUNT(u.id) as super_admin_count,
    ARRAY_AGG(u.email) as super_admin_emails
FROM organizations o
LEFT JOIN users u ON u.organization_id = o.id AND u.is_super_admin = TRUE AND u.status = 'active'
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
    AND u.is_super_admin = TRUE
    AND u.status = 'active'
)
ORDER BY o.id;
