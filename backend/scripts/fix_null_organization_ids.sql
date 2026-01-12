-- Fix NULL organization_id records by setting them to match existing records for same email
-- This script is SAFE and IDEMPOTENT - can be run multiple times

-- Step 1: Preview what will be changed (DRY RUN)
-- Uncomment to see what would be updated:
/*
SELECT
  uc1.id,
  uc1.email,
  uc1.organization_id as current_org_id,
  (SELECT uc2.organization_id
   FROM user_correlations uc2
   WHERE uc2.email = uc1.email
     AND uc2.organization_id IS NOT NULL
   LIMIT 1) as new_org_id,
  uc1.integration_ids::text
FROM user_correlations uc1
WHERE uc1.organization_id IS NULL
  AND uc1.email IN (SELECT email FROM user_correlations WHERE organization_id IS NOT NULL)
ORDER BY uc1.email;
*/

-- Step 2: Perform the update
-- Sets organization_id to match the first non-NULL organization_id found for the same email
UPDATE user_correlations
SET organization_id = (
  SELECT uc2.organization_id
  FROM user_correlations uc2
  WHERE uc2.email = user_correlations.email
    AND uc2.organization_id IS NOT NULL
  LIMIT 1
)
WHERE organization_id IS NULL
  AND email IN (
    SELECT email
    FROM user_correlations
    WHERE organization_id IS NOT NULL
  );

-- Step 3: Verify the fix
SELECT
  'Fixed' as status,
  COUNT(*) as total_records,
  COUNT(CASE WHEN organization_id IS NULL THEN 1 END) as still_null,
  COUNT(CASE WHEN organization_id IS NOT NULL THEN 1 END) as has_org_id
FROM user_correlations;
