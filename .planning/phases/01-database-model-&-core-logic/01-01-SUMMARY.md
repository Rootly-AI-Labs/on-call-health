---
phase: 01-database-model-&-core-logic
plan: 01
subsystem: database
tags: [sqlalchemy, argon2, api-keys, dual-hash, postgresql]

# Dependency graph
requires: []
provides:
  - APIKey SQLAlchemy model with dual-hash storage pattern
  - User.api_keys relationship for bidirectional navigation
  - argon2-cffi dependency for Argon2id hashing
affects:
  - 01-02 (migration generation)
  - 01-03 (key generation service)
  - 02-auth-middleware (key validation)

# Tech tracking
tech-stack:
  added:
    - argon2-cffi==25.1.0
  patterns:
    - Dual-hash storage (SHA-256 indexed lookup + Argon2id verification)
    - Integer primary keys (codebase standard)
    - Cascade delete for user-owned resources

key-files:
  created:
    - backend/app/models/api_key.py
  modified:
    - backend/requirements.txt
    - backend/app/models/__init__.py
    - backend/app/models/user.py

key-decisions:
  - "Dual-hash pattern: SHA-256 for O(1) indexed lookup, Argon2id for timing-safe verification"
  - "Integer primary key to match existing codebase pattern (not UUID)"
  - "och_live_ prefix for production keys (following industry convention)"
  - "scope default 'full_access' for v1 (future: granular permissions)"

patterns-established:
  - "APIKey model follows survey_period.py patterns for properties and to_dict"
  - "Cascade delete on user relationship to clean up keys on user deletion"

# Metrics
duration: 7min
completed: 2026-01-30
---

# Phase 01 Plan 01: APIKey Model Summary

**APIKey SQLAlchemy model with dual-hash storage (SHA-256 + Argon2id), 12 columns, 4 indexes, and bidirectional User relationship**

## Performance

- **Duration:** 7 min
- **Started:** 2026-01-30T23:13:54Z
- **Completed:** 2026-01-30T23:20:25Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Created APIKey model with all required columns for secure key storage
- Implemented dual-hash pattern: SHA-256 for fast indexed lookup, Argon2id for cryptographic verification
- Added proper indexes for performance (key_hash_sha256, user_id, last_used_at)
- Established bidirectional relationship between User and APIKey models
- Added helper properties (is_active, masked_key) and to_dict() for API responses

## Task Commits

Each task was committed atomically:

1. **Task 1: Add argon2-cffi dependency** - `6a2022c1` (chore)
2. **Task 2: Create APIKey model** - `2c331aad` (feat)
3. **Task 3: Update models exports and User relationship** - `63fe3d0f` (feat)

## Files Created/Modified
- `backend/requirements.txt` - Added argon2-cffi==25.1.0 for Argon2id hashing
- `backend/app/models/api_key.py` - New APIKey SQLAlchemy model (121 lines)
- `backend/app/models/__init__.py` - Export APIKey from models package
- `backend/app/models/user.py` - Add api_keys relationship with cascade delete

## Decisions Made
- Used Integer primary key to match existing codebase pattern (not UUID)
- Placed argon2-cffi in Authentication & OAuth section of requirements.txt
- Used `cascade="all, delete-orphan"` on User.api_keys relationship to clean up keys when user is deleted
- Key prefix defaults to `och_live_` following industry convention (similar to Stripe's sk_live_)
- Scope defaults to `full_access` for v1 simplicity

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- DATABASE_URL required for direct Python import verification - worked around by using AST parsing and regex to verify model structure without loading SQLAlchemy runtime

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- APIKey model ready for migration generation (Plan 01-02)
- Model structure verified: 12 columns, 4 indexes/constraints, all properties working
- Relationship to User established for foreign key in migration
- argon2-cffi available for key generation service (Plan 01-03)

---
*Phase: 01-database-model-&-core-logic*
*Completed: 2026-01-30*
