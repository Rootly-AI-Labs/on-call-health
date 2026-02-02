# Codebase Structure

**Analysis Date:** 2026-01-30

## Directory Layout

```
project-root/
├── backend/                                    # FastAPI backend application
│   ├── app/
│   │   ├── main.py                            # FastAPI app initialization, middleware setup
│   │   ├── api/
│   │   │   └── endpoints/                     # REST API route handlers
│   │   │       ├── auth.py                    # Google/GitHub OAuth, login, logout
│   │   │       ├── analyses.py                # Burnout analysis CRUD
│   │   │       ├── integrations/              # Per-platform setup (GitHub, Slack, Jira, Linear)
│   │   │       ├── rootly.py                  # Rootly incident webhooks
│   │   │       ├── pagerduty.py               # PagerDuty incident webhooks
│   │   │       ├── surveys.py                 # Survey creation, responses
│   │   │       ├── notifications.py           # User notification status
│   │   │       ├── invitations.py             # Organization team invitations
│   │   │       ├── admin.py                   # Admin/debug endpoints
│   │   │       └── migrate.py                 # Data migration helpers
│   │   ├── auth/                              # Authentication & authorization
│   │   │   ├── oauth.py                       # User auth OAuth providers
│   │   │   ├── integration_oauth.py           # Integration-specific OAuth (Slack, Jira, Linear, GitHub)
│   │   │   ├── jwt.py                         # JWT token encode/decode
│   │   │   └── dependencies.py                # FastAPI dependency injection
│   │   ├── models/                            # SQLAlchemy ORM models
│   │   │   ├── user.py                        # User entity
│   │   │   ├── organization.py                # Organization (team) entity
│   │   │   ├── analysis.py                    # Burnout analysis result storage
│   │   │   ├── {platform}_integration.py      # Rootly, GitHub, Slack, Jira, Linear
│   │   │   ├── user_mapping.py                # Cross-platform user identity mapping
│   │   │   ├── integration_mapping.py         # Mapping configurations
│   │   │   ├── user_burnout_report.py         # Per-user burnout analysis results
│   │   │   ├── survey_*.py                    # Survey schedule, period, responses
│   │   │   └── base.py                        # Base model, session factory
│   │   ├── services/                          # Core business logic
│   │   │   ├── unified_burnout_analyzer.py    # Main burnout detection engine
│   │   │   ├── ai_burnout_analyzer.py         # AI-enhanced analysis (OpenAI/Anthropic)
│   │   │   ├── github_only_burnout_analyzer.py # GitHub-only fallback
│   │   │   ├── github_collector.py            # GitHub API data fetching
│   │   │   ├── slack_collector.py             # Slack API data fetching
│   │   │   ├── github_mapping_service.py      # GitHub user mapping logic
│   │   │   ├── {platform}_mapping_service.py  # Jira, Linear, Slack user mappers
│   │   │   ├── integration_validator.py       # Integration permission/access validation
│   │   │   ├── survey_scheduler.py            # Periodic survey triggering
│   │   │   ├── notification_service.py        # Email/Slack notification sender
│   │   │   ├── user_sync_service.py           # Sync users from integrations
│   │   │   ├── token_refresh_coordinator.py   # OAuth token refresh manager
│   │   │   └── account_linking.py             # Multi-account linking logic
│   │   ├── core/                              # Shared utilities & config
│   │   │   ├── config.py                      # Settings (DATABASE_URL, JWT_SECRET_KEY, etc.)
│   │   │   ├── pagerduty_client.py            # PagerDuty API wrapper
│   │   │   ├── rootly_client.py               # Rootly API wrapper
│   │   │   ├── api_cache.py                   # Redis-based response caching
│   │   │   ├── distributed_lock.py            # Redis-based distributed locking
│   │   │   ├── rate_limiting.py               # Rate limit definitions & handlers
│   │   │   ├── input_validation.py            # Pydantic validation models
│   │   │   ├── burnout_config.py              # Burnout scoring thresholds
│   │   │   ├── och_config.py                  # Organization config
│   │   │   └── error_handler.py               # Custom error response formatting
│   │   ├── middleware/                        # Request/response processing
│   │   │   ├── security.py                    # CORS, CSRF, security headers
│   │   │   ├── user_logging.py                # Adds user_id to request context
│   │   │   └── logging_context.py             # Custom logging filter
│   │   ├── agents/                            # AI agent framework (experimental)
│   │   │   ├── burnout_agent.py               # Main agent orchestrator
│   │   │   ├── tools/                         # Agent analysis tools
│   │   │   │   ├── sentiment_analyzer.py
│   │   │   │   ├── workload_analyzer.py
│   │   │   │   ├── pattern_analyzer.py
│   │   │   │   └── ...more tools
│   │   │   └── workflows/                     # Multi-step analysis workflows
│   │   ├── mcp/                               # Model Context Protocol server
│   │   │   ├── server.py                      # MCP server definition
│   │   │   ├── auth.py                        # MCP authentication
│   │   │   └── serializers.py                 # Data serializers for MCP
│   │   ├── utils/                             # Helper utilities
│   │   │   ├── visual_logger.py               # Logging helper for task progress
│   │   │   └── ...other utilities
│   │   └── static/                            # Static assets (favicon)
│   ├── migrations/                            # Database migrations
│   │   ├── migration_runner.py                # Migration execution logic
│   │   └── *.sql                              # Individual migration files
│   ├── tests/                                 # Backend tests
│   │   ├── mock_data/                         # Test fixtures & scenarios
│   │   └── ...test files
│   ├── scripts/                               # Utility scripts
│   └── requirements.txt                       # Python dependencies
├── frontend/                                  # Next.js frontend application
│   ├── src/
│   │   ├── app/                              # Next.js App Router pages
│   │   │   ├── layout.tsx                    # Root layout with providers
│   │   │   ├── page.tsx                      # Landing page
│   │   │   ├── dashboard/                    # Main dashboard page
│   │   │   ├── auth/                         # Auth pages (login, oauth callbacks)
│   │   │   ├── integrations/                 # Integration setup pages
│   │   │   ├── setup/                        # Onboarding pages
│   │   │   ├── invitations/                  # Team invitation pages
│   │   │   ├── methodology/                  # Methodology documentation page
│   │   │   ├── disclaimer/                   # Legal disclaimer page
│   │   │   └── globals.css                   # Global styling
│   │   ├── components/                       # Reusable React components
│   │   │   ├── dashboard/                    # Dashboard-specific components
│   │   │   │   ├── charts/                   # Chart components (Recharts)
│   │   │   │   ├── dialogs/                  # Modal dialogs (delete, settings)
│   │   │   │   └── insights/                 # Analysis insight displays
│   │   │   ├── integrations/                 # Integration UI components
│   │   │   ├── ui/                           # Radix UI + shadcn components
│   │   │   ├── notifications/                # Toast notifications
│   │   │   ├── TopPanel.tsx                  # Header with user menu
│   │   │   ├── mapping-drawer.tsx            # User mapping UI
│   │   │   ├── SlackSurveyTabs.tsx           # Survey delivery UI
│   │   │   └── ...more components
│   │   ├── contexts/                         # React Context providers
│   │   │   ├── ChartModeContext.tsx          # Chart view mode (radar/bar)
│   │   │   └── GettingStartedContext.tsx     # Onboarding state
│   │   ├── hooks/                            # Custom React hooks
│   │   │   ├── useDashboard.ts               # Main dashboard logic (data fetching, state)
│   │   │   ├── useNotifications.ts           # Notification management
│   │   │   ├── use-integrations-state.ts     # Integration setup state
│   │   │   └── ...more hooks
│   │   ├── lib/                              # Utilities & helper functions
│   │   │   ├── types.ts                      # TypeScript interfaces for API responses
│   │   │   ├── githubMetricUtils.ts          # GitHub metric calculations
│   │   │   ├── riskFactorUtils.ts            # Burnout risk factor helpers
│   │   │   ├── health-check.ts               # Backend connectivity check
│   │   │   └── metadata.ts                   # Page metadata
│   │   └── types/                            # Type definitions
│   ├── public/                               # Static assets
│   │   ├── images/                           # Brand/product images
│   │   └── fonts/                            # Web fonts
│   ├── e2e/                                  # Playwright E2E tests
│   ├── package.json                          # Node dependencies
│   ├── tsconfig.json                         # TypeScript config
│   └── next.config.js                        # Next.js config
├── .github/                                   # GitHub Actions CI/CD
│   └── workflows/                             # Pipeline definitions
├── migrations/                                # (Root-level) Migration scripts
├── docker-compose.yml                         # Docker Compose configuration
└── README.md                                  # Project documentation
```

