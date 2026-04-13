"use client"

import { useState, useRef, useMemo } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Bot, TrendingUp, TrendingDown, Minus } from "lucide-react"

interface AIUsageCardProps {
  currentAnalysis: any
}

// DailyUsage shape from backend: { "2025-03-01": { input_tokens, output_tokens, total_tokens, requests } }
type DailyEntry = { input_tokens: number; output_tokens: number; total_tokens: number; requests: number }
type UsageData = Record<string, DailyEntry>

// ------------------------------------------------------------------ //
//  Helpers
// ------------------------------------------------------------------ //

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

function formatDate(iso: string): string {
  const d = new Date(iso + "T00:00:00Z")
  return d.toLocaleDateString([], { month: "short", day: "numeric" })
}

function buildSortedDays(usage: UsageData): string[] {
  return Object.keys(usage).sort()
}

function sumUsage(usage: UsageData): DailyEntry {
  const out = { input_tokens: 0, output_tokens: 0, total_tokens: 0, requests: 0 }
  for (const v of Object.values(usage)) {
    out.input_tokens += v.input_tokens
    out.output_tokens += v.output_tokens
    out.total_tokens += v.total_tokens
    out.requests += v.requests
  }
  return out
}

function computeTrend(usage: UsageData, days: number): number | null {
  const sorted = buildSortedDays(usage)
  if (sorted.length < 2) return null
  const recent = sorted.slice(-days)
  const prior = sorted.slice(-days * 2, -days)
  if (prior.length === 0) return null
  const recentTotal = recent.reduce((s, d) => s + (usage[d]?.total_tokens ?? 0), 0)
  const priorTotal = prior.reduce((s, d) => s + (usage[d]?.total_tokens ?? 0), 0)
  if (priorTotal === 0) return null
  return Math.round(((recentTotal - priorTotal) / priorTotal) * 100)
}

// ------------------------------------------------------------------ //
//  Sparkline SVG
// ------------------------------------------------------------------ //

const CHART_H = 64
const CHART_PADDING_Y = 4

