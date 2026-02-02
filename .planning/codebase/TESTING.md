# Testing Patterns

**Analysis Date:** 2026-01-30

## Test Framework

**Backend:**
- Runner: pytest (configured via requirements.txt: `pytest`)
- Assertion Library: unittest (standard library)
- Config: `backend/tests/conftest.py` provides shared fixtures and environment setup

**Frontend:**
- E2E Runner: Playwright (`@playwright/test` ^1.58.0)
- E2E Config: `frontend/playwright.config.ts`
- Assertion Library: Playwright's built-in expect
- Unit/Component Tests: Not detected; E2E tests are primary testing approach

**Run Commands:**

Backend:
```bash
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest backend/tests/           # Run backend test suite
pytest backend/tests/test_admin_security.py  # Run specific test file
```

Frontend:
```bash
npm run test:e2e                # Run E2E tests
npm run test:e2e:ui            # Interactive Playwright UI
npm run test:e2e:debug         # Debug mode
npm run test:e2e:report        # View HTML report
```

## Test File Organization

**Location:**
- Backend: Co-located in `backend/tests/` directory (separate from source)
- Frontend: Co-located in `frontend/e2e/` directory (separate from source)

**Naming:**
- Backend: `test_*.py` (e.g., `test_admin_security.py`, `test_integration_validator.py`)
- Frontend: `*.spec.ts` (e.g., `integrations.spec.ts`, `smoke.spec.ts`)
- Frontend setup: `*.setup.ts` (e.g., `auth.setup.ts` runs before test suite)

**Structure:**
- Backend tests grouped by feature in same directory
- Frontend tests also grouped by feature
- Shared fixtures in `backend/tests/conftest.py`
- Authentication setup in `frontend/e2e/auth.setup.ts` (runs once before all tests)

## Test Structure

**Backend Pattern (Unit Tests):**

```python
import unittest
from unittest.mock import Mock, patch, AsyncMock

class TestFeatureName(unittest.TestCase):
    """Test suite for feature description."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=Session)
        self.service = ServiceClass(self.mock_db)

    def test_positive_case_description(self):
        """Test the expected behavior."""
        # Setup
        mock_obj = Mock()
        mock_obj.property = "value"

        # Execute
        result = self.service.method(mock_obj)

        # Assert
        self.assertTrue(result)
        self.assertEqual(result.field, "expected")

    def test_error_case_description(self):
        """Test error handling."""
        with self.assertRaises(ValueError):
            self.service.method(invalid_input)

    def _run_async(self, coro):
        """Helper to run async functions in tests."""
        return asyncio.run(coro)

    @patch('module.external_function')
    def test_with_mocking(self, mock_func):
        """Test with mocked external dependency."""
        mock_func.return_value = expected_value
        result = self.service.method()
        self.assertEqual(result, expected_value)
```

**Frontend Pattern (E2E Tests):**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Navigation and setup before each test
    await page.goto('/feature-path');
    await page.waitForLoadState('networkidle');
  });

  test('should display element when loaded', async ({ page }) => {
    // Check initial state
    const element = page.locator('selector');
    await expect(element).toBeVisible({ timeout: DEFAULT_TIMEOUT });
  });

  test('should handle user interaction', async ({ page }) => {
    // User action
    await page.locator('button').click();

    // Verify result
    const result = page.locator('.result');
    await expect(result).toContainText('expected text');
  });

  test('should handle async operations', async ({ page, request }) => {
    // API interaction
    const response = await request.post('/api/endpoint', {
      data: { field: 'value' }
    });

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.success).toBe(true);
  });
});
```

## Mocking

**Backend Framework:** unittest.mock (Mock, MagicMock, patch, AsyncMock)

**Patterns:**

1. **Mock database session:**
```python
self.mock_db = Mock(spec=Session)
self.mock_db.query().filter().first.return_value = mock_obj
```

2. **Mock async external calls:**
```python
with patch('httpx.AsyncClient') as mock_client:
    mock_response = Mock()
    mock_response.status_code = 200
    mock_client.return_value.__aenter__.return_value.get = AsyncMock(
        return_value=mock_response
    )
```

3. **Patch external functions:**
```python
@patch('app.services.module.external_function')
def test_something(self, mock_func):
    mock_func.return_value = expected_value
```

4. **Patch environment variables:**
```python
with patch.dict(os.environ, {"VAR": "value"}, clear=False):
    # Test with patched environment
```

**Frontend (E2E):**
- No traditional mocking; tests against real backend
- Authentication handled via setup project storing auth state
- Environment variables configured via `.env` or GitHub Actions secrets

**What to Mock:**
- External API calls (GitHub, Slack, Jira, etc.)
- Database operations
- Time-dependent operations
- File system operations

**What NOT to Mock:**
- Business logic within same module
- Integration points that should be tested together
- User-visible behavior (use real components in E2E)

## Fixtures and Factories

**Backend Test Data:**

Located in `backend/tests/conftest.py`:

```python
# Environment setup
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ENCRYPTION_KEY", "base64-encoded-key")

# Mock frameworks
mock_fastmcp_instance = MagicMock()
mock_fastmcp_instance.app = MagicMock()
mock_fastmcp_instance.tool = MagicMock(return_value=lambda f: f)

sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
```

**Test Pattern - Manual Fixtures:**

```python
class TestIntegrationValidator(unittest.TestCase):
    def setUp(self):
        """Set up fresh fixtures for each test."""
        self.mock_db = Mock(spec=Session)
        self.mock_integration = Mock(spec=GitHubIntegration)
        self.mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = self.mock_integration