## Directory Purposes

**Backend Core (`backend/app/`):**
- Main application code organized by layer (API, Services, Models, Core utilities)
- Python FastAPI application with SQLAlchemy ORM
- Entry point: `app/main.py`

**API Endpoints (`backend/app/api/endpoints/`):**
- REST route handlers for all operations
- Each file focuses on a domain (auth, analyses, integrations, etc.)
- Pattern: One router per file, registered in main.py

**Models (`backend/app/models/`):**
- SQLAlchemy declarative models
- Database schema definition
- Relationships: User→Organization→Integrations, User→Analysis
- Key file: `base.py` (SessionLocal, Base, create_tables)

**Services (`backend/app/services/`):**
- Business logic layer with complex operations
- Examples: UnifiedBurnoutAnalyzer orchestrates analysis workflow
- Collectors (GitHub, Slack) encapsulate platform-specific API interactions
- Mappers resolve user identities across platforms

**Auth (`backend/app/auth/`):**
- OAuth provider configuration (Google, GitHub for login)
- Integration OAuth managers (Slack, Jira, Linear, GitHub for data sources)
- JWT token creation/validation
- Dependency injection for route protection

**Core (`backend/app/core/`):**
- Shared configuration and clients
- API clients for external services (PagerDuty, Rootly, GitHub, Slack, etc.)
- Caching, locking, rate limiting, validation

