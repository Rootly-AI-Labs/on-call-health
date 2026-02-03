# Coding Conventions

**Analysis Date:** 2026-01-30

## Naming Patterns

**Files:**
- TypeScript/React: camelCase for files (e.g., `ChartModeContext.tsx`, `integration_validator.py`)
- Python: snake_case for files (e.g., `api_cache.py`, `input_validation.py`)
- Test files: prefix with `test_` and match module name (e.g., `test_integration_validator.py`)
- E2E test files: descriptive.spec.ts pattern (e.g., `smoke.spec.ts`, `auth.spec.ts`)

**Functions:**
- Python: snake_case (e.g., `sanitize_string()`, `validate_token_format()`, `_get_redis_client()`)
- TypeScript/React: camelCase (e.g., `useChartMode()`, `ChartModeProvider()`)
- Async functions: use async/await pattern, explicitly named with verb prefix (e.g., `async validateGitHub()`)
- Private functions: prefix with underscore (e.g., `_validate_github()`, `_get_redis_client()`)

**Variables:**
- Python: snake_case for module-level and local vars (e.g., `MAX_STRING_LENGTH`, `_fallback_cache`)
- TypeScript: camelCase for local variables (e.g., `chartMode`, `currentStep`)
- Constants: UPPER_SNAKE_CASE in both languages (e.g., `MAX_REQUEST_SIZE = 10 * 1024 * 1024`)
- Type/interface names in TypeScript: PascalCase (e.g., `ChartModeContextType`, `Notification`)
- Boolean variables: prefix with is/has/should (e.g., `isOpen`, `hasRefreshToken`, `shouldLog`)

**Types:**
- TypeScript interfaces: PascalCase (e.g., `GettingStartedContextType`, `NotificationActions`)
- Enums: PascalCase for enum, PascalCase for values (e.g., `PlatformType.GITHUB`, `AnalysisTimeRange.DAYS_7`)
- Pydantic models: PascalCase (e.g., `BaseValidatedModel`, `RootlyIntegrationRequest`)

## Code Style

**Formatting:**
- Frontend: ESLint with Next.js core-web-vitals config
- Config: `.eslintrc.json` at `frontend/.eslintrc.json`
- Key rule override: `react/no-unescaped-entities: off` (allow unescaped entities in JSX)
- Prettier integration via ESLint (no separate .prettierrc observed)
- Line length: Not explicitly specified but code follows readable conventions

**Linting:**
- Frontend: ESLint 9.x with Next.js config extension
- Python: Not formally configured (no pylint/flake8 config found)
- Enforcement: ESLint runs via `npm run lint` in frontend
- TypeScript: strict mode OFF (`"strict": false` in tsconfig.json) - allows development flexibility

## Import Organization

**Order:**
1. React/Framework imports from 'react' or 'next/*'
2. Third-party UI library imports (@radix-ui, lucide-react, etc.)
3. Custom component imports from '@/' paths
4. Local utility/hook imports

**Example from `frontend/src/app/auth/success/page.tsx`:**
```typescript
import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'
```

**Path Aliases:**
- Frontend: `@/*` maps to `./src/*` (configured in tsconfig.json baseUrl and paths)
- Used throughout codebase for imports (e.g., `@/components/ui/card`, `@/contexts/ChartModeContext`)

**Python imports:**
- Standard library first
- Third-party libraries next (fastapi, pydantic, sqlalchemy, redis, etc.)
- Local module imports last
- No path aliases (all relative imports)

## Error Handling

**Patterns:**
- **FastAPI/Python backend**: Use try/except blocks with specific exception handling
  - Security middleware: catch broad exceptions, log with emoji prefix (🚨) for visibility
  - Validation: raise `ValueError` with descriptive messages
  - Database operations: catch `sqlalchemy.exc.OperationalError` for lock/transient errors
  - Network operations: catch `httpx.TimeoutException`, `httpx.NetworkError` separately

- **Frontend**: Use try/catch for async operations
  - Auth pages: Set status state ('processing' | 'success' | 'error')
  - Include ref to prevent double execution in React Strict Mode: `hasAttemptedAuth = useRef(false)`
  - Generic error messages for security (no information disclosure)

**Error Messages:**
- Backend: "Authentication error" for token failures (generic, no token details)
- Backend: Include context: `f"Request size exceeds maximum allowed limit"` with specific limits in response
- Frontend: Use user-friendly messages, hide technical details
- Logging: Include stack traces and context for debugging, emoji prefix for security events

## Logging

**Framework:** Python standard `logging` module

**Patterns:**
- Import at module level: `logger = logging.getLogger(__name__)`
- Log levels: WARNING for security events, DEBUG for validation, INFO for flow
- Security events: Use emoji prefix (🚨) for visibility (e.g., `logger.warning(f"🚨 Security event: ...")`)
- Sample-rate logging for high-volume operations: `if _should_log(): logger.info(...)`
- Structured logging: Use JSON format for complex event data: `json.dumps(event_data)`

**Example from `security.py`:**
```python
logger.warning(f"🚨 Request too large: {content_length} bytes from {request.client.host}")
logger.error(f"🚨 Security middleware error: {e}")
```

## Comments

**When to Comment:**
- Explain "why" decisions, not "what" code does
- Complex algorithms or non-obvious validation logic
- Security-related workarounds (e.g., "Skip restrictive CSP for Swagger UI")
- Prevent common mistakes (e.g., "Body reading would consume request stream")
- Configuration rationale (e.g., "Uses DB 0, same as oncall cache")

**JSDoc/TSDoc:**
- Not heavily used in frontend code
- Python docstrings present for module/function documentation
- Example from `input_validation.py`:
```python
"""
Comprehensive input validation and sanitization for API security.
"""

def sanitize_string(value: str, max_length: int = MAX_STRING_LENGTH) -> str:
    """
    Sanitize string input to prevent XSS and injection attacks.
    """
```

## Function Design

**Size:** Functions are focused and typically 20-50 lines
- Middleware functions: 40-80 lines (handle multiple responsibilities)
- Validation functions: 10-30 lines (single concern)
- Helper functions: 5-20 lines (pure logic)

**Parameters:**
- Use type hints consistently (both Python and TypeScript)
- Optional parameters at end, use defaults
- Python: Use Pydantic models for complex inputs (validated input models)
- TypeScript: Use interfaces for component props

**Return Values:**
- Early returns for guard clauses (e.g., check None and return)
- Explicit return types via type hints
- Async functions return awaitable values (Promise in TS, coroutine in Python)
- Validation functions return bool or raise ValueError

**Example from `input_validation.py`:**
```python
def validate_token_format(platform: str, token: str) -> bool:
    """Validate API token format based on platform."""
    pattern_key = f"{platform.lower()}_token"
    pattern = PATTERNS.get(pattern_key)

    if not pattern:
        logger.warning(f"No token pattern defined for platform: {platform}")
        return len(token) >= 10 and re.match(r"^[A-Za-z0-9_-]+$", token)

    return bool(pattern.match(token))
```

## Module Design

**Exports:**
- Python: Use `__all__` at end of module to explicitly export public API
- TypeScript: Use named exports, avoid default exports for functions/classes
- Example from `input_validation.py`:
```python
__all__ = [
    'BaseValidatedModel',
    'TokenValidation',
    'validate_token_format',
    'sanitize_string'
]
```

**Barrel Files:**
- Not explicitly used in observed codebase
- Component exports done individually

**Module Organization:**
- Constants/configuration at top
- Helper functions before main functions
- Classes before functions that use them
- Exports at end (__all__)

---

*Convention analysis: 2026-01-30*
