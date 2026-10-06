import { test as base, expect, type Page } from '@playwright/test';
import type { AnalysisResult } from '../src/lib/types';

const FIRST_ID = '201';
const SECOND_ID = '202';
const AUTOMATIC_ID = '203';
const FIRST_LABEL = 'Retention cached report';
const SECOND_LABEL = 'Retention current report';
const FIRST_MEMBER = 'Cached Report Member';
const SECOND_MEMBER = 'Current Report Member';
const AUTOMATIC_MEMBER = 'Automatic Report Member';

function report(id: string, label: string, memberName: string): AnalysisResult {
  const member = {
    user_id: `member-${id}`, user_name: memberName,
    user_email: `member-${id}@example.test`, cbi_score: 35, risk_score_100: 35, incident_count: 1,
    factors: { workload: 10, after_hours: 0, weekend_work: 0, incident_load: 10, response_time: 0 },
    metrics: { avg_response_time_minutes: 5, after_hours_percentage: 0, weekend_percentage: 0 },
  };
  return {
    id, uuid: `00000000-0000-4000-8000-${id.padStart(12, '0')}`,
    integration_id: 61, integration_name: label, platform: 'rootly',
    created_at: '2026-05-01T12:00:00Z', completed_at: '2026-10-06T12:01:00Z',
    results_generated_at: id === SECOND_ID ? null : '2026-10-05T12:01:00Z',
    status: 'completed', time_range: 180, is_saved: true, is_auto_refresh: false,
    config: { include_github: false, include_slack: false },
    analysis_data: {
      total_incidents: 1,
      data_sources: { incident_data: true, github_data: false, slack_data: false },
      team_health: {
        overall_score: 35, health_status: 'fair',
        risk_distribution: { low: 1, medium: 0, high: 0, critical: 0 },
      },
      team_analysis: { members: [member] },
      insights: [], recommendations: [],
    },
  };
}

type ReadOutcome = 200 | 404 | 410 | 503 | 'aborted';
type BlockedRead = { started: Promise<void>; release: (outcome: ReadOutcome) => void };

type DashboardApi = {
  expired: Set<string>;
  reads: string[];
  summariesIncludeResults: boolean;
  hasAutomaticReport: boolean;
  automaticStatus: 'completed' | 'pending' | 'running' | 'failed';
  automaticFailure: string | null;
  automaticOutcomes: ReadOutcome[];
  allowAutomaticCancel: boolean;
  allowAnalysisRun: boolean;
  holdRead: (id: string) => BlockedRead;
};

