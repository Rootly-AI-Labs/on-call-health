# Codebase Structure

**Analysis Date:** 2026-01-30

## Directory Layout

```
on-call-health/
├── backend/                       # FastAPI backend application
│   ├── app/                       # Main application code
│   │   ├── main.py               # FastAPI app initialization and router registration
│   │   ├── api/                  # API route definitions
│   │   │   └── endpoints/        # All API endpoints (analyses, auth, integrations)
│   │   ├── services/             # Business logic services (analyzers, collectors, mappers)
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── core/                 # Core infrastructure (config, clients, validation)
│   │   ├── auth/                 # OAuth and JWT authentication
│   │   ├── middleware/           # HTTP middleware (logging, security)
│   │   ├── agents/               # AI agent definitions
│   │   ├── mcp/                  # Model Context Protocol server implementation
│   │   ├── workers/              # Background worker tasks
│   │   ├── utils/                # Utility functions
│   │   └── static/               # Static assets (favicon)
│   ├── tests/                    # Pytest tests and mock data
│   ├── migrations/               # Alembic database migrations
│   ├── mock_data_helpers/        # Mock data generation for development
│   ├── scripts/                  # Utility scripts
│   ├── requirements.txt          # Python dependencies
│   └── .env.example              # Environment variables template
├── frontend/                      # Next.js React frontend
│   ├── src/
│   │   ├── app/                  # Next.js app router pages
│   │   │   ├── dashboard/        # Main dashboard page
│   │   │   ├── auth/             # Authentication pages (login, callback)
│   │   │   ├── integrations/     # Integration setup pages
│   │   │   ├── setup/            # Initial setup wizard
│   │   │   ├── layout.tsx        # Root layout with providers
│   │   │   └── globals.css       # Global styles
│   │   ├── components/           # React components
│   │   │   ├── dashboard/        # Dashboard-specific components
│   │   │   ├── integrations/     # Integration UI components
│   │   │   ├── ui/               # Shadcn UI components
│   │   │   ├── notifications/    # Notification components
│   │   │   └── [misc].tsx        # Standalone components
│   │   ├── contexts/             # React Context providers
│   │   ├── hooks/                # Custom React hooks
│   │   ├── lib/                  # Utility functions and types
│   │   └── types/                # TypeScript type definitions
│   ├── public/                   # Static assets (images, fonts, videos)
│   ├── e2e/                      # Playwright end-to-end tests
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   └── playwright.config.ts
├── .github/                       # GitHub configuration
├── docker-compose.yml            # Docker Compose configuration
├── .env.example                  # Example environment variables
└── README.md

```

## Directory Purposes

**`backend/app/`:**
- Purpose: Main application package containing all backend business logic
- Contains: API routes, services, models, authentication, middleware
- Key files: `main.py` (FastAPI app initialization)

**`backend/app/api/endpoints/`:**
- Purpose: All REST API endpoint definitions
- Contains: Router objects with endpoint handlers, request/response models
- Key files: `analyses.py`, `auth.py`, `rootly.py`, `pagerduty.py`, `github.py`, `slack.py`, `jira.py`, `linear.py`
- Naming: One file per major feature/integration

**`backend/app/services/`:**
- Purpose: Business logic services for data collection, analysis, and processing
- Contains: Collector classes, analyzer classes, mapping services
- Typical organization:
  - Collector pattern: `*_collector.py` (e.g., `github_collector.py`, `slack_collector.py`)
  - Analyzer pattern: `*_analyzer.py` (e.g., `unified_burnout_analyzer.py`, `ai_burnout_analyzer.py`)
  - Mapper pattern: `*_mapping_service.py` (e.g., `github_mapping_service.py`)
- Key files: `unified_burnout_analyzer.py` (orchestrates analysis), `ai_burnout_analyzer.py` (LLM-based analysis)

**`backend/app/models/`:**
- Purpose: SQLAlchemy ORM model definitions
- Contains: Declarative models with relationships
- Naming: Snake_case file names matching model names (e.g., `user.py` for `User` model)
- Special: `__init__.py` exports all models and database utilities (`get_db`, `create_tables`, `SessionLocal`)
- Key files: `base.py` (Base model and database setup), `user.py`, `organization.py`, `analysis.py`

**`backend/app/core/`:**
- Purpose: Core infrastructure and configuration
- Contains: Settings, API clients, configuration, caching, validation, rate limiting
- Key files:
  - `config.py`: Environment-based settings from .env
  - `och_config.py`: Burnout scoring logic and configuration
  - `rootly_client.py`: Rootly API client
  - `pagerduty_client.py`: PagerDuty API client
  - `input_validation.py`: Pydantic request validation schemas

