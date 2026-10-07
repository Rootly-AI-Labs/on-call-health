# Organization data retention implementation tracker

This document tracks implementation and verification of automatic deletion after an organization administrator selects a retention period in days. It is the shared record for decisions, code changes, tests, and user verification throughout the work.

Branch: `feat/org-data-retention`

Last updated: October 6, 2026

Current status: **Steps 1 through 6 are implemented** with result-generation age and daily cleanup at **03:00 UTC**, restored after local testing. The first local scheduled cleanup succeeded October 6 at 15:00 UTC, clearing three result payloads, deleting one old survey and detaching two newer/undated survey links. The user subsequently approved deleting expired manually saved analysis records entirely, including configuration and metadata; recurring auto-refresh setup remains. That local change passed **699 retention backend checks**, **31 settings browser scenarios** and TypeScript. A second temporary test run at 15:40 UTC fully deleted the three expired saved records. The restored UTC schedule passed **84 scheduler/status checks** and TypeScript. Step 7, full staging verification, remains.

## Agreed direction

- Configure retention in Organization Management using organization admin permissions.
- Apply one policy to the organization, rather than individual members or teams.
- Enforce the policy automatically with a daily backend job.
- Support the same behavior in hosted and self-hosted installations.
- Keep accounts, memberships, and integration credentials available for continued use.
- Cover analysis results and historical metrics plus survey responses.
- Determine analysis expiry from when its stored result was generated; survey responses use their own submission timestamp.
- Keep retention disabled until an organization admin explicitly enables it.
- Expire the entire stored result once its generation date is older than the rolling cutoff, including embedded activity, metrics, insights and enrichments. Delete manually saved analysis records, including configuration and metadata; preserve recurring auto-refresh setup and unsaved analysis rows.
- Preserve the requested historical analysis window. A report generated today may cover four months of source activity and remain available for N days after generation. Successfully generating its replacement starts a new lifetime; a failed attempt without a new result does not renew the old snapshot.
- Retention does not disable enrichment inputs. Existing feature settings and provider permissions continue to control collection; unrelated baseline feature limitations remain.
- Keep the settings simple: enable/disable, N days, preview, and one ordinary deletion confirmation. There is no Advanced cleanup option or new approval for deleting results with unknown dates.
- Exclude the built-in sample/demo analyses from retention. Dedicated local retention test fixtures stay eligible so automatic cleanup can still be tested.

The analysis window and retention period are independent. Four months is only the current demo's example, not a limit: a six-month analysis retains its six months of available source data, and its complete result expires N days after generation. Retention adds no analysis-window cap; the app's existing supported date-range limits still apply. The management explanation now uses general N-day wording and explicitly says retention does not shorten the requested window.

The company requested automatic deletion after N days. Manual deletion by date range and deletion of the organization itself are separate features.

## October 6 approved change: delete expired manually saved records

This supersedes the earlier decision to preserve every analysis configuration. A dated expired analysis with `is_saved: true` and `is_auto_refresh: false` is now deleted entirely in the cleanup transaction. Its saved/sidebar entry disappears on the next list refresh. Auto-refresh records retain their setup so future successful runs can generate replacement results; unsaved records retain the previous content-clearing behavior.

Existing saved rows whose contents were already cleared by earlier cleanup are also removed when their canonical `results_generated_at` proves that they expired. Empty configurations without a canonical generation date are preserved; row creation or completion alone cannot prove a previously stored result existed. Error-only records retain their independent error-content age check, so a newer error does not cause an already-cleared row to expire prematurely.

Surveys still use their own submission age: expired responses are deleted, and newer/undated responses survive with their analysis link cleared. Related mappings and notifications are deleted, digest history is detached, and old linked surveys are deleted before the saved parent to satisfy foreign keys. Ownership checks, cache eviction, locks, outcome recording and deletion remain atomic. Missing rows encountered by waiting analysis reads return 404 rather than a refresh error.

Fresh, unknown-date, active and built-in demo analyses keep their existing protections. Prior snapshot-bound legacy approvals authorize clearing content only, so they do not delete unknown-date saved configurations. The settings description and deletion confirmation now explain full manual-record deletion and preserved auto-refresh setup. No migration or policy-setting change is required.

