import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should show login page', async ({ page }) => {
    await page.goto('/auth/login');

    // Wait for page to fully load
    await page.waitForLoadState('networkidle');

    // Check for login form elements with descriptive error messages
    const form = page.locator('form').first();
    await expect(form, 'Login form should be visible on /auth/login page').toBeVisible();

    // Verify form has essential elements
    const inputs = form.locator('input');
    const inputCount = await inputs.count();
    expect(inputCount, 'Login form should have at least one input field').toBeGreaterThan(0);
  });

  test('should validate required fields', async ({ page }) => {
    await page.goto('/auth/login');
    await page.waitForLoadState('networkidle');

    // Try to submit empty form
    const submitButton = page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Login")').first();
    await expect(submitButton, 'Submit button should exist on login form').toBeVisible();

    await submitButton.click();

    // Wait a bit for validation to trigger
    await page.waitForTimeout(500);

    // Should still be on login page (validation prevented submission)
    await expect(page, 'Should remain on login page after invalid submission').toHaveURL(/.*auth\/login.*/);
  });

  // Add more auth tests as needed:
  // - test('should login with valid credentials')
  // - test('should show error with invalid credentials')
  // - test('should redirect to dashboard after login')
});
