-- ============================================================================
-- POST-MERGE VERIFICATION SCRIPT
-- Run this AFTER merging dev → main and deployment completes
-- ============================================================================
-- Usage: railway connect
--        \i verify_production_post_merge.sql
-- ============================================================================

\echo '============================================================================'
\echo 'POST-MERGE DATABASE VERIFICATION'
\echo 'Timestamp:'
SELECT NOW();
\echo '============================================================================'
\echo ''

-- ============================================================================
-- 1. VERIFY ALL NEW TABLES WERE CREATED
-- ============================================================================
\echo '1. VERIFYING NEW TABLES...'
\echo ''

SELECT
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organizations')
        THEN '✅ organizations EXISTS'
        ELSE '❌ organizations MISSING - FAILED!'
    END as table_status
UNION ALL
SELECT
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organization_invitations')
        THEN '✅ organization_invitations EXISTS'
        ELSE '❌ organization_invitations MISSING - FAILED!'
    END
UNION ALL
SELECT
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_notifications')
        THEN '✅ user_notifications EXISTS'
        ELSE '❌ user_notifications MISSING - FAILED!'
    END
UNION ALL
SELECT
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_burnout_reports')
        THEN '✅ user_burnout_reports EXISTS'
        ELSE '❌ user_burnout_reports MISSING - FAILED!'
    END
UNION ALL
SELECT
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'slack_workspace_mappings')
        THEN '✅ slack_workspace_mappings EXISTS'
        ELSE '❌ slack_workspace_mappings MISSING - FAILED!'
    END
UNION ALL
SELECT
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'survey_schedules')
        THEN '✅ survey_schedules EXISTS'
        ELSE '❌ survey_schedules MISSING - FAILED!'
    END;

\echo ''
\echo '============================================================================'
\echo '2. VERIFY USER_CORRELATIONS MIGRATIONS (MOST CRITICAL)'
\echo '============================================================================'
\echo ''

\echo 'Checking for new columns...'
SELECT
    column_name,
    data_type,
    is_nullable,
    CASE
        WHEN column_name = 'organization_id' THEN '⭐ CRITICAL - Multi-tenancy'
        WHEN column_name = 'name' THEN '📝 Display names'
        WHEN column_name = 'integration_ids' THEN '🔗 Multi-integration support'
        ELSE ''
    END as purpose
FROM information_schema.columns
WHERE table_name = 'user_correlations'
AND column_name IN ('organization_id', 'name', 'integration_ids')
ORDER BY column_name;

\echo ''
\echo 'Organization_id population status:'
SELECT
    COUNT(*) as total_correlations,
    COUNT(organization_id) as with_org_id,
    COUNT(*) - COUNT(organization_id) as missing_org_id,
    ROUND(100.0 * COUNT(organization_id) / NULLIF(COUNT(*), 0), 2) as percent_populated
FROM user_correlations;

\echo ''
\echo '⚠️  WARNING: If missing_org_id > 0, some users may not be able to use Slack surveys!'
\echo ''

\echo 'Checking indexes were created...'
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'user_correlations'
AND indexname IN (
    'idx_user_correlations_organization_id',
    'idx_user_correlations_org_email',
    'idx_user_correlations_org_slack'
)
ORDER BY indexname;

\echo ''
\echo '============================================================================'
\echo '3. VERIFY MIGRATIONS WERE APPLIED'
\echo '============================================================================'
\echo ''

SELECT
    name,
    applied_at,
    status,
    CASE
        WHEN name LIKE '%001%' THEN 'Migration 001: Integration fields'
        WHEN name LIKE '%002%' THEN '⭐ Migration 002: Multi-tenancy (CRITICAL)'
        WHEN name LIKE '%003%' THEN 'Migration 003: User names'
        WHEN name LIKE '%004%' THEN 'Migration 004: Integration IDs'
        WHEN name LIKE '%005%' THEN 'Migration 005: Personal circumstances'
        ELSE 'Other migration'
    END as description
FROM migrations
WHERE status = 'completed'
ORDER BY applied_at DESC
LIMIT 10;

\echo ''
\echo 'Expected migrations: 001, 002, 003, 004, 005'
\echo ''

-- Check if all 5 migrations are present
WITH expected_migrations AS (
    SELECT unnest(ARRAY[
        '001_add_integration_fields_to_analyses',
        '002_add_organization_id_to_user_correlations',
        '003_add_name_to_user_correlations',
        '004_add_integration_ids_to_user_correlations',
        '005_add_personal_circumstances_to_reports'
    ]) AS migration_name
)
SELECT
    em.migration_name,
    CASE
        WHEN m.name IS NOT NULL THEN '✅ Applied'
        ELSE '❌ MISSING - Check logs!'
    END as status
FROM expected_migrations em
LEFT JOIN migrations m ON m.name = em.migration_name
ORDER BY em.migration_name;

\echo ''
\echo '============================================================================'
\echo '4. DATA INTEGRITY CHECKS'
\echo '============================================================================'
\echo ''

