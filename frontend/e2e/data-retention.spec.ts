import { test as base, expect, type Page } from '@playwright/test';
import type { RetentionCleanupStatus } from '../src/lib/data-retention';

type Policy = {
  organization_id: number;
  retention_days: number | null;
  enabled: boolean;
  age_basis: 'analysis_generation';
  survey_age_basis: 'submission';
  scope: string[];
  updated_at: string | null;
  policy_version: string;
  cleanup_status: RetentionCleanupStatus;
  legacy_cleanup: {
    state: 'none' | 'pending' | 'completed' | 'cancelled';
    requested_count: number;
    pending_count: number;
    cleared_count: number;
    skipped_count: number;
    cancelled_count: number;
    approved_at: string | null;
    finished_at: string | null;
  };
};

function cleanupStatus(overrides: Partial<RetentionCleanupStatus> = {}): RetentionCleanupStatus {
  return {
    state: 'never', last_attempt_at: null, last_finished_at: null,
    last_success_at: null, next_retry_at: null, next_cleanup_due_at: null,
    consecutive_failures: 0, error_code: null, message: null,
    counts: {
      analysis_results_expired: 0, legacy_analysis_results_cleared: 0,
      survey_responses_deleted: 0, survey_links_cleared: 0,
      survey_period_links_cleared: 0, mappings_deleted: 0,
      notifications_deleted: 0, digest_links_cleared: 0,
      analyses_unverifiable: 0, analyses_deferred: 0,
      legacy_analyses_skipped: 0, legacy_analyses_deferred: 0,
      surveys_unverifiable: 0,
    },
    ...overrides,
  };
}

type RetentionBody = {
  retention_days: number | null;
  clear_unverifiable_analyses?: boolean;
  confirm_deletion?: boolean;
  confirm_legacy_deletion?: boolean;
  legacy_preview_token?: string | null;
  expected_policy_version?: string;
};

type ApiHarness = {
  identity: { role: string; organization_id: number | null };
  policy: Policy;
  reads: number;
  previews: RetentionBody[];
  writes: RetentionBody[];
  saveError: { code: string; message: string } | null;
  previewError: string | null;
  previewOrganizationId: number;
  excludedDemoAnalyses: number;
  identityRequests: number;
  pauseNextIdentity: Promise<void> | null;
};

function policy(days: number | null = null): Policy {
  return {
    organization_id: 41,
    retention_days: days,
    enabled: days !== null,
    age_basis: 'analysis_generation',
    survey_age_basis: 'submission',
    scope: ['analyses', 'survey_responses'],
    updated_at: days === null ? null : '2026-10-01T12:00:00Z',
    policy_version: 'a'.repeat(64),
    cleanup_status: cleanupStatus({ next_cleanup_due_at: days === null ? null : '2026-10-06T03:00:00Z' }),
    legacy_cleanup: {
      state: 'none', requested_count: 0, pending_count: 0,
      cleared_count: 0, skipped_count: 0, cancelled_count: 0,
      approved_at: null, finished_at: null,
    },
  };
}

