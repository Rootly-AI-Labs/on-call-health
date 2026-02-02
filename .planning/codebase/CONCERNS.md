# Codebase Concerns

**Analysis Date:** 2026-01-30

## Tech Debt

**Monolithic burnout analyzer (6000+ lines):**
- Issue: `UnifiedBurnoutAnalyzer` in `/backend/app/services/unified_burnout_analyzer.py` is 6056 lines with single class handling multiple concerns: incident analysis, AI integration, GitHub correlation, Slack analysis, daily trends, and Jira integration
- Files: `backend/app/services/unified_burnout_analyzer.py`
- Impact: Difficult to test individual features, high maintenance burden, risk of regressions when modifying scoring logic, difficult to debug specific data flow paths
- Fix approach: Break into specialized analyzers (IncidentAnalyzer, GitHubAnalyzer, SlackAnalyzer, JiraAnalyzer) with shared interfaces and composition pattern

**Duplicated large components and page files:**
- Issue: `page.tsx` (5411 lines) and `useDashboard.ts` (2305 lines) contain tightly coupled UI and business logic with multiple state managers and handler namespaces
- Files: `frontend/src/app/integrations/page.tsx`, `frontend/src/hooks/useDashboard.ts`, `backend/app/api/endpoints/analyses.py` (3303 lines)
- Impact: Difficult to test individual features, high cognitive load, increased risk of state consistency bugs, difficult to reuse logic
- Fix approach: Extract features into smaller components/hooks, create custom hooks for each integration type, separate API response handling from UI logic

**Broad exception handling (Exception and pass):**
- Issue: Widespread `except Exception as e:` clauses that catch all exceptions including transient errors and bugs. Line 52 in `unified_burnout_analyzer.py` has `except ImportError as e: pass` for mock data loading
- Files: `backend/app/services/` (40+ instances), `backend/app/api/endpoints/` (30+ instances)
- Impact: Masks bugs, makes debugging difficult, hides integration failures that should be escalated
- Fix approach: Replace broad catches with specific exception types (ValueError, KeyError, TimeoutError, ConnectionError), always log caught exceptions, re-raise unexpected errors

**Soft validation of external API responses:**
- Issue: `validate_mapping` endpoint in `/backend/app/api/endpoints/manual_mappings.py` line 329-337 returns hardcoded placeholder validation ("valid": True, "exists": True) without actual API validation
- Files: `backend/app/api/endpoints/manual_mappings.py` (TODO at line 329)
- Impact: Users may create invalid mappings to non-existent GitHub/Slack identifiers that silently fail during analysis
- Fix approach: Implement actual validation against GitHub/Slack APIs on mapping creation, return descriptive errors when identifiers don't exist

**Unsafe type casting (excessive `any` types):**
- Issue: 198+ instances of `: any` type annotations in frontend TypeScript, example in `frontend/src/app/setup/linear/callback/page.tsx` line 72 and line-by-line state in `useDashboard.ts`
- Files: `frontend/src/hooks/useDashboard.ts`, `frontend/src/app/integrations/page.tsx`, and 30+ other files
- Impact: Type safety disabled for 20% of frontend code, no compile-time verification of data structures, higher risk of runtime errors
- Fix approach: Define explicit TypeScript interfaces for API responses and state (e.g., `IntegrationState`, `MappingResponse`), use type predicates for runtime validation

**Console logging in production frontend code:**
- Issue: 161 instances of `console.log`, `console.error`, `console.warn` in `frontend/src/` that remain in production builds
- Files: `frontend/src/` (widespread)
- Impact: Potential information leakage in production, makes it harder to spot legitimate issues in real production logs, memory overhead if logging large objects
- Fix approach: Replace all console calls with structured logging using a logging library (e.g., pino, winston-lite), gate debug logs behind environment variable check

