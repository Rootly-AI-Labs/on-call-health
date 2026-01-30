# Project State: API Key Management

**Project:** API Key Management for On-Call Health
**Milestone:** v1.0 - MVP Launch
**Updated:** 2026-01-30
**Status:** 🟡 Planning Complete - Ready for Phase 1

## Current State

### Progress Overview

```
✅ Project Initialization    [████████████████████] 100%
✅ Requirements Definition   [████████████████████] 100%
✅ Roadmap Creation          [████████████████████] 100%
⏳ Phase 1: Database Model   [░░░░░░░░░░░░░░░░░░░░]   0%
⏳ Phase 2: Auth Middleware  [░░░░░░░░░░░░░░░░░░░░]   0%
⏳ Phase 3: API Endpoints    [░░░░░░░░░░░░░░░░░░░░]   0%
⏳ Phase 4: Frontend UI      [░░░░░░░░░░░░░░░░░░░░]   0%
```

**Overall Project Progress:** 0/31 requirements implemented (0%)

### Active Phase

**Current:** Planning Complete
**Next:** Phase 1 - Database Model & Core Logic
**Blocking:** None - ready to start

### Phase Status

| Phase | Status | Requirements | Completed | Progress |
|-------|--------|--------------|-----------|----------|
| Phase 1: Database Model | 🔵 Not Started | 11 | 0/11 | 0% |
| Phase 2: Auth Middleware | 🔵 Not Started | 6 | 0/6 | 0% |
| Phase 3: API Endpoints | 🔵 Not Started | 6 | 0/6 | 0% |
| Phase 4: Frontend UI | 🔵 Not Started | 8 | 0/8 | 0% |

**Status Legend:**
- 🔵 Not Started
- 🟡 In Progress
- 🟢 Complete
- 🔴 Blocked

---

## Requirements Status

### Implemented (0/31)

None yet - starting Phase 1

### In Progress (0/31)

None yet

### Blocked (0/31)

None yet

### Not Started (31/31)

**Phase 1 Requirements (11):**
- REQ-F-001: API Key Creation (data model)
- REQ-F-002: Prefixed Key Format
- REQ-F-007: Optional Expiration Date
- REQ-F-008: Unlimited Keys Per User
- REQ-F-011: Created Timestamp
- REQ-F-012: Last Used Timestamp
- REQ-F-013: Hashed Storage (dual-hash)
- REQ-F-017: Full Access Scope Only (v1)
- REQ-NF-002: Database Indexing
- REQ-NF-005: Cryptographically Secure Random
- REQ-NF-006: No Plaintext Storage
- REQ-NF-008: Existing Stack Compatibility

**Phase 2 Requirements (6):**
- REQ-F-005: Key Revocation (validation logic)
- REQ-F-014: Dual Authentication Support
- REQ-F-015: Per-Key Rate Limiting
- REQ-F-016: HTTPS Transmission Only
- REQ-NF-001: Fast Key Validation (<50ms)
- REQ-NF-003: Async Last Used Update
- REQ-NF-004: Timing-Safe Comparison
- REQ-NF-007: Backward Compatibility with JWT
- REQ-NF-009: Structured Logging
- REQ-NF-010: Error Messages

**Phase 3 Requirements (6):**
- REQ-F-001: API Key Creation (endpoint)
- REQ-F-003: Show Full Key Once
- REQ-F-004: Copy-to-Clipboard (backend support)
- REQ-F-005: Key Revocation (endpoint)
- REQ-F-006: Revocation Confirmation Dialog (backend support)
- REQ-F-009: Key List View (endpoint)
- REQ-F-010: Masked Key Display (endpoint)

**Phase 4 Requirements (8):**
- REQ-F-003: Show Full Key Once (UI)
- REQ-F-004: Copy-to-Clipboard (UI button)
- REQ-F-006: Revocation Confirmation Dialog (UI)
- REQ-F-007: Optional Expiration Date (UI form)
- REQ-F-009: Key List View (UI table)
- REQ-F-010: Masked Key Display (UI)
- REQ-F-018: Dedicated API Keys Navigation
- REQ-F-019: Key Creation UI
- REQ-F-020: Key List UI
- REQ-F-021: Key Revocation UI

---

## Recent Activity

### 2026-01-30 - Project Initialization

**Actions Taken:**
1. ✅ Created PROJECT.md with validated and active requirements
2. ✅ Created config.json with workflow settings (quality model profile)
3. ✅ Fixed .gitignore to allow planning docs to be committed
4. ✅ Spawned 4 parallel Opus research agents (stack, features, architecture, pitfalls)
5. ✅ Synthesized research into SUMMARY.md with high confidence
6. ✅ Generated REQUIREMENTS.md with 31 requirements (21 functional, 10 non-functional)
7. ✅ Created ROADMAP.md with 4-phase breakdown
8. ✅ Initialized STATE.md (this file)

**Key Decisions:**
- Use argon2-cffi 25.1.0 (NOT passlib - unmaintained)
- Dual-hash storage pattern: SHA-256 (fast indexed lookup) + Argon2id (verification)
- Unified auth dependency supporting both JWT and API keys
- 4-phase build order: Model → Auth → API → UI
- Show-once key display (industry standard)
- UI-only management (no REST API for key CRUD to prevent escalation)
- Per-key rate limiting for security isolation
- Optional expiration dates (user flexibility)

**Research Findings:**
- Rootly API doesn't expose individual paging/notification data (deferred)
- Pivoted to API key management to solve MCP JWT expiration problem
- Timing-safe comparison required (CVE-2026-23996)
- Database indexing critical (prevents 35x slowdown)
- <50ms validation requirement drives dual-hash pattern

