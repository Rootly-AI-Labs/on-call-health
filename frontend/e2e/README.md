# E2E Tests

End-to-end tests using Playwright.

## Setup

1. Copy the example environment file:
```bash
cd frontend
cp .env.test.example .env.test
```

2. Edit `.env.test` with test credentials (get from team or GitHub Secrets):
```bash
E2E_TEST_EMAIL_AVERY=your-test-email@example.com
E2E_TEST_PASSWORD_AVERY=your-test-password
PLAYWRIGHT_API_URL=http://localhost:8000
PLAYWRIGHT_BASE_URL=http://localhost:3000
```

3. Start the backend server:
```bash
cd backend
source venv/bin/activate
DATABASE_URL="<get from team>" uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

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
