-- Migration: Add CASCADE DELETE to integration_mappings.analysis_id foreign key
-- Purpose: Fix foreign key constraint violation when deleting analyses
-- When an analysis is deleted, all related integration_mappings records will be automatically deleted

-- Drop the existing foreign key constraint
ALTER TABLE integration_mappings
DROP CONSTRAINT integration_mappings_analysis_id_fkey;

-- Re-add the constraint with ON DELETE CASCADE
ALTER TABLE integration_mappings
ADD CONSTRAINT integration_mappings_analysis_id_fkey
FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE;
