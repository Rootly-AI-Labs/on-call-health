const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "")
const RETENTION_URL = `${API_BASE}/auth/organizations/retention`

export interface LegacyCleanupStatus {
  state: "none" | "pending" | "completed" | "cancelled"
  requested_count: number
  pending_count: number
  cleared_count: number
  skipped_count: number
  cancelled_count: number
  approved_at: string | null
  finished_at: string | null
}

export interface RetentionCleanupCounts {
  analysis_results_expired: number
  legacy_analysis_results_cleared: number
  survey_responses_deleted: number
  survey_links_cleared: number
  survey_period_links_cleared: number
  mappings_deleted: number
  notifications_deleted: number
  digest_links_cleared: number
  analyses_unverifiable: number
  analyses_deferred: number
  legacy_analyses_skipped: number
  legacy_analyses_deferred: number
  surveys_unverifiable: number
}

export interface RetentionCleanupStatus {
  state: "never" | "succeeded" | "failed" | "skipped"
  last_attempt_at: string | null
  last_finished_at: string | null
  last_success_at: string | null
  next_retry_at: string | null
  next_cleanup_due_at: string | null
  consecutive_failures: number
  error_code: string | null
  message: string | null
  counts: RetentionCleanupCounts
}

export interface RetentionPolicyResponse {
  organization_id: number
  policy_version: string
  retention_days: number | null
  enabled: boolean
  age_basis: "analysis_generation"
  survey_age_basis: "submission"
  scope: Array<"analyses" | "survey_responses">
  updated_at: string | null
  legacy_cleanup: LegacyCleanupStatus
  cleanup_status: RetentionCleanupStatus
}

export interface RetentionPreviewRequest {
  // Omit this field to preview the saved policy; null explicitly previews disabling it.
  retention_days?: number | null
  clear_unverifiable_analyses?: boolean
}

export interface RetentionPolicyUpdate {
  retention_days: number | null
  expected_policy_version?: string | null
  confirm_deletion?: boolean
  clear_unverifiable_analyses?: boolean
  confirm_legacy_deletion?: boolean
  legacy_preview_token?: string | null
}

export interface AnalysisPreviewCounts {
  total: number
  expired: number
  retained: number
  unverifiable: number
  deferred: number
  empty: number
  regeneration_candidates: number
}

export interface SurveyPreviewCounts {
  total: number
  expired: number
  retained: number
  unverifiable: number
}

export interface RelatedPreviewCounts {
  analysis_mappings: number
  analysis_notifications: number
  survey_links_to_clear: number
  survey_period_links_to_clear: number
  digest_links_to_clear: number
  references_requiring_review: number
}

export interface AnalysisPreviewSample {
  analysis_id: number
  disposition: "expired" | "retained" | "unverifiable" | "deferred" | "empty"
  generation_at: string | null
  reason: string
  is_saved: boolean
  is_auto_refresh: boolean
  will_clear_as_legacy: boolean
}

export interface LegacyCleanupPreview {
  requested: boolean
  analysis_candidates: number
  pending_analyses: number
  unverifiable_surveys: number
  preview_token: string | null
  preview_expires_at: string | null
}

export interface RetentionPreviewResponse {
  organization_id: number
  preview_only: true
  policy_source: "saved" | "proposed"
  retention_days: number | null
  enabled: boolean
  evaluated_at: string
  cutoff_at: string | null
  policy_updated_at: string | null
  analyses: AnalysisPreviewCounts
  survey_responses: SurveyPreviewCounts
  related_records: RelatedPreviewCounts
  samples: AnalysisPreviewSample[]
  samples_truncated: boolean
  warnings: string[]
  legacy_cleanup: LegacyCleanupPreview
}

const PREVIEW_ERROR_MESSAGES: Record<string, string> = {
  retention_policy_changed: "Your organization or retention policy changed. Refresh settings and review a new preview.",
  legacy_preview_expired: "The legacy cleanup preview expired. Review a new preview before confirming.",
  legacy_preview_stale: "The analysis history or retention policy changed. Review a new preview before confirming.",
  legacy_preview_already_used: "This legacy cleanup preview has already been confirmed. Refresh the cleanup status before reviewing another preview.",
  legacy_preview_invalid: "The legacy cleanup preview is invalid. Review a new preview before confirming.",
  legacy_preview_required: "Review a legacy cleanup preview before confirming this one-time clear.",
}