Verification: **699 backend checks passed**, including 27 new saved-record cases and the existing dependency test expanded to cover full deletion. The guarded disposable database verifies foreign-key ordering, independent survey age, preserved recurring setup, generation cutoffs, already-cleared rows, unknown-date/active/demo/organization exclusions, error-only content, idempotence, rollback, saved-list removal and 404 reads after deletion. **31 settings browser scenarios** and TypeScript passed. The backend and frontend were restarted; local health and Management return successfully. A read-only local preview confirms the three previously cleared saved fixture rows are now expired deletion candidates. No additional cleanup was run against application data during this change; they will disappear after the next scheduled cleanup and dashboard refresh.

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

## October 6: selected PR #530 review fixes

The user approved fixes **1, 4-5, 7, 8 and 9** from the ranked review: demo refresh, PagerDuty team scoping, OpenAI directory permissions, OpenAI pagination and tracked AI usage table creation. Other review findings were explicitly excluded from this change.

- Removed demo refresh's redundant deletion of all analyses owned by unverified users. Existing demo-only cleanup and authorization remain, and the compatibility response field stays zero.
- Added an optional REST incident team filter and propagated it through both Analytics fallbacks and failed-analysis recovery. Selected-team analyses reject incomplete, unavailable, empty, malformed or unmatched membership instead of widening to the account. Member requests include full user profiles; unresolved reference-only profiles fail safely when no synced roster exists. Unscoped analyses keep their existing behavior.
- Require organization user-management permission before retrieving the shared OpenAI directory; personal integration owners retain access.
- Both OpenAI usage collectors preserve the original date/filter/grouping parameters and use the documented `page` cursor across all pages.
- Register the existing table-creation SQL as **056_create_ai_usage_integrations**, before **053_ai_usage_nullable_org**, without renaming any existing migration. Fresh migration-only setup and existing nullable/personal rows are tested in isolated schemas.

Verification: **140 targeted backend checks passed**, including **51 new regressions** and existing admin, PagerDuty, normalization and retention collection/result tests. Provider calls and cache effects are mocked. Destructive tests use only the explicitly guarded disposable PostgreSQL database and roll back their rows/schemas. Independent code review found no material blocker. The unrelated local frontend TypeScript configuration edit remains excluded.

The local backend was restarted successfully. Read-only health reports healthy with the retention scheduler running, and migration metadata confirms 053, 055 and the newly registered 056 are completed. No manual demo refresh or retention cleanup was run against application data.

## October 6: PR #534 follow-up findings

All six new findings were validated and the user authorized their fixes:

- Auto-refresh preserves the existing result, its generation timestamp and error content until a replacement is stored. Known legacy generation dates are captured before resetting attempt status. Failed runs with no replacement cannot discard or renew the snapshot. Active report reads return only safe polling metadata, withholding the previous result, errors and surveys until the run becomes terminal.
- Migration **057** adds `Analysis.error_generated_at`. New error writes use a canonical UTC content timestamp; status-only writes do not renew it, and new result payloads clear stale errors. Backfill uses only known failed-run completion dates. Error-only analyses now participate in preview, read restrictions and cleanup; undated error content stays stored but unavailable under enabled retention. Existing receipts for unchanged undated snapshots retain their fingerprints; replacing or dating error content invalidates approval.
- PagerDuty membership rejects any incomplete entry rather than dropping it; cache versioning prevents reuse of old incomplete successes. Selected-team REST errors, malformed pages, stalled pagination and timeouts propagate as collection failures, including through fallback and recovery. Empty successful pages remain valid; unscoped REST compatibility is preserved.
- Skipped retries recheck current saved failure eligibility and queue a targeted retry at least 15 minutes later, respecting later backoff and existing timers. Healthy, disabled, stale and shutdown cases do not requeue. No global polling was added.
- Dashboard bootstrap/default/manual reads share selection ownership. Late success, HTTP 410 and cancellation from an older request cannot overwrite or clear a newer selection, its URL or caches.

