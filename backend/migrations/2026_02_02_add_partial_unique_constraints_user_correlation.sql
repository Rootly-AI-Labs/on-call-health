-- Migration: Add partial unique constraints for UserCorrelation to prevent duplicates
-- Date: 2026-02-02
--
-- Problem:
-- The existing unique constraint uq_user_correlation_user_email UNIQUE (user_id, email)
-- doesn't prevent duplicates in multi-tenant mode where user_id IS NULL.
-- Team members (user_id=NULL) can have duplicate (organization_id, email) rows.
--
-- Solution:
-- Add partial unique indexes to enforce uniqueness for both cases:
-- 1. Multi-tenant: UNIQUE (organization_id, email) WHERE user_id IS NULL
-- 2. Personal: UNIQUE (user_id, email) WHERE user_id IS NOT NULL

-- Step 1: Check for and merge existing duplicates before adding constraints
-- This prevents migration failure if duplicates already exist.

DO $$
DECLARE
    dup_record RECORD;
    keep_id INTEGER;
    dup_count INTEGER := 0;
BEGIN
    -- Find and merge duplicates in multi-tenant mode (organization_id, email where user_id IS NULL)
    FOR dup_record IN
        SELECT organization_id, email, array_agg(id ORDER BY created_at DESC) as ids
        FROM user_correlations
        WHERE user_id IS NULL AND organization_id IS NOT NULL
        GROUP BY organization_id, email
        HAVING COUNT(*) > 1
    LOOP
        -- Keep the first ID (most recent by created_at)
        keep_id := dup_record.ids[1];
        dup_count := dup_count + 1;

        RAISE NOTICE 'Merging % duplicates for org=% email=%: keeping id=%',
            array_length(dup_record.ids, 1), dup_record.organization_id, dup_record.email, keep_id;

        -- Update survey_periods to reference the kept record
        UPDATE survey_periods
        SET user_correlation_id = keep_id
        WHERE user_correlation_id = ANY(dup_record.ids[2:array_length(dup_record.ids, 1)]);

        -- Merge integration_ids arrays from duplicates into kept record
        UPDATE user_correlations
        SET integration_ids = (
            SELECT ARRAY(
                SELECT DISTINCT unnest(integration_ids)
                FROM user_correlations
                WHERE id = ANY(dup_record.ids)
                AND integration_ids IS NOT NULL
            )
        )
        WHERE id = keep_id;

        -- Delete duplicate records (keep the first one)
        DELETE FROM user_correlations
        WHERE id = ANY(dup_record.ids[2:array_length(dup_record.ids, 1)]);
    END LOOP;

    -- Find and merge duplicates in personal mode (user_id, email where user_id IS NOT NULL)
    FOR dup_record IN
        SELECT user_id, email, array_agg(id ORDER BY created_at DESC) as ids
        FROM user_correlations
        WHERE user_id IS NOT NULL
        GROUP BY user_id, email
        HAVING COUNT(*) > 1
    LOOP
        -- Keep the first ID (most recent by created_at)
        keep_id := dup_record.ids[1];
        dup_count := dup_count + 1;

        RAISE NOTICE 'Merging % duplicates for user_id=% email=%: keeping id=%',
            array_length(dup_record.ids, 1), dup_record.user_id, dup_record.email, keep_id;

        -- Update survey_periods to reference the kept record
        UPDATE survey_periods
        SET user_correlation_id = keep_id
        WHERE user_correlation_id = ANY(dup_record.ids[2:array_length(dup_record.ids, 1)]);

        -- Merge integration_ids arrays from duplicates into kept record
        UPDATE user_correlations
        SET integration_ids = (
            SELECT ARRAY(
                SELECT DISTINCT unnest(integration_ids)
                FROM user_correlations
                WHERE id = ANY(dup_record.ids)
                AND integration_ids IS NOT NULL
            )
        )
        WHERE id = keep_id;

        -- Delete duplicate records (keep the first one)
        DELETE FROM user_correlations
        WHERE id = ANY(dup_record.ids[2:array_length(dup_record.ids, 1)]);
    END LOOP;

    IF dup_count > 0 THEN
        RAISE NOTICE 'Merged and cleaned up % duplicate groups', dup_count;
    ELSE
        RAISE NOTICE 'No duplicates found - database is clean';
    END IF;
END $$;

-- Step 2: Drop the old constraint if it exists
-- The old constraint UNIQUE (user_id, email) doesn't properly handle NULL user_id cases
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_user_correlation_user_email'
    ) THEN
        ALTER TABLE user_correlations
        DROP CONSTRAINT uq_user_correlation_user_email;
        RAISE NOTICE 'Dropped old constraint uq_user_correlation_user_email';
    END IF;
END $$;

-- Step 3: Create partial unique index for multi-tenant mode (org-scoped roster)
-- This prevents duplicate team members within an organization
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_correlation_org_email_null_user
ON user_correlations (organization_id, email)
WHERE user_id IS NULL;

-- Step 4: Create partial unique index for personal mode (user-scoped)
-- This prevents duplicate correlations for a specific user's personal records
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_correlation_user_email_not_null
ON user_correlations (user_id, email)
WHERE user_id IS NOT NULL;

-- Step 5: Verify constraints are in place
DO $$
DECLARE
    org_index_exists BOOLEAN;
    user_index_exists BOOLEAN;
BEGIN
    -- Check if org-scoped index exists
    SELECT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'uq_user_correlation_org_email_null_user'
    ) INTO org_index_exists;

    -- Check if user-scoped index exists
    SELECT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'uq_user_correlation_user_email_not_null'
    ) INTO user_index_exists;

    IF org_index_exists AND user_index_exists THEN
        RAISE NOTICE '✅ Both partial unique indexes are in place';
    ELSE
        RAISE WARNING '⚠️ One or both partial unique indexes are missing!';
    END IF;
END $$;
