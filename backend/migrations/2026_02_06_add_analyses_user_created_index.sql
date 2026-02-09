-- Add composite indexes on analyses table for the two main query patterns.

-- Optimizes list_analyses: WHERE user_id = ? ORDER BY created_at DESC LIMIT N
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analyses_user_created
    ON analyses(user_id, created_at DESC);

-- Optimizes get_analysis_by_identifier 404 fallback and get_platform_mappings:
-- WHERE organization_id = ? AND status = 'completed' ORDER BY created_at DESC LIMIT 1
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analyses_org_status_created
    ON analyses(organization_id, status, created_at DESC);