**Middleware (`backend/app/middleware/`):**
- Request/response interceptors
- Security headers, CORS, user logging context
- Runs before all endpoints

**Frontend App Router (`frontend/src/app/`):**
- Next.js App Router directory structure
- Each subdirectory is a route (dashboard/, auth/, integrations/)
- `page.tsx` files are entry points for routes
- `layout.tsx` is the root layout wrapper

**Components (`frontend/src/components/`):**
- Reusable React components
- Dashboard components for charts, dialogs, insights
- Integration UI components
- Radix UI + shadcn components in `ui/` subdirectory

**Hooks (`frontend/src/hooks/`):**
- Custom React hooks for data fetching and state management
- `useDashboard.ts` is the main hook (1600+ lines) managing all dashboard logic
- Hooks handle API communication, local state, caching

**Lib (`frontend/src/lib/`):**
- Utility functions and type definitions
- `types.ts`: TypeScript interfaces matching backend API responses
- Helper utilities for metrics, UI state, health checks

**Contexts (`frontend/src/contexts/`):**
- React Context providers for global state
- ChartModeContext: Chart view preference
- GettingStartedContext: Onboarding UI state

## Key File Locations

**Entry Points:**
- Backend: `backend/app/main.py` (FastAPI app creation, middleware, router registration)
- Frontend: `frontend/src/app/layout.tsx` (Root layout with providers)
- Database: `backend/app/models/base.py` (SessionLocal, create_tables)

**Configuration:**
- Backend env: `backend/.env` (DATABASE_URL, JWT_SECRET_KEY, OAuth credentials)
- Backend code: `backend/app/core/config.py` (Settings class)
- Frontend env: `frontend/.env.local` (NEXT_PUBLIC_API_URL, GA_MEASUREMENT_ID)

**Core Business Logic:**
- Burnout analysis: `backend/app/services/unified_burnout_analyzer.py`
- Dashboard state: `frontend/src/hooks/useDashboard.ts`
- Authentication: `backend/app/auth/` (oauth.py, dependencies.py)

**Testing:**
- Backend tests: `backend/tests/`
- Frontend E2E: `frontend/e2e/` (Playwright tests)
- Mock data: `backend/tests/mock_data/scenarios/`

## Naming Conventions

**Files:**
- Python: `snake_case.py` (e.g., `unified_burnout_analyzer.py`)
- TypeScript: `kebab-case.ts` (hooks, utils) or `PascalCase.tsx` (components, pages)
- API files: `{platform}_name.py` (e.g., `github_collector.py`, `slack_integration.py`)
- Test files: `test_{module}.py` or `{module}.test.ts`

