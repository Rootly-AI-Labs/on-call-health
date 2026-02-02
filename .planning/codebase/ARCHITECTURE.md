# Architecture

**Analysis Date:** 2026-01-30

## Pattern Overview

**Overall:** Three-tier distributed microservice architecture with FastAPI backend, Next.js frontend, and heavy emphasis on external API integrations.

**Key Characteristics:**
- Separation of concerns: API layer, business logic (services), data models, and presentation
- Service-oriented: Extensive use of specialized collector and analyzer services
- Integration-heavy: Multiple external APIs (Rootly, PagerDuty, GitHub, Slack, Jira, Linear) with pluggable patterns
- Asynchronous processing: Background tasks for long-running analysis operations
- State management: PostgreSQL for persistence, Redis for distributed locking

## Layers

**Presentation (Frontend):**
- Purpose: React-based Next.js UI for displaying burnout analysis and managing integrations
- Location: `frontend/src/`
- Contains: React components, hooks, contexts, utility functions, TypeScript types
- Depends on: Backend API via HTTP, context providers for state management
- Used by: End users (engineers, team leads, org admins)

**API Layer (Backend):**
- Purpose: RESTful endpoints that handle requests and coordinate business logic
- Location: `backend/app/api/endpoints/`
- Contains: Router definitions, request/response models, endpoint handlers
- Depends on: Authentication, services, models, core utilities
- Used by: Frontend, external integrations, webhooks
- Key files: `analyses.py`, `auth.py`, `rootly.py`, `pagerduty.py`, `slack.py`, `github.py`, `jira.py`, `linear.py`

**Business Logic (Services):**
- Purpose: Encapsulate domain logic for data collection, analysis, and processing
- Location: `backend/app/services/`
- Contains: Collector classes, analyzer classes, mapping services, utility services
- Depends on: Models, core configuration, external API clients
- Key patterns: Separation of concerns, single responsibility per service
- Major services:
  - `unified_burnout_analyzer.py`: Core burnout analysis orchestration
  - `ai_burnout_analyzer.py`: AI-powered burnout analysis
  - `github_collector.py`: GitHub data collection
  - `slack_collector.py`: Slack data collection
  - `github_correlation_service.py`: User-to-GitHub correlation
  - Integration mapping services: `github_mapping_service.py`, `jira_mapping_service.py`, `linear_mapping_service.py`

**Data Access (Models):**
- Purpose: SQLAlchemy ORM models defining database schema and relationships
- Location: `backend/app/models/`
- Contains: SQLAlchemy declarative models with relationships
- Key models: `User`, `Organization`, `Analysis`, `RootlyIntegration`, `GitHubIntegration`, `SlackIntegration`, `JiraIntegration`, `LinearIntegration`, `UserMapping`, `IntegrationMapping`

**Core Infrastructure:**
- Purpose: Configuration, clients, validation, caching, rate limiting
- Location: `backend/app/core/`
- Contains: Settings, API clients, business logic configuration, input validation, caching
- Key files:
  - `config.py`: Environment-based settings
  - `och_config.py`: Burnout scoring configuration and calculation
  - `rootly_client.py`: Rootly API client
  - `pagerduty_client.py`: PagerDuty API client
  - `api_cache.py`: Caching layer for API responses
  - `input_validation.py`: Pydantic request validation
  - `rate_limiting.py`: Rate limit enforcement

**Authentication & Security:**
- Purpose: OAuth, JWT tokens, and security middleware
- Location: `backend/app/auth/` and `backend/app/middleware/`
- Contains: OAuth providers (Google, GitHub, Slack, Jira, Linear), JWT handling, security headers
- Key files: `oauth.py`, `integration_oauth.py`, `jwt.py`, `security.py`, `user_logging.py`

**Frontend State Management:**
- Purpose: React Context API for global state without Redux
- Location: `frontend/src/contexts/`
- Contains: Context providers, context hooks
- Contexts: `GettingStartedContext`, `ChartModeContext`, auth state (implicit in hooks)

## Data Flow

