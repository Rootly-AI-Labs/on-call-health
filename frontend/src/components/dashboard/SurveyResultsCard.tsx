"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { TrendingUp, TrendingDown, Minus, MessageSquare } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"

interface SurveyResponse {
  feeling_score: number
  workload_score: number
  combined_score: number
  submitted_at: string
  stress_factors?: string[]
  personal_circumstances?: string
  additional_comments?: string
  submitted_via?: string
}

interface SurveyData {
  survey_count_in_period: number
  latest_feeling_score: number
  latest_workload_score: number
  latest_combined_score: number
  trend: 'improving' | 'stable' | 'declining'
  survey_responses: SurveyResponse[]
}

interface SurveyResultsCardProps {
  surveyData: SurveyData | null
  userEmail: string
}

const getScoreColor = (score: number) => {
  if (score >= 4) return 'text-green-600'
  if (score >= 3) return 'text-yellow-600'
  if (score >= 2) return 'text-orange-600'
  return 'text-red-600'
}

const getScoreBadgeColor = (score: number) => {
  if (score >= 4) return 'bg-green-100 text-green-800'
  if (score >= 3) return 'bg-orange-500 text-white'
  if (score >= 2) return 'bg-orange-700 text-white'
  return 'bg-orange-900 text-white'
}

const getTrendIcon = (trend: string) => {
  if (trend === 'improving') return <TrendingUp className="w-4 h-4 text-green-500" />
  if (trend === 'declining') return <TrendingDown className="w-4 h-4 text-red-500" />
  return <Minus className="w-4 h-4 text-neutral-500" />
}

const getFeelingText = (score: number) => {
  if (score === 5) return 'Very good'
  if (score === 4) return 'Good'
  if (score === 3) return 'Okay'
  if (score === 2) return 'Not great'
  return 'Struggling'
}

const getWorkloadText = (score: number) => {
  if (score === 5) return 'Very manageable'
  if (score === 4) return 'Manageable'
  if (score === 3) return 'Moderate'
  if (score === 2) return 'Heavy'
  return 'Overwhelming'
}

const getStressSourceLabel = (source: string) => {
  const labels: { [key: string]: string } = {
    'oncall_frequency': 'On-call frequency',
    'after_hours': 'After-hours incidents',
    'incident_complexity': 'Incident complexity',
    'time_pressure': 'Time pressure',
    'team_support': 'Team support',
    'work_life_balance': 'Work-life balance',
    'personal': 'Personal',
    'other': 'Other',
    // Legacy labels (for backwards compatibility)
    'lack_support': 'Lack of support',
    'context_switches': 'Context switches',
    'unclear_expectations': 'Unclear expectations'
  }
  return labels[source] || source
}

