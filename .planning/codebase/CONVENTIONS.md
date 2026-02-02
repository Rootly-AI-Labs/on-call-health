# Coding Conventions

**Analysis Date:** 2026-01-30

## Naming Patterns

**Files:**
- TypeScript/TSX files: kebab-case for components and utilities (e.g., `use-toast.ts`, `error-boundary.tsx`, `github-integration-card.tsx`)
- Python files: snake_case (e.g., `slack_collector.py`, `rootly_client.py`, `integration_validator.py`)
- UI components: PascalCase (e.g., `SlackIntegrationCard.tsx`, `AIInsightsCard.tsx`)

**Functions:**
- Frontend: camelCase (e.g., `testConnection()`, `loadRootlyIntegrations()`, `deleteIntegration()`)
- Backend: snake_case (e.g., `test_connection()`, `validate_github()`, `get_cached_validation()`)
- React hooks: camelCase with `use` prefix (e.g., `useToast()`, `useDashboard()`, `useInfiniteScroll()`)

**Variables:**
- Frontend: camelCase (e.g., `setConnectionStatus`, `previewData`, `integrationId`)
- Backend: snake_case (e.g., `auth_token`, `user_id`, `error_details`)

**Types:**
- TypeScript interfaces: PascalCase (e.g., `State`, `ToasterToast`, `Integration`)
- Python models: PascalCase class names (e.g., `User`, `SlackIntegration`, `UserCorrelation`)
- Enums/constants: UPPER_SNAKE_CASE (e.g., `TOAST_LIMIT`, `TOAST_REMOVE_DELAY`)

## Code Style

**Formatting:**
- Frontend: Uses ESLint with Next.js core-web-vitals config, maintained at `frontend/.eslintrc.json`
- Backend: Python follows PEP 8 conventions (implicit, no explicit formatter detected)
- Indentation: 2 spaces in TypeScript/JavaScript, 4 spaces in Python (standard)

**Linting:**
- Frontend: ESLint configured via `frontend/.eslintrc.json` with one custom rule: `"react/no-unescaped-entities": "off"`
- Backend: No explicit linter detected; follows standard Python conventions
- Type checking: Frontend runs TypeScript strict type checking (note: `tsconfig.json` has `"strict": false`)

**Line Length:**
- No explicit limit detected; follows common patterns of ~80-100 characters

## Import Organization

**Frontend (TypeScript/React):**
1. React/Next.js imports
2. Third-party libraries
3. Type imports (using `import type`)
4. Internal aliases (using `@/` path alias)
5. Relative imports

Example from `use-toast.ts`:
```typescript
import * as React from "react"
import type { ToastActionElement, ToastProps } from "@/components/ui/toast"
```

**Backend (Python):**
1. Standard library imports
2. Third-party imports (fastapi, sqlalchemy, etc.)
3. Relative imports from app modules

Example from `rootly.py`:
```python
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging
import os
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ...models import get_db, User, RootlyIntegration
from ...auth.dependencies import get_current_active_user
from ...core.rootly_client import RootlyAPIClient
```

**Path Aliases:**
- Frontend: `@/*` maps to `./src/*` (configured in `frontend/tsconfig.json`)

## Error Handling

**Frontend Patterns:**
- Try-catch blocks with finally clauses for cleanup
- User-facing error messages via toast notifications (using `sonner` library)
- Error state management through React state (e.g., `setConnectionStatus('error')`)
- Console logging for debugging: `console.error('Error message:', error)`
- Error details captured and passed to user: `user_message`, `user_guidance`, `error_code`

Example from `integration-handlers.ts`:
```typescript
try {
  // operation
  toast.success("Success message")
} catch (error) {
  console.error('Error context:', error)
  toast.error(error instanceof Error ? error.message : "An unexpected error occurred.")
} finally {
  setIsLoading(false)
}
```

**Backend Patterns:**
- Custom exception classes: `RetryableError`, `NonRetryableError` in `core/error_handler.py`
- HTTPException for API responses with detailed error context
- Structured error responses with `user_message`, `user_guidance`, `error_code` fields
- Logger-based error tracking: `logger.error()`, `logger.warning()`
- Retry mechanism with exponential backoff for transient errors

