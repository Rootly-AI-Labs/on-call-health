"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Bell, AlertTriangle, Clock, Calendar, TrendingUp, RefreshCw, CheckCheck } from "lucide-react"

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) {
    const m = Math.floor(seconds / 60)
    const s = Math.round(seconds % 60)
    return s > 0 ? `${m}m ${s}s` : `${m}m`
  }
  const h = Math.floor(seconds / 3600)
  const m = Math.round((seconds % 3600) / 60)
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}

interface UserAlertsCardProps {
  memberData: any
  alertsMeta?: any
}

function formatDate(value?: string): string {
  if (!value) return "unknown"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "unknown"
  return date.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })
}

const SOURCE_COLORS = [
  "bg-blue-500",
  "bg-green-500",
  "bg-orange-400",
  "bg-purple-500",
  "bg-pink-500",
  "bg-yellow-400",
  "bg-cyan-500",
  "bg-red-400",
]

const URGENCY_COLORS: Record<string, string> = {
  high: "bg-red-500",
  medium: "bg-orange-400",
  low: "bg-gray-300",
}

const URGENCY_DOT_COLORS: Record<string, string> = {
  high: "bg-red-500",
  medium: "bg-orange-400",
  low: "bg-gray-400",
}

export function UserAlertsCard({ memberData, alertsMeta }: UserAlertsCardProps): React.ReactElement {
  const count = memberData?.alerts_count
  const dateRange = alertsMeta ? `${formatDate(alertsMeta.start)} - ${formatDate(alertsMeta.end)}` : "unknown"

  const notifiedCount = typeof memberData?.alerts_notified_count === "number" ? memberData.alerts_notified_count : null
  const respondedCount = typeof memberData?.alerts_responded_count === "number" ? memberData.alerts_responded_count : null

  const noiseCounts = memberData?.alerts_noise_counts || {}
  const totalForNoise = typeof count === "number" && count > 0 ? count : null
  const notNoiseCount = typeof noiseCounts.not_noise === "number" ? noiseCounts.not_noise : 0
  const notNoisePct = totalForNoise !== null ? Math.floor((notNoiseCount / totalForNoise) * 100) : null

  const alertsWithIncidentsCount =
    typeof memberData?.alerts_with_incidents_count === "number" ? memberData.alerts_with_incidents_count : null
  const alertsWithIncidentsPct =
    totalForNoise !== null && alertsWithIncidentsCount !== null
      ? Math.round((alertsWithIncidentsCount / totalForNoise) * 100)
      : null

  const afterHoursCount =
    typeof memberData?.alerts_after_hours_count === "number" ? memberData.alerts_after_hours_count : null
  const afterHoursPct =
    totalForNoise !== null && afterHoursCount !== null
      ? Math.ceil((afterHoursCount / totalForNoise) * 100)
      : null

  const nightTimeCount =
    typeof memberData?.alerts_night_time_count === "number" ? memberData.alerts_night_time_count : null
  const nightTimePct =
    totalForNoise !== null && nightTimeCount !== null
      ? Math.ceil((nightTimeCount / totalForNoise) * 100)
      : null

  const urgencyCounts = memberData?.alerts_urgency_counts || {}
  const urgencyEntries = Object.entries(urgencyCounts)
    .filter(([, value]) => typeof value === "number" && (value as number) >= 0)
    .sort((a, b) => {
      const order = ["high", "medium", "low"]
      return order.indexOf(a[0]) - order.indexOf(b[0])
    })
  const urgencyTotal = urgencyEntries.reduce((sum, [, v]) => sum + (v as number), 0)

  const sourceCounts = memberData?.alerts_derived_source_counts || memberData?.alerts_source_counts || {}

  const ackedCount = typeof memberData?.alerts_acked_count === "number" ? memberData.alerts_acked_count : null
  const resolvedCount = typeof memberData?.alerts_resolved_count === "number" ? memberData.alerts_resolved_count : null
  const escalatedCount = typeof memberData?.alerts_escalated_count === "number" ? memberData.alerts_escalated_count : null
  const escalatedPct = typeof count === "number" && count > 0 && escalatedCount !== null
    ? Math.floor((escalatedCount / count) * 100) : null
  const retriggeredCount = typeof memberData?.alerts_retriggered_count === "number" ? memberData.alerts_retriggered_count : null
  const retriggeredPct = typeof count === "number" && count > 0 && retriggeredCount !== null
    ? Math.floor((retriggeredCount / count) * 100) : null
  const avgMttaSeconds = typeof memberData?.alerts_avg_mtta_seconds === "number" ? memberData.alerts_avg_mtta_seconds : null
  const avgMttrSeconds = typeof memberData?.alerts_avg_mttr_seconds === "number" ? memberData.alerts_avg_mttr_seconds : null
  const sourceEntries = Object.entries(sourceCounts)
    .filter(([, value]) => typeof value === "number" && (value as number) > 0)
    .sort((a, b) => (b[1] as number) - (a[1] as number))
  const sourceMax = sourceEntries.length > 0 ? (sourceEntries[0][1] as number) : 1

  return (
    <Card className="bg-white">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-neutral-900">User Alerts</CardTitle>
            <CardDescription>Alerts associated with this user</CardDescription>
          </div>
          <div className="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center">
            <Bell className="w-4 h-4 text-red-500" />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Count + date */}
          <div className="flex items-center gap-3">
            <span className="text-4xl font-bold text-neutral-900">
              {typeof count === "number" ? count : "N/A"}
            </span>
            <div className="flex items-center gap-1 text-sm text-neutral-500">
              <Calendar className="w-3.5 h-3.5" />
              <span>{dateRange}</span>
            </div>
          </div>

          {/* Notified / Responded stat boxes */}
          {(notifiedCount !== null || respondedCount !== null) && (
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                <div className="text-xs text-neutral-500 mb-1">Notified</div>
                <div className="text-2xl font-bold text-neutral-900">
                  {notifiedCount !== null ? notifiedCount : "N/A"}
                </div>
              </div>
              <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                <div className="text-xs text-neutral-500 mb-1">Responded</div>
                <div className="text-2xl font-bold text-neutral-900">
                  {respondedCount !== null ? respondedCount : "N/A"}
                </div>
              </div>
            </div>
          )}

          {/* Signal Quality */}
          {notNoisePct !== null && (
            <div>
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-neutral-700 font-medium">Signal Quality</span>
                <span className="text-green-600 font-medium">{notNoisePct}% actionable</span>
              </div>
              <div className="h-2 w-full bg-neutral-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full"
                  style={{ width: `${notNoisePct}%` }}
                />
              </div>
            </div>
          )}

          {/* Alerts with incidents */}
          {alertsWithIncidentsCount !== null && (
            <div className="flex items-center justify-between text-sm text-neutral-700">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-neutral-400" />
                <span>Alerts with incidents</span>
              </div>
              <span className="font-medium">
                {alertsWithIncidentsCount}
                {alertsWithIncidentsPct !== null && (
                  <span className="text-neutral-400 font-normal ml-1">({alertsWithIncidentsPct}%)</span>
                )}
              </span>
            </div>
          )}

          {/* After-hours */}
          {afterHoursCount !== null && (
            <div className="flex items-center justify-between text-sm text-neutral-700">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-neutral-400" />
                <span>After-hours alerts</span>
              </div>
              <span className="font-medium">
                {afterHoursCount}
                {afterHoursPct !== null && (
                  <span className="text-neutral-400 font-normal ml-1">({afterHoursPct}%)</span>
                )}
              </span>
            </div>
          )}

          {/* Night-time */}
          {nightTimeCount !== null && (
            <div className="flex items-center justify-between text-sm text-neutral-700">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-neutral-400" />
                <span>Night-time alerts <span className="text-neutral-400 font-normal">(10pm–6am)</span></span>
              </div>
              <span className="font-medium">
                {nightTimeCount}
                {nightTimePct !== null && (
                  <span className="text-neutral-400 font-normal ml-1">({nightTimePct}%)</span>
                )}
              </span>
            </div>
          )}

          {/* Avg MTTA + MTTR */}
          {(avgMttaSeconds !== null || avgMttrSeconds !== null) && (
            <div className="grid grid-cols-2 gap-3">
              {avgMttaSeconds !== null && (
                <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                  <div className="text-xs text-neutral-500 mb-1">Avg MTTA</div>
                  <div className="text-lg font-bold text-neutral-900">{formatDuration(avgMttaSeconds)}</div>
                </div>
              )}
              {avgMttrSeconds !== null && (
                <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                  <div className="text-xs text-neutral-500 mb-1">Avg MTTR</div>
                  <div className="text-lg font-bold text-neutral-900">{formatDuration(avgMttrSeconds)}</div>
                </div>
              )}
            </div>
          )}

          {/* Acked vs Resolved */}
          {(ackedCount !== null || resolvedCount !== null) && (
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                <div className="text-xs text-neutral-500 mb-1">Acknowledged</div>
                <div className="text-2xl font-bold text-neutral-900">
                  {ackedCount !== null ? ackedCount : "N/A"}
                </div>
              </div>
              <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                <div className="flex items-center gap-1 text-xs text-neutral-500 mb-1">
                  <CheckCheck className="w-3 h-3" />
                  <span>Resolved</span>
                </div>
                <div className="text-2xl font-bold text-neutral-900">
                  {resolvedCount !== null ? resolvedCount : "N/A"}
                </div>
              </div>
            </div>
          )}

          {/* Escalated */}
          {escalatedCount !== null && escalatedCount > 0 && (
            <div className="flex items-center justify-between text-sm text-neutral-700">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-orange-400" />
                <span>Escalated alerts</span>
              </div>
              <span className="font-medium">
                {escalatedCount}
                {escalatedPct !== null && (
                  <span className="text-neutral-400 font-normal ml-1">({escalatedPct}%)</span>
                )}
              </span>
            </div>
          )}

          {/* Retriggered */}
          {retriggeredCount !== null && retriggeredCount > 0 && (
            <div className="flex items-center justify-between text-sm text-neutral-700">
              <div className="flex items-center gap-2">
                <RefreshCw className="w-4 h-4 text-red-400" />
                <span>Retriggered alerts</span>
              </div>
              <span className="font-medium">
                {retriggeredCount}
                {retriggeredPct !== null && (
                  <span className="text-neutral-400 font-normal ml-1">({retriggeredPct}%)</span>
                )}
              </span>
            </div>
          )}

          {/* Urgency */}
          {urgencyEntries.length > 0 && (
            <div>
              <div className="text-sm font-semibold text-neutral-800 mb-2">Urgency</div>
              <div className="flex h-2.5 w-full rounded-full overflow-hidden bg-neutral-100 mb-2">
                {urgencyEntries.map(([key, value]) => {
                  const pct = urgencyTotal > 0 ? ((value as number) / urgencyTotal) * 100 : 0
                  return (
                    <div
                      key={key}
                      className={`h-full ${URGENCY_COLORS[key] ?? "bg-gray-400"}`}
                      style={{ width: `${pct}%` }}
                    />
                  )
                })}
              </div>
              <div className="flex items-center gap-4 text-xs text-neutral-600">
                {urgencyEntries.map(([key, value]) => (
                  <div key={key} className="flex items-center gap-1">
                    <span className={`w-2 h-2 rounded-full inline-block ${URGENCY_DOT_COLORS[key] ?? "bg-gray-400"}`} />
                    <span className="capitalize">{key}</span>
                    <span className="font-semibold text-neutral-800 ml-0.5">{value as number}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Alert Sources */}
          {sourceEntries.length > 0 && (
            <div>
              <div className="text-sm font-semibold text-neutral-800 mb-2">Alert Sources</div>
              <div className="overflow-y-auto max-h-48 space-y-2 pr-1">
                {sourceEntries.map(([key, value], i) => (
                  <div key={key}>
                    <div className="flex items-center justify-between text-xs text-neutral-600 mb-1">
                      <span className="capitalize">{key.replace(/_/g, " ")}</span>
                      <span className="font-semibold text-neutral-800">{value as number}</span>
                    </div>
                    <div className="h-1.5 w-full bg-neutral-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${SOURCE_COLORS[i % SOURCE_COLORS.length]}`}
                        style={{ width: `${Math.round(((value as number) / sourceMax) * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
