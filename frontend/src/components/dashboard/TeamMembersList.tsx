"use client"

import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronRight, Users, Loader2, TrendingUp, TrendingDown, Minus, ChevronsUp, ChevronsDown } from "lucide-react"
import { useState } from "react"
import Image from "next/image"

// User trend categories (5 levels)
type UserTrend = 'significantly_worsening' | 'worsening' | 'stable' | 'improving' | 'significantly_improving'

interface TrendInfo {
  trend: UserTrend
  percentage: number
  firstHalfScore: number
  secondHalfScore: number
}

// Calculate user trend from their individual daily data
function calculateUserTrend(
  userEmail: string,
  individualDailyData: Record<string, Record<string, any>> | undefined
): TrendInfo {
  const defaultTrend: TrendInfo = { trend: 'stable', percentage: 0, firstHalfScore: 0, secondHalfScore: 0 }

  if (!individualDailyData || !userEmail) return defaultTrend

  // Find user data (try both exact match and lowercase)
  const userData = individualDailyData[userEmail] || individualDailyData[userEmail.toLowerCase()]
  if (!userData) return defaultTrend

  // Get dates sorted chronologically
  const dates = Object.keys(userData).sort()
  if (dates.length < 4) return defaultTrend // Need minimum data for meaningful trend

  // Compare first days to last days (not halves) for true overall direction
  const numDaysToCompare = Math.min(7, Math.floor(dates.length / 2))
  const firstDates = dates.slice(0, numDaysToCompare)
  const lastDates = dates.slice(-numDaysToCompare)

  // Calculate weighted incident score for a set of dates
  const calculateScore = (datesToCalc: string[]) => {
    let total = 0
    for (const date of datesToCalc) {
      const day = userData[date]
      if (day) {
        // Weight: incidents=1, severity=0.5, after_hours=0.3
        total += (day.incident_count || 0) +
                 (day.severity_weighted_count || 0) * 0.5 +
                 (day.after_hours_count || 0) * 0.3
      }
    }
    return total / datesToCalc.length // Average per day
  }

  const firstScore = calculateScore(firstDates)
  const lastScore = calculateScore(lastDates)

  // Calculate percentage change (positive = worsening, negative = improving)
  if (firstScore === 0 && lastScore === 0) {
    return { trend: 'stable', percentage: 0, firstHalfScore: 0, secondHalfScore: 0 }
  }

  const baseline = firstScore || 0.1 // Avoid division by zero
  const change = ((lastScore - firstScore) / baseline) * 100

  // Use 15% threshold for stable (matches other trend components)
  let trend: UserTrend
  if (change <= -30) trend = 'significantly_improving'
  else if (change <= -15) trend = 'improving'
  else if (change >= 30) trend = 'significantly_worsening'
  else if (change >= 15) trend = 'worsening'
  else trend = 'stable'

  return { trend, percentage: Math.round(Math.abs(change)), firstHalfScore: firstScore, secondHalfScore: lastScore }
}

// Get trend display config
function getTrendConfig(trend: UserTrend) {
  switch (trend) {
    case 'significantly_improving':
      return {
        label: 'Improving Fast',
        icon: <ChevronsDown className="w-4 h-4" />,
        className: 'bg-green-100 text-green-700 border-green-200',
        tooltip: 'Workload decreased significantly'
      }
    case 'improving':
      return {
        label: 'Improving',
        icon: <TrendingDown className="w-4 h-4" />,
        className: 'bg-green-50 text-green-600 border-green-100',
        tooltip: 'Workload trending down'
      }
    case 'stable':
      return {
        label: 'Stable',
        icon: <Minus className="w-4 h-4" />,
        className: 'bg-purple-50 text-purple-600 border-purple-200',
        tooltip: 'Workload consistent'
      }
    case 'worsening':
      return {
        label: 'Worsening',
        icon: <TrendingUp className="w-4 h-4" />,
        className: 'bg-red-50 text-red-600 border-red-100',
        tooltip: 'Workload trending up'
      }
    case 'significantly_worsening':
      return {
        label: 'Needs Attention',
        icon: <ChevronsUp className="w-4 h-4" />,
        className: 'bg-red-100 text-red-700 border-red-200',
        tooltip: 'Workload increased significantly'
      }
  }
}

interface TeamMembersListProps {
  currentAnalysis: any
  setSelectedMember: (member: any) => void
  getRiskColor: (riskLevel: string) => string
  getProgressColor: (riskLevel: string) => string
}

