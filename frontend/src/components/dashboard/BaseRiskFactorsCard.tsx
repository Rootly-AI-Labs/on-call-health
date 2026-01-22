"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Tooltip } from "recharts"
import { Info, AlertTriangle, Loader2 } from "lucide-react"

export interface BaseRiskFactorsCardProps {
  title: string
  description: string | React.ReactNode
  factorsData: Array<{ factor: string; value: number }>

  // Optional features
  showAlert?: boolean
  alertCount?: number
  showInfoTooltip?: boolean
  factorDescriptions?: Record<string, string>

  // Chart configuration
  domain?: [number, number]
  height?: string  // Tailwind class like "h-64"
  chartColor?: string  // Default: "#8b5cf6"

  // States
  loading?: boolean
  className?: string
}

export function BaseRiskFactorsCard({
  title,
  description,
  factorsData,
  showAlert = false,
  alertCount = 0,
  showInfoTooltip = true,
  factorDescriptions = {},
  domain = [0, 100],
  height = "h-80",
  chartColor = "#8b5cf6",
  loading = false,
  className = ""
}: BaseRiskFactorsCardProps): React.ReactElement {
  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className={`${height} flex items-center justify-center`}>
            <div className="flex flex-col items-center space-y-3">
              <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
              <p className="text-sm text-neutral-500">Loading risk factors...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!factorsData || factorsData.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className={`${height} flex items-center justify-center`}>
            <p className="text-sm text-neutral-500">No risk factor data available</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex-1 space-y-1.5">
            <div className="flex items-center space-x-2">
              <CardTitle>{title}</CardTitle>
              {showAlert && alertCount && alertCount > 0 && (
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

          {showInfoTooltip && Object.keys(factorDescriptions).length > 0 && (
            <div className="relative group ml-4">
              <Info className="w-4 h-4 text-neutral-500 cursor-help hover:text-neutral-700 transition-colors" />
              <div className="absolute top-full right-0 mt-2 px-3 py-2 bg-neutral-900/95 text-white text-xs rounded-lg w-72 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                <div className="font-semibold mb-2">Risk Factors Scoring</div>
                <div className="space-y-2">
                  {factorsData.map((factor) => {
                    const description = factorDescriptions[factor.factor]
                    return (
                      <div key={factor.factor}>
                        <div className="font-medium text-blue-300">{factor.factor}</div>
                        {description && (
                          <div className="text-xs mt-1">{description}</div>
                        )}
                      </div>
                    )
                  })}
                </div>
                <div className="absolute bottom-full right-4 w-0 h-0 border-l-4 border-r-4 border-b-4 border-l-transparent border-r-transparent border-b-gray-900/95"></div>
              </div>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className={height}>
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={factorsData} outerRadius="80%">
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
                stroke={chartColor}
                fill={chartColor}
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
