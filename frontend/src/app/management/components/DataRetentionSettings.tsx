"use client"

import { useEffect, useRef, useState } from "react"
import { AlertCircle, CheckCircle, Loader2, Shield } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import {
  getOrganizationRetention, previewOrganizationRetention, updateOrganizationRetention,
  RetentionApiError, type RetentionPolicyResponse, type RetentionPreviewResponse,
} from "@/lib/data-retention"

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "")

function readableDate(value: string | null) {
  return value ? new Date(value).toLocaleString(undefined, { timeZone: "UTC" }) + " UTC" : "Unknown"
}

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : "Unable to update data retention. Please try again."
}

export function DataRetentionSettings() {
  const [policy, setPolicy] = useState<RetentionPolicyResponse | null>(null)
  const [access, setAccess] = useState<"loading" | "admin" | "member" | "no-org" | "error">("loading")
  const [enabled, setEnabled] = useState(false)
  const [daysInput, setDaysInput] = useState("90")
  const [clearLegacy, setClearLegacy] = useState(false)
  const [preview, setPreview] = useState<RetentionPreviewResponse | null>(null)
  const [busy, setBusy] = useState<"preview" | "save" | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [confirmPolicy, setConfirmPolicy] = useState(false)
  const [confirmLegacy, setConfirmLegacy] = useState(false)
  const [clock, setClock] = useState(Date.now())
  const sessionToken = useRef<string | null>(null)
  const actionController = useRef<AbortController | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      setAccess("loading")
      setError(null)
      setPreview(null)
      setDialogOpen(false)
      setPolicy(null)
      const token = localStorage.getItem("auth_token")
      sessionToken.current = token
      try {
        if (!token) throw new Error("Sign in to view your organization's data retention policy.")
        const response = await fetch(`${API_BASE}/auth/user/me`, {
          headers: { Authorization: `Bearer ${token}` }, cache: "no-store", signal: controller.signal,
        })
        if (!response.ok) throw new Error("Unable to verify your account. Sign in again or refresh settings.")
        const user: { role: string; organization_id: number | null } = await response.json()
        if (controller.signal.aborted) return
        if (!user.organization_id) {
          setAccess("no-org")
          return
        }
        const saved = await getOrganizationRetention(token, controller.signal)
        if (saved.organization_id !== user.organization_id) throw new Error("Your organization changed. Refresh settings before continuing.")
        if (!/^[a-f0-9]{64}$/.test(saved.policy_version)) throw new Error("Unable to verify the saved policy version. Refresh settings before continuing.")
        if (controller.signal.aborted) return
        setPolicy(saved)
        setEnabled(saved.enabled)
        setDaysInput(String(saved.retention_days ?? 90))
        setClearLegacy(false)
        setAccess(user.role === "admin" ? "admin" : "member")
      } catch (failure) {
        if (controller.signal.aborted) return
        setError(messageFrom(failure))
        setAccess("error")
      }
    }
    void load()
    return () => { controller.abort(); actionController.current?.abort() }
  }, [reload])

  useEffect(() => {
    if (!preview?.legacy_cleanup.preview_expires_at) return
    setClock(Date.now())
    const timer = window.setInterval(() => setClock(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [preview])

  const isAdmin = access === "admin"
  const validDays = /^\d+$/.test(daysInput) && Number(daysInput) >= 1 && Number(daysInput) <= 3650
  const days = enabled ? Number(daysInput) : null
  const invalidDays = enabled && !validDays
  const pendingLegacy = policy?.legacy_cleanup.state === "pending"
  const policyChanged = policy !== null && days !== policy.retention_days
  const previewMatches = preview !== null && preview.retention_days === days && preview.legacy_cleanup.requested === clearLegacy
  const legacyExpired = clearLegacy && preview !== null && (
    !preview.legacy_cleanup.preview_token || !preview.legacy_cleanup.preview_expires_at ||
    new Date(preview.legacy_cleanup.preview_expires_at).getTime() <= clock
  )
  const needsPolicyConfirmation = days !== null && policy !== null && (
    policy.retention_days === null || days < policy.retention_days
  )
  const canSave = isAdmin && !busy && !invalidDays && previewMatches && !legacyExpired && (policyChanged || clearLegacy)

  function invalidatePreview() {
    setPreview(null)
    setError(null)
    setSuccess(null)
    setConfirmPolicy(false)
    setConfirmLegacy(false)
  }

  async function verifiedTokenForAction(signal: AbortSignal) {
    const token = localStorage.getItem("auth_token")
    if (!token || token !== sessionToken.current) throw new Error("Your session changed. Refresh settings before continuing.")
    const response = await fetch(`${API_BASE}/auth/user/me`, {
      headers: { Authorization: `Bearer ${token}` }, cache: "no-store", signal,
    })
    if (!response.ok) throw new Error("Unable to verify your account. Sign in again or refresh settings.")
    const user: { role: string; organization_id: number | null } = await response.json()
    if (user.organization_id !== policy?.organization_id || user.role !== "admin") {
      throw new Error("Your organization or permissions changed. Refresh settings before continuing.")
    }
    if (localStorage.getItem("auth_token") !== token || token !== sessionToken.current) {
      throw new Error("Your session changed. Refresh settings before continuing.")
    }
    return token
  }

  async function requestPreview() {
    if (!isAdmin || invalidDays || busy) return
    setBusy("preview")
    setError(null)
    setSuccess(null)
    setPreview(null)
    setConfirmPolicy(false)
    setConfirmLegacy(false)
    const controller = new AbortController()
    actionController.current = controller
    try {
      const result = await previewOrganizationRetention(await verifiedTokenForAction(controller.signal), {
        retention_days: days, clear_unverifiable_analyses: clearLegacy,
      }, controller.signal)
      if (controller.signal.aborted) return
      if (result.organization_id !== policy?.organization_id) throw new Error("Your organization changed. Refresh settings before continuing.")
      setClock(Date.now())
      setPreview(result)
    } catch (failure) {
      if (controller.signal.aborted) return
      setError(messageFrom(failure))
    } finally {
      if (!controller.signal.aborted) setBusy(null)
    }
  }

  async function savePolicy() {
    if (!canSave || (needsPolicyConfirmation && !confirmPolicy) || (clearLegacy && !confirmLegacy)) return
    setBusy("save")
    setError(null)
    const controller = new AbortController()
    actionController.current = controller
    try {
      const result = await updateOrganizationRetention(await verifiedTokenForAction(controller.signal), {
        retention_days: days,
        expected_policy_version: policy!.policy_version,
        ...(needsPolicyConfirmation ? { confirm_deletion: confirmPolicy } : {}),
        ...(clearLegacy ? {
          clear_unverifiable_analyses: true, confirm_legacy_deletion: confirmLegacy,
          legacy_preview_token: preview!.legacy_cleanup.preview_token,
        } : {}),
      }, controller.signal)
      if (controller.signal.aborted) return
      if (result.organization_id !== policy?.organization_id) throw new Error("Your organization changed. Refresh settings to verify the saved policy.")
      if (!/^[a-f0-9]{64}$/.test(result.policy_version)) throw new Error("Unable to verify the saved policy version. Refresh settings to verify the saved policy.")
      setPolicy(result)
      setEnabled(result.enabled)
      setDaysInput(String(result.retention_days ?? 90))
      setClearLegacy(false)
      setPreview(null)
      setDialogOpen(false)
      setConfirmPolicy(false)
      setConfirmLegacy(false)
      setSuccess(result.enabled
        ? "Retention policy saved. Cleanup uses these settings at the next daily run at 03:00 UTC, within 24 hours; no data was deleted by this save."
        : "Retention disabled. Any pending legacy cleanup approval has been cancelled.")
    } catch (failure) {
      if (controller.signal.aborted) return
      setError(messageFrom(failure))
      // A failed or ambiguous save must never leave a receipt ready for reuse.
      setPreview(null)
      setDialogOpen(false)
      setConfirmPolicy(false)
      setConfirmLegacy(false)
      if (failure instanceof RetentionApiError && (failure.status === 401 || failure.status === 403)) setAccess("error")
    } finally {
      if (!controller.signal.aborted) setBusy(null)
    }
  }

  const legacy = policy?.legacy_cleanup
  const cleanup = policy?.cleanup_status
  const deletionWarning = needsPolicyConfirmation && !invalidDays ? (
    <div role="alert" aria-label="Existing data deletion warning" className="space-y-3 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm leading-relaxed text-amber-950">
      <p className="font-semibold">Permanent deletion of existing data</p>
      <p>{policy?.retention_days === null ? `Enabling ${days}-day retention` : `Shortening retention to ${days} days`} will permanently clear entire analysis results generated more than {days} days ago, including the imported activity, historical metrics, enrichments, and insights stored inside them, and delete survey responses submitted more than {days} days ago. This applies to existing data as well as future data.</p>
      <p>Newer survey responses, analysis configuration, accounts, memberships, and integration settings are preserved. Deleted data cannot be restored by disabling retention or increasing the period.</p>
      <p>Expired analysis results and results with unknown generation dates become unavailable immediately when the policy is saved. Physical deletion happens during cleanup; saving does not run deletion. Results with unknown generation dates require separate approval for deletion.</p>
    </div>
  ) : null

  return (
    <section aria-labelledby="data-retention-heading" className="mb-6 rounded-lg border border-neutral-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-neutral-200 p-6">
        <div>
          <h2 id="data-retention-heading" className="flex items-center gap-2 text-lg font-semibold text-neutral-900">
            <Shield className="h-5 w-5 text-purple-700" aria-hidden="true" /> Data retention
          </h2>
          <p className="mt-1 max-w-xl text-sm text-neutral-600">One policy for your whole On-Call Health organization, across its integrations and teams.</p>
        </div>
        {policy && <span className={`rounded-full px-3 py-1 text-xs font-medium ${policy.enabled ? "bg-purple-100 text-purple-800" : "bg-neutral-100 text-neutral-600"}`}>
          {policy.enabled ? `Saved · Enabled · ${policy.retention_days} days` : "Saved · Disabled"}
        </span>}
      </div>
      <div className="space-y-5 p-6">
        {access === "loading" && <p role="status" className="flex items-center gap-2 text-sm text-neutral-600"><Loader2 className="h-4 w-4 animate-spin" /> Loading retention settings…</p>}
        {access === "no-org" && <p className="text-sm text-neutral-600">Join an organization to use organization data retention.</p>}
        {error && <p role="alert" className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</p>}
        {success && <p role="status" className="flex items-start gap-2 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800"><CheckCircle className="mt-0.5 h-4 w-4 shrink-0" />{success}</p>}
        {policy && (access === "admin" || access === "member") && <>
          <p className="text-sm leading-relaxed text-neutral-600">Analysis results expire N days after their latest successful generation. Each result can cover your requested historical window, even when its events are older than N days. A successful rerun starts a new retention period for the replacement result. Surveys expire by their own submission age; newer surveys survive and their links to expired analyses are cleared. Saved analysis configuration, accounts, memberships, and integration settings are preserved.</p>
          <div aria-label="Automatic cleanup timing" className="space-y-2 rounded-md bg-neutral-50 p-3 text-sm leading-relaxed text-neutral-600">
            <p>{policy.enabled
              ? "Automatic cleanup runs once a day at 03:00 UTC. Newly enabled or changed policies and approved legacy batches are included at the next daily run, within 24 hours."
              : "Retention is disabled. No automatic cleanup is scheduled for this organization. Enable and save a policy to schedule cleanup."}</p>
            <p>Saving does not delete data. Expired results become unavailable immediately when retention is enabled; stored content is cleared during cleanup. Only failed cleanup attempts are retried sooner, with increasing delays from 15 minutes up to 6 hours, while retention remains enabled.</p>
          </div>
          {isAdmin ? <>
            <div className="flex items-start justify-between gap-4">
              <div><label htmlFor="retention-enabled" className="text-sm font-medium text-neutral-900">Enable data retention</label><p id="retention-enabled-help" className="mt-1 text-xs text-neutral-500">Disabled by default. Disabling cancels pending legacy cleanup approval and cannot restore deleted data.</p></div>
              <Switch id="retention-enabled" checked={enabled} disabled={Boolean(busy)} aria-describedby="retention-enabled-help" onCheckedChange={(value) => { setEnabled(value); setClearLegacy(false); invalidatePreview() }} />
            </div>
            <div>
              <label htmlFor="retention-days" className="mb-2 block text-sm font-medium text-neutral-900">Retention period (days)</label>
              <Input id="retention-days" type="number" min={1} max={3650} step={1} value={daysInput} disabled={!enabled || Boolean(busy)} aria-invalid={invalidDays} aria-describedby="retention-days-help" className="max-w-44" onChange={(event) => { setDaysInput(event.target.value); invalidatePreview() }} />
              <p id="retention-days-help" className={`mt-2 text-xs ${invalidDays ? "text-red-700" : "text-neutral-500"}`}>{invalidDays ? "Enter a whole number from 1 to 3650." : "Keep each analysis result for N days after successful generation, and each survey response for N days after submission, measured in UTC. Existing data uses the same cutoff."}</p>
            </div>
            {deletionWarning}
            <div className="rounded-md border border-neutral-200 p-4">
              <div className="flex items-start gap-3">
                <Checkbox id="retention-legacy" checked={clearLegacy} disabled={!enabled || Boolean(busy) || pendingLegacy} aria-describedby="retention-legacy-help" onCheckedChange={(checked) => { setClearLegacy(checked === true); invalidatePreview() }} />
                <label htmlFor="retention-legacy" className="text-sm font-medium leading-5 text-neutral-900">Include results with unknown generation dates in this one-time cleanup</label>
              </div>
              <p id="retention-legacy-help" className="mt-2 text-xs leading-relaxed text-neutral-600">Optional: clear reviewed analysis results whose generation dates cannot be verified. This requires a separate confirmation and does not authorize clearing future results with unknown generation dates. Surveys with unknown submission dates remain for separate review.</p>
              {pendingLegacy && <p className="mt-2 text-xs text-amber-800">An approved legacy batch is pending. It must complete or be cancelled by disabling retention before another batch can be approved.</p>}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => void requestPreview()} disabled={Boolean(busy) || invalidDays}>{busy === "preview" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Preview deletion</Button>
              <Button className="bg-purple-700 text-white hover:bg-purple-800" disabled={!canSave} onClick={() => { setConfirmPolicy(false); setConfirmLegacy(false); setDialogOpen(true) }}>Save retention policy</Button>
              <Button variant="ghost" disabled={Boolean(busy)} onClick={() => { setSuccess(null); setReload((value) => value + 1) }}>Refresh settings</Button>
            </div>
            {!preview && <p className="text-xs text-neutral-500">Preview the proposed settings before saving. Previewing does not save the policy or delete data.</p>}
            {legacyExpired && <p role="alert" className="text-sm text-amber-800">The legacy preview expired. Run Preview deletion again before saving.</p>}
          </> : <div className="space-y-3"><p className="text-sm text-neutral-500">Only organization admins can change this policy or preview deletion.</p><Button variant="ghost" onClick={() => setReload((value) => value + 1)}>Refresh settings</Button></div>}

          <details className="rounded-md border border-neutral-200 p-4 text-sm">
            <summary className="cursor-pointer font-medium text-neutral-800">Analysis history and retention</summary>
            <p className="mt-2 leading-relaxed text-neutral-600">Retention keeps the full analysis window you requested and existing integration behavior. GitHub, Slack, Jira, Linear, AI usage, and Rootly alert enrichment follow their existing integration settings; retention does not omit additional inputs. Imported activity and metrics are kept within the generated result and cleared together when that result expires. The analysis window and retention period are independent: a six-month analysis keeps its six months of available source data, and the entire generated result expires N days after generation. Retention does not shorten the analysis window. A successful rerun replaces the result and starts a new N-day period; it can import older source events again.</p>
            <p className="mt-2 leading-relaxed text-neutral-600">Results whose generation dates cannot be verified are unavailable while retention is enabled. They require a successful rerun or separate approval for cleanup. Surveys follow their own submission dates.</p>
          </details>

          {cleanup && <div className="space-y-3 rounded-md border border-neutral-200 p-4 text-sm" aria-label="Automatic cleanup status">
            <h3 className="font-medium text-neutral-900">Automatic cleanup status: {cleanup.state === "never" ? "Not run yet" : cleanup.state === "succeeded" ? "Succeeded" : cleanup.state === "failed" ? "Failed" : "Skipped"}</h3>
            {cleanup.state === "never" && <p className="text-neutral-600">No cleanup has run for this organization yet.</p>}
            {cleanup.state === "failed" && <p role="alert" className="rounded-md bg-red-50 p-3 leading-relaxed text-red-800">{cleanup.message || "Cleanup could not finish. The organization will be retried automatically while retention remains enabled."}</p>}
            {cleanup.state === "skipped" && cleanup.message && <p className="text-neutral-600">{cleanup.message}</p>}
            <dl className="grid gap-2 text-xs text-neutral-600 sm:grid-cols-2">
              <div><dt className="font-medium">Last attempt</dt><dd>{cleanup.last_attempt_at ? readableDate(cleanup.last_attempt_at) : "Never"}</dd></div>
              <div><dt className="font-medium">Last attempt finished</dt><dd>{cleanup.last_finished_at ? readableDate(cleanup.last_finished_at) : "Never"}</dd></div>
              <div><dt className="font-medium">Last successful cleanup</dt><dd>{cleanup.last_success_at ? readableDate(cleanup.last_success_at) : "Never"}</dd></div>
              <div><dt className="font-medium">{cleanup.next_retry_at && policy.enabled ? "Next retry eligible" : "Next cleanup due"}</dt><dd>{policy.enabled
                ? cleanup.next_retry_at ? readableDate(cleanup.next_retry_at) : cleanup.next_cleanup_due_at ? readableDate(cleanup.next_cleanup_due_at) : "At the next daily cleanup"
                : "Not scheduled while retention is disabled"}</dd></div>
            </dl>
            {policy.enabled && <p className="text-xs text-neutral-500">The next cleanup is scheduled for the daily run at 03:00 UTC, or the displayed retry time after a failure. Cleanup may finish later if another run is in progress.</p>}
            {cleanup.state !== "never" && <>
              <p className="text-xs text-neutral-500">Counts below are from the last successful cleanup. A failed attempt does not replace those counts.</p>
              <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  ["Analysis results cleared", cleanup.counts.analysis_results_expired],
                  ["Legacy results cleared", cleanup.counts.legacy_analysis_results_cleared],
                  ["Survey responses deleted", cleanup.counts.survey_responses_deleted],
                  ["Survey links detached", cleanup.counts.survey_links_cleared],
                ].map(([label, count]) => <div key={label} className="rounded-md bg-neutral-50 p-3"><dt className="text-xs leading-5 text-neutral-600">{label}</dt><dd className="mt-1 text-xl font-semibold tabular-nums text-neutral-900">{count}</dd></div>)}
              </dl>
              <details className="rounded-md border border-neutral-200 p-3 text-xs leading-relaxed text-neutral-600">
                <summary className="cursor-pointer font-medium">Related cleanup outcomes</summary>
                <p className="mt-2">Mappings removed: {cleanup.counts.mappings_deleted}; notifications removed: {cleanup.counts.notifications_deleted}; survey-period links cleared: {cleanup.counts.survey_period_links_cleared}; digest links cleared: {cleanup.counts.digest_links_cleared}.</p>
                <p className="mt-2">Results with unknown generation dates found: {cleanup.counts.analyses_unverifiable}; running or pending results deferred: {cleanup.counts.analyses_deferred}; approved legacy results skipped: {cleanup.counts.legacy_analyses_skipped}; approved legacy results deferred: {cleanup.counts.legacy_analyses_deferred}; surveys with unknown submission dates preserved: {cleanup.counts.surveys_unverifiable}.</p>
              </details>
            </>}
            {cleanup.state === "failed" && <p className="text-xs text-neutral-500">Consecutive failed attempts: {cleanup.consecutive_failures}.</p>}
          </div>}
          {legacy && legacy.state !== "none" && <div className="rounded-md border border-neutral-200 p-4 text-sm" aria-label="Legacy cleanup status">
            <h3 className="font-medium text-neutral-900">Legacy cleanup status: {legacy.state}</h3>
            <p className="mt-2 text-neutral-600">Approved: {legacy.requested_count} · Pending: {legacy.pending_count} · Cleared: {legacy.cleared_count} · Skipped: {legacy.skipped_count} · Cancelled: {legacy.cancelled_count}</p>
            <p className="mt-1 text-xs text-neutral-500">Approved {readableDate(legacy.approved_at)}{legacy.finished_at ? ` · Finished ${readableDate(legacy.finished_at)}` : ""}</p>
          </div>}
          {policy.updated_at && <p className="text-xs text-neutral-500">Policy last changed {readableDate(policy.updated_at)}.</p>}
        </>}
        {access === "error" && <Button variant="outline" onClick={() => setReload((value) => value + 1)}>Refresh settings</Button>}

        {preview && previewMatches && <div className="space-y-4 border-t border-neutral-200 pt-5" aria-label="Deletion preview">
          <div><h3 className="font-semibold text-neutral-900">Deletion preview</h3><p className="mt-1 text-xs text-neutral-500">Evaluated {readableDate(preview.evaluated_at)}{preview.cutoff_at ? ` · Results generated or surveys submitted before ${readableDate(preview.cutoff_at)}` : " · Retention disabled: no expiry candidates"}</p></div>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["Analysis results to expire", preview.analyses.expired],
              ["Survey responses to delete", preview.survey_responses.expired],
              [preview.legacy_cleanup.requested ? "Legacy results to clear" : "Approved legacy results", preview.legacy_cleanup.analysis_candidates],
              ["Survey links to detach", preview.related_records.survey_links_to_clear],
            ].map(([label, count]) => <div key={label} className="rounded-md bg-neutral-50 p-3"><dt className="text-xs leading-5 text-neutral-600">{label}</dt><dd className="mt-1 text-xl font-semibold tabular-nums text-neutral-900">{count}</dd></div>)}
          </dl>
          <p className="text-sm text-neutral-600">Results with unknown generation dates: {preview.analyses.unverifiable} · Surveys with unknown submission dates: {preview.survey_responses.unverifiable} · Running or pending analyses deferred: {preview.analyses.deferred}.</p>
          <p className="text-xs text-neutral-500">Retained: {preview.analyses.retained} analysis results and {preview.survey_responses.retained} surveys. Surveys with unknown submission dates are not deleted by legacy approval. Changing any setting requires a new preview.</p>
          <p className="text-xs text-neutral-500">Counts can change before cleanup as data and the rolling cutoff change.</p>
          {preview.legacy_cleanup.preview_expires_at && <p className="text-xs text-neutral-500">Legacy approval preview valid until {readableDate(preview.legacy_cleanup.preview_expires_at)}.</p>}
          {preview.warnings.length > 0 && <ul className="list-disc space-y-1 pl-5 text-xs leading-relaxed text-amber-900">{preview.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>}
          <details className="rounded-md border border-neutral-200 p-3 text-sm"><summary className="cursor-pointer font-medium">Related records</summary><p className="mt-2 leading-relaxed text-neutral-600">Mappings to remove: {preview.related_records.analysis_mappings}; notifications to remove: {preview.related_records.analysis_notifications}; survey-period links to clear: {preview.related_records.survey_period_links_to_clear}; digest links to clear: {preview.related_records.digest_links_to_clear}; references requiring review: {preview.related_records.references_requiring_review}.</p></details>
          {preview.samples.length > 0 && <details className="rounded-md border border-neutral-200 p-3 text-sm"><summary className="cursor-pointer font-medium">Analysis samples ({preview.samples.length})</summary><div className="mt-3 max-h-72 overflow-auto"><table className="w-full text-left text-xs"><thead><tr className="border-b"><th className="p-2">Analysis</th><th className="p-2">Generated</th><th className="p-2">Outcome</th><th className="p-2">Reason</th></tr></thead><tbody>{preview.samples.map((sample) => <tr key={sample.analysis_id} className="border-b last:border-0"><td className="whitespace-nowrap p-2 align-top">#{sample.analysis_id}{sample.is_saved ? " · Saved" : ""}{sample.is_auto_refresh ? " · Auto-refresh" : ""}</td><td className="p-2 align-top">{readableDate(sample.generation_at)}</td><td className="p-2 align-top">{sample.will_clear_as_legacy ? "Legacy clear" : sample.disposition}</td><td className="p-2 align-top">{sample.reason}</td></tr>)}</tbody></table></div>{preview.samples_truncated && <p className="mt-2 text-xs text-neutral-500">Only the first 100 analyses are shown. Counts include all organization data.</p>}</details>}
        </div>}
      </div>
      <Dialog open={dialogOpen} onOpenChange={(open) => { if (busy !== "save") setDialogOpen(open) }}>
        <DialogContent className="max-h-[85vh] max-w-xl overflow-y-auto">
          <DialogHeader><DialogTitle>Confirm retention policy</DialogTitle><DialogDescription>{enabled ? `Keep each analysis result for ${days} days after successful generation, and each survey response for ${days} days after submission.` : "Disable organization data retention."}</DialogDescription></DialogHeader>
          <div className="space-y-4 text-sm">
            {deletionWarning || <p>Saving configures future cleanup. It does not delete data immediately. Deleted data cannot be restored by increasing the period or disabling retention.</p>}
            {enabled && preview && <p aria-label="Cleanup preview summary" className="rounded-md bg-neutral-50 p-3">This preview identifies {preview.analyses.expired} expired analysis results, {preview.survey_responses.expired} old survey responses, and {preview.legacy_cleanup.analysis_candidates} legacy results to clear. Counts can change before cleanup.</p>}
            {!enabled && pendingLegacy && <p className="rounded-md bg-amber-50 p-3 text-amber-900">Disabling retention will cancel the {policy?.legacy_cleanup.pending_count} remaining entries in the approved legacy cleanup batch.</p>}
            {needsPolicyConfirmation && <div className="flex items-start gap-3"><Checkbox id="confirm-retention-policy" checked={confirmPolicy} disabled={Boolean(busy)} onCheckedChange={(value) => setConfirmPolicy(value === true)} /><label htmlFor="confirm-retention-policy" className="leading-5">I understand this policy can permanently delete existing analysis results and old survey responses.</label></div>}
            {clearLegacy && <><p className="text-xs text-neutral-600">Legacy clearing applies only to the unchanged results reviewed in this preview. Newer surveys survive, and surveys with unknown submission dates are preserved.</p><div className="flex items-start gap-3"><Checkbox id="confirm-retention-legacy" checked={confirmLegacy} disabled={Boolean(busy)} onCheckedChange={(value) => setConfirmLegacy(value === true)} /><label htmlFor="confirm-retention-legacy" className="leading-5">I also confirm clearing the reviewed results with unknown generation dates.</label></div></>}
            {legacyExpired && <p role="alert" className="text-amber-900">The legacy preview expired. Close this dialog and run a new preview.</p>}
          </div>
          <DialogFooter><Button variant="outline" disabled={Boolean(busy)} onClick={() => setDialogOpen(false)}>Cancel</Button><Button className="bg-purple-700 text-white hover:bg-purple-800" disabled={!canSave || (needsPolicyConfirmation && !confirmPolicy) || (clearLegacy && !confirmLegacy)} onClick={() => void savePolicy()}>{busy === "save" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Confirm and save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
