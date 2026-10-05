# Organization data retention implementation tracker

This document tracks implementation and verification of automatic deletion after an organization administrator selects a retention period in days. It is the shared record for decisions, code changes, tests, and user verification throughout the work.

Branch: `feat/org-data-retention`

Last updated: October 4, 2026

Current status: The user verified coverage, event age, the disabled default, and whole-result expiry for mixed-age analyses. Steps 1 through 3 are complete with 142 passing PostgreSQL tests across policy and preview. No retention deletion jobs have been implemented or run.

## Agreed direction

- Configure retention in Organization Management using organization admin permissions.
- Apply one policy to the organization, rather than individual members or teams.
- Enforce the policy automatically with a daily backend job.
- Support the same behavior in hosted and self-hosted installations.
- Keep accounts, memberships, and integration credentials available for continued use.
- Cover analysis results and historical metrics plus survey responses.
- Determine expiry from underlying event age; survey responses use their submission timestamp.
- Keep retention disabled until an organization admin explicitly enables it.
- Expire the entire analysis result when it contains expired events, even if it also contains recent events; regeneration must use the retained window.

The company requested automatic deletion after N days. Manual deletion by date range and deletion of the organization itself are separate features.

## Implementation sequence

| Step | Work | Status | Verification before moving on |
| --- | --- | --- | --- |
| 1 | Define covered data, age rules, and relationships | Complete | User verified coverage, event age, disabled default, and whole-result expiry |
| 2 | Add the organization policy and admin API | Complete | 55 PostgreSQL integration tests passed; independent code review found no actionable issues |
| 3 | Build a read-only cleanup preview | Complete | 87 preview tests passed, including cutoff boundaries, full-result expiry, and read-only behavior |
| 4 | Implement deletion and dependency handling | Not started | Tests prove correct deletion, isolation, repeatability, and failure handling |
| 5 | Add the admin settings UI | Not started | User checks saving, explanation, preview, and confirmation behavior |
| 6 | Schedule daily cleanup and record outcomes | Not started | Tests cover overlap prevention, policy changes, failure reporting, and retry |
| 7 | Verify the full flow in staging | Not started | User verifies the feature with controlled data before pilot activation |

Each step will update this document with changes, test results, unresolved issues, and the verification question for the next step. Ask for verification at meaningful product milestones, rather than for every routine code edit.

## Step 1 findings

These findings come from source inspection. A read-only query also verified the five live foreign keys referencing analyses and survey responses in the local PostgreSQL database. No application data was changed.

| Data | Source | Organization and age fields | Proposed treatment |
| --- | --- | --- | --- |
| Analysis results and embedded historical metrics | `backend/app/models/analysis.py` | Nullable `organization_id`; `created_at`, `completed_at`; JSON `results` | Included. Results may contain events older than the analysis itself |
| Survey responses and comments | `backend/app/models/user_burnout_report.py` | Nullable `organization_id`; `submitted_at`; optional `analysis_id` | Included. Age responses independently from analyses |
| Survey delivery and reminder records | `backend/app/models/survey_period.py` | Required `organization_id`; period dates; optional `response_id` | Review expired records and links to deleted responses; preserve active delivery behavior |
| Analysis mapping records | `backend/app/models/integration_mapping.py` | Optional `analysis_id` | Remove mappings belonging to deleted analyses; source defines a database cascade |
| Analysis notifications | `backend/app/models/user_notification.py` | Nullable `organization_id`; optional `analysis_id`; content and action URL | Remove or sanitize linked content; avoid links to deleted analyses |
| Digest send metadata | `backend/app/models/weekly_digest_log.py` | `user_id`, optional `analysis_id`, `sent_at` | Source defines SET NULL for deleted analysis references. Verify whether this metadata needs a separate retention period |
| Cached API and on-call data | `backend/app/core/api_cache.py`, `backend/app/core/oncall_cache.py` | Cache keys and expiry rather than uniform organization foreign keys | Review invalidation and TTL behavior so deletion does not leave accessible copies |
| Organization policy | `backend/app/models/organization.py` | Existing JSON `settings` | Decide between validated settings storage and a dedicated column during step 2 |

