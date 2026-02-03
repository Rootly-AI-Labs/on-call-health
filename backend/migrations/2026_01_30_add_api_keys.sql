-- Migration: Add api_keys table for programmatic API access
-- Description: Creates api_keys table with dual-hash storage pattern for secure API key management.
--              SHA-256 for fast indexed lookup, Argon2id for cryptographic verification.

-- ============================================================================
-- Create api_keys table
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,

    -- Dual-hash storage (never store plaintext key)
    key_hash_sha256 VARCHAR(64) NOT NULL,  -- Fast indexed lookup
    key_hash_argon2 TEXT NOT NULL,          -- Cryptographic verification

    -- Key display fields (safe to show)
    prefix VARCHAR(20) NOT NULL DEFAULT 'och_live_',
    last_four VARCHAR(4) NOT NULL,

    -- Scope (v1: full_access only)
    scope VARCHAR(50) NOT NULL DEFAULT 'full_access',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- Table and column comments
-- ============================================================================
COMMENT ON TABLE api_keys IS 'API keys for programmatic access. Uses dual-hash pattern: SHA-256 for O(1) lookup, Argon2id for cryptographic verification.';

COMMENT ON COLUMN api_keys.key_hash_sha256 IS 'SHA-256 hash of full API key for fast indexed lookup (64 hex chars)';
COMMENT ON COLUMN api_keys.key_hash_argon2 IS 'Argon2id hash of full API key for timing-safe cryptographic verification';

-- ============================================================================
-- Indexes for api_keys
-- ============================================================================

-- Primary lookup index: O(1) lookup by SHA-256 hash
-- Critical for performance - prevents 35x slowdown on key validation
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash_sha256
ON api_keys(key_hash_sha256);

-- User index: For listing user's keys efficiently
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id
ON api_keys(user_id);

-- Activity index: For querying keys by last usage
CREATE INDEX IF NOT EXISTS idx_api_keys_last_used_at
ON api_keys(last_used_at);

-- Unique constraint: Prevent duplicate names per user (only for non-revoked keys)
CREATE UNIQUE INDEX IF NOT EXISTS uq_api_keys_user_name
ON api_keys(user_id, name)
WHERE revoked_at IS NULL;

-- ============================================================================
-- ROLLBACK (run manually if needed to revert this migration)
-- ============================================================================
-- DROP INDEX IF EXISTS uq_api_keys_user_name;
-- DROP INDEX IF EXISTS idx_api_keys_last_used_at;
-- DROP INDEX IF EXISTS idx_api_keys_user_id;
-- DROP INDEX IF EXISTS idx_api_keys_key_hash_sha256;
-- DROP TABLE IF EXISTS api_keys;
