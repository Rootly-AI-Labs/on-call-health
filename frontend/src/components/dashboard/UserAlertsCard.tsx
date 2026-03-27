"use client"

import { useState, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Minus, CheckCheck, ChevronRight, X, Bell, Reply } from "lucide-react"
import { InfoTooltip } from "@/components/ui/info-tooltip"

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

function formatDate(value?: string): string {
  if (!value) return "unknown"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "unknown"
  return date.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })
}

const SOURCE_COLORS = [
  "bg-blue-500", "bg-green-500", "bg-orange-400", "bg-purple-500",
  "bg-pink-500", "bg-yellow-400", "bg-cyan-500", "bg-red-400",
]

const URGENCY_COLORS: Record<string, string> = {
  high: "bg-red-500", medium: "bg-orange-400", low: "bg-gray-300",
}
const URGENCY_DOT_COLORS: Record<string, string> = {
  high: "bg-red-500", medium: "bg-orange-400", low: "bg-gray-400",
}

type AlertTrendKey = "incidents" | "after_hours" | "night_time" | "escalated" | "retrigger"

function calcAlertTrend(daily: Record<string, any>, key: AlertTrendKey): number | null {
  const days = Object.keys(daily).sort()
  if (days.length < 4) return null
  const values = days.map((d) => {
    const day = daily[d]
    return day.total > 0 ? (day[key] ?? 0) / day.total : 0
  })
  const n = values.length
  const xMean = (n - 1) / 2
  const yMean = values.reduce((s, v) => s + v, 0) / n
  let num = 0, den = 0
  for (let i = 0; i < n; i++) {
    num += (i - xMean) * (values[i] - yMean)
    den += (i - xMean) ** 2
  }
  const slope = den !== 0 ? num / den : 0
  const intercept = yMean - slope * xMean
  const predicted0 = intercept
  const predictedN = intercept + slope * (n - 1)
  if (predicted0 <= 0 && predictedN <= 0) return 0
  if (predicted0 <= 0) return predictedN > 0 ? 100 : 0
  return Math.round(((predictedN - predicted0) / predicted0) * 100)
}

function TrendTag({ change }: { change: number | null }) {
  if (change === null) return null
  if (change <= -30) return (
    <span className="inline-flex items-center gap-0.5 text-[9px] font-semibold px-1.5 py-0.5 rounded-full border bg-green-100 text-green-700 border-green-200">
      <TrendingUp className="w-2.5 h-2.5" /><TrendingUp className="w-2.5 h-2.5" />Improving Fast
    </span>
  )
  if (change <= -15) return (
    <span className="inline-flex items-center gap-0.5 text-[9px] font-semibold px-1.5 py-0.5 rounded-full border bg-green-50 text-green-600 border-green-100">
      <TrendingUp className="w-2.5 h-2.5" />Improving
    </span>
  )
  if (change >= 30) return (
    <span className="inline-flex items-center gap-0.5 text-[9px] font-semibold px-1.5 py-0.5 rounded-full border bg-red-100 text-red-700 border-red-200">
      <TrendingDown className="w-2.5 h-2.5" /><TrendingDown className="w-2.5 h-2.5" />Critical
    </span>
  )
  if (change >= 15) return (
    <span className="inline-flex items-center gap-0.5 text-[9px] font-semibold px-1.5 py-0.5 rounded-full border bg-yellow-50 text-yellow-700 border-yellow-100">
      <TrendingDown className="w-2.5 h-2.5" />Worsening
    </span>
  )
  return (
    <span className="inline-flex items-center gap-0.5 text-[9px] font-semibold px-1.5 py-0.5 rounded-full border bg-purple-50 text-purple-600 border-purple-200">
      <Minus className="w-2.5 h-2.5" />Stable
    </span>
  )
}

type UserPopupTab = "breakdown" | "sources" | "activity"
type LeaderboardKey = "total" | "noise" | "night_time" | "after_hours" | "no_incident" | "escalated" | "retriggered"

