# Codebase Concerns

**Analysis Date:** 2026-01-30

## Tech Debt

**Monolithic UnifiedBurnoutAnalyzer (6,056 lines):**
- Issue: Single file handles all analysis logic - incident processing, AI analysis, GitHub/Slack/Jira/Linear integration, daily trends, and scoring
- Files: `backend/app/services/unified_burnout_analyzer.py`
- Impact: Difficult to test independently, hard to extend, difficult to debug specific features
- Fix approach: Break into smaller, focused service classes (IncidentProcessor, ScoreCalculator, IntegrationAggregator, TrendAnalyzer)

**Excessive DEBUG Logging in Production Code:**
- Issue: 190+ debug logging statements remain in backend code, many with emoji markers and detailed data dumps
- Files:
  - `backend/app/services/unified_burnout_analyzer.py` (DEBUG comments at lines 1187, 1650, 1758, 4156, 4180, 4196, 4542, 4574)
  - `backend/app/api/endpoints/analyses.py` (lines 254-255, 304, 2209-2211, 2537, 3089, 3092, 3098, 3129, 3174)
  - `backend/app/api/endpoints/mappings.py` (lines 154, 240-241, 298, 316, 341, 354, 408-410)
  - `backend/app/core/pagerduty_client.py` (lines 31, 612, 631, 650)
  - `backend/app/core/rootly_client.py` (line 772)
- Impact: Log noise makes debugging harder, potential PII leakage through debug output, performance impact on Railway deployments
- Fix approach: Remove all DEBUG comments, consolidate info logging to essential points only (setup, errors), move detailed logging to test-only code

**Unfinished Feature: Jira OCH Contribution Tuning:**
- Issue: Comment at line 5226 indicates Jira scoring is not final - needs to incorporate deadline dates, priority, and ticket counts
- Files: `backend/app/services/unified_burnout_analyzer.py`
- Impact: Jira burnout contribution may not accurately reflect actual workload
- Fix approach: Complete the `_calculate_jira_och_contribution()` method implementation with date-based penalties

**Missing Multi-Tenant Organization Filtering:**
- Issue: TODO comment at line 583 indicates organization_id filtering was disabled during multi-tenant migration
- Files: `backend/app/api/endpoints/analyses.py`
- Impact: Analyses may not properly isolate data between organizations
- Fix approach: Re-enable organization_id filtering after multi-tenant migration stability is confirmed

**Incomplete OAuth Implementation:**
- Issue: Base `OAuthProvider` class has NotImplementedError methods, but these are not used - actual implementations exist in subclasses (GoogleOAuth, GitHubOAuth)
- Files: `backend/app/auth/oauth.py`
- Impact: Dead code adds confusion, forces maintainers to check multiple locations
- Fix approach: Remove base class NotImplementedError stubs, use duck typing or explicit interface documentation

## Known Issues

**Incident Data Missing Assignments:**
- Symptom: Warnings logged when unified analyzer finds incidents with no assignments
- Files: `backend/app/services/unified_burnout_analyzer.py` (lines 337, 374)
- Trigger: Occurs when incidents from integration don't include user assignments or when user ID mapping fails
- Impact: Incomplete incident-to-person mapping, potentially missing team members in burnout analysis
- Workaround: Manual user mappings can supplement missing assignments
- Current state: Analyzer continues with reduced dataset but logs the issue

**Large Frontend Page Component:**
- Issue: `frontend/src/app/integrations/page.tsx` is 5,407 lines - contains all integration UI, mapping logic, and state management
- Files: `frontend/src/app/integrations/page.tsx`
- Impact: Single file change requires recompilation of entire page, difficult navigation, hard to test individual features
- Fix approach: Extract UI components (IntegrationCard, MappingUI, SettingsPanel) and state management hooks

## Security Considerations