// This suite never authenticates against a server or reaches the application DB.
// Empty storage plus mocked authoritative identity also verifies that a forged
// localStorage role cannot grant access to the admin controls.
const test = base.extend<{ api: ApiHarness }>({
  api: async ({ page, baseURL }, use) => {
    const api: ApiHarness = {
      identity: { role: 'admin', organization_id: 41 },
      policy: policy(), reads: 0, previews: [], writes: [],
      saveError: null, previewError: null,
      previewOrganizationId: 41, excludedDemoAnalyses: 0,
      identityRequests: 0, pauseNextIdentity: null,
    };
    const unexpectedMutations: string[] = [];
    const origin = new URL(baseURL || 'http://localhost:3000').origin;

    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'retention-ui-mocked-token');
      localStorage.setItem('user_id', '7');
      localStorage.setItem('user_name', 'Retention Test Admin');
      localStorage.setItem('user_email', 'retention-ui@example.test');
      localStorage.setItem('user_role', 'admin');
      localStorage.setItem('user_organization_id', '41');
    });

    await page.route('**/*', async route => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.origin === origin) {
        await route.continue();
        return;
      }
      const reply = (body: unknown, status = 200) => route.fulfill({
        status, contentType: 'application/json', body: JSON.stringify(body),
        headers: {
          'access-control-allow-origin': origin,
          'access-control-allow-credentials': 'true',
          'access-control-allow-headers': 'authorization,content-type',
          'access-control-allow-methods': 'GET,POST,PUT,OPTIONS',
        },
      });
      if (request.method() === 'OPTIONS') {
        await reply({});
        return;
      }
      if (url.pathname === '/auth/user/me') {
        api.identityRequests++;
        const pause = api.pauseNextIdentity;
        api.pauseNextIdentity = null;
        if (pause) await pause;
        await reply({
          id: 7, email: 'retention-ui@example.test', name: 'Retention Test Admin',
          ...api.identity,
        });
        return;
      }
      if (url.pathname === '/auth/organizations/retention') {
        if (request.method() === 'GET') {
          api.reads++;
          await reply(api.policy);
          return;
        }
        if (request.method() === 'PUT') {
          const body = request.postDataJSON() as RetentionBody;
          api.writes.push(body);
          if (api.saveError) {
            await reply({ detail: api.saveError }, 409);
            return;
          }
          const previous = api.policy;
          api.policy = { ...previous, ...policy(body.retention_days) };
          const nextDaily = new Date();
          nextDaily.setUTCHours(15, 0, 0, 0);
          if (nextDaily.getTime() <= Date.now()) nextDaily.setUTCDate(nextDaily.getUTCDate() + 1);
          api.policy.cleanup_status = {
            ...previous.cleanup_status,
            next_cleanup_due_at: body.retention_days === null ? null : nextDaily.toISOString(),
            next_retry_at: body.retention_days === null ? null : previous.cleanup_status.next_retry_at,
          };
          api.policy.policy_version = api.writes.length.toString(16).padStart(64, '0');
          if (body.clear_unverifiable_analyses) {
            api.policy.legacy_cleanup = {
              state: 'pending', requested_count: 2, pending_count: 2,
              cleared_count: 0, skipped_count: 0, cancelled_count: 0,
              approved_at: new Date().toISOString(), finished_at: null,
            };
          } else if (body.retention_days === null && previous.legacy_cleanup.state === 'pending') {
            api.policy.legacy_cleanup = {
              ...previous.legacy_cleanup, state: 'cancelled', pending_count: 0,
              cancelled_count: previous.legacy_cleanup.pending_count,
              finished_at: new Date().toISOString(),
            };
          } else {
            api.policy.legacy_cleanup = previous.legacy_cleanup;
          }
          await reply(api.policy);
          return;
        }
      }
      if (url.pathname === '/auth/organizations/retention/preview' && request.method() === 'POST') {
        const body = request.postDataJSON() as RetentionBody;
        api.previews.push(body);
        if (api.previewError) {
          await reply({ detail: api.previewError }, 503);
          return;
        }
        const evaluated = new Date();
        const legacy = Boolean(body.clear_unverifiable_analyses);
        const previouslyApproved = body.retention_days !== null && api.policy.legacy_cleanup.state === 'pending'
          ? api.policy.legacy_cleanup.pending_count : 0;
        const legacyCandidates = legacy ? 2 : previouslyApproved;
        await reply({
          organization_id: api.previewOrganizationId, preview_only: true, policy_source: 'proposed',
          retention_days: body.retention_days, enabled: body.retention_days !== null,
          evaluated_at: evaluated.toISOString(),
          cutoff_at: body.retention_days === null ? null : new Date(evaluated.getTime() - body.retention_days * 86400000).toISOString(),
          policy_updated_at: api.policy.updated_at,
          analyses: {
            total: 5, expired: body.retention_days === null ? 0 : 1,
            excluded: api.excludedDemoAnalyses,
            retained: 1, unverifiable: 2, deferred: 1, empty: 0,
            regeneration_candidates: body.retention_days === null ? 0 : 1 + legacyCandidates,
          },
          survey_responses: {
            total: 4, expired: body.retention_days === null ? 0 : 1,
            retained: 2, unverifiable: 1,
          },
          related_records: {
            analysis_mappings: 2, analysis_notifications: 1,
            survey_links_to_clear: 2, survey_period_links_to_clear: 1,
            digest_links_to_clear: 1, references_requiring_review: 0,
          },
          samples: [{
            analysis_id: 101, disposition: 'expired', generation_at: '2026-05-01T12:00:00Z',
            reason: 'Result was generated before the retention cutoff.', is_saved: true,
            is_auto_refresh: false, will_clear_as_legacy: false,
          }, {
            analysis_id: 103, disposition: 'unverifiable', generation_at: null,
            reason: 'Stored result generation date cannot be verified.', is_saved: true,
            is_auto_refresh: false, will_clear_as_legacy: legacyCandidates > 0,
          }],
          samples_truncated: false,
          warnings: ['Newer surveys are preserved and detached from cleared analyses.'],
          legacy_cleanup: {
            requested: legacy, analysis_candidates: legacyCandidates,
            pending_analyses: api.policy.legacy_cleanup.pending_count,
            unverifiable_surveys: 1,
            preview_token: legacy ? `mock-preview-receipt-${api.previews.length}` : null,
            preview_expires_at: legacy ? new Date(evaluated.getTime() + 900000).toISOString() : null,
          },
        });
        return;
      }
      if (url.pathname.includes('/integrations') && request.method() === 'GET') {
        await reply({ integrations: [], connected: false, openai_enabled: false });
        return;
      }
      if (url.pathname.startsWith('/api/notifications')) {
        await reply({ notifications: [], unread_count: 0, has_more: false });
        return;
      }
      if (request.method() !== 'GET' && (url.port === '8000' || url.pathname.startsWith('/api/'))) {
        unexpectedMutations.push(`${request.method()} ${url.pathname}`);
      }
      // No off-origin request is ever passed through, including analytics.
      await reply({ members: [], invitations: [], users: [] });
    });

    await use(api);
    expect(unexpectedMutations, 'Only mocked retention preview/update may mutate').toEqual([]);
  },
});