**`backend/app/auth/`:**
- Purpose: Authentication and authorization logic
- Contains: OAuth providers, JWT handling, authentication dependencies
- Key files:
  - `oauth.py`: Primary OAuth handler
  - `integration_oauth.py`: OAuth for integrations (GitHub, Slack, Jira, Linear)
  - `jwt.py`: JWT token encoding/decoding
  - `dependencies.py`: FastAPI authentication dependencies

**`backend/app/middleware/`:**
- Purpose: HTTP middleware for cross-cutting concerns
- Contains: Security headers, logging, error handling
- Key files:
  - `security.py`: Security headers middleware
  - `user_logging.py`: User context logging middleware
  - `logging_context.py`: Context filter for structured logging

**`backend/tests/`:**
- Purpose: Pytest unit and integration tests
- Contains: Test files and mock data
- Naming: `test_*.py` files matching module names
- Key files:
  - `conftest.py`: Pytest fixtures and configuration
  - `mock_data/`: Mock data generators for testing

**`frontend/src/app/`:**
- Purpose: Next.js app router pages and layout
- Contains: Page components, layout definitions, global styles
- Structure: Next.js file-based routing (e.g., `dashboard/page.tsx` → `/dashboard` route)
- Key files:
  - `layout.tsx`: Root layout with all providers
  - `page.tsx`: Home page
  - `dashboard/page.tsx`: Main dashboard page

**`frontend/src/components/`:**
- Purpose: Reusable React components
- Contains: UI components, dashboard components, integration components
- Subdirectories:
  - `ui/`: Shadcn UI primitive components (Button, Dialog, etc.)
  - `dashboard/`: Dashboard-specific components (cards, charts, modals)
  - `integrations/`: Integration setup and configuration UI
- Naming: PascalCase `.tsx` files (e.g., `TeamHealthOverview.tsx`)

**`frontend/src/contexts/`:**
- Purpose: React Context API providers for global state
- Contains: Context definitions and provider components
- Naming: `*Context.ts` for context definition, wrapped in provider
- Key contexts: `GettingStartedContext`, `ChartModeContext`

**`frontend/src/hooks/`:**
- Purpose: Custom React hooks for reusable logic
- Contains: API calls, state management, side effects
- Naming: `use*.ts` (e.g., `useDashboard.ts`, `useNotifications.ts`)
- Key hooks: `useDashboard` (loads analysis data), `useIntegrations` (integration state)

**`frontend/src/lib/`:**
- Purpose: Utility functions, type definitions, helper functions
- Contains: Non-component code (types, utils, API helpers)
- Key files:
  - `types.ts`: TypeScript interfaces (Integration, GitHubActivity, etc.)
  - `githubMetricUtils.ts`: GitHub metric calculations
  - `riskFactorUtils.ts`: Risk factor calculations
  - `health-check.ts`: API health checks

**`frontend/e2e/`:**
- Purpose: End-to-end tests using Playwright
- Contains: E2E test files
- Naming: `*.spec.ts` files
- Key tests: `smoke.spec.ts`, `auth.spec.ts`, `integrations.spec.ts`

**`backend/migrations/`:**
- Purpose: Alembic database migration scripts
- Contains: Migration files for schema changes
- Naming: Alembic-generated files with migration descriptions
- Pattern: One migration per significant schema change

**`backend/mock_data_helpers/`:**
- Purpose: Generate mock data for development and testing
- Contains: Mock data generators matching real API formats

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: FastAPI app initialization
- `frontend/src/app/layout.tsx`: Next.js root layout
- `frontend/src/app/dashboard/page.tsx`: Main dashboard page

**Configuration:**
- `backend/app/core/config.py`: Environment settings
- `frontend/next.config.js`: Next.js configuration
- `frontend/tsconfig.json`: TypeScript configuration
- `backend/requirements.txt`: Python dependencies

**Core Logic:**
- `backend/app/services/unified_burnout_analyzer.py`: Main analysis orchestrator
- `backend/app/services/ai_burnout_analyzer.py`: AI-powered analysis
- `backend/app/core/och_config.py`: Burnout scoring configuration
- `frontend/src/hooks/useDashboard.ts`: Dashboard data fetching

**Authentication:**
- `backend/app/api/endpoints/auth.py`: OAuth endpoints
- `backend/app/auth/dependencies.py`: FastAPI auth dependencies
- `frontend/src/components/AuthInterceptor.tsx`: Auth interceptor

**Integrations:**
- `backend/app/api/endpoints/github.py`: GitHub integration endpoints
- `backend/app/api/endpoints/slack.py`: Slack integration endpoints
- `backend/app/services/github_collector.py`: GitHub data collection
- `backend/app/services/slack_collector.py`: Slack data collection

**Testing:**
- `backend/tests/conftest.py`: Pytest configuration and fixtures
- `frontend/e2e/smoke.spec.ts`: Basic smoke tests
- `frontend/e2e/integrations.spec.ts`: Integration flow tests

