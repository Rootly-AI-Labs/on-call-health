# Organization data retention implementation tracker

This document tracks implementation and verification of automatic deletion after an organization administrator selects a retention period in days. It is the shared record for decisions, code changes, tests, and user verification throughout the work.

Branch: `feat/org-data-retention`

Last updated: October 5, 2026

Current status: **Steps 1 through 6 are implemented** with the user's approved result generation age rule and **one normal daily cleanup at 03:00 UTC**. Failed organizations receive separate targeted retries. The original backend suite passed **649 tests**, and subsequent mock-exclusion changes passed **441 related checks**. The current settings/dashboard UI passes **34 browser scenarios**, and TypeScript passes with the committed module-resolution configuration. The user enabled a **90-day policy for the local Retention Demo organization** at October 6, 03:21 UTC; its first cleanup is due October 7, 03:00 UTC. No application cleanup has run as of the read-only verification at 03:24 UTC, and destructive automated tests used only the disposable database. Step 7, full staging verification, remains.

## Agreed direction

- Configure retention in Organization Management using organization admin permissions.
- Apply one policy to the organization, rather than individual members or teams.
- Enforce the policy automatically with a daily backend job.
- Support the same behavior in hosted and self-hosted installations.
- Keep accounts, memberships, and integration credentials available for continued use.
- Cover analysis results and historical metrics plus survey responses.
- Determine analysis expiry from when its stored result was generated; survey responses use their own submission timestamp.
- Keep retention disabled until an organization admin explicitly enables it.
- Expire the entire stored result once its generation date is older than the rolling cutoff, including embedded activity, metrics, insights and enrichments. Preserve analysis configuration.
- Preserve the requested historical analysis window. A report generated today may cover four months of source activity and remain available for N days after generation. Successfully generating its replacement starts a new lifetime; a failed attempt without a new result does not renew the old snapshot.
- Retention does not disable enrichment inputs. Existing feature settings and provider permissions continue to control collection; unrelated baseline feature limitations remain.
- Keep the settings simple: enable/disable, N days, preview, and one ordinary deletion confirmation. There is no Advanced cleanup option or new approval for deleting results with unknown dates.
- Exclude the built-in sample/demo analyses from retention. Dedicated local retention test fixtures stay eligible so automatic cleanup can still be tested.

The analysis window and retention period are independent. Four months is only the current demo's example, not a limit: a six-month analysis retains its six months of available source data, and its complete result expires N days after generation. Retention adds no analysis-window cap; the app's existing supported date-range limits still apply. The management explanation now uses general N-day wording and explicitly says retention does not shorten the requested window.

The company requested automatic deletion after N days. Manual deletion by date range and deletion of the organization itself are separate features.

## October 5 approved change: retain each generated result for N days

The user explicitly asked to replace source event-age enforcement with report/result-age retention. This specification supersedes the original event-age decisions and source exclusions recorded in the historical findings below.

- Store the server's generation timestamp in `Analysis.results_generated_at`. It is independent of the analysis row's creation date, source event dates, and terminal run-attempt bookkeeping in `completed_at`.
- Each newly stored result snapshot receives the current UTC generation timestamp. Status-only failures preserve an existing result and its timestamp. Existing successful legacy completion dates are used when available; never invent a generation time from row creation or result JSON.
- A 90-day policy allows a newly generated four-month report to retain its complete history for 90 days. Cleanup then clears the whole result and linked analysis diagnostics/caches. A new generated replacement may import older provider events again.
- Surveys remain independently aged by submission date. Delete old responses, preserve newer or undated responses, and clear their links when the analysis expires. Delivery/send history and ongoing setup retain their existing treatment.
- Remove the retention-specific incident-window clamp, event certification, and enrichment exclusions. GitHub, Slack, Jira, Linear, AI usage, and Rootly alerts use their existing settings and requested windows. Slack's unrelated pre-existing production limitation is unchanged.
- Preview and reads use the same generation-date eligibility. Unknown generation dates require separate snapshot-bound approval for clearing; timestamps of the embedded source events no longer make a dated result unverifiable. The optional legacy receipt signing domain and result fingerprints changed so old event-age receipts cannot authorize this flow.
- Policy responses report `age_basis: "analysis_generation"` and `survey_age_basis: "submission"`. Previously stored event-age draft settings normalize to the new basis without losing the configured period. Conditional saves still require a fresh policy version.
- Enabling/shortening warnings now describe previously generated results, embedded data, preserved newer surveys/configuration, immediate read restrictions, and separate physical cleanup. The UI explains full requested history and displays generation dates in preview samples; it no longer claims enrichment is omitted.

Migration **055**, `2026_10_05_add_analysis_results_generated_at.sql`, adds a nullable timezone-aware timestamp with no default. It backfills only existing completed results with known completion dates. Missing dates and failed legacy snapshots stay unknown. The startup migration runner registers it; it was also applied to the disposable test database. A regression test executes the actual SQL loader and migration twice, verifies backfill boundaries, and preserves payloads.

Final verification: **577 backend checks**, **19 browser scenarios**, and TypeScript passed. Coverage includes full four-month windows and all configured enrichment inputs, expired generation dates despite recent source events, fresh results despite old source events, failures that cannot renew old snapshots, successful replacement, alternate result writers, legacy security, organization isolation, cache failures, dependencies, and migration idempotence. Provider/email calls and caches were mocked in destructive tests. The live management preview and member permissions passed with the policy still disabled.

The existing local demo now has three 120-day-old generated results and one fresh result containing four months of source history. At 90 days it still previews **3 expired results, 1 old survey, and 2 detached survey links**; the fresh historical result remains retained. `upgrade --local-compose` updates only a marked disabled fixture, refuses unexpected dependencies, and is idempotent. The update preserved the organization, account membership, survey rows, credentials, and saved configuration.

## October 5 UI simplification: remove Advanced cleanup

The user requested removal of the advanced option to keep retention easy to configure. The UI now sends only the proposed period for previews and the period, current policy version, and ordinary enabling/shortening consent for saves. The unknown-date checkbox, separate confirmation, receipt handling, and expiry timer have been removed. Preview and save still use authoritative organization/admin checks and session validation.

Results without a reliable generation or successful completion timestamp are preserved, rather than assigned a guessed age. They remain unavailable while retention is enabled until successfully regenerated. Undated surveys remain preserved independently. Dated results continue to expire N days after generation without shortening their requested historical window.

The backend retains its previous API for compatibility with already-issued approvals. A small notice appears only if an earlier unknown-date cleanup approval is still pending; turning retention off and saving cancels it. Preview and cleanup-history analysis totals include any such previously approved results so the simplified UI does not hide authorized deletion. Ordinary UI requests cannot create or renew those approvals.