### Dependency checks

- Survey responses can reference analyses. Deleting an old analysis must not accidentally erase a newer survey response; its link may need to be cleared.
- Survey periods reference survey responses. Deleting responses requires handling those references first or defining a suitable database action.
- Notifications reference analyses and can contain related text. Clearing a foreign key alone may leave retained content.
- Analysis mappings use ON DELETE CASCADE in both the model and local database.
- Digest metadata uses ON DELETE SET NULL in both the model and local database.
- The local database has no automatic delete action for survey responses linked to analyses, survey periods linked to responses, or notifications linked to analyses. Cleanup must handle those references explicitly.
- Some records have no organization ID. Do not infer ownership from email domains or delete these records blindly.
- Analyses can be running, saved, or configured for auto-refresh. Define cleanup behavior for each so retention does not interrupt work or accidentally stop future refreshes.

### Verified age semantics

Record age and source event age are different. A new analysis can contain incidents and metrics from before the retention cutoff. Deleting only old analysis records does not guarantee that all underlying data older than N days disappears.

The user chose underlying event age. Collection windows, caches, embedded results, and derived metrics must therefore respect the cutoff. The implementation must avoid importing old data again after cleanup; using analysis creation time as a fallback would weaken the chosen policy.

Implementation boundary: use UTC and expire data strictly older than `now - retention_days`. Retain timestamped records exactly at the cutoff. Date-only metrics can represent local days, so the preview uses the earliest possible day start at UTC+14 as a conservative bound. A bucket overlapping the cutoff may expire earlier than an exact timestamped event. Naive date-time strings with no timezone require review rather than a guessed offset.

### Verified result expiry behavior

An analysis combines incident data, survey scores, historical metrics, insights, and aggregate team scores. Removing individual old events from its JSON would leave their contribution in the aggregate scores. The user approved expiring the complete analysis result when its oldest covered event or trustworthy collection-window start crosses the cutoff. This can also remove newer events in that result; a new analysis can regenerate results from the retained window.

Saved analyses would follow the same policy. Auto-refresh scheduling configuration must survive expiry separately from expired result content. Running jobs must recheck the policy when storing results. Missing or unreliable coverage bounds must be handled conservatively rather than by analysis creation time.

The normal live survey query in `backend/app/api/endpoints/analyses.py` currently lacks an organization filter. This must be corrected before using those responses in organization-scoped retention results. Jira and Linear result payloads also lack sufficient event timestamps, so their collection and coverage handling need additional work before strict retention can be claimed. These are findings for the enforcement steps, not completed fixes.

## Step 2 implementation

Policy storage uses the existing `Organization.settings` JSON under `data_retention`; no database migration is needed for this step. Replacing the JSON value ensures SQLAlchemy persists the update, and a row lock protects concurrent updates. Other organization settings are preserved.

- `GET /auth/organizations/retention` returns the current organization's policy; active members can view it.
- `PUT /auth/organizations/retention` accepts `retention_days` as null for disabled, or a strict integer from 1 through 3650. Only active organization admins may write.
- Organization ownership comes from the authenticated user, not a client-supplied ID. Unknown request fields are rejected.
- Enabling or shortening retention requires `confirm_deletion: true`; disabling or lengthening does not. This prepares the contract for later destructive enforcement.
- Responses identify event age and both analysis and survey scope. Changes record time and actor; repeated identical saves preserve the original metadata.
- These endpoints configure policy only. Cleanup, collection-window filtering, and the UI have not been implemented. No policy has been enabled on the current application database.

Implementation files: `backend/app/services/data_retention.py`, `backend/app/api/endpoints/retention.py`, and router registration in `backend/app/main.py`.

