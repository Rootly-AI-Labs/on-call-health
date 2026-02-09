-- Migration: Consolidate survey_periods to use team roster user_correlations
-- Date: 2026-02-09
--
-- Problem:
-- survey_periods may reference both personal correlations (user_id IS NOT NULL)
-- and team roster entries (user_id IS NULL) for the same email in org mode.
-- This causes duplicates to appear in analysis views.
--
-- Solution:
-- Update survey_periods that reference personal correlations to instead
-- reference the corresponding team roster entry (user_id IS NULL) for that
-- organization and email.

DO $$
DECLARE
    updated_count INTEGER := 0;
BEGIN
    -- Update survey_periods that reference personal correlations
    -- to instead reference team roster entries
    WITH roster_mappings AS (
        SELECT
            personal.id as personal_id,
            roster.id as roster_id,
            personal.email,
            personal.organization_id
        FROM user_correlations personal
        INNER JOIN user_correlations roster ON (
            roster.organization_id = personal.organization_id
            AND roster.email = personal.email
            AND roster.user_id IS NULL  -- Team roster entry
        )
        WHERE personal.user_id IS NOT NULL  -- Personal correlation
        AND personal.organization_id IS NOT NULL  -- Must be in an org
    )
    UPDATE survey_periods sp
    SET user_correlation_id = rm.roster_id
    FROM roster_mappings rm
    WHERE sp.user_correlation_id = rm.personal_id
    AND sp.organization_id = rm.organization_id;

    GET DIAGNOSTICS updated_count = ROW_COUNT;

    IF updated_count > 0 THEN
        RAISE NOTICE '✅ Updated % survey_periods to reference team roster entries', updated_count;
    ELSE
        RAISE NOTICE 'ℹ️  No survey_periods needed updating';
    END IF;
END $$;
