-- Check current state of rootly.com organization and users

-- 1. Check if rootly.com organization exists
SELECT 'Rootly.com Organization:' as check_type;
SELECT id, name, domain, status, created_at
FROM organizations
WHERE domain = 'rootly.com';

-- 2. Check all users with rootly.com emails
SELECT '';
SELECT 'Rootly.com Users:' as check_type;
SELECT
    u.id,
    u.name,
    u.email,
    u.role,
    u.organization_id,
    o.name as org_name,
    o.domain as org_domain,
    CASE
        WHEN u.organization_id IS NULL THEN '❌ NO ORG'
        WHEN u.role IS NULL OR u.role IN ('user', 'member') THEN '❌ WRONG ROLE'
        ELSE '✓ OK'
    END as status
FROM users u
LEFT JOIN organizations o ON u.organization_id = o.id
WHERE u.email LIKE '%@rootly.com'
ORDER BY u.created_at;

-- 3. Summary
SELECT '';
SELECT 'Summary:' as check_type;
SELECT
    COUNT(*) as total_rootly_users,
    COUNT(CASE WHEN organization_id IS NULL THEN 1 END) as users_without_org,
    COUNT(CASE WHEN role != 'org_admin' OR role IS NULL THEN 1 END) as users_with_wrong_role
FROM users
WHERE email LIKE '%@rootly.com';
