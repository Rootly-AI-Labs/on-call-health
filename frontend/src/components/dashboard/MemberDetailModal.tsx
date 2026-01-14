"use client"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, BarChart, Bar, Cell } from "recharts"
import { Info, RefreshCw, BarChart3 } from "lucide-react"
import { useState, useEffect, useRef } from "react"
import { UserObjectiveDataCard } from "@/components/dashboard/UserObjectiveDataCard"
import { UserRiskFactorsCard } from "@/components/dashboard/UserRiskFactorsCard"
import { SurveyResultsCard } from "@/components/dashboard/SurveyResultsCard"
import { TicketingCard } from "@/components/dashboard/TicketingCard"

// OCB risk level helpers
function getOCBRiskInfo(score: number | undefined | null): { level: string; label: string } {
  if (score === undefined || score === null) {
    return { level: 'unknown', label: 'Unknown Risk' }
  }
  if (score < 25) return { level: 'healthy', label: 'Healthy' }
  if (score < 50) return { level: 'fair', label: 'Fair' }
  if (score < 75) return { level: 'poor', label: 'Poor' }
  return { level: 'critical', label: 'Critical' }
}

function getOCBBadgeColor(level: string): string {
  switch (level) {
    case 'critical': return 'bg-red-100 text-red-800 border-red-300'
    case 'poor': return 'bg-red-50 text-red-600 border-red-200'
    case 'fair': return 'bg-yellow-50 text-yellow-600 border-yellow-200'
    case 'healthy': return 'bg-green-50 text-green-600 border-green-200'
    default: return 'bg-gray-50 text-gray-600 border-gray-200'
  }
}

function getOCBScoreColor(score: number | undefined): string {
  if (score === undefined) return 'text-gray-900'
  if (score < 25) return 'text-green-600'
  if (score < 50) return 'text-yellow-600'
  if (score < 75) return 'text-orange-600'
  return 'text-red-600'
}

