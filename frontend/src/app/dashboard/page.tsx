"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Line,
  LineChart,
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
  X,
  AlertCircle,
  Trash2,
} from "lucide-react"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { useToast } from "@/hooks/use-toast"

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
}

interface TeamMember {
  id: string
  name: string
  email: string
  role?: string
  avatar?: string
  burnoutScore: number
  riskLevel: 'high' | 'medium' | 'low'
  trend: 'up' | 'down' | 'stable'
  incidentsHandled: number
  avgResponseTime: string
  factors: {
    workload: number
    afterHours: number
    weekendWork: number
    incidentLoad: number
    responseTime: number
  }
}

interface AnalysisResult {
  id: string
  integration_id: number
  created_at: string
  status: string
  time_range: number
  error_message?: string
  teamName?: string // For display purposes
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
  teamMembers?: TeamMember[] // For display purposes
  burnoutFactors?: Array<{ factor: string; value: number }> // For display purposes
  analysis_data?: {
    team_health: {
      overall_score: number
      risk_distribution: {
        low: number
        medium: number
        high: number
      }
      health_status: string
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
        }
      }>
    }
    insights: Array<{
      type: string
      message: string
      severity: string
    }>
    recommendations: Array<{
      type: string
      message: string
      priority: string
    }>
    partial_data?: {
      users: Array<any>
      incidents: Array<any>
      metadata: any
    }
    error?: string
    data_collection_successful?: boolean
    failure_stage?: string
  }
}

type AnalysisStage = "loading" | "fetching" | "calculating" | "preparing" | "complete"

// Mock data generator
const generateMockAnalysis = (integration: Integration): AnalysisResult => {
  // Add some randomness to make each analysis unique
  const baseScore = 72 + Math.floor(Math.random() * 10) - 5
  const mockMembers: TeamMember[] = [
    {
      id: "1",
      name: "Alex Chen",
      email: "alex.chen@rootly.com",
      role: "Senior Engineer",
      avatar: "/placeholder.svg?height=40&width=40",
      burnoutScore: 85,
      riskLevel: "high",
      trend: "up",
      incidentsHandled: 23,
      avgResponseTime: "12m",
      factors: {
        workload: 90,
        afterHours: 85,
        weekendWork: 70,
        incidentLoad: 95,
        responseTime: 60,
      },
    },
    {
      id: "2",
      name: "Sarah Johnson",
      email: "sarah.johnson@rootly.com",
      role: "Staff Engineer",
      avatar: "/placeholder.svg?height=40&width=40",
      burnoutScore: 78,
      riskLevel: "high",
      trend: "up",
      incidentsHandled: 19,
      avgResponseTime: "8m",
      factors: {
        workload: 80,
        afterHours: 90,
        weekendWork: 85,
        incidentLoad: 75,
        responseTime: 45,
      },
    },
    {
      id: "3",
      name: "Mike Rodriguez",
      email: "mike.rodriguez@rootly.com",
      role: "Engineering Manager",
      avatar: "/placeholder.svg?height=40&width=40",
      burnoutScore: 68,
      riskLevel: "medium",
      trend: "stable",
      incidentsHandled: 15,
      avgResponseTime: "15m",
      factors: {
        workload: 70,
        afterHours: 65,
        weekendWork: 60,
        incidentLoad: 80,
        responseTime: 70,
      },
    },
    {
      id: "4",
      name: "Emily Davis",
      email: "emily.davis@rootly.com",
      role: "Senior Engineer",
      avatar: "/placeholder.svg?height=40&width=40",
      burnoutScore: 45,
      riskLevel: "low",
      trend: "down",
      incidentsHandled: 12,
      avgResponseTime: "10m",
      factors: {
        workload: 50,
        afterHours: 40,
        weekendWork: 30,
        incidentLoad: 60,
        responseTime: 45,
      },
    },
  ]

  return {
    id: `analysis-${Date.now()}`,
    integration_id: integration.id,
    created_at: new Date().toISOString(),
    status: "completed",
    time_range: 30,
    teamName: integration.name,
    timeRange: "30", // This will be set from the actual selected range
    overallScore: baseScore,
    trend: baseScore > 72 ? "up" : baseScore < 72 ? "down" : "stable",
    atRiskCount: baseScore > 75 ? 3 : baseScore > 65 ? 2 : 1,
    totalMembers: mockMembers.length,
    lastAnalysis: new Date().toISOString(),
    trends: {
      daily: [
        { date: "Jan 1", score: 65 },
        { date: "Jan 8", score: 68 },
        { date: "Jan 15", score: 72 },
        { date: "Jan 22", score: 75 },
        { date: "Jan 29", score: 72 },
      ],
      weekly: [
        { week: "Week 1", score: 65 },
        { week: "Week 2", score: 68 },
        { week: "Week 3", score: 72 },
        { week: "Week 4", score: 75 },
      ],
      monthly: [
        { month: "Dec", score: 68 },
        { month: "Jan", score: 72 },
        { month: "Feb", score: 75 },
      ],
    },
    teamMembers: mockMembers,
    burnoutFactors: [
      { factor: "Workload", value: 75 },
      { factor: "After Hours", value: 70 },
      { factor: "Weekend Work", value: 60 },
      { factor: "Incident Load", value: 80 },
      { factor: "Response Time", value: 55 },
    ],
  }
}

