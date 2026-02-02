# Testing Patterns

**Analysis Date:** 2026-01-30

## Test Framework

**Runner:**
- Backend: pytest (configured in `requirements.txt`)
- Frontend: Playwright for E2E testing (`@playwright/test` ^1.58.0)
- No unit test framework detected for frontend (no Jest/Vitest config)

**Assertion Library:**
- Backend: Built-in unittest assertions + pytest conventions
- Frontend: Playwright assertions (`expect()` API)

**Run Commands:**
```bash
# Backend (inferred from requirements)
pytest                     # Run all tests
pytest tests/test_integration_validator.py  # Run specific test file
pytest -v                  # Verbose output

# Frontend E2E
npm run test:e2e          # Run Playwright tests
npm run test:e2e:ui       # Open Playwright UI for interactive testing
npm run test:e2e:debug    # Debug mode with browser open
npm run test:e2e:report   # View HTML test report
```

## Test File Organization

**Location:**
- Backend: `backend/tests/` directory co-located with app
- Frontend: `frontend/e2e/` directory for E2E tests
- No unit test files in frontend (all testing appears to be E2E)

**Naming:**
- Backend: `test_*.py` pattern (e.g., `test_integration_validator.py`, `test_admin_security.py`)
- Frontend: `*.spec.ts` pattern (e.g., `smoke.spec.ts`, `auth.spec.ts`, `integrations.spec.ts`)

**Structure:**
```
backend/tests/
├── conftest.py                    # Pytest fixtures and configuration
├── mock_data/                     # Mock data for tests
│   ├── __init__.py
│   └── loader.py
├── test_integration_validator.py
├── test_admin_security.py
├── test_slack_interactions.py
├── test_mcp_auth.py
├── test_och_calculations.py
├── test_member_surveys.py
└── [other test files]

frontend/e2e/
├── smoke.spec.ts                  # Basic app loading tests
├── auth.spec.ts                   # Authentication flow tests
├── integrations.spec.ts           # Integration tests
├── org-management.spec.ts         # Organization management tests
├── landing-page.spec.ts           # Landing page functionality
└── .auth/                         # Playwright auth state storage
    └── user.json
```

## Test Structure

**Suite Organization:**
```typescript
// Frontend/Playwright pattern
test.describe('Smoke Tests', () => {
  test('landing page has correct title', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle('On-Call Health')
  })
})
```

**Backend/Pytest pattern:**
```python
class TestIntegrationValidator(unittest.TestCase):
    """Test suite for IntegrationValidator service."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=Session)
        self.validator = IntegrationValidator(self.mock_db)

    def test_validate_github_success(self):
        """Test successful GitHub validation."""
        # Arrange
        mock_integration = Mock(spec=GitHubIntegration)
        # Act & Assert
```

**Patterns:**
- Setup: `setUp()` method creates fresh fixtures before each test
- Teardown: `tearDown()` method cleans up after tests (e.g., `_fallback_cache.clear()`)
- Async support: Helper method `_run_async()` to run coroutines in tests

## Mocking

**Framework:**
- Backend: `unittest.mock` (Mock, patch, AsyncMock)
- Frontend: Playwright page/browser mocks (built-in)

**Patterns - Backend:**
```python
# Mock database session
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

self.mock_db = Mock(spec=Session)

# Mock external HTTP calls
with patch('httpx.AsyncClient') as mock_client:
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {...}}
    mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    result = self._run_async(self.validator._validate_github(user_id=1))

# Mock specific functions
with patch('app.services.integration_validator.decrypt_token') as mock_decrypt:
    mock_decrypt.return_value = "decrypted_token"
```

**Patterns - Frontend:**
```typescript
// Playwright's built-in locator matching
const heading = page.locator('h1:has-text("Catch exhaustion")')
await expect(heading).toBeVisible()

// Attribute matching
const githubLink = page.locator('a[href*="github.com/Rootly-AI-Labs"]')
await expect(githubLink.first()).toBeVisible()
```

**What to Mock:**
- External API calls (GitHub, Linear, Jira, PagerDuty) via httpx.AsyncClient
- Database queries via Mock(spec=Session)
- Encryption/decryption functions (decrypt_token, encrypt_token)
- Redis client when testing fallback behavior

**What NOT to Mock:**
- Pydantic validation models (test with real models)
- Core business logic that should be tested
- Internal helper functions (test through public API)
- Time/datetime for most tests (except expiry validation)

## Fixtures and Factories

**Test Data:**
```python
# Backend pattern - create mocks inline
mock_integration = Mock(spec=LinearIntegration)
mock_integration.access_token = "encrypted_token"
mock_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(hours=12)

# Time-based fixtures for expiry testing
expired = datetime.now(dt_timezone.utc) - timedelta(minutes=10)
far_future = datetime.now(dt_timezone.utc) + timedelta(hours=12)
```