// Individual Daily Health Chart component
function IndividualDailyHealthChart({ memberData, analysisId, currentAnalysis }: {
  memberData: any
  analysisId?: number | string
  currentAnalysis?: any
}) {
  const [dailyHealthData, setDailyHealthData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDailyHealth = async () => {
      if (!memberData?.user_email || !analysisId) {
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const url = `${API_BASE}/analyses/${analysisId}/members/${encodeURIComponent(memberData.user_email)}/daily-health`;

        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const result = await response.json();

        if (result.status === 'success' && result.data?.daily_health) {
          const formattedData = result.data.daily_health.map((day: any) => ({
            date: day.date,
            health_score: day.health_score,
            incident_count: day.incident_count,
            team_health: day.team_health,
            day_name: day.day_name || new Date(day.date).toLocaleDateString('en-US', {
              weekday: 'short', month: 'short', day: 'numeric'
            }),
            factors: day.factors,
            has_data: day.has_data !== undefined ? day.has_data : day.incident_count > 0,
            tooltip_summary: day.tooltip_summary
          }));

          setDailyHealthData(formattedData);
        } else {
          setError(result.message || 'No daily health data available');
        }
      } catch (err) {
        console.error('Error fetching daily health:', err);
        setError('No individual daily health data available - this member had no incident involvement during the analysis period');
      } finally {
        setLoading(false);
      }
    };

    fetchDailyHealth();
  }, [memberData?.user_email, analysisId]);

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-neutral-500 mx-auto mb-2" />
          <p className="text-sm text-neutral-700">Loading daily health data...</p>
        </CardContent>
      </Card>
    );
  }

  if (error || !dailyHealthData || dailyHealthData.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-center">
          <BarChart3 className="w-8 h-8 text-neutral-500 mx-auto mb-2" />
          <p className="text-neutral-500 mb-2">{error || 'No daily health data available'}</p>
          <p className="text-sm text-neutral-700">
            Daily health scores are calculated for days when incidents occur
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Daily Health Timeline</CardTitle>
        <CardDescription>
          Individual daily risk level over the analysis period
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="mb-4 flex flex-wrap items-center gap-4 text-xs text-neutral-500">
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-red-500 rounded"></div>
            <span>Critical (75-100)</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-orange-500 rounded"></div>
            <span>Poor (50-74)</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-yellow-500 rounded"></div>
            <span>Fair (25-49)</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-green-500 rounded"></div>
            <span>Healthy (0-24)</span>
          </div>
        </div>

        <div style={{ width: '100%', height: '250px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={dailyHealthData}
              margin={{ top: 20, right: 30, left: 40, bottom: 60 }}
            >
              <XAxis
                dataKey="day_name"
                fontSize={9}
                angle={-45}
                textAnchor="end"
                height={60}
                tick={{ fill: '#6B7280' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[0, 100]}
                fontSize={10}
                tick={{ fill: '#6B7280' }}
                axisLine={false}
                tickLine={false}
                label={{
                  value: 'Health Score',
                  angle: -90,
                  position: 'insideLeft',
                  style: { textAnchor: 'middle', fill: '#6B7280', fontSize: '11px' }
                }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload[0]) {
                    const data = payload[0].payload;
                    if (data.tooltip_summary) {
                      return (
                        <div className="bg-white p-4 border border-neutral-300 rounded-lg shadow-xl text-sm max-w-sm">
                          <div className="whitespace-pre-line text-neutral-900 font-medium leading-relaxed">
                            {data.tooltip_summary}
                          </div>
                          <div className="mt-3 pt-3 border-t border-neutral-300 text-xs">
                            <div className="flex justify-between text-neutral-700 font-semibold">
                              <span>Health Score: {data.health_score}/100</span>
                              <span>Team Avg: {data.team_health}/100</span>
                            </div>
                          </div>
                        </div>
                      );
                    }

                    return (
                      <div className="bg-white p-4 border border-neutral-300 rounded-lg shadow-xl text-sm max-w-xs">
                        <p className="font-bold text-neutral-900 mb-3">{data.day_name}</p>
                        {data.has_data ? (
                          <>
                            <p className="text-blue-700 font-semibold mb-1">Health Score: {data.health_score}/100</p>
                            <p className="text-red-700 font-semibold mb-1">Incidents: {data.incident_count}</p>
                            <p className="text-green-700 font-semibold">Team Average: {data.team_health}/100</p>
                          </>
                        ) : (
                          <>
                            <p className="text-neutral-900 font-semibold">No Incidents</p>
                            <p className="text-neutral-700 text-xs font-medium mt-1">Healthy day - no incident involvement</p>
                          </>
                        )}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar
                dataKey="health_score"
                radius={[4, 4, 0, 0]}
                maxBarSize={40}
              >
                {dailyHealthData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      !entry.has_data ? '#D1D5DB' :
                      entry.health_score >= 75 ? '#EF4444' :
                      entry.health_score >= 50 ? '#F97316' :
                      entry.health_score >= 25 ? '#F59E0B' :
                      '#10B981'
                    }
                    stroke={!entry.has_data ? '#9CA3AF' : 'none'}
                    strokeWidth={!entry.has_data ? 2 : 0}
                    strokeDasharray={!entry.has_data ? '4,4' : 'none'}
                    opacity={!entry.has_data ? 0.7 : 1}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

      </CardContent>
    </Card>
  );
}

interface MemberDetailModalProps {
  selectedMember: any | null
  setSelectedMember: (member: any | null) => void
  members: any[]
  analysisId?: number | string
  currentAnalysis?: any
  timeRange?: number | string
}

export function MemberDetailModal({
  selectedMember,
  setSelectedMember,
  members,
  analysisId,
  currentAnalysis,
  timeRange
}: MemberDetailModalProps) {
  const [dailyCommitsData, setDailyCommitsData] = useState<any[]>([]);
  const [loadingCommits, setLoadingCommits] = useState(false);
  const dialogContentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchDailyCommits = async () => {
      if (!selectedMember?.email || !analysisId) {
        return;
      }

      setLoadingCommits(true);
      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const url = `${API_BASE}/analyses/users/${encodeURIComponent(selectedMember.email)}/github-daily-commits?analysis_id=${analysisId}`;

        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const result = await response.json();
          if (result.status === 'success' && result.data?.daily_commits) {
            setDailyCommitsData(result.data.daily_commits);
          }
        }
      } catch (err) {
        console.error('Error fetching daily commits:', err);
      } finally {
        setLoadingCommits(false);
      }
    };

    fetchDailyCommits();
  }, [selectedMember?.email, analysisId]);

  // Scroll to top when member changes
  useEffect(() => {
    if (selectedMember && dialogContentRef.current) {
      // Set scrollTop directly and wait for animation to complete
      setTimeout(() => {
        if (dialogContentRef.current) {
          dialogContentRef.current.scrollTop = 0;
        }
      }, 50);
    }
  }, [selectedMember?.email]);

  if (!selectedMember) return null

  return (
    <Dialog open={!!selectedMember} onOpenChange={() => setSelectedMember(null)}>
      <DialogContent
        ref={dialogContentRef}
        className="max-w-5xl max-h-[80vh] overflow-y-auto"
        aria-describedby="member-detail-description"
      >
        {selectedMember && (() => {
          // Find the correct member data from the analysis (consistent with dashboard)
          const memberData = members?.find(m => m.user_name === selectedMember.name);

          return (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center space-x-4">
                  <Avatar className="w-16 h-16">
                    <AvatarImage src={selectedMember?.avatar} />
                    <AvatarFallback className="text-lg">
                      {selectedMember?.name
                        .split(" ")
                        .map((n) => n[0])
                        .join("")}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-xl font-semibold">{selectedMember?.name}</h2>
                        <p className="text-neutral-700">{selectedMember?.role || selectedMember?.email}</p>
                      </div>
                    </div>
                  </div>
                </DialogTitle>
                <DialogDescription id="member-detail-description" className="sr-only">
                  Detailed burnout analysis and daily health timeline for team member.
                  Shows risk factors, incident response metrics, and daily health scores.
                </DialogDescription>
              </DialogHeader>

              <div className="mt-4 space-y-6">
                {/* Overall Burnout Assessment */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card>
                    <CardContent className="p-4 text-center">
                      <p className="text-sm text-gray-600 mb-2">Overall Risk Level</p>
                      {(() => {
                        const riskInfo = getOCBRiskInfo(memberData?.ocb_score)
                        return (
                          <Badge className={`px-3 py-1 ${getOCBBadgeColor(riskInfo.level)}`}>
                            {riskInfo.label}
                          </Badge>
                        )
                      })()}
                      <div className="mt-3">
                        <div className={`text-2xl font-bold ${getOCBScoreColor(memberData?.ocb_score)}`}>
                          {memberData?.ocb_score !== undefined
                            ? `${memberData.ocb_score.toFixed(0)}/100`
                            : 'No Score Available'}
                        </div>
                        <p className="text-xs text-gray-500">
                          {memberData?.ocb_score !== undefined ? 'Risk Level' : 'No Score Available'}
                        </p>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="p-4 text-center">
                      <p className="text-sm text-gray-600 mb-2">Incidents Handled</p>
                      <div className="text-2xl font-bold text-blue-600">
                        {memberData?.incident_count || 0}
                      </div>
                      <p className="text-xs text-gray-500">Past {timeRange || 30} days</p>

                      <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">After Hours Work</span>
                          <span className="font-medium">{(memberData?.metrics?.after_hours_percentage || 0).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Weekend Work</span>
                          <span className="font-medium">{(memberData?.metrics?.weekend_percentage || 0).toFixed(1)}%</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* OCH Risk Levels */}
                {memberData?.ocb_personal_score !== undefined && memberData?.ocb_work_score !== undefined && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Risk Level Scores</CardTitle>
                      <CardDescription>Copenhagen Burnout Inventory dimensional assessment</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="text-center p-3 rounded-lg bg-blue-50 border border-blue-100">
                          <div className="text-lg font-bold text-blue-600">
                            {memberData.ocb_personal_score.toFixed(1)}/100
                          </div>
                          <p className="text-sm font-medium text-blue-800">Personal Burnout</p>
                          <p className="text-xs text-blue-600 mt-1">Physical and psychological fatigue</p>
                        </div>
                        <div className="text-center p-3 rounded-lg bg-orange-50 border border-orange-100">
                          <div className="text-lg font-bold text-orange-600">
                            {memberData.ocb_work_score.toFixed(1)}/100
                          </div>
                          <p className="text-sm font-medium text-orange-800">Work-Related Burnout</p>
                          <p className="text-xs text-orange-600 mt-1">Work-specific exhaustion and cynicism</p>
                        </div>
                      </div>
                      <div className="mt-4 text-center">
                        <div className="text-2xl font-bold text-gray-900">
                          {memberData.ocb_score.toFixed(1)}/100
                        </div>
                        <p className="text-sm text-gray-600">Composite Risk Level</p>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* User Objective Data Card */}
                <UserObjectiveDataCard
                  memberData={memberData}
                  analysisId={analysisId}
                  timeRange={timeRange}
                  currentAnalysis={currentAnalysis}
                />

                {/* Health Check-ins (Survey Data) - Always render directly */}
                <SurveyResultsCard
                  surveyData={currentAnalysis?.analysis_data?.member_surveys?.[selectedMember.user_email || selectedMember.email] || null}
                  userEmail={selectedMember.user_email || selectedMember.email}
                />

                {/* User Risk Factors - Using shared component */}
                <UserRiskFactorsCard selectedMember={selectedMember} />

                {/* GitHub / Slack Tabs (conditional) */}
                {(() => {
                  const hasGitHubData = selectedMember.github_activity?.commits_count > 0 ||
                    selectedMember.github_activity?.pull_requests_count > 0

                  const hasSlackData = selectedMember.slack_activity?.messages_sent > 0 ||
                    selectedMember.slack_activity?.channels_active > 0

                  const tabCount = [hasGitHubData, hasSlackData].filter(Boolean).length
                  const defaultTab = hasGitHubData ? "github" : "communication"

                  if (tabCount === 0) return null

                  function getGridColsClass(count: number): string {
                    if (count === 1) return 'grid-cols-1'
                    if (count === 2) return 'grid-cols-2'
                    return 'grid-cols-3'
                  }

                  return (
                    <Tabs defaultValue={defaultTab} className="w-full">
                      <TabsList className={`grid w-full ${getGridColsClass(tabCount)}`}>
                        {hasGitHubData && <TabsTrigger value="github">GitHub</TabsTrigger>}
                        {hasSlackData && <TabsTrigger value="communication">Communication</TabsTrigger>}
                      </TabsList>

                      <TabsContent value="github" className="space-y-4">
                        {selectedMember.github_activity ? (
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <Card>
                              <CardHeader>
                                <CardTitle className="text-sm">Development Activity</CardTitle>
                              </CardHeader>
                              <CardContent className="space-y-3">
                                <div className="flex justify-between">
                                  <span className="text-sm">Commits</span>
                                  <span className="font-medium">{selectedMember.github_activity?.commits_count || 0}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-sm">Commits/Week</span>
                                  <span className="font-medium">{selectedMember.github_activity?.commits_per_week?.toFixed(1) || '0.0'}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-sm">After Hours Commits</span>
                                  <span className="font-medium">{selectedMember.github_activity?.after_hours_commits || 0}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-sm">Weekend Activity</span>
                                  <span className="font-medium">{selectedMember.github_activity?.weekend_commits || 0}</span>
                                </div>
                              </CardContent>
                            </Card>

                                <Card>
                                  <CardHeader>
                                    <CardTitle className="text-sm">Commit Pattern</CardTitle>
                                  </CardHeader>
                                  <CardContent>
                                    {loadingCommits ? (
                                      <div className="text-center py-8">
                                        <RefreshCw className="w-4 h-4 animate-spin text-neutral-500 mx-auto mb-2" />
                                        <p className="text-xs text-neutral-500">Loading commit data...</p>
                                      </div>
                                    ) : dailyCommitsData && dailyCommitsData.length > 0 ? (
                                      <div className="space-y-3">
                                        <div className="h-32">
                                          <ResponsiveContainer width="100%" height="100%">
                                            <AreaChart data={dailyCommitsData}>
                                              <XAxis
                                                dataKey="date"
                                                fontSize={10}
                                                tick={{ fontSize: 10 }}
                                                domain={[0, 'dataMax']}
                                              />
                                              <YAxis
                                                fontSize={10}
                                                tick={{ fontSize: 10 }}
                                                domain={[0, 'dataMax']}
                                              />
                                              <Tooltip
                                                content={({ payload, label }) => {
                                                  if (payload && payload.length > 0) {
                                                    const data = payload[0].payload;
                                                    return (
                                                      <div className="bg-white p-2 border border-neutral-200 rounded-lg shadow-lg">
                                                        <p className="text-xs font-semibold text-neutral-900">{label}</p>
                                                        <p className="text-xs text-indigo-600">
                                                          {data.commits} commits
                                                          {data.weekend_commits > 0 && <span className="text-neutral-500 ml-1">(Weekend)</span>}
                                                        </p>
                                                        {data.after_hours_commits > 0 && (
                                                          <p className="text-xs text-neutral-500">
                                                            {data.after_hours_commits} after hours
                                                          </p>
                                                        )}
                                                      </div>
                                                    );
                                                  }
                                                  return null;
                                                }}
                                              />
                                              <Area
                                                type="monotone"
                                                dataKey="commits"
                                                stroke="#6366F1"
                                                strokeWidth={2}
                                                fillOpacity={1}
                                                fill="url(#colorCommits)"
                                              />
                                            </AreaChart>
                                          </ResponsiveContainer>
                                        </div>
                                        <div className="text-xs text-indigo-600 text-center">
                                          Average: {selectedMember.github_activity.commits_per_week?.toFixed(1) || '0'} commits/week
                                          {selectedMember.github_activity.after_hours_commits > 0 && (
                                            <span className="ml-2">
                                              • {((selectedMember.github_activity.after_hours_commits / selectedMember.github_activity.commits_count) * 100).toFixed(0)}% after hours
                                            </span>
                                          )}
                                        </div>
                                      </div>
                                    ) : (
                                      <div className="text-center py-4">
                                        <p className="text-xs text-neutral-500">Daily commit data not available</p>
                                        <p className="text-xs text-neutral-500 mt-1">
                                          Total: {selectedMember.github_activity?.commits_count || 0} commits
                                        </p>
                                      </div>
                                    )}
                                  </CardContent>
                                </Card>

                                {/* GitHub Activity Timeline */}
                                <Card>
                                  <CardHeader>
                                    <CardTitle className="text-sm">GitHub Activity Timeline</CardTitle>
                                  </CardHeader>
                                  <CardContent className="space-y-3">
                                    <div className="flex justify-between">
                                      <span className="text-sm">Pull Requests</span>
                                      <span className="font-medium">{selectedMember.github_activity?.pull_requests_count || 0}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className="text-sm">Code Reviews</span>
                                      <span className="font-medium">{selectedMember.github_activity?.reviews_count || 0}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className="text-sm">Avg PR Size</span>
                                      <span className="font-medium">{selectedMember.github_activity?.avg_pr_size || 0} lines</span>
                                    </div>
                                    <Separator className="my-2" />
                                    <div className="space-y-2">
                                      <p className="text-xs font-semibold text-neutral-700">Work-life Balance</p>
                                      <div className="flex items-center justify-between text-xs">
                                        <span className="text-neutral-700">After-Hours</span>
                                        <span className="font-medium text-orange-600">
                                          {selectedMember.github_activity?.commits_count > 0
                                            ? ((selectedMember.github_activity.after_hours_commits / selectedMember.github_activity.commits_count) * 100).toFixed(1)
                                            : 0}%
                                        </span>
                                      </div>
                                      <div className="flex items-center justify-between text-xs">
                                        <span className="text-neutral-700">Weekend</span>
                                        <span className="font-medium text-purple-600">
                                          {selectedMember.github_activity?.commits_count > 0
                                            ? ((selectedMember.github_activity.weekend_commits / selectedMember.github_activity.commits_count) * 100).toFixed(1)
                                            : 0}%
                                        </span>
                                      </div>
                                    </div>
                                  </CardContent>
                                </Card>
                              </div>
                            ) : (
                              <Card>
                                <CardContent className="p-6 text-center">
                                  <p className="text-neutral-500">No GitHub activity data available</p>
                                </CardContent>
                              </Card>
                            )}
                          </TabsContent>

                          <TabsContent value="communication" className="space-y-4">
                            {selectedMember.slack_activity ? (
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <Card className="border border-neutral-200">
                                  <CardHeader>
                                    <CardTitle className="text-sm">Communication Activity</CardTitle>
                                  </CardHeader>
                                  <CardContent className="space-y-3">
                                    <div className="flex justify-between">
                                      <span className="text-sm">Messages Sent</span>
                                      <span className="font-medium">{selectedMember.slack_activity?.messages_sent || 0}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className="text-sm">Active Channels</span>
                                      <span className="font-medium">{selectedMember.slack_activity?.channels_active || 0}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className="text-sm">After Hours Messages</span>
                                      <span className="font-medium">{selectedMember.slack_activity?.after_hours_messages || 0}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className="text-sm">Sentiment Score</span>
                                      <span className="font-medium">{selectedMember.slack_activity?.sentiment_score || 'N/A'}</span>
                                    </div>
                                  </CardContent>
                                </Card>
                              </div>
                            ) : (
                              <Card>
                                <CardContent className="p-6 text-center">
                                  <p className="text-neutral-500">No Slack activity data available</p>
                                </CardContent>
                              </Card>
                            )}
                          </TabsContent>
                        </Tabs>
                      );
                    })()}
                    

                    {/* Risk Level Breakdown – Deep Dive (moved to bottom) */}
                    <Card>
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <h4 className="font-semibold text-neutral-900">Burnout Analysis</h4>
                          <div className="relative group">
                            <Info className="w-4 h-4 text-neutral-400 cursor-help hover:text-neutral-600" />
                            <div className="absolute top-full right-0 mt-2 px-3 py-2 bg-neutral-900 text-white text-xs rounded-lg w-80 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                              <div className="font-semibold mb-2">Burnout Dimensions</div>
                              <div className="space-y-2">
                                <div>
                                  <div className="font-medium text-blue-300 mb-1">Personal Burnout</div>
                                  <div className="text-xs">• Incident frequency (incidents per week)<br/>• After-hours work patterns<br/>• Weekend activity levels<br/>• Sleep disruption indicators<br/>• Overall workload intensity relative to team baseline</div>
                                </div>
                                <div>
                                  <div className="font-medium text-blue-300 mb-1">Work-Related Burnout</div>
                                  <div className="text-xs">• Incident response time patterns<br/>• Severity-weighted incident load<br/>• GitHub commit activity and timing<br/>• Slack communication patterns<br/>• Work-life boundary violations (late night/weekend work)</div>
                                </div>
                              </div>
                              <div className="absolute bottom-full right-4 w-0 h-0 border-l-4 border-r-4 border-b-4 border-l-transparent border-r-transparent border-b-gray-900"></div>
                            </div>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="p-4">
                        {memberData?.ocb_reasoning ? (
                          <div className="space-y-6">
                            {/* Dimensional Breakdown */}
                            {memberData.ocb_breakdown && (
                              <div className="space-y-1">
                                {/* Personal Burnout */}
                                <div className="rounded-lg p-2">
                                  <div className="flex items-center justify-between mb-1">
                                    <span></span>
                                    {(() => {
                                      const score = memberData.ocb_breakdown.personal ?? 0;
                                      let severity = 'Good';
                                      let color = 'bg-green-100 text-green-800';
                                      if (score >= 70) {
                                        severity = 'Critical';
                                        color = 'bg-red-100 text-red-800';
                                      } else if (score >= 50) {
                                        severity = 'Poor';
                                        color = 'bg-orange-100 text-orange-800';
                                      } else if (score >= 30) {
                                        severity = 'Fair';
                                        color = 'bg-yellow-100 text-yellow-800';
                                      }
                                      return (
                                        <span className={`text-xs font-medium px-2 py-1 rounded-full ${color}`}>
                                          {severity}
                                        </span>
                                      );
                                    })()}
                                  </div>
                                  <div className="flex items-center gap-3">
                                    <span className="w-20 text-sm font-medium text-gray-700">Personal</span>
                                    <div className="flex-1">
                                      <div className="w-full bg-gray-300 rounded-full h-2">
                                        <div
                                          className="h-2 rounded-full transition-all duration-500"
                                          style={{
                                            width: `${memberData.ocb_breakdown.personal ?? 0}%`,
                                            backgroundColor: (() => {
                                              const score = memberData.ocb_breakdown.personal ?? 0;
                                              if (score >= 70) return '#EF4444'; // red-500
                                              if (score >= 50) return '#F97316'; // orange-500
                                              if (score >= 30) return '#F59E0B'; // yellow-500
                                              return '#10B981'; // green-500
                                            })()
                                          }}
                                        ></div>
                                      </div>
                                    </div>
                                  </div>
                                </div>

                                {/* Work-Related Burnout */}
                                <div className="rounded-lg p-2">
                                  <div className="flex items-center justify-between mb-1">
                                    <span></span>
                                    {(() => {
                                      const score = memberData.ocb_breakdown.work_related ?? 0;
                                      let severity = 'Good';
                                      let color = 'bg-green-100 text-green-800';
                                      if (score >= 70) {
                                        severity = 'Critical';
                                        color = 'bg-red-100 text-red-800';
                                      } else if (score >= 50) {
                                        severity = 'Poor';
                                        color = 'bg-orange-100 text-orange-800';
                                      } else if (score >= 30) {
                                        severity = 'Fair';
                                        color = 'bg-yellow-100 text-yellow-800';
                                      }
                                      return (
                                        <span className={`text-xs font-medium px-2 py-1 rounded-full ${color}`}>
                                          {severity}
                                        </span>
                                      );
                                    })()}
                                  </div>
                                  <div className="flex items-center gap-3">
                                    <span className="w-20 text-sm font-medium text-gray-700">Work-Related</span>
                                    <div className="flex-1">
                                      <div className="w-full bg-gray-300 rounded-full h-2">
                                        <div
                                          className="h-2 rounded-full transition-all duration-500"
                                          style={{
                                            width: `${memberData.ocb_breakdown.work_related ?? 0}%`,
                                            backgroundColor: (() => {
                                              const score = memberData.ocb_breakdown.work_related ?? 0;
                                              if (score >= 70) return '#EF4444'; // red-500
                                              if (score >= 50) return '#F97316'; // orange-500
                                              if (score >= 30) return '#F59E0B'; // yellow-500
                                              return '#10B981'; // green-500
                                            })()
                                          }}
                                        ></div>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Contributing Factors */}
                            <div className="grid grid-cols-2 gap-y-1.5 gap-x-4 mt-2">
                              {(() => {
                                const filteredReasons = memberData.ocb_reasoning.slice(1).filter((reason: string) => {
                                  const cleanReason = reason.replace(/^[\s]*[•·\-*]\s*/, '').trim();
                                  return !cleanReason.endsWith(':');
                                });

                                return filteredReasons.map((reason: string, index: number) => {
                                  const cleanReason = reason.replace(/^[\s]*[•·\-*]\s*/, '').trim().replace(/\s*\([^)]*\)$/, '');
                                  const isLastItem = index === filteredReasons.length - 1;

                                  if (isLastItem) {
                                    return (
                                      <div key={index} className="col-span-2 text-sm text-neutral-700 font-semibold mt-4 pt-3 border-t border-neutral-200">
                                        {cleanReason}
                                      </div>
                                    );
                                  }

                                  return (
                                    <div key={index} className="flex items-start gap-1.5 text-sm text-neutral-700">
                                      <span className="text-neutral-400 flex-shrink-0 leading-relaxed">•</span>
                                      <span className="leading-relaxed">{cleanReason}</span>
                                    </div>
                                  );
                                });
                              })()}
                            </div>
                          </div>
                        ) : (
                          <p className="text-sm text-neutral-500 italic">
                            Risk level analysis not available. Run a new analysis to see detailed risk factors.
                          </p>
                        )}
                      </CardContent>
                    </Card>

                {/* Ticketing Workload Card */}
                <TicketingCard memberData={memberData} />
              </div>
            </>
          )
        })()}
      </DialogContent>
    </Dialog>
  )
}
