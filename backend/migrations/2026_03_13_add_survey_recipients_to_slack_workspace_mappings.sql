-- Migration: Add org-level survey recipient storage to Slack workspace mappings
-- This makes the Team Members checkbox selection the single source of truth for
-- scheduled Slack surveys, while backfilling from legacy Rootly integration rows.

ALTER TABLE slack_workspace_mappings
ADD COLUMN IF NOT EXISTS survey_recipients JSON;

COMMENT ON COLUMN slack_workspace_mappings.survey_recipients IS
'Organization-wide selected UserCorrelation IDs for scheduled Slack surveys';

UPDATE slack_workspace_mappings swm
SET survey_recipients = (
    SELECT ri.survey_recipients
    FROM rootly_integrations ri
    JOIN users u ON u.id = ri.user_id
    WHERE u.organization_id = swm.organization_id
      AND ri.platform = 'rootly'
      AND ri.is_active = TRUE
      AND ri.survey_recipients IS NOT NULL
    ORDER BY
      ri.last_synced_at DESC NULLS LAST,
      ri.last_used_at DESC NULLS LAST,
      ri.created_at DESC,
      ri.id DESC
    LIMIT 1
)
WHERE swm.organization_id IS NOT NULL
  AND swm.survey_recipients IS NULL;
