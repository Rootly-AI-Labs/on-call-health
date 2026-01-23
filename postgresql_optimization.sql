-- PostgreSQL Optimization Script for Railway
-- Run these commands to diagnose and optimize the database

-- ========================================
-- 1. FIX COLLATION VERSION MISMATCH
-- ========================================
-- This warning appears in logs and can affect text sorting/indexing

-- Fix for main database
ALTER DATABASE postgres REFRESH COLLATION VERSION;

-- If using a different database name, replace 'postgres' with actual name
-- ALTER DATABASE your_db_name REFRESH COLLATION VERSION;

-- ========================================
-- 2. CHECK CURRENT DATABASE SIZE & STATS
-- ========================================

-- Overall database size
SELECT
    pg_size_pretty(pg_database_size(current_database())) as db_size;

-- Table sizes (top 10 largest)
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;

-- ========================================
-- 3. CHECK INDEX USAGE
-- ========================================

-- Unused indexes (candidates for removal)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND indexrelname NOT LIKE '%pkey%'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Most used indexes (verify they exist)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC
LIMIT 20;

-- ========================================
-- 4. CHECK FOR MISSING INDEXES
-- ========================================

-- Tables with sequential scans (may need indexes)
SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    seq_tup_read / NULLIF(seq_scan, 0) as avg_seq_rows,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_scan DESC
LIMIT 20;

-- ========================================
-- 5. CHECK QUERY PERFORMANCE (if pg_stat_statements is enabled)
-- ========================================

-- Enable pg_stat_statements extension (run as superuser if not enabled)
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Slowest queries (requires pg_stat_statements)
-- SELECT
--     query,
--     calls,
--     total_exec_time,
--     mean_exec_time,
--     max_exec_time,
--     stddev_exec_time
-- FROM pg_stat_statements
-- WHERE mean_exec_time > 100  -- queries averaging >100ms
-- ORDER BY mean_exec_time DESC
-- LIMIT 20;

-- ========================================
-- 6. CHECK FOR BLOAT
-- ========================================

-- Table bloat estimation
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    n_dead_tup as dead_tuples,
    n_live_tup as live_tuples,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_tuple_percent
FROM pg_stat_user_tables
WHERE n_live_tup > 0
ORDER BY n_dead_tup DESC
LIMIT 20;

-- ========================================
-- 7. VACUUM RECOMMENDATIONS
-- ========================================

-- Tables that need vacuuming
SELECT
    schemaname,
    tablename,
    last_vacuum,
    last_autovacuum,
    n_dead_tup,
    n_live_tup
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;

-- Run VACUUM on tables with high dead tuples
-- VACUUM ANALYZE analyses;
-- VACUUM ANALYZE user_correlations;
-- VACUUM ANALYZE user_burnout_reports;

-- ========================================
-- 8. CONNECTION STATISTICS
-- ========================================

-- Current connections
SELECT
    datname,
    count(*) as connections,
    max(state) as state
FROM pg_stat_activity
GROUP BY datname;

-- Active queries
SELECT
    pid,
    now() - query_start as duration,
    state,
    query
FROM pg_stat_activity
WHERE state != 'idle'
    AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC;

-- ========================================
-- 9. RECOMMENDED INDEXES (based on common queries)
-- ========================================

-- Check if these indexes exist, create if missing:

-- For analyses table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analyses_user_id_status
    ON analyses(user_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analyses_org_status
    ON analyses(organization_id, status)
    WHERE status IN ('completed', 'running');

-- For user_correlations (already has some from migration 039)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_correlations_org_active
    ON user_correlations(organization_id, is_active);

-- For user_burnout_reports
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_burnout_reports_email_submitted
    ON user_burnout_reports(email, submitted_at DESC);

-- For integration_mappings
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_integration_mappings_analysis
    ON integration_mappings(analysis_id)
    WHERE analysis_id IS NOT NULL;

-- ========================================
-- 10. MAINTENANCE RECOMMENDATIONS
-- ========================================

-- Run these periodically (Railway may do this automatically)

-- Update statistics (helps query planner)
-- ANALYZE;

-- Reindex if you see performance degradation
-- REINDEX DATABASE CONCURRENTLY your_db_name;

-- Check for long-running transactions (can cause bloat)
SELECT
    pid,
    now() - xact_start AS duration,
    state,
    query
FROM pg_stat_activity
WHERE state != 'idle'
    AND xact_start IS NOT NULL
ORDER BY duration DESC
LIMIT 10;