Example from `rootly.py`:
```python
try:
  # operation
except SomeError:
  error_details = {
    "error_code": code,
    "user_message": "User-friendly text",
    "user_guidance": "Actionable steps"
  }
  raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_details)
```

## Logging

**Frontend:**
- Framework: `console` object
- Pattern: `console.error()`, `console.log()` for debugging
- Usage: Primarily for error tracking and debugging; used in catch blocks

Example: `console.error('Connection test error:', error)`

**Backend:**
- Framework: Python `logging` module
- Pattern: `logger = logging.getLogger(__name__)` at module level
- Levels: `logger.info()`, `logger.warning()`, `logger.error()`
- Context: Error context strings in retry logs and operation failures

Example from `error_handler.py`:
```python
logger.info(f"Operation attempt {attempt + 1}/{max}, retrying in {delay}s")
logger.warning(f"Operation failed after {max_retries} retries: {error}")
```

## Comments

**When to Comment:**
- Docstrings for all functions and classes (especially in Python models and services)
- Inline comments for complex logic or non-obvious implementations
- Comments explaining regex patterns (seen in `slack_collector.py`)
- Comments marking removed/deprecated code with context

**JSDoc/TSDoc:**
- Backend: Docstrings using Python conventions (`"""..."""`)
- Frontend: Minimal JSDoc; relies on TypeScript types for documentation

Example from `user.py`:
```python
def has_github_integration(self) -> bool:
    """Check if user has GitHub integration set up."""
    return len(self.github_integrations) > 0
```

## Function Design

**Size:** Functions typically 20-80 lines; longer functions exist for complex operations like data collection

**Parameters:**
- Frontend: Functions accept React state setters and simple data types; avoid over-parameterization
  - Example: `testConnection(platform, token, setIsTestingConnection, setConnectionStatus, ...)`
- Backend: Use dependency injection for database sessions and authentication
  - Example: `async def test_rootly_token_preview(request: Request, token_request: RootlyTokenRequest, current_user: User = Depends(...), db: Session = Depends(...))`

**Return Values:**
- Frontend: Often return Promise<void> with side effects through state setters
- Backend: Return structured Pydantic models or HTTPException for errors

Example from `integration_validator.py`:
```python
async def _validate_github(self, user_id: int) -> Dict[str, Any]:
    """Return {"valid": bool, "error": str|None, ...}"""
```

## Module Design

**Exports:**
- Frontend: Re-export components and utilities via barrel files (e.g., `components/notifications/index.ts`)
- Backend: Use `__init__.py` for module organization but import directly from specific files

Example barrel file at `frontend/src/components/notifications/index.ts`:
```typescript
// Re-exports from this module
```

**Barrel Files:**
- Frontend: Used in `components/ui/`, `components/notifications/` for organizing UI components
- Backend: Minimal use; typically import from specific modules

## Architecture Patterns

**Frontend:**
- Custom hooks pattern for state and side effects
- Handler pattern for async operations (e.g., `integration-handlers.ts` contains functions like `testConnection()`, `addIntegration()`)
- API service layer (e.g., `components/integrations/api-service.ts`)
- Separation of UI components from business logic

**Backend:**
- Service layer pattern (e.g., `services/slack_collector.py`, `services/github_collector.py`)
- Model-driven architecture using SQLAlchemy ORM
- Dependency injection via FastAPI
- Endpoint-per-feature organization (e.g., `api/endpoints/rootly.py`, `api/endpoints/slack.py`)
- Custom middleware for security, logging, and rate limiting

## Async Patterns

**Frontend:**
- Async functions for API calls and external operations
- Return void with state updates via setters
- Use `Promise<void>` return type for async handlers

**Backend:**
- Async/await throughout for I/O operations
- asyncio.gather() for parallel operations
- return_exceptions=True when collecting results from parallel tasks
- Retry logic with exponential backoff

Example from `rootly_client.py`:
```python
results = await asyncio.gather(
  *[fetch_task(item) for item in items],
  return_exceptions=True
)
```

## Type Safety

**Frontend:**
- TypeScript with `strict: false` in tsconfig (permissive mode)
- `type` keyword for type-only imports
- Partial<T> for optional updates
- type guards using `instanceof`

**Backend:**
- Python type hints on function signatures
- Pydantic models for validation and serialization
- Dict[str, Any] for flexible data structures
- Optional[T] for nullable values

---

*Convention analysis: 2026-01-30*
