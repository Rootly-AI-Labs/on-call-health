"use client"

import { useState } from "react"
import type { ReactElement } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Area,
  AreaChart,
  Bar,
  ComposedChart,
  XAxis,
  YAxis,
  Line,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from "recharts"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Info, TrendingUp, TrendingDown, Minus } from "lucide-react"

interface ObjectiveDataCardProps {
  currentAnalysis: any
  loadingTrends: boolean
}

// Aggregate daily data into weekly buckets
function aggregateToWeekly(dailyData: any[]): any[] {
  if (!dailyData || dailyData.length === 0) return []

  const weeklyBuckets: Map<string, any[]> = new Map()

  dailyData.forEach((day) => {
    const date = new Date(day.date)
    const dayOfWeek = date.getDay()
    const monday = new Date(date)
    monday.setDate(date.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1))
    const weekKey = monday.toISOString().split('T')[0]

    if (!weeklyBuckets.has(weekKey)) {
      weeklyBuckets.set(weekKey, [])
    }
    weeklyBuckets.get(weekKey)!.push(day)
  })

  const weeklyData = Array.from(weeklyBuckets.entries())
    .map(([weekStart, days]) => {
      const avgRiskLevel = days.reduce((sum, d) => sum + Math.max(0, Math.min(100, 100 - Math.round((d.overall_score || 0) * 10))), 0) / days.length
      const totalIncidents = days.reduce((sum, d) => sum + (d.incident_count || 0), 0)
      const avgAfterHours = days.reduce((sum, d) => sum + (d.after_hours_percentage || 0), 0) / days.length
      const avgSeverityWeighted = days.reduce((sum, d) => sum + (d.severity_weighted_count || 0), 0) / days.length
      const totalAfterHoursCount = days.reduce((sum, d) => sum + (d.after_hours_count || 0), 0)
      const totalHighSeverity = days.reduce((sum, d) => sum + (d.high_severity_count || 0), 0)

      const teamSize = days[0]?.total_members || 1
      const incidentPenalty = Math.min((totalIncidents / days.length / teamSize) * 0.8, 2.0)
      const severityPenalty = Math.min((avgSeverityWeighted / teamSize) * 1.2, 3.0)
      const afterHoursPenalty = Math.min((totalAfterHoursCount / days.length) * 0.5, 1.5)
      const highSeverityPenalty = Math.min((totalHighSeverity / days.length) * 0.8, 2.0)

      const totalPenalty = incidentPenalty + severityPenalty + afterHoursPenalty + highSeverityPenalty

      const factors = totalPenalty > 0 ? {
        incidents: Math.round((incidentPenalty / totalPenalty) * 100),
        severity: Math.round((severityPenalty / totalPenalty) * 100),
        afterHours: Math.round((afterHoursPenalty / totalPenalty) * 100),
        highSeverity: Math.round((highSeverityPenalty / totalPenalty) * 100),
      } : { incidents: 0, severity: 0, afterHours: 0, highSeverity: 0 }

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
        factors,
        daysInWeek: days.length
      }
    })
    .sort((a, b) => a.weekStart.localeCompare(b.weekStart))

  return weeklyData
}

function calculateTrend(current: number, previous: number): { direction: 'up' | 'down' | 'stable', percentage: number } {
  if (previous === 0) return { direction: 'stable', percentage: 0 }
  const change = ((current - previous) / previous) * 100
  if (Math.abs(change) < 5) return { direction: 'stable', percentage: Math.round(change) }
  return {
    direction: change > 0 ? 'up' : 'down',
    percentage: Math.round(Math.abs(change))
  }
}

