import { test as setup, expect } from '@playwright/test';
import * as path from 'path';

const authFile = path.join(__dirname, '.auth/user.json');

// Load credentials from environment variables (supports both local .env and GitHub Actions secrets)
// GitHub Secrets use per-user naming: E2E_TEST_EMAIL_AVERY, E2E_TEST_PASSWORD_AVERY
const TEST_EMAIL = process.env.E2E_TEST_EMAIL_AVERY || process.env.E2E_TEST_EMAIL || 'avery.kim@oncallhealth.ai';
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD_AVERY || process.env.E2E_TEST_PASSWORD || 'Rootlydemo100!!';
const API_URL = process.env.PLAYWRIGHT_API_URL || 'http://localhost:8000';
const ROOTLY_API_KEY = process.env.E2E_ROOTLY_API_KEY || process.env.ROOTLY_API_KEY;
const GITHUB_TOKEN = process.env.E2E_GITHUB_TOKEN || process.env.GITHUB_TOKEN;

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

  // Connect Rootly integration if API key is available
  if (ROOTLY_API_KEY) {
    console.log('✓ Connecting Rootly integration...');

    // Test Rootly token
    const rootlyTestResponse = await request.post(`${API_URL}/rootly/token/test`, {
      headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
      },
      data: {
        token: ROOTLY_API_KEY
      }
    });

    if (rootlyTestResponse.status() === 200) {
      const rootlyData = await rootlyTestResponse.json();
      console.log('✓ Rootly token validated:', rootlyData.preview?.organization_name || 'Unknown org');

      // Add Rootly integration
      const addRootlyResponse = await request.post(`${API_URL}/rootly/token/add`, {
        headers: {
          'Authorization': `Bearer ${access_token}`,
          'Content-Type': 'application/json'
        },
        data: {
          token: ROOTLY_API_KEY,
          name: rootlyData.preview?.suggested_name || 'Rootly Test',
          organization_name: rootlyData.preview?.organization_name || 'Test Org',
          total_users: rootlyData.preview?.total_users || 0,
          permissions: rootlyData.account_info?.permissions || {}
        }
      });

      if (addRootlyResponse.status() === 200 || addRootlyResponse.status() === 400) {
        let integrationId = null;

        if (addRootlyResponse.status() === 200) {
          // New integration created
          const integrationData = await addRootlyResponse.json().catch(() => null);
          integrationId = integrationData?.integration?.id || integrationData?.id;
          console.log('✓ Rootly integration connected (ID:', integrationId, ')');
        } else if (addRootlyResponse.status() === 400) {
          // Integration already exists - fetch it
          console.log('✓ Rootly integration already exists - fetching existing integration...');

          const listResponse = await request.get(`${API_URL}/rootly/integrations`, {
            headers: {
              'Authorization': `Bearer ${access_token}`,
              'Content-Type': 'application/json'
            }
          });

          if (listResponse.status() === 200) {
            const data = await listResponse.json();
            const integrations = data.integrations || [];
            // Get the first active Rootly integration, or just the first one if none are marked active
            const existingIntegration = integrations.find((i: any) => i.is_active) || integrations[0];
            if (existingIntegration) {
              integrationId = existingIntegration.id;
              console.log('✓ Found existing integration (ID:', integrationId, 'is_active:', existingIntegration.is_active, ')');
            } else {
              console.log('⚠ No integrations found in response');
            }
          }
        }

        // Set as selected organization if we have an ID
        if (integrationId) {
          await page.evaluate((id) => {
            localStorage.setItem('selected_organization', id.toString());
          }, integrationId);

          console.log('✓ Rootly integration selected as active organization');
        } else {
          console.log('⚠ Warning: Could not determine integration ID');
        }
      }
    } else {
      console.log('⚠ Rootly token test failed - tests may be limited');
    }
  } else {
    console.log('⚠ No Rootly API key - tests will run with limited functionality');
  }

  // Connect GitHub integration if token is available
  if (GITHUB_TOKEN) {
    console.log('✓ GitHub token available for matching tests');
  }

  // Save the authentication state for other tests to reuse
  await page.context().storageState({ path: authFile });

  console.log('✓ Auth state saved to', authFile);
});
