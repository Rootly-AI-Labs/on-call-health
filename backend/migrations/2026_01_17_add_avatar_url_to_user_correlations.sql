-- Migration: Add avatar_url column to user_correlations table
-- Description: Stores profile image URLs from PagerDuty/Rootly for user avatars

ALTER TABLE user_correlations ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(512);

COMMENT ON COLUMN user_correlations.avatar_url IS 'Profile image URL from PagerDuty or Rootly';
