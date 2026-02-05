# Deployment Guide: Checkpoint-Resilient Analysis System

This guide covers deploying the checkpoint-based analysis system that survives Railway deployments without losing work.

## Overview

The checkpoint system allows long-running analysis tasks to survive Railway deployments by:
- Saving intermediate state to PostgreSQL at key phases
- Automatically resuming interrupted analyses on worker restart
- Handling SIGTERM gracefully to save checkpoints before shutdown
- Using ARQ (async Redis queue) for persistent job management

## Architecture

```
Frontend → FastAPI → ARQ Queue → ARQ Worker → PostgreSQL
                           ↓
                      Checkpoint Data
                           ↓
                      Resume on Restart
```

### Components

1. **FastAPI API** - Enqueues analysis jobs to ARQ
2. **ARQ Worker** - Processes jobs with checkpoint support
3. **Redis** - Job queue persistence
4. **PostgreSQL** - Checkpoint data storage
5. **Railway** - Container orchestration with 10s shutdown window

## Prerequisites

### Required Services on Railway

1. **PostgreSQL Database**
   - Database with checkpoint fields migrated (see Database Schema below)

2. **Redis Instance**
   - Used for ARQ job queue
   - Must be accessible from both API and worker services

3. **FastAPI Service** (existing)
   - Main API server
   - Enqueues analysis jobs

4. **ARQ Worker Service** (new)
   - Dedicated worker process
   - Runs `start_worker.sh`

### Environment Variables

#### FastAPI Service
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# ARQ/Redis
ARQ_REDIS_URL=redis://redis-host:6379/1
ARQ_TIMEOUT=10
ARQ_KEEP_RESULT=600    # Keep job results for 10 minutes
ARQ_RETRY_JOBS=true    # Retry failed jobs
```

#### ARQ Worker Service
```bash
# Database (same as FastAPI)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# ARQ/Redis (same as FastAPI)
ARQ_REDIS_URL=redis://redis-host:6379/1
ARQ_TIMEOUT=10
ARQ_KEEP_RESULT=600
ARQ_RETRY_JOBS=true

# Worker Configuration
PYTHONUNBUFFERED=1     # Ensure logs are immediately visible
```

## Deployment Steps

### Step 1: Run Database Migration

Apply the checkpoint fields migration:

```bash
# On your local machine or Railway shell
cd backend
python migrations/migration_runner.py
```

This adds:
- `last_checkpoint` - Last completed checkpoint (0-3)
- `checkpoint_data` - JSON blob with intermediate results
- `arq_job_id` - ARQ job ID for tracking
- `attempt_count` - Number of resume attempts
- `updated_at` - Timestamp for staleness detection

### Step 2: Deploy Redis (if not exists)

1. In Railway dashboard, click "+ New"
2. Select "Database" → "Redis"
3. Note the connection URL (e.g., `redis://default:password@host:6379`)
4. Update ARQ_REDIS_URL in both services

### Step 3: Update FastAPI Service

1. Add new environment variables (see above)
2. Redeploy FastAPI service
3. Verify startup logs show "ARQ pool initialized"

### Step 4: Create ARQ Worker Service

**Option A: Railway Template (Recommended)**

1. In Railway dashboard, click "+ New"
2. Select "Empty Service"
3. Connect to same GitHub repo
4. Configure:
   - **Start Command**: `bash backend/start_worker.sh`
   - **Root Directory**: `/`
   - **Environment Variables**: Copy from FastAPI service + worker-specific vars

**Option B: Manual Configuration**

