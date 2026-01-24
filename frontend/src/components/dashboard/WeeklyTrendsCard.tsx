"use client"

import type { ReactElement } from "react"
import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Bar,
  BarChart,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Line,
  ComposedChart,
  ReferenceLine
} from "recharts"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Info, TrendingUp, TrendingDown, Minus, ArrowUpRight, ArrowDownRight } from "lucide-react"

interface WeeklyTrendsCardProps {
  dailyTrends: any[]
  loading: boolean
  timeRange: number
}

// Aggregate daily data into weekly buckets
function aggregateToWeekly(dailyData: any[]): any[] {
  if (!dailyData || dailyData.length === 0) return []

  const weeklyBuckets: Map<string, any[]> = new Map()

  dailyData.forEach((day) => {
    const date = new Date(day.date)
    // Get the Monday of this week
    const dayOfWeek = date.getDay()
    const monday = new Date(date)
    monday.setDate(date.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1))
    const weekKey = monday.toISOString().split('T')[0]

    if (!weeklyBuckets.has(weekKey)) {
      weeklyBuckets.set(weekKey, [])
    }
    weeklyBuckets.get(weekKey)!.push(day)
  })

  // Convert buckets to weekly averages
  const weeklyData = Array.from(weeklyBuckets.entries())
    .map(([weekStart, days]) => {
      const avgRiskLevel = days.reduce((sum, d) => sum + Math.max(0, Math.min(100, 100 - Math.round((d.overall_score || 0) * 10))), 0) / days.length
      const totalIncidents = days.reduce((sum, d) => sum + (d.incident_count || 0), 0)
      const avgAfterHours = days.reduce((sum, d) => sum + (d.after_hours_percentage || 0), 0) / days.length
      const avgSeverityWeighted = days.reduce((sum, d) => sum + (d.severity_weighted_count || 0), 0) / days.length

      const weekDate = new Date(weekStart)
      const weekEnd = new Date(weekStart)
      weekEnd.setDate(weekEnd.getDate() + 6)

      return {
        weekStart,
        weekLabel: `${weekDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`,
        weekRange: `${weekDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`,
        riskLevel: Math.round(avgRiskLevel),
        incidentCount: totalIncidents,
        afterHoursPercentage: Math.round(avgAfterHours),
        severityWeighted: Math.round(avgSeverityWeighted),
        daysInWeek: days.length
      }
    })
    .sort((a, b) => a.weekStart.localeCompare(b.weekStart))

  return weeklyData
}

// Calculate trend between two periods
function calculateTrend(current: number, previous: number): { direction: 'up' | 'down' | 'stable', percentage: number } {
  if (previous === 0) return { direction: 'stable', percentage: 0 }
  const change = ((current - previous) / previous) * 100
  if (Math.abs(change) < 5) return { direction: 'stable', percentage: Math.round(change) }
  return {
    direction: change > 0 ? 'up' : 'down',
    percentage: Math.round(Math.abs(change))
  }
}

function TrendIndicator({ trend, metric }: { trend: { direction: string, percentage: number }, metric: string }) {
  // For risk metrics, down is good (improving), up is bad (worsening)
  const isImproving = trend.direction === 'down'
  const isWorsening = trend.direction === 'up'

  if (trend.direction === 'stable') {
    return (
      <div className="flex items-center gap-1 text-neutral-500">
        <Minus className="w-4 h-4" />
        <span className="text-sm font-medium">Stable</span>
      </div>
    )
  }

  return (
    <div className={`flex items-center gap-1 ${isImproving ? 'text-green-600' : 'text-red-600'}`}>
      {isImproving ? (
        <ArrowDownRight className="w-4 h-4" />
      ) : (
        <ArrowUpRight className="w-4 h-4" />
      )}
      <span className="text-sm font-medium">
        {trend.percentage}% {isImproving ? 'better' : 'worse'}
      </span>
    </div>
  )
}