Verification: **776 distinct backend checks passed across the affected suites**, plus **6 dashboard browser scenarios**. TypeScript passed with committed node resolution; migration consistency and whitespace checks passed. Regression coverage includes actual scheduler-to-failure preservation, active polling without content, error cutoff/unknown-date handling, migration idempotence, incomplete PagerDuty collection, persistent lock/release retry recovery and held-response browser races. Provider calls are mocked and database mutations occur only in guarded disposable fixtures. Independent final review found no remaining material blocker. The local backend restarted healthy and migration 057 is recorded completed. No manual application cleanup or provider call was run.

## October 6: preview detail simplification

Removed the **Related records** disclosure and its mapping, notification, survey-period, digest and ownership-review counts from the management deletion preview at the user's request. Backend dependency checks and cleanup are unchanged.

## October 6: compact deletion preview

Simplified the management preview to two counts (analysis results and survey responses) and a short preservation note. Removed evaluation/cutoff timestamps, the detachment tile, raw retained/unknown/deferred counts, the excluded-demo count and generic explanation/warning lists. Optional analysis samples remain collapsed. Prior approval totals and actual ownership-review blockers still appear when applicable. This changes presentation only; survey detachment and all retention rules are unchanged.

Verification: TypeScript and all **6 affected existing browser scenarios** passed, including simplified cards, prior approval counts, demo preservation, generation samples, confirmation and mobile overflow. The local frontend was restarted.

## October 6: temporary local testing schedule

Changed the local daily cleanup from 03:00 UTC to **11:00 a.m. America/Toronto** at the user's request. The scheduler and next-due calculation use the same timezone: 15:00 UTC during daylight time and 16:00 UTC during standard time. Failure retries and retention periods are unchanged. No separate one-time job or helper was scheduled. This temporary local change has not been committed or pushed.

Verification: **90 scheduler/status checks**, including daylight-saving boundaries, and **2 existing browser timing/confirmation checks** passed; TypeScript passed. The restarted backend reports the next cleanup for organization 3 as October 6, 15:00 UTC / 11:00 Toronto, with its 60-day policy unchanged.

The user subsequently moved the local daily time to **11:40 a.m. Toronto**, so cleanup can run again on October 6 after the earlier 11:00 run. The same daily CronTrigger now uses minute 40, and UI timing and test expectations match. Read-only verification at approximately 11:35 confirms the scheduler is running and organization 3 is due **October 6, 15:40 UTC**, with its 60-day policy unchanged. **91 scheduler/status checks** passed, including a regression confirming an earlier same-day success does not suppress the later slot; **2 affected browser checks** and TypeScript passed. The browser timing assertion was updated from 3:00 to 3:40 UTC before its successful rerun. No one-time job or status reset was needed.

Actual scheduled verification: the October 6 **11:40 a.m. Toronto** run succeeded and fully deleted the three previously cleared saved fixtures (IDs 3, 5 and 7). Read-only database verification at 11:42 confirms five saved entries remain for the local owner: the fresh October 5 result (ID 4), unknown-date legacy result (ID 6), mock running/deferred result (ID 8), empty undated configuration (ID 9), and exempt built-in demo (ID 1). These match the user's screenshot; the displayed 130d/30d values describe source windows, not stored-result age. The current organization period is 60 days. At that verification, next cleanup was October 7 at 11:40 a.m. Toronto (15:40 UTC).

Testing complete: at the user's request, restored the original **03:00 UTC daily schedule**, UTC slot calculations, associated backend tests, and displayed timing. Removed the temporary Eastern-time scheduling changes. Restarted both services and verified the live scheduler reports `daily_time_utc=03:00`; organization 3 is next due **October 7 at 03:00 UTC** (October 6 at 11 p.m. Toronto). Its 60-day policy and recorded successful test cleanup remain. **84 scheduler/status checks**, **2 affected browser checks** and TypeScript passed.

## Implementation sequence

### October 6 review follow-up: terminal failed polling state

The finding is valid on the previously pushed branch and was reproduced with a pending report opened from its URL. A successful HTTP polling response with `status: failed` stopped the running indicator but left the pending snapshot displayed; notification-disabled polling provided no visible failure feedback.

The failed-status branch now publishes the terminal response as the current report and updates its automatic-report state, so the sidebar no longer says Refreshing. It preserves the supplied error message or uses a generic failure message when no detail is provided. The failure card gives an explicit error precedence over a missing incident count, avoiding a misleading No Incidents heading. Existing polling ownership checks still prevent a late failed response from replacing a newer selected report.