**Directories:**
- Python packages: `snake_case` (e.g., `app/api/endpoints/`)
- React: `components/`, `hooks/`, `lib/`, `app/`, `contexts/`
- Feature domains: Feature name in plural or singular depending on scope (e.g., `integrations/`, `surveys/`)

**Classes/Functions:**
- Python classes: `PascalCase` (e.g., `UnifiedBurnoutAnalyzer`, `GitHubCollector`)
- Python functions: `snake_case` (e.g., `extract_analysis_summary`, `get_current_user`)
- React components: `PascalCase` (e.g., `TopPanel`, `MappingDrawer`)
- React hooks: `useXxx` (e.g., `useDashboard`, `useNotifications`)

**Variables/State:**
- Python: `snake_case`
- TypeScript: `camelCase` (local), `PascalCase` (interfaces/types)
- React state: `camelCase` (e.g., `selectedIntegration`, `analysisRunning`)

## Where to Add New Code

**New Feature (e.g., new analysis type):**
- Primary code: `backend/app/services/{feature_name}.py`
- API endpoint: `backend/app/api/endpoints/{feature_name}.py`
- Models: `backend/app/models/{feature_name}.py` (if new entities)
- Frontend page: `frontend/src/app/{feature_name}/page.tsx`
- Frontend components: `frontend/src/components/{feature_name}/`
- Tests: `backend/tests/test_{feature_name}.py`, `frontend/e2e/{feature_name}.spec.ts`

**New Component/Module (reusable):**
- React component: `frontend/src/components/{ComponentName}.tsx`
- Hook: `frontend/src/hooks/use{FeatureName}.ts`
- Service: `backend/app/services/{module_name}.py`
- Middleware: `backend/app/middleware/{concern_name}.py` (if cross-cutting)

**Utilities:**
- Shared helpers: `frontend/src/lib/{utility_name}.ts` or `backend/app/utils/{utility_name}.py`
- Type definitions: `frontend/src/lib/types.ts` (append to interfaces) or `frontend/src/types/` (new file)
- Constants: Collocated with usage (module-level) or in `backend/app/core/config.py` for config

**Integration with External Service:**
- Client/API wrapper: `backend/app/core/{platform}_client.py`
- Collector: `backend/app/services/{platform}_collector.py`
- OAuth handler: `backend/app/auth/integration_oauth.py` (extend handlers)
- Model: `backend/app/models/{platform}_integration.py`
- Endpoint: `backend/app/api/endpoints/{platform}.py`

## Special Directories

**Migrations (`backend/migrations/`):**
- Purpose: Track database schema changes
- Generated: Yes (via migration runner)
- Committed: Yes
- Pattern: Each migration is a `.sql` or `.py` file applied sequentially
- Runner: `backend/migrations/migration_runner.py` (called on app startup)

**Tests (`backend/tests/`, `frontend/e2e/`):**
- Purpose: Unit tests, integration tests, E2E tests
- Generated: No (manually written)
- Committed: Yes
- Backend: Use pytest framework
- Frontend: Use Playwright for E2E

**Mock Data (`backend/tests/mock_data/`):**
- Purpose: Test fixtures and scenario data
- Generated: May be auto-generated from templates
- Committed: Yes (small datasets)
- Structure: `scenarios/` for predefined test scenarios

**Static Assets (`frontend/public/`, `backend/app/static/`):**
- Purpose: Favicon, images, fonts
- Generated: No
- Committed: Yes
- Frontend public assets loaded by Next.js at build time

**Node Modules (`frontend/node_modules/`):**
- Purpose: npm dependencies
- Generated: Yes (via npm install)
- Committed: No (in .gitignore)

**Python Environment (`backend/venv/` or `.venv/`):**
- Purpose: Isolated Python dependencies
- Generated: Yes (via python -m venv)
- Committed: No (in .gitignore)

**Build Output (`frontend/.next/`, `frontend/dist/`):**
- Purpose: Compiled Next.js output
- Generated: Yes (via npm run build)
- Committed: No (in .gitignore)

---

*Structure analysis: 2026-01-30*