```

**Frontend Test Data:**

Configured via environment variables:
```typescript
const TEST_EMAIL = process.env.E2E_TEST_EMAIL_AVERY || process.env.E2E_TEST_EMAIL;
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD_AVERY || process.env.E2E_TEST_PASSWORD;
const ROOTLY_TEST_TOKEN = process.env.E2E_ROOTLY_API_KEY || process.env.ROOTLY_API_TOKEN;
```

Authentication state persisted across tests via Playwright:
```typescript
{
  name: 'chromium',
  use: {
    ...devices['Desktop Chrome'],
    storageState: './e2e/.auth/user.json',
  },
  dependencies: ['setup'],
}
```

## Coverage

**Requirements:** Not explicitly enforced (no coverage config detected)

**View Coverage:**

Backend (if needed):
```bash
pytest --cov=app backend/tests/
pytest --cov=app --cov-report=html backend/tests/
```

Frontend (if implemented):
```bash
# Coverage not currently configured for E2E tests
```

## Test Types

**Backend - Unit Tests:**
- Scope: Individual service/function behavior
- Approach: Mocked dependencies, isolated logic
- Examples:
  - `test_admin_security.py`: API key validation, IP whitelist parsing
  - `test_integration_validator.py`: Token validation for GitHub, Linear, Jira
  - `test_incident_metrics.py`: OCH metric calculations from incident data
  - `test_token_refresh_coordinator.py`: Token refresh and caching logic

**Backend - Integration Tests:**
- Not explicitly separated from unit tests
- Tests with real database queries and multiple service interactions
- Example: `test_member_surveys.py` tests survey response aggregation

**Frontend - E2E Tests:**
- Scope: Full user workflows and UI interactions
- Approach: Real browser, real backend
- Authentication: Centralized in setup project
- Examples:
  - `integrations.spec.ts`: Integration page loading, card display, interactions
  - `auth.spec.ts`: Login flow with real API
  - `smoke.spec.ts`: Basic smoke tests
  - `landing-page.spec.ts`: Public pages
  - `org-management.spec.ts`: Organization features

## Common Patterns

**Backend - Async Testing:**

```python
def _run_async(self, coro):
    """Helper to run async functions in synchronous test context."""
    return asyncio.run(coro)

# Usage in test:
result = self._run_async(self.validator._validate_github(user_id=1))
```

**Backend - Error Testing:**

```python
def test_error_case(self):
    """Test that errors are properly raised."""
    with self.assertRaises(HTTPException) as context:
        some_operation_that_fails()

    self.assertEqual(context.exception.status_code, 400)
    self.assertIn("error_code", context.exception.detail)
```

**Backend - Mock Configuration:**

```python
@patch('app.services.integration_validator.decrypt_token')
def test_with_patched_function(self, mock_decrypt):
    """Test with specific function mocked."""
    mock_decrypt.return_value = "decrypted_value"

    result = self.service.method()

    mock_decrypt.assert_called_once()
```

**Frontend - Playwright Setup (Authentication):**

```typescript
// auth.setup.ts - runs once before all tests
setup('authenticate with password', async ({ page, request }) => {
  const response = await request.post(`${API_URL}/auth/login/password`, {
    data: { email: TEST_EMAIL, password: TEST_PASSWORD }
  });

  const { access_token } = await response.json();

  await page.goto('/');
  await page.evaluate((token) => {
    localStorage.setItem('auth_token', token);
  }, access_token);

  await page.context().storageState({ path: './e2e/.auth/user.json' });
});
```

**Frontend - Page Interactions:**

```typescript
test('should respond to user action', async ({ page }) => {
  // Navigate
  await page.goto('/integrations');
  await page.waitForLoadState('networkidle');

  // Interact
  await page.locator('button:has-text("Connect")').click();

  // Assert
  const dialog = page.locator('[role="dialog"]');
  await expect(dialog).toBeVisible({ timeout: 10000 });
});
```

**Frontend - API Mocking (Request Interception):**

Currently not used; tests hit real backend. If needed:

```typescript
await page.route('**/api/integrations', route => {
  route.abort('blockedbyresponse');
  // or
  route.continue({
    response: {
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockData)
    }
  });
});
```

## Test Coverage Gaps

**Backend:**
- No tests detected for: MCP server endpoints, AI agent workflows
- Limited test coverage for: Authentication OAuth flows, token refresh edge cases

**Frontend:**
- No unit/component tests; only E2E coverage
- Missing: Modal/dialog interactions, form validation edge cases, error states
- Missing: Accessibility testing

## Configuration Details

**Backend Test Isolation:**
- Uses mock database: `postgresql://test:test@localhost/test`
- Mocks external services (GitHub, Slack, etc.) to avoid API calls
- Isolates tests via setUp() method resetting fixtures

**Frontend Test Isolation:**
- E2E tests run against real backend (no test data isolation)
- Authentication state stored in `.auth/user.json` per browser project
- Tests run sequentially in CI (workers: 1) to avoid database conflicts
- Parallel in local development (fullyParallel: true)

**CI/CD Integration:**
- Backend: Can be run via pytest directly
- Frontend: Playwright configured for CI with retries (2 retries on CI)
- Frontend: Screenshots captured on failure, traces on first retry
- Authentication: Supports GitHub Actions secrets per user (E2E_TEST_EMAIL_AVERY, E2E_TEST_PASSWORD_AVERY)

---

*Testing analysis: 2026-01-30*
