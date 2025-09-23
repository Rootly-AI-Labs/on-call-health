"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { ArrowLeft, TrendingUp, Clock, AlertTriangle, Activity, Timer } from "lucide-react"
import { useRouter } from "next/navigation"
import Image from "next/image"

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

          <div className="flex items-center justify-between mb-4">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Burnout Methodology
              </h1>
              <p className="text-gray-600">
                How we calculate burnout risk using the Copenhagen Burnout Inventory
              </p>
            </div>
            <div className="flex flex-col items-center ml-8">
              <span className="text-xs text-gray-400">powered by</span>
              <Image
                src="/images/rootly-ai-logo.png"
                alt="Rootly AI"
                width={120}
                height={48}
                className="h-6 w-auto"
              />
            </div>
          </div>
        </div>

        {/* Overview */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>The Science Behind Our Scoring</CardTitle>
            <CardDescription>
              Based on the Copenhagen Burnout Inventory (CBI), a scientifically validated framework for measuring burnout
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-gray-700 mb-4">
              Our burnout detection system analyzes incident response data from PagerDuty and Rootly to calculate
              burnout risk across three key dimensions. The Copenhagen Burnout Inventory is a well-established
              psychological assessment tool that measures burnout in three core areas: emotional exhaustion,
              depersonalization/cynicism, and reduced personal accomplishment.
            </p>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                <strong>Multi-Source Analysis:</strong> We analyze incident data from PagerDuty/Rootly as the primary source,
                with additional insights from GitHub activity patterns and Slack communication when available.
                The system adapts based on available integrations to provide the most comprehensive assessment possible.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Burnout Factors */}
        <div className="space-y-6 mb-8">
          <h2 className="text-2xl font-semibold text-gray-900">The Five Key Burnout Factors</h2>

          <p className="text-gray-700 mb-6">
            We analyze five specific factors that contribute to burnout in incident response teams. Each factor is measured
            on a scale of 0-10, with higher scores indicating greater burnout risk. These factors are then combined using
            the three-dimensional Copenhagen Burnout Inventory framework to produce an overall burnout score.
          </p>

          {/* Workload */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Activity className="w-5 h-5 mr-2 text-red-500" />
                Workload Factor
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-700 mb-3">
                Measures the frequency and volume of incidents handled by each team member over time.
                This is one of the strongest predictors of burnout, as high incident volumes can lead to
                chronic stress and exhaustion.
              </p>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-600">
                  <strong>Scoring:</strong> 0-2 incidents/week = Low (0-3 points) • 2-5 incidents/week = Moderate (3-7 points) •
                  5-8 incidents/week = High (7-10 points) • 8+ incidents/week = Critical (10 points)
                </p>
              </div>
            </CardContent>
          </Card>

          {/* After Hours */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Clock className="w-5 h-5 mr-2 text-orange-500" />
                After Hours Factor
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-700 mb-3">
                Tracks work performed outside normal business hours, including incident responses, code commits,
                and team communications. Excessive after-hours work disrupts work-life balance and contributes
                to emotional exhaustion.
              </p>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-600">
                  <strong>Data Sources:</strong> Incident timestamps from PagerDuty/Rootly, GitHub commit times,
                  and Slack message activity (when connected)
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Weekend Work */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <AlertTriangle className="w-5 h-5 mr-2 text-yellow-500" />
                Weekend Work Factor
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-700 mb-3">
                Measures weekend activity that disrupts personal time and recovery periods. Regular weekend work
                prevents proper rest and contributes to chronic stress accumulation, leading to depersonalization
                and cynicism toward work.
              </p>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-600">
                  <strong>Boundary Health:</strong> Healthy teams typically have &lt;10% weekend activity.
                  Scores above 25% indicate significant work-life boundary violations.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Response Time */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Timer className="w-5 h-5 mr-2 text-blue-500" />
                Response Time Pressure
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-700 mb-3">
                Measures the time pressure to respond quickly to incidents. While fast response times are important
                for business continuity, excessive pressure to respond immediately can create chronic stress and
                contribute to feelings of being overwhelmed and losing control.
              </p>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-600">
                  <strong>Pressure Points:</strong> Average response time under 5 minutes indicates high pressure.
                  Sustained pressure can lead to anxiety and reduced job satisfaction.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Incident Load */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <TrendingUp className="w-5 h-5 mr-2 text-purple-500" />
                Severity-Weighted Incident Load
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-700 mb-3">
                Goes beyond simple incident count to measure the actual psychological burden of different incident
                severities. Critical incidents (SEV0/SEV1) cause significantly more stress than minor issues,
                so this factor weights incidents by their business impact and stress level.
              </p>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-600">
                  <strong>Severity Weighting:</strong> Critical incidents = 4x weight • High = 3x weight •
                  Medium = 2x weight • Low = 1x weight. This reflects the exponentially higher stress
                  of handling business-critical outages.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Three Dimensions */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Copenhagen Burnout Inventory Dimensions</CardTitle>
            <CardDescription>
              How the five factors map to the three scientifically validated burnout dimensions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <h4 className="font-semibold text-gray-900 mb-2 flex items-center">
                  <div className="w-4 h-4 bg-red-500 rounded mr-2"></div>
                  Emotional Exhaustion (40% weight)
                </h4>
                <p className="text-sm text-gray-700 mb-3">
                  Physical and psychological fatigue from work demands. This dimension measures the core stress
                  experience and depletion of emotional resources that characterizes burnout.
                </p>
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-xs text-red-800">
                    <strong>Calculation:</strong> Workload Factor (50%) + After Hours Factor (30%) + Incident Load (20%)
                  </p>
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-2 flex items-center">
                  <div className="w-4 h-4 bg-yellow-500 rounded mr-2"></div>
                  Depersonalization/Cynicism (30% weight)
                </h4>
                <p className="text-sm text-gray-700 mb-3">
                  Detached, callous attitudes toward work and colleagues. This reflects the psychological
                  distancing and defensive coping mechanisms that develop under chronic stress.
                </p>
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="text-xs text-yellow-800">
                    <strong>Calculation:</strong> Response Time Pressure (50%) + Weekend Work Factor (50%)
                  </p>
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-gray-900 mb-2 flex items-center">
                  <div className="w-4 h-4 bg-blue-500 rounded mr-2"></div>
                  Reduced Personal Accomplishment (30% weight)
                </h4>
                <p className="text-sm text-gray-700 mb-3">
                  Feelings of ineffectiveness and lack of achievement at work. This dimension captures
                  the erosion of professional self-efficacy and satisfaction with one's contributions.
                </p>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="text-xs text-blue-800">
                    <strong>Calculation:</strong> Inverted measure of effectiveness under pressure, derived from
                    response time pressure and incident load factors.
                  </p>
                </div>
              </div>

              <div className="mt-6 bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p className="text-sm text-gray-700">
                  <strong>Final Score:</strong> The three dimensions are weighted and combined to produce a final
                  burnout score from 0-100, with higher scores indicating greater burnout risk. The weighting
                  reflects the relative importance of each dimension based on burnout research.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Risk Levels */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Risk Level Classification</CardTitle>
            <CardDescription>
              How we categorize burnout risk and what each level means for team intervention
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <div className="flex items-center space-x-4 mb-2">
                  <Badge className="bg-green-500 w-24">Low Risk</Badge>
                  <Progress value={20} className="h-3 flex-1" />
                  <span className="text-sm font-medium">0-24 points</span>
                </div>
                <p className="text-sm text-gray-600 ml-28">
                  Sustainable workload and healthy work-life balance. Team members are functioning well
                  with minimal stress indicators. Continue current practices and monitor for changes.
                </p>
              </div>

              <div>
                <div className="flex items-center space-x-4 mb-2">
                  <Badge className="bg-yellow-500 w-24">Moderate</Badge>
                  <Progress value={37} className="h-3 flex-1" />
                  <span className="text-sm font-medium">25-49 points</span>
                </div>
                <p className="text-sm text-gray-600 ml-28">
                  Some stress indicators present but manageable. Consider workload distribution,
                  schedule adjustments, or additional support. Monitor closely for escalation.
                </p>
              </div>

              <div>
                <div className="flex items-center space-x-4 mb-2">
                  <Badge className="bg-orange-500 w-24">High Risk</Badge>
                  <Progress value={62} className="h-3 flex-1" />
                  <span className="text-sm font-medium">50-74 points</span>
                </div>
                <p className="text-sm text-gray-600 ml-28">
                  Significant burnout indicators requiring intervention. Recommend workload reduction,
                  schedule changes, additional team support, or temporary assignment adjustments.
                </p>
              </div>

              <div>
                <div className="flex items-center space-x-4 mb-2">
                  <Badge className="bg-red-500 w-24">Critical</Badge>
                  <Progress value={87} className="h-3 flex-1" />
                  <span className="text-sm font-medium">75-100 points</span>
                </div>
                <p className="text-sm text-gray-600 ml-28">
                  Severe burnout risk requiring immediate action. Consider temporary on-call rotation
                  removal, significant workload reduction, or professional support resources.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}