Verification: all **30 browser scenarios** passed (29 in the initial run; the remaining case passed after updating its assertion for the shortened retry explanation), **97 backend preview tests** passed, and TypeScript passed. Independent read-only review found no material issue. The actual local API/browser smoke confirmed admin previews, member read-only access, and the expected **3 expired results / 1 old survey / 2 detached links**. Desktop rendering was inspected; browser checks covered mobile overflow and single consent. No application policy was saved or cleanup run.

## October 5 mock-analysis exclusion

Built-in mock reports are excluded from retention previews, automatic clearing, unknown-date approval candidates, and result-age read restrictions. They remain viewable even if their generation date is old or missing. Excluded reports are omitted from deletion totals and samples; previews show a small excluded count when applicable.

The exclusion uses the server-created strict `config.is_demo: true` marker and requires no real incident integration link. Report names, mock source events, truthy strings, and numeric markers do not create an exemption. Analysis reads refresh the integration link before allowing the exclusion. Prior unknown-date approvals skip exempt demos instead of clearing them.

The separate local **Retention Demo** fixtures have an explicit `local_retention_demo` marker and remain eligible by design. This preserves the controlled old/recent/unknown test cases. Survey responses still follow their own submission age, even when linked to an exempt demo; this exemption does not protect real old survey responses.

Verification: **25 new regression cases** passed alongside **65 demo tests**. The other related suites passed **351 checks**, giving **441 distinct backend checks** for this change after updating two expected response shapes for the new excluded count. TypeScript and **5 focused browser checks** passed. A read-only local check found **2 built-in demo reports excluded** and **7 retention fixtures eligible**; the actual management preview still reports **3 expired results / 1 old survey / 2 detached links**. No application policy was saved or cleanup run.

## October 5 explanation copy refinement

Removed the entire **How retention works** disclosure at the user's request. The preview helper is now one sentence: "Preview deletion before saving; previewing does not save settings or delete data." The controls, preview counts, cleanup history, and enabling/shortening confirmation remain; retention behavior is unchanged.

Verification: TypeScript and all **6 affected browser scenarios** passed, including the absence of the disclosure, exact shortened helper, preview dates/counts, cleanup timing, demo exclusions, and mobile confirmation. The local frontend was restarted to load the edit.

## October 5 short-description placement

Removed the disabled cleanup sentence and the preview helper sentence. Moved the short generation/submission-age description above the enable/period controls, in the former cleanup-status text position. The period input retains its accessible description; invalid-day validation appears separately next to the controls. Cleanup history still provides scheduling information. Retention behavior is unchanged.

Verification: TypeScript and **8 affected browser scenarios** passed, including exact description placement and uniqueness, removal of both sentences, separate accessible validation, member view, cleanup history, and mobile confirmation. The local frontend was restarted.

## October 5 short-description wording

The description above the controls now starts with the feature name and states the age rules: "Data retention, when enabled, automatically clears analysis results N days after generation and survey responses N days after submission." This is a wording-only change.

Verification: all **3 affected existing browser scenarios** passed; local frontend restarted.

## October 6 UTC: first enabled-policy diagnosis

The user enabled the local Retention Demo policy at **October 6, 03:21 UTC**, after the day's 03:00 slot. The next normal cleanup is **October 7, 03:00 UTC**, or **October 6 at 11 p.m. Toronto time**. Saving the policy does not perform immediate physical deletion. The scheduler is running; its status correctly remains Not run yet.

Read-only verification found **3 expired results and 1 expired survey**, with one retained result, one unknown-date result, one running result and one empty row. Guarded reads already reject expired results with HTTP 410. The sidebar's 130d/30d label is the requested analysis window, while its date is row creation; neither is the stored result-generation timestamp. Saved sidebar entries intentionally remain after content clearing because the saved configuration is preserved.

The review also found frontend shortcuts that could display an in-memory result without another guarded API read. Saved, automatic and most-recent report selections now revalidate with the server rather than using full results from client caches or list summaries. Full reads use no-store; unavailable or failed reads clear displayed content and derived caches. HTTP 410 displays a retention-unavailable message without selecting an unvalidated fallback. This does not retract content that a browser has already displayed; selection/opening now requires a current server decision.

Verification: frontend TypeScript passed and **3 isolated dashboard regressions** passed, covering cached-result revisits, list responses containing full results, and switching from a readable report to one rejected with HTTP 410. Positive readable reports still load, while rejected content and export access disappear and saved configuration remains. The local frontend was restarted. No manual cleanup was triggered against the application database.

## Implementation sequence

| Step | Work | Status | Verification before moving on |
| --- | --- | --- | --- |
| 1 | Define covered data, age rules, and relationships | Complete | User approved result generation age, independent survey submission age, disabled default, and whole-result clearing |
| 2 | Add the organization policy and admin API | Complete | 55 PostgreSQL integration tests passed; independent code review found no actionable issues |
| 3 | Build a read-only cleanup preview | Complete | 87 preview tests passed, including cutoff boundaries, full-result expiry, and read-only behavior |
| 4 | Implement deletion and dependency handling | Complete with result-age semantics | Final combined backend suite: 577 passed; retention-specific source exclusions removed |
| 5 | Add the admin settings UI | Complete; compact UI ready for review | 30 isolated browser scenarios, TypeScript, and live mock preview passed; compact desktop/mobile layout and confirmation guards verified |
| 6 | Schedule daily cleanup and record outcomes | Complete | 649 backend checks, 23 UI scenarios, TypeScript, fixed daily slots, targeted retries, PostgreSQL concurrency and shutdown drain passed |
| 7 | Verify the full flow in staging | Not started | User verifies the feature with controlled data before pilot activation |

Each step will update this document with changes, test results, unresolved issues, and the verification question for the next step. Ask for verification at meaningful product milestones, rather than for every routine code edit.

## Step 1 findings

Historical note: the initial source event-age approach described in the original step 1 through 4 findings was superseded by the approved result-generation rule above. It no longer requires limiting source windows or disabling enrichment collectors.

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

Initial inspection found a missing organization filter in the normal live survey query in `backend/app/api/endpoints/analyses.py`; step 4 corrected it. Jira and Linear result payloads also lack sufficient event timestamps, so their collection and coverage handling still need additional work before full integration coverage can be claimed.

## Step 2 implementation

Policy storage uses the existing `Organization.settings` JSON under `data_retention`; no database migration is needed for this step. Replacing the JSON value ensures SQLAlchemy persists the update, and a row lock protects concurrent updates. Other organization settings are preserved.