// This suite uses a fabricated, locally decoded JWT and intercepts every API
// request. It does not sign in, change retention policy, or reach application data.
const test = base.extend<{ api: DashboardApi }>({
  api: async ({ page, baseURL }, use) => {
    const heldReads = new Map<string, BlockedRead & {
      response: Promise<ReadOutcome>; markStarted: () => void;
    }>();
    const api: DashboardApi = {
      expired: new Set(), reads: [], summariesIncludeResults: false, hasAutomaticReport: false,
      automaticStatus: 'completed', automaticOutcomes: [],
      automaticFailure: null,
      allowAutomaticCancel: false,
      allowAnalysisRun: false,
      holdRead: id => {
        let markStarted!: () => void;
        let release!: (outcome: ReadOutcome) => void;
        const started = new Promise<void>(resolve => { markStarted = resolve; });
        const response = new Promise<ReadOutcome>(resolve => { release = resolve; });
        heldReads.set(id, { started, response, release, markStarted });
        return { started, release };
      },
    };
    const reports = [report(FIRST_ID, FIRST_LABEL, FIRST_MEMBER), report(SECOND_ID, SECOND_LABEL, SECOND_MEMBER)];
    const automaticReport = {
      ...report(AUTOMATIC_ID, 'Retention automatic report', AUTOMATIC_MEMBER), is_auto_refresh: true,
    };
    const origin = new URL(baseURL || 'http://localhost:3000').origin;
    const unexpectedMutations: string[] = [];

    await page.addInitScript(() => {
      const payload = btoa(JSON.stringify({ sub: '7', exp: Math.floor(Date.now() / 1000) + 3600 }))
        .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
      localStorage.setItem('auth_token', `mock.${payload}.mock`);
      localStorage.setItem('user_id', '7');
      localStorage.setItem('user_name', 'Retention Dashboard Tester');
      localStorage.setItem('user_email', 'retention-dashboard@example.test');
      localStorage.setItem('user_role', 'admin');
      localStorage.setItem('user_organization_id', '41');
      localStorage.setItem('onboarding-seen', 'true');
      localStorage.setItem('onboarding-seen-7', 'true');
    });

    await page.route('**/*', async route => {
      const request = route.request();
      const url = new URL(request.url());
      const apiPath = /^\/(?:analyses|auth|rootly|pagerduty|integrations|api\/notifications)(?:\/|$)/.test(url.pathname);
      if (url.origin === origin && !apiPath) {
        await route.continue();
        return;
      }
      const reply = (body: unknown, status = 200) => route.fulfill({
        status, contentType: 'application/json', body: JSON.stringify(body),
        headers: {
          'access-control-allow-origin': origin,
          'access-control-allow-credentials': 'true',
          'access-control-allow-headers': 'authorization,content-type',
          'access-control-allow-methods': 'GET,DELETE,OPTIONS',
        },
      });
      if (request.method() === 'OPTIONS') {
        await reply({});
        return;
      }
      if (apiPath && request.method() !== 'GET') {
        if (api.allowAnalysisRun && request.method() === 'POST' && url.pathname === '/analyses/run') {
          await reply({ id: Number(AUTOMATIC_ID) });
          return;
        }
        if (api.allowAutomaticCancel && request.method() === 'DELETE'
          && url.pathname === `/analyses/${AUTOMATIC_ID}`) {
          await reply({ success: true });
          return;
        }
        unexpectedMutations.push(`${request.method()} ${url.pathname}`);
        await reply({ detail: 'Mutations are blocked in this browser test.' }, 405);
        return;
      }
      if (url.pathname === '/auth/user/me') {
        await reply({ id: 7, email: 'retention-dashboard@example.test', name: 'Retention Dashboard Tester', role: 'admin', organization_id: 41 });
        return;
      }
      if (url.pathname === '/analyses') {
        await reply({
          analyses: reports.map(item => api.summariesIncludeResults ? item : { ...item, analysis_data: undefined }),
          total: reports.length,
        });
        return;
      }
      if (url.pathname === '/analyses/auto-refresh') {
        await reply(api.hasAutomaticReport ? { ...automaticReport, status: api.automaticStatus, analysis_data: undefined } : null);
        return;
      }
      const analysisMatch = url.pathname.match(/^\/analyses\/(?:by-id\/)?([^/]+)$/);
      if (analysisMatch) {
        const automatic = { ...automaticReport, status: api.automaticStatus };
        const item = [...reports, automatic].find(value => value.id === analysisMatch[1] || value.uuid === analysisMatch[1]);
        if (item) {
          api.reads.push(item.id);
          const replyOutcome = async (outcome: ReadOutcome) => {
            const body = item.id === AUTOMATIC_ID ? {
              ...item, status: api.automaticStatus,
              analysis_data: api.automaticStatus === 'completed' ? automaticReport.analysis_data : {},
              error_message: api.automaticStatus === 'failed' ? api.automaticFailure : undefined,
            } : item;
            if (outcome === 'aborted') await route.abort();
            else await reply(outcome === 200
              ? body
              : { detail: outcome === 404 ? 'Analysis not found' : 'Synthetic unavailable analysis' }, outcome);
          };
          const held = heldReads.get(item.id);
          if (held) {
            held.markStarted();
            const outcome = await held.response;
            await replyOutcome(outcome);
            return;
          }
          if (item.id === AUTOMATIC_ID && api.automaticOutcomes.length) {
            await replyOutcome(api.automaticOutcomes.shift()!);
            return;
          }
          await replyOutcome(api.expired.has(item.id) ? 410 : 200);
          return;
        }
      }
      if (url.pathname === '/rootly/integrations') {
        await reply({ integrations: [{
          id: 61, name: 'Retention test integration', organization_name: 'Retention Test',
          total_users: 1, is_default: true, created_at: '2026-05-01T12:00:00Z',
          last_used_at: null, token_suffix: 'mock', platform: 'rootly',
          permissions: { users: { access: true }, incidents: { access: true } },
        }] });
        return;
      }
      if (url.pathname === '/pagerduty/integrations') {
        await reply({ integrations: [] });
        return;
      }
      if (url.pathname === '/analyses/validate-integrations') {
        await reply({ all_valid: true });
        return;
      }
      if (url.pathname.startsWith('/integrations/')) {
        await reply({ connected: false, integration: null, mappings: [], openai_enabled: false, anthropic_enabled: false });
        return;
      }
      if (url.pathname.startsWith('/api/notifications')) {
        await reply({ notifications: [], unread_count: 0, has_more: false });
        return;
      }
      // Historical trends and all other off-origin requests remain isolated.
      await reply({ daily: [], weekly: [], monthly: [], members: [], users: [], integrations: [] });
    });

    await use(api);
    for (const held of heldReads.values()) held.release('aborted');
    expect(unexpectedMutations, 'Dashboard report reads must not mutate application data').toEqual([]);
  },
});

