/**
 * @deprecated Use BaseRiskFactorsCard with TeamRiskFactorsCard or UserRiskFactorsCard wrappers instead.
 * This component has been replaced with a shared base component architecture for consistency.
 *
 * Old usage (Team Trends):
 * - Replaced by: TeamRiskFactorsCard
 *
 * Old usage (User Risk Factors):
 * - Replaced by: UserRiskFactorsCard
 *
 * To remove: Delete this file after confirming no other references exist.
 */

"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Tooltip } from "recharts"
import { Info, AlertTriangle } from "lucide-react"

interface RiskFactorsCardProps {
  title: string
  description: string | React.ReactNode
  factorsData: Array<{ factor: string; value: number }>
  showAlert?: boolean
  alertCount?: number
  domain?: [number, number]
}

const FACTOR_DESCRIPTIONS: Record<string, { tooltip: string }> = {
  'Workload Intensity': {
    tooltip: 'Measures workload stress by weighting incidents based on their severity level. Higher values indicate more stressful workload.'
  },
  'After Hours Activity': {
    tooltip: 'Work outside business hours (9 AM - 5 PM) and weekends. Timezone-aware based on team member\'s local time.'
  },
  'Incident Load': {
    tooltip: 'Total incident volume and frequency. Counts all incidents regardless of severity or timing.'
  },
  'Workload': {
    tooltip: 'Measures workload stress by weighting incidents based on their severity level. Higher values indicate more stressful workload.'
  },
  'After Hours': {
    tooltip: 'Work outside business hours (9 AM - 5 PM) and weekends. Timezone-aware based on team member\'s local time.'
  }
}

export function RiskFactorsCard({
  title,
  description,
  factorsData,
  showAlert = false,
  alertCount = 0,
  domain = [0, 100]
}: RiskFactorsCardProps) {

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex-1 space-y-1.5">
            <div className="flex items-center space-x-2">
              <CardTitle>{title}</CardTitle>
              {showAlert && alertCount > 0 && (
                <div className="flex items-center space-x-1">
                  <AlertTriangle className="w-4 h-4 text-red-500" />
                  <span className="text-sm font-medium text-red-600">
                    {alertCount} factor{alertCount > 1 ? 's' : ''} need{alertCount === 1 ? 's' : ''} attention
                  </span>
                </div>
              )}
            </div>
            <CardDescription>{description}</CardDescription>
          </div>

          {/* Info icon with tooltip */}
          <div className="relative group ml-4">
            <Info className="w-4 h-4 text-neutral-500 cursor-help hover:text-neutral-700 transition-colors" />
            <div className="absolute top-full right-0 mt-2 px-3 py-2 bg-neutral-900/95 text-white text-xs rounded-lg w-72 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
              <div className="font-semibold mb-2">Risk Factors Scoring</div>
              <div className="space-y-2">
                <div>
                  <div className="font-medium text-blue-300">Workload Intensity</div>
                  <div className="text-xs mt-1">{FACTOR_DESCRIPTIONS['Workload Intensity'].tooltip}</div>
                </div>
                <div>
                  <div className="font-medium text-blue-300">After Hours Activity</div>
                  <div className="text-xs mt-1">{FACTOR_DESCRIPTIONS['After Hours Activity'].tooltip}</div>
                </div>
                <div>
                  <div className="font-medium text-blue-300">Incident Load</div>
                  <div className="text-xs mt-1">{FACTOR_DESCRIPTIONS['Incident Load'].tooltip}</div>
                </div>
              </div>
              <div className="absolute bottom-full right-4 w-0 h-0 border-l-4 border-r-4 border-b-4 border-l-transparent border-r-transparent border-b-gray-900/95"></div>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={factorsData}>
              <PolarGrid gridType="polygon" />
              <PolarAngleAxis
                dataKey="factor"
                tick={{ fontSize: 13, fill: '#374151', fontWeight: 500 }}
              />
              <PolarRadiusAxis
                domain={domain}
                tick={false}
                angle={90}
              />
              <Radar
                name="Risk Level"
                dataKey="value"
                stroke="#8b5cf6"
                fill="#8b5cf6"
                fillOpacity={0.3}
                strokeWidth={2}
              />
              <Tooltip
                content={({ payload }) => {
                  if (payload && payload.length > 0) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-neutral-900 p-3 border border-neutral-700 rounded-lg shadow-lg">
                        <p className="text-sm font-medium text-neutral-300">{data.factor}</p>
                        <p className="text-base font-semibold text-purple-400 mt-1">
                          Score: {Math.round(data.value)}/{domain[1]}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
