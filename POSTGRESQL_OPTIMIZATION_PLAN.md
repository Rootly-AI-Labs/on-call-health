# PostgreSQL Optimization Plan for Railway

## Issues Identified

### 1. **Collation Version Mismatch** (HIGH PRIORITY)
- **Issue:** Database created with collation 2.36, OS provides 2.41
- **Impact:** Affects text sorting/indexing, potential query inconsistencies
- **Fix:** Run `ALTER DATABASE postgres REFRESH COLLATION VERSION;`
- **Effort:** 1 minute
- **Risk:** Low

### 2. **Slow Data Fetching** (HIGH PRIORITY)
- **Issue:** Analysis data fetch taking 9.38s for 41 users
- **Impact:** Users waiting 28+ seconds for analysis
- **Fixes:**
  - ✅ Fixed N+1 query in `get_member_surveys` (16 queries → 2)
  - ⏳ Add composite indexes on frequently queried columns
  - ⏳ Enable connection pooling if not already enabled
- **Effort:** 30 minutes
- **Risk:** Low (indexes are safe)

### 3. **Missing Query Performance Monitoring** (MEDIUM PRIORITY)
- **Issue:** `pg_stat_statements` extension not available
- **Impact:** Can't identify slow queries without it
- **Fix:** Enable extension (may require Railway support ticket)
- **Effort:** 5 minutes (if we have permissions)
- **Risk:** None

### 4. **No Index Usage Statistics** (LOW PRIORITY)
- **Issue:** Don't know which indexes are actually being used
- **Impact:** May have unused indexes wasting space
- **Fix:** Run diagnostic queries in `postgresql_optimization.sql`
- **Effort:** 10 minutes
- **Risk:** None (read-only queries)

## Optimization Steps

### Immediate (Do Today)

1. **Fix Collation Mismatch**
   ```sql
   ALTER DATABASE postgres REFRESH COLLATION VERSION;
   ```

2. **Check Database Stats**
   - Run sections 2-4 of `postgresql_optimization.sql`
   - Identify largest tables and missing indexes

3. **Create Missing Indexes** (if needed)
   ```sql
   CREATE INDEX CONCURRENTLY idx_analyses_user_id_status
       ON analyses(user_id, status);

   CREATE INDEX CONCURRENTLY idx_burnout_reports_email_submitted
       ON user_burnout_reports(email, submitted_at DESC);
   ```

### Short-term (This Week)

4. **Enable pg_stat_statements**
   - Check if we can enable it ourselves
   - Otherwise, contact Railway support

5. **Vacuum Analysis**
   - Check for bloated tables (section 6)
   - Run VACUUM ANALYZE on tables with >10% dead tuples

6. **Monitor Query Performance**
   - After enabling pg_stat_statements, identify queries >500ms
   - Add indexes or optimize queries as needed

### Long-term (Next Sprint)

7. **Connection Pooling**
   - Verify Railway PostgreSQL has pooling enabled
   - Consider adding pgBouncer if needed

8. **Database Upgrade**
   - Check current PostgreSQL version
   - Upgrade to latest stable if on old version

9. **Automated Maintenance**
   - Set up scheduled VACUUM ANALYZE
   - Monitor index bloat weekly

## Expected Impact

| Optimization | Current | Expected | Improvement |
|--------------|---------|----------|-------------|
| Data fetch | 9.38s | 2-3s | 70% faster |
| Analysis total | 28.46s | 15-18s | 40% faster |
| AI enhancement | 15.81s | 10-12s* | 25% faster |

*AI enhancement requires code optimization (Task #4), not just DB

## Monitoring

After optimizations, monitor these metrics:

1. **Query Performance**
   - `get_member_surveys`: Should be <500ms
   - `list_analyses`: Should be <200ms
   - `get_notifications`: Already at 281ms (good)

2. **Database Size**
   - Track growth weekly
   - Alert if >80% of Railway plan limit

3. **Connection Count**
   - Should stay under Railway limit
   - Alert if approaching limit

## Railway-Specific Notes

- Railway auto-vacuums and auto-analyzes by default
- Default shared_buffers may be small (check with Railway)
- Connection limit depends on plan (check current usage)
- Consider upgrading PostgreSQL plan if consistently slow

## Next Steps

1. ✅ Run `ALTER DATABASE postgres REFRESH COLLATION VERSION;`
2. ✅ Run diagnostic queries from `postgresql_optimization.sql`
3. Share results and we'll create targeted indexes
4. Monitor performance after N+1 fix is deployed
