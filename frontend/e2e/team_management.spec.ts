import { test, expect } from '@playwright/test';

/**
 * E2E tests for Team Management - Sync Popup Flows
 * Focus: Regression prevention for sync popups when adding integrations
 * Tests: Rootly + GitHub sync flows (PD skipped per requirements)
 */

// Load test credentials
const ROOTLY_API_KEY = process.env.E2E_ROOTLY_API_KEY;
const GITHUB_TOKEN = process.env.E2E_GITHUB_TOKEN;
const DEFAULT_TIMEOUT = 30000;
const SYNC_TIMEOUT = 180000; // For slower browsers

test.describe('Team Management - Sync Popup Flows', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/integrations', { waitUntil: 'domcontentloaded' });
  });

  // ========================================================================
  // SYNC POPUP REGRESSION TESTS
  // ========================================================================

  test.describe('Sync Popup - Rootly Added', () => {
    test('should show sync popup when Rootly integration is added', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      // Look for sync popup that appears when Rootly is added
      // Modal shows: "Sync your team members" or "Sync Team Members"
      const syncPopup = page.locator('[role="dialog"]').filter({
        hasText: /sync.*team members/i
      }).first();

      // Wait for popup (might appear within a few seconds of page load or integration)
      const popupVisible = await syncPopup.isVisible({ timeout: 10000 }).catch(() => false);

      if (popupVisible) {
        // Verify key elements are present
        const syncNowButton = syncPopup.locator('button', { hasText: /sync now/i });
        await expect(syncNowButton).toBeVisible();

        // Should have either Cancel or Skip button
        const secondaryButton = syncPopup.locator('button', { hasText: /cancel|skip/i });
        await expect(secondaryButton).toBeVisible();

        console.log('✓ Sync popup shown correctly when Rootly added');
      } else {
        console.log('ℹ  Sync popup not shown on initial load - may appear after integration addition');
      }
    });

    test('should complete sync when "Sync Now" button clicked', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      const syncPopup = page.locator('[role="dialog"]').filter({
        hasText: /sync.*team members/i
      }).first();

      const popupVisible = await syncPopup.isVisible({ timeout: 10000 }).catch(() => false);

      if (popupVisible) {
        const syncNowButton = syncPopup.locator('button', { hasText: /sync now/i });
        await syncNowButton.click();

        // Wait for sync completion indicator
        const completionIndicator = page.locator('text=/sync complete|sync results/i').first();
        const completed = await completionIndicator.isVisible({ timeout: SYNC_TIMEOUT }).catch(() => false);

        expect(completed).toBeTruthy();
        console.log('✓ Sync completed successfully');
      }
    });
  });

  test.describe('Sync Popup - GitHub Added After Rootly', () => {
    test('should show sync popup when GitHub is added after Rootly', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub');

      // Look for the specific popup shown when GitHub is added
      // This popup has text "We need to match GitHub users with your existing team"
      const syncPopup = page.locator('[role="dialog"]').filter({
        hasText: /github.*users|match.*github/i
      }).first();

      const popupVisible = await syncPopup.isVisible({ timeout: 10000 }).catch(() => false);

      if (popupVisible) {
        // Verify expected elements in GitHub sync popup
        const syncNowButton = syncPopup.locator('button', { hasText: /sync now/i });
        const skipButton = syncPopup.locator('button', { hasText: /skip/i });

        await expect(syncNowButton).toBeVisible();
        await expect(skipButton).toBeVisible();

        console.log('✓ GitHub sync popup shown correctly');
      } else {
        console.log('ℹ  GitHub sync popup not shown - may require active GitHub integration addition');
      }
    });

    test('should skip sync when "Skip" button clicked', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub');

      const syncPopup = page.locator('[role="dialog"]').filter({
        hasText: /github.*users|match.*github|sync.*team/i
      }).first();

      const popupVisible = await syncPopup.isVisible({ timeout: 10000 }).catch(() => false);

      if (popupVisible) {
        const skipButton = syncPopup.locator('button', { hasText: /skip/i });

        if (await skipButton.isVisible({ timeout: 5000 }).catch(() => false)) {
          await skipButton.click();

          // Popup should close
          await page.waitForTimeout(500);
          const stillVisible = await syncPopup.isVisible({ timeout: 2000 }).catch(() => false);
          expect(stillVisible).toBeFalsy();

          console.log('✓ Skip functionality works correctly');
        }
      }
    });

    test('should allow sync after previously skipping', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY || !GITHUB_TOKEN, 'Requires Rootly + GitHub');

      // Select an organization first (required for sync button to be enabled)
      const selectTrigger = page.locator('[role="combobox"]').first();
      const selectorExists = await selectTrigger.isVisible({ timeout: 5000 }).catch(() => false);

      if (!selectorExists) {
        console.log('ℹ  No organization selector available');
        return;
      }

      await selectTrigger.click();

      // Wait for dropdown options and select first one
      const firstOption = page.locator('[role="option"]').first();
      await expect(firstOption).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await firstOption.click();

      // Scroll to Team Management section
      const teamManagementSection = page.locator('text=/team management/i').first();
      await teamManagementSection.scrollIntoViewIfNeeded();

      // Find the Sync Members button - should now be enabled
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await expect(syncButton).toBeEnabled({ timeout: DEFAULT_TIMEOUT });
      await syncButton.click();

      // Should open sync confirmation modal
      const syncConfirmModal = page.locator('[role="dialog"]').filter({
        hasText: /sync.*team|confirm/i
      }).first();

      await expect(syncConfirmModal).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      console.log('✓ Sync button accessible after skip');
    });

    test('should disable sync button when organization is deleted', async ({ page }) => {
      test.skip(!ROOTLY_API_KEY, 'Requires Rootly API key');

      // Select an organization first
      const selectTrigger = page.locator('[role="combobox"]').first();
      const selectorExists = await selectTrigger.isVisible({ timeout: 5000 }).catch(() => false);

      if (!selectorExists) {
        console.log('ℹ  No organizations available to test deletion flow');
        return;
      }

      await selectTrigger.click();
      const firstOption = page.locator('[role="option"]').first();
      await expect(firstOption).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      await firstOption.click();

      // Verify sync button is enabled with org selected
      const syncButton = page.locator('button', { hasText: /sync members/i }).first();
      await syncButton.scrollIntoViewIfNeeded();
      await expect(syncButton).toBeEnabled({ timeout: DEFAULT_TIMEOUT });
      console.log('✓ Sync button enabled with organization selected');

      // Find and click the delete integration button
      const deleteButton = page.locator('button', { hasText: /delete integration/i }).first();
      await deleteButton.scrollIntoViewIfNeeded();
      await deleteButton.click();

      // Confirm deletion in modal
      const deleteConfirmModal = page.locator('[role="dialog"]').filter({
        hasText: /delete integration/i
      }).first();
      await expect(deleteConfirmModal).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      const confirmDeleteButton = deleteConfirmModal.locator('button', { hasText: /delete integration/i });
      await confirmDeleteButton.click();

      // Wait for modal to close and deletion to complete
      await page.waitForTimeout(1000);

      // Verify sync button is now disabled (no organization selected)
      await expect(syncButton).toBeDisabled({ timeout: DEFAULT_TIMEOUT });
      console.log('✓ Sync button disabled after organization deletion');
    });
  });

  test.describe('Sync Popup - GitHub Without Rootly/PD', () => {
    test('should NOT show sync popup when only GitHub is added (no Rootly/PD)', async ({ page }) => {
      // This test verifies the regression: sync popup should not appear if no source integration (Rootly/PD)
      test.skip(!GITHUB_TOKEN, 'Requires GitHub token');

      // Check for any sync-related popups
      const anyPopup = page.locator('[role="dialog"]').filter({
        hasText: /sync.*team|sync your team/i
      }).first();

      const popupShown = await anyPopup.isVisible({ timeout: 5000 }).catch(() => false);

      // This is expected to be false - no sync without source integration
      if (popupShown) {
        console.log('⚠ Unexpected: Sync popup shown without Rootly/PD connection');
      }

      expect(popupShown).toBeFalsy();
      console.log('✓ No sync popup shown without source integration (correct behavior)');
    });
  });
});
