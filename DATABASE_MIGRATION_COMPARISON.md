# Database Schema Comparison: Main vs Dev

**Generated**: 2025-10-03
**Last Updated**: 2025-10-06
**Purpose**: Ensure all migration scripts are in place before merging dev → main

---

## 🆕 Recent Updates (Since 2025-10-03)

### New Migrations Added to migration_runner.py:
1. **Migration 003**: `add_name_to_user_correlations` ✅
   - Adds `name VARCHAR(255)` to user_correlations table

2. **Migration 004**: `add_integration_ids_to_user_correlations` ✅
   - Adds `integration_ids JSON` to user_correlations table

3. **Migration 005**: `add_personal_circumstances_to_reports` ✅
   - Adds `personal_circumstances TEXT` to user_burnout_reports table

4. **Migration 006**: `make_slack_user_id_nullable` ✅
   - Makes `slack_user_id` nullable in slack_integrations table
   - Required for OAuth bot tokens which don't have a specific user ID

### Backend Service Updates:
- ✅ Added user notification system for Slack DM surveys (2025-10-06)
  - Users receive in-app notifications when they get automated survey DMs
  - Different messages for initial surveys vs reminders
- ✅ Fixed Slack OAuth disconnect flow (2025-10-06)
  - Now properly marks workspace_mapping as disconnected
  - Fixed double-disconnect bug
  - Improved loading states and removed page reloads
- ✅ Optimized OAuth verification polling (2025-10-06)
  - Reduced interval from 1000ms to 500ms
  - Added localStorage persistence across OAuth redirect
- ✅ Reduced backend logging verbosity for production (2025-10-06)
  - Added LOG_LEVEL environment variable support
- ✅ Fixed analysis 404 errors (2025-10-06)
  - Added organization_id field to analyses on creation
  - **Disabled organization_id filtering to avoid prod regressions**
  - Analyses now filter by user_id only (original behavior)
  - Multi-tenant filtering can be re-enabled later when stable

---

## 📊 Summary

### New Tables in Dev (6)
1. `organizations` - Multi-tenant organization management
2. `organization_invitations` - Invitation system for shared domain emails
3. `user_notifications` - In-app notification system
4. `user_burnout_reports` - Survey responses (decoupled from analyses)
5. `slack_workspace_mappings` - Slack workspace to org mapping
6. `survey_schedules` - Automated survey scheduling

### Modified Tables (4)
1. `users` - Added org relationship and role management
2. `user_correlations` - Added multi-tenancy support, name field, and integration_ids
3. `analyses` - Added organization_id (field exists but not used for filtering yet)
4. `slack_integrations` - Added workspace fields, made slack_user_id nullable

---

## 🆕 New Tables Schema

### 1. `organizations`
```sql
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    primary_contact_email VARCHAR(255),
    billing_email VARCHAR(255),
    website VARCHAR(255),
    plan_type VARCHAR(50) DEFAULT 'free',
    max_users INTEGER DEFAULT 50,
    max_analyses_per_month INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    settings JSON
);

CREATE INDEX idx_organizations_domain ON organizations(domain);
CREATE INDEX idx_organizations_slug ON organizations(slug);
```

**Migration**: Created by SQLAlchemy auto-migration via `create_tables()`

---

### 2. `organization_invitations`
```sql
CREATE TABLE organization_invitations (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    email VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    invited_by INTEGER REFERENCES users(id),
    token VARCHAR(255) UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    used_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_organization_invitations_email ON organization_invitations(email);
CREATE INDEX idx_organization_invitations_token ON organization_invitations(token);
```

**Migration**: Created by SQLAlchemy auto-migration via `create_tables()`

---

### 3. `user_notifications`
```sql
CREATE TABLE user_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'general',
    priority VARCHAR(20) DEFAULT 'normal',
    status VARCHAR(20) DEFAULT 'unread',
    action_url VARCHAR(500),
    action_label VARCHAR(100),
    metadata JSON,
    expires_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_notifications_user_id ON user_notifications(user_id);
CREATE INDEX idx_user_notifications_status ON user_notifications(status);
CREATE INDEX idx_user_notifications_created_at ON user_notifications(created_at DESC);
```

**Migration**: Created by SQLAlchemy auto-migration via `create_tables()`

---

