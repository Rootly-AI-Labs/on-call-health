# E2E Tests

End-to-end tests using Playwright for the On-Call Health frontend.

## Running Tests Locally

```bash
# Run all tests (headless)
npm run test:e2e

# Run tests with UI mode (recommended for development)
npm run test:e2e:ui

# Run tests in debug mode
npm run test:e2e:debug

# View last test report
npm run test:e2e:report
```

## Running Specific Tests

```bash
# Run tests in a specific file
npx playwright test e2e/landing-page.spec.ts

# Run a single test by name
npx playwright test -g "should load and display main heading"

# Run tests on a specific browser
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

## CI/CD

E2E tests run automatically on:
- **Manual trigger**: Go to Actions → E2E Tests → Run workflow
- **Nightly**: Every day at 2 AM UTC
- **PRs to main**: Runs on all PRs targeting the main branch

### Manual Trigger Options
You can choose which browser to test:
- `chromium` (default)
- `firefox`
- `webkit`
- `all` (runs all three browsers in parallel)

## Writing Tests

Tests are located in the `e2e/` directory. Each test file should follow the pattern `*.spec.ts`.

Example:
```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test('should do something', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toBeVisible();
  });
});
```

## Debugging

1. **UI Mode** (recommended): `npm run test:e2e:ui`
   - Visual test runner
   - Time-travel debugging
   - Watch mode

2. **Debug Mode**: `npm run test:e2e:debug`
   - Step through tests
   - Playwright Inspector

3. **Screenshots & Videos**:
   - Screenshots taken on failure (stored in `test-results/`)
   - Videos available in CI artifacts

## Configuration

See `playwright.config.ts` for configuration options.

Key settings:
- Base URL: `http://localhost:3000` (configurable via `PLAYWRIGHT_BASE_URL`)
- Retries: 2 retries on CI, 0 locally
- Parallel: Enabled by default
- Web server: Automatically starts dev server before tests
