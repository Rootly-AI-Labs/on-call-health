"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Bell } from "lucide-react"

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

export function UserAlertsCard({ memberData, alertsMeta }: UserAlertsCardProps): React.ReactElement {
  const count = memberData?.alerts_count
  const dateRange = alertsMeta ? `${formatDate(alertsMeta.start)} - ${formatDate(alertsMeta.end)}` : "unknown"
  const noiseCounts = memberData?.alerts_noise_counts || {}
  const totalForNoise = typeof count === "number" && count > 0 ? count : null
  const noisePct = totalForNoise !== null ? Math.round(((noiseCounts.noise || 0) / totalForNoise) * 100) : null
  const notNoisePct = totalForNoise !== null ? Math.round(((noiseCounts.not_noise || 0) / totalForNoise) * 100) : null
  const afterHoursCount = typeof memberData?.alerts_after_hours_count === "number" ? memberData.alerts_after_hours_count : null
  const afterHoursPct = totalForNoise !== null && afterHoursCount !== null
    ? Math.round((afterHoursCount / totalForNoise) * 100)
    : null
  const urgencyCounts = memberData?.alerts_urgency_counts || {}
  const urgencyEntries = Object.entries(urgencyCounts)
    .filter(([, value]) => typeof value === "number" && value > 0)
    .sort((a, b) => (b[1] as number) - (a[1] as number))

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle>User Alerts</CardTitle>
            <CardDescription>Alerts associated with this user</CardDescription>
          </div>
          <div className="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center">
            <Bell className="w-4 h-4 text-red-600" />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-semibold text-neutral-900">
          {typeof count === "number" ? count : "N/A"}
        </div>
        <div className="text-sm text-neutral-600 mt-2">
          Date range: {dateRange}
        </div>
        {(noisePct !== null || notNoisePct !== null) && (
          <div className="pt-2 text-xs text-neutral-600">
            Noise: {noisePct !== null ? `${noisePct}%` : "N/A"} · Not noise: {notNoisePct !== null ? `${notNoisePct}%` : "N/A"}
          </div>
        )}
        {(afterHoursCount !== null || afterHoursPct !== null) && (
          <div className="pt-1 text-xs text-neutral-600">
            After-hours alerts: {afterHoursCount !== null ? afterHoursCount : "N/A"}
            {afterHoursPct !== null ? ` (${afterHoursPct}%)` : ""}
          </div>
        )}
        {urgencyEntries.length > 0 && (
          <div className="pt-2 text-xs text-neutral-600">
            Urgency: {urgencyEntries.map(([key, value]) => `${key}: ${value as number}`).join(" · ")}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