Tests: `backend/tests/test_retention_policy.py`. All 55 cases passed against the separate `oncall_health_retention_test` database. Each case rolls back its records, including writes committed by the endpoint. Tests skip without an explicit test database URL and reject URLs that do not identify a PostgreSQL database named with `retention_test`.

To repeat this step's checks with the local Docker setup:

```powershell
docker compose exec -T -e RETENTION_TEST_DATABASE_URL=postgresql://postgres:password@postgres:5432/oncall_health_retention_test backend python -m pytest tests/test_retention_policy.py -q
```

## Step 3 implementation

`POST /auth/organizations/retention/preview` is an admin-only, read-only endpoint. An empty request object uses the saved policy; an explicit `retention_days` previews a proposed setting without saving it. Explicit null previews disabled retention. This lets an admin inspect consequences before enabling a policy.

The response includes the evaluation time, cutoff, counts for analyses and surveys, dependency counts, and up to 100 analysis samples with IDs and explanations. It returns no result payloads, emails, comments, integration tokens, or credentials. Samples are limited, while aggregate counts cover all scoped rows. Database queries stream one large analysis result at a time and batch dependency counts.

Analysis categories:

- **Expired:** a recognized event or valid coverage window is older than the cutoff; the whole result expires.
- **Retained:** incident coverage is trustworthy and no known old event or unresolved source coverage was found.
- **Unverifiable:** age, timezone, or enrichment coverage is missing or unreliable. Recent sampled incidents cannot prove the age of the aggregate result.
- **Deferred:** a pending or running analysis must be handled when its results are written.
- **Empty:** no result content exists; configuration is preserved.

Survey responses expire independently using their own `submitted_at`. Newer responses linked to an expired analysis are counted for detachment, not deletion. Preview also counts analysis mappings, notifications, survey-period references, and digest references. Missing or mismatched organization ownership is reported separately for review.

Active integrations with stored credentials make an expired result a regeneration candidate; the preview does not contact providers, guarantee access, regenerate results, invalidate caches, delete data, or save policy changes. Disabled policies return organization totals with no expiry candidates.

Implementation: `backend/app/services/retention_preview.py` and the preview route in `backend/app/api/endpoints/retention.py`. Tests: `backend/tests/test_retention_preview.py`.

Verification: all 87 preview tests and 55 policy tests passed against the dedicated PostgreSQL test database. Tests cover mixed-age results, surveys, local-day boundaries, malformed and missing timestamps, legacy enrichment without inclusion flags, organization isolation, dependent records, sample limits, and repeated previews. SQL write interception, before-and-after table comparisons, and commit/autoflush guards verify that preview itself does not write data. Only an existing SQLAlchemy deprecation warning appeared.

Run both suites:

```powershell
docker compose exec -T -e RETENTION_TEST_DATABASE_URL=postgresql://postgres:password@postgres:5432/oncall_health_retention_test backend python -m pytest tests/test_retention_policy.py tests/test_retention_preview.py -q
```

## Decisions awaiting verification

| Decision | Proposal | Status |
| --- | --- | --- |
| Initial coverage | Analysis results and historical metrics plus survey responses | Confirmed by user |
| How data age is measured | Underlying event age; survey submission age | Confirmed by user |
| Existing organization default | Disabled until an admin explicitly enables retention | Confirmed by user |
| Mixed-age analysis results | Expire the complete result when its oldest covered event crosses the cutoff; regenerate from retained data | Confirmed by user |
| Saved and auto-refresh analyses | Saved data should not bypass an enabled policy; retain scheduling configuration where needed | Awaiting design review |
| Running analyses | Avoid deleting in-progress work; enforce the chosen age rule when results are stored | Awaiting design review |
| Related metadata | Define handling of survey periods, notifications, digest records, and caches | Awaiting dependency review |
| Allowed number of days | Strict whole number from 1 through 3650; null disables the policy | Implemented in step 2 |
| Backups and operational logs | Document a separate policy; database cleanup alone does not erase backups or logs | Awaiting deployment review |

