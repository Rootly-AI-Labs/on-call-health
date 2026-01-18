"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertTriangle, Loader2 } from "lucide-react"

// Safely extract numeric value, handling NaN and non-numbers
const safeNum = (val: unknown): number => {
  if (typeof val !== 'number' || isNaN(val)) return 0
  return val
}

interface UserIncidentCardProps {
  memberData: {
    user_name?: string
    incident_count?: number
    metrics?: {
      severity_distribution?: Record<string, number>
      after_hours_percentage?: number
    }
  }
  timeRange?: number
  platform?: string
  loading?: boolean
}

export function UserIncidentCard({
  memberData,
  timeRange = 30,
  platform = "rootly",
  loading = false
}: UserIncidentCardProps) {
  const memberName = memberData?.user_name || 'Team Member'
  const incidentCount = memberData?.incident_count || 0
  const severityDist = memberData?.metrics?.severity_distribution || {}

  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Incidents</CardTitle>
          <CardDescription>Incident load for {memberName}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-32 flex items-center justify-center">
            <div className="flex flex-col items-center space-y-3">
              <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
              <p className="text-sm text-neutral-500">Loading incidents...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  const hasSeverityData = Object.keys(severityDist).length > 0
  const isPagerDuty = platform === 'pagerduty'

  const pagerDutyCounts = {
    high: safeNum(severityDist.sev1) + safeNum(severityDist.high) + safeNum(severityDist.critical),
    low: safeNum(severityDist.sev4) + safeNum(severityDist.sev5) + safeNum(severityDist.low) + safeNum(severityDist.medium)
  }

  const rootlyCounts = {
    sev0: safeNum(severityDist.sev0 ?? severityDist.critical),
    sev1: safeNum(severityDist.sev1 ?? severityDist.high),
    sev2: safeNum(severityDist.sev2 ?? severityDist.medium),
    sev3: safeNum(severityDist.sev3 ?? severityDist.low),
    sev4: safeNum(severityDist.sev4 ?? severityDist.info)
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex-1 space-y-1.5">
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-500" />
              Incidents
            </CardTitle>
            <CardDescription>Past {timeRange} days</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pb-6">
        {/* Total incidents */}
        <div className="text-center mb-4">
          <div className="text-3xl font-bold text-neutral-900">{incidentCount}</div>
          <p className="text-sm text-neutral-500">Total Incidents Handled</p>
        </div>

        {/* Severity breakdown */}
        {hasSeverityData && incidentCount > 0 && isPagerDuty && (
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <div className="text-xs font-semibold text-red-700 mb-1">High Urgency</div>
              <div className="text-xl font-bold text-red-600">{pagerDutyCounts.high}</div>
            </div>
            <div className="bg-green-50 rounded-lg p-3 text-center">
              <div className="text-xs font-semibold text-green-700 mb-1">Low Urgency</div>
              <div className="text-xl font-bold text-green-600">{pagerDutyCounts.low}</div>
            </div>
          </div>
        )}

        {hasSeverityData && incidentCount > 0 && !isPagerDuty && (
          <div className={`grid ${rootlyCounts.sev0 > 0 ? 'grid-cols-5' : 'grid-cols-4'} gap-2`}>
            {rootlyCounts.sev0 > 0 && (
              <div className="bg-purple-50 rounded-lg p-2 text-center">
                <div className="text-xs font-semibold text-purple-600">SEV0</div>
                <div className="text-lg font-bold text-purple-600">{rootlyCounts.sev0}</div>
              </div>
            )}
            <div className="bg-red-50 rounded-lg p-2 text-center">
              <div className="text-xs font-semibold text-red-600">SEV1</div>
              <div className="text-lg font-bold text-red-600">{rootlyCounts.sev1}</div>
            </div>
            <div className="bg-orange-50 rounded-lg p-2 text-center">
              <div className="text-xs font-semibold text-orange-600">SEV2</div>
              <div className="text-lg font-bold text-orange-600">{rootlyCounts.sev2}</div>
            </div>
            <div className="bg-yellow-50 rounded-lg p-2 text-center">
              <div className="text-xs font-semibold text-yellow-600">SEV3</div>
              <div className="text-lg font-bold text-yellow-600">{rootlyCounts.sev3}</div>
            </div>
            <div className="bg-green-50 rounded-lg p-2 text-center">
              <div className="text-xs font-semibold text-green-600">SEV4</div>
              <div className="text-lg font-bold text-green-600">{rootlyCounts.sev4}</div>
            </div>
          </div>
        )}

        {/* No severity data message */}
        {(!hasSeverityData || incidentCount === 0) && (
          <div className="text-center text-sm text-neutral-500 py-2">
            No severity breakdown available
          </div>
        )}
      </CardContent>
    </Card>
  )
}
