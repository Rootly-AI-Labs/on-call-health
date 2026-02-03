# Milestones

## v1.1: Token Authentication (2025-07 → 2026-02)

**Status:** ✅ SHIPPED 2026-02-03

**Scope:** Token-based authentication for Jira and Linear integrations alongside OAuth

**Stats:**
- 5 phases (Backend Foundation → User Experience)
- 12 plans executed
- 70 files changed (+14,062 lines)
- All 16 v1.1 requirements delivered

**Key Accomplishments:**
- TokenManager service with OAuth auto-refresh and encryption parity for manual tokens
- Real-time token validation with platform-specific error messages (5 Jira types, 4 Linear types)
- Complete Jira and Linear manual token setup flows with auto-save after validation
- Auth method visibility (OAuth vs API Token badges) and seamless switching between methods
- Comprehensive security testing (25 encryption tests, no token leakage in errors or logs)
- Cross-phase integration verified (8/8 integration points, 3/3 E2E flows)

**Technical Highlights:**
- Unified token abstraction hides OAuth refresh complexity from API clients
- Platform-specific validation with format checks, API calls, and actionable error guidance
- Frontend validation hook with debouncing, abort controllers, and structured state management
- Encryption parity verified: manual tokens use same Fernet encryption as OAuth tokens
- Zero breaking changes to existing OAuth integrations

**Archive:** `.planning/milestones/v1.1-*.md`

**Git range:** `feat(01-01): create TokenManager service` → `feat(05-02): wire switch flow`

---