\echo 'A. Users without organizations (should be 0 or minimal):'
SELECT
    COUNT(*) as count,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ All users have organizations'
        WHEN COUNT(*) < 5 THEN '⚠️  Few users without orgs (acceptable for new signups)'
        ELSE '❌ Many users without orgs - investigate!'
    END as status
FROM users
WHERE organization_id IS NULL;

\echo ''
\echo 'B. User correlations without organization_id (should be 0):'
SELECT
    COUNT(*) as count,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ All correlations have organization_id'
        WHEN COUNT(*) < 10 THEN '⚠️  Some correlations missing org_id - check backfill'
        ELSE '❌ Many correlations missing org_id - BACKFILL FAILED!'
    END as status
FROM user_correlations
WHERE organization_id IS NULL;

\echo ''
\echo 'C. Duplicate user_correlations within same organization (should be 0):'
SELECT
    COUNT(*) as duplicate_pairs,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ No duplicates - multi-tenancy working correctly'
        ELSE '❌ Found duplicates - investigate!'
    END as status
FROM (
    SELECT organization_id, email, COUNT(*) as cnt
    FROM user_correlations
    WHERE organization_id IS NOT NULL
    GROUP BY organization_id, email
    HAVING COUNT(*) > 1
) dups;

\echo ''
\echo 'D. Analyses without organization_id:'
SELECT
    COUNT(*) as count,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ All analyses have organization_id'
        ELSE 'ℹ️  Some old analyses may not have org_id (acceptable)'
    END as status
FROM analyses
WHERE organization_id IS NULL;

\echo ''
\echo '============================================================================'
\echo '5. DATA COUNTS COMPARISON'
\echo '============================================================================'
\echo ''

\echo 'Current data counts:'
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
SELECT 'user_burnout_reports', COUNT(*) FROM user_burnout_reports
UNION ALL
SELECT 'slack_workspace_mappings', COUNT(*) FROM slack_workspace_mappings
UNION ALL
SELECT 'survey_schedules', COUNT(*) FROM survey_schedules
ORDER BY count DESC;

\echo ''
\echo '⚠️  Compare these counts with pre-merge output!'
\echo '   - User/correlation/analysis counts should be the same or slightly higher'
\echo '   - New tables (burnout_reports, mappings, schedules) may be 0 initially'
\echo ''

\echo ''
\echo '============================================================================'
\echo '6. ORGANIZATION HEALTH CHECK'
\echo '============================================================================'
\echo ''

\echo 'Organizations with users and correlations:'
SELECT
    o.id,
    o.name,
    o.status,
    COUNT(DISTINCT u.id) as user_count,
    COUNT(DISTINCT uc.id) as correlation_count
FROM organizations o
LEFT JOIN users u ON u.organization_id = o.id
LEFT JOIN user_correlations uc ON uc.organization_id = o.id
GROUP BY o.id, o.name, o.status
ORDER BY user_count DESC
LIMIT 10;

\echo ''
\echo '============================================================================'
\echo '7. FUNCTIONAL TESTS'
\echo '============================================================================'
\echo ''

\echo 'A. Check Slack workspace mappings exist:'
SELECT
    COUNT(*) as mapping_count,
    CASE
        WHEN COUNT(*) > 0 THEN '✅ Slack workspaces mapped'
        ELSE 'ℹ️  No Slack workspaces yet (users need to connect)'
    END as status
FROM slack_workspace_mappings;

\echo ''
\echo 'B. Check survey schedules:'
SELECT
    COUNT(*) as schedule_count,
    CASE
        WHEN COUNT(*) > 0 THEN '✅ Survey schedules configured'
        ELSE 'ℹ️  No schedules yet (users need to set up)'
    END as status
FROM survey_schedules;

\echo ''
\echo 'C. Sample user_correlation with organization_id (verify structure):'
SELECT
    id,
    email,
    name,
    organization_id,
    slack_user_id,
    CASE WHEN integration_ids IS NOT NULL THEN 'Has integration_ids' ELSE 'NULL' END as integration_ids_status
FROM user_correlations
WHERE organization_id IS NOT NULL
LIMIT 3;

\echo ''
\echo '============================================================================'
\echo 'POST-MERGE VERIFICATION COMPLETE'
\echo '============================================================================'
\echo ''

\echo '✅ SUCCESS CRITERIA:'
\echo '  - All 6 new tables exist'
\echo '  - All 5 migrations show as completed'
\echo '  - user_correlations.organization_id is 95%+ populated'
\echo '  - No duplicate correlations within same organization'
\echo '  - User/correlation counts match pre-merge (or slightly higher)'
\echo ''

\echo '⚠️  IF ANY CHECKS FAILED:'
\echo '  1. Check Railway deployment logs for migration errors'
\echo '  2. Run: SELECT * FROM migrations ORDER BY applied_at DESC;'
\echo '  3. Verify app is running: Check Railway dashboard'
\echo '  4. If critical failure, consider rollback'
\echo ''

\echo '📋 NEXT STEPS:'
\echo '  1. Test user login'
\echo '  2. Test Slack integration connection'
\echo '  3. Test survey delivery'
\echo '  4. Test beta token sync'
\echo '  5. Monitor logs for errors'
\echo ''
\echo '============================================================================'