**Commits:**
- ✅ Committed PROJECT.md and config.json
- ⏳ Ready to commit REQUIREMENTS.md, ROADMAP.md, STATE.md

---

## Known Issues

None yet - planning phase complete

---

## Technical Debt

None yet - greenfield feature

---

## Dependencies

### External Dependencies
**New Packages Required:**
- `argon2-cffi==25.1.0` - Secure password hashing (Phase 1)

**Existing Dependencies (Already Available):**
- FastAPI - Web framework
- SQLAlchemy - ORM
- PostgreSQL - Database
- Redis - Caching and rate limiting
- slowapi - Rate limiting
- Next.js 16 - Frontend framework
- TypeScript - Type safety
- Tailwind CSS - Styling

### Internal Dependencies
**Existing Code to Integrate:**
- `backend/app/models/user.py` - User model (foreign key)
- `backend/app/auth/dependencies.py` - Auth dependency (MODIFY in Phase 2)
- `backend/app/auth/jwt.py` - JWT validation (REUSE in Phase 2)
- `backend/app/core/rate_limiting.py` - Rate limiter (EXTEND in Phase 2)
- `backend/app/mcp/auth.py` - MCP auth (UPDATE in Phase 2)
- `backend/app/mcp/server.py` - MCP server (UPDATE in Phase 2)

---

## Codebase Context

### Architecture
- Three-tier architecture: API → Services → Models
- Service-oriented with specialized services for different concerns
- FastAPI with dependency injection
- SQLAlchemy ORM with PostgreSQL
- React/Next.js frontend with TypeScript

### Authentication (Current)
- OAuth 2.0 (Google, GitHub) for web login
- JWT tokens (7-day expiry) stored in httpOnly cookies
- `get_current_user` dependency in all protected endpoints
- MCP server uses JWT bearer tokens (expires, breaks clients)

### Authentication (After This Project)
- OAuth 2.0 + JWT for web sessions (unchanged)
- API keys for programmatic access (new)
- Unified `get_current_user` supporting both (modified)
- MCP server accepts both JWT and API keys (modified)
- Per-key rate limiting (new)

### File Organization
```
backend/
  app/
    models/          # SQLAlchemy models
    services/        # Business logic
    api/
      endpoints/     # FastAPI routers
    auth/            # Authentication logic
    core/            # Config, clients, utilities
    mcp/             # MCP server
  alembic/
    versions/        # Database migrations
  tests/             # Pytest tests

frontend/
  src/
    app/             # Next.js App Router pages
    components/      # React components
    hooks/           # Custom React hooks
    types/           # TypeScript types
```

---

## Success Criteria (v1.0 Launch)

### Phase Completion
- [ ] Phase 1: Database Model & Core Logic
- [ ] Phase 2: Auth Middleware Integration
- [ ] Phase 3: API Endpoints
- [ ] Phase 4: Frontend UI & UX

### Testing
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] End-to-end test: Create → Use → Revoke
- [ ] Performance benchmarks met (<50ms auth validation)
- [ ] Security checklist completed

### Documentation
- [ ] API usage documentation with curl examples
- [ ] MCP integration guide updated
- [ ] Internal developer documentation
- [ ] User-facing help text in UI

### Deployment
- [ ] Deployed to staging environment
- [ ] User acceptance testing completed
- [ ] No regressions in existing functionality
- [ ] Backward compatibility with JWT verified

### Launch Criteria
- [ ] All 31 requirements implemented
- [ ] All success criteria met
- [ ] Security review passed
- [ ] Performance benchmarks passed
- [ ] Zero critical bugs
- [ ] User acceptance sign-off

---

## Next Actions

### Immediate (Phase 1 Planning)
1. Review Phase 1 requirements in ROADMAP.md
2. Plan Phase 1 implementation with detailed tasks
3. Create Phase 1 plan document (or use /gsd:plan-phase command)
4. Begin implementation: APIKey model

### This Phase (Phase 1)
- Create APIKey SQLAlchemy model
- Implement dual-hash pattern (SHA-256 + Argon2id)
- Generate database migration with indexes
- Write key generation service with `secrets.token_hex()`
- Write unit tests for model and services
- Run migration on development database
- Verify indexes with EXPLAIN ANALYZE

### Upcoming Phases
- Phase 2: Unified auth dependency, per-key rate limiting, MCP integration
- Phase 3: API endpoints for CRUD operations
- Phase 4: Frontend UI components and routing

---

## Questions & Decisions Log

### Q: Should API keys be manageable via REST API?
**Decision:** No - UI only to prevent compromised key escalation attack
**Rationale:** Compromised API key shouldn't be able to create/revoke other keys
**Source:** FEATURES.md - Anti-Features, security best practice

### Q: What hashing algorithm for API keys?
**Decision:** Dual-hash pattern - SHA-256 (indexed) + Argon2id (verification)
**Rationale:** Bcrypt/Argon2 alone too slow (200-350ms), need <50ms validation
**Source:** STACK.md research, PITFALLS.md

### Q: Should key expiration be mandatory?
**Decision:** Optional - user can choose "Never" or set date
**Rationale:** User flexibility, avoid breaking automations silently
**Source:** PROJECT.md - Key Decisions, FEATURES.md

### Q: Where in UI navigation?
**Decision:** Dedicated "API Keys" menu item (not buried in Account Settings)
**Rationale:** Signals developer feature, improves discoverability
**Source:** PROJECT.md - Key Decisions, FEATURES.md

### Q: How many keys can a user create?
**Decision:** Unlimited
**Rationale:** User manages complexity, no artificial limits
**Source:** PROJECT.md - Key Decisions

---

*Last Updated: 2026-01-30*
*Next Update: After Phase 1 planning begins*
