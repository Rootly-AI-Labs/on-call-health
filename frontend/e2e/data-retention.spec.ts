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
const previewButton = (page: Page) => page.getByRole('button', { name: 'Preview deletion', exact: true });
const saveButton = (page: Page) => page.getByRole('button', { name: 'Save retention policy', exact: true });
const confirmDialog = (page: Page) => page.getByRole('dialog', { name: 'Confirm retention policy' });
const deletionWarning = (page: Page) => page.getByRole('alert', { name: 'Existing data deletion warning' });
const deletionConfirmation = (page: Page) => page.getByRole('checkbox', { name: 'I understand this policy can permanently delete existing analysis results and old survey responses.' });
const confirmSave = (page: Page) => page.getByRole('button', { name: 'Confirm and save', exact: true });
const cleanupPanel = (page: Page) => page.locator('[aria-label="Automatic cleanup status"]');
const previewPreservationNote = 'Newer reports and surveys are kept. Demo reports are excluded. Undated records are skipped.';

const retentionToggle = (page: Page) => page.locator('button[aria-controls="data-retention-panel"]');

async function openDisclosure(page: Page, name: string) {
  const summary = page.locator('summary').filter({ hasText: name }).first();
  if (await summary.count() && await summary.locator('..').getAttribute('open') === null) await summary.click();
}

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
  // Scenarios reveal cleanup outcomes; product defaults remain compact.
  await openDisclosure(page, 'Cleanup history');
}

async function openManagement(page: Page) {
  await page.goto('/management');
  await expandRetention(page);
}

