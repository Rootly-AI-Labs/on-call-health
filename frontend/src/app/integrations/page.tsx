"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Tooltip } from "@/components/ui/tooltip"
import {
  Activity,
  ArrowLeft,
  Building,
  Calendar,
  ChevronRight,
  ChevronDown,
  Clock,
  Edit3,
  Key,
  MoreVertical,
  Plus,
  Settings,
  Shield,
  Star,
  Trash2,
  Users,
  Zap,
  Loader2,
  CheckCircle,
  AlertCircle,
  Eye,
  EyeOff,
  Copy,
  Check,
  HelpCircle,
  ExternalLink,
} from "lucide-react"
import Link from "next/link"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { useToast } from "@/hooks/use-toast"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Validation schemas
const rootlyFormSchema = z.object({
  rootlyToken: z.string()
    .min(1, "Rootly API token is required")
    .regex(/^rootly_[a-f0-9]{64}$/, "Invalid Rootly token format. Token should start with 'rootly_' followed by 64 hex characters"),
  nickname: z.string().optional(),
})

const pagerdutyFormSchema = z.object({
  pagerdutyToken: z.string()
    .min(1, "PagerDuty API token is required")
    .regex(/^[A-Za-z0-9+_-]{20,32}$/, "Invalid PagerDuty token format. Token should be 20-32 characters long"),
  nickname: z.string().optional(),
})

// Helper functions
const isValidRootlyToken = (token: string): boolean => {
  return /^rootly_[a-f0-9]{64}$/.test(token)
}

const isValidPagerDutyToken = (token: string): boolean => {
  return /^[A-Za-z0-9+_-]{20,32}$/.test(token)
}

type RootlyFormData = z.infer<typeof rootlyFormSchema>
type PagerDutyFormData = z.infer<typeof pagerdutyFormSchema>

interface Integration {
  id: number
  name: string
  organization_name: string
  total_users: number
  total_services?: number
  is_default: boolean
  created_at: string
  last_used_at: string | null
  token_suffix: string
  platform: "rootly" | "pagerduty"
  permissions?: {
    users: {
      access: boolean
      error: string | null
    }
    incidents: {
      access: boolean
      error: string | null
    }
  }
}

interface PreviewData {
  organization_name: string
  total_users: number
  total_services?: number
  suggested_name?: string
  can_add?: boolean
  current_user?: string
}