## Test strategy

Use a separate PostgreSQL database with disposable fixtures. Do not run destructive retention tests against the current local application database. A feature branch does not isolate Docker volumes.

Inject a fixed clock into cleanup tests. Seed data around the cutoff rather than waiting for days to pass.

| Test area | Required evidence |
| --- | --- |
| Policy permissions | Organization admin succeeds; member and admin from another organization fail |
| Policy validation | Reject invalid values and preserve saved values on reload |
| Default behavior | No policy means no automatic deletion |
| Time boundaries | Older data expires; newer data and exact-cutoff data remain under the proposed boundary |
| Organization isolation | Only the target organization's eligible records are affected |
| Dependencies | No broken references; newer linked records survive as designed |
| Preserved configuration | Accounts, memberships, credentials, and future collection remain functional |
| Saved and running data | Behavior matches the verified policy for saved, running, and auto-refresh analyses |
| Event age | Old underlying data is excluded even from newly generated results |
| Preview consistency | Preview and deletion use the same eligibility logic, with cutoff and policy recorded |
| Repeated runs | Second cleanup safely finds nothing already deleted |
| Failure handling | Transaction behavior is correct; failures are visible and retries are safe |
| Scheduler | Multiple processes cannot perform overlapping cleanup for the same organization |
| UI flow | Admin sets policy, reviews consequences, confirms, reloads, and sees the saved value |

## Verification log

| Date | Step | Work or check | Outcome |
| --- | --- | --- | --- |
| October 4, 2026 | 1 | Inspected organization, analysis, survey, mapping, notification, and digest models | Initial data map recorded |
| October 4, 2026 | 1 | Checked dependency declarations, migration sources, and live foreign keys using a read-only query | Confirmed five dependencies; mappings cascade, digest references become NULL, and three references need explicit handling |
| October 4, 2026 | 1 | User verified coverage, age semantics, and the default policy in chat | Both analyses and survey responses; event age; disabled initially |
| October 4, 2026 | 1 | Reviewed event windows, derived metrics, caches, survey queries, and auto-refresh | Whole-result expiry proposal recorded; ingestion filters, missing timestamps, and organization scoping need enforcement work |
| October 4, 2026 | 2 | Added policy storage and current-organization GET and PUT endpoints | Implemented; no policy changes made to the current application database |
| October 4, 2026 | 2 | Checked API registration and local health | GET and PUT appear in OpenAPI; backend remains healthy |
| October 4, 2026 | 2 | Ran 55 PostgreSQL integration tests on the dedicated test database | All passed; only an existing SQLAlchemy deprecation warning |
| October 4, 2026 | 2 | Independently reviewed permissions, validation, JSON persistence, locking, and confirmation | No actionable issues found |
| October 4, 2026 | 1 | User approved whole-result expiry for mixed-age analyses and regeneration from retained data | Confirmed in chat |
| October 4, 2026 | 3 | Implemented proposed-policy preview, event-age classification, dependency counts, and capped samples | Read-only; no changes made to the current application database |
| October 4, 2026 | 3 | Reviewed eligibility and large-payload handling; corrected legacy source detection and malformed Slack timestamps | Review findings addressed; analysis result streaming reduced to one payload per batch |
| October 4, 2026 | 3 | Ran combined policy and preview tests including regression cases | 142 passed: 55 policy plus 87 preview; only an existing SQLAlchemy deprecation warning |
| October 4, 2026 | 3 | Checked preview registration and local API health | Preview appears in OpenAPI and backend remains healthy |

## Next action

Implement step 4 cleanup with explicit dependency handling and retained-window regeneration safeguards. Do not claim event-age enforcement until collection paths, missing provenance, caches, running jobs, and auto-refresh continuity are handled. Continue using normal chat for verification questions because the terminal question widget was inaccessible.
