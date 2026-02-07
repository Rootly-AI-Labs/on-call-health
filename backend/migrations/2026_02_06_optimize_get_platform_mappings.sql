-- Optimize get_platform_mappings endpoint with two covering indexes.

-- 1. Analyses: find latest completed analysis with results for a user.
-- Query: WHERE user_id = :uid AND status = 'completed' AND results IS NOT NULL
--        ORDER BY created_at DESC LIMIT 1
-- Existing idx_analyses_user_created covers (user_id, created_at) but forces
-- a filter on status. This composite + partial index is an exact match.
CREATE INDEX IF NOT EXISTS idx_analyses_user_status_created_has_results
    ON analyses(user_id, status, created_at DESC)
    WHERE results IS NOT NULL;

-- 2. Integration mappings: fetch platform mappings sorted by recency.
-- Query: WHERE user_id = :uid AND target_platform = :platform
--        ORDER BY created_at DESC LIMIT 50
-- Existing ix_integration_mappings_user_platform covers (user_id, target_platform)
-- but doesn't include created_at, forcing a sort step.
CREATE INDEX IF NOT EXISTS idx_integration_mappings_user_platform_created
    ON integration_mappings(user_id, target_platform, created_at DESC);
