import { test, expect } from '@playwright/test';

const DEFAULT_TIMEOUT = parseInt(process.env.E2E_TIMEOUT || '10000', 10);

// Helper to validate email format
function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

test.describe('Organization Management', () => {
  test.use({ storageState: '.auth/user.json' });

  // Setup function to navigate and open team management
  async function openTeamManagement(page: any) {
    await page.goto('/integrations');
    await page.waitForLoadState('networkidle');

    const teamManagementButton = page.getByRole('button', { name: /team|members|organization/i });
    await expect(teamManagementButton).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    await teamManagementButton.click();

    // Wait for dialog to be visible instead of arbitrary timeout
    const dialog = page.locator('[role="dialog"], [data-testid="team-dialog"]');
    await expect(dialog).toBeVisible({ timeout: DEFAULT_TIMEOUT });

    return dialog;
  }

  test('should display organization members list', async ({ page }) => {
    const dialog = await openTeamManagement(page);

    // Verify members list is visible with proper selectors
    const membersList = dialog.locator('[data-testid="members-list"], table');
    await expect(membersList).toBeVisible({ timeout: DEFAULT_TIMEOUT });

    // Verify at least one member is shown
    const memberRows = membersList.locator('tr:has(td), [data-testid="member-row"]');
    await expect(memberRows.first()).toBeVisible({ timeout: DEFAULT_TIMEOUT });

    const count = await memberRows.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should show only @oncallhealth.ai users in members list', async ({ page }) => {
    const dialog = await openTeamManagement(page);

    // Get all table cells that contain email addresses using specific selector
    const memberRows = dialog.locator('table tbody tr');
    await expect(memberRows.first()).toBeVisible({ timeout: DEFAULT_TIMEOUT });

    const rowCount = await memberRows.count();
    expect(rowCount).toBeGreaterThan(0);

    // Extract and validate all emails
    const emails: string[] = [];
    for (let i = 0; i < rowCount; i++) {
      const row = memberRows.nth(i);
      const emailCell = row.locator('td').filter({ hasText: '@' });

      if (await emailCell.count() > 0) {
        const emailText = (await emailCell.first().textContent())?.trim() || '';

        // Validate email format before checking domain
        if (isValidEmail(emailText)) {
          emails.push(emailText);
          expect(emailText.toLowerCase()).toContain('@oncallhealth.ai');
        }
      }
    }

    // Ensure we found at least one valid email
    expect(emails.length).toBeGreaterThan(0);
  });

  test('should not show users from other organizations', async ({ page }) => {
    const dialog = await openTeamManagement(page);

    // Check that these email domains are NOT present
    const forbiddenDomains = [
      '@gmail.com',
      '@kalache.fr',
      '@bigopr.com',
      '@canarytechnologies.com'
    ];

    const memberRows = dialog.locator('table tbody tr');
    await expect(memberRows.first()).toBeVisible({ timeout: DEFAULT_TIMEOUT });

    const rowCount = await memberRows.count();

    // Extract all emails and verify none match forbidden domains
    for (let i = 0; i < rowCount; i++) {
      const row = memberRows.nth(i);
      const emailCell = row.locator('td').filter({ hasText: '@' });

      if (await emailCell.count() > 0) {
        const emailText = (await emailCell.first().textContent())?.trim().toLowerCase() || '';

        if (isValidEmail(emailText)) {
          for (const domain of forbiddenDomains) {
            expect(emailText).not.toContain(domain.toLowerCase());
          }
        }
      }
    }
  });

  test('should display expected oncallhealth.ai team members', async ({ page }) => {
    const dialog = await openTeamManagement(page);

    // Expected oncallhealth.ai team members
    const expectedMembers = [
      'avery.kim@oncallhealth.ai',
      'sam.rodriguez@oncallhealth.ai',
      'ethan.hart@oncallhealth.ai',
      'anika.shah@oncallhealth.ai'
    ];

    const memberRows = dialog.locator('table tbody tr');
    await expect(memberRows.first()).toBeVisible({ timeout: DEFAULT_TIMEOUT });

    // Extract all emails from the table
    const rowCount = await memberRows.count();
    const foundEmails: string[] = [];

    for (let i = 0; i < rowCount; i++) {
      const row = memberRows.nth(i);
      const emailCell = row.locator('td').filter({ hasText: '@' });

      if (await emailCell.count() > 0) {
        const emailText = (await emailCell.first().textContent())?.trim().toLowerCase() || '';
        if (isValidEmail(emailText)) {
          foundEmails.push(emailText);
        }
      }
    }

    // Verify all expected members are present
    for (const expectedEmail of expectedMembers) {
      expect(foundEmails).toContain(expectedEmail.toLowerCase());
    }

    // Verify we found exactly the expected number of members
    expect(foundEmails.length).toBe(expectedMembers.length);
  });

  test('should not allow inviting users from other domains', async ({ page }) => {
    const dialog = await openTeamManagement(page);

    // Look for invite button
    const inviteButton = dialog.getByRole('button', { name: /invite|add member/i });

    // Skip test if invite functionality not available
    if (!await inviteButton.isVisible({ timeout: 5000 })) {
      test.skip();
      return;
    }

    await inviteButton.click();

    // Wait for invite form to appear
    const emailInput = dialog.locator('input[type="email"], input[name*="email"]').first();
    await expect(emailInput).toBeVisible({ timeout: DEFAULT_TIMEOUT });

    // Try to invite a user from wrong domain
    await emailInput.fill('wrong@gmail.com');

    // Submit the form
    const submitButton = dialog.getByRole('button', { name: /send|invite|submit/i });
    await expect(submitButton).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    await submitButton.click();

    // Verify error message appears
    const errorMessage = dialog.locator('text=/domain|organization|not allowed/i, [role="alert"]');
    await expect(errorMessage).toBeVisible({ timeout: DEFAULT_TIMEOUT });
  });
});
