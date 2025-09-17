# Database Migration System

This directory contains the database migration system for the Rootly Burnout Detector backend.

## How It Works

1. **Automatic Migrations**: Migrations run automatically on every Railway deployment
2. **Migration Tracking**: Each migration is tracked in a `migrations` table to prevent re-running
3. **Safe Execution**: Migrations use `IF NOT EXISTS` clauses to avoid errors on re-runs
4. **Ordered Execution**: Migrations run in numerical order (001, 002, 003, etc.)

## Files

- `migration_runner.py` - Main migration system that runs all pending migrations
- `README.md` - This documentation file

## Current Migrations

### 001_add_integration_fields_to_analyses
**Status**: ✅ Ready to deploy
**Description**: Adds `integration_name` and `platform` columns to the analyses table
**SQL**:
```sql
ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS integration_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS platform VARCHAR(50)
```

## Adding New Migrations

1. Edit `migration_runner.py`
2. Add a new migration object to the `migrations` list:

```python
{
    "name": "002_your_migration_name",
    "description": "Brief description of what this migration does",
    "sql": [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS new_field VARCHAR(100)",
        "CREATE INDEX IF NOT EXISTS idx_users_new_field ON users(new_field)"
    ]
}
```

3. Use incrementing numbers (002, 003, 004, etc.)
4. Always use `IF NOT EXISTS` or `IF EXISTS` clauses for safety
5. Test locally before deploying

## Manual Migration Execution

To run migrations manually (useful for immediate fixes):

```bash
# From the backend directory
python run_migrations.py
```

Or on Railway:
```bash
railway run python run_migrations.py
```

## Migration Status

To check which migrations have been applied:

```python
from migrations.migration_runner import MigrationRunner
runner = MigrationRunner()
runner.get_migration_status()
runner.close()
```

## Safety Features

- ✅ Migrations table automatically created
- ✅ Each migration tracked to prevent re-running
- ✅ Database connection retry logic
- ✅ Graceful error handling
- ✅ IF NOT EXISTS clauses to prevent conflicts
- ✅ Continues startup even if migrations fail

## Deployment Flow

1. **Railway Deployment Starts**
2. **Database Connection** - Waits up to 60 seconds for DB
3. **Migration System** - Creates migrations table if needed
4. **Run Migrations** - Applies all pending migrations in order
5. **Table Creation** - Ensures all app tables exist
6. **Start Application** - Launches FastAPI server

The entire process is logged so you can see what happened in the Railway deployment logs.