## Naming Conventions

**Files:**

- **Python**: `snake_case.py`
  - Models: `model_name.py` (e.g., `user.py`, `rootly_integration.py`)
  - Services: `service_name.py` or `service_name_service.py` (e.g., `unified_burnout_analyzer.py`, `github_collector.py`)
  - Tests: `test_feature.py` (e.g., `test_github_slack_metrics.py`)
  - Utilities: `function_name.py` or `*_utils.py` (e.g., `incident_utils.py`)

- **TypeScript/React**: `PascalCase.tsx` or `camelCase.ts`
  - Components: `ComponentName.tsx` (e.g., `DashboardView.tsx`, `TeamHealthOverview.tsx`)
  - Hooks: `useName.ts` (e.g., `useDashboard.ts`, `useNotifications.ts`)
  - Utilities: `camelCase.ts` or `name-utils.ts` (e.g., `githubMetricUtils.ts`)
  - Types: `types.ts` or `*-types.ts`

**Directories:**

- **Backend**:
  - Feature packages: `lowercase` (e.g., `services/`, `models/`, `auth/`)
  - Grouping: By domain (e.g., all auth files in `auth/`)

- **Frontend**:
  - Page routes: `lowercase` matching route path (e.g., `dashboard/`, `auth/`)
  - Feature groups: `lowercase` (e.g., `components/dashboard/`, `components/integrations/`)

**Classes and Functions:**

- **Python**: `PascalCase` for classes, `snake_case` for functions
  - Classes: `UnifiedBurnoutAnalyzer`, `GitHubCollector`, `RootlyAPIClient`
  - Functions: `analyze_incidents()`, `get_user_by_id()`, `extract_analysis_summary()`

- **TypeScript**: `PascalCase` for types and components, `camelCase` for functions
  - Types: `interface Integration`, `type GitHubActivity`
  - Components: `export function DashboardView() {}`
  - Functions: `const fetchAnalysis = async () => {}`

## Where to Add New Code

**New Feature - Backend:**
- Primary code: `backend/app/services/feature_name.py` (if business logic) or `backend/app/api/endpoints/feature_name.py` (if new endpoints)
- Database model: `backend/app/models/feature_name.py`
- Tests: `backend/tests/test_feature_name.py`
- Integration: Import and register router in `backend/app/main.py` if new endpoint

**New Feature - Frontend:**
- Page: `frontend/src/app/feature-name/page.tsx` (if new route)
- Components: `frontend/src/components/feature-name/FeatureName.tsx`
- Hook: `frontend/src/hooks/useFeature.ts` (if state management needed)
- Types: Add to `frontend/src/lib/types.ts`
- Tests: `frontend/e2e/feature-name.spec.ts`

**New External Integration (e.g., new platform):**
- Model: `backend/app/models/platform_integration.py`
- Collector: `backend/app/services/platform_collector.py`
- Mapper: `backend/app/services/platform_mapping_service.py`
- Endpoints: `backend/app/api/endpoints/platform.py`
- OAuth handler: Add to `backend/app/auth/integration_oauth.py` or create `backend/app/auth/platform_oauth.py`
- Frontend UI: `frontend/src/components/integrations/PlatformSetup.tsx`

**New Utility Function:**
- Shared helpers: `backend/app/utils/feature_utils.py` or `frontend/src/lib/feature-utils.ts`
- Math/calculations: `backend/app/core/feature_config.py` (if configuration-heavy)

## Special Directories

**`backend/migrations/`:**
- Purpose: Database schema version control
- Generated: Yes (by Alembic)
- Committed: Yes (track all migrations in git)
- When to create: After modifying any model with `alembic revision --autogenerate`

**`frontend/public/`:**
- Purpose: Static assets served directly by Next.js
- Subdirectories: `images/`, `fonts/`, `videos/`
- Generated: No (manually managed)
- Committed: Yes (except node_modules)

**`backend/tests/mock_data/`:**
- Purpose: Mock data for development and testing
- Generated: Dynamically at test runtime
- Committed: Yes (generators and fixtures, not data instances)
- Use: Import `MockDataLoader` in tests to generate realistic test data

**`backend/app/static/`:**
- Purpose: Static files served by FastAPI (favicon)
- Generated: No
- Committed: Yes

**`backend/app/mcp/`:**
- Purpose: Model Context Protocol server for AI integration
- Generated: No
- Committed: Yes
- Special: Provides tools/capabilities to Claude/AI models

**`backend/app/agents/`:**
- Purpose: AI agent definitions using smolagents framework
- Generated: No
- Committed: Yes
- Usage: Called by burnout analyzer for AI-enhanced analysis

---

*Structure analysis: 2026-01-30*