- `GET /auth/organizations/retention` returns the current organization's policy; active members can view it.
- `PUT /auth/organizations/retention` accepts `retention_days` as null for disabled, or a strict integer from 1 through 3650. Only active organization admins may write.
- Organization ownership comes from the authenticated user, not a client-supplied ID. Unknown request fields are rejected.
- Enabling or shortening retention requires `confirm_deletion: true`; disabling or lengthening does not. This prepares the contract for later destructive enforcement.
- Responses identify event age and both analysis and survey scope. Changes record time and actor; repeated identical saves preserve the original metadata.
- These endpoints configure policy without executing deletion. Enforcement and the UI are described in steps 4 and 5 below. No policy has been enabled on the current application database.

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

## Step 4 implementation

`cleanup_organization_data` in `backend/app/services/retention_cleanup.py` applies the currently saved policy using a timezone-aware injected clock. It locks the organization before analyses and responses, verifies dependency ownership under row locks, and commits the organization cleanup atomically. A missing or mismatched organization reference aborts the whole transaction. Database or configured Redis failures roll back changes; retrying is safe.

- Expire an entire analysis result by clearing `results` and its error text. Preserve its ID, saved flag, account links, credentials, requested configuration, and refresh settings.
- Delete surveys strictly older than the cutoff by their own `submitted_at`, independently of their analysis.
- Preserve newer or unknown-age surveys and clear only their expired analysis link.
- Clear links from survey periods to deleted responses while preserving completion and delivery history, avoiding accidental resends.
- Delete scoped analysis mappings and notifications; clear digest analysis links while preserving send history.
- Invalidate every result-cache key belonging to the organization, including already-empty rows. Current provider roster and permission caches are configuration, not historical analysis data, and remain available.
- Report unverifiable ages and defer pending/running jobs. Unverifiable content is not deleted based on analysis creation time. An explicit one-time legacy approval can clear reviewed, unchanged analysis results; unknown-age surveys remain separate.

Read safeguards prevent an enabled policy from serving expired or unverifiable snapshots, even before the daily job runs. They bypass Redis while retention is enabled and check database result existence before using a cache while disabled. Analysis survey queries, Slack survey status, admin survey results, and connected-user survey counts now enforce organization ownership and the saved cutoff. Personal accounts remain scoped to their owner. Digest sends also require eligible results. Result writes re-read the saved policy after collection, rejecting inputs that are no longer eligible.

Regeneration now filters primary incidents using exact timezone-aware event timestamps before any scoring, excludes older and future events, and rejects undated inputs. Worker provenance records the earliest timestamp across all scored inputs before raw incidents are capped for storage. Certified query boundaries and display-day labels are not mistaken for actual source events. Uncertified legacy results retain the conservative preview rules.

**Current coverage limitation:** GitHub, Slack, Jira, Linear, AI usage and Rootly alert enrichment lack reliable exact event provenance in the existing collectors. Retention-enabled regeneration omits those sources with an explanatory metadata notice; GitHub detail refetches return unavailable rather than importing old activity. Requested integration settings are preserved. Unknown-age legacy results remain stored until their explicit one-time approval is processed and are unavailable through guarded analysis reads while retention is enabled. Unknown-age surveys still require separate review. Restoring full integration coverage is required before claiming complete historical-data deletion for the pilot.

Retention-enabled auto-refresh preserves the analysis row and newer survey links, retains requested settings, and retries failed attempts at the configured interval. This step provides cleanup logic and safeguards; it does not enable retention, trigger cleanup against the current application database, introduce a manual deletion button, regenerate results automatically on cleanup, or add the daily schedule. The UI is step 5 and scheduling is step 6.

Initial step 4 verification: **353 targeted tests passed**: 305 policy, preview, cleanup, provenance, collection, result/refresh, digest, and survey checks plus 48 existing regression checks. The October 5 extension raised the combined total to **482 passing tests**. All database cases used `oncall_health_retention_test`; provider and email calls were mocked. Only existing SQLAlchemy/Pydantic deprecation warnings appeared. Independent reviews prompted fixes for ownership races, manual reruns, lock ordering, Redis fallback, survey count leakage, and a digest failure that could stop later recipients. These regression cases now pass.

A separate broader analyzer check produced 49 passes and 10 failures. Running that suite against the committed pre-step-4 analyzer source reproduced the identical 10 failures and 49 passes, confirming that the failures already existed. They reference removed helper methods and obsolete score fields; they remain outside this retention change.

Repeat the final targeted suite:

```powershell
docker compose exec -T `
  -e DATABASE_URL=postgresql://postgres:password@postgres:5432/oncall_health_retention_test `
  -e RETENTION_TEST_DATABASE_URL=postgresql://postgres:password@postgres:5432/oncall_health_retention_test `
  backend python -m pytest `
  tests/test_retention_policy.py tests/test_retention_policy_version.py tests/test_retention_preview.py `
  tests/test_retention_cleanup.py tests/test_retention_provenance.py `
  tests/test_retention_collection_inputs.py tests/test_retention_analysis_guards.py `
  tests/test_retention_digest_guards.py tests/test_retention_survey_guards.py `
  tests/test_retention_legacy_cleanup.py tests/test_retention_legacy_receipts.py `
  tests/test_retention_demo.py `
  tests/test_retention_generation_migration.py `
  tests/test_retention_status.py tests/test_retention_scheduler.py `
  tests/test_analysis_trim.py tests/test_member_surveys.py `
  tests/test_survey_response_service.py tests/test_pd_analytics_normalize_slim.py -q