test.use({
  storageState: { cookies: [], origins: [] },
  ...(process.env.RETENTION_E2E_CHROMIUM_PATH
    ? { launchOptions: { executablePath: process.env.RETENTION_E2E_CHROMIUM_PATH } }
    : {}),
});

const enable = (page: Page) => page.getByRole('switch', { name: 'Enable data retention' });
const days = (page: Page) => page.getByLabel('Retention period (days)', { exact: true });
const saveButton = (page: Page) => page.getByRole('button', { name: 'Save retention policy', exact: true });
const confirmDialog = (page: Page) => page.getByRole('dialog', { name: 'Confirm retention policy' });
const deletionWarning = (page: Page) => page.getByRole('alert', { name: 'Existing data deletion warning' });
const confirmSave = (page: Page) => page.getByRole('button', { name: 'Confirm and save', exact: true });

const retentionToggle = (page: Page) => page.locator('button[aria-controls="data-retention-panel"]');


async function expandRetention(page: Page) {
  await expect(retentionToggle(page)).toBeVisible();
  await expect.poll(async () =>
    await retentionToggle(page).isEnabled()
    || await page.getByText('Join an organization to use organization data retention.', { exact: true }).isVisible()
    || await page.getByRole('region', { name: 'Data retention' }).getByRole('alert').first().isVisible()
  ).toBe(true);
  if (await retentionToggle(page).isDisabled()) return;
  if (await retentionToggle(page).getAttribute('aria-expanded') !== 'true') await retentionToggle(page).click();
  await expect(page.locator('#data-retention-panel')).toBeVisible();
}

async function openManagement(page: Page) {
  await page.goto('/management');
  await expandRetention(page);
}

async function openReview(page: Page) {
  await saveButton(page).click();
  await expect(confirmDialog(page)).toBeVisible();
  await expect(confirmSave(page)).toBeEnabled();
}

async function cancelReview(page: Page) {
  await confirmDialog(page).getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(confirmDialog(page)).not.toBeVisible();
}

async function enableAndReview(page: Page, period = '90') {
  await enable(page).check();
  await days(page).fill(period);
  await openReview(page);
}

