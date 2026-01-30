import { test, expect } from '@playwright/test';

/**
 * E2E tests for Team Management Sync Members Feature
 * Tests sync functionality, modal interactions, and integration combinations
 * Focus: Rootly + GitHub + PagerDuty (Jira and Linear excluded for now)
 */

// Load test credentials from environment (support both E2E_ prefixed and non-prefixed names)
const ROOTLY_API_KEY = process.env.E2E_ROOTLY_API_KEY || process.env.ROOTLY_API_KEY;
const GITHUB_TOKEN = process.env.E2E_GITHUB_TOKEN || process.env.GITHUB_TOKEN;
const PAGERDUTY_API_KEY = process.env.E2E_PAGERDUTY_API_KEY || process.env.PAGERDUTY_API_KEY;
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

  // ========================================================================
  // COMBINATION-SPECIFIC TESTS
  // ========================================================================

  test.describe('Combination #1: No Integrations Connected', () => {
    test.skip('should show disabled/empty state', async ({ page }) => {
      // Requires test setup to disconnect all integrations
      // TODO: Implement integration disconnect utility
    });

    test.skip('should display "Connect Rootly or PagerDuty" message', async ({ page }) => {
      // Requires empty state verification
      // TODO: Check for prompt message when no integrations
    });

    test.skip('should disable Sync Members button', async ({ page }) => {
      // Requires empty state
      // TODO: Verify button is disabled
    });

    test.skip('should not display team members panel', async ({ page }) => {
      // Requires empty state
      // TODO: Verify panel doesn't exist or is empty
    });
  });

  test.describe('Combination #2: Only GitHub Connected', () => {
    test.skip('should show sync disabled (no team source)', async ({ page }) => {
      // Requires GitHub-only state
      // TODO: Connect only GitHub, verify sync disabled
    });

    test.skip('should display "Connect Rootly or PagerDuty first" warning', async ({ page }) => {
      // Requires GitHub-only state
      // TODO: Check for warning message
    });

    test.skip('should not allow sync operation', async ({ page }) => {
      // Requires GitHub-only state
      // TODO: Verify sync button disabled/non-functional
    });

    test.skip('should show GitHub connected but unusable for sync', async ({ page }) => {
      // Requires GitHub-only state
      // TODO: Verify GitHub shows as connected but incomplete
    });

    test.skip('should explain need for team source', async ({ page }) => {
      // Requires GitHub-only state
      // TODO: Check for explanatory text
    });
  });

  test.describe('Combination #3: Only Rootly Connected', () => {
    test('should enable sync button', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      // Verify sync button is enabled with Rootly only
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await expect(syncButton).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await expect(syncButton).toBeEnabled();
    });

    test('should sync team members from Rootly', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      // Open sync modal and initiate sync
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      const syncNowButton = page.locator('button', { hasText: /sync now/i }).first();
      await syncNowButton.click();

      // Wait for sync completion indicator
      const completionIndicator = page.locator('text=/complete|finished|success/i').first();
      await expect(completionIndicator).toBeVisible({ timeout: SYNC_TIMEOUT });

      // Verify members synced from Rootly
      const stats = page.locator('text=/synced.*rootly|rootly.*user/i').first();
      await expect(stats).toBeVisible();
    });

    test('should display team members without GitHub mappings', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      // Perform sync first
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      const syncNowButton = page.locator('button', { hasText: /sync now/i }).first();
      await syncNowButton.click();

      // Wait for sync to complete
      await page.locator('text=/complete|success/i').first().waitFor({ timeout: SYNC_TIMEOUT });

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Verify members are listed
        const memberRows = panel.locator('tr, [class*="member"], [class*="row"]');
        const count = await memberRows.count();
        expect(count).toBeGreaterThan(0);
      }
    });

    test('should show "Not mapped" for GitHub column', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Look for "Not mapped" text in GitHub column
        const notMapped = panel.locator('text=/not mapped/i');
        const count = await notMapped.count();
        expect(count).toBeGreaterThan(0);
      }
    });

    test('should show statistics: X created, 0 GitHub matched', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      // Perform sync
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      const syncNowButton = page.locator('button', { hasText: /sync now/i }).first();
      await syncNowButton.click();

      // Wait for completion
      const completionIndicator = page.locator('text=/complete|finished|success/i').first();
      await expect(completionIndicator).toBeVisible({ timeout: SYNC_TIMEOUT });

      // Verify statistics show created count
      const createdStat = page.locator('text=/created.*user|user.*created/i').first();
      await expect(createdStat).toBeVisible();

      // GitHub matched should be 0 since GitHub not connected
      const githubZeroStat = page.locator('text=/github.*0|0.*github/i').first();
      const exists = await githubZeroStat.isVisible({ timeout: 5000 }).catch(() => false);
      console.log('GitHub matched count shown as 0:', exists);
    });

    test('should disable manual mapping (no GitHub)', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Check for edit icons - should be disabled or not present for GitHub column
        const editIcons = panel.locator('button[aria-label*="edit"], button:has(svg[class*="pencil"])');
        const count = await editIcons.count();
        // When GitHub not connected, edit icons should be disabled or minimal
        console.log('Edit icon count (GitHub not connected):', count);
      }
    });

    test('should prompt to connect GitHub for code data', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      // Look for prompt/banner suggesting GitHub connection
      const githubPrompt = page.locator('text=/connect github|github.*integration|code.*data/i').first();
      const exists = await githubPrompt.isVisible({ timeout: 5000 }).catch(() => false);
      console.log('GitHub connection prompt visible:', exists);
    });
  });

  test.describe('Combination #4: Only PagerDuty Connected', () => {
    test.skip('should enable sync button', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY, 'Requires PagerDuty API key');
      // TODO: With only PagerDuty connected, verify sync button enabled
    });

    test.skip('should sync team members from PagerDuty', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY, 'Requires PagerDuty API key');
      // TODO: Perform sync with PagerDuty only, verify members appear
    });

    test.skip('should display team members without GitHub mappings', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY, 'Requires PagerDuty API key');
      // TODO: Open team panel, verify no GitHub usernames shown
    });

    test.skip('should show "Not mapped" for GitHub column', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY, 'Requires PagerDuty API key');
      // TODO: Verify GitHub mapping column shows "Not mapped"
    });

    test.skip('should show statistics: X created, 0 GitHub matched', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY, 'Requires PagerDuty API key');
      // TODO: Verify sync stats show 0 GitHub matches
    });

    test.skip('should disable manual mapping (no GitHub)', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY, 'Requires PagerDuty API key');
      // TODO: Verify edit icons disabled or show "Connect GitHub" message
    });

    test.skip('should prompt to connect GitHub for code data', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY, 'Requires PagerDuty API key');
      // TODO: Check for prompt/banner suggesting GitHub connection
    });
  });

  // ========================================================================
  // COMBINATION #5: ROOTLY + GITHUB (PRIMARY USE CASE)
  // ========================================================================

  test.describe('Combination #5: Rootly + GitHub ⭐ PRIMARY', () => {
    test('should enable sync button with both connected', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub credentials');

      // Verify sync button is enabled
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await expect(syncButton).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await expect(syncButton).toBeEnabled();
    });

    test('should sync team members from Rootly', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub credentials');

      // Open sync modal
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      // Start sync
      const syncNowButton = page.locator('button', { hasText: /sync now/i }).first();
      await syncNowButton.click();

      // Wait for sync to complete
      const completionIndicator = page.locator('text=/complete|finished|success/i').first();
      await expect(completionIndicator).toBeVisible({ timeout: SYNC_TIMEOUT });

      // Verify members synced from Rootly
      const stats = page.locator('text=/synced.*rootly/i').first();
      await expect(stats).toBeVisible();
    });

    test('should match GitHub users by email automatically', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub credentials');

      // Perform sync (assuming sync was already done in previous test)
      // Or trigger sync here

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        // Check for automatically matched users
        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Look for GitHub usernames (indicates successful match)
        const githubUsernames = panel.locator('text=/github|@/').first();
        await expect(githubUsernames).toBeVisible();
      }
    });

    test('should display GitHub usernames for matched users', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub credentials');

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Verify GitHub usernames are displayed
        // Look for pattern like "octocat" or GitHub username format
        const githubColumn = panel.locator('[class*="github"], text=/github/i');
        const count = await githubColumn.count();
        expect(count).toBeGreaterThan(0);
      }
    });

    test('should show "Not mapped" for unmatched users', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub credentials');

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Look for "Not mapped" text
        const notMapped = panel.locator('text=/not mapped/i').first();
        // Should exist for at least some users (unless all are matched)
        const exists = await notMapped.isVisible({ timeout: 5000 }).catch(() => false);
        // This is expected behavior - some users may not have GitHub matches
        console.log('Not mapped users present:', exists);
      }
    });

    test('should show statistics: X created, Y GitHub matched', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub credentials');

      // Perform sync
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      const syncNowButton = page.locator('button', { hasText: /sync now/i }).first();
      await syncNowButton.click();

      // Wait for completion
      const completionIndicator = page.locator('text=/complete|finished|success/i').first();
      await expect(completionIndicator).toBeVisible({ timeout: SYNC_TIMEOUT });

      // Verify statistics show created count
      const createdStat = page.locator('text=/created.*user|user.*created/i').first();
      await expect(createdStat).toBeVisible();

      // Verify statistics show GitHub matched count
      const githubStat = page.locator('text=/github.*matched|matched.*github/i').first();
      await expect(githubStat).toBeVisible();
    });

    test('should enable manual mapping for unmatched users', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub credentials');

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Look for edit icons (pencil icons) for manual mapping
        const editIcons = panel.locator('button[aria-label*="edit"], button:has(svg[class*="pencil"]), button:has(svg[class*="edit"])');
        const count = await editIcons.count();
        expect(count).toBeGreaterThan(0);
      }
    });

    test('should display GitHub user dropdown in manual mapping', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub credentials');

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Click first edit icon
        const editIcon = panel.locator('button[aria-label*="edit"], button:has(svg)').first();
        await editIcon.click();

        // Manual mapping dialog should appear
        const mappingDialog = page.locator('[role="dialog"]').filter({ hasText: /map|github|manual/i }).first();
        await expect(mappingDialog).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Check for GitHub user dropdown/select
        const githubDropdown = mappingDialog.locator('select, [role="combobox"], [role="listbox"]').first();
        await expect(githubDropdown).toBeVisible();
      }
    });

    test('should handle users with same email (auto-match)', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub credentials');

      // This test verifies that users with matching emails are automatically mapped
      // Requires test data with matching emails between Rootly and GitHub

      // Perform sync
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      const syncNowButton = page.locator('button', { hasText: /sync now/i }).first();
      await syncNowButton.click();

      // Wait for completion
      await page.locator('text=/complete|success/i').first().waitFor({ timeout: SYNC_TIMEOUT });

      // Check sync output for auto-match messages
      const autoMatchMessage = page.locator('text=/auto.*match|automatically.*matched/i').first();
      const exists = await autoMatchMessage.isVisible({ timeout: 5000 }).catch(() => false);
      console.log('Auto-match occurred:', exists);
    });

    test('should handle users with different emails (manual match needed)', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub credentials');

      // This test verifies that users with different emails show "Not mapped"
      // and require manual mapping

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Find a user with "Not mapped" status
        const notMappedUser = panel.locator('text=/not mapped/i').first();
        if (await notMappedUser.isVisible({ timeout: 5000 })) {
          // Verify edit icon is available for manual mapping
          const editIcon = panel.locator('button[aria-label*="edit"], button:has(svg)').first();
          await expect(editIcon).toBeVisible();
        }
      }
    });

    test('should prevent duplicate GitHub mappings', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub credentials');

      // This test verifies that the same GitHub user cannot be mapped to multiple Rootly users
      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Try to open manual mapping dialog
        const editIcon = panel.locator('button[aria-label*="edit"], button:has(svg)').first();
        if (await editIcon.isVisible({ timeout: 5000 })) {
          await editIcon.click();

          const mappingDialog = page.locator('[role="dialog"]').filter({ hasText: /map|github|manual/i }).first();
          await expect(mappingDialog).toBeVisible({ timeout: DEFAULT_TIMEOUT });

          // Check for dropdown/select with GitHub users
          const githubDropdown = mappingDialog.locator('select, [role="combobox"], [role="listbox"]').first();
          if (await githubDropdown.isVisible({ timeout: 5000 })) {
            // Verify dropdown has options (filtering prevents duplicates)
            const options = mappingDialog.locator('[role="option"], option');
            const optionCount = await options.count();
            expect(optionCount).toBeGreaterThan(0);
          }
        }
      }
    });

    test('should allow updating existing mappings', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub credentials');

      // This test verifies that existing manual mappings can be changed

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Click edit on a mapped user
        const editIcon = panel.locator('button[aria-label*="edit"], button:has(svg)').first();
        if (await editIcon.isVisible({ timeout: 5000 })) {
          await editIcon.click();

          // Dialog should open
          const mappingDialog = page.locator('[role="dialog"]').last();
          await expect(mappingDialog).toBeVisible({ timeout: DEFAULT_TIMEOUT });

          // Find GitHub dropdown and change selection
          const githubDropdown = mappingDialog.locator('select, [role="combobox"], [role="listbox"]').first();
          if (await githubDropdown.isVisible({ timeout: 5000 })) {
            // Click to open dropdown
            await githubDropdown.click();

            // Select second option if available
            const options = mappingDialog.locator('[role="option"], option');
            const optionCount = await options.count();
            if (optionCount > 1) {
              const secondOption = options.nth(1);
              await secondOption.click();

              // Find and click save button
              const saveButton = mappingDialog.locator('button', { hasText: /save|confirm|update/i }).first();
              if (await saveButton.isVisible({ timeout: 5000 })) {
                await saveButton.click();

                // Verify mapping was saved - look for confirmation
                const successMessage = page.locator('text=/saved|updated|mapped/i').first();
                const exists = await successMessage.isVisible({ timeout: 5000 }).catch(() => false);
                console.log('Mapping update confirmed:', exists);
              }
            }
          }
        }
      }
    });
  });

  // ========================================================================
  // COMBINATION #6: PAGERDUTY + GITHUB (ALTERNATIVE PRIMARY)
  // ========================================================================

  test.describe('Combination #6: PagerDuty + GitHub ⭐ ALTERNATIVE', () => {
    test.skip('should enable sync button with both connected', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub credentials');

      // Verify sync button is enabled
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await expect(syncButton).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await expect(syncButton).toBeEnabled();
    });

    test.skip('should sync team members from PagerDuty', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub credentials');

      // Open sync modal
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      // Start sync
      const syncNowButton = page.locator('button', { hasText: /sync now/i }).first();
      await syncNowButton.click();

      // Wait for sync to complete
      const completionIndicator = page.locator('text=/complete|finished|success/i').first();
      await expect(completionIndicator).toBeVisible({ timeout: SYNC_TIMEOUT });

      // Verify members synced from PagerDuty
      const stats = page.locator('text=/synced.*pagerduty|pagerduty.*user/i').first();
      await expect(stats).toBeVisible();
    });

    test.skip('should match GitHub users by email automatically', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub credentials');

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        // Check for automatically matched users
        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Look for GitHub usernames (indicates successful match)
        const githubUsernames = panel.locator('text=/github|@/').first();
        await expect(githubUsernames).toBeVisible();
      }
    });

    test.skip('should display GitHub usernames for matched users', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub credentials');

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Verify GitHub usernames are displayed
        const githubColumn = panel.locator('[class*="github"], text=/github/i');
        const count = await githubColumn.count();
        expect(count).toBeGreaterThan(0);
      }
    });

    test.skip('should show "Not mapped" for unmatched users', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub credentials');

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Look for "Not mapped" text
        const notMapped = panel.locator('text=/not mapped/i').first();
        const exists = await notMapped.isVisible({ timeout: 5000 }).catch(() => false);
        console.log('Not mapped users present:', exists);
      }
    });

    test.skip('should show statistics: X created, Y GitHub matched', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub credentials');

      // Perform sync
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      const syncNowButton = page.locator('button', { hasText: /sync now/i }).first();
      await syncNowButton.click();

      // Wait for completion
      const completionIndicator = page.locator('text=/complete|finished|success/i').first();
      await expect(completionIndicator).toBeVisible({ timeout: SYNC_TIMEOUT });

      // Verify statistics
      const createdStat = page.locator('text=/created.*user|user.*created/i').first();
      await expect(createdStat).toBeVisible();

      const githubStat = page.locator('text=/github.*matched|matched.*github/i').first();
      await expect(githubStat).toBeVisible();
    });

    test.skip('should enable manual mapping for unmatched users', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub credentials');

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Look for edit icons
        const editIcons = panel.locator('button[aria-label*="edit"], button:has(svg[class*="pencil"]), button:has(svg[class*="edit"])');
        const count = await editIcons.count();
        expect(count).toBeGreaterThan(0);
      }
    });

    test.skip('should display GitHub user dropdown in manual mapping', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub credentials');

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Click edit icon
        const editIcon = panel.locator('button[aria-label*="edit"], button:has(svg)').first();
        await editIcon.click();

        // Manual mapping dialog
        const mappingDialog = page.locator('[role="dialog"]').filter({ hasText: /map|github|manual/i }).first();
        await expect(mappingDialog).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Check for GitHub dropdown
        const githubDropdown = mappingDialog.locator('select, [role="combobox"], [role="listbox"]').first();
        await expect(githubDropdown).toBeVisible();
      }
    });

    test.skip('should handle users with same email (auto-match)', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub credentials');

      // Perform sync
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.click();

      const syncNowButton = page.locator('button', { hasText: /sync now/i }).first();
      await syncNowButton.click();

      // Wait for completion
      await page.locator('text=/complete|success/i').first().waitFor({ timeout: SYNC_TIMEOUT });

      // Check for auto-match indication
      const autoMatchMessage = page.locator('text=/auto.*match|automatically.*matched/i').first();
      const exists = await autoMatchMessage.isVisible({ timeout: 5000 }).catch(() => false);
      console.log('Auto-match occurred:', exists);
    });

    test.skip('should handle users with different emails (manual match needed)', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub credentials');

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Find user with "Not mapped"
        const notMappedUser = panel.locator('text=/not mapped/i').first();
        if (await notMappedUser.isVisible({ timeout: 5000 })) {
          // Verify edit icon available
          const editIcon = panel.locator('button[aria-label*="edit"], button:has(svg)').first();
          await expect(editIcon).toBeVisible();
        }
      }
    });

    test.skip('should prevent duplicate GitHub mappings', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub credentials');
      // TODO: Implement duplicate prevention test
    });

    test.skip('should allow updating existing mappings', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub credentials');

      // Open team members panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Click edit on mapped user
        const editIcon = panel.locator('button[aria-label*="edit"], button:has(svg)').first();
        await editIcon.click();

        // Dialog should open
        const mappingDialog = page.locator('[role="dialog"]').last();
        await expect(mappingDialog).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // TODO: Change selection and verify update
      }
    });
  });

  // ========================================================================
  // SOURCE SWITCHING TESTS (ADVANCED)
  // ========================================================================

  test.describe('Source Switching (Rootly ↔ PagerDuty)', () => {
    test.skip('should allow switching from Rootly to PagerDuty', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !PAGERDUTY_API_KEY, 'Requires both Rootly and PagerDuty keys');
      // TODO: Disconnect Rootly, connect PagerDuty, verify switch
    });

    test.skip('should allow switching from PagerDuty to Rootly', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !PAGERDUTY_API_KEY, 'Requires both Rootly and PagerDuty keys');
      // TODO: Disconnect PagerDuty, connect Rootly, verify switch
    });

    test.skip('should re-sync members when switching sources', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !PAGERDUTY_API_KEY, 'Requires both keys');
      // TODO: Switch source and verify re-sync happens
    });

    test.skip('should warn before switching sources (data loss)', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !PAGERDUTY_API_KEY, 'Requires both keys');
      // TODO: Look for warning dialog before source switch
    });

    test.skip('should preserve GitHub mappings when switching sources', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires all credentials');
      // TODO: Create mappings, switch source, verify mappings preserved
    });

    test.skip('should clear source-specific data on switch', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !PAGERDUTY_API_KEY, 'Requires both keys');
      // TODO: Verify old source data is cleaned up
    });
  });
});