```

## October 5 extension: existing data and unknown-age legacy history

The user approved applying retention to both existing and future data as soon as an admin enables it. There is no additional N-day waiting period: the first cleanup processes eligible existing events and surveys older than the current cutoff. Saving settings still does not execute deletion; step 6 will schedule cleanup.

Unknown-age analysis history has a separate, optional one-time clearing flow:

1. Preview the desired period with `clear_unverifiable_analyses: true`. The response distinguishes legacy analysis candidates, pending approved entries, and unknown-age survey counts. Samples mark which unknown-age results would be cleared. Related-record counts include those results.
2. Confirm the policy using `confirm_deletion` where required, and separately confirm legacy clearing using `confirm_legacy_deletion: true` plus the returned `legacy_preview_token`. A normal policy confirmation never authorizes unknown-age deletion.
3. The backend checks the organization's identity, requested days, saved policy revision, preview expiry, and the current result snapshot. Changed history requires a new preview. Preview receipts expire after 15 minutes and cannot be replayed as new approvals.
4. The saved approval contains only specific analysis IDs and fingerprints of their result content and generation timestamps. It grants no ongoing permission to delete future unknown-age results. Confirming queues cleanup; it does not immediately clear application data.
5. Cleanup clears matching unchanged unknown-age results and their scoped dependencies, preserving analysis configuration and newer surveys. Changed, regenerated, new, retained, empty, or deleted results are skipped. Unchanged snapshots in running jobs remain pending until eligible for another run. Approval consumption and data clearing commit together; failures preserve the approval for retry.
6. Disabling retention cancels pending legacy approval. GET policy reports pending/completed/cancelled status and counts. Another approval cannot replace a pending batch accidentally.

API example for step 5 to wire into the admin UI:

`POST /auth/organizations/retention/preview`

```json
{"retention_days":90,"clear_unverifiable_analyses":true}
```

After reviewing the returned counts and samples:

`PUT /auth/organizations/retention`

```json
{
  "retention_days":90,
  "confirm_deletion":true,
  "clear_unverifiable_analyses":true,
  "confirm_legacy_deletion":true,
  "legacy_preview_token":"<legacy_cleanup.preview_token from the preview>"
}
```

Omit the legacy fields for normal retention configuration. Preview and confirmation require organization admin permissions. Preview receipts are separate from login tokens, and confirmed receipt IDs are remembered through their 15-minute validity window. Cancellation reports the cancelled remainder separately from cleared and skipped records.

Surveys retain their own submission-age rule. Missing submission timestamps are reported separately and never deleted under a legacy analysis approval. Newer surveys survive and lose only links to cleared analysis results.

Implementation: `retention_legacy.py`, policy/preview endpoints and services, and cleanup integration. No database migration is needed; the one-time authorization uses a separate organization settings key. Step 5 now provides the admin UI; the daily scheduler remains step 6. This extension covers legacy handling; restoring each omitted integration is separate collector work.

Suggested restoration order from source review: AI usage (preserve UTC bucket bounds and exclude overlapping buckets), Jira/Linear (fetch and filter created/updated timestamps before scores), Rootly alerts (filter alerts and related events before counters), and GitHub (replace or certify aggregates whose inputs differ from sampled commits). Slack is already disabled globally and needs a separate organization/workspace scoping and timestamp review. Every restored source must supply verified input provenance; grandfathering older analyses does not fix future collection of old events.

Verification complete: **482 targeted tests passed** in the combined run: 434 retention checks plus 48 existing regressions. The extension adds 58 API/database cleanup tests and 71 receipt/security tests. These cover immediate application to existing expired data, separate admin confirmation, stale and replayed previews, exact approved generations, cancellation accounting, active-job deferral, safe retries, scoped dependencies, and newer/unknown-age survey preservation. Database tests use the disposable test database and mocked caches; pure receipt tests contact no external services. Independent review found no remaining actionable issue in the approval-to-cleanup flow. The API remains healthy, and the new confirmation fields are exposed in OpenAPI.

## Step 5 implementation

Organization Management at `/management` now includes a **Data retention** card above the integration-specific table. It applies to the authenticated user's On-Call Health organization and stays independent of the incident integration selector and team roles. Both management views show the same organization policy. The card also works without a primary integration.

- Fetch current identity and role from `/auth/user/me`. Members can read the saved policy and cleanup status; only admins see editing or preview controls. Cached browser roles cannot grant access. Accounts without an organization receive a clear explanation.
- Provide a disabled-by-default switch and a retention-days field with whole-number validation from 1 through 3650. The initial 90-day draft is not saved or enabled automatically.
- Require a matching read-only preview before saving changed settings. Show analysis and survey expiry counts, legacy candidates, detached links, unknown ages, deferred jobs, related records, warnings, and capped analysis samples. Editing any setting invalidates the preview. Counts can change before cleanup as data and the rolling cutoff change.
- Require confirmation of permanent deletion when enabling or shortening retention. Clearing unknown-age analyses requires its own checkbox and fresh receipt. Legacy receipt expiry disables saving, and errors discard the old receipt instead of automatically retrying it.
- Show an explicit amber warning beside the draft controls and again in the confirmation dialog when enabling retention or shortening its period. Use the proposed number of days and explain that existing and future data are covered, entire mixed-age results are cleared, surveys expire by submission age, newer responses and configuration survive, and deleted content cannot be restored. Distinguish immediate result-read restrictions from physical cleanup; unknown-age deletion still requires separate approval. The dialog shows preview counts and explains that counts can change before cleanup. No destructive warning is shown for disabled drafts, invalid periods, or lengthening retention.
- Show pending/completed/cancelled legacy status with cleared, skipped, and cancelled counts. Prevent approving another batch while one is pending. Disabling retention explains cancellation before saving.
- Explain whole-result expiry by generation date, independent survey age, preserved configuration, requested historical windows and existing integration behavior. Normal automatic cleanup runs once daily at 03:00 UTC. Saving configures cleanup without running deletion during the request; only failed organizations get earlier retries.
- Reload saved settings and status with **Refresh settings**. Verify current identity before each action, detect changed sessions and organization membership, cancel client requests on unmount, and keep controls disabled while a request runs.

Conditional saves close a race between preview and confirmation. GET and PUT policy responses include a `policy_version` digest of the organization ID and complete policy revision. The UI sends it as `expected_policy_version`; the backend compares it under the organization row lock before staging changes. A different organization or newer policy returns `409 retention_policy_changed` and requires refreshed settings and a new preview. The digest contains no secrets and is not an authorization token. Existing API callers that omit this optional precondition remain compatible.

Implementation files: `frontend/src/app/management/components/DataRetentionSettings.tsx`, `frontend/src/lib/data-retention.ts`, its mount in `frontend/src/app/management/page.tsx`, and the conditional-save guard in `backend/app/services/data_retention.py`.

Initial verification passed 505 backend tests and 18 browser scenarios. The approved generation-age revision now passes **577 backend tests and 19 browser scenarios**, plus TypeScript. Tests in `frontend/e2e/data-retention.spec.ts` mock every off-origin request and never authenticate against or modify the application database. They cover permissions despite forged cached roles, days validation, enabling/shortening/lengthening, independent legacy consent, exact receipt and policy version payloads, changed settings and stale receipts, pending cancellation, reload/status, preview errors, changed membership and sessions (including changes during an awaited identity check), generation-date samples, four-month history, and mobile overflow. Desktop and 390-pixel mobile previews and confirmation dialogs were rendered and visually inspected.

Repeat the isolated browser suite with frontend dependencies and a Playwright browser available:

```powershell
npx playwright test e2e/data-retention.spec.ts --project=chromium --no-deps --workers=1 --reporter=line
```

Run from `frontend`. The test overrides authentication storage and uses mocked identity; `--no-deps` skips the existing setup project's real login. The local Windows run used existing Playwright packages from the Docker dependency volume in a temporary folder and the cached Chromium executable via `RETENTION_E2E_CHROMIUM_PATH`, without installing dependencies or modifying configuration.

To repeat using the temporary tooling already prepared on this computer:

```powershell
$retentionTools = Join-Path $env:TEMP 'oncall-retention-playwright'
$env:NODE_PATH = Join-Path $retentionTools 'node_modules'
$env:E2E_TEST_EMAIL = 'unused@example.test'
$env:E2E_TEST_PASSWORD = 'unused-mocked-test'
$env:RETENTION_E2E_CHROMIUM_PATH = Join-Path $env:LOCALAPPDATA 'ms-playwright\chromium_headless_shell-1234\chrome-headless-shell-win64\chrome-headless-shell.exe'
node (Join-Path $retentionTools 'node_modules\@playwright\test\cli.js') test e2e/data-retention.spec.ts --project=chromium --no-deps --workers=1 --reporter=line
```

The email/password values are inert placeholders; the test suite makes no real login requests.

Existing lint tooling is incompatible with the installed package versions: `bun run lint` invokes the removed `next lint` command, and a direct attempt with the installed Next ESLint configuration fails in `eslint-plugin-react` under ESLint 10. Dependency and lint configuration repairs are outside this retention step; TypeScript, backend tests, and browser checks provide the current verification.

## Step 6: automatic cleanup and outcome reporting

The user authorized moving on after verification of generation-based retention. Implemented `retention_scheduler.py` and `retention_status.py`, wired application startup/shutdown, and added cleanup outcomes to the policy API and Organization Management.

- A UTC-aware background scheduler runs one normal **daily job at 03:00 UTC**. The user replaced the earlier 15-minute polling design with this daily schedule. Newly enabled settings, changed policies and new legacy approvals wait for the next daily slot, normally within 24 hours. A single startup recovery handles missed eligible daily work and rehydrates failed-organization retry timers; there is no recurring global 15-minute scan.
- Eligibility is anchored to the daily UTC slot and the successful attempt's start, not its completion plus 24 hours. A 03:00 run that finishes at 03:03 does not skip the following day. Existing status records without a start timestamp use completion-day fallback. Policy/approval changes made after the latest slot wait for the next one. Finishing a legacy batch does not repeatedly trigger cleanup.
- Scan active organization IDs in bounded pages without fetching every organization's settings or credentials. Resolve the current strict policy after claiming each organization. Disabled, inactive, locked, not-due and invalid policies do not delete data. One organization's failure does not stop the others.
- Claim an organization with PostgreSQL `FOR UPDATE SKIP LOCKED` in the same session used through cleanup's commit. The policy, result writers and cleanup already share organization locks. Competing processes skip a claimed organization, and persisted success metadata prevents duplicate work after a restart. No Redis lease can expire while deletion is still running.
- Store the last successful outcome and counts under the separate `Organization.settings.data_retention_cleanup` key **in the same transaction as deletion**. A database/commit failure rolls back both data changes and success metadata. This status does not alter the policy version or invalidate a reviewed policy merely because the job ran.
- After a failed transaction, record only a fixed error code/message under a fresh organization lock. Reject stale failure reports if the policy, approved legacy batch, or newer attempt superseded them. Preserve previous successful counts. Queue a one-off timer for that failed organization after 15, 30, 60, 120, 240 and then at most 360 minutes, measured from the attempt's finish. The callback rechecks current failure state and revision under the same row lock; obsolete timers cannot process healthy work or newly changed settings. Locked retries do not repeatedly reschedule an overdue timer in a busy loop.
- Perform synchronous database/cache work in the scheduler's worker executor. On shutdown, stop claiming organizations, finish the current atomic cleanup, await the executor drain, and only then dispose the database engine. Repeated start/stop and simultaneous stop callers are covered. This replaced an initial async-wrapper design that could leave a thread running during shutdown.
- GET/PUT policy includes `cleanup_status`: state, last attempt/finish/success, future due/retry eligibility, consecutive failures and typed last-successful counts. Arbitrary saved error text is never returned. Revision identifiers are constrained to their hash/UUID formats. Unknown or invalid status is reported without echoing stored content.
- The UI shows timing, paused/never/succeeded/failed/skipped states, last successful counts and related outcomes, and fixed failure/retry messages. Members can read and refresh these details without gaining editing or preview permissions. Scheduling text uses the **saved** policy, independently of unsaved draft switches. Due times describe eligibility, not an exact deletion appointment.

Physical deletion follows expiry at a normal daily run, or a failure retry/recovery if applicable; result-read safeguards enforce expiry before physical cleanup. Saving does not execute deletion in that request. Newly enabled settings apply to cleanup at the next scheduled daily slot. This is the same application behavior for hosted and self-hosted deployment while the backend is running.

No database migration is needed for step 6; validated status uses a separate existing JSON settings key. Health exposes `retention_scheduler_running` for operational verification. Normal automated cleanup applies the organization policy; the manual demo CLI additionally enforces its fixture manifest.

Verification complete: **649 targeted backend tests passed**, including 54 scheduler and 18 status checks. PostgreSQL tests use the guarded `oncall_health_retention_test` database with mocked cache/provider effects. They verify actual independent-session concurrent workers, startup deduplication, fixed daily slots despite long completion, after-slot policy/approval changes, healthy/stale/locked retry safeguards, one-off retry restoration, rollback and commit failure, sanitized status, bounded retries, organization isolation, and a blocked cleanup that drains before shutdown without taking another organization. Existing repeat-cleanup tests allow only the target organization's outcome metadata/updated timestamp to change while requiring all business data and other organizations to remain identical.

All **23 browser scenarios** and TypeScript passed, including successful outcomes, legacy counts, preserved counts after failure, retry display, member refresh and disabled scheduling. Desktop/mobile status panels were rendered and reviewed. The live mock management preview and member permissions pass, backend health reports the scheduler running, and there are **zero enabled local policies**. The mock policy remains disabled, its status is **Not run yet**, and no application results or surveys were deleted. Provider/email actions were not performed by verification.

## Compact UI refinement before staging (historical)

This records the first compact layout and its verification. The subsequent UI simplification and description refinements above supersede its advanced disclosure, receipt timer and explanation controls; the current UI has no Advanced cleanup option.

The user requested that optional retention settings stop occupying most of Organization Management. Retention now starts as a collapsed row containing its name, saved status, and **Configure** action (**View settings** for members). The integration section remains visible below it. The disclosure supports keyboard activation and exposes expanded state; its accessible name includes the action's visible label.

The status badge is simply **Enabled** or **Disabled**, as requested. It represents the currently applied policy; unsaved edits keep their separate indicator. The period remains available inside settings, including a read-only value for members.

Expanded settings show only the enable switch, period, short date-basis/schedule help, preview/save/refresh actions, and a concise existing-data warning. **Advanced cleanup** contains the optional unknown-generation-date choice and its explanation. **How retention works** contains the fuller preservation, timing and retry notes. **Cleanup history** contains outcomes and counts; a never-run organization gets one sentence rather than four empty timestamp rows. The complete permanent-deletion warning and separate legacy consent remain in the confirmation dialog.

Unsaved changes, failed cleanup, pending legacy approval and expired previews remain discoverable in the collapsed header. Closing settings neither saves nor discards a draft and does not renew a preview receipt. The component stays mounted so expiry clocks continue. Busy requests prevent collapsing the panel. Cleanup history preserves its open state across refresh, and permissions/session/version checks are unchanged.

Verification: **30 isolated browser scenarios passed** and TypeScript passed. New cases verify compact height at 1440px and 390px, keyboard expansion, unsaved collapse/reopen, visible attention states, opt-in advanced cleanup with independent confirmation, and receipt expiry while collapsed. Existing member/admin, changed session/organization, stale receipt, preview, scheduling and mobile checks still pass. Desktop/mobile images were reviewed. The live local preview and member permissions also passed; retention remains disabled and no application data changed. Backend logic was unchanged, so its prior 649-test validation remains applicable.

## Local mock organization for user verification

Created October 5 at the user's request in the local Compose application database: **Retention Demo** (organization ID 3), with the selected existing local account as admin. Alex Morgan, Priya Shah, and Noah Chen are fictional members with reserved `.invalid` email addresses. Open `http://localhost:3000/management`; **Team Roles** shows all four accounts. Refresh an existing session to pick up the membership.