function AISparkline({
  usage,
  days,
  metric,
  color,
}: {
  usage: UsageData
  days: string[]
  metric: keyof DailyEntry
  color: string
}) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  const values = days.map(d => usage[d]?.[metric] ?? 0)
  const maxVal = Math.max(...values, 1)

  const W = 400
  const stepX = W / Math.max(days.length - 1, 1)

  function ptX(i: number) { return i * stepX }
  function ptY(v: number) { return CHART_H - CHART_PADDING_Y - ((v / maxVal) * (CHART_H - CHART_PADDING_Y * 2)) }

  const pathD = values.map((v, i) => `${i === 0 ? "M" : "L"}${ptX(i)},${ptY(v)}`).join(" ")
  const hoverEntry = hoverIdx !== null ? { day: days[hoverIdx], val: values[hoverIdx] } : null

  return (
    <div className="relative w-full" style={{ height: CHART_H }}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${CHART_H}`}
        preserveAspectRatio="none"
        className="w-full h-full"
        onMouseMove={(e) => {
          const rect = svgRef.current!.getBoundingClientRect()
          const x = ((e.clientX - rect.left) / rect.width) * W
          const idx = Math.round(x / stepX)
          setHoverIdx(Math.min(Math.max(idx, 0), days.length - 1))
        }}
        onMouseLeave={() => setHoverIdx(null)}
      >
        <defs>
          <linearGradient id="aiGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.15" />
            <stop offset="100%" stopColor={color} stopOpacity="0.01" />
          </linearGradient>
        </defs>
        {values.length > 1 && (
          <path
            d={`${pathD} L${ptX(values.length - 1)},${CHART_H} L0,${CHART_H} Z`}
            fill="url(#aiGrad)"
          />
        )}
        <path d={pathD} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
        {hoverIdx !== null && (
          <circle cx={ptX(hoverIdx)} cy={ptY(values[hoverIdx])} r="3" fill={color} />
        )}
      </svg>

      {hoverEntry && (
        <div className="absolute top-0 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
          <div className="bg-neutral-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap shadow-lg">
            <div className="font-medium text-neutral-300">{formatDate(hoverEntry.day)}</div>
            <div className="font-semibold">{formatTokens(hoverEntry.val)}</div>
          </div>
        </div>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ //
//  Main card
// ------------------------------------------------------------------ //

export function AIUsageCard({ currentAnalysis }: AIUsageCardProps) {
  const [activeMetric, setActiveMetric] = useState<keyof DailyEntry>("total_tokens")

  // ai_usage key present → feature was enabled for this analysis (show card)
  // ai_usage key absent → feature wasn't connected/enabled (hide card entirely)
  const metadata = currentAnalysis?.analysis_data?.metadata
  const aiUsageEnabled = metadata !== undefined && "ai_usage" in metadata
  const usage: UsageData = useMemo(() => {
    return (metadata?.ai_usage as UsageData | undefined) ?? {}
  }, [metadata])

  const days = useMemo(() => buildSortedDays(usage), [usage])
  const totals = useMemo(() => sumUsage(usage), [usage])
  const trend = useMemo(() => computeTrend(usage, 7), [usage])

  if (!aiUsageEnabled) return null

  if (Object.keys(usage).length === 0) {
    return (
      <div>
        <Card className="bg-white flex flex-col">
          <CardHeader className="pb-2 shrink-0">
            <div className="space-y-1">
              <CardTitle className="text-neutral-900">Team AI Usage</CardTitle>
              <CardDescription>Past {currentAnalysis?.time_range ?? 30} days of token consumption from OpenAI and/or Anthropic</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-neutral-500">
              No usage data returned from your AI provider for this time period. This is expected if your team hasn't made any API calls yet, or if usage occurred outside the selected date range.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const metricOptions: { key: keyof DailyEntry; label: string; color: string }[] = [
    { key: "total_tokens",  label: "Total tokens",  color: "#6366f1" },
    { key: "input_tokens",  label: "Input tokens",  color: "#3b82f6" },
    { key: "output_tokens", label: "Output tokens", color: "#10b981" },
    { key: "requests",      label: "Requests",      color: "#f97316" },
  ]

  const activeConfig = metricOptions.find(m => m.key === activeMetric)!

  const TrendIcon = trend === null ? Minus : trend > 0 ? TrendingUp : TrendingDown
  const trendColor = trend === null ? "text-neutral-400" : trend > 0 ? "text-green-600" : "text-red-500"

  return (
    <div>
      <Card className="bg-white flex flex-col">
        <CardHeader className="pb-2 shrink-0">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <CardTitle className="text-neutral-900">Team AI Usage</CardTitle>
            </div>
            <CardDescription>Past {currentAnalysis?.time_range ?? days.length} days of token consumption from OpenAI and/or Anthropic</CardDescription>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Metric selector tiles */}
          <div className="grid grid-cols-4 gap-3">
            {metricOptions.map(m => (
              <button
                key={m.key}
                onClick={() => setActiveMetric(m.key)}
                className={`rounded-lg p-2.5 text-left transition-colors border ${
                  activeMetric === m.key
                    ? "border-neutral-300 bg-neutral-50"
                    : "border-neutral-200 bg-white hover:border-neutral-300"
                }`}
              >
                <div className="text-xs text-neutral-400 mb-0.5">{m.label}</div>
                <div
                  className="text-base font-bold"
                  style={{ color: activeMetric === m.key ? m.color : "#171717" }}
                >
                  {formatTokens(totals[m.key])}
                </div>
              </button>
            ))}
          </div>

          {/* Trend */}
          {trend !== null && (
            <div className="flex items-center gap-1.5 text-xs">
              <TrendIcon className={`h-3.5 w-3.5 ${trendColor}`} />
              <span className={trendColor}>
                {trend > 0 ? "+" : ""}{trend}% vs prior 7 days
              </span>
            </div>
          )}

          {/* Sparkline */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-neutral-400">{activeConfig.label} / day</span>
            </div>
            <AISparkline usage={usage} days={days} metric={activeMetric} color={activeConfig.color} />
            <div className="flex justify-between mt-1">
              <span className="text-xs text-neutral-300">{days[0] ? formatDate(days[0]) : ""}</span>
              <span className="text-xs text-neutral-300">{days[days.length - 1] ? formatDate(days[days.length - 1]) : ""}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
