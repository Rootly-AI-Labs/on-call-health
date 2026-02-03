# Roadmap: On-Call Health Token Authentication

## Overview

This roadmap extends the existing OAuth-based Jira and Linear integrations to support manual API token authentication alongside OAuth flows. The work progresses from foundational security infrastructure through platform-specific implementations to user experience polish. Each phase delivers verifiable capabilities that enterprise users can adopt immediately.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Backend Foundation** - Token storage architecture with encryption parity
- [x] **Phase 2: Validation Infrastructure** - Type-aware token validation system
- [x] **Phase 3: Jira Token Integration** - Complete Jira API token setup flow
- [ ] **Phase 4: Linear Token Integration** - Complete Linear API token setup flow
- [ ] **Phase 5: User Experience** - Status indicators, help text, and method switching

## Phase Details

### Phase 1: Backend Foundation
**Goal**: Establish secure token storage architecture with encryption parity between OAuth and API tokens
**Depends on**: Nothing (first phase)
**Requirements**: TOKEN-01, TOKEN-02, TOKEN-03
**Success Criteria** (what must be TRUE):
  1. API tokens stored with same Fernet encryption as OAuth tokens (ENCRYPTION_KEY)
  2. Database models distinguish OAuth vs manual tokens via token_source field
  3. TokenManager service provides get_valid_token() abstraction hiding OAuth refresh logic from API clients
  4. Integration models expose is_oauth, is_manual, and supports_refresh properties
  5. Encryption parity verified by security tests (no plaintext tokens)
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Create TokenManager service with get_valid_token() abstraction
- [x] 01-02-PLAN.md — Security tests for token encryption parity

### Phase 2: Validation Infrastructure
**Goal**: Build type-aware token validation system that handles OAuth refresh and manual token virtual expiration
**Depends on**: Phase 1
**Requirements**: AUTH-03, AUTH-04, AUTH-05
**Success Criteria** (what must be TRUE):
  1. Token validation distinguishes OAuth (refresh on expiry) from manual (check virtual expiration)
  2. Validation executes during setup before saving token to database
  3. Clear error messages display for validation failures (network, authentication, permissions)
  4. Visual status indicators show connection state (validating, connected, error)
  5. Validation uses existing IntegrationValidator service patterns
**Plans**: 4 plans

Plans:
- [x] 02-01-PLAN.md — Backend validation endpoints for Jira and Linear
- [x] 02-02-PLAN.md — Notification service and validation tests
- [x] 02-03-PLAN.md — Frontend validation hooks and status indicators
- [x] 02-04-PLAN.md — Cache configuration and end-to-end verification

### Phase 3: Jira Token Integration
**Goal**: Users can connect Jira integration using API token (alternative to OAuth)
**Depends on**: Phase 2
**Requirements**: AUTH-01, UX-01, UX-02, UX-05
**Success Criteria** (what must be TRUE):
  1. User can choose between OAuth and API Token when connecting Jira
  2. Integration setup modal shows both OAuth and Token options
  3. Help text provides guidance for obtaining Jira Personal Access Token
  4. Platform-specific error messages display for Jira token failures
  5. User can successfully connect Jira integration using valid API token
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Backend POST /connect-manual endpoint with validation and encryption
- [x] 03-02-PLAN.md — Frontend dual-button card and auto-save form

### Phase 4: Linear Token Integration
**Goal**: Users can connect Linear integration using API token (alternative to OAuth)
**Depends on**: Phase 2
**Requirements**: AUTH-02, UX-01, UX-03, UX-06
**Success Criteria** (what must be TRUE):
  1. User can choose between OAuth and API Token when connecting Linear
  2. Integration setup modal shows both OAuth and Token options
  3. Help text provides guidance for obtaining Linear Personal API Key
  4. Platform-specific error messages display for Linear token failures
  5. User can successfully connect Linear integration using valid API token
**Plans**: 2 plans

Plans:
- [ ] 04-01-PLAN.md — Backend POST /connect-manual endpoint with validation, encryption, and workspace mapping
- [ ] 04-02-PLAN.md — Frontend dual-button card and auto-save form

### Phase 5: User Experience
**Goal**: Users can see auth method for integrations, access helpful guidance, and switch between OAuth and token
**Depends on**: Phase 3, Phase 4
**Requirements**: UX-04, SWITCH-01, SWITCH-02
**Success Criteria** (what must be TRUE):
  1. Integration page displays which auth method is used (OAuth vs Token) for each connected integration
  2. User can disconnect existing OAuth integration and reconnect with API token without data loss
  3. User can disconnect existing API token integration and reconnect with OAuth without data loss
  4. Auth method indicators clearly distinguish OAuth (auto-renew) from Token (manual rotation)
**Plans**: TBD

Plans:
- [ ] TBD after phase planning

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Backend Foundation | 2/2 | Complete | 2026-02-01 |
| 2. Validation Infrastructure | 4/4 | Complete | 2026-02-02 |
| 3. Jira Token Integration | 2/2 | Complete | 2026-02-02 |
| 4. Linear Token Integration | 0/2 | Planned | - |
| 5. User Experience | 0/TBD | Not started | - |
