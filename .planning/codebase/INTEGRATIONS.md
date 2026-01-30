# External Integrations

**Analysis Date:** 2026-01-30

## APIs & External Services

**Incident Management:**
- PagerDuty - On-call schedules and incident data
  - SDK/Client: Custom `PagerDutyAPIClient` in `backend/app/core/pagerduty_client.py`
  - Auth: API token via `PAGERDUTY_API_KEY` (HTTP `Authorization: Token token=X`)
  - Base URL: `https://api.pagerduty.com`
  - Data: Users, on-call schedules, incidents with timezone normalization

- Rootly - Engineering reliability platform (primary on-call data source)
  - SDK/Client: Custom HTTP client in `backend/app/api/endpoints/rootly.py`
  - Auth: API token
  - Base URL: Configurable via `ROOTLY_API_BASE_URL` (default: `https://api.rootly.com`)
  - Data: On-call schedules, incidents, team metadata

**Social/Communication:**
- Slack - Team messaging and notifications
  - SDK/Client: Custom collectors in `backend/app/services/slack_collector.py` and `backend/app/services/enhanced_slack_collector.py`
  - OAuth: `slack_integration_oauth` in `backend/app/auth/integration_oauth.py`
  - Auth: OAuth 2.0 with client ID/secret or bot token
  - Client ID env var: `SLACK_CLIENT_ID`
  - Client Secret env var: `SLACK_CLIENT_SECRET`
  - Signing secret env var: `SLACK_SIGNING_SECRET` (for webhook verification)
  - Webhook handling: Incoming webhooks in `backend/app/api/endpoints/slack.py`
  - Data: Messages, user activity, workspace info
  - Service: Direct message sending via `backend/app/services/slack_dm_sender.py`

- GitHub - Code repository and team activity
  - SDK/Client: Custom `GitHubCollector` in `backend/app/services/github_collector.py`
  - HTTP library: `requests` module
  - OAuth: `github_integration_oauth` in `backend/app/auth/integration_oauth.py`
  - Auth: OAuth 2.0 with client ID/secret
  - Client ID env var: `GITHUB_CLIENT_ID`
  - Client Secret env var: `GITHUB_CLIENT_SECRET`
  - Frontend OAuth: `NEXT_PUBLIC_GITHUB_CLIENT_ID` available but optional
  - Data: Commits, pull requests, code reviews, team contributions
  - Service: `backend/app/services/github_api_manager.py` for API calls

- Jira - Issue tracking and project management
  - SDK/Client: Custom client in `backend/app/api/endpoints/jira.py`
  - OAuth: `jira_integration_oauth` in `backend/app/auth/integration_oauth.py`
  - Auth: OAuth 2.0 with client ID/secret
  - Client ID env var: `JIRA_CLIENT_ID`
  - Client Secret env var: `JIRA_CLIENT_SECRET`
  - HTTP library: `httpx` for async requests
  - Service: `backend/app/services/jira_user_sync_service.py` for user synchronization
  - Data: Issues, worklogs, project metadata

- Linear - Modern issue tracking
  - SDK/Client: Custom client in `backend/app/api/endpoints/linear.py`
  - OAuth: `linear_integration_oauth` in `backend/app/auth/integration_oauth.py`
  - Auth: OAuth 2.0 with client ID/secret
  - Client ID env var: `LINEAR_CLIENT_ID`
  - Client Secret env var: `LINEAR_CLIENT_SECRET`
  - Data: Issues, cycles, team members

**Authentication Providers:**
- Google OAuth - Login and user authentication
  - Provider: `GoogleOAuth` in `backend/app/auth/oauth.py`
  - Client ID env var: `GOOGLE_CLIENT_ID`
  - Client Secret env var: `GOOGLE_CLIENT_SECRET`
  - Redirect URI: Configurable via `GOOGLE_REDIRECT_URI` (default: `http://localhost:8000/auth/google/callback`)
  - Auth endpoints: `https://accounts.google.com/o/oauth2/auth`, `https://oauth2.googleapis.com/token`
  - Scopes: `openid email profile`

- GitHub OAuth - Login and user authentication
  - Provider: `GitHubOAuth` in `backend/app/auth/oauth.py`
  - Client ID env var: `GITHUB_CLIENT_ID`
  - Client Secret env var: `GITHUB_CLIENT_SECRET`
  - Redirect URI: Configurable via `GITHUB_REDIRECT_URI` (default: `http://localhost:8000/auth/github/callback`)
  - Scopes: `user:email`

**AI/LLM Services (conditional):**
- Anthropic API - AI burnout analysis (conditionally imported)
  - Client: Imported dynamically in `backend/app/api/endpoints/llm.py`
  - Usage: AI-powered analysis of burnout indicators

- OpenAI API - AI burnout analysis (conditionally imported)
  - Client: Imported dynamically in `backend/app/api/endpoints/llm.py`
  - Usage: Alternative AI provider for analysis

## Data Storage

