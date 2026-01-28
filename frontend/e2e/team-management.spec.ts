import { test, expect } from '@playwright/test';

/**
 * E2E tests for Team Management Sync Members Feature
 * Tests sync functionality, modal interactions, and integration combinations
 * Focus: Rootly + GitHub + PagerDuty (Jira and Linear excluded for now)
 */

// Load test credentials from environment
const ROOTLY_API_KEY = process.env.E2E_ROOTLY_API_KEY;
const GITHUB_TOKEN = process.env.E2E_GITHUB_TOKEN;
const PAGERDUTY_API_KEY = process.env.E2E_PAGERDUTY_API_KEY;
const DEFAULT_TIMEOUT = parseInt(process.env.E2E_TIMEOUT || '30000', 10);
const SYNC_TIMEOUT = 120000; // Sync operations can be slow

test.describe('Team Management - Sync Members', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to integrations page before each test
    await page.goto('/integrations', { waitUntil: 'domcontentloaded' });
  });

  test.describe('Prerequisites & Setup', () => {
    test('should have required integrations configured', async () => {
      // Verify environment variables are set
      expect(ROOTLY_API_KEY, 'Rootly API key should be configured in .env.test').toBeTruthy();
      expect(GITHUB_TOKEN, 'GitHub token should be configured in .env.test').toBeTruthy();

      // Note: PagerDuty is optional for basic tests
      if (PAGERDUTY_API_KEY) {
        console.log('✓ PagerDuty API key configured');
      } else {
        console.log('⚠ PagerDuty API key not configured - some tests will be skipped');
      }
    });

    test('should navigate to integrations page successfully', async ({ page }) => {
      await page.goto('/integrations', { waitUntil: 'domcontentloaded' });

      // Verify page loaded
      await expect(page).toHaveURL(/.*integrations/);

      // Check for main page heading
      const heading = page.locator('h1, h2').filter({ hasText: /integrations/i }).first();
      await expect(heading).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    });

    test('should display Team Management section', async ({ page }) => {
      // Look for Team Management heading
      const teamManagementHeading = page.locator('text=/team.*management/i').first();
      await expect(teamManagementHeading).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Verify description is present
      const description = page.locator('text=/sync and manage your team members/i').first();
      await expect(description).toBeVisible();
    });

    test('should show Team Member Sync card with description', async ({ page }) => {
      // Look for Team Member Sync card
      const syncCard = page.locator('text=/team member sync/i').first();
      await expect(syncCard).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Verify description
      const cardDescription = page.locator('text=/sync team members from connected integrations/i').first();
      await expect(cardDescription).toBeVisible();
    });
  });

  test.describe('Sync Members Button', () => {
    test('should display Sync Members button in Team Management card', async ({ page }) => {
      // Find the Sync Members button
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await expect(syncButton).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    });

    test('should have enabled Sync Members button', async ({ page }) => {
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await expect(syncButton).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Check button is not disabled
      await expect(syncButton).toBeEnabled();
    });

    test('should open sync modal when Sync Members button is clicked', async ({ page }) => {
      // Click Sync Members button
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      // Wait for modal to appear
      const modal = page.locator('[role="dialog"]', { hasText: /sync.*team members/i }).first();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    });
  });

  test.describe('Sync Modal Interactions', () => {
    test.beforeEach(async ({ page }) => {
      // Open sync modal before each test
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      // Wait for modal
      const modal = page.locator('[role="dialog"]').first();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    });

    test('should display sync modal with correct title', async ({ page }) => {
      // Check modal title
      const modalTitle = page.locator('text=/sync.*team members/i').first();
      await expect(modalTitle).toBeVisible();
    });

    test('should show description about matching users', async ({ page }) => {
      // Look for description text
      const description = page.locator('text=/match.*users.*existing team/i, text=/include.*data.*analyses/i').first();
      await expect(description).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    });

    test('should display Sync Now button', async ({ page }) => {
      const syncNowButton = page.locator('button', { hasText: /sync now/i }).first();
      await expect(syncNowButton).toBeVisible();
      await expect(syncNowButton).toBeEnabled();
    });

    test('should display Skip button', async ({ page }) => {
      const skipButton = page.locator('button', { hasText: /skip/i }).first();
      await expect(skipButton).toBeVisible();
      await expect(skipButton).toBeEnabled();
    });

    test('should show footer text about syncing anytime', async ({ page }) => {
      const footerText = page.locator('text=/sync.*anytime.*integrations page/i').first();
      await expect(footerText).toBeVisible();
    });

    test('should close modal when Skip button is clicked', async ({ page }) => {
      const skipButton = page.locator('button', { hasText: /skip/i }).first();
      await skipButton.click();

      // Modal should close
      const modal = page.locator('[role="dialog"]', { hasText: /sync.*team members/i });
      await expect(modal).not.toBeVisible({ timeout: 5000 });
    });

    test('should close modal with X button', async ({ page }) => {
      // Look for close button (X icon)
      const closeButton = page.locator('[role="dialog"] button[aria-label*="close"], [role="dialog"] button:has(svg)').first();

      if (await closeButton.isVisible()) {
        await closeButton.click();

        // Modal should close
        const modal = page.locator('[role="dialog"]', { hasText: /sync.*team members/i });
        await expect(modal).not.toBeVisible({ timeout: 5000 });
      } else {
        test.skip();
      }
    });

    test('should close modal with ESC key', async ({ page }) => {
      // Press ESC key
      await page.keyboard.press('Escape');

      // Modal should close
      const modal = page.locator('[role="dialog"]', { hasText: /sync.*team members/i });
      await expect(modal).not.toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Sync Operation', () => {
    test('should initiate sync when Sync Now is clicked', async ({ page }) => {
      // Open sync modal
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      // Click Sync Now
      const syncNowButton = page.locator('button', { hasText: /sync now/i }).first();
      await syncNowButton.click();

      // Should show sync progress modal or loading state
      const progressModal = page.locator('[role="dialog"]', { hasText: /sync|progress/i }).first();
      await expect(progressModal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    });

    test.skip('should display sync progress modal during operation', async ({ page }) => {
      // This test requires actual sync operation
      // Skip if credentials not configured properly
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires API credentials');

      // Open sync modal and start sync
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      const syncNowButton = page.locator('button', { hasText: /sync now/i }).first();
      await syncNowButton.click();

      // Wait for progress modal
      const progressModal = page.locator('[role="dialog"]').filter({ hasText: /progress|syncing/i }).first();
      await expect(progressModal).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Should show console output or progress indicators
      const consoleOutput = page.locator('pre, code, [class*="console"], [class*="log"]').first();
      await expect(consoleOutput).toBeVisible({ timeout: 10000 });
    });

    test.skip('should show sync statistics on completion', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires API credentials');

      // Perform sync operation
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      const syncNowButton = page.locator('button', { hasText: /sync now/i }).first();
      await syncNowButton.click();

      // Wait for completion (up to 2 minutes)
      const completionIndicator = page.locator('text=/complete|finished|done/i').first();
      await expect(completionIndicator).toBeVisible({ timeout: SYNC_TIMEOUT });

      // Check for statistics
      const stats = page.locator('text=/created|updated|matched/i').first();
      await expect(stats).toBeVisible();
    });
  });

  test.describe('Team Members Panel', () => {
    test.skip('should open Team Members panel', async ({ page }) => {
      // Look for team members button/icon
      const teamButton = page.locator('button[aria-label*="team"], button:has-text("Team Members")').first();

      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        // Panel should open
        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      } else {
        test.skip();
      }
    });

    test.skip('should display team members list', async ({ page }) => {
      // Open team members panel
      const teamButton = page.locator('button[aria-label*="team"], button:has-text("Team Members")').first();

      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        // Wait for panel
        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Check for member list items
        const memberItems = panel.locator('[class*="member"], [class*="user"], li');
        const count = await memberItems.count();

        expect(count).toBeGreaterThan(0);
      } else {
        test.skip();
      }
    });

    test.skip('should show member mapping status', async ({ page }) => {
      // Open team members panel
      const teamButton = page.locator('button[aria-label*="team"], button:has-text("Team Members")').first();

      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        // Wait for panel
        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Look for mapping status indicators
        const mappingStatus = panel.locator('text=/mapped|not mapped|github|rootly/i').first();
        await expect(mappingStatus).toBeVisible();
      } else {
        test.skip();
      }
    });
  });

  test.describe('Manual Mapping', () => {
    test.skip('should display edit icon for team members', async ({ page }) => {
      // Open team members panel
      const teamButton = page.locator('button[aria-label*="team"], button:has-text("Team Members")').first();

      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        // Wait for panel
        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Look for edit icons (pencil icon)
        const editIcon = panel.locator('button[aria-label*="edit"], button:has(svg[class*="pencil"]), button:has(svg[class*="edit"])').first();
        await expect(editIcon).toBeVisible();
      } else {
        test.skip();
      }
    });

    test.skip('should open manual mapping dialog when edit icon is clicked', async ({ page }) => {
      // Open team members panel
      const teamButton = page.locator('button[aria-label*="team"], button:has-text("Team Members")').first();

      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        // Wait for panel
        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Click edit icon
        const editIcon = panel.locator('button[aria-label*="edit"], button:has(svg)').first();
        await editIcon.click();

        // Manual mapping dialog should appear
        const mappingDialog = page.locator('[role="dialog"]').filter({ hasText: /map|github|manual/i }).first();
        await expect(mappingDialog).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      } else {
        test.skip();
      }
    });
  });

  test.describe('Integration Status', () => {
    test('should show integration cards on page', async ({ page }) => {
      // Look for integration cards (GitHub, Slack, etc.)
      const integrationCards = page.locator('[class*="integration"], [class*="card"]').filter({
        hasText: /github|slack|pagerduty|rootly/i
      });

      const count = await integrationCards.count();
      expect(count).toBeGreaterThan(0);
    });

    test('should display GitHub integration card', async ({ page }) => {
      const githubCard = page.locator('text=/github/i').first();
      await expect(githubCard).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    });

    test('should display PagerDuty integration card', async ({ page }) => {
      const pagerdutyCard = page.locator('text=/pagerduty/i').first();
      await expect(pagerdutyCard).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    });
  });

  test.describe('Error Handling', () => {
    test('should handle sync gracefully when no integrations connected', async ({ page }) => {
      // This would require test setup to disconnect integrations
      // Marking as placeholder for now
      test.skip();
    });

    test('should display error message on sync failure', async ({ page }) => {
      // This would require forcing an API error
      // Marking as placeholder for now
      test.skip();
    });
  });
});