**Content Security Policy Relaxed for Swagger UI:**
- Risk: Swagger documentation endpoint allows 'unsafe-inline' and 'unsafe-eval' in CSP headers
- Files: `backend/app/middleware/security.py` (lines 168-179)
- Current mitigation: CSP relaxation only applied to `/docs`, `/openapi.json`, `/redoc` paths
- Recommendations:
  - Consider disabling Swagger in production builds
  - Use nonce-based CSP instead of 'unsafe-inline'
  - Document why Swagger requires these permissions (library limitation)

**Validation of Dangerous Functions (eval/exec):**
- Risk: Input validation checks for eval() and exec() patterns, but validation occurs only at middleware layer
- Files: `backend/app/core/input_validation.py`, `backend/app/middleware/security.py`
- Current mitigation: Request size limits (10MB), content-type validation, pattern matching for dangerous functions
- Recommendations:
  - Validate all user inputs at API layer before data processing
  - Add rate limiting per user/IP (appears implemented but needs audit)
  - Implement request signing/HMAC for sensitive endpoints

**Distributed Lock Relies on Redis Availability:**
- Risk: Distributed lock for token refresh falls back gracefully if Redis unavailable, but fallback is unclear
- Files: `backend/app/core/distributed_lock.py` (lines 21-32)
- Current mitigation: Function returns False if Redis unavailable; caller should implement fallback locking
- Recommendations:
  - Make Redis availability a startup requirement or implement database-backed fallback
  - Document the contract: what happens when lock acquisition fails
  - Add monitoring for Redis availability

## Performance Bottlenecks

**Analysis Endpoint Blocks on Full Result Calculation:**
- Problem: `run_analysis_task()` calculates full results in background but endpoint returns immediately - frontend polls for status
- Files: `backend/app/api/endpoints/analyses.py` (line 2675+)
- Cause: Large analyses (1000+ incidents) can take 30+ seconds; response size can exceed 30MB
- Current state: Results are extracted to lightweight summaries (lines 25-71) to reduce payload
- Improvement path:
  - Implement streaming/pagination for results (return members in batches)
  - Cache frequently-accessed analysis views
  - Consider caching incident-to-user mappings

**Multiple Integration Collectors Run Sequentially:**
- Problem: GitHub, Slack, Jira, Linear collectors run one at a time during analysis
- Files: `backend/app/services/unified_burnout_analyzer.py`
- Cause: Collector implementations appear to have mutual dependencies or shared state
- Improvement path: Audit collector dependencies, parallelize independent integrations using asyncio

**Log Retention No Limit:**
- Problem: 190+ debug logging statements can generate 1GB+ logs daily on active deployments
- Files: Multiple backend files (see DEBUG Logging section)
- Impact: Storage costs, slower log searches, potential log rotation issues on Railway
- Fix approach: Remove debug statements, implement structured logging with sampling

## Fragile Areas

**User Mapping & Correlation Logic:**
- Files:
  - `backend/app/services/enhanced_github_matcher.py` (877 lines)
  - `backend/app/services/enhanced_jira_matcher.py`
  - `backend/app/services/enhanced_slack_collector.py`
  - `backend/app/services/github_correlation_service.py`
- Why fragile: Multiple email/username matching strategies that may conflict; no single source of truth for user identity
- Safe modification: Add comprehensive unit tests for each matching strategy before changes; document assumptions about input data
- Test coverage gaps: Matcher tests exist but edge cases for multiple matching strategies not fully covered

**Burnout Score Calculation with Multiple Scoring Paths:**
- Files: `backend/app/services/unified_burnout_analyzer.py`, `backend/app/core/platform_scoring.py`
- Why fragile: Scores calculated via incident analysis, then optionally adjusted by Jira/GitHub/Slack data - multiple paths can create inconsistent results
- Safe modification: Comprehensive test suite for score combinations (incident + Jira, incident + Slack, etc.) before touching
- Test coverage: `backend/tests/test_och_calculations.py` provides baseline but integration scenarios need more coverage

