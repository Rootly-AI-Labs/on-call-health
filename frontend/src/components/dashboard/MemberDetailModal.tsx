"use client"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts"
import { Info } from "lucide-react"

interface MemberDetailModalProps {
  selectedMember: any | null
  setSelectedMember: (member: any | null) => void
  members: any[]
}

export function MemberDetailModal({
  selectedMember,
  setSelectedMember,
  members
}: MemberDetailModalProps) {
  if (!selectedMember) return null

  return (
    <Dialog open={!!selectedMember} onOpenChange={() => setSelectedMember(null)}>
      <DialogContent className="max-w-5xl max-h-[80vh] overflow-y-auto">
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
                        <p className="text-gray-600">{selectedMember?.role || selectedMember?.email}</p>
                      </div>
                      {memberData && 'github_burnout_breakdown' in memberData && memberData.github_burnout_breakdown && (
                        <span className={`text-xs font-semibold px-3 py-1 rounded-full ${
                          (memberData.github_burnout_breakdown as any).score_source === 'github_based' ? 'bg-blue-100 text-blue-800' :
                          (memberData.github_burnout_breakdown as any).score_source === 'hybrid' ? 'bg-purple-100 text-purple-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {(memberData.github_burnout_breakdown as any).score_source === 'github_based' ? 'GitHub Activity Only' :
                           (memberData.github_burnout_breakdown as any).score_source === 'hybrid' ? 'GitHub + Incidents Combined' :
                           'Incident-Based Only'}
                        </span>
                      )}
                    </div>
                  </div>
                </DialogTitle>
              </DialogHeader>
          
          {(() => {
            // Get the correct burnout score (handle both data formats)
            const burnoutScore = memberData?.burnout_score || (selectedMember.burnoutScore ? selectedMember.burnoutScore / 10 : 0) || 0;
            
            // Burnout dimensions no longer used - replaced with CBI scores
          
          // Calculate overall burnout score (0-10 scale, higher = more burnout, consistent with dimensions)
          const overallBurnoutScore = Math.max(0, Math.min(10, burnoutScore || 0));
          const healthStatus = overallBurnoutScore <= 3 ? 'Low Risk' : 
                             overallBurnoutScore <= 5 ? 'Moderate Risk' : 
                             overallBurnoutScore <= 7 ? 'High Risk' : 'Critical Risk';
          const healthColor = overallBurnoutScore <= 3 ? 'text-green-700 bg-green-100 font-medium' : 
                            overallBurnoutScore <= 5 ? 'text-amber-700 bg-amber-100 font-medium' : 
                            overallBurnoutScore <= 7 ? 'text-orange-700 bg-orange-100 font-medium' : 'text-red-700 bg-red-100 font-medium';
                            
          // Generate burnout summary highlighting concrete metrics and patterns
          const burnoutSummary = (() => {
            const concerns = [];
            const metrics = [];
            
            // Analyze concrete incident data
            const incidentCount = memberData?.incident_count || 0;
            const afterHoursPercent = memberData?.metrics?.after_hours_percentage || 0;
            const weekendPercent = memberData?.metrics?.weekend_percentage || 0;
            const avgResponseTime = memberData?.metrics?.avg_response_time_minutes || 0;
            
            // Incident load concerns
            if (incidentCount > 30) {
              concerns.push(`handling ${incidentCount} incidents (high volume)`);
            } else if (incidentCount > 15) {
              concerns.push(`managing ${incidentCount} incidents`);
            }
            
            // After-hours work patterns
            if (afterHoursPercent > 50) {
              concerns.push(`${afterHoursPercent.toFixed(0)}% of incidents handled after-hours`);
            } else if (afterHoursPercent > 20) {
              concerns.push(`${afterHoursPercent.toFixed(0)}% after-hours incident work`);
            }
            
            // Weekend work disruption
            if (weekendPercent > 20) {
              concerns.push(`${weekendPercent.toFixed(0)}% weekend incident activity`);
            }
            
            // Response time pressure
            if (avgResponseTime > 60) {
              concerns.push(`${Math.round(avgResponseTime)} min average response time`);
            }
            
            // GitHub activity patterns
            if (selectedMember.github_activity?.burnout_indicators) {
              const indicators = selectedMember.github_activity.burnout_indicators;
              if (indicators.excessive_commits) metrics.push("high commit frequency");
              if (indicators.late_night_activity) metrics.push("late-night coding");
              if (indicators.weekend_work) metrics.push("weekend development work");
            }
            
            return {
              concerns,
              metrics,
              summary: concerns.length > 0 ? 
                `Primary stressors include ${concerns.slice(0, 2).join(' and ')}.` : 
                'No significant risk indicators identified.'
            };
          })();
        
        return (
          <div className="mt-4 space-y-6">
            {/* Overall Burnout Assessment */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardContent className="p-4 text-center">
                  <p className="text-sm text-gray-600 mb-2">Overall Risk Level</p>
                  {(() => {
                    // Calculate CBI-based risk level when available
                    const getCBIRiskLevel = () => {
                      if (memberData?.cbi_score !== undefined && memberData?.cbi_score !== null) {
                        // Use CBI scoring (0-100, higher = more burnout)
                        if (memberData.cbi_score < 25) return { level: 'healthy', label: 'Healthy' };
                        if (memberData.cbi_score < 50) return { level: 'fair', label: 'Fair' };
                        if (memberData.cbi_score < 75) return { level: 'poor', label: 'Poor' };
                        return { level: 'critical', label: 'Critical' };
                      }
                      // Fallback to legacy system
                      return { level: selectedMember.riskLevel.toLowerCase(), label: healthStatus };
                    };
                    
                    const riskInfo = getCBIRiskLevel();
                    const getCBIColor = (level: string) => {
                      switch(level) {
                        case 'critical': return 'bg-red-100 text-red-800 border-red-300';
                        case 'poor': return 'bg-red-50 text-red-600 border-red-200'; 
                        case 'fair': return 'bg-yellow-50 text-yellow-600 border-yellow-200';
                        case 'healthy': return 'bg-green-50 text-green-600 border-green-200';
                        default: return healthColor;
                      }
                    };
                    
                    return (
                      <Badge className={`px-3 py-1 ${getCBIColor(riskInfo.level)}`}>
                        {riskInfo.label}
                      </Badge>
                    );
                  })()}
                  <div className="mt-3">
                    <div className={`text-2xl font-bold ${(() => {
                      if (memberData?.cbi_score !== undefined) {
                        // Color the CBI score based on risk level
                        const score = memberData.cbi_score;
                        if (score < 25) return 'text-green-600';      // Healthy
                        if (score < 50) return 'text-yellow-600';     // Fair
                        if (score < 75) return 'text-orange-600';     // Poor  
                        return 'text-red-600';                       // Critical
                      }
                      return 'text-gray-900'; // Legacy fallback
                    })()}`}>
                      {memberData?.cbi_score !== undefined ? 
                        `${memberData.cbi_score.toFixed(0)}/100` : 
                        `${(overallBurnoutScore * 10).toFixed(0)}%`
                      }
                    </div>
                    <p className="text-xs text-gray-500">
                      {memberData?.cbi_score !== undefined ? 'CBI Score' : 'Burnout Risk Score'}
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
                  <p className="text-xs text-gray-500">Past 30 days</p>
                </CardContent>
              </Card>
              
            </div>
            
            {/* CBI Burnout Analysis */}
            <Card>
              <CardContent className="p-4">
                <h4 className="font-semibold text-gray-900 mb-2">Burnout Analysis</h4>
                {memberData?.cbi_reasoning ? (
                  <div className="space-y-6">
                    {/* Contributing Factors */}
                    <div className="space-y-3">
                      <h5 className="text-sm font-semibold text-gray-900 mb-3 pb-1 border-b border-gray-200">
                        Factors
                      </h5>
                      <div className="space-y-2">
                        {memberData.cbi_reasoning.slice(1).map((reason: string, index: number) => {
                          const cleanReason = reason.replace(/^[\s]*[•·\-*]\s*/, '').trim();
                          
                          // Skip section headers
                          const isSectionHeader = cleanReason.endsWith(':');
                          if (isSectionHeader) return null;
                          
                          return (
                            <div key={index} className="px-3 py-2 bg-gray-50 rounded-md border text-sm text-gray-700">
                              {cleanReason}
                            </div>
                          );
                        }).filter(Boolean)}
                      </div>
                    </div>

                    {/* Dimensional Breakdown */}
                    {memberData.cbi_breakdown && (
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-green-50 rounded-lg p-3">
                          <div className="flex items-center space-x-1 mb-1">
                            <div className="text-xs font-medium text-green-600 uppercase">Personal</div>
                            <div className="relative group">
                              <Info className="w-3 h-3 text-green-500 cursor-help" />
                              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg w-72 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                                <div className="font-semibold mb-1">Personal Burnout - What We Measure</div>
                                <div>• Incident frequency (incidents per week)<br/>• After-hours work patterns<br/>• Weekend activity levels<br/>• Sleep disruption indicators<br/>• Overall workload intensity relative to team baseline</div>
                                <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-900"></div>
                              </div>
                            </div>
                          </div>
                          <div className="text-lg font-bold text-green-700">
                            {memberData.cbi_breakdown.personal?.toFixed(0)}/100
                          </div>
                        </div>
                        <div className="bg-blue-50 rounded-lg p-3">
                          <div className="flex items-center space-x-1 mb-1">
                            <div className="text-xs font-medium text-blue-600 uppercase">Work-Related</div>
                            <div className="relative group">
                              <Info className="w-3 h-3 text-blue-500 cursor-help" />
                              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg w-72 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                                <div className="font-semibold mb-1">Work-Related Burnout - What We Measure</div>
                                <div>• Incident response time patterns<br/>• Severity-weighted incident load<br/>• GitHub commit activity and timing<br/>• Slack communication patterns<br/>• Work-life boundary violations (late night/weekend work)</div>
                                <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-900"></div>
                              </div>
                            </div>
                          </div>
                          <div className="text-lg font-bold text-blue-700">
                            {memberData.cbi_breakdown.work_related?.toFixed(0)}/100
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 italic">
                    CBI burnout analysis not available. Run a new analysis to see detailed burnout factors.
                  </p>
                )}
              </CardContent>
            </Card>

            {/* CBI Scores */}
            {memberData?.cbi_personal_score !== undefined && memberData?.cbi_work_score !== undefined && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">CBI Scores</CardTitle>
                  <CardDescription>Copenhagen Burnout Inventory dimensional assessment</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="text-center p-3 rounded-lg bg-blue-50 border border-blue-100">
                      <div className="text-lg font-bold text-blue-600">
                        {memberData.cbi_personal_score.toFixed(1)}/100
                      </div>
                      <p className="text-sm font-medium text-blue-800">Personal Burnout</p>
                      <p className="text-xs text-blue-600 mt-1">Physical and psychological fatigue</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-orange-50 border border-orange-100">
                      <div className="text-lg font-bold text-orange-600">
                        {memberData.cbi_work_score.toFixed(1)}/100
                      </div>
                      <p className="text-sm font-medium text-orange-800">Work-Related Burnout</p>
                      <p className="text-xs text-orange-600 mt-1">Work-specific exhaustion and cynicism</p>
                    </div>
                  </div>
                  <div className="mt-4 text-center">
                    <div className="text-2xl font-bold text-gray-900">
                      {memberData.cbi_score.toFixed(1)}/100
                    </div>
                    <p className="text-sm text-gray-600">Composite CBI Score</p>
                  </div>
                </CardContent>
              </Card>
            )}

            <Tabs defaultValue="factors" className="w-full">
              {(() => {
                // Check if GitHub data exists
                const hasGitHubData = selectedMember.github_activity?.commits_count > 0 || 
                                     selectedMember.github_activity?.pull_requests_count > 0;
                
                // Check if Slack data exists  
                const hasSlackData = selectedMember.slack_activity?.messages_sent > 0 ||
                                   selectedMember.slack_activity?.channels_active > 0;
                
                // Calculate grid columns based on available data
                const tabCount = 2 + (hasGitHubData ? 1 : 0) + (hasSlackData ? 1 : 0);
                const gridCols = tabCount === 2 ? 'grid-cols-2' :
                                tabCount === 3 ? 'grid-cols-3' : 'grid-cols-4';
                
                return (
                  <TabsList className={`grid w-full ${gridCols}`}>
                    <TabsTrigger value="factors">Factors</TabsTrigger>
                    <TabsTrigger value="incidents">Incidents</TabsTrigger>
                    {hasGitHubData && <TabsTrigger value="github">GitHub</TabsTrigger>}
                    {hasSlackData && <TabsTrigger value="communication">Communication</TabsTrigger>}
                  </TabsList>
                );
              })()}

              <TabsContent value="factors" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Burnout Risk Factors</CardTitle>
                    <CardDescription>Key factors contributing to burnout risk</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart data={[
                          { 
                            factor: 'Workload', 
                            value: selectedMember.factors?.workload || 0
                          },
                          { 
                            factor: 'After Hours', 
                            value: selectedMember.factors?.afterHours || 0
                          },
                          { 
                            factor: 'Weekend Work', 
                            value: selectedMember.factors?.weekendWork || 0
                          },
                          { 
                            factor: 'Incident Load', 
                            value: selectedMember.factors?.incidentLoad || 0
                          },
                          { 
                            factor: 'Response Time', 
                            value: selectedMember.factors?.responseTime || 0
                          }
                        ]}>
                          <PolarGrid />
                          <PolarAngleAxis dataKey="factor" tick={{ fontSize: 11 }} />
                          <PolarRadiusAxis domain={[0, 10]} tick={{ fontSize: 9 }} />
                          <Radar
                            name="Risk Level"
                            dataKey="value"
                            stroke="#8b5cf6"
                            fill="#8b5cf6"
                            fillOpacity={0.3}
                            strokeWidth={2}
                          />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="incidents" className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Incident Response Metrics</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-sm">Total Incidents</span>
                        <span className="font-medium">{selectedMember.incidentsHandled}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm">Avg Response Time</span>
                        <span className="font-medium">{selectedMember.avgResponseTime}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm">After Hours Work</span>
                        <span className="font-medium">{(memberData?.metrics?.after_hours_percentage || 0).toFixed(1)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm">Weekend Work</span>
                        <span className="font-medium">{(memberData?.metrics?.weekend_percentage || 0).toFixed(1)}%</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="github" className="space-y-4">
                {selectedMember.github_activity ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                    
                    {selectedMember.github_activity?.daily_commits && (
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-sm">Commit Pattern (Last 30 Days)</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="h-32">
                            <ResponsiveContainer width="100%" height="100%">
                              <AreaChart data={selectedMember.github_activity.daily_commits}>
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
                            Average: {selectedMember.github_activity.commits_per_week?.toFixed(1) || '0'} commits/week
                            {selectedMember.github_activity.after_hours_commits > 0 && (
                              <span className="ml-2">
                                • {((selectedMember.github_activity.after_hours_commits / selectedMember.github_activity.commits_count) * 100).toFixed(0)}% after hours
                              </span>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                ) : (
                  <Card>
                    <CardContent className="p-6 text-center">
                      <p className="text-gray-500">No GitHub activity data available</p>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="communication" className="space-y-4">
                {selectedMember.slack_activity ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Card>
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
                      <p className="text-gray-500">No Slack activity data available</p>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>
            </Tabs>
          </div>
        );
        })()}
        </>
      );
        })()}
      </DialogContent>
    </Dialog>
  )
}