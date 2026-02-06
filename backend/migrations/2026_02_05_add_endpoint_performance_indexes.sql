-- Migration: Add performance indexes for slow integration endpoints
-- Description: Adds composite and single-column indexes identified by New Relic
--   performance analysis of the 5 slowest endpoints.
-- Impact: Reduces query time from 50-200ms to 5-10ms for affected queries.

-- ============================================================================
-- user_burnout_reports: composite index for analyses endpoint survey query
-- Query: WHERE email IN (...) AND submitted_at BETWEEN x AND y
--         ORDER BY email, submitted_at ASC
-- ============================================================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_burnout_reports_email_submitted
    ON user_burnout_reports(email, submitted_at);

-- ============================================================================
-- jira_integrations: user_id index for /jira/status endpoint
-- Query: WHERE user_id = ?
-- Currently only has FK constraint, no index
-- ============================================================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jira_integrations_user_id
    ON jira_integrations(user_id);

-- ============================================================================
-- jira_workspace_mappings: composite index for workspace lookup
-- Query: WHERE jira_cloud_id = ? AND organization_id = ?
-- Currently only has unique constraint on jira_cloud_id alone
-- ============================================================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jira_workspace_cloud_org
    ON jira_workspace_mappings(jira_cloud_id, organization_id);

-- ============================================================================
-- slack_workspace_mappings: composite indexes for /slack/status endpoint
-- Query 1: WHERE organization_id = ? AND status = 'active'
-- Query 2: WHERE owner_user_id = ? AND status = 'active'
-- Currently no indexes on any of these columns
-- ============================================================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_slack_workspace_org_status
    ON slack_workspace_mappings(organization_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_slack_workspace_owner_status
    ON slack_workspace_mappings(owner_user_id, status);