export function TeamMembersList({
  currentAnalysis,
  setSelectedMember,
  getRiskColor,
  getProgressColor
}: TeamMembersListProps) {
  const [showMembersWithoutIncidents, setShowMembersWithoutIncidents] = useState(false);
  const dataSources = currentAnalysis?.analysis_data?.data_sources;
  const analysisConfig = currentAnalysis?.config;
  const individualDailyData = currentAnalysis?.analysis_data?.individual_daily_data;

  const isDataSourceEnabled = (source: 'github' | 'slack' | 'jira' | 'linear') => {
    if (Array.isArray(dataSources)) {
      return dataSources.includes(source);
    }

    if (dataSources && typeof dataSources === 'object') {
      const keyMap = {
        github: 'github_data',
        slack: 'slack_data',
        jira: 'jira_data',
        linear: 'linear_data'
      } as const;
      const value = (dataSources as any)[keyMap[source]];
      if (typeof value === 'boolean') {
        return value;
      }
    }

    if (analysisConfig) {
      const configMap = {
        github: 'include_github',
        slack: 'include_slack',
        jira: 'include_jira',
        linear: 'include_linear'
      } as const;
      const value = (analysisConfig as any)[configMap[source]];
      if (typeof value === 'boolean') {
        return value;
      }
    }

    return false;
  };

  const isGithubEnabled = isDataSourceEnabled('github');
  const isSlackEnabled = isDataSourceEnabled('slack');
  const isJiraEnabled = isDataSourceEnabled('jira');
  const isLinearEnabled = isDataSourceEnabled('linear');
  
  const isLoading = !currentAnalysis || !currentAnalysis.analysis_data

  // OCH risk level from score (0-100 scale, higher = more burnout)
  function getOCHRiskLevel(score: number | undefined | null): string {
    if (score === undefined || score === null) return 'low'
    if (score < 25) return 'healthy'
    if (score < 50) return 'fair'
    if (score < 75) return 'poor'
    return 'critical'
  }

  // OCH 4-color system for progress bars (0-100 scale, higher = more burnout)
  function getOCHProgressColor(score: number): string {
    const clampedScore = Math.max(0, Math.min(100, score))
    if (clampedScore < 25) return '#10b981'  // Green - Low/minimal burnout (0-24)
    if (clampedScore < 50) return '#eab308'  // Yellow - Mild burnout symptoms (25-49)
    if (clampedScore < 75) return '#f97316'  // Orange - Moderate/significant burnout (50-74)
    return '#dc2626'                          // Red - High/severe burnout (75-100)
  }

  const renderMemberCard = (member: any) => {
    // Calculate user trend from individual daily data
    const trendInfo = calculateUserTrend(member.user_email, individualDailyData)
    const trendConfig = getTrendConfig(trendInfo.trend)

    return (
    <Card
      key={member.user_id}
      className="cursor-pointer hover:shadow-md transition-shadow"
      onClick={() => setSelectedMember({
        id: member.user_id || '',
        name: member.user_name || 'Unknown',
        email: member.user_email || '',
        avatar_url: member.avatar_url || null,
        burnoutScore: member.och_score || 0,
        riskLevel: (member.risk_level || 'low') as 'high' | 'medium' | 'low',
        trend: trendInfo.trend,
        trendPercentage: trendInfo.percentage,
        incidentsHandled: member.incident_count || 0,
        avgResponseTime: `${Math.round(member.metrics?.avg_response_time_minutes || 0)}m`,
        factors: {
          workload: Math.round(((member.factors?.workload || (member as any).key_metrics?.incidents_per_week || 0)) * 10) / 10,
          afterHours: Math.round(((member.factors?.after_hours || (member as any).key_metrics?.after_hours_percentage || 0)) * 10) / 10,
          incidentLoad: Math.round(((member.factors?.incident_load || (member as any).key_metrics?.incidents_per_week || 0)) * 10) / 10,
        },
        metrics: member.metrics || {},
        github_activity: member.github_activity || null,
        slack_activity: member.slack_activity || null
      })}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-3">
            <Avatar>
              {member.avatar_url && (
                <AvatarImage src={member.avatar_url} alt={member.user_name || 'User avatar'} />
              )}
              <AvatarFallback>
                {member.user_name
                  ? member.user_name.split(" ").map((n) => n[0]).join("")
                  : member.user_email?.charAt(0).toUpperCase() || "?"}
              </AvatarFallback>
            </Avatar>
            <div className="flex items-center gap-2">
              <h3 className="font-medium">{member.user_name || member.user_email}</h3>
              {/* Integration icons - inline with username */}
              <div className="flex gap-1">
                {member.github_username && (
                  <div className="flex items-center justify-center w-5 h-5 bg-neutral-200 rounded-full border border-neutral-200" title="GitHub">
                    <svg className="w-3 h-3 text-neutral-700" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
                    </svg>
                  </div>
                )}
                {member.slack_user_id && (
                  <div className="flex items-center justify-center w-5 h-5 bg-white rounded-full border border-neutral-200" title="Slack">
                    <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none">
                      <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52z" fill="#E01E5A"/>
                      <path d="M6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z" fill="#E01E5A"/>
                      <path d="M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834z" fill="#36C5F0"/>
                      <path d="M8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z" fill="#36C5F0"/>
                      <path d="M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834z" fill="#2EB67D"/>
                      <path d="M17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312z" fill="#2EB67D"/>
                      <path d="M15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52z" fill="#ECB22E"/>
                      <path d="M15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" fill="#ECB22E"/>
                    </svg>
                  </div>
                )}
                {isJiraEnabled && member.jira_account_id && (
                  <div className="flex items-center justify-center w-5 h-5 bg-blue-50 rounded-full border border-blue-200" title="Jira">
                    <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none">
                      <path d="M11.571 11.513H0a5.218 5.218 0 0 0 5.232 5.215h2.13v2.057A5.215 5.215 0 0 0 12.575 24V12.518a1.005 1.005 0 0 0-1.005-1.005zm5.723-5.756H5.736a5.215 5.215 0 0 0 5.215 5.214h2.129v2.058a5.218 5.218 0 0 0 5.215 5.214V6.758a1.001 1.001 0 0 0-1.001-1.001zM23.013 0H11.455a5.215 5.215 0 0 0 5.215 5.215h2.129v2.057A5.215 5.215 0 0 0 24 12.483V1.005A1.001 1.001 0 0 0 23.013 0z" fill="#2684FF"/>
                    </svg>
                  </div>
                )}
                {member.linear_user_id && (
                  <div className="flex items-center justify-center w-5 h-5" title="Linear">
                    <Image src="/images/linear-logo.png" alt="Linear" width={14} height={14} />
                  </div>
                )}
                {member.rootly_user_id && (
                  <div className="flex items-center justify-center w-5 h-5 rounded" title="Rootly">
                    <Image src="/images/rootly-logo-icon.jpg" alt="Rootly" width={14} height={14} className="rounded" />
                  </div>
                )}
                {currentAnalysis?.analysis_data?.member_surveys?.[member.user_email] && (
                  <div className="flex items-center justify-center w-5 h-5 bg-blue-50 rounded-full border border-blue-200" title="Survey Data Available">
                    <svg className="w-3 h-3 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {/* Trend badge - most important, shown first */}
            <div className="relative group">
              <Badge className={`flex items-center gap-1 ${trendConfig.className} border`}>
                {trendConfig.icon}
                {trendConfig.label}
              </Badge>
              {trendInfo.percentage > 0 && (
                <div className="absolute top-full right-0 mt-1 px-2 py-1 bg-neutral-900/95 text-white text-xs rounded whitespace-nowrap opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                  {trendInfo.trend.includes('improving')
                    ? `Workload down ${trendInfo.percentage}%`
                    : trendInfo.trend.includes('worsening')
                    ? `Workload up ${trendInfo.percentage}%`
                    : 'No significant change'}
                </div>
              )}
            </div>
            {member.is_oncall && (
              <Badge className="bg-purple-50 text-purple-700 border border-purple-200">
                ON-CALL
              </Badge>
            )}
            {member?.och_score !== undefined && (() => {
              const getOCHRiskLevel = (och_score: number): string => {
                if (och_score < 25) return 'healthy';
                if (och_score < 50) return 'fair';
                if (och_score < 75) return 'poor';
                return 'critical';
              };

              const riskLevel = getOCHRiskLevel(member.och_score);
              const displayLabel = riskLevel === 'healthy' ? 'HEALTHY' :
                                 riskLevel === 'fair' ? 'FAIR' :
                                 riskLevel === 'poor' ? 'POOR' :
                                 'CRITICAL';

              return <Badge className={getRiskColor(riskLevel)}>{displayLabel}</Badge>;
            })()}
          </div>
        </div>

        <div className="space-y-2">
          {member?.och_score !== undefined ? (
            <div className="text-sm">
              <span>Risk Level</span>
            </div>
          ) : (
            <div className="text-sm">
              <span>No Risk Level Available</span>
            </div>
          )}
          <div className="relative h-2 w-full overflow-hidden rounded-full bg-neutral-300">
            <div 
              className="h-full transition-all"
              style={{ 
                width: `${member?.och_score || 0}%`,
                backgroundColor: member?.och_score !== undefined 
                  ? getOCHProgressColor(member.och_score)
                  : undefined
              }}
            />
          </div>
          <div className="flex justify-between text-xs text-neutral-500">
            <span>{member.incident_count} incidents</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )}

  return (
    <>
      {/* Organization Members Grid */}
      <Card>
        <CardHeader>
          <CardTitle>Team Member Risk Levels</CardTitle>
          <CardDescription>Click on a member to view detailed analysis</CardDescription>
        </CardHeader>
        <CardContent>
          {(() => {
            const teamAnalysis = currentAnalysis?.analysis_data?.team_analysis
            const allMembers = Array.isArray(teamAnalysis) ? teamAnalysis : teamAnalysis?.members
            
            if (!allMembers || allMembers.length === 0) {
              return (
                <div className="text-center text-neutral-500 py-8">
                  No organization member data available yet
                </div>
              )
            }
            
            // Filter members with valid scores
            const validMembers = allMembers.filter((member) => {
              return member.och_score !== undefined && member.och_score !== null
            })
            
            // Separate members with incidents/burnout and those with neither
            // Include members with incidents OR OCH risk level (e.g., from Jira) in main section
            const membersWithIncidents = validMembers.filter(member =>
              (member.incident_count || 0) > 0 || (member.och_score || 0) > 0
            )
            // Only hide members with BOTH zero incidents AND zero OCH risk level
            const membersWithoutIncidents = validMembers.filter(member =>
              (member.incident_count || 0) === 0 && (member.och_score || 0) === 0
            )

            
            // Sort members by score (highest risk first)
            const sortMembers = (members: any[]) => members.sort((a, b) => {
              // Sort by OCH risk level only (higher score = higher risk)
              return (b.och_score || 0) - (a.och_score || 0);
            })

            // Sort members alphabetically by name
            const sortMembersAlphabetically = (members: any[]) => members.sort((a, b) => {
              const nameA = (a.user_name || '').toLowerCase();
              const nameB = (b.user_name || '').toLowerCase();
              return nameA.localeCompare(nameB);
            })

            return (
              <>
                {/* Members with incidents or burnout (from Jira, GitHub, etc.) */}
                {membersWithIncidents.length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    {sortMembers(membersWithIncidents).map(renderMemberCard)}
                  </div>
                )}

                {/* Collapsible section for members with no activity (no incidents and no burnout) */}
                {(membersWithoutIncidents.length > 0 || isLoading) && (
                  <div className="mt-6">
                    <Button
                      variant="outline" 
                      onClick={() => setShowMembersWithoutIncidents(!showMembersWithoutIncidents)}
                      className="w-full mb-4 text-neutral-700 border-neutral-300 hover:bg-neutral-100"
                      disabled={isLoading}
                    >
                      <div className="flex items-center justify-center space-x-2">
                        {isLoading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          showMembersWithoutIncidents ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                        )}
                        <Users className="w-4 h-4" />
                        <span>
                          {isLoading ? (
                            'Loading team members...'
                          ) : (
                            <>
                              {showMembersWithoutIncidents ? 'Hide' : 'Show'} team members with no activity
                              <span className="ml-1 text-xs bg-neutral-300 px-2 py-1 rounded">
                                {membersWithoutIncidents.length}
                              </span>
                            </>
                          )}
                        </span>
                      </div>
                    </Button>

                    {showMembersWithoutIncidents && !isLoading && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {sortMembersAlphabetically(membersWithoutIncidents).map(renderMemberCard)}
                      </div>
                    )}
                  </div>
                )}

                {/* No members case */}
                {membersWithIncidents.length === 0 && membersWithoutIncidents.length === 0 && (
                  <div className="text-center text-neutral-500 py-8">
                    No team members with valid health data found
                  </div>
                )}
              </>
            )
          })()}
        </CardContent>
      </Card>
    </>
  )
}
