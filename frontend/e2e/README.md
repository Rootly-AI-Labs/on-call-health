# E2E Tests

End-to-end tests using Playwright.

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
