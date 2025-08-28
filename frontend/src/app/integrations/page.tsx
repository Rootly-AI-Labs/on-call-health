"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
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
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
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
  TestTube,
  RotateCcw,
  BarChart3,
  Database,
  Users2,
  RefreshCw,
  X,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  LogOut,
} from "lucide-react"
import Link from "next/link"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { useBackendHealth } from "@/hooks/use-backend-health"
import { MappingDrawer } from "@/components/mapping-drawer"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"

interface IntegrationMapping {
  id: number | string // Can be number or "manual_123" for manual mappings
  source_platform: string
  source_identifier: string
  source_name?: string  // User's full name from analysis data
  target_platform: string
  target_identifier: string | null
  mapping_successful: boolean
  mapping_method: string | null
  error_message: string | null
  data_collected: boolean
  data_points_count: number | null
  created_at: string
  mapping_key: string
  // New properties for manual mappings
  is_manual?: boolean
  source?: 'integration' | 'manual'
  mapping_type?: string
  status?: string
  confidence_score?: number
  last_verified?: string
}

interface MappingStatistics {
  overall_success_rate: number
  total_attempts: number
  mapped_members?: number
  members_with_data?: number
  manual_mappings_count?: number
  github_was_enabled?: boolean | null
  platform_breakdown: {
    [key: string]: {
      total_attempts: number
      successful: number
      failed: number
      success_rate: number
    }
  }
}

// New interface for analysis-specific mapping statistics
interface AnalysisMappingStatistics {
  total_team_members: number
  successful_mappings: number
  members_with_data: number
  success_rate: number
  failed_mappings: number
}

interface ManualMapping {
  id: number
  source_platform: string
  source_identifier: string
  target_platform: string
  target_identifier: string
  mapping_type: string
  confidence_score?: number
  last_verified?: string
  created_at: string
  updated_at?: string
  status: string
  is_verified: boolean
  mapping_key: string
}

interface ManualMappingStatistics {
  total_mappings: number
  manual_mappings: number
  auto_detected_mappings: number
  verified_mappings: number
  verification_rate: number
  platform_breakdown: { [key: string]: { [key: string]: number } }
  last_updated?: string
}

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

interface GitHubIntegration {
  id: number | string // Can be "beta-github" for beta integration
  github_username: string
  organizations: string[]
  token_source: "oauth" | "manual" | "beta"
  is_oauth: boolean
  supports_refresh: boolean
  connected_at: string
  last_updated: string
  is_beta?: boolean // Optional flag for beta integrations
  token_preview?: string // Token preview for display
}

interface SlackIntegration {
  id: number
  slack_user_id: string
  workspace_id: string
  token_source: "oauth" | "manual"
  is_oauth: boolean
  supports_refresh: boolean
  has_webhook: boolean
  webhook_configured: boolean
  connected_at: string
  last_updated: string
  total_channels?: number
  channel_names?: string[]
  token_preview?: string
  webhook_preview?: string
}

interface PreviewData {
  organization_name: string
  total_users: number
  total_services?: number
  suggested_name?: string
  can_add?: boolean
  current_user?: string
  permissions?: {
    users?: {
      access: boolean
      error?: string
    }
    incidents?: {
      access: boolean
      error?: string
    }
  }
}

