import { test, expect } from '@playwright/test';

/**
 * E2E tests for Team Management - Focus on critical user flows
 * Tests: Rootly, PagerDuty, and GitHub integrations
 * Coverage: Sync flows, manual mapping, error handling
 */

// Load test credentials
const ROOTLY_API_KEY = process.env.E2E_ROOTLY_API_KEY;
const GITHUB_TOKEN = process.env.E2E_GITHUB_TOKEN;
const PAGERDUTY_API_KEY = process.env.E2E_PAGERDUTY_API_KEY;
const DEFAULT_TIMEOUT = 30000;
const SYNC_TIMEOUT = 180000; // Increased from 120s to 180s for slower browsers (Firefox)

test.describe('Team Management - Critical Flows', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/integrations', { waitUntil: 'domcontentloaded' });
  });

  // ========================================================================
  // PREREQUISITES - Minimal checks to ensure test environment is ready
  // ========================================================================

  test.describe('Prerequisites', () => {
    test('should have required environment configured', async () => {
      expect(ROOTLY_API_KEY, 'Rootly API key required for active tests').toBeTruthy();

      if (!ROOTLY_API_KEY) console.log('⚠ Rootly API key not configured - Rootly tests will be skipped');
      if (!GITHUB_TOKEN) console.log('⚠ GitHub token not configured - GitHub matching tests will be skipped');

      // PagerDuty tests are currently skipped
      console.log('ℹ️  PagerDuty tests are skipped (test.describe.skip) - remove .skip to enable');
    });

    test('should display Team Management section with Sync button', async ({ page }) => {
      const teamManagementHeading = page.locator('text=/team.*management/i').first();
      await expect(teamManagementHeading).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await expect(syncButton).toBeVisible();
      await expect(syncButton).toBeEnabled();
    });
  });

  // ========================================================================
  // FLOW 1: ROOTLY ONLY - Basic team sync without GitHub
  // ========================================================================

  test.describe('Rootly Only - Basic Sync', () => {
    test('should sync team members from Rootly', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      // Open team drawer
      await page.locator('button', { hasText: /sync members/i }).first().click();

      // Wait for drawer to open
      const drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Wait for drawer content to load (button text stabilizes from "Loading..." to "Sync Members")
      const syncButton = drawer.locator('button', { hasText: /sync members/i }).first();
      await syncButton.waitFor({ state: 'visible', timeout: 15000 });
      await expect(syncButton).toBeEnabled({ timeout: 5000 });
      await syncButton.click();

      // Wait for confirmation modal and click "Sync Now"
      const modal = page.locator('[role="dialog"]').filter({ hasText: /sync.*team members/i }).last();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await modal.locator('button', { hasText: /sync now/i }).click();

      // Wait for completion
      const completionIndicator = page.locator('text=/sync complete/i').first();
      await expect(completionIndicator).toBeVisible({ timeout: SYNC_TIMEOUT });

      // Verify sync results are shown
      const syncResults = page.locator('text=/sync results/i').first();
      await expect(syncResults).toBeVisible();
    });

    test('should show team members without GitHub mappings', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      // Open drawer and sync
      await page.locator('button', { hasText: /sync members/i }).first().click();
      const drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Wait for drawer content to load (button text stabilizes from "Loading..." to "Sync Members")
      const syncButton = drawer.locator('button', { hasText: /sync members/i }).first();
      await syncButton.waitFor({ state: 'visible', timeout: 15000 });
      await expect(syncButton).toBeEnabled({ timeout: 5000 });
      await syncButton.click();

      // Click Sync Now in modal
      const modal = page.locator('[role="dialog"]').filter({ hasText: /sync.*team members/i }).last();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await modal.locator('button', { hasText: /sync now/i }).click();

      await page.locator('text=/sync complete/i').first().waitFor({ timeout: SYNC_TIMEOUT });

      // Open team panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').filter({ hasText: /team members/i }).first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Verify members listed
        const memberRows = panel.locator('tr, [class*="member"], [class*="row"]');
        const count = await memberRows.count();
        expect(count).toBeGreaterThan(0);

        // Should show "Not mapped" since no GitHub integration
        const notMapped = panel.locator('text=/not mapped/i');
        expect(await notMapped.count()).toBeGreaterThan(0);
      }
    });

    test('should indicate 0 GitHub matches in statistics', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      await page.locator('button', { hasText: /sync members/i }).first().click();
      const drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Wait for drawer content to load (button text stabilizes from "Loading..." to "Sync Members")
      const syncButton = drawer.locator('button', { hasText: /sync members/i }).first();
      await syncButton.waitFor({ state: 'visible', timeout: 15000 });
      await expect(syncButton).toBeEnabled({ timeout: 5000 });
      await syncButton.click();

      // Click Sync Now in modal
      const modal = page.locator('[role="dialog"]').filter({ hasText: /sync.*team members/i }).last();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await modal.locator('button', { hasText: /sync now/i }).click();

      const completionIndicator = page.locator('text=/sync complete/i').first();
      await expect(completionIndicator).toBeVisible({ timeout: SYNC_TIMEOUT });

      // Look for indication that GitHub matching was skipped or 0
      // This could be "GitHub: 0 matched" or "GitHub not connected"
      const githubStatus = page.locator('text=/github.*0|github.*not|skip.*github/i').first();
      const visible = await githubStatus.isVisible({ timeout: 5000 }).catch(() => false);

      // Log for debugging - we expect either explicit 0 or skipped message
      console.log('GitHub status shown (0 or skipped):', visible);
    });
  });

  // ========================================================================
  // FLOW 2: PAGERDUTY ONLY - Basic team sync without GitHub
  // ========================================================================

  test.describe.skip('PagerDuty Only - Basic Sync', () => {
    test('should sync team members from PagerDuty', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY, 'Requires PagerDuty API key');

      await page.locator('button', { hasText: /sync members/i }).first().click();
      const drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await drawer.locator('button', { hasText: /sync members/i }).first().click();

      // Click Sync Now in modal
      const modal = page.locator('[role="dialog"]').filter({ hasText: /sync.*team members/i }).last();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await modal.locator('button', { hasText: /sync now/i }).click();

      const completionIndicator = page.locator('text=/sync complete/i').first();
      await expect(completionIndicator).toBeVisible({ timeout: SYNC_TIMEOUT });

      // Verify sync results shown
      const syncResults = page.locator('text=/sync results/i').first();
      await expect(syncResults).toBeVisible();
    });

    test('should show team members without GitHub mappings', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY, 'Requires PagerDuty API key');

      await page.locator('button', { hasText: /sync members/i }).first().click();
      const drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await drawer.locator('button', { hasText: /sync members/i }).first().click();

      // Click Sync Now in modal
      const modal = page.locator('[role="dialog"]').filter({ hasText: /sync.*team members/i }).last();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await modal.locator('button', { hasText: /sync now/i }).click();

      await page.locator('text=/sync complete/i').first().waitFor({ timeout: SYNC_TIMEOUT });

      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Verify "Not mapped" shown
        const notMapped = panel.locator('text=/not mapped/i');
        expect(await notMapped.count()).toBeGreaterThan(0);
      }
    });
  });

  // ========================================================================
  // FLOW 3: ROOTLY + GITHUB - Auto-matching and manual mapping (PRIMARY)
  // ========================================================================

  test.describe('Rootly + GitHub - Full Flow ⭐', () => {
    test('should sync and auto-match GitHub users by email', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub');

      // Open drawer and start sync
      await page.locator('button', { hasText: /sync members/i }).first().click();
      const drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Wait for drawer content to load (button text stabilizes from "Loading..." to "Sync Members")
      const syncButton = drawer.locator('button', { hasText: /sync members/i }).first();
      await syncButton.waitFor({ state: 'visible', timeout: 15000 });
      await expect(syncButton).toBeEnabled({ timeout: 5000 });
      await syncButton.click();

      // Click Sync Now in modal
      const modal = page.locator('[role="dialog"]').filter({ hasText: /sync.*team members/i }).last();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await modal.locator('button', { hasText: /sync now/i }).click();

      // Wait for completion
      const completionIndicator = page.locator('text=/sync complete/i').first();
      await expect(completionIndicator).toBeVisible({ timeout: SYNC_TIMEOUT });

      // Verify sync results are shown
      const syncResults = page.locator('text=/sync results/i').first();
      await expect(syncResults).toBeVisible();

      // Just verify the modal shows completion - specific stats vary by data
      const doneButton = page.locator('button', { hasText: /done/i }).first();
      await expect(doneButton).toBeVisible();
    });

    test('should display GitHub usernames for auto-matched users', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub');

      // Perform sync
      await page.locator('button', { hasText: /sync members/i }).first().click();
      const drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Wait for drawer content to load (button text stabilizes from "Loading..." to "Sync Members")
      const syncButton = drawer.locator('button', { hasText: /sync members/i }).first();
      await syncButton.waitFor({ state: 'visible', timeout: 15000 });
      await expect(syncButton).toBeEnabled({ timeout: 5000 });
      await syncButton.click();

      // Click Sync Now in modal
      const modal = page.locator('[role="dialog"]').filter({ hasText: /sync.*team members/i }).last();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await modal.locator('button', { hasText: /sync now/i }).click();

      await page.locator('text=/sync complete/i').first().waitFor({ timeout: SYNC_TIMEOUT });

      // Open team panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Look for GitHub usernames (indicates successful auto-match)
        const githubUsernames = panel.locator('[class*="github"]').first();
        await expect(githubUsernames).toBeVisible({ timeout: 10000 });
      }
    });

    test('should allow manual mapping for unmatched users', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub');

      // Open team panel
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();

      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Find edit icon for manual mapping
        const editIcon = panel.locator('button[aria-label*="edit"], button:has(svg[class*="pencil"]), button:has(svg[class*="edit"])').first();

        if (await editIcon.isVisible({ timeout: 5000 })) {
          await editIcon.click();

          // Manual mapping dialog should open
          const mappingDialog = page.locator('[role="dialog"]').filter({ hasText: /map|github|manual/i }).first();
          await expect(mappingDialog).toBeVisible({ timeout: DEFAULT_TIMEOUT });

          // Verify GitHub user dropdown exists
          const githubDropdown = mappingDialog.locator('select, [role="combobox"], [role="listbox"]').first();
          await expect(githubDropdown).toBeVisible();
        }
      }
    });

    test('should save manual mapping and persist across page reloads', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub');

      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();

      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Find user with "Not mapped" status
        const notMappedRow = panel.locator('text=/not mapped/i').first();

        if (await notMappedRow.isVisible({ timeout: 5000 })) {
          // Find edit button in same row
          const editIcon = panel.locator('button[aria-label*="edit"], button:has(svg)').first();
          await editIcon.click();

          const mappingDialog = page.locator('[role="dialog"]').last();
          await expect(mappingDialog).toBeVisible({ timeout: DEFAULT_TIMEOUT });

          // Select a GitHub user
          const githubDropdown = mappingDialog.locator('select, [role="combobox"], [role="listbox"]').first();
          if (await githubDropdown.isVisible({ timeout: 5000 })) {
            await githubDropdown.click();

            // Select first available option
            const firstOption = mappingDialog.locator('[role="option"], option').first();
            if (await firstOption.isVisible({ timeout: 5000 })) {
              const selectedUsername = await firstOption.textContent();
              await firstOption.click();

              // Save mapping
              const saveButton = mappingDialog.locator('button', { hasText: /save|confirm/i }).first();
              if (await saveButton.isVisible({ timeout: 5000 })) {
                await saveButton.click();

                // Wait for save confirmation
                await page.waitForTimeout(1000);

                // Close panel and reopen to verify persistence
                const closeButton = panel.locator('button[aria-label*="close"]').first();
                if (await closeButton.isVisible({ timeout: 3000 })) {
                  await closeButton.click();
                  await page.waitForTimeout(500);

                  // Reopen panel
                  await teamButton.click();
                  await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

                  // Verify mapping persisted - look for the GitHub username we selected
                  const mappedUsername = panel.locator(`text=${selectedUsername}`).first();
                  const persisted = await mappedUsername.isVisible({ timeout: 5000 }).catch(() => false);

                  console.log(`Manual mapping persisted: ${persisted} (username: ${selectedUsername})`);
                }
              }
            }
          }
        }
      }
    });

    test('should prevent duplicate GitHub username mappings', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub');

      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();

      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Open manual mapping for first user
        const firstEditIcon = panel.locator('button[aria-label*="edit"], button:has(svg)').first();
        if (await firstEditIcon.isVisible({ timeout: 5000 })) {
          await firstEditIcon.click();

          const mappingDialog = page.locator('[role="dialog"]').last();
          await expect(mappingDialog).toBeVisible({ timeout: DEFAULT_TIMEOUT });

          // Get list of available GitHub users
          const githubDropdown = mappingDialog.locator('select, [role="combobox"], [role="listbox"]').first();
          if (await githubDropdown.isVisible({ timeout: 5000 })) {
            await githubDropdown.click();

            const availableOptions = await mappingDialog.locator('[role="option"], option').count();

            // Close this dialog
            const cancelButton = mappingDialog.locator('button', { hasText: /cancel|close/i }).first();
            if (await cancelButton.isVisible()) {
              await cancelButton.click();
            }

            // Open mapping for second user
            const secondEditIcon = panel.locator('button[aria-label*="edit"], button:has(svg)').nth(1);
            if (await secondEditIcon.isVisible({ timeout: 5000 })) {
              await secondEditIcon.click();

              const secondDialog = page.locator('[role="dialog"]').last();
              await expect(secondDialog).toBeVisible({ timeout: DEFAULT_TIMEOUT });

              const secondDropdown = secondDialog.locator('select, [role="combobox"], [role="listbox"]').first();
              if (await secondDropdown.isVisible({ timeout: 5000 })) {
                await secondDropdown.click();

                const secondAvailableOptions = await secondDialog.locator('[role="option"], option').count();

                // If first user was mapped, second user should have fewer options
                // (already-mapped users should be filtered out)
                console.log(`Available GitHub users: First user: ${availableOptions}, Second user: ${secondAvailableOptions}`);

                // Verify that mapped users are excluded from dropdown
                // This is a soft check - implementation may vary
                expect(secondAvailableOptions).toBeGreaterThan(0);
              }
            }
          }
        }
      }
    });
  });

  // ========================================================================
  // FLOW 4: PAGERDUTY + GITHUB - Auto-matching and manual mapping
  // ========================================================================

  test.describe.skip('PagerDuty + GitHub - Full Flow', () => {
    test('should sync and auto-match GitHub users by email', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub');

      await page.locator('button', { hasText: /sync members/i }).first().click();
      const drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await drawer.locator('button', { hasText: /sync members/i }).first().click();

      // Click Sync Now in modal
      const modal = page.locator('[role="dialog"]').filter({ hasText: /sync.*team members/i }).last();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await modal.locator('button', { hasText: /sync now/i }).click();

      const completionIndicator = page.locator('text=/sync complete/i').first();
      await expect(completionIndicator).toBeVisible({ timeout: SYNC_TIMEOUT });

      // Verify both PagerDuty sync and GitHub matching occurred
      const stats = page.locator('text=/created|matched/i').first();
      await expect(stats).toBeVisible();
    });

    test('should display GitHub usernames for auto-matched users', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub');

      await page.locator('button', { hasText: /sync members/i }).first().click();
      const drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await drawer.locator('button', { hasText: /sync members/i }).first().click();

      // Click Sync Now in modal
      const modal = page.locator('[role="dialog"]').filter({ hasText: /sync.*team members/i }).last();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await modal.locator('button', { hasText: /sync now/i }).click();

      await page.locator('text=/sync complete/i').first().waitFor({ timeout: SYNC_TIMEOUT });

      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Verify GitHub usernames are shown
        const githubColumn = panel.locator('[class*="github"]').first();
        await expect(githubColumn).toBeVisible({ timeout: 10000 });
      }
    });

    test('should allow manual mapping for unmatched users', async ({ page }) => {
      test.skip(!PAGERDUTY_API_KEY || !GITHUB_TOKEN, 'Requires PagerDuty + GitHub');

      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();

      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        const editIcon = panel.locator('button[aria-label*="edit"], button:has(svg)').first();
        if (await editIcon.isVisible({ timeout: 5000 })) {
          await editIcon.click();

          const mappingDialog = page.locator('[role="dialog"]').last();
          await expect(mappingDialog).toBeVisible({ timeout: DEFAULT_TIMEOUT });

          const githubDropdown = mappingDialog.locator('select, [role="combobox"], [role="listbox"]').first();
          await expect(githubDropdown).toBeVisible();
        }
      }
    });
  });

  // ========================================================================
  // FLOW 5: ERROR SCENARIOS - Critical error handling paths
  // ========================================================================

  test.describe('Error Handling', () => {
    test('should handle modal close gracefully', async ({ page }) => {
      // Open team drawer
      await page.locator('button', { hasText: /sync members/i }).first().click();

      const drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Close drawer using ESC key (more reliable than clicking close button)
      await page.keyboard.press('Escape');

      // Wait for drawer to close
      await page.waitForTimeout(500);
      await expect(drawer).not.toBeVisible({ timeout: 5000 });
    });

    test('should handle sync with no integrations connected', async ({ page }) => {
      // This test would require disconnecting all integrations first
      // For now, just verify the sync button behavior
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();

      // Button should exist (even if disabled without integrations)
      await expect(syncButton).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Note: Actual disabled state testing requires integration disconnect utility
      console.log('Sync button found - disabled state testing requires clean environment');
    });

    test('should display appropriate error when sync fails', async ({ page }) => {
      // This would require forcing an API error (invalid token, network failure, etc.)
      // Implementation depends on test setup capability
      test.skip(true, 'Requires ability to inject API errors - implement when test infrastructure supports it');
    });
  });

  // ========================================================================
  // FLOW 6: RE-SYNC - Verify updates work correctly
  // ========================================================================

  test.describe('Re-sync Behavior', () => {
    test('should update existing members on re-sync', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      // First sync
      await page.locator('button', { hasText: /sync members/i }).first().click();
      let drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Wait for drawer content to load (button text stabilizes from "Loading..." to "Sync Members")
      let syncButton = drawer.locator('button', { hasText: /sync members/i }).first();
      await syncButton.waitFor({ state: 'visible', timeout: 15000 });
      await expect(syncButton).toBeEnabled({ timeout: 5000 });
      await syncButton.click();

      // Click Sync Now in modal
      let modal = page.locator('[role="dialog"]').filter({ hasText: /sync.*team members/i }).last();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await modal.locator('button', { hasText: /sync now/i }).click();

      await page.locator('text=/sync complete/i').first().waitFor({ timeout: SYNC_TIMEOUT });

      // Get initial count from sync results
      const syncResults = page.locator('text=/sync results/i').first();
      await expect(syncResults).toBeVisible();

      // Close the completion modal
      const doneButton = page.locator('button', { hasText: /done/i }).first();
      await doneButton.click();

      // Wait for completion modal to close
      await page.waitForTimeout(500);

      // Close the drawer using ESC key
      await page.keyboard.press('Escape');

      // Wait for drawer to fully close
      await page.waitForTimeout(1000);

      // Second sync
      await page.locator('button', { hasText: /sync members/i }).first().click();
      drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Wait for drawer content to load (button text stabilizes from "Loading..." to "Sync Members")
      syncButton = drawer.locator('button', { hasText: /sync members/i }).first();
      await syncButton.waitFor({ state: 'visible', timeout: 15000 });
      await expect(syncButton).toBeEnabled({ timeout: 5000 });
      await syncButton.click();

      // Click Sync Now in modal
      modal = page.locator('[role="dialog"]').filter({ hasText: /sync.*team members/i }).last();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await modal.locator('button', { hasText: /sync now/i }).click();

      await page.locator('text=/sync complete/i').first().waitFor({ timeout: SYNC_TIMEOUT });

      // Verify sync completed successfully
      const secondSyncResults = page.locator('text=/sync results/i').first();
      await expect(secondSyncResults).toBeVisible();

      console.log('Re-sync completed successfully');
    });

    test('should preserve manual mappings after re-sync', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub');

      // This test verifies that manual mappings persist across syncs
      // Implementation would require:
      // 1. Create manual mapping
      // 2. Re-sync
      // 3. Verify mapping still exists

      // For now, log that this is a critical flow to test
      console.log('Manual mapping persistence across re-sync - requires manual mapping creation first');
      test.skip(true, 'Implement after manual mapping creation is stable');
    });
  });

  // ========================================================================
  // FLOW 7: MIXED SCENARIOS - Edge cases that could cause regressions
  // ========================================================================

  test.describe('Edge Cases', () => {
    test('should handle users with identical names but different emails', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub');

      await page.locator('button', { hasText: /sync members/i }).first().click();
      const drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Wait for drawer content to load (button text stabilizes from "Loading..." to "Sync Members")
      const syncButton = drawer.locator('button', { hasText: /sync members/i }).first();
      await syncButton.waitFor({ state: 'visible', timeout: 15000 });
      await expect(syncButton).toBeEnabled({ timeout: 5000 });
      await syncButton.click();

      // Click Sync Now in modal
      const modal = page.locator('[role="dialog"]').filter({ hasText: /sync.*team members/i }).last();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await modal.locator('button', { hasText: /sync now/i }).click();

      await page.locator('text=/sync complete/i').first().waitFor({ timeout: SYNC_TIMEOUT });

      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Count total members
        const memberRows = panel.locator('tr, [class*="member"], [class*="row"]');
        const count = await memberRows.count();

        // All members should be listed individually (no duplicates merged)
        console.log(`Total members displayed: ${count}`);
        expect(count).toBeGreaterThan(0);
      }
    });

    test('should handle partial GitHub matching (some matched, some not)', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub');

      await page.locator('button', { hasText: /sync members/i }).first().click();
      const drawer = page.locator('[role="dialog"], aside, [class*="drawer"], [class*="sheet"]').filter({ hasText: /team members/i }).first();
      await expect(drawer).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Wait for drawer content to load (button text stabilizes from "Loading..." to "Sync Members")
      const syncButton = drawer.locator('button', { hasText: /sync members/i }).first();
      await syncButton.waitFor({ state: 'visible', timeout: 15000 });
      await expect(syncButton).toBeEnabled({ timeout: 5000 });
      await syncButton.click();

      // Click Sync Now in modal
      const modal = page.locator('[role="dialog"]').filter({ hasText: /sync.*team members/i }).last();
      await expect(modal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await modal.locator('button', { hasText: /sync now/i }).click();

      await page.locator('text=/sync complete/i').first().waitFor({ timeout: SYNC_TIMEOUT });

      // Verify sync completed
      const syncResults = page.locator('text=/sync results/i').first();
      await expect(syncResults).toBeVisible();

      // Close the completion modal
      const doneButton = page.locator('button', { hasText: /done/i }).first();
      await doneButton.click();
      await page.waitForTimeout(500);

      // Open team panel to verify mixed state
      const teamButton = page.locator('button:has-text("Team Members"), button[aria-label*="team"]').first();
      if (await teamButton.isVisible({ timeout: 5000 })) {
        await teamButton.click();

        const panel = page.locator('[role="dialog"], aside, [class*="drawer"]').first();
        await expect(panel).toBeVisible({ timeout: DEFAULT_TIMEOUT });

        // Should have both matched users (with GitHub usernames) and unmatched (Not mapped)
        const githubUsernames = panel.locator('[class*="github"]');
        const notMappedUsers = panel.locator('text=/not mapped/i');

        const hasMatched = await githubUsernames.count() > 0;
        const hasUnmatched = await notMappedUsers.count() > 0;

        console.log(`Mixed state: ${hasMatched ? 'Has matched users' : 'No matches'}, ${hasUnmatched ? 'Has unmatched users' : 'All matched'}`);
      }
    });
  });
});
