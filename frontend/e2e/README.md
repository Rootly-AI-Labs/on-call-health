# E2E Tests

End-to-end tests using Playwright.

## Setup

Create a `.env` file in the `frontend/` directory with the required credentials:

```bash
# Required for authentication
E2E_TEST_EMAIL=your-test-email@example.com
E2E_TEST_PASSWORD=your-test-password

# Optional: Rootly integration for org management tests
E2E_ROOTLY_API_KEY=rootly_xxxxx

# Optional: Override API URL (defaults to http://localhost:8000)
PLAYWRIGHT_API_URL=https://your-backend-url.com
```

**Note:** Never commit credentials to the repository. The `.env` file is gitignored.

## Quick Start

```bash
# Run with UI (recommended)
npm run test:e2e:ui

# Run all tests
npm run test:e2e

# Debug mode
npm run test:e2e:debug
```

## CI/CD

Tests run on:
- **Manual trigger** via GitHub Actions
- **Nightly** at 2 AM UTC
- **PRs to main**

## Writing Tests

```typescript
import { test, expect } from '@playwright/test';

test('example test', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1')).toBeVisible();
});
```

Tests auto-discover from `e2e/*.spec.ts`
