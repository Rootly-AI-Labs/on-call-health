-- Fix missing source_platform values in user_mappings table
-- Run this in Railway's PostgreSQL console

-- First, check how many mappings have NULL source_platform
SELECT 
    COUNT(*) as null_count,
    COUNT(CASE WHEN source_platform IS NOT NULL THEN 1 END) as not_null_count,
    COUNT(*) as total_count
FROM user_mappings;

-- Show a sample of the NULL mappings
SELECT id, source_platform, source_identifier, target_platform, target_identifier, mapping_type
FROM user_mappings 
WHERE source_platform IS NULL 
ORDER BY id 
LIMIT 10;

-- Update all NULL source_platform to 'rootly'
UPDATE user_mappings 
SET source_platform = 'rootly' 
WHERE source_platform IS NULL;

-- Verify the fix
SELECT 
    COUNT(*) as total_mappings,
    COUNT(CASE WHEN source_platform = 'rootly' THEN 1 END) as rootly_mappings,
    COUNT(CASE WHEN source_platform IS NULL THEN 1 END) as null_mappings
FROM user_mappings;