async function enableAndPreview(page: Page, period = '90') {
  await enable(page).check();
  await days(page).fill(period);
  await previewButton(page).click();
  await expect(saveButton(page)).toBeEnabled();
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
      const bounds = await card.boundingBox();
      expect(bounds).not.toBeNull();
      expect(bounds!.height).toBeLessThan(viewport.width < 500 ? 210 : 150);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`retention-compact-${viewport.width}.png`), fullPage: true });
      expect(api.previews).toHaveLength(0);
      expect(api.writes).toHaveLength(0);
    });
  }

  test('keyboard expansion preserves unsaved drafts without changing the saved policy', async ({ page, api }) => {
    await page.goto('/management');
    await expect(retentionToggle(page)).toBeEnabled();
    await retentionToggle(page).focus();
    await page.keyboard.press('Enter');
    await expect(retentionToggle(page)).toHaveAttribute('aria-expanded', 'true');
    await enable(page).check();
    await days(page).fill('30');
    await retentionToggle(page).click();
    await expect(page.getByText('Disabled', { exact: true })).toBeVisible();
    await expect(page.getByText('Unsaved changes', { exact: true })).toBeVisible();
    await expect(page.locator('#data-retention-panel')).not.toBeVisible();
    await retentionToggle(page).focus();
    await page.keyboard.press('Space');
    await expect(days(page)).toHaveValue('30');
    await expect(saveButton(page)).toBeDisabled();
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

  test('simple retention has no advanced cleanup and collapse preserves its ordinary preview', async ({ page, api }) => {
    await openManagement(page);
    await expect(page.locator('summary').filter({ hasText: 'Advanced cleanup' })).toHaveCount(0);
    await expect(page.locator('summary').filter({ hasText: 'How retention works' })).toHaveCount(0);
    await expect(page.getByText('Preview deletion before saving; previewing does not save settings or delete data.', { exact: true })).toHaveCount(0);
    await expect(page.getByRole('checkbox', { name: /Include results with unknown generation dates/ })).toHaveCount(0);
    await enableAndPreview(page);
    const preview = page.getByLabel('Deletion preview');
    await expect(preview).toContainText(previewPreservationNote);
    await expect(preview.getByRole('term')).toHaveText(['Analysis results to clear', 'Survey responses to delete']);
    await expect(preview.getByRole('definition')).toHaveCount(2);
    await expect(preview.getByText(/^Evaluated /)).toHaveCount(0);
    await expect(preview).not.toContainText('Survey links to detach');
    await expect(preview).not.toContainText('Results with unknown generation dates:');
    await expect(preview).not.toContainText('Retained:');
    await expect(preview.locator('ul')).toHaveCount(0);
    await retentionToggle(page).click();
    await retentionToggle(page).click();
    await expect(saveButton(page)).toBeEnabled();
    await saveButton(page).click();
    await expect(confirmDialog(page).getByRole('checkbox')).toHaveCount(1);
    await deletionConfirmation(page).check();
    await expect(confirmSave(page)).toBeEnabled();
    await confirmSave(page).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.previews).toEqual([{ retention_days: 90 }]);
    expect(api.writes).toEqual([{
      retention_days: 90, expected_policy_version: 'a'.repeat(64), confirm_deletion: true,
    }]);
    expect(api.policy.legacy_cleanup.state).toBe('none');
  });

  test('an existing prior approval is visible and included in preview totals without new consent fields', async ({ page, api }) => {
    api.policy = policy(90);
    api.policy.legacy_cleanup = {
      state: 'pending', requested_count: 2, pending_count: 2, cleared_count: 0,
      skipped_count: 0, cancelled_count: 0, approved_at: '2026-10-04T12:00:00Z', finished_at: null,
    };
    await openManagement(page);
    await expect(page.getByText('Prior cleanup approval pending', { exact: true })).toBeVisible();
    await days(page).fill('120');
    await previewButton(page).click();
    const preview = page.getByLabel('Deletion preview');
    await expect(preview.getByText('Analysis results to clear', { exact: true }).locator('..').getByRole('definition')).toHaveText('3');
    await expect(preview).toContainText('Includes 2 previously approved results.');
    await expect(preview).toContainText('Newer reports and surveys are kept. Demo reports are excluded.');
    await expect(preview).toContainText('Previously approved undated results are included.');
    await saveButton(page).click();
    await expect(confirmDialog(page).getByLabel('Cleanup preview summary')).toContainText('3 analysis results to clear');
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
    const description = page.locator('#retention-days-help');
    const descriptionText = 'Data retention, when enabled, deletes manually saved analyses N days after generation and survey responses N days after submission; auto-refresh results expire while their setup is kept.';
    await expect(description).toHaveText(descriptionText);
    await expect(page.getByText(descriptionText, { exact: true })).toHaveCount(1);
    expect(await description.evaluate(element => ['retention-enabled', 'retention-days'].every(id => {
      const control = document.getElementById(id);
      return control !== null && Boolean(element.compareDocumentPosition(control) & Node.DOCUMENT_POSITION_FOLLOWING);
    }))).toBe(true);
    await expect(page.getByText('Automatic cleanup is off for this organization.', { exact: true })).toHaveCount(0);
    await expect(page.getByText('Preview deletion before saving; previewing does not save settings or delete data.', { exact: true })).toHaveCount(0);
    await expect(cleanupPanel(page)).toContainText('Automatic cleanup status: Not run yet');
    await expect(cleanupPanel(page)).toContainText('No cleanup has run for this organization yet');
    await enable(page).check();
    await expect(page.getByRole('region', { name: 'Data retention' }).getByText('Disabled', { exact: true })).toBeVisible();
    expect(api.policy.enabled).toBe(false);
    expect(api.writes).toHaveLength(0);
  });

  test('preview keeps demo reports out of the simplified deletion counts', async ({ page, api }) => {
    api.excludedDemoAnalyses = 2;
    await openManagement(page);
    await enableAndPreview(page);
    const preview = page.getByLabel('Deletion preview');
    await expect(preview).toContainText(previewPreservationNote);
    await expect(preview).not.toContainText('Demo analyses excluded:');
    await expect(preview.getByText('Analysis results to clear', { exact: true }).locator('..').getByRole('definition')).toHaveText('1');
    await saveButton(page).click();
    await expect(confirmDialog(page).getByLabel('Cleanup preview summary')).toContainText('1 analysis results to clear');
    expect(api.previews).toEqual([{ retention_days: 90 }]);
    expect(api.writes).toHaveLength(0);
  });

  test('shows daily cleanup timing and combines all cleared results in successful outcomes', async ({ page, api }, testInfo) => {
    api.policy = policy(90);
    const counts = {
      ...cleanupStatus().counts, analysis_results_expired: 3,
      legacy_analysis_results_cleared: 2, survey_responses_deleted: 1,
      survey_links_cleared: 2, survey_period_links_cleared: 1,
      digest_links_cleared: 2, mappings_deleted: 4, notifications_deleted: 5,
      analyses_unverifiable: 1, analyses_deferred: 2,
      legacy_analyses_skipped: 1, legacy_analyses_deferred: 1,
      surveys_unverifiable: 1,
    };
    api.policy.cleanup_status = cleanupStatus({
      state: 'succeeded', last_attempt_at: '2026-10-04T12:00:00Z',
      last_finished_at: '2026-10-04T12:01:00Z', last_success_at: '2026-10-04T12:01:00Z',
      next_cleanup_due_at: '2026-10-05T03:00:00Z', counts,
    });
    api.policy.legacy_cleanup = {
      state: 'completed', requested_count: 3, pending_count: 0,
      cleared_count: 2, skipped_count: 1, cancelled_count: 0,
      approved_at: '2026-10-03T12:00:00Z', finished_at: '2026-10-04T12:01:00Z',
    };
    await openManagement(page);
    const panel = cleanupPanel(page);
    await expect(panel).toContainText('Automatic cleanup status: Succeeded');
    await expect(panel.getByText('Analysis results cleared', { exact: true }).locator('..').getByRole('definition')).toHaveText('5');
    await expect(panel.getByText('Legacy results cleared', { exact: true })).toHaveCount(0);
    await expect(panel.getByText('Survey responses deleted', { exact: true }).locator('..').getByRole('definition')).toHaveText('1');
    await expect(panel.getByText('Survey links detached', { exact: true }).locator('..').getByRole('definition')).toHaveText('2');
    await expect(panel.getByText('Last successful cleanup', { exact: true }).locator('..')).toContainText('UTC');
    await expect(panel.getByText('Next cleanup due', { exact: true }).locator('..')).toContainText('2026');
    await expect(panel.getByText('Next cleanup due', { exact: true }).locator('..')).toContainText('3:00:00');
    await expect(panel).toContainText('Cleanup runs daily at 03:00 UTC');
    await expect(panel).not.toContainText('next 15-minute check');
    await panel.getByText('Related cleanup outcomes', { exact: true }).click();
    await expect(panel).toContainText('Mappings removed: 4; notifications removed: 5');
    await expect(panel).toContainText('surveys with unknown submission dates preserved: 1');
    await expect(page.getByRole('heading', { name: /Legacy cleanup status/ })).toHaveCount(0);
    await panel.screenshot({ path: testInfo.outputPath('retention-cleanup-status-desktop.png'), animations: 'disabled' });
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(panel.getByRole('heading', { name: 'Automatic cleanup status: Succeeded', exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await panel.screenshot({ path: testInfo.outputPath('retention-cleanup-status-mobile.png'), animations: 'disabled' });
    expect(api.previews).toHaveLength(0);
    expect(api.writes).toHaveLength(0);
  });

  test('reports sanitized failure and retry eligibility while preserving successful cleanup counts', async ({ page, api }) => {
    api.policy = policy(90);
    api.policy.cleanup_status = cleanupStatus({
      state: 'failed', last_attempt_at: '2026-10-05T12:00:00Z',
      last_finished_at: '2026-10-05T12:01:00Z', last_success_at: '2026-10-04T12:01:00Z',
      next_retry_at: '2026-10-05T12:31:00Z', next_cleanup_due_at: '2026-10-05T12:31:00Z',
      consecutive_failures: 2, error_code: 'cleanup_failed',
      message: 'Cleanup could not finish. Please contact an organization administrator if failures continue.',
      counts: { ...cleanupStatus().counts, analysis_results_expired: 3, survey_responses_deleted: 1 },
    });
    await openManagement(page);
    const panel = cleanupPanel(page);
    await expect(panel).toContainText('Automatic cleanup status: Failed');
    await expect(panel.getByRole('alert')).toHaveText(api.policy.cleanup_status.message!);
    await expect(panel).toContainText('Consecutive failed attempts: 2');
    await expect(panel.getByText('Next retry eligible', { exact: true }).locator('..')).toContainText('UTC');
    await expect(panel.getByText('Next retry eligible', { exact: true }).locator('..')).toContainText('12:31:00');
    await expect(panel).toContainText('Counts below are from the last successful cleanup');
    await expect(panel.getByText('Analysis results cleared', { exact: true }).locator('..').getByRole('definition')).toHaveText('3');
    await expect(panel).not.toContainText('cleanup_failed');
    expect(api.writes).toHaveLength(0);
  });

  test('members can refresh cleanup outcomes without gaining admin controls', async ({ page, api }) => {
    api.identity.role = 'member';
    api.policy = policy(90);
    api.policy.cleanup_status = cleanupStatus({
      state: 'skipped', message: 'Cleanup was skipped because the policy changed before the run.',
      last_attempt_at: '2026-10-05T12:00:00Z', last_finished_at: '2026-10-05T12:00:01Z',
      next_cleanup_due_at: '2026-10-06T03:00:00Z',
    });
    await openManagement(page);
    await expect(cleanupPanel(page)).toContainText('Automatic cleanup status: Skipped');
    await expect(cleanupPanel(page)).toContainText('policy changed before the run');
    const reads = api.reads;
    api.policy.cleanup_status = cleanupStatus({
      state: 'succeeded', last_attempt_at: '2026-10-05T12:15:00Z',
      last_finished_at: '2026-10-05T12:16:00Z', last_success_at: '2026-10-05T12:16:00Z',
      next_cleanup_due_at: '2026-10-06T03:00:00Z',
      counts: { ...cleanupStatus().counts, analysis_results_expired: 2 },
    });
    await page.getByRole('button', { name: 'Refresh settings', exact: true }).click();
    await expect(cleanupPanel(page)).toContainText('Automatic cleanup status: Succeeded');
    await expect(cleanupPanel(page).getByText('Analysis results cleared', { exact: true }).locator('..').getByRole('definition')).toHaveText('2');
    await expect(enable(page)).toHaveCount(0);
    await expect(previewButton(page)).toHaveCount(0);
    await expect(saveButton(page)).toHaveCount(0);
    expect(api.reads).toBeGreaterThan(reads);
    expect(api.previews).toHaveLength(0);
    expect(api.writes).toHaveLength(0);
  });

  test('disabled retention preserves historical outcomes but does not advertise a scheduled retry', async ({ page, api }) => {
    api.policy.cleanup_status = cleanupStatus({
      state: 'failed', last_attempt_at: '2026-10-05T12:00:00Z',
      last_finished_at: '2026-10-05T12:01:00Z', consecutive_failures: 1,
      message: 'Cleanup could not finish.',
    });
    await openManagement(page);
    await expect(cleanupPanel(page)).toContainText('Automatic cleanup status: Failed');
    await expect(cleanupPanel(page)).toContainText('Not scheduled while retention is disabled');
    await expect(cleanupPanel(page)).not.toContainText('Next retry eligible');
    await expect(page.getByRole('region', { name: 'Data retention' }).getByText('Disabled', { exact: true })).toBeVisible();
    expect(api.policy.enabled).toBe(false);
    expect(api.writes).toHaveLength(0);
  });

  test('shows the generation-age helper and generation dates in the preview', async ({ page, api }) => {
    api.policy = policy(90);
    await openManagement(page);
    const retention = page.getByRole('region', { name: 'Data retention' });
    await expect(days(page)).toHaveAttribute('aria-describedby', 'retention-days-help');
    await expect(page.locator('#retention-days-help')).toHaveText('Data retention, when enabled, deletes manually saved analyses N days after generation and survey responses N days after submission; auto-refresh results expire while their setup is kept.');
    await expect(retention).not.toContainText('omitted until they support retention');
    await previewButton(page).click();
    await retention.getByText('Analysis samples (2)', { exact: true }).click();
    await expect(retention.getByRole('columnheader', { name: 'Generated', exact: true })).toBeVisible();
    const expired = retention.getByRole('row').filter({ hasText: '#101' });
    await expect(expired.getByRole('cell').nth(1)).toContainText('2026');
    await expect(expired.getByRole('cell').nth(1)).toContainText('UTC');
    await expect(expired).toContainText('Result was generated before the retention cutoff.');
    const legacy = retention.getByRole('row').filter({ hasText: '#103' });
    await expect(legacy.getByRole('cell').nth(1)).toHaveText('Unknown');
    await expect(legacy).toContainText('Stored result generation date cannot be verified.');
    expect(api.writes).toHaveLength(0);
  });

  test('members see the saved policy but cannot edit despite a forged cached admin role', async ({ page, api }) => {
    api.identity.role = 'member';
    api.policy = policy(90);
    await openManagement(page);
    await expect(page.getByRole('heading', { name: 'Data retention', exact: true })).toBeVisible();
    await expect(page.getByText(/90 days/).first()).toBeVisible();
    await expect(enable(page)).toHaveCount(0);
    await expect(previewButton(page)).toHaveCount(0);
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
      await expect(days(page)).toHaveAttribute('aria-describedby', 'retention-days-help retention-days-error');
      await expect(page.locator('#retention-days-error')).toHaveText('Enter a whole number from 1 to 3650.');
      await expect(page.locator('#retention-days-help')).toContainText('Data retention, when enabled, deletes manually saved analyses N days after generation');
      await expect(previewButton(page)).toBeDisabled();
      await expect(saveButton(page)).toBeDisabled();
      await expect(deletionWarning(page)).toHaveCount(0);
    }
    await days(page).fill('3650');
    await expect(days(page)).toHaveAttribute('aria-describedby', 'retention-days-help');
    await expect(page.locator('#retention-days-error')).toHaveCount(0);
    await expect(previewButton(page)).toBeEnabled();
    expect(api.previews).toHaveLength(0);
    expect(api.writes).toHaveLength(0);
  });

  test('enabling requires a reviewed preview and confirmation, survives reload, and Cancel saves nothing', async ({ page, api }) => {
    await openManagement(page);
    await enable(page).check();
    await expect(deletionWarning(page)).toBeVisible();
    await expect(deletionWarning(page)).toContainText('Enabling retention permanently clears existing results');
    await expect(deletionWarning(page)).toContainText('more than 90 days ago during cleanup');
    await expect(saveButton(page)).toBeDisabled();
    await previewButton(page).click();
    await expect(saveButton(page)).toBeEnabled();
    expect(api.previews).toEqual([{ retention_days: 90 }]);
    expect(api.writes).toHaveLength(0);
    await saveButton(page).click();
    await expect(confirmDialog(page)).toBeVisible();
    const dialogWarning = confirmDialog(page).getByRole('alert', { name: 'Existing data deletion warning' });
    await expect(dialogWarning).toContainText('Enabling 90-day retention');
    await expect(dialogWarning).toContainText('Expired manually saved analyses are deleted, including their configuration and metadata');
    await expect(dialogWarning).toContainText('auto-refresh configuration, accounts, memberships, and integration settings are preserved');
    await expect(dialogWarning).toContainText('become unavailable immediately when the policy is saved');
    await expect(dialogWarning).toContainText('saving does not run deletion');
    await expect(dialogWarning).toContainText('Results with unknown generation dates are preserved until successfully regenerated');
    await expect(confirmDialog(page).getByLabel('Cleanup preview summary')).toContainText('1 analysis results to clear and 1 old survey responses to delete');
    await expect(confirmSave(page)).toBeDisabled();
    await confirmDialog(page).getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes).toHaveLength(0);
    await saveButton(page).click();
    await deletionConfirmation(page).check();
    await confirmSave(page).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes).toHaveLength(1);
    await expect(page.getByRole('status').filter({ hasText: 'Retention policy saved.' })).toContainText('next daily run at 03:00 UTC');
    expect(api.writes[0]).toMatchObject({ retention_days: 90, confirm_deletion: true });
    expect(api.writes[0].expected_policy_version).toBe('a'.repeat(64));
    expect(api.writes[0].clear_unverifiable_analyses).not.toBe(true);
    await page.reload();
    await expandRetention(page);
    await expect(enable(page)).toBeChecked();
    await expect(days(page)).toHaveValue('90');
    expect(api.writes).toHaveLength(1);
  });

  test('shortening requires destructive confirmation', async ({ page, api }) => {
    api.policy = policy(90);
    await openManagement(page);
    await days(page).fill('30');
    await expect(deletionWarning(page)).toContainText('Shortening retention permanently clears existing results');
    await expect(deletionWarning(page)).toContainText('more than 30 days ago during cleanup');
    await previewButton(page).click();
    await saveButton(page).click();
    await expect(confirmDialog(page).getByRole('alert', { name: 'Existing data deletion warning' })).toContainText('Shortening retention to 30 days');
    await expect(deletionConfirmation(page)).toBeVisible();
    await expect(confirmSave(page)).toBeDisabled();
    await deletionConfirmation(page).check();
    await confirmSave(page).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes[0]).toMatchObject({ retention_days: 30, confirm_deletion: true });
  });

  test('lengthening does not require deletion consent', async ({ page, api }) => {
    api.policy = policy(30);
    await openManagement(page);
    await days(page).fill('90');
    await expect(deletionWarning(page)).toHaveCount(0);
    await previewButton(page).click();
    await saveButton(page).click();
    await expect(confirmDialog(page)).toBeVisible();
    await expect(confirmDialog(page).getByRole('alert', { name: 'Existing data deletion warning' })).toHaveCount(0);
    await expect(deletionConfirmation(page)).toHaveCount(0);
    await expect(confirmSave(page)).toBeEnabled();
    await confirmSave(page).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes[0].retention_days).toBe(90);
    expect(api.writes[0].confirm_deletion).not.toBe(true);
  });

  test('ordinary desktop confirmation has a single consent and cannot authorize unknown-date cleanup', async ({ page, api }, testInfo) => {
    await openManagement(page);
    await enable(page).check();
    await previewButton(page).click();
    await expect(saveButton(page)).toBeEnabled();
    await page.setViewportSize({ width: 1280, height: 1600 });
    await page.getByRole('heading', { name: 'Data retention', exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath('retention-desktop-preview.png'), fullPage: true, animations: 'disabled' });
    await page.setViewportSize({ width: 1280, height: 720 });
    await saveButton(page).click();
    await expect(confirmDialog(page).getByRole('checkbox')).toHaveCount(1);
    await deletionConfirmation(page).check();
    await expect(confirmSave(page)).toBeEnabled();
    await page.screenshot({ path: testInfo.outputPath('retention-desktop-confirmation.png'), animations: 'disabled' });
    await confirmSave(page).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes).toEqual([{
      retention_days: 90, confirm_deletion: true,
      expected_policy_version: 'a'.repeat(64),
    }]);
    await expect(page.getByText('Prior cleanup approval pending', { exact: true })).toHaveCount(0);
    expect(api.policy.legacy_cleanup.state).toBe('none');
  });

  test('changing days or enabled state invalidates a previous preview', async ({ page, api }) => {
    await openManagement(page);
    await enableAndPreview(page);
    await days(page).fill('30');
    await expect(saveButton(page)).toBeDisabled();
    await previewButton(page).click();
    await expect(saveButton(page)).toBeEnabled();
    await enable(page).uncheck();
    await expect(saveButton(page)).toBeDisabled();
    expect(api.previews).toHaveLength(2);
    expect(api.writes).toHaveLength(0);
  });

  test('a changed policy requires refreshed settings and a new preview without retrying old consent', async ({ page, api }) => {
    api.policy = policy(90);
    api.saveError = { code: 'retention_policy_changed', message: 'The retention policy changed. Refresh settings and review a new preview before saving.' };
    await openManagement(page);
    await days(page).fill('30');
    await previewButton(page).click();
    await saveButton(page).click();
    await deletionConfirmation(page).check();
    await confirmSave(page).click();
    await expect(page.getByRole('alert').filter({ hasText: /policy changed.*new preview/i })).toBeVisible();
    await expect(saveButton(page)).toBeDisabled();
    expect(api.writes).toHaveLength(1);
    api.saveError = null;
    await page.getByRole('button', { name: 'Refresh settings', exact: true }).click();
    await expect(days(page)).toHaveValue('90');
    await days(page).fill('30');
    await previewButton(page).click();
    await expect(saveButton(page)).toBeEnabled();
    await saveButton(page).click();
    await expect(deletionConfirmation(page)).not.toBeChecked();
    await deletionConfirmation(page).check();
    await confirmSave(page).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes).toHaveLength(2);
    expect(api.writes[1]).toEqual({
      retention_days: 30, expected_policy_version: 'a'.repeat(64), confirm_deletion: true,
    });
  });

  test('disabling a prior cleanup approval cancels it and removes the pending notice', async ({ page, api }) => {
    api.policy = policy(90);
    api.policy.legacy_cleanup = {
      state: 'pending', requested_count: 3, pending_count: 2,
      cleared_count: 1, skipped_count: 0, cancelled_count: 0,
      approved_at: '2026-10-04T12:00:00Z', finished_at: null,
    };
    await openManagement(page);
    await expect(page.getByText('Prior cleanup approval pending', { exact: true })).toBeVisible();
    await enable(page).uncheck();
    await previewButton(page).click();
    await saveButton(page).click();
    await expect(confirmDialog(page).getByText(/cancel/i).first()).toBeVisible();
    await confirmSave(page).click();
    await expect(confirmDialog(page)).not.toBeVisible();
    expect(api.writes[0].retention_days).toBeNull();
    expect(api.writes[0].clear_unverifiable_analyses).not.toBe(true);
    expect(api.writes[0].confirm_legacy_deletion).not.toBe(true);
    await expect(page.getByRole('status').filter({ hasText: /prior cleanup approval has been cancelled/i })).toBeVisible();
    await expect(page.getByText('Prior cleanup approval pending', { exact: true })).toHaveCount(0);
    await page.reload();
    await expandRetention(page);
    await expect(enable(page)).not.toBeChecked();
    await expect(page.getByText('Prior cleanup approval pending', { exact: true })).toHaveCount(0);
    expect(api.policy.legacy_cleanup.state).toBe('cancelled');
  });

  test('preview failure stays read-only and a fresh preview can recover', async ({ page, api }) => {
    api.previewError = 'Retention preview temporarily unavailable.';
    await openManagement(page);
    await enable(page).check();
    await previewButton(page).click();
    await expect(page.getByText(api.previewError, { exact: true }).first()).toBeVisible();
    await expect(saveButton(page)).toBeDisabled();
    expect(api.writes).toHaveLength(0);
    api.previewError = null;
    await previewButton(page).click();
    await expect(saveButton(page)).toBeEnabled();
    expect(api.previews).toHaveLength(2);
  });

  test('a changed session blocks saving a preview approved under the earlier account', async ({ page, api }) => {
    await openManagement(page);
    await enableAndPreview(page);
    await saveButton(page).click();
    await deletionConfirmation(page).check();
    await page.evaluate(() => localStorage.setItem('auth_token', 'another-mocked-session'));
    await confirmSave(page).click();
    await expect(page.getByText('Your session changed. Refresh settings before continuing.', { exact: true })).toBeVisible();
    await expect(saveButton(page)).toBeDisabled();
    expect(api.writes).toHaveLength(0);
  });

  test('a preview from a different organization cannot be approved', async ({ page, api }) => {
    api.previewOrganizationId = 42;
    await openManagement(page);
    await enable(page).check();
    await previewButton(page).click();
    await expect(page.getByRole('alert').filter({ hasText: /organization changed/i })).toBeVisible();
    await expect(saveButton(page)).toBeDisabled();
    expect(api.writes).toHaveLength(0);
  });

  test('switching accounts during awaited identity verification cannot dispatch the earlier save', async ({ page, api }) => {
    await openManagement(page);
    await enableAndPreview(page);
    await saveButton(page).click();
    await deletionConfirmation(page).check();
    const identityRequests = api.identityRequests;
    let release: () => void = () => {};
    api.pauseNextIdentity = new Promise<void>(resolve => { release = resolve; });
    await confirmSave(page).click();
    await expect.poll(() => api.identityRequests).toBeGreaterThan(identityRequests);
    await page.evaluate(() => localStorage.setItem('auth_token', 'changed-during-verification'));
    release();
    await expect(page.getByRole('alert').filter({ hasText: /session changed/i })).toBeVisible();
    await expect(saveButton(page)).toBeDisabled();
    expect(api.writes).toHaveLength(0);
  });

  test('membership changing under the same token blocks saving in the new organization', async ({ page, api }) => {
    await openManagement(page);
    await enableAndPreview(page);
    await saveButton(page).click();
    await deletionConfirmation(page).check();
    api.identity.organization_id = 42;
    await confirmSave(page).click();
    await expect(page.getByRole('alert').filter({ hasText: /organization.*changed|role.*changed|account.*changed/i })).toBeVisible();
    await expect(saveButton(page)).toBeDisabled();
    expect(api.writes).toHaveLength(0);
  });

  test('refresh discards unsaved edits and loads the current cleanup status', async ({ page, api }) => {
    api.policy = policy(90);
    await openManagement(page);
    await days(page).fill('30');
    api.policy = policy(120);
    api.policy.cleanup_status = cleanupStatus({
      state: 'succeeded', last_attempt_at: '2026-10-05T12:00:00Z',
      last_finished_at: '2026-10-05T12:01:00Z', last_success_at: '2026-10-05T12:01:00Z',
      counts: { ...cleanupStatus().counts, analysis_results_expired: 2 },
    });
    await page.getByRole('button', { name: 'Refresh settings', exact: true }).click();
    await expect(days(page)).toHaveValue('120');
    await expect(cleanupPanel(page)).toContainText('Automatic cleanup status: Succeeded');
    await expect(saveButton(page)).toBeDisabled();
    expect(api.writes).toHaveLength(0);
  });

  test('mobile preview and single confirmation fit without horizontal page overflow', async ({ page, api }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openManagement(page);
    await enable(page).check();
    await previewButton(page).click();
    await expect(saveButton(page)).toBeEnabled();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.getByRole('heading', { name: 'Deletion preview', exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath('retention-mobile-preview.png'), fullPage: true, animations: 'disabled' });
    await saveButton(page).click();
    await expect(deletionConfirmation(page)).toBeVisible();
    await expect(confirmDialog(page).getByRole('checkbox')).toHaveCount(1);
    await page.screenshot({ path: testInfo.outputPath('retention-mobile-confirmation.png'), animations: 'disabled' });
    await deletionConfirmation(page).check();
    await expect(confirmSave(page)).toBeEnabled();
    await expect(confirmDialog(page).getByRole('button', { name: 'Cancel', exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(api.writes).toHaveLength(0);
  });
});