**Analysis Execution Flow:**

1. **Initiation**: User clicks "Run Analysis" in frontend
2. **Request**: Frontend sends `POST /analyses` with integration_id, time_range, and feature flags
3. **Authentication**: `get_current_active_user` dependency validates JWT from httpOnly cookie or Authorization header
4. **Validation**: `AnalysisRequest` Pydantic model validates input
5. **Storage**: Endpoint creates `Analysis` record with status="pending"
6. **Async Task**: `BackgroundTasks.add_task()` queues analysis execution (no formal task queue like Celery)
7. **Collection**: Service fetches data from external APIs (Rootly/PagerDuty for incidents, GitHub/Slack for activity)
8. **Analysis**: `UnifiedBurnoutAnalyzer` orchestrates analysis using:
   - Incident metrics calculation
   - GitHub activity analysis
   - Slack message sentiment analysis
   - User correlation (email to GitHub username)
   - AI-enhanced analysis (if enabled)
9. **Storage**: Results stored as JSON in `Analysis.results`, status updated to "completed"
10. **Retrieval**: Frontend polls `GET /analyses/{analysis_id}` until completed, then displays results

**User Authentication Flow:**

1. User navigates to `/auth` on frontend
2. Frontend redirects to backend OAuth endpoint (e.g., `/auth/google/callback`)
3. Backend validates OAuth token, creates/updates User record
4. JWT token set in httpOnly cookie (secure, httponly, same-site)
5. Frontend can now make authenticated requests

**Integration Connection Flow:**

1. User connects external integration (GitHub, Slack, etc.)
2. User OAuth-authorizes the integration
3. Integration credentials encrypted and stored in integration model
4. Mapping created: User → External Service User ID
5. Collectors use stored credentials to fetch data during analysis

**State Management:**

- **Frontend**: React Context API (`GettingStartedProvider`, `ChartModeProvider`) + local component state
- **Backend**: PostgreSQL for persistence, Redis for distributed locks during token refresh
- **Session**: JWT tokens with 7-day expiration stored in httpOnly cookies

## Key Abstractions

**Analyzer Abstraction:**

- Purpose: Different analysis strategies for different integration types
- Examples: `UnifiedBurnoutAnalyzer`, `GitHubOnlyBurnoutAnalyzer`, `DemoAnalysisService`
- Pattern: Single interface with different data sources
- Location: `backend/app/services/`

**Collector Abstraction:**

- Purpose: Unified interface for collecting data from external sources
- Examples: `GitHubCollector`, `SlackCollector`, collectors for Rootly/PagerDuty
- Pattern: Async methods for fetching and correlating data
- Location: `backend/app/services/`

**Mapping Service Abstraction:**

- Purpose: Correlate users across systems (email to GitHub username, Slack user ID, etc.)
- Examples: `GitHubMappingService`, `JiraUserSyncService`, `ManualMappingService`
- Pattern: Multiple matching strategies, user-overridable manual mappings
- Location: `backend/app/services/`

**Integration Model Abstraction:**

- Purpose: Unified schema for storing credentials/tokens for different platforms
- Examples: `RootlyIntegration`, `GitHubIntegration`, `SlackIntegration`
- Pattern: Encrypted token storage, platform-specific metadata
- Location: `backend/app/models/`

**API Client Abstraction:**

- Purpose: Encapsulate HTTP logic and auth for external APIs
- Examples: `RootlyAPIClient`, `PagerDutyAPIClient`
- Pattern: Async HTTP client with caching and rate limiting
- Location: `backend/app/core/`

## Entry Points

**Backend Entry Point:**
- Location: `backend/app/main.py`
- Triggers: `uvicorn app.main:app`
- Responsibilities:
  - Initialize FastAPI app with middleware (CORS, security, rate limiting, GZip)
  - Register routers for all endpoints
  - Start database migrations on startup
  - Start survey scheduler background task
  - Configure logging with user context filter