export function SurveyResultsCard({ surveyData, userEmail }: SurveyResultsCardProps) {
  if (!surveyData || surveyData.survey_count_in_period === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Health Check-ins</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500">No survey responses in this analysis period</p>
        </CardContent>
      </Card>
    )
  }

  const latestResponse = surveyData.survey_responses[surveyData.survey_responses.length - 1]
  const previousResponse = surveyData.survey_responses.length > 1
    ? surveyData.survey_responses[surveyData.survey_responses.length - 2]
    : null

  // Prepare chart data
  const chartData = surveyData.survey_responses.map((response) => ({
    date: new Date(response.submitted_at).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric'
    }),
    feeling: response.feeling_score,
    workload: response.workload_score
  }))

  // Calculate baseline averages
  const avgFeeling = surveyData.survey_responses.reduce((sum, r) => sum + r.feeling_score, 0) / surveyData.survey_responses.length
  const avgWorkload = surveyData.survey_responses.reduce((sum, r) => sum + r.workload_score, 0) / surveyData.survey_responses.length

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Health Check-ins</CardTitle>
          <div className="flex items-center gap-2">
            {getTrendIcon(surveyData.trend)}
            <span className="text-xs text-neutral-500 capitalize">{surveyData.trend}</span>
          </div>
        </div>
        <CardDescription>
          {surveyData.survey_count_in_period} {surveyData.survey_count_in_period === 1 ? 'response' : 'responses'} in analysis period
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Trend Chart */}
        {surveyData.survey_responses.length > 2 && (
          <div className="space-y-2">
            <div className="text-xs font-medium text-neutral-700">Score Trends</div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  stroke="#737373"
                />
                <YAxis
                  domain={[0, 5]}
                  ticks={[1, 2, 3, 4, 5]}
                  tick={{ fontSize: 11 }}
                  stroke="#737373"
                />
                <Tooltip
                  contentStyle={{
                    fontSize: '12px',
                    backgroundColor: 'white',
                    border: '1px solid #e5e5e5',
                    borderRadius: '6px'
                  }}
                />
                <ReferenceLine
                  y={avgFeeling}
                  stroke="#3b82f6"
                  strokeDasharray="5 5"
                  strokeOpacity={0.3}
                  label={{
                    value: `Avg Feeling: ${avgFeeling.toFixed(1)}`,
                    fontSize: 10,
                    fill: '#3b82f6',
                    position: 'insideTopRight'
                  }}
                />
                <ReferenceLine
                  y={avgWorkload}
                  stroke="#8b5cf6"
                  strokeDasharray="5 5"
                  strokeOpacity={0.3}
                  label={{
                    value: `Avg Workload: ${avgWorkload.toFixed(1)}`,
                    fontSize: 10,
                    fill: '#8b5cf6',
                    position: 'insideBottomRight'
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="feeling"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6', r: 3 }}
                  name="Feeling"
                />
                <Line
                  type="monotone"
                  dataKey="workload"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={{ fill: '#8b5cf6', r: 3 }}
                  name="Workload"
                />
              </LineChart>
            </ResponsiveContainer>
            <div className="flex items-center justify-center gap-4 text-xs">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                <span className="text-neutral-600">Feeling</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                <span className="text-neutral-600">Workload</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-0.5 bg-neutral-400"></div>
                <span className="text-neutral-600">Average</span>
              </div>
            </div>
          </div>
        )}

        {/* Latest Response */}
        <div className="space-y-4 p-3 bg-neutral-50 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-neutral-700">Latest Check-in</span>
            <span className="text-xs text-neutral-500">
              {new Date(latestResponse.submitted_at).toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
                timeZoneName: 'short'
              })} via {latestResponse.submitted_via || 'web'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <span className="text-xs text-neutral-500">How they're feeling</span>
              <div className="flex items-center gap-2">
                <Badge className={getScoreBadgeColor(latestResponse.feeling_score)}>
                  {latestResponse.feeling_score}/5
                </Badge>
                <span className="text-sm font-medium">{getFeelingText(latestResponse.feeling_score)}</span>
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-xs text-neutral-500">Workload</span>
              <div className="flex items-center gap-2">
                <Badge className={getScoreBadgeColor(latestResponse.workload_score)}>
                  {latestResponse.workload_score}/5
                </Badge>
                <span className="text-sm font-medium">{getWorkloadText(latestResponse.workload_score)}</span>
              </div>
            </div>
          </div>

          {latestResponse.stress_factors && latestResponse.stress_factors.length > 0 && (
            <div>
              <div className="text-xs font-medium text-neutral-700 mb-2">Stress Sources</div>
              <div className="flex flex-wrap gap-1">
                {latestResponse.stress_factors.map((factor, index) => (
                  <Badge key={index} variant="outline" className="text-xs">
                    {getStressSourceLabel(factor)}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {latestResponse.personal_circumstances && (
            <div>
              <div className="text-xs font-medium text-neutral-700 mb-1">Personal Circumstances Impact</div>
              <p className="text-sm text-neutral-700">{latestResponse.personal_circumstances}</p>
            </div>
          )}

          {latestResponse.additional_comments && (
            <div>
              <div className="flex items-center gap-1 text-xs font-medium text-neutral-700 mb-1">
                <MessageSquare className="w-3 h-3" />
                <span>Comments</span>
              </div>
              <p className="text-sm text-neutral-700">{latestResponse.additional_comments}</p>
            </div>
          )}
        </div>

        {/* Response History */}
        {surveyData.survey_responses.length > 1 && (
          <>
            <Separator />
            <div>
              <div className="text-xs font-medium text-neutral-700 mb-3">Previous Check-ins</div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {surveyData.survey_responses.slice().reverse().slice(1).map((response, index) => (
                  <div key={index} className="flex items-center justify-between text-sm py-2 border-b last:border-0">
                    <span className="text-xs text-neutral-500">
                      {new Date(response.submitted_at).toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit'
                      })}
                    </span>
                    <div className="flex gap-4 text-xs">
                      <span className={getScoreColor(response.feeling_score)}>
                        Feeling: {response.feeling_score}/5
                      </span>
                      <span className={getScoreColor(response.workload_score)}>
                        Workload: {response.workload_score}/5
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
