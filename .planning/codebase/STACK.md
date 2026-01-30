# Technology Stack

**Analysis Date:** 2026-01-30

## Languages

**Primary:**
- TypeScript 5+ - Frontend code in `frontend/src`
- Python 3.x - Backend API in `backend/app`

**Secondary:**
- JavaScript - Configuration files and build tooling
- SQL - PostgreSQL database queries via SQLAlchemy ORM

## Runtime

**Environment:**
- Node.js (latest LTS via Bun) - Frontend development and Next.js
- Python 3.x - Backend FastAPI server

**Package Managers:**
- npm - Frontend package management (`frontend/package.json`)
  - Lockfile: `package-lock.json` (standard npm lock)
- pip - Python backend (`backend/requirements.txt`)
  - Uses requirements.txt without pinned versions (flexible dependencies)

## Frameworks

**Core:**
- Next.js 16.1.5 - Frontend React framework with App Router
  - Configured with `frontend/next.config.js` for standalone output
- FastAPI (via `fastapi[all]`) - Python backend REST API
  - Server: Uvicorn with `uvicorn[standard]`
- SQLAlchemy + Alembic - Python ORM and database migrations
  - Migrations run at startup via `backend/migrations/migration_runner.py`

**UI Components:**
- Radix UI (multiple components: alert-dialog, avatar, checkbox, dialog, dropdown, popover, progress, radio-group, select, separator, slot, tabs, toast)
- Tailwind CSS 3.3.0 - Utility-first CSS
  - PostCSS for processing
  - Tailwind plugins: `@tailwindcss/typography`, `tailwindcss-animate`
  - Configured in `frontend/tailwind.config.js` and `frontend/postcss.config.js`
- Recharts 3.7.0 - React charting library
- Lucide React 0.562.0 - Icon library
- Sonner 2.0.7 - Toast notifications

**Forms & Validation:**
- React Hook Form 7.70.0 - Form state management
- Zod 4.3.5 - TypeScript-first schema validation
- `@hookform/resolvers` - Integration between Hook Form and Zod

**Testing:**
- Playwright 1.58.0 - E2E testing
  - Config: `frontend/playwright.config.ts`
  - Test directory: `frontend/e2e`
  - Supports multiple browsers (Chrome, Firefox)
  - Authenticated state: `frontend/e2e/.auth/user.json`
- pytest - Python backend testing (in `requirements.txt`)

**Build/Dev:**
- ESLint 9 - Code linting for Next.js
  - Config: `eslint-config-next`
- TypeScript - Type checking
  - Config: `frontend/tsconfig.json`
  - Path alias: `@/*` maps to `./src/*`
- Husky 9.1.7 - Git hooks for pre-commit checks
- dotenv 17.2.3 - Environment variable loading

**Date/Time:**
- date-fns 4.1.0 - Modern date utilities
- react-day-picker 9.13.0 - Calendar component
- pytz - Python timezone handling
- python-dateutil - Advanced Python date utilities

**Markdown Rendering:**
- react-markdown 10.1.0 - React markdown component

## Key Dependencies

**Critical:**
- httpx (Python) - Async HTTP client for API calls to external services
- aiohttp (Python) - Async HTTP library for concurrent requests
- requests (Python) - Synchronous HTTP client (legacy, being phased out)
- Authlib + python-jose - OAuth and JWT token handling
- passlib[bcrypt] - Password hashing and verification
- cryptography - Encryption for OAuth tokens stored in database

**Infrastructure:**
- Redis (Python client: `redis`) - Rate limiting and distributed locking
  - Configured via `REDIS_URL` (default: `redis://localhost:6379`)
  - Uses Docker image: `redis:7-alpine`
- PostgreSQL (psycopg2-binary) - Primary data store
  - Connection pooling configured in `backend/app/models/base.py` (pool_size=30)
  - Query timeout: 60 seconds, Lock timeout: 30 seconds
  - Uses Docker image: `postgres:15`

**AI & Analytics:**
- anthropic - Anthropic API client (imported conditionally in `backend/app/api/endpoints/llm.py`)
- openai - OpenAI API client (imported conditionally)
- smolagents - AI agent framework (not yet actively used)
- litellm - LLM provider abstraction layer
- vaderSentiment - Sentiment analysis for burnout detection

**Monitoring:**
- newrelic - Application performance monitoring
  - Backend: `newrelic` in requirements.txt
  - Frontend: `@newrelic/browser-agent` v1.307.0
  - Configured via env vars in frontend: `NEXT_PUBLIC_NEW_RELIC_*`

**Scheduling:**
- APScheduler - Background job scheduling for surveys
  - Service: `backend/app/services/survey_scheduler.py`

**Rate Limiting:**
- slowapi - Rate limiting middleware for FastAPI
  - Handler: `backend/app/core/rate_limiting.py`

**Security:**
- python-multipart - Form data parsing for OAuth flows

**Utilities:**
- class-variance-authority 0.7.0 - CSS-in-JS variant library
- clsx 2.0.0 - Conditional CSS class names
- tailwind-merge 3.4.0 - Tailwind CSS class merging
- simple-icons 16.6.0 - Brand icon SVGs
- pydantic + pydantic-settings - Python data validation and settings management

## Configuration

**Environment:**
- Frontend: `frontend/.env`, `frontend/.env.local`, `frontend/.env.test.example`
  - Required: None for local Docker hosting (all have sensible defaults)
  - Optional: New Relic credentials, OAuth client IDs, GA measurement ID
  - API URL defaults to `http://localhost:8000` for local development
- Backend: `backend/.env`, `backend/.env.example`
  - Required: `DATABASE_URL`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY`
  - Optional: OAuth credentials (Google, GitHub, Jira, Linear), Redis URL
  - API: `ROOTLY_API_BASE_URL` (defaults to `https://api.rootly.com`)
  - Hours: Configurable business hours and late-night thresholds

**Build:**
- Next.js: `frontend/next.config.js` (standalone output mode)
- TypeScript: `frontend/tsconfig.json`
  - Target: ES2017
  - Module: ESNext
  - Path alias: `@/*` → `./src/*`
- Tailwind: `frontend/tailwind.config.js`
- PostCSS: `frontend/postcss.config.js`

## Platform Requirements

**Development:**
- Node.js with npm (or Bun for faster local development)
- Python 3.x with pip
- Docker + Docker Compose (for local PostgreSQL and Redis)
- PostgreSQL 15 (via Docker)
- Redis 7 (via Docker)

**Production:**
- Deployment target: Railway (indicated by `VERCEL_URL` support and Railway-specific configurations)
- Supports both traditional container deployment and Vercel Next.js hosting
- Environment detection: `ENVIRONMENT` variable (development/staging/production)

---

*Stack analysis: 2026-01-30*