**Analysis Background Task Error Recovery:**
- Files: `backend/app/api/endpoints/analyses.py` (lines 2675+)
- Why fragile: Background task catches broad Exception at line 5220, continues with partial results; unclear what "partial" state means
- Safe modification: Map specific error scenarios to specific recovery paths (retry vs skip vs fail); document what analysis state is valid when
- Test coverage: Happy path tested but error recovery scenarios need explicit testing

## Scaling Limits

**Single Analysis Result Storage:**
- Current capacity: Results stored in-database as JSON blobs; 30MB+ for large analyses
- Limit: Database connection pool, memory usage during processing
- Scaling path:
  - Store results in object storage (S3) with database references
  - Implement result pagination/streaming
  - Cache frequently-accessed subsets

**No Caching Strategy for Integration Data:**
- Current capacity: Each analysis re-fetches all integration data (incidents, GitHub PRs, Jira tickets, Slack data)
- Limit: API rate limits on external services, slow repeat analyses
- Scaling path:
  - Cache GitHub/Slack/Jira data with TTL (configurable per integration)
  - Implement incremental collection (only new incidents since last run)
  - Add manual cache invalidation endpoints

**Hardcoded Business Hours Configuration:**
- Issue: Business hours are environment variables but applied globally
- Improvement: Support per-organization business hours configuration
- Impact: Affects late-night burnout penalty calculations

## Dependencies at Risk

**Deprecation of Multiple Analyzer Classes:**
- Risk: Code still references SimpleBurnoutAnalyzer and BurnoutAnalyzerService in 21 places, but these appear to be replaced by UnifiedBurnoutAnalyzer
- Files: Multiple backend files reference deprecated analyzers
- Impact: Migration incomplete; dead code increases maintenance burden
- Migration plan: Remove all SimpleBurnoutAnalyzer/BurnoutAnalyzerService imports and update tests to use UnifiedBurnoutAnalyzer

**Test Data Loader in Production:**
- Risk: Mock data loader is conditionally imported in UnifiedBurnoutAnalyzer and can be enabled via environment variable
- Files: `backend/app/services/unified_burnout_analyzer.py` (lines 36-47, 92-93)
- Impact: If USE_MOCK_DATA=true in production, real analysis doesn't run
- Fix approach: Move mock data loading to test-only code, remove from production service class

## Missing Critical Features

**No Manual Result Correction UI:**
- Problem: If analysis gets user mapping wrong, no way to correct individual scores before reporting
- Blocks: Accurate reporting when integrations don't provide complete user data

**No Analysis Versioning/History:**
- Problem: When scoring algorithm changes, previous analyses become incomparable
- Blocks: Longitudinal burnout tracking across algorithm updates

**No Scheduled Analysis Exports:**
- Problem: Users must manually export analysis results; no scheduled PDF/email reports
- Blocks: Executive visibility into trends without manual intervention

## Test Coverage Gaps

**Untested Analyzer Integration Combinations:**
- What's not tested: Analyses combining all 4 integrations (GitHub + Slack + Jira + Linear) simultaneously
- Files: `backend/app/services/unified_burnout_analyzer.py`
- Risk: Edge cases in multi-integration scoring logic could break unnoticed
- Priority: High (affects core feature)

**Missing Error Path Tests:**
- What's not tested: When integration API calls fail mid-analysis (e.g., GitHub rate limit, Slack timeout)
- Files: `backend/app/services/unified_burnout_analyzer.py`, collector classes
- Risk: Partial analysis state not well-defined, unclear which results are safe to use
- Priority: High (affects reliability)

**Frontend Integration Page State Transitions:**
- What's not tested: All modal/sheet state transitions during integration setup and mapping configuration
- Files: `frontend/src/app/integrations/page.tsx` (5,407 lines, mostly UI state)
- Risk: UI gets into invalid state or loses user input during long operations
- Priority: Medium (affects UX but has workarounds)

**End-to-End Analysis Workflow:**
- What's not tested: Complete flow from running analysis through viewing results across both frontend and backend
- Files: Both frontend and backend
- Risk: Breaking changes in API contracts not caught until production
- Priority: High (core feature)

---

*Concerns audit: 2026-01-30*
