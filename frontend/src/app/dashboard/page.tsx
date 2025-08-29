"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { MappingDrawer } from "@/components/mapping-drawer"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Line,
  LineChart,
  Area,
  AreaChart,
  Bar,
  BarChart,
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts"
import {
  Activity,
  ChevronLeft,
  ChevronRight,
  Play,
  Clock,
  FileText,
  Settings,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  Download,
  RefreshCw,
  AlertCircle,
  Trash2,
  LogOut,
  BookOpen,
  Users,
  Star,
  Info,
  BarChart3,
  Sparkles,
} from "lucide-react"
import { TeamHealthOverview } from "@/components/dashboard/TeamHealthOverview"
import { AnalysisProgressSection } from "@/components/dashboard/AnalysisProgressSection"
import { TeamMembersList } from "@/components/dashboard/TeamMembersList"
import { HealthTrendsChart } from "@/components/dashboard/HealthTrendsChart"
import { MemberDetailModal } from "@/components/dashboard/MemberDetailModal"
import Image from "next/image"
import { useRouter, useSearchParams } from "next/navigation"
import { toast } from "sonner"
import { useBackendHealth } from "@/hooks/use-backend-health"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Integration {
  id: number
  name: string
  organization_name: string
  total_users: number
  is_default: boolean
  created_at: string
  last_used_at: string | null
  token_suffix: string
  platform?: 'rootly' | 'pagerduty'
  permissions?: {
    users?: {
      access: boolean
    }
    incidents?: {
      access: boolean
    }
  }
}

interface GitHubIntegration {
  id: number
  github_username: string
  organizations: string[]
  token_source: string
  connected_at: string
  last_updated: string
}

interface SlackIntegration {
  id: number
  slack_user_id: string
  workspace_id: string
  token_source: string
  connected_at: string
  last_updated: string
  total_channels?: number
}

interface OrganizationMember {
  id: string
  name: string
  email: string
  role?: string
  avatar?: string
  burnoutScore: number
  burnout_score?: number // API returns snake_case
  riskLevel: 'high' | 'medium' | 'low'
  trend: 'up' | 'down' | 'stable'
  incidentsHandled: number
  incident_count?: number // API returns this
  avgResponseTime: string
  factors: {
    workload: number
    afterHours: number
    weekendWork: number
    incidentLoad: number
    responseTime: number
    // Snake case versions from API
    after_hours?: number
    weekend_work?: number
    incident_load?: number
    response_time?: number
  }
  metrics?: {
    avg_response_time_minutes: number
    after_hours_percentage: number
    weekend_percentage: number
    status_distribution?: any
  }
  github_activity?: {
    commits_count: number
    pull_requests_count: number
    reviews_count: number
    after_hours_commits: number
    weekend_commits: number
    avg_pr_size: number
    burnout_indicators: {
      excessive_commits: boolean
      late_night_activity: boolean
      weekend_work: boolean
      large_prs: boolean
    }
  }
  slack_activity?: {
    messages_sent: number
    channels_active: number
    after_hours_messages: number
    weekend_messages: number
    avg_response_time_minutes: number
    sentiment_score: number
    burnout_indicators: {
      excessive_messaging: boolean
      poor_sentiment: boolean
      late_responses: boolean
      after_hours_activity: boolean
    }
  }
  github_burnout_breakdown?: {
    exhaustion_score: number
    depersonalization_score: number
    accomplishment_score: number
    final_score: number
  }
  // Additional fields from API response
  user_id?: string
  user_name?: string
  user_email?: string
  risk_level?: string
}

interface AnalysisResult {
  id: string
  uuid?: string
  integration_id: number
  created_at: string
  status: string
  time_range: number
  error_message?: string
  organizationName?: string // For display purposes
  timeRange?: string // For display purposes
  overallScore?: number // For display purposes
  trend?: "up" | "down" | "stable" // For display purposes
  atRiskCount?: number // For display purposes
  totalMembers?: number // For display purposes
  lastAnalysis?: string // For display purposes
  trends?: {
    daily: Array<{ date: string; score: number }>
    weekly: Array<{ week: string; score: number }>
    monthly: Array<{ month: string; score: number }>
  } // For display purposes
  organizationMembers?: OrganizationMember[] // For display purposes
  burnoutFactors?: Array<{ factor: string; value: number }> // For display purposes
  analysis_data?: {
    data_sources: {
      incident_data: boolean
      github_data: boolean
      slack_data: boolean
      github_users_analyzed?: number
      slack_users_analyzed?: number
    }
    team_health: {
      overall_score: number
      risk_distribution: {
        low: number
        medium: number
        high: number
        critical: number
      }
      health_status: string
      data_source_contributions?: {
        incident_contribution: number
        github_contribution: number
        slack_contribution: number
      }
    }
    team_summary?: {
      total_users: number
      average_score: number
      highest_score: number
      risk_distribution: {
        high: number
        medium: number
        low: number
        critical: number
      }
      users_at_risk: number
    }
    team_analysis: {
      members: Array<{
        user_id: string
        user_name: string
        user_email: string
        burnout_score: number
        risk_level: string
        factors: {
          workload: number
          after_hours: number
          weekend_work: number
          incident_load: number
          response_time: number
        }
        incident_count: number
        metrics: {
          avg_response_time_minutes: number
          after_hours_percentage: number
          weekend_percentage: number
          status_distribution?: any
        }
        github_activity?: any
        slack_activity?: any
      }>
    } | Array<{
      user_id: string
      user_name: string
      user_email: string
      burnout_score: number
      risk_level: string
      incident_count: number
      key_metrics?: {
        incidents_per_week: number
        severity_weighted_per_week?: number
        after_hours_percentage: number
        avg_resolution_hours: number
      }
      recommendations?: string[]
      factors?: any
      metrics?: any
      github_activity?: any
      slack_activity?: any
    }>
    github_insights?: {
      total_commits: number
      total_pull_requests: number
      total_reviews: number
      after_hours_activity_percentage: number
      weekend_activity_percentage?: number
      weekend_commit_percentage?: number
      top_contributors: Array<{
        username: string
        commits: number
        prs: number
        reviews: number
      }>
      burnout_indicators: {
        excessive_late_night_commits: number
        large_pr_pattern: number
        weekend_workers: number
      }
      activity_data?: {
        commits_count: number
        pull_requests_count: number
        reviews_count: number
        after_hours_commits: number
        weekend_commits: number
        avg_pr_size: number
      }
    }
    slack_insights?: {
      total_messages: number
      active_channels: number
      avg_response_time_minutes: number
      after_hours_activity_percentage: number
      weekend_activity_percentage?: number
      weekend_commit_percentage?: number
      weekend_percentage?: number
      sentiment_analysis: {
        avg_sentiment: number
        negative_sentiment_users: number
      }
      burnout_indicators: {
        excessive_messaging: number
        poor_sentiment_users: number
        after_hours_communicators: number
      }
    }
    insights: Array<{
      type: string
      message: string
      severity: string
      source?: 'incident' | 'github' | 'slack' | 'combined'
    }>
    recommendations: Array<{
      type: string
      message: string
      priority: string
      source?: 'incident' | 'github' | 'slack' | 'combined'
    }>
    partial_data?: {
      users: Array<any>
      incidents: Array<any>
      metadata: any
    }
    error?: string
    data_collection_successful?: boolean
    failure_stage?: string
    session_hours?: number
    total_incidents?: number
    ai_team_insights?: {
      available: boolean
      summary?: string
      recommendations?: string[]
      key_insights?: string[]
      insights?: {
        team_size?: number
        risk_distribution?: {
          high: number
          medium: number
          low: number
          critical?: number
        }
        [key: string]: any
      }
    }
    daily_trends?: Array<{
      date: string
      overall_score: number
      incident_count: number
      severity_weighted_count: number
      after_hours_count: number
      users_involved: number
      members_at_risk: number
      total_members: number
      health_status: string
    }>
    period_summary?: {
      average_score: number
      days_analyzed: number
      total_days_with_data: number
    }
  }
}

type AnalysisStage = "loading" | "connecting" | "fetching_users" | "fetching" | "fetching_github" | "fetching_slack" | "calculating" | "analyzing" | "preparing" | "complete"

// Mock data generator function removed - following "NO FALLBACK DATA" principle
// All dashboard components now only display real analysis data from the API