Verification: **17 dashboard browser scenarios** and TypeScript passed, including four new pending/running URL cases with/without error detail and a late failed response after cancellation and a different selection. The test cancellation route remains fully mocked, including its DELETE preflight; no application data or provider APIs were used. The local frontend was restarted. This follow-up is verified for publication on `feat/org-data-retention`.

### October 6 review follow-up: polling fallback and deleted-row reads

Both Greptile findings are valid and were reproduced before the fixes. A running automatic report's 404 left the dashboard without a saved report; a pending saved report finishing unsuccessfully and being cleaned while its reader waited caused an unhandled `InvalidRequestError` during the polling metadata refresh.

Polling terminal failures now create an explicitly owned fallback selection, exclude the failed automatic report and try saved candidates until an API read succeeds. Polling belongs to the same selection generation as other report reads; changing selection, cancelling or unmounting stops timers and makes late responses ineligible to change the displayed report. Opening/restoring a pending report continues its polling without duplicate loops.

The metadata-only `_retention_refresh_status` path now uses the existing `_refresh_retention_analysis` helper, returning 404 when its row disappeared. It still exposes no retained result/error content while an analysis is active. Regression tests interleave the actual failed-result writer and cleanup with reads by numeric ID, UUID and the by-id endpoint, for both pending and running states, in rollback-only disposable PostgreSQL sessions.

Verification: **103 related backend checks** and **12 dashboard browser scenarios** passed, including six new cases in each suite. Browser coverage includes polling 404, exhausted HTTP retries, unavailable saved candidates, resumed polling and late completed/404 responses after cancellation and a newer selection. TypeScript and whitespace checks passed; browser/provider APIs were mocked. Both services were restarted. Fixes are verified for publication on `feat/org-data-retention`.

### October 6 minimal cleanup history

Simplified the optional Cleanup history disclosure to one row with **Last successful cleanup**, **Analyses cleared**, **Surveys deleted**, and **Survey links detached**. Desktop shows four columns; mobile wraps to two columns. The date stays explicitly UTC and omits seconds; its full timestamp remains available on hover. Before any success, the date displays Never. Counts remain those recorded for the last successful run, even after a later failure.

Removed attempt/finish timestamps, next-run/retry timestamps, schedule and count explanations, related-record/deferred/unknown-date details, failure-attempt totals and policy-change dates from this view. The status badge and actual failure message remain. Backend scheduling, deletion rules, stored outcomes and permissions are unchanged.

Verification: **7 affected existing browser scenarios** and TypeScript passed, covering successful counts including legacy clears, no prior success, failure without replacing successful counts, read-only member refresh, disabled status, draft refresh, and mobile layout. Desktop/mobile summary renders were reviewed; the local frontend was restarted.

The user subsequently requested removal of **Analysis samples** from the deletion preview. Removed the disclosure and its per-analysis table, including generation timestamps, eligibility outcomes/reasons and truncation text. The preview retains its two counts, short preservation note and conditional ownership/prior-approval notices. This is a UI-only change; API eligibility and cleanup are unchanged. **3 affected existing browser scenarios** and TypeScript passed; the local frontend was restarted.

### October 6 preview-free disabling

An admin can now turn off retention and click **Save retention policy** directly, without generating a deletion preview or opening a confirmation dialog. Saving an already-disabled, unchanged policy remains unavailable. Enabled policies still require a matching preview; enabling or shortening the period still requires deletion consent. Account/session verification, organization admin permissions, conditional policy versions and cancellation of prior cleanup approvals continue through the existing save API.

Verification: **8 affected existing browser scenarios** and TypeScript passed, including direct disabling without preview requests, approval cancellation and disabled state after reload, enabling/shortening consent, lengthening, draft invalidation, stale-policy refresh, session changes and member restrictions. Provider/application data remained isolated behind mocked APIs; the local frontend was restarted.

### October 6 retention placement and save feedback

Moved the collapsed Data retention card below the main Organization Management/Team Management content. It remains outside both view modes, including when no primary integration is connected, and stays mounted when switching Synced Org/Team Roles so draft values are preserved. Added spacing above the card to match the page.

