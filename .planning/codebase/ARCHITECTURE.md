# Architecture

**Analysis Date:** 2026-01-30

## Pattern Overview

**Overall:** Monolithic full-stack application with clear separation between frontend (Next.js) and backend (FastAPI), following a layered architecture with domain-driven service organization.

**Key Characteristics:**
- Multi-tenant SaaS architecture supporting organizations with multiple team members
- Event-driven burnout analysis powered by AI agents and unified analyzer
- OAuth-based authentication (Google, GitHub, Slack, Jira, Linear) with JWT session tokens
- Multi-source data collection from incident platforms (Rootly, PagerDuty) and developer tools (GitHub, Slack, Jira, Linear)
- API-first backend with async processing for analysis jobs and surveys
- Real-time dashboard with cached analysis results and lazy loading

## Layers

**Presentation (Frontend):**
- Purpose: User-facing interface for dashboard, integrations, setup, and account management
- Location: `frontend/src/`
- Contains: Next.js pages, React components, hooks, contexts, and UI library integration
- Depends on: Backend REST API, localStorage for token/state, contexts for global state
- Used by: End users via web browser

**API Layer (Backend):**
- Purpose: REST endpoints for authentication, analysis, integrations, and data management
- Location: `backend/app/api/endpoints/`
- Contains: FastAPI routers for auth, analyses, integrations (GitHub, Slack, Jira, Linear, Rootly, PagerDuty), notifications, surveys, invitations, admin operations
- Depends on: Models, Services, Core utilities, Auth/Dependencies
- Used by: Frontend application, external webhooks (Slack, etc.)

**Business Logic Layer (Services):**
- Purpose: Core domain logic for burnout analysis, data collection, user synchronization, and token management
- Location: `backend/app/services/`
- Contains: Burnout analyzers (unified, AI-enhanced, GitHub-only), collectors (GitHub, Slack), mappers (GitHub, Jira, Linear), account linking, user sync, notification service, survey scheduler, token refresh coordinator
- Key files: `unified_burnout_analyzer.py`, `ai_burnout_analyzer.py`, `slack_collector.py`, `github_collector.py`, `survey_scheduler.py`
- Depends on: Models, Core utilities, External API clients
- Used by: API endpoints, Agents

**Data/Persistence Layer:**
- Purpose: Database models and ORM configuration for all entities
- Location: `backend/app/models/`
- Contains: User, Organization, Analysis, Integration models (Rootly, GitHub, Slack, Jira, Linear), mappings, survey data, notifications, invitations, correlations
- Database: PostgreSQL via SQLAlchemy ORM
- Depends on: SQLAlchemy, Core config for database connection
- Used by: All services and API endpoints

**Core Utilities Layer:**
- Purpose: Shared configuration, clients, caching, validation, and cross-cutting concerns
- Location: `backend/app/core/`
- Contains: Configuration settings, API cache, distributed locking (Redis), rate limiting, input validation, PagerDuty/Rootly API clients, platform scoring, burnout config
- Depends on: External services (Redis, third-party APIs), Models
- Used by: Services, API endpoints, Middleware

**Authentication & Authorization:**
- Purpose: User identity verification and session management
- Location: `backend/app/auth/`
- Contains: JWT token creation/decoding, OAuth flow handlers (Google, GitHub, Slack, Jira, Linear), integration OAuth managers, dependency injection for authenticated endpoints
- Key files: `jwt.py`, `oauth.py`, `integration_oauth.py`, `dependencies.py`
- Depends on: Core config, Models, Encryption utilities
- Used by: All authenticated endpoints

**Middleware & Cross-Cutting Concerns:**
- Purpose: Request/response processing, security headers, logging context, rate limiting
- Location: `backend/app/middleware/`
- Contains: Security middleware (CORS, CSRF, headers), user logging context (adds user_id to log records), logging configuration
- Depends on: Core utilities, Models
- Used by: FastAPI application

**Agents (Experimental):**
- Purpose: AI-powered burnout analysis using smolagents framework
- Location: `backend/app/agents/`
- Contains: BurnoutDetectionAgent with tools for sentiment analysis, pattern analysis, workload analysis, code quality analysis, cross-platform correlation, burnout prediction
- Depends on: LLM provider (OpenAI/Anthropic via LiteLLM), service layer data
- Used by: AI-enhanced burnout analyzer services

**MCP Server (Experimental):**
- Purpose: Model Context Protocol server for Claude/AI integration
- Location: `backend/app/mcp/`
- Contains: MCP server definition with resources and tools for analysis, integrations, and user access
- Depends on: Models, Services, Auth
- Used by: External Claude/AI systems via MCP protocol

