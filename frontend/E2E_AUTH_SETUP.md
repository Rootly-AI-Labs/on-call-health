# E2E Test Authentication Setup

## Overview

This project uses **API-based authentication** for E2E tests, which is the recommended best practice for 2025. This approach is:
- ✅ Faster than UI-based login
- ✅ More reliable (avoids CAPTCHA, rate limits)
- ✅ Easier to maintain
- ✅ Works identically for OAuth and password authentication

## Test Credentials

### Test Account
- **Email:** `avery.kim@oncallhealth.ai`
- **Password:** `Rootlydemo100!!`
- **Alternative accounts:** `ethan.hart@oncallhealth.ai`, `anika.shah@oncallhealth.ai` (same password)

⚠️ **Important:** These are dedicated test accounts with access to test data only.

## Local Development Setup

1. **Copy the environment template:**
   ```bash
   cd frontend
   cp .env.test.example .env.test
   ```

2. **Edit `.env.test` (optional):**
   ```bash
   # The defaults work out of the box, but you can customize:
   E2E_TEST_EMAIL=avery.kim@oncallhealth.ai
   E2E_TEST_PASSWORD=Rootlydemo100!!
   PLAYWRIGHT_API_URL=http://localhost:8000
   PLAYWRIGHT_BASE_URL=http://localhost:3000
   ```

3. **Run tests:**
   ```bash
   npm run test:e2e
   ```

## CI/CD Setup (GitHub Actions)

### Add Secrets to GitHub Repository

1. Go to: **Settings** → **Secrets and variables** → **Actions**
2. Add the following **Repository secrets**:
   - `E2E_TEST_EMAIL` = `avery.kim@oncallhealth.ai`
   - `E2E_TEST_PASSWORD` = `Rootlydemo100!!`

### Example GitHub Actions Workflow

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci
        working-directory: ./frontend

      - name: Install Playwright browsers
        run: npx playwright install --with-deps
        working-directory: ./frontend

      - name: Run E2E tests
        env:
          E2E_TEST_EMAIL: ${{ secrets.E2E_TEST_EMAIL }}
          E2E_TEST_PASSWORD: ${{ secrets.E2E_TEST_PASSWORD }}
        run: npm run test:e2e
        working-directory: ./frontend
```

## How It Works

### 1. Authentication Setup (`e2e/auth.setup.ts`)
```typescript
// This runs once before all tests
// 1. Calls the password login API
// 2. Stores the JWT token in localStorage
// 3. Saves the auth state to .auth/user.json
```

### 2. Session Reuse
All other tests automatically reuse the saved authentication state via `storageState` in `playwright.config.ts`:

```typescript
use: {
  storageState: './e2e/.auth/user.json',
}
```

This means:
- ✅ Login happens **once** per test run
- ✅ All tests run with authenticated session
- ✅ Significantly faster test execution

## Security Best Practices

### ✅ DO:
- Use dedicated test accounts (not real user accounts)
- Store credentials in environment variables
- Add `.env.test` to `.gitignore`
- Use GitHub Secrets for CI/CD
- Rotate test passwords regularly (every 90 days)

### ❌ DON'T:
- Hardcode credentials in test files
- Commit `.env.test` to git
- Use real user credentials for testing
- Share test credentials publicly
- Use production credentials in tests

## Password Management

### Backend Implementation
Test accounts have password hashes stored in the database:
- Hash algorithm: `bcrypt` with salt
- Password endpoint: `POST /auth/login/password`
- Returns: JWT token with 7-day expiration

### Rotating Test Passwords

If you need to change the test password:

1. **Update the database:**
   ```bash
   # Generate new hash
   python3 -c "import bcrypt; print(bcrypt.hashpw(b'NewPassword123', bcrypt.gensalt()).decode())"

   # Update database
   psql -d your_database -c "UPDATE users SET password_hash = '<new_hash>' WHERE email = 'avery.kim@oncallhealth.ai';"
   ```

2. **Update secrets:**
   - Local: Update `.env.test`
   - GitHub: Update `E2E_TEST_PASSWORD` secret

## Troubleshooting

### Tests fail with "Password login failed: 401"
- Check that the backend is running on port 8000
- Verify credentials are correct in `.env.test`
- Ensure test account exists in database with password hash

### Tests fail with "Auth state file not found"
- Run the `setup` project first: `npx playwright test --project=setup`
- Check that `.auth/user.json` was created in `frontend/e2e/.auth/`

### Tests fail in CI but work locally
- Verify GitHub Secrets are configured correctly
- Check that the backend URL is accessible in CI
- Ensure Playwright browsers are installed in CI

## Additional Resources

- [Playwright Authentication Guide](https://playwright.dev/docs/auth)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [E2E Testing Best Practices](https://playwright.dev/docs/best-practices)
