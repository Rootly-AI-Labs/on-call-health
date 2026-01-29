import { test as setup, expect } from '@playwright/test';
import * as path from 'path';

const authFile = path.join(__dirname, '.auth/user.json');

// Load credentials from environment variables (supports both local .env and GitHub Actions secrets)
// GitHub Secrets use per-user naming: E2E_TEST_EMAIL_AVERY, E2E_TEST_PASSWORD_AVERY
const TEST_EMAIL = process.env.E2E_TEST_EMAIL_AVERY || process.env.E2E_TEST_EMAIL || 'avery.kim@oncallhealth.ai';
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD_AVERY || process.env.E2E_TEST_PASSWORD || 'Rootlydemo100!!';
const API_URL = process.env.PLAYWRIGHT_API_URL || 'http://localhost:8000';
const ROOTLY_TEST_TOKEN = process.env.E2E_ROOTLY_TOKEN || process.env.ROOTLY_API_TOKEN;

setup('authenticate with password', async ({ page, request }) => {
  // Use real API authentication (works locally and in CI against production)
  console.log(`✓ Authenticating against backend: ${API_URL}`);

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

  // Configure a test Rootly integration if token is available
  if (ROOTLY_TEST_TOKEN) {
    console.log('✓ Rootly token available, setting up test integration...');

    // Step 1: Test the token
    const testResponse = await request.post(`${API_URL}/rootly/token/test`, {
      headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
      },
      data: {
        token: ROOTLY_TEST_TOKEN
      }
    });

    if (testResponse.status() === 200) {
      const testData = await testResponse.json();
      console.log('✓ Rootly token validated:', testData.preview?.suggested_name || 'Unknown Org');

      // Step 2: Add the integration
      const addResponse = await request.post(`${API_URL}/rootly/token/add`, {
        headers: {
          'Authorization': `Bearer ${access_token}`,
          'Content-Type': 'application/json'
        },
        data: {
          token: ROOTLY_TEST_TOKEN,
          name: testData.preview?.suggested_name || 'E2E Test Integration'
        }
      });

      if (addResponse.status() === 200) {
        const integrationData = await addResponse.json();
        console.log('✓ Rootly integration created:', integrationData.integration?.name);
      } else {
        const errorText = await addResponse.text();
        console.log('⚠ Failed to add Rootly integration:', addResponse.status(), errorText);
      }
    } else {
      const errorText = await testResponse.text();
      console.log('⚠ Failed to validate Rootly token:', testResponse.status(), errorText);
    }
  } else {
    console.log('⚠ No Rootly token configured (E2E_ROOTLY_TOKEN or ROOTLY_API_TOKEN)');
    console.log('  Organization selector will not be available for E2E tests');
  }

  // Save the authentication state for other tests to reuse
  await page.context().storageState({ path: authFile });

  console.log('✓ Auth state saved to', authFile);
});