### 4. `user_burnout_reports`
```sql
CREATE TABLE user_burnout_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    organization_id INTEGER REFERENCES organizations(id),
    slack_user_id VARCHAR(50),
    self_reported_score INTEGER,
    energy_level VARCHAR(20),
    work_life_balance VARCHAR(20),
    workload_level VARCHAR(20),
    stress_factors TEXT,
    comments TEXT,
    personal_circumstances TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_burnout_reports_user_id ON user_burnout_reports(user_id);
CREATE INDEX idx_user_burnout_reports_org_id ON user_burnout_reports(organization_id);
CREATE INDEX idx_user_burnout_reports_slack_user_id ON user_burnout_reports(slack_user_id);
```

**Migration Script**: `migrate_user_burnout_reports.py`

---

### 5. `slack_workspace_mappings`
```sql
CREATE TABLE slack_workspace_mappings (
    id SERIAL PRIMARY KEY,
    workspace_id VARCHAR(50) UNIQUE NOT NULL,
    workspace_name VARCHAR(255),
    organization_id INTEGER REFERENCES organizations(id),
    owner_user_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'active',
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_slack_workspace_mappings_workspace_id ON slack_workspace_mappings(workspace_id);
CREATE INDEX idx_slack_workspace_mappings_org_id ON slack_workspace_mappings(organization_id);
```

**Migration Script**: `migrate_slack_workspace_mappings.py`

---

### 6. `survey_schedules`
```sql
CREATE TABLE survey_schedules (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER UNIQUE REFERENCES organizations(id),
    enabled BOOLEAN DEFAULT FALSE,
    send_time TIME NOT NULL,
    timezone VARCHAR(100) NOT NULL,
    send_weekdays_only BOOLEAN DEFAULT TRUE,
    send_reminder BOOLEAN DEFAULT FALSE,
    reminder_hours_after INTEGER DEFAULT 5,
    last_sent_at TIMESTAMP WITH TIME ZONE,
    next_send_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_survey_schedules_organization_id ON survey_schedules(organization_id);
CREATE INDEX idx_survey_schedules_next_send_at ON survey_schedules(next_send_at);
```

**Migration**: Created by SQLAlchemy auto-migration via `create_tables()`

---

## 🔧 Modified Tables

### `users` table
**New Columns:**
```sql
ALTER TABLE users ADD COLUMN organization_id INTEGER REFERENCES organizations(id);
ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user';
ALTER TABLE users ADD COLUMN joined_org_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE users ADD COLUMN last_active_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active';
```

**Migration**: Created by organization migration scripts (`migrate_organizations*.py`)

**Status**: ✅ Likely already applied in production (org feature was merged ~4 weeks ago)

---

### `user_correlations` table ⚠️ **CRITICAL**
**New Columns:**
```sql
ALTER TABLE user_correlations ADD COLUMN organization_id INTEGER;
ALTER TABLE user_correlations ADD COLUMN name VARCHAR(255);
ALTER TABLE user_correlations ADD COLUMN integration_ids JSON;

-- Foreign key constraint
ALTER TABLE user_correlations
ADD CONSTRAINT fk_user_correlations_organization
FOREIGN KEY (organization_id) REFERENCES organizations(id);

-- Indexes for multi-tenancy
CREATE INDEX idx_user_correlations_organization_id ON user_correlations(organization_id);
CREATE INDEX idx_user_correlations_org_email ON user_correlations(organization_id, email);
CREATE INDEX idx_user_correlations_org_slack ON user_correlations(organization_id, slack_user_id) WHERE slack_user_id IS NOT NULL;
```

**Migration**:
- ✅ Automated via `migration_runner.py` - Migration #002
- ✅ Backfills `organization_id` from `users.organization_id`
- ✅ Run automatically on app startup

**Status**: ❌ **NEW TODAY** - Not in production yet

---

### `analyses` table
**New Columns:**
```sql
ALTER TABLE analyses ADD COLUMN organization_id INTEGER REFERENCES organizations(id);
ALTER TABLE analyses ADD COLUMN integration_name VARCHAR(255);
ALTER TABLE analyses ADD COLUMN platform VARCHAR(50);
```

**Migration**: Migration #001 in `migration_runner.py` (integration fields)

**Status**: ⚠️ Unknown - Need to verify in production

---