Successful-save notices now disappear after **five seconds**. The saved Enabled/Disabled badge remains; actual errors and cleanup-attention indicators are not dismissed by this timer. The timer resets with a new notice and is cancelled when the notice changes or the component unmounts.

Verification: **8 affected existing browser scenarios** and TypeScript passed. Checked desktop/mobile card placement after the management content, collapsed size, draft continuity across both tabs, absence of primary integrations, persistent failure/pending indicators, and automatic save-notice dismissal. Desktop and 390-pixel mobile renders were inspected; the local frontend was restarted.

### October 6 sidebar date clarification

Saved and automatic report entries now show the report name, **Covers N days**, and **Generated [date]** when a stored generation timestamp is available. Otherwise they show **Created [date]** without relabeling row creation or failed-run completion as generation. Dates include the year; hovering shows the exact local date/time and identifies an unknown generation date when the creation fallback is used. Full truncated report names are also available on hover.

The expanded sidebar is slightly wider (240 to 288 pixels) and no longer shrinks under main-content pressure. Both report sections share the same metadata display. The analysis API exposes nullable `results_generated_at` in saved summaries and individual/automatic responses; the list query still avoids loading result content. Frontend types accept older responses without this field.

The user subsequently chose simpler fixed labels: **Time range: N days** and **Created [date]**, for both saved and automatic entries. The displayed date now always comes from row creation, with the exact local time available on hover. This is a display change; retention still ages stored results by generation time. The wider sidebar and year-inclusive dates remain. Updated existing assertions and verified **6 dashboard browser scenarios** and TypeScript; the local frontend was restarted.

Verification: **97 backend checks**, **6 existing dashboard browser scenarios**, and TypeScript passed. Existing list assertions verify generation is distinct from row creation and completion timestamps. Browser fixtures verify Generated/Created labels and automatic-report metadata; a targeted desktop/mobile rerun passed after restarting the frontend to load the updated sidebar accessibility label. Desktop and 390-pixel mobile renders were inspected. Both local services were restarted; health is healthy, the running API schema includes the generation timestamp, and Dashboard responds successfully.

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
| Three manually saved results generated 120 days ago | 3 analysis records expire and are deleted, including rows and configuration |
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
4. Wait for the daily run and click **Refresh settings** to inspect the saved outcome, or run the fixture-only cleanup command below to test immediately. The three expired manually saved records are deleted, the old survey disappears, and two preserved survey links become null. The unknown-date result and survey remain stored. Refresh the dashboard to confirm the expired entries disappear from the Saved panel. Repeat cleanup to verify it does not delete preserved responses; its last-successful counts update to reflect the new no-op run.

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
| Manually saved analyses | Delete expired records, including configuration and metadata, so saved/sidebar entries disappear after refresh | Approved by user October 6; implemented |
| Auto-refresh analyses | Clear expired results while preserving recurring setup; refresh in place when retention is enabled | Implemented; failed refreshes preserve retained snapshots |
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
| Preserved configuration | Auto-refresh setup, accounts, memberships, credentials, and future collection remain functional |
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
| October 6, 2026 | Selected PR #530 fixes | Fixed demo refresh, PagerDuty team scoping, directory permission, OpenAI pagination and tracked table creation | 140 backend checks passed, including 51 new regressions; provider calls mocked and destructive tests isolated; ignored findings unchanged |
| October 6, 2026 | PR #534 follow-up fixes | Preserved retained snapshots, aged error-only content, enforced complete PagerDuty collection, restored lock-deferred retries and guarded concurrent dashboard reads | 776 distinct backend checks and 6 browser cases passed; TypeScript/migration consistency passed; local migration057 completed |
| October 6, 2026 | Manual saved-record expiry | Delete expired manual saved rows and metadata; preserve recurring setup and independently aged surveys; cover previously cleared entries | 699 retention backend checks, 31 settings browser scenarios and TypeScript passed; live preview finds three prior cleared rows; next daily cleanup will remove them |

## Next action

