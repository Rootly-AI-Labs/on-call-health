"use client"

import { 
  Heart, 
  Shield, 
  BarChart3, 
  Database,
  CheckCircle,
  Minus,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  Info
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface TeamHealthOverviewProps {
  currentAnalysis: any
  historicalTrends: any
  expandedDataSources: {
    incident: boolean
    github: boolean
    slack: boolean
  }
  setExpandedDataSources: (fn: (prev: any) => any) => void
}

export function TeamHealthOverview({
  currentAnalysis,
  historicalTrends,
  expandedDataSources,
  setExpandedDataSources
}: TeamHealthOverviewProps) {
  return (
    <>
      {/* Tooltip Portal */}
      <div className="fixed z-[99999] invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gray-900 text-white text-xs rounded-lg p-3 w-64 shadow-lg pointer-events-none"
           id="health-score-tooltip"
           style={{ top: '-200px', left: '-200px' }}>
        <div className="space-y-2">
          <div><strong className="text-green-400">Excellent (90-100%):</strong> Low stress, sustainable workload</div>
          <div><strong className="text-blue-400">Good (70-89%):</strong> Manageable workload with minor stress</div>
          <div><strong className="text-yellow-400">Fair (50-69%):</strong> Moderate stress, watch for trends</div>
          <div><strong className="text-orange-400">Poor (30-49%):</strong> High stress, intervention needed</div>
          <div><strong className="text-red-400">Critical (&lt;30%):</strong> Severe burnout risk</div>
        </div>
        <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-900"></div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6 overflow-visible">
        <Card className="border-2 border-purple-200 bg-white/70 backdrop-blur-sm shadow-lg overflow-visible">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-purple-700 flex items-center space-x-2">
              <Heart className="w-4 h-4" />
              <span>Team Health</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {currentAnalysis?.analysis_data?.team_health || (currentAnalysis?.analysis_data?.team_analysis && currentAnalysis?.status === 'completed') ? (
              <div>
                <div className="flex items-start space-x-3">
                  <div>
                    <div className="text-2xl font-bold text-gray-900">{(() => {
                      // Use the latest point from health trends for consistency with chart
                      if (historicalTrends?.daily_trends?.length > 0) {
                        const latestTrend = historicalTrends.daily_trends[historicalTrends.daily_trends.length - 1];
                        return `${Math.round(latestTrend.overall_score * 10)}%`;
                      }
                      // Fallback to current analysis daily trends if available
                      if (currentAnalysis?.analysis_data?.daily_trends?.length > 0) {
                        const latestTrend = currentAnalysis.analysis_data.daily_trends[currentAnalysis.analysis_data.daily_trends.length - 1];
                        return `${Math.round(latestTrend.overall_score * 10)}%`;
                      }
                      // Show real data from team_health if available
                      if (currentAnalysis?.analysis_data?.team_health) {
                        return `${Math.round(currentAnalysis.analysis_data.team_health.overall_score * 10)}%`;
                      }
                      if (currentAnalysis?.analysis_data?.team_summary) {
                        return `${Math.round(currentAnalysis.analysis_data.team_summary.average_score * 10)}%`;
                      }
                      // NO FALLBACK DATA - show actual system state
                      return "No data";
                    })()}</div>
                    <div className="text-xs text-gray-500">Current</div>
                  </div>
                  {(() => {
                    // Debug: Log what data is available
                    console.log("Debug - historicalTrends:", historicalTrends);
                    console.log("Debug - period_summary:", currentAnalysis?.analysis_data?.period_summary);
                    console.log("Debug - daily_trends length:", currentAnalysis?.analysis_data?.daily_trends?.length);
                    console.log("Debug - team_health:", currentAnalysis?.analysis_data?.team_health);
                    // Always show average section, handle fallbacks inside
                    return true;
                  })() && (
                    <div className="border-l border-gray-200 pl-3">
                      <div className="text-2xl font-bold text-gray-900">{(() => {
                        // Calculate average directly from Health Trends chart data (same source as chart)
                        if (historicalTrends?.daily_trends?.length > 0) {
                          const dailyScores = historicalTrends.daily_trends.map((d: any) => d.overall_score);
                          const average = dailyScores.reduce((a: number, b: number) => a + b, 0) / dailyScores.length;
                          console.log("Debug - calculated average from historicalTrends daily_trends:", average * 10);
                          return `${Math.round(average * 10)}%`; // Convert 0-10 to 0-100%
                        }
                        // Fallback: Calculate from current analysis daily trends
                        if (currentAnalysis?.analysis_data?.daily_trends?.length > 0) {
                          const dailyScores = currentAnalysis.analysis_data.daily_trends.map((d: any) => d.overall_score);
                          const average = dailyScores.reduce((a: number, b: number) => a + b, 0) / dailyScores.length;
                          console.log("Debug - calculated average from currentAnalysis daily_trends:", average * 10);
                          return `${Math.round(average * 10)}%`; // Convert 0-10 to 0-100%
                        }
                        // Use current score if daily trends are empty but historical available
                        if (historicalTrends?.daily_trends?.length > 0) {
                          const latestTrend = historicalTrends.daily_trends[historicalTrends.daily_trends.length - 1];
                          console.log("Debug - using latest trend:", latestTrend.overall_score * 10);
                          return `${Math.round(latestTrend.overall_score * 10)}%`;
                        }
                        console.log("Debug - no data available for average");
                        return "No data";
                      })()}</div>
                      <div className="text-xs text-gray-500">{currentAnalysis?.time_range || 30}-day avg</div>
                    </div>
                  )}
                </div>
                <div className="mt-2 flex items-center space-x-1">
                  <div className="text-sm font-medium text-purple-600">{(() => {
                    // Use the same data source as current score for consistency
                    let currentScore = 0;
                    
                    if (historicalTrends?.daily_trends?.length > 0) {
                      const latestTrend = historicalTrends.daily_trends[historicalTrends.daily_trends.length - 1];
                      currentScore = latestTrend.overall_score;
                    } else if (currentAnalysis?.analysis_data?.daily_trends?.length > 0) {
                      const latestTrend = currentAnalysis.analysis_data.daily_trends[currentAnalysis.analysis_data.daily_trends.length - 1];
                      currentScore = latestTrend.overall_score;
                    } else if (currentAnalysis?.analysis_data?.team_health) {
                      currentScore = currentAnalysis.analysis_data.team_health.overall_score;
                    } else if (currentAnalysis?.analysis_data?.team_summary) {
                      currentScore = currentAnalysis.analysis_data.team_summary.average_score;
                    }
                    
                    // Convert to health status (0-10 scale, higher=better)
                    // Match tooltip ranges exactly: Good (70-89%), Fair (50-69%), Poor (30-49%), Critical (<30%)
                    if (currentScore >= 9) return 'Excellent';  // 90-100%
                    if (currentScore >= 7) return 'Good';        // 70-89% - "Manageable workload with minor stress"
                    if (currentScore >= 5) return 'Fair';        // 50-69% - "Moderate stress, watch for trends"  
                    if (currentScore >= 3) return 'Poor';        // 30-49% - "High stress, intervention needed"
                    return 'Critical';                           // <30% - "Severe burnout risk"
                  })()}</div>
                  <Info className="w-3 h-3 text-purple-500" 
                          onMouseEnter={(e) => {
                            const tooltip = document.getElementById('health-score-tooltip')
                            if (tooltip) {
                              const rect = e.currentTarget.getBoundingClientRect()
                              tooltip.style.top = `${rect.top - 180}px`
                              tooltip.style.left = `${rect.left - 120}px`
                              tooltip.classList.remove('invisible', 'opacity-0')
                              tooltip.classList.add('visible', 'opacity-100')
                            }
                          }}
                          onMouseLeave={() => {
                            const tooltip = document.getElementById('health-score-tooltip')
                            if (tooltip) {
                              tooltip.classList.add('invisible', 'opacity-0')
                              tooltip.classList.remove('visible', 'opacity-100')
                            }
                          }} />
                </div>
                <p className="text-xs text-gray-600 mt-1">
                  {(() => {
                    const status = (currentAnalysis.analysis_data.team_health?.health_status || (() => {
                      // Use the SAME score calculation logic as the percentage display for consistency
                      let currentScore = 0;
                      if (historicalTrends?.daily_trends?.length > 0) {
                        const latestTrend = historicalTrends.daily_trends[historicalTrends.daily_trends.length - 1];
                        currentScore = latestTrend.overall_score;
                      } else if (currentAnalysis?.analysis_data?.daily_trends?.length > 0) {
                        const latestTrend = currentAnalysis.analysis_data.daily_trends[currentAnalysis.analysis_data.daily_trends.length - 1];
                        currentScore = latestTrend.overall_score;
                      } else if (currentAnalysis?.analysis_data?.team_health) {
                        currentScore = currentAnalysis.analysis_data.team_health.overall_score;
                      } else if (currentAnalysis?.analysis_data?.team_summary) {
                        currentScore = currentAnalysis.analysis_data.team_summary.average_score;
                      }
                      
                      // Convert to health status using exact tooltip ranges: Good (70-89%), Fair (50-69%), Poor (30-49%), Critical (<30%)
                      if (!currentScore) return 'good';  // Default to good instead of excellent
                      if (currentScore >= 9) return 'excellent';  // 90-100%
                      if (currentScore >= 7) return 'good';       // 70-89% - "Manageable workload with minor stress"
                      if (currentScore >= 5) return 'fair';       // 50-69% - "Moderate stress, watch for trends"
                      if (currentScore >= 3) return 'poor';       // 30-49% - "High stress, intervention needed"
                      return 'critical';                          // <30% - "Severe burnout risk"
                    })()).toLowerCase()
                    switch(status) {
                      case 'excellent':
                        return 'Low stress, sustainable workload'
                      case 'good':
                        return 'Manageable workload with minor stress'
                      case 'fair':
                        return 'Moderate stress, watch for trends'
                      case 'poor':
                        return 'High stress, intervention needed'
                      case 'critical':
                        return 'Severe burnout risk'
                      default:
                        return 'Measures team workload sustainability and burnout risk levels'
                    }
                  })()}
                </p>
              </div>
            ) : (
              <div className="text-gray-500">
                {currentAnalysis?.status === 'failed' ? 'Analysis failed' : 'Analysis in progress...'}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-2 border-purple-200 bg-white/70 backdrop-blur-sm shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-purple-700 flex items-center space-x-2">
              <Shield className="w-4 h-4" />
              <span>At Risk</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {currentAnalysis?.analysis_data?.team_health || (currentAnalysis?.analysis_data?.team_analysis && currentAnalysis?.status === 'completed') ? (
              <div>
                <div className="space-y-1">
                  {(currentAnalysis.analysis_data.team_health?.risk_distribution?.critical > 0 || currentAnalysis.analysis_data.team_summary?.risk_distribution?.critical > 0) && (
                    <div className="flex items-center space-x-2">
                      <div className="text-2xl font-bold text-red-800">{currentAnalysis.analysis_data.team_health?.risk_distribution?.critical || currentAnalysis.analysis_data.team_summary?.risk_distribution?.critical || 0}</div>
                      <AlertTriangle className="w-6 h-6 text-red-700" />
                      <span className="text-sm text-gray-600">Critical risk</span>
                    </div>
                  )}
                  <div className="flex items-center space-x-2">
                    <div className="text-2xl font-bold text-red-600">{currentAnalysis.analysis_data.team_health?.risk_distribution?.high || currentAnalysis.analysis_data.team_summary?.risk_distribution?.high || 0}</div>
                    <AlertTriangle className="w-6 h-6 text-red-500" />
                    <span className="text-sm text-gray-600">High risk</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="text-2xl font-bold text-orange-600">{currentAnalysis.analysis_data.team_health?.risk_distribution?.medium || currentAnalysis.analysis_data.team_summary?.risk_distribution?.medium || 0}</div>
                    <div className="w-6 h-6 rounded-full bg-orange-500/20 flex items-center justify-center">
                      <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                    </div>
                    <span className="text-sm text-gray-600">Medium risk</span>
                  </div>
                </div>
                <p className="text-xs text-gray-600 mt-2">
                  Out of {Array.isArray(currentAnalysis.analysis_data.team_analysis) ? currentAnalysis.analysis_data.team_analysis.length : (currentAnalysis.analysis_data.team_analysis?.members?.length || 0)} members
                </p>
              </div>
            ) : (
              <div className="text-gray-500">
                {currentAnalysis?.status === 'failed' ? 'Analysis failed' : 'Analysis in progress...'}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-2 border-purple-200 bg-white/70 backdrop-blur-sm shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-purple-700 flex items-center space-x-2">
              <BarChart3 className="w-4 h-4" />
              <span>Total Incidents</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">
              {(currentAnalysis.analysis_data as any)?.metadata?.total_incidents !== undefined 
                ? (currentAnalysis.analysis_data as any).metadata.total_incidents
                : (currentAnalysis.analysis_data as any)?.team_analysis?.total_incidents !== undefined
                ? (currentAnalysis.analysis_data as any).team_analysis.total_incidents
                : currentAnalysis.analysis_data?.partial_data?.incidents?.length || 0}
            </div>
            <p className="text-xs text-gray-600 mt-1">
              In the last {currentAnalysis.time_range || 30} days
            </p>
            {(currentAnalysis.analysis_data as any)?.metadata?.severity_breakdown && (
              <div className={`mt-4 grid ${(currentAnalysis.analysis_data as any).metadata.severity_breakdown.sev0_count > 0 ? 'grid-cols-5' : 'grid-cols-4'} gap-2`}>
                {(currentAnalysis.analysis_data as any).metadata.severity_breakdown.sev0_count > 0 && (
                  <div className="bg-purple-50 rounded-lg p-2 text-center">
                    <div className="text-xs font-semibold text-purple-700">SEV0</div>
                    <div className="text-lg font-bold text-purple-600">
                      {(currentAnalysis.analysis_data as any).metadata.severity_breakdown.sev0_count}
                    </div>
                  </div>
                )}
                <div className="bg-red-50 rounded-lg p-2 text-center">
                  <div className="text-xs font-semibold text-red-700">SEV1</div>
                  <div className="text-lg font-bold text-red-600">
                    {(currentAnalysis.analysis_data as any).metadata.severity_breakdown.sev1_count || 0}
                  </div>
                </div>
                <div className="bg-orange-50 rounded-lg p-2 text-center">
                  <div className="text-xs font-semibold text-orange-700">SEV2</div>
                  <div className="text-lg font-bold text-orange-600">
                    {(currentAnalysis.analysis_data as any).metadata.severity_breakdown.sev2_count || 0}
                  </div>
                </div>
                <div className="bg-yellow-50 rounded-lg p-2 text-center">
                  <div className="text-xs font-semibold text-yellow-700">SEV3</div>
                  <div className="text-lg font-bold text-yellow-600">
                    {(currentAnalysis.analysis_data as any).metadata.severity_breakdown.sev3_count || 0}
                  </div>
                </div>
                <div className="bg-green-50 rounded-lg p-2 text-center">
                  <div className="text-xs font-semibold text-green-700">SEV4</div>
                  <div className="text-lg font-bold text-green-600">
                    {(currentAnalysis.analysis_data as any).metadata.severity_breakdown.sev4_count || 0}
                  </div>
                </div>
              </div>
            )}
            {currentAnalysis.analysis_data?.session_hours !== undefined && (
              <p className="text-xs text-gray-600 mt-1">
                {currentAnalysis.analysis_data.session_hours?.toFixed(1) || '0.0'} total hours
              </p>
            )}
          </CardContent>
        </Card>

        {/* Data Sources Card */}
        <Card className="border-2 border-blue-200 bg-white/70 backdrop-blur-sm shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-blue-700 flex items-center space-x-2">
              <Database className="w-4 h-4" />
              <span>Data Sources</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {/* Incident Data */}
              <div className="space-y-2">
                <div 
                  className="flex items-center cursor-pointer hover:bg-gray-50 rounded px-1 py-0.5 transition-colors"
                  onClick={() => setExpandedDataSources(prev => ({ ...prev, incident: !prev.incident }))}
                >
                  {expandedDataSources.incident ? 
                    <ChevronDown className="w-3 h-3 mr-1 text-gray-500" /> : 
                    <ChevronRight className="w-3 h-3 mr-1 text-gray-500" />
                  }
                  <div className="w-2 h-2 bg-purple-500 rounded-full mr-2"></div>
                  <span className="text-xs font-medium text-slate-700 flex-1">Incident Management</span>
                  <CheckCircle className="w-3 h-3 text-green-600 ml-2" />
                </div>
                {expandedDataSources.incident && (
                  <div className="ml-7 text-xs text-gray-600 space-y-1">
                    <div>• {(currentAnalysis?.analysis_data as any)?.metadata?.total_incidents || 0} incidents</div>
                    <div>• {(currentAnalysis?.analysis_data as any)?.team_analysis?.members?.length || 0} users</div>
                  </div>
                )}
              </div>
              
              {/* GitHub Data */}
              <div className="space-y-2">
                <div 
                  className="flex items-center cursor-pointer hover:bg-gray-50 rounded px-1 py-0.5 transition-colors"
                  onClick={() => setExpandedDataSources(prev => ({ ...prev, github: !prev.github }))}
                >
                  {expandedDataSources.github ? 
                    <ChevronDown className="w-3 h-3 mr-1 text-gray-500" /> : 
                    <ChevronRight className="w-3 h-3 mr-1 text-gray-500" />
                  }
                  <div className="w-2 h-2 bg-gray-900 rounded-full mr-2"></div>
                  <span className="text-xs font-medium text-slate-700 flex-1">GitHub Activity</span>
                  {currentAnalysis?.analysis_data?.data_sources?.github_data ? (
                    <CheckCircle className="w-3 h-3 text-green-600 ml-2" />
                  ) : (
                    <Minus className="w-3 h-3 text-gray-400 ml-2" />
                  )}
                </div>
                {expandedDataSources.github && currentAnalysis?.analysis_data?.data_sources?.github_data && (
                  <div className="ml-7 text-xs text-gray-600 space-y-1">
                    <div>• {currentAnalysis?.analysis_data?.github_insights?.total_commits?.toLocaleString() || '0'} commits</div>
                    <div>• {currentAnalysis?.analysis_data?.github_insights?.total_pull_requests?.toLocaleString() || '0'} PRs</div>
                  </div>
                )}
              </div>
              
              {/* Slack Data */}
              <div className="space-y-2">
                <div 
                  className="flex items-center cursor-pointer hover:bg-gray-50 rounded px-1 py-0.5 transition-colors"
                  onClick={() => setExpandedDataSources(prev => ({ ...prev, slack: !prev.slack }))}
                >
                  {expandedDataSources.slack ? 
                    <ChevronDown className="w-3 h-3 mr-1 text-gray-500" /> : 
                    <ChevronRight className="w-3 h-3 mr-1 text-gray-500" />
                  }
                  <div className="w-2 h-2 bg-purple-500 rounded-full mr-2"></div>
                  <span className="text-xs font-medium text-slate-700 flex-1">Slack Communications</span>
                  {currentAnalysis?.analysis_data?.data_sources?.slack_data ? (
                    <CheckCircle className="w-3 h-3 text-green-600 ml-2" />
                  ) : (
                    <Minus className="w-3 h-3 text-gray-400 ml-2" />
                  )}
                </div>
                {expandedDataSources.slack && currentAnalysis?.analysis_data?.data_sources?.slack_data && (
                  <div className="ml-7 text-xs text-gray-600 space-y-1">
                    <div>• {currentAnalysis?.analysis_data?.slack_insights?.total_messages?.toLocaleString() || '0'} messages</div>
                    <div>• {currentAnalysis?.analysis_data?.slack_insights?.active_channels?.toLocaleString() || '0'} channels</div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}