```bash
# Railway.toml (if using)
[build]
builder = "NIXPACKS"
buildCommand = "cd backend && pip install -r requirements.txt"

[deploy]
startCommand = "bash backend/start_worker.sh"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

### Step 5: Verify Deployment

1. **Check Worker Logs**:
   ```
   ✅ ARQ worker starting up
   ✅ SIGTERM handler registered for graceful shutdown
   ✅ Checking for interrupted analyses...
   ✅ ARQ worker startup complete
   ```

2. **Test Analysis Endpoint**:
   ```bash
   curl -X POST https://your-api.railway.app/analyses/run \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"integration_id": 1, "time_range": 30}'
   ```

3. **Monitor Job Progress**:
   - Check analysis status via `/analyses/{analysis_id}` endpoint
   - Look for `arq_job_id` in analysis record
   - Monitor checkpoint progress in `last_checkpoint` field

### Step 6: Test Deployment Resilience

1. Start a long-running analysis (30+ days)
2. Wait for first checkpoint (should happen within 30-60 seconds)
3. Trigger Railway deployment (code push or manual restart)
4. Verify:
   - Worker logs show "Received signal 15 (SIGTERM)"
   - Worker logs show "Waiting up to 8s for checkpoint save"
   - Worker exits cleanly with code 0
   - Analysis resumes automatically on new worker startup
   - Analysis completes without data loss

## Monitoring

### Key Metrics to Track

1. **Checkpoint Progress**
   ```sql
   SELECT id, status, last_checkpoint, attempt_count, created_at, updated_at
   FROM analyses
   WHERE status = 'running'
   ORDER BY updated_at DESC;
   ```

2. **Stale Analyses** (stuck for 30+ minutes)
   ```sql
   SELECT id, status, last_checkpoint, updated_at
   FROM analyses
   WHERE status = 'running'
     AND updated_at < NOW() - INTERVAL '30 minutes';
   ```

3. **Failed Analyses**
   ```sql
   SELECT id, status, error_message, attempt_count
   FROM analyses
   WHERE status = 'failed'
     AND created_at > NOW() - INTERVAL '1 day';
   ```

4. **Resume Success Rate**
   ```sql
   SELECT
     COUNT(*) FILTER (WHERE attempt_count > 0) as resumed_analyses,
     COUNT(*) FILTER (WHERE attempt_count > 0 AND status = 'completed') as successful_resumes,
     COUNT(*) FILTER (WHERE attempt_count > 3) as max_attempts_exceeded
   FROM analyses
   WHERE created_at > NOW() - INTERVAL '7 days';
   ```

### Logs to Monitor

**Worker Startup**:
- Signal handler registration
- Interrupted analysis detection
- Job resumption

**Checkpoint Saves**:
- "CHECKPOINT X: [description]"
- "Checkpoint data saved"
- Any checkpoint errors

**Graceful Shutdown**:
- "Received signal 15 (SIGTERM)"
- "Shutdown requested"
- "Waiting up to 8s for checkpoint save"
- "Exiting (SIGTERM handler)"

**Errors**:
- Checkpoint save failures
- ARQ connection errors
- Database timeout errors
- Analysis failures after max retries

## Troubleshooting

### Worker Won't Start

**Symptoms**: Worker crashes immediately after starting

**Check**:
1. Database connection:
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```
2. Redis connection:
   ```bash
   redis-cli -u $ARQ_REDIS_URL ping
   ```
3. Python dependencies:
   ```bash
   python -c "import arq; print(arq.__version__)"
   ```

**Fix**:
- Verify DATABASE_URL and ARQ_REDIS_URL are correct
- Ensure migrations have been run
- Check Railway service logs for detailed errors

### Analyses Not Resuming

**Symptoms**: Analyses stay in "running" status after deployment

**Check**:
1. Worker startup logs for "Checking for interrupted analyses"
2. Database for stale analyses:
   ```sql
   SELECT * FROM analyses WHERE status = 'running' AND updated_at < NOW() - INTERVAL '10 minutes';
   ```
3. ARQ job IDs match:
   ```sql
   SELECT id, arq_job_id, last_checkpoint FROM analyses WHERE status = 'running';
   ```

**Fix**:
- Manually mark stale analyses as failed:
  ```sql
  UPDATE analyses
  SET status = 'failed', error_message = 'Analysis did not resume after deployment'
  WHERE status = 'running' AND updated_at < NOW() - INTERVAL '1 hour';
  ```
- Restart worker to trigger resume logic

### Checkpoint Data Too Large

**Symptoms**: "Checkpoint data exceeds 5MB limit" errors

