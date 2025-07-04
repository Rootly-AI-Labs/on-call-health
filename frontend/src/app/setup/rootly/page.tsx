"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Input } from "@/components/ui/input"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import {
  Activity,
  ExternalLink,
  Shield,
  CheckCircle,
  AlertCircle,
  Eye,
  EyeOff,
  ArrowLeft,
  ArrowRight,
  Loader2,
  Key,
  Copy,
  Check,
  Plus,
  Building,
  Users,
  Edit3,
  Trash2,
  Star,
  Calendar,
  Clock,
  Settings,
} from "lucide-react"
import Link from "next/link"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useToast } from "@/hooks/use-toast"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const formSchema = z.object({
  rootlyToken: z.string().min(1, "Rootly API token is required"),
})

type FormData = z.infer<typeof formSchema>

interface PreviewData {
  organization_name: string
  suggested_name: string
  total_users: number
  can_add: boolean
}

interface Integration {
  id: number
  name: string
  organization_name: string
  total_users: number
  is_default: boolean
  created_at: string
  last_used_at: string | null
  token_suffix: string
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

export default function RootlySetupPage() {
  // Component state
  const [isShowingToken, setIsShowingToken] = useState(false)
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'error' | 'duplicate'>('idle')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isAdding, setIsAdding] = useState(false)
  const [copied, setCopied] = useState(false)
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [nickname, setNickname] = useState("")
  const [duplicateInfo, setDuplicateInfo] = useState<any>(null)
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loadingIntegrations, setLoadingIntegrations] = useState(true)
  const [editingIntegration, setEditingIntegration] = useState<number | null>(null)
  const [editingName, setEditingName] = useState("")
  const [cameFromDashboard, setCameFromDashboard] = useState(false)
  const router = useRouter()
  const { toast } = useToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      rootlyToken: "",
    },
  })

  // Load existing integrations on component mount
  useEffect(() => {
    loadIntegrations()
    
    // Check if user came from dashboard
    const referrer = document.referrer
    if (referrer && referrer.includes('/dashboard')) {
      setCameFromDashboard(true)
    }
  }, [])

  const loadIntegrations = async () => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      const response = await fetch(`${API_BASE}/rootly/integrations`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setIntegrations(data.integrations)
      }
    } catch (error) {
      console.error('Failed to load integrations:', error)
    } finally {
      setLoadingIntegrations(false)
    }
  }

  const checkIntegrationPermissions = async (integrationId: number, token: string) => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return null

      const response = await fetch(`${API_BASE}/rootly/token/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          token: token
        })
      })

      if (response.ok) {
        const data = await response.json()
        return data.account_info?.permissions || null
      }
    } catch (error) {
      console.error('Failed to check permissions:', error)
    }
    return null
  }

  const updateIntegrationName = async (integrationId: number, newName: string) => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      const response = await fetch(`${API_BASE}/rootly/integrations/${integrationId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          name: newName
        })
      })

      if (response.ok) {
        toast({
          title: "Integration updated",
          description: `Integration renamed to '${newName}'`,
        })
        await loadIntegrations() // Reload the list
        setEditingIntegration(null)
        
        // If we were updating a duplicate, reset the form
        if (connectionStatus === 'duplicate') {
          form.reset()
          setConnectionStatus('idle')
          setPreviewData(null)
          setDuplicateInfo(null)
          setNickname("")
        }
      } else {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to update integration')
      }
    } catch (error) {
      toast({
        title: "Update failed",
        description: error instanceof Error ? error.message : "Failed to update integration",
        variant: "destructive",
      })
    }
  }

  const deleteIntegration = async (integrationId: number, integrationName: string) => {
    if (!confirm(`Are you sure you want to revoke the integration '${integrationName}'? This action cannot be undone.`)) {
      return
    }

    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      const response = await fetch(`${API_BASE}/rootly/integrations/${integrationId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        toast({
          title: "Integration revoked",
          description: `'${integrationName}' has been removed from your account`,
        })
        await loadIntegrations() // Reload the list
      } else {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to delete integration')
      }
    } catch (error) {
      toast({
        title: "Delete failed",
        description: error instanceof Error ? error.message : "Failed to delete integration",
        variant: "destructive",
      })
    }
  }

  const handleTestConnection = async () => {
    const values = form.getValues()
    
    if (!values.rootlyToken) {
      toast({
        title: "Missing information",
        description: "Please fill in the API token before testing.",
        variant: "destructive",
      })
      return
    }

    setIsTestingConnection(true)
    setConnectionStatus('idle')
    setPreviewData(null)
    setDuplicateInfo(null)

    try {
      // Get auth token for backend API call
      const authToken = localStorage.getItem('auth_token')
      
      if (!authToken) {
        throw new Error('No authentication token found')
      }

      // Test the token connection
      const response = await fetch(`${API_BASE}/rootly/token/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          token: values.rootlyToken,
        }),
      })

      const responseData = await response.json()

      if (response.ok) {
        if (responseData.status === 'duplicate_token') {
          setConnectionStatus('duplicate')
          setDuplicateInfo(responseData.existing_integration)
          setNickname(responseData.existing_integration.name) // Pre-populate with current name
          toast({
            title: "Token already connected",
            description: `This token is already connected as '${responseData.existing_integration.name}'. You can rename it below.`,
            variant: "destructive",
          })
        } else if (responseData.status === 'success') {
          setConnectionStatus('success')
          setPreviewData(responseData.preview)
          setNickname(responseData.preview.suggested_name)
          toast({
            title: "Connection successful!",
            description: "Your Rootly API token is working correctly.",
          })
        }
      } else {
        throw new Error(`HTTP ${response.status}: ${responseData.message || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Rootly connection test error:', error)
      setConnectionStatus('error')
      
      let errorMessage = "Unable to connect to Rootly. Please check your API token."
      if (error instanceof Error) {
        if (error.message.includes('No authentication token found')) {
          errorMessage = "Please log in again - your session has expired."
        } else if (error.message.includes('fetch')) {
          errorMessage = "Network error. Please check if the backend server is running."
        }
      }
      
      toast({
        title: "Connection failed",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setIsTestingConnection(false)
    }
  }

  const handleAddIntegration = async () => {
    const values = form.getValues()
    
    if (!previewData || !nickname.trim()) {
      toast({
        title: "Missing information", 
        description: "Please enter a nickname for this integration.",
        variant: "destructive",
      })
      return
    }

    setIsAdding(true)

    try {
      const authToken = localStorage.getItem('auth_token')
      
      if (!authToken) {
        throw new Error('No authentication token found')
      }

      const response = await fetch(`${API_BASE}/rootly/token/add`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          token: values.rootlyToken,
          name: nickname.trim(),
        }),
      })

      const responseData = await response.json()

      if (response.ok) {
        toast({
          title: "Integration added!",
          description: `${nickname} has been successfully connected.`,
        })
        // Reset form and reload integrations
        form.reset()
        setConnectionStatus('idle')
        setPreviewData(null)
        setNickname("")
        await loadIntegrations()
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

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy: ', err)
    }
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-purple-100 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Image
              src="/images/rootly-logo.svg"
              alt="Rootly"
              width={120}
              height={35}
              className="h-8 w-auto"
            />
            <div>
              <span className="text-xl font-bold text-slate-900">Burnout Detector</span>
              <Badge variant="secondary" className="ml-2 text-xs bg-purple-100 text-purple-700">
                Setup
              </Badge>
            </div>
          </div>

          <Link href={cameFromDashboard || integrations.length > 0 ? "/dashboard" : "/auth/success"}>
            <Button variant="ghost" size="sm" className="flex items-center space-x-2 hover:bg-purple-50">
              <ArrowLeft className="w-4 h-4" />
              <span>{cameFromDashboard || integrations.length > 0 ? "Back to Dashboard" : "Back"}</span>
            </Button>
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-12">
        <div className="max-w-2xl mx-auto">
          {/* Progress indicator */}
          <div className="flex items-center justify-center mb-8">
            <div className="flex items-center space-x-4">
              <div className="flex items-center justify-center w-8 h-8 bg-purple-600 text-white rounded-full text-sm font-semibold">
                1
              </div>
              <div className="w-16 h-0.5 bg-purple-200"></div>
              <div className="flex items-center justify-center w-8 h-8 bg-purple-600 text-white rounded-full text-sm font-semibold">
                2
              </div>
            </div>
          </div>

          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-white border-2 border-purple-200 rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm">
              <Key className="w-8 h-8 text-purple-600" />
            </div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Manage Rootly Integrations</h1>
            <p className="text-slate-600 text-lg">Connect and manage your Rootly organizations for burnout analysis</p>
          </div>

          {/* Instructions Card */}
          <Card className="border-2 border-purple-200 bg-white/70 backdrop-blur-sm shadow-lg mb-8">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Key className="w-5 h-5 text-purple-600" />
                <span>Getting Your Rootly API Token</span>
              </CardTitle>
              <CardDescription>
                Follow these steps to generate your API token in Rootly
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-start space-x-3">
                  <div className="flex items-center justify-center w-6 h-6 bg-purple-100 text-purple-600 rounded-full text-sm font-semibold flex-shrink-0 mt-0.5">
                    1
                  </div>
                  <div>
                    <p className="text-sm text-slate-700">
                      Go to your Rootly dashboard and navigate to{" "}
                      <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono">
                        Configuration → API Keys
                      </code>
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="flex items-center justify-center w-6 h-6 bg-purple-100 text-purple-600 rounded-full text-sm font-semibold flex-shrink-0 mt-0.5">
                    2
                  </div>
                  <div>
                    <p className="text-sm text-slate-700">
                      Click "Generate New API Key" in the top right
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="flex items-center justify-center w-6 h-6 bg-purple-100 text-purple-600 rounded-full text-sm font-semibold flex-shrink-0 mt-0.5">
                    3
                  </div>
                  <div>
                    <p className="text-sm text-slate-700">
                      Give it a name like "Burnout Detector" and set appropriate permissions (read access to incidents and users)
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="flex items-center justify-center w-6 h-6 bg-purple-100 text-purple-600 rounded-full text-sm font-semibold flex-shrink-0 mt-0.5">
                    4
                  </div>
                  <div>
                    <p className="text-sm text-slate-700">
                      Copy the generated token and paste it below
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Form */}
          <Card className="border-2 border-purple-200 bg-white shadow-lg mb-8">
            <CardHeader>
              <CardTitle>Add New Integration</CardTitle>
              <CardDescription>
                Connect another Rootly organization to your account
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <div className="space-y-6">
                  <FormField
                    control={form.control}
                    name="rootlyToken"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Rootly API Token</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Input
                              {...field}
                              type={isShowingToken ? "text" : "password"}
                              placeholder="Enter your Rootly API token"
                              className="pr-20"
                            />
                            <div className="absolute inset-y-0 right-0 flex items-center space-x-1 pr-3">
                              {field.value && (
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 w-7 p-0 hover:bg-slate-100"
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
                                className="h-7 w-7 p-0 hover:bg-slate-100"
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
                          Your API token will be stored securely and only used to fetch incident data
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />


                  {/* Test Connection */}
                  <div className="flex space-x-3">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleTestConnection}
                      disabled={isTestingConnection || !form.watch('rootlyToken')}
                      className="flex-1"
                    >
                      {isTestingConnection ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Testing...
                        </>
                      ) : (
                        <>
                          <Shield className="w-4 h-4 mr-2" />
                          Test Connection
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Connection Status Messages */}
                  {connectionStatus === 'error' && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        Unable to connect to Rootly. Please check your API token.
                      </AlertDescription>
                    </Alert>
                  )}

                  {connectionStatus === 'duplicate' && duplicateInfo && (
                    <Card className="border-yellow-200 bg-yellow-50">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-lg flex items-center space-x-2">
                          <AlertCircle className="w-5 h-5 text-yellow-600" />
                          <span>Token Already Connected</span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-slate-600">Current Name:</span>
                            <p className="font-semibold text-slate-900">{duplicateInfo.name}</p>
                          </div>
                          <div>
                            <span className="text-slate-600">Organization:</span>
                            <p className="font-semibold text-slate-900">{duplicateInfo.organization_name}</p>
                          </div>
                        </div>
                        
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-slate-700 flex items-center space-x-1">
                            <Edit3 className="w-4 h-4" />
                            <span>Update Integration Name</span>
                          </label>
                          <Input
                            value={nickname}
                            onChange={(e) => setNickname(e.target.value)}
                            placeholder="Enter a new name for this integration"
                            className="w-full"
                          />
                          <p className="text-xs text-slate-600">
                            You can rename this existing integration instead of adding a duplicate.
                          </p>
                        </div>

                        <Button
                          onClick={() => updateIntegrationName(duplicateInfo.id, nickname)}
                          disabled={!nickname.trim() || nickname === duplicateInfo.name}
                          className="w-full bg-gradient-to-r from-yellow-600 to-orange-500 hover:from-yellow-700 hover:to-orange-600 text-white"
                        >
                          <Edit3 className="w-4 h-4 mr-2" />
                          Update Integration Name
                        </Button>
                      </CardContent>
                    </Card>
                  )}

                  {/* Preview Section */}
                  {connectionStatus === 'success' && previewData && (
                    <div className="space-y-4">
                      <Alert>
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <AlertDescription className="text-green-700">
                          Connection successful! Your API token is working correctly.
                        </AlertDescription>
                      </Alert>

                      <Card className="border-green-200 bg-green-50">
                        <CardHeader className="pb-3">
                          <CardTitle className="text-lg flex items-center space-x-2">
                            <Building className="w-5 h-5 text-green-600" />
                            <span>Ready to Add Integration</span>
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="text-slate-600">Organization:</span>
                              <p className="font-semibold text-slate-900">{previewData.organization_name}</p>
                            </div>
                            <div>
                              <span className="text-slate-600">Team Size:</span>
                              <p className="font-semibold text-slate-900 flex items-center">
                                <Users className="w-4 h-4 mr-1" />
                                {previewData.total_users} users
                              </p>
                            </div>
                          </div>

                          <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700 flex items-center space-x-1">
                              <Edit3 className="w-4 h-4" />
                              <span>Integration Name</span>
                            </label>
                            <Input
                              value={nickname}
                              onChange={(e) => setNickname(e.target.value)}
                              placeholder="Enter a name for this integration"
                              className="w-full"
                            />
                            <p className="text-xs text-slate-600">
                              This name will help you identify this Rootly organization in your dashboard.
                            </p>
                          </div>

                          <Button
                            onClick={handleAddIntegration}
                            disabled={isAdding || !nickname.trim()}
                            className="w-full bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-700 hover:to-emerald-600 text-white"
                          >
                            {isAdding ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Adding Integration...
                              </>
                            ) : (
                              <>
                                <Plus className="w-4 h-4 mr-2" />
                                Add Integration
                              </>
                            )}
                          </Button>
                        </CardContent>
                      </Card>
                    </div>
                  )}
                </div>
              </Form>
            </CardContent>
          </Card>

          {/* Connected Integrations */}
          <Card className="border-2 border-green-200 bg-white shadow-lg mb-8">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Settings className="w-5 h-5 text-green-600" />
                <span>Connected Integrations</span>
                {!loadingIntegrations && integrations.length > 0 && (
                  <Badge variant="secondary" className="ml-auto">
                    {integrations.length} active
                  </Badge>
                )}
              </CardTitle>
              <CardDescription>
                {loadingIntegrations 
                  ? "Loading connected integrations..."
                  : integrations.length > 0 
                    ? "Manage your connected Rootly organizations"
                    : "Add at least one Rootly integration to continue"
                }
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {loadingIntegrations ? (
                // Skeleton loaders while loading
                <>
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="p-4 border border-green-200 rounded-lg bg-green-50 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="w-6 h-6 bg-gray-200 rounded animate-pulse"></div>
                          <div className="space-y-2">
                            <div className="w-32 h-4 bg-gray-200 rounded animate-pulse"></div>
                            <div className="w-24 h-3 bg-gray-200 rounded animate-pulse"></div>
                          </div>
                        </div>
                        <div className="flex space-x-2">
                          <div className="w-16 h-8 bg-gray-200 rounded animate-pulse"></div>
                          <div className="w-16 h-8 bg-gray-200 rounded animate-pulse"></div>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <div className="w-20 h-6 bg-gray-200 rounded animate-pulse"></div>
                        <div className="w-24 h-6 bg-gray-200 rounded animate-pulse"></div>
                      </div>
                    </div>
                  ))}
                </>
              ) : integrations.length > 0 ? (
                  integrations.map((integration) => (
                  <div
                    key={integration.id}
                    className="p-4 border border-green-200 rounded-lg bg-green-50 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        {editingIntegration === integration.id ? (
                          <div className="flex items-center space-x-2 flex-1">
                            <Input
                              value={editingName}
                              onChange={(e) => setEditingName(e.target.value)}
                              className="flex-1"
                              onKeyPress={(e) => {
                                if (e.key === 'Enter') {
                                  updateIntegrationName(integration.id, editingName)
                                }
                              }}
                            />
                            <Button
                              size="sm"
                              onClick={() => updateIntegrationName(integration.id, editingName)}
                              disabled={!editingName.trim()}
                            >
                              <Check className="w-4 h-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setEditingIntegration(null)
                                setEditingName("")
                              }}
                            >
                              ✕
                            </Button>
                          </div>
                        ) : (
                          <>
                            <div className="flex items-center space-x-2">
                              <Building className="w-5 h-5 text-green-600" />
                              <div>
                                <div className="flex items-center space-x-2">
                                  <span className="font-semibold text-slate-900">
                                    {integration.name}
                                  </span>
                                  {integration.is_default && (
                                    <Star className="w-4 h-4 text-yellow-500 fill-current" />
                                  )}
                                </div>
                                <p className="text-sm text-slate-600">
                                  {integration.organization_name}
                                </p>
                                <p className="text-xs text-slate-500 mt-1 font-mono">
                                  API Key: {integration.token_suffix}
                                </p>
                                
                                {/* Permissions Display */}
                                {integration.permissions && (
                                  <div className="mt-2 space-y-1">
                                    <p className="text-xs font-semibold text-slate-700 mb-1">Permissions:</p>
                                    <div className="flex flex-wrap gap-1">
                                      <div className="flex items-center space-x-1">
                                        {integration.permissions.users.access ? (
                                          <CheckCircle className="w-3 h-3 text-green-600" />
                                        ) : (
                                          <AlertCircle className="w-3 h-3 text-red-600" />
                                        )}
                                        <span className="text-xs text-slate-600">Users</span>
                                      </div>
                                      <div className="flex items-center space-x-1">
                                        {integration.permissions.incidents.access ? (
                                          <CheckCircle className="w-3 h-3 text-green-600" />
                                        ) : (
                                          <AlertCircle className="w-3 h-3 text-red-600" />
                                        )}
                                        <span className="text-xs text-slate-600">Incidents</span>
                                      </div>
                                    </div>
                                    
                                    {/* Show errors if any */}
                                    {(!integration.permissions.users.access && integration.permissions.users.error) && (
                                      <p className="text-xs text-red-600 mt-1">Users: {integration.permissions.users.error}</p>
                                    )}
                                    {(!integration.permissions.incidents.access && integration.permissions.incidents.error) && (
                                      <p className="text-xs text-red-600 mt-1">Incidents: {integration.permissions.incidents.error}</p>
                                    )}
                                    
                                    {/* Overall permission status */}
                                    {integration.permissions && (
                                      <div className="mt-2 flex items-center space-x-2">
                                        {integration.permissions.users.access && integration.permissions.incidents.access ? (
                                          <div className="flex items-center space-x-1">
                                            <CheckCircle className="w-3 h-3 text-green-600" />
                                            <span className="text-xs text-green-700 font-medium">All permissions granted</span>
                                          </div>
                                        ) : (
                                          <div className="flex items-center space-x-1">
                                            <AlertCircle className="w-3 h-3 text-orange-600" />
                                            <span className="text-xs text-orange-700 font-medium">Limited permissions</span>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          </>
                        )}
                      </div>
                      
                      {editingIntegration !== integration.id && (
                        <div className="flex items-center space-x-2">
                          <div className="text-right text-sm text-slate-600">
                            <div className="flex items-center space-x-1">
                              <Users className="w-3 h-3" />
                              <span>{integration.total_users} users</span>
                            </div>
                            <div className="flex items-center space-x-1">
                              <Calendar className="w-3 h-3" />
                              <span>Added {new Date(integration.created_at).toLocaleDateString()}</span>
                            </div>
                          </div>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => loadIntegrations()}
                            title="Refresh permissions"
                          >
                            <Settings className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              setEditingIntegration(integration.id)
                              setEditingName(integration.name)
                            }}
                          >
                            <Edit3 className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={() => deleteIntegration(integration.id, integration.name)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                  ))
                ) : (
                  <div className="text-center py-8">
                    <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Building className="w-8 h-8 text-slate-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">No Integrations Yet</h3>
                    <p className="text-slate-600 mb-4">
                      Use the form above to test and add your first Rootly integration.
                    </p>
                    <p className="text-sm text-slate-500">
                      You'll need at least one connected integration to proceed to the dashboard.
                    </p>
                  </div>
                )}

                {/* Continue Button - only show when there are integrations */}
                {integrations.length > 0 && (
                  <div className="pt-4 border-t border-green-200">
                    <Button
                      onClick={() => router.push('/dashboard')}
                      className="w-full bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-700 hover:to-emerald-600 text-white"
                    >
                      Continue to Dashboard
                      <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

          {/* Security Note */}
          <div className="mt-8 p-4 bg-purple-50 rounded-lg border border-purple-200">
            <div className="flex items-start space-x-3">
              <Shield className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-purple-900 mb-1">Data Security & Privacy</h3>
                <p className="text-sm text-purple-700 leading-relaxed">
                  Your API token is encrypted and stored securely. We only access incident metadata to calculate burnout metrics - no sensitive incident details are stored or shared. You can revoke access at any time from your Rootly settings.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}