export default function IntegrationsPage() {
  // State management
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loadingRootly, setLoadingRootly] = useState(true)
  const [loadingPagerDuty, setLoadingPagerDuty] = useState(true) 
  const [loadingGitHub, setLoadingGitHub] = useState(true)
  const [loadingSlack, setLoadingSlack] = useState(true)
  const [userInfo, setUserInfo] = useState<{name: string, email: string, avatar?: string} | null>(null)
  const [activeTab, setActiveTab] = useState<"rootly" | "pagerduty" | null>(null)
  const [backUrl, setBackUrl] = useState<string>('/dashboard')
  const [selectedOrganization, setSelectedOrganization] = useState<string>("")
  
  // GitHub/Slack integration state
  const [githubIntegration, setGithubIntegration] = useState<GitHubIntegration | null>(null)
  const [slackIntegration, setSlackIntegration] = useState<SlackIntegration | null>(null)
  const [activeEnhancementTab, setActiveEnhancementTab] = useState<"github" | "slack" | null>(null)
  
  // Mapping data state
  const [showMappingDialog, setShowMappingDialog] = useState(false)
  const [selectedMappingPlatform, setSelectedMappingPlatform] = useState<'github' | 'slack' | null>(null)
  
  // MappingDrawer state (reusable component)
  const [mappingDrawerOpen, setMappingDrawerOpen] = useState(false)
  const [mappingDrawerPlatform, setMappingDrawerPlatform] = useState<'github' | 'slack'>('github')
  const [mappingData, setMappingData] = useState<IntegrationMapping[]>([])
  const [mappingStats, setMappingStats] = useState<MappingStatistics | null>(null)
  const [analysisMappingStats, setAnalysisMappingStats] = useState<AnalysisMappingStatistics | null>(null)
  const [currentAnalysisId, setCurrentAnalysisId] = useState<number | null>(null)
  const [loadingMappingData, setLoadingMappingData] = useState(false)
  const [inlineEditingId, setInlineEditingId] = useState<number | string | null>(null)
  const [inlineEditingValue, setInlineEditingValue] = useState('')
  const [savingInlineMapping, setSavingInlineMapping] = useState(false)
  const [validatingGithub, setValidatingGithub] = useState(false)
  const [githubValidation, setGithubValidation] = useState<{valid: boolean, message?: string} | null>(null)
  
  // Sorting state
  const [sortField, setSortField] = useState<'email' | 'status' | 'data' | 'method'>('email')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [showOnlyFailed, setShowOnlyFailed] = useState(false)
  
  // Manual mapping state
  const [showManualMappingDialog, setShowManualMappingDialog] = useState(false)
  const [manualMappings, setManualMappings] = useState<ManualMapping[]>([])
  const [manualMappingStats, setManualMappingStats] = useState<ManualMappingStatistics | null>(null)
  const [selectedManualMappingPlatform, setSelectedManualMappingPlatform] = useState<'github' | 'slack' | null>(null)
  const [loadingManualMappings, setLoadingManualMappings] = useState(false)
  const [newMappingDialogOpen, setNewMappingDialogOpen] = useState(false)
  const [editingMapping, setEditingMapping] = useState<ManualMapping | null>(null)
  const [newMappingForm, setNewMappingForm] = useState({
    source_platform: 'rootly' as string,
    source_identifier: '',
    target_platform: 'github' as string,
    target_identifier: ''
  })
  const [githubToken, setGithubToken] = useState('')
  const [slackWebhookUrl, setSlackWebhookUrl] = useState('')
  const [slackBotToken, setSlackBotToken] = useState('')
  const [showGithubInstructions, setShowGithubInstructions] = useState(false)
  const [showSlackInstructions, setShowSlackInstructions] = useState(false)
  const [showGithubToken, setShowGithubToken] = useState(false)
  const [showSlackWebhook, setShowSlackWebhook] = useState(false)
  const [showSlackToken, setShowSlackToken] = useState(false)
  const [isConnectingGithub, setIsConnectingGithub] = useState(false)
  const [isConnectingSlack, setIsConnectingSlack] = useState(false)
  
  // Disconnect confirmation state
  const [githubDisconnectDialogOpen, setGithubDisconnectDialogOpen] = useState(false)
  const [slackDisconnectDialogOpen, setSlackDisconnectDialogOpen] = useState(false)
  const [isDisconnectingGithub, setIsDisconnectingGithub] = useState(false)
  const [isDisconnectingSlack, setIsDisconnectingSlack] = useState(false)
  const [slackPermissions, setSlackPermissions] = useState<any>(null)
  const [isLoadingPermissions, setIsLoadingPermissions] = useState(false)
  
  // AI Integration state
  const [llmToken, setLlmToken] = useState('')
  const [llmModel, setLlmModel] = useState('gpt-4o-mini')
  const [llmProvider, setLlmProvider] = useState('openai')
  const [showLlmToken, setShowLlmToken] = useState(false)
  const [isConnectingAI, setIsConnectingAI] = useState(false)
  const [llmConfig, setLlmConfig] = useState<{has_token: boolean, provider?: string, token_suffix?: string} | null>(null)
  const [loadingLlmConfig, setLoadingLlmConfig] = useState(true)
  const [tokenError, setTokenError] = useState<string | null>(null)
  
  // Add integration state
  const [addingPlatform, setAddingPlatform] = useState<"rootly" | "pagerduty" | null>(null)
  const [isShowingToken, setIsShowingToken] = useState(false)
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'error' | 'duplicate'>('idle')
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [duplicateInfo, setDuplicateInfo] = useState<any>(null)
  const [isAddingRootly, setIsAddingRootly] = useState(false)
  const [isAddingPagerDuty, setIsAddingPagerDuty] = useState(false)
  const [copied, setCopied] = useState(false)
  
  // Edit/Delete state
  const [editingIntegration, setEditingIntegration] = useState<number | null>(null)
  const [editingName, setEditingName] = useState("")
  const [savingIntegrationId, setSavingIntegrationId] = useState<number | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [integrationToDelete, setIntegrationToDelete] = useState<Integration | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  
  // Instructions state
  const [showRootlyInstructions, setShowRootlyInstructions] = useState(false)
  const [showPagerDutyInstructions, setShowPagerDutyInstructions] = useState(false)
  
  const router = useRouter()
  
  // Backend health monitoring - temporarily disabled
  // const { isHealthy } = useBackendHealth({
  //   showToasts: true,
  //   autoStart: true,
  // })
  
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
    // ✨ PHASE 1 OPTIMIZATION: Re-enabled with API endpoint fixes
    console.log('✨ PHASE 1 RE-ENABLED: Using optimized loading with correct API endpoints')
    loadAllIntegrationsOptimized()
    
    // 🚨 ROLLBACK: Individual loading functions (fallback disabled)
    // loadRootlyIntegrations()
    // loadPagerDutyIntegrations() 
    // loadGitHubIntegration()
    // loadSlackIntegration()
    loadLlmConfig()
    
    // Load saved organization preference
    const savedOrg = localStorage.getItem('selected_organization')
    if (savedOrg) {
      setSelectedOrganization(savedOrg)
    }
    
    // Load user info from localStorage
    const userName = localStorage.getItem('user_name')
    const userEmail = localStorage.getItem('user_email')
    const userAvatar = localStorage.getItem('user_avatar')
    
    console.log('Debug: User info from localStorage:', { 
      userName, 
      userEmail, 
      userAvatar,
      userNameType: typeof userName,
      userEmailType: typeof userEmail,
      userNameTruthy: !!userName,
      userEmailTruthy: !!userEmail
    })
    
    // Check for valid, non-empty strings (not "null", "undefined", or empty)
    const validUserName = userName && userName !== 'null' && userName !== 'undefined' && userName.trim() !== ''
    const validUserEmail = userEmail && userEmail !== 'null' && userEmail !== 'undefined' && userEmail.trim() !== ''
    
    if (validUserName && validUserEmail) {
      setUserInfo({
        name: userName,
        email: userEmail,
        avatar: (userAvatar && userAvatar !== 'null' && userAvatar !== 'undefined') ? userAvatar : undefined
      })
      console.log('Debug: User info set:', { name: userName, email: userEmail, avatar: userAvatar })
    } else {
      console.log('Debug: No valid user info found in localStorage', { 
        validUserName, 
        validUserEmail, 
        userName, 
        userEmail 
      })
      
      // Try to fetch user info from API as fallback
      const authToken = localStorage.getItem('auth_token')
      if (authToken) {
        console.log('Debug: Attempting to fetch user info from API')
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        fetch(`${API_BASE}/auth/user/me`, {
          headers: { 
            'Authorization': `Bearer ${authToken}`,
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache'
          }
        })
        .then(response => response.json())
        .then(userData => {
          console.log('Debug: User data from API:', userData)
          if (userData.name && userData.email) {
            setUserInfo({
              name: userData.name,
              email: userData.email,
              avatar: userData.avatar || undefined
            })
            // Store in localStorage for future use
            localStorage.setItem('user_name', userData.name)
            localStorage.setItem('user_email', userData.email)
            if (userData.avatar) {
              localStorage.setItem('user_avatar', userData.avatar)
            }
          }
        })
        .catch(error => {
          console.log('Debug: Failed to fetch user info from API:', error)
        })
      }
    }
    
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
      // For first-time users or direct access, start without back button
      // Will be updated based on integration status
      setBackUrl('')
    }
  }, [])

  // Load Slack permissions when integration is available
  useEffect(() => {
    if (slackIntegration && activeEnhancementTab === 'slack') {
      loadSlackPermissions()
    }
  }, [slackIntegration, activeEnhancementTab])

  // Load each provider independently for better UX
  const loadRootlyIntegrations = async (forceRefresh = false) => {
    // Check cache first
    if (!forceRefresh) {
      const cachedIntegrations = localStorage.getItem('all_integrations')
      if (cachedIntegrations) {
        try {
          const parsed = JSON.parse(cachedIntegrations)
          const rootlyIntegrations = parsed.filter((i: Integration) => i.platform === 'rootly')
          setIntegrations(prev => [
            ...prev.filter(i => i.platform !== 'rootly'),
            ...rootlyIntegrations
          ])
          setLoadingRootly(false)
          return
        } catch (e) {}
      }
    }

    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      const response = await fetch(`${API_BASE}/rootly/integrations`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })

      const data = response.ok ? await response.json() : { integrations: [] }
      const rootlyIntegrations = data.integrations.map((i: Integration) => ({ ...i, platform: 'rootly' }))

      setIntegrations(prev => [
        ...prev.filter(i => i.platform !== 'rootly'),
        ...rootlyIntegrations
      ])
    } catch (error) {
      console.error('Error loading Rootly integrations:', error)
    } finally {
      setLoadingRootly(false)
    }
  }

  const loadPagerDutyIntegrations = async (forceRefresh = false) => {
    // Check cache first
    if (!forceRefresh) {
      const cachedIntegrations = localStorage.getItem('all_integrations')
      if (cachedIntegrations) {
        try {
          const parsed = JSON.parse(cachedIntegrations)
          const pagerdutyIntegrations = parsed.filter((i: Integration) => i.platform === 'pagerduty')
          setIntegrations(prev => [
            ...prev.filter(i => i.platform !== 'pagerduty'),
            ...pagerdutyIntegrations
          ])
          setLoadingPagerDuty(false)
          return
        } catch (e) {}
      }
    }

    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      const response = await fetch(`${API_BASE}/pagerduty/integrations`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })

      const data = response.ok ? await response.json() : { integrations: [] }
      const pagerdutyIntegrations = data.integrations || []

      setIntegrations(prev => [
        ...prev.filter(i => i.platform !== 'pagerduty'),
        ...pagerdutyIntegrations
      ])
    } catch (error) {
      console.error('Error loading PagerDuty integrations:', error)
    } finally {
      setLoadingPagerDuty(false)
    }
  }

  const loadGitHubIntegration = async (forceRefresh = false) => {
    if (!forceRefresh) {
      const cached = localStorage.getItem('github_integration')
      if (cached) {
        try {
          const githubData = JSON.parse(cached)
          setGithubIntegration(githubData.connected ? githubData.integration : null)
          setLoadingGitHub(false)
          return
        } catch (e) {}
      }
    }

    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      const response = await fetch(`${API_BASE}/integrations/github/status`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })

      const githubData = response.ok ? await response.json() : { connected: false, integration: null }
      setGithubIntegration(githubData.connected ? githubData.integration : null)
      localStorage.setItem('github_integration', JSON.stringify(githubData))
    } catch (error) {
      console.error('Error loading GitHub integration:', error)
    } finally {
      setLoadingGitHub(false)
    }
  }

  const loadSlackIntegration = async (forceRefresh = false) => {
    if (!forceRefresh) {
      const cached = localStorage.getItem('slack_integration')
      if (cached) {
        try {
          const slackData = JSON.parse(cached)
          setSlackIntegration(slackData.integration)
          setLoadingSlack(false)
          return
        } catch (e) {}
      }
    }

    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      const response = await fetch(`${API_BASE}/integrations/slack/status`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })

      const slackData = response.ok ? await response.json() : { integration: null }
      setSlackIntegration(slackData.integration)
      localStorage.setItem('slack_integration', JSON.stringify(slackData))
    } catch (error) {
      console.error('Error loading Slack integration:', error)
    } finally {
      setLoadingSlack(false)
    }
  }

  // ✨ PHASE 1 OPTIMIZATION: Instant cache loading with background refresh
  const [refreshingInBackground, setRefreshingInBackground] = useState(false)
  
  // Synchronous cache reading for instant display
  const loadFromCacheSync = () => {
    try {
      console.log('🚀 DEBUG: Reading cache from localStorage')
      const cachedIntegrations = localStorage.getItem('all_integrations')
      const cachedGithub = localStorage.getItem('github_integration')
      const cachedSlack = localStorage.getItem('slack_integration')
      
      console.log('🚀 DEBUG: Cache items found:', {
        cachedIntegrations: !!cachedIntegrations,
        cachedGithub: !!cachedGithub,
        cachedSlack: !!cachedSlack
      })
      
      if (cachedIntegrations) {
        const parsedIntegrations = JSON.parse(cachedIntegrations)
        setIntegrations(parsedIntegrations)
        console.log('✨ INSTANT CACHE: Loaded', parsedIntegrations.length, 'integrations immediately')
      }
      
      if (cachedGithub) {
        const githubData = JSON.parse(cachedGithub)
        setGithubIntegration(githubData.connected ? githubData.integration : null)
        console.log('🚀 DEBUG: Loaded GitHub cache')
      }
      
      if (cachedSlack) {
        const slackData = JSON.parse(cachedSlack)
        setSlackIntegration(slackData.integration)
        console.log('🚀 DEBUG: Loaded Slack cache')
      }
      
      const hasAllCache = !!(cachedIntegrations && cachedGithub && cachedSlack)
      console.log('🚀 DEBUG: Has all cache?', hasAllCache)
      return hasAllCache
    } catch (error) {
      console.error('🚀 DEBUG: Error loading cache:', error)
      return false
    }
  }
  
  // Background refresh function (non-blocking) - does NOT affect loading states
  const refreshInBackground = async () => {
    setRefreshingInBackground(true)
    try {
      console.log('🚀 DEBUG: Background refresh starting (no loading state changes)')
      await loadAllIntegrationsAPIBackground()
      console.log('✨ BACKGROUND REFRESH: Completed')
    } catch (error) {
      console.error('Background refresh failed:', error)
    } finally {
      setRefreshingInBackground(false)
    }
  }

  // Background API loading - does NOT change loading states (for silent refresh)
  const loadAllIntegrationsAPIBackground = async () => {
    console.log('🚀 DEBUG: loadAllIntegrationsAPIBackground starting (no skeleton changes)')
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        console.log('🚀 DEBUG: No auth token, skipping background refresh')
        return
      }

      const [rootlyResponse, pagerdutyResponse, githubResponse, slackResponse] = await Promise.all([
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

      const [rootlyData, pagerdutyData, githubData, slackData] = await Promise.all([
        rootlyResponse.ok ? rootlyResponse.json() : { integrations: [] },
        pagerdutyResponse.ok ? pagerdutyResponse.json() : { integrations: [] },
        githubResponse.ok ? githubResponse.json() : { connected: false, integration: null },
        slackResponse.ok ? slackResponse.json() : { integration: null }
      ])

      // Update state silently
      const allIntegrations = [
        ...rootlyData.integrations.map((i: any) => ({ ...i, platform: 'rootly' })),
        ...pagerdutyData.integrations.map((i: any) => ({ ...i, platform: 'pagerduty' }))
      ]

      setIntegrations(allIntegrations)
      setGithubIntegration(githubData.connected ? githubData.integration : null)
      setSlackIntegration(slackData.integration)

      // Update cache with fresh data
      localStorage.setItem('all_integrations', JSON.stringify(allIntegrations))
      localStorage.setItem('all_integrations_timestamp', Date.now().toString())
      localStorage.setItem('github_integration', JSON.stringify(githubData))
      localStorage.setItem('slack_integration', JSON.stringify(slackData))

      console.log('🚀 DEBUG: Background refresh completed, cache updated')
    } catch (error) {
      console.error('🚀 DEBUG: Error in background refresh:', error)
    }
  }
  
  // Check if cache is stale (older than 5 minutes)
  const isCacheStale = () => {
    const cacheTimestamp = localStorage.getItem('all_integrations_timestamp')
    if (!cacheTimestamp) return true
    
    const cacheAge = Date.now() - parseInt(cacheTimestamp)
    const maxCacheAge = 5 * 60 * 1000 // 5 minutes
    return cacheAge > maxCacheAge
  }
  
  // New optimized loading function with instant cache + background refresh
  const loadAllIntegrationsOptimized = async (forceRefresh = false) => {
    console.log('🚀 DEBUG: Starting optimized integration loading, forceRefresh=', forceRefresh)
    
    try {
      // Step 1: Always show cached data instantly (0ms)
      console.log('🚀 DEBUG: Calling loadFromCacheSync()')
      const hasCachedData = loadFromCacheSync()
      console.log('🚀 DEBUG: hasCachedData =', hasCachedData)
      
      // Step 2: If we have cached data and it's not forced refresh, show it immediately
      if (hasCachedData && !forceRefresh) {
        console.log('🚀 DEBUG: Has cached data, setting loading states to false')
        setLoadingRootly(false) // Hide skeleton immediately
        setLoadingPagerDuty(false)
        setLoadingGitHub(false)
        setLoadingSlack(false)
        
        // Step 3: Check if cache is stale and refresh in background if needed
        const cacheIsStale = isCacheStale()
        console.log('🚀 DEBUG: Cache is stale?', cacheIsStale)
        if (cacheIsStale) {
          console.log('✨ CACHE STALE: Starting background refresh')
          // Non-blocking background refresh
          setTimeout(() => refreshInBackground(), 100)
        } else {
          console.log('✨ CACHE FRESH: No refresh needed')
        }
        return
      }
      
      // Step 4: If no cache or forced refresh, fall back to normal loading
      console.log('🚀 DEBUG: No cache or forced refresh, calling loadAllIntegrationsAPI()')
      await loadAllIntegrationsAPI()
      console.log('🚀 DEBUG: loadAllIntegrationsAPI() completed')
    } catch (error) {
      console.error('🚀 DEBUG: Error in loadAllIntegrationsOptimized:', error)
      // Fallback: set loading states to false to prevent infinite loading
      setLoadingRootly(false)
      setLoadingPagerDuty(false)
      setLoadingGitHub(false)
      setLoadingSlack(false)
    }
  }
  
  // Original API loading logic (extracted for reuse)
  const loadAllIntegrationsAPI = async () => {
    console.log('🚀 DEBUG: loadAllIntegrationsAPI starting')
    // Set individual loading states to true
    setLoadingRootly(true)
    setLoadingPagerDuty(true)
    setLoadingGitHub(true)
    setLoadingSlack(true)
    console.log('🚀 DEBUG: Set all loading states to true')
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        router.push('/auth/success')
        return
      }

      const [rootlyResponse, pagerdutyResponse, githubResponse, slackResponse] = await Promise.all([
        fetch(`${API_BASE}/rootly/integrations`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        }),
        fetch(`${API_BASE}/pagerduty/integrations`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        }),
        fetch(`${API_BASE}/integrations/github/status`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        }).catch(() => ({ ok: false })),
        fetch(`${API_BASE}/integrations/slack/status`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        }).catch(() => ({ ok: false }))
      ])

      const rootlyData = rootlyResponse.ok ? await rootlyResponse.json() : { integrations: [] }
      const pagerdutyData = pagerdutyResponse.ok ? await pagerdutyResponse.json() : { integrations: [] }
      const githubData = (githubResponse as Response).ok ? await (githubResponse as Response).json() : { connected: false, integration: null }
      const slackData = (slackResponse as Response).ok ? await (slackResponse as Response).json() : { integration: null }

      const rootlyIntegrations = rootlyData.integrations.map((i: Integration) => ({ ...i, platform: 'rootly' }))
      const pagerdutyIntegrations = pagerdutyData.integrations || []

      const allIntegrations = [...rootlyIntegrations, ...pagerdutyIntegrations]
      setIntegrations(allIntegrations)
      setGithubIntegration(githubData.connected ? githubData.integration : null)
      setSlackIntegration(slackData.integration)
      
      // Cache the integrations (same as dashboard caching)
      localStorage.setItem('all_integrations', JSON.stringify(allIntegrations))
      localStorage.setItem('all_integrations_timestamp', Date.now().toString())
      
      // Cache GitHub and Slack integration status separately
      localStorage.setItem('github_integration', JSON.stringify(githubData))
      localStorage.setItem('slack_integration', JSON.stringify(slackData))
      
      // Update back URL based on integration status
      if (backUrl === '') {
        // If user has no integrations, this is onboarding - don't show back button
        // If user has integrations, they're managing them - show back to dashboard
        if (allIntegrations.length > 0) {
          setBackUrl('/dashboard')
        }
        // Otherwise keep backUrl empty to hide the back button
      }
    } catch (error) {
      console.error('🚀 DEBUG: Error in loadAllIntegrationsAPI:', error)
      toast.error("Failed to load integrations. Please try refreshing the page.")
    } finally {
      console.log('🚀 DEBUG: loadAllIntegrationsAPI finally block - setting loading states to false')
      // Set all integration loading states to false
      setLoadingRootly(false)
      setLoadingPagerDuty(false)
      setLoadingGitHub(false)
      setLoadingSlack(false)
      console.log('🚀 DEBUG: All loading states set to false')
    }
  }

  const loadLlmConfig = async () => {
    setLoadingLlmConfig(true)
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        return
      }

      const response = await fetch(`${API_BASE}/llm/token`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        const config = await response.json()
        setLlmConfig(config)
        if (config.provider) {
          setLlmProvider(config.provider)
          setLlmModel(config.provider === 'openai' ? 'gpt-4o-mini' : 'claude-3-haiku')
        }
      }
    } catch (error) {
      console.error('Failed to load LLM config:', error)
    } finally {
      setLoadingLlmConfig(false)
    }
  }

  const handleConnectAI = async () => {
    if (!llmToken.trim()) {
      setTokenError("Please enter your LLM API token")
      toast.error("Please enter your LLM API token")
      return
    }

    setIsConnectingAI(true)
    setTokenError(null) // Clear any previous errors
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        throw new Error('No authentication token found')
      }

      const response = await fetch(`${API_BASE}/llm/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          token: llmToken,
          provider: llmProvider
        })
      })

      if (response.ok) {
        const result = await response.json()
        setLlmConfig({
          has_token: true,
          provider: result.provider,
          token_suffix: result.token_suffix
        })
        setLlmToken('')
        setTokenError(null) // Clear any errors on success
        toast.success(`Successfully connected ${result.provider} ${llmModel}`)
      } else {
        const error = await response.json()
        const errorDetail = error.detail || 'Failed to connect AI'
        
        // Provide specific feedback based on error type
        let title = "Connection Failed"
        let description = errorDetail
        
        if (errorDetail.includes('format')) {
          title = "Invalid Token Format"
          description = `${llmProvider === 'openai' ? 'OpenAI' : 'Anthropic'} tokens must start with "${llmProvider === 'openai' ? 'sk-' : 'sk-ant-api'}"`
        } else if (errorDetail.includes('verification failed') || errorDetail.includes('check your')) {
          title = "Invalid API Token"
          description = `The ${llmProvider === 'openai' ? 'OpenAI' : 'Anthropic'} token appears to be invalid or expired. Please verify your token and try again.`
        } else if (errorDetail.includes('connect')) {
          title = "Connection Error"
          description = `Unable to connect to ${llmProvider === 'openai' ? 'OpenAI' : 'Anthropic'} API. Please check your internet connection and try again.`
        }
        
        throw new Error(description)
      }
    } catch (error) {
      console.error('Failed to connect AI:', error)
      const errorMessage = error.message || "Failed to connect to AI service"
      
      // Determine toast title based on error content
      let toastTitle = "Connection Failed"
      if (errorMessage.includes('Invalid Token Format') || errorMessage.includes('must start with')) {
        toastTitle = "Invalid Token Format"
      } else if (errorMessage.includes('invalid or expired') || errorMessage.includes('verify your token')) {
        toastTitle = "Invalid API Token"
      } else if (errorMessage.includes('Connection Error') || errorMessage.includes('internet connection')) {
        toastTitle = "Connection Error"
      }
      
      // Set the error on the input field as well
      setTokenError(errorMessage)
      
      toast.error(errorMessage)
    } finally {
      setIsConnectingAI(false)
    }
  }

  const handleDisconnectAI = async () => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        throw new Error('No authentication token found')
      }

      const response = await fetch(`${API_BASE}/llm/token`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        setLlmConfig({has_token: false})
        toast.success("LLM token removed successfully")
      } else {
        throw new Error('Failed to disconnect AI')
      }
    } catch (error) {
      console.error('Failed to disconnect AI:', error)
      toast.error("Failed to disconnect AI service")
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
            permissions: data.account_info?.permissions
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
    
    // Set service-specific loading state
    if (platform === 'rootly') {
      setIsAddingRootly(true)
    } else {
      setIsAddingPagerDuty(true)
    }
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        throw new Error('No authentication token found')
      }

      const form = platform === 'rootly' ? rootlyForm : pagerdutyForm
      const values = form.getValues()
      const token = platform === 'rootly' ? (values as any).rootlyToken : (values as any).pagerdutyToken
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
        toast.success(`Your ${platform === 'rootly' ? 'Rootly' : 'PagerDuty'} account has been connected successfully.`)
        
        // Clear local storage cache
        localStorage.removeItem(`${platform}_integrations`)
        localStorage.removeItem(`${platform}_integrations_timestamp`)
        localStorage.removeItem('all_integrations')
        localStorage.removeItem('all_integrations_timestamp')
        
        // If this is the first integration, set it as selected for dashboard
        try {
          const newIntegrationId = responseData.integration?.id || responseData.id
          if (newIntegrationId && integrations.length === 0) {
            localStorage.setItem('selected_organization', newIntegrationId.toString())
          }
        } catch (error) {
          console.error('Error setting default integration:', error)
          // Continue without setting default - not critical
        }
        
        // Reset form and state
        form.reset()
        setConnectionStatus('idle')
        setPreviewData(null)
        setAddingPlatform(null)
        
        // Reload integrations to show the newly added one
        if (platform === 'rootly') {
          await loadRootlyIntegrations(true)
        } else {
          await loadPagerDutyIntegrations(true)
        }
      } else {
        throw new Error(responseData.detail?.message || responseData.message || 'Failed to add integration')
      }
    } catch (error) {
      console.error('Add integration error:', error)
      toast.error(error instanceof Error ? error.message : "An unexpected error occurred.")
    } finally {
      // Reset service-specific loading state
      if (platform === 'rootly') {
        setIsAddingRootly(false)
      } else {
        setIsAddingPagerDuty(false)
      }
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
        toast.success("The integration has been removed.")
        
        // Optimized: Update local state directly instead of full reload
        const updatedIntegrations = integrations.filter(i => i.id !== integrationToDelete.id)
        setIntegrations(updatedIntegrations)
        
        // Update cache with filtered results
        localStorage.setItem('all_integrations', JSON.stringify(updatedIntegrations))
        localStorage.setItem('all_integrations_timestamp', Date.now().toString())
        
        // Clear platform-specific cache
        localStorage.removeItem(`${integrationToDelete.platform}_integrations`)
        localStorage.removeItem(`${integrationToDelete.platform}_integrations_timestamp`)
        
        // If we deleted the currently selected integration, clear the selection
        const selectedOrg = localStorage.getItem('selected_organization')
        if (selectedOrg === integrationToDelete.id.toString()) {
          localStorage.removeItem('selected_organization')
        }
        
        setDeleteDialogOpen(false)
        setIntegrationToDelete(null)
      } else {
        throw new Error('Failed to delete integration')
      }
    } catch (error) {
      console.error('Delete error:', error)
      toast.error("An error occurred while deleting the integration.")
    } finally {
      setIsDeleting(false)
    }
  }

  const updateIntegrationName = async (integration: Integration, newName: string) => {
    setSavingIntegrationId(integration.id)
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
        toast.success("Integration name has been updated.")
        
        // Update the integration in state without reloading everything
        setIntegrations(prevIntegrations => 
          prevIntegrations.map(int => 
            int.id === integration.id 
              ? { ...int, name: newName }
              : int
          )
        )
        
        // Clear cache to ensure next full reload has fresh data
        localStorage.removeItem('all_integrations')
        localStorage.removeItem('all_integrations_timestamp')
      }
    } catch (error) {
      console.error('Error updating name:', error)
      toast.error("Could not update integration name.")
    } finally {
      setSavingIntegrationId(null)
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

  // GitHub integration handlers
  const handleGitHubConnect = async (token: string) => {
    setIsConnectingGithub(true)
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        throw new Error('No authentication token found')
      }

      const response = await fetch(`${API_BASE}/integrations/github/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ token })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to connect GitHub')
      }

      toast.success("Your GitHub account has been connected successfully.")
      
      setGithubToken('')
      setActiveEnhancementTab(null)
      loadGitHubIntegration(true) // Force refresh to update cache
    } catch (error) {
      console.error('Error connecting GitHub:', error)
      toast.error(error instanceof Error ? error.message : "An unexpected error occurred.")
    } finally {
      setIsConnectingGithub(false)
    }
  }

  const handleGitHubDisconnect = async () => {
    setIsDisconnectingGithub(true)
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      const response = await fetch(`${API_BASE}/integrations/github/disconnect`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        toast.success("Your GitHub integration has been removed.")
        setGithubDisconnectDialogOpen(false)
        loadGitHubIntegration(true) // Force refresh after changes
      }
    } catch (error) {
      console.error('Error disconnecting GitHub:', error)
      toast.error(error instanceof Error ? error.message : "An unexpected error occurred.")
    } finally {
      setIsDisconnectingGithub(false)
    }
  }

  const handleGitHubTest = async () => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        toast.error("Please log in to test your GitHub integration.")
        return
      }

      toast.info("Testing GitHub connection...")

      const response = await fetch(`${API_BASE}/github/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        // Show permissions info if available
        if (data.permissions) {
          const missingPerms = []
          if (!data.permissions.repo_access) missingPerms.push('repository access')
          if (!data.permissions.org_access) missingPerms.push('organization access')
          
          if (missingPerms.length > 0) {
            toast.warning(`✅ Connected as ${data.user_info?.username || 'GitHub user'}, but missing: ${missingPerms.join(', ')}`)
          } else {
            toast.success(`✅ GitHub test successful! Connected as ${data.user_info?.username || 'GitHub user'} with full access.`)
          }
        } else {
          toast.success(`✅ GitHub test successful! Connected as ${data.user_info?.username || 'GitHub user'}. Integration is working properly.`)
        }
      } else {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Connection test failed')
      }
    } catch (error) {
      console.error('Error testing GitHub connection:', error)
      toast.error(`❌ GitHub test failed: ${error instanceof Error ? error.message : "Unable to test GitHub connection."}`)
    }
  }

  // Slack integration handlers
  const handleSlackConnect = async (webhookUrl: string, botToken: string) => {
    setIsConnectingSlack(true)
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        throw new Error('No authentication token found')
      }

      const response = await fetch(`${API_BASE}/integrations/slack/setup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ 
          webhook_url: webhookUrl,
          token: botToken 
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to connect Slack')
      }

      toast.success("Your Slack workspace has been connected successfully.")
      
      setSlackWebhookUrl('')
      setSlackBotToken('')
      setActiveEnhancementTab(null)
      loadSlackIntegration(true)
    } catch (error) {
      console.error('Error connecting Slack:', error)
      toast.error(error instanceof Error ? error.message : "An unexpected error occurred.")
    } finally {
      setIsConnectingSlack(false)
    }
  }

  const handleSlackDisconnect = async () => {
    setIsDisconnectingSlack(true)
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      const response = await fetch(`${API_BASE}/integrations/slack/disconnect`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        toast.success("Your Slack integration has been removed.")
        setSlackDisconnectDialogOpen(false)
        loadSlackIntegration(true) // Force refresh after changes
      }
    } catch (error) {
      console.error('Error disconnecting Slack:', error)
      toast.error(error instanceof Error ? error.message : "An unexpected error occurred.")
    } finally {
      setIsDisconnectingSlack(false)
    }
  }

  const handleSlackTest = async () => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        toast.error("Please log in to test your Slack integration.")
        return
      }

      toast.info("Testing Slack connection...")

      const response = await fetch(`${API_BASE}/integrations/slack/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        console.log('Full Slack test response:', data)
        setSlackPermissions(data.permissions)
        
        // Store channels list if available
        if (data.channels) {
          setSlackIntegration(prev => prev ? {...prev, channels: data.channels} : null)
        }
        
        const workspaceName = data.workspace_info?.team_name || 'your workspace'
        const userName = data.user_info?.name || 'Slack user'
        
        toast.success(`✅ Slack test successful! Connected as ${userName} in ${workspaceName}. Permissions updated.`)
      } else {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Connection test failed')
      }
    } catch (error) {
      console.error('Error testing Slack connection:', error)
      toast.error(`❌ Slack test failed: ${error instanceof Error ? error.message : "Unable to test Slack connection."}`)
    }
  }

  const loadSlackPermissions = async () => {
    if (!slackIntegration) return
    
    setIsLoadingPermissions(true)
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) return

      const response = await fetch(`${API_BASE}/integrations/slack/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        console.log('Slack permissions API response:', data)
        console.log('Permissions object:', data.permissions)
        setSlackPermissions(data.permissions)
      }
    } catch (error) {
      console.error('Error loading Slack permissions:', error)
    } finally {
      setIsLoadingPermissions(false)
    }
  }

  // Mapping data handlers
  // Function to open the reusable MappingDrawer
  const openMappingDrawer = (platform: 'github' | 'slack') => {
    console.log(`🎯 Integrations: openMappingDrawer called with platform: ${platform}`)
    setMappingDrawerPlatform(platform)
    setMappingDrawerOpen(true)
  }

  const loadMappingData = async (platform: 'github' | 'slack') => {
    console.log('🔴 loadMappingData called with platform:', platform)
    setLoadingMappingData(true)
    setSelectedMappingPlatform(platform)
    
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        console.error('🔴 No auth token found')
        toast.error('Please log in to view mapping data')
        return
      }

      // Use the existing working endpoints
      console.log(`🔍 DEBUG: Fetching mapping data for platform: ${platform}`)
      console.log(`🔍 DEBUG: API URLs:`, {
        mappings: `${API_BASE}/integrations/mappings/platform/${platform}`,
        stats: `${API_BASE}/integrations/mappings/success-rate?platform=${platform}`
      })
      
      const [mappingsResponse, statsResponse] = await Promise.all([
        fetch(`${API_BASE}/integrations/mappings/platform/${platform}`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        }),
        fetch(`${API_BASE}/integrations/mappings/success-rate?platform=${platform}`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        })
      ])

      console.log('🔍 API Response statuses:', {
        mappings: mappingsResponse.status,
        stats: statsResponse.status
      })

      if (mappingsResponse.ok && statsResponse.ok) {
        const mappings = await mappingsResponse.json()
        const stats = await statsResponse.json()
        
        const failedMappings = mappings.filter(m => !m.target_identifier)
        const successfulMappings = mappings.filter(m => m.target_identifier)
        
        console.log(`🔍 DEBUG: Received data for ${platform}:`, {
          mappings: mappings.length,
          stats: stats,
          failed_mappings: failedMappings.length,
          successful_mappings: successfulMappings.length,
          sample_failed: failedMappings.slice(0, 2).map(m => ({
            email: m.source_identifier,
            target: m.target_identifier,
            successful: m.mapping_successful,
            error: m.error_message
          })),
          sample_successful: successfulMappings.slice(0, 2).map(m => ({
            email: m.source_identifier,
            target: m.target_identifier,
            successful: m.mapping_successful
          }))
        })
        
        setMappingData(mappings)
        setMappingStats(stats)
        setAnalysisMappingStats(null)
        setCurrentAnalysisId(null)
        setShowMappingDialog(true)
        
        console.log('🔍 Successfully set all state, opening dialog')
        
        // Show success message only if dialog is already open (refresh action)
        if (showMappingDialog) {
          toast.success(`${platform === 'github' ? 'GitHub' : 'Slack'} mapping data refreshed successfully`)
        }
      } else {
        console.error('🔴 API responses not OK:', {
          mappingsStatus: mappingsResponse.status,
          statsStatus: statsResponse.status,
          mappingsText: await mappingsResponse.text().catch(() => 'Could not read response'),
          statsText: await statsResponse.text().catch(() => 'Could not read response')
        })
        throw new Error(`Failed to fetch mapping data - Mappings: ${mappingsResponse.status}, Stats: ${statsResponse.status}`)
      }
    } catch (error) {
      console.error('🔴 Error loading mapping data:', error)
      toast.error(`Failed to load mapping data: ${error.message}`)
    } finally {
      console.log('🔍 Setting loadingMappingData to false')
      setLoadingMappingData(false)
    }
  }

  // Inline mapping edit handlers
  const startInlineEdit = (mappingId: number | string, currentValue: string = '') => {
    // Don't allow editing of manual mappings inline since they already exist
    if (typeof mappingId === 'string' && mappingId.startsWith('manual_')) {
      toast.error('Manual mappings cannot be edited. They are already mapped.')
      return
    }
    setInlineEditingId(mappingId)
    setInlineEditingValue(currentValue)
    setGithubValidation(null)
  }
  
  // Validate GitHub username
  const validateGithubUsername = async (username: string) => {
    if (!username.trim()) {
      setGithubValidation({ valid: false, message: 'Username cannot be empty' })
      return false
    }
    
    setValidatingGithub(true)
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        setGithubValidation({ valid: false, message: 'Not authenticated' })
        return false
      }
      
      const response = await fetch(`${API_BASE}/integrations/mappings/github/validate/${encodeURIComponent(username.trim())}`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })
      
      const data = await response.json()
      console.log('🔍 GitHub validation response:', {
        status: response.status,
        data: data,
        url: response.url
      })
      
      if (response.ok && data.valid) {
        setGithubValidation({ valid: true, message: `Found: ${data.name || data.username}` })
        return true
      } else {
        const errorMsg = data.message || data.error || `API Error (${response.status})`
        setGithubValidation({ valid: false, message: errorMsg })
        console.error('❌ GitHub validation failed:', errorMsg)
        return false
      }
    } catch (error) {
      console.error('Error validating GitHub username:', error)
      setGithubValidation({ valid: false, message: 'Validation failed' })
      return false
    } finally {
      setValidatingGithub(false)
    }
  }
  
  // Sorting function
  const handleSort = (field: 'email' | 'status' | 'data' | 'method') => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }
  
  // Filter and sort mappings
  const filteredMappings = showOnlyFailed 
    ? mappingData.filter(m => !m.mapping_successful)
    : mappingData
    
  const sortedMappings = [...filteredMappings].sort((a, b) => {
    let aValue: any, bValue: any
    
    switch (sortField) {
      case 'email':
        aValue = a.source_identifier.toLowerCase()
        bValue = b.source_identifier.toLowerCase()
        break
      case 'status':
        aValue = a.mapping_successful ? 1 : 0
        bValue = b.mapping_successful ? 1 : 0
        break
      case 'data':
        aValue = a.data_points_count || 0
        bValue = b.data_points_count || 0
        break
      case 'method':
        aValue = a.mapping_method || ''
        bValue = b.mapping_method || ''
        break
    }
    
    if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1
    if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1
    return 0
  })

  const cancelInlineEdit = () => {
    setInlineEditingId(null)
    setInlineEditingValue('')
    setGithubValidation(null)
  }

  const startEditExisting = (mappingId: number | string, currentValue: string) => {
    setInlineEditingId(mappingId)
    setInlineEditingValue(currentValue)
    setGithubValidation(null)
  }

  const saveEditedMapping = async (mappingId: number | string, email: string) => {
    if (!inlineEditingValue.trim()) {
      toast.error('Please enter a valid username')
      return
    }
    
    const authToken = localStorage.getItem('auth_token')
    if (!authToken) {
      toast.error('Please log in to edit mappings')
      return
    }
    
    // Validate GitHub username first (for both manual and auto mappings)
    if (selectedMappingPlatform === 'github') {
      if (!githubValidation || githubValidation.valid !== true) {
        const isValid = await validateGithubUsername(inlineEditingValue)
        if (!isValid) {
          toast.error(`Invalid GitHub username: ${githubValidation?.message || 'User not found'}`, {
            duration: 4000
          })
          return
        }
      }
    }
    
    // Handle manual mappings differently (use UserMapping endpoint during migration period)
    if (typeof mappingId === 'string' && mappingId.startsWith('manual_')) {
      // Extract the numeric ID from "manual_123" format
      const numericId = parseInt(mappingId.replace('manual_', ''))
      
      setSavingInlineMapping(true)
      try {
        // Use the manual mappings endpoint instead
        const response = await fetch(`${API_BASE}/integrations/manual-mappings/${numericId}`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            target_identifier: inlineEditingValue.trim()
          })
        })

        if (response.ok) {
          const result = await response.json()
          toast.success(`Successfully updated manual mapping to '${inlineEditingValue}'`)
          
          // Update the local mapping data
          setMappingData(prevData => 
            prevData.map(m => 
              m.id === mappingId 
                ? { ...m, target_identifier: inlineEditingValue.trim(), mapping_successful: true }
                : m
            )
          )
          
          // Clear editing state
          setInlineEditingId(null)
          setInlineEditingValue('')
          setGithubValidation(null)
          return
        } else {
          const errorData = await response.json()
          toast.error(errorData.detail || 'Failed to update manual mapping')
          return
        }
      } catch (error) {
        console.error('Manual mapping edit error:', error)
        toast.error('Failed to update manual mapping')
        return
      } finally {
        setSavingInlineMapping(false)
      }
    }

    setSavingInlineMapping(true)
    try {

      const response = await fetch(`${API_BASE}/integrations/mappings/${mappingId}/edit?new_target_identifier=${encodeURIComponent(inlineEditingValue.trim())}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const result = await response.json()
        toast.success(result.message || `Successfully updated mapping to '${inlineEditingValue}'`)
        
        // Update the local mapping data
        setMappingData(prevData => 
          prevData.map(m => 
            m.id === mappingId 
              ? { 
                  ...m, 
                  target_identifier: inlineEditingValue.trim(),
                  mapping_successful: true,
                  is_manual: true,  // It becomes manual after editing
                  source: 'manual',
                  mapping_method: 'manual_edit',
                  last_updated: new Date().toISOString()
                } 
              : m
          )
        )
        
        // Clear editing state
        setInlineEditingId(null)
        setInlineEditingValue('')
        setGithubValidation(null)
      } else {
        const errorData = await response.json()
        toast.error(errorData.message || 'Failed to update mapping')
      }
    } catch (error) {
      console.error('Error updating mapping:', error)
      toast.error('Failed to update mapping')
    } finally {
      setSavingInlineMapping(false)
    }
  }
  
  // Handle inline value change with debounced validation
  const handleInlineValueChange = (value: string) => {
    setInlineEditingValue(value)
    setGithubValidation(null) // Clear previous validation
    
    // Debounce validation
    if (value.trim() && selectedMappingPlatform === 'github') {
      const timeoutId = setTimeout(() => {
        validateGithubUsername(value)
      }, 500)
      
      return () => clearTimeout(timeoutId)
    }
  }

  const saveInlineMapping = async (mappingId: number | string, email: string) => {
    // Skip manual mappings - they can't be edited inline as they already exist
    if (typeof mappingId === 'string' && mappingId.startsWith('manual_')) {
      toast.error('Manual mappings cannot be edited inline')
      return
    }
    if (!inlineEditingValue.trim()) {
      toast.error('Please enter a GitHub username')
      return
    }
    
    // Validate GitHub username first
    if (selectedMappingPlatform === 'github') {
      // If we haven't validated yet or validation failed, validate now
      if (!githubValidation || githubValidation.valid !== true) {
        const isValid = await validateGithubUsername(inlineEditingValue)
        if (!isValid) {
          toast.error(`Invalid GitHub username: ${githubValidation?.message || 'User not found'}`, {
            duration: 4000
          })
          return
        }
      }
    }

    setSavingInlineMapping(true)
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        toast.error('Please log in to save mappings')
        return
      }

      const response = await fetch(`${API_BASE}/integrations/manual-mappings`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          source_platform: 'rootly',
          source_identifier: email,
          target_platform: selectedMappingPlatform,
          target_identifier: inlineEditingValue.trim()
        })
      })

      if (response.ok) {
        toast.success(`Manual mapping saved: ${email} → ${inlineEditingValue}`)
        
        // Update the local mapping data to show the change immediately
        setMappingData(prevData => 
          prevData.map(m => 
            m.id === mappingId 
              ? { 
                  ...m, 
                  target_identifier: inlineEditingValue.trim(),
                  mapping_successful: true,
                  error_message: null,
                  mapping_method: 'manual'
                }
              : m
          )
        )
        
        // Reset inline editing state
        setInlineEditingId(null)
        setInlineEditingValue('')
        
        // Note: The manual mapping is saved but won't show in IntegrationMapping 
        // until the next analysis is run
        toast.info('Manual mapping saved. Run a new analysis to use this mapping.', {
          duration: 5000
        })
      } else {
        const error = await response.json()
        toast.error(`Failed to save mapping: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Error saving manual mapping:', error)
      toast.error('Failed to save mapping')
    } finally {
      setSavingInlineMapping(false)
    }
  }

  // Manual mapping handlers
  const loadManualMappings = async (platform: 'github' | 'slack') => {
    try {
      setLoadingManualMappings(true)
      setSelectedManualMappingPlatform(platform)
      
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        toast.error('Please log in to view manual mappings')
        return
      }
      
      const [mappingsResponse, statsResponse] = await Promise.all([
        fetch(`${API_BASE}/integrations/manual-mappings?target_platform=${platform}`, {
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          }
        }),
        fetch(`${API_BASE}/integrations/manual-mappings/statistics`, {
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          }
        })
      ])
      
      if (mappingsResponse.ok && statsResponse.ok) {
        const mappingsData = await mappingsResponse.json()
        const statsData = await statsResponse.json()
        
        setManualMappings(mappingsData)
        setManualMappingStats(statsData)
        setShowManualMappingDialog(true)
      } else {
        toast.error('Failed to load manual mappings')
      }
    } catch (error) {
      console.error('Error loading manual mappings:', error)
      toast.error('Failed to load manual mappings')
    } finally {
      setLoadingManualMappings(false)
    }
  }

  const createManualMapping = async () => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        toast.error('Please log in to create mappings')
        return
      }

      const response = await fetch(`${API_BASE}/integrations/manual-mappings`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newMappingForm)
      })
      
      if (response.ok) {
        toast.success('Manual mapping created successfully')
        // Reload mappings if dialog is open
        if (showManualMappingDialog && selectedManualMappingPlatform) {
          loadManualMappings(selectedManualMappingPlatform)
        }
        setNewMappingDialogOpen(false)
        setNewMappingForm({
          source_platform: 'rootly',
          source_identifier: '',
          target_platform: selectedManualMappingPlatform || 'github',
          target_identifier: ''
        })
      } else {
        const errorData = await response.json()
        toast.error(errorData.detail || 'Failed to create mapping')
      }
    } catch (error) {
      console.error('Error creating manual mapping:', error)
      toast.error('Failed to create mapping')
    }
  }

  const updateManualMapping = async (mappingId: number, targetIdentifier: string) => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        toast.error('Please log in to update mappings')
        return
      }

      const response = await fetch(`${API_BASE}/integrations/manual-mappings/${mappingId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ target_identifier: targetIdentifier })
      })
      
      if (response.ok) {
        toast.success('Manual mapping updated successfully')
        // Reload mappings
        if (showManualMappingDialog && selectedManualMappingPlatform) {
          loadManualMappings(selectedManualMappingPlatform)
        }
        setEditingMapping(null)
      } else {
        const errorData = await response.json()
        toast.error(errorData.detail || 'Failed to update mapping')
      }
    } catch (error) {
      console.error('Error updating manual mapping:', error)
      toast.error('Failed to update mapping')
    }
  }

  const deleteManualMapping = async (mappingId: number) => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
        toast.error('Please log in to delete mappings')
        return
      }

      const response = await fetch(`${API_BASE}/integrations/manual-mappings/${mappingId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      })
      
      if (response.ok) {
        toast.success('Manual mapping deleted successfully')
        // Reload mappings
        if (showManualMappingDialog && selectedManualMappingPlatform) {
          loadManualMappings(selectedManualMappingPlatform)
        }
      } else {
        const errorData = await response.json()
        toast.error(errorData.detail || 'Failed to delete mapping')
      }
    } catch (error) {
      console.error('Error deleting manual mapping:', error)
      toast.error('Failed to delete mapping')
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
          <div className="flex items-center space-x-4">
            {backUrl && (
              <Link href={backUrl}>
                <Button variant="ghost" size="sm" className="flex items-center space-x-2">
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back</span>
                </Button>
              </Link>
            )}
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold text-slate-900">Manage Integrations</h1>
              
              {/* ✨ PHASE 1: Background refresh indicator */}
              {refreshingInBackground && (
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  <span className="text-xs text-blue-600 font-medium">Refreshing...</span>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center">
            {/* User Account Indicator */}
            {userInfo ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <div className="flex items-center space-x-3 px-3 py-1 bg-slate-50/80 rounded-full border border-slate-200 hover:bg-slate-100 cursor-pointer transition-colors">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={userInfo.avatar} alt={userInfo.name} />
                      <AvatarFallback className="bg-purple-600 text-white text-xs">
                        {userInfo.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="hidden sm:block text-left">
                      <div className="text-sm font-medium text-slate-900">{userInfo.name}</div>
                      <div className="text-xs text-slate-500">{userInfo.email}</div>
                    </div>
                  </div>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuItem disabled className="px-2 py-1.5">
                    <div>
                      <div className="font-medium text-gray-900">{userInfo.name}</div>
                      <div className="text-xs text-gray-500">{userInfo.email}</div>
                    </div>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    className="text-red-600 hover:text-red-700 hover:bg-red-50 px-2 py-1.5 cursor-pointer"
                    onClick={() => {
                      // Clear all user data
                      localStorage.clear();
                      // Redirect to home page
                      window.location.href = '/';
                    }}
                  >
                    <LogOut className="w-4 h-4 mr-2" />
                    Sign Out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <div className="flex items-center space-x-2 px-3 py-1 bg-slate-50/80 rounded-full border border-slate-200">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-gray-400 text-white text-xs">
                    ?
                  </AvatarFallback>
                </Avatar>
                <div className="hidden sm:block text-left">
                  <div className="text-sm font-medium text-slate-900">Loading...</div>
                  <div className="text-xs text-slate-500">User info</div>
                </div>
              </div>
            )}
          </div>
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
        {(loadingRootly || loadingPagerDuty) ? (
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
          {/* Rootly Card */}
          {loadingRootly ? (
            <Card className="border-2 border-gray-200 p-8 flex items-center justify-center relative h-32 animate-pulse">
                <div className="absolute top-4 right-4 w-6 h-6 bg-gray-300 rounded"></div>
                <div className="h-12 w-48 bg-gray-300 rounded"></div>
            </Card>
          ) : (
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
                  <>
                    <div className="absolute top-4 left-4">
                      <CheckCircle className="w-6 h-6 text-purple-600" />
                    </div>
                    <div className="absolute top-4 right-4">
                      <Badge variant="secondary" className="bg-purple-100 text-purple-700">{rootlyCount}</Badge>
                    </div>
                  </>
                )}
                {activeTab !== 'rootly' && rootlyCount > 0 && (
                  <Badge variant="secondary" className="absolute top-4 right-4">{rootlyCount}</Badge>
                )}
                <div className="flex items-center justify-center">
                  <Image
                    src="/images/rootly-logo-branded.png"
                    alt="Rootly"
                    width={200}
                    height={80}
                    className="h-16 w-auto object-contain"
                  />
                </div>
              </Card>
          )}

          {/* PagerDuty Card */}
          {loadingPagerDuty ? (
            <Card className="border-2 border-gray-200 p-8 flex items-center justify-center relative h-32 animate-pulse">
              <div className="absolute top-4 right-4 w-6 h-6 bg-gray-300 rounded"></div>
              <div className="flex items-center space-x-2">
                <div className="w-10 h-10 bg-gray-300 rounded"></div>
                <div className="h-8 w-32 bg-gray-300 rounded"></div>
              </div>
            </Card>
          ) : (
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
                <>
                  <div className="absolute top-4 left-4">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  </div>
                  <div className="absolute top-4 right-4">
                    <Badge variant="secondary" className="bg-green-100 text-green-700">{pagerdutyCount}</Badge>
                  </div>
                </>
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
          )}
        </div>

        {/* Organization Selector */}
        {integrations.length > 0 && (
          <Card className="mt-8 mb-8 max-w-2xl mx-auto border-2 border-purple-200 bg-purple-50">
            <CardHeader className="pb-4">
              <CardTitle className="text-xl flex items-center">
                <Settings className="w-5 h-5 mr-2 text-purple-600" />
                Dashboard Organization
              </CardTitle>
              <CardDescription className="text-base">
                Select which organization to analyze on the dashboard.
              </CardDescription>
            </CardHeader>
            <CardContent className="pb-6">
              <Select 
                value={selectedOrganization} 
                onValueChange={(value) => {
                  // Only show toast if selecting a different organization
                  if (value !== selectedOrganization) {
                    const selected = integrations.find(i => i.id.toString() === value)
                    if (selected) {
                      toast.success(`${selected.name} has been set as your default organization.`)
                    }
                  }
                  
                  setSelectedOrganization(value)
                  // Save to localStorage for persistence
                  localStorage.setItem('selected_organization', value)
                }}
              >
                <SelectTrigger className="w-full h-12 text-base bg-white">
                  <SelectValue placeholder="Choose an organization to analyze">
                    {selectedOrganization && (() => {
                      const selected = integrations.find(i => i.id.toString() === selectedOrganization)
                      if (selected) {
                        return (
                          <div className="flex items-center justify-between w-full">
                            <div className="flex items-center">
                              <div className={`w-2 h-2 rounded-full mr-2 ${
                                selected.platform === 'rootly' ? 'bg-purple-500' : 'bg-green-500'
                              }`}></div>
                              {selected.name}
                            </div>
                            <Star className="w-4 h-4 text-yellow-500 fill-yellow-500 ml-2" />
                          </div>
                        )
                      }
                      return null
                    })()}
                  </SelectValue>
                </SelectTrigger>
              <SelectContent>
                {/* Group integrations by platform */}
                {(() => {
                  const rootlyIntegrations = integrations.filter(i => i.platform === 'rootly')
                  const pagerdutyIntegrations = integrations.filter(i => i.platform === 'pagerduty')
                  
                  return (
                    <>
                      {/* Rootly Organizations */}
                      {rootlyIntegrations.length > 0 && (
                        <>
                          <div className="px-2 py-1.5 text-xs font-medium text-gray-500 bg-gray-50 border-b">
                            <div className="flex items-center">
                              <div className="w-2 h-2 bg-purple-500 rounded-full mr-2"></div>
                              Rootly Organizations
                            </div>
                          </div>
                          {rootlyIntegrations.map((integration) => (
                            <SelectItem key={integration.id} value={integration.id.toString()}>
                              <div className="flex items-center justify-between w-full">
                                <div className="flex items-center">
                                  <div className="w-2 h-2 bg-purple-500 rounded-full mr-2"></div>
                                  {integration.name}
                                </div>
                                {selectedOrganization === integration.id.toString() && (
                                  <Star className="w-4 h-4 text-yellow-500 fill-yellow-500 ml-2" />
                                )}
                              </div>
                            </SelectItem>
                          ))}
                        </>
                      )}
                      
                      {/* PagerDuty Organizations */}
                      {pagerdutyIntegrations.length > 0 && (
                        <>
                          {rootlyIntegrations.length > 0 && (
                            <div className="my-1 border-t border-gray-200"></div>
                          )}
                          <div className="px-2 py-1.5 text-xs font-medium text-gray-500 bg-gray-50 border-b">
                            <div className="flex items-center">
                              <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                              PagerDuty Organizations
                            </div>
                          </div>
                          {pagerdutyIntegrations.map((integration) => (
                            <SelectItem key={integration.id} value={integration.id.toString()}>
                              <div className="flex items-center justify-between w-full">
                                <div className="flex items-center">
                                  <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                                  {integration.name}
                                </div>
                                {selectedOrganization === integration.id.toString() && (
                                  <Star className="w-4 h-4 text-yellow-500 fill-yellow-500 ml-2" />
                                )}
                              </div>
                            </SelectItem>
                          ))}
                        </>
                      )}
                    </>
                  )
                })()}
              </SelectContent>
              </Select>
            </CardContent>
          </Card>
        )}

        <div className="space-y-6">

            {/* Add Rootly Integration Form */}
            {addingPlatform === 'rootly' && (
              <Card className="border-purple-200 max-w-2xl mx-auto">
                <CardHeader className="p-8">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                      <Image src="/images/rootly-logo-branded.png" alt="Rootly" width={24} height={24} />
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
                              <li><strong>1.</strong> Log in to your Rootly account</li>
                              <li><strong>2.</strong> Navigate to <code className="bg-purple-100 px-1 rounded">Settings → API Keys</code></li>
                              <li><strong>3.</strong> Click <strong>"Create API Key"</strong></li>
                              <li><strong>4.</strong> Give it a name (e.g., <strong>"Burnout Detector"</strong>)</li>
                              <li><strong>5.</strong> Select appropriate permissions (<strong>required:</strong> read access to incidents and users)</li>
                              <li><strong>6.</strong> Copy the generated token (starts with <strong>"rootly_"</strong>)</li>
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
                                  {previewData.permissions && (
                                    <div className="mt-2">
                                      <p className="font-medium">Permissions:</p>
                                      <div className="grid grid-cols-2 gap-2 mt-1">
                                        <div className="flex items-center">
                                          {previewData.permissions.users?.access ? (
                                            <CheckCircle className="w-3 h-3 text-green-600 mr-1" />
                                          ) : (
                                            <AlertCircle className="w-3 h-3 text-red-600 mr-1" />
                                          )}
                                          <span className="text-xs">Users</span>
                                        </div>
                                        <div className="flex items-center">
                                          {previewData.permissions.incidents?.access ? (
                                            <CheckCircle className="w-3 h-3 text-green-600 mr-1" />
                                          ) : (
                                            <AlertCircle className="w-3 h-3 text-red-600 mr-1" />
                                          )}
                                          <span className="text-xs">Incidents</span>
                                        </div>
                                      </div>
                                      {(!previewData.permissions.users?.access || !previewData.permissions.incidents?.access) && (
                                        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs">
                                          <p className="font-medium text-red-800">Missing permissions:</p>
                                          {!previewData.permissions.users?.access && (
                                            <p className="text-red-700">• Users: {previewData.permissions.users?.error}</p>
                                          )}
                                          {!previewData.permissions.incidents?.access && (
                                            <p className="text-red-700">• Incidents: {previewData.permissions.incidents?.error}</p>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  )}
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
                            disabled={isAddingRootly}
                            className="bg-green-600 hover:bg-green-700"
                          >
                            {isAddingRootly ? (
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
                              <li><strong>1.</strong> In your PagerDuty account, click on <strong>Integrations</strong> in the top navigation</li>
                              <li><strong>2.</strong> Look for <strong>API Access Keys</strong> in the dropdown menu</li>
                              <li><strong>3.</strong> Click <code className="bg-green-100 px-1 rounded">Create API User Token</code> (NOT "Create API Key" - must be user-level)</li>
                              <li><strong>4.</strong> Give it a description (e.g., <strong>"Burnout Detector"</strong>) and click <strong>Create</strong></li>
                              <li><strong>5.</strong> Copy the generated token (starts with letters/numbers like <strong>"u+..."</strong>)</li>
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
                            disabled={isAddingPagerDuty}
                            className="bg-blue-600 hover:bg-blue-700"
                          >
                            {isAddingPagerDuty ? (
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
            ) : (loadingRootly || loadingPagerDuty) ? (
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
                      p-6 rounded-lg border relative
                      ${integration.platform === 'rootly' ? 'border-green-200 bg-green-50' : 'border-green-200 bg-green-50'}
                      ${savingIntegrationId === integration.id ? 'opacity-75' : ''}
                    `}>
                      {/* Saving overlay */}
                      {savingIntegrationId === integration.id && (
                        <div className="absolute inset-0 bg-white bg-opacity-50 flex items-center justify-center rounded-lg">
                          <div className="flex items-center space-x-2">
                            <Loader2 className="w-5 h-5 animate-spin" />
                            <span className="text-sm font-medium">Saving...</span>
                          </div>
                        </div>
                      )}
                      
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            
                            {editingIntegration === integration.id ? (
                              <div className="flex items-center space-x-2">
                                <Input
                                  value={editingName}
                                  onChange={(e) => setEditingName(e.target.value)}
                                  className="h-8 w-48"
                                  disabled={savingIntegrationId === integration.id}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter' && savingIntegrationId !== integration.id) {
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
                                  disabled={savingIntegrationId === integration.id}
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
                                  disabled={savingIntegrationId === integration.id}
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
                            <>
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
                              
                              {/* Error message for insufficient permissions */}
                              {(!integration.permissions.users.access || !integration.permissions.incidents.access) && (
                                <div className="mt-3">
                                  <Alert className="border-red-200 bg-red-50">
                                    <AlertCircle className="h-4 w-4 text-red-600" />
                                    <AlertDescription className="text-red-800">
                                      <strong>Insufficient permissions.</strong> Update API token with Users and Incidents read access.
                                    </AlertDescription>
                                  </Alert>
                                </div>
                              )}
                            </>
                          )}
                        </div>
                        
                        <div className="flex items-center">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              setIntegrationToDelete(integration)
                              setDeleteDialogOpen(true)
                            }}
                            className="h-8 w-8 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  {/* General Run Analysis Button */}
                  <div className="pt-6 mt-4 border-t border-gray-200">
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

        {/* GitHub and Slack Integrations Section */}
        <div className="mt-16 space-y-8">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-slate-900 mb-3">Enhanced Integrations</h2>
            <p className="text-lg text-slate-600 mb-2">
              Add GitHub and Slack for deeper burnout analysis
            </p>
            <p className="text-slate-500">
              Analyze code patterns and communication trends to get additional insights
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8 mb-8 max-w-2xl mx-auto">
            {/* GitHub Card */}
            {loadingGitHub ? (
              <Card className="border-2 border-gray-200 p-8 flex items-center justify-center relative h-32 animate-pulse">
                <div className="absolute top-4 right-4 w-16 h-5 bg-gray-300 rounded"></div>
                <div className="flex items-center space-x-2">
                  <div className="w-10 h-10 bg-gray-300 rounded"></div>
                  <div className="h-8 w-24 bg-gray-300 rounded"></div>
                </div>
              </Card>
            ) : (
                <Card 
                  className={`border-2 transition-all cursor-pointer hover:shadow-lg ${
                    activeEnhancementTab === 'github' 
                      ? 'border-gray-500 shadow-lg bg-gray-50' 
                      : 'border-gray-200 hover:border-gray-300'
                  } p-8 flex items-center justify-center relative h-32`}
                  onClick={() => {
                    setActiveEnhancementTab(activeEnhancementTab === 'github' ? null : 'github')
                  }}
                >
                  {githubIntegration ? (
                    <div className="absolute top-4 right-4 flex flex-col items-end space-y-1">
                      <Badge variant="secondary" className="bg-green-100 text-green-700 border-green-200">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Connected
                      </Badge>
                    </div>
                  ) : null}
                  {activeEnhancementTab === 'github' && (
                    <div className="absolute top-4 left-4">
                      <CheckCircle className="w-6 h-6 text-gray-600" />
                    </div>
                  )}
                  <div className="flex items-center space-x-2">
                    <div className="w-10 h-10 rounded flex items-center justify-center">
                      <Image
                        src="/images/github-logo.png"
                        alt="GitHub"
                        width={40}
                        height={40}
                        className="h-10 w-10 object-contain"
                      />
                    </div>
                    <span className="text-2xl font-bold text-slate-900">GitHub</span>
                  </div>
                </Card>
            )}

            {/* Slack Card */}
            {loadingSlack ? (
              <Card className="border-2 border-gray-200 p-8 flex items-center justify-center relative h-32 animate-pulse">
                <div className="absolute top-4 right-4 w-16 h-5 bg-gray-300 rounded"></div>
                <div className="flex items-center space-x-2">
                  <div className="w-10 h-10 bg-gray-300 rounded"></div>
                  <div className="h-8 w-20 bg-gray-300 rounded"></div>
                </div>
              </Card>
            ) : (
              <Card 
                className={`border-2 transition-all cursor-pointer hover:shadow-lg ${
                  activeEnhancementTab === 'slack' 
                    ? 'border-purple-500 shadow-lg bg-purple-50' 
                    : 'border-gray-200 hover:border-purple-300'
                } p-8 flex items-center justify-center relative h-32`}
                onClick={() => {
                  setActiveEnhancementTab(activeEnhancementTab === 'slack' ? null : 'slack')
                }}
              >
                  {slackIntegration ? (
                    <div className="absolute top-4 right-4">
                      <Badge variant="secondary" className="bg-green-100 text-green-700">Connected</Badge>
                    </div>
                  ) : null}
                  {activeEnhancementTab === 'slack' && (
                    <div className="absolute top-4 left-4">
                      <CheckCircle className="w-6 h-6 text-purple-600" />
                    </div>
                  )}
                  <div className="flex items-center space-x-2">
                    <div className="w-10 h-10 rounded flex items-center justify-center">
                      <Image
                        src="/images/slack-logo.png"
                        alt="Slack"
                        width={40}
                        height={40}
                        className="h-10 w-10 object-contain"
                      />
                    </div>
                    <span className="text-2xl font-bold text-slate-900">Slack</span>
                  </div>
                </Card>
            )}
          </div>

          {/* Integration Forms */}
          <div className="space-y-6">
            {/* GitHub Token Form */}
            {activeEnhancementTab === 'github' && !githubIntegration && (
              <Card className="border-gray-200 max-w-2xl mx-auto">
                <CardHeader className="p-8">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center">
                      <Image
                        src="/images/github-logo.png"
                        alt="GitHub"
                        width={40}
                        height={40}
                        className="h-10 w-10 object-contain"
                      />
                    </div>
                    <div>
                      <CardTitle>Add GitHub Integration</CardTitle>
                      <CardDescription>Connect your GitHub account to analyze development patterns</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 p-8 pt-0">
                  {/* Instructions */}
                  <div>
                    <button 
                      type="button"
                      onClick={() => setShowGithubInstructions(!showGithubInstructions)}
                      className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-700"
                    >
                      <HelpCircle className="w-4 h-4" />
                      <span>How to get your GitHub Personal Access Token</span>
                      <ChevronDown className={`w-4 h-4 transition-transform ${showGithubInstructions ? 'rotate-180' : ''}`} />
                    </button>
                    {showGithubInstructions && (
                      <div className="mt-4">
                        <Alert className="border-gray-200 bg-gray-50">
                          <AlertDescription>
                            <div className="space-y-4">
                              <div>
                                <h4 className="font-medium text-gray-900 mb-2"><strong>Step 1:</strong> Go to GitHub Settings</h4>
                                <p className="text-sm text-gray-600 mb-2">
                                  Navigate to <strong>GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)</strong>
                                </p>
                                <a 
                                  href="https://github.com/settings/tokens" 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center text-sm text-blue-600 hover:underline"
                                >
                                  Open GitHub Settings <ExternalLink className="w-3 h-3 ml-1" />
                                </a>
                              </div>
                              
                              <div>
                                <h4 className="font-medium text-gray-900 mb-2"><strong>Step 2:</strong> Generate New Token</h4>
                                <p className="text-sm text-gray-600 mb-2">Click <strong>"Generate new token (classic)"</strong> and configure:</p>
                                <ul className="text-sm text-gray-600 space-y-1 ml-4">
                                  <li>• <strong>Note:</strong> Give it a descriptive name (e.g., "Burnout Detector")</li>
                                  <li>• <strong>Expiration:</strong> Set an appropriate expiration date</li>
                                </ul>
                              </div>
                              
                              <div>
                                <h4 className="font-medium text-gray-900 mb-2"><strong>Step 3:</strong> Select Required Scopes</h4>
                                <p className="text-sm text-gray-600 mb-2">Select these <strong>permissions:</strong></p>
                                <ul className="text-sm text-gray-600 space-y-1 ml-4">
                                  <li>• <code className="bg-gray-200 px-1 rounded">repo</code> - Full repository access</li>
                                  <li>• <code className="bg-gray-200 px-1 rounded">read:user</code> - Read user profile information</li>
                                  <li>• <code className="bg-gray-200 px-1 rounded">read:org</code> - Read organization membership</li>
                                </ul>
                              </div>
                              
                              <div>
                                <h4 className="font-medium text-gray-900 mb-2"><strong>Step 4:</strong> Generate and Copy Token</h4>
                                <p className="text-sm text-gray-600">
                                  Click <strong>"Generate token"</strong> and immediately copy the token (starts with <code className="bg-gray-200 px-1 rounded">ghp_</code>). 
                                  <strong>You won't be able to see it again!</strong>
                                </p>
                              </div>
                            </div>
                          </AlertDescription>
                        </Alert>
                      </div>
                    )}
                  </div>

                  <div className="space-y-2">
                    <label htmlFor="github-token" className="text-sm font-medium">GitHub Personal Access Token</label>
                    <div className="relative">
                      <Input
                        id="github-token"
                        type={showGithubToken ? "text" : "password"}
                        placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                        className="pr-10"
                        value={githubToken}
                        onChange={(e) => setGithubToken(e.target.value)}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                        onClick={() => setShowGithubToken(!showGithubToken)}
                      >
                        {showGithubToken ? (
                          <EyeOff className="h-4 w-4 text-gray-400" />
                        ) : (
                          <Eye className="h-4 w-4 text-gray-400" />
                        )}
                      </Button>
                    </div>
                    <p className="text-sm text-gray-500">
                      Token should start with "ghp_" followed by 36 characters
                    </p>
                  </div>
                  <Button 
                    className="bg-gray-900 hover:bg-gray-800 text-white"
                    onClick={() => githubToken && handleGitHubConnect(githubToken)}
                    disabled={!githubToken || isConnectingGithub}
                  >
                    {isConnectingGithub ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Connecting...
                      </>
                    ) : (
                      'Connect GitHub'
                    )}
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Slack Webhook Form */}
            {activeEnhancementTab === 'slack' && !slackIntegration && (
              <Card className="border-purple-200 max-w-2xl mx-auto">
                <CardHeader className="p-8">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center">
                      <Image
                        src="/images/slack-logo.png"
                        alt="Slack"
                        width={40}
                        height={40}
                        className="h-10 w-10 object-contain"
                      />
                    </div>
                    <div>
                      <CardTitle>Add Slack Integration</CardTitle>
                      <CardDescription>Connect your Slack workspace to analyze communication patterns</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 p-8 pt-0">
                  {/* Instructions */}
                  <div>
                    <button 
                      type="button"
                      onClick={() => setShowSlackInstructions(!showSlackInstructions)}
                      className="flex items-center space-x-2 text-sm text-purple-600 hover:text-purple-700"
                    >
                      <HelpCircle className="w-4 h-4" />
                      <span>How to get your Slack credentials</span>
                      <ChevronDown className={`w-4 h-4 transition-transform ${showSlackInstructions ? 'rotate-180' : ''}`} />
                    </button>
                    {showSlackInstructions && (
                      <div className="mt-4">
                        <Alert className="border-purple-200 bg-purple-50">
                          <AlertDescription>
                            <div className="space-y-4">
                              <div>
                                <h4 className="font-medium text-purple-900 mb-2"><strong>Step 1:</strong> Create a Slack App</h4>
                                <p className="text-sm text-purple-800 mb-2">
                                  Go to the <strong>Slack API website</strong> and create a new app:
                                </p>
                                <a 
                                  href="https://api.slack.com/apps" 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center text-sm text-blue-600 hover:underline"
                                >
                                  Create Slack App <ExternalLink className="w-3 h-3 ml-1" />
                                </a>
                                <p className="text-sm text-purple-800 mt-2">Click "Create New App" → "From scratch" → Enter app name and select your workspace</p>
                              </div>
                              
                              <div>
                                <h4 className="font-medium text-purple-900 mb-2">Step 2: Configure Incoming Webhooks</h4>
                                <p className="text-sm text-purple-800 mb-2">In your app settings:</p>
                                <ul className="text-sm text-purple-800 space-y-1 ml-4">
                                  <li>• Go to "Incoming Webhooks" in the sidebar</li>
                                  <li>• Toggle "Activate Incoming Webhooks" to <strong>On</strong></li>
                                  <li>• Click "Add New Webhook to Workspace"</li>
                                  <li>• Select a channel and click "Allow"</li>
                                  <li>• Copy the webhook URL (starts with <code className="bg-purple-200 px-1 rounded">https://hooks.slack.com/</code>)</li>
                                </ul>
                              </div>
                              
                              <div>
                                <h4 className="font-medium text-purple-900 mb-2">Step 3: Add Bot Token Scopes</h4>
                                <p className="text-sm text-purple-800 mb-2">In "OAuth & Permissions" → "Scopes" → "Bot Token Scopes", add these <strong>3 required scopes</strong>:</p>
                                <ul className="text-sm text-purple-800 space-y-1 ml-4">
                                  <li>• <code className="bg-purple-200 px-1 rounded">channels:read</code> - View basic channel information</li>
                                  <li>• <code className="bg-purple-200 px-1 rounded">channels:history</code> - Read public channel messages</li>
                                  <li>• <code className="bg-purple-200 px-1 rounded">users:read</code> - View user information</li>
                                </ul>
                                <div className="mt-2 p-2 bg-amber-100 border border-amber-300 rounded text-xs text-amber-800">
                                  <strong>Important:</strong> After adding scopes, you MUST reinstall the app to your workspace for changes to take effect.
                                </div>
                              </div>
                              
                              <div>
                                <h4 className="font-medium text-purple-900 mb-2">Step 4: Install App and Get Bot Token</h4>
                                <ul className="text-sm text-purple-800 space-y-1 ml-4">
                                  <li>• Click "Install to Workspace" at the top of OAuth & Permissions</li>
                                  <li>• Review permissions and click "Allow"</li>
                                  <li>• Copy the "Bot User OAuth Token" (starts with <code className="bg-purple-200 px-1 rounded">xoxb-</code>)</li>
                                </ul>
                              </div>
                              
                              <div>
                                <h4 className="font-medium text-purple-900 mb-2">Step 5: Add Bot to Channels</h4>
                                <p className="text-sm text-purple-800 mb-2">After setup, add the bot to relevant channels:</p>
                                <ul className="text-sm text-purple-800 space-y-1 ml-4">
                                  <li>• Go to each channel you want analyzed in Slack</li>
                                  <li>• Type <code className="bg-purple-200 px-1 rounded">@Burnout Detector</code> and invite the bot</li>
                                  <li>• The bot must be in channels to read message history</li>
                                </ul>
                                <div className="mt-2 p-2 bg-red-100 border border-red-300 rounded text-xs text-red-800">
                                  <strong>Required:</strong> Bot permissions will show "Bot not in channels" until you add it to at least one channel.
                                </div>
                              </div>
                              
                              <div className="bg-purple-100 border border-purple-300 rounded p-3">
                                <p className="text-sm text-purple-800">
                                  <strong>Note:</strong> You'll need both the webhook URL and bot token. The webhook is for sending notifications, 
                                  and the bot token is for reading messages and user data.
                                </p>
                              </div>
                            </div>
                          </AlertDescription>
                        </Alert>
                      </div>
                    )}
                  </div>

                  <div className="space-y-2">
                    <label htmlFor="slack-webhook" className="text-sm font-medium">Slack Webhook URL</label>
                    <div className="relative">
                      <Input
                        id="slack-webhook"
                        type={showSlackWebhook ? "text" : "password"}
                        placeholder="https://hooks.slack.com/services/..."
                        className="pr-10"
                        value={slackWebhookUrl}
                        onChange={(e) => setSlackWebhookUrl(e.target.value)}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                        onClick={() => setShowSlackWebhook(!showSlackWebhook)}
                      >
                        {showSlackWebhook ? (
                          <EyeOff className="h-4 w-4 text-gray-400" />
                        ) : (
                          <Eye className="h-4 w-4 text-gray-400" />
                        )}
                      </Button>
                    </div>
                    <p className="text-sm text-gray-500">
                      URL should start with "https://hooks.slack.com/services/"
                    </p>
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="slack-token" className="text-sm font-medium">Slack Bot Token</label>
                    <div className="relative">
                      <Input
                        id="slack-token"
                        type={showSlackToken ? "text" : "password"}
                        placeholder="xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx"
                        className="pr-10"
                        value={slackBotToken}
                        onChange={(e) => setSlackBotToken(e.target.value)}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                        onClick={() => setShowSlackToken(!showSlackToken)}
                      >
                        {showSlackToken ? (
                          <EyeOff className="h-4 w-4 text-gray-400" />
                        ) : (
                          <Eye className="h-4 w-4 text-gray-400" />
                        )}
                      </Button>
                    </div>
                    <p className="text-sm text-gray-500">
                      Token should start with "xoxb-" followed by your bot token
                    </p>
                  </div>
                  <Button 
                    className="bg-purple-600 hover:bg-purple-700 text-white"
                    onClick={() => slackWebhookUrl && slackBotToken && handleSlackConnect(slackWebhookUrl, slackBotToken)}
                    disabled={!slackWebhookUrl || !slackBotToken || isConnectingSlack}
                  >
                    {isConnectingSlack ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Connecting...
                      </>
                    ) : (
                      'Connect Slack'
                    )}
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Connected GitHub Status */}
            {activeEnhancementTab === 'github' && githubIntegration && (
              <Card className="border-green-200 bg-green-50 max-w-2xl mx-auto">
                <CardHeader className="p-8">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-lg flex items-center justify-center">
                        <Image
                          src="/images/github-logo.png"
                          alt="GitHub"
                          width={40}
                          height={40}
                          className="h-10 w-10 object-contain"
                        />
                      </div>
                      <div>
                        <CardTitle>GitHub Connected</CardTitle>
                        <CardDescription>
                          <div className="space-y-1">
                            <div>Username: {githubIntegration.github_username}</div>
                            {!githubIntegration.is_beta && (
                              <div>Token: {githubIntegration.token_preview}</div>
                            )}
                          </div>
                        </CardDescription>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => openMappingDrawer('github')}
                        disabled={loadingMappingData}
                        className="bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100 hover:text-blue-800 hover:border-blue-300"
                        title="View and manage GitHub user mappings"
                      >
                        {loadingMappingData && selectedMappingPlatform === 'github' ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Loading...
                          </>
                        ) : (
                          <>
                            <Users className="w-4 h-4 mr-2" />
                            View Mappings
                          </>
                        )}
                      </Button>
                      {githubIntegration.is_beta ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleGitHubTest}
                        >
                          <TestTube className="w-4 h-4 mr-1" />
                          Test Connection
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setGithubDisconnectDialogOpen(true)}
                          className="h-8 w-8 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-8 pt-0">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div className="flex items-center space-x-2">
                      <Key className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="font-medium">Token Source</div>
                        <div className="text-gray-600">
                          {githubIntegration.is_beta 
                            ? "Beta" 
                            : githubIntegration.token_source === "oauth" 
                              ? "OAuth" 
                              : "Personal Access Token"
                          }
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Calendar className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="font-medium">Connected</div>
                        <div className="text-gray-600">{new Date(githubIntegration.connected_at).toLocaleDateString()}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Building className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="font-medium">Organizations</div>
                        <div className="text-gray-600">
                          {githubIntegration.organizations && githubIntegration.organizations.length > 0 
                            ? githubIntegration.organizations.join(', ') 
                            : 'None'}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Clock className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="font-medium">Last Updated</div>
                        <div className="text-gray-600">{new Date(githubIntegration.last_updated).toLocaleDateString()}</div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Beta Access Information */}
                  {githubIntegration.is_beta && (
                    <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                      <div className="flex items-start space-x-2">
                        <div className="w-5 h-5 text-blue-600 mt-0.5">
                          <CheckCircle className="w-5 h-5" />
                        </div>
                        <div className="flex-1 text-sm">
                          <div className="font-medium text-blue-800 mb-1">Beta Access Enabled</div>
                          <div className="text-blue-700">
                            You're using a shared GitHub integration for testing purposes. 
                            No personal token setup required.
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                </CardContent>
              </Card>
            )}

            {/* Connected Slack Status */}
            {activeEnhancementTab === 'slack' && slackIntegration && (
              <Card className="border-green-200 bg-green-50 max-w-2xl mx-auto">
                <CardHeader className="p-8">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-lg flex items-center justify-center">
                        <Image
                          src="/images/slack-logo.png"
                          alt="Slack"
                          width={40}
                          height={40}
                          className="h-10 w-10 object-contain"
                        />
                      </div>
                      <div>
                        <CardTitle>Slack Connected</CardTitle>
                        <CardDescription>User ID: {slackIntegration.slack_user_id}</CardDescription>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => openMappingDrawer('slack')}
                        disabled={loadingMappingData}
                        className="bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100 hover:text-purple-800 hover:border-purple-300"
                        title="View and manage Slack user mappings"
                      >
                        {loadingMappingData && selectedMappingPlatform === 'slack' ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Loading...
                          </>
                        ) : (
                          <>
                            <Users className="w-4 h-4 mr-2" />
                            View Mappings
                          </>
                        )}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={handleSlackTest}
                        className="h-8 w-8 p-0 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                      >
                        <RotateCcw className="w-4 h-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setSlackDisconnectDialogOpen(true)}
                        className="h-8 w-8 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-8 pt-0">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div className="flex items-center space-x-2">
                      <Key className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="font-medium">Webhook URL</div>
                        <div className="text-gray-600 font-mono text-xs">
                          {slackIntegration.webhook_preview || 'Not configured'}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Key className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="font-medium">Bot Token</div>
                        <div className="text-gray-600 font-mono text-xs">
                          {slackIntegration.token_preview || 'Not available'}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Building className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="font-medium">Workspace ID</div>
                        <div className="text-gray-600 font-mono text-xs">{slackIntegration.workspace_id}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Calendar className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="font-medium">Connected</div>
                        <div className="text-gray-600">{new Date(slackIntegration.connected_at).toLocaleDateString()}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Clock className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="font-medium">Last Updated</div>
                        <div className="text-gray-600">{new Date(slackIntegration.last_updated).toLocaleDateString()}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Users className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="font-medium">User ID</div>
                        <div className="text-gray-600 font-mono text-xs">{slackIntegration.slack_user_id}</div>
                      </div>
                    </div>
                  </div>

                  {/* Permissions Section */}
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium text-sm">Bot Permissions</h4>
                      {isLoadingPermissions ? (
                        <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                      ) : (
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={loadSlackPermissions}
                          className="h-8 w-8 p-0 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                        >
                          <RotateCcw className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                    {slackPermissions ? (
                      <div className="grid grid-cols-1 gap-2">
                        {Object.entries(slackPermissions)
                          .filter(([permission]) => ['channels_access', 'users_access', 'channels_history'].includes(permission))
                          .map(([permission, hasAccess]) => {
                          const isGranted = hasAccess === true
                          const permissionLabels: { [key: string]: string } = {
                            'channels_access': 'Channel Access',
                            'users_access': 'User Access', 
                            'channels_history': 'Channel History'
                          }
                          
                          return (
                            <div key={permission} className="flex items-center justify-between text-xs">
                              <span className="text-gray-600">{permissionLabels[permission] || permission}</span>
                              <div className="flex items-center space-x-1">
                                {isGranted ? (
                                  <>
                                    <CheckCircle className="w-3 h-3 text-green-500" />
                                    <span className="text-green-600 font-medium">Granted</span>
                                  </>
                                ) : (
                                  <>
                                    <AlertCircle className="w-3 h-3 text-red-500" />
                                    <span className="text-red-600 font-medium">
                                      {permission === 'channels_history' && slackPermissions.errors?.includes('not_in_channel') 
                                        ? 'Bot not in channels' 
                                        : 'Missing'}
                                    </span>
                                  </>
                                )}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    ) : (
                      <div className="text-xs text-gray-500">
                        Click "Test" or the refresh icon to check permissions
                      </div>
                    )}
                  </div>
                  
                  {/* Bot Channels Section */}
                  <div className="mt-6">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium text-sm">Bot Channels</h4>
                    </div>
                    {slackIntegration?.channel_names && slackIntegration.channel_names.length > 0 ? (
                      <div className="space-y-1">
                        {slackIntegration.channel_names.map((channelName: string) => (
                          <div key={channelName} className="flex items-center space-x-2 text-xs">
                            <span className="text-gray-400">#</span>
                            <span className="text-gray-700">{channelName}</span>
                            <CheckCircle className="w-3 h-3 text-green-500" />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-xs text-gray-500">
                        {slackPermissions?.errors?.includes('not_in_channel') 
                          ? 'Bot is not in any channels. Add it to channels in Slack.'
                          : 'No channels found'}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        {/* AI Insights Section - Hidden for Railway deployment (AI always enabled) */}
        {false && (
          <div className="mt-16 space-y-8">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-slate-900 mb-3">AI Insights Included</h2>
              <p className="text-lg text-slate-600 mb-2">
                Enable AI-powered burnout analysis with natural language reasoning
              </p>
              <p className="text-slate-500">
                Get intelligent insights and recommendations automatically with every analysis
              </p>
            </div>

            <div className="max-w-xl mx-auto">
              <Card className="border-2 border-blue-200 p-6">
                <CardHeader className="pb-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                        <Zap className="w-6 h-6 text-blue-600" />
                      </div>
                      <div>
                        <CardTitle className="text-xl">LLM Token</CardTitle>
                        <CardDescription>
                          Connect your language model for AI-powered analysis
                        </CardDescription>
                      </div>
                    </div>
                    {llmConfig?.has_token && (
                      <Badge variant="secondary" className="bg-green-100 text-green-700">
                        Connected
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {llmConfig?.has_token ? (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="w-5 h-5 text-green-600" />
                        <div className="text-sm text-green-800">
                          <p className="font-medium">
                            {llmConfig.provider === 'openai' ? 'OpenAI' : 'Anthropic'} Connected
                          </p>
                          <p className="text-xs">
                            AI-powered analysis enabled for all users
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-700">
                          Provider
                        </label>
                        <select 
                          value={llmProvider} 
                          onChange={(e) => {
                            setLlmProvider(e.target.value)
                            setLlmModel(e.target.value === 'openai' ? 'gpt-4o-mini' : 'claude-3-haiku')
                            if (tokenError) setTokenError(null) // Clear error when changing provider
                          }}
                          className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                          <option value="openai">OpenAI (GPT-4o-mini)</option>
                          <option value="anthropic">Anthropic (Claude 3 Haiku)</option>
                        </select>
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-700">
                          API Token
                        </label>
                        <div className="relative">
                          <Input
                            type={showLlmToken ? "text" : "password"}
                            placeholder={`Enter your ${llmProvider === 'openai' ? 'OpenAI' : 'Anthropic'} API token`}
                            value={llmToken}
                            onChange={(e) => {
                              setLlmToken(e.target.value)
                              if (tokenError) setTokenError(null) // Clear error when user types
                            }}
                            className={`pr-10 ${tokenError ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''}`}
                          />
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setShowLlmToken(!showLlmToken)}
                            className="absolute right-2 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
                          >
                            {showLlmToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </Button>
                        </div>
                        
                        {tokenError ? (
                          <p className="text-xs text-red-600 flex items-center space-x-1">
                            <AlertCircle className="w-3 h-3" />
                            <span>{tokenError}</span>
                          </p>
                        ) : (
                          <p className="text-xs text-slate-500">
                            {llmProvider === 'openai' 
                              ? 'Token should start with "sk-" and have 51+ characters'
                              : 'Token should start with "sk-ant-api" and have 100+ characters'
                            }
                          </p>
                        )}
                      </div>

                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex items-start space-x-2">
                          <HelpCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                          <div className="text-sm text-blue-800">
                            <p className="font-medium mb-1">AI Features Include:</p>
                            <ul className="space-y-1 text-xs">
                              <li>• Natural language reasoning about burnout patterns</li>
                              <li>• Intelligent risk assessment with explanations</li>
                              <li>• Context-aware recommendations</li>
                              <li>• Team-level insights and trends</li>
                            </ul>
                          </div>
                        </div>
                      </div>

                      <div className="flex space-x-2">
                        <Button 
                          className="flex-1" 
                          onClick={handleConnectAI}
                          disabled={isConnectingAI || !llmToken.trim()}
                        >
                          {isConnectingAI ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Verifying Token...
                            </>
                          ) : (
                            'Connect AI'
                          )}
                        </Button>
                        <Button variant="outline" size="sm" asChild>
                          <a 
                            href={llmProvider === 'openai' 
                              ? 'https://platform.openai.com/api-keys' 
                              : 'https://console.anthropic.com/'
                            } 
                            target="_blank" 
                            rel="noopener noreferrer"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        </Button>
                      </div>
                    </>
                  )}

                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription className="text-sm">
                      AI insights are automatically included with every analysis - no setup or API tokens required!
                    </AlertDescription>
                  </Alert>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </main>

      {/* Data Mapping Drawer */}
      <Sheet open={showMappingDialog} onOpenChange={setShowMappingDialog}>
        <SheetContent className="w-full sm:max-w-4xl lg:max-w-5xl overflow-y-auto">
          <SheetHeader className="space-y-4">
            <SheetTitle className="flex items-center justify-between pr-6">
              <div className="flex items-center space-x-2">
                <BarChart3 className="w-5 h-5" />
                <span>
                  {selectedMappingPlatform === 'github' ? 'GitHub' : 'Slack'} Data Mapping
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  console.log('🔴 REFRESH BUTTON CLICKED!', selectedMappingPlatform)
                  selectedMappingPlatform && loadMappingData(selectedMappingPlatform)
                }}
                disabled={loadingMappingData}
                className="h-8 w-8 p-0"
                title="Refresh mapping data"
              >
                <RefreshCw className={`w-4 h-4 ${loadingMappingData ? 'animate-spin' : ''}`} />
              </Button>
            </SheetTitle>
            <SheetDescription>
              View how team members from your incident data are mapped to {selectedMappingPlatform === 'github' ? 'GitHub' : 'Slack'} accounts. Click the refresh button to reload the latest mapping data.
            </SheetDescription>
          </SheetHeader>

          {mappingStats && (
            <div className="relative space-y-6">
              {/* Loading overlay when refreshing */}
              {loadingMappingData && (
                <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-10 rounded-lg">
                  <div className="flex items-center space-x-2 text-gray-600">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span className="text-sm">Refreshing mapping data...</span>
                  </div>
                </div>
              )}
              
              {/* Overall Statistics */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                <Card className="p-4 border-purple-200">
                  <div className="flex items-center space-x-2">
                    <Users2 className="w-4 h-4 text-green-600" />
                    <div>
                      <div className="text-2xl font-bold">{(mappingStats as any).mapped_members || mappingStats.total_attempts}</div>
                      <div className="text-sm text-gray-600">Mapped Members</div>
                    </div>
                  </div>
                </Card>
                <Card className="p-4 border-purple-200">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <div>
                      <div className="text-2xl font-bold text-green-600">
                        {mappingStats.overall_success_rate}%
                      </div>
                      <div className="text-sm text-gray-600">Success Rate</div>
                    </div>
                  </div>
                </Card>
                <Card className="p-4 border-purple-200">
                  <div className="flex items-center space-x-2">
                    <Database className="w-4 h-4 text-purple-600" />
                    <div>
                      <div className="text-2xl font-bold">
                        {(mappingStats as any).members_with_data || mappingData.filter(m => m.data_collected && m.mapping_successful).length}
                      </div>
                      <div className="text-sm text-gray-600">With Data</div>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Mapping Results Table */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">Mapping Results</h3>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={showOnlyFailed}
                      onChange={(e) => setShowOnlyFailed(e.target.checked)}
                      className="rounded border-gray-300"
                    />
                    Show only failed mappings
                  </label>
                </div>
                <div className="border rounded-lg overflow-hidden">
                  <div className="bg-gray-50 px-4 py-3 border-b">
                    <div className="grid grid-cols-4 gap-4 text-sm font-medium text-gray-600">
                      <button
                        onClick={() => handleSort('email')}
                        className="flex items-center gap-1 hover:text-gray-900 text-left"
                      >
                        Team Member
                        {sortField === 'email' ? (
                          sortDirection === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 opacity-50" />
                        )}
                      </button>
                      <button
                        onClick={() => handleSort('status')}
                        className="flex items-center gap-1 hover:text-gray-900 text-left"
                      >
                        Status
                        {sortField === 'status' ? (
                          sortDirection === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 opacity-50" />
                        )}
                      </button>
                      <div>{selectedMappingPlatform === 'github' ? 'GitHub User' : 'Slack User'} 
                        <span className="text-xs text-gray-500 block">Click + to add missing</span>
                      </div>
                      <button
                        onClick={() => handleSort('method')}
                        className="flex items-center gap-1 hover:text-gray-900 text-left"
                      >
                        Method
                        {sortField === 'method' ? (
                          sortDirection === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 opacity-50" />
                        )}
                      </button>
                    </div>
                  </div>
                  <div className="divide-y max-h-96 overflow-y-auto">
                    {sortedMappings.length > 0 ? sortedMappings.map((mapping) => {
                      console.log('🔍 Mapping row:', {
                        id: mapping.id,
                        email: mapping.source_identifier,
                        target: mapping.target_identifier,
                        successful: mapping.mapping_successful,
                        hasTarget: !!mapping.target_identifier
                      })
                      return (
                      <div key={mapping.id} className="px-4 py-3">
                        <div className="grid grid-cols-4 gap-4 text-sm">
                          <div className="font-medium" title={mapping.source_identifier}>
                            <div className="truncate">
                              {mapping.source_name ? (
                                <>
                                  <span className="font-semibold">{mapping.source_name}</span>
                                  <div className="text-xs text-gray-500 truncate">{mapping.source_identifier}</div>
                                </>
                              ) : (
                                mapping.source_identifier
                              )}
                            </div>
                          </div>
                          <div className="space-y-1">
                            {mapping.mapping_successful ? (
                              <Badge variant="default" className="bg-green-100 text-green-800 border-green-200">
                                <CheckCircle className="w-3 h-3 mr-1" />
                                Success
                              </Badge>
                            ) : (
                              <Badge variant="destructive" className="bg-red-100 text-red-800 border-red-200">
                                <AlertCircle className="w-3 h-3 mr-1" />
                                Failed
                              </Badge>
                            )}
                            <div className="text-xs text-gray-500">
                              {mapping.data_points_count ? (
                                <span>{mapping.data_points_count} data points</span>
                              ) : (
                                // Only show "No data" if GitHub was enabled in the analysis
                                mappingStats?.github_was_enabled && selectedMappingPlatform === 'github' ? (
                                  <span>No data</span>
                                ) : null
                              )}
                            </div>
                          </div>
                          <div className="truncate" title={mapping.target_identifier || mapping.error_message || ''}>
                            {(() => {
                              console.log('🔍 Button logic for', mapping.source_identifier, {
                                hasTarget: !!mapping.target_identifier,
                                target: mapping.target_identifier,
                                isEditing: inlineEditingId === mapping.id,
                                shouldShowPlusButton: !mapping.target_identifier && inlineEditingId !== mapping.id,
                                mapping_successful: mapping.mapping_successful,
                                error_message: mapping.error_message,
                                full_mapping: mapping,
                                is_manual: mapping.is_manual
                              })
                              return mapping.target_identifier ? (
                                inlineEditingId === mapping.id ? (
                                  // Show edit form for existing mapping
                                  <div className="space-y-1">
                                    <div className="flex items-center space-x-2">
                                      <input
                                        type="text"
                                        value={inlineEditingValue}
                                        onChange={(e) => handleInlineValueChange(e.target.value)}
                                        placeholder={`Edit ${selectedMappingPlatform === 'github' ? 'GitHub' : 'Slack'} username`}
                                        className={`flex-1 px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 ${
                                          githubValidation?.valid === false 
                                            ? 'border-red-300 focus:ring-red-500' 
                                            : githubValidation?.valid === true
                                            ? 'border-green-300 focus:ring-green-500'
                                            : 'border-gray-300 focus:ring-blue-500'
                                        }`}
                                        autoFocus
                                        onKeyDown={(e) => {
                                          if (e.key === 'Enter') {
                                            saveEditedMapping(mapping.id, mapping.source_identifier)
                                          } else if (e.key === 'Escape') {
                                            cancelInlineEdit()
                                          }
                                        }}
                                      />
                                      <button
                                        onClick={() => {
                                          if (selectedMappingPlatform === 'github' && githubValidation?.valid !== true) {
                                            toast.error(`Cannot save invalid username: ${githubValidation?.message || 'Please enter a valid GitHub username'}`, {
                                              duration: 4000
                                            })
                                            return
                                          }
                                          saveEditedMapping(mapping.id, mapping.source_identifier)
                                        }}
                                        disabled={savingInlineMapping || validatingGithub}
                                        className={`p-1 hover:opacity-80 disabled:opacity-50 ${
                                          selectedMappingPlatform === 'github' && githubValidation?.valid !== true
                                            ? 'text-gray-400 cursor-not-allowed'
                                            : 'text-green-600 hover:text-green-700'
                                        }`}
                                        title="Save changes"
                                      >
                                        <CheckCircle className="w-4 h-4" />
                                      </button>
                                      <button
                                        onClick={cancelInlineEdit}
                                        disabled={savingInlineMapping}
                                        className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                                        title="Cancel"
                                      >
                                        <X className="w-4 h-4" />
                                      </button>
                                    </div>
                                    {/* Validation feedback */}
                                    {(validatingGithub || githubValidation) && (
                                      <div className="flex items-center gap-1 text-xs">
                                        {validatingGithub ? (
                                          <>
                                            <Loader2 className="w-3 h-3 animate-spin" />
                                            <span className="text-gray-500">Validating...</span>
                                          </>
                                        ) : githubValidation?.valid ? (
                                          <>
                                            <CheckCircle className="w-3 h-3 text-green-600" />
                                            <span className="text-green-600">{githubValidation.message}</span>
                                          </>
                                        ) : (
                                          <>
                                            <AlertCircle className="w-3 h-3 text-red-600" />
                                            <span className="text-red-600">{githubValidation?.message}</span>
                                          </>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                ) : (
                                  // Show existing mapping with manual indicator and edit button
                                  <div className="flex items-center gap-1 group">
                                    <span>{mapping.target_identifier}</span>
                                    {mapping.is_manual && (
                                      <Tooltip content="Manual mapping - will show data collection status after running an analysis">
                                        <Badge variant="outline" className="ml-1 text-xs bg-blue-50 text-blue-700 border-blue-200 cursor-help">
                                          Manual
                                        </Badge>
                                      </Tooltip>
                                    )}
                                    <button
                                      onClick={() => startEditExisting(mapping.id, mapping.target_identifier)}
                                      className="ml-1 p-1 text-gray-400 hover:text-blue-600 transition-colors"
                                      title="Edit mapping"
                                    >
                                      <Edit3 className="w-3 h-3" />
                                    </button>
                                  </div>
                                )
                              ) : inlineEditingId === mapping.id ? (
                              // Show inline edit form
                              <div className="space-y-1">
                                <div className="flex items-center space-x-2">
                                  <input
                                    type="text"
                                    value={inlineEditingValue}
                                    onChange={(e) => handleInlineValueChange(e.target.value)}
                                    placeholder={`Enter ${selectedMappingPlatform === 'github' ? 'GitHub' : 'Slack'} username`}
                                    className={`flex-1 px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 ${
                                      githubValidation?.valid === false 
                                        ? 'border-red-300 focus:ring-red-500' 
                                        : githubValidation?.valid === true
                                        ? 'border-green-300 focus:ring-green-500'
                                        : 'border-gray-300 focus:ring-blue-500'
                                    }`}
                                    autoFocus
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                      saveInlineMapping(mapping.id, mapping.source_identifier)
                                    } else if (e.key === 'Escape') {
                                      cancelInlineEdit()
                                    }
                                  }}
                                />
                                <button
                                  onClick={() => {
                                    if (selectedMappingPlatform === 'github' && githubValidation?.valid !== true) {
                                      toast.error(`Cannot save invalid username: ${githubValidation?.message || 'Please enter a valid GitHub username'}`, {
                                        duration: 4000
                                      })
                                      return
                                    }
                                    saveInlineMapping(mapping.id, mapping.source_identifier)
                                  }}
                                  disabled={savingInlineMapping || validatingGithub}
                                  className={`p-1 hover:opacity-80 disabled:opacity-50 ${
                                    selectedMappingPlatform === 'github' && githubValidation?.valid !== true
                                      ? 'text-gray-400 cursor-not-allowed'
                                      : 'text-green-600 hover:text-green-700'
                                  }`}
                                  title={
                                    selectedMappingPlatform === 'github' && githubValidation?.valid !== true
                                      ? 'Enter a valid GitHub username to save'
                                      : 'Save'
                                  }
                                >
                                  <CheckCircle className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={cancelInlineEdit}
                                  disabled={savingInlineMapping}
                                  className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                                  title="Cancel"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                                </div>
                                {/* Validation feedback */}
                                {(validatingGithub || githubValidation) && (
                                  <div className="flex items-center gap-1 text-xs">
                                    {validatingGithub ? (
                                      <>
                                        <Loader2 className="w-3 h-3 animate-spin" />
                                        <span className="text-gray-500">Validating...</span>
                                      </>
                                    ) : githubValidation?.valid ? (
                                      <>
                                        <CheckCircle className="w-3 h-3 text-green-600" />
                                        <span className="text-green-600">{githubValidation.message}</span>
                                      </>
                                    ) : (
                                      <>
                                        <AlertCircle className="w-3 h-3 text-red-600" />
                                        <span className="text-red-600">{githubValidation?.message}</span>
                                      </>
                                    )}
                                  </div>
                                )}
                              </div>
                            ) : (
                              // Show clickable "Add username" area
                              <button
                                onClick={() => startInlineEdit(mapping.id)}
                                className="w-full text-left px-2 py-1 text-xs text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded border border-dashed border-gray-300 hover:border-blue-300 transition-colors flex items-center gap-2"
                                title={`Click to add ${selectedMappingPlatform === 'github' ? 'GitHub' : 'Slack'} username`}
                              >
                                <Plus className="w-3 h-3 flex-shrink-0" />
                                <span className="truncate">Click to add {selectedMappingPlatform === 'github' ? 'GitHub' : 'Slack'} username</span>
                              </button>
                            )
                            })()}
                          </div>
                          <div className="text-gray-600">
                            {mapping.is_manual ? (
                              <div className="flex items-center gap-1">
                                <Tooltip content="Manual mapping - will show data collection status after running an analysis">
                                  <span className="cursor-help">Manual</span>
                                </Tooltip>
                                <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                                  User Added
                                </Badge>
                              </div>
                            ) : (
                              mapping.mapping_method?.replace('_', ' ') || 'Auto-detected'
                            )}
                          </div>
                        </div>
                      </div>
                      )
                    }) : (
                      <div className="px-4 py-8 text-center text-gray-500">
                        No mapping data available yet. Run an analysis to see mapping results.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

        </SheetContent>
      </Sheet>

      {/* Reusable Mapping Drawer */}
      <MappingDrawer
        isOpen={mappingDrawerOpen}
        onClose={() => setMappingDrawerOpen(false)}
        platform={mappingDrawerPlatform}
        onRefresh={() => {
          // Optional: Refresh any parent data if needed
          console.log(`Refreshed ${mappingDrawerPlatform} mapping data from integrations page`)
        }}
      />

      {/* Manual Mapping Management Dialog */}
      <Dialog open={showManualMappingDialog} onOpenChange={setShowManualMappingDialog}>
        <DialogContent className="max-w-5xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2">
              <Users2 className="w-5 h-5" />
              <span>
                Manage {selectedManualMappingPlatform === 'github' ? 'GitHub' : 'Slack'} Manual Mappings
              </span>
            </DialogTitle>
            <DialogDescription>
              Create and manage manual user mappings for {selectedManualMappingPlatform === 'github' ? 'GitHub' : 'Slack'} platform correlations.
            </DialogDescription>
          </DialogHeader>

          {manualMappingStats && (
            <div className="space-y-6">
              {/* Statistics Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="flex items-center space-x-2">
                    <Database className="w-4 h-4 text-blue-600" />
                    <div>
                      <div className="text-2xl font-bold">{manualMappingStats.total_mappings}</div>
                      <div className="text-sm text-gray-600">Total Mappings</div>
                    </div>
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="flex items-center space-x-2">
                    <Edit3 className="w-4 h-4 text-green-600" />
                    <div>
                      <div className="text-2xl font-bold text-green-600">
                        {manualMappingStats.manual_mappings}
                      </div>
                      <div className="text-sm text-gray-600">Manual</div>
                    </div>
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="flex items-center space-x-2">
                    <Zap className="w-4 h-4 text-purple-600" />
                    <div>
                      <div className="text-2xl font-bold text-purple-600">
                        {manualMappingStats.auto_detected_mappings}
                      </div>
                      <div className="text-sm text-gray-600">Auto-Detected</div>
                    </div>
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <div>
                      <div className="text-2xl font-bold text-green-600">
                        {Math.round(manualMappingStats.verification_rate * 100)}%
                      </div>
                      <div className="text-sm text-gray-600">Verified</div>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Action Buttons */}
              <div className="flex justify-between items-center">
                <Button 
                  onClick={() => {
                    setNewMappingForm({
                      source_platform: 'rootly',
                      source_identifier: '',
                      target_platform: selectedManualMappingPlatform || 'github',
                      target_identifier: ''
                    })
                    setNewMappingDialogOpen(true)
                  }}
                  className="flex items-center space-x-2"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add New Mapping</span>
                </Button>
                
                <Button 
                  variant="outline" 
                  onClick={() => selectedManualMappingPlatform && loadManualMappings(selectedManualMappingPlatform)}
                  disabled={loadingManualMappings}
                >
                  {loadingManualMappings ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <RotateCcw className="w-4 h-4 mr-2" />
                  )}
                  Refresh
                </Button>
              </div>

              {/* Mappings Table */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold">Current Mappings</h3>
                {manualMappings.length > 0 ? (
                  <div className="border rounded-lg overflow-hidden">
                    <div className="bg-gray-50 px-4 py-3 border-b">
                      <div className="grid grid-cols-6 gap-4 text-sm font-medium text-gray-600">
                        <div>Source Platform</div>
                        <div>Source Identifier</div>
                        <div>Target Identifier</div>
                        <div>Type</div>
                        <div>Status</div>
                        <div>Actions</div>
                      </div>
                    </div>
                    <div className="divide-y max-h-64 overflow-y-auto">
                      {manualMappings.map((mapping) => (
                        <div key={mapping.id} className="px-4 py-3">
                          <div className="grid grid-cols-6 gap-4 text-sm items-center">
                            <div className="font-medium">
                              {mapping.source_platform}
                            </div>
                            <div className="truncate" title={mapping.source_identifier}>
                              {mapping.source_identifier}
                            </div>
                            <div className="truncate" title={mapping.target_identifier}>
                              {editingMapping?.id === mapping.id ? (
                                <Input
                                  value={mapping.target_identifier}
                                  onChange={(e) => setEditingMapping({
                                    ...editingMapping,
                                    target_identifier: e.target.value
                                  })}
                                  className="h-8"
                                />
                              ) : (
                                mapping.target_identifier
                              )}
                            </div>
                            <div>
                              <Badge variant={mapping.mapping_type === 'manual' ? 'default' : 'secondary'}>
                                {mapping.mapping_type}
                              </Badge>
                            </div>
                            <div>
                              {mapping.is_verified ? (
                                <Badge variant="default" className="bg-green-100 text-green-800 border-green-200">
                                  <CheckCircle className="w-3 h-3 mr-1" />
                                  Verified
                                </Badge>
                              ) : (
                                <Badge variant="secondary">
                                  <Clock className="w-3 h-3 mr-1" />
                                  Pending
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center space-x-1">
                              {editingMapping?.id === mapping.id ? (
                                <>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => updateManualMapping(mapping.id, editingMapping.target_identifier)}
                                    className="h-8 w-8 p-0 text-green-600 hover:text-green-700"
                                  >
                                    <Check className="w-4 h-4" />
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => setEditingMapping(null)}
                                    className="h-8 w-8 p-0 text-gray-600 hover:text-gray-700"
                                  >
                                    <ArrowLeft className="w-4 h-4" />
                                  </Button>
                                </>
                              ) : (
                                <>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => setEditingMapping(mapping)}
                                    className="h-8 w-8 p-0 text-blue-600 hover:text-blue-700"
                                  >
                                    <Edit3 className="w-4 h-4" />
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => deleteManualMapping(mapping.id)}
                                    className="h-8 w-8 p-0 text-red-600 hover:text-red-700"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </Button>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="border rounded-lg p-8 text-center text-gray-500">
                    <Users2 className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <h3 className="text-lg font-medium mb-2">No manual mappings yet</h3>
                    <p className="text-sm">Create your first manual mapping to get started.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowManualMappingDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* New Manual Mapping Dialog */}
      <Dialog open={newMappingDialogOpen} onOpenChange={setNewMappingDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2">
              <Plus className="w-5 h-5" />
              <span>Create New Manual Mapping</span>
            </DialogTitle>
            <DialogDescription>
              Create a manual mapping between a source platform user and {selectedManualMappingPlatform === 'github' ? 'GitHub' : 'Slack'} account.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Source Platform</label>
                <Select 
                  value={newMappingForm.source_platform} 
                  onValueChange={(value) => setNewMappingForm(prev => ({...prev, source_platform: value}))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select source platform" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="rootly">Rootly</SelectItem>
                    <SelectItem value="pagerduty">PagerDuty</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">Target Platform</label>
                <Select 
                  value={newMappingForm.target_platform} 
                  onValueChange={(value) => setNewMappingForm(prev => ({...prev, target_platform: value}))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select target platform" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="github">GitHub</SelectItem>
                    <SelectItem value="slack">Slack</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Source Identifier</label>
              <Input
                placeholder="e.g., john.doe@company.com or John Doe"
                value={newMappingForm.source_identifier}
                onChange={(e) => setNewMappingForm(prev => ({...prev, source_identifier: e.target.value}))}
              />
              <p className="text-xs text-gray-500">
                The email or name as it appears in {newMappingForm.source_platform} incidents
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Target Identifier</label>
              <Input
                placeholder={
                  newMappingForm.target_platform === 'github' 
                    ? "e.g., johndoe or john-doe-123"
                    : "e.g., U1234567890 or @johndoe"
                }
                value={newMappingForm.target_identifier}
                onChange={(e) => setNewMappingForm(prev => ({...prev, target_identifier: e.target.value}))}
              />
              <p className="text-xs text-gray-500">
                The {newMappingForm.target_platform === 'github' ? 'GitHub username' : 'Slack user ID or @username'}
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setNewMappingDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button 
              onClick={createManualMapping}
              disabled={!newMappingForm.source_identifier || !newMappingForm.target_identifier}
            >
              Create Mapping
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* GitHub Disconnect Confirmation Dialog */}
      <Dialog open={githubDisconnectDialogOpen} onOpenChange={setGithubDisconnectDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disconnect GitHub Integration</DialogTitle>
            <DialogDescription>
              Are you sure you want to disconnect your GitHub integration? 
              This will remove access to your GitHub data and you'll need to reconnect to use GitHub features again.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setGithubDisconnectDialogOpen(false)}
              disabled={isDisconnectingGithub}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleGitHubDisconnect}
              disabled={isDisconnectingGithub}
            >
              {isDisconnectingGithub ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Disconnecting...
                </>
              ) : (
                "Disconnect GitHub"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Slack Disconnect Confirmation Dialog */}
      <Dialog open={slackDisconnectDialogOpen} onOpenChange={setSlackDisconnectDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disconnect Slack Integration</DialogTitle>
            <DialogDescription>
              Are you sure you want to disconnect your Slack integration? 
              This will remove access to your Slack workspace data and you'll need to reconnect to use Slack features again.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setSlackDisconnectDialogOpen(false)}
              disabled={isDisconnectingSlack}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleSlackDisconnect}
              disabled={isDisconnectingSlack}
            >
              {isDisconnectingSlack ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Disconnecting...
                </>
              ) : (
                "Disconnect Slack"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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

      {/* Powered by Rootly AI Footer */}
      <div className="mt-12 pt-8 border-t border-gray-200 text-center">
        <a 
          href="https://rootly.com" 
          target="_blank" 
          rel="noopener noreferrer"
          className="inline-flex flex-col items-center space-y-1 hover:opacity-80 transition-opacity"
        >
          <span className="text-lg text-gray-600">powered by</span>
          <Image 
            src="/images/rootly-ai-logo.png" 
            alt="Rootly AI" 
            width={200} 
            height={80}
            className="h-12 w-auto"
          />
        </a>
      </div>
    </div>
  )
}