-- Add team-scoped key columns to rootly_integrations
-- key_type: "global" or "team" (NULL means global/unknown for existing rows)
-- team_name: owning team name for team-scoped API keys

ALTER TABLE rootly_integrations
ADD COLUMN IF NOT EXISTS key_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS team_name VARCHAR(255);