## Data Flow

**User Authentication & Session Flow:**

1. User visits `/auth/login` (frontend)
2. Frontend presents OAuth provider choices (Google, GitHub)
3. User selects provider, frontend redirects to `/auth/{provider}` (backend)
4. Backend initiates OAuth handshake with provider
5. Provider redirects back to `/auth/{provider}/callback` with authorization code
6. Backend exchanges code for access token with provider
7. Backend creates or updates User in database, generates JWT
8. Backend sets `auth_token` as httpOnly cookie and redirects to frontend
9. Frontend stores token in localStorage (from cookie via JavaScript)
10. All subsequent requests include JWT in Authorization header or cookie
11. Middleware validates token and adds user_id to request context

**Integration OAuth Setup Flow (Slack/Jira/Linear/GitHub - as data source):**

1. User navigates to `/integrations` dashboard
2. Frontend shows "Connect [Platform]" dialog
3. User clicks connect, frontend redirects to `/integrations/{platform}/oauth-start`
4. Backend initiates OAuth handshake specific to that integration
5. Integration provider redirects back to callback with auth code
6. Backend exchanges code for access token, stores encrypted token in database
7. Backend validates permissions and triggers user sync job (async)
8. Frontend polls status or receives webhook notification
9. Integration now available in analysis workflow

**Burnout Analysis Flow:**

1. Frontend calls `POST /analyses` with integration_id, time_range, include_github flag
2. API validates request and checks user permissions
3. Backend queues analysis as background task
4. Analysis service fetches raw data from integrated platforms:
   - Rootly/PagerDuty for incident data
   - GitHub for commit/PR activity
   - Slack for message patterns
   - Jira/Linear for issue activity
5. Data gets cleaned, normalized, and correlated across platforms
6. Unified analyzer applies burnout scoring logic:
   - Time-based scoring (after-hours, weekends)
   - Workload metrics (commits, incidents, issue volume)
   - Severity weighting
   - Team composition metrics
7. (Optional) AI analyzer provides enriched insights if enabled
8. Results stored in Analysis table with summary extraction (reduces 30MB+ to <1KB)
9. Frontend polls `/analyses/{id}` or receives completion notification
10. Dashboard displays results: team health score, member burnout risks, trend charts

**Survey Lifecycle:**

1. Survey schedule configured by admin (via UI or API)
2. SurveyScheduler (background task, started at app startup) triggers periodic surveys
3. Scheduler queries SurveySchedule entries and creates Survey instances
4. Slack channel gets invitation posted or DM sent to users
5. Users click survey link (frontend `/surveys/{survey_id}`)
6. Frontend collects responses, POSTs to `/api/surveys/responses`
7. Responses stored in database
8. Analysis includes survey data in burnout scoring calculations

**State Management (Frontend):**

- Auth token: localStorage (`auth_token`)
- User session: AuthInterceptor component validates on app load
- Analysis results: useDashboard hook with in-memory caching (Map<id, AnalysisResult>)
- Global UI state: ChartModeProvider (chart view mode), GettingStartedProvider (onboarding)
- API data: On-demand fetching with localStorage fallback for offline resilience

## Key Abstractions

**UnifiedBurnoutAnalyzer:**
- Purpose: Core burnout detection engine combining multi-source data
- Location: `backend/app/services/unified_burnout_analyzer.py`
- Pattern: Service class with async methods for different analysis types
- Used by: Analysis endpoints
- Responsibilities: Coordinate collectors, apply scoring logic, generate team/member reports

**DataCollector (Abstract Base):**
- Purpose: Standard interface for fetching platform-specific data
- Implementations: GitHubCollector, SlackCollector, RootlyClient, PagerDutyClient
- Pattern: Collector classes with API-specific logic, shared caching via ApiCache
- Used by: Burnout analyzer, Integration setup flows

**Integration Models (Polymorphic):**
- Purpose: Represent connections to external platforms
- Classes: RootlyIntegration, GitHubIntegration, SlackIntegration, JiraIntegration, LinearIntegration
- Pattern: Each integration inherits from base, stores platform-specific tokens/config
- Location: `backend/app/models/`
- Relationships: User->Organization->Integrations (many-to-one hierarchy)

**User Mapping Entities:**
- Purpose: Match team members across different platforms (Slack user ↔ GitHub user ↔ Jira user)
- Classes: UserMapping, SlackWorkspaceMapping, JiraWorkspaceMapping, LinearWorkspaceMapping, IntegrationMapping
- Pattern: Joiners/mappers bridging identities across platforms
- Used by: Analysis to correlate activity across sources