### `slack_integrations` table
**New Columns:**
```sql
ALTER TABLE slack_integrations ADD COLUMN workspace_id VARCHAR(50);
ALTER TABLE slack_integrations ADD COLUMN workspace_name VARCHAR(255);
ALTER TABLE slack_integrations ADD COLUMN connection_type VARCHAR(20);
ALTER TABLE slack_integrations ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
```

**Migration**: Applied via SQLAlchemy auto-migration

**Status**: ⚠️ Unknown - Need to verify in production

---

## 🎯 Migration Scripts Inventory

### Automated Migrations (Run on Startup)
Located in: `backend/migrations/migration_runner.py`

1. ✅ **Migration 001**: `add_integration_fields_to_analyses`
   - Adds `integration_name`, `platform` to analyses
   - Status: Likely already applied

2. ⚠️ **Migration 002**: `add_organization_id_to_user_correlations`
   - Adds `organization_id` column
   - Creates FK and indexes
   - Backfills from users table
   - **Status**: NEW TODAY - Will run on next deploy

### Manual Migration Scripts
Located in: `backend/`

1. ✅ `migrate_organizations.py` - Full org migration with data population
2. ✅ `migrate_organizations_mvp.py` - MVP version
3. ✅ `migrate_organizations_secure.py` - Schema only, no data (**RECOMMENDED**)
4. ✅ `migrate_slack_workspace_mappings.py` - Slack workspace mapping
5. ✅ `migrate_user_burnout_reports.py` - Survey response migration
6. ⚠️ `add_integration_id_to_user_correlations.py` - Adds integration_ids JSON field
7. ⚠️ `add_name_to_user_correlation.py` - Adds name field
8. ⚠️ `add_personal_circumstances_column.py` - Adds field to burnout reports
9. ⚠️ `add_unique_constraint_user_correlation.py` - Adds unique constraint

### Fix/Utility Scripts
10. `fix_organization_status_none.py` - Fixes NULL status values
11. `promote_user_to_admin.py` - Manual user role promotion
12. `check_slack_mappings.py` - Diagnostic script
13. `update_survey_messages.py` - Updates survey message text

### SQL Files
14. `add_organization_id_to_user_correlations.sql` - Manual SQL version of migration 002
15. `fix_organization_status.sql` - Status fix SQL
16. `fix_slack_workspace.sql` - Slack fix SQL
17. `workspace_mappings.sql` - Workspace mapping SQL

---

## ✅ Migration Gaps Analysis (RESOLVED)

### Previously Missing Migrations - Now Added ✅

All schema changes are now properly tracked in `migration_runner.py`:

1. **`user_correlations.name`** ✅ ADDED
   - Migration 003: `add_name_to_user_correlations`
   - Status: In migration_runner.py

2. **`user_correlations.integration_ids`** ✅ ADDED
   - Migration 004: `add_integration_ids_to_user_correlations`
   - Status: In migration_runner.py

3. **`user_burnout_reports.personal_circumstances`** ✅ ADDED
   - Migration 005: `add_personal_circumstances_to_reports`
   - Status: In migration_runner.py

4. **`slack_integrations.slack_user_id` nullable** ✅ ADDED
   - Migration 006: `make_slack_user_id_nullable`
   - Status: In migration_runner.py

5. **New table creations** ✅
   - Migration 001b: `create_organizations_tables`
   - Handles all organization-related table creation
   - SQLAlchemy `create_tables()` as fallback

---

## 🔍 Pre-Merge Verification Queries

Run these on **PRODUCTION** to check current state:

```sql
-- 1. Check if organizations exist
SELECT
    EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'organizations') as orgs_exist,
    EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'user_notifications') as notifications_exist,
    EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'survey_schedules') as schedules_exist,
    EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'user_burnout_reports') as reports_exist,
    EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'slack_workspace_mappings') as slack_mappings_exist;

-- 2. Check users columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name IN ('organization_id', 'role', 'joined_org_at', 'status')
ORDER BY column_name;

-- 3. Check user_correlations columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'user_correlations'
AND column_name IN ('organization_id', 'name', 'integration_ids')
ORDER BY column_name;

-- 4. Check analyses columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'analyses'
AND column_name IN ('organization_id', 'integration_name', 'platform')
ORDER BY column_name;

-- 5. Check migrations table
SELECT name, applied_at, status
FROM migrations
ORDER BY applied_at DESC;

-- 6. Count data integrity
SELECT
    (SELECT COUNT(*) FROM users WHERE organization_id IS NULL) as users_no_org,
    (SELECT COUNT(*) FROM user_correlations WHERE organization_id IS NULL) as correlations_no_org,
    (SELECT COUNT(*) FROM organizations) as total_orgs;
```

