import { test, expect } from '@playwright/test';

const DEFAULT_TIMEOUT = parseInt(process.env.E2E_TIMEOUT || '10000', 10);

// Helper to validate email format
function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

test.describe('Organization Management', () => {
  // Setup function to navigate and open team management
  async function openTeamManagement(page: any) {
    await page.goto('/integrations');
    await page.waitForLoadState('networkidle');

    // Check if organization selector exists (requires at least one integration)
    const orgSelector = page.locator('select, [role="combobox"]').first();
    const selectorExists = await orgSelector.isVisible({ timeout: DEFAULT_TIMEOUT }).catch(() => false);

    if (!selectorExists) {
      // No integrations configured - skip test
      return null;
    }

    // Select the first available organization if none is selected
    const selectTrigger = page.locator('[role="combobox"]').first();
    await selectTrigger.click();

    // Wait for dropdown options and select first one
    const firstOption = page.locator('[role="option"]').first();
    await expect(firstOption).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    await firstOption.click();

    // Now click the Team button (should be enabled after org selection)
    const teamManagementButton = page.getByRole('button', { name: /team/i });
    await expect(teamManagementButton).toBeEnabled({ timeout: DEFAULT_TIMEOUT });
    await teamManagementButton.click();

    // Wait for dialog to be visible instead of arbitrary timeout
    const dialog = page.locator('[role="dialog"], [data-testid="team-dialog"]');
    await expect(dialog).toBeVisible({ timeout: DEFAULT_TIMEOUT });

    return dialog;
  }

  // Helper to extract all emails from table efficiently
  async function extractEmailsFromTable(dialog: any): Promise<string[]> {
    const memberRows = dialog.locator('table tbody tr');
    await expect(memberRows.first()).toBeVisible({ timeout: DEFAULT_TIMEOUT });

    const rowCount = await memberRows.count();
    const emails: string[] = [];

    for (let i = 0; i < rowCount; i++) {
      const row = memberRows.nth(i);
      // Get all text content from the row and extract emails
      const rowText = await row.textContent();
      if (rowText) {
        // Find emails using regex in the full row text
        const emailMatches = rowText.match(/\b[^\s@]+@[^\s@]+\.[^\s@]+\b/g);
        if (emailMatches) {
          for (const email of emailMatches) {
            if (isValidEmail(email)) {
              emails.push(email.toLowerCase());
            }
          }
        }
      }
    }

    return emails;
  }

  test('should display organization members list', async ({ page }) => {
    const dialog = await openTeamManagement(page);
    if (!dialog) {
      test.skip(true, 'No integrations configured - organization selector not available');
    }

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
    if (!dialog) {
      test.skip(true, 'No integrations configured - organization selector not available');
      return;
    }

    const emails = await extractEmailsFromTable(dialog);

    // Ensure we found at least one valid email
    expect(emails.length).toBeGreaterThan(0);

    // Verify all emails are from oncallhealth.ai domain
    for (const email of emails) {
      expect(email).toContain('@oncallhealth.ai');
    }
  });

  test('should not show users from other organizations', async ({ page }) => {
    const dialog = await openTeamManagement(page);
    if (!dialog) {
      test.skip(true, 'No integrations configured - organization selector not available');
      return;
    }

    // Check that these email domains are NOT present
    const forbiddenDomains = [
      '@gmail.com',
      '@kalache.fr',
      '@bigopr.com',
      '@canarytechnologies.com'
    ];

    const emails = await extractEmailsFromTable(dialog);

    // Verify none of the emails match forbidden domains
    for (const email of emails) {
      for (const domain of forbiddenDomains) {
        expect(email).not.toContain(domain.toLowerCase());
      }
    }
  });

  test('should display at least one oncallhealth.ai team member with valid data', async ({ page }) => {
    const dialog = await openTeamManagement(page);
    if (!dialog) {
      test.skip(true, 'No integrations configured - organization selector not available');
      return;
    }

    const emails = await extractEmailsFromTable(dialog);

    // Verify we have at least one member
    expect(emails.length).toBeGreaterThan(0);

    // Verify all members have valid oncallhealth.ai emails
    for (const email of emails) {
      expect(email).toMatch(/@oncallhealth\.ai$/);
      expect(isValidEmail(email)).toBe(true);
    }

    // Log found members for debugging (won't fail test)
    console.log(`Found ${emails.length} team members:`, emails);
  });

  test('should not allow inviting users from other domains', async ({ page }) => {
    const dialog = await openTeamManagement(page);
    if (!dialog) {
      test.skip(true, 'No integrations configured - organization selector not available');
      return;
    }

    // Look for invite button
    const inviteButton = dialog.getByRole('button', { name: /invite|add member/i });

    // Skip test if invite functionality not available
    if (!await inviteButton.isVisible({ timeout: DEFAULT_TIMEOUT })) {
      test.skip(true, 'Invite functionality not available');
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
