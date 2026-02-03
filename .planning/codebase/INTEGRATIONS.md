# External Integrations

**Analysis Date:** 2026-01-30

## APIs & External Services

**Incident & On-Call Platforms:**
- **Rootly** - Incident management and response platform
  - SDK/Client: Custom `RootlyAPIClient` in `backend/app/core/rootly_client.py`
  - Auth: `ROOTLY_API_KEY` environment variable
  - Base URL: `ROOTLY_API_BASE_URL` (default: https://api.rootly.com)
  - Used for: Fetching incidents, incident resolution data, user schedules
  - Timeout: 32s for incidents endpoint, 30s default

- **PagerDuty** - On-call scheduling and alerting
  - SDK/Client: Custom `PagerDutyClient` in `backend/app/core/pagerduty_client.py`
  - Auth: `PAGERDUTY_API_KEY` environment variable
  - Used for: Fetching on-call schedules, incidents, user data
  - Integration: Token validation and caching

**Code & Issue Tracking:**
- **Jira** - Issue tracking and project management
  - OAuth: OAuth 2.0 integration via `backend/app/auth/integration_oauth.py`
  - Config: `JIRA_CLIENT_ID`, `JIRA_CLIENT_SECRET`
  - Callback: `GET /auth/jira/callback`
  - Used for: Mapping issues to incidents, workload analysis
  - Token Storage: Encrypted in database via `JiraIntegration` model
  - Automatic Token Refresh: Implemented for OAuth tokens

- **Linear** - Issue tracking and planning
  - OAuth: OAuth 2.0 integration via `backend/app/auth/integration_oauth.py`
  - Config: `LINEAR_CLIENT_ID`, `LINEAR_CLIENT_SECRET`
  - Callback: `GET /auth/linear/callback`
  - Used for: Issue mapping, workload analysis
  - Token Storage: Encrypted in database via `LinearIntegration` model
  - Workspace Mapping: Stored in `LinearWorkspaceMapping` model

- **GitHub** - Code repository and collaboration
  - OAuth: OAuth 2.0 integration for authentication (see below)
  - API Integration: Direct GitHub API via PAT in `backend/app/auth/integration_oauth.py`
  - Config: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_TOKEN` (PAT)
  - Used for: Repository data, commit analysis, PR activity

**Communication:**
- **Slack** - Team messaging and notifications
  - OAuth: OAuth 2.0 integration via `backend/app/auth/integration_oauth.py`
  - Config: `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_SIGNING_SECRET`
  - Callback: `GET /auth/slack/callback`
  - Used for: Message analysis, channel data, team metrics
  - Token Storage: Encrypted in database via `SlackIntegration` model
  - Workspace Mapping: Stored in `SlackWorkspaceMapping` model

## Authentication & Identity

**User Login Providers (OAuth 2.0):**
- **Google OAuth**
  - Implementation: `GoogleOAuth` class in `backend/app/auth/oauth.py`
  - Endpoints: `GET /auth/google`, `GET /auth/google/callback`
  - Scopes: `openid email profile`
  - Config: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
  - Redirect URI: `GOOGLE_REDIRECT_URI` (default: http://localhost:8000/auth/google/callback)

- **GitHub OAuth**
  - Implementation: `GitHubOAuth` class in `backend/app/auth/oauth.py`
  - Endpoints: `GET /auth/github`, `GET /auth/github/callback`
  - Config: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`
  - Redirect URI: `GITHUB_REDIRECT_URI` (default: http://localhost:8000/auth/github/callback)

**Session Management:**
- JWT tokens for API authentication
  - Secret: `JWT_SECRET_KEY` (required, generated via `openssl rand -hex 32`)
  - Algorithm: HS256
  - Expiration: 7 days
  - Stored in httpOnly cookies or Authorization header

- Token encryption for sensitive data
  - Encryption Key: `ENCRYPTION_KEY` (required, generated via `openssl rand -base64 32`)
  - Method: Fernet (symmetric encryption)
  - Used for: OAuth tokens, API tokens, LLM keys stored in database

## Data Storage

**Database:**
- PostgreSQL 15
  - Connection: `DATABASE_URL` env var (e.g., `postgresql://postgres:password@postgres:5432/burnout_detector`)
  - ORM: SQLAlchemy
  - Models location: `backend/app/models/`
  - Migrations: Alembic in `backend/migrations/`
  - Key tables: `users`, `oauth_provider`, `jira_integration`, `linear_integration`, `slack_integration`, `user_burnout_report`, `survey_period`

**Caching & Locking:**
- Redis 7
  - Connection: `REDIS_URL` or `REDIS_HOST:REDIS_PORT` env vars
  - Client: `redis` Python library
  - Uses:
    - API response caching (`api_cache.py`)
    - Distributed locking for token refresh (`distributed_lock.py`)
    - Rate limiting via slowapi
  - Default DB: 1 (configurable via `REDIS_DB`)

**File Storage:**
- Local filesystem only - No external file storage service
- Mock data helpers in `backend/mock_data_helpers/`

## LLM Integration

**Language Models:**
- **Anthropic Claude** - Primary AI model
  - SDK: `anthropic` Python library
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Integration: Both system-level and per-user token storage
  - Endpoint: `/api/llm/token` for token management

- **OpenAI** - Alternative LLM provider
  - SDK: `openai` Python library
  - Auth: User-provided API key via `/api/llm/token`
  - Used by: Agent framework (smolagents) as fallback

**AI Framework:**
- **smolagents** - Agent framework for agentic analysis
  - Integration: `CodeAgent` in `backend/app/agents/burnout_agent.py`
  - Supports: LiteLLMModel abstraction layer
  - Custom tools: Sentiment, pattern, workload, code quality analysis

**Model Abstraction:**
- **litellm** - Unified LLM interface
  - Supports: Multiple providers (OpenAI, Anthropic, others)
  - Used by: smolagents framework for model flexibility

## Monitoring & Observability

**Error Tracking & APM:**
- **New Relic** - Application Performance Monitoring
  - Backend: `newrelic` Python agent
    - Config: `backend/newrelic.ini`
    - License: `NEW_RELIC_LICENSE_KEY` env var
    - App name: `NEW_RELIC_APP_NAME` env var
  - Frontend: `@newrelic/browser-agent` npm package
    - Config via env vars:
      - `NEXT_PUBLIC_NEW_RELIC_ACCOUNT_ID`
      - `NEXT_PUBLIC_NEW_RELIC_TRUST_KEY`
      - `NEXT_PUBLIC_NEW_RELIC_AGENT_ID`
      - `NEXT_PUBLIC_NEW_RELIC_LICENSE_KEY`
      - `NEXT_PUBLIC_NEW_RELIC_APPLICATION_ID`

**Logging:**
- Python logging module (backend)
  - Log level: `LOG_LEVEL` env var (default: INFO)
  - Output: Console and New Relic agent
  - Contextualized logging: `backend/app/middleware/logging_context.py`
  - User tracking: `backend/app/middleware/user_logging.py`

**Analytics:**
- **Google Analytics 4** (optional)
  - Frontend: `NEXT_PUBLIC_GA_MEASUREMENT_ID` env var
  - Default ID: `G-VMJT128VZS` (project's own measurement)
  - Optional: Users can provide their own GA4 measurement ID

## CI/CD & Deployment

**Hosting:**
- Railway - Container hosting platform
  - Base images: `rootlyio/on-call-health:backend-base` and `rootlyio/on-call-health:frontend-base`
  - Environment: Both staging and production supported
  - Secrets managed via Railway environment variables

**CI Pipeline:**
- GitHub Actions
  - Workflow files in `.github/workflows/`
  - `ci.yml` - Build and test pipeline
  - `e2e-tests.yml` - End-to-end testing with Playwright
  - `claude-code-review.yml` - AI-powered code review

**Deployment Process:**
- Docker-based deployment
  - Backend: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
  - Database migrations: Automated in `start.sh` (alembic)
  - Frontend: `bun run build && next start`

## Webhooks & Callbacks

**Incoming Webhooks:**
- OAuth callbacks for integration setup:
  - `GET /auth/google/callback` - Google OAuth completion
  - `GET /auth/github/callback` - GitHub OAuth completion
  - `GET /auth/jira/callback` - Jira OAuth completion
  - `GET /auth/linear/callback` - Linear OAuth completion
  - `GET /auth/slack/callback` - Slack OAuth completion

**Outgoing Webhooks:**
- Not detected - Integrations use polling/API calls rather than event-driven webhooks

## Environment Configuration

**Required Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Secret for JWT signing (generate: `openssl rand -hex 32`)
- `ENCRYPTION_KEY` - Key for token encryption (generate: `openssl rand -base64 32`)

**Optional but Recommended:**
- `ROOTLY_API_KEY` - Rootly API authentication
- `PAGERDUTY_API_KEY` - PagerDuty API authentication
- `FRONTEND_URL` - URL for survey links (default: http://localhost:3000)
- `ENVIRONMENT` - Environment name (default: development)
- `LOG_LEVEL` - Logging verbosity (default: INFO, use WARNING for production)

**OAuth Configuration:**
- Google: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- GitHub: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI`, `GITHUB_TOKEN`
- Jira: `JIRA_CLIENT_ID`, `JIRA_CLIENT_SECRET`
- Linear: `LINEAR_CLIENT_ID`, `LINEAR_CLIENT_SECRET`
- Slack: `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_SIGNING_SECRET`, `SLACK_REDIRECT_URI`

**LLM Configuration:**
- `ANTHROPIC_API_KEY` - For system-level Claude API access
- User-provided LLM keys stored encrypted in database

**Frontend-Specific:**
- `NEXT_PUBLIC_API_URL` - Backend API base URL
- `NEXT_PUBLIC_GA_MEASUREMENT_ID` - Google Analytics measurement ID
- `NEXT_PUBLIC_SLACK_CLIENT_ID` - For OAuth flow from frontend
- `NEXT_PUBLIC_JIRA_CLIENT_ID` - For OAuth flow from frontend
- `NEXT_PUBLIC_NEW_RELIC_*` - New Relic browser monitoring configuration

## Working Hours & Timezone Configuration

**Business Hours Customization:**
- `BUSINESS_HOURS_START` - Start of business hours (default: 9, 24-hour format)
- `BUSINESS_HOURS_END` - End of business hours (default: 17)
- `LATE_NIGHT_START` - Start of late night (default: 22)
- `LATE_NIGHT_END` - End of late night (default: 6)
- Note: All times applied in user's local timezone (fetched from Rootly/PagerDuty profiles)

## Rate Limiting

**Configuration:**
- `BYPASS_RATE_LIMITING` - Bypass rate limits for development (default: false)
- Redis-based rate limiting via slowapi
- Token refresh distributed locking:
  - `TOKEN_REFRESH_LOCK_TTL` - TTL for lock (default: 30s)
  - `TOKEN_REFRESH_LOCK_TIMEOUT` - Lock acquisition timeout (default: 10s)

---

*Integration audit: 2026-01-30*