export function ObjectiveDataCard({
  currentAnalysis,
  loadingTrends
}: ObjectiveDataCardProps) {
  const [selectedMetric, setSelectedMetric] = useState<string>("health_score")
  const [viewMode, setViewMode] = useState<'weekly' | 'daily'>('weekly')

  const METRIC_CONFIG: any = {
    health_score: {
      label: "Risk Level",
      color: "#7C63D6",
      yAxisLabel: "Risk Level",
      dataKey: "dailyScore",
      weeklyDataKey: "riskLevel",
      showMeanLine: true,
      transformer: (trend: any) => Math.max(0, Math.min(100, 100 - Math.round(trend.overall_score * 10)))
    },
    incident_load: {
      label: "Incident Count",
      color: "#7C63D6",
      yAxisLabel: "Incident Count",
      dataKey: "incidentCount",
      weeklyDataKey: "incidentCount",
      showMeanLine: true,
      transformer: (trend: any) => trend.incident_count || 0
    },
    after_hours: {
      label: "After Hours Activity",
      color: "#7C63D6",
      yAxisLabel: "After Hours Activity %",
      dataKey: "afterHoursPercentage",
      weeklyDataKey: "afterHoursPercentage",
      showMeanLine: true,
      transformer: (trend: any) => trend.after_hours_percentage || 0
    },
    severity_weighted: {
      label: "Workload Intensity",
      color: "#7C63D6",
      yAxisLabel: "Severity-Weighted Load",
      dataKey: "severityWeightedCount",
      weeklyDataKey: "severityWeighted",
      showMeanLine: true,
      transformer: (trend: any) => Math.round(trend.severity_weighted_count || 0)
    }
  }

  const METRIC_DESCRIPTIONS: any = {
    health_score: {
      title: "Risk Level",
      description: "Measures the team's overall on-call health based on factors such as incident frequency, after-hours work and severity. Higher scores indicate higher risk of overwork."
    },
    incident_load: {
      title: "Incident Count",
      description: "Total count of incidents handled per day. Counts all incidents regardless of severity or timing."
    },
    after_hours: {
      title: "After Hours Activity",
      description: "Incidents occurring outside business hours (before 9 AM or after 5 PM) or on weekends. Timezone-aware based on each team member's local time."
    },
    severity_weighted: {
      title: "Workload Intensity",
      description: "Measures workload stress by weighting incidents based on their severity level. Higher values indicate more stressful workload."
    }
  }

  const dailyTrends = currentAnalysis?.analysis_data?.daily_trends || []
  const timeRange = currentAnalysis?.time_range || currentAnalysis?.analysis_data?.metadata?.days_analyzed || 30
  const config = METRIC_CONFIG[selectedMetric]

  // Daily chart data
  const getDailyChartData = () => {
    if (!dailyTrends || dailyTrends.length === 0) return []

    const chartData = dailyTrends.map((trend: any) => ({
      date: new Date(trend.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      [config.dataKey]: config.transformer(trend),
      incidentCount: trend.incident_count || 0,
      afterHours: trend.after_hours_count || 0,
    }))

    const values = chartData.map((d: any) => d[config.dataKey])
    const mean = values.length > 0 ? values.reduce((a: number, b: number) => a + b, 0) / values.length : 0

    return chartData.map((d: any) => ({ ...d, meanScore: Math.round(mean) }))
  }

  // Weekly chart data
  const weeklyData = aggregateToWeekly(dailyTrends)
  const weeklyMean = weeklyData.length > 0
    ? weeklyData.reduce((sum, w) => sum + w[config.weeklyDataKey], 0) / weeklyData.length
    : 0

  // Calculate overall trend for weekly view
  const halfIndex = Math.floor(weeklyData.length / 2)
  const firstHalfAvg = weeklyData.slice(0, halfIndex).reduce((sum, w) => sum + w[config.weeklyDataKey], 0) / halfIndex || 0
  const secondHalfAvg = weeklyData.slice(halfIndex).reduce((sum, w) => sum + w[config.weeklyDataKey], 0) / (weeklyData.length - halfIndex) || 0
  const overallTrend = calculateTrend(secondHalfAvg, firstHalfAvg)

  // Week-over-week comparison
  const currentWeek = weeklyData[weeklyData.length - 1]
  const previousWeek = weeklyData[weeklyData.length - 2]
  const vsLastWeek = currentWeek && previousWeek
    ? calculateTrend(currentWeek[config.weeklyDataKey], previousWeek[config.weeklyDataKey])
    : null
  const vsMean = currentWeek
    ? calculateTrend(currentWeek[config.weeklyDataKey], weeklyMean)
    : null

  const dailyChartData = getDailyChartData()
  const hasData = viewMode === 'weekly' ? weeklyData.length > 0 : dailyChartData.length > 0

  const dailyMean = dailyChartData.length > 0 ? dailyChartData[0]?.meanScore : 0
  const description = hasData
    ? viewMode === 'weekly'
      ? `Weekly averages over ${weeklyData.length} weeks. Mean: ${Math.round(weeklyMean)} ${config.label.toLowerCase()}.`
      : `Over the last ${timeRange} days, the average ${config.yAxisLabel.toLowerCase()} was ${Math.round(dailyMean)} points.`
    : "No trend data available for this analysis"

  if (loadingTrends) {
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
            {viewMode === 'weekly' && hasData && (
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
          <CardDescription>{description}</CardDescription>
        </div>

        <div className="flex items-center space-x-2">
          {/* View Toggle */}
          <div className="flex items-center bg-neutral-100 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('weekly')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                viewMode === 'weekly'
                  ? 'bg-white text-neutral-900 shadow-sm'
                  : 'text-neutral-500 hover:text-neutral-700'
              }`}
            >
              Weekly
            </button>
            <button
              onClick={() => setViewMode('daily')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                viewMode === 'daily'
                  ? 'bg-white text-neutral-900 shadow-sm'
                  : 'text-neutral-500 hover:text-neutral-700'
              }`}
            >
              Daily
            </button>
          </div>

          {/* Info tooltip */}
          <div className="relative group">
            <Info className="w-4 h-4 text-neutral-500 cursor-help hover:text-neutral-700 transition-colors" />
            <div className="absolute top-full right-0 mt-2 px-3 py-2 bg-neutral-900/95 text-white text-xs rounded-lg w-64 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
              <div className="font-semibold mb-1">{METRIC_DESCRIPTIONS[selectedMetric].title}</div>
              <div>{METRIC_DESCRIPTIONS[selectedMetric].description}</div>
            </div>
          </div>

          {/* Metric selector */}
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
            <div className="text-center">
              <div className="w-12 h-12 bg-neutral-200 rounded-full flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <p className="text-sm text-neutral-500 font-medium">No Data Available</p>
              <p className="text-xs text-neutral-500 mt-1">Run an analysis to view trends</p>
            </div>
          </div>
        ) : viewMode === 'weekly' ? (
          <>
            {/* Weekly Bar Chart */}
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
                  />
                  {selectedMetric === 'health_score' && (
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tick={{ fontSize: 11, fill: '#F59E0B' }}
                      axisLine={false}
                      tickLine={false}
                    />
                  )}
                  <ReferenceLine
                    yAxisId="left"
                    y={weeklyMean}
                    stroke="#9C84E8"
                    strokeDasharray="5 5"
                  />
                  <Tooltip
                    content={({ payload }) => {
                      if (!payload || payload.length === 0) return null
                      const data = payload[0]?.payload
                      const factors = data?.factors || {}
                      const hasFactors = factors.incidents > 0 || factors.severity > 0 || factors.afterHours > 0 || factors.highSeverity > 0

                      return (
                        <div className="bg-neutral-900/95 p-3 border border-neutral-700 rounded-lg shadow-lg min-w-[200px]">
                          <p className="text-sm font-medium text-neutral-300 mb-2">{data?.weekRange}</p>
                          <p className="text-lg font-bold text-white mb-1">
                            {data?.[config.weeklyDataKey]} {config.label}
                          </p>
                          {selectedMetric === 'health_score' && (
                            <p className="text-sm text-amber-400 mb-2">
                              {data?.incidentCount} incidents this week
                            </p>
                          )}
                          {selectedMetric === 'health_score' && hasFactors && (
                            <div className="border-t border-neutral-700 pt-2 mt-2">
                              <p className="text-xs text-neutral-400 mb-1.5">Risk breakdown:</p>
                              <div className="space-y-1">
                                {[
                                  { key: 'severity', label: 'Severity impact', value: factors.severity },
                                  { key: 'incidents', label: 'Incident volume', value: factors.incidents },
                                  { key: 'highSeverity', label: 'High severity', value: factors.highSeverity },
                                  { key: 'afterHours', label: 'After hours', value: factors.afterHours },
                                ]
                                  .filter(f => f.value > 0)
                                  .sort((a, b) => b.value - a.value)
                                  .map(factor => (
                                    <div key={factor.key} className="flex justify-between text-xs">
                                      <span className="text-neutral-400">{factor.label}</span>
                                      <span className="text-white font-medium">{factor.value}%</span>
                                    </div>
                                  ))
                                }
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    }}
                  />
                  <Bar
                    yAxisId="left"
                    dataKey={config.weeklyDataKey}
                    fill="#7C63D6"
                    radius={[4, 4, 0, 0]}
                    maxBarSize={50}
                  />
                  {selectedMetric === 'health_score' && (
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="incidentCount"
                      stroke="#F59E0B"
                      strokeWidth={2}
                      dot={{ fill: '#F59E0B', r: 4 }}
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
              {selectedMetric === 'health_score' && (
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
            {currentWeek && (
              <div className="mt-4 flex items-center justify-center gap-6 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-neutral-500">This week:</span>
                  <span className="font-semibold text-neutral-900">{currentWeek[config.weeklyDataKey]}</span>
                </div>
                {vsLastWeek && (
                  <div className="flex items-center gap-2">
                    <span className="text-neutral-500">vs last week:</span>
                    <span className={`font-medium ${vsLastWeek.direction === 'down' ? 'text-green-600' : vsLastWeek.direction === 'up' ? 'text-red-600' : 'text-neutral-500'}`}>
                      {vsLastWeek.direction === 'stable' ? '—' : `${vsLastWeek.direction === 'down' ? '↓' : '↑'}${vsLastWeek.percentage}%`}
                    </span>
                  </div>
                )}
                {vsMean && (
                  <div className="flex items-center gap-2">
                    <span className="text-neutral-500">vs mean:</span>
                    <span className={`font-medium ${vsMean.direction === 'down' ? 'text-green-600' : vsMean.direction === 'up' ? 'text-red-600' : 'text-neutral-500'}`}>
                      {vsMean.direction === 'stable' ? '—' : `${vsMean.direction === 'down' ? '↓' : '↑'}${vsMean.percentage}%`}
                    </span>
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <>
            {/* Daily Area Chart */}
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={dailyChartData}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="purpleGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#7C63D6" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#7C63D6" stopOpacity={0.01} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="date"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 10, fill: '#6B7280' }}
                    angle={-45}
                    textAnchor="end"
                    height={50}
                    interval={Math.floor(dailyChartData.length / 7) || 0}
                  />
                  <YAxis hide={selectedMetric === 'health_score'} />
                  <Tooltip
                    content={({ payload }) => {
                      if (!payload || payload.length === 0) return null
                      const data = payload[0]?.payload
                      const metricValue = data?.[config.dataKey] || 0
                      const meanScore = data?.meanScore || 0
                      const percentageChange = meanScore !== 0 ? ((metricValue - meanScore) / meanScore) * 100 : 0
                      const isPositive = percentageChange <= 0

                      return (
                        <div className="bg-neutral-900/95 p-3 border border-neutral-700 rounded-lg shadow-lg">
                          <p className="text-sm font-medium text-neutral-300 mb-2">{data?.date}</p>
                          <p className={`text-base font-bold mb-2 ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                            {percentageChange >= 0 ? '↑' : '↓'} {Math.abs(percentageChange).toFixed(1)}%
                          </p>
                          <p className="text-sm text-neutral-300">
                            {config.label}: <span className="font-semibold">{metricValue}</span>
                          </p>
                          <p className="text-xs text-neutral-400 mt-1">Mean: {meanScore}</p>
                        </div>
                      )
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey={config.dataKey}
                    stroke={config.color}
                    strokeWidth={2}
                    fill="url(#purpleGradient)"
                    dot={false}
                  />
                  {config.showMeanLine && (
                    <Line
                      type="monotone"
                      dataKey="meanScore"
                      stroke="#9C84E8"
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      dot={false}
                    />
                  )}
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Legend */}
            <div className="mt-4 flex items-center justify-start space-x-6 text-sm text-neutral-700">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: config.color }}></div>
                <span>{config.label}</span>
              </div>
              {config.showMeanLine && (
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-0.5 bg-purple-500 border-dashed"></div>
                  <span>Mean</span>
                </div>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