export class RetentionApiError extends Error {
  readonly status: number
  readonly code?: string
  readonly needsNewPreview: boolean

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = "RetentionApiError"
    this.status = status
    this.code = code
    this.needsNewPreview = Boolean(code && Object.prototype.hasOwnProperty.call(PREVIEW_ERROR_MESSAGES, code))
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
}

function parseApiError(status: number, payload: unknown): RetentionApiError {
  let code: string | undefined
  let message = status === 401
    ? "Your session expired. Sign in again to manage data retention."
    : status === 403
      ? "Only active organization admins can change or preview data retention."
      : "Unable to complete the data retention request. Please try again."

  const detail = isRecord(payload) ? payload.detail : undefined
  if (typeof detail === "string" && detail.trim()) {
    message = detail
  } else if (isRecord(detail)) {
    code = typeof detail.code === "string" ? detail.code : undefined
    if (typeof detail.message === "string" && detail.message.trim()) message = detail.message
  } else if (Array.isArray(detail)) {
    // FastAPI validation errors also contain rejected inputs; expose messages only.
    const messages = detail
      .filter(isRecord)
      .map((issue) => issue.msg)
      .filter((value): value is string => typeof value === "string" && Boolean(value.trim()))
    if (messages.length) message = messages.join(". ")
  }

  if (code && Object.prototype.hasOwnProperty.call(PREVIEW_ERROR_MESSAGES, code)) {
    message = PREVIEW_ERROR_MESSAGES[code]
  }
  return new RetentionApiError(message, status, code)
}

async function retentionRequest<T>(
  token: string,
  method: "GET" | "POST" | "PUT",
  body?: RetentionPreviewRequest | RetentionPolicyUpdate,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(method === "POST" ? `${RETENTION_URL}/preview` : RETENTION_URL, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    cache: "no-store",
    signal,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  let payload: unknown
  try {
    payload = await response.json()
  } catch (error) {
    if (signal?.aborted || (error instanceof Error && error.name === "AbortError")) throw error
    if (response.ok) {
      throw new RetentionApiError("The server returned an invalid data retention response. Please try again.", response.status, "invalid_response")
    }
  }
  if (!response.ok) throw parseApiError(response.status, payload)
  return payload as T
}

/** The backend resolves organization ownership from this user's bearer token. */
export function getOrganizationRetention(token: string, signal?: AbortSignal): Promise<RetentionPolicyResponse> {
  return retentionRequest<RetentionPolicyResponse>(token, "GET", undefined, signal)
}

/** Previewing never changes the saved policy or deletes data. */
export function previewOrganizationRetention(
  token: string,
  request: RetentionPreviewRequest = {},
  signal?: AbortSignal,
): Promise<RetentionPreviewResponse> {
  const body: RetentionPreviewRequest = {
    ...(request.retention_days === undefined ? {} : { retention_days: request.retention_days }),
    ...(request.clear_unverifiable_analyses === undefined ? {} : { clear_unverifiable_analyses: request.clear_unverifiable_analyses }),
  }
  return retentionRequest<RetentionPreviewResponse>(token, "POST", body, signal)
}

/** Saving queues confirmed cleanup; it does not execute deletion in this request. */
export function updateOrganizationRetention(
  token: string,
  update: RetentionPolicyUpdate,
  signal?: AbortSignal,
): Promise<RetentionPolicyResponse> {
  const body: RetentionPolicyUpdate = {
    retention_days: update.retention_days,
    ...(update.expected_policy_version === undefined ? {} : { expected_policy_version: update.expected_policy_version }),
    ...(update.confirm_deletion === undefined ? {} : { confirm_deletion: update.confirm_deletion }),
    ...(update.clear_unverifiable_analyses === undefined ? {} : { clear_unverifiable_analyses: update.clear_unverifiable_analyses }),
    ...(update.confirm_legacy_deletion === undefined ? {} : { confirm_legacy_deletion: update.confirm_legacy_deletion }),
    ...(update.legacy_preview_token === undefined ? {} : { legacy_preview_token: update.legacy_preview_token }),
  }
  return retentionRequest<RetentionPolicyResponse>(token, "PUT", body, signal)
}
