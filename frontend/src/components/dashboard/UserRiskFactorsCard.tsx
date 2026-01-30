"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2 } from "lucide-react"
import { InfoTooltip } from "@/components/ui/info-tooltip"
import { FACTOR_DESCRIPTIONS } from "./TeamRiskFactorsCard"

interface OCHFactor {
  key: string
  name: string
  percentage: number
  dimension: string
}

interface UserRiskFactorsCardProps {
  selectedMember: {
    user_name?: string
    och_factors?: {
      all?: OCHFactor[]
    }
  }
  loading?: boolean
}

export function UserRiskFactorsCard({
  selectedMember,
  loading = false
}: UserRiskFactorsCardProps): React.ReactElement {
  const memberName = selectedMember?.user_name || 'Team Member'
  const factors = selectedMember?.och_factors?.all || []

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Risk Factors</CardTitle>
          <CardDescription>Top 5 risk factors for {memberName}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center">
            <div className="flex flex-col items-center space-y-3">
              <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
              <p className="text-sm text-neutral-500">Loading risk factors...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (factors.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Risk Factors</CardTitle>
          <CardDescription>Top 5 risk factors for {memberName}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center">
            <p className="text-sm text-neutral-500">No risk factor data available</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex-1 space-y-1.5">
            <CardTitle>Risk Factors</CardTitle>
            <CardDescription>Top 5 risk factors for {memberName}</CardDescription>
          </div>
          <InfoTooltip
            content="Percentage contribution of each factor to the overall risk score based on work patterns, incident load, and timing."
            side="left"
            iconClassName="ml-4 w-4 h-4"
          />
        </div>
      </CardHeader>
      <CardContent className="p-4 pb-6">
        <div className="space-y-3">
          {factors.slice(0, 5).map((factor: OCHFactor) => {
            const factorDescription = FACTOR_DESCRIPTIONS[factor.name]
            return (
              <div key={factor.key}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm text-neutral-700">{factor.name}</span>
                  {factorDescription && (
                    <InfoTooltip content={factorDescription} side="right" />
                  )}
                  <span className="text-sm font-semibold text-violet-600 ml-auto">{factor.percentage}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full transition-all duration-500 bg-violet-500"
                    style={{
                      width: `${Math.min(factor.percentage * 2, 100)}%`
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
