-- Migration: Add sync tracking columns to rootly_integrations
-- Date: 2026-02-06
-- Description: Track who last synced and when for each integration

-- Add columns to track last sync
ALTER TABLE rootly_integrations
ADD COLUMN IF NOT EXISTS last_synced_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMP WITH TIME ZONE;

-- Create index for efficient queries
CREATE INDEX IF NOT EXISTS idx_rootly_integrations_last_synced
ON rootly_integrations(last_synced_at DESC);

-- Verification
SELECT 'Added sync tracking columns' as status;
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'rootly_integrations'
  AND column_name IN ('last_synced_by', 'last_synced_at');