**Check**:
```sql
SELECT id, pg_column_size(checkpoint_data) as size_bytes
FROM analyses
WHERE checkpoint_data IS NOT NULL
ORDER BY size_bytes DESC
LIMIT 10;
```

**Fix**:
- Reduce team size or days_back for large analyses
- Check for unnecessary data in checkpoint_data
- Consider increasing MAX_CHECKPOINT_SIZE in checkpoint.py (with caution)

### Worker Killed Before Checkpoint Save

**Symptoms**: Analyses restart from beginning despite checkpoints

**Check**:
- Railway shutdown timeout (should be 10s minimum)
- Worker logs for "Waiting up to 8s for checkpoint save"
- Time between SIGTERM and SIGKILL

**Fix**:
- Ensure Railway has 10s minimum shutdown window
- Reduce SHUTDOWN_TIMEOUT_SECONDS in signal_handler.py if needed (currently 8s)
- Check for database connection latency during checkpoint saves

## Rollback Plan

If issues arise, rollback by:

1. **Disable ARQ Worker**:
   ```bash
   # In Railway dashboard, stop the worker service
   ```

2. **Revert API Changes** (if needed):
   ```bash
   git revert <commit-hash>
   git push
   ```

3. **Clear Stuck Jobs**:
   ```bash
   redis-cli -u $ARQ_REDIS_URL FLUSHDB
   ```

4. **Mark Running Analyses as Failed**:
   ```sql
   UPDATE analyses
   SET status = 'failed',
       error_message = 'System rollback - please rerun analysis'
   WHERE status IN ('running', 'pending');
   ```

## Performance Impact

### Expected Behavior

- **Checkpoint Overhead**: ~100-200ms per checkpoint save (4 checkpoints per analysis)
- **Memory Usage**: +10-50MB per worker for checkpoint data
- **Database Load**: Minimal - 4 checkpoint writes + 1 final write per analysis
- **Resume Time**: 5-10 seconds to resume interrupted analysis
- **Deployment Downtime**: None (workers restart independently)

### Resource Requirements

**ARQ Worker**:
- CPU: 0.5-1 vCPU (scales with concurrent jobs)
- RAM: 512MB-1GB baseline + 50MB per concurrent job
- Network: Low (mostly internal Redis/PostgreSQL)

**Redis**:
- Memory: 256MB minimum (jobs are transient)
- Persistence: Not required (jobs resume from database)

## Security Considerations

1. **Checkpoint Data**:
   - Contains intermediate analysis results (user data)
   - Stored in PostgreSQL with application-level encryption
   - Size-limited to 5MB to prevent DoS

2. **ARQ Job IDs**:
   - Include timestamp to prevent replay attacks
   - Unique per analysis to prevent duplicate processing

3. **Resume Attempts**:
   - Limited to 3 attempts to prevent infinite loops
   - Tracks attempt_count to detect retry bombing

4. **Signal Handling**:
   - Only responds to SIGTERM (safe shutdown)
   - Exits cleanly to prevent zombie processes
   - Does not expose checkpoint data in logs

## Success Criteria

Deployment is successful when:

- ✅ Worker starts and registers signal handler
- ✅ API successfully enqueues ARQ jobs
- ✅ Analyses complete with checkpoints saved
- ✅ Deployments trigger graceful shutdowns
- ✅ Interrupted analyses resume automatically
- ✅ No data loss during deployments
- ✅ 76/76 tests passing
- ✅ Worker logs show clean startup/shutdown

## Support

For issues or questions:

1. Check Railway service logs first
2. Review database state with monitoring queries
3. Verify environment variables match this guide
4. Test with a small analysis (1-7 days) first
5. Escalate to team if issues persist

## Related Documentation

- [Checkpoint System Design](DEPLOYMENT_RESILIENT_ANALYSIS_DESIGN.md)
- [ARQ Documentation](https://arq-docs.helpmanual.io/)
- [Railway Deployment Docs](https://docs.railway.app/deploy/deployments)
- [PostgreSQL Row Locking](https://www.postgresql.org/docs/current/explicit-locking.html)
