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
            
            // Use real Maslach dimensions from backend if available, otherwise show single burnout score  
            const maslachDimensions = (memberData as any)?.maslach_dimensions || null;
          
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
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardContent className="p-4 text-center">
                  <p className="text-sm text-gray-600 mb-2">Overall Risk Level</p>
                  <Badge className={`px-3 py-1 ${healthColor}`}>
                    {healthStatus}
                  </Badge>
                  <div className="mt-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {(overallBurnoutScore * 10).toFixed(0)}%
                    </div>
                    <p className="text-xs text-gray-500">Burnout Risk Score</p>
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
              
              <Card>
                <CardContent className="p-4 text-center">
                  <p className="text-sm text-gray-600 mb-2">Response Time</p>
                  <div className="text-2xl font-bold text-purple-600">
                    {Math.round(memberData?.metrics?.avg_response_time_minutes || 0)}m
                  </div>
                  <p className="text-xs text-gray-500">Average</p>
                </CardContent>
              </Card>
            </div>
            
            {/* Burnout Summary */}
            <Card>
              <CardContent className="p-4">
                <h4 className="font-semibold text-gray-900 mb-2">Burnout Analysis</h4>
                <p className="text-sm text-gray-700 mb-3">{burnoutSummary.summary}</p>
                {(burnoutSummary.concerns.length > 0 || burnoutSummary.metrics.length > 0) && (
                  <div className="flex flex-wrap gap-2">
                    {burnoutSummary.concerns.map((concern, i) => (
                      <Badge key={i} variant="outline" className="text-xs bg-orange-50 text-orange-700">
                        🔥 {concern}
                      </Badge>
                    ))}
                    {burnoutSummary.metrics.map((metric, i) => (
                      <Badge key={i} variant="outline" className="text-xs bg-blue-50 text-blue-700">
                        📈 {metric}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Maslach Dimensions */}
            {maslachDimensions && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Burnout Dimensions (Maslach Inventory)</CardTitle>
                  <CardDescription>Clinical burnout assessment across three key dimensions</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="text-center p-3 rounded-lg bg-red-50 border border-red-100">
                      <div className="text-lg font-bold text-red-600">
                        {(maslachDimensions.exhaustion * 10).toFixed(0)}%
                      </div>
                      <p className="text-sm font-medium text-red-800">Emotional Exhaustion</p>
                      <p className="text-xs text-red-600 mt-1">Feeling emotionally drained</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-orange-50 border border-orange-100">
                      <div className="text-lg font-bold text-orange-600">
                        {(maslachDimensions.cynicism * 10).toFixed(0)}%
                      </div>
                      <p className="text-sm font-medium text-orange-800">Cynicism</p>
                      <p className="text-xs text-orange-600 mt-1">Detached attitude toward work</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-blue-50 border border-blue-100">
                      <div className="text-lg font-bold text-blue-600">
                        {(10 - maslachDimensions.personal_accomplishment) * 10}%
                      </div>
                      <p className="text-sm font-medium text-blue-800">Reduced Accomplishment</p>
                      <p className="text-xs text-blue-600 mt-1">Lower sense of effectiveness</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            <Tabs defaultValue="factors" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="factors">Factors</TabsTrigger>
                <TabsTrigger value="incidents">Incidents</TabsTrigger>
                <TabsTrigger value="github">GitHub</TabsTrigger>
                <TabsTrigger value="communication">Communication</TabsTrigger>
              </TabsList>

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