**Loose database session management:**
- Issue: Multiple files reuse database sessions to "prevent connection pool exhaustion" without proper cleanup guarantees
- Files: `backend/app/services/unified_burnout_analyzer.py` line 99, `backend/app/api/endpoints/analyses.py` line 3055, `backend/app/services/github_collector.py` line 88
- Impact: Sessions may not be returned to pool if exceptions occur, connection pool exhaustion under error conditions, potential memory leaks
- Fix approach: Use SQLAlchemy context managers consistently, implement proper exception handling in try/finally blocks, verify connection pool settings (currently pool_size=30, max_overflow=20)

## Known Bugs

**Multi-tenant filtering disabled:**
- Symptoms: Organizations not properly isolated; users from different organizations could potentially access each other's data
- Files: `backend/app/api/endpoints/analyses.py` line 583
- Trigger: Any user accessing `/analyses/{analysis_id}` endpoint
- Workaround: None currently in place - code comment indicates "TODO: Re-enable organization_id filtering after multi-tenant migration is stable"
- Fix: Re-enable `organization_id` filtering in query at line 584-586, add integration tests for multi-tenant isolation

**PagerDuty mapping validation incomplete:**
- Symptoms: PagerDuty schedule/escalation policy mappings not validated for existence
- Files: `backend/app/api/endpoints/manual_mappings.py` line 623 (TODO comment)
- Trigger: Creating manual mappings for PagerDuty integration
- Workaround: None
- Fix: Extend mapping validation logic to support PagerDuty API checks using `PagerDutyAPIClient`

**Jira OCH contribution fine-tuning needed:**
- Symptoms: Jira ticket count affects burnout scores but algorithm needs field-level tuning
- Files: `backend/app/services/unified_burnout_analyzer.py` line 5226 (TODO comment)
- Trigger: When Jira integration is enabled
- Workaround: Current algorithm uses ticket count and priority weighting, but doesn't account for deadline date
- Fix: Incorporate deadline proximity, number of tickets assigned per user, and sprint progress into OCH contribution calculation

**Skipped E2E tests (15 instances):**
- Symptoms: 15 test cases marked with `test.skip()` or skipped due to "not implemented"
- Files: `frontend/e2e/auth.spec.ts`, `frontend/e2e/landing-page.spec.ts`
- Trigger: Running E2E test suite
- Workaround: Existing tests that do run are smoke tests only
- Fix: Implement missing login UI and validation, uncomment and update skipped tests, add assertions for each skipped test

## Security Considerations