function WeekOverWeekComparison({ weeklyData, metric }: { weeklyData: any[], metric: string }) {
  if (weeklyData.length < 2) return null

  const current = weeklyData[weeklyData.length - 1]
  const previous = weeklyData[weeklyData.length - 2]
  const fourWeeksAgo = weeklyData.length >= 4 ? weeklyData[weeklyData.length - 4] : null

  const metricKey = metric === 'health_score' ? 'riskLevel' :
                    metric === 'incident_load' ? 'incidentCount' :
                    metric === 'after_hours' ? 'afterHoursPercentage' : 'severityWeighted'

  const vsLastWeek = calculateTrend(current[metricKey], previous[metricKey])
  const vs4WeeksAgo = fourWeeksAgo ? calculateTrend(current[metricKey], fourWeeksAgo[metricKey]) : null

  return (
    <div className="mt-4 flex items-center justify-center gap-6 text-sm">
      <div className="flex items-center gap-2">
        <span className="text-neutral-500">This week:</span>
        <span className="font-semibold text-neutral-900">{current[metricKey]}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-neutral-500">vs last week:</span>
        <span className={`font-medium ${vsLastWeek.direction === 'down' ? 'text-green-600' : vsLastWeek.direction === 'up' ? 'text-red-600' : 'text-neutral-500'}`}>
          {vsLastWeek.direction === 'stable' ? '—' : `${vsLastWeek.direction === 'down' ? '↓' : '↑'}${vsLastWeek.percentage}%`}
        </span>
      </div>
      {vs4WeeksAgo && (
        <div className="flex items-center gap-2">
          <span className="text-neutral-500">vs 4 wks ago:</span>
          <span className={`font-medium ${vs4WeeksAgo.direction === 'down' ? 'text-green-600' : vs4WeeksAgo.direction === 'up' ? 'text-red-600' : 'text-neutral-500'}`}>
            {vs4WeeksAgo.direction === 'stable' ? '—' : `${vs4WeeksAgo.direction === 'down' ? '↓' : '↑'}${vs4WeeksAgo.percentage}%`}
          </span>
        </div>
      )}
    </div>
  )
}