export default function Dashboard() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [selectedIntegration, setSelectedIntegration] = useState<string>("")
  const [loadingIntegrations, setLoadingIntegrations] = useState(true)
  const [analysisRunning, setAnalysisRunning] = useState(false)
  const [analysisStage, setAnalysisStage] = useState<AnalysisStage>("loading")
  const [analysisProgress, setAnalysisProgress] = useState(0)
  const [currentAnalysis, setCurrentAnalysis] = useState<AnalysisResult | null>(null)
  const [previousAnalyses, setPreviousAnalyses] = useState<AnalysisResult[]>([])
  const [selectedMember, setSelectedMember] = useState<TeamMember | null>(null)
  const [timeRange, setTimeRange] = useState("30")
  const [chartType, setChartType] = useState("daily")
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [analysisToDelete, setAnalysisToDelete] = useState<AnalysisResult | null>(null)
  
  const router = useRouter()
  const { toast } = useToast()

  useEffect(() => {
    loadIntegrations()
    loadPreviousAnalyses()
  }, [])

  const loadPreviousAnalyses = async () => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      console.log('Loading previous analyses...')
      const response = await fetch(`${API_BASE}/analyses`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        console.log('Loaded analyses:', data.analyses?.length || 0, 'analyses')
        setPreviousAnalyses(data.analyses || [])
      } else {
        console.error('Failed to load analyses, status:', response.status)
      }
    } catch (error) {
      console.error('Failed to load previous analyses:', error)
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
        }
        
        toast({
          title: "Analysis deleted",
          description: "The analysis has been successfully removed.",
        })
        
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
      toast({
        title: "Delete failed",
        description: error instanceof Error ? error.message : "Failed to delete analysis",
        variant: "destructive",
      })
      setDeleteDialogOpen(false)
      setAnalysisToDelete(null)
    }
  }

  const loadIntegrations = async () => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        router.push('/auth/login')
        return
      }

      const response = await fetch(`${API_BASE}/rootly/integrations`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setIntegrations(data.integrations)
        
        // Set default integration
        const defaultIntegration = data.integrations.find((i: Integration) => i.is_default)
        if (defaultIntegration) {
          setSelectedIntegration(defaultIntegration.id.toString())
        } else if (data.integrations.length > 0) {
          setSelectedIntegration(data.integrations[0].id.toString())
        }
      } else if (response.status === 401) {
        router.push('/auth/login')
      }
    } catch (error) {
      console.error('Failed to load integrations:', error)
      toast({
        title: "Failed to load integrations",
        description: "Please try refreshing the page",
        variant: "destructive",
      })
    } finally {
      setLoadingIntegrations(false)
    }
  }

  const analysisStages = [
    { key: "loading", label: "Initializing Analysis", detail: "Setting up analysis parameters", duration: 800 },
    { key: "connecting", label: "Connecting to Rootly", detail: "Validating API credentials", duration: 1000 },
    { key: "fetching_users", label: "Fetching Team Members", detail: "Loading user profiles", duration: 1200 },
    { key: "fetching", label: "Collecting Incident Data", detail: "Gathering incident history", duration: 1800 },
    { key: "calculating", label: "Processing Patterns", detail: "Analyzing response times and workload", duration: 2000 },
    { key: "analyzing", label: "Calculating Metrics", detail: "Computing burnout scores", duration: 1500 },
    { key: "preparing", label: "Generating Insights", detail: "Creating recommendations", duration: 1000 },
    { key: "complete", label: "Analysis Complete", detail: "Preparing results", duration: 300 },
  ]

  const [showTimeRangeDialog, setShowTimeRangeDialog] = useState(false)
  const [selectedTimeRange, setSelectedTimeRange] = useState("30")

  const startAnalysis = () => {
    if (!selectedIntegration) {
      toast({
        title: "No integration selected",
        description: "Please select a Rootly integration to analyze",
        variant: "destructive",
      })
      return
    }

    setShowTimeRangeDialog(true)
  }

  const runAnalysisWithTimeRange = async () => {
    setShowTimeRangeDialog(false)
    setTimeRange(selectedTimeRange)
    setAnalysisRunning(true)
    setAnalysisStage("loading")
    setAnalysisProgress(0)

    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        throw new Error('No authentication token found')
      }

      // Start the analysis
      const response = await fetch(`${API_BASE}/analyses/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          integration_id: parseInt(selectedIntegration),
          time_range: parseInt(selectedTimeRange),
          include_weekends: true
        }),
      })

      const responseData = await response.json()
      
      if (!response.ok) {
        throw new Error(responseData.detail || 'Failed to start analysis')
      }

      const { id: analysis_id } = responseData
      
      if (!analysis_id) {
        throw new Error('No analysis ID returned from server')
      }

      console.log('Started analysis with ID:', analysis_id)
      
      // Refresh the analyses list to show the new running analysis in sidebar
      await loadPreviousAnalyses()

      // Poll for analysis completion
      let currentStageIndex = 0
      let pollRetryCount = 0
      const maxRetries = 10 // Stop after 10 failed polls
      
      const pollAnalysis = async () => {
        try {
          if (!analysis_id) {
            console.error('Analysis ID is undefined, stopping polling')
            setAnalysisRunning(false)
            return
          }
          
          const pollResponse = await fetch(`${API_BASE}/analyses/${analysis_id}`, {
            headers: {
              'Authorization': `Bearer ${authToken}`
            }
          })

          if (pollResponse.ok) {
            const analysisData = await pollResponse.json()
            
            if (analysisData.status === 'completed') {
              setAnalysisRunning(false)
              setCurrentAnalysis(analysisData)
              
              // Reload previous analyses from API to ensure sidebar is up-to-date
              await loadPreviousAnalyses()
              
              toast({
                title: "Analysis completed!",
                description: "Your team burnout analysis is ready.",
              })
              return
            } else if (analysisData.status === 'failed') {
              setAnalysisRunning(false)
              
              // Check if we have partial data to display
              if (analysisData.analysis_data?.partial_data) {
                setCurrentAnalysis(analysisData)
                toast({
                  title: "Analysis completed with data",
                  description: "Analysis processing failed, but raw data was collected successfully.",
                  variant: "default",
                })
                await loadPreviousAnalyses()
              } else {
                toast({
                  title: "Analysis failed",
                  description: analysisData.error_message || "The analysis could not be completed. Please try again.",
                  variant: "destructive",
                })
              }
              return
            }
          }

          // Simulate progress through stages
          if (currentStageIndex < analysisStages.length - 1) {
            const stage = analysisStages[currentStageIndex]
            setAnalysisStage(stage.key as AnalysisStage)
            setAnalysisProgress((currentStageIndex + 1) * (100 / analysisStages.length))
            currentStageIndex++
          }

          // Continue polling
          pollRetryCount = 0 // Reset retry count on successful poll
          setTimeout(pollAnalysis, 2000)
        } catch (error) {
          console.error('Polling error:', error)
          pollRetryCount++
          
          if (pollRetryCount >= maxRetries) {
            console.error('Max polling retries reached, stopping analysis')
            setAnalysisRunning(false)
            toast({
              title: "Analysis polling failed",
              description: "Unable to get analysis status. Please try running the analysis again.",
              variant: "destructive",
            })
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
      toast({
        title: "Analysis failed",
        description: error instanceof Error ? error.message : "Failed to run analysis",
        variant: "destructive",
      })
    }
  }

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
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
      team_name: selectedIntegrationData?.name,
      ...currentAnalysis.analysis_data
    }
    
    const dataStr = JSON.stringify(exportData, null, 2)
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)
    const exportFileDefaultName = `burnout-analysis-${selectedIntegrationData?.name || 'team'}-${new Date().toISOString().split('T')[0]}.json`
    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()
  }

  const handleManageIntegrations = () => {
    router.push('/setup/rootly')
  }

  if (loadingIntegrations) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <Activity className="w-8 h-8 text-purple-600 animate-pulse mx-auto mb-4" />
          <p className="text-gray-600">Loading integrations...</p>
        </div>
      </div>
    )
  }

  if (integrations.length === 0) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>No Integrations Found</CardTitle>
            <CardDescription>
              You need to connect at least one Rootly integration to start analyzing team burnout.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={handleManageIntegrations} className="w-full">
              <Settings className="w-4 h-4 mr-2" />
              Manage Integrations
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const selectedIntegrationData = integrations.find(i => i.id.toString() === selectedIntegration)
  
  // Generate chart data from real analysis results
  const chartData = currentAnalysis?.analysis_data?.team_health ? [
    { date: "Week 4", score: Math.max(0, currentAnalysis.analysis_data.team_health.overall_score * 10 - 10) },
    { date: "Week 3", score: Math.max(0, currentAnalysis.analysis_data.team_health.overall_score * 10 - 5) },
    { date: "Week 2", score: Math.max(0, currentAnalysis.analysis_data.team_health.overall_score * 10) },
    { date: "Week 1", score: currentAnalysis.analysis_data.team_health.overall_score * 10 },
  ] : []
  
  const memberBarData = currentAnalysis?.analysis_data?.team_analysis?.members?.map((member) => ({
    name: member.user_name.split(" ")[0],
    fullName: member.user_name,
    score: member.burnout_score * 10, // Convert 0-10 scale to 0-100 for display
    riskLevel: member.risk_level,
    fill: member.risk_level === "high" ? "#dc2626" :      // Red for high
          member.risk_level === "medium" ? "#f59e0b" :    // Amber for medium
          "#10b981",                                       // Green for low
  })) || []
  
  const members = currentAnalysis?.analysis_data?.team_analysis?.members || []
  const burnoutFactors = members.length > 0 ? [
    { factor: "Workload", value: members.reduce((avg, m) => avg + (m.factors?.workload || 0), 0) / members.length * 10 },
    { factor: "After Hours", value: members.reduce((avg, m) => avg + (m.factors?.after_hours || 0), 0) / members.length * 10 },
    { factor: "Weekend Work", value: members.reduce((avg, m) => avg + (m.factors?.weekend_work || 0), 0) / members.length * 10 },
    { factor: "Incident Load", value: members.reduce((avg, m) => avg + (m.factors?.incident_load || 0), 0) / members.length * 10 },
    { factor: "Response Time", value: members.reduce((avg, m) => avg + (m.factors?.response_time || 0), 0) / members.length * 10 },
  ] : []

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div
        className={`${sidebarCollapsed ? "w-16" : "w-60"} bg-gray-900 text-white transition-all duration-300 flex flex-col`}
      >
        {/* Header */}
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center justify-between">
            {!sidebarCollapsed && (
              <div className="flex items-center space-x-2">
                <Image
                  src="/images/rootly-logo.svg"
                  alt="Rootly"
                  width={24}
                  height={24}
                  className="h-6 w-6 invert"
                />
                <span className="font-semibold text-sm">Burnout Detector</span>
              </div>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="text-gray-400 hover:text-white hover:bg-gray-800"
            >
              {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </Button>
          </div>
        </div>

        {/* Team Selector */}
        {!sidebarCollapsed && (
          <div className="p-4 border-b border-gray-700">
            <Select value={selectedIntegration} onValueChange={setSelectedIntegration}>
              <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {integrations.map((integration) => (
                  <SelectItem key={integration.id} value={integration.id.toString()}>
                    {integration.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Navigation */}
        <div className="flex-1 flex flex-col p-4 space-y-2">
          <div className="flex-1 space-y-2">
            <Button
              onClick={startAnalysis}
              disabled={analysisRunning}
              className="w-full justify-start bg-purple-600 hover:bg-purple-700 text-white"
            >
              <Play className="w-4 h-4 mr-2" />
              {!sidebarCollapsed && "New Analysis"}
            </Button>

            <div className="space-y-1">
              {!sidebarCollapsed && previousAnalyses.length > 0 && (
                <p className="text-xs text-gray-400 uppercase tracking-wide px-2 py-1 mt-4">Recent</p>
              )}
              {previousAnalyses.slice(0, 5).map((analysis) => {
                const analysisDate = new Date(analysis.created_at)
                const timeStr = analysisDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
                const dateStr = analysisDate.toLocaleDateString([], { month: 'short', day: 'numeric' })
                
                // Debug integration matching
                const matchingIntegration = integrations.find(i => i.id === Number(analysis.integration_id)) || 
                                          integrations.find(i => String(i.id) === String(analysis.integration_id))
                
                if (!matchingIntegration) {
                  console.log('No matching integration found for analysis:', {
                    analysisId: analysis.id,
                    integrationId: analysis.integration_id,
                    integrationIdType: typeof analysis.integration_id,
                    availableIntegrations: integrations.map(i => ({id: i.id, name: i.name, type: typeof i.id}))
                  })
                }
                
                const teamName = matchingIntegration?.name || 'Unknown Team'
                const isSelected = currentAnalysis?.id === analysis.id
                return (
                  <div key={analysis.id} className={`relative group ${isSelected ? 'bg-gray-800' : ''} rounded`}>
                    <Button 
                      variant="ghost" 
                      className={`w-full justify-start text-gray-300 hover:text-white hover:bg-gray-800 py-2 h-auto ${isSelected ? 'bg-gray-800 text-white' : ''}`}
                      onClick={() => setCurrentAnalysis(analysis)}
                    >
                      {sidebarCollapsed ? (
                        <Clock className="w-4 h-4" />
                      ) : (
                        <div className="flex flex-col items-start w-full text-xs pr-8">
                          <div className="flex justify-between items-center w-full mb-1">
                            <span className="font-medium">{teamName}</span>
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
              })}
            </div>
          </div>

          <div className="space-y-2">
            <Separator className="bg-gray-700" />
            <Button 
              variant="ghost" 
              className="w-full justify-start text-gray-300 hover:text-white hover:bg-gray-800"
              onClick={handleManageIntegrations}
            >
              <Settings className="w-4 h-4 mr-2" />
              {!sidebarCollapsed && "Manage Integrations"}
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Team Burnout Analysis</h1>
              <p className="text-gray-600">
                {selectedIntegrationData ? `${selectedIntegrationData.name} - ${selectedIntegrationData.organization_name}` : 'Select a team to analyze'}
              </p>
            </div>
            {/* Export Dropdown */}
            {currentAnalysis && currentAnalysis.analysis_data && (
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
                      <span className="text-xs text-gray-500">Team member scores</span>
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

          {/* Analysis Running State */}
          {analysisRunning && (
            <Card className="mb-6 bg-gradient-to-b from-purple-50 to-white border-purple-200 shadow-lg">
              <CardContent className="p-8 text-center">
                <div className="w-20 h-20 bg-gradient-to-r from-purple-100 to-purple-200 rounded-full flex items-center justify-center mx-auto mb-6 animate-pulse shadow-md">
                  <Activity className="w-10 h-10 text-purple-600 animate-spin" />
                </div>
                <h3 className="text-xl font-bold mb-2 text-purple-900">
                  {analysisStages.find((s) => s.key === analysisStage)?.label}
                </h3>
                <p className="text-sm text-purple-600 mb-6 font-medium">
                  {analysisStages.find((s) => s.key === analysisStage)?.detail}
                </p>
                
                {/* Enhanced Progress Bar */}
                <div className="w-full max-w-md mx-auto mb-6">
                  <div className="relative">
                    <div className="w-full h-4 bg-purple-100 rounded-full border border-purple-200 overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-purple-400 via-purple-500 to-purple-600 rounded-full transition-all duration-1000 ease-out relative"
                        style={{ width: `${analysisProgress}%` }}
                      >
                        <div className="absolute inset-0 bg-white opacity-30 animate-pulse rounded-full"></div>
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-20 animate-ping rounded-full"></div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center justify-center space-x-4 mb-6">
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-purple-300 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                  <p className="text-lg font-semibold text-purple-800">
                    {Math.round(analysisProgress)}% complete
                  </p>
                </div>
                
                <Button variant="outline" onClick={() => setAnalysisRunning(false)} className="border-purple-300 hover:bg-purple-50 text-purple-700">
                  <X className="w-4 h-4 mr-2" />
                  Cancel Analysis
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Failed Analysis Without Data */}
          {!analysisRunning && currentAnalysis && currentAnalysis.status === 'failed' && 
           !currentAnalysis.analysis_data?.partial_data && !currentAnalysis.analysis_data?.team_health && (
            <Card className="mb-6 border-red-200 bg-red-50">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2 text-red-800">
                  <AlertTriangle className="w-5 h-5" />
                  <span>Analysis Failed</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-red-700 mb-4">
                  This analysis failed and no data was collected.
                </p>
                <div className="p-3 bg-red-100 rounded-lg">
                  <p className="text-xs text-red-600">
                    <strong>Error:</strong> {currentAnalysis.error_message || 'Unknown error occurred'}
                  </p>
                </div>
                <div className="mt-4">
                  <Button
                    onClick={() => setShowTimeRangeDialog(true)}
                    className="bg-red-600 hover:bg-red-700 text-white"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    Try Again
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Analysis Complete State */}
          {!analysisRunning && currentAnalysis && (currentAnalysis.analysis_data?.team_health || currentAnalysis.analysis_data?.partial_data) && (
            <>
              {/* Overview Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <Card className="border-2 border-purple-200 bg-white/70 backdrop-blur-sm shadow-lg">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-purple-700">Team Health Score</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {currentAnalysis?.analysis_data?.team_health ? (
                      <div>
                        <div className="flex items-center justify-between">
                          <div className="text-2xl font-bold text-gray-900">{Math.round(currentAnalysis.analysis_data.team_health.overall_score * 10)}/100</div>
                          <div className="text-sm font-medium text-purple-600">{currentAnalysis.analysis_data.team_health.health_status}</div>
                        </div>
                        <p className="text-xs text-gray-600 mt-1">
                          Based on {currentAnalysis.time_range || 30} days of data
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
                    <CardTitle className="text-sm font-medium text-purple-700">At-Risk Members</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {currentAnalysis?.analysis_data?.team_health ? (
                      <div>
                        <div className="flex items-center space-x-2">
                          <div className="text-2xl font-bold text-red-600">{currentAnalysis.analysis_data.team_health.risk_distribution.high}</div>
                          <AlertTriangle className="w-5 h-5 text-red-500" />
                        </div>
                        <p className="text-xs text-gray-600 mt-1">Out of {currentAnalysis.analysis_data.team_analysis?.members?.length || 0} members</p>
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
                    <CardTitle className="text-sm font-medium text-purple-700">Last Analysis</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-gray-900">
                      {currentAnalysis.created_at ? new Date(currentAnalysis.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'N/A'}
                    </div>
                    <p className="text-xs text-gray-600 mt-1">
                      {currentAnalysis.created_at ? (
                        <>
                          {new Date(currentAnalysis.created_at).toLocaleDateString('en-US', { year: 'numeric' })}, 
                          {' ' + new Date(currentAnalysis.created_at).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
                        </>
                      ) : 'No date available'}
                    </p>
                  </CardContent>
                </Card>
              </div>

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

              {/* Team Member Scores - Full Width */}
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>Team Member Scores</CardTitle>
                  <CardDescription>Burnout risk levels across team members</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={memberBarData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis domain={[0, 100]} />
                        <Tooltip 
                          formatter={(value, name, props) => {
                            const data = props.payload;
                            return [
                              `${value}%`, 
                              `Burnout Score (${data.riskLevel.charAt(0).toUpperCase() + data.riskLevel.slice(1)} Risk)`
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
                </CardContent>
              </Card>

              {/* Charts Section */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                {/* Trend Chart */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>Burnout Trend</CardTitle>
                      <Select value={chartType} onValueChange={setChartType}>
                        <SelectTrigger className="w-24">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="daily">Daily</SelectItem>
                          <SelectItem value="weekly">Weekly</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[250px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey={chartType === 'daily' ? 'date' : 'week'} />
                          <YAxis domain={[0, 100]} />
                          <Tooltip />
                          <Line type="monotone" dataKey="score" stroke="#8B5CF6" strokeWidth={2} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                {/* Radar Chart */}
                <Card>
                  <CardHeader>
                    <CardTitle>Burnout Factors</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[250px] p-4">
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart data={burnoutFactors} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
                          <PolarGrid />
                          <PolarAngleAxis 
                            dataKey="factor" 
                            tick={{ fontSize: 12, fill: '#374151' }}
                            className="text-xs"
                          />
                          <PolarRadiusAxis 
                            domain={[0, 100]} 
                            tick={{ fontSize: 10, fill: '#6B7280' }}
                            tickCount={4}
                          />
                          <Radar 
                            dataKey="value" 
                            stroke="#8B5CF6" 
                            fill="#8B5CF6" 
                            fillOpacity={0.3}
                            strokeWidth={2}
                          />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Team Members Grid */}
              <Card>
                <CardHeader>
                  <CardTitle>Team Members</CardTitle>
                  <CardDescription>Click on a member to view detailed analysis</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {currentAnalysis?.analysis_data?.team_analysis?.members?.map((member) => (
                      <Card
                        key={member.user_id}
                        className="cursor-pointer hover:shadow-md transition-shadow"
                        onClick={() => setSelectedMember({
                          id: member.user_id,
                          name: member.user_name,
                          email: member.user_email,
                          burnoutScore: member.burnout_score * 10,
                          riskLevel: member.risk_level as 'high' | 'medium' | 'low',
                          trend: 'stable' as const,
                          incidentsHandled: member.incident_count,
                          avgResponseTime: `${Math.round(member.metrics.avg_response_time_minutes)}m`,
                          factors: {
                            workload: member.factors.workload * 10,
                            afterHours: member.factors.after_hours * 10,
                            weekendWork: member.factors.weekend_work * 10,
                            incidentLoad: member.factors.incident_load * 10,
                            responseTime: member.factors.response_time * 10,
                          }
                        })}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center space-x-3">
                              <Avatar>
                                <AvatarFallback>
                                  {member.user_name
                                    .split(" ")
                                    .map((n) => n[0])
                                    .join("")}
                                </AvatarFallback>
                              </Avatar>
                              <div>
                                <h3 className="font-medium">{member.user_name}</h3>
                                <p className="text-sm text-gray-500">{member.user_email}</p>
                              </div>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Badge className={getRiskColor(member.risk_level)}>{member.risk_level.toUpperCase()}</Badge>
                            </div>
                          </div>
                          <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                              <span>Burnout Score</span>
                              <span className="font-medium">{Math.round(member.burnout_score * 10)}/100</span>
                            </div>
                            <Progress value={member.burnout_score * 10} className="h-2" />
                            <div className="flex justify-between text-xs text-gray-500">
                              <span>{member.incident_count} incidents</span>
                              <span>{Math.round(member.metrics.avg_response_time_minutes)}m avg response</span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    )) || (
                      <div className="col-span-full text-center text-gray-500 py-8">
                        No team member data available yet
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </>
          )}

          {/* Empty State */}
          {!analysisRunning && !currentAnalysis && (
            <Card className="text-center p-8">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Activity className="w-8 h-8 text-purple-600" />
              </div>
              <h3 className="text-lg font-semibold mb-2">No Analysis Yet</h3>
              <p className="text-gray-600 mb-4">
                Click "New Analysis" to start analyzing your team's burnout metrics
              </p>
              <Button onClick={startAnalysis} className="bg-purple-600 hover:bg-purple-700">
                <Play className="w-4 h-4 mr-2" />
                New Analysis
              </Button>
            </Card>
          )}
        </div>
      </div>

      {/* Time Range Selection Dialog */}
      <Dialog open={showTimeRangeDialog} onOpenChange={setShowTimeRangeDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Select Analysis Time Range</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Choose the time period for analyzing burnout metrics:
            </p>
            <Select value={selectedTimeRange} onValueChange={setSelectedTimeRange}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
            <div className="flex justify-end space-x-2 pt-4">
              <Button variant="outline" onClick={() => setShowTimeRangeDialog(false)}>
                Cancel
              </Button>
              <Button onClick={runAnalysisWithTimeRange} className="bg-purple-600 hover:bg-purple-700">
                <Play className="w-4 h-4 mr-2" />
                Start Analysis
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Member Detail Modal */}
      <Dialog open={!!selectedMember} onOpenChange={() => setSelectedMember(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-3">
              <Avatar>
                <AvatarImage src={selectedMember?.avatar} />
                <AvatarFallback>
                  {selectedMember?.name
                    .split(" ")
                    .map((n) => n[0])
                    .join("")}
                </AvatarFallback>
              </Avatar>
              <div>
                <span>{selectedMember?.name}</span>
                <p className="text-sm text-gray-500 font-normal">{selectedMember?.role || selectedMember?.email}</p>
              </div>
            </DialogTitle>
          </DialogHeader>
          {selectedMember && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Burnout Score</p>
                  <p className="text-2xl font-bold">{selectedMember.burnoutScore}/100</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Risk Level</p>
                  <Badge className={getRiskColor(selectedMember.riskLevel)}>
                    {selectedMember.riskLevel.toUpperCase()}
                  </Badge>
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-2">Burnout Factors</p>
                <div className="space-y-2">
                  {Object.entries(selectedMember.factors).map(([factor, value]) => (
                    <div key={factor} className="flex items-center justify-between">
                      <span className="text-sm capitalize">{factor.replace(/([A-Z])/g, " $1")}</span>
                      <div className="flex items-center space-x-2">
                        <Progress value={value} className="w-20 h-2" />
                        <span className="text-sm font-medium w-8">{value}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-600">Incidents Handled</p>
                  <p className="font-medium">{selectedMember.incidentsHandled}</p>
                </div>
                <div>
                  <p className="text-gray-600">Avg Response Time</p>
                  <p className="font-medium">{selectedMember.avgResponseTime}</p>
                </div>
              </div>
              {currentAnalysis?.analysis_data?.recommendations?.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm text-gray-600 font-medium">Recommendations:</p>
                  {currentAnalysis.analysis_data.recommendations.slice(0, 3).map((rec, index) => (
                    <Alert key={index}>
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        <strong>{rec.priority} Priority:</strong> {rec.message}
                      </AlertDescription>
                    </Alert>
                  ))}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

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
                     'Unknown Team'}
                  </span>
                  <span className="text-gray-500">
                    {new Date(analysisToDelete.created_at).toLocaleDateString([], { 
                      month: 'short', 
                      day: 'numeric', 
                      year: 'numeric',
                      hour: 'numeric',
                      minute: '2-digit'
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
    </div>
  )
}