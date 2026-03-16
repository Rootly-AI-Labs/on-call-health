"use client"

import { useState, useMemo } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Trophy } from "lucide-react"

interface AlertsLeaderboardProps {
  currentAnalysis: any
}

type SortKey =
  | "total"
  | "with_incidents"
  | "after_hours"
  | "night_time"
  | "escalated"
  | "retriggered"
  | "high"
  | "mtta"
  | "mttr"

const FILTERS: { key: SortKey; label: string; description: string }[] = [
  { key: "total",          label: "Total",          description: "Total alerts responded to by each team member." },
  { key: "with_incidents", label: "With Incidents", description: "Alerts that escalated into a full incident." },
  { key: "after_hours",    label: "After-Hours",    description: "Alerts received outside of business hours (before 9am or after 5pm, and weekends)." },
  { key: "night_time",     label: "Night-Time",     description: "Alerts received during deep night hours (10pm – 6am)." },
  { key: "escalated",      label: "Escalated",      description: "Alerts that were escalated to another responder or level." },
  { key: "retriggered",    label: "Retriggered",    description: "Alerts that fired again after being acknowledged or resolved." },
  { key: "high",           label: "High Urgency",   description: "Alerts classified as high urgency — requiring immediate attention." },
  { key: "mtta",           label: "Avg MTTA",       description: "Average time from alert trigger to first acknowledgement." },
  { key: "mttr",           label: "Avg MTTR",       description: "Average time from alert trigger to full resolution." },
]

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

function getMemberValue(member: any, key: SortKey): number {
  switch (key) {
    case "total":          return member.alerts_count ?? 0
    case "with_incidents": return member.alerts_with_incidents_count ?? 0
    case "after_hours":    return member.alerts_after_hours_count ?? 0
    case "night_time":     return member.alerts_night_time_count ?? 0
    case "escalated":      return member.alerts_escalated_count ?? 0
    case "retriggered":    return member.alerts_retriggered_count ?? 0
    case "high":           return member.alerts_urgency_counts?.high ?? 0
    case "mtta":           return member.alerts_avg_mtta_seconds ?? 0
    case "mttr":           return member.alerts_avg_mttr_seconds ?? 0
    default:               return 0
  }
}

function formatValue(value: number, key: SortKey): string {
  if (key === "mtta" || key === "mttr") return value > 0 ? formatDuration(value) : "—"
  return String(value)
}

const RANK_COLORS    = ["text-yellow-500", "text-neutral-400", "text-orange-600"]
const RANK_BAR_COLORS = ["bg-yellow-400",  "bg-neutral-400",   "bg-orange-400"]

export function AlertsLeaderboard({ currentAnalysis }: AlertsLeaderboardProps) {
  const [activeKey, setActiveKey] = useState<SortKey>("total")

  const activeFilter = FILTERS.find((f) => f.key === activeKey)!

  const members: any[] = useMemo(() => {
    const teamAnalysis = currentAnalysis?.analysis_data?.team_analysis
    const arr = Array.isArray(teamAnalysis) ? teamAnalysis : (teamAnalysis as any)?.members ?? []
    return arr.filter((m: any) => typeof m === "object" && m !== null)
  }, [currentAnalysis])

  const sorted = useMemo(() => {
    return [...members]
      .filter((m) => getMemberValue(m, activeKey) > 0)
      .sort((a, b) => getMemberValue(b, activeKey) - getMemberValue(a, activeKey))
  }, [members, activeKey])

  const maxVal = sorted.length > 0 ? getMemberValue(sorted[0], activeKey) : 1

  return (
    <Card className="bg-white flex flex-col h-full overflow-hidden">
      <CardHeader className="pb-2 shrink-0">
        <div className="space-y-1">
          <CardTitle className="text-neutral-900">Alerts Leaderboard</CardTitle>
          <CardDescription>Team members ranked by alert metric</CardDescription>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col flex-1 min-h-0 overflow-hidden">
        {/* Filter tabs */}
        <div className="flex flex-wrap gap-1.5 mb-2 shrink-0">
          {FILTERS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveKey(key)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                activeKey === key
                  ? "bg-neutral-900 text-white"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Active filter description */}
        <p className="text-xs text-neutral-400 mb-3 shrink-0">{activeFilter.description}</p>

        {sorted.length === 0 ? (
          <div className="text-sm text-neutral-400 text-center py-6">No data for this metric</div>
        ) : (
          <div className="overflow-y-auto flex-1 space-y-2 pr-6 min-h-0">
            {sorted.map((member, i) => {
              const name   = member.user_name || member.name || member.user_email || "Unknown"
              const val    = getMemberValue(member, activeKey)
              const barPct = Math.max(maxVal > 0 ? (val / maxVal) * 100 : 0, 2)
              const isTop3 = i < 3

              return (
                <div key={member.user_id ?? member.user_email ?? i} className="flex items-center gap-3">
                  <span className={`text-xs font-bold w-5 text-right shrink-0 ${RANK_COLORS[i] ?? "text-neutral-400"}`}>
                    {i + 1}
                  </span>
                  <span className="text-sm text-neutral-700 font-medium w-36 shrink-0 truncate">{name}</span>
                  <div className="flex-1 min-w-0 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${isTop3 ? (RANK_BAR_COLORS[i] ?? "bg-neutral-300") : "bg-neutral-300"}`}
                      style={{ width: `${barPct}%` }}
                    />
                  </div>
                  <span className={`text-xs font-semibold shrink-0 w-10 text-right ${isTop3 ? RANK_COLORS[i] : "text-neutral-600"}`}>
                    {formatValue(val, activeKey)}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