export function WeeklyTrendsCard({
  dailyTrends,
  loading,
  timeRange
}: WeeklyTrendsCardProps): ReactElement {
  const [selectedMetric, setSelectedMetric] = useState<string>("health_score")
  const [showIncidentOverlay, setShowIncidentOverlay] = useState(true)

  const METRIC_CONFIG: Record<string, any> = {
    health_score: {
      label: "Risk Level",
      color: "#7C63D6",
      dataKey: "riskLevel",
      yAxisLabel: "Risk Level"
    },
    incident_load: {
      label: "Incident Count",
      color: "#7C63D6",
      dataKey: "incidentCount",
      yAxisLabel: "Incidents"
    },
    after_hours: {
      label: "After Hours %",
      color: "#7C63D6",
      dataKey: "afterHoursPercentage",
      yAxisLabel: "After Hours %"
    },
    severity_weighted: {
      label: "Workload Intensity",
      color: "#7C63D6",
      dataKey: "severityWeighted",
      yAxisLabel: "Severity Score"
    }
  }

  const weeklyData = aggregateToWeekly(dailyTrends)
  const config = METRIC_CONFIG[selectedMetric]

  // Calculate overall trend (first half vs second half)
  const halfIndex = Math.floor(weeklyData.length / 2)
  const firstHalfAvg = weeklyData.slice(0, halfIndex).reduce((sum, w) => sum + w[config.dataKey], 0) / halfIndex || 0
  const secondHalfAvg = weeklyData.slice(halfIndex).reduce((sum, w) => sum + w[config.dataKey], 0) / (weeklyData.length - halfIndex) || 0
  const overallTrend = calculateTrend(secondHalfAvg, firstHalfAvg)

  // Calculate mean
  const mean = weeklyData.reduce((sum, w) => sum + w[config.dataKey], 0) / weeklyData.length || 0

  const hasData = weeklyData.length > 0

  if (loading) {
    return (
      <Card className="mb-6">
        <CardContent className="flex items-center justify-center h-[400px]">
          <div className="text-center">
            <div className="animate-spin w-6 h-6 border-2 border-purple-600 border-t-transparent rounded-full mx-auto mb-2" />
            <p className="text-sm text-neutral-500">Loading trends...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="mb-6">
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-1.5">
          <div className="flex items-center gap-3">
            <CardTitle>Team Trends</CardTitle>
            {hasData && (
              <div className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${
                overallTrend.direction === 'down' ? 'bg-green-100 text-green-700' :
                overallTrend.direction === 'up' ? 'bg-red-100 text-red-700' :
                'bg-neutral-100 text-neutral-600'
              }`}>
                {overallTrend.direction === 'down' ? (
                  <TrendingDown className="w-3 h-3" />
                ) : overallTrend.direction === 'up' ? (
                  <TrendingUp className="w-3 h-3" />
                ) : (
                  <Minus className="w-3 h-3" />
                )}
                {overallTrend.direction === 'stable' ? 'Stable' :
                 overallTrend.direction === 'down' ? 'Improving' : 'Needs Attention'}
              </div>
            )}
          </div>
          <CardDescription>
            {hasData
              ? `Weekly averages over ${weeklyData.length} weeks. Mean: ${Math.round(mean)} ${config.label.toLowerCase()}.`
              : "No data available"
            }
          </CardDescription>
        </div>

        <div className="flex items-center space-x-2">
          {selectedMetric === 'health_score' && (
            <label className="flex items-center gap-2 text-sm text-neutral-600 cursor-pointer">
              <input
                type="checkbox"
                checked={showIncidentOverlay}
                onChange={(e) => setShowIncidentOverlay(e.target.checked)}
                className="rounded border-neutral-300"
              />
              Show incidents
            </label>
          )}
          <Select value={selectedMetric} onValueChange={setSelectedMetric}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(METRIC_CONFIG).map(([key, value]: [string, any]) => (
                <SelectItem key={key} value={key}>
                  {value.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>

      <CardContent className="pb-6">
        {!hasData ? (
          <div className="flex items-center justify-center h-[300px]">
            <p className="text-sm text-neutral-500">Run an analysis to view trends</p>
          </div>
        ) : (
          <>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={weeklyData}
                  margin={{ top: 20, right: 30, left: 0, bottom: 5 }}
                >
                  <XAxis
                    dataKey="weekLabel"
                    tick={{ fontSize: 11, fill: '#6B7280' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    yAxisId="left"
                    tick={{ fontSize: 11, fill: '#6B7280' }}
                    axisLine={false}
                    tickLine={false}
                    label={{
                      value: config.yAxisLabel,
                      angle: -90,
                      position: 'insideLeft',
                      style: { fontSize: '11px', fill: '#6B7280' }
                    }}
                  />
                  {showIncidentOverlay && selectedMetric === 'health_score' && (
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tick={{ fontSize: 11, fill: '#F59E0B' }}
                      axisLine={false}
                      tickLine={false}
                      label={{
                        value: 'Incidents',
                        angle: 90,
                        position: 'insideRight',
                        style: { fontSize: '11px', fill: '#F59E0B' }
                      }}
                    />
                  )}
                  <ReferenceLine
                    yAxisId="left"
                    y={mean}
                    stroke="#9C84E8"
                    strokeDasharray="5 5"
                    label={{
                      value: `Mean: ${Math.round(mean)}`,
                      position: 'right',
                      style: { fontSize: '10px', fill: '#9C84E8' }
                    }}
                  />
                  <Tooltip
                    content={({ payload }) => {
                      if (!payload || payload.length === 0) return null
                      const data = payload[0]?.payload
                      return (
                        <div className="bg-neutral-900/95 p-3 border border-neutral-700 rounded-lg shadow-lg">
                          <p className="text-sm font-medium text-neutral-300 mb-2">{data?.weekRange}</p>
                          <p className="text-lg font-bold text-white mb-1">
                            {data?.[config.dataKey]} {config.label}
                          </p>
                          {showIncidentOverlay && selectedMetric === 'health_score' && (
                            <p className="text-sm text-amber-400">
                              {data?.incidentCount} incidents this week
                            </p>
                          )}
                          <p className="text-xs text-neutral-400 mt-1">
                            Based on {data?.daysInWeek} days of data
                          </p>
                        </div>
                      )
                    }}
                  />
                  <Bar
                    yAxisId="left"
                    dataKey={config.dataKey}
                    fill="#7C63D6"
                    radius={[4, 4, 0, 0]}
                    maxBarSize={50}
                  />
                  {showIncidentOverlay && selectedMetric === 'health_score' && (
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="incidentCount"
                      stroke="#F59E0B"
                      strokeWidth={2}
                      dot={{ fill: '#F59E0B', r: 4 }}
                      name="Incidents"
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            {/* Legend */}
            <div className="flex items-center justify-center gap-6 mt-2 text-sm text-neutral-600">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-purple-600"></div>
                <span>{config.label}</span>
              </div>
              {showIncidentOverlay && selectedMetric === 'health_score' && (
                <div className="flex items-center gap-2">
                  <div className="w-4 h-0.5 bg-amber-500"></div>
                  <span>Incidents</span>
                </div>
              )}
              <div className="flex items-center gap-2">
                <div className="w-4 h-0.5 bg-purple-400 border-dashed"></div>
                <span>Mean</span>
              </div>
            </div>

            {/* Week-over-Week Comparison */}
            <WeekOverWeekComparison weeklyData={weeklyData} metric={selectedMetric} />
          </>
        )}
      </CardContent>
    </Card>
  )
}