**OAuth token storage and refresh:**
- Risk: OAuth tokens stored in database (Jira, Linear, GitHub) with manual refresh mechanism; token refresh timing could lead to expired tokens
- Files: `backend/app/auth/integration_oauth.py`, `backend/app/api/endpoints/jira.py` (Jira token refresh added in recent PR)
- Current mitigation: Tokens are encrypted at rest, refresh tokens stored, recent PR (#291) added automatic token refresh for Jira
- Recommendations: Extend automatic refresh to all OAuth integrations (Linear, GitHub), implement token expiry alerts, add rotation schedules, audit token access logs

**Environment variable configuration:**
- Risk: Database passwords and API keys exposed in environment variables without rotation mechanism
- Files: `backend/app/models/base.py`, `backend/app/core/config.py`
- Current mitigation: Environment variables loaded from .env file, not committed to repo
- Recommendations: Implement secrets rotation schedule, audit environment variable access, use HashiCorp Vault or similar for production

**Broad exception suppression in error handlers:**
- Risk: Error suppression mechanism in `ErrorHandler.log_suppressed_error` could hide security-related errors
- Files: `backend/app/core/error_handler.py`
- Current mitigation: Errors are still logged once, then suppressed for 60 minutes
- Recommendations: Never suppress auth-related errors, rate-limit errors, permission errors; only suppress non-critical operational errors

**Missing input validation on mappings:**
- Risk: Manual mapping creation accepts identifiers without format validation (e.g., GitHub username pattern, Slack user ID format)
- Files: `backend/app/api/endpoints/manual_mappings.py` line 315-343
- Current mitigation: Some validation in request models, but no actual integration validation
- Recommendations: Add regex validation for identifiers, call integration APIs to verify ownership, implement rate limiting on mapping creation

## Performance Bottlenecks

**Synchronous analysis requests with 900-second timeout:**
- Problem: Analysis endpoint blocks request thread for up to 15 minutes; large incident history causes timeout risk
- Files: `backend/app/services/unified_burnout_analyzer.py` line 1112-1130
- Cause: Single-threaded incident data collection, GitHub API pagination loops, Slack message processing all in request handler
- Improvement path: Move analysis to background task queue (Celery/RQ), return job ID immediately, poll status endpoint, process multiple data sources in parallel

**Inefficient GitHub correlation with pagination:**
- Problem: GitHub API paginated endpoint calls with 0.5s delays between batches during member resolution
- Files: `backend/app/services/enhanced_github_matcher.py` line 206-208, `backend/app/services/github_collector.py` line 88+
- Cause: Sequential batch processing with artificial delays to respect rate limits
- Improvement path: Implement exponential backoff with jitter, batch API calls more aggressively (GitHub allows 5000 requests/hour), cache member lists with TTL

**Frontend state with 95+ useState calls:**
- Problem: `useDashboard.ts` hook manages 95+ separate state variables, each state change re-renders entire component tree
- Files: `frontend/src/hooks/useDashboard.ts` (lines 21-100+)
- Cause: Monolithic hook managing UI state, API data, cache, and derived state all together
- Improvement path: Refactor into specialized state hooks (useIntegrations, useAnalysisHistory, useUIState), use Context + reducer for shared state, consider Zustand or Jotai for state management

**Large frontendpage component renders entire integration UI:**
- Problem: 5411-line page component renders all integration management, mapping, surveys, and configuration in single tree
- Files: `frontend/src/app/integrations/page.tsx`
- Cause: No component extraction for features, all handler namespaces imported at top
- Improvement path: Extract tabs into separate components (GitHubTab, SlackTab, etc.), lazy-load integration features, memoize handlers

**Database pool exhaustion risk under load:**
- Problem: Pool_size=30 with max_overflow=20 (total 50 connections) may be insufficient for concurrent analysis requests
- Files: `backend/app/models/base.py` line 24-25
- Cause: Each analysis request creates new UnifiedBurnoutAnalyzer instance that may hold connections
- Improvement path: Profile connection usage under load, increase pool_size based on expected concurrent users, implement connection timeout and cleanup

## Fragile Areas

**Burnout score calculation algorithms (multiple versions):**
- Files: `backend/app/services/unified_burnout_analyzer.py` (SimpleBurnoutAnalyzer approach), `backend/app/services/ai_burnout_analyzer.py` (AI-powered), `backend/app/services/github_only_burnout_analyzer.py` (GitHub-only)
- Why fragile: Three separate scoring implementations with different weighting schemes; incident severity breakdown calculation changes could affect all versions; OCH score composition tested implicitly through integration tests only
- Safe modification: Add unit tests for each scoring component, create test fixtures with known incident data and expected scores, maintain version history of algorithm changes in comment docs
- Test coverage: Missing unit tests for score calculation components, no regression tests for algorithm changes

**Jira, Linear, and GitHub OAuth integration endpoints:**
- Files: `backend/app/auth/integration_oauth.py`, `backend/app/api/endpoints/jira.py`, `backend/app/api/endpoints/linear.py`, `backend/app/api/endpoints/github.py`
- Why fragile: OAuth callback handling duplicated across integrations, token refresh timing differs, error handling varies (some return detailed errors, some generic)
- Safe modification: Create OAuthFlowBase class with standard callback handling, use composition for integration-specific logic, add integration tests that mock OAuth flows
- Test coverage: E2E OAuth flows not covered, token refresh timing not tested, error scenarios (expired tokens, insufficient scopes) not tested

**User sync and team mapping service:**
- Files: `backend/app/services/user_sync_service.py` (1282 lines), `backend/app/services/account_linking.py`
- Why fragile: Synchronization of users across multiple data sources (Rootly, PagerDuty, GitHub, Slack, Jira, Linear) with inconsistent ID mappings; avatar and metadata merging logic complex
- Safe modification: Add comprehensive sync tests with mock data, verify idempotency of sync operations, test partial failure scenarios (one source fails, others succeed)
- Test coverage: User sync has some unit tests but missing scenarios: duplicate user detection, metadata conflicts, partial sync failures

**Frontend integration mapping and drawer state management:**
- Files: `frontend/src/components/mapping-drawer.tsx`, `frontend/src/app/integrations/page.tsx`
- Why fragile: MappingDrawer and integration page coordinate complex state (which mapping is selected, edit vs create mode, validation errors); event handler chains trigger state updates
- Safe modification: Use explicit state machine for drawer states (closed, viewing, editing, saving), validate state transitions, test all state transitions with Cypress/Playwright
- Test coverage: E2E tests for mapping creation exist but missing: edit existing mapping, delete mapping, validation error scenarios

**Survey scheduling and delivery:**
- Files: `backend/app/services/survey_scheduler.py` (768 lines)
- Why fragile: Complex date/timezone logic for determining survey periods (daily, weekday, weekly), broad exception handling on timezone conversion (line 52 silently falls back to local date)
- Safe modification: Add unit tests for each survey frequency type with different timezones, test timezone edge cases (DST transitions), test frequency boundary conditions (Monday surveys, month boundaries)
- Test coverage: Missing unit tests for period calculation, missing timezone-specific tests

## Scaling Limits

**Database connection pool (50 total):**
- Current capacity: 30 base + 20 overflow = 50 concurrent connections
- Limit: With concurrent analysis requests taking 5-15 seconds each and 5-10 database queries per request, production traffic above 50 concurrent users will exhaust pool
- Scaling path: Monitor connection pool usage metrics, increase to 100+ for production (adjust based on RDS instance type), implement query caching layer, add connection pooling proxy (PgBouncer)

**Synchronous 15-minute analysis timeout:**
- Current capacity: 1 analysis at a time per request handler thread
- Limit: With 4-8 gunicorn workers, can handle 4-8 concurrent analyses; assuming 10-minute average, throughput ~24-48 analyses/hour
- Scaling path: Convert to background jobs with Celery/RQ, scale worker count independently of API servers, implement job queue with priority for re-analyses

**GitHub API rate limit (5000 requests/hour):**
- Current capacity: Each analysis makes ~20-50 GitHub API calls (members, repos, PRs, issues), supporting ~100-250 concurrent analyses/hour
- Limit: With burst analysis requests (e.g., onboarding team of 50 members), rate limit hit
- Scaling path: Implement GitHub GraphQL batching to reduce request count by 70%, add intelligent caching (member lists don't change hourly), use GitHub App installation instead of user tokens for higher limits

**Slack API rate limits (20 requests/minute standard tier):**
- Current capacity: Each analysis makes ~10-20 Slack API calls, supporting ~60-120 concurrent analyses/hour
- Limit: With team onboarding, will hit Slack rate limits
- Scaling path: Upgrade Slack tier if available, batch message queries, implement message deduplication, cache channel/user metadata

**Frontend component tree depth (95+ state variables in single hook):**
- Current capacity: useCallback and useMemo optimizations prevent full re-renders for ~90% of state changes
- Limit: With 100+ connected users in same organization, rendering all integrations simultaneously will cause jank
- Scaling path: Migrate to Zustand/Jotai for granular reactivity, virtualize integration lists, implement code splitting for tab content

## Dependencies at Risk

**OpenAI API key for AI burnout analyzer:**
- Risk: Feature disabled if API key not present; fallback to non-AI analysis, but users expect AI insights; API pricing scales with usage
- Files: `backend/app/services/ai_burnout_analyzer.py`, `backend/app/agents/burnout_agent.py`
- Impact: Feature incomplete without OpenAI, costs scale with active users and analysis depth
- Migration plan: Use alternative LLM (Claude, Anthropic, Llama), implement local LLM option for self-hosted deployments, add feature flags to control AI analysis per organization

**Rootly/PagerDuty incident API dependency:**
- Risk: Both are required incident sources; if one API is down, analysis shows incomplete data
- Files: `backend/app/core/rootly_client.py`, `backend/app/core/pagerduty_client.py`
- Impact: Users get false sense of team health if source is unavailable; no visibility into missing data
- Migration plan: Add incident provider abstraction, support generic incident webhooks, implement fallback to cached incident data if API unavailable

**Slack API for team sync:**
- Risk: Slack workspace token permissions could be revoked; team changes not reflected in analysis
- Files: `backend/app/services/slack_collector.py`, `backend/app/services/user_sync_service.py`
- Impact: Mappings become stale, users drop off reports
- Migration plan: Implement Slack event subscriptions for real-time user updates, add webhook endpoint for user changes, reduce polling frequency

**PostgreSQL database:**
- Risk: Schema migrations required for feature changes; rollback procedure not documented
- Files: `backend/migrations/migration_runner.py`
- Impact: Deployment risk, potential data loss on failed migrations
- Migration plan: Implement zero-downtime migration patterns (add column, backfill, drop old column), test migrations in staging first, document rollback procedures

## Test Coverage Gaps

**Untested burnout score calculation:**
- What's not tested: OCH score components (work_hours_trend, after_hours_activity, sleep_quality_proxy) calculated independently from incidents
- Files: `backend/app/services/unified_burnout_analyzer.py` (lines 1900-2000+)
- Risk: Algorithm changes could introduce silent bugs affecting all users' scores
- Priority: High - affects core product metric

**Missing E2E tests for OAuth flows:**
- What's not tested: Full OAuth callback flow for each integration (Jira, Linear, GitHub), token refresh scenarios, permission error handling
- Files: `backend/app/auth/integration_oauth.py`, `frontend/src/app/setup/jira/callback/page.tsx`, `frontend/src/app/setup/linear/callback/page.tsx`
- Risk: Token refresh failures go undetected, users see stale data without error message
- Priority: High - affects data freshness for all integrations

**Missing multi-tenant isolation tests:**
- What's not tested: Organization isolation at database level (analysis queries, integration data, user mappings)
- Files: `backend/app/api/endpoints/analyses.py` (line 583 TODO)
- Risk: Data leakage between organizations in shared deployment
- Priority: Critical - security issue

**Frontend state synchronization tests:**
- What's not tested: useDashboard hook state consistency across rapid API responses, race conditions in state updates, memory leaks from uncleaned listeners
- Files: `frontend/src/hooks/useDashboard.ts`
- Risk: UI crashes or incorrect data displayed under high-frequency updates
- Priority: Medium - affects reliability under load

**Survey delivery and scheduling tests:**
- What's not tested: Survey period boundaries (Monday, month boundaries), timezone DST transitions, survey delivery with different frequencies, notification deduplication
- Files: `backend/app/services/survey_scheduler.py`
- Risk: Users miss surveys or receive duplicates
- Priority: Medium - affects user engagement

**GitHub mapping algorithm tests:**
- What's not tested: Enhanced matching algorithm with multiple name variations, confidence scoring, fallback strategies for ambiguous matches
- Files: `backend/app/services/enhanced_github_matcher.py`
- Risk: Users misidentified, incidents attributed to wrong person
- Priority: High - affects accuracy of burnout assessment

---

*Concerns audit: 2026-01-30*