test.use({
  storageState: { cookies: [], origins: [] },
  ...(process.env.RETENTION_E2E_CHROMIUM_PATH
    ? { launchOptions: { executablePath: process.env.RETENTION_E2E_CHROMIUM_PATH } }
    : {}),
});

const savedReport = (page: Page, label: string) => page.getByRole('button', { name: new RegExp(label) });

async function openReport(page: Page, id: string, memberName: string) {
  await page.goto(`/dashboard?analysis=${id}`);
  await expect(page.getByText(memberName, { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Export', exact: true })).toBeVisible();
  await expect(savedReport(page, FIRST_LABEL)).toBeEnabled();
  await expect(savedReport(page, SECOND_LABEL)).toBeEnabled();
  await expect(savedReport(page, FIRST_LABEL)).toContainText('Time range: 180 days');
  await expect(savedReport(page, FIRST_LABEL)).toContainText('Created May 1, 2026');
  await expect(savedReport(page, SECOND_LABEL)).toContainText('Created May 1, 2026');
}

async function expectUnavailableReport(page: Page) {
  await expect(page.getByText(FIRST_MEMBER, { exact: true })).toHaveCount(0);
  await expect(page.getByText(SECOND_MEMBER, { exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Export', exact: true })).toHaveCount(0);
  await expect(page.getByText("Analysis results are unavailable under your organization's data retention policy.", { exact: true })).toBeVisible();
  // Retention clears report content, while saved configuration remains available.
  await expect(savedReport(page, FIRST_LABEL)).toBeVisible();
}

test.describe('Dashboard retention read enforcement', () => {
  test('a newly started report stops polling on retention 410 and falls back', async ({ page, api }) => {
    api.allowAnalysisRun = true;
    api.automaticOutcomes = [410];
    await openReport(page, FIRST_ID, FIRST_MEMBER);
    await page.getByRole('button', { name: 'New Analysis', exact: true }).first().click();
    await page.getByRole('dialog', { name: 'Start New Analysis' }).getByRole('button', { name: 'Start Analysis', exact: true }).click();
    await expect(page.getByText("Analysis results are unavailable under your organization's data retention policy.", { exact: true })).toBeVisible();
    await expect(page.getByText(FIRST_MEMBER, { exact: true })).toBeVisible();
    expect(api.reads.filter(id => id === AUTOMATIC_ID)).toHaveLength(1);
    expect(await page.evaluate(() => localStorage.getItem('running_analysis_id'))).toBeNull();
  });

  test('a late 410 from a newly started report cannot clear a newer saved selection', async ({ page, api }) => {
    api.allowAnalysisRun = true;
    api.allowAutomaticCancel = true;
    await openReport(page, FIRST_ID, FIRST_MEMBER);
    const held = api.holdRead(AUTOMATIC_ID);
    try {
      await page.getByRole('button', { name: 'New Analysis', exact: true }).first().click();
      await page.getByRole('dialog', { name: 'Start New Analysis' }).getByRole('button', { name: 'Start Analysis', exact: true }).click();
      await held.started;
      await page.getByRole('button', { name: 'Cancel Analysis', exact: true }).click();
      await savedReport(page, SECOND_LABEL).click();
      await expect(page.getByText(SECOND_MEMBER, { exact: true })).toBeVisible();
      const response = page.waitForResponse(value => new URL(value.url()).pathname === `/analyses/${AUTOMATIC_ID}` && value.status() === 410);
      held.release(410);
      await (await response).finished();
      await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
      await expect(page.getByText(SECOND_MEMBER, { exact: true })).toBeVisible();
      await expect(page).toHaveURL(new RegExp(`analysis=${SECOND_ID}(?:&|$)`));
      await expect(page.getByText("Analysis results are unavailable under your organization's data retention policy.", { exact: true })).toHaveCount(0);
    } finally { held.release('aborted'); }
  });

  for (const status of ['pending', 'running'] as const) {
    test(`stops ${status} report polling immediately on retention 410`, async ({ page, api }) => {
      api.hasAutomaticReport = true;
      api.automaticStatus = status;
      api.automaticOutcomes = [410];
      await page.goto('/dashboard');
      await expect(page.getByText(FIRST_MEMBER, { exact: true })).toBeVisible({ timeout: 5000 });
      await expect(page.getByText("Analysis results are unavailable under your organization's data retention policy.", { exact: true })).toBeVisible();
      expect(api.reads.filter(id => id === AUTOMATIC_ID)).toHaveLength(1);
      expect(await page.evaluate(() => localStorage.getItem('running_analysis_id'))).toBeNull();
    });
  }

  test('initial loading skips an unavailable newest saved report', async ({ page, api }) => {
    api.expired.add(FIRST_ID);
    await page.goto('/dashboard');
    await expect(page.getByText(SECOND_MEMBER, { exact: true })).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`analysis=${SECOND_ID}(?:&|$)`));
    expect(api.reads).toContain(FIRST_ID);
    expect(api.reads).toContain(SECOND_ID);
  });

  test('initial loading leaves no stale report when all saved reports are unavailable', async ({ page, api }) => {
    api.expired.add(FIRST_ID);
    api.expired.add(SECOND_ID);
    await page.goto('/dashboard');
    await expect.poll(() => api.reads.includes(SECOND_ID)).toBe(true);
    await expect(page.getByText(FIRST_MEMBER, { exact: true })).toHaveCount(0);
    await expect(page.getByText(SECOND_MEMBER, { exact: true })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Export', exact: true })).toHaveCount(0);
  });

  test('a delayed initial unavailable response cannot replace a newer manual selection', async ({ page, api }) => {
    const firstRead = api.holdRead(FIRST_ID);
    await page.goto('/dashboard');
    await firstRead.started;
    await savedReport(page, SECOND_LABEL).click();
    await expect(page.getByText(SECOND_MEMBER, { exact: true })).toBeVisible();
    const secondReads = api.reads.filter(id => id === SECOND_ID).length;
    const initialResponse = page.waitForResponse(response =>
      new RegExp(`/analyses/(?:by-id/)?${FIRST_ID}$`).test(new URL(response.url()).pathname)
      && response.status() === 410);
    firstRead.release(410);
    await (await initialResponse).finished();
    await expect(page.getByText(SECOND_MEMBER, { exact: true })).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`analysis=${SECOND_ID}(?:&|$)`));
    expect(api.reads.filter(id => id === SECOND_ID)).toHaveLength(secondReads);
  });

  test('opens an available saved report when running automatic polling returns 404', async ({ page, api }) => {
    api.hasAutomaticReport = true;
    api.automaticStatus = 'running';
    api.automaticOutcomes = [404];
    await page.goto('/dashboard');
    await expect(page.getByText(FIRST_MEMBER, { exact: true })).toBeVisible({ timeout: 5000 });
    await expect(page).toHaveURL(new RegExp(`analysis=${FIRST_ID}(?:&|$)`));
    expect(api.reads.filter(id => id === AUTOMATIC_ID)).toHaveLength(1);
  });

  test('opens a saved report after automatic polling exhausts its error retries', async ({ page, api }) => {
    api.hasAutomaticReport = true;
    api.automaticStatus = 'pending';
    api.automaticOutcomes = [503, 503, 503];
    await page.goto('/dashboard');
    await expect(page.getByText(FIRST_MEMBER, { exact: true })).toBeVisible({ timeout: 25000 });
    await expect(page).toHaveURL(new RegExp(`analysis=${FIRST_ID}(?:&|$)`));
    expect(api.reads.filter(id => id === AUTOMATIC_ID)).toHaveLength(3);
    expect(await page.evaluate(() => localStorage.getItem('running_analysis_id'))).toBeNull();
  });

  test('fallback skips a saved result that has become unavailable', async ({ page, api }) => {
    api.hasAutomaticReport = true;
    api.automaticStatus = 'running';
    api.automaticOutcomes = [404];
    api.expired.add(FIRST_ID);
    await page.goto('/dashboard');
    await expect(page.getByText(SECOND_MEMBER, { exact: true })).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`analysis=${SECOND_ID}(?:&|$)`));
    expect(api.reads.filter(id => id === AUTOMATIC_ID)).toHaveLength(1);
  });

  test('a restored running report keeps polling through its initial URL read', async ({ page, api }) => {
    api.hasAutomaticReport = true;
    api.automaticStatus = 'pending';
    await page.addInitScript(id => {
      localStorage.setItem('running_analysis_id', id);
      localStorage.setItem('running_analysis_start', Date.now().toString());
    }, AUTOMATIC_ID);
    await page.goto(`/dashboard?analysis=${AUTOMATIC_ID}`);
    await expect.poll(() => api.reads.filter(id => id === AUTOMATIC_ID).length).toBeGreaterThanOrEqual(2);
    api.automaticStatus = 'completed';
    await expect(page.getByText(AUTOMATIC_MEMBER, { exact: true })).toBeVisible({ timeout: 12000 });
    await expect(page).toHaveURL(new RegExp(`analysis=${AUTOMATIC_ID}(?:&|$)`));
    expect(await page.evaluate(() => localStorage.getItem('running_analysis_id'))).toBeNull();
  });

  for (const status of ['pending', 'running'] as const) {
    for (const detailedError of [true, false]) {
      test(`shows failure after a ${status} report opened by URL fails (${detailedError ? 'specific error' : 'no error supplied'})`, async ({ page, api }) => {
        api.hasAutomaticReport = true;
        api.automaticStatus = status;
        api.automaticFailure = detailedError ? 'A temporary provider outage stopped this analysis.' : null;
        await page.goto(`/dashboard?analysis=${AUTOMATIC_ID}`);
        await expect.poll(() => api.reads.filter(id => id === AUTOMATIC_ID).length).toBeGreaterThanOrEqual(2);
        api.automaticStatus = 'failed';
        await expect(page.getByText(api.automaticFailure || 'Analysis failed. Please try again.', { exact: true })).toBeVisible({ timeout: 12000 });
        await expect(page.getByRole('heading', { name: 'Analysis Failed', exact: true })).toBeVisible();
        await expect(savedReport(page, SECOND_LABEL)).toBeEnabled();
        await expect(page.getByText('Refreshing', { exact: true })).toHaveCount(0);
        await expect(page).toHaveURL(new RegExp(`analysis=${AUTOMATIC_ID}(?:&|$)`));
        expect(await page.evaluate(() => localStorage.getItem('running_analysis_id'))).toBeNull();
        expect(api.reads.filter(id => id === FIRST_ID)).toHaveLength(0);
      });
    }
  }

  for (const [outcome, status] of [[410, 'completed'], [404, 'completed'], [200, 'completed'], [200, 'failed']] as const) {
    test(`late polling ${outcome}/${status} cannot replace a saved report selected after cancellation`, async ({ page, api }) => {
      api.hasAutomaticReport = true;
      api.automaticStatus = 'running';
      api.allowAutomaticCancel = true;
      const held = api.holdRead(AUTOMATIC_ID);
      try {
        await page.goto('/dashboard');
        await held.started;
        await page.getByRole('button', { name: 'Cancel Analysis', exact: true }).click();
        await expect(savedReport(page, SECOND_LABEL)).toBeEnabled();
        await savedReport(page, SECOND_LABEL).click();
        await expect(page.getByText(SECOND_MEMBER, { exact: true })).toBeVisible();
        const late = page.waitForResponse(response => new URL(response.url()).pathname === `/analyses/${AUTOMATIC_ID}`
          && response.status() === outcome).then(response => response.finished());
        api.automaticStatus = status;
        held.release(outcome);
        await late;
        await page.evaluate(() => new Promise<void>(resolve => {
          requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
        }));
        await expect(page.getByText(SECOND_MEMBER, { exact: true })).toBeVisible();
        await expect(page.getByText(AUTOMATIC_MEMBER, { exact: true })).toHaveCount(0);
        await expect(page).toHaveURL(new RegExp(`analysis=${SECOND_ID}(?:&|$)`));
        expect(api.reads.filter(id => id === FIRST_ID)).toHaveLength(0);
      } finally { held.release('aborted'); }
    });
  }

  for (const outcome of [410, 200, 'aborted'] as const) {
    test(`keeps the manually opened report when an older automatic read returns ${outcome}`, async ({ page, api }) => {
      api.hasAutomaticReport = true;
      const automaticRead = api.holdRead(AUTOMATIC_ID);
      try {
        await page.goto('/dashboard');
        await automaticRead.started;
        await expect(savedReport(page, SECOND_LABEL)).toBeEnabled();
        const automaticEntry = savedReport(page, 'Retention automatic report');
        await expect(automaticEntry).toContainText('Time range: 180 days');
        await expect(automaticEntry).toContainText('Created May 1, 2026');
        await savedReport(page, SECOND_LABEL).click();
        await expect(page.getByText(SECOND_MEMBER, { exact: true })).toBeVisible();
        await expect(page).toHaveURL(new RegExp(`analysis=${SECOND_ID}(?:&|$)`));
        await expect(savedReport(page, SECOND_LABEL)).toBeEnabled();

        const lateResponse = outcome === 'aborted'
          ? page.waitForEvent('requestfailed', {
            predicate: request => new URL(request.url()).pathname === `/analyses/${AUTOMATIC_ID}`,
          })
          : page.waitForResponse(response => new URL(response.url()).pathname === `/analyses/${AUTOMATIC_ID}`
            && response.status() === outcome).then(response => response.finished());
        automaticRead.release(outcome);
        await lateResponse;
        // Let the response continuation and its React update finish before checking
        // that neither the old report nor its default fallback replaced the user choice.
        await page.evaluate(() => new Promise<void>(resolve => {
          requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
        }));

        await expect(page.getByText(SECOND_MEMBER, { exact: true })).toBeVisible();
        await expect(page.getByText(FIRST_MEMBER, { exact: true })).toHaveCount(0);
        await expect(page.getByText(AUTOMATIC_MEMBER, { exact: true })).toHaveCount(0);
        await expect(page.getByRole('button', { name: 'Export', exact: true })).toBeVisible();
        await expect(page).toHaveURL(new RegExp(`analysis=${SECOND_ID}(?:&|$)`));
        expect(api.reads.filter(id => id === FIRST_ID)).toHaveLength(0);
        await expect(page.getByText("Analysis results are unavailable under your organization's data retention policy.", { exact: true })).toHaveCount(0);
        if (outcome === 200) {
          const sidebar = page.getByRole('complementary', { name: 'Analysis history' });
          await sidebar.screenshot({ path: 'test-results/sidebar-dates-desktop.png' });
          await page.setViewportSize({ width: 390, height: 844 });
          await page.reload();
          await expect(savedReport(page, SECOND_LABEL)).toBeVisible();
          await expect(savedReport(page, FIRST_LABEL)).toContainText('Created May 1, 2026');
          await expect(savedReport(page, SECOND_LABEL)).toContainText('Created May 1, 2026');
          const bounds = await sidebar.boundingBox();
          expect(bounds).not.toBeNull();
          expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(390);
          await sidebar.screenshot({ path: 'test-results/sidebar-dates-mobile.png' });
        }
      } finally {
        automaticRead.release('aborted');
      }
    });
  }

  for (const summariesIncludeResults of [false, true]) {
    test(`revalidates a previously cached saved report before display (${summariesIncludeResults ? 'full list results' : 'summary list'})`, async ({ page, api }) => {
      api.summariesIncludeResults = summariesIncludeResults;
      await openReport(page, FIRST_ID, FIRST_MEMBER);

      const secondReads = api.reads.filter(id => id === SECOND_ID).length;
      await savedReport(page, SECOND_LABEL).click();
      await expect(page.getByText(SECOND_MEMBER, { exact: true })).toBeVisible();
      await expect(page.getByText(FIRST_MEMBER, { exact: true })).toHaveCount(0);
      await expect.poll(() => api.reads.filter(id => id === SECOND_ID).length).toBeGreaterThan(secondReads);

      // The server's decision changes after the client has already cached this result.
      api.expired.add(FIRST_ID);
      const firstReads = api.reads.filter(id => id === FIRST_ID).length;
      await savedReport(page, FIRST_LABEL).click();
      await expect.poll(() => api.reads.filter(id => id === FIRST_ID).length).toBeGreaterThan(firstReads);
      await expectUnavailableReport(page);
    });
  }

  test('clears the previous report when a different saved report returns 410', async ({ page, api }) => {
    api.expired.add(FIRST_ID);
    await openReport(page, SECOND_ID, SECOND_MEMBER);

    expect(api.reads.filter(id => id === FIRST_ID)).toHaveLength(0);
    await savedReport(page, FIRST_LABEL).click();
    await expect.poll(() => api.reads.filter(id => id === FIRST_ID).length).toBe(1);
    await expectUnavailableReport(page);
  });
});
