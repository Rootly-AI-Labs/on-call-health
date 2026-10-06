"use client"

import { useEffect, useRef, useState } from "react"
import { AlertCircle, CheckCircle, ChevronDown, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
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

function readableCleanupDate(value: string | null) {
  return value ? new Date(value).toLocaleString(undefined, {
    timeZone: "UTC", month: "short", day: "numeric", year: "numeric",
    hour: "numeric", minute: "2-digit",
  }) + " UTC" : "Never"
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
  const sessionToken = useRef<string | null>(null)
  const actionController = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!success) return
    const timer = setTimeout(() => setSuccess(null), 5000)
    return () => clearTimeout(timer)
  }, [success])

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
  const canReview = isAdmin && !busy && !invalidDays && policyChanged
  const canSave = canReview && (!enabled || previewMatches)

  function invalidatePreview() {
    setPreview(null)
    setError(null)
    setSuccess(null)
  }

  function closeDialog() {
    if (busy === "save") return
    actionController.current?.abort()
    actionController.current = null
    setBusy(null)
    setPreview(null)
    setDialogOpen(false)
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
    if (!canReview || !enabled) return
    setBusy("preview")
    setError(null)
    setSuccess(null)
    setPreview(null)
    setDialogOpen(true)
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
      setDialogOpen(false)
      setError(messageFrom(failure))
    } finally {
      if (!controller.signal.aborted) setBusy(null)
    }
  }

  async function savePolicy(confirmedDeletion = false) {
    if (!canSave || (needsPolicyConfirmation && !confirmedDeletion)) return
    setBusy("save")
    setError(null)
    const controller = new AbortController()
    actionController.current = controller
    try {
      const result = await updateOrganizationRetention(await verifiedTokenForAction(controller.signal), {
        retention_days: days,
        expected_policy_version: policy!.policy_version,
        ...(needsPolicyConfirmation ? { confirm_deletion: confirmedDeletion } : {}),
      }, controller.signal)
      if (controller.signal.aborted) return
      if (result.organization_id !== policy?.organization_id) throw new Error("Your organization changed. Refresh settings to verify the saved policy.")
      if (!/^[a-f0-9]{64}$/.test(result.policy_version)) throw new Error("Unable to verify the saved policy version. Refresh settings to verify the saved policy.")
      setPolicy(result)
      setEnabled(result.enabled)
      setDaysInput(String(result.retention_days ?? 90))
      setPreview(null)
      setDialogOpen(false)
      setSuccess(result.enabled
        ? "Retention policy saved. Cleanup uses these settings at the next daily run at 03:00 UTC; no data was deleted by this save."
        : pendingLegacy ? "Retention disabled. The prior cleanup approval has been cancelled." : "Retention disabled.")
    } catch (failure) {
      if (controller.signal.aborted) return
      setError(messageFrom(failure))
      // Discard the previous preview after a failed or ambiguous save.
      setPreview(null)
      setDialogOpen(false)
      if (failure instanceof RetentionApiError && (failure.status === 401 || failure.status === 403)) setAccess("error")
    } finally {
      if (!controller.signal.aborted) setBusy(null)
    }
  }

  const cleanup = policy?.cleanup_status
  const cleanupState = cleanup?.state === "never" ? "Not run yet" : cleanup?.state === "succeeded" ? "Succeeded" : cleanup?.state === "failed" ? "Failed" : "Skipped"
  const unsavedChanges = policyChanged
  const dayUnit = days === 1 ? "day" : "days"
  const deletionWarning = needsPolicyConfirmation && !invalidDays ? (
    <div role="alert" aria-label="Existing data deletion warning" className="space-y-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-relaxed text-amber-950">
      <p className="font-semibold">Deletion is permanent</p>
      <p>{policy?.retention_days === null ? "Enabling" : "Shortening"} retention permanently clears existing results generated and surveys submitted more than {days} {dayUnit} ago during cleanup.</p>
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
          {unsavedChanges && <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">Unsaved</span>}
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
            {pendingLegacy && <p role="status" className="rounded-md bg-amber-50 p-3 text-xs leading-relaxed text-amber-950">An earlier approval to clear {policy.legacy_cleanup.pending_count} results with unknown generation dates is still pending. These unchanged results may be cleared at cleanup. Turn retention off and save to cancel the remaining approval.</p>}
            <div className="flex flex-wrap gap-2">
              <Button className="bg-purple-700 text-white hover:bg-purple-800" disabled={!canReview} onClick={() => {
                if (!enabled) { void savePolicy(); return }
                void requestPreview()
              }}>Save retention policy</Button>
              <Button variant="ghost" disabled={Boolean(busy)} onClick={() => { setSuccess(null); setReload((value) => value + 1) }}>Refresh settings</Button>
            </div>
          </> : <div className="space-y-3">{policy.enabled && <p className="text-sm text-neutral-700">Retention period: <span className="font-medium">{policy.retention_days} days</span></p>}<p className="text-sm text-neutral-500">Only organization admins can change this policy or preview deletion.</p><Button variant="ghost" onClick={() => setReload((value) => value + 1)}>Refresh settings</Button></div>}


          {cleanup && <details open={historyOpen} onToggle={(event) => setHistoryOpen(event.currentTarget.open)} className="rounded-md border border-neutral-200 p-3 text-sm" aria-label="Automatic cleanup status">
            <summary className="cursor-pointer font-medium text-neutral-800">Cleanup history<span className={`ml-2 rounded-full px-2 py-0.5 text-xs font-normal ${cleanup.state === "failed" ? "bg-red-50 text-red-700" : "bg-neutral-100 text-neutral-500"}`}>{cleanupState}</span></summary>
            <div className="mt-3 space-y-3">
              <h3 className="sr-only">Automatic cleanup status: {cleanupState}</h3>
              {cleanup.state === "failed" && <p role="alert" className="rounded-md bg-red-50 p-3 text-xs leading-relaxed text-red-800">{cleanup.message || "Cleanup could not finish. The organization will be retried automatically while retention remains enabled."}</p>}
              <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-xs text-neutral-600 sm:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))]">
                <div className="min-w-0"><dt>Last successful cleanup</dt><dd className="mt-1 font-medium text-neutral-900" title={cleanup.last_success_at ? readableDate(cleanup.last_success_at) : undefined}>{readableCleanupDate(cleanup.last_success_at)}</dd></div>
                {[
                  ["Analyses cleared", cleanup.counts.analysis_results_expired + cleanup.counts.legacy_analysis_results_cleared],
                  ["Surveys deleted", cleanup.counts.survey_responses_deleted],
                  ["Survey links detached", cleanup.counts.survey_links_cleared],
                ].map(([label, count]) => <div key={label} className="min-w-0"><dt>{label}</dt><dd className="mt-1 font-medium tabular-nums text-neutral-900">{count}</dd></div>)}
              </dl>
            </div>
          </details>}
        </>}

      </div>
      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) closeDialog() }}>
        <DialogContent className="max-h-[85vh] max-w-lg overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Confirm retention policy</DialogTitle>
            <DialogDescription>{enabled ? <>
              <span className="block">Analysis results: {days} {dayUnit} after generation.</span>
              <span className="block">Surveys: {days} {dayUnit} after submission.</span>
            </> : "Disable organization data retention."}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 text-sm">
            {busy === "preview" && <p role="status" className="flex items-center gap-2 text-neutral-500"><Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />Loading deletion preview…</p>}
            {preview && previewMatches && <div aria-label="Deletion preview" className="space-y-2">
              <dl className="grid grid-cols-2 gap-3">
                {[
                  ["Analysis results to clear", preview.analyses.expired + preview.legacy_cleanup.analysis_candidates],
                  ["Survey responses to delete", preview.survey_responses.expired],
                ].map(([label, count]) => <div key={label} className="rounded-md bg-neutral-50 p-3"><dt className="text-xs leading-5 text-neutral-600">{label}</dt><dd className="mt-1 text-xl font-semibold tabular-nums text-neutral-900">{count}</dd></div>)}
              </dl>
              {preview.legacy_cleanup.analysis_candidates > 0 && <p className="text-xs text-amber-900">Includes {preview.legacy_cleanup.analysis_candidates} previously approved results.</p>}
              {preview.related_records.references_requiring_review > 0 && <p role="alert" className="text-xs text-amber-900">Some linked records need review before cleanup can proceed.</p>}
            </div>}
            {deletionWarning || <p>Saving schedules cleanup; it does not delete data immediately. Deletion is permanent.</p>}
            {!enabled && pendingLegacy && <p className="rounded-md bg-amber-50 p-3 text-amber-900">Disabling retention will cancel the {policy?.legacy_cleanup.pending_count} remaining entries in the prior cleanup approval.</p>}
          </div>
          <DialogFooter><Button variant="outline" disabled={busy === "save"} onClick={closeDialog}>Cancel</Button><Button className="bg-purple-700 text-white hover:bg-purple-800" disabled={!canSave} onClick={() => void savePolicy(true)}>{busy === "save" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Confirm and save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