Next is **step 7: verify the complete automatic flow in staging** with a controlled organization and synthetic data before pilot activation. The local 60-day policy's October 6, 11:40 a.m. Toronto test cleanup succeeded and deleted all three expired saved fixture records; read-only database and screenshot verification confirms their sidebar entries are gone. Its original UTC schedule has been restored; the next daily run is **October 7 at 03:00 UTC**. Review the outcome at `http://localhost:3000/management`. Delivery/security history and backups have separate retention scope. Continue using normal chat for verification questions because the terminal question widget was inaccessible.


### October 6: remaining staging review fixes

PagerDuty analysis collection now requests the complete incident window on both Analytics and REST paths, with the same selected-team filter. Analytics follows all cursors instead of stopping at 5,000 incidents. REST partitions requested history into windows no longer than 90 days, bisects windows that exceed the provider's 10,000-record offset ceiling, and deduplicates inclusive boundary records by incident ID. Failed pages, repeated cursors, timeouts, and an unsplittable one-second density ceiling fail collection rather than storing a partial report as complete. General capped API calls outside analysis collection retain their prior behavior.

Cleanup first filters likely candidates in SQL and projects eligibility metadata, avoiding full result JSON transfer for ordinary expiry. Only previously approved legacy snapshots load full contents for fingerprint comparison. Survey scans lock expired responses and affected references, rather than every response. Normal full-report endpoints project frontend-used result keys once and reuse that roster for survey enrichment; metadata guards do not refresh full result JSON. Cleanup still uses one atomic transaction for each organization.

Lock ordering remains **organization -> analysis -> dependent records**. Policy changes and cleanup use an exclusive organization lock; result reads/writes take an organization share lock first. Readers now share-lock the validated analysis metadata so the subsequent result projection belongs to the same stored snapshot. GitHub collection releases its preflight transaction before provider I/O and reacquires/rechecks policy and result eligibility after collection. Cleanup claims are nonblocking, with bounded follow-ups for due organizations skipped because of locks.

Expired retired auto-refresh carrier rows are deleted, including older unsaved carriers identifiable by their stored refresh interval. New retired carriers receive a server-written configuration marker. Active recurring configurations and ordinary unsaved configurations remain preserved; newer surveys lose only the deleted parent link. Redis cleanup clients close in a finally block on successful eviction and on failure. The unused scheduler singleton, duplicate import, unreachable selected-team REST branches and unreachable disable-confirmation JSX were removed. The tested status helper's defensive skipped-outcome handling remains.

Generation-checked caching was considered. Retention-enabled reads continue bypassing the current ID-only Redis result cache; shared-row metadata checks plus one projected result read avoid reintroducing stale results. Introducing a versioned cache requires auditing every in-place report mutation, beyond the successful-generation writer, before it can safely replace this path.

Verification: **863 backend checks passed**, including 21 new cases for complete windows, split/deduplicated REST pagination, projected reads, retired rows, and a controlled-organization HTTP/worker flow. SQL observation confirms zero full-result selections during ordinary cleanup and one result-key projection per full report GET across ID, UUID and identifier routes. The controlled organization test uses the current staging code and a guarded disposable PostgreSQL database: disabled default, read-only preview, confirmed policy save, immediate 410 enforcement, real due/claim/daily worker cleanup, saved/retired row deletion, recurring configuration preservation, independent survey expiry/detachment, demo/unknown-date/other-org preservation, cleanup status, and disabling without restoring deleted content. Authentication, providers and Redis are isolated; fixture data rolls back.

Browser verification: **25 dashboard regression scenarios** and the settings disable/cancel-prior-approval scenario passed with isolated API responses. TypeScript passed using the committed module-resolution configuration.

This is local verification of staging code, not a run against a deployed staging service. Deployed staging verification with an authenticated controlled organization remains required before pilot activation. No cleanup was manually invoked against application or deployed data.

### October 7: commit remaining UI simplifications

The retention card now uses the approved short description, omits redundant preview counts, cleanup history, refresh controls and save-success banners, and keeps the permanent-deletion warning with the daily 03:00 UTC schedule. Closing settings discards unsaved changes and restores the saved policy. Enabling/shortening still requires confirmation and internal preview validation; disabling saves directly. Admin, session and organization checks remain in place.

Verification: **31 isolated retention-settings browser scenarios**, TypeScript and whitespace checks passed. The UI, reload guidance and updated browser scenarios are committed together; backend retention behavior is unchanged.
