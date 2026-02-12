-- Migration: Add organization_id to user_mappings table for multi-tenancy isolation
-- Date: 2026-02-11
-- Purpose: Fix critical security vulnerability where UserMapping queries were not organization-scoped

-- Step 1: Add organization_id column (nullable for existing records)
ALTER TABLE user_mappings
ADD COLUMN organization_id INTEGER;

-- Step 2: Add foreign key constraint
ALTER TABLE user_mappings
ADD CONSTRAINT fk_user_mappings_organization
FOREIGN KEY (organization_id) REFERENCES organizations(id)
ON DELETE CASCADE;

-- Step 3: Backfill organization_id from users table
-- This populates organization_id for all existing UserMapping records
UPDATE user_mappings um
SET organization_id = u.organization_id
FROM users u
WHERE um.user_id = u.id
AND um.organization_id IS NULL;

-- Step 4: Add index for efficient organization-scoped queries
CREATE INDEX ix_user_mapping_org_user ON user_mappings(organization_id, user_id);

-- Step 5: Log migration results
DO $$
DECLARE
    total_count INTEGER;
    updated_count INTEGER;
    null_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_count FROM user_mappings;
    SELECT COUNT(*) INTO updated_count FROM user_mappings WHERE organization_id IS NOT NULL;
    SELECT COUNT(*) INTO null_count FROM user_mappings WHERE organization_id IS NULL;

    RAISE NOTICE 'Migration completed:';
    RAISE NOTICE '  Total UserMapping records: %', total_count;
    RAISE NOTICE '  Records with organization_id: %', updated_count;
    RAISE NOTICE '  Records with NULL organization_id: %', null_count;

    IF null_count > 0 THEN
        RAISE WARNING 'Found % records with NULL organization_id - these may be orphaned records', null_count;
    END IF;
END $$;
