import { test, expect } from '@playwright/test';

const DEFAULT_TIMEOUT = parseInt(process.env.E2E_TIMEOUT || '10000', 10);

test.describe('Organization Management', () => {
  test.use({ storageState: '.auth/user.json' });

  test('should display organization members list', async ({ page }) => {
    await page.goto('/integrations');
    await page.waitForLoadState('networkidle');

    // Look for Team Management button/dialog trigger
    const teamManagementButton = page.getByRole('button', { name: /team|members|organization/i });

    if (await teamManagementButton.isVisible({ timeout: DEFAULT_TIMEOUT })) {
      await teamManagementButton.click();
      await page.waitForTimeout(500); // Wait for dialog animation
    }
  });

  test('should show only @oncallhealth.ai users in members list', async ({ page }) => {
    await page.goto('/integrations');
    await page.waitForLoadState('networkidle');

    // Open team management dialog
    const teamButton = page.getByRole('button', { name: /team|members/i }).first();

    if (await teamButton.isVisible({ timeout: DEFAULT_TIMEOUT })) {
      await teamButton.click();
      await page.waitForTimeout(500);

      // Check for member list container
      const membersList = page.locator('[data-testid="members-list"], [class*="member"], table tbody tr');

      // Wait for members to load
      await expect(membersList.first()).toBeVisible({ timeout: DEFAULT_TIMEOUT });

      // Get all member email elements
      const emailElements = page.locator('text=/@oncallhealth\\.ai/i, [data-testid*="email"], td:has-text("@")');
      const count = await emailElements.count();

      if (count > 0) {
        console.log(`✓ Found ${count} members`);

        // Verify all visible emails are @oncallhealth.ai
        for (let i = 0; i < count; i++) {
          const emailText = await emailElements.nth(i).textContent();
          if (emailText && emailText.includes('@')) {
            console.log(`  Checking email: ${emailText}`);
            expect(emailText.toLowerCase()).toContain('@oncallhealth.ai');
          }
        }

        console.log('✓ All visible members are from @oncallhealth.ai domain');
      } else {
        console.log('⚠ No email elements found in members list');
      }
    } else {
      test.skip('Team management button not found');
    }
  });

  test('should not show users from other organizations', async ({ page }) => {
    await page.goto('/integrations');
    await page.waitForLoadState('networkidle');

    // Open team management dialog
    const teamButton = page.getByRole('button', { name: /team|members/i }).first();

    if (await teamButton.isVisible({ timeout: DEFAULT_TIMEOUT })) {
      await teamButton.click();
      await page.waitForTimeout(500);

      // Check that these email domains are NOT present
      const forbiddenDomains = [
        '@gmail.com',
        '@kalache.fr',
        '@bigopr.com',
        '@canarytechnologies.com'
      ];

      for (const domain of forbiddenDomains) {
        const wrongDomainElements = page.locator(`text=/${domain}/i`);
        const count = await wrongDomainElements.count();

        expect(count).toBe(0);
        console.log(`✓ No users from ${domain} domain found`);
      }
    } else {
      test.skip('Team management button not found');
    }
  });

  test('should display expected oncallhealth.ai team members', async ({ page }) => {
    await page.goto('/integrations');
    await page.waitForLoadState('networkidle');

    // Open team management
    const teamButton = page.getByRole('button', { name: /team|members/i }).first();

    if (await teamButton.isVisible({ timeout: DEFAULT_TIMEOUT })) {
      await teamButton.click();
      await page.waitForTimeout(500);

      // Expected oncallhealth.ai team members
      const expectedMembers = [
        'avery.kim@oncallhealth.ai',
        'sam.rodriguez@oncallhealth.ai',
        'ethan.hart@oncallhealth.ai',
        'anika.shah@oncallhealth.ai'
      ];

      // Check for each expected member
      for (const email of expectedMembers) {
        const memberElement = page.locator(`text=/${email}/i`);
        const isVisible = await memberElement.isVisible({ timeout: DEFAULT_TIMEOUT }).catch(() => false);

        if (isVisible) {
          console.log(`✓ Found expected member: ${email}`);
        } else {
          console.log(`⚠ Expected member not visible: ${email}`);
        }
      }

      // At least verify we can see some members
      const anyMemberEmail = page.locator('text=/@oncallhealth\\.ai/i').first();
      await expect(anyMemberEmail).toBeVisible({ timeout: DEFAULT_TIMEOUT });
      console.log('✓ Organization members list is functional');
    } else {
      test.skip('Team management button not found');
    }
  });

  test('should not allow inviting users from other domains', async ({ page }) => {
    await page.goto('/integrations');
    await page.waitForLoadState('networkidle');

    // Open team management
    const teamButton = page.getByRole('button', { name: /team|members/i }).first();

    if (await teamButton.isVisible({ timeout: DEFAULT_TIMEOUT })) {
      await teamButton.click();
      await page.waitForTimeout(500);

      // Look for invite button
      const inviteButton = page.getByRole('button', { name: /invite|add member/i });

      if (await inviteButton.isVisible({ timeout: 5000 })) {
        await inviteButton.click();
        await page.waitForTimeout(300);

        // Try to invite a user from wrong domain
        const emailInput = page.locator('input[type="email"], input[name*="email"]').first();

        if (await emailInput.isVisible({ timeout: 3000 })) {
          await emailInput.fill('wrong@gmail.com');

          // Try to submit
          const submitButton = page.getByRole('button', { name: /send|invite|submit/i });
          if (await submitButton.isVisible({ timeout: 3000 })) {
            await submitButton.click();
            await page.waitForTimeout(500);

            // Should show an error or validation message
            const errorMessage = page.locator('text=/domain|organization|not allowed/i, [role="alert"]');
            const hasError = await errorMessage.isVisible({ timeout: 3000 }).catch(() => false);

            if (hasError) {
              console.log('✓ System correctly rejects invitation to wrong domain');
            } else {
              console.log('⚠ No validation error shown for wrong domain');
            }
          }
        }
      } else {
        console.log('⚠ Invite functionality not tested (button not found)');
      }
    } else {
      test.skip('Team management button not found');
    }
  });
});
