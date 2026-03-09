import { test, expect } from '@playwright/test';

test.describe('Not Found Page', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('renders the 404 page for unknown routes and navigates home', async ({ page }) => {
    const response = await page.goto('/this-route-should-not-exist');

    expect(response?.status(), 'Unknown route should return 404').toBe(404);

    await expect(page.getByText('Error 404')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible();

    const homeLink = page.getByRole('link', { name: 'Go to home' });
    await expect(homeLink).toBeVisible();
    await homeLink.click();

    await expect(page).toHaveURL('/');
  });
});
