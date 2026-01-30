-- Migration: Add unique constraint on organization_id to survey_schedules
-- Description: Ensure only one survey schedule per organization to prevent duplicate survey sends
-- Date: 2026-01-30

-- Check if constraint already exists
DO $$
BEGIN
    -- Add unique constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_survey_schedules_organization_id'
    ) THEN
        -- First, check for and handle any duplicate schedules
        -- Keep the most recently created schedule for each org
        WITH duplicates AS (
            SELECT
                id,
                organization_id,
                ROW_NUMBER() OVER (PARTITION BY organization_id ORDER BY created_at DESC, id DESC) as rn
            FROM survey_schedules
        )
        DELETE FROM survey_schedules
        WHERE id IN (
            SELECT id FROM duplicates WHERE rn > 1
        );

        -- Now add the unique constraint
        ALTER TABLE survey_schedules
        ADD CONSTRAINT uq_survey_schedules_organization_id
        UNIQUE (organization_id);

        RAISE NOTICE 'Added unique constraint on survey_schedules.organization_id';
    ELSE
        RAISE NOTICE 'Unique constraint already exists on survey_schedules.organization_id';
    END IF;
END $$;

-- Create index for faster lookups (if not exists)
CREATE INDEX IF NOT EXISTS idx_survey_schedules_organization_id
ON survey_schedules(organization_id);

-- Rollback instructions:
-- To rollback this migration, run:
-- ALTER TABLE survey_schedules DROP CONSTRAINT IF EXISTS uq_survey_schedules_organization_id;
-- DROP INDEX IF EXISTS idx_survey_schedules_organization_id;