const LEADERBOARD_FILTERS: { key: LeaderboardKey; label: string; description: string; color: string }[] = [
  { key: "total",       label: "Most Fired",  description: "Alerts that fired the most times in this period.",                              color: "bg-neutral-400" },
  { key: "noise",       label: "Noisiest",    description: "Alerts classified as noise (firing without being actionable).",                 color: "bg-red-400" },
  { key: "night_time",  label: "Night-Time",  description: "Alerts firing during deep night hours (10pm–6am).",                            color: "bg-indigo-400" },
  { key: "after_hours", label: "After-Hours", description: "Alerts firing outside business hours (6pm–9am), evenings and weekends.",        color: "bg-violet-400" },
  { key: "no_incident", label: "No Incident", description: "Alerts that fired but never escalated into a full incident.",                   color: "bg-orange-400" },
  { key: "escalated",   label: "Escalated",   description: "Alerts that were escalated to another responder or level.",                    color: "bg-yellow-500" },
  { key: "retriggered", label: "Retriggered", description: "Alerts that fired again after being acknowledged or resolved.",                 color: "bg-pink-400" },
]

interface UserAlertsCardProps {
  memberData: any
  alertsMeta?: any
  platform?: string
}

export function UserAlertsCard({ memberData, alertsMeta, platform }: UserAlertsCardProps): React.ReactElement {
  const [showPopup, setShowPopup] = useState(false)
  const [tab, setTab] = useState<UserPopupTab>("breakdown")

  const trends = useMemo(() => {
    const d: Record<string, any> = memberData?.alerts_daily_breakdown || {}
    return {
      incidents:   calcAlertTrend(d, "incidents"),
      after_hours: calcAlertTrend(d, "after_hours"),
      night_time:  calcAlertTrend(d, "night_time"),
      escalated:   calcAlertTrend(d, "escalated"),
      retrigger:   calcAlertTrend(d, "retrigger"),
    }
  }, [memberData])

  if (platform === 'pagerduty') {
    return (
      <Card className="bg-white">
        <CardHeader className="pb-2">
          <CardTitle className="text-neutral-900">User Alerts</CardTitle>
          <CardDescription>Volume, signal quality and breakdown trends</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center py-10 text-center gap-2">
          <p className="text-sm font-medium text-neutral-600">Alert data is not available for PagerDuty</p>
          <p className="text-xs text-neutral-400">Connect Rootly to access alert insights</p>
        </CardContent>
      </Card>
    )
  }

  const count = memberData?.alerts_count
  const dateRange = alertsMeta ? `${formatDate(alertsMeta.start)} - ${formatDate(alertsMeta.end)}` : "unknown"

  const noiseCounts = memberData?.alerts_noise_counts || {}
  const totalForNoise = typeof count === "number" && count > 0 ? count : null
  const notNoiseCount = typeof noiseCounts.not_noise === "number" ? noiseCounts.not_noise : 0
  const notNoisePct = totalForNoise !== null ? Math.floor((notNoiseCount / totalForNoise) * 100) : null

  const urgencyCounts = memberData?.alerts_urgency_counts || {}
  const urgencyEntries = Object.entries(urgencyCounts)
    .filter(([, value]) => typeof value === "number" && (value as number) >= 0)
    .sort((a, b) => ["high", "medium", "low"].indexOf(a[0]) - ["high", "medium", "low"].indexOf(b[0]))
  const urgencyTotal = urgencyEntries.reduce((sum, [, v]) => sum + (v as number), 0)

  const alertsWithIncidentsCount = typeof memberData?.alerts_with_incidents_count === "number" ? memberData.alerts_with_incidents_count : null
  const alertsWithIncidentsPct = totalForNoise !== null && alertsWithIncidentsCount !== null ? Math.round((alertsWithIncidentsCount / totalForNoise) * 100) : null
  const afterHoursCount = typeof memberData?.alerts_after_hours_count === "number" ? memberData.alerts_after_hours_count : null
  const afterHoursPct = totalForNoise !== null && afterHoursCount !== null ? Math.ceil((afterHoursCount / totalForNoise) * 100) : null
  const nightTimeCount = typeof memberData?.alerts_night_time_count === "number" ? memberData.alerts_night_time_count : null
  const nightTimePct = totalForNoise !== null && nightTimeCount !== null ? Math.ceil((nightTimeCount / totalForNoise) * 100) : null
  const escalatedCount = typeof memberData?.alerts_escalated_count === "number" ? memberData.alerts_escalated_count : null
  const escalatedPct = totalForNoise !== null && escalatedCount !== null ? Math.floor((escalatedCount / totalForNoise) * 100) : null
  const retriggeredCount = typeof memberData?.alerts_retriggered_count === "number" ? memberData.alerts_retriggered_count : null
  const retriggeredPct = totalForNoise !== null && retriggeredCount !== null ? Math.floor((retriggeredCount / totalForNoise) * 100) : null

  const notifiedCount = typeof memberData?.alerts_notified_count === "number" ? memberData.alerts_notified_count : null
  const respondedCount = typeof memberData?.alerts_responded_count === "number" ? memberData.alerts_responded_count : null
  const ackedCount = typeof memberData?.alerts_acked_count === "number" ? memberData.alerts_acked_count : null
  const resolvedCount = typeof memberData?.alerts_resolved_count === "number" ? memberData.alerts_resolved_count : null
  const avgMttaSeconds = typeof memberData?.alerts_avg_mtta_seconds === "number" ? memberData.alerts_avg_mtta_seconds : null
  const avgMttrSeconds = typeof memberData?.alerts_avg_mttr_seconds === "number" ? memberData.alerts_avg_mttr_seconds : null

  const sourceCounts = memberData?.alerts_derived_source_counts || memberData?.alerts_source_counts || {}
  const sourceEntries = Object.entries(sourceCounts)
    .filter(([, value]) => typeof value === "number" && (value as number) > 0)
    .sort((a, b) => (b[1] as number) - (a[1] as number))
  const sourceMax = sourceEntries.length > 0 ? (sourceEntries[0][1] as number) : 1

  const breakdownItems = [
    alertsWithIncidentsCount !== null && { count: alertsWithIncidentsCount, pct: alertsWithIncidentsPct, label: "With incidents", trend: trends.incidents },
    afterHoursCount !== null          && { count: afterHoursCount,          pct: afterHoursPct,          label: "After-hours",   trend: trends.after_hours },
    nightTimeCount !== null           && { count: nightTimeCount,           pct: nightTimePct,           label: "Night-time",    trend: trends.night_time },
    escalatedCount !== null && escalatedCount > 0 && { count: escalatedCount,   pct: escalatedPct,   label: "Escalated",    trend: trends.escalated },
    retriggeredCount !== null && retriggeredCount > 0 && { count: retriggeredCount, pct: retriggeredPct, label: "Retriggered", trend: trends.retrigger },
  ].filter(Boolean) as { count: number; pct: number | null; label: string; trend: number | null }[]

  const activityItems = [
    notifiedCount !== null  && { count: notifiedCount,  label: "Notified",      icon: <Bell className="w-4 h-4" /> },
    respondedCount !== null && { count: respondedCount, label: "Responded",     icon: <Reply className="w-4 h-4" /> },
    ackedCount !== null     && { count: ackedCount,     label: "Acknowledged",  icon: <CheckCheck className="w-4 h-4" /> },
    resolvedCount !== null  && { count: resolvedCount,  label: "Resolved",      icon: <CheckCheck className="w-4 h-4" /> },
  ].filter(Boolean) as { count: number; label: string; icon: React.ReactElement }[]

  return (
    <>
      <Card className="bg-white">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <CardTitle className="text-neutral-900">User Alerts</CardTitle>
              <CardDescription>Volume, signal quality and breakdown trends</CardDescription>
            </div>
            <button
              onClick={() => setShowPopup(true)}
              className="flex items-center gap-0.5 text-xs text-neutral-500 hover:text-neutral-800 transition-colors shrink-0"
            >
              View Details <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Total count */}
          <div className="flex flex-col gap-0.5 mb-1">
            <span className="text-4xl font-bold text-neutral-900 leading-tight">
              {typeof count === "number" ? count : "N/A"}
            </span>
            <span className="text-xs text-neutral-400">{dateRange}</span>
          </div>

          {/* Urgency + Signal Quality */}
          {(urgencyEntries.length > 0 || notNoisePct !== null) && (
            <div className="grid grid-cols-2 gap-4 my-6">
              {urgencyEntries.length > 0 && (
                <div>
                  <div className="flex items-center justify-between text-[13px] mb-1">
                    <div className="flex items-center gap-1">
                      <span className="text-neutral-700 font-medium">Urgency</span>
                      <InfoTooltip content="Breakdown of alert severity: High requires immediate action, Medium needs prompt response, Low is informational." side="bottom" />
                    </div>
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
                      return <div key={key} className={`h-full ${URGENCY_COLORS[key] ?? "bg-gray-400"}`} style={{ width: `${pct}%` }} />
                    })}
                  </div>
                </div>
              )}
              {notNoisePct !== null && (
                <div>
                  <div className="flex items-center justify-between text-[13px] mb-1">
                    <div className="flex items-center gap-1">
                      <span className="text-neutral-700 font-medium">Signal Quality</span>
                      <InfoTooltip content="Percentage of alerts that are actionable (not noise)." side="bottom" />
                    </div>
                    <span className="text-green-600 font-medium">{notNoisePct}% actionable</span>
                  </div>
                  <div className="h-2 w-full bg-neutral-100 rounded-full overflow-hidden">
                    <div className="h-full bg-green-500 rounded-full" style={{ width: `${notNoisePct}%` }} />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Alert Breakdown tiles */}
          {breakdownItems.length > 0 && (
            <div>
              <div className="text-[13px] font-semibold text-neutral-800 mb-1">Alert Breakdown</div>
              <div className="grid grid-cols-5 gap-2">
                {breakdownItems.map((item) => (
                  <div key={item.label} className="flex flex-col p-2">
                    <div className="flex justify-end mb-0.5">
                      <TrendTag change={item.trend ?? null} />
                    </div>
                    <span className="text-base font-bold text-neutral-900 leading-tight">
                      {item.count}
                      {item.pct !== null && (
                        <span className="text-xs font-normal text-neutral-400 ml-1">({item.pct}%)</span>
                      )}
                    </span>
                    <span className="text-[10px] mt-0.5 leading-tight text-neutral-400">{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Popup */}
      {showPopup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setShowPopup(false)}>
          <div
            className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-4xl mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close */}
            <div className="flex items-center justify-end mb-3">
              <button onClick={() => setShowPopup(false)} className="text-neutral-400 hover:text-neutral-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-4 border-b border-neutral-200">
              {(["breakdown", "sources", "activity"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-4 py-2 text-sm font-medium rounded-t transition-colors ${
                    tab === t
                      ? "border-b-2 border-neutral-800 text-neutral-800 -mb-px"
                      : "text-neutral-400 hover:text-neutral-600"
                  }`}
                >
                  {t === "breakdown" ? "Alert Breakdown" : t === "sources" ? "Alert Sources" : "Alert Activity"}
                </button>
              ))}
            </div>

            {/* Alert Breakdown tab */}
            {tab === "breakdown" && (
              <div className="space-y-5">
                {/* Urgency + Signal Quality */}
                {(urgencyEntries.length > 0 || notNoisePct !== null) && (
                  <div className="grid grid-cols-2 gap-6">
                    {urgencyEntries.length > 0 && (
                      <div>
                        <div className="flex items-center justify-between text-[13px] mb-1">
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
                        <div className="flex h-2.5 w-full rounded-full overflow-hidden bg-neutral-100">
                          {urgencyEntries.map(([key, value]) => {
                            const pct = urgencyTotal > 0 ? ((value as number) / urgencyTotal) * 100 : 0
                            return <div key={key} className={`h-full ${URGENCY_COLORS[key] ?? "bg-gray-400"}`} style={{ width: `${pct}%` }} />
                          })}
                        </div>
                      </div>
                    )}
                    {notNoisePct !== null && (
                      <div>
                        <div className="flex items-center justify-between text-[13px] mb-1">
                          <span className="text-neutral-700 font-medium">Signal Quality</span>
                          <span className="text-green-600 font-medium">{notNoisePct}% actionable</span>
                        </div>
                        <div className="h-2.5 w-full bg-neutral-100 rounded-full overflow-hidden">
                          <div className="h-full bg-green-500 rounded-full" style={{ width: `${notNoisePct}%` }} />
                        </div>
                      </div>
                    )}
                  </div>
                )}
                {/* Breakdown tiles */}
                {breakdownItems.length > 0 && (
                  <div>
                    <div className="text-[13px] font-semibold text-neutral-800 mb-2">Breakdown</div>
                    <div className="grid grid-cols-5 gap-3">
                      {breakdownItems.map((item) => (
                        <div key={item.label} className="flex flex-col rounded-lg border border-neutral-100 bg-neutral-50 p-3">
                          <span className="text-xl font-bold text-neutral-900 leading-tight">{item.count}</span>
                          {item.pct !== null && <span className="text-xs text-neutral-400 mt-0.5">{item.pct}%</span>}
                          <span className="text-[11px] text-neutral-500 mt-1">{item.label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Alert Sources tab */}
            {tab === "sources" && (
              <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                {sourceEntries.length === 0 ? (
                  <p className="text-sm text-neutral-400">No source data available.</p>
                ) : (
                  sourceEntries.map(([key, value], i) => (
                    <div key={key}>
                      <div className="flex items-center justify-between text-xs text-neutral-600 mb-1">
                        <span className="capitalize">{key.replace(/_/g, " ")}</span>
                        <span className="font-semibold text-neutral-800">{value as number}</span>
                      </div>
                      <div className="h-2 w-full bg-neutral-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${SOURCE_COLORS[i % SOURCE_COLORS.length]}`}
                          style={{ width: `${Math.round(((value as number) / sourceMax) * 100)}%` }}
                        />
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Alert Activity tab */}
            {tab === "activity" && (
              <div className="space-y-4">
                {activityItems.length > 0 && (
                  <div className="grid grid-cols-4 gap-3">
                    {activityItems.map((item) => (
                      <div key={item.label} className="flex flex-col rounded-lg border border-neutral-100 bg-neutral-50 p-4">
                        <div className="text-neutral-400 mb-2">{item.icon}</div>
                        <span className="text-2xl font-bold text-neutral-900 leading-tight">{item.count}</span>
                        <span className="text-xs text-neutral-500 mt-1">{item.label}</span>
                      </div>
                    ))}
                  </div>
                )}
                {(avgMttaSeconds !== null || avgMttrSeconds !== null) && (
                  <div>
                    <div className="text-[13px] font-semibold text-neutral-800 mb-2">Response Times</div>
                    <div className="grid grid-cols-2 gap-3">
                      {avgMttaSeconds !== null && (
                        <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-4">
                          <div className="text-xs text-neutral-500 mb-1">Avg MTTA</div>
                          <div className="text-xl font-bold text-neutral-900">{formatDuration(avgMttaSeconds)}</div>
                          <div className="text-[10px] text-neutral-400 mt-0.5">Mean time to acknowledge</div>
                        </div>
                      )}
                      {avgMttrSeconds !== null && (
                        <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-4">
                          <div className="text-xs text-neutral-500 mb-1">Avg MTTR</div>
                          <div className="text-xl font-bold text-neutral-900">{formatDuration(avgMttrSeconds)}</div>
                          <div className="text-[10px] text-neutral-400 mt-0.5">Mean time to resolve</div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                {activityItems.length === 0 && avgMttaSeconds === null && avgMttrSeconds === null && (
                  <p className="text-sm text-neutral-400 text-center py-6">No activity data available.</p>
                )}
              </div>
            )}

          </div>
        </div>
      )}
    </>
  )
}