**Frontend Entry Point:**
- Location: `frontend/src/app/layout.tsx`
- Triggers: Next.js routing (browser navigation)
- Responsibilities:
  - Wrap app with providers (`GettingStartedProvider`, `ChartModeProvider`, `NewRelicProvider`)
  - Initialize error boundary and auth interceptor
  - Load Google Analytics if configured
  - Render child routes

**API Endpoints (Major):**
- `POST /analyses` - Start new burnout analysis (`backend/app/api/endpoints/analyses.py`)
- `GET /analyses` - List user's analyses (`backend/app/api/endpoints/analyses.py`)
- `GET /analyses/{id}` - Retrieve analysis details (`backend/app/api/endpoints/analyses.py`)
- `POST /auth/google/callback` - OAuth callback (`backend/app/api/endpoints/auth.py`)
- `POST /integrations` - Connect external integration (`backend/app/api/endpoints/github.py`, `slack.py`, etc.)
- `GET /dashboard` - Get dashboard data (`frontend/src/app/dashboard/page.tsx`)

**Background Processes:**
- Survey scheduler: Runs surveys on schedule (`backend/app/services/survey_scheduler.py`)
- Analysis execution: Runs in background task pool (not a dedicated queue)

## Error Handling

**Strategy:** Multi-layered error handling with custom exception classes, retry logic, and graceful degradation.

**Patterns:**

**Custom Exception Classes:**
- `RetryableError`: Temporary errors that can be retried (rate limits, timeouts)
- `NonRetryableError`: Permanent errors that should not be retried (auth failures, invalid input)
- Location: `backend/app/core/error_handler.py`

**Retry Mechanism:**
- Location: `backend/app/core/error_handler.py`
- Implementation: Exponential backoff with configurable max retries
- Used for: API calls that may temporarily fail due to rate limits or network issues

**Error Suppression:**
- `ErrorSuppressor` context manager: Catches exceptions and returns defaults instead of crashing
- Used for: Optional data collection (GitHub, Slack activity when unavailable)
- Pattern: `try-except` blocks that log but continue analysis with partial data

**HTTP Error Handling:**
- FastAPI dependency exceptions converted to HTTP responses
- 401 for auth failures, 422 for validation errors, 500 for server errors
- Logging middleware captures all errors with user context

**API Response Validation:**
- Pydantic models validate all request/response data
- Invalid requests rejected before business logic execution
- Location: `backend/app/core/input_validation.py`

## Cross-Cutting Concerns

**Logging:**
- Approach: Structured logging with user context (user_id, analysis_ref)
- Implementation: `UserContextFilter` adds context to all log records
- Location: `backend/app/main.py`, `backend/app/middleware/user_logging.py`
- Levels: Configurable via `LOG_LEVEL` env var; suppresses verbose libraries in production

**Validation:**
- Input validation: Pydantic models in `backend/app/core/input_validation.py`
- Business validation: Service-level checks (e.g., integration has required credentials)
- Database constraints: Unique indices, foreign keys in SQLAlchemy models

**Authentication:**
- OAuth flow: `/auth/{provider}/callback` endpoints handle token exchange
- JWT tokens: Signed with `JWT_SECRET_KEY`, expires in 7 days
- Credentials dependency: Checks Authorization header or httpOnly cookie
- Location: `backend/app/auth/dependencies.py`, `backend/app/api/endpoints/auth.py`

**Rate Limiting:**
- Slowapi integration: Per-endpoint rate limit decorators
- General limits: 100 req/min per user
- Analysis limits: More restrictive limits on computationally expensive endpoints
- Location: `backend/app/core/rate_limiting.py`

**Caching:**
- API response caching: `APICache` wraps external API calls
- Purpose: Reduce external API calls and improve performance
- TTL: Configurable per cache key
- Location: `backend/app/core/api_cache.py`

**Data Encryption:**
- OAuth tokens encrypted at rest in database
- Encryption key: `ENCRYPTION_KEY` separate from JWT secret
- Implementation: `cryptography` library with Fernet symmetric encryption
- Used for: Rootly API tokens, GitHub tokens, Slack tokens, etc.

---

*Architecture analysis: 2026-01-30*