The seed temporarily moves the selected existing account into this organization and disables its weekly digest. Its original organization, role, join date, and digest preference are stored in the demo manifest for restoration. Original analyses, other organizations, passwords, and real OAuth credentials are preserved. Fictional users have no passwords, provider tokens, or digest delivery. Their local provider markers only make them visible in Team Roles. No external integrations, refresh jobs or survey schedules are created, and retention starts disabled. The mock `running` analysis is deliberately deferred; no worker is executing it.

Retention starts **disabled**. The seven analysis fixtures and four surveys cover these cases:

| Fixture | Expected outcome at 90 days |
| --- | --- |
| Three results generated 120 days ago, including a saved result | 3 whole analysis results expire; rows and configuration remain |
| Fresh result containing four months of historical activity | 1 result retained, including its older source data |
| Legacy result with unknown generation date | 1 reported as unknown; preserved by normal retention, with no advanced approval in the UI |
| Mock running result | 1 deferred |
| Empty result | 1 empty |
| Old survey linked to an old result | 1 survey deleted by its own submission age |
| Recent survey linked to the mixed result | Response preserved; analysis link cleared |
| Unknown-age survey linked to the old result | Response preserved; analysis link cleared |
| Recent survey linked to the recent result | Response and link preserved |

### Simple manual test