test.describe('Organization data retention with isolated API responses', () => {
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    test(`optional retention stays compact by default at ${viewport.width}px`, async ({ page, api }, testInfo) => {
      await page.setViewportSize(viewport);
      await page.goto('/management');
      const card = page.getByRole('region', { name: 'Data retention' });
      await expect(card.getByText('Disabled', { exact: true })).toBeVisible();
      await expect(retentionToggle(page)).toHaveAttribute('aria-expanded', 'false');
      await expect(retentionToggle(page)).toHaveAccessibleName('Configure data retention settings');
      await expect(page.locator('#data-retention-panel')).not.toBeVisible();
      await expect(enable(page)).not.toBeVisible();
      await expect(page.getByRole('heading', { name: 'No Primary Integrations Connected', exact: true })).toBeVisible();
      expect(await card.evaluate(element => {
        const mainContent = element.parentElement?.previousElementSibling;
        return mainContent?.textContent?.includes('No Primary Integrations Connected')
          && Boolean(mainContent.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_FOLLOWING);
      })).toBe(true);
      await card.scrollIntoViewIfNeeded();
      const bounds = await card.boundingBox();
      expect(bounds).not.toBeNull();
      expect(bounds!.height).toBeLessThan(viewport.width < 500 ? 210 : 150);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`retention-compact-${viewport.width}.png`), fullPage: true });
      expect(api.previews).toHaveLength(0);
      expect(api.writes).toHaveLength(0);
    });
  }

  test('closing settings discards drafts while tab switches preserve an open draft', async ({ page, api }) => {
    await page.goto('/management');
    await expect(retentionToggle(page)).toBeEnabled();
    await retentionToggle(page).focus();
    await page.keyboard.press('Enter');
    await expect(retentionToggle(page)).toHaveAttribute('aria-expanded', 'true');
    await enable(page).check();
    await days(page).fill('30');
    await expect(page.getByText('Unsaved', { exact: true })).toBeVisible();
    await retentionToggle(page).click();
    await expect(page.getByText('Disabled', { exact: true })).toBeVisible();
    await expect(page.getByText('Unsaved', { exact: true })).toHaveCount(0);
    await expect(page.locator('#data-retention-panel')).not.toBeVisible();
    await retentionToggle(page).focus();
    await page.keyboard.press('Space');
    await expect(enable(page)).not.toBeChecked();
    await expect(days(page)).toHaveValue('90');
    await expect(days(page)).toBeDisabled();
    await expect(saveButton(page)).toBeDisabled();
    expect(api.previews).toHaveLength(0);
    await enable(page).check();
    await days(page).fill('30');
    await expect(saveButton(page)).toBeEnabled();
    await page.getByRole('button', { name: 'Team Roles', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Data retention' })).toHaveCount(0);
    await expect(page.locator('#data-retention-panel')).not.toBeVisible();
    await page.getByRole('button', { name: 'Synced Org', exact: true }).click();
    await expect(days(page)).toHaveValue('30');
    expect(api.policy.enabled).toBe(false);
    expect(api.writes).toHaveLength(0);
  });

  for (const attention of ['failure', 'pending'] as const) {
    test(`collapsed retention still exposes ${attention} attention`, async ({ page, api }) => {
      api.policy = policy(90);
      if (attention === 'failure') api.policy.cleanup_status = cleanupStatus({ state: 'failed', message: 'Cleanup needs a retry.' });
      else api.policy.legacy_cleanup = {
        state: 'pending', requested_count: 2, pending_count: 2, cleared_count: 0,
        skipped_count: 0, cancelled_count: 0, approved_at: '2026-10-04T12:00:00Z', finished_at: null,
      };
      await page.goto('/management');
      await expect(page.getByText(attention === 'failure' ? 'Cleanup needs attention' : 'Prior cleanup approval pending', { exact: true })).toBeVisible();
      await expect(retentionToggle(page)).toHaveAttribute('aria-expanded', 'false');
      expect(api.writes).toHaveLength(0);
    });
  }

  test('settings and confirmation omit redundant text, counts, history and refresh controls', async ({ page, api }) => {
    await openManagement(page);
    await expect(page.getByRole('button', { name: 'Refresh settings', exact: true })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Preview deletion', exact: true })).toHaveCount(0);
    await expect(page.getByText(/Off by default/)).toHaveCount(0);
    await expect(page.locator('summary').filter({ hasText: 'Cleanup history' })).toHaveCount(0);
    await expect(page.getByLabel('Automatic cleanup status')).toHaveCount(0);
    await expect(page.locator('#retention-enabled-help')).toHaveText('Applies to everyone in this organization.');
    await enableAndReview(page);
    const dialog = confirmDialog(page);
    await expect(dialog.getByRole('term')).toHaveCount(0);
    await expect(dialog.getByRole('definition')).toHaveCount(0);
    await expect(dialog.getByLabel('Deletion preview')).toHaveCount(0);
    await expect(dialog).not.toContainText('Analysis results:');
    await expect(dialog).not.toContainText('Surveys:');
    await expect(dialog.getByRole('alert', { name: 'Existing data deletion warning' })).toContainText('Cleanup runs daily at 03:00 UTC.');
    await expect(dialog.getByRole('checkbox')).toHaveCount(0);
    expect(api.previews).toEqual([{ retention_days: 90 }]);
    expect(api.writes).toHaveLength(0);
    await confirmSave(page).click();
    await expect(dialog).not.toBeVisible();
    expect(api.writes).toEqual([{
      retention_days: 90, expected_policy_version: 'a'.repeat(64), confirm_deletion: true,
    }]);
    await expect(page.getByText(/Retention policy saved\./)).toHaveCount(0);
  });

  test('prior approval remains visible without creating new cleanup authorization', async ({ page, api }) => {
    api.policy = policy(90);
    api.policy.legacy_cleanup = {
      state: 'pending', requested_count: 2, pending_count: 2, cleared_count: 0,
      skipped_count: 0, cancelled_count: 0, approved_at: '2026-10-04T12:00:00Z', finished_at: null,
    };
    await openManagement(page);
    await expect(page.getByText('Prior cleanup approval pending', { exact: true })).toBeVisible();
    await days(page).fill('120');
    await openReview(page);
    await expect(confirmDialog(page).getByLabel('Cleanup preview summary')).toHaveCount(0);
    await expect(confirmDialog(page).getByRole('checkbox')).toHaveCount(0);
    await confirmSave(page).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.previews).toEqual([{ retention_days: 120 }]);
    expect(api.writes).toEqual([{
      retention_days: 120, expected_policy_version: 'a'.repeat(64),
    }]);
    expect(api.policy.legacy_cleanup.pending_count).toBe(2);
  });

  test('starts disabled and is available without a primary integration', async ({ page, api }) => {
    await openManagement(page);
    await expect(page.getByRole('heading', { name: 'Data retention', exact: true })).toBeVisible();
    await expect(enable(page)).not.toBeChecked();
    await expect(days(page)).toBeDisabled();
    await expect(page.getByText('Prior cleanup approval pending', { exact: true })).toHaveCount(0);
    await expect(deletionWarning(page)).toHaveCount(0);
    await expect(page.locator('#retention-days-help')).toHaveCount(0);
    await expect(page.getByText('Automatic cleanup is off for this organization.', { exact: true })).toHaveCount(0);
    await expect(page.getByText('Preview deletion before saving; previewing does not save settings or delete data.', { exact: true })).toHaveCount(0);
    await enable(page).check();
    await expect(page.getByRole('region', { name: 'Data retention' }).getByText('Disabled', { exact: true })).toBeVisible();
    expect(api.policy.enabled).toBe(false);
    expect(api.writes).toHaveLength(0);
  });



  test('successful cleanup metadata stays out of the settings panel', async ({ page, api }) => {
    api.policy = policy(90);
    api.policy.cleanup_status = cleanupStatus({
      state: 'succeeded', last_success_at: '2026-10-06T15:40:00Z',
      counts: { ...cleanupStatus().counts, analysis_results_expired: 3 },
    });
    await openManagement(page);
    const card = page.getByRole('region', { name: 'Data retention' });
    await expect(card).not.toContainText('Cleanup history');
    await expect(card).not.toContainText('Last successful cleanup');
    await expect(card).not.toContainText('Analyses cleared');
    await expect(card.getByRole('definition')).toHaveCount(0);
    expect(api.previews).toHaveLength(0);
    expect(api.writes).toHaveLength(0);
  });

  test('cleanup failures still show attention without restoring history', async ({ page, api }) => {
    api.policy = policy(90);
    api.policy.cleanup_status = cleanupStatus({
      state: 'failed', counts: { ...cleanupStatus().counts, analysis_results_expired: 3 },
    });
    await openManagement(page);
    await expect(page.getByText('Cleanup needs attention', { exact: true })).toBeVisible();
    await expect(page.getByLabel('Automatic cleanup status')).toHaveCount(0);
    expect(api.policy.cleanup_status.counts.analysis_results_expired).toBe(3);
    expect(api.writes).toHaveLength(0);
  });

  test('members can reload saved settings without gaining admin controls', async ({ page, api }) => {
    api.identity.role = 'member';
    api.policy = policy(90);
    await openManagement(page);
    await expect(page.getByText('Retention period: 90 days')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Refresh settings', exact: true })).toHaveCount(0);
    const reads = api.reads;
    api.policy = policy(120);
    await page.reload();
    await expandRetention(page);
    await expect(page.getByText('Retention period: 120 days')).toBeVisible();
    await expect(enable(page)).toHaveCount(0);
    await expect(saveButton(page)).toHaveCount(0);
    expect(api.reads).toBeGreaterThan(reads);
    expect(api.previews).toHaveLength(0);
    expect(api.writes).toHaveLength(0);
  });

  test('disabled retention shows no cleanup history or retry schedule', async ({ page, api }) => {
    api.policy.cleanup_status = cleanupStatus({ state: 'failed', consecutive_failures: 1 });
    await openManagement(page);
    await expect(page.getByText('Last cleanup failed', { exact: true })).toBeVisible();
    await expect(page.getByLabel('Automatic cleanup status')).toHaveCount(0);
    await expect(page.getByRole('region', { name: 'Data retention' }).getByText('Disabled', { exact: true })).toBeVisible();
    expect(api.policy.enabled).toBe(false);
    expect(api.writes).toHaveLength(0);
  });

  test('omits explanatory copy and analysis sample details from retention settings', async ({ page, api }) => {
    api.policy = policy(90);
    await openManagement(page);
    const retention = page.getByRole('region', { name: 'Data retention' });
    await expect(days(page)).not.toHaveAttribute('aria-describedby');
    await expect(page.locator('#retention-days-help')).toHaveCount(0);
    await expect(retention).not.toContainText('omitted until they support retention');
    await days(page).fill('120');
    await openReview(page);
    await expect(confirmDialog(page).getByLabel('Deletion preview')).toHaveCount(0);
    await expect(confirmDialog(page).getByRole('table')).toHaveCount(0);
    expect(api.writes).toHaveLength(0);
  });

  test('members see the saved policy but cannot edit despite a forged cached admin role', async ({ page, api }) => {
    api.identity.role = 'member';
    api.policy = policy(90);
    await openManagement(page);
    await expect(page.getByRole('heading', { name: 'Data retention', exact: true })).toBeVisible();
    await expect(page.getByText(/90 days/).first()).toBeVisible();
    await expect(enable(page)).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Preview deletion', exact: true })).toHaveCount(0);
    await expect(saveButton(page)).toHaveCount(0);
    expect(api.reads).toBeGreaterThan(0);
    expect(api.previews).toHaveLength(0);
    expect(api.writes).toHaveLength(0);
  });

  test('an orgless identity cannot use a forged cached organization', async ({ page, api }) => {
    api.identity.organization_id = null;
    await openManagement(page);
    await expect(page.getByRole('heading', { name: 'Data retention', exact: true })).toBeVisible();
    await expect(page.getByText('Join an organization to use organization data retention.', { exact: true })).toBeVisible();
    await expect(enable(page)).toHaveCount(0);
    await expect(saveButton(page)).toHaveCount(0);
    expect(api.reads).toBe(0);
    expect(api.writes).toHaveLength(0);
  });

  test('invalid day values cannot be previewed or saved', async ({ page, api }) => {
    await openManagement(page);
    await enable(page).check();
    for (const invalid of ['', '0', '1.5', '3651']) {
      await days(page).fill(invalid);
      await expect(days(page)).toHaveAttribute('aria-describedby', 'retention-days-error');
      await expect(page.locator('#retention-days-error')).toHaveText('Enter a whole number from 1 to 3650.');
      await expect(saveButton(page)).toBeDisabled();
      await expect(deletionWarning(page)).toHaveCount(0);
    }
    await days(page).fill('3650');
    await expect(days(page)).not.toHaveAttribute('aria-describedby');
    await expect(page.locator('#retention-days-error')).toHaveCount(0);
    await expect(saveButton(page)).toBeEnabled();
    expect(api.previews).toHaveLength(0);
    expect(api.writes).toHaveLength(0);
  });

  test('enabling requires a reviewed preview and confirmation, survives reload, and Cancel saves nothing', async ({ page, api }) => {
    await openManagement(page);
    await enable(page).check();
    await days(page).fill('10');
    await expect(deletionWarning(page)).toHaveCount(0);
    await expect(saveButton(page)).toBeEnabled();
    await openReview(page);
    await expect(confirmSave(page)).toBeEnabled();
    expect(api.previews).toEqual([{ retention_days: 10 }]);
    expect(api.writes).toHaveLength(0);
    await expect(confirmDialog(page)).toBeVisible();
    const dialogWarning = confirmDialog(page).getByRole('alert', { name: 'Existing data deletion warning' });
    await expect(dialogWarning).toContainText('Deletion is permanent');
    await expect(dialogWarning).toContainText('Cleanup runs daily at 03:00 UTC.');
    await expect(dialogWarning).toContainText('Enabling retention permanently clears existing results generated and surveys submitted more than 10 days ago during cleanup.');
    await expect(confirmDialog(page)).not.toContainText('Existing data is included.');
    await expect(confirmDialog(page).getByLabel('Cleanup preview summary')).toHaveCount(0);
    await expect(confirmSave(page)).toBeEnabled();
    await confirmDialog(page).getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes).toHaveLength(0);
    await openReview(page);
    await confirmSave(page).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes).toHaveLength(1);
    await expect(page.getByText('Retention policy saved.', { exact: false })).toHaveCount(0);
    await expect(page.getByRole('region', { name: 'Data retention' }).getByText('Enabled', { exact: true })).toBeVisible();
    expect(api.writes[0]).toMatchObject({ retention_days: 10, confirm_deletion: true });
    expect(api.writes[0].expected_policy_version).toBe('a'.repeat(64));
    expect(api.writes[0].clear_unverifiable_analyses).not.toBe(true);
    await page.reload();
    await expandRetention(page);
    await expect(enable(page)).toBeChecked();
    await expect(days(page)).toHaveValue('10');
    expect(api.writes).toHaveLength(1);
  });

  test('shortening requires destructive confirmation', async ({ page, api }) => {
    api.policy = policy(90);
    await openManagement(page);
    await days(page).fill('30');
    await expect(deletionWarning(page)).toHaveCount(0);
    await openReview(page);
    await expect(confirmDialog(page).getByRole('alert', { name: 'Existing data deletion warning' })).toContainText('Deletion is permanent');
    await expect(confirmDialog(page).getByRole('alert', { name: 'Existing data deletion warning' })).toContainText('Shortening retention permanently clears existing results generated and surveys submitted more than 30 days ago during cleanup.');
    await expect(confirmSave(page)).toBeEnabled();
    await confirmSave(page).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes[0]).toMatchObject({ retention_days: 30, confirm_deletion: true });
  });

  test('lengthening does not require deletion consent', async ({ page, api }) => {
    api.policy = policy(30);
    await openManagement(page);
    await days(page).fill('90');
    await expect(deletionWarning(page)).toHaveCount(0);
    await openReview(page);
    await expect(confirmDialog(page)).toBeVisible();
    await expect(confirmDialog(page).getByRole('alert', { name: 'Existing data deletion warning' })).toHaveCount(0);
    await expect(confirmDialog(page).getByRole('checkbox')).toHaveCount(0);
    await expect(confirmSave(page)).toBeEnabled();
    await confirmSave(page).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes[0].retention_days).toBe(90);
    expect(api.writes[0].confirm_deletion).not.toBe(true);
  });

  test('ordinary desktop confirmation has no checkbox and cannot authorize unknown-date cleanup', async ({ page, api }, testInfo) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await openManagement(page);
    await enableAndReview(page);
    await expect(confirmDialog(page).getByRole('checkbox')).toHaveCount(0);
    await page.screenshot({ path: testInfo.outputPath('retention-desktop-confirmation.png'), animations: 'disabled' });
    await confirmSave(page).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes).toEqual([{
      retention_days: 90, confirm_deletion: true, expected_policy_version: 'a'.repeat(64),
    }]);
    expect(api.policy.legacy_cleanup.state).toBe('none');
  });

  test('changing days or enabled state requires fresh counts when saving', async ({ page, api }) => {
    await openManagement(page);
    await enableAndReview(page);
    await cancelReview(page);
    await days(page).fill('30');
    await expect(saveButton(page)).toBeEnabled();
    await openReview(page);
    await expect(confirmDialog(page)).toContainText('more than 30 days ago during cleanup.');
    expect(api.previews).toEqual([{ retention_days: 90 }, { retention_days: 30 }]);
    await cancelReview(page);
    await enable(page).uncheck();
    await expect(saveButton(page)).toBeDisabled();
    await expect(page.getByLabel('Deletion preview')).toHaveCount(0);
    expect(api.writes).toHaveLength(0);
  });

  test('a changed policy requires refreshed settings and a new preview without retrying old consent', async ({ page, api }) => {
    api.policy = policy(90);
    api.saveError = { code: 'retention_policy_changed', message: 'The retention policy changed. Refresh settings and review a new preview before saving.' };
    await openManagement(page);
    await days(page).fill('30');
    await openReview(page);
    await confirmSave(page).click();
    await expect(page.getByRole('alert').filter({ hasText: /policy changed.*reload the page/i })).toBeVisible();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes).toHaveLength(1);
    api.saveError = null;
    await page.reload();
    await expandRetention(page);
    await expect(days(page)).toHaveValue('90');
    await days(page).fill('30');
    await openReview(page);
    await confirmSave(page).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes).toHaveLength(2);
    expect(api.writes[1]).toEqual({
      retention_days: 30, expected_policy_version: 'a'.repeat(64), confirm_deletion: true,
    });
  });

  test('disabling saves without a preview or confirmation and cancels prior cleanup approval', async ({ page, api }) => {
    api.policy = policy(90);
    api.policy.legacy_cleanup = {
      state: 'pending', requested_count: 3, pending_count: 2,
      cleared_count: 1, skipped_count: 0, cancelled_count: 0,
      approved_at: '2026-10-04T12:00:00Z', finished_at: null,
    };
    await openManagement(page);
    await expect(page.getByText('Prior cleanup approval pending', { exact: true })).toBeVisible();
    await enable(page).uncheck();
    await expect(saveButton(page)).toBeEnabled();
    await saveButton(page).click();
    await expect(page.getByRole('region', { name: 'Data retention' }).getByText('Disabled', { exact: true })).toBeVisible();
    await expect(page.getByText(/Retention disabled\./)).toHaveCount(0);
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.previews).toHaveLength(0);
    expect(api.writes).toEqual([{
      retention_days: null, expected_policy_version: 'a'.repeat(64),
    }]);
    expect(api.writes[0].retention_days).toBeNull();
    expect(api.writes[0].clear_unverifiable_analyses).not.toBe(true);
    expect(api.writes[0].confirm_legacy_deletion).not.toBe(true);
    await expect(page.getByText('Prior cleanup approval pending', { exact: true })).toHaveCount(0);
    await expect(page.getByRole('status').filter({ hasText: /prior cleanup approval has been cancelled/i })).toHaveCount(0);
    await expect(page.getByRole('region', { name: 'Data retention' }).getByText('Disabled', { exact: true })).toBeVisible();
    await page.reload();
    await expandRetention(page);
    await expect(enable(page)).not.toBeChecked();
    await expect(page.getByText('Prior cleanup approval pending', { exact: true })).toHaveCount(0);
    expect(api.policy.legacy_cleanup.state).toBe('cancelled');
  });

  test('preview failure blocks confirmation and Save retries with a fresh preview', async ({ page, api }) => {
    api.previewError = 'Retention preview temporarily unavailable.';
    await openManagement(page);
    await enable(page).check();
    await saveButton(page).click();
    await expect(page.getByText(api.previewError, { exact: true }).first()).toBeVisible();
    await expect(confirmDialog(page)).not.toBeVisible();
    await expect(saveButton(page)).toBeEnabled();
    expect(api.writes).toHaveLength(0);
    api.previewError = null;
    await openReview(page);
    expect(api.previews).toHaveLength(2);
    expect(api.writes).toHaveLength(0);
  });

  test('a changed session blocks saving a preview approved under the earlier account', async ({ page, api }) => {
    await openManagement(page);
    await enableAndReview(page);
    await page.evaluate(() => localStorage.setItem('auth_token', 'another-mocked-session'));
    await confirmSave(page).click();
    await expect(page.getByText('Your session changed. Reload the page before continuing.', { exact: true })).toBeVisible();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes).toHaveLength(0);
  });

  test('a preview from a different organization cannot be approved', async ({ page, api }) => {
    api.previewOrganizationId = 42;
    await openManagement(page);
    await enable(page).check();
    await saveButton(page).click();
    await expect(page.getByRole('alert').filter({ hasText: /organization changed/i })).toBeVisible();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes).toHaveLength(0);
  });

  test('switching accounts during awaited identity verification cannot dispatch the earlier save', async ({ page, api }) => {
    await openManagement(page);
    await enableAndReview(page);
    const identityRequests = api.identityRequests;
    let release: () => void = () => {};
    api.pauseNextIdentity = new Promise<void>(resolve => { release = resolve; });
    await confirmSave(page).click();
    await expect.poll(() => api.identityRequests).toBeGreaterThan(identityRequests);
    await page.evaluate(() => localStorage.setItem('auth_token', 'changed-during-verification'));
    release();
    await expect(page.getByRole('alert').filter({ hasText: /session changed/i })).toBeVisible();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes).toHaveLength(0);
  });

  test('membership changing under the same token blocks saving in the new organization', async ({ page, api }) => {
    await openManagement(page);
    await enableAndReview(page);
    api.identity.organization_id = 42;
    await confirmSave(page).click();
    await expect(page.getByRole('alert').filter({ hasText: /organization.*changed|role.*changed|account.*changed/i })).toBeVisible();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes).toHaveLength(0);
  });

  test('page reload discards unsaved edits and loads the current policy', async ({ page, api }) => {
    api.policy = policy(90);
    await openManagement(page);
    await days(page).fill('30');
    api.policy = policy(120);
    await page.reload();
    await expandRetention(page);
    await expect(days(page)).toHaveValue('120');
    await expect(saveButton(page)).toBeDisabled();
    await expect(page.getByText('Unsaved', { exact: true })).toHaveCount(0);
    expect(api.writes).toHaveLength(0);
  });

  test('minimal mobile confirmation fits without horizontal page overflow', async ({ page, api }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openManagement(page);
    await enableAndReview(page);
      await expect(confirmDialog(page).getByRole('checkbox')).toHaveCount(0);
    await page.screenshot({ path: testInfo.outputPath('retention-mobile-confirmation.png'), animations: 'disabled' });
    await expect(confirmSave(page)).toBeEnabled();
    await expect(confirmDialog(page).getByRole('button', { name: 'Cancel', exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(api.writes).toHaveLength(0);
  });

  test('Cancel stops a loading preview without allowing a late confirmation', async ({ page, api }) => {
    await openManagement(page);
    await enable(page).check();
    let release: () => void = () => {};
    api.pauseNextIdentity = new Promise<void>(resolve => { release = resolve; });
    try {
      await saveButton(page).click();
      await expect(confirmDialog(page).getByRole('status')).toContainText('Preparing confirmation');
      await expect(confirmSave(page)).toBeDisabled();
      await cancelReview(page);
      await expect(saveButton(page)).toBeEnabled();
    } finally { release(); }
    await openReview(page);
    expect(api.previews).toEqual([{ retention_days: 90 }]);
    expect(api.writes).toHaveLength(0);
    await cancelReview(page);
    await openReview(page);
    expect(api.previews).toHaveLength(2);
    expect(api.writes).toHaveLength(0);
  });

});
