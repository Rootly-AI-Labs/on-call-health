"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Bell, AlertTriangle, Clock, Calendar, TrendingUp, RefreshCw } from "lucide-react"

interface AlertsCountCardProps {
  currentAnalysis: any
}

function formatDate(value?: string): string {
  if (!value) return "unknown"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "unknown"
  return date.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })
}

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

export function AlertsCountCard({ currentAnalysis }: AlertsCountCardProps): React.ReactElement | null {
  const alerts = currentAnalysis?.analysis_data?.metadata?.alerts
  if (!alerts) return null

  const total = alerts.filtered_total ?? alerts.total
  const hasError = Boolean(alerts.error)
  const dateRange = `${formatDate(alerts.start)} - ${formatDate(alerts.end)}`

  const noiseCounts = alerts.noise_counts || {}
  const totalForNoise = typeof total === "number" && total > 0 ? total : null
  const notNoiseCount = typeof noiseCounts.not_noise === "number" ? noiseCounts.not_noise : 0
  const notNoisePct = totalForNoise !== null ? Math.floor((notNoiseCount / totalForNoise) * 100) : null

  const afterHoursCount = typeof alerts.after_hours_count === "number" ? alerts.after_hours_count : null
  const afterHoursPct =
    totalForNoise !== null && afterHoursCount !== null
      ? Math.ceil((afterHoursCount / totalForNoise) * 100)
      : null

  const nightTimeCount = typeof alerts.night_time_count === "number" ? alerts.night_time_count : null
  const nightTimePct =
    totalForNoise !== null && nightTimeCount !== null
      ? Math.ceil((nightTimeCount / totalForNoise) * 100)
      : null

  const alertsWithIncidentsCount =
    typeof alerts.alerts_with_incidents_count === "number" ? alerts.alerts_with_incidents_count : null
  const alertsWithIncidentsPct =
    totalForNoise !== null && alertsWithIncidentsCount !== null
      ? Math.round((alertsWithIncidentsCount / totalForNoise) * 100)
      : null

  const avgMttaSeconds = typeof alerts.avg_mtta_seconds === "number" ? alerts.avg_mtta_seconds : null
  const mttaCount = typeof alerts.mtta_count === "number" ? alerts.mtta_count : 0
  const avgMttrSeconds = typeof alerts.avg_mttr_seconds === "number" ? alerts.avg_mttr_seconds : null
  const mttrCount = typeof alerts.mttr_count === "number" ? alerts.mttr_count : 0
  const escalatedCount = typeof alerts.escalated_count === "number" ? alerts.escalated_count : null
  const escalatedPct = totalForNoise !== null && escalatedCount !== null
    ? Math.floor((escalatedCount / totalForNoise) * 100) : null
  const retriggerCount = typeof alerts.retrigger_count === "number" ? alerts.retrigger_count : null
  const retriggerPct = totalForNoise !== null && retriggerCount !== null
    ? Math.floor((retriggerCount / totalForNoise) * 100) : null

  const urgencyCounts = alerts.urgency_counts || {}
  const urgencyEntries = Object.entries(urgencyCounts)
    .filter(([, value]) => typeof value === "number" && (value as number) >= 0)
    .sort((a, b) => {
      const order = ["high", "medium", "low"]
      return order.indexOf(a[0]) - order.indexOf(b[0])
    })
  const urgencyTotal = urgencyEntries.reduce((sum, [, v]) => sum + (v as number), 0)

  const sourceCounts = alerts.derived_source_counts || alerts.source_counts || {}
  const sourceEntries = Object.entries(sourceCounts)
    .filter(([, value]) => typeof value === "number" && (value as number) > 0)
    .sort((a, b) => (b[1] as number) - (a[1] as number))
  const sourceMax = sourceEntries.length > 0 ? (sourceEntries[0][1] as number) : 1

  return (
    <Card className="bg-white flex flex-col">
      <CardHeader className="pb-2 shrink-0">
        <div className="space-y-1">
          <CardTitle className="text-neutral-900">Team Alerts</CardTitle>
          <CardDescription>Rootly alert count for this analysis window</CardDescription>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col min-h-0 overflow-y-auto">
        {hasError ? (
          <div className="flex items-start gap-2 text-sm text-red-700">
            <AlertTriangle className="w-4 h-4 mt-0.5" />
            <span>Alerts data unavailable ({alerts.error})</span>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Count + date */}
            <div className="flex flex-col gap-1">
              <span className="text-4xl font-bold text-neutral-900">
                {typeof total === "number" ? total : "N/A"}
              </span>
              <span className="text-sm text-neutral-500">{dateRange}</span>
            </div>

            {alerts.truncated && (
              <div className="text-xs text-yellow-700">Alert count may be partial (page limit reached)</div>
            )}

            {/* Urgency Distribution + Signal Quality - Side by side */}
            {(urgencyEntries.length > 0 || notNoisePct !== null) && (
              <div className="grid grid-cols-2 gap-4">
                {/* Urgency Distribution */}
                {urgencyEntries.length > 0 && (
                  <div>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-neutral-700 font-medium">Urgency</span>
                      <div className="flex items-center gap-2 text-xs text-neutral-600">
                        {urgencyEntries.map(([key, value]) => (
                          <div key={key} className="flex items-center gap-1">
                            <span className={`w-2 h-2 rounded-full inline-block ${URGENCY_DOT_COLORS[key] ?? "bg-gray-400"}`} />
                            <span className="capitalize font-medium">{key}</span>
                            <span className="font-semibold text-neutral-800">{value as number}</span>
                          </div>
                        ))}
                      </div>
                    </div>
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
              </div>
            )}

            {/* Avg MTTA + MTTR */}
            {(avgMttaSeconds !== null || avgMttrSeconds !== null) && (
              <div className="grid grid-cols-2 gap-3">
                {avgMttaSeconds !== null && (
                  <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                    <div className="text-xs text-neutral-500 mb-1">
                      Avg MTTA
                      {mttaCount > 0 && <span className="ml-1">({mttaCount})</span>}
                    </div>
                    <div className="text-lg font-bold text-neutral-900">{formatDuration(avgMttaSeconds)}</div>
                  </div>
                )}
                {avgMttrSeconds !== null && (
                  <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                    <div className="text-xs text-neutral-500 mb-1">
                      Avg MTTR
                      {mttrCount > 0 && <span className="ml-1">({mttrCount})</span>}
                    </div>
                    <div className="text-lg font-bold text-neutral-900">{formatDuration(avgMttrSeconds)}</div>
                  </div>
                )}
              </div>
            )}

            {/* Alert Breakdown */}
            {(alertsWithIncidentsCount !== null || afterHoursCount !== null || nightTimeCount !== null || escalatedCount !== null || retriggerCount !== null) && (
              <div>
                <div className="text-sm font-semibold text-neutral-800 mb-3">Alert Breakdown</div>
                <div className="grid grid-cols-5 gap-2">
                  {alertsWithIncidentsCount !== null && (
                    <div className="flex flex-col items-center text-center p-3 rounded-lg border border-neutral-200 bg-neutral-50">
                      <AlertTriangle className="w-5 h-5 text-neutral-600 mb-2" />
                      <span className="text-xl font-bold text-neutral-900">{alertsWithIncidentsCount}</span>
                      <span className="text-xs text-neutral-500 mt-1">With incidents</span>
                    </div>
                  )}
                  {afterHoursCount !== null && (
                    <div className="flex flex-col items-center text-center p-3 rounded-lg border border-neutral-200 bg-neutral-50">
                      <Clock className="w-5 h-5 text-neutral-600 mb-2" />
                      <span className="text-xl font-bold text-neutral-900">{afterHoursCount}</span>
                      <span className="text-xs text-neutral-500 mt-1">After-hours</span>
                    </div>
                  )}
                  {nightTimeCount !== null && (
                    <div className="flex flex-col items-center text-center p-3 rounded-lg border border-neutral-200 bg-neutral-50">
                      <Clock className="w-5 h-5 text-neutral-600 mb-2" />
                      <span className="text-xl font-bold text-neutral-900">{nightTimeCount}</span>
                      <span className="text-xs text-neutral-500 mt-1">Night-time</span>
                    </div>
                  )}
                  {escalatedCount !== null && escalatedCount > 0 && (
                    <div className="flex flex-col items-center text-center p-3 rounded-lg border border-neutral-200 bg-neutral-50">
                      <TrendingUp className="w-5 h-5 text-neutral-600 mb-2" />
                      <span className="text-xl font-bold text-neutral-900">{escalatedCount}</span>
                      <span className="text-xs text-neutral-500 mt-1">Escalated</span>
                    </div>
                  )}
                  {retriggerCount !== null && retriggerCount > 0 && (
                    <div className="flex flex-col items-center text-center p-3 rounded-lg border border-neutral-200 bg-neutral-50">
                      <RefreshCw className="w-5 h-5 text-neutral-600 mb-2" />
                      <span className="text-xl font-bold text-neutral-900">{retriggerCount}</span>
                      <span className="text-xs text-neutral-500 mt-1">Retriggered</span>
                    </div>
                  )}
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
        )}
      </CardContent>
    </Card>
  )
}
