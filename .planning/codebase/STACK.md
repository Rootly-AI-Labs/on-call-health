# Technology Stack

**Analysis Date:** 2026-01-30

## Languages

**Primary:**
- Python 3.11+ - Backend API and services (`/backend`)
- TypeScript/JavaScript - Frontend UI and client logic (`/frontend`)

**Secondary:**
- YAML - Configuration and CI/CD workflows
- SQL - PostgreSQL database schemas

## Runtime

**Environment:**
- Python runtime in Docker for backend
- Node.js (bun) for frontend development and build
- Docker Compose for local orchestration

**Package Manager:**
- Backend: `pip` with `requirements.txt`
- Frontend: `npm` with `package.json` and `package-lock.json`

## Frameworks

**Core Backend:**
- FastAPI 0.104+ - REST API framework
- Uvicorn - ASGI application server

**Core Frontend:**
- Next.js 16.1.6+ - React framework with server components
- React 19.2.4+ - UI component library

**UI Components & Styling:**
- Tailwind CSS 3.3.0 - Utility-first CSS framework
- Radix UI - Headless component library (15+ packages)
- shadcn/ui - Built on Radix UI, imported via `components.json`
- Lucide React - Icon library
- Recharts - Chart/visualization components

**Form & Validation:**
- React Hook Form 7.70.0 - Form state management
- @hookform/resolvers - Schema validation adapters
- Zod 4.3.6 - TypeScript-first schema validation

**Testing:**
- Playwright 1.58.0 - Browser automation and E2E testing
- pytest - Python unit testing framework
- Husky 9.1.7 - Git hooks manager (frontend)

**Build/Dev Tools:**
- TypeScript 5.x - Type checking
- ESLint 9.x - Code linting
- Autoprefixer - CSS vendor prefixing

## Key Dependencies

**Critical Backend:**
- SQLAlchemy - ORM for database operations
- Alembic - Database migration tool
- psycopg2-binary - PostgreSQL database adapter
- httpx - Async HTTP client for external API calls
- aiohttp - Alternative async HTTP client
- Authlib - OAuth 2.0 client library
- python-jose[cryptography] - JWT token handling
- passlib[bcrypt] - Password hashing

**Backend Infrastructure:**
- slowapi - Rate limiting for FastAPI
- redis - Redis client for distributed locking and caching
- APScheduler - Job scheduling for background tasks

**Backend AI/Analytics:**
- smolagents - Agentic framework for AI-powered analysis
- litellm - Language model abstraction layer (supports OpenAI, Anthropic, etc.)
- anthropic - Anthropic Claude API client
- openai - OpenAI API client
- vaderSentiment - Sentiment analysis library

**Backend Monitoring:**
- newrelic - Application Performance Monitoring (APM)

**Frontend Critical:**
- next-themes - Dark mode theming
- react-markdown - Markdown rendering
- sonner - Toast notification library
- simple-icons - Social/brand icons
- date-fns - Date manipulation utilities
- class-variance-authority - CSS class composition
- tailwind-merge - Tailwind CSS class merging
- clsx - Conditional className builder

**Frontend Monitoring:**
- @newrelic/browser-agent - New Relic browser RUM monitoring

## Configuration

**Environment:**
Backend configuration via:
- `.env` file (local development)
- Environment variables (Docker Compose, production)
- Required: `DATABASE_URL`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY`
- Optional: OAuth credentials (Google, GitHub, Jira, Linear), API keys (Rootly, PagerDuty)

Frontend configuration via:
- `.env` files (development/test)
- Environment variables at build/runtime
- Optional: New Relic browser monitoring, Google Analytics

**Build Configuration:**
- Backend: Dockerfile and Dockerfile.base in `/backend`
- Frontend: Dockerfile, Dockerfile.dev, Dockerfile.base in `/frontend`
- Compose: `docker-compose.yml` orchestrates backend, frontend, PostgreSQL, and Redis

## Platform Requirements

**Development:**
- Docker and Docker Compose (for containerized local development)
- Node.js/Bun (for frontend development)
- Python 3.11+ (for backend development)
- PostgreSQL 15 (containerized via Docker Compose)
- Redis 7 (containerized via Docker Compose)

**Production:**
- Deployment target: Railway (indicated by base image: `rootlyio/on-call-health:*-base`)
- PostgreSQL 15+ (managed database)
- Redis 7+ (managed cache/locking)
- Environment variables for secrets management

## Networking & Ports

**Local Development (Docker Compose):**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

**Inter-service Communication:**
- Frontend → Backend API: `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Backend → Database: `DATABASE_URL=postgresql://...@postgres:5432/burnout_detector`
- Backend → Redis: `REDIS_HOST=redis:6379` (Docker Compose internal networking)

---

*Stack analysis: 2026-01-30*
