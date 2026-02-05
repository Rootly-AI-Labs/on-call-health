# Checkpoint System Deployment Checklist

Use this checklist when deploying the checkpoint-resilient analysis system to production.

## Pre-Deployment

### Code Review
- [ ] All 76 tests passing locally
- [ ] Code reviewed and approved
- [ ] No console.log or debug statements in production code
- [ ] Security review completed (checkpoint data handling, size limits)

### Database
- [ ] Migration file exists: `backend/migrations/2026_01_27_add_checkpoint_fields.sql`
- [ ] Migration tested on dev/staging database
- [ ] Backup of production database taken
- [ ] Migration runner tested: `python migrations/migration_runner.py`

### Dependencies
- [ ] `arq` added to `requirements.txt`
- [ ] Redis instance available on Railway
- [ ] PostgreSQL database accessible
- [ ] All environment variables documented

## Deployment Steps

### 1. Database Migration (15 minutes)
- [ ] Run migration on production:
  ```bash
  python backend/migrations/migration_runner.py
  ```
- [ ] Verify new fields exist:
  ```sql
  \d analyses
  -- Should show: last_checkpoint, checkpoint_data, arq_job_id, attempt_count, updated_at
  ```
- [ ] Check indexes created:
  ```sql
  \di analyses*
  -- Should show indexes on arq_job_id, last_checkpoint, etc.
  ```

### 2. Environment Variables
- [ ] FastAPI service has ARQ variables:
  - `ARQ_REDIS_URL=redis://...`
  - `ARQ_TIMEOUT=10`
  - `ARQ_KEEP_RESULT=600`
  - `ARQ_RETRY_JOBS=true`
- [ ] Worker service has same ARQ variables
- [ ] Worker service has `PYTHONUNBUFFERED=1`

### 3. Deploy FastAPI Service
- [ ] Push code changes to GitHub
- [ ] Railway auto-deploys FastAPI service
- [ ] Verify startup logs show "ARQ pool initialized"
- [ ] Test health endpoint responds
- [ ] No errors in Railway logs

### 4. Create ARQ Worker Service
- [ ] Create new service in Railway dashboard
- [ ] Connect to same GitHub repo
- [ ] Set start command: `bash backend/start_worker.sh`
- [ ] Copy environment variables from FastAPI service
- [ ] Add worker-specific variables
- [ ] Deploy worker service

### 5. Verify Worker Startup
- [ ] Check worker logs for:
  ```
  ✅ ARQ worker starting up
  ✅ SIGTERM handler registered
  ✅ Checking for interrupted analyses...
  ✅ ARQ worker startup complete
  ```
- [ ] No error messages in logs
- [ ] Worker stays running (doesn't crash-loop)
- [ ] Redis connection successful

## Post-Deployment Testing

### Smoke Tests (10 minutes)
- [ ] Start a small analysis (7 days):
  ```bash
  curl -X POST /analyses/run \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"integration_id": 1, "time_range": 7}'
  ```
- [ ] Verify ARQ job enqueued (check `arq_job_id` in database)
- [ ] Monitor analysis progress through checkpoints (0→1→2→3)
- [ ] Analysis completes successfully
- [ ] Results are correct

### Deployment Resilience Test (20 minutes)
- [ ] Start a large analysis (30 days)
- [ ] Wait for checkpoint 1 or 2 (30-90 seconds)
- [ ] Trigger Railway deployment (code push or manual restart)
- [ ] Verify graceful shutdown in logs:
  ```
  Received signal 15 (SIGTERM)
  Shutdown requested (analysis X)
  Waiting up to 8s for checkpoint save...
  Exiting (SIGTERM handler)
  ```
- [ ] New worker starts and resumes analysis
- [ ] Analysis completes without data loss
- [ ] Verify `attempt_count` incremented by 1

### Load Test (30 minutes)
- [ ] Start 5 concurrent analyses
- [ ] Monitor worker logs for checkpoint saves
- [ ] Monitor database for stale analyses
- [ ] All analyses complete successfully
- [ ] No memory leaks or crashes

## Monitoring Setup

### Alerts
- [ ] Set up alert for worker crashes (restart count > 5/hour)
- [ ] Set up alert for stale analyses (running > 30 min)
- [ ] Set up alert for failed analyses (> 10/hour)
- [ ] Set up alert for Redis connection failures

### Dashboards
- [ ] Analysis success/failure rate
- [ ] Checkpoint progress distribution (how many reach each checkpoint)
- [ ] Resume success rate
- [ ] Worker resource usage (CPU, memory)

### Log Aggregation
- [ ] Worker logs forwarded to logging service
- [ ] Checkpoint events tagged for filtering
- [ ] SIGTERM events tagged for monitoring
- [ ] Error logs have proper context

## Rollback Plan

### If Critical Issues Found

**Immediate Actions**:
- [ ] Stop ARQ worker service in Railway
- [ ] Revert FastAPI code changes:
  ```bash
  git revert <commit-hash>
  git push
  ```
- [ ] Mark stuck analyses as failed:
  ```sql
  UPDATE analyses
  SET status = 'failed',
      error_message = 'System rollback - please rerun'
  WHERE status IN ('running', 'pending');
  ```

**Communication**:
- [ ] Notify team in Slack
- [ ] Update status page if customer-facing
- [ ] Document root cause
- [ ] Plan fix and re-deployment

## Success Criteria

Deployment is successful when:

- [ ] All smoke tests pass
- [ ] Deployment resilience test passes
- [ ] No errors in logs for 1 hour
- [ ] Worker stays healthy for 24 hours
- [ ] At least 10 analyses complete successfully
- [ ] At least 1 analysis successfully resumes after deployment
- [ ] Customer feedback is positive

## Post-Launch (Week 1)

### Daily Checks
- [ ] Monitor stale analyses query
- [ ] Check worker uptime and restart count
- [ ] Review failed analysis error messages
- [ ] Check resume success rate
- [ ] Verify no checkpoint data corruption

### Week 1 Review
- [ ] Analyze checkpoint performance metrics
- [ ] Review any customer-reported issues
- [ ] Document lessons learned
- [ ] Plan optimizations if needed

## Documentation

- [ ] DEPLOYMENT_CHECKPOINTS.md shared with team
- [ ] Runbook updated with troubleshooting steps
- [ ] Team trained on monitoring dashboards
- [ ] On-call team briefed on rollback procedures

## Sign-Off

- [ ] Engineering lead approves deployment
- [ ] Database migration reviewed by DBA (if applicable)
- [ ] Security review completed
- [ ] Ready for production deployment

---

**Date Deployed**: _______________
**Deployed By**: _______________
**Notes**: _______________
