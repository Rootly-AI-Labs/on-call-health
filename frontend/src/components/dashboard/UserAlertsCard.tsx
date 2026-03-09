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
  const relatedCounts = memberData?.alerts_related_counts || {}
  const relatedEntries = Object.entries(relatedCounts)
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
        {relatedEntries.length > 0 && (
          <div className="pt-3">
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
      </CardContent>
    </Card>
  )
}
