"use client"

import { useState, useEffect } from "react"
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

// Custom tick component for mobile-friendly labels with line breaks
function CustomPolarAngleTick(props: any) {
  const { x, y, payload, isMobile, cx = 0, cy = 0 } = props

  // Map of factor names to mobile-friendly versions with line breaks
  const mobileBreaks: Record<string, string[]> = {
    'After-hours activity': isMobile ? ['After', 'hours activity'] : ['After-hours activity'],
    'Consecutive incident days': isMobile ? ['Consecutive', 'incident days'] : ['Consecutive incident days'],
    'Task load': isMobile ? ['Task', 'load'] : ['Task load'],
    'High-severity incidents': isMobile ? ['High severity', 'incidents'] : ['High-severity incidents'],
    'After Hours Activity': isMobile ? ['After', 'hours activity'] : ['After Hours Activity'],
    'Workload Intensity': isMobile ? ['Workload', 'Intensity'] : ['Workload Intensity'],
    'On-call load': isMobile ? ['On-call', 'load'] : ['On-call load'],
    'Weekend Work': isMobile ? ['Weekend', 'Work'] : ['Weekend Work'],
    'Response Time': isMobile ? ['Response', 'Time'] : ['Response Time'],
  }

  const lines = mobileBreaks[payload.value] || [payload.value]

  // Calculate offset from center to push labels further away
  const dx = x - (cx || 0)
  const dy = y - (cy || 0)
  const distance = Math.sqrt(dx * dx + dy * dy)
  const offsetFactor = isMobile ? 1.15 : 1.1 // Push labels 10% further on desktop, 15% on mobile

  // Prevent division by zero when distance is 0
  let offsetX = 0
  let offsetY = 0
  if (distance > 0) {
    const unitX = dx / distance
    const unitY = dy / distance
    const scaledDistance = distance * offsetFactor
    offsetX = unitX * scaledDistance
    offsetY = unitY * scaledDistance
  }

  const finalX = (cx || 0) + offsetX
  const finalY = (cy || 0) + offsetY

  return (
    <text
      x={finalX}
      y={finalY}
      textAnchor="middle"
      dominantBaseline="middle"
      className="text-xs font-medium fill-neutral-700"
      style={{ fontSize: isMobile ? '11px' : '13px' }}
    >
      {lines.map((line, index) => (
        <tspan key={index} x={finalX} dy={index === 0 ? 0 : '1em'}>
          {line}
        </tspan>
      ))}
    </text>
  )
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
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    // Only run on client-side
    if (typeof window === 'undefined') return

    let isMounted = true
    const checkMobile = () => {
      if (isMounted) {
        setIsMobile(window.innerWidth < 768)
      }
    }

    checkMobile()
    window.addEventListener('resize', checkMobile)

    return () => {
      isMounted = false
      window.removeEventListener('resize', checkMobile)
    }
  }, [])

  // Use fixed 0-100 scale for consistent axis representation
  const effectiveDomain: [number, number] = [0, 100]
  const ringCount = 5
  const radiusTicks = Array.from({ length: ringCount + 1 }, (_, index) => {
    const raw = (effectiveDomain[1] / ringCount) * index
    return Math.round(raw * 100) / 100
  })

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
        <div className="flex-1 min-h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={factorsData} cx="50%" cy="52%" outerRadius={isMobile ? "62%" : "75%"}>
              <PolarGrid gridType="polygon" />
              <PolarAngleAxis
                dataKey="factor"
                tick={(props) => <CustomPolarAngleTick {...props} isMobile={isMobile} />}
                radius={isMobile ? 75 : 160}
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
