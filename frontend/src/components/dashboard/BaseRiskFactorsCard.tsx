"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Tooltip } from "recharts"
import { Info, AlertTriangle, Loader2 } from "lucide-react"
import { InfoTooltip } from "@/components/ui/info-tooltip"

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
  // Dynamically scale the chart so low values still fill the space.
  // Round up to the nearest "nice" ceiling (10, 20, 25, 50, 100).
  const maxValue = Math.max(...factorsData.map(d => d.value), 0)
  const niceSteps = [10, 20, 25, 50, 100]
  const dynamicMax = niceSteps.find(s => s >= maxValue * 1.2) ?? 100
  const effectiveDomain: [number, number] = domain[1] !== 100
    ? domain                         // respect explicit caller override
    : [0, Math.max(dynamicMax, 10)]  // auto-scale when using default

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
    <Card className={`h-full flex flex-col ${className}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex-1 space-y-1.5">
            <div className="flex items-center space-x-2">
              <CardTitle>{title}</CardTitle>
              {showAlert && alertCount > 0 && (
                <div className="flex items-center space-x-1">
                  <AlertTriangle className="w-4 h-4 text-red-500" />
                  <span className="text-sm font-medium text-red-600">
                    {alertCount === 1
                      ? '1 factor needs attention'
                      : `${alertCount} factors need attention`}
                  </span>
                </div>
              )}
            </div>
            <CardDescription>{description}</CardDescription>
          </div>

          {showInfoTooltip && Object.keys(factorDescriptions).length > 0 && (
            <div className="ml-4">
              <InfoTooltip
                content={
                  factorsData.map((factor) => {
                    const description = factorDescriptions[factor.factor]
                    return description ? `${factor.factor}: ${description}` : factor.factor
                  }).join('\n\n')
                }
                side="left"
              />
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col min-h-0 pb-2">
        <div className="flex-1 min-h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={factorsData} cx="50%" cy="55%" outerRadius="95%">
              <PolarGrid gridType="polygon" />
              <PolarAngleAxis
                dataKey="factor"
                tick={{ fontSize: 13, fill: '#374151', fontWeight: 500 }}
              />
              <PolarRadiusAxis
                domain={effectiveDomain}
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
                          Score: {Math.round(data.value)}/{effectiveDomain[1]}
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
