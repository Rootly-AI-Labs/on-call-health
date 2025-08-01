"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Progress } from "@/components/ui/progress"
import { ArrowLeft, TrendingUp, Clock, Calendar, Activity, AlertTriangle } from "lucide-react"
import { useRouter } from "next/navigation"

export default function MethodologyPage() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Button 
            variant="ghost" 
            onClick={() => router.push('/dashboard')}
            className="mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
          
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Burnout Score Methodology
          </h1>
          <p className="text-gray-600">
            Understanding how we calculate team burnout risk using the Maslach Burnout Inventory
          </p>
        </div>

        {/* Overview Card */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>The Science Behind Our Scoring</CardTitle>
            <CardDescription>
              Based on the Maslach Burnout Inventory (MBI), the gold standard for measuring burnout
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-gray-700 mb-4">
              Our burnout detection system analyzes multiple data sources to calculate three key dimensions 
              of burnout, providing an evidence-based assessment of team mental health and well-being.
            </p>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <p className="text-sm text-blue-800">
                <strong>Multi-Source Analysis:</strong> We analyze incident data from PagerDuty/Rootly (primary source), 
                with optional GitHub activity data for code patterns and Slack communication data for sentiment analysis. 
                The analysis adapts based on available integrations to provide the most comprehensive assessment possible.
              </p>
            </div>
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <p className="text-sm text-purple-800">
                <strong>GitHub-Only Analysis:</strong> When only GitHub data is available, our system can provide 
                a complete burnout assessment (100% scoring) using advanced flow state detection to distinguish 
                healthy high-productivity from burnout patterns. Confidence intervals and baseline comparisons 
                ensure scientifically rigorous results even with a single data source.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Three Dimensions */}
        <div className="space-y-6 mb-8">
          <h2 className="text-2xl font-semibold text-gray-900">The Three Dimensions of Burnout</h2>
          
          {/* Emotional Exhaustion */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center">
                  <TrendingUp className="w-5 h-5 mr-2 text-red-500" />
                  Emotional Exhaustion (40% weight)
                </CardTitle>
                <Badge variant="destructive">High Impact</Badge>
              </div>
              <CardDescription>
                The depletion of emotional resources and feeling overwhelmed
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-gray-700">
                  We measure emotional exhaustion by analyzing:
                </p>
                <div className="grid gap-3">
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-red-500 rounded-full mt-1.5"></div>
                    <div>
                      <strong className="text-sm">Workload Pressure</strong>
                      <p className="text-sm text-gray-600">Incident frequency and volume over time, weighted by severity:</p>
                      <ul className="text-xs text-gray-500 mt-1 ml-4">
                        <li>• SEV0 incidents: 5x weight (catastrophic - complete outage)</li>
                        <li>• SEV1 incidents: 4x weight (critical business impact)</li>
                        <li>• SEV2 incidents: 2x weight (major functionality affected)</li>
                        <li>• SEV3 incidents: 1.5x weight (moderate impact)</li>
                        <li>• SEV4 incidents: 1x weight (minor issues)</li>
                      </ul>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-red-500 rounded-full mt-1.5"></div>
                    <div>
                      <strong className="text-sm">After-Hours Activity</strong>
                      <p className="text-sm text-gray-600">Work performed outside normal business hours (incidents, commits, messages)</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-red-500 rounded-full mt-1.5"></div>
                    <div>
                      <strong className="text-sm">GitHub Activity Patterns</strong>
                      <p className="text-sm text-gray-600">High commit frequency (&gt;25/week), late-night commits (&gt;30% after hours), and weekend coding activity (&gt;25%)</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-red-500 rounded-full mt-1.5"></div>
                    <div>
                      <strong className="text-sm">Communication Stress</strong>
                      <p className="text-sm text-gray-600">Negative sentiment patterns in Slack messages (when available)</p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Depersonalization */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center">
                  <AlertTriangle className="w-5 h-5 mr-2 text-yellow-500" />
                  Depersonalization (30% weight)
                </CardTitle>
                <Badge variant="outline" className="border-yellow-500 text-yellow-700">Medium Impact</Badge>
              </div>
              <CardDescription>
                Detachment from work and decreased empathy
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-gray-700">
                  We identify signs of depersonalization through:
                </p>
                <div className="grid gap-3">
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full mt-1.5"></div>
                    <div>
                      <strong className="text-sm">Response Time Pressure</strong>
                      <p className="text-sm text-gray-600">Time pressure to respond quickly to incidents</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full mt-1.5"></div>
                    <div>
                      <strong className="text-sm">Weekend Work Disruption</strong>
                      <p className="text-sm text-gray-600">Work performed during weekends (incidents, commits, messages)</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full mt-1.5"></div>
                    <div>
                      <strong className="text-sm">Code Collaboration Decline</strong>
                      <p className="text-sm text-gray-600">Large, infrequent PRs (&gt;1000 lines), declining code review participation (&lt;50%), and shorter commit messages (&lt;20 chars)</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full mt-1.5"></div>
                    <div>
                      <strong className="text-sm">Communication Cynicism</strong>
                      <p className="text-sm text-gray-600">Declining communication quality and engagement in Slack (when available)</p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Personal Accomplishment */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center">
                  <Activity className="w-5 h-5 mr-2 text-green-500" />
                  Personal Accomplishment (30% weight)
                </CardTitle>
                <Badge variant="outline" className="border-green-500 text-green-700">Protective Factor</Badge>
              </div>
              <CardDescription>
                Sense of achievement and effectiveness (inverted for scoring)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-gray-700">
                  We measure personal accomplishment through:
                </p>
                <div className="grid gap-3">
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full mt-1.5"></div>
                    <div>
                      <strong className="text-sm">Resolution Success Rate</strong>
                      <p className="text-sm text-gray-600">Inverse of response time pressure - better response times indicate higher accomplishment</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full mt-1.5"></div>
                    <div>
                      <strong className="text-sm">Incident Load Management</strong>
                      <p className="text-sm text-gray-600">Ability to handle incident volume effectively without degradation. The incident volume score combines:</p>
                      <ul className="text-xs text-gray-500 mt-1 ml-4">
                        <li>• Workload component (40%): Based on incidents per week per responder</li>
                        <li>• Severity component (60%): Weighted by incident severity (SEV0-4)</li>
                      </ul>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full mt-1.5"></div>
                    <div>
                      <strong className="text-sm">Code Quality & Collaboration</strong>
                      <p className="text-sm text-gray-600">PR merge success rate (&gt;80%), constructive code review quality, and knowledge sharing through documentation</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full mt-1.5"></div>
                    <div>
                      <strong className="text-sm">Communication Effectiveness</strong>
                      <p className="text-sm text-gray-600">Positive sentiment and constructive communication patterns in Slack (when available)</p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* GitHub-Only Analysis Section */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center">
              <Badge className="mr-3 bg-purple-500">GitHub-Only</Badge>
              Comprehensive Single-Source Analysis
            </CardTitle>
            <CardDescription>
              How we achieve 100% burnout scoring using only GitHub data with scientific rigor
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <h4 className="font-semibold mb-3">Flow State vs. Frantic Activity Detection</h4>
                <p className="text-sm text-gray-700 mb-3">
                  Our advanced algorithm distinguishes between healthy high-productivity (flow state) and 
                  burnout-driven frantic activity by analyzing multiple patterns:
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <h5 className="font-medium text-green-800 mb-2">Healthy Flow State</h5>
                    <ul className="text-xs text-green-700 space-y-1">
                      <li>• Consistent, sustainable work pace</li>
                      <li>• High-quality output (fewer revisions)</li>
                      <li>• Balanced activities (coding + reviews + docs)</li>
                      <li>• Reasonable work hour boundaries</li>
                    </ul>
                  </div>
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <h5 className="font-medium text-red-800 mb-2">Frantic Burnout Activity</h5>
                    <ul className="text-xs text-red-700 space-y-1">
                      <li>• Erratic commit patterns with extreme peaks</li>
                      <li>• Poor quality output (many revisions, rushed commits)</li>
                      <li>• Imbalanced work (all coding, no collaboration)</li>
                      <li>• Constant boundary violations (24/7 activity)</li>
                    </ul>
                  </div>
                </div>
              </div>
              
              <Separator />
              
              <div>
                <h4 className="font-semibold mb-3">Baseline Comparison System</h4>
                <p className="text-sm text-gray-700 mb-3">
                  Individual metrics are compared against three baseline types for accurate risk assessment:
                </p>
                <div className="space-y-2">
                  <div className="flex items-center space-x-3">
                    <Badge variant="outline" className="w-20 text-xs">Personal</Badge>
                    <span className="text-sm text-gray-600">Individual's historical patterns and trends</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <Badge variant="outline" className="w-20 text-xs">Team</Badge>
                    <span className="text-sm text-gray-600">Team median values (70% weight)</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <Badge variant="outline" className="w-20 text-xs">Industry</Badge>
                    <span className="text-sm text-gray-600">Software industry standards (30% weight)</span>
                  </div>
                </div>
              </div>
              
              <Separator />
              
              <div>
                <h4 className="font-semibold mb-3">Confidence Intervals & Validation</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-2">
                      <span className="text-green-600 font-bold">High</span>
                    </div>
                    <p className="text-xs text-gray-600">
                      Comprehensive GitHub data, active team, 30+ day period
                    </p>
                  </div>
                  <div className="text-center">
                    <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-2">
                      <span className="text-yellow-600 font-bold">Med</span>
                    </div>
                    <p className="text-xs text-gray-600">
                      Good data coverage, some limitations in scope or time
                    </p>
                  </div>
                  <div className="text-center">
                    <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-2">
                      <span className="text-red-600 font-bold">Low</span>
                    </div>
                    <p className="text-xs text-gray-600">
                      Limited data - results should be validated with team
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Scoring System */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Risk Level Classification</CardTitle>
            <CardDescription>
              How we categorize burnout risk based on the combined score
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                <div className="w-24">
                  <Badge className="bg-green-500">Low Risk</Badge>
                </div>
                <div className="flex-1">
                  <Progress value={30} className="h-3" />
                </div>
                <span className="text-sm font-medium">0-40%</span>
              </div>
              <p className="text-sm text-gray-600 ml-24">
                Healthy work-life balance, sustainable incident load
              </p>
              
              <div className="flex items-center space-x-4">
                <div className="w-24">
                  <Badge className="bg-yellow-500">Medium Risk</Badge>
                </div>
                <div className="flex-1">
                  <Progress value={60} className="h-3" />
                </div>
                <span className="text-sm font-medium">40-70%</span>
              </div>
              <p className="text-sm text-gray-600 ml-24">
                Showing signs of stress, intervention recommended
              </p>
              
              <div className="flex items-center space-x-4">
                <div className="w-24">
                  <Badge className="bg-red-500">High Risk</Badge>
                </div>
                <div className="flex-1">
                  <Progress value={85} className="h-3" />
                </div>
                <span className="text-sm font-medium">70-100%</span>
              </div>
              <p className="text-sm text-gray-600 ml-24">
                Critical burnout indicators, immediate action needed
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Data Sources */}
        <Card>
          <CardHeader>
            <CardTitle>Data Privacy & Accuracy</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-medium mb-2">What We Analyze</h4>
              <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                <li>Incident frequency, timing, and resolution patterns (PagerDuty/Rootly)</li>
                <li>GitHub commit patterns, PR activity, and code review participation</li>
                <li>Slack message sentiment, timing, and communication patterns (when connected)</li>
                <li>Work hour distribution and boundary violations across all platforms</li>
                <li>Flow state analysis: sustainable productivity vs. frantic burnout patterns</li>
                <li>Code quality indicators: PR merge rates, review depth, commit message quality</li>
                <li>Collaboration patterns: knowledge sharing, mentoring, cross-team contributions</li>
              </ul>
            </div>
            
            <Separator />
            
            <div>
              <h4 className="font-medium mb-2">What We Don't Track</h4>
              <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                <li>Specific content of Slack messages (only sentiment analysis)</li>
                <li>Private repository code or proprietary information</li>
                <li>Individual performance reviews or HR data</li>
                <li>Personal calendar or non-work related activities</li>
                <li>Detailed code content (only commit patterns and timing)</li>
              </ul>
            </div>
            
            <Separator />
            
            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              <p className="text-sm text-gray-700">
                <strong>GitHub-Only Analysis Validation:</strong> When using only GitHub data, our system 
                achieves high accuracy through flow state detection and baseline comparisons. However, 
                the most comprehensive assessment comes from combining multiple data sources (incidents + GitHub + Slack).
              </p>
              <p className="text-sm text-gray-700">
                <strong>Important:</strong> This tool provides data-driven insights but should not replace 
                professional mental health assessment. Always consult with HR and mental health professionals 
                when addressing burnout concerns.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}