**OAuth Provider Pattern:**
- Purpose: Standardized OAuth token management for user authentication
- Classes: OAuthProvider, UserEmail
- Pattern: Separate from integration OAuth; handles primary login credentials
- Used by: Auth endpoints, User creation/update

**API Cache & Distributed Lock:**
- Purpose: Reduce API calls, coordinate concurrent operations
- Location: `backend/app/core/api_cache.py`, `backend/app/core/distributed_lock.py`
- Pattern: TTL-based caching via Redis, pessimistic locking for token refresh
- Used by: All data collectors, token refresh coordinator

## Entry Points

**Frontend Entry Point:**
- Location: `frontend/src/app/layout.tsx`
- Triggers: Browser navigation to `/`
- Responsibilities:
  - Load root layout with providers (ChartModeProvider, GettingStartedProvider)
  - Initialize ErrorBoundary for error handling
  - Set up NewRelicProvider for monitoring
  - Configure auth interceptor
  - Register global CSS and fonts

**Backend Entry Point:**
- Location: `backend/app/main.py`
- Triggers: Application startup (via uvicorn or Docker)
- Responsibilities:
  - Configure FastAPI app with middleware stack (CORS, GZip, Security, User Logging)
  - Register all API routers
  - Set up rate limiting and exception handlers
  - Run database migrations on startup
  - Initialize survey scheduler background task
  - Load survey schedules from database

**API Endpoints Entry Points (by domain):**
- Authentication: `backend/app/api/endpoints/auth.py` → `/auth/{provider}`, `/auth/{provider}/callback`
- Analyses: `backend/app/api/endpoints/analyses.py` → `POST /analyses`, `GET /analyses`
- Integrations: Multiple routers for setup/config
- Webhooks: Slack/GitHub/Jira/Linear event receivers

**Background Job Entry Points:**
- SurveyScheduler: Started in main.py startup event, runs periodic surveys
- Analysis Job: Triggered by API endpoint, runs async via BackgroundTasks
- Token Refresh: TokenRefreshCoordinator triggered by token-expired events

## Error Handling

**Strategy:** Defensive with context-aware error messages; fail fast for invalid inputs, graceful degradation for external API failures.

**Patterns:**

- **Input Validation:** `backend/app/core/input_validation.py` defines Pydantic models for all endpoints; automatic 422 responses for invalid data
- **Rate Limiting:** `backend/app/core/rate_limiting.py` uses slowapi; custom handler returns 429 with retry-after header
- **External API Failures:** Services catch exceptions from third-party APIs (GitHub, Slack, etc.), log context, return partial results or retry with exponential backoff
- **Database Errors:** Middleware logs OperationalError with user_id context; API returns 500 with generic message (details in logs)
- **Authentication Failures:** Dependency injection raises 401 Unauthorized with "Could not validate credentials" message
- **Authorization Failures:** Service methods check user ownership; return 403 Forbidden if user lacks permission

**Frontend Error Handling:**
- AuthInterceptor catches 401 responses, redirects to login
- API calls wrapped in try/catch, show toast notifications for user-visible errors
- ErrorBoundary catches React component errors, displays fallback UI

## Cross-Cutting Concerns

**Logging:**
- Centralized in `backend/app/main.py` with custom format: `%(asctime)s - %(name)s - %(levelname)s - [user=%(user_id)s]%(analysis_ref)s - %(message)s`
- UserContextFilter (in `middleware/logging_context.py`) adds user_id to every log record
- All loggers inherit this context, enabling audit trails and debugging per-user

**Validation:**
- Pydantic models in `backend/app/core/input_validation.py` validate all API inputs
- Custom validators for integration configs, email addresses, date ranges
- Automatic 422 responses on validation failure

**Authentication:**
- HTTPBearer + JWT: Authorization header or httpOnly cookie
- Token expiry: 7 days (configurable)
- Refresh: Automatic token refresh via TokenRefreshCoordinator on expiry detection

**Rate Limiting:**
- Global limit: 100 requests/minute per IP
- Auth endpoints: 10 requests/minute to prevent brute force
- Analysis endpoints: 5 requests/minute per user to prevent runaway jobs
- Custom handler returns 429 with retry-after

**Caching:**
- API responses cached in Redis (TTL varies by endpoint)
- Frontend: In-memory Map cache for analysis results
- Database query optimization via SQLAlchemy eager loading

---

*Architecture analysis: 2026-01-30*
