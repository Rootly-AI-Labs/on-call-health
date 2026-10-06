import { test as base, expect, type Page } from '@playwright/test';
import type { AnalysisResult } from '../src/lib/types';

const FIRST_ID = '201';
const SECOND_ID = '202';
const FIRST_LABEL = 'Retention cached report';
const SECOND_LABEL = 'Retention current report';
const FIRST_MEMBER = 'Cached Report Member';
const SECOND_MEMBER = 'Current Report Member';

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
    created_at: '2026-05-01T12:00:00Z', completed_at: '2026-05-01T12:01:00Z',
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

type DashboardApi = {
  expired: Set<string>;
  reads: string[];
  summariesIncludeResults: boolean;
};

// This suite uses a fabricated, locally decoded JWT and intercepts every API
// request. It does not sign in, change retention policy, or reach application data.
const test = base.extend<{ api: DashboardApi }>({
  api: async ({ page, baseURL }, use) => {
    const api: DashboardApi = { expired: new Set(), reads: [], summariesIncludeResults: false };
    const reports = [report(FIRST_ID, FIRST_LABEL, FIRST_MEMBER), report(SECOND_ID, SECOND_LABEL, SECOND_MEMBER)];
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
          'access-control-allow-methods': 'GET,OPTIONS',
        },
      });
      if (request.method() === 'OPTIONS') {
        await reply({});
        return;
      }
      if (apiPath && request.method() !== 'GET') {
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
        await reply(null);
        return;
      }
      const analysisMatch = url.pathname.match(/^\/analyses\/(?:by-id\/)?([^/]+)$/);
      if (analysisMatch) {
        const item = reports.find(value => value.id === analysisMatch[1] || value.uuid === analysisMatch[1]);
        if (item) {
          api.reads.push(item.id);
          await reply(api.expired.has(item.id)
            ? { detail: 'Analysis results are unavailable under the organization data retention policy.' }
            : item, api.expired.has(item.id) ? 410 : 200);
          return;
        }
      }
      if (url.pathname === '/rootly/integrations') {
        await reply({ integrations: [{
          id: 61, name: 'Retention test integration', organization_name: 'Retention Test',
          total_users: 1, is_default: true, created_at: '2026-05-01T12:00:00Z',
          last_used_at: null, token_suffix: 'mock', platform: 'rootly',
        }] });
        return;
      }
      if (url.pathname === '/pagerduty/integrations') {
        await reply({ integrations: [] });
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
