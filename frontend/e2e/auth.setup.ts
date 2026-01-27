import { test as setup, expect } from '@playwright/test';
import * as path from 'path';

const authFile = path.join(__dirname, '.auth/user.json');

// Load credentials from environment variables (supports both local .env and GitHub Actions secrets)
const TEST_EMAIL = process.env.E2E_TEST_EMAIL || 'avery.kim@oncallhealth.ai';
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD || 'Rootlydemo100!!';
const API_URL = process.env.PLAYWRIGHT_API_URL || 'http://localhost:8000';

setup('authenticate with password', async ({ page, request }) => {
  // Use API-based authentication (faster and more reliable than UI login)
  const response = await request.post(`${API_URL}/auth/login/password`, {
    data: {
      email: TEST_EMAIL,
      password: TEST_PASSWORD
    }
  });

  if (response.status() !== 200) {
    console.log('Password login failed with status:', response.status());
    console.log('Response:', await response.text());
    throw new Error(`Password login failed: ${response.status()}`);
  }

  expect(response.status()).toBe(200);

  const responseData = await response.json();
  const { access_token, user } = responseData;

  console.log('✓ Password login successful for:', user.email);
  console.log('✓ JWT token received');

  // Set up authentication state by injecting the token
  await page.goto('/');

  await page.evaluate((token) => {
    localStorage.setItem('auth_token', token);
  }, access_token);

  console.log('✓ Token stored in localStorage');

  // Save the authentication state for other tests to reuse
  await page.context().storageState({ path: authFile });

  console.log('✓ Auth state saved to', authFile);
});