1. Click **Configure** on the compact **Data retention** row, turn on the draft switch if disabled, leave **90** days, and click **Preview deletion**. Before the first cleanup, expect **3 analysis results**, **1 survey response**, and **2 survey links**. Previewing changes no policy or data. If the saved policy is already enabled at 90 days, skip step 3; there is no policy change to save.
2. Review the generated dates and unknown-date counts in the preview. The legacy result is preserved and becomes unavailable while retention is enabled; a successful rerun gives its replacement a reliable date. The unknown-age survey remains preserved. There is no Advanced cleanup option or extra confirmation.
3. Click **Save retention policy**, review the confirmation, and save. Reload to verify the saved 90-day policy. Saving does not run cleanup during the request; the next normal daily run is at 03:00 UTC, normally within 24 hours while the backend is running.
4. Wait for the daily run and click **Refresh settings** to inspect the saved outcome, or run the fixture-only cleanup command below to test immediately. The three expired payloads become empty, the old survey disappears, and two preserved survey links become null. The unknown-date result and survey remain stored. Saved entries remain in the sidebar with their configuration, even after result content is cleared. Repeat cleanup to verify it does not delete the preserved responses; its last-successful counts update to reflect the new no-op run.

```powershell
docker compose exec -T backend python scripts/retention_demo.py cleanup --local-compose
docker compose exec -T backend python scripts/retention_demo.py status --local-compose
```

To start over, reset the recorded demo and seed it again. Reset also restores the original account membership and digest preference before removing the fictional accounts and fixture data. Replace the example email with an existing local account's email.

```powershell
docker compose exec -T backend python scripts/retention_demo.py reset --local-compose
docker compose exec -T backend python scripts/retention_demo.py seed --local-compose --email you@example.com
```

Reset and cleanup refuse unexpected members, data, schedules, providers, or dependent records instead of cascading through them. If new data was added and reset refuses, use **restore** to restore the original account membership, disable demo retention, cancel pending legacy approval, and leave all demo history intact:

```powershell
docker compose exec -T backend python scripts/retention_demo.py restore --local-compose
```

An optional single-use local login link avoids changing passwords. Run the first command to sign in as the selected existing account, or the second to check Alex's read-only member view. Substitute `priya` or `noah` for other members. Links expire in five minutes and create a 30-minute session. Link creation refuses accounts with GitHub/Jira/Linear integrations because the existing login page warms their provider permissions; use an existing session for such accounts.

```powershell
docker compose exec -T backend python scripts/retention_demo.py login-link --local-compose
docker compose exec -T backend python scripts/retention_demo.py login-link --local-compose --member alex
```

Implementation: `backend/scripts/retention_demo.py` and `backend/scripts/retention_demo_fixtures.py`. Commands require the explicit local flag, local PostgreSQL Compose database, DEBUG mode, and backend container. They add no web endpoint or scheduler. Repeated seed is idempotent and preserves an already configured policy. Status previews 90 days read-only even when the saved policy differs; its `saved_policy` reports the actual value.

Verification: **67 demo safety tests passed** against the disposable test database with rollback transactions and mocked cache/provider effects. These cover seed atomicity/idempotence, original data preservation, both cleanup modes, restoration/reset, generation-date upgrades, unexpected dependencies, cache failures, single-use login, provider-free links, and permissions. Live API and browser checks then confirmed the disabled policy, expected preview counts, four visible members, read-only member UI, and forbidden member preview/save requests. The live checks saved no policy and ran no cleanup. No real provider or email calls were made.

```powershell
docker compose exec -T `
  -e DATABASE_URL=postgresql://postgres:password@postgres:5432/oncall_health_retention_test `
  -e RETENTION_TEST_DATABASE_URL=postgresql://postgres:password@postgres:5432/oncall_health_retention_test `
  backend python -m pytest tests/test_retention_demo.py -q