---

## ✅ Recommended Actions

### Before Merge:

1. **Run production verification queries above** ✓
2. **Backup production database** ✓
3. ~~**Add missing migrations to migration_runner.py**~~ ✅ **COMPLETED**
   - All migrations 003-006 have been added to migration_runner.py

4. **Test merge locally**:
   ```bash
   git checkout -b test-merge main
   git merge dev --no-commit
   # Review conflicts
   git merge --abort
   ```

### After Merge:

1. Monitor Railway deployment logs for migration status
2. Run verification queries again
3. Test critical flows:
   - User login
   - Slack connection
   - Survey delivery
   - Beta token sync

---

## 🎯 Expected Production State

Based on git history analysis:

| Feature | Production Status |
|---------|------------------|
| Organizations table | ✅ EXISTS (merged ~4 weeks ago) |
| Users.organization_id | ✅ EXISTS |
| Users.role | ✅ EXISTS |
| UserCorrelations.organization_id | ❌ MISSING (added today) |
| UserCorrelations.name | ⚠️ UNKNOWN |
| UserCorrelations.integration_ids | ⚠️ UNKNOWN |
| Analyses.organization_id | ⚠️ UNKNOWN |
| Survey schedules | ⚠️ UNKNOWN |
| User burnout reports | ⚠️ UNKNOWN |
| Slack workspace mappings | ⚠️ UNKNOWN |
| User notifications | ⚠️ UNKNOWN |

---

## 🚨 Critical Migration: organization_id to user_correlations

**This is the most important migration added today.**

**What it does:**
1. Adds `organization_id` column to `user_correlations`
2. Backfills values from `users.organization_id`
3. Creates indexes for multi-tenancy queries

**Why it's critical:**
- ALL Slack survey queries now filter by `organization_id`
- ALL beta token syncs now scope by `organization_id`
- Without this, surveys will fail

**Rollback plan:**
```sql
-- If needed, remove the column
ALTER TABLE user_correlations DROP COLUMN IF EXISTS organization_id CASCADE;
DROP INDEX IF EXISTS idx_user_correlations_organization_id;
DROP INDEX IF EXISTS idx_user_correlations_org_email;
DROP INDEX IF EXISTS idx_user_correlations_org_slack;
```

---

## 📊 Migration Execution Order

When merge happens, migrations will run in this order:

1. Migration 001 - Analyses integration fields
2. Migration 001b - Create all organization-related tables ⭐
3. Migration 002 - UserCorrelations organization_id ⭐ **CRITICAL**
4. Migration 003 - UserCorrelations name field
5. Migration 004 - UserCorrelations integration_ids field
6. Migration 005 - UserBurnoutReports personal_circumstances field
7. Migration 006 - Slack slack_user_id nullable ⭐

**Total migrations**: 6 (not 7 - migration 007 was removed)
**Total estimated time**: 60-90 seconds (depending on data volume)

---

## ✅ Success Criteria

After merge and deployment:

- [ ] All 6 new tables exist in production
- [ ] All 6 migrations (001, 001b, 002, 003, 004, 005, 006) show as "completed"
- [ ] `user_correlations.organization_id` is populated for 95%+ of records
- [ ] `user_correlations.name` column exists
- [ ] `user_correlations.integration_ids` column exists
- [ ] `user_burnout_reports.personal_circumstances` column exists
- [ ] `slack_integrations.slack_user_id` is nullable
- [ ] `analyses.organization_id` column exists (but not used for filtering)
- [ ] No SQL errors in deployment logs
- [ ] Users can log in and access dashboard
- [ ] **Analyses can be created and retrieved without 404 errors** ⭐
- [ ] Slack OAuth connect/disconnect works in single attempt
- [ ] Slack surveys work end-to-end with user notifications
- [ ] Beta tokens can sync users
- [ ] No duplicate user_correlations per organization

---

**Last Updated**: 2025-10-06
**Generated by**: Claude Code Database Analysis