// Component for individual daily health tracking
function IndividualDailyHealthChart({ memberData, analysisId, currentAnalysis }: {
  memberData: any
  analysisId?: number | string
  currentAnalysis?: any
}) {
  const [dailyHealthData, setDailyHealthData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch daily health data for this member
  useEffect(() => {
    const fetchDailyHealth = async () => {
      if (!memberData?.user_email || !analysisId) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(
          `${API_BASE}/analyses/${analysisId}/members/${encodeURIComponent(memberData.user_email)}/daily-health`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            'Content-Type': 'application/json'
          }
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.status === 'success' && result.data?.daily_health) {
          // Format the data for the chart
          const formattedData = result.data.daily_health.map((day: any) => ({
            date: day.date,
            health_score: day.health_score,
            incident_count: day.incident_count,
            team_health: day.team_health,
            day_name: new Date(day.date).toLocaleDateString('en-US', { 
              weekday: 'short', month: 'short', day: 'numeric' 
            }),
            factors: day.factors
          }));
          
          setDailyHealthData(formattedData);
        } else {
          setError(result.message || 'No daily health data available');
        }
      } catch (err) {
        console.error('Error fetching daily health:', err);
        
        // Fallback: Calculate daily health from existing analysis data
        if (currentAnalysis && currentAnalysis.results) {
          try {
            const dailyTrends = currentAnalysis.results.daily_trends || [];
            const memberEmail = memberData?.user_email?.toLowerCase();
            
            // Don't show fabricated data - only show if there's actual individual incident data
            setError('No individual daily health data available - this member had no incident involvement during the analysis period');
          } catch (fallbackErr) {
            console.error('Fallback calculation failed:', fallbackErr);
            setError('Failed to load daily health data');
          }
        } else {
          setError('Failed to load daily health data');
        }
      } finally {
        setLoading(false);
      }
    };
    
    fetchDailyHealth();
  }, [memberData?.user_email, analysisId]);

  if (loading) {
    return (
      <div>
        <h3 className="text-lg font-semibold mb-4">📈 Individual Daily Health Timeline</h3>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-600">Loading daily health data...</p>
        </div>
      </div>
    );
  }

  if (error || !dailyHealthData || dailyHealthData.length === 0) {
    return (
      <div>
        <h3 className="text-lg font-semibold mb-4">📈 Individual Daily Health Timeline</h3>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
          <div className="text-gray-500 mb-2">
            <BarChart3 className="w-8 h-8 mx-auto mb-2" />
            {error || 'No daily health data available'}
          </div>
          <p className="text-sm text-gray-600">
            Daily health scores are calculated for days when incidents occur
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">📈 Individual Daily Health Timeline</h3>
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Daily health timeline (last {dailyHealthData.length} days)
          </p>
          <div className="flex items-center space-x-4 text-xs text-gray-500">
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-green-500 rounded"></div>
              <span>Healthy (0-24 CBI)</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-yellow-500 rounded"></div>
              <span>Fair (25-49 CBI)</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-orange-500 rounded"></div>
              <span>Poor (50-74 CBI)</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-red-500 rounded"></div>
              <span>Critical (75-100 CBI)</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-gray-300 border border-gray-400 border-dashed rounded"></div>
              <span>No Data</span>
            </div>
          </div>
        </div>
        
        <div style={{ width: '100%', height: '300px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={dailyHealthData}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
              <XAxis 
                dataKey="day_name" 
                fontSize={11}
                tick={{ fill: '#6B7280' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis 
                domain={[0, 100]}
                fontSize={11}
                tick={{ fill: '#6B7280' }}
                axisLine={false}
                tickLine={false}
                label={{ 
                  value: 'Health Score', 
                  angle: -90, 
                  position: 'insideLeft',
                  style: { textAnchor: 'middle' }
                }}
              />
              <Tooltip 
                content={({ active, payload, label }) => {
                  if (active && payload && payload[0]) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-white p-3 border rounded-lg shadow-lg text-sm">
                        <p className="font-semibold text-gray-800">{data.day_name}</p>
                        {data.has_data ? (
                          <>
                            <p className="text-green-600">Health Score: {data.health_score}/100</p>
                            <p className="text-gray-600">Incidents: {data.incident_count}</p>
                            <p className="text-blue-600">Team Health: {data.team_health}/100</p>
                          </>
                        ) : (
                          <p className="text-gray-500 italic">No incident involvement this day</p>
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
              >
                {dailyHealthData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={
                      !entry.has_data ? '#E5E7EB' : // Grey for no-data days
                      entry.health_score >= 70 ? '#10B981' : 
                      entry.health_score >= 40 ? '#F59E0B' : '#EF4444'
                    }
                    stroke={!entry.has_data ? '#9CA3AF' : undefined}
                    strokeWidth={!entry.has_data ? 1 : 0}
                    strokeDasharray={!entry.has_data ? '3,3' : undefined}
                    opacity={!entry.has_data ? 0.6 : 1}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        
        <div className="mt-4 text-xs text-gray-500 space-y-1">
          <p>• Health scores calculated only for days with incident involvement</p>
          <p>• Grey bars indicate days without incident involvement - no data available</p>
          <p>• Lower scores indicate higher stress from workload, after-hours work, and response time pressure</p>
        </div>
      </div>
    </div>
  );
}

// Component to fetch and display real GitHub daily commit data
function GitHubCommitsTimeline({ analysisId, totalCommits, weekendPercentage }: {
  analysisId: number
  totalCommits: number
  weekendPercentage: number
}) {
  const [loading, setLoading] = useState(true)
  const [timelineData, setTimelineData] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTimelineData = async () => {
      if (!analysisId) {
        return
      }

      setLoading(true)
      setError(null)

      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const url = `${API_BASE}/analyses/${analysisId}/github-commits-timeline`
        
        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            'Content-Type': 'application/json'
          }
        })


        if (!response.ok) {
          throw new Error(`Failed to fetch GitHub timeline data: ${response.status}`)
        }

        const result = await response.json()
        
        if (result.status === 'success' && result.data?.daily_commits) {
          setTimelineData(result.data.daily_commits)
        } else if (result.status === 'error') {
          setError(result.message || 'Failed to fetch timeline data')
        }
      } catch (err) {
        console.error('GitHubCommitsTimeline: Error fetching timeline:', err)
        setError('Unable to load timeline data')
      } finally {
        setLoading(false)
      }
    }

    fetchTimelineData()
  }, [analysisId])

  if (loading) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
        <h4 className="text-sm font-semibold text-gray-800 mb-3">Commit Activity Timeline</h4>
        <div className="h-32 flex items-center justify-center">
          <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      </div>
    )
  }

  if (error || !timelineData || timelineData.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
        <h4 className="text-sm font-semibold text-gray-800 mb-3">Commit Activity Timeline</h4>
        <div className="h-32 flex items-center justify-center">
          <div className="text-center">
            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-2">
              <BarChart3 className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-xs text-gray-500 font-medium">
              {error || 'No timeline data available'}
            </p>
          </div>
        </div>
        <div className="mt-2 flex items-center justify-between text-xs text-gray-600">
          <span>
            Total: <strong>{totalCommits.toLocaleString()}</strong> commits
          </span>
          <span>
            Weekend: <strong>{weekendPercentage ? `${weekendPercentage.toFixed(1)}%` : 'N/A'}</strong>
          </span>
        </div>
      </div>
    )
  }

  // Transform data for the chart
  const chartData = timelineData.map(day => ({
    date: new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    commits: day.commits,
    contributors: day.unique_contributors || 0
  }))

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
      <h4 className="text-sm font-semibold text-gray-800 mb-3">Commit Activity Timeline</h4>
      <div className="h-32">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart 
            data={chartData}
            margin={{ top: 5, right: 5, left: 5, bottom: 5 }}
          >
            <defs>
              <linearGradient id="githubGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10B981" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#10B981" stopOpacity={0.1}/>
              </linearGradient>
            </defs>
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 10 }}
              interval={Math.floor(chartData.length / 7)}
            />
            <YAxis 
              tick={{ fontSize: 10 }}
              domain={[0, 'dataMax']}
            />
            <Tooltip 
              content={({ payload, label }) => {
                if (payload && payload.length > 0) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-white p-2 border border-gray-200 rounded shadow-sm">
                      <p className="text-xs font-semibold">{label}</p>
                      <p className="text-xs text-green-600">
                        {data.commits} commits
                      </p>
                      {data.contributors > 0 && (
                        <p className="text-xs text-gray-500">
                          {data.contributors} contributors
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
              stroke="#10B981" 
              strokeWidth={2}
              fill="url(#githubGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-gray-600">
        <span>
          Total: <strong>{totalCommits.toLocaleString()}</strong> commits
        </span>
        <span>
          Weekend: <strong>{weekendPercentage ? `${weekendPercentage.toFixed(1)}%` : 'N/A'}</strong>
        </span>
      </div>
    </div>
  )
}

function GitHubActivityChart({ userEmail, analysisId, memberData }: { 
  userEmail: string, 
  analysisId: number, 
  memberData: any 
}) {
  const [loading, setLoading] = useState(true)
  const [dailyData, setDailyData] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchDailyCommits = async () => {
      if (!userEmail || !analysisId) return

      setLoading(true)
      setError(null)

      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(
          `${API_BASE}/analyses/users/${encodeURIComponent(userEmail)}/github-daily-commits?analysis_id=${analysisId}`,
          {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
              'Content-Type': 'application/json'
            }
          }
        )

        if (!response.ok) {
          throw new Error('Failed to fetch GitHub daily data')
        }

        const result = await response.json()
        
        if (result.status === 'success' && result.data?.daily_commits) {
          setDailyData(result.data.daily_commits)
        } else if (result.status === 'error') {
          setError(result.message || 'Failed to fetch data')
        }
      } catch (err) {
        console.error('Error fetching GitHub daily commits:', err)
        setError('Unable to load daily commit data')
      } finally {
        setLoading(false)
      }
    }

    fetchDailyCommits()
  }, [userEmail, analysisId])

  if (loading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin text-indigo-600 mx-auto mb-2" />
          <p className="text-sm text-gray-600">Loading daily commit data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-48 flex items-center justify-center bg-white rounded-lg border-2 border-dashed border-indigo-200">
        <div className="text-center">
          <AlertTriangle className="mx-auto h-12 w-12 text-yellow-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">{error}</h3>
          <p className="mt-1 text-xs text-gray-500 max-w-xs mx-auto">
            {error === 'GitHub integration not found' 
              ? 'Please connect your GitHub account in Settings to see activity data'
              : 'Unable to retrieve daily activity data at this time'}
          </p>
        </div>
      </div>
    )
  }

  if (!dailyData || dailyData.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center bg-white rounded-lg border-2 border-dashed border-indigo-200">
        <div className="text-center">
          <svg className="mx-auto h-12 w-12 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No Commit Activity</h3>
          <p className="mt-1 text-xs text-gray-500 max-w-xs mx-auto">
            No commits found during this analysis period
          </p>
        </div>
      </div>
    )
  }

  // Transform data for the chart
  const chartData = dailyData.map(day => ({
    date: new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    commits: day.commits,
    isWeekend: new Date(day.date).getDay() === 0 || new Date(day.date).getDay() === 6,
    afterHours: day.after_hours_commits,
    weekend: day.weekend_commits
  }))

  return (
    <>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart 
            data={chartData}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="colorCommits" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366F1" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#6366F1" stopOpacity={0.1}/>
              </linearGradient>
            </defs>
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 10 }}
              interval={Math.floor(chartData.length / 7)}
            />
            <YAxis 
              tick={{ fontSize: 10 }}
              domain={[0, 'dataMax']}
            />
            <Tooltip 
              content={({ payload, label }) => {
                if (payload && payload.length > 0) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-white p-2 border border-gray-200 rounded-lg shadow-lg">
                      <p className="text-xs font-semibold text-gray-900">{label}</p>
                      <p className="text-xs text-indigo-600">
                        {data.commits} commits
                        {data.isWeekend && <span className="text-gray-500 ml-1">(Weekend)</span>}
                      </p>
                      {data.afterHours > 0 && (
                        <p className="text-xs text-gray-500">
                          {data.afterHours} after hours
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
      <div className="mt-2 text-xs text-indigo-600 text-center">
        Average: {memberData.github_activity.commits_per_week?.toFixed(1) || '0'} commits/week
        {memberData.github_activity.after_hours_commits > 0 && (
          <span className="ml-2">
            • {((memberData.github_activity.after_hours_commits / memberData.github_activity.commits_count) * 100).toFixed(0)}% after hours
          </span>
        )}
      </div>
    </>
  )
}

export default function Dashboard() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [selectedIntegration, setSelectedIntegration] = useState<string>("")
  const [loadingIntegrations, setLoadingIntegrations] = useState(false)
  const [dropdownLoading, setDropdownLoading] = useState(false)
  const [analysisRunning, setAnalysisRunning] = useState(false)
  const [analysisStage, setAnalysisStage] = useState<AnalysisStage>("loading")
  const [analysisProgress, setAnalysisProgress] = useState(0)
  const [currentRunningAnalysisId, setCurrentRunningAnalysisId] = useState<number | null>(null)
  const [currentStageIndex, setCurrentStageIndex] = useState(0)
  const [targetProgress, setTargetProgress] = useState(0)
  const [currentAnalysis, setCurrentAnalysis] = useState<AnalysisResult | null>(null)
  const [previousAnalyses, setPreviousAnalyses] = useState<AnalysisResult[]>([])
  const [selectedMember, setSelectedMember] = useState<OrganizationMember | null>(null)
  const [timeRange, setTimeRange] = useState("30")
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [analysisToDelete, setAnalysisToDelete] = useState<AnalysisResult | null>(null)
  const [debugSectionOpen, setDebugSectionOpen] = useState(false)
  // Removed member view mode - only showing radar chart now
  const [historicalTrends, setHistoricalTrends] = useState<any>(null)
  const [loadingTrends, setLoadingTrends] = useState(false)
  const [initialDataLoaded, setInitialDataLoaded] = useState(false)
  const [analysisMappings, setAnalysisMappings] = useState<any>(null)
  const [hasDataFromCache, setHasDataFromCache] = useState(false)
  
  // Mapping drawer states
  const [mappingDrawerOpen, setMappingDrawerOpen] = useState(false)
  const [mappingDrawerPlatform, setMappingDrawerPlatform] = useState<'github' | 'slack'>('github')
  
  // Data source expansion states
  const [expandedDataSources, setExpandedDataSources] = useState<{
    incident: boolean
    github: boolean
    slack: boolean
  }>({
    incident: false,
    github: false,
    slack: false
  })
  // Initialize redirectingToSuggested to true if there's an analysis ID in URL
  const [redirectingToSuggested, setRedirectingToSuggested] = useState(() => {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search)
      return urlParams.get('analysis') !== null
    }
    return false
  })
  
  const router = useRouter()
  const searchParams = useSearchParams()
  
  // Backend health monitoring - temporarily disabled
  // const { isHealthy, healthStatus } = useBackendHealth({
  //   showToasts: true,
  //   autoStart: true,
  // })

  // Function to update URL with analysis ID (UUID)
  const updateURLWithAnalysis = (analysisId: string | null) => {
    const params = new URLSearchParams(searchParams.toString())
    
    if (analysisId) {
      params.set('analysis', analysisId)
    } else {
      params.delete('analysis')
    }
    
    // Update URL without page reload
    router.push(`/dashboard?${params.toString()}`, { scroll: false })
  }

  // Function to clear integration cache
  const clearIntegrationCache = () => {
    localStorage.removeItem('all_integrations')
    localStorage.removeItem('all_integrations_timestamp')
  }

  const cancelRunningAnalysis = async () => {
    try {
      // If there's a running analysis, delete it
      if (currentRunningAnalysisId) {
        const authToken = localStorage.getItem('auth_token')
        if (authToken) {
          await fetch(`${API_BASE}/analyses/${currentRunningAnalysisId}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${authToken}`
            }
          })
          console.log(`Deleted cancelled analysis ${currentRunningAnalysisId}`)
        }
      }
    } catch (error) {
      console.warn('Failed to delete cancelled analysis:', error)
    } finally {
      // Reset all analysis state
      setAnalysisRunning(false)
      setCurrentRunningAnalysisId(null)
      setCurrentRunningAnalysisId(null)
      setAnalysisProgress(0)
      setAnalysisStage("loading")
      setCurrentStageIndex(0)
      setTargetProgress(0)
      
      // Refresh the analysis list to remove the deleted analysis
      await loadPreviousAnalyses()
    }
  }

  // Helper function to determine if insufficient data card should be shown
  const shouldShowInsufficientDataCard = () => {
    if (!currentAnalysis || analysisRunning) return false
    
    // Show for failed analyses
    if (currentAnalysis.status === 'failed') return true
    
    // Show for completed analyses with no meaningful data
    if (currentAnalysis.status === 'completed') {
      // Check if analysis_data is completely missing
      if (!currentAnalysis.analysis_data) {
        console.log('Analysis has no analysis_data - showing insufficient data card')
        return true
      }
      
      // Check if we have team_health or team_summary data but with no meaningful content
      if (currentAnalysis.analysis_data?.team_health || currentAnalysis.analysis_data?.team_summary) {
        // Check if the analysis has 0 members - this indicates insufficient data
        const teamAnalysis = currentAnalysis.analysis_data.team_analysis
        
        // Handle both array format (team_analysis directly) and object format (team_analysis.members)
        const members = Array.isArray(teamAnalysis) ? teamAnalysis : teamAnalysis?.members
        const hasNoMembers = !members || members.length === 0
        
        if (hasNoMembers) {
          return true // Show insufficient data card
        }
        
        return false // Has meaningful data - even if 0 incidents, show normal dashboard
      }
      
      // If we have partial data with incidents/users, show the partial data UI
      if (currentAnalysis.analysis_data?.partial_data) {
        return false
      }
      
      // If we have team_analysis with members, we have data
      const teamAnalysis = currentAnalysis.analysis_data?.team_analysis
      const members = Array.isArray(teamAnalysis) ? teamAnalysis : teamAnalysis?.members
      if (members && members.length > 0) {
        return false
      }
      
      // Otherwise, insufficient data
      return true
    }
    
    return false
  }

  useEffect(() => {
    // Check for organization parameter from URL
    const urlParams = new URLSearchParams(window.location.search)
    const orgId = urlParams.get('org')
    const analysisId = urlParams.get('analysis')
    
    // Add event listener for page focus to refresh integrations (less aggressive)
    const handlePageFocus = () => {
      // Only refresh if we haven't refreshed in the last 30 seconds
      const lastRefresh = localStorage.getItem('last_integrations_refresh')
      const now = Date.now()
      if (!lastRefresh || now - parseInt(lastRefresh) > 30000) {
        console.log('Page focused, refreshing integrations (30s throttle)')
        localStorage.setItem('last_integrations_refresh', now.toString())
        loadIntegrations(true, false)
      }
    }

    // Load cached integrations FIRST (before event listeners)
    const cachedIntegrations = localStorage.getItem('all_integrations')
    const cacheTimestamp = localStorage.getItem('all_integrations_timestamp')
    
    if (cachedIntegrations && cacheTimestamp) {
      // Check if cache is less than 5 minutes old for more frequent updates
      const cacheAge = Date.now() - parseInt(cacheTimestamp)
      const fiveMinutes = 5 * 60 * 1000
      
      if (cacheAge < fiveMinutes) {
        try {
          const parsed = JSON.parse(cachedIntegrations)
          setIntegrations(parsed)
          console.log('🚀 DASHBOARD CACHE: Loaded', parsed.length, 'integrations from cache instantly')
          
          // Also load GitHub and Slack from cache if available
          const cachedGithub = localStorage.getItem('github_integration')
          const cachedSlack = localStorage.getItem('slack_integration')
          
          if (cachedGithub) {
            const githubData = JSON.parse(cachedGithub)
            if (githubData.connected && githubData.integration) {
              setGithubIntegration(githubData.integration)
            } else {
              setGithubIntegration(null)
            }
          }
          
          if (cachedSlack) {
            const slackData = JSON.parse(cachedSlack)
            if (slackData.connected && slackData.integration) {
              setSlackIntegration(slackData.integration)
            } else {
              setSlackIntegration(null)
            }
          }
          
          // Set integration based on URL parameter, saved preference, or first available
          if (orgId) {
            setSelectedIntegration(orgId)
            // Save this selection for future use
            localStorage.setItem('selected_organization', orgId)
          } else {
            // Check for saved organization preference
            const savedOrg = localStorage.getItem('selected_organization')
            if (savedOrg && parsed.find((i: Integration) => i.id.toString() === savedOrg)) {
              setSelectedIntegration(savedOrg)
            } else if (parsed.length > 0) {
              // Fall back to first available organization
              setSelectedIntegration(parsed[0].id.toString())
              localStorage.setItem('selected_organization', parsed[0].id.toString())
            }
          }
        } catch (e) {
          console.error('Failed to parse cached integrations:', e)
        }
        
        // Set loading to false when using cache
        setLoadingIntegrations(false)
        setHasDataFromCache(true)
        
        // Still need to load previous analyses and trends even if integrations are cached
        loadPreviousAnalyses()
        loadHistoricalTrends()
        
        return // Exit early since we used cache
      }
    }
    
    // Add event listeners for page focus/visibility changes
    window.addEventListener('focus', handlePageFocus)
    const visibilityHandler = () => {
      if (!document.hidden) {
        handlePageFocus()
      }
    }
    document.addEventListener('visibilitychange', visibilityHandler)
    
    const loadInitialData = async () => {
      try {
        // If we already have cached data, mark as loaded immediately
        if (hasDataFromCache) {
          setInitialDataLoaded(true)
          return
        }
        
        // Load data with individual error handling to prevent blocking
        const results = await Promise.allSettled([
          loadPreviousAnalyses(),
          loadIntegrations(false, false), // Don't force refresh, don't show global loading
          loadHistoricalTrends()
        ])
        
        // Log any failures but don't block the UI
        results.forEach((result, index) => {
          const functionNames = ['loadPreviousAnalyses', 'loadIntegrations', 'loadHistoricalTrends']
          if (result.status === 'rejected') {
            console.error(`${functionNames[index]} failed:`, result.reason)
          }
        })
        
        // Small delay to ensure state updates have propagated
        setTimeout(() => {
          setInitialDataLoaded(true)
        }, 100)
      } catch (error) {
        console.error('Error loading initial data:', error)
        // Always set to true to prevent endless loading, even if some data fails
        setInitialDataLoaded(true)
      }
    }
    
    loadInitialData()
    
    // Fallback timeout to prevent endless loading (max 15 seconds)
    const timeoutId = setTimeout(() => {
      console.warn('Initial data loading timed out after 15 seconds')
      setInitialDataLoaded(true)
    }, 15000)

    // Listen for localStorage changes (when integrations are updated on other pages)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'all_integrations' && e.newValue) {
        console.log('Detected integration cache update, refreshing...')
        try {
          const updatedIntegrations = JSON.parse(e.newValue)
          setIntegrations(updatedIntegrations)
          
          // Also check for GitHub/Slack updates
          const githubCache = localStorage.getItem('github_integration')
          const slackCache = localStorage.getItem('slack_integration')
          
          if (githubCache) {
            const githubData = JSON.parse(githubCache)
            setGithubIntegration(githubData.connected ? githubData.integration : null)
          }
          
          if (slackCache) {
            const slackData = JSON.parse(slackCache)
            setSlackIntegration(slackData.integration)
          }
        } catch (e) {
          console.error('Failed to parse updated integrations:', e)
        }
      }
    }
    
    window.addEventListener('storage', handleStorageChange)

    // Cleanup event listeners and timeout
    return () => {
      window.removeEventListener('focus', handlePageFocus)
      document.removeEventListener('visibilitychange', visibilityHandler)
      window.removeEventListener('storage', handleStorageChange)
      clearTimeout(timeoutId)
    }
  }, [])

  // Check if URL analysis exists in loaded analyses and show loader if not
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const analysisId = urlParams.get('analysis')
    
    if (analysisId && previousAnalyses.length > 0 && !redirectingToSuggested) {
      // Check if this analysis ID exists in our current analyses list
      const analysisExists = previousAnalyses.some(analysis => 
        analysis.id.toString() === analysisId || 
        (analysis.uuid && analysis.uuid === analysisId)
      )
      
      // If this ID doesn't exist, show loader immediately
      if (!analysisExists) {
        console.log(`Analysis ${analysisId} not found in loaded analyses, showing redirect loader`)
        setRedirectingToSuggested(true)
      }
    }
  }, [previousAnalyses, redirectingToSuggested])

  // Load specific analysis from URL - with delay to ensure auth token is available
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const analysisId = urlParams.get('analysis')
    
    if (analysisId) {
      // Small delay to ensure auth token and integrations are loaded
      const loadAnalysisWithDelay = () => {
        const authToken = localStorage.getItem('auth_token')
        if (authToken) {
          console.log('Loading specific analysis from URL:', analysisId)
          loadSpecificAnalysis(analysisId)
        } else {
          console.warn('Auth token not yet available, retrying in 500ms...')
          // Retry after another short delay
          setTimeout(loadAnalysisWithDelay, 500)
        }
      }
      
      // Initial delay to let other useEffects run first
      setTimeout(loadAnalysisWithDelay, 100)
    }
  }, []) // Only run once on mount

  // Smooth progress animation effect
  useEffect(() => {
    if (!analysisRunning) return

    const interval = setInterval(() => {
      setAnalysisProgress(currentProgress => {
        if (currentProgress < targetProgress) {
          // Increment by 1 towards target, with small random variations
          const increment = Math.random() > 0.7 ? 2 : 1 // Occasionally jump by 2
          return Math.min(currentProgress + increment, targetProgress)
        }
        return currentProgress
      })
    }, 200) // Update every 200ms for smooth animation

    return () => clearInterval(interval)
  }, [analysisRunning, targetProgress])

  // Only load historical trends when we have a valid current analysis
  useEffect(() => {
    if (currentAnalysis && currentAnalysis.status === 'completed') {
      loadHistoricalTrends()
    } else {
      // Clear trends data when no valid analysis
      setHistoricalTrends(null)
    }
  }, [currentAnalysis])

  // Load platform mappings on component mount (same as integrations page)
  useEffect(() => {
    fetchPlatformMappings()
  }, [])

  const loadPreviousAnalyses = async () => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        console.warn('No auth token found, skipping previous analyses load')
        return
      }

      console.log('Loading previous analyses...')
      let response
      try {
        response = await fetch(`${API_BASE}/analyses`, {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        })
      } catch (networkError) {
        console.error('Network error loading analyses:', networkError)
        throw new Error('Cannot connect to backend server')
      }

      if (response.ok) {
        const data = await response.json()
        console.log('Loaded analyses:', data.analyses?.length || 0, 'analyses')
        console.log('Previous analyses data:', data.analyses)
        setPreviousAnalyses(data.analyses || [])
        
        // If no specific analysis is loaded and we have analyses, load the most recent one
        const urlParams = new URLSearchParams(window.location.search)
        const analysisId = urlParams.get('analysis')
        
        if (!analysisId && data.analyses && data.analyses.length > 0 && !currentAnalysis) {
          const mostRecentAnalysis = data.analyses[0] // Analyses should be ordered by created_at desc
          console.log('Auto-loading most recent analysis:', mostRecentAnalysis.id)
          setCurrentAnalysis(mostRecentAnalysis)
          // Fetch platform mappings (same as integrations page)
          fetchPlatformMappings()
        }
      } else {
        console.error('Failed to load analyses, status:', response.status)
      }
    } catch (error) {
      console.error('Failed to load previous analyses:', error)
      
      // Check if this is a network connectivity issue
      const isNetworkError = error instanceof Error && (
        error.message.includes('fetch') || 
        error.message.includes('network') ||
        error.message.includes('Failed to fetch') ||
        error.name === 'TypeError'
      )
      
      if (isNetworkError) {
        toast.error("Cannot connect to backend")
      }
    }
  }

  const loadSpecificAnalysis = async (analysisId: string) => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        console.warn('loadSpecificAnalysis called but no auth token available')
        return
      }

      // Check if analysisId is a UUID (contains hyphens) or integer ID
      const isUuid = analysisId.includes('-')

      // Use the unified endpoint that handles both UUIDs and integer IDs
      const endpoint = `${API_BASE}/analyses/by-id/${analysisId}`
      
      console.log(`Making API call to load analysis: ${endpoint}`)
      const response = await fetch(endpoint, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        const analysis = await response.json()
        console.log('Loaded specific analysis from URL:', analysis.uuid || analysis.id)
        setCurrentAnalysis(analysis)
        // Fetch platform mappings (same as integrations page)
        fetchPlatformMappings()
        // Turn off redirect loader since we successfully loaded the analysis
        setRedirectingToSuggested(false)
        // Update URL to use UUID if we loaded by integer ID
        if (!isUuid && analysis.uuid) {
          updateURLWithAnalysis(analysis.uuid || analysis.id)
        }
      } else {
        console.error('Failed to load analysis:', analysisId, 'Status:', response.status)
        
        // Show user-friendly error message and handle suggested redirect
        if (response.status === 404) {
          try {
            const errorData = await response.json()
            console.warn(`Analysis ${analysisId} not found:`, errorData.detail)
            console.log('Attempting to parse suggestion from error response:', errorData)
            
            // Check if backend provided a suggested analysis ID
            const suggestionMatch = errorData.detail?.match(/Most recent analysis available: (.+)$/)
            if (suggestionMatch && suggestionMatch[1]) {
              const suggestedId = suggestionMatch[1]
              console.log(`Backend suggested redirecting to analysis: ${suggestedId}`)
              
              // Set redirect state to show loader instead of error (don't clear analysis yet)
              setRedirectingToSuggested(true)
              
              // Auto-redirect to suggested analysis after a brief delay
              setTimeout(() => {
                console.log(`Auto-redirecting to suggested analysis: ${suggestedId}`)
                updateURLWithAnalysis(suggestedId)
                loadSpecificAnalysis(suggestedId)
                setRedirectingToSuggested(false)
              }, 1000) // Reduced to 1 second since we're showing a loader
              
              return // Exit early to prevent clearing analysis state
            }
          } catch (parseError) {
            console.warn(`Analysis ${analysisId} not found. Please select a valid analysis from the history.`)
          }
        }
        
        // Only clear analysis state if we couldn't auto-redirect
        setCurrentAnalysis(null)
        setHistoricalTrends(null)
        // Remove invalid analysis ID from URL
        updateURLWithAnalysis(null)
      }
    } catch (error) {
      console.error('Error loading specific analysis:', error)
    }
  }

  const loadHistoricalTrends = async () => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        console.error('No auth token found in localStorage')
        return
      }
      
      console.log('Auth token found:', authToken ? `${authToken.substring(0, 10)}...` : 'null')

      setLoadingTrends(true)
      console.log('Loading historical trends...')
      
      // Use 30 days to get more historical data points for all integrations
      const params = new URLSearchParams({ days_back: '30' })
      // No integration filtering - show data from all integrations

      const fullUrl = `${API_BASE}/analyses/trends/historical?${params}`
      console.log('Making request to:', fullUrl)
      console.log('API_BASE:', API_BASE)
      console.log('Params:', params.toString())
      
      // Test the main analyses endpoint with same auth token to verify auth works
      console.log('Testing main analyses endpoint with same token...')
      try {
        const testResponse = await fetch(`${API_BASE}/analyses`, {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        })
        console.log('Main analyses endpoint test status:', testResponse.status)
      } catch (testError) {
        console.log('Main analyses endpoint test error:', testError)
      }
      
      let response
      try {
        response = await fetch(fullUrl, {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        })
      } catch (networkError) {
        console.error('Network error loading trends:', networkError)
        throw new Error('Cannot connect to backend server')
      }

      if (response.ok) {
        const data = await response.json()
        console.log('Loaded historical trends:', data)
        setHistoricalTrends(data)
      } else {
        console.error('Failed to load trends, status:', response.status)
        console.error('Response URL:', response.url)
        console.error('Response headers:', [...response.headers.entries()])
        const errorText = await response.text()
        console.error('Response body:', errorText)
      }
    } catch (error) {
      console.error('Failed to load historical trends:', error)
    } finally {
      setLoadingTrends(false)
    }
  }

  const openDeleteDialog = (analysis: AnalysisResult, event: React.MouseEvent) => {
    event.stopPropagation() // Prevent triggering the analysis selection
    setAnalysisToDelete(analysis)
    setDeleteDialogOpen(true)
  }

  const confirmDeleteAnalysis = async () => {
    if (!analysisToDelete) return

    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      console.log('Deleting analysis:', analysisToDelete.id)
      
      const response = await fetch(`${API_BASE}/analyses/${analysisToDelete.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      console.log('Delete response status:', response.status)

      if (response.ok) {
        console.log('Delete successful, updating local state...')
        console.log('Current analyses before delete:', previousAnalyses.map(a => ({id: a.id, integration_id: a.integration_id})))
        console.log('Deleting analysis with ID:', analysisToDelete.id, 'type:', typeof analysisToDelete.id)
        
        // Immediately remove from local state - be more explicit about ID matching
        setPreviousAnalyses(prev => {
          const filtered = prev.filter(a => {
            const match = a.id === analysisToDelete.id || String(a.id) === String(analysisToDelete.id)
            console.log(`Comparing ${a.id} (${typeof a.id}) with ${analysisToDelete.id} (${typeof analysisToDelete.id}): ${match ? 'REMOVE' : 'KEEP'}`)
            return !match
          })
          console.log('Filtered analyses:', filtered.map(a => ({id: a.id, integration_id: a.integration_id})))
          return filtered
        })
        
        // If the deleted analysis was currently selected, clear it
        if (currentAnalysis?.id === analysisToDelete.id) {
          console.log('Clearing currently selected analysis')
          setCurrentAnalysis(null)
          updateURLWithAnalysis(null)
        }
        
        toast.success("Analysis deleted")
        
        // Close dialog and reset state
        setDeleteDialogOpen(false)
        setAnalysisToDelete(null)
        
        // Also reload from server to ensure consistency
        console.log('Reloading analyses list from server...')
        setTimeout(() => loadPreviousAnalyses(), 500)
        
      } else {
        const errorData = await response.json()
        console.error('Delete failed:', errorData)
        throw new Error(errorData.detail || 'Failed to delete analysis')
      }
    } catch (error) {
      console.error('Delete error:', error)
      toast.error(error instanceof Error ? error.message : "Failed to delete analysis")
      setDeleteDialogOpen(false)
      setAnalysisToDelete(null)
    }
  }

  // Function to fetch platform mappings (same as integrations page)
  const fetchPlatformMappings = async () => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return
      
      // Fetch both GitHub and Slack mappings like the integrations page does
      const [githubResponse, slackResponse] = await Promise.all([
        fetch(`${API_BASE}/integrations/mappings/platform/github`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        }),
        fetch(`${API_BASE}/integrations/mappings/platform/slack`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        })
      ])
      
      let allMappings: any[] = []
      
      if (githubResponse.ok) {
        const githubMappings = await githubResponse.json()
        console.log('📊 GitHub mappings from platform endpoint:', githubMappings)
        allMappings = allMappings.concat(githubMappings)
      }
      
      if (slackResponse.ok) {
        const slackMappings = await slackResponse.json()
        console.log('📊 Slack mappings from platform endpoint:', slackMappings)
        allMappings = allMappings.concat(slackMappings)
      }
      
      console.log('📊 All platform mappings loaded (same as integrations page):', allMappings)
      setAnalysisMappings({ mappings: allMappings })
    } catch (error) {
      console.error('Error fetching platform mappings:', error)
    }
  }

  // Helper function to check if user has GitHub mapping (only if actually mapped)
  const hasGitHubMapping = (userEmail: string) => {
    if (!analysisMappings?.mappings) {
      console.log('🔍 No mappings data available yet for', userEmail)
      return false
    }
    
    const hasMapping = analysisMappings.mappings.some((mapping: any) => 
      mapping.source_identifier === userEmail && 
      mapping.target_platform === "github" &&
      mapping.target_identifier && // Must have a target identifier
      mapping.target_identifier !== "unknown" && // Must not be "unknown"
      mapping.target_identifier.trim() !== "" // Must not be empty
    )
    
    console.log(`🔍 GitHub mapping check for ${userEmail}:`, hasMapping)
    return hasMapping
  }

  // Helper function to check if user has Slack mapping (only if actually mapped)
  const hasSlackMapping = (userEmail: string) => {
    if (!analysisMappings?.mappings) return false
    
    return analysisMappings.mappings.some((mapping: any) => 
      mapping.source_identifier === userEmail && 
      mapping.target_platform === "slack" &&
      mapping.target_identifier && // Must have a target identifier
      mapping.target_identifier !== "unknown" && // Must not be "unknown"
      mapping.target_identifier.trim() !== "" // Must not be empty
    )
  }

  // Functions to open mapping drawer
  const openMappingDrawer = (platform: 'github' | 'slack') => {
    console.log(`🎯 Dashboard: openMappingDrawer called with platform: ${platform}`)
    setMappingDrawerPlatform(platform)
    setMappingDrawerOpen(true)
    console.log(`🎯 Dashboard: Set mappingDrawerPlatform to ${platform} and mappingDrawerOpen to true`)
  }

  const loadIntegrations = async (forceRefresh = false, showGlobalLoading = true) => {
    // Check if we have valid cached data and don't need to refresh
    if (!forceRefresh && integrations.length > 0) {
      return
    }

    // Check localStorage cache
    if (!forceRefresh) {
      const cachedIntegrations = localStorage.getItem('all_integrations')
      const cacheTimestamp = localStorage.getItem('all_integrations_timestamp')
      
      if (cachedIntegrations && cacheTimestamp) {
        const cacheAge = Date.now() - parseInt(cacheTimestamp)
        const fiveMinutes = 5 * 60 * 1000
        
        if (cacheAge < fiveMinutes) {
          try {
            const cached = JSON.parse(cachedIntegrations)
            setIntegrations(cached)
            
            // Also load GitHub and Slack from cache if available
            const cachedGithub = localStorage.getItem('github_integration')
            const cachedSlack = localStorage.getItem('slack_integration')
            
            if (cachedGithub) {
              const githubData = JSON.parse(cachedGithub)
              if (githubData.connected && githubData.integration) {
                setGithubIntegration(githubData.integration)
              } else {
                setGithubIntegration(null)
              }
            }
            
            if (cachedSlack) {
              const slackData = JSON.parse(cachedSlack)
              if (slackData.connected && slackData.integration) {
                setSlackIntegration(slackData.integration)
              } else {
                setSlackIntegration(null)
              }
            }
            
            // Set integration based on saved preference
            const savedOrg = localStorage.getItem('selected_organization')
            if (savedOrg && cached.find((i: Integration) => i.id.toString() === savedOrg)) {
              setSelectedIntegration(savedOrg)
            } else if (cached.length > 0) {
              setSelectedIntegration(cached[0].id.toString())
              localStorage.setItem('selected_organization', cached[0].id.toString())
            }
            
            // Set loading to false when using cache
            setLoadingIntegrations(false)
            setHasDataFromCache(true)
            
            // Still need to load previous analyses and trends even if integrations are cached
            loadPreviousAnalyses()
            loadHistoricalTrends()
            
            return
          } catch (error) {
            console.error('Failed to parse cached integrations:', error)
            // Continue to fetch fresh data
          }
        }
      }
    }

    // Only show global loading if requested and we don't have any integrations yet
    if (showGlobalLoading && integrations.length === 0) {
      setLoadingIntegrations(true)
    }

    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        router.push('/auth/login')
        return
      }

      // Load both Rootly, PagerDuty, GitHub, and Slack integrations
      console.log('Fetching integrations from:', {
        rootlyUrl: `${API_BASE}/rootly/integrations`,
        pagerdutyUrl: `${API_BASE}/pagerduty/integrations`,
        githubUrl: `${API_BASE}/integrations/github/status`,
        slackUrl: `${API_BASE}/integrations/slack/status`
      })
      
      let rootlyResponse, pagerdutyResponse, githubResponse, slackResponse
      try {
        [rootlyResponse, pagerdutyResponse, githubResponse, slackResponse] = await Promise.all([
          fetch(`${API_BASE}/rootly/integrations`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
          }),
          fetch(`${API_BASE}/pagerduty/integrations`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
          }),
          fetch(`${API_BASE}/integrations/github/status`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
          }),
          fetch(`${API_BASE}/integrations/slack/status`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
          })
        ])
      } catch (networkError) {
        console.error('Network error fetching integrations:', networkError)
        throw new Error('Cannot connect to backend server. Please check if the backend is running and try again.')
      }

      const rootlyData = rootlyResponse.ok ? await rootlyResponse.json() : { integrations: [] }
      const pagerdutyData = pagerdutyResponse.ok ? await pagerdutyResponse.json() : { integrations: [] }
      const githubData = githubResponse.ok ? await githubResponse.json() : { connected: false, integration: null }
      const slackData = slackResponse.ok ? await slackResponse.json() : { connected: false, integration: null }

      console.log('Raw API responses:', {
        rootlyResponse: { ok: rootlyResponse.ok, status: rootlyResponse.status },
        pagerdutyResponse: { ok: pagerdutyResponse.ok, status: pagerdutyResponse.status },
        githubResponse: { ok: githubResponse.ok, status: githubResponse.status },
        slackResponse: { ok: slackResponse.ok, status: slackResponse.status },
        rootlyData: rootlyData,
        pagerdutyData: pagerdutyData,
        githubData: githubData,
        slackData: slackData
      })

      // Set GitHub and Slack integration states
      if (githubData.connected && githubData.integration) {
        setGithubIntegration(githubData.integration)
      } else {
        setGithubIntegration(null)
      }
      
      if (slackData.connected && slackData.integration) {
        setSlackIntegration(slackData.integration)
      } else {
        setSlackIntegration(null)
      }
      
      // Cache GitHub and Slack integration status separately
      localStorage.setItem('github_integration', JSON.stringify(githubData))
      localStorage.setItem('slack_integration', JSON.stringify(slackData))

      // Ensure platform is set
      const rootlyIntegrations = (rootlyData.integrations || []).map((i: Integration, index: number) => {
        console.log(`Rootly integration ${index}:`, { id: i.id, name: i.name, originalPlatform: i.platform })
        return { ...i, platform: 'rootly' as const }
      })
      const pagerdutyIntegrations = (pagerdutyData.integrations || []).map((i: Integration, index: number) => {
        console.log(`PagerDuty integration ${index}:`, { id: i.id, name: i.name, originalPlatform: i.platform })
        return { ...i, platform: 'pagerduty' as const }
      })
      
      const allIntegrations = [...rootlyIntegrations, ...pagerdutyIntegrations]
      
      console.log('Processed integrations:', {
        rootlyCount: rootlyIntegrations.length,
        pagerdutyCount: pagerdutyIntegrations.length,
        totalCount: allIntegrations.length,
        rootlyIntegrations: rootlyIntegrations.map(i => ({ id: i.id, name: i.name, platform: i.platform })),
        pagerdutyIntegrations: pagerdutyIntegrations.map(i => ({ id: i.id, name: i.name, platform: i.platform }))
      })
      setIntegrations(allIntegrations)
      
      // Cache the integrations
      localStorage.setItem('all_integrations', JSON.stringify(allIntegrations))
      localStorage.setItem('all_integrations_timestamp', Date.now().toString())
        
      // Set integration based on saved preference if not already set
      if (!selectedIntegration) {
        const savedOrg = localStorage.getItem('selected_organization')
        if (savedOrg && allIntegrations.find((i: Integration) => i.id.toString() === savedOrg)) {
          setSelectedIntegration(savedOrg)
        } else if (allIntegrations.length > 0) {
          setSelectedIntegration(allIntegrations[0].id.toString())
          localStorage.setItem('selected_organization', allIntegrations[0].id.toString())
        }
      }
    } catch (error) {
      console.error('Failed to load integrations:', error)
      
      // Check if this is a network connectivity issue
      const isNetworkError = error instanceof Error && (
        error.message.includes('fetch') || 
        error.message.includes('network') ||
        error.message.includes('Failed to fetch') ||
        error.name === 'TypeError'
      )
      
      toast.error(isNetworkError ? "Cannot connect to backend server" : "Failed to load integrations")
    } finally {
      setLoadingIntegrations(false)
    }
  }

  // Format radar chart labels to fit in multiple lines
  const formatRadarLabel = (value: string) => {
    // If text is short enough, keep it as is
    if (value.length <= 8) return value;
    
    const words = value.split(' ');
    if (words.length <= 1) {
      // Single long word - try to break it intelligently
      if (value.length > 10) {
        const mid = Math.floor(value.length / 2);
        return `${value.substring(0, mid)}\n${value.substring(mid)}`;
      }
      return value;
    }
    
    // For multiple words, put each word on separate line if reasonable
    if (words.length === 2) {
      return `${words[0]}\n${words[1]}`;
    }
    
    // For more words, split in half
    const midpoint = Math.ceil(words.length / 2);
    const firstLine = words.slice(0, midpoint).join(' ');
    const secondLine = words.slice(midpoint).join(' ');
    
    return `${firstLine}\n${secondLine}`;
  };

  // Accurate analysis stages based on actual backend workflow and data sources
  const getAnalysisStages = () => {
    const stages = [
      { key: "loading", label: "Initializing Analysis", detail: "Setting up analysis parameters", progress: 5 },
      { key: "connecting", label: "Connecting to Platform", detail: "Validating API credentials", progress: 12 },
      { key: "fetching_users", label: "Fetching Organization Members", detail: "Loading user profiles and permissions", progress: 20 },
      { key: "fetching", label: "Collecting Incident Data", detail: "Gathering 30-day incident history", progress: 35 }
    ]

    let currentProgress = 35
    const hasGithub = includeGithub && githubIntegration
    const hasSlack = includeSlack && slackIntegration  
    const hasAI = enableAI

    // Add GitHub data collection if enabled (Step 2 extension)
    if (hasGithub) {
      stages.push({
        key: "fetching_github",
        label: "Collecting GitHub Data",
        detail: "Gathering commits, PRs, and code review patterns", 
        progress: 45
      })
      currentProgress = 45
    }

    // Add Slack data collection if enabled (Step 2 extension)  
    if (hasSlack) {
      stages.push({
        key: "fetching_slack",
        label: "Collecting Slack Data",
        detail: "Gathering messaging patterns and team communication",
        progress: hasGithub ? 52 : 45
      })
      currentProgress = hasGithub ? 52 : 45
    }

    // Backend Step 3: Team analysis (main processing phase)
    stages.push({
      key: "analyzing_team",
      label: "Analyzing Team Data", 
      detail: "Processing incidents and calculating member metrics",
      progress: currentProgress + 15
    })
    currentProgress += 15

    // Backend Step 4: Team health calculation
    stages.push({
      key: "calculating_health",
      label: "Calculating Team Health",
      detail: "Computing burnout scores and risk levels", 
      progress: currentProgress + 10
    })
    currentProgress += 10

    // Backend Step 5: Insights generation
    stages.push({
      key: "generating_insights",
      label: "Generating Insights",
      detail: "Analyzing patterns and creating recommendations",
      progress: currentProgress + 8
    })
    currentProgress += 8

    // Backend Step 7: AI enhancement (if enabled)
    if (hasAI) {
      stages.push({
        key: "ai_analysis", 
        label: "AI Team Analysis",
        detail: "Generating intelligent insights and narratives",
        progress: currentProgress + 12
      })
      currentProgress += 12
    }

    // Final preparation 
    stages.push({
      key: "preparing",
      label: "Finalizing Analysis",
      detail: "Preparing results",
      progress: 95
    })

    stages.push({
      key: "complete",
      label: "Analysis Complete",
      detail: "Results ready",
      progress: 100
    })

    return stages
  }

  const getAnalysisDescription = () => {
    const sources = []
    sources.push("incident response patterns")
    if (includeGithub && githubIntegration) sources.push("code activity")
    if (includeSlack && slackIntegration) sources.push("communication patterns")
    
    if (sources.length === 1) return sources[0]
    if (sources.length === 2) return `${sources[0]} and ${sources[1]}`
    return `${sources.slice(0, -1).join(", ")}, and ${sources[sources.length - 1]}`
  }

  const [showTimeRangeDialog, setShowTimeRangeDialog] = useState(false)
  const [selectedTimeRange, setSelectedTimeRange] = useState("30")
  const [dialogSelectedIntegration, setDialogSelectedIntegration] = useState<string>("")
  
  // GitHub/Slack integration states
  const [githubIntegration, setGithubIntegration] = useState<GitHubIntegration | null>(null)
  const [slackIntegration, setSlackIntegration] = useState<SlackIntegration | null>(null)
  const [includeGithub, setIncludeGithub] = useState(true)
  const [includeSlack, setIncludeSlack] = useState(true)
  const [enableAI, setEnableAI] = useState(true)
  const [llmConfig, setLlmConfig] = useState<{has_token: boolean, provider?: string} | null>(null)
  const [isLoadingGitHubSlack, setIsLoadingGitHubSlack] = useState(false)

  // Load LLM configuration
  const loadLlmConfig = async () => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      let response
      try {
        response = await fetch(`${API_BASE}/llm/token`, {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        })
      } catch (networkError) {
        console.error('Network error loading LLM config:', networkError)
        throw new Error('Cannot connect to backend server')
      }

      if (response.ok) {
        const config = await response.json()
        setLlmConfig(config)
      }
    } catch (error) {
      console.error('Failed to load LLM config:', error)
      
      // Check if this is a network connectivity issue
      const isNetworkError = error instanceof Error && (
        error.message.includes('fetch') || 
        error.message.includes('network') ||
        error.message.includes('Failed to fetch') ||
        error.name === 'TypeError'
      )
      
      if (isNetworkError) {
        toast.error("Cannot connect to backend")
      }
    }
  }

  const startAnalysis = async () => {
    // Check if we have basic integrations cached
    if (integrations.length === 0) {
      // Check if we have cached data in localStorage first
      const cachedIntegrations = localStorage.getItem('all_integrations')
      const cacheTimestamp = localStorage.getItem('all_integrations_timestamp')
      
      if (cachedIntegrations && cacheTimestamp) {
        const cacheAge = Date.now() - parseInt(cacheTimestamp)
        if (cacheAge < 5 * 60 * 1000) { // 5 minutes
          console.log('🔍 DEBUG: Using cached integrations data for modal')
          // Load from cache without API call
          const cached = JSON.parse(cachedIntegrations)
          const rootlyIntegrations = Array.isArray(cached.rootly) ? cached.rootly : []
          const pagerdutyIntegrations = Array.isArray(cached.pagerduty) ? cached.pagerduty : []
          setIntegrations(rootlyIntegrations.concat(pagerdutyIntegrations))
          setGithubIntegration(cached.github?.connected ? cached.github.integration : null)
          setSlackIntegration(cached.slack?.integration || null)
        } else {
          // Cache is stale, need to load fresh data
          console.log('🔍 DEBUG: Cache is stale, loading fresh integrations data')
          await loadIntegrations(true, false) // Force refresh but don't show global loading
        }
      } else {
        // No cache, need to load fresh data  
        console.log('🔍 DEBUG: No cache found, loading fresh integrations data')
        await loadIntegrations(true, false) // Force refresh but don't show global loading
      }
      
      if (integrations.length === 0) {
        toast.error("No integrations found - please add an integration first")
        return
      }
    } else {
      console.log('🔍 DEBUG: Using existing integrations data, no loading needed')
    }

    // If no integration selected but we have integrations available, auto-select the first one
    let integrationToUse = selectedIntegration
    if (!integrationToUse && integrations.length > 0) {
      // Use saved preference or first available
      const savedOrg = localStorage.getItem('selected_organization')
      if (savedOrg && integrations.find(i => i.id.toString() === savedOrg)) {
        integrationToUse = savedOrg
      } else {
        integrationToUse = integrations[0].id.toString()
        localStorage.setItem('selected_organization', integrationToUse)
      }
      setSelectedIntegration(integrationToUse)
    }

    if (!integrationToUse) {
      toast.error("No integration available")
      return
    }

    // Set the dialog integration to the currently selected one by default
    setDialogSelectedIntegration(integrationToUse)
    setShowTimeRangeDialog(true)

    // Load cached GitHub/Slack data immediately if we don't have it in state
    if (!githubIntegration || !slackIntegration) {
      const cachedGitHub = localStorage.getItem('github_integration')
      const cachedSlack = localStorage.getItem('slack_integration')
      
      if (cachedGitHub && !githubIntegration) {
        try {
          setGithubIntegration(JSON.parse(cachedGitHub))
        } catch (e) {
          console.error('Error parsing cached GitHub integration:', e)
        }
      }
      
      if (cachedSlack && !slackIntegration) {
        try {
          setSlackIntegration(JSON.parse(cachedSlack))
        } catch (e) {
          console.error('Error parsing cached Slack integration:', e)
        }
      }
    }

    // Check cache validity for GitHub/Slack data
    const lastIntegrationsLoad = localStorage.getItem('all_integrations_timestamp')
    const integrationsCacheAge = lastIntegrationsLoad ? Date.now() - parseInt(lastIntegrationsLoad) : Infinity
    const integrationsCacheValid = integrationsCacheAge < 15 * 60 * 1000 // 15 minutes (increased from 5)
    
    // Only load GitHub/Slack data if we don't have it in state yet
    // The modal can function without this data - it's only needed for the toggle switches
    const needsGitHubSlackData = (!githubIntegration || !slackIntegration) && !integrationsCacheValid
    const needsLlmConfig = !llmConfig
    
    if (needsGitHubSlackData || needsLlmConfig) {
      setIsLoadingGitHubSlack(true)
      
      const promises = []
      if (needsGitHubSlackData) {
        console.log('🔍 DEBUG: Loading GitHub/Slack data for toggle switches')
        promises.push(loadIntegrations(true, false)) // Refresh integrations without showing loading
      }
      if (needsLlmConfig) {
        console.log('🔍 DEBUG: Loading LLM config')
        promises.push(loadLlmConfig())
      }
      
      Promise.all(promises).then(() => {
        setIsLoadingGitHubSlack(false)
      }).catch(err => {
        console.error('Error loading modal data:', err)
        setIsLoadingGitHubSlack(false)
      })
    } else {
      console.log('🔍 DEBUG: GitHub/Slack/LLM data available, no loading needed')
    }
  }

  const runAnalysisWithTimeRange = async () => {
    // Check permissions before running - only for Rootly integrations
    const selectedIntegration = integrations.find(i => i.id.toString() === dialogSelectedIntegration);
    
    // Only check permissions for Rootly integrations, not PagerDuty
    if (selectedIntegration?.platform === 'rootly') {
      const hasUserPermission = selectedIntegration?.permissions?.users?.access;
      const hasIncidentPermission = selectedIntegration?.permissions?.incidents?.access;
      
      if (!hasUserPermission || !hasIncidentPermission) {
        toast.error("Missing required permissions - update API token")
        return;
      }
    }
    
    setShowTimeRangeDialog(false)
    setTimeRange(selectedTimeRange)
    setAnalysisRunning(true)
    setAnalysisStage("loading")
    setAnalysisProgress(0)
    setTargetProgress(5) // Initial target
    setCurrentStageIndex(0)

    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        throw new Error('No authentication token found')
      }

      // Debug log the request data
      // Handle both string (beta) and numeric (regular) integration IDs
      const integrationId = isNaN(parseInt(dialogSelectedIntegration)) 
        ? dialogSelectedIntegration  // Keep as string for beta integrations
        : parseInt(dialogSelectedIntegration);  // Convert to number for regular integrations
      
      const requestData = {
        integration_id: integrationId,
        time_range: parseInt(selectedTimeRange),
        include_weekends: true,
        include_github: githubIntegration ? includeGithub : false,
        include_slack: slackIntegration ? includeSlack : false,
        enable_ai: enableAI  // User can toggle, uses Railway token when enabled
      }
      
      console.log('DEBUG: Analysis request data:', requestData)
      console.log('DEBUG: State values:', {
        githubIntegration,
        slackIntegration,
        includeGithub,
        includeSlack,
        enableAI,
        llmConfig
      })

      // Start the analysis
      let response
      try {
        response = await fetch(`${API_BASE}/analyses/run`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify(requestData),
        })
      } catch (networkError) {
        console.error('Network error:', networkError)
        throw new Error('Cannot connect to backend server. Please check if the backend is running and try again.')
      }

      if (!response) {
        throw new Error('No response from server. Please check if the backend is running.')
      }

      let responseData
      try {
        responseData = await response.json()
      } catch (parseError) {
        console.error('JSON parse error:', parseError)
        throw new Error(`Server returned invalid response (${response.status}). The backend may be experiencing issues.`)
      }
      
      if (!response.ok) {
        throw new Error(responseData.detail || responseData.message || `Analysis failed with status ${response.status}`)
      }

      const { id: analysis_id } = responseData
      setCurrentRunningAnalysisId(analysis_id)
      
      if (!analysis_id) {
        throw new Error('No analysis ID returned from server')
      }

      console.log('Started analysis with ID:', analysis_id)
      
      // Refresh the analyses list to show the new running analysis in sidebar
      await loadPreviousAnalyses()

      // Poll for analysis completion
      let pollRetryCount = 0
      const maxRetries = 10 // Stop after 10 failed polls
      
      // Set initial progress target
      setTargetProgress(10)
      setAnalysisStage("loading")
      
      const pollAnalysis = async () => {
        try {
          if (!analysis_id) {
            console.error('Analysis ID is undefined, stopping polling')
            setAnalysisRunning(false)
      setCurrentRunningAnalysisId(null)
            setCurrentRunningAnalysisId(null)
            return
          }
          
          let pollResponse
          try {
            pollResponse = await fetch(`${API_BASE}/analyses/${analysis_id}`, {
              headers: {
                'Authorization': `Bearer ${authToken}`
              }
            })
          } catch (networkError) {
            console.error('Network error during polling:', networkError)
            throw new Error('Cannot connect to backend server during polling')
          }

          if (pollResponse.ok) {
            // Response is OK, continue to process
          } else if (pollResponse.status === 404) {
            // Analysis was deleted during polling - stop immediately
            console.warn(`Analysis ${analysis_id} was deleted during polling`)
            setAnalysisRunning(false)
            setCurrentRunningAnalysisId(null)
            toast.error("Analysis was deleted or no longer exists")
            
            // Try to load the most recent analysis as fallback
            await loadPreviousAnalyses()
            return
          } else {
            // Other HTTP errors - treat as polling failure
            throw new Error(`HTTP ${pollResponse.status}: ${pollResponse.statusText}`)
          }
          
          let analysisData
          if (pollResponse.ok) {
            analysisData = await pollResponse.json()
            
            if (analysisData.status === 'completed') {
              console.log('Analysis completed. Full data structure:', analysisData)
              console.log('analysis_data:', analysisData.analysis_data)
              console.log('metadata:', analysisData.analysis_data?.metadata)
              console.log('total_incidents from metadata:', analysisData.analysis_data?.metadata?.total_incidents)
              
              // Set progress to 95% first, then jump to 100% right before showing data
              setTargetProgress(95)
              setAnalysisStage("complete")
              
              // Wait for progress to reach 95%, then show 100% briefly before showing data
              setTimeout(() => {
                setTargetProgress(100)
                setTimeout(() => {
                  setAnalysisRunning(false)
      setCurrentRunningAnalysisId(null)
            setCurrentRunningAnalysisId(null)
                  setCurrentRunningAnalysisId(null)
                  setCurrentAnalysis(analysisData)
                  setRedirectingToSuggested(false) // Turn off redirect loader
                  updateURLWithAnalysis(analysisData.uuid || analysisData.id)
                }, 500) // Show 100% for just 0.5 seconds before showing data
              }, 800) // Wait 0.8 seconds to reach 95%
              
              // Reload previous analyses from API to ensure sidebar is up-to-date
              await loadPreviousAnalyses()
              
              toast.success("Analysis completed!")
              return
            } else if (analysisData.status === 'failed') {
              setAnalysisRunning(false)
      setCurrentRunningAnalysisId(null)
            setCurrentRunningAnalysisId(null)
              
              // Check if we have partial data to display
              if (analysisData.analysis_data?.partial_data) {
                setCurrentAnalysis(analysisData)
                updateURLWithAnalysis(analysisData.uuid)
                toast("Analysis completed with partial data")
                await loadPreviousAnalyses()
              } else {
                toast.error(analysisData.error_message || "Analysis failed - please try again")
              }
              return
            } else if (analysisData.status === 'running') {
              // Update progress through stages based on analysis status
              console.log('Analysis running, checking progress...', {
                hasProgress: analysisData.progress !== undefined,
                hasStage: !!analysisData.stage,
                status: analysisData.status
              })
              
              // Check if we have progress information from the API
              if (analysisData.progress !== undefined) {
                console.log('Using API progress:', analysisData.progress)
                setTargetProgress(Math.min(analysisData.progress, 85))
              } else if (analysisData.stage) {
                // If the API provides a stage, use it
                const stageData = getAnalysisStages().find(s => s.key === analysisData.stage)
                if (stageData) {
                  console.log('Using API stage:', analysisData.stage, 'progress:', stageData.progress)
                  setAnalysisStage(analysisData.stage as AnalysisStage)
                  
                  // If we're fetching users and have progress info
                  if (analysisData.stage === 'fetching_users' && analysisData.users_processed && analysisData.total_users) {
                    // Calculate progress between 20% and 40% based on users processed
                    const userProgress = (analysisData.users_processed / analysisData.total_users) * 20
                    setTargetProgress(20 + userProgress)
                  } else if (analysisData.stage === 'fetching' && analysisData.incidents_processed) {
                    // Calculate progress between 40% and 60% based on incidents processed
                    const baseProgress = 40
                    const progressRange = 20
                    // Assume we'll process ~100-200 incidents, scale accordingly
                    const incidentProgress = Math.min((analysisData.incidents_processed / 100) * progressRange, progressRange)
                    setTargetProgress(baseProgress + incidentProgress)
                  } else {
                    setTargetProgress(stageData.progress)
                  }
                }
              } else {
                // Simulate progress through stages - advance conservatively with random increments
                console.log('Using simulated progress, advancing stages...')
                setCurrentStageIndex(prevIndex => {
                  // Allow simulation to progress further while waiting for API
                  const currentStages = getAnalysisStages()
                  const maxSimulatedIndex = currentStages.length - 2 // Stop before final stage
                  const stageIndex = Math.min(prevIndex, currentStages.length - 1)
                  const stage = currentStages[stageIndex]
                  console.log('Advancing to stage:', stage.key, 'progress:', stage.progress, 'index:', prevIndex)
                  setAnalysisStage(stage.key as AnalysisStage)
                  
                  // Add some randomness to the target progress but respect stage boundaries
                  const baseProgress = stage.progress
                  const randomOffset = Math.floor(Math.random() * 3) // 0-2 random offset (smaller for more predictable feel)
                  const targetWithRandomness = Math.min(baseProgress + randomOffset, 88) // Cap at 88% for simulation
                  setTargetProgress(targetWithRandomness)
                  
                  // Add realistic timing delays based on stage type
                  const stageTimings = {
                    'loading': 1500,
                    'connecting': 2000, 
                    'fetching_users': 2500,
                    'fetching': 3000,
                    'fetching_github': 4000, // GitHub can be slower
                    'fetching_slack': 3500,  
                    'analyzing_team': 4500,  // Main processing takes longer
                    'calculating_health': 2000,
                    'generating_insights': 2500,
                    'ai_analysis': 5000,     // AI processing is slower
                    'preparing': 1000
                  }
                  
                  // Log timing for this stage
                  const timing = stageTimings[stage.key] || 2000
                  console.log(`Stage "${stage.key}" will advance in ~${timing}ms`)
                  
                  // Only advance if we haven't reached the max simulated stage
                  if (prevIndex < maxSimulatedIndex) {
                    const nextIndex = prevIndex + 1
                    console.log('Next stage index will be:', nextIndex)
                    return nextIndex
                  } else {
                    console.log('Reached max simulated progress, waiting for API confirmation...')
                    return prevIndex
                  }
                })
              }
            }
          }

          // Continue polling only if analysis is still running
          if (analysisData.status !== 'completed' && analysisData.status !== 'failed') {
            pollRetryCount = 0 // Reset retry count on successful poll
            setTimeout(pollAnalysis, 2000)
          } else {
            // Analysis is complete - stop polling
            console.log('Analysis completed, stopping polling')
            setAnalysisRunning(false)
            setCurrentRunningAnalysisId(null)
          }
        } catch (error) {
          console.error('Polling error:', error)
          pollRetryCount++
          
          if (pollRetryCount >= maxRetries) {
            console.error('Max polling retries reached, stopping analysis')
            setAnalysisRunning(false)
      setCurrentRunningAnalysisId(null)
            setCurrentRunningAnalysisId(null)
            toast.error("Analysis polling failed - please try again")
            return
          }
          
          // Continue polling with exponential backoff
          setTimeout(pollAnalysis, Math.min(2000 * pollRetryCount, 10000))
        }
      }

      // Start polling after a short delay
      setTimeout(pollAnalysis, 1000)

    } catch (error) {
      console.error('Analysis error:', error)
      setAnalysisRunning(false)
      setCurrentRunningAnalysisId(null)
      toast.error(error instanceof Error ? error.message : "Failed to run analysis")
    }
  }

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      // CBI 4-tier system
      case "critical":
        return "text-red-800 bg-red-100 border-red-300"    // Critical (75-100): Dark red
      case "poor": 
        return "text-red-600 bg-red-50 border-red-200"     // Poor (50-74): Red
      case "fair":
        return "text-yellow-600 bg-yellow-50 border-yellow-200" // Fair (25-49): Yellow  
      case "healthy":
        return "text-green-600 bg-green-50 border-green-200"    // Healthy (0-24): Green
      
      // Legacy 3-tier system fallback
      case "high":
        return "text-red-600 bg-red-50 border-red-200"
      case "medium":
        return "text-yellow-600 bg-yellow-50 border-yellow-200"
      case "low":
        return "text-green-600 bg-green-50 border-green-200"
      default:
        return "text-gray-600 bg-gray-50 border-gray-200"
    }
  }

  const getProgressColor = (riskLevel: string) => {
    switch (riskLevel) {
      case "high":
        return "bg-red-500"
      case "medium":
        return "bg-yellow-500"
      case "low":
        return "bg-green-500"
      default:
        return "bg-gray-500"
    }
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case "up":
        return <TrendingUp className="w-4 h-4 text-red-500" />
      case "down":
        return <TrendingDown className="w-4 h-4 text-green-500" />
      default:
        return <Minus className="w-4 h-4 text-gray-500" />
    }
  }

  const exportAsJSON = () => {
    if (!currentAnalysis) return
    
    // Create a clean export object
    const exportData = {
      analysis_id: currentAnalysis.id,
      export_date: new Date().toISOString(),
      integration_id: currentAnalysis.integration_id,
      time_range_days: currentAnalysis.time_range,
      organization_name: selectedIntegrationData?.name,
      ...currentAnalysis.analysis_data
    }
    
    const dataStr = JSON.stringify(exportData, null, 2)
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)
    const exportFileDefaultName = `burnout-analysis-${selectedIntegrationData?.name || 'organization'}-${new Date().toISOString().split('T')[0]}.json`
    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()
  }

  const handleManageIntegrations = () => {
    router.push('/integrations')
  }

  const ensureIntegrationsLoaded = async () => {
    if (integrations.length === 0 && !dropdownLoading) {
      setDropdownLoading(true)
      try {
        await loadIntegrations(true, false) // Force refresh, no global loading
      } finally {
        setDropdownLoading(false)
      }
    }
  }

  const handleSignOut = () => {
    localStorage.removeItem('auth_token')
    router.push('/')
  }

  const selectedIntegrationData = integrations.find(i => i.id.toString() === selectedIntegration)
  
  // Generate chart data from real historical analysis results
  const chartData = historicalTrends?.daily_trends?.length > 0 
    ? historicalTrends.daily_trends.slice(-7).map((trend: any) => ({
        date: new Date(trend.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        score: Math.round((10 - trend.overall_score) * 10) // Convert 0-10 burnout to 0-100 health scale
      }))
    : currentAnalysis?.analysis_data?.team_health 
      ? [{ 
          date: "Current", 
          score: Math.round(currentAnalysis.analysis_data.team_health.overall_score * 10) 
        }] 
      : []
  
  const memberBarData = (() => {
    const teamAnalysis = currentAnalysis?.analysis_data?.team_analysis
    const members = Array.isArray(teamAnalysis) ? teamAnalysis : teamAnalysis?.members
    return members
      ?.filter((member) => {
        // Check if member has CBI score or legacy burnout score
        const memberWithCbi = member as any;
        const hasCbiScore = memberWithCbi.cbi_score !== undefined && memberWithCbi.cbi_score !== null && memberWithCbi.cbi_score > 0
        const hasLegacyScore = member.burnout_score !== undefined && member.burnout_score !== null && member.burnout_score > 0
        return (hasCbiScore || hasLegacyScore) // Include all members with valid scores
      })
      ?.map((member) => {
        // Use CBI score if available, otherwise fall back to legacy score
        const score = (member as any).cbi_score !== undefined 
          ? (member as any).cbi_score // CBI: Use raw score (0-100, where higher = more burnout)
          : (member.burnout_score * 10) // Legacy: Convert 0-10 burnout to 0-100 burnout scale
        
        const burnoutScore = Math.max(0, score);
        
        // Official CBI 4-color system based on burnout score (higher = worse)
        const getRiskFromBurnoutScore = (burnoutScore: number) => {
          if (burnoutScore < 25) return { level: 'low', color: '#10b981' };      // Green - Low/minimal burnout (0-24)
          if (burnoutScore < 50) return { level: 'mild', color: '#eab308' };     // Yellow - Mild burnout symptoms (25-49)  
          if (burnoutScore < 75) return { level: 'moderate', color: '#f97316' }; // Orange - Moderate/significant burnout (50-74)
          return { level: 'high', color: '#dc2626' };                           // Red - High/severe burnout (75-100)
        };
        
        const riskInfo = getRiskFromBurnoutScore(burnoutScore);
        
        return {
          name: member.user_name.split(" ")[0],
          fullName: member.user_name,
          score: burnoutScore,
          riskLevel: riskInfo.level,
          backendRiskLevel: member.risk_level, // Keep original for reference
          scoreType: (member as any).cbi_score !== undefined ? 'CBI' : 'Legacy',
          fill: riskInfo.color,
        }
      })
      ?.sort((a, b) => b.score - a.score) // Sort by score descending (highest burnout first)
      || []
  })();
  
  const members = (() => {
    const teamAnalysis = currentAnalysis?.analysis_data?.team_analysis
    return Array.isArray(teamAnalysis) ? teamAnalysis : (teamAnalysis?.members || [])
  })();
  
  // Helper function to get color based on severity
  const getFactorColor = (value) => {
    if (value >= 7) return '#DC2626' // Red - Critical
    if (value >= 5) return '#F59E0B' // Orange - Warning  
    if (value >= 3) return '#10B981' // Green - Good
    return '#6B7280' // Gray - Low risk
  }
  
  // Helper function to get recommendations
  const getRecommendation = (factor) => {
    switch(factor.toLowerCase()) {
      case 'workload':
        return 'Consider redistributing incidents or adding team members'
      case 'after hours':
        return 'Implement on-call rotation limits and recovery time'
      case 'weekend work':
        return 'Establish weekend work policies and coverage plans'
      case 'incident load':
        return 'Review incident prevention and escalation procedures'
      case 'resolution time':
        return 'Review escalation procedures and skill gaps'
      default:
        return 'Monitor this factor closely and consider intervention'
    }
  }
  
  // NO FALLBACK DATA: Only show burnout factors if we have REAL API data
  // Include ALL members with burnout scores, not just those with incidents
  // Members with high GitHub activity but no incidents should still be included
  const membersWithBurnoutScores = members.filter((m: any) => 
    m?.burnout_score !== undefined && m?.burnout_score !== null && m?.burnout_score > 0
  );
  
  // For backward compatibility, keep membersWithIncidents for other parts of the code
  const membersWithIncidents = members.filter((m: any) => (m?.incident_count || 0) > 0);
  
  // Check if we have any real factors data from the API (not calculated/fake values)
  const hasRealFactorsData = membersWithIncidents.length > 0 && 
    membersWithIncidents.some((m: any) => m?.factors && (
      (m.factors.after_hours !== undefined && m.factors.after_hours !== null) ||
      (m.factors.weekend_work !== undefined && m.factors.weekend_work !== null) ||
      (m.factors.incident_load !== undefined && m.factors.incident_load !== null) ||
      (m.factors.response_time !== undefined && m.factors.response_time !== null)
    ));
  
  // Use backend-calculated factors for organization-level metrics
  // Backend provides pre-calculated factors - frontend should ONLY display, never recalculate
  const membersWithGitHubData = members.filter((m: any) => 
    m?.github_activity && (m.github_activity.commits_count > 0 || m.github_activity.commits_per_week > 0));
  const allActiveMembers = members; // Include all team members

  const burnoutFactors = (allActiveMembers.length > 0) ? [
    { 
      factor: "Workload Intensity", 
      value: (() => {
        if (allActiveMembers.length === 0) return null;
        
        // Use backend-calculated workload factors
        const workloadScores = allActiveMembers
          .map((m: any) => m?.factors?.workload ?? 0)
          .filter(score => score > 0);
        
        if (workloadScores.length === 0) return 0;
        
        const sum = workloadScores.reduce((total, score) => total + score, 0);
        const average = sum / workloadScores.length;
        // Convert 0-10 scale to CBI 0-100 scale (whole integer)
        return Math.round(average * 10);
      })(),
      metrics: `Average workload factor from ${allActiveMembers.length} active team members`
    },
    { 
      factor: "After Hours Activity", 
      value: (() => {
        if (allActiveMembers.length === 0) return null;
        
        // Use backend-calculated after_hours factors
        const afterHoursScores = allActiveMembers
          .map((m: any) => m?.factors?.after_hours ?? 0)
          .filter(score => score > 0);
        
        if (afterHoursScores.length === 0) return 0;
        
        const sum = afterHoursScores.reduce((total, score) => total + score, 0);
        const average = sum / afterHoursScores.length;
        // Convert 0-10 scale to CBI 0-100 scale (whole integer)
        return Math.round(average * 10);
      })(),
      metrics: `Average after-hours factor from ${allActiveMembers.length} active team members`
    },
    { 
      factor: "Weekend Work", 
      value: (() => {
        if (allActiveMembers.length === 0) return null;
        
        // Use backend-calculated weekend_work factors
        const weekendScores = allActiveMembers
          .map((m: any) => m?.factors?.weekend_work ?? 0)
          .filter(score => score > 0);
        
        if (weekendScores.length === 0) return 0;
        
        const sum = weekendScores.reduce((total, score) => total + score, 0);
        const average = sum / weekendScores.length;
        // Convert 0-10 scale to CBI 0-100 scale (whole integer)
        return Math.round(average * 10);
      })(),
      metrics: `Average weekend work factor from ${allActiveMembers.length} active team members`
    },
    { 
      factor: "Response Pressure", 
      value: (() => {
        if (allActiveMembers.length === 0) return null;
        
        // Use backend-calculated response_time factors
        const responseScores = allActiveMembers
          .map((m: any) => m?.factors?.response_time ?? 0)
          .filter(score => score > 0);
        
        if (responseScores.length === 0) return 0;
        
        const sum = responseScores.reduce((total, score) => total + score, 0);
        const average = sum / responseScores.length;
        // Convert 0-10 scale to CBI 0-100 scale (whole integer)
        return Math.round(average * 10);
      })(),
      metrics: `Average response time factor from ${allActiveMembers.length} active team members`
    },
    { 
      factor: "Incident Load", 
      value: (() => {
        if (allActiveMembers.length === 0) return null;
        
        // Use backend-calculated incident_load factors
        const incidentLoadScores = allActiveMembers
          .map((m: any) => m?.factors?.incident_load ?? 0)
          .filter(score => score > 0);
        
        if (incidentLoadScores.length === 0) return 0;
        
        const sum = incidentLoadScores.reduce((a: number, b: number) => a + b, 0);
        const average = sum / incidentLoadScores.length;
        // Convert 0-10 scale to CBI 0-100 scale (whole integer)
        return Math.round(average * 10);
      })(),
      metrics: `Average incident load factor from ${allActiveMembers.length} active team members`
    },
  ].map(factor => ({
    ...factor,
    color: getFactorColor(factor.value!),
    recommendation: getRecommendation(factor.factor),
    severity: factor.value! >= 70 ? 'Critical' : factor.value! >= 50 ? 'Poor' : factor.value! >= 30 ? 'Fair' : 'Good'
  })) : [];
  
  // Get high-risk factors for emphasis (CBI scale 0-100)
  const highRiskFactors = burnoutFactors.filter(f => f.value >= 50).sort((a, b) => b.value - a.value);

  // Debug log to check the actual values
  useEffect(() => {
    console.log('🔍 DEBUG: Radar chart burnout factors:', burnoutFactors)
    console.log('🔍 DEBUG: Members raw factors:', (members as any[]).map((m: any) => ({ name: m.user_name, factors: m.factors })))
    console.log('🔍 DEBUG: Organization burnout score:', membersWithIncidents.length > 0 ? (membersWithIncidents as any[]).reduce((avg: number, m: any) => avg + (m.burnout_score || 0), 0) / membersWithIncidents.length * 10 : 0, '%')
    console.log('🔍 DEBUG: Members with incidents:', membersWithIncidents.length, '/', members.length)
    console.log('🔍 DEBUG: Selected member factors:', selectedMember ? selectedMember.factors : 'None selected')
    console.log('🔍 DEBUG: Selected member slack activity:', selectedMember?.slack_activity)
    console.log('🔍 DEBUG: Selected member github activity:', selectedMember?.github_activity)
    
    // Additional debugging for radar chart zeros
    if (members.length > 0) {
      console.log('🔍 RADAR DEBUG: First member structure:', JSON.stringify(members[0], null, 2))
      const firstMember = members[0] as any
      console.log('🔍 RADAR DEBUG: First member factors check:', {
        hasFactors: !!firstMember?.factors,
        workload: firstMember?.factors?.workload,
        afterHours: firstMember?.factors?.after_hours,
        weekendWork: firstMember?.factors?.weekend_work,
        incidentLoad: firstMember?.factors?.incident_load,
        responseTime: firstMember?.factors?.response_time
      })
      console.log('🔍 RADAR DEBUG: Team analysis structure keys:', Object.keys(currentAnalysis?.analysis_data?.team_analysis || {}))
      if (currentAnalysis?.analysis_data?.team_analysis && !Array.isArray(currentAnalysis.analysis_data.team_analysis)) {
        console.log('🔍 RADAR DEBUG: Team analysis object keys:', Object.keys(currentAnalysis.analysis_data.team_analysis))
        console.log('🔍 RADAR DEBUG: Team analysis members array length:', currentAnalysis.analysis_data.team_analysis.members?.length || 0)
      }
    }
  }, [burnoutFactors, members, selectedMember, currentAnalysis])

  // Show full-screen loading when loading integrations
  if (loadingIntegrations) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="text-center">
          <Activity className="w-8 h-8 text-purple-600 animate-pulse mx-auto mb-4" />
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  // Show main page loader while initial data loads (but not if we have cached data)
  // Also show loader if we haven't loaded analyses yet to prevent empty state flash
  const showLoader = (!initialDataLoaded && !hasDataFromCache) || 
                     (initialDataLoaded && previousAnalyses.length === 0 && !hasDataFromCache);
  
  if (showLoader) {
    return (
      <div className="flex h-screen bg-gray-50">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600">Loading dashboard...</p>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div
        className={`${sidebarCollapsed ? "w-16" : "w-60"} bg-gray-900 text-white transition-all duration-300 flex flex-col`}
      >
        {/* Header */}
        <div className="relative h-12">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className={`text-gray-400 hover:text-white hover:bg-gray-800 absolute top-2 ${sidebarCollapsed ? 'left-2' : 'right-2'}`}
          >
            {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </Button>
        </div>

        {/* Navigation */}
        <div className={`flex-1 flex flex-col ${sidebarCollapsed ? 'p-2' : 'p-4'} space-y-2`}>
          {!sidebarCollapsed ? (
            <div className="flex-1 space-y-2">
              <Button
                onClick={startAnalysis}
                disabled={analysisRunning}
                className="w-full justify-start bg-purple-600 hover:bg-purple-700 text-white"
              >
                <Play className="w-4 h-4 mr-2" />
                New Analysis
              </Button>

            <div className="space-y-1">
              {!sidebarCollapsed && previousAnalyses.length > 0 && (
                <p className="text-xs text-gray-400 uppercase tracking-wide px-2 py-1 mt-4">Recent</p>
              )}
              <div className="max-h-96 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
                {!initialDataLoaded && previousAnalyses.length === 0 ? (
                  // Show loading state for analyses
                  <div className="flex items-center justify-center py-8">
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                      {!sidebarCollapsed && (
                        <span className="text-xs text-gray-400">Loading analyses...</span>
                      )}
                    </div>
                  </div>
                ) : previousAnalyses.length === 0 ? (
                  // Show empty state
                  !sidebarCollapsed && (
                    <div className="text-center py-8 text-gray-400">
                      <p className="text-xs">No analyses yet</p>
                      <p className="text-xs mt-1">Start your first analysis above</p>
                    </div>
                  )
                ) : (
                  // Show analyses list
                  previousAnalyses.slice(0, 50).map((analysis) => {
                const analysisDate = new Date(analysis.created_at)
                const timeStr = analysisDate.toLocaleTimeString([], { 
                  hour: 'numeric', 
                  minute: '2-digit',
                  hour12: true,
                  timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                })
                const dateStr = analysisDate.toLocaleDateString([], { 
                  month: 'short', 
                  day: 'numeric',
                  timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                })
                
                // Load integrations if needed for team name display
                const matchingIntegration = integrations.find(i => i.id === Number(analysis.integration_id)) || 
                                          integrations.find(i => String(i.id) === String(analysis.integration_id))
                
                // Use organization name from analysis results if available, fall back to integration name
                let organizationName = (analysis as any).analysis_data?.metadata?.organization_name || 
                                      (analysis as any).config?.organization_name ||
                                      matchingIntegration?.name || 
                                      matchingIntegration?.organization_name ||
                                      // Handle beta integrations by looking at config
                                      ((analysis as any).config?.beta_integration_id === 'beta-rootly' ? 'Rootly' : 
                                       (analysis as any).config?.beta_integration_id === 'beta-pagerduty' ? 'PagerDuty' : 
                                       (analysis.integration_id && String(analysis.integration_id) !== 'null' ? `Organization ${analysis.integration_id}` : 'Unknown Organization'))
                
                // Special handling for beta integrations during running state
                if (!matchingIntegration && typeof analysis.integration_id === 'string') {
                  if (String(analysis.integration_id) === 'beta-rootly') {
                    organizationName = integrations.find(i => String(i.id) === 'beta-rootly')?.name || 'Rootly'
                  } else if (String(analysis.integration_id) === 'beta-pagerduty') {
                    organizationName = integrations.find(i => String(i.id) === 'beta-pagerduty')?.name || 'PagerDuty'
                  }
                }
                const isSelected = currentAnalysis?.id === analysis.id
                
                // Determine platform color from integration or analysis data
                let platformColor = 'bg-gray-500' // default
                if (matchingIntegration?.platform === 'rootly') {
                  platformColor = 'bg-purple-500'  // Rootly = Purple
                } else if (matchingIntegration?.platform === 'pagerduty') {
                  platformColor = 'bg-green-500'   // PagerDuty = Green
                } else {
                  // For beta integrations or analyses, check multiple sources
                  const analysisConfig = (analysis as any).analysis_data?.config || {};
                  const betaIntegrationId = analysisConfig.beta_integration_id;
                  
                  if (betaIntegrationId === 'beta-rootly' || String(analysis.integration_id) === 'beta-rootly' || organizationName.includes('Rootly')) {
                    platformColor = 'bg-purple-500'  // Rootly = Purple
                  } else if (betaIntegrationId === 'beta-pagerduty' || String(analysis.integration_id) === 'beta-pagerduty' || organizationName.includes('PagerDuty')) {
                    platformColor = 'bg-green-500'   // PagerDuty = Green
                  }
                }
                return (
                  <div key={analysis.id} className={`relative group ${isSelected ? 'bg-gray-800' : ''} rounded`}>
                    <Button 
                      variant="ghost" 
                      className={`w-full justify-start text-gray-300 hover:text-white hover:bg-gray-800 py-2 h-auto ${isSelected ? 'bg-gray-800 text-white' : ''}`}
                      onClick={async () => {
                        console.log('Clicking historical analysis:', analysis.id)
                        
                        // If analysis doesn't have full data, fetch it
                        if (!analysis.analysis_data || !analysis.analysis_data.team_analysis) {
                          try {
                            const authToken = localStorage.getItem('auth_token')
                            if (!authToken) return
                            
                            console.log('Fetching full analysis details for:', analysis.id)
                            const response = await fetch(`${API_BASE}/analyses/${analysis.id}`, {
                              headers: {
                                'Authorization': `Bearer ${authToken}`
                              }
                            })
                            
                            if (response.ok) {
                              const fullAnalysis = await response.json()
                              console.log('Fetched full analysis:', {
                                id: fullAnalysis.id,
                                hasAnalysisData: !!fullAnalysis.analysis_data,
                                hasTeamAnalysis: !!fullAnalysis.analysis_data?.team_analysis,
                                memberCount: fullAnalysis.analysis_data?.team_analysis?.members?.length || 0
                              })
                              setCurrentAnalysis(fullAnalysis)
                              setRedirectingToSuggested(false) // Turn off redirect loader
                              updateURLWithAnalysis(fullAnalysis.uuid || fullAnalysis.id)
                            } else {
                              console.error('Failed to fetch full analysis')
                              setCurrentAnalysis(analysis)
                              setRedirectingToSuggested(false) // Turn off redirect loader
                              updateURLWithAnalysis(analysis.uuid || analysis.id)
                            }
                          } catch (error) {
                            console.error('Error fetching full analysis:', error)
                            setCurrentAnalysis(analysis)
                            setRedirectingToSuggested(false) // Turn off redirect loader
                            updateURLWithAnalysis(analysis.uuid || analysis.id)
                          }
                        } else {
                          console.log('Analysis already has data:', {
                            hasTeamAnalysis: !!analysis.analysis_data.team_analysis,
                            memberCount: Array.isArray(analysis.analysis_data.team_analysis) ? analysis.analysis_data.team_analysis.length : (analysis.analysis_data.team_analysis?.members?.length || 0)
                          })
                          setCurrentAnalysis(analysis)
                          setRedirectingToSuggested(false) // Turn off redirect loader
                          updateURLWithAnalysis(analysis.uuid || analysis.id)
                        }
                      }}
                    >
                      {sidebarCollapsed ? (
                        <Clock className="w-4 h-4" />
                      ) : (
                        <div className="flex flex-col items-start w-full text-xs pr-8">
                          <div className="flex justify-between items-center w-full mb-1">
                            <div className="flex items-center space-x-2">
                              {(matchingIntegration || platformColor !== 'bg-gray-500') && (
                                <div className={`w-2 h-2 rounded-full ${platformColor}`}></div>
                              )}
                              <span className="font-medium">{organizationName}</span>
                            </div>
                            <span className="text-gray-500">{analysis.time_range || 30}d</span>
                          </div>
                          <div className="flex justify-between items-center w-full text-gray-400">
                            <span>{dateStr}</span>
                            <span>{timeStr}</span>
                          </div>
                        </div>
                      )}
                    </Button>
                    {!sidebarCollapsed && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity p-1 h-6 w-6 text-gray-400 hover:text-red-400 hover:bg-red-900/20"
                        onClick={(e) => openDeleteDialog(analysis, e)}
                        title="Delete analysis"
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    )}
                  </div>
                )
                })
                )}
              </div>
            </div>
            </div>
          ) : (
            <div className="flex-1">
              {/* Collapsed state - just show new analysis button */}
              <Button
                onClick={startAnalysis}
                disabled={analysisRunning}
                className="w-full bg-purple-600 hover:bg-purple-700 text-white p-2"
                title="New Analysis"
              >
                <Play className="w-4 h-4" />
              </Button>
            </div>
          )}

          <div className="space-y-2">
            <Separator className="bg-gray-700" />
            <Button 
              variant="ghost" 
              className={`w-full ${sidebarCollapsed ? 'p-2' : ''} justify-start text-gray-300 hover:text-white hover:bg-gray-800`}
              onClick={() => router.push('/methodology')}
              title="Methodology"
            >
              <BookOpen className={`w-4 h-4 ${sidebarCollapsed ? '' : 'mr-2'}`} />
              {!sidebarCollapsed && "Methodology"}
            </Button>
            {/* Show changelog only in development */}
            {process.env.NODE_ENV === 'development' && (
              <Button 
                variant="ghost" 
                className={`w-full ${sidebarCollapsed ? 'p-2' : ''} justify-start text-gray-300 hover:text-white hover:bg-gray-800`}
                onClick={() => router.push('/changelog')}
                title="Changelog"
              >
                <FileText className={`w-4 h-4 ${sidebarCollapsed ? '' : 'mr-2'}`} />
                {!sidebarCollapsed && "Changelog"}
              </Button>
            )}
            <Button 
              variant="ghost" 
              className={`w-full ${sidebarCollapsed ? 'p-2' : ''} justify-start text-gray-300 hover:text-white hover:bg-gray-800`}
              onClick={handleManageIntegrations}
              title="Manage Integrations"
            >
              <Settings className={`w-4 h-4 ${sidebarCollapsed ? '' : 'mr-2'}`} />
              {!sidebarCollapsed && "Manage Integrations"}
            </Button>
            <Button 
              variant="ghost" 
              className={`w-full ${sidebarCollapsed ? 'p-2' : ''} justify-start text-gray-300 hover:text-white hover:bg-gray-800`}
              onClick={handleSignOut}
              title="Sign Out"
            >
              <LogOut className={`w-4 h-4 ${sidebarCollapsed ? '' : 'mr-2'}`} />
              {!sidebarCollapsed && "Sign Out"}
            </Button>
            
            {/* Powered by Rootly */}
            {!sidebarCollapsed && (
              <div className="mt-4 pt-4 border-t border-gray-700">
                <a 
                  href="https://rootly.com" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex flex-col items-center -space-y-1 hover:opacity-80 transition-opacity"
                >
                  <span className="text-sm text-slate-300">powered by</span>
                  <Image 
                    src="/images/rootly-ai-logo.png" 
                    alt="Rootly AI" 
                    width={160} 
                    height={64} 
                    className="h-8 w-auto ml-3 brightness-0 invert filter drop-shadow-sm"
                  />
                </a>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto bg-gray-100">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center justify-between w-full">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Organization Burnout Analysis</h1>
                <p className="text-gray-600">
                  {(() => {
                    // If viewing a specific analysis, show the integration used for that analysis
                    if (currentAnalysis) {
                      const analysisIntegration = integrations.find(i => i.id === currentAnalysis.integration_id);
                      if (analysisIntegration) {
                        const platform = analysisIntegration.platform === 'pagerduty' ? 'PagerDuty' : 'Rootly';
                        return `${platform} - ${analysisIntegration.organization_name || analysisIntegration.name}`;
                      }
                      return 'Analysis Dashboard';
                    }
                    // Otherwise show the currently selected integration
                    if (selectedIntegrationData) {
                      const platform = selectedIntegrationData.platform === 'pagerduty' ? 'PagerDuty' : 'Rootly';
                      return `${platform} - ${selectedIntegrationData.organization_name || selectedIntegrationData.name}`;
                    }
                    return 'Organization Burnout Analysis Dashboard';
                  })()}
                </p>
              </div>
              <div className="flex items-center space-x-4">
                <div className="flex flex-col items-center">
                  <span className="text-xs text-gray-400">powered by</span>
                  <Image 
                    src="/images/rootly-ai-logo.png" 
                    alt="Rootly AI" 
                    width={120} 
                    height={48}
                    className="h-6 w-auto"
                  />
                </div>
                {/* Export Dropdown */}
                {!shouldShowInsufficientDataCard() && currentAnalysis && currentAnalysis.analysis_data && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button 
                        variant="outline" 
                        className="flex items-center space-x-2 border-gray-300 hover:bg-gray-50"
                        title="Export analysis data"
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                      <DropdownMenuItem onClick={exportAsJSON} className="flex items-center space-x-2">
                        <Download className="w-4 h-4" />
                        <div className="flex flex-col">
                          <span className="font-medium">Export as JSON</span>
                          <span className="text-xs text-gray-500">Complete analysis data</span>
                        </div>
                      </DropdownMenuItem>
                      <DropdownMenuItem disabled className="flex items-center space-x-2 opacity-50">
                        <Download className="w-4 h-4" />
                        <div className="flex flex-col">
                          <span className="font-medium">Export as CSV</span>
                          <span className="text-xs text-gray-500">Organization member scores</span>
                        </div>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem disabled className="flex items-center space-x-2 opacity-50">
                        <FileText className="w-4 h-4" />
                        <div className="flex flex-col">
                          <span className="font-medium">Generate PDF Report</span>
                          <span className="text-xs text-gray-500">Executive summary</span>
                        </div>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
            </div>
          </div>

          {/* Debug Section - Only show in development */}
          {false && process.env.NODE_ENV === 'development' && currentAnalysis && (
            <Card className="mb-6 bg-yellow-50 border-yellow-200">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-yellow-800 flex items-center">
                    <AlertCircle className="w-4 h-4 mr-2" />
                    Debug: Analysis Data Structure
                  </h3>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setDebugSectionOpen(!debugSectionOpen)}
                    className="text-yellow-600 hover:text-yellow-800 hover:bg-yellow-100"
                  >
                    {debugSectionOpen ? 'Hide' : 'Show'} Debug Info
                  </Button>
                </div>
                
                {debugSectionOpen && (
                  <div className="space-y-3">
                    <div className="text-xs bg-white p-3 rounded border border-yellow-200">
                      <div className="font-medium text-gray-700 mb-2">Analysis Overview:</div>
                      <div className="space-y-1 text-gray-600">
                        <div>ID: {currentAnalysis.id}</div>
                        <div>Status: {currentAnalysis.status}</div>
                        <div>Created: {new Date(currentAnalysis.created_at).toLocaleString([], {
                          timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                          hour12: true
                        })}</div>
                        <div>Integration ID: {currentAnalysis.integration_id}</div>
                        <div>Has analysis_data: {currentAnalysis.analysis_data ? 'Yes' : 'No'}</div>
                      </div>
                    </div>
                    
                    {currentAnalysis.analysis_data && (
                      <div className="text-xs bg-white p-3 rounded border border-yellow-200">
                        <div className="font-medium text-gray-700 mb-2">Analysis Data Structure:</div>
                        <div className="space-y-1 text-gray-600">
                          <div>Has team_health: {currentAnalysis.analysis_data.team_health ? 'Yes' : 'No'}</div>
                          <div>Has team_analysis: {currentAnalysis.analysis_data.team_analysis ? 'Yes' : 'No'}</div>
                          <div>Has partial_data: {currentAnalysis.analysis_data.partial_data ? 'Yes' : 'No'}</div>
                          
                          {currentAnalysis.analysis_data.team_analysis && (
                            <div className="ml-4 space-y-1 mt-2">
                              <div className="font-medium text-gray-700">Team Analysis:</div>
                              <div>Members count: {Array.isArray(currentAnalysis.analysis_data.team_analysis) ? (currentAnalysis.analysis_data.team_analysis as any[]).length : ((currentAnalysis.analysis_data.team_analysis as any)?.members?.length || 0)}</div>
                              <div>Has organization_health: {(currentAnalysis.analysis_data.team_analysis as any).organization_health ? 'Yes' : 'No'}</div>
                              <div>Has insights: {(currentAnalysis.analysis_data.team_analysis as any).insights ? 'Yes' : 'No'}</div>
                            </div>
                          )}
                          
                          {(() => {
                            const teamAnalysis = currentAnalysis.analysis_data.team_analysis
                            const members = Array.isArray(teamAnalysis) ? teamAnalysis : (teamAnalysis as any)?.members
                            return members && members.length > 0
                          })() && (
                            <div className="ml-4 space-y-1 mt-2">
                              <div className="font-medium text-gray-700">Sample Member Data Sources:</div>
                              {(() => {
                                const teamAnalysis = currentAnalysis.analysis_data.team_analysis
                                const members = Array.isArray(teamAnalysis) ? teamAnalysis : (teamAnalysis as any)?.members
                                const member = members[0]
                                return (
                                  <div className="ml-4 space-y-1">
                                    <div>Has GitHub data: {(member as any).github_data ? 'Yes' : 'No'}</div>
                                    <div>Has Slack data: {(member as any).slack_data ? 'Yes' : 'No'}</div>
                                    <div>Has incident data: {member.incident_count !== undefined ? 'Yes' : 'No'}</div>
                                    <div>Has metrics: {member.metrics ? 'Yes' : 'No'}</div>
                                    <div>Has factors: {member.factors ? 'Yes' : 'No'}</div>
                                  </div>
                                )
                              })()}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    
                    <div className="text-xs bg-white p-3 rounded border border-yellow-200">
                      <div className="font-medium text-gray-700 mb-2">Raw Analysis Data (JSON):</div>
                      <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded border max-h-60 overflow-y-auto">
                        {JSON.stringify(currentAnalysis.analysis_data, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          <AnalysisProgressSection 
            analysisRunning={analysisRunning}
            analysisStage={analysisStage}
            analysisProgress={analysisProgress}
            currentAnalysis={currentAnalysis}
            shouldShowInsufficientDataCard={shouldShowInsufficientDataCard}
            getAnalysisStages={getAnalysisStages}
            cancelRunningAnalysis={cancelRunningAnalysis}
            startAnalysis={startAnalysis}
            openDeleteDialog={openDeleteDialog}
          />

          {/* Analysis Complete State - Only show if analysis has meaningful data */}
          {!shouldShowInsufficientDataCard() && !analysisRunning && currentAnalysis && (currentAnalysis.analysis_data?.team_health || currentAnalysis.analysis_data?.team_summary || currentAnalysis.analysis_data?.partial_data || currentAnalysis.analysis_data?.team_analysis) && (
            <>
              {/* Debug Section - Development Only */}
              {false && process.env.NODE_ENV === 'development' && (
                <Card className="mb-6 border-yellow-300 bg-yellow-50">
                  <CardHeader>
                    <CardTitle className="text-yellow-800 text-sm">🐛 Debug: Analysis Data Sources</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-xs space-y-2">
                      <p><strong>Analysis ID:</strong> {currentAnalysis.id}</p>
                      <p><strong>Status:</strong> {currentAnalysis.status}</p>
                      <p><strong>Data Sources Present:</strong></p>
                      <ul className="ml-4 space-y-1">
                        <li>• data_sources object: {currentAnalysis.analysis_data?.data_sources ? '✅ Present' : '❌ Missing'}</li>
                        <li>• github_data flag: {currentAnalysis.analysis_data?.data_sources?.github_data ? '✅ True' : '❌ False/Missing'}</li>
                        <li>• slack_data flag: {currentAnalysis.analysis_data?.data_sources?.slack_data ? '✅ True' : '❌ False/Missing'}</li>
                        <li>• github_insights: {currentAnalysis.analysis_data?.github_insights ? '✅ Present' : '❌ Missing'}</li>
                        <li>• slack_insights: {currentAnalysis.analysis_data?.slack_insights ? '✅ Present' : '❌ Missing'}</li>
                        <li>• team_analysis.members count: {Array.isArray(currentAnalysis.analysis_data?.team_analysis) ? (currentAnalysis.analysis_data.team_analysis as any[]).length : ((currentAnalysis.analysis_data?.team_analysis as any)?.members?.length || 0)}</li>
                      </ul>
                      <p><strong>Metadata Check:</strong></p>
                      <ul className="ml-4 space-y-1">
                        <li>• metadata.include_github: {(currentAnalysis.analysis_data as any)?.metadata?.include_github ? '✅ True' : '❌ False/Missing'}</li>
                        <li>• metadata.include_slack: {(currentAnalysis.analysis_data as any)?.metadata?.include_slack ? '✅ True' : '❌ False/Missing'}</li>
                        <li>• metadata object: {(currentAnalysis.analysis_data as any)?.metadata ? '✅ Present' : '❌ Missing'}</li>
                      </ul>
                      <details className="mt-2">
                        <summary className="cursor-pointer text-yellow-700 hover:text-yellow-900">Raw analysis_data structure</summary>
                        <pre className="mt-2 p-2 bg-white rounded text-xs overflow-auto max-h-40">
                          {JSON.stringify(currentAnalysis.analysis_data, null, 2)}
                        </pre>
                      </details>
                      <details className="mt-2">
                        <summary className="cursor-pointer text-yellow-700 hover:text-yellow-900">GitHub insights data</summary>
                        <pre className="mt-2 p-2 bg-white rounded text-xs overflow-auto max-h-40">
                          {JSON.stringify(currentAnalysis.analysis_data?.github_insights, null, 2)}
                        </pre>
                      </details>
                      <details className="mt-2">
                        <summary className="cursor-pointer text-yellow-700 hover:text-yellow-900">Slack insights data</summary>
                        <pre className="mt-2 p-2 bg-white rounded text-xs overflow-auto max-h-40">
                          {JSON.stringify(currentAnalysis.analysis_data?.slack_insights, null, 2)}
                        </pre>
                      </details>
                    </div>
                  </CardContent>
                </Card>
              )}

              <TeamHealthOverview 
                currentAnalysis={currentAnalysis}
                historicalTrends={historicalTrends}
                expandedDataSources={expandedDataSources}
                setExpandedDataSources={setExpandedDataSources}
              />

              {/* AI Insights Card - Text-based summary */}
              {currentAnalysis?.analysis_data?.ai_team_insights?.available && (
                <Card className="mb-6 bg-gradient-to-br from-blue-50 via-white to-indigo-50 border-blue-200 shadow-sm">
                  <CardHeader>
                    <div className="flex items-center space-x-2">
                      <CardTitle>AI Team Insights</CardTitle>
                      <Badge variant="secondary" className="text-xs">AI Enhanced</Badge>
                    </div>
                    <CardDescription>
                      Analysis generated from {currentAnalysis.analysis_data.ai_team_insights.insights?.team_size || 0} team members
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="prose prose-sm max-w-none">
                    {(() => {
                      const aiInsights = currentAnalysis.analysis_data.ai_team_insights.insights;
                      
                      // Check if we have LLM-generated narrative
                      if (aiInsights?.llm_team_analysis) {
                        return (
                          <div className="space-y-4">
                            <div 
                              className="leading-relaxed text-gray-800"
                              dangerouslySetInnerHTML={{ 
                                __html: aiInsights.llm_team_analysis
                                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                  .replace(/\n\n/g, '</p><p class="mt-4">')
                                  .replace(/^/, '<p>')
                                  .replace(/$/, '</p>')
                              }}
                            />
                          </div>
                        );
                      }
                      
                      // No LLM-generated content available
                      const isAnalysisRunning = currentAnalysis?.status === 'running' || currentAnalysis?.status === 'pending';
                      
                      if (isAnalysisRunning) {
                        return (
                          <div className="text-center py-12 text-gray-500">
                            <Sparkles className="h-10 w-10 mx-auto mb-4 opacity-40 animate-pulse" />
                            <h4 className="font-medium text-gray-700 mb-2">Generating AI Insights</h4>
                            <p className="text-sm">AI analysis is being generated...</p>
                          </div>
                        )
                      } else {
                        return (
                          <div className="text-center py-12 text-gray-500">
                            <Sparkles className="h-10 w-10 mx-auto mb-4 opacity-40" />
                            <h4 className="font-medium text-gray-700 mb-2">AI Insights Unavailable</h4>
                            <p className="text-sm mb-4">Configure your AI token to enable intelligent team insights</p>
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => router.push('/settings')}
                            >
                              Configure AI Settings
                            </Button>
                          </div>
                        )
                      }
                    })()}
                  </CardContent>
                </Card>
              )}

              {/* Partial Data Warning */}
              {currentAnalysis?.analysis_data?.error && currentAnalysis?.analysis_data?.partial_data && (
                <Card className="mb-6 border-yellow-200 bg-yellow-50">
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2 text-yellow-800">
                      <AlertTriangle className="w-5 h-5" />
                      <span>Partial Data Available</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-yellow-700 mb-4">
                      Analysis processing failed, but we successfully collected raw data from Rootly:
                    </p>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-medium">Users collected:</span>
                        <p className="text-lg font-bold text-yellow-800">
                          {currentAnalysis.analysis_data.partial_data.users?.length || 0}
                        </p>
                      </div>
                      <div>
                        <span className="font-medium">Incidents collected:</span>
                        <p className="text-lg font-bold text-yellow-800">
                          {currentAnalysis.analysis_data.partial_data.incidents?.length || 0}
                        </p>
                      </div>
                    </div>
                    <div className="mt-4 p-3 bg-yellow-100 rounded-lg">
                      <p className="text-xs text-yellow-600">
                        <strong>Error:</strong> {currentAnalysis.analysis_data.error}
                      </p>
                    </div>
                    <div className="mt-4 flex space-x-3">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          const partialData = {
                            analysis_id: currentAnalysis.id,
                            export_date: new Date().toISOString(),
                            data_collection_successful: currentAnalysis.analysis_data.data_collection_successful,
                            failure_stage: currentAnalysis.analysis_data.failure_stage,
                            error: currentAnalysis.analysis_data.error,
                            users: currentAnalysis.analysis_data.partial_data.users,
                            incidents: currentAnalysis.analysis_data.partial_data.incidents,
                            metadata: currentAnalysis.analysis_data.partial_data.metadata
                          }
                          
                          const blob = new Blob([JSON.stringify(partialData, null, 2)], { type: 'application/json' })
                          const url = URL.createObjectURL(blob)
                          const a = document.createElement('a')
                          a.href = url
                          a.download = `rootly-partial-data-${currentAnalysis.id}.json`
                          document.body.appendChild(a)
                          a.click()
                          document.body.removeChild(a)
                          URL.revokeObjectURL(url)
                        }}
                        className="border-yellow-300 text-yellow-700 hover:bg-yellow-100"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Export Raw Data
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Organization Member Scores - Full Width */}
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>Individual Burnout Scores</CardTitle>
                  <CardDescription>Team member CBI burnout scores (higher = more burnout risk)</CardDescription>
                </CardHeader>
                <CardContent>
                  {memberBarData.length > 0 ? (
                    <div className="h-[350px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={memberBarData} margin={{ top: 20, right: 30, bottom: 60, left: 20 }}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis 
                            dataKey="fullName" 
                            angle={-45}
                            textAnchor="end"
                            height={60}
                            interval={0}
                            tick={{ fontSize: 11 }}
                          />
                          <YAxis domain={[0, 100]} />
                          <Tooltip 
                            formatter={(value, name, props) => {
                              const data = props.payload;
                              const getRiskLabel = (level: string) => {
                                switch(level) {
                                  case 'low': return 'Low/Minimal Burnout';
                                  case 'mild': return 'Mild Burnout Symptoms';
                                  case 'moderate': return 'Moderate/Significant Burnout';
                                  case 'high': return 'High/Severe Burnout';
                                  default: return level;
                                }
                              };
                              return [
                                `${Number(value).toFixed(1)}/100`, 
                                `${data.scoreType} Score (${getRiskLabel(data.riskLevel)})`
                              ];
                            }}
                            labelFormatter={(label, payload) => {
                              const data = payload?.[0]?.payload;
                              return data ? `${data.fullName}` : label;
                            }}
                            contentStyle={{
                              backgroundColor: 'white',
                              border: '1px solid #e5e7eb',
                              borderRadius: '8px',
                              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                            }}
                          />
                          <Bar 
                            dataKey="score" 
                            radius={[4, 4, 0, 0]}
                          >
                            {memberBarData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.fill} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="h-[350px] flex items-center justify-center text-gray-500">
                      <div className="text-center">
                        <p className="text-lg font-medium">No incident data available</p>
                        <p className="text-sm mt-2">Members with zero incidents are not displayed in this chart</p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Charts Section */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                {/* Burnout Journey Map */}
                <Card>
                  <CardHeader>
                    <CardTitle>Burnout Timeline</CardTitle>
                    <CardDescription>
                      {(() => {
                        if (currentAnalysis?.analysis_data?.daily_trends?.length > 0) {
                          const dailyTrends = currentAnalysis.analysis_data.daily_trends;
                          // Quick count of standout events
                          let standoutCount = 0;
                          for (let i = 1; i < dailyTrends.length - 1; i++) {
                            const prev = dailyTrends[i-1];
                            const curr = dailyTrends[i];
                            const next = dailyTrends[i+1];
                            const score = Math.round(curr.overall_score * 10);
                            const prevChange = prev ? score - Math.round(prev.overall_score * 10) : 0;
                            
                            if ((prev && next && score > Math.round(prev.overall_score * 10) && score > Math.round(next.overall_score * 10) && score >= 75) ||
                                (prev && next && score < Math.round(prev.overall_score * 10) && score < Math.round(next.overall_score * 10) && score <= 60) ||
                                Math.abs(prevChange) >= 20 ||
                                curr.incident_count >= 15 ||
                                (score <= 45 && curr.members_at_risk >= 3)) {
                              standoutCount++;
                            }
                          }
                          return `Timeline from ${standoutCount} significant events across the selected time range`;
                        }
                        return "Timeline of significant events and trends across the selected time range";
                      })()}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-6">
                      {loadingTrends ? (
                        <div className="flex items-center justify-center h-32">
                          <div className="text-center">
                            <div className="animate-spin w-6 h-6 border-2 border-purple-600 border-t-transparent rounded-full mx-auto mb-2"></div>
                            <p className="text-sm text-gray-500">Loading journey...</p>
                          </div>
                        </div>
                      ) : (
                        (() => {
                        // Calculate high risk members for journey map
                        const highRiskMembers = members.filter(m => m.risk_level === 'high' || m.risk_level === 'critical');
                        
                        // Calculate health score
                        const healthScore = currentAnalysis?.analysis_data?.team_health ? 
                          Math.round(currentAnalysis.analysis_data.team_health.overall_score * 10) : 92;
                        
                        // Generate timeline events using the same intelligent detection as the health trends chart
                        let journeyEvents = [];
                        
                        if (currentAnalysis?.analysis_data?.daily_trends?.length > 0) {
                          const dailyTrends = currentAnalysis.analysis_data.daily_trends;
                          
                          // Transform data and detect standout events (same logic as chart)
                          const chartData = dailyTrends.map((trend: any, index: number) => ({
                            date: trend.date,
                            // Use CBI score methodology (0-100, where higher = more burnout)
                            score: Math.round(trend.overall_score * 10), // Convert 0-10 to 0-100 CBI scale
                            membersAtRisk: trend.members_at_risk,
                            totalMembers: trend.total_members,
                            incidentCount: trend.incident_count || 0,
                            rawScore: trend.overall_score,
                            index: index
                          }));
                          
                          // Identify standout events (same algorithm as chart)
                          const identifyStandoutEvents = (data: any[]) => {
                            if (data.length < 3) return data;
                            
                            return data.map((point: any, i: number) => {
                              let eventType = 'normal';
                              let eventDescription = '';
                              let significance = 0;
                              
                              const prev = i > 0 ? data[i-1] : null;
                              const next = i < data.length-1 ? data[i+1] : null;
                              
                              // Calculate changes
                              const prevChange = prev ? point.score - prev.score : 0;
                              
                              // Detect peaks (local maxima)
                              if (prev && next && point.score > prev.score && point.score > next.score && point.score >= 75) {
                                eventType = 'peak';
                                // Convert health score to CBI score for display (100 - health_percentage = CBI score)
                                const cbiScore = Math.round(100 - point.score);
                                eventDescription = `Team wellness at peak (${cbiScore} CBI score) - ${point.incidentCount} incidents handled without stress signs`;
                                significance = point.score >= 90 ? 3 : 2;
                              }
                              // Detect valleys (local minima)  
                              else if (prev && next && point.score < prev.score && point.score < next.score && point.score <= 60) {
                                eventType = 'valley';
                                // Convert health score to CBI score for display (100 - health_percentage = CBI score)
                                const cbiScore = Math.round(100 - point.score);
                                eventDescription = `Team showing signs of strain (${cbiScore} CBI score) - ${point.incidentCount} incidents, ${point.membersAtRisk} team members need support`;
                                significance = point.score <= 40 ? 3 : 2;
                              }
                              // Detect sharp improvements
                              else if (prevChange >= 20) {
                                eventType = 'recovery';
                                // For improvement, show it as CBI score reduction (health increase = CBI decrease)
                                const cbiImprovement = Math.abs(prevChange);
                                eventDescription = `Great turnaround! Team burnout reduced by ${cbiImprovement} CBI points - interventions working well`;
                                significance = prevChange >= 30 ? 3 : 2;
                              }
                              // Detect sharp declines
                              else if (prevChange <= -20) {
                                eventType = 'decline';
                                // For decline, show it as CBI score increase (health decrease = CBI increase)
                                const cbiIncrease = Math.abs(prevChange);
                                eventDescription = `Warning: Team burnout increased by ${cbiIncrease} CBI points - immediate attention recommended`;
                                significance = prevChange <= -30 ? 3 : 2;
                              }
                              // Detect high incident volume days
                              else if (point.incidentCount >= 15) {
                                eventType = 'high-volume';
                                eventDescription = `Heavy workload day - ${point.incidentCount} incidents may be causing team stress`;
                                significance = point.incidentCount >= 25 ? 3 : 2;
                              }
                              // Detect critical health days
                              else if (point.score <= 45 && point.membersAtRisk >= 3) {
                                eventType = 'critical';
                                // Convert health score to CBI score for display (100 - health_percentage = CBI score)
                                const cbiScore = Math.round(100 - point.score);
                                eventDescription = `URGENT: Team at burnout risk (${cbiScore} CBI score) - ${point.membersAtRisk} members need immediate support`;
                                significance = 3;
                              }
                              
                              return {
                                ...point,
                                eventType,
                                eventDescription,
                                significance,
                                isStandout: significance > 0
                              };
                            });
                          };
                          
                          const standoutEvents = identifyStandoutEvents(chartData);
                          
                          // Convert standout events to timeline format, sorted by significance
                          journeyEvents = standoutEvents
                            .filter(event => event.isStandout)
                            .sort((a, b) => b.significance - a.significance) // Highest significance first
                            .slice(0, 8) // Limit to top 8 events
                            .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()) // Sort by date for timeline
                            .map((event: any) => ({
                              date: new Date(event.date).toLocaleDateString('en-US', { 
                                month: 'short', 
                                day: 'numeric' 
                              }),
                              status: event.eventType,
                              title: event.eventType === 'peak' ? 'Team Wellness Peak' :
                                    event.eventType === 'valley' ? 'Team Support Needed' :
                                    event.eventType === 'recovery' ? 'Wellness Recovery' :
                                    event.eventType === 'decline' ? 'Burnout Risk Increase' :
                                    event.eventType === 'high-volume' ? 'High Workload Period' :
                                    event.eventType === 'critical' ? 'Burnout Alert' :
                                    'Significant Event',
                              description: event.eventDescription,
                              color: event.eventType === 'peak' ? 'bg-green-500' :
                                    event.eventType === 'valley' ? 'bg-red-500' :
                                    event.eventType === 'recovery' ? 'bg-blue-500' :
                                    event.eventType === 'decline' ? 'bg-orange-500' :
                                    event.eventType === 'high-volume' ? 'bg-purple-500' :
                                    event.eventType === 'critical' ? 'bg-red-600' :
                                    'bg-gray-500',
                              impact: event.eventType === 'peak' || event.eventType === 'recovery' ? 'positive' :
                                     event.eventType === 'valley' || event.eventType === 'decline' || event.eventType === 'critical' ? 'negative' :
                                     'neutral',
                              significance: event.significance
                            }));
                          
                          // Add current state
                          if (journeyEvents.length === 0 || journeyEvents[journeyEvents.length - 1].date !== 'Current') {
                            journeyEvents.push({
                              date: 'Current',
                              status: 'current',
                              title: 'Current State',
                              description: `${healthScore}% organization health score`,
                              color: 'bg-purple-500',
                              impact: healthScore >= 80 ? 'positive' : healthScore >= 60 ? 'neutral' : 'negative'
                            });
                          }
                        } else {
                          // Fallback to single current state
                          journeyEvents = [{
                            date: 'Current',
                            status: 'current',
                            title: 'Current State',
                            description: `${healthScore}% organization health score`,
                            color: 'bg-purple-500',
                            impact: healthScore >= 80 ? 'positive' : healthScore >= 60 ? 'neutral' : 'negative'
                          }];
                        }

                        return (
                          <div className="relative max-h-80 overflow-y-auto pr-2">
                            {/* Timeline line */}
                            <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200"></div>
                            
                            {journeyEvents.map((event, index) => (
                              <div key={index} className="relative flex items-start space-x-4 pb-6">
                                {/* Timeline dot */}
                                <div className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-full ${(() => {
                                  // Ensure success events have visible round colored backgrounds
                                  if (event.status === 'excellence') return 'bg-emerald-500';
                                  if (event.status === 'recovery') return 'bg-green-500';
                                  if (event.status === 'improvement') return 'bg-blue-500';
                                  if (event.status === 'risk-eliminated') return 'bg-green-500';
                                  if (event.status === 'risk-decrease') return 'bg-green-400';
                                  return event.color || 'bg-gray-500';
                                })()} shadow-sm ring-4 ring-white`}>
                                  {(() => {
                                    // Use more vibrant colors for success icons
                                    let iconColor = 'text-white'; // Default for dark backgrounds
                                    
                                    if (event.impact === 'positive' || event.status === 'risk-decrease' || event.status === 'improvement' || event.status === 'recovery' || event.status === 'excellence' || event.status === 'risk-eliminated') {
                                      // Success icons get vibrant colors based on event type
                                      if (event.status === 'excellence') {
                                        iconColor = 'text-green-800'; // Dark green on emerald for vibrant success
                                      } else if (event.status === 'risk-eliminated' || event.status === 'recovery') {
                                        iconColor = 'text-white'; // White on green for strong contrast
                                      } else if (event.status === 'risk-decrease') {
                                        iconColor = 'text-green-800'; // Dark green on light green
                                      } else if (event.status === 'improvement') {
                                        iconColor = 'text-white'; // White on blue
                                      } else {
                                        iconColor = 'text-white'; // Default white for other positive events
                                      }
                                      return <TrendingUp className={`h-4 w-4 ${iconColor}`} />;
                                    }
                                    if (event.impact === 'negative' || event.status === 'critical-burnout' || event.status === 'medium-risk' || event.status === 'decline' || event.status === 'risk-increase') {
                                      return <TrendingDown className={`h-4 w-4 text-white`} />;
                                    }
                                    if (event.impact === 'neutral' || event.status === 'current') {
                                      return <Minus className={`h-4 w-4 text-white`} />;
                                    }
                                    return null;
                                  })()}
                                </div>
                                
                                {/* Event content */}
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center justify-between">
                                    <p className="text-sm font-medium text-gray-900">{event.title}</p>
                                    <time className="text-xs text-gray-500">{event.date}</time>
                                  </div>
                                  <p className="text-sm text-gray-600 mt-1">{event.description}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        );
                        })()
                      )}
                    </div>
                  </CardContent>
                </Card>

                <HealthTrendsChart
                  currentAnalysis={currentAnalysis}
                  historicalTrends={historicalTrends}
                  loadingTrends={loadingTrends}
                />
              </div>

              {/* Burnout Factors Section */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                {/* Radar Chart */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>Team Burnout Risk Factors</CardTitle>
                      {highRiskFactors.length > 0 && (
                        <div className="flex items-center space-x-2">
                          <AlertTriangle className="w-4 h-4 text-red-500" />
                          <span className="text-sm font-medium text-red-600">
                            {highRiskFactors.length} factor{highRiskFactors.length > 1 ? 's' : ''} need{highRiskFactors.length === 1 ? 's' : ''} attention
                          </span>
                        </div>
                      )}
                    </div>
                    <CardDescription>
                      {(() => {
                        const hasGitHubMembers = membersWithGitHubData.length > 0;
                        const hasIncidentMembers = membersWithIncidents.length > 0;
                        
                        if (hasGitHubMembers && hasIncidentMembers) {
                          return `Holistic burnout analysis combining incident response patterns and development activity across ${allActiveMembers.length} team members`;
                        } else if (hasGitHubMembers && !hasIncidentMembers) {
                          return `Development-focused burnout analysis based on GitHub activity patterns from ${membersWithGitHubData.length} active developers`;
                        } else if (!hasGitHubMembers && hasIncidentMembers) {
                          return `Incident response burnout analysis from ${membersWithIncidents.length} team members handling incidents`;
                        } else {
                          return "Team burnout risk assessment based on available activity data";
                        }
                      })()}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[450px] p-4">
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart data={burnoutFactors} margin={{ top: 60, right: 80, bottom: 60, left: 80 }}>
                          <PolarGrid gridType="polygon" />
                          <PolarAngleAxis 
                            dataKey="factor" 
                            tick={{ fontSize: 13, fill: '#374151', fontWeight: 500 }}
                            className="text-sm"
                            tickFormatter={formatRadarLabel}
                          />
                          <PolarRadiusAxis 
                            domain={[0, 100]} 
                            tick={{ fontSize: 11, fill: '#6B7280' }}
                            tickCount={6}
                            angle={270}
                          />
                          <Radar 
                            dataKey="value" 
                            stroke="#8B5CF6" 
                            fill="#8B5CF6" 
                            fillOpacity={0.2}
                            strokeWidth={2}
                            dot={{ fill: '#8B5CF6', strokeWidth: 2, r: 4 }}
                          />
                          <Tooltip 
                            content={({ payload, label }) => {
                              if (payload && payload.length > 0) {
                                const data = payload[0].payload
                                return (
                                  <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
                                    <p className="font-semibold text-gray-900">{label}</p>
                                    <p className="text-purple-600">Score: {Math.round(data.value)}/100</p>
                                    <p className="text-xs text-gray-500 mt-1">
                                      {data.value < 30 ? 'Good' : 
                                       data.value < 50 ? 'Fair' : 
                                       data.value < 70 ? 'Poor' : 'Critical'}
                                    </p>
                                  </div>
                                )
                              }
                              return null
                            }}
                          />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
                
                {/* Risk Factors Bar Chart - Always show if we have any factors */}
                {burnoutFactors.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        {highRiskFactors.length > 0 ? (
                          <>
                            <AlertTriangle className="w-5 h-5 text-red-500" />
                            <span>Risk Factors</span>
                          </>
                        ) : (
                          <>
                            <BarChart3 className="w-5 h-5 text-blue-500" />
                            <span>Risk Factors</span>
                          </>
                        )}
                      </CardTitle>
                      <CardDescription>
                        {highRiskFactors.length > 0 
                          ? "Risk factors requiring immediate attention based on combined incident response and development activity patterns"
                          : "Current risk factors based on team activity patterns"
                        }
                      </CardDescription>
                    </CardHeader>
                    
                    <CardContent>
                      <div className="space-y-4">
                        {burnoutFactors.map((factor, index) => (
                          <div key={factor.factor} className="relative">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center space-x-2">
                                <span className="font-medium text-gray-900">{factor.factor}</span>
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                  factor.severity === 'Critical' ? 'bg-red-100 text-red-800' :
                                  factor.severity === 'Poor' ? 'bg-orange-100 text-orange-800' :
                                  factor.severity === 'Fair' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-green-100 text-green-800'
                                }`}>
                                  {factor.severity}
                                </span>
                              </div>
                              <span className="text-lg font-bold" style={{ color: factor.color }}>
                                {factor.value}/100
                              </span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                              <div 
                                className="h-2 rounded-full transition-all duration-500" 
                                style={{ 
                                  width: `${factor.value}%`,
                                  backgroundColor: (() => {
                                    // Standardize colors to match CBI burnout risk levels (0-100 scale)
                                    if (factor.value < 30) return '#10B981'; // green-500 - Good
                                    if (factor.value < 50) return '#F59E0B'; // yellow-500 - Fair
                                    if (factor.value < 70) return '#F97316'; // orange-500 - Poor
                                    return '#EF4444'; // red-500 - Critical
                                  })()
                                }}
                              ></div>
                            </div>
                            <div className="text-sm text-gray-600">
                              <div>{factor.metrics}</div>
                              {factor.value >= 5 && (
                                <div className="mt-1 text-blue-600">
                                  <strong>Action:</strong> {factor.recommendation}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>


              {/* GitHub and Slack Metrics Section */}
              {(currentAnalysis?.analysis_data?.github_insights || currentAnalysis?.analysis_data?.slack_insights) && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                  {/* GitHub Metrics Card */}
                  {currentAnalysis?.analysis_data?.github_insights && (
                    <Card className="border-2 border-gray-200 bg-white/70 backdrop-blur-sm shadow-lg">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="flex items-center space-x-2">
                            <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
                              <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.942.359.31.678.921.678 1.856 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z" clipRule="evenodd" />
                              </svg>
                            </div>
                            <span className="text-gray-900">GitHub Activity</span>
                          </CardTitle>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openMappingDrawer('github')}
                            className="bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100 hover:text-blue-800 hover:border-blue-300"
                          >
                            <Users className="w-4 h-4 mr-2" />
                            View Mappings
                          </Button>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {(() => {
                          const github = currentAnalysis.analysis_data.github_insights
                          
                          // Check if we have any real GitHub data
                          const hasGitHubData = github && (
                            (github.total_commits && github.total_commits > 0) ||
                            (github.total_pull_requests && github.total_pull_requests > 0) ||
                            (github.total_reviews && github.total_reviews > 0)
                          )
                          
                          if (!hasGitHubData) {
                            return (
                              <div className="text-center py-8">
                                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                  <svg className="w-8 h-8 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.942.359.31.678.921.678 1.856 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z" clipRule="evenodd" />
                                  </svg>
                                </div>
                                <h3 className="text-lg font-medium text-gray-900 mb-2">No GitHub Data Available</h3>
                                <p className="text-sm text-gray-500 mb-4">
                                  {currentAnalysis?.analysis_data?.data_sources?.github_data 
                                    ? "No GitHub activity found for team members in this analysis period"
                                    : "GitHub integration not connected or no team members mapped to GitHub accounts"
                                  }
                                </p>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => openMappingDrawer('github')}
                                  className="bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100"
                                >
                                  <Users className="w-4 h-4 mr-2" />
                                  Configure GitHub Mappings
                                </Button>
                              </div>
                            )
                          }
                          
                          return (
                            <>
                              {/* GitHub Metrics Grid */}
                              <div className="grid grid-cols-2 gap-4">
                                <div className="bg-gray-50 rounded-lg p-3">
                                  <p className="text-xs text-gray-600 font-medium">Total Commits</p>
                                  {github.total_commits ? (
                                    <p className="text-lg font-bold text-gray-900">{github.total_commits.toLocaleString()}</p>
                                  ) : (
                                    <p className="text-lg font-bold text-gray-400 italic">No data</p>
                                  )}
                                </div>
                                <div className="bg-gray-50 rounded-lg p-3">
                                  <p className="text-xs text-gray-600 font-medium">Pull Requests</p>
                                  {github.total_pull_requests ? (
                                    <p className="text-lg font-bold text-gray-900">{github.total_pull_requests.toLocaleString()}</p>
                                  ) : (
                                    <p className="text-lg font-bold text-gray-400 italic">No data</p>
                                  )}
                                </div>
                                <div className="bg-gray-50 rounded-lg p-3">
                                  <p className="text-xs text-gray-600 font-medium">Code Reviews</p>
                                  {github.total_reviews ? (
                                    <p className="text-lg font-bold text-gray-900">{github.total_reviews.toLocaleString()}</p>
                                  ) : (
                                    <p className="text-lg font-bold text-gray-400 italic">No data</p>
                                  )}
                                </div>
                                <div className="bg-gray-50 rounded-lg p-3">
                                  <p className="text-xs text-gray-600 font-medium">After Hours</p>
                                  {github.after_hours_activity_percentage !== undefined && github.after_hours_activity_percentage !== null ? (
                                    <p className="text-lg font-bold text-gray-900">{github.after_hours_activity_percentage.toFixed(1)}%</p>
                                  ) : (
                                    <p className="text-lg font-bold text-gray-400 italic">No data</p>
                                  )}
                                </div>
                                <div className="bg-gray-50 rounded-lg p-3">
                                  <p className="text-xs text-gray-600 font-medium">Weekend Commits</p>
                                  {(github.weekend_activity_percentage !== undefined && github.weekend_activity_percentage !== null) || 
                                   (github.weekend_commit_percentage !== undefined && github.weekend_commit_percentage !== null) ? (
                                    <div>
                                      <p className="text-lg font-bold text-gray-900">{(github.weekend_activity_percentage || github.weekend_commit_percentage || 0).toFixed(1)}%</p>
                                      {github.activity_data?.weekend_commits !== undefined && (
                                        <p className="text-xs text-gray-500">{github.activity_data.weekend_commits} commits</p>
                                      )}
                                    </div>
                                  ) : (
                                    <p className="text-lg font-bold text-gray-400 italic">No data</p>
                                  )}
                                </div>
                              </div>

                              {/* Commit Activity Timeline */}
                              <GitHubCommitsTimeline 
                                analysisId={currentAnalysis?.id ? parseInt(currentAnalysis.id) : 0}
                                totalCommits={github.total_commits || 0}
                                weekendPercentage={(github.weekend_activity_percentage || github.weekend_commit_percentage || 0)}
                              />

                              {/* Burnout Indicators */}
                              {github.burnout_indicators && (
                                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                  <h4 className="text-sm font-semibold text-red-800 mb-2">Burnout Risk Indicators</h4>
                                  {/* Show total high-risk member count if available */}
                                  {(github as any).high_risk_member_count !== undefined && (github as any).high_risk_member_count > 0 && (
                                    <div className="mb-2 pb-2 border-b border-red-200">
                                      <div className="flex items-center space-x-2">
                                        <AlertTriangle className="w-4 h-4 text-red-600" />
                                        <span className="text-sm font-semibold text-red-800">
                                          {(github as any).high_risk_member_count} members with GitHub burnout indicators
                                        </span>
                                      </div>
                                      {/* Show risk distribution if available */}
                                      {(github as any).risk_distribution && (
                                        <div className="mt-1 text-xs text-gray-600">
                                          Overall risk levels: {
                                            (() => {
                                              const dist = (github as any).risk_distribution
                                              const parts = []
                                              if (dist.high > 0) parts.push(`${dist.high} high`)
                                              if (dist.medium > 0) parts.push(`${dist.medium} medium`)
                                              if (dist.low > 0) parts.push(`${dist.low} low`)
                                              
                                              return parts.join(', ') || 'Risk distribution unavailable'
                                            })()
                                          }
                                        </div>
                                      )}
                                    </div>
                                  )}
                                  <div className="space-y-1 text-xs">
                                    {github.burnout_indicators.excessive_late_night_commits > 0 && (
                                      <div className="flex items-center space-x-2">
                                        <AlertTriangle className="w-3 h-3 text-red-600" />
                                        <span className="text-red-700">{github.burnout_indicators.excessive_late_night_commits} members with excessive late-night commits</span>
                                      </div>
                                    )}
                                    {github.burnout_indicators.weekend_workers > 0 && (
                                      <div className="flex items-center space-x-2">
                                        <AlertTriangle className="w-3 h-3 text-red-600" />
                                        <span className="text-red-700">{github.burnout_indicators.weekend_workers} members working weekends</span>
                                      </div>
                                    )}
                                    {github.burnout_indicators.large_pr_pattern > 0 && (
                                      <div className="flex items-center space-x-2">
                                        <AlertTriangle className="w-3 h-3 text-red-600" />
                                        <span className="text-red-700">{github.burnout_indicators.large_pr_pattern} members with large PR patterns</span>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}

                            </>
                          )
                        })()}
                      </CardContent>
                    </Card>
                  )}

                  {/* Slack Metrics Card */}
                  {currentAnalysis?.analysis_data?.slack_insights && (
                    <Card className="border-2 border-purple-200 bg-white/70 backdrop-blur-sm shadow-lg">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="flex items-center space-x-2">
                            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
                              <svg className="w-8 h-8" viewBox="0 0 124 124" fill="none">
                                <path d="M26.3996 78.2003C26.3996 84.7003 21.2996 89.8003 14.7996 89.8003C8.29961 89.8003 3.19961 84.7003 3.19961 78.2003C3.19961 71.7003 8.29961 66.6003 14.7996 66.6003H26.3996V78.2003Z" fill="#E01E5A"/>
                                <path d="M32.2996 78.2003C32.2996 71.7003 37.3996 66.6003 43.8996 66.6003C50.3996 66.6003 55.4996 71.7003 55.4996 78.2003V109.2C55.4996 115.7 50.3996 120.8 43.8996 120.8C37.3996 120.8 32.2996 115.7 32.2996 109.2V78.2003Z" fill="#E01E5A"/>
                                <path d="M43.8996 26.4003C37.3996 26.4003 32.2996 21.3003 32.2996 14.8003C32.2996 8.30026 37.3996 3.20026 43.8996 3.20026C50.3996 3.20026 55.4996 8.30026 55.4996 14.8003V26.4003H43.8996Z" fill="#36C5F0"/>
                                <path d="M43.8996 32.3003C50.3996 32.3003 55.4996 37.4003 55.4996 43.9003C55.4996 50.4003 50.3996 55.5003 43.8996 55.5003H12.8996C6.39961 55.5003 1.29961 50.4003 1.29961 43.9003C1.29961 37.4003 6.39961 32.3003 12.8996 32.3003H43.8996Z" fill="#36C5F0"/>
                                <path d="M95.5996 43.9003C95.5996 37.4003 100.7 32.3003 107.2 32.3003C113.7 32.3003 118.8 37.4003 118.8 43.9003C118.8 50.4003 113.7 55.5003 107.2 55.5003H95.5996V43.9003Z" fill="#2EB67D"/>
                                <path d="M89.6996 43.9003C89.6996 50.4003 84.5996 55.5003 78.0996 55.5003C71.5996 55.5003 66.4996 50.4003 66.4996 43.9003V12.9003C66.4996 6.40026 71.5996 1.30026 78.0996 1.30026C84.5996 1.30026 89.6996 6.40026 89.6996 12.9003V43.9003Z" fill="#2EB67D"/>
                                <path d="M78.0996 95.6003C84.5996 95.6003 89.6996 100.7 89.6996 107.2C89.6996 113.7 84.5996 118.8 78.0996 118.8C71.5996 118.8 66.4996 113.7 66.4996 107.2V95.6003H78.0996Z" fill="#ECB22E"/>
                                <path d="M78.0996 89.7003C71.5996 89.7003 66.4996 84.6003 66.4996 78.1003C66.4996 71.6003 71.5996 66.5003 78.0996 66.5003H109.1C115.6 66.5003 120.7 71.6003 120.7 78.1003C120.7 84.6003 115.6 89.7003 109.1 89.7003H78.0996Z" fill="#ECB22E"/>
                              </svg>
                            </div>
                            <span className="text-gray-900">Slack Communications</span>
                          </CardTitle>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openMappingDrawer('slack')}
                            className="bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100 hover:text-purple-800 hover:border-purple-300"
                          >
                            <Users className="w-4 h-4 mr-2" />
                            View Mappings
                          </Button>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {(() => {
                          const slack = currentAnalysis.analysis_data.slack_insights
                          
                          // Check if this analysis actually has valid Slack data
                          const teamAnalysis = currentAnalysis.analysis_data.team_analysis
                          const teamMembers = Array.isArray(teamAnalysis) ? teamAnalysis : (teamAnalysis?.members || [])
                          const hasRealSlackData = teamMembers.some(member => 
                            member.slack_activity && 
                            (member.slack_activity.messages_sent > 0 || member.slack_activity.channels_active > 0)
                          )
                          
                          // Check for API errors
                          const hasRateLimitErrors = (slack as any)?.errors?.rate_limited_channels?.length > 0
                          const hasOtherErrors = (slack as any)?.errors?.other_errors?.length > 0
                          
                          // If no real Slack data, show empty state
                          if (!hasRealSlackData && !hasRateLimitErrors && !hasOtherErrors) {
                            return (
                              <div className="text-center py-8">
                                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                  <svg className="w-8 h-8 text-gray-400" viewBox="0 0 124 124" fill="currentColor">
                                    <path d="M26.3996 78.2003C26.3996 84.7003 21.2996 89.8003 14.7996 89.8003C8.29961 89.8003 3.19961 84.7003 3.19961 78.2003C3.19961 71.7003 8.29961 66.6003 14.7996 66.6003H26.3996V78.2003Z" />
                                    <path d="M32.2996 78.2003C32.2996 71.7003 37.3996 66.6003 43.8996 66.6003C50.3996 66.6003 55.4996 71.7003 55.4996 78.2003V109.2C55.4996 115.7 50.3996 120.8 43.8996 120.8C37.3996 120.8 32.2996 115.7 32.2996 109.2V78.2003Z" />
                                    <path d="M43.8996 26.4003C37.3996 26.4003 32.2996 21.3003 32.2996 14.8003C32.2996 8.30026 37.3996 3.20026 43.8996 3.20026C50.3996 3.20026 55.4996 8.30026 55.4996 14.8003V26.4003H43.8996Z" />
                                    <path d="M43.8996 32.3003C50.3996 32.3003 55.4996 37.4003 55.4996 43.9003C55.4996 50.4003 50.3996 55.5003 43.8996 55.5003H12.8996C6.39961 55.5003 1.29961 50.4003 1.29961 43.9003C1.29961 37.4003 6.39961 32.3003 12.8996 32.3003H43.8996Z" />
                                  </svg>
                                </div>
                                <h3 className="text-lg font-medium text-gray-900 mb-2">No Slack Data Available</h3>
                                <p className="text-sm text-gray-500 mb-4">
                                  {currentAnalysis?.analysis_data?.data_sources?.slack_data 
                                    ? "No Slack communication activity found for team members in this analysis period"
                                    : "Slack integration not connected or no team members mapped to Slack accounts"
                                  }
                                </p>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => openMappingDrawer('slack')}
                                  className="bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100"
                                >
                                  <Users className="w-4 h-4 mr-2" />
                                  Configure Slack Mappings
                                </Button>
                              </div>
                            )
                          }
                          
                          return (
                            <>
                              {/* Error Messages */}
                              {hasRateLimitErrors && (
                                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                                  <div className="flex items-center space-x-2">
                                    <svg className="w-4 h-4 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                    </svg>
                                    <span className="text-sm font-medium text-yellow-800">Rate Limited</span>
                                  </div>
                                  <p className="text-xs text-yellow-700 mt-1">
                                    Some channels were rate limited: {(slack as any).errors.rate_limited_channels.join(", ")}. 
                                    Data may be incomplete. <button 
                                      onClick={() => window.location.reload()} 
                                      className="text-yellow-800 underline hover:text-yellow-900"
                                    >
                                      Refresh to retry
                                    </button>
                                  </p>
                                </div>
                              )}
                              
                              {hasOtherErrors && (
                                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                  <div className="flex items-center space-x-2">
                                    <svg className="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                    </svg>
                                    <span className="text-sm font-medium text-red-800">Connection Issues</span>
                                  </div>
                                  <p className="text-xs text-red-700 mt-1">
                                    {(slack as any).errors.other_errors.slice(0, 2).join("; ")}
                                    {(slack as any).errors.other_errors.length > 2 && ` and ${(slack as any).errors.other_errors.length - 2} more...`}
                                  </p>
                                </div>
                              )}
                              
                              {/* Only show metrics if we have real data */}
                              {hasRealSlackData && (
                                <>
                                  {/* Slack Metrics Grid */}
                                  <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-purple-50 rounded-lg p-3">
                                      <p className="text-xs text-purple-600 font-medium">Total Messages</p>
                                      {slack?.total_messages ? (
                                        <p className="text-lg font-bold text-purple-900">{slack.total_messages.toLocaleString()}</p>
                                      ) : (
                                        <p className="text-lg font-bold text-gray-400 italic">No data</p>
                                      )}
                                    </div>
                                    <div className="bg-purple-50 rounded-lg p-3">
                                      <p className="text-xs text-purple-600 font-medium">Active Channels</p>
                                      {slack?.active_channels ? (
                                        <p className="text-lg font-bold text-purple-900">{slack.active_channels}</p>
                                      ) : (
                                        <p className="text-lg font-bold text-gray-400 italic">No data</p>
                                      )}
                                    </div>
                                    <div className="bg-purple-50 rounded-lg p-3">
                                      <p className="text-xs text-purple-600 font-medium">After Hours</p>
                                      {slack?.after_hours_activity_percentage !== undefined && slack.after_hours_activity_percentage !== null ? (
                                        <p className="text-lg font-bold text-purple-900">{slack.after_hours_activity_percentage.toFixed(1)}%</p>
                                      ) : (
                                        <p className="text-lg font-bold text-gray-400 italic">No data</p>
                                      )}
                                    </div>
                                    <div className="bg-purple-50 rounded-lg p-3">
                                      <p className="text-xs text-purple-600 font-medium">Weekend Messages</p>
                                      {(slack?.weekend_activity_percentage !== undefined && slack.weekend_activity_percentage !== null) || 
                                       (slack?.weekend_percentage !== undefined && slack.weekend_percentage !== null) ? (
                                        <p className="text-lg font-bold text-purple-900">{(slack.weekend_activity_percentage || slack.weekend_percentage || 0).toFixed(1)}%</p>
                                      ) : (
                                        <p className="text-lg font-bold text-gray-400 italic">No data</p>
                                      )}
                                    </div>
                                    <div className="bg-purple-50 rounded-lg p-3">
                                      <p className="text-xs text-purple-600 font-medium">Avg Response Time</p>
                                      {slack?.avg_response_time_minutes ? (
                                        <p className="text-lg font-bold text-purple-900">{slack.avg_response_time_minutes.toFixed(0)}m</p>
                                      ) : (
                                        <p className="text-lg font-bold text-gray-400 italic">No data</p>
                                      )}
                                    </div>
                                    <div className="bg-purple-50 rounded-lg p-3">
                                      <p className="text-xs text-purple-600 font-medium">Sentiment Score</p>
                                      {slack?.sentiment_analysis?.avg_sentiment !== undefined && slack.sentiment_analysis.avg_sentiment !== null ? (
                                        <p className="text-lg font-bold text-purple-900">{slack.sentiment_analysis.avg_sentiment.toFixed(2)}</p>
                                      ) : (
                                        <p className="text-lg font-bold text-gray-400 italic">No data</p>
                                      )}
                                    </div>
                                  </div>

                                  {/* Sentiment Analysis */}
                                  {slack?.sentiment_analysis && slack.sentiment_analysis.avg_sentiment !== null && (
                                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                      <h4 className="text-sm font-semibold text-blue-800 mb-2">Communication Health</h4>
                                      <div className="flex items-center justify-between">
                                        <span className="text-xs text-blue-700">Average Sentiment</span>
                                        <div className="flex items-center space-x-2">
                                          <span className={`text-lg font-bold ${
                                            (slack.sentiment_analysis.avg_sentiment || 0) > 0.1 ? 'text-green-600' :
                                            (slack.sentiment_analysis.avg_sentiment || 0) < -0.1 ? 'text-red-600' : 'text-yellow-600'
                                          }`}>
                                            {(slack.sentiment_analysis.avg_sentiment || 0) > 0.1 ? 'Positive' :
                                             (slack.sentiment_analysis.avg_sentiment || 0) < -0.1 ? 'Negative' : 'Neutral'}
                                          </span>
                                          <span className="text-xs text-blue-600">
                                            ({slack.sentiment_analysis.avg_sentiment?.toFixed(2) || 'N/A'})
                                          </span>
                                        </div>
                                      </div>
                                    </div>
                                  )}

                                  {/* Burnout Indicators */}
                                  {slack?.burnout_indicators && (
                                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                      <h4 className="text-sm font-semibold text-red-800 mb-2">Communication Risk Indicators</h4>
                                      <div className="space-y-1 text-xs">
                                        {slack.burnout_indicators.excessive_messaging > 0 && (
                                          <div className="flex items-center space-x-2">
                                            <AlertTriangle className="w-3 h-3 text-red-600" />
                                            <span className="text-red-700">{slack.burnout_indicators.excessive_messaging} members with excessive messaging</span>
                                          </div>
                                        )}
                                        {slack.burnout_indicators.poor_sentiment_users > 0 && (
                                          <div className="flex items-center space-x-2">
                                            <AlertTriangle className="w-3 h-3 text-red-600" />
                                            <span className="text-red-700">{slack.burnout_indicators.poor_sentiment_users} members with poor sentiment</span>
                                          </div>
                                        )}
                                        {slack.burnout_indicators.after_hours_communicators > 0 && (
                                          <div className="flex items-center space-x-2">
                                            <AlertTriangle className="w-3 h-3 text-red-600" />
                                            <span className="text-red-700">{slack.burnout_indicators.after_hours_communicators} members communicating after hours</span>
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  )}
                                </>
                              )}
                            </>
                          )
                        })()}
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}

              <TeamMembersList 
                currentAnalysis={currentAnalysis}
                setSelectedMember={setSelectedMember}
                getRiskColor={getRiskColor}
                getProgressColor={getProgressColor}
              />
            </>
          )}

          {/* Analysis Selected But Insufficient Data (For completed analyses with no meaningful data) */}
          {shouldShowInsufficientDataCard() && currentAnalysis.status !== 'failed' && (
            <Card className="text-center p-8 border-yellow-200 bg-yellow-50">
              <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertTriangle className="w-8 h-8 text-yellow-600" />
              </div>
              <h3 className="text-lg font-semibold mb-2 text-yellow-800">Insufficient Data</h3>
              <p className="text-yellow-700 mb-4">
                This analysis has insufficient data to generate meaningful burnout insights. This could be due to lack of organization member data, incident history, or API access issues.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button 
                  onClick={startAnalysis} 
                  className="bg-yellow-600 hover:bg-yellow-700 text-white"
                >
                  <Play className="w-4 h-4 mr-2" />
                  Rerun Analysis
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => {
                    if (currentAnalysis) {
                      openDeleteDialog(currentAnalysis, { stopPropagation: () => {} } as React.MouseEvent)
                    }
                  }}
                  className="border-red-300 text-red-700 hover:bg-red-100"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Remove Selection
                </Button>
              </div>
            </Card>
          )}

          {/* Analysis Not Found State or Auto-Redirect Loader */}
          {!analysisRunning && searchParams.get('analysis') && (redirectingToSuggested || !currentAnalysis) && (
            <Card className={`text-center p-8 ${redirectingToSuggested ? 'border-blue-200 bg-blue-50' : 'border-red-200 bg-red-50'}`}>
              {redirectingToSuggested ? (
                <>
                  <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                  <h3 className="text-xl font-semibold text-blue-900 mb-2">Redirecting to Recent Analysis</h3>
                  <p className="text-blue-700 mb-6">
                    Analysis "{searchParams.get('analysis')}" not found. Redirecting to your most recent analysis...
                  </p>
                </>
              ) : (
                <>
                  <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L4.316 15.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                  </div>
                  <h3 className="text-xl font-semibold text-red-900 mb-2">Analysis Not Found</h3>
                  <p className="text-red-700 mb-6">
                    The analysis with ID "{searchParams.get('analysis')}" could not be found or may have been deleted.
                  </p>
                </>
              )}
              {!redirectingToSuggested && (
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                  <Button 
                    onClick={() => {
                      updateURLWithAnalysis(null)
                      if (previousAnalyses.length > 0) {
                        setCurrentAnalysis(previousAnalyses[0])
                        updateURLWithAnalysis(previousAnalyses[0].uuid || previousAnalyses[0].id)
                      }
                    }}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    Load Most Recent Analysis
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={() => updateURLWithAnalysis(null)}
                    className="border-red-300 text-red-700 hover:bg-red-50"
                  >
                    Clear URL and Start Fresh
                  </Button>
                </div>
              )}
            </Card>
          )}

          {/* Empty State */}
          {!analysisRunning && !currentAnalysis && !searchParams.get('analysis') && (
            <>
              {/* Check if integrations exist */}
              {integrations.length === 0 ? (
                <Card className="text-center p-8">
                  <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Settings className="w-8 h-8 text-blue-600" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2">Setup Required</h3>
                  <p className="text-gray-600 mb-4">
                    Connect your first integration to start analyzing burnout metrics. Both Rootly and PagerDuty are supported.
                  </p>
                  <Button onClick={() => router.push('/integrations')} className="bg-blue-600 hover:bg-blue-700">
                    <Settings className="w-4 h-4 mr-2" />
                    Setup Integrations
                  </Button>
                </Card>
              ) : (
                <>
                  {/* Check for missing platforms */}
                  {(() => {
                    const hasRootly = integrations.some(i => i.platform === 'rootly')
                    
                    if (!hasRootly) {
                      return (
                        <div className="space-y-4 mb-6">
                          {!hasRootly && (
                            <Alert className="border-purple-200 bg-purple-50">
                              <Info className="w-4 h-4 text-purple-600" />
                              <AlertDescription className="text-purple-800">
                                <div className="flex items-center justify-between">
                                  <div>
                                    <strong>Rootly Integration Available</strong>
                                    <span className="block text-sm mt-1">
                                      Connect Rootly for comprehensive incident management and team burnout analysis.
                                    </span>
                                  </div>
                                  <Button 
                                    size="sm" 
                                    onClick={() => router.push('/integrations')} 
                                    className="bg-purple-600 hover:bg-purple-700 ml-4"
                                  >
                                    Setup Rootly
                                  </Button>
                                </div>
                              </AlertDescription>
                            </Alert>
                          )}
                        </div>
                      )
                    }
                    return null
                  })()}
                  
                  {/* Standard empty state */}
                  <Card className="text-center p-8">
                    <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Activity className="w-8 h-8 text-purple-600" />
                    </div>
                    <h3 className="text-lg font-semibold mb-2">No Analysis Yet</h3>
                    <p className="text-gray-600 mb-4">
                      Click "New Analysis" to start analyzing your organization's burnout metrics
                    </p>
                    <Button onClick={startAnalysis} className="bg-purple-600 hover:bg-purple-700">
                      <Play className="w-4 h-4 mr-2" />
                      New Analysis
                    </Button>
                  </Card>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {/* Time Range Selection Dialog */}
      <Dialog open={showTimeRangeDialog} onOpenChange={setShowTimeRangeDialog}>
        <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Start New Analysis</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 block">
                Organization
              </label>
              <div className="p-3 bg-gray-50 rounded-md border border-gray-200">
                {(() => {
                  const selected = integrations.find(i => i.id.toString() === dialogSelectedIntegration)
                  if (selected) {
                    return (
                      <div>
                        <div className="flex items-center">
                          <div className={`w-2 h-2 rounded-full mr-2 ${
                            selected.platform === 'rootly' ? 'bg-purple-500' : 'bg-green-500'
                          }`}></div>
                          <span className="font-medium">
                            {selected.organization_name || selected.name || `${selected.platform === 'rootly' ? 'Rootly' : 'PagerDuty'} Integration`}
                          </span>
                          <Star className="w-4 h-4 text-yellow-500 fill-yellow-500 ml-auto" />
                        </div>
                        <button 
                          onClick={() => {
                            setShowTimeRangeDialog(false)
                            router.push('/integrations')
                          }}
                          className="text-xs text-blue-600 hover:text-blue-800 hover:underline mt-1 block"
                        >
                          Manage integrations
                        </button>
                      </div>
                    )
                  }
                  return <span className="text-gray-500">No organization selected</span>
                })()}
              </div>
            </div>

            {/* Permission Error Alert - Only for Rootly */}
            {dialogSelectedIntegration && (() => {
              const selectedIntegration = integrations.find(i => i.id.toString() === dialogSelectedIntegration);
              
              // Only check permissions for Rootly integrations, not PagerDuty
              if (selectedIntegration?.platform === 'rootly') {
                const hasUserPermission = selectedIntegration?.permissions?.users?.access;
                const hasIncidentPermission = selectedIntegration?.permissions?.incidents?.access;
                
                if (!hasUserPermission || !hasIncidentPermission) {
                  return (
                    <Alert className="border-red-200 bg-red-50 py-2 px-3">
                      <AlertCircle className="w-4 h-4 text-red-600" />
                      <AlertDescription className="text-red-800 text-sm">
                        <strong>Missing Required Permissions</strong>
                        <span className="block mt-1">
                          {!hasUserPermission && !hasIncidentPermission 
                            ? "User and incident read access required" 
                            : !hasUserPermission 
                            ? "User read access required" 
                            : "Incident read access required"}
                        </span>
                        <span className="text-xs opacity-75">Update API token permissions in Rootly settings</span>
                      </AlertDescription>
                    </Alert>
                  );
                }
              }
              return null;
            })()}

            {/* Additional Data Sources */}
            {true && (
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  Additional Data Sources
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {/* GitHub Toggle Card */}
                  {true && (
                    <div className={`border rounded-lg p-3 transition-all ${includeGithub && githubIntegration ? 'border-gray-900 bg-gray-50' : 'border-gray-200 bg-white'}`}>
                      {/* Always show GitHub content immediately, no skeleton loader */}
                      {(
                        <>
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center space-x-2">
                              <div className="w-6 h-6 bg-gray-900 rounded flex items-center justify-center">
                                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.942.359.31.678.921.678 1.856 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z" clipRule="evenodd" />
                                </svg>
                              </div>
                              <div>
                                <h3 className="text-sm font-medium text-gray-900">GitHub</h3>
                              </div>
                            </div>
                            <Switch
                              checked={includeGithub && !!githubIntegration}
                              onCheckedChange={(checked) => {
                                if (!githubIntegration) {
                                  toast.error("GitHub not connected - please connect on integrations page")
                                } else {
                                  setIncludeGithub(checked)
                                }
                              }}
                              disabled={false}
                            />
                          </div>
                          <p className="text-xs text-gray-600 mb-1">Code patterns & activity</p>
                          <p className="text-xs text-gray-500">{githubIntegration?.github_username || 'Not connected'}</p>
                        </>
                      )}
                    </div>
                  )}

                  {/* Slack Toggle Card */}
                  {true && (
                    <div className={`border rounded-lg p-3 transition-all ${includeSlack && slackIntegration ? 'border-purple-500 bg-purple-50' : 'border-gray-200 bg-white'}`}>
                      {/* Always show Slack content immediately, no skeleton loader */}
                      {(
                        <>
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center space-x-2">
                              <div className="w-6 h-6 rounded flex items-center justify-center">
                                <svg className="w-6 h-6" viewBox="0 0 124 124" fill="none">
                                  <path d="M26.3996 78.2003C26.3996 84.7003 21.2996 89.8003 14.7996 89.8003C8.29961 89.8003 3.19961 84.7003 3.19961 78.2003C3.19961 71.7003 8.29961 66.6003 14.7996 66.6003H26.3996V78.2003Z" fill="#E01E5A"/>
                                  <path d="M32.2996 78.2003C32.2996 71.7003 37.3996 66.6003 43.8996 66.6003C50.3996 66.6003 55.4996 71.7003 55.4996 78.2003V109.2C55.4996 115.7 50.3996 120.8 43.8996 120.8C37.3996 120.8 32.2996 115.7 32.2996 109.2V78.2003Z" fill="#E01E5A"/>
                                  <path d="M43.8996 26.4003C37.3996 26.4003 32.2996 21.3003 32.2996 14.8003C32.2996 8.30026 37.3996 3.20026 43.8996 3.20026C50.3996 3.20026 55.4996 8.30026 55.4996 14.8003V26.4003H43.8996Z" fill="#36C5F0"/>
                                  <path d="M43.8996 32.3003C50.3996 32.3003 55.4996 37.4003 55.4996 43.9003C55.4996 50.4003 50.3996 55.5003 43.8996 55.5003H12.8996C6.39961 55.5003 1.29961 50.4003 1.29961 43.9003C1.29961 37.4003 6.39961 32.3003 12.8996 32.3003H43.8996Z" fill="#36C5F0"/>
                                  <path d="M95.5996 43.9003C95.5996 37.4003 100.7 32.3003 107.2 32.3003C113.7 32.3003 118.8 37.4003 118.8 43.9003C118.8 50.4003 113.7 55.5003 107.2 55.5003H95.5996V43.9003Z" fill="#2EB67D"/>
                                  <path d="M89.6996 43.9003C89.6996 50.4003 84.5996 55.5003 78.0996 55.5003C71.5996 55.5003 66.4996 50.4003 66.4996 43.9003V12.9003C66.4996 6.40026 71.5996 1.30026 78.0996 1.30026C84.5996 1.30026 89.6996 6.40026 89.6996 12.9003V43.9003Z" fill="#2EB67D"/>
                                  <path d="M78.0996 95.6003C84.5996 95.6003 89.6996 100.7 89.6996 107.2C89.6996 113.7 84.5996 118.8 78.0996 118.8C71.5996 118.8 66.4996 113.7 66.4996 107.2V95.6003H78.0996Z" fill="#ECB22E"/>
                                  <path d="M78.0996 89.7003C71.5996 89.7003 66.4996 84.6003 66.4996 78.1003C66.4996 71.6003 71.5996 66.5003 78.0996 66.5003H109.1C115.6 66.5003 120.7 71.6003 120.7 78.1003C120.7 84.6003 115.6 89.7003 109.1 89.7003H78.0996Z" fill="#ECB22E"/>
                                </svg>
                              </div>
                              <div>
                                <h3 className="text-sm font-medium text-gray-900">Slack</h3>
                              </div>
                            </div>
                            <Switch
                              checked={includeSlack && !!slackIntegration}
                              onCheckedChange={(checked) => {
                                if (!slackIntegration) {
                                  toast.error("Slack not connected - please connect on integrations page")
                                } else {
                                  setIncludeSlack(checked)
                                }
                              }}
                              disabled={false}
                            />
                          </div>
                          <p className="text-xs text-gray-600 mb-1">Communication patterns</p>
                          <p className="text-xs text-gray-500">
                            {slackIntegration?.total_channels ? `${slackIntegration.total_channels} channels` : (slackIntegration ? 'Connected' : 'Not connected')}
                          </p>
                        </>
                      )}
                    </div>
                  )}

                  {/* Empty grid cell if only one integration */}
                  {false && (
                    <div></div>
                  )}
                </div>
              </div>
            )}

            {/* AI Insights Toggle */}
            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 block">
                AI Insights
              </label>
              <div className={`border rounded-lg p-4 transition-all ${enableAI ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white'}`}>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
                      <div className="w-5 h-5 text-blue-600">🤖</div>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">Enhanced AI Analysis</h3>
                      <p className="text-xs text-gray-600">Natural language reasoning and insights</p>
                    </div>
                  </div>
                  <Switch
                    checked={enableAI}
                    onCheckedChange={setEnableAI}
                  />
                </div>
                
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-xs font-medium text-green-700">
                      Anthropic Claude Connected (Railway)
                    </span>
                  </div>
                  <div className="text-xs text-gray-600">
                    {enableAI ? 
                      '✨ AI will provide intelligent analysis and recommendations' : 
                      '⚡ Using traditional pattern analysis only'
                    }
                  </div>
                </div>
              </div>
            </div>
            
            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 block">
                Analysis Time Range
              </label>
              <Select value={selectedTimeRange} onValueChange={setSelectedTimeRange}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="3">Last 3 days</SelectItem>
                  <SelectItem value="7">Last 7 days</SelectItem>
                  <SelectItem value="30">Last 30 days</SelectItem>
                  <SelectItem value="60">Last 60 days</SelectItem>
                  <SelectItem value="90">Last 90 days</SelectItem>
                  <SelectItem value="180">Last 6 months</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex justify-end space-x-2 pt-4">
              <Button variant="outline" onClick={() => setShowTimeRangeDialog(false)}>
                Cancel
              </Button>
              <Button 
                onClick={runAnalysisWithTimeRange} 
                className="bg-purple-600 hover:bg-purple-700"
                disabled={!dialogSelectedIntegration || (() => {
                  const selectedIntegration = integrations.find(i => i.id.toString() === dialogSelectedIntegration);
                  
                  // Only check permissions for Rootly integrations, not PagerDuty
                  if (selectedIntegration?.platform === 'rootly') {
                    const hasUserPermission = selectedIntegration?.permissions?.users?.access;
                    const hasIncidentPermission = selectedIntegration?.permissions?.incidents?.access;
                    return !hasUserPermission || !hasIncidentPermission;
                  }
                  
                  // For PagerDuty or other platforms, don't block based on permissions
                  return false;
                })()}
              >
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Start Analysis
                </>
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <MemberDetailModal
        selectedMember={selectedMember}
        setSelectedMember={setSelectedMember}
        members={members}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-4 h-4 text-red-600" />
              </div>
              <span>Delete Analysis</span>
            </DialogTitle>
            <DialogDescription className="text-gray-600 mt-2">
              Are you sure you want to delete this analysis? This action cannot be undone and will permanently remove all data associated with this analysis.
            </DialogDescription>
          </DialogHeader>
          
          {analysisToDelete && (
            <div className="my-4 p-3 bg-gray-50 rounded-lg border">
              <div className="flex items-center justify-between text-sm">
                <div className="flex flex-col">
                  <span className="font-medium text-gray-900">
                    {integrations.find(i => i.id === Number(analysisToDelete.integration_id))?.name || 
                     integrations.find(i => String(i.id) === String(analysisToDelete.integration_id))?.name || 
                     `Organization ${analysisToDelete.integration_id}`}
                  </span>
                  <span className="text-gray-500">
                    {new Date(analysisToDelete.created_at).toLocaleString([], { 
                      month: 'short', 
                      day: 'numeric', 
                      year: 'numeric',
                      hour: 'numeric',
                      minute: '2-digit',
                      hour12: true,
                      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    })}
                  </span>
                </div>
                <span className="text-gray-400 text-xs">
                  {analysisToDelete.time_range || 30} days
                </span>
              </div>
            </div>
          )}

          <DialogFooter className="flex space-x-2">
            <Button
              variant="outline"
              onClick={() => {
                setDeleteDialogOpen(false)
                setAnalysisToDelete(null)
              }}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDeleteAnalysis}
              className="flex-1 bg-red-600 hover:bg-red-700"
            >
              Delete Analysis
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Mapping Drawer */}
      <MappingDrawer
        isOpen={mappingDrawerOpen}
        onClose={() => setMappingDrawerOpen(false)}
        platform={mappingDrawerPlatform}
        onRefresh={fetchPlatformMappings}
      />
    </div>
  )
}