**Location:**
- Backend: Inline in test classes or in `conftest.py` for shared fixtures
- `conftest.py` sets environment variables before imports (to prevent app init errors)
- Mock data files: `backend/tests/mock_data/` for reusable test data

**Example from `conftest.py`:**
```python
# Set required environment variables before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItdGVzdGluZy1vbmx5")

# Mock FastMCP before imports to avoid ASGI errors
mock_fastmcp_instance = MagicMock()
sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server.fastmcp"].FastMCP = mock_fastmcp_class
```

## Coverage

**Requirements:** No formal coverage requirements detected in configuration

**View Coverage:**
```bash
# Backend (inferred - pytest-cov likely)
pytest --cov=app tests/

# Frontend
npm run test:e2e -- --reporter=coverage  # If configured
```

**Observed Coverage:**
- Backend: Unit tests for core services (integration_validator, validation, security)
- Frontend: E2E tests only (no unit test coverage detected)
- High-coverage areas: validation, security, authentication
- Lower coverage: UI components (E2E-only approach)

## Test Types

**Unit Tests:**
- Location: `backend/tests/test_*.py`
- Scope: Individual functions, classes, and services
- Approach: Isolate with mocks, test behavior with assertions
- Example: `TestIntegrationValidator` tests validation logic for GitHub/Linear/Jira integrations
- Async support: Use `_run_async()` helper to run coroutines

**Integration Tests:**
- Not explicitly separated in file structure
- Some test files appear to test multiple components (e.g., validation cache interaction)
- Example: `TestValidationCache` tests interaction between cache getters/setters and expiry
- Use real cache objects, mock external services

**E2E Tests:**
- Location: `frontend/e2e/*.spec.ts`
- Scope: Full user workflows across pages
- Approach: Browser automation with Playwright
- Example: `smoke.spec.ts` verifies landing page loads and buttons visible
- Example: `auth.spec.ts` tests complete authentication flow
- Configuration: `playwright.config.ts` defines baseURL, retries, and parallelization

## Common Patterns

**Async Testing - Backend:**
```python
def _run_async(self, coro):
    """Helper to run async functions in tests."""
    return asyncio.run(coro)

# Usage in test
def test_validate_github_success(self):
    result = self._run_async(self.validator._validate_github(user_id=1))
    self.assertTrue(result["valid"])
```

**Async Testing - Frontend:**
```typescript
test('landing page has correct title', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle('On-Call Health')
})
```

**Error Testing - Backend:**
```python
def test_get_valid_linear_token_no_refresh_token_raises_error(self):
    """Test that expired token with no refresh token raises an error."""
    mock_integration = Mock(spec=LinearIntegration)
    mock_integration.token_expires_at = datetime.now(dt_timezone.utc) - timedelta(minutes=10)
    mock_integration.refresh_token = None

    with self.assertRaises(ValueError) as context:
        self._run_async(self.validator._get_valid_linear_token(mock_integration))

    self.assertIn("Authentication error", str(context.exception))
```

**Error Testing - Frontend:**
```typescript
test('landing page shows sign in buttons', async ({ page }) => {
  await page.goto('/')

  const googleButton = page.locator('button:has-text("Sign in with Google")')
  await expect(googleButton).toBeVisible()
})
```

**Mocking HTTP Responses:**
```python
with patch('httpx.AsyncClient') as mock_client:
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "new_token", "expires_in": 86400}
    mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

    # Test code that uses the client
    token = self._run_async(self.validator._get_valid_linear_token(mock_integration))
```

**State Management in Tests:**
```python
def setUp(self):
    """Set up test fixtures."""
    self.mock_db = Mock(spec=Session)
    self.validator = IntegrationValidator(self.mock_db)

def tearDown(self):
    """Clear cache after each test."""
    _fallback_cache.clear()
```

## Playwright Configuration

**File:** `frontend/playwright.config.ts`

**Key Settings:**
- Test directory: `./e2e`
- Fully parallel: Tests run in parallel (unless CI environment)
- CI behavior: Retries enabled (2 retries), serial execution (1 worker)
- Base URL: Configurable via `PLAYWRIGHT_BASE_URL` env var (defaults to `http://localhost:3000`)
- Reporters: HTML report generation
- Trace: Collected on first retry for debugging
- Screenshots: Only on failure
- Auth setup: Uses `.auth/user.json` for storing authenticated session state
- Web server: Automatically starts `npm run dev` before tests (reuses existing if available)

**Browser Coverage:**
- Chromium (primary)
- Firefox
- WebKit (Safari)
- Mobile viewports: Commented out (can be enabled)

---

*Testing analysis: 2026-01-30*
