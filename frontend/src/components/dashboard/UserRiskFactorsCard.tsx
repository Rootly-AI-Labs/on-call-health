"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Info, Loader2 } from "lucide-react"

interface OCBFactor {
  key: string
  name: string
  percentage: number
  dimension: string
}

interface UserRiskFactorsCardProps {
  selectedMember: {
    user_name?: string
    ocb_factors?: {
      all?: OCBFactor[]
    }
  }
  loading?: boolean
}

export function UserRiskFactorsCard({
  selectedMember,
  loading = false
}: UserRiskFactorsCardProps) {
  const memberName = selectedMember?.user_name || 'Team Member'
  const factors = selectedMember?.ocb_factors?.all || []

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Risk Factors</CardTitle>
          <CardDescription>Key factors contributing to risk for {memberName}</CardDescription>
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
          <CardDescription>Key factors contributing to risk for {memberName}</CardDescription>
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
            <CardDescription>Key factors contributing to risk for {memberName}</CardDescription>
          </div>
          <div className="relative group ml-4">
            <Info className="w-4 h-4 text-neutral-500 cursor-help hover:text-neutral-700 transition-colors" />
            <div className="absolute top-full right-0 mt-2 px-3 py-2 bg-neutral-900/95 text-white text-xs rounded-lg w-72 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
              <div className="font-semibold mb-2">Risk Factor Contributions</div>
              <div className="text-xs">Percentage contribution of each factor to the overall risk score based on work patterns, incident load, and timing.</div>
              <div className="absolute bottom-full right-4 w-0 h-0 border-l-4 border-r-4 border-b-4 border-l-transparent border-r-transparent border-b-gray-900/95"></div>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-4">
        <div className="space-y-2">
          <div className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-2">
            Contributing Factors
          </div>
          {factors.map((factor: OCBFactor) => (
            <div key={factor.key} className="flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-neutral-700 truncate">{factor.name}</span>
                  <span className="text-sm font-semibold text-neutral-900 ml-2">{factor.percentage}%</span>
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
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
