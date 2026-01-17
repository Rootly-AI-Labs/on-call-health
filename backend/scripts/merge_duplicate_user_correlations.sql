-- Merge duplicate user_correlation records directly in database
-- This script merges all duplicates for (organization_id, email) combinations
-- by keeping the best record and merging all data into it

-- SAFETY: This script uses a transaction with BEGIN/COMMIT
-- If anything fails, all changes are rolled back

BEGIN;

-- Step 1: Create a temporary table to track which record to keep for each duplicate group
CREATE TEMP TABLE records_to_keep AS
SELECT DISTINCT ON (organization_id, email)
  id as keep_id,
  organization_id,
  email
FROM user_correlations
WHERE organization_id IS NOT NULL
ORDER BY
  organization_id,
  email,
  -- Prioritize records with most data
  CASE WHEN github_username IS NOT NULL THEN 1 ELSE 0 END DESC,
  CASE WHEN slack_user_id IS NOT NULL THEN 1 ELSE 0 END DESC,
  CASE WHEN jira_account_id IS NOT NULL THEN 1 ELSE 0 END DESC,
  CASE WHEN integration_ids IS NOT NULL THEN 1 ELSE 0 END DESC,
  created_at DESC;

-- Step 2: For each kept record, merge integration_ids from duplicates
UPDATE user_correlations uc_keep
SET integration_ids = (
  SELECT jsonb_agg(DISTINCT elem)
  FROM (
    SELECT jsonb_array_elements(
      CASE
        WHEN integration_ids IS NOT NULL THEN integration_ids::jsonb
        ELSE '[]'::jsonb
      END
    ) as elem
    FROM user_correlations uc_dup
    WHERE uc_dup.organization_id = uc_keep.organization_id
      AND uc_dup.email = uc_keep.email
  ) elements
)
WHERE uc_keep.id IN (SELECT keep_id FROM records_to_keep)
  AND uc_keep.organization_id IN (
    SELECT organization_id
    FROM user_correlations
    WHERE organization_id IS NOT NULL
    GROUP BY organization_id, email
    HAVING COUNT(*) > 1
  );

-- Step 3: Merge other fields from duplicates into kept records
UPDATE user_correlations uc_keep
SET
  github_username = COALESCE(uc_keep.github_username, (
    SELECT github_username FROM user_correlations uc_dup
    WHERE uc_dup.organization_id = uc_keep.organization_id
      AND uc_dup.email = uc_keep.email
      AND uc_dup.github_username IS NOT NULL
    LIMIT 1
  )),
  slack_user_id = COALESCE(uc_keep.slack_user_id, (
    SELECT slack_user_id FROM user_correlations uc_dup
    WHERE uc_dup.organization_id = uc_keep.organization_id
      AND uc_dup.email = uc_keep.email
      AND uc_dup.slack_user_id IS NOT NULL
    LIMIT 1
  )),
  jira_account_id = COALESCE(uc_keep.jira_account_id, (
    SELECT jira_account_id FROM user_correlations uc_dup
    WHERE uc_dup.organization_id = uc_keep.organization_id
      AND uc_dup.email = uc_keep.email
      AND uc_dup.jira_account_id IS NOT NULL
    LIMIT 1
  )),
  linear_user_id = COALESCE(uc_keep.linear_user_id, (
    SELECT linear_user_id FROM user_correlations uc_dup
    WHERE uc_dup.organization_id = uc_keep.organization_id
      AND uc_dup.email = uc_keep.email
      AND uc_dup.linear_user_id IS NOT NULL
    LIMIT 1
  )),
  rootly_user_id = COALESCE(uc_keep.rootly_user_id, (
    SELECT rootly_user_id FROM user_correlations uc_dup
    WHERE uc_dup.organization_id = uc_keep.organization_id
      AND uc_dup.email = uc_keep.email
      AND uc_dup.rootly_user_id IS NOT NULL
    LIMIT 1
  )),
  pagerduty_user_id = COALESCE(uc_keep.pagerduty_user_id, (
    SELECT pagerduty_user_id FROM user_correlations uc_dup
    WHERE uc_dup.organization_id = uc_keep.organization_id
      AND uc_dup.email = uc_keep.email
      AND uc_dup.pagerduty_user_id IS NOT NULL
    LIMIT 1
  )),
  name = COALESCE(uc_keep.name, (
    SELECT name FROM user_correlations uc_dup
    WHERE uc_dup.organization_id = uc_keep.organization_id
      AND uc_dup.email = uc_keep.email
      AND uc_dup.name IS NOT NULL
    LIMIT 1
  ))
WHERE uc_keep.id IN (SELECT keep_id FROM records_to_keep);

-- Step 4: Delete duplicate records (keep only the best one)
DELETE FROM user_correlations
WHERE id NOT IN (SELECT keep_id FROM records_to_keep)
  AND (organization_id, email) IN (
    SELECT organization_id, email
    FROM user_correlations
    WHERE organization_id IS NOT NULL
    GROUP BY organization_id, email
    HAVING COUNT(*) > 1
  );

-- Step 5: Show results
SELECT
  'MERGE COMPLETE' as status,
  COUNT(*) as total_records,
  COUNT(DISTINCT email) as unique_emails,
  COUNT(*) - COUNT(DISTINCT email) as duplicates_remaining
FROM user_correlations
WHERE organization_id IS NOT NULL;

-- If everything looks good, uncomment COMMIT below and comment out ROLLBACK
COMMIT;
-- ROLLBACK;  -- Comment this out when ready to apply changes
