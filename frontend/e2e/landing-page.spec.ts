import { test, expect } from '@playwright/test';

test.describe('Landing Page', () => {
  test('should load and display main heading', async ({ page }) => {
    await page.goto('/');

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Check that the main heading is visible
    const heading = page.locator('h1').first();
    await expect(heading, 'Main heading should be visible on landing page').toBeVisible();

    // Verify heading has content
    const headingText = await heading.textContent();
    expect(headingText, 'Main heading should contain text').toBeTruthy();
  });

  test('should have working navigation', async ({ page }) => {
    await page.goto('/');

    // Check for navigation elements with more specific selector
    const nav = page.locator('nav, [role="navigation"]').first();
    await expect(nav, 'Navigation should be visible on landing page').toBeVisible();

    // Verify nav has links
    const navLinks = nav.locator('a');
    const linkCount = await navLinks.count();
    expect(linkCount, 'Navigation should contain at least one link').toBeGreaterThan(0);
  });

  test('should display call-to-action buttons', async ({ page }) => {
    await page.goto('/');

    // Look for CTA buttons with better selectors
    const buttons = page.locator('button, a[role="button"], a.btn, button.btn');
    const buttonCount = await buttons.count();

    expect(buttonCount, 'Landing page should have at least one CTA button').toBeGreaterThan(0);

    // Check first button is visible and has content
    const firstButton = buttons.first();
    await expect(firstButton, 'First CTA button should be visible').toBeVisible();

    const buttonText = await firstButton.textContent();
    expect(buttonText?.trim(), 'CTA button should have text content').toBeTruthy();
  });
});