export default function IntegrationsPage() {
  // State management
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loadingIntegrations, setLoadingIntegrations] = useState(true)
  const [activeTab, setActiveTab] = useState<"rootly" | "pagerduty" | null>(null)
  const [backUrl, setBackUrl] = useState<string>('/dashboard')
  
  // Add integration state
  const [addingPlatform, setAddingPlatform] = useState<"rootly" | "pagerduty" | null>(null)
  const [isShowingToken, setIsShowingToken] = useState(false)
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'error' | 'duplicate'>('idle')
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [duplicateInfo, setDuplicateInfo] = useState<any>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [copied, setCopied] = useState(false)
  
  // Edit/Delete state
  const [editingIntegration, setEditingIntegration] = useState<number | null>(null)
  const [editingName, setEditingName] = useState("")
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [integrationToDelete, setIntegrationToDelete] = useState<Integration | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  
  // Instructions state
  const [showRootlyInstructions, setShowRootlyInstructions] = useState(false)
  const [showPagerDutyInstructions, setShowPagerDutyInstructions] = useState(false)
  
  const router = useRouter()
  const { toast } = useToast()
  
  // Forms
  const rootlyForm = useForm<RootlyFormData>({
    resolver: zodResolver(rootlyFormSchema),
    defaultValues: {
      rootlyToken: "",
      nickname: "",
    },
  })
  
  const pagerdutyForm = useForm<PagerDutyFormData>({
    resolver: zodResolver(pagerdutyFormSchema),
    defaultValues: {
      pagerdutyToken: "",
      nickname: "",
    },
  })

  useEffect(() => {
    loadAllIntegrations()
    
    // Determine back navigation based on referrer
    const referrer = document.referrer
    if (referrer) {
      const referrerUrl = new URL(referrer)
      const pathname = referrerUrl.pathname
      
      if (pathname.includes('/auth/success')) {
        setBackUrl('/auth/success')
      } else if (pathname.includes('/dashboard')) {
        setBackUrl('/dashboard')
      } else if (pathname === '/') {
        setBackUrl('/')
      } else {
        setBackUrl('/dashboard') // default fallback
      }
    } else {
      setBackUrl('/dashboard') // default when no referrer
    }
  }, [])

  const loadAllIntegrations = async () => {
    setLoadingIntegrations(true)
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        router.push('/auth/success')
        return
      }

      const [rootlyResponse, pagerdutyResponse] = await Promise.all([
        fetch(`${API_BASE}/rootly/integrations`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        }),
        fetch(`${API_BASE}/pagerduty/integrations`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        })
      ])

      const rootlyData = rootlyResponse.ok ? await rootlyResponse.json() : { integrations: [] }
      const pagerdutyData = pagerdutyResponse.ok ? await pagerdutyResponse.json() : { integrations: [] }

      const rootlyIntegrations = rootlyData.integrations.map((i: Integration) => ({ ...i, platform: 'rootly' }))
      const pagerdutyIntegrations = pagerdutyData.integrations || []

      setIntegrations([...rootlyIntegrations, ...pagerdutyIntegrations])
    } catch (error) {
      console.error('Failed to load integrations:', error)
      toast({
        title: "Failed to load integrations",
        description: "Please try refreshing the page",
        variant: "destructive"
      })
    } finally {
      setLoadingIntegrations(false)
    }
  }

  const testConnection = async (platform: "rootly" | "pagerduty", token: string) => {
    console.log('testConnection called for platform:', platform)
    setIsTestingConnection(true)
    setConnectionStatus('idle')
    setPreviewData(null)
    setDuplicateInfo(null)
    
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        console.log('No auth token found')
        throw new Error('No authentication token found')
      }

      const endpoint = platform === 'rootly' 
        ? `${API_BASE}/rootly/token/test`
        : `${API_BASE}/pagerduty/token/test`
      
      console.log('Making request to:', endpoint)

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          token: token
        })
      })

      const data = await response.json()
      
      console.log('Response status:', response.status)
      console.log('Response ok:', response.ok) 
      console.log('Response data:', data)

      if (response.ok && (data.valid || data.status === 'success')) {
        setConnectionStatus('success')
        if (platform === 'rootly') {
          setPreviewData({
            organization_name: data.preview?.organization_name || data.account_info?.organization_name,
            total_users: data.preview?.total_users || data.account_info?.total_users,
            suggested_name: data.preview?.suggested_name || data.account_info?.suggested_name,
            can_add: data.preview?.can_add || data.account_info?.can_add,
          })
        } else {
          setPreviewData(data.account_info)
        }
      } else if (response.status === 409) {
        setConnectionStatus('duplicate')
        setDuplicateInfo(data.detail)
      } else {
        setConnectionStatus('error')
      }
    } catch (error) {
      console.error('Connection test error:', error)
      setConnectionStatus('error')
    } finally {
      setIsTestingConnection(false)
    }
  }

  const addIntegration = async (platform: "rootly" | "pagerduty") => {
    if (!previewData) return
    
    setIsAdding(true)
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        throw new Error('No authentication token found')
      }

      const form = platform === 'rootly' ? rootlyForm : pagerdutyForm
      const values = form.getValues()
      const token = platform === 'rootly' ? values.rootlyToken : values.pagerdutyToken
      const nickname = values.nickname

      const endpoint = platform === 'rootly'
        ? `${API_BASE}/rootly/token/add`
        : `${API_BASE}/pagerduty/integrations`

      const body = platform === 'rootly'
        ? {
            token: token,
            name: nickname || previewData.suggested_name || previewData.organization_name,
          }
        : {
            token: token,
            name: nickname || previewData.organization_name,
            platform: 'pagerduty'
          }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(body)
      })

      const responseData = await response.json()

      if (response.ok) {
        toast({
          title: "Integration added!",
          description: `Your ${platform === 'rootly' ? 'Rootly' : 'PagerDuty'} account has been connected successfully.`,
        })
        
        // Clear local storage cache
        localStorage.removeItem(`${platform}_integrations`)
        localStorage.removeItem(`${platform}_integrations_timestamp`)
        
        // Reset form and state
        form.reset()
        setConnectionStatus('idle')
        setPreviewData(null)
        setAddingPlatform(null)
        
        // Reload integrations
        loadAllIntegrations()
      } else {
        throw new Error(responseData.detail?.message || responseData.message || 'Failed to add integration')
      }
    } catch (error) {
      console.error('Add integration error:', error)
      toast({
        title: "Failed to add integration",
        description: error instanceof Error ? error.message : "An unexpected error occurred.",
        variant: "destructive",
      })
    } finally {
      setIsAdding(false)
    }
  }

  const deleteIntegration = async () => {
    if (!integrationToDelete) return
    
    setIsDeleting(true)
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      const endpoint = integrationToDelete.platform === 'rootly'
        ? `${API_BASE}/rootly/integrations/${integrationToDelete.id}`
        : `${API_BASE}/pagerduty/integrations/${integrationToDelete.id}`

      const response = await fetch(endpoint, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        toast({
          title: "Integration deleted",
          description: "The integration has been removed.",
        })
        
        // Clear local storage
        localStorage.removeItem(`${integrationToDelete.platform}_integrations`)
        localStorage.removeItem(`${integrationToDelete.platform}_integrations_timestamp`)
        
        loadAllIntegrations()
        setDeleteDialogOpen(false)
        setIntegrationToDelete(null)
      } else {
        throw new Error('Failed to delete integration')
      }
    } catch (error) {
      console.error('Delete error:', error)
      toast({
        title: "Failed to delete",
        description: "An error occurred while deleting the integration.",
        variant: "destructive",
      })
    } finally {
      setIsDeleting(false)
    }
  }

  const updateIntegrationName = async (integration: Integration, newName: string) => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      const endpoint = integration.platform === 'rootly'
        ? `${API_BASE}/rootly/integrations/${integration.id}`
        : `${API_BASE}/pagerduty/integrations/${integration.id}`

      const response = await fetch(endpoint, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: newName })
      })

      if (response.ok) {
        toast({
          title: "Name updated",
          description: "Integration name has been updated.",
        })
        loadAllIntegrations()
      }
    } catch (error) {
      console.error('Error updating name:', error)
      toast({
        title: "Failed to update",
        description: "Could not update integration name.",
        variant: "destructive"
      })
    }
  }

  const setAsDefault = async (integration: Integration) => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      const endpoint = integration.platform === 'rootly'
        ? `${API_BASE}/rootly/integrations/${integration.id}`
        : `${API_BASE}/pagerduty/integrations/${integration.id}`

      const response = await fetch(endpoint, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ is_default: true })
      })

      if (response.ok) {
        toast({
          title: "Default integration updated",
          description: `${integration.name} is now the default integration.`,
        })
        loadAllIntegrations()
      }
    } catch (error) {
      console.error('Error setting default:', error)
      toast({
        title: "Failed to update",
        description: "Could not set as default integration.",
        variant: "destructive"
      })
    }
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy: ', err)
    }
  }

  const filteredIntegrations = integrations.filter(integration => {
    if (activeTab === null) return false
    return integration.platform === activeTab
  })

  const rootlyCount = integrations.filter(i => i.platform === 'rootly').length
  const pagerdutyCount = integrations.filter(i => i.platform === 'pagerduty').length

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-slate-200 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Manage Integrations</h1>
          </div>

          <Link href={backUrl}>
            <Button variant="ghost" size="sm" className="flex items-center space-x-2">
              <ArrowLeft className="w-4 h-4" />
              <span>
                {backUrl === '/auth/success' ? 'Back' : 
                 backUrl === '/dashboard' ? 'Back to Dashboard' : 
                 'Back'}
              </span>
            </Button>
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Introduction Text */}
        <div className="text-center mb-8 max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-slate-900 mb-3">Connect Your Incident Management Platform</h2>
          <p className="text-lg text-slate-600 mb-2">
            Integrate with your incident management tool to analyze team burnout patterns
          </p>
          <p className="text-slate-500">
            We analyze incident response patterns, on-call schedules, and workload distribution to identify burnout risk across your team
          </p>
        </div>

        {/* Ready for Analysis CTA */}
        {loadingIntegrations ? (
          <div className="bg-gradient-to-r from-gray-50 to-gray-100 border border-gray-200 rounded-lg p-6 mb-8 max-w-2xl mx-auto animate-pulse">
            <div className="text-center">
              <div className="w-12 h-12 bg-gray-300 rounded-full mx-auto mb-4"></div>
              <div className="h-6 bg-gray-300 rounded w-80 mx-auto mb-2"></div>
              <div className="h-4 bg-gray-300 rounded w-96 mx-auto mb-2"></div>
              <div className="h-4 bg-gray-300 rounded w-72 mx-auto mb-4"></div>
              <div className="h-10 bg-gray-300 rounded w-40 mx-auto"></div>
            </div>
          </div>
        ) : integrations.length > 0 && (
          <div className="bg-gradient-to-r from-purple-50 to-green-50 border border-purple-200 rounded-lg p-6 mb-8 max-w-2xl mx-auto">
            <div className="text-center">
              <div className="w-12 h-12 bg-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-2">
                Ready to analyze your team's burnout risk!
              </h3>
              <p className="text-slate-600 mb-4">
                You have {integrations.length} integration{integrations.length > 1 ? 's' : ''} connected. 
                Run your first analysis to identify burnout patterns across your team.
              </p>
              <Link href="/dashboard">
                <Button className="bg-purple-600 hover:bg-purple-700 text-white">
                  <Activity className="w-4 h-4 mr-2" />
                  Go to Dashboard
                </Button>
              </Link>
            </div>
          </div>
        )}

        {/* Platform Selection Cards */}
        <div className="grid md:grid-cols-2 gap-8 mb-8 max-w-2xl mx-auto">
          {loadingIntegrations ? (
            <>
              {/* Rootly Card Skeleton */}
              <Card className="border-2 border-gray-200 p-8 flex items-center justify-center relative h-32 animate-pulse">
                <div className="absolute top-4 right-4 w-6 h-6 bg-gray-300 rounded"></div>
                <div className="h-12 w-48 bg-gray-300 rounded"></div>
              </Card>
              
              {/* PagerDuty Card Skeleton */}
              <Card className="border-2 border-gray-200 p-8 flex items-center justify-center relative h-32 animate-pulse">
                <div className="absolute top-4 right-4 w-6 h-6 bg-gray-300 rounded"></div>
                <div className="flex items-center space-x-2">
                  <div className="w-10 h-10 bg-gray-300 rounded"></div>
                  <div className="h-8 w-32 bg-gray-300 rounded"></div>
                </div>
              </Card>
            </>
          ) : (
            <>
              {/* Rootly Card */}
              <Card 
                className={`border-2 transition-all cursor-pointer hover:shadow-lg ${
                  activeTab === 'rootly' 
                    ? 'border-purple-500 shadow-lg bg-purple-50' 
                    : 'border-gray-200 hover:border-purple-300'
                } p-8 flex items-center justify-center relative h-32`}
                onClick={() => {
                  setActiveTab('rootly')
                  setAddingPlatform('rootly')
                }}
              >
                {activeTab === 'rootly' && (
                  <div className="absolute top-4 right-4 flex items-center space-x-2">
                    <CheckCircle className="w-6 h-6 text-purple-600" />
                    <Badge variant="secondary" className="bg-purple-100 text-purple-700">{rootlyCount}</Badge>
                  </div>
                )}
                {activeTab !== 'rootly' && rootlyCount > 0 && (
                  <Badge variant="secondary" className="absolute top-4 right-4">{rootlyCount}</Badge>
                )}
                <Image
                  src="/images/rootly-logo-final.svg"
                  alt="Rootly"
                  width={220}
                  height={50}
                  className="h-12 w-auto object-contain"
                />
              </Card>

              {/* PagerDuty Card */}
              <Card 
                className={`border-2 transition-all cursor-pointer hover:shadow-lg ${
                  activeTab === 'pagerduty' 
                    ? 'border-green-500 shadow-lg bg-green-50' 
                    : 'border-gray-200 hover:border-green-300'
                } p-8 flex items-center justify-center relative h-32`}
                onClick={() => {
                  setActiveTab('pagerduty')
                  setAddingPlatform('pagerduty')
                }}
              >
                {activeTab === 'pagerduty' && (
                  <div className="absolute top-4 right-4 flex items-center space-x-2">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                    <Badge variant="secondary" className="bg-green-100 text-green-700">{pagerdutyCount}</Badge>
                  </div>
                )}
                {activeTab !== 'pagerduty' && pagerdutyCount > 0 && (
                  <Badge variant="secondary" className="absolute top-4 right-4">{pagerdutyCount}</Badge>
                )}
                <div className="flex items-center space-x-2">
                  <div className="w-10 h-10 bg-green-600 rounded flex items-center justify-center">
                    <span className="text-white font-bold text-base">PD</span>
                  </div>
                  <span className="text-2xl font-bold text-slate-900">PagerDuty</span>
                </div>
              </Card>
            </>
          )}
        </div>

        <div className="space-y-6">

            {/* Add Rootly Integration Form */}
            {addingPlatform === 'rootly' && (
              <Card className="border-purple-200 max-w-2xl mx-auto">
                <CardHeader className="p-8">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                      <Image src="/images/rootly-logo.svg" alt="Rootly" width={24} height={24} />
                    </div>
                    <div>
                      <CardTitle>Add Rootly Integration</CardTitle>
                      <CardDescription>Connect your Rootly account to analyze incident data</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 p-8 pt-0">
                  {/* Instructions */}
                  <div>
                    <button 
                      type="button"
                      onClick={() => setShowRootlyInstructions(!showRootlyInstructions)}
                      className="flex items-center space-x-2 text-sm text-purple-600 hover:text-purple-700"
                    >
                      <HelpCircle className="w-4 h-4" />
                      <span>How to get your Rootly API token</span>
                      <ChevronDown className={`w-4 h-4 transition-transform ${showRootlyInstructions ? 'rotate-180' : ''}`} />
                    </button>
                    {showRootlyInstructions && (
                      <div className="mt-4">
                        <Alert className="border-purple-200 bg-purple-50">
                          <AlertDescription>
                            <ol className="space-y-2 text-sm">
                              <li>1. Log in to your Rootly account</li>
                              <li>2. Navigate to <code className="bg-purple-100 px-1 rounded">Settings → API Keys</code></li>
                              <li>3. Click "Create API Key"</li>
                              <li>4. Give it a name (e.g., "Burnout Detector")</li>
                              <li>5. Select appropriate permissions (at minimum: read access to incidents and users)</li>
                              <li>6. Copy the generated token (starts with "rootly_")</li>
                            </ol>
                          </AlertDescription>
                        </Alert>
                      </div>
                    )}
                  </div>

                  {/* Form */}
                  <Form {...rootlyForm}>
                    <form onSubmit={rootlyForm.handleSubmit((data) => testConnection('rootly', data.rootlyToken))} className="space-y-4">
                      <FormField
                        control={rootlyForm.control}
                        name="rootlyToken"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Rootly API Token</FormLabel>
                            <FormControl>
                              <div className="relative">
                                <Input
                                  {...field}
                                  type={isShowingToken ? "text" : "password"}
                                  placeholder="rootly_********************************"
                                  className="pr-20"
                                />
                                <div className="absolute inset-y-0 right-0 flex items-center space-x-1 pr-3">
                                  {field.value && (
                                    <Button
                                      type="button"
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 w-7 p-0"
                                      onClick={() => copyToClipboard(field.value)}
                                    >
                                      {copied ? (
                                        <Check className="h-3 w-3 text-green-600" />
                                      ) : (
                                        <Copy className="h-3 w-3 text-slate-400" />
                                      )}
                                    </Button>
                                  )}
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 w-7 p-0"
                                    onClick={() => setIsShowingToken(!isShowingToken)}
                                  >
                                    {isShowingToken ? (
                                      <EyeOff className="h-3 w-3 text-slate-400" />
                                    ) : (
                                      <Eye className="h-3 w-3 text-slate-400" />
                                    )}
                                  </Button>
                                </div>
                              </div>
                            </FormControl>
                            <FormDescription>
                              Token should start with "rootly_" followed by 64 hex characters
                            </FormDescription>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      {/* Connection Status */}
                      {connectionStatus === 'success' && previewData && (
                        <>
                          <Alert className="border-purple-200 bg-purple-50">
                            <CheckCircle className="h-4 w-4 text-purple-600" />
                            <AlertDescription className="text-purple-800">
                              <div className="space-y-2">
                                <p className="font-semibold">Connection successful!</p>
                                <div className="space-y-1 text-sm">
                                  <p><span className="font-medium">Organization:</span> {previewData.organization_name}</p>
                                  <p><span className="font-medium">Users:</span> {previewData.total_users}</p>
                                </div>
                              </div>
                            </AlertDescription>
                          </Alert>

                          <FormField
                            control={rootlyForm.control}
                            name="nickname"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Integration Name (optional)</FormLabel>
                                <FormControl>
                                  <Input
                                    {...field}
                                    placeholder={previewData.suggested_name || previewData.organization_name}
                                  />
                                </FormControl>
                                <FormDescription>
                                  Give this integration a custom name
                                </FormDescription>
                              </FormItem>
                            )}
                          />
                        </>
                      )}

                      {connectionStatus === 'error' && (
                        <Alert variant="destructive">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>
                            Failed to connect. Please check your API token and try again.
                          </AlertDescription>
                        </Alert>
                      )}

                      {connectionStatus === 'duplicate' && duplicateInfo && (
                        <Alert className="border-yellow-200 bg-yellow-50">
                          <AlertCircle className="h-4 w-4 text-yellow-600" />
                          <AlertDescription className="text-yellow-800">
                            This Rootly account is already connected as "{duplicateInfo.existing_integration?.name || 'Unknown'}".
                          </AlertDescription>
                        </Alert>
                      )}

                      <div className="flex space-x-3">
                        <Button 
                          type="submit" 
                          disabled={isTestingConnection || !isValidRootlyToken(rootlyForm.watch('rootlyToken') || '')}
                          className="bg-purple-600 hover:bg-purple-700"
                        >
                          {isTestingConnection ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Testing Connection...
                            </>
                          ) : (
                            <>
                              <Shield className="w-4 h-4 mr-2" />
                              Test Connection
                            </>
                          )}
                        </Button>

                        {connectionStatus === 'success' && previewData?.can_add && (
                          <Button
                            type="button"
                            onClick={() => addIntegration('rootly')}
                            disabled={isAdding}
                            className="bg-green-600 hover:bg-green-700"
                          >
                            {isAdding ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Adding...
                              </>
                            ) : (
                              <>
                                <Plus className="w-4 h-4 mr-2" />
                                Add Integration
                              </>
                            )}
                          </Button>
                        )}
                      </div>
                    </form>
                  </Form>
                </CardContent>
              </Card>
            )}

            {/* Add PagerDuty Integration Form */}
            {addingPlatform === 'pagerduty' && (
              <Card className="border-green-200 max-w-2xl mx-auto">
                <CardHeader className="p-8">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                      <span className="text-green-600 font-bold">PD</span>
                    </div>
                    <div>
                      <CardTitle>Add PagerDuty Integration</CardTitle>
                      <CardDescription>Connect your PagerDuty account for burnout analysis</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 p-8 pt-0">
                  {/* Instructions */}
                  <div>
                    <button 
                      type="button"
                      onClick={() => setShowPagerDutyInstructions(!showPagerDutyInstructions)}
                      className="flex items-center space-x-2 text-sm text-green-600 hover:text-green-700"
                    >
                      <HelpCircle className="w-4 h-4" />
                      <span>How to get your PagerDuty API token</span>
                      <ChevronDown className={`w-4 h-4 transition-transform ${showPagerDutyInstructions ? 'rotate-180' : ''}`} />
                    </button>
                    {showPagerDutyInstructions && (
                      <div className="mt-4">
                        <Alert className="border-green-200 bg-green-50">
                          <AlertDescription>
                            <ol className="space-y-2 text-sm">
                              <li>1. Go to your PagerDuty account and click on your profile icon</li>
                              <li>2. Navigate to <code className="bg-green-100 px-1 rounded">My Profile → User Settings</code></li>
                              <li>3. Click on the "User Settings" tab</li>
                              <li>4. Create a new REST API User Token</li>
                            </ol>
                          </AlertDescription>
                        </Alert>
                      </div>
                    )}
                  </div>

                  {/* Form */}
                  <Form {...pagerdutyForm}>
                    <form onSubmit={pagerdutyForm.handleSubmit((data) => testConnection('pagerduty', data.pagerdutyToken))} className="space-y-4">
                      <FormField
                        control={pagerdutyForm.control}
                        name="pagerdutyToken"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>PagerDuty API Token</FormLabel>
                            <FormControl>
                              <div className="relative">
                                <Input
                                  {...field}
                                  type={isShowingToken ? "text" : "password"}
                                  placeholder="Enter your PagerDuty API token"
                                  className="pr-20"
                                />
                                <div className="absolute inset-y-0 right-0 flex items-center space-x-1 pr-3">
                                  {field.value && (
                                    <Button
                                      type="button"
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 w-7 p-0"
                                      onClick={() => copyToClipboard(field.value)}
                                    >
                                      {copied ? (
                                        <Check className="h-3 w-3 text-green-600" />
                                      ) : (
                                        <Copy className="h-3 w-3 text-slate-400" />
                                      )}
                                    </Button>
                                  )}
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 w-7 p-0"
                                    onClick={() => setIsShowingToken(!isShowingToken)}
                                  >
                                    {isShowingToken ? (
                                      <EyeOff className="h-3 w-3 text-slate-400" />
                                    ) : (
                                      <Eye className="h-3 w-3 text-slate-400" />
                                    )}
                                  </Button>
                                </div>
                              </div>
                            </FormControl>
                            <FormDescription>
                              Your API token should be 20-32 characters long
                            </FormDescription>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      {/* Connection Status */}
                      {connectionStatus === 'success' && previewData && (
                        <>
                          <Alert className="border-green-200 bg-green-50">
                            <CheckCircle className="h-4 w-4 text-green-600" />
                            <AlertDescription className="text-green-800">
                              <div className="space-y-2">
                                <p className="font-semibold">Connection successful!</p>
                                <div className="space-y-1 text-sm">
                                  <p><span className="font-medium">Organization:</span> {previewData.organization_name}</p>
                                  <p><span className="font-medium">Users:</span> {previewData.total_users}</p>
                                  <p><span className="font-medium">Services:</span> {previewData.total_services}</p>
                                </div>
                              </div>
                            </AlertDescription>
                          </Alert>

                          <FormField
                            control={pagerdutyForm.control}
                            name="nickname"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Integration Name (optional)</FormLabel>
                                <FormControl>
                                  <Input
                                    {...field}
                                    placeholder={previewData.organization_name}
                                  />
                                </FormControl>
                                <FormDescription>
                                  Give this integration a custom name
                                </FormDescription>
                              </FormItem>
                            )}
                          />
                        </>
                      )}

                      {connectionStatus === 'error' && (
                        <Alert variant="destructive">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>
                            Failed to connect. Please check your API token and try again.
                          </AlertDescription>
                        </Alert>
                      )}

                      {connectionStatus === 'duplicate' && duplicateInfo && (
                        <Alert className="border-yellow-200 bg-yellow-50">
                          <AlertCircle className="h-4 w-4 text-yellow-600" />
                          <AlertDescription className="text-yellow-800">
                            This PagerDuty account is already connected as "{duplicateInfo.existing_integration}".
                          </AlertDescription>
                        </Alert>
                      )}

                      <div className="flex space-x-3">
                        <Button 
                          type="submit" 
                          disabled={isTestingConnection || !isValidPagerDutyToken(pagerdutyForm.watch('pagerdutyToken') || '')}
                          className="bg-green-600 hover:bg-green-700"
                        >
                          {isTestingConnection ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Testing Connection...
                            </>
                          ) : (
                            <>
                              <Shield className="w-4 h-4 mr-2" />
                              Test Connection
                            </>
                          )}
                        </Button>

                        {connectionStatus === 'success' && previewData?.can_add && (
                          <Button
                            type="button"
                            onClick={() => addIntegration('pagerduty')}
                            disabled={isAdding}
                            className="bg-blue-600 hover:bg-blue-700"
                          >
                            {isAdding ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Adding...
                              </>
                            ) : (
                              <>
                                <Plus className="w-4 h-4 mr-2" />
                                Add Integration
                              </>
                            )}
                          </Button>
                        )}
                      </div>
                    </form>
                  </Form>
                </CardContent>
              </Card>
            )}

            {/* Existing Integrations */}
            {activeTab === null ? (
              <div className="text-center py-12">
                <Shield className="w-12 h-12 mx-auto text-slate-300 mb-4" />
                <p className="text-lg font-medium mb-2 text-slate-700">Choose a platform to get started</p>
                <p className="text-sm text-slate-500">Select Rootly or PagerDuty above to view and manage your integrations</p>
              </div>
            ) : loadingIntegrations ? (
              <Card className="max-w-2xl mx-auto">
                <CardContent className="p-6 space-y-4">
                {/* Skeleton loading cards */}
                {[1, 2].map((i) => (
                  <Card key={i} className="border-gray-200 bg-gray-50 animate-pulse">
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-4">
                            <div className="h-6 bg-gray-300 rounded w-32"></div>
                            <div className="h-5 bg-gray-300 rounded w-20"></div>
                            <div className="h-5 bg-gray-300 rounded w-16"></div>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            {[1, 2, 3, 4, 5].map((j) => (
                              <div key={j} className="flex items-start space-x-2">
                                <div className="w-4 h-4 bg-gray-300 rounded mt-0.5"></div>
                                <div>
                                  <div className="h-4 bg-gray-300 rounded w-20 mb-1"></div>
                                  <div className="h-4 bg-gray-300 rounded w-16"></div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="h-8 bg-gray-300 rounded w-24"></div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                  <div className="text-center py-4">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-slate-400" />
                    <p className="text-sm text-gray-500 mt-2">Loading integrations...</p>
                  </div>
                </CardContent>
              </Card>
            ) : filteredIntegrations.length > 0 ? (
              <Card className="max-w-2xl mx-auto">
                <CardContent className="p-6 space-y-4">
                  {filteredIntegrations.map((integration) => (
                    <div key={integration.id} className={`
                      p-6 rounded-lg border
                      ${integration.platform === 'rootly' ? 'border-green-200 bg-green-50' : 'border-green-200 bg-green-50'}
                    `}>
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            
                            {editingIntegration === integration.id ? (
                              <div className="flex items-center space-x-2">
                                <Input
                                  value={editingName}
                                  onChange={(e) => setEditingName(e.target.value)}
                                  className="h-8 w-48"
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                      updateIntegrationName(integration, editingName)
                                      setEditingIntegration(null)
                                    } else if (e.key === 'Escape') {
                                      setEditingIntegration(null)
                                    }
                                  }}
                                />
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => {
                                    updateIntegrationName(integration, editingName)
                                    setEditingIntegration(null)
                                  }}
                                >
                                  <Check className="w-4 h-4" />
                                </Button>
                              </div>
                            ) : (
                              <div className="flex items-center space-x-2">
                                <h3 className="font-semibold text-lg">{integration.name}</h3>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => {
                                    setEditingIntegration(integration.id)
                                    setEditingName(integration.name)
                                  }}
                                >
                                  <Edit3 className="w-3 h-3" />
                                </Button>
                              </div>
                            )}
                            
                            <Badge variant={integration.platform === 'rootly' ? 'default' : 'secondary'} 
                                   className={integration.platform === 'rootly' ? 'bg-purple-100 text-purple-700' : 'bg-green-100 text-green-700'}>
                              {integration.platform}
                            </Badge>
                            
                            {integration.is_default && (
                              <Badge className="bg-yellow-100 text-yellow-700">
                                <Star className="w-3 h-3 mr-1" />
                                Default
                              </Badge>
                            )}
                          </div>
                          
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
                            <div className="flex items-start space-x-2">
                              <Building className="w-4 h-4 mt-0.5 text-gray-400" />
                              <div>
                                <div className="font-bold text-gray-900">Organization</div>
                                <div className="text-gray-600">{integration.organization_name}</div>
                              </div>
                            </div>
                            <div className="flex items-start space-x-2">
                              <Users className="w-4 h-4 mt-0.5 text-gray-400" />
                              <div>
                                <div className="font-bold text-gray-900">Users</div>
                                <div className="text-gray-600">{integration.total_users}</div>
                              </div>
                            </div>
                            {integration.platform === 'pagerduty' && integration.total_services !== undefined && (
                              <div className="flex items-start space-x-2">
                                <Zap className="w-4 h-4 mt-0.5 text-gray-400" />
                                <div>
                                  <div className="font-bold text-gray-900">Services</div>
                                  <div className="text-gray-600">{integration.total_services}</div>
                                </div>
                              </div>
                            )}
                            <div className="flex items-start space-x-2">
                              <Key className="w-4 h-4 mt-0.5 text-gray-400" />
                              <div>
                                <div className="font-bold text-gray-900">Token</div>
                                <div className="text-gray-600">•••{integration.token_suffix}</div>
                              </div>
                            </div>
                            <div className="flex items-start space-x-2">
                              <Calendar className="w-4 h-4 mt-0.5 text-gray-400" />
                              <div>
                                <div className="font-bold text-gray-900">Added</div>
                                <div className="text-gray-600">{new Date(integration.created_at).toLocaleDateString()}</div>
                              </div>
                            </div>
                            {integration.last_used_at && (
                              <div className="flex items-start space-x-2">
                                <Clock className="w-4 h-4 mt-0.5 text-gray-400" />
                                <div>
                                  <div className="font-bold text-gray-900">Last used</div>
                                  <div className="text-gray-600">{new Date(integration.last_used_at).toLocaleDateString()}</div>
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Permissions for Rootly and PagerDuty */}
                          {integration.permissions && (
                            <div className="mt-3 flex items-center space-x-4 text-sm">
                              <span className="text-gray-500">Read permissions:</span>
                              <div className="flex items-center space-x-1">
                                {integration.permissions.users.access ? (
                                  <Tooltip content="✓ User read permissions: Required to run burnout analysis and identify team members">
                                    <CheckCircle className="w-4 h-4 text-green-500 cursor-help" />
                                  </Tooltip>
                                ) : (
                                  <Tooltip content={`✗ User read permissions required: ${integration.permissions.users.error || "Permission denied"}. Both User and Incident read permissions are required to run burnout analysis.`}>
                                    <AlertCircle className="w-4 h-4 text-red-500 cursor-help" />
                                  </Tooltip>
                                )}
                                <span>Users</span>
                              </div>
                              <div className="flex items-center space-x-1">
                                {integration.permissions.incidents.access ? (
                                  <Tooltip content="✓ Incident read permissions: Required to run burnout analysis and analyze incident response patterns">
                                    <CheckCircle className="w-4 h-4 text-green-500 cursor-help" />
                                  </Tooltip>
                                ) : (
                                  <Tooltip content={`✗ Incident read permissions required: ${integration.permissions.incidents.error || "Permission denied"}. Both User and Incident read permissions are required to run burnout analysis.`}>
                                    <AlertCircle className="w-4 h-4 text-red-500 cursor-help" />
                                  </Tooltip>
                                )}
                                <span>Incidents</span>
                              </div>
                            </div>
                          )}
                        </div>
                        
                        <div className="flex items-center">
                          <Button
                            size="sm"
                            onClick={() => {
                              setIntegrationToDelete(integration)
                              setDeleteDialogOpen(true)
                            }}
                            className="bg-red-100 hover:bg-red-200 text-red-700 border border-red-200"
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Remove Token
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  {/* General Run Analysis Button */}
                  <div className="pt-4 border-t border-gray-200">
                    <Button
                      onClick={() => router.push('/dashboard')}
                      className="w-full bg-purple-600 hover:bg-purple-700 text-white"
                      size="lg"
                    >
                      <Activity className="w-5 h-5 mr-2" />
                      Run Analysis
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <div className="text-center py-12 text-gray-500">
                <Shield className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p className="text-lg font-medium mb-2">No integrations yet</p>
                <p className="text-sm">Add a Rootly or PagerDuty integration to get started!</p>
              </div>
            )}
        </div>
      </main>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Integration</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{integrationToDelete?.name}"? 
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDeleteDialogOpen(false)
                setIntegrationToDelete(null)
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={deleteIntegration}
              disabled={isDeleting}
            >
              {isDeleting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                "Delete Integration"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}