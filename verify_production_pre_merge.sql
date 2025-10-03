-- ============================================================================
-- PRE-MERGE VERIFICATION SCRIPT
-- Run this BEFORE merging dev → main to document production state
-- ============================================================================
-- Usage: railway connect
--        \i verify_production_pre_merge.sql
-- ============================================================================

\echo '============================================================================'
\echo 'PRE-MERGE DATABASE VERIFICATION'
\echo 'Timestamp:'
SELECT NOW();
\echo '============================================================================'
\echo ''

-- ============================================================================
-- 1. TABLE EXISTENCE CHECK
-- ============================================================================
\echo '1. CHECKING WHICH TABLES EXIST...'
\echo ''

SELECT
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organizations')
        THEN '✅ organizations'
        ELSE '❌ organizations (MISSING - will be created)'
    END as table_status
UNION ALL
SELECT
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organization_invitations')
        THEN '✅ organization_invitations'
        ELSE '❌ organization_invitations (MISSING - will be created)'
    END
UNION ALL
SELECT
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_notifications')
        THEN '✅ user_notifications'
        ELSE '❌ user_notifications (MISSING - will be created)'
    END
UNION ALL
SELECT
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_burnout_reports')
        THEN '✅ user_burnout_reports'
        ELSE '❌ user_burnout_reports (MISSING - will be created)'
    END
UNION ALL
SELECT
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'slack_workspace_mappings')
        THEN '✅ slack_workspace_mappings'
        ELSE '❌ slack_workspace_mappings (MISSING - will be created)'
    END
UNION ALL
SELECT
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'survey_schedules')
        THEN '✅ survey_schedules'
        ELSE '❌ survey_schedules (MISSING - will be created)'
    END;

\echo ''
\echo '============================================================================'
\echo '2. USERS TABLE SCHEMA CHECK'
\echo '============================================================================'
\echo ''

SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name IN ('organization_id', 'role', 'joined_org_at', 'last_active_at', 'status')
ORDER BY column_name;

\echo ''
\echo 'Users without organization:'
SELECT COUNT(*) as users_without_org FROM users WHERE organization_id IS NULL;

\echo ''
\echo 'Users by role:'
SELECT role, COUNT(*) as count FROM users GROUP BY role ORDER BY count DESC;

\echo ''
\echo '============================================================================'
\echo '3. USER_CORRELATIONS TABLE SCHEMA CHECK (CRITICAL)'
\echo '============================================================================'
\echo ''

SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'user_correlations'
AND column_name IN ('organization_id', 'name', 'integration_ids')
ORDER BY column_name;

\echo ''
\echo 'User correlations status:'
SELECT
    COUNT(*) as total_correlations,
    COUNT(organization_id) as with_organization_id,
    COUNT(*) - COUNT(organization_id) as missing_organization_id,
    COUNT(name) as with_name,
    COUNT(integration_ids) as with_integration_ids
FROM user_correlations;

\echo ''
\echo '============================================================================'
\echo '4. ANALYSES TABLE SCHEMA CHECK'
\echo '============================================================================'
\echo ''

SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'analyses'
AND column_name IN ('organization_id', 'integration_name', 'platform')
ORDER BY column_name;

\echo ''
\echo 'Analyses status:'
SELECT
    COUNT(*) as total_analyses,
    COUNT(organization_id) as with_organization_id,
    COUNT(integration_name) as with_integration_name,
    COUNT(platform) as with_platform
FROM analyses;

\echo ''
\echo '============================================================================'
\echo '5. MIGRATIONS TABLE STATUS'
\echo '============================================================================'
\echo ''

SELECT
    name,
    applied_at,
    status
FROM migrations
ORDER BY applied_at DESC
LIMIT 10;

\echo ''
\echo '============================================================================'
\echo '6. DATA COUNTS'
\echo '============================================================================'
\echo ''

SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'organizations', COUNT(*) FROM organizations
UNION ALL
SELECT 'user_correlations', COUNT(*) FROM user_correlations
UNION ALL
SELECT 'analyses', COUNT(*) FROM analyses
UNION ALL
SELECT 'slack_integrations', COUNT(*) FROM slack_integrations
UNION ALL
SELECT 'rootly_integrations', COUNT(*) FROM rootly_integrations
ORDER BY count DESC;

\echo ''
\echo '============================================================================'
\echo '7. ORGANIZATION HEALTH CHECK'
\echo '============================================================================'
\echo ''

\echo 'Organizations with user counts:'
SELECT
    o.id,
    o.name,
    o.domain,
    o.status,
    COUNT(u.id) as user_count
FROM organizations o
LEFT JOIN users u ON u.organization_id = o.id
GROUP BY o.id, o.name, o.domain, o.status
ORDER BY user_count DESC;

\echo ''
\echo '============================================================================'
\echo '8. CRITICAL CHECKS - MUST BE REVIEWED'
\echo '============================================================================'
\echo ''

\echo 'A. Users without organizations (should be 0 or very few):'
SELECT COUNT(*) FROM users WHERE organization_id IS NULL;

\echo ''
\echo 'B. Duplicate user_correlations per organization (should be 0):'
SELECT
    organization_id,
    email,
    COUNT(*) as duplicate_count
FROM user_correlations
WHERE organization_id IS NOT NULL
GROUP BY organization_id, email
HAVING COUNT(*) > 1
LIMIT 10;

\echo ''
\echo 'C. User correlations without organization_id:'
SELECT COUNT(*) FROM user_correlations WHERE organization_id IS NULL;

\echo ''
\echo '============================================================================'
\echo 'PRE-MERGE VERIFICATION COMPLETE'
\echo '============================================================================'
\echo ''
\echo 'SAVE THIS OUTPUT! Compare with post-merge verification.'
\echo ''
\echo 'Key things to note:'
\echo '- Which tables are missing (will be created)'
\echo '- Which columns are missing (will be added by migrations)'
\echo '- Current data counts'
\echo '- Any users or correlations without organization_id'
\echo ''
\echo 'Next step: Merge dev → main, then run verify_production_post_merge.sql'
\echo '============================================================================'