```

## October 5 step 5 verification and scope clarification

The user requested a fresh verification before scheduling and asked whether retention simply removes analyses created before the cutoff and all linked data. No age or deletion rules were changed during this review.

During this earlier review the implementation measured **underlying event age**, rather than `Analysis.created_at`; the user subsequently replaced that rule with result-generation age in the approved change above. Whole-result clearing and preservation of configuration remain unchanged.

| Data | Current treatment |
| --- | --- |
| Expired analysis content | Clear the whole result payload, including existing enrichments |
| Analysis record and configuration | Preserve |
| Linked analysis mappings and notifications | Delete within the organization |
| Analysis result caches | Evict; retention-enabled reads recheck persisted eligibility |
| Old surveys, including unlinked ones | Delete by their own submission age |
| Recent or unknown-age surveys linked to expired results | Preserve responses and clear only their analysis links |
| Unknown-age analysis results | Hide from analysis reads immediately when enabled; retain stored content unless separately approved for one-time clearing |
| Running/pending analysis results | Defer cleanup; workers check the policy before persisting results |
| Survey delivery periods and digest send history | Preserve history; clear references to removed responses/results |
| Accounts, memberships, credentials, integration settings and rosters | Preserve |
| Unrelated notifications, login/audit records, backups, operational logs and already-sent emails | Outside this cleanup |
| Original records in external providers | Outside this application's deletion scope |
| Records without organization ownership | Outside automatic organization cleanup; do not guess ownership |

The earlier **Current analysis coverage** warning described source exclusions required by the old event-age rule. Those retention-specific exclusions have now been removed. The replacement **Analysis history and retention** explanation describes preserving requested windows and expiring each generated result as a unit.

Saving a policy does not run physical cleanup during that request, but enabling it immediately changes result-read eligibility. The final generation-age implementation preserves requested collection windows and integration behavior. The retained operational metadata and daily cleanup timing must be understood before pilot activation. The company request specifies automatic deletion after N days; it does not itself define the age basis or require deletion of every linked record regardless of that record's own age.

Fresh verification: **565 targeted backend tests passed**, **18 isolated browser scenarios passed**, and frontend TypeScript passed. The live mock API/browser check again confirmed the expected 90-day preview (3 expired analyses, 1 old survey, 2 detached links), four-member Team Roles, and read-only member access. No application policy was saved, no cleanup ran, and no provider/email calls were made. Independent read-only review confirmed the scope above. Source: `retention_preview.py`, `retention_cleanup.py`, `analyses.py`, and the management retention card.

The user subsequently approved the explicit existing-data warning. Implemented it in the settings and confirmation dialog without changing deletion rules. Extended the existing enabling, shortening, lengthening and invalid-period browser cases to verify the warning, dynamic days, preservation, timing, preview counts, and unchanged confirmation gates. All 18 browser scenarios and TypeScript passed. Desktop/mobile dialogs were visually inspected; an additional mobile check confirmed that the longer dialog scrolls to both separate checkboxes and the save button. The live demo preview still passes and its saved policy remains disabled.

## Decisions awaiting verification

| Decision | Proposal | Status |
| --- | --- | --- |
| Initial coverage | Analysis results and historical metrics plus survey responses | Confirmed by user |
| How data age is measured | Analysis result generation age; independent survey submission age | Approved change implemented October 5 |
| Existing organization default | Disabled until an admin explicitly enables retention | Confirmed by user |
| Historical events within a report | Keep the complete requested historical window; expire the whole result N days after generation | Approved change implemented October 5 |
| Saved and auto-refresh analyses | Saved results expire; preserve analysis rows/configuration, and refresh in place when retention is enabled | Implemented in step 4; awaiting user verification |
| Running analyses | Defer cleanup of active jobs; check the current policy before saving or returning any result | Implemented in step 4 |
| Related metadata | Delete scoped mappings/notifications; detach newer surveys, survey periods and digest links; evict result caches | Implemented in step 4 |
| Enrichment collection | Preserve existing integration behavior and requested windows; no retention-specific exclusions | Restored and tested October 5 |
| Existing versus future data | Apply the same rolling cutoff to both from the first cleanup; no additional N-day wait | Confirmed by user October 5 |
| Legacy analyses with unknown generation dates | Preserve undated results; no advanced approval in ordinary settings | Advanced UI removed; prior pending approvals remain visible and cancellable for API compatibility |
| Unknown-age surveys | Report separately for review; do not cascade-delete from analyses | Approved by user October 5 |
| Allowed number of days | Strict whole number from 1 through 3650; null disables the policy | Implemented in step 2 |
| Admin settings UI | Compact organization-wide card with period, preview, ordinary confirmation, and status | Advanced UI removed at the user's request; awaiting user flow verification |
| Backups and operational logs | Document a separate policy; database cleanup alone does not erase backups or logs | Awaiting deployment review |

## Test strategy

Use a separate PostgreSQL database with disposable fixtures for automated destructive tests. A feature branch does not isolate Docker volumes. The user-authorized, marked local demo above is the manual verification exception: its CLI refuses cleanup/reset when unexpected data or dependencies are present.

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
| Generation age | Old result generations expire; fresh reports retain older source history; successful replacement renews age and failed attempts do not |
| Preview consistency | Preview and deletion use the same eligibility logic, with cutoff and policy recorded |
| Repeated runs | Second cleanup safely finds nothing already deleted |
| Failure handling | Transaction behavior is correct; failures are visible and retries are safe |
| Prior legacy authorization | Existing backend approvals remain snapshot-bound; simplified UI cannot create or renew one and exposes pending cancellation/counts |
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
| October 4, 2026 | 4 | Implemented atomic cleanup, scoped dependency locks, independent survey expiry, result-cache eviction and repeatability | Tested only in the disposable database; application data untouched |
| October 4, 2026 | 4 | Added exact incident filtering, full-input provenance and policy checks on result writes/reads | Unsupported enrichment excluded; unknown-age legacy results reported for review |
| October 4, 2026 | 4 | Corrected auto-refresh continuity, survey status/results/count ownership, and digest eligibility/failure handling | Newer responses and requested settings preserved; mocked email/provider calls only |
| October 4, 2026 | 4 | Ran final targeted suite after independent reviews | 353 passed: 305 retention checks plus 48 existing regressions |
| October 4, 2026 | 4 | Compared older analyzer suite with committed pre-change source | Identical 10 failures and 49 passes; failures predate step 4 |
| October 4, 2026 | 4 | Checked Docker services, API health, branch and patch whitespace | App healthy on localhost:3000; branch feat/org-data-retention; no whitespace errors |
| October 5, 2026 | 4 extension | Added signed legacy previews, separate snapshot-bound approval, cancellation status, and atomic cleanup consumption | Backend implemented; no policy enabled or cleanup run against application data |
| October 5, 2026 | 4 extension | Ran 58 legacy API/database tests and 71 receipt/security tests | Passed; covers existing data, exact generations, replay, cancellation, failures, and survey preservation |
| October 5, 2026 | 4 extension | Ran the combined targeted suite and independently reviewed approval-to-cleanup flow | 482 passed; only three existing deprecation warnings; no remaining actionable review issue |
| October 5, 2026 | 4 extension | Checked API health, confirmation schema, and patch whitespace | Healthy local API; preview and legacy confirmation fields available |
| October 5, 2026 | 5 | Added organization-wide retention settings, read-only member view, previews, confirmations, and cleanup status | Implemented without changing an application policy |
| October 5, 2026 | 5 | Added server-checked conditional saves and independent identity/session checks | 23 new PostgreSQL tests passed, including organization changes and stale revisions |
| October 5, 2026 | 5 | Ran full backend suite and frontend TypeScript check | 505 backend tests passed; TypeScript passed |
| October 5, 2026 | 5 | Attempted existing and direct lint commands | Existing Next/ESLint version incompatibilities prevent lint execution; dependency setup unchanged |
| October 5, 2026 | 5 | Ran isolated browser suite and reviewed desktop/mobile renders | 18 passed; member/admin, confirmations, cancellation, stale revisions, sessions, and mobile overflow verified |
| October 5, 2026 | 5 | Checked running frontend, API health, OpenAPI and patch whitespace | Management returns 200; API healthy; conditional-save schema available; no whitespace errors |
| October 5, 2026 | 5 user verification | Added reversible local demo CLI, seven analysis fixtures, four surveys and three fictional members | Selected local account is admin of Retention Demo; saved retention remains disabled; no cleanup run |
| October 5, 2026 | 5 user verification | Ran disposable demo lifecycle, ownership, dependency, rollback and login checks | 60 passed; application data excluded from automated destructive tests |
| October 5, 2026 | 5 user verification | Checked actual API and browser preview, four-member Team Roles and read-only member permissions | Expected 3 expired results, 1 survey and 2 detached links; member preview/save returns 403; policy unchanged |
| October 5, 2026 | 5 scope review | Re-ran targeted backend, browser and TypeScript checks and repeated the live mock preview | 565 backend and 18 browser tests passed; TypeScript passed; demo policy remains disabled |
| October 5, 2026 | 5 scope review | Independently audited age basis, payload clearing, dependencies, preserved data and source exclusions | Event-age rules confirmed; broader deletion scope and enrichment omissions require product verification before step 6 |
| October 5, 2026 | 5 warning refinement | Added approved existing-data warning to draft controls and confirmation, with proposed days, preview counts, preservation and timing | 18 browser scenarios and TypeScript passed; additional mobile control/scroll check passed; live demo remains disabled |
| October 5, 2026 | Approved age-rule change | Switched analysis retention to stored result generation timestamps; restored full requested windows and enrichment behavior | Migration 055 applied; failed attempts preserve old snapshot age; no application results deleted |
| October 5, 2026 | Approved age-rule change | Updated backend/UI/legacy security and upgraded the existing marked local demo | 577 backend and 19 browser checks passed; TypeScript passed; live demo remains disabled with 3/1/2 preview counts |
| October 5, 2026 | Window clarification | Confirmed six-month/custom analysis windows remain independent of N-day retention; removed the fixed four-month UI example | Focused generation/history UI check passed; no retention-window logic changed |
| October 5, 2026 | 6 | Added daily cleanup polling, atomic outcome status, bounded retry, same-session claims and sanitized API/UI reporting | Scheduler wired; local enabled-policy count is zero |
| October 5, 2026 | 6 | Fixed shutdown to drain the current organization and prevent new claims before engine disposal | Real blocked-worker lifecycle test passed; independent review found no remaining blocker |
| October 5, 2026 | 6 | Ran final backend/UI/type checks and live mock/health verification | 625 backend, 23 UI and TypeScript passed; scheduler running; mock still disabled and never cleaned |
| October 5, 2026 | 6 schedule refinement | Replaced the 15-minute routine poll with daily 03:00 UTC cleanup and failure-only one-off timers | 649 backend and 23 UI tests passed; TypeScript passed; no application policy enabled or data deleted |
| October 5, 2026 | Compact UI refinement | Collapsed optional retention by default; moved advanced options, explanations and history into disclosures | 30 browser cases and TypeScript passed; desktop/mobile reviewed; live preview passes; no policy/data changes |
| October 5, 2026 | Simple retention UI | Removed Advanced cleanup, separate unknown-date consent and receipt handling; retained conditional prior-approval notice and accurate combined counts | 30 browser scenarios, 97 preview tests and TypeScript passed; live demo preview passed; retention remains disabled |
| October 5, 2026 | Mock analysis exclusion | Excluded built-in sample reports from preview, cleanup, legacy candidates and result-age reads; dedicated retention fixtures remain eligible | 25 new cases and 416 existing related checks passed after two expected-shape updates; TypeScript and 5 browser checks passed; live mock preview unchanged |
| October 5, 2026 | Explanation copy refinement | Removed How retention works and shortened the preview helper to one sentence | TypeScript and 6 affected browser scenarios passed; local frontend restarted |
| October 5, 2026 | Short-description placement | Removed disabled-status and preview-helper sentences; moved age description above controls with separate validation | TypeScript and 8 affected browser scenarios passed; local frontend restarted |
| October 5, 2026 | Short-description wording | Reworded the description to introduce Data retention and state generation/submission expiry | 3 affected browser scenarios passed; local frontend restarted |
| October 6, 2026 UTC | Enabled-policy diagnosis and browser revalidation | Confirmed first daily run timing, window versus generation age and saved configuration preservation; removed client result-cache display shortcuts | Read-only preview 3 expired results/1 survey; expired server reads return410; TypeScript and 3 dashboard cases passed; no manual app cleanup |
| October 6, 2026 UTC | Commit preparation | Reviewed final diff, corrected historical/manual instructions, and verified the current settings/dashboard UI | 34 browser scenarios passed (33 initially, 1 after synchronizing its refresh wait); TypeScript passed using committed node resolution; whitespace check passed; unrelated local tsconfig change excluded |

## Next action

Next is **step 7: verify the complete automatic flow in staging** with a controlled organization and synthetic data before pilot activation. The user has enabled the local mock's 90-day policy; its first scheduled cleanup is October 7, 03:00 UTC. Review the outcome panel at `http://localhost:3000/management` after that scheduled run. Confirm separate policies for delivery/security history and backups before describing the feature as deletion of every organization record. Continue using normal chat for verification questions because the terminal question widget was inaccessible.
