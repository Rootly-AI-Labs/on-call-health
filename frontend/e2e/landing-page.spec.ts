import { test, expect } from '@playwright/test';

test.describe('Landing Page', () => {
  test('should load and display main heading', async ({ page }) => {
    await page.goto('/');

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Check that the main heading is visible
    await expect(page.locator('h1')).toBeVisible();
  });

  test('should have working navigation', async ({ page }) => {
    await page.goto('/');

    // Check for navigation elements (adjust selectors based on your actual nav)
    const nav = page.locator('nav');
    await expect(nav).toBeVisible();
  });

  test('should display call-to-action buttons', async ({ page }) => {
    await page.goto('/');

    // Look for CTA buttons (adjust text based on your actual buttons)
    const buttons = page.locator('button, a[role="button"]');
    await expect(buttons.first()).toBeVisible();
  });
});
