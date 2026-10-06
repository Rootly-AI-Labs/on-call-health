"use client"

import { useEffect, useRef, useState } from "react"
import { AlertCircle, CheckCircle, ChevronDown, Loader2 } from "lucide-react"
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
  const [preview, setPreview] = useState<RetentionPreviewResponse | null>(null)
  const [busy, setBusy] = useState<"preview" | "save" | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [confirmPolicy, setConfirmPolicy] = useState(false)
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

  const isAdmin = access === "admin"
  const validDays = /^\d+$/.test(daysInput) && Number(daysInput) >= 1 && Number(daysInput) <= 3650
  const days = enabled ? Number(daysInput) : null
  const invalidDays = enabled && !validDays
  const pendingLegacy = policy?.legacy_cleanup.state === "pending"
  const policyChanged = policy !== null && days !== policy.retention_days
  const previewMatches = preview !== null && preview.retention_days === days
  const needsPolicyConfirmation = days !== null && policy !== null && (
    policy.retention_days === null || days < policy.retention_days
  )
  const canSave = isAdmin && !busy && !invalidDays && previewMatches && policyChanged

  function invalidatePreview() {
    setPreview(null)
    setError(null)
    setSuccess(null)
    setConfirmPolicy(false)
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
    const controller = new AbortController()
    actionController.current = controller
    try {
      const result = await previewOrganizationRetention(await verifiedTokenForAction(controller.signal), {
        retention_days: days,
      }, controller.signal)
      if (controller.signal.aborted) return
      if (result.organization_id !== policy?.organization_id) throw new Error("Your organization changed. Refresh settings before continuing.")
      setPreview(result)
    } catch (failure) {
      if (controller.signal.aborted) return
      setError(messageFrom(failure))
    } finally {
      if (!controller.signal.aborted) setBusy(null)
    }
  }

  async function savePolicy() {
    if (!canSave || (needsPolicyConfirmation && !confirmPolicy)) return
    setBusy("save")
    setError(null)
    const controller = new AbortController()
    actionController.current = controller
    try {
      const result = await updateOrganizationRetention(await verifiedTokenForAction(controller.signal), {
        retention_days: days,
        expected_policy_version: policy!.policy_version,
        ...(needsPolicyConfirmation ? { confirm_deletion: confirmPolicy } : {}),
      }, controller.signal)
      if (controller.signal.aborted) return
      if (result.organization_id !== policy?.organization_id) throw new Error("Your organization changed. Refresh settings to verify the saved policy.")
      if (!/^[a-f0-9]{64}$/.test(result.policy_version)) throw new Error("Unable to verify the saved policy version. Refresh settings to verify the saved policy.")
      setPolicy(result)
      setEnabled(result.enabled)
      setDaysInput(String(result.retention_days ?? 90))
      setPreview(null)
      setDialogOpen(false)
      setConfirmPolicy(false)
      setSuccess(result.enabled
        ? "Retention policy saved. Cleanup uses these settings at the next daily run at 03:00 UTC; no data was deleted by this save."
        : pendingLegacy ? "Retention disabled. The prior cleanup approval has been cancelled." : "Retention disabled.")
    } catch (failure) {
      if (controller.signal.aborted) return
      setError(messageFrom(failure))
      // A failed or ambiguous save requires a fresh preview before another attempt.
      setPreview(null)
      setDialogOpen(false)
      setConfirmPolicy(false)
      if (failure instanceof RetentionApiError && (failure.status === 401 || failure.status === 403)) setAccess("error")
    } finally {
      if (!controller.signal.aborted) setBusy(null)
    }
  }

  const cleanup = policy?.cleanup_status
  const cleanupState = cleanup?.state === "never" ? "Not run yet" : cleanup?.state === "succeeded" ? "Succeeded" : cleanup?.state === "failed" ? "Failed" : "Skipped"
  const unsavedChanges = policyChanged
  const deletionWarning = needsPolicyConfirmation && !invalidDays ? (
    <div role="alert" aria-label="Existing data deletion warning" className="space-y-3 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm leading-relaxed text-amber-950">
      <p className="font-semibold">Permanent deletion of existing data</p>
      <p>{policy?.retention_days === null ? `Enabling ${days}-day retention` : `Shortening retention to ${days} days`} will permanently clear entire analysis results generated more than {days} days ago, including the imported activity, historical metrics, enrichments, and insights stored inside them, and delete survey responses submitted more than {days} days ago. This applies to existing data as well as future data.</p>
      <p>Expired manually saved analyses are deleted, including their configuration and metadata. Newer survey responses, auto-refresh configuration, accounts, memberships, and integration settings are preserved. Deleted data cannot be restored by disabling retention or increasing the period.</p>
      <p>Expired analysis results and results with unknown generation dates become unavailable immediately when the policy is saved. Physical deletion happens during cleanup; saving does not run deletion. Results with unknown generation dates are preserved until successfully regenerated.{pendingLegacy && " Previously approved, unchanged results may still be cleared at cleanup."}</p>
    </div>
  ) : null

  return (
    <section aria-labelledby="data-retention-heading" className="mb-6 rounded-lg border border-neutral-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3 p-4">
        <div className="flex min-w-0 items-center gap-3">
          <div>
            <h2 id="data-retention-heading" className="text-sm font-semibold text-neutral-900">Data retention</h2>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {access === "loading" && <span role="status" className="flex items-center gap-2 text-xs text-neutral-500"><Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading settings…</span>}
          {policy && <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${policy.enabled ? "bg-purple-100 text-purple-800" : "bg-neutral-100 text-neutral-600"}`}>
            {policy.enabled ? "Enabled" : "Disabled"}
          </span>}
          {unsavedChanges && <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">Unsaved changes</span>}
          {cleanup?.state === "failed" && <span role="status" className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700">{policy?.enabled ? "Cleanup needs attention" : "Last cleanup failed"}</span>}
          {pendingLegacy && <span role="status" className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">Prior cleanup approval pending</span>}
          <Button variant="ghost" size="sm" aria-label={expanded ? "Close data retention settings" : isAdmin ? "Configure data retention settings" : "View settings for data retention"} aria-expanded={expanded} aria-controls="data-retention-panel" disabled={!policy || Boolean(busy)} onClick={() => setExpanded((value) => !value)}>
            {expanded ? "Close" : isAdmin ? "Configure" : "View settings"}<ChevronDown className={`ml-1.5 h-4 w-4 transition-transform ${expanded ? "rotate-180" : ""}`} aria-hidden="true" />
          </Button>
        </div>
      </div>
      {access === "no-org" && <p className="px-4 pb-4 text-sm text-neutral-600">Join an organization to use organization data retention.</p>}
      {error && <div className="px-4 pb-4"><p role="alert" className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</p></div>}
      {success && <div className="px-4 pb-4"><p role="status" className="flex items-start gap-2 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800"><CheckCircle className="mt-0.5 h-4 w-4 shrink-0" />{success}</p></div>}
      {access === "error" && <div className="px-4 pb-4"><Button variant="outline" onClick={() => setReload((value) => value + 1)}>Refresh settings</Button></div>}
      <div id="data-retention-panel" hidden={!expanded} className="space-y-4 border-t border-neutral-200 p-4">
        {policy && (access === "admin" || access === "member") && <>
          <p id="retention-days-help" className="text-xs text-neutral-500">Data retention, when enabled, deletes manually saved analyses N days after generation and survey responses N days after submission; auto-refresh results expire while their setup is kept.</p>
          {isAdmin ? <>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex items-start justify-between gap-4 rounded-md bg-neutral-50 p-3">
                <div><label htmlFor="retention-enabled" className="text-sm font-medium text-neutral-900">Enable data retention</label><p id="retention-enabled-help" className="mt-1 text-xs text-neutral-500">Off by default. Applies to everyone in this organization.</p></div>
                <Switch id="retention-enabled" checked={enabled} disabled={Boolean(busy)} aria-describedby="retention-enabled-help" onCheckedChange={(value) => { setEnabled(value); invalidatePreview() }} />
              </div>
              <div>
                <label htmlFor="retention-days" className="mb-1.5 block text-sm font-medium text-neutral-900">Retention period (days)</label>
                <Input id="retention-days" type="number" min={1} max={3650} step={1} value={daysInput} disabled={!enabled || Boolean(busy)} aria-invalid={invalidDays} aria-describedby={invalidDays ? "retention-days-help retention-days-error" : "retention-days-help"} className="max-w-32" onChange={(event) => { setDaysInput(event.target.value); invalidatePreview() }} />
              </div>
            </div>
            {invalidDays && <p id="retention-days-error" className="text-xs text-red-700">Enter a whole number from 1 to 3650.</p>}
            {needsPolicyConfirmation && !invalidDays && <p role="alert" aria-label="Existing data deletion warning" className="flex items-start gap-2 rounded-md bg-amber-50 p-3 text-xs leading-relaxed text-amber-950"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />{policy.retention_days === null ? "Enabling" : "Shortening"} retention permanently clears existing results generated and surveys submitted more than {days} days ago during cleanup.</p>}
            {pendingLegacy && <p role="status" className="rounded-md bg-amber-50 p-3 text-xs leading-relaxed text-amber-950">An earlier approval to clear {policy.legacy_cleanup.pending_count} results with unknown generation dates is still pending. These unchanged results may be cleared at cleanup. Turn retention off and save to cancel the remaining approval.</p>}
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => void requestPreview()} disabled={Boolean(busy) || invalidDays}>{busy === "preview" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Preview deletion</Button>
              <Button className="bg-purple-700 text-white hover:bg-purple-800" disabled={!canSave} onClick={() => { setConfirmPolicy(false); setDialogOpen(true) }}>Save retention policy</Button>
              <Button variant="ghost" disabled={Boolean(busy)} onClick={() => { setSuccess(null); setReload((value) => value + 1) }}>Refresh settings</Button>
            </div>
          </> : <div className="space-y-3">{policy.enabled && <p className="text-sm text-neutral-700">Retention period: <span className="font-medium">{policy.retention_days} days</span></p>}<p className="text-sm text-neutral-500">Only organization admins can change this policy or preview deletion.</p><Button variant="ghost" onClick={() => setReload((value) => value + 1)}>Refresh settings</Button></div>}


          {cleanup && <details open={historyOpen} onToggle={(event) => setHistoryOpen(event.currentTarget.open)} className="rounded-md border border-neutral-200 p-3 text-sm" aria-label="Automatic cleanup status">
            <summary className="cursor-pointer font-medium text-neutral-800">Cleanup history<span className={`ml-2 rounded-full px-2 py-0.5 text-xs font-normal ${cleanup.state === "failed" ? "bg-red-50 text-red-700" : "bg-neutral-100 text-neutral-500"}`}>{cleanupState}</span></summary>
            <div className="mt-3 space-y-3">
              <h3 className="sr-only">Automatic cleanup status: {cleanupState}</h3>
              {cleanup.state === "never" && <p className="text-xs text-neutral-600">No cleanup has run for this organization yet.{policy.enabled && <> Next cleanup: {cleanup.next_cleanup_due_at ? readableDate(cleanup.next_cleanup_due_at) : "the next daily run at 03:00 UTC"}.</>}</p>}
              {cleanup.state === "failed" && <p role="alert" className="rounded-md bg-red-50 p-3 leading-relaxed text-red-800">{cleanup.message || "Cleanup could not finish. The organization will be retried automatically while retention remains enabled."}</p>}
              {cleanup.state === "skipped" && cleanup.message && <p className="text-neutral-600">{cleanup.message}</p>}
              {cleanup.state !== "never" && <dl className="grid gap-2 text-xs text-neutral-600 sm:grid-cols-2">
                <div><dt className="font-medium">Last attempt</dt><dd>{cleanup.last_attempt_at ? readableDate(cleanup.last_attempt_at) : "Never"}</dd></div>
                <div><dt className="font-medium">Last attempt finished</dt><dd>{cleanup.last_finished_at ? readableDate(cleanup.last_finished_at) : "Never"}</dd></div>
                <div><dt className="font-medium">Last successful cleanup</dt><dd>{cleanup.last_success_at ? readableDate(cleanup.last_success_at) : "Never"}</dd></div>
                <div><dt className="font-medium">{cleanup.next_retry_at && policy.enabled ? "Next retry eligible" : "Next cleanup due"}</dt><dd>{policy.enabled
                  ? cleanup.next_retry_at ? readableDate(cleanup.next_retry_at) : cleanup.next_cleanup_due_at ? readableDate(cleanup.next_cleanup_due_at) : "At the next daily cleanup"
                  : "Not scheduled while retention is disabled"}</dd></div>
              </dl>}
              {policy.enabled && cleanup.state !== "never" && <p className="text-xs text-neutral-500">Cleanup runs daily at 03:00 UTC, or at the displayed retry time after a failure. It may finish later if another run is in progress.</p>}
              {cleanup.state !== "never" && <>
                <p className="text-xs text-neutral-500">Counts below are from the last successful cleanup. A failed attempt does not replace those counts.</p>
                <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {[
                    ["Analysis results cleared", cleanup.counts.analysis_results_expired + cleanup.counts.legacy_analysis_results_cleared],
                    ["Survey responses deleted", cleanup.counts.survey_responses_deleted],
                    ["Survey links detached", cleanup.counts.survey_links_cleared],
                  ].map(([label, count]) => <div key={label} className="rounded-md bg-neutral-50 p-3"><dt className="text-xs leading-5 text-neutral-600">{label}</dt><dd className="mt-1 text-xl font-semibold tabular-nums text-neutral-900">{count}</dd></div>)}
                </dl>
                <details className="rounded-md border border-neutral-200 p-3 text-xs leading-relaxed text-neutral-600">
                  <summary className="cursor-pointer font-medium">Related cleanup outcomes</summary>
                  <p className="mt-2">Mappings removed: {cleanup.counts.mappings_deleted}; notifications removed: {cleanup.counts.notifications_deleted}; survey-period links cleared: {cleanup.counts.survey_period_links_cleared}; digest links cleared: {cleanup.counts.digest_links_cleared}.</p>
                  <p className="mt-2">Results with unknown generation dates found: {cleanup.counts.analyses_unverifiable}; running or pending results deferred: {cleanup.counts.analyses_deferred}; surveys with unknown submission dates preserved: {cleanup.counts.surveys_unverifiable}.</p>
                </details>
              </>}
              {cleanup.state === "failed" && <p className="text-xs text-neutral-500">Consecutive failed attempts: {cleanup.consecutive_failures}.</p>}
              {policy.updated_at && <p className="text-xs text-neutral-500">Policy last changed {readableDate(policy.updated_at)}.</p>}
            </div>
          </details>}
        </>}

        {preview && previewMatches && <div className="space-y-4 border-t border-neutral-200 pt-5" aria-label="Deletion preview">
          <h3 className="font-semibold text-neutral-900">Deletion preview</h3>
          <dl className="grid grid-cols-2 gap-3">
            {[
              ["Analysis results to clear", preview.analyses.expired + preview.legacy_cleanup.analysis_candidates],
              ["Survey responses to delete", preview.survey_responses.expired],
            ].map(([label, count]) => <div key={label} className="rounded-md bg-neutral-50 p-3"><dt className="text-xs leading-5 text-neutral-600">{label}</dt><dd className="mt-1 text-xl font-semibold tabular-nums text-neutral-900">{count}</dd></div>)}
          </dl>
          {preview.enabled ? <p className="text-xs text-neutral-500">Newer reports and surveys are kept. Demo reports are excluded. {preview.legacy_cleanup.analysis_candidates > 0 ? "Previously approved undated results are included." : "Undated records are skipped."}</p> : <p className="text-xs text-neutral-500">These settings turn off automatic cleanup.</p>}
          {preview.legacy_cleanup.analysis_candidates > 0 && <p className="text-xs text-amber-900">Includes {preview.legacy_cleanup.analysis_candidates} previously approved results.</p>}
          {preview.related_records.references_requiring_review > 0 && <p role="alert" className="text-xs text-amber-900">Some linked records need review before cleanup can proceed.</p>}
          {preview.samples.length > 0 && <details className="rounded-md border border-neutral-200 p-3 text-sm"><summary className="cursor-pointer font-medium">Analysis samples ({preview.samples.length})</summary><div className="mt-3 max-h-72 overflow-auto"><table className="w-full text-left text-xs"><thead><tr className="border-b"><th className="p-2">Analysis</th><th className="p-2">Generated</th><th className="p-2">Outcome</th><th className="p-2">Reason</th></tr></thead><tbody>{preview.samples.map((sample) => <tr key={sample.analysis_id} className="border-b last:border-0"><td className="whitespace-nowrap p-2 align-top">#{sample.analysis_id}{sample.is_saved ? " · Saved" : ""}{sample.is_auto_refresh ? " · Auto-refresh" : ""}</td><td className="p-2 align-top">{readableDate(sample.generation_at)}</td><td className="p-2 align-top">{sample.will_clear_as_legacy ? "Previously approved" : sample.disposition}</td><td className="p-2 align-top">{sample.reason}</td></tr>)}</tbody></table></div>{preview.samples_truncated && <p className="mt-2 text-xs text-neutral-500">Only the first 100 analyses are shown. Counts include all organization data.</p>}</details>}
        </div>}
      </div>
      <Dialog open={dialogOpen} onOpenChange={(open) => { if (busy !== "save") setDialogOpen(open) }}>
        <DialogContent className="max-h-[85vh] max-w-xl overflow-y-auto">
          <DialogHeader><DialogTitle>Confirm retention policy</DialogTitle><DialogDescription>{enabled ? `Keep each analysis result for ${days} days after successful generation, and each survey response for ${days} days after submission.` : "Disable organization data retention."}</DialogDescription></DialogHeader>
          <div className="space-y-4 text-sm">
            {deletionWarning || <p>Saving configures future cleanup. It does not delete data immediately. Deleted data cannot be restored by increasing the period or disabling retention.</p>}
            {enabled && preview && <p aria-label="Cleanup preview summary" className="rounded-md bg-neutral-50 p-3">This preview identifies {preview.analyses.expired + preview.legacy_cleanup.analysis_candidates} analysis results to clear and {preview.survey_responses.expired} old survey responses to delete.{preview.legacy_cleanup.analysis_candidates > 0 && ` The analysis count includes ${preview.legacy_cleanup.analysis_candidates} unchanged results from an earlier cleanup approval.`} Counts can change before cleanup.</p>}
            {!enabled && pendingLegacy && <p className="rounded-md bg-amber-50 p-3 text-amber-900">Disabling retention will cancel the {policy?.legacy_cleanup.pending_count} remaining entries in the prior cleanup approval.</p>}
            {needsPolicyConfirmation && <div className="flex items-start gap-3"><Checkbox id="confirm-retention-policy" checked={confirmPolicy} disabled={Boolean(busy)} onCheckedChange={(value) => setConfirmPolicy(value === true)} /><label htmlFor="confirm-retention-policy" className="leading-5">I understand this policy can permanently delete existing analysis results and old survey responses.</label></div>}
          </div>
          <DialogFooter><Button variant="outline" disabled={Boolean(busy)} onClick={() => setDialogOpen(false)}>Cancel</Button><Button className="bg-purple-700 text-white hover:bg-purple-800" disabled={!canSave || (needsPolicyConfirmation && !confirmPolicy)} onClick={() => void savePolicy()}>{busy === "save" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Confirm and save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
