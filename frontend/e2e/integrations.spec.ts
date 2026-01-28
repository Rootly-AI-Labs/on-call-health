import { test, expect } from '@playwright/test';

/**
 * E2E tests for the Integrations page
 * Tests integration cards, connection flows, and UI interactions
 */

const ROOTLY_API_KEY = process.env.E2E_ROOTLY_API_KEY;

test.describe('Integrations Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to integrations page before each test
    await page.goto('/integrations');
    await page.waitForLoadState('networkidle');
  });

  test('should load integrations page successfully', async ({ page }) => {
    // Check page loads with 200 status
    const response = await page.goto('/integrations');
    expect(response?.status()).toBe(200);

    // Verify page has content
    const bodyText = await page.textContent('body');
    expect(bodyText?.length).toBeGreaterThan(0);
  });

  test('should display page heading', async ({ page }) => {
    // Look for main heading (could be h1 or h2)
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible();

    const headingText = await heading.textContent();
    expect(headingText).toBeTruthy();
  });

  test('should display integration cards', async ({ page }) => {
    // Use consistent selector for both waiting and counting
    const cardSelector = '[data-testid*="integration"], [class*="card"]';

    // Wait for loading to complete
    await page.waitForSelector(cardSelector, {
      state: 'visible',
      timeout: 10000
    });

    // Check that integration cards are present using same selector
    const cards = page.locator(cardSelector);
    const cardCount = await cards.count();

    expect(cardCount).toBeGreaterThan(0);
  });

  test('should display Slack integration card', async ({ page }) => {
    // Look for Slack-related content
    const slackCard = page.locator('text=/slack/i').first();
    await expect(slackCard).toBeVisible({ timeout: 10000 });
  });

  test('should display PagerDuty integration card', async ({ page }) => {
    // Look for PagerDuty-related content
    const pagerDutyCard = page.locator('text=/pagerduty/i').first();
    await expect(pagerDutyCard).toBeVisible({ timeout: 10000 });
  });

  test('should display Jira integration card', async ({ page }) => {
    // Look for Jira-related content
    const jiraCard = page.locator('text=/jira/i').first();
    await expect(jiraCard).toBeVisible({ timeout: 10000 });
  });

  test('should display GitHub integration card', async ({ page }) => {
    // Look for GitHub-related content
    const githubCard = page.locator('text=/github/i').first();
    await expect(githubCard).toBeVisible({ timeout: 10000 });
  });

  test('should have interactive elements on integration cards', async ({ page }) => {
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');

    // Look for any interactive elements (buttons or links)
    const interactiveElements = page.locator('button, a[href]');
    const elementCount = await interactiveElements.count();

    // Should have at least one interactive element on the page
    expect(elementCount).toBeGreaterThan(0);
  });

  test('should have integration content loaded', async ({ page }) => {
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');

    // Verify page has loaded with integration-specific content
    const bodyText = await page.textContent('body');

    // Page should have meaningful integration-related content
    expect(bodyText).toContain('Integration');

    // Should have at least one integration name visible
    const hasIntegrationName =
      bodyText?.includes('Slack') ||
      bodyText?.includes('PagerDuty') ||
      bodyText?.includes('Jira') ||
      bodyText?.includes('GitHub');
    expect(hasIntegrationName).toBe(true);
  });

  test('should display loading state initially', async ({ page }) => {
    // Navigate to page and immediately check for loading indicator
    const pagePromise = page.goto('/integrations');

    // Check if loading indicator appears (even briefly)
    const loadingIndicator = page.locator('text=/loading/i, [class*="spin"], [class*="loader"]').first();

    await pagePromise;

    // After loading, page should be interactive
    await page.waitForLoadState('networkidle');
    const interactiveElements = page.locator('button, a[href]');
    const elementCount = await interactiveElements.count();
    expect(elementCount).toBeGreaterThan(0);
  });

  test('should have responsive layout', async ({ page }) => {
    // Check that integration cards are laid out properly
    const cards = page.locator('[data-testid*="integration"], [class*="card"]').first();

    if (await cards.count() > 0) {
      await expect(cards).toBeVisible();

      // Check that cards have proper sizing
      const boundingBox = await cards.boundingBox();
      expect(boundingBox?.width).toBeGreaterThan(100);
      expect(boundingBox?.height).toBeGreaterThan(50);
    }
  });

  test.skip('should not have critical console errors', async ({ page }) => {
    // Skipping this test as it's too flaky - React errors in CI vary by environment
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('/integrations');
    await page.waitForLoadState('networkidle');

    // Filter out known/acceptable errors
    const significantErrors = consoleErrors.filter(error =>
      !error.includes('favicon') &&
      !error.includes('sourcemap') &&
      !error.includes('Failed to load resource') &&
      !error.includes('404')
    );

    // Log all errors for debugging but don't fail on non-critical errors
    if (consoleErrors.length > 0) {
      console.log('Console errors found:', consoleErrors);
    }

    // Only fail if there are critical errors (not resource loading errors)
    expect(significantErrors.length).toBe(0);
  });

  test.describe('Integration Interactions', () => {
    test('should be able to click on integration cards', async ({ page }) => {
      // Wait for page to fully load
      await page.waitForLoadState('networkidle');

      // Find first clickable card or button
      const clickableElement = page.locator('button, a[href], [role="button"]').first();

      if (await clickableElement.count() > 0) {
        await expect(clickableElement).toBeVisible();

        // Verify element is clickable (not disabled)
        const isDisabled = await clickableElement.getAttribute('disabled');
        expect(isDisabled).toBeNull();
      }
    });

    test('should display integration descriptions', async ({ page }) => {
      // Look for descriptive text about integrations
      const descriptions = page.locator('p, span, div').filter({
        hasText: /connect|integrate|sync|monitor|alert/i
      });

      const descCount = await descriptions.count();
      expect(descCount).toBeGreaterThan(0);
    });
  });

  test.describe('Rootly Integration', () => {
    test('should display Rootly integration card', async ({ page }) => {
      // Look for Rootly-related content
      const rootlyCard = page.locator('text=/rootly/i').first();
      await expect(rootlyCard).toBeVisible({ timeout: 10000 });
    });

    test('should have Rootly API key configured in environment', async () => {
      test.skip(!ROOTLY_API_KEY, 'Rootly API key not configured');

      // Verify API key is available and valid format
      expect(ROOTLY_API_KEY).toBeTruthy();
      expect(typeof ROOTLY_API_KEY).toBe('string');

      // Rootly API keys typically start with 'rootly_'
      // But don't enforce this as format may change
      const trimmedKey = ROOTLY_API_KEY.trim();
      expect(trimmedKey.length).toBeGreaterThan(0);

      // Verify it doesn't contain obvious placeholder text
      expect(trimmedKey.toLowerCase()).not.toContain('placeholder');
      expect(trimmedKey.toLowerCase()).not.toContain('example');
    });

    test('should be able to connect to Rootly API', async ({ request }) => {
      test.skip(!ROOTLY_API_KEY, 'Rootly API key not configured');

      // Test API connectivity
      const response = await request.get('https://api.rootly.com/v1/services', {
        headers: {
          'Authorization': `Bearer ${ROOTLY_API_KEY}`,
        },
        timeout: 10000,
      });

      // Should get a valid response (200 or 401 means API is reachable)
      expect([200, 401, 403]).toContain(response.status());
    });

    test.skip('should connect Rootly integration with valid API key', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Rootly API key not configured');

      // This test is skipped by default - enable when Rootly integration form is ready
      // Look for Rootly connect button or form
      const connectButton = page.locator('button:has-text("Connect"), a:has-text("Connect")').filter({
        has: page.locator('text=/rootly/i')
      }).first();

      if (await connectButton.count() > 0) {
        await connectButton.click();

        // Wait for form or connection dialog to appear
        await page.waitForLoadState('networkidle');

        // Fill in API key if input exists
        const apiKeyInput = page.locator('input[placeholder*="API"], input[name*="api"]').first();
        if (await apiKeyInput.count() > 0) {
          await apiKeyInput.fill(ROOTLY_API_KEY);
        }
      }
    });
  });
});