**Databases:**
- PostgreSQL 15
  - Connection: `DATABASE_URL` environment variable (required)
  - Client: SQLAlchemy ORM with psycopg2-binary driver
  - Pool: 30 base connections + 20 overflow (total max: 50)
  - Query timeout: 60 seconds (configurable via `DB_STATEMENT_TIMEOUT_MS`)
  - Lock timeout: 30 seconds (configurable via `DB_LOCK_TIMEOUT_MS`)
  - Pool recycle: 5 minutes (connections recycled every 300 seconds)
  - Migrations: Alembic in `backend/migrations/` (run automatically at startup)

**File Storage:**
- Local filesystem only
  - Static files: `app/static/` for favicon.svg and API documentation assets
  - No external storage (S3, GCS, etc.) configured

**Caching:**
- Redis 7
  - Connection: `REDIS_URL` (default: `redis://localhost:6379`)
  - Alternative config: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
  - Client: Python `redis` module
  - Purpose: Distributed rate limiting and locking
  - Distributed lock service: `backend/app/core/distributed_lock.py` for token refresh coordination
  - API response caching: `backend/app/core/api_cache.py` for PagerDuty/Rootly responses (1-hour TTL)

## Authentication & Identity

**Auth Provider:**
- Custom OAuth implementation
  - Implementation: `backend/app/auth/oauth.py` for Google/GitHub
  - Implementation: `backend/app/auth/integration_oauth.py` for Slack/GitHub/Jira/Linear integrations
  - Token storage: Encrypted in database (`ENCRYPTION_KEY` required)
  - JWT: HS256 signing key (`JWT_SECRET_KEY` required)
  - Token expiry: 7 days (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7`)
  - Encryption: Separate encryption key for OAuth tokens to prevent token exposure on database breach

**Session Management:**
- Frontend: localStorage for `auth_token` (retrieved in `frontend/src/components/integrations/api-service.ts`)
- Backend: JWT tokens in Authorization header
- CORS: Configured for localhost:3000-3002 (dev) and production domains
  - `https://www.oncallburnout.com`, `https://oncallburnout.com`
  - Dynamic: `PRODUCTION_FRONTEND_URL` and `VERCEL_URL` if set

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry, Rollbar, etc.)
- Application uses standard logging with context

**Logs:**
- Standard Python logging in backend
  - Format: `%(asctime)s - %(name)s - %(levelname)s - [user=%(user_id)s]%(analysis_ref)s - %(message)s`
  - User context: Middleware in `backend/app/middleware/user_logging.py` adds user_id to all logs
  - Configurable level via `LOG_LEVEL` env var (default: INFO)
  - Production: WARNING level recommended to reduce noise
- Browser monitoring: New Relic (optional, via frontend env vars)
  - `NEXT_PUBLIC_NEW_RELIC_ACCOUNT_ID`
  - `NEXT_PUBLIC_NEW_RELIC_TRUST_KEY`
  - `NEXT_PUBLIC_NEW_RELIC_AGENT_ID`
  - `NEXT_PUBLIC_NEW_RELIC_LICENSE_KEY`
  - `NEXT_PUBLIC_NEW_RELIC_APPLICATION_ID`
- Server monitoring: New Relic (optional, backend)
  - Package: `newrelic` in requirements.txt (agent would be configured via newrelic.ini)

## CI/CD & Deployment

**Hosting:**
- Primary: Railway (platform-specific env vars supported)
  - Detection: `VERCEL_URL` environment variable
  - Fallback: Vercel Next.js deployment support
- Docker containerization: `frontend/Dockerfile`, `frontend/Dockerfile.dev`, `backend/Dockerfile`
- Docker Compose: `docker-compose.yml` for local development

**CI Pipeline:**
- Not detected in codebase (no GitHub Actions, CircleCI, etc. configs)
- Pre-commit: Husky 9.1.7 for local hooks

## Environment Configuration

**Required env vars:**
- Backend:
  - `DATABASE_URL` - PostgreSQL connection string
  - `JWT_SECRET_KEY` - JWT signing key (generate: `openssl rand -hex 32`)
  - `ENCRYPTION_KEY` - OAuth token encryption (generate: `openssl rand -base64 32`)
- Frontend:
  - None required for local development (all have sensible defaults)

**Secrets location:**
- Backend: `backend/.env` file (not committed, created from `.env.example`)
- Frontend: `frontend/.env.local` (not committed, created from `.env.example`)
- Production: Railway environment variables or managed secret store

**Optional integrations env vars (backend):**
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`
- `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_SIGNING_SECRET`
- `JIRA_CLIENT_ID`, `JIRA_CLIENT_SECRET`
- `LINEAR_CLIENT_ID`, `LINEAR_CLIENT_SECRET`
- `ROOTLY_API_KEY`
- `PAGERDUTY_API_KEY`
- `REDIS_URL` (or `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`)

## Webhooks & Callbacks

**Incoming:**
- Slack: `backend/app/api/endpoints/slack.py` accepts webhook events for interactive components
  - Signature verification using `SLACK_SIGNING_SECRET`
- No other incoming webhooks configured

**Outgoing:**
- Slack DM delivery: `backend/app/services/slack_dm_sender.py` sends survey notifications
- No outgoing webhooks to other services detected

---

*Integration audit: 2026-01-30*
