# UUID Migration Guide - Production Railway Database

## Overview
This guide walks through safely adding UUID support to the existing analyses table in Railway's PostgreSQL database.

## Files Created
- `safe_uuid_migration.py` - Ultra-safe migration script with comprehensive error handling
- `run_uuid_migration.py` - Railway-specific runner
- `UUID_MIGRATION_README.md` - This guide

## Migration Steps

### Phase 1: Database Migration (Ultra-Safe)

**⚠️ IMPORTANT: Do this on Railway production console**

1. **Access Railway Console**:
   ```bash
   # Option 1: Railway CLI
   railway shell
   
   # Option 2: Railway Web Console
   # Go to project → Environment → Console tab
   ```

2. **Run the Migration**:
   ```bash
   cd backend
   python run_uuid_migration.py
   ```

3. **What the Migration Does**:
   - ✅ Adds UUID column to analyses table (nullable initially)
   - ✅ Populates ALL existing analyses with unique UUIDs
   - ✅ Sets UUID column to NOT NULL
   - ✅ Creates unique index on UUID column
   - ✅ Verifies success before committing
   - ✅ Rolls back automatically if anything fails

### Phase 2: Code Updates

**After migration succeeds on Railway**:

1. **Uncomment UUID in Model**:
   ```python
   # In backend/app/models/analysis.py line 14:
   # Change this:
   # uuid = Column(String(36), unique=True, index=True, nullable=True, default=lambda: str(uuid.uuid4()))  # Commented until Railway migration
   
   # To this:
   uuid = Column(String(36), unique=True, index=True, nullable=True, default=lambda: str(uuid.uuid4()))
   ```

2. **Deploy Backend Changes**:
   ```bash
   git add backend/app/models/analysis.py
   git commit -m "Enable UUID column in Analysis model after Railway migration"
   git push origin main
   ```

### Phase 3: API Updates (Backend)

Update API endpoints to handle both UUID and integer IDs:

```python
# In backend/app/api/endpoints/analyses.py
def get_analysis_safely(identifier: str, db: Session):
    """Safely handle both UUID and integer ID"""
    # UUID detection (safer than just checking dashes)
    if len(identifier) >= 32 and '-' in identifier:
        return db.query(Analysis).filter(Analysis.uuid == identifier).first()
    else:
        try:
            int_id = int(identifier)
            return db.query(Analysis).filter(Analysis.id == int_id).first()
        except ValueError:
            return None
```

### Phase 4: Frontend Updates

Frontend will automatically work with both ID types through existing API endpoints.

## Safety Features

### Pre-Migration Checks
- ✅ Verifies database connection
- ✅ Checks current table state
- ✅ Counts existing analyses
- ✅ Identifies what needs to be done

### During Migration
- ✅ Uses database transactions (atomic operations)
- ✅ Progress indicators for large datasets
- ✅ Comprehensive error handling
- ✅ Automatic rollback on failure

### Post-Migration Verification
- ✅ Verifies all analyses have UUIDs
- ✅ Confirms constraints are in place
- ✅ Validates data integrity

### Rollback Plan
If something goes wrong after deployment:

```sql
-- Emergency rollback (removes UUID column entirely)
BEGIN;
ALTER TABLE analyses DROP COLUMN uuid;
DROP INDEX IF EXISTS idx_analyses_uuid;
COMMIT;
```

## Expected Results

### Before Migration
- Table: `analyses` with columns: `id`, `user_id`, `status`, `results`, etc.
- URLs: `?analysis=123`

### After Migration
- Table: `analyses` with additional `uuid` column
- All existing analyses have UUIDs populated
- URLs work with both: `?analysis=123` AND `?analysis=550e8400-e29b-41d4-a716-446655440000`

## Testing Plan

1. **After Migration**:
   - Verify existing integer URLs still work: `?analysis=123`
   - Verify new UUID URLs work: `?analysis=uuid-here`
   - Verify auto-redirect works for both ID types

2. **After Code Deployment**:
   - Test creating new analyses (should get UUIDs automatically)
   - Test that sharing UUID URLs works between users
   - Monitor for any errors in logs

## Troubleshooting

### Migration Fails
1. Check error message from migration script
2. Verify DATABASE_URL is set correctly
3. Ensure Railway console has proper permissions
4. Check database connection

### After Migration Issues
1. Check that UUID column exists: `\d analyses` in Railway PostgreSQL console
2. Verify UUIDs are populated: `SELECT COUNT(*) FROM analyses WHERE uuid IS NOT NULL;`
3. Check unique constraint: `\d+ analyses`

### Rollback Required
If major issues occur, uncomment the UUID line in the model and redeploy to disable UUID functionality.

## Success Criteria

✅ Migration completes without errors  
✅ All existing analyses have UUIDs  
✅ New analyses get UUIDs automatically  
✅ Both integer and UUID URLs work  
✅ No existing functionality broken  
✅ Shareable UUID URLs work properly  

## Commands Summary

```bash
# 1. Run migration on Railway
railway shell
cd backend
python run_uuid_migration.py

# 2. After migration succeeds, update code
# Uncomment UUID line in backend/app/models/analysis.py

# 3. Deploy
git add backend/app/models/analysis.py
git commit -m "Enable UUID column after Railway migration"
git push origin main
```