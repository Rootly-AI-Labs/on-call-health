"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Bell, AlertTriangle } from "lucide-react"

interface AlertsCountCardProps {
  currentAnalysis: any
}

function formatDate(value?: string): string {
  if (!value) return "unknown"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "unknown"
  return date.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })
}

export function AlertsCountCard({ currentAnalysis }: AlertsCountCardProps): React.ReactElement | null {
  const alerts = currentAnalysis?.analysis_data?.metadata?.alerts
  if (!alerts) return null

  const total = alerts.filtered_total ?? alerts.total
  const hasError = Boolean(alerts.error)
  const isScoped = alerts.filtered_total !== null && alerts.filtered_total !== undefined
  const scopeLabel = alerts.team_name ? `Scoped to ${alerts.team_name}` : "All users"
  const dateRange = `${formatDate(alerts.start)} - ${formatDate(alerts.end)}`
  const relatedCounts = alerts.related_counts || alerts.included_counts || {}
  const relatedEntries = Object.entries(relatedCounts)
    .filter(([, value]) => typeof value === "number" && value > 0)
    .sort((a, b) => (b[1] as number) - (a[1] as number))

  return (
    <Card className="mb-6">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle>Alerts</CardTitle>
            <CardDescription>Rootly alert count for this analysis window</CardDescription>
          </div>
          <div className="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center">
            <Bell className="w-4 h-4 text-red-600" />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {hasError ? (
          <div className="flex items-start gap-2 text-sm text-red-700">
            <AlertTriangle className="w-4 h-4 mt-0.5" />
            <span>Alerts data unavailable ({alerts.error})</span>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-end gap-3">
              <div className="text-3xl font-semibold text-neutral-900">
                {typeof total === "number" ? total : "N/A"}
              </div>
              <div className="text-sm text-neutral-600">{scopeLabel}</div>
            </div>
            <div className="text-sm text-neutral-600">Date range: {dateRange}</div>
            {isScoped && typeof alerts.total === "number" && (
              <div className="text-xs text-neutral-500">Org total in range: {alerts.total}</div>
            )}
            {alerts.truncated && (
              <div className="text-xs text-yellow-700">Alert count may be partial (page limit reached)</div>
            )}
            {relatedEntries.length > 0 && (
              <div className="pt-2">
                <div className="text-xs font-medium text-neutral-600 mb-2">Related data (distinct)</div>
                <div className="flex flex-wrap gap-2">
                  {relatedEntries.map(([key, value]) => (
                    <span
                      key={key}
                      className="text-xs px-2 py-1 rounded-full bg-neutral-100 text-neutral-700"
                    >
                      {key}: {value as number}
                    </span>
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
