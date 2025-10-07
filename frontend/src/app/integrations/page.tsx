"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
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
  ChevronDown,
  Clock,
  Edit3,
  Key,
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
  UserPlus,
  Mail,
  Send,
  MessageSquare,
} from "lucide-react"
import Link from "next/link"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { MappingDrawer } from "@/components/mapping-drawer"
import { NotificationDrawer } from "@/components/notifications"
import ManualSurveyDeliveryModal from "@/components/ManualSurveyDeliveryModal"
import { SlackSurveyTabs } from "@/components/SlackSurveyTabs"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import {
  type Integration,
  type GitHubIntegration,
  type SlackIntegration,
  type PreviewData,
  type IntegrationMapping,
  type MappingStatistics,
  type AnalysisMappingStatistics,
  type ManualMapping,
  type ManualMappingStatistics,
  type UserInfo,
  type RootlyFormData,
  type PagerDutyFormData,
  rootlyFormSchema,
  pagerdutyFormSchema,
  isValidRootlyToken,
  isValidPagerDutyToken,
  API_BASE,
} from "./types"
import * as GithubHandlers from "./handlers/github-handlers"
import * as SlackHandlers from "./handlers/slack-handlers"
import * as TeamHandlers from "./handlers/team-handlers"
import * as IntegrationHandlers from "./handlers/integration-handlers"
import * as OrganizationHandlers from "./handlers/organization-handlers"
import * as AIHandlers from "./handlers/ai-handlers"
import * as MappingHandlers from "./handlers/mapping-handlers"
import * as Utils from "./utils"
import { GitHubIntegrationCard } from "./components/GitHubIntegrationCard"
import { GitHubConnectedCard } from "./components/GitHubConnectedCard"
import { SlackConnectedCard } from "./components/SlackConnectedCard"
import { RootlyIntegrationForm } from "./components/RootlyIntegrationForm"
import { PagerDutyIntegrationForm } from "./components/PagerDutyIntegrationForm"
import { DeleteIntegrationDialog } from "./dialogs/DeleteIntegrationDialog"
import { GitHubDisconnectDialog } from "./dialogs/GitHubDisconnectDialog"
import { SlackDisconnectDialog } from "./dialogs/SlackDisconnectDialog"
import { NewMappingDialog } from "./dialogs/NewMappingDialog"
import { OrganizationManagementDialog } from "./dialogs/OrganizationManagementDialog"

export default function IntegrationsPage() {
  // State management
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loadingRootly, setLoadingRootly] = useState(true)
  const [loadingPagerDuty, setLoadingPagerDuty] = useState(true)
  const [loadingGitHub, setLoadingGitHub] = useState(true)
  const [loadingSlack, setLoadingSlack] = useState(true)
  const [reloadingIntegrations, setReloadingIntegrations] = useState(false)
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  const [activeTab, setActiveTab] = useState<"rootly" | "pagerduty" | null>(null)
  const [backUrl, setBackUrl] = useState<string>('/dashboard')
  const [selectedOrganization, setSelectedOrganization] = useState<string>("")
  
  // GitHub/Slack integration state
  const [githubIntegration, setGithubIntegration] = useState<GitHubIntegration | null>(null)
  const [slackIntegration, setSlackIntegration] = useState<SlackIntegration | null>(null)
  const [activeEnhancementTab, setActiveEnhancementTab] = useState<"github" | "slack" | null>(null)

  // Slack feature selection for OAuth
  const [enableSlackSurvey, setEnableSlackSurvey] = useState(true) // Default both enabled
  const [enableSlackSentiment, setEnableSlackSentiment] = useState(true)
  
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

  // Invite modal state
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState("manager")
  const [isInviting, setIsInviting] = useState(false)

  // Organization members and invitations state
  const [orgMembers, setOrgMembers] = useState([])
  const [pendingInvitations, setPendingInvitations] = useState([])
  const [loadingOrgData, setLoadingOrgData] = useState(false)

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
  const [slackSurveyDisconnectDialogOpen, setSlackSurveyDisconnectDialogOpen] = useState(false)
  const [slackSurveyConfirmDisconnectOpen, setSlackSurveyConfirmDisconnectOpen] = useState(false)
  const [isDisconnectingGithub, setIsDisconnectingGithub] = useState(false)
  const [isDisconnectingSlack, setIsDisconnectingSlack] = useState(false)
  const [isDisconnectingSlackSurvey, setIsDisconnectingSlackSurvey] = useState(false)
  const [isConnectingSlackOAuth, setIsConnectingSlackOAuth] = useState(false)
  const [slackPermissions, setSlackPermissions] = useState<any>(null)
  const [isLoadingPermissions, setIsLoadingPermissions] = useState(false)

  // Team members state
  const [teamMembers, setTeamMembers] = useState<any[]>([])
  const [loadingTeamMembers, setLoadingTeamMembers] = useState(false)
  const [teamMembersError, setTeamMembersError] = useState<string | null>(null)
  const [syncedUsers, setSyncedUsers] = useState<any[]>([])
  const [loadingSyncedUsers, setLoadingSyncedUsers] = useState(false)
  const [showSyncedUsers, setShowSyncedUsers] = useState(false)
  const [teamMembersDrawerOpen, setTeamMembersDrawerOpen] = useState(false)

  // Manual survey delivery modal state
  const [showManualSurveyModal, setShowManualSurveyModal] = useState(false)

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
    loadAllIntegrationsOptimized()
    
    // 🚨 ROLLBACK: Individual loading functions (fallback disabled)
    // loadRootlyIntegrations()
    // loadPagerDutyIntegrations() 
    // loadGitHubIntegration()
    // loadSlackIntegration()
    loadLlmConfig()
    
    // Load saved organization preference
    const savedOrg = localStorage.getItem('selected_organization')
    // Accept both numeric IDs and beta string IDs (like "beta-rootly")
    if (savedOrg) {
      setSelectedOrganization(savedOrg)
    }

    // Load user info from localStorage first for immediate display
    const userName = localStorage.getItem('user_name')
    const userEmail = localStorage.getItem('user_email')
    const userAvatar = localStorage.getItem('user_avatar')
    const userRole = localStorage.getItem('user_role')
    const userId = localStorage.getItem('user_id')
    const userOrgId = localStorage.getItem('user_organization_id')

    // Set initial state from localStorage
    if (userName && userEmail) {
      setUserInfo({
        name: userName,
        email: userEmail,
        avatar: userAvatar || undefined,
        role: userRole || 'member',
        id: userId ? parseInt(userId) : undefined,
        organization_id: userOrgId ? parseInt(userOrgId) : undefined
      })
    }

    // Then fetch fresh data in background to update if needed
    const authToken = localStorage.getItem('auth_token')
    if (authToken) {
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
      fetch(`${API_BASE}/auth/user/me`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache'
        }
      })
      .then(response => {
        if (!response.ok) throw new Error('Failed to fetch')
        return response.json()
      })
      .then(userData => {
        if (userData.name && userData.email) {
          setUserInfo({
            name: userData.name,
            email: userData.email,
            avatar: userData.avatar || undefined,
            role: userData.role || 'member',
            id: userData.id,
            organization_id: userData.organization_id
          })
          // Update localStorage with fresh data
          localStorage.setItem('user_name', userData.name)
          localStorage.setItem('user_email', userData.email)
          localStorage.setItem('user_role', userData.role || 'member')
          if (userData.avatar) localStorage.setItem('user_avatar', userData.avatar)
          if (userData.id) localStorage.setItem('user_id', userData.id.toString())
          if (userData.organization_id) localStorage.setItem('user_organization_id', userData.organization_id.toString())
        }
      })
      .catch(error => {
        // Silently fail - we already loaded from localStorage
      })
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

  // Load organization data when invite modal opens
  useEffect(() => {
    if (showInviteModal) {
      loadOrganizationData()
    }
  }, [showInviteModal])

  // Handle Slack OAuth success redirect
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const slackConnected = urlParams.get('slack_connected')
    const workspace = urlParams.get('workspace')
    const status = urlParams.get('status')

    // Check auth token after OAuth redirect
    const authToken = localStorage.getItem('auth_token')

    // Debug: Log all URL parameters (persist across redirects)
    const debugInfo = {
      fullUrl: window.location.href,
      search: window.location.search,
      slackConnected,
      workspace,
      status,
      hasAuthToken: !!authToken,
      allParams: Object.fromEntries(urlParams.entries()),
      timestamp: new Date().toISOString()
    }

    // Store in sessionStorage for persistence
    sessionStorage.setItem('slack_oauth_debug', JSON.stringify(debugInfo))

    // Add global debug function for manual checking
    ;(window as any).getSlackOAuthDebug = () => {
      const stored = sessionStorage.getItem('slack_oauth_debug')
      if (stored) {
        const parsed = JSON.parse(stored)
        return parsed
      }
      return null
    }

    // Check if we're returning from OAuth and set loading state
    const isReturningFromOAuth = localStorage.getItem('slack_oauth_in_progress')
    if (isReturningFromOAuth) {
      setIsConnectingSlackOAuth(true)

      // If we have the OAuth in progress flag but no success params yet,
      // it means the redirect is still happening or failed silently
      if (slackConnected !== 'true' && slackConnected !== 'false') {
        // Keep showing loading for a bit, then timeout
        setTimeout(() => {
          const stillInProgress = localStorage.getItem('slack_oauth_in_progress')
          if (stillInProgress && !window.location.search.includes('slack_connected')) {
            localStorage.removeItem('slack_oauth_in_progress')
            setIsConnectingSlackOAuth(false)
            toast.warning('OAuth redirect timed out', {
              description: 'Please try connecting again.',
            })
          }
        }, 10000) // 10 second timeout
      }
    }

    if (slackConnected === 'true' && workspace) {
      // Show loading toast immediately
      const loadingToastId = toast.loading('Verifying Slack connection...', {
        description: 'Please wait while we confirm your workspace connection.',
      })

      // Clean up URL parameters
      const newUrl = window.location.pathname
      window.history.replaceState({}, '', newUrl)

      // Poll for connection status with retries
      let retries = 0
      const maxRetries = 15
      const pollInterval = 500

      const checkConnection = async () => {
        try {
          retries++

          // Check if Slack is now connected
          const authToken = localStorage.getItem('auth_token')
          if (!authToken) return

          const response = await fetch(`${API_BASE}/integrations/slack/status`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
          })

          if (response.ok) {
            const data = await response.json()
            if (data.connected) {
              // Update Slack integration state directly without reloading other cards
              setSlackIntegration(data.integration)
              // Update cache
              localStorage.setItem('slack_integration', JSON.stringify(data))
              localStorage.setItem('all_integrations_timestamp', Date.now().toString())

              // Clear OAuth loading state
              localStorage.removeItem('slack_oauth_in_progress')
              setIsConnectingSlackOAuth(false)

              toast.dismiss(loadingToastId)
              if (status === 'pending_user_association') {
                toast.success(`🎉 Slack app installed successfully!`, {
                  description: `Connected to "${decodeURIComponent(workspace)}" workspace. The /burnout-survey command is now available.`,
                  duration: 6000,
                })
              } else {
                toast.success(`🎉 Slack integration connected!`, {
                  description: `Successfully connected to "${decodeURIComponent(workspace)}" workspace.`,
                  duration: 5000,
                })
              }
              return
            }
          }

          // Not connected yet, retry if we haven't exceeded max retries
          if (retries < maxRetries) {
            setTimeout(checkConnection, pollInterval)
          } else {
            // Max retries reached, show warning
            localStorage.removeItem('slack_oauth_in_progress')
            setIsConnectingSlackOAuth(false)
            toast.dismiss(loadingToastId)
            toast.warning('Connection verification timed out', {
              description: 'Your Slack workspace was added, but verification took longer than expected. Try refreshing the page.',
              duration: 8000,
            })
          }
        } catch (error) {
          if (retries < maxRetries) {
            setTimeout(checkConnection, pollInterval)
          } else {
            localStorage.removeItem('slack_oauth_in_progress')
            setIsConnectingSlackOAuth(false)
            toast.dismiss(loadingToastId)
            toast.error('Failed to verify connection', {
              description: 'Please refresh the page to check your Slack connection status.',
            })
          }
        }
      }

      // Start checking immediately
      checkConnection()
    } else if (slackConnected === 'false') {
      // Clear OAuth loading state
      localStorage.removeItem('slack_oauth_in_progress')
      setIsConnectingSlackOAuth(false)

      // Show error toast
      const errorParam = urlParams.get('error')
      const errorMessage = errorParam ? decodeURIComponent(errorParam) : 'Unknown error occurred'

      toast.error('Failed to connect Slack', {
        description: errorMessage,
        duration: 8000,
      })

      // Clean up URL parameters
      const newUrl = window.location.pathname
      window.history.replaceState({}, '', newUrl)
    }
  }, [])

  // Load each provider independently for better UX
  const loadRootlyIntegrations = async (forceRefresh = false) => {
    return IntegrationHandlers.loadRootlyIntegrations(forceRefresh, setIntegrations, setLoadingRootly)
  }

  const loadPagerDutyIntegrations = async (forceRefresh = false) => {
    return IntegrationHandlers.loadPagerDutyIntegrations(forceRefresh, setIntegrations, setLoadingPagerDuty)
  }

  const loadGitHubIntegration = async (forceRefresh = false) => {
    return GithubHandlers.loadGitHubIntegration(forceRefresh, setGithubIntegration, setLoadingGitHub)
  }

  const loadSlackIntegration = async (forceRefresh = false) => {
    return SlackHandlers.loadSlackIntegration(forceRefresh, setSlackIntegration, setLoadingSlack)
  }

  // ✨ PHASE 1 OPTIMIZATION: Instant cache loading with background refresh
  const [refreshingInBackground, setRefreshingInBackground] = useState(false)
  
  // Synchronous cache reading for instant display
  const loadFromCacheSync = () => {
    try {
      const cachedIntegrations = localStorage.getItem('all_integrations')
      const cachedGithub = localStorage.getItem('github_integration')
      const cachedSlack = localStorage.getItem('slack_integration')
      
      
      if (cachedIntegrations) {
        const parsedIntegrations = JSON.parse(cachedIntegrations)
        setIntegrations(parsedIntegrations)
      }
      
      if (cachedGithub) {
        const githubData = JSON.parse(cachedGithub)
        setGithubIntegration(githubData.connected ? githubData.integration : null)
      }
      
      if (cachedSlack) {
        const slackData = JSON.parse(cachedSlack)
        setSlackIntegration(slackData.integration)
      }
      
      const hasAllCache = !!(cachedIntegrations && cachedGithub && cachedSlack)
      return hasAllCache
    } catch (error) {
      return false
    }
  }
  
  // Background refresh function (non-blocking) - does NOT affect loading states
  const refreshInBackground = async () => {
    setRefreshingInBackground(true)
    try {
      await loadAllIntegrationsAPIBackground()
    } catch (error) {
      console.error('Background refresh failed:', error)
    } finally {
      setRefreshingInBackground(false)
    }
  }

  // Invite function
  const handleInvite = async () => {
    return OrganizationHandlers.handleInvite(
      inviteEmail,
      inviteRole,
      setIsInviting,
      setInviteEmail,
      setInviteRole,
      setShowInviteModal,
      loadOrganizationData
    )
  }

  // Handle role change for organization members
  const handleRoleChange = async (userId: number, newRole: string) => {
    return OrganizationHandlers.handleRoleChange(userId, newRole, loadOrganizationData)
  }

  // Load organization members and pending invitations
  const loadOrganizationData = async () => {
    return OrganizationHandlers.loadOrganizationData(
      setLoadingOrgData,
      setOrgMembers,
      setPendingInvitations
    )
  }

  // Background API loading - does NOT change loading states (for silent refresh)
  const loadAllIntegrationsAPIBackground = async () => {
    try {
      const authToken = localStorage.getItem('auth_token')
      if (!authToken) {
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

    } catch (error) {
    }
  }
  
  // Check if cache is stale (older than 5 minutes)
  const isCacheStale = Utils.isCacheStale
  
  // New optimized loading function with instant cache + background refresh
  const loadAllIntegrationsOptimized = async (forceRefresh = false) => {
    
    try {
      // Step 1: Always show cached data instantly (0ms)
      const hasCachedData = loadFromCacheSync()
      
      // Step 2: If we have cached data and it's not forced refresh, show it immediately
      if (hasCachedData && !forceRefresh) {
        setLoadingRootly(false) // Hide skeleton immediately
        setLoadingPagerDuty(false)
        setLoadingGitHub(false)
        setLoadingSlack(false)
        
        // Step 3: Check if cache is stale and refresh in background if needed
        const cacheIsStale = isCacheStale()
        if (cacheIsStale) {
          // Non-blocking background refresh
          setTimeout(() => refreshInBackground(), 100)
        } else {
        }
        return
      }
      
      // Step 4: If no cache or forced refresh, fall back to normal loading
      await loadAllIntegrationsAPI()
    } catch (error) {
      // Fallback: set loading states to false to prevent infinite loading
      setLoadingRootly(false)
      setLoadingPagerDuty(false)
      setLoadingGitHub(false)
      setLoadingSlack(false)
    }
  }
  
  // Original API loading logic (extracted for reuse)
  const loadAllIntegrationsAPI = async () => {
    // Set individual loading states to true
    setLoadingRootly(true)
    setLoadingPagerDuty(true)
    setLoadingGitHub(true)
    setLoadingSlack(true)
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
      toast.error("Failed to load integrations. Please try refreshing the page.")
    } finally {
      // Set all integration loading states to false
      setLoadingRootly(false)
      setLoadingPagerDuty(false)
      setLoadingGitHub(false)
      setLoadingSlack(false)
    }
  }

  const loadLlmConfig = async () => {
    return AIHandlers.loadLlmConfig(
      setLoadingLlmConfig,
      setLlmConfig,
      setLlmProvider,
      setLlmModel
    )
  }

  const handleConnectAI = async () => {
    return AIHandlers.handleConnectAI(
      llmToken,
      llmProvider,
      llmModel,
      setIsConnectingAI,
      setTokenError,
      setLlmConfig,
      setLlmToken
    )
  }

  const handleDisconnectAI = async () => {
    return AIHandlers.handleDisconnectAI(setLlmConfig)
  }

  const testConnection = async (platform: "rootly" | "pagerduty", token: string) => {
    return IntegrationHandlers.testConnection(
      platform,
      token,
      setIsTestingConnection,
      setConnectionStatus,
      setPreviewData,
      setDuplicateInfo
    )
  }

  const addIntegration = async (platform: "rootly" | "pagerduty") => {
    const form = platform === 'rootly' ? rootlyForm : pagerdutyForm
    return IntegrationHandlers.addIntegration(
      platform,
      previewData,
      form,
      integrations,
      setIsAddingRootly,
      setIsAddingPagerDuty,
      setConnectionStatus,
      setPreviewData,
      setAddingPlatform,
      setReloadingIntegrations,
      loadRootlyIntegrations,
      loadPagerDutyIntegrations
    )
  }

  const deleteIntegration = async () => {
    if (!integrationToDelete) return
    return IntegrationHandlers.deleteIntegration(
      integrationToDelete,
      integrations,
      setIsDeleting,
      setIntegrations,
      setDeleteDialogOpen,
      setIntegrationToDelete
    )
  }

  const updateIntegrationName = async (integration: Integration, newName: string) => {
    return IntegrationHandlers.updateIntegrationName(
      integration,
      newName,
      setSavingIntegrationId,
      setIntegrations,
      setEditingIntegration
    )
  }


  const copyToClipboard = async (text: string) => {
    return Utils.copyToClipboard(text, setCopied)
  }

  // GitHub integration handlers
  const handleGitHubConnect = async (token: string) => {
    return GithubHandlers.handleGitHubConnect(
      token,
      setIsConnectingGithub,
      setGithubToken,
      setActiveEnhancementTab,
      loadGitHubIntegration
    )
  }

  const handleGitHubDisconnect = async () => {
    return GithubHandlers.handleGitHubDisconnect(
      setIsDisconnectingGithub,
      setGithubDisconnectDialogOpen,
      loadGitHubIntegration
    )
  }

  const handleGitHubTest = async () => {
    return GithubHandlers.handleGitHubTest()
  }

  // Slack integration handlers
  const handleSlackConnect = async (webhookUrl: string, botToken: string) => {
    return SlackHandlers.handleSlackConnect(
      webhookUrl,
      botToken,
      setIsConnectingSlack,
      setSlackWebhookUrl,
      setSlackBotToken,
      setActiveEnhancementTab,
      loadSlackIntegration
    )
  }

  const handleSlackDisconnect = async () => {
    return SlackHandlers.handleSlackDisconnect(
      setIsDisconnectingSlack,
      setSlackDisconnectDialogOpen,
      loadSlackIntegration
    )
  }

  const handleSlackTest = async () => {
    return SlackHandlers.handleSlackTest(setSlackPermissions, setSlackIntegration)
  }

  const loadSlackPermissions = async () => {
    return SlackHandlers.loadSlackPermissions(slackIntegration, setIsLoadingPermissions, setSlackPermissions)
  }

  // Mapping data handlers
  // Function to open the reusable MappingDrawer
  const openMappingDrawer = (platform: 'github' | 'slack') => {
    return Utils.openMappingDrawer(platform, setMappingDrawerPlatform, setMappingDrawerOpen)
  }

  const loadMappingData = async (platform: 'github' | 'slack') => {
    return MappingHandlers.loadMappingData(
      platform,
      showMappingDialog,
      setLoadingMappingData,
      setSelectedMappingPlatform,
      setMappingData,
      setMappingStats,
      setAnalysisMappingStats,
      setCurrentAnalysisId,
      setShowMappingDialog
    )
  }

  // Fetch team members from selected organization
  const fetchTeamMembers = async () => {
    return TeamHandlers.fetchTeamMembers(
      selectedOrganization,
      setLoadingTeamMembers,
      setTeamMembersError,
      setTeamMembers,
      setTeamMembersDrawerOpen
    )
  }

  // Sync users to UserCorrelation table
  const syncUsersToCorrelation = async () => {
    return TeamHandlers.syncUsersToCorrelation(
      selectedOrganization,
      setLoadingTeamMembers,
      setTeamMembersError,
      fetchTeamMembers,
      fetchSyncedUsers
    )
  }

  // Sync Slack user IDs to UserCorrelation records
  const syncSlackUserIds = async () => {
    return TeamHandlers.syncSlackUserIds(setLoadingTeamMembers, fetchSyncedUsers)
  }

  // Fetch synced users from database
  const fetchSyncedUsers = async (showToast = true, autoSync = true) => {
    return TeamHandlers.fetchSyncedUsers(
      selectedOrganization,
      setLoadingSyncedUsers,
      setSyncedUsers,
      setShowSyncedUsers,
      setTeamMembersDrawerOpen,
      syncUsersToCorrelation,
      showToast,
      autoSync
    )
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
    return MappingHandlers.validateGithubUsername(
      username,
      setValidatingGithub,
      setGithubValidation
    )
  }
  
  // Sorting function
  const handleSort = (field: 'email' | 'status' | 'data' | 'method') => {
    return Utils.handleSort(field, sortField, sortDirection, setSortField, setSortDirection)
  }

  // Filter and sort mappings
  const filteredMappings = Utils.filterMappings(mappingData, showOnlyFailed)
  const sortedMappings = Utils.sortMappings(filteredMappings, sortField, sortDirection)

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
    return MappingHandlers.saveEditedMapping(
      mappingId,
      email,
      inlineEditingValue,
      selectedMappingPlatform,
      githubValidation,
      setSavingInlineMapping,
      setMappingData,
      setInlineEditingId,
      setInlineEditingValue,
      setGithubValidation,
      validateGithubUsername
    )
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
    return MappingHandlers.saveInlineMapping(
      mappingId,
      email,
      inlineEditingValue,
      selectedMappingPlatform,
      githubValidation,
      setSavingInlineMapping,
      setMappingData,
      setInlineEditingId,
      setInlineEditingValue,
      validateGithubUsername
    )
  }

  // Manual mapping handlers
  const loadManualMappings = async (platform: 'github' | 'slack') => {
    return MappingHandlers.loadManualMappings(
      platform,
      setLoadingManualMappings,
      setSelectedManualMappingPlatform,
      setManualMappings,
      setManualMappingStats,
      setShowManualMappingDialog
    )
  }

  const createManualMapping = async () => {
    return MappingHandlers.createManualMapping(
      newMappingForm,
      showManualMappingDialog,
      selectedManualMappingPlatform,
      setNewMappingDialogOpen,
      setNewMappingForm,
      loadManualMappings
    )
  }

  const updateManualMapping = async (mappingId: number, targetIdentifier: string) => {
    return MappingHandlers.updateManualMapping(
      mappingId,
      targetIdentifier,
      showManualMappingDialog,
      selectedManualMappingPlatform,
      setEditingMapping,
      loadManualMappings
    )
  }

  const deleteManualMapping = async (mappingId: number) => {
    return MappingHandlers.deleteManualMapping(
      mappingId,
      showManualMappingDialog,
      selectedManualMappingPlatform,
      loadManualMappings
    )
  }

  const filteredIntegrations = integrations.filter(integration => {
    if (activeTab === null) return true // Show all integrations when no tab selected
    return integration.platform === activeTab
  })

  const rootlyCount = integrations.filter(i => i.platform === 'rootly').length
  const pagerdutyCount = integrations.filter(i => i.platform === 'pagerduty').length

  // Helper booleans to distinguish between Slack Survey (OAuth) and Enhanced Integration (webhook/token)
  // Note: Backend returns ONE integration at a time - either OAuth or manual, not both simultaneously
  // Users must choose one integration type. If they want to switch, they disconnect one and connect the other.
  const hasSlackSurvey = slackIntegration?.connection_type === 'oauth'
  const hasSlackEnhanced = slackIntegration && slackIntegration.connection_type !== 'oauth'

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-slate-200 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
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

          <div className="flex items-center space-x-4">
            {/* Notifications */}
            <NotificationDrawer />

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
                      <div className="text-xs text-gray-400 mt-1 capitalize">
                        {userInfo.role?.replace('_', ' ') || 'Member'}
                      </div>
                    </div>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  {/* Temporarily hidden for beta - everyone is an org admin */}
                  {/* {(userInfo.role === 'org_admin' || userInfo.role === 'super_admin') && (
                    <>
                      <DropdownMenuItem
                        className="px-2 py-1.5 cursor-pointer"
                        onClick={() => setShowInviteModal(true)}
                      >
                        <UserPlus className="w-4 h-4 mr-2" />
                        Org Management
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                    </>
                  )} */}
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
                  // Reset connection state when switching platforms
                  setConnectionStatus('idle')
                  setPreviewData(null)
                  setDuplicateInfo(null)
                  setTokenError(null)
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
          {(loadingPagerDuty ? (
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
                // Reset connection state when switching platforms
                setConnectionStatus('idle')
                setPreviewData(null)
                setDuplicateInfo(null)
                setTokenError(null)
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
          ))}
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
              <RootlyIntegrationForm
                form={rootlyForm}
                onTest={testConnection}
                onAdd={() => addIntegration('rootly')}
                connectionStatus={connectionStatus}
                previewData={previewData}
                duplicateInfo={duplicateInfo}
                isTestingConnection={isTestingConnection}
                isAdding={isAddingRootly}
                isValidToken={isValidRootlyToken}
                onCopyToken={copyToClipboard}
                copied={copied}
              />
            )}

            {/* Add PagerDuty Integration Form */}
            {addingPlatform === 'pagerduty' && (
              <PagerDutyIntegrationForm
                form={pagerdutyForm}
                onTest={testConnection}
                onAdd={() => addIntegration('pagerduty')}
                connectionStatus={connectionStatus}
                previewData={previewData}
                duplicateInfo={duplicateInfo}
                isTestingConnection={isTestingConnection}
                isAdding={isAddingPagerDuty}
                isValidToken={isValidPagerDutyToken}
                onCopyToken={copyToClipboard}
                copied={copied}
              />
            )}

            {/* Existing Integrations */}
            {(activeTab === null && !selectedOrganization && integrations.length === 0) ? (
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
            ) : integrations.length > 0 && filteredIntegrations.length > 0 ? (
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

                  {/* Skeleton card while reloading integrations */}
                  {reloadingIntegrations && (
                    <div className="p-6 rounded-lg border border-gray-200 bg-gray-50 animate-pulse">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-3">
                          <div className="w-6 h-6 bg-gray-300 rounded"></div>
                          <div className="h-5 w-32 bg-gray-300 rounded"></div>
                        </div>
                        <div className="w-16 h-6 bg-gray-300 rounded"></div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
                        <div className="flex items-start space-x-2">
                          <div className="w-4 h-4 mt-0.5 bg-gray-300 rounded"></div>
                          <div>
                            <div className="h-4 w-20 bg-gray-300 rounded mb-2"></div>
                            <div className="h-4 w-24 bg-gray-300 rounded"></div>
                          </div>
                        </div>
                        <div className="flex items-start space-x-2">
                          <div className="w-4 h-4 mt-0.5 bg-gray-300 rounded"></div>
                          <div>
                            <div className="h-4 w-16 bg-gray-300 rounded mb-2"></div>
                            <div className="h-4 w-8 bg-gray-300 rounded"></div>
                          </div>
                        </div>
                        <div className="flex items-start space-x-2">
                          <div className="w-4 h-4 mt-0.5 bg-gray-300 rounded"></div>
                          <div>
                            <div className="h-4 w-12 bg-gray-300 rounded mb-2"></div>
                            <div className="h-4 w-16 bg-gray-300 rounded"></div>
                          </div>
                        </div>
                      </div>

                      {/* Loading indicator */}
                      <div className="flex items-center justify-center mt-4 pt-4 border-t border-gray-300">
                        <Loader2 className="w-4 h-4 animate-spin mr-2 text-gray-400" />
                        <span className="text-sm text-gray-500">Adding integration...</span>
                      </div>
                    </div>
                  )}
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

        {/* User-Reported Connection Section */}
        <div className="mt-16 space-y-8">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-slate-900 mb-3">User-Reported Insights</h2>
            <p className="text-lg text-slate-600 mb-2">
              Enable team members to share their own burnout insights
            </p>
            <p className="text-slate-500">
              Collect direct feedback through Slack commands and web surveys
            </p>
          </div>

          <div className="max-w-2xl mx-auto space-y-6">
            {/* Slack Survey with Tabs */}
            <Card className="border-2 border-purple-200 bg-purple-50/30">
              {loadingSlack ? (
                <>
                  <CardHeader className="pb-4">
                    <div className="flex items-center justify-between animate-pulse">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-gray-200 rounded-lg"></div>
                        <div className="space-y-2">
                          <div className="w-32 h-5 bg-gray-200 rounded"></div>
                          <div className="w-64 h-4 bg-gray-200 rounded"></div>
                        </div>
                      </div>
                      <div className="w-24 h-9 bg-gray-200 rounded-lg"></div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-6 animate-pulse">
                      {/* Skeleton for "Connect Slack Workspace" button */}
                      <div className="flex flex-col items-center justify-center py-8 space-y-3">
                        <div className="w-64 h-12 bg-gray-200 rounded-lg"></div>
                        <div className="w-96 h-4 bg-gray-200 rounded"></div>
                      </div>

                      {/* Skeleton for "How it works" section */}
                      <div className="space-y-4">
                        <div className="w-32 h-6 bg-gray-200 rounded"></div>
                        <div className="space-y-4">
                          <div className="flex items-start space-x-3">
                            <div className="w-8 h-8 bg-gray-200 rounded-full flex-shrink-0"></div>
                            <div className="flex-1 space-y-2">
                              <div className="w-3/4 h-4 bg-gray-200 rounded"></div>
                            </div>
                          </div>
                          <div className="flex items-start space-x-3">
                            <div className="w-8 h-8 bg-gray-200 rounded-full flex-shrink-0"></div>
                            <div className="flex-1 space-y-2">
                              <div className="w-2/3 h-4 bg-gray-200 rounded"></div>
                              <div className="w-full h-20 bg-gray-200 rounded-lg mt-2"></div>
                            </div>
                          </div>
                          <div className="flex items-start space-x-3">
                            <div className="w-8 h-8 bg-gray-200 rounded-full flex-shrink-0"></div>
                            <div className="flex-1 space-y-2">
                              <div className="w-3/4 h-4 bg-gray-200 rounded"></div>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Skeleton for footer */}
                      <div className="flex items-center justify-between pt-4 border-t">
                        <div className="flex items-center space-x-2">
                          <div className="w-4 h-4 bg-gray-200 rounded"></div>
                          <div className="w-48 h-4 bg-gray-200 rounded"></div>
                        </div>
                      <div className="flex items-center space-x-2">
                        <div className="w-4 h-4 bg-gray-200 rounded"></div>
                        <div className="w-40 h-4 bg-gray-200 rounded"></div>
                      </div>
                    </div>
                  </div>
                  </CardContent>
                </>
              ) : (
                <>
                  <CardHeader className="pb-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
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
                          <CardTitle className="text-lg text-gray-900">Slack Survey</CardTitle>
                          <p className="text-sm text-gray-600">Let team members report burnout scores directly in Slack</p>
                        </div>
                      </div>

                      {/* Slack Connection Status */}
                      {hasSlackSurvey ? (
                        <button
                          onClick={() => setSlackSurveyDisconnectDialogOpen(true)}
                          disabled={isDisconnectingSlackSurvey}
                          className="inline-flex items-center space-x-2 bg-green-100 text-green-800 px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isDisconnectingSlackSurvey ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              <span>Disconnecting...</span>
                            </>
                          ) : (
                            <>
                              <CheckCircle className="w-4 h-4" />
                              <span>Connected</span>
                            </>
                          )}
                        </button>
                      ) : process.env.NEXT_PUBLIC_SLACK_CLIENT_ID ? (
                        <div className="flex flex-col items-end space-y-3">
                          {/* Feature Selection Checkboxes */}
                          <div className="flex flex-col space-y-2 text-sm">
                            <label className="flex items-center space-x-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={enableSlackSurvey}
                                onChange={(e) => setEnableSlackSurvey(e.target.checked)}
                                className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                              />
                              <span className="text-gray-700">Enable Survey Delivery (/burnout-survey)</span>
                            </label>
                            <label className="flex items-center space-x-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={enableSlackSentiment}
                                onChange={(e) => setEnableSlackSentiment(e.target.checked)}
                                className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                              />
                              <span className="text-gray-700">Enable Sentiment Analysis (Read Messages)</span>
                            </label>
                          </div>

                          <Button
                            onClick={() => {
                              // Validate at least one feature is selected
                              if (!enableSlackSurvey && !enableSlackSentiment) {
                                toast.error('Please select at least one feature to enable')
                                return
                              }

                              const clientId = process.env.NEXT_PUBLIC_SLACK_CLIENT_ID
                              const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL

                              if (!backendUrl) {
                                toast.error('Backend URL not configured. Please contact support.')
                                return
                              }

                              // Build dynamic scopes based on feature selection
                              const scopesArray = []
                              if (enableSlackSurvey) {
                                scopesArray.push('commands', 'chat:write', 'team:read')
                              }
                              if (enableSlackSentiment) {
                                scopesArray.push('channels:history', 'channels:read', 'users:read', 'users:read.email')
                              }
                              const scopes = Array.from(new Set(scopesArray)).join(',') // Remove duplicates

                              // Include feature flags in state parameter
                              const redirectUri = `${backendUrl}/integrations/slack/oauth/callback`
                              const currentUser = userInfo
                              const stateData = {
                                orgId: currentUser?.organization_id,
                                userId: currentUser?.id,
                                email: currentUser?.email,
                                enableSurvey: enableSlackSurvey,
                                enableSentiment: enableSlackSentiment
                              }
                              const state = currentUser ? btoa(JSON.stringify(stateData)) : ''

                              const slackAuthUrl = `https://slack.com/oauth/v2/authorize?client_id=${clientId}&scope=${scopes}&redirect_uri=${encodeURIComponent(redirectUri)}&state=${encodeURIComponent(state)}`

                              // Show loading state and persist in localStorage
                              setIsConnectingSlackOAuth(true)
                              localStorage.setItem('slack_oauth_in_progress', 'true')
                              toast.info('Redirecting to Slack...')

                              // Use window.location to navigate in same tab so auth token is preserved
                              window.location.href = slackAuthUrl
                            }}
                            disabled={isConnectingSlackOAuth || (!enableSlackSurvey && !enableSlackSentiment)}
                            className="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {isConnectingSlackOAuth ? (
                              <span className="flex items-center space-x-2">
                                <Loader2 className="w-4 h-4 animate-spin" />
                                <span>Connecting...</span>
                              </span>
                            ) : (
                              'Add to Slack'
                            )}
                          </Button>
                        </div>
                      ) : (
                        <div className="inline-flex items-center space-x-2 bg-gray-100 text-gray-500 px-4 py-2 rounded-lg text-sm font-medium">
                          <svg className="w-4 h-4" viewBox="0 0 124 124" fill="currentColor">
                            <path d="M26.3996 78.2003C26.3996 84.7003 21.2996 89.8003 14.7996 89.8003C8.29961 89.8003 3.19961 84.7003 3.19961 78.2003C3.19961 71.7003 8.29961 66.6003 14.7996 66.6003H26.3996V78.2003Z"/>
                            <path d="M32.2996 78.2003C32.2996 71.7003 37.3996 66.6003 43.8996 66.6003C50.3996 66.6003 55.4996 71.7003 55.4996 78.2003V109.2C55.4996 115.7 50.3996 120.8 43.8996 120.8C37.3996 120.8 32.2996 115.7 32.2996 109.2V78.2003Z"/>
                            <path d="M43.8996 26.4003C37.3996 26.4003 32.2996 21.3003 32.2996 14.8003C32.2996 8.30026 37.3996 3.20026 43.8996 3.20026C50.3996 3.20026 55.4996 8.30026 55.4996 14.8003V26.4003H43.8996Z"/>
                          </svg>
                          <span>Slack App Not Configured</span>
                        </div>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <SlackSurveyTabs
                    slackIntegration={hasSlackSurvey ? slackIntegration : null}
                    selectedOrganization={selectedOrganization}
                    integrations={integrations}
                    teamMembers={teamMembers}
                    loadingTeamMembers={loadingTeamMembers}
                    loadingSyncedUsers={loadingSyncedUsers}
                    userInfo={userInfo}
                    fetchTeamMembers={fetchTeamMembers}
                    syncUsersToCorrelation={syncUsersToCorrelation}
                    fetchSyncedUsers={fetchSyncedUsers}
                    setShowManualSurveyModal={setShowManualSurveyModal}
                    loadSlackPermissions={loadSlackPermissions}
                    toast={toast}
                  />
                  </CardContent>
                </>
              )}
            </Card>

            {/* OLD SLACK SURVEY CONTENT - TO BE REMOVED AFTER TESTING */}
            <Card className="border-2 border-purple-200 bg-purple-50/30" style={{display: 'none'}}>
              <CardHeader className="pb-4">
                <div className="text-sm text-gray-500">Old content hidden - remove after testing</div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-white rounded-lg border p-4 space-y-4">
                  {!process.env.NEXT_PUBLIC_SLACK_CLIENT_ID && (
                    <div className="text-center py-2">
                      <p className="text-sm text-gray-600 mb-4">
                        The official Slack app is not currently configured. You can still use the manual Slack integration below to connect your workspace with webhook URL and bot token.
                      </p>
                    </div>
                  )}

                  <div className="border-t pt-4">
                    <h4 className="font-medium text-gray-900 mb-3">How it works:</h4>
                    <div className="space-y-3">
                      <div className="flex items-start space-x-3">
                        <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span className="text-green-600 text-xs font-bold">1</span>
                        </div>
                        <div>
                          <p className="text-sm text-gray-700"><strong>Authorize the app</strong> to add slash commands to your Slack workspace</p>
                        </div>
                      </div>

                      <div className="flex items-start space-x-3">
                        <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span className="text-green-600 text-xs font-bold">2</span>
                        </div>
                        <div>
                          <p className="text-sm text-gray-700"><strong>Team members type</strong> <code className="bg-gray-100 px-1 rounded text-xs">/burnout-survey</code></p>
                          <div className="bg-slate-800 rounded p-3 font-mono text-sm text-green-400 mt-2">
                            <div>/burnout-survey</div>
                            <div className="text-slate-400 mt-1">→ Opens 2-minute burnout survey with 3 questions</div>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-start space-x-3">
                        <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span className="text-green-600 text-xs font-bold">3</span>
                        </div>
                        <div>
                          <p className="text-sm text-gray-700"><strong>Survey responses appear automatically</strong> in your burnout analysis to validate automated detection</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Workspace Details for OAuth Connections */}
                {slackIntegration?.connection_type === 'oauth' && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h4 className="font-medium text-blue-900 mb-2 flex items-center">
                      <Building className="w-4 h-4 mr-2" />
                      Registered Workspace
                    </h4>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-blue-700 font-medium">Workspace:</span>
                        <p className="text-blue-900">{slackIntegration.workspace_name || 'Unknown'}</p>
                      </div>
                      <div>
                        <span className="text-blue-700 font-medium">Status:</span>
                        <p className="text-blue-900 capitalize">{slackIntegration.status || 'Active'}</p>
                      </div>
                      <div>
                        <span className="text-blue-700 font-medium">Registered:</span>
                        <p className="text-blue-900">{new Date(slackIntegration.connected_at).toLocaleDateString()}</p>
                      </div>
                      <div>
                        <span className="text-blue-700 font-medium">Workspace ID:</span>
                        <p className="text-blue-900 font-mono text-xs">{slackIntegration.workspace_id}</p>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-blue-200">
                      <p className="text-xs text-blue-800">
                        💡 The <code className="bg-blue-100 px-1 rounded">/burnout-survey</code> command will only show analyses for your organization
                      </p>
                    </div>
                  </div>
                )}

                {/* Workspace Registration Fix Button - Always show when Slack connected */}
                {slackIntegration && (
                  <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <h4 className="font-medium text-yellow-900 mb-2 flex items-center text-sm">
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      Troubleshooting
                    </h4>
                    <p className="text-xs text-yellow-800 mb-3">
                      If the <code className="bg-yellow-100 px-1 rounded">/burnout-survey</code> command shows "workspace not registered" error, click below to fix:
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={async () => {
                        try {
                          const authToken = localStorage.getItem('auth_token')
                          if (!authToken) {
                            toast.error('Please log in to check workspace status')
                            return
                          }

                          // Check workspace status
                          const statusResponse = await fetch(`${API_BASE}/integrations/slack/workspace/status`, {
                            headers: {
                              'Authorization': `Bearer ${authToken}`,
                              'Content-Type': 'application/json'
                            }
                          })

                          if (!statusResponse.ok) {
                            toast.error('Failed to check workspace status')
                            return
                          }

                          const statusData = await statusResponse.json()

                          if (statusData.diagnosis.has_workspace_mapping) {
                            toast.success('✅ Workspace is properly registered! /burnout-survey command should work.')
                          } else {
                            // Need to register workspace
                            if (!slackIntegration?.workspace_id) {
                              toast.error('No workspace ID found. Please reconnect Slack.')
                              return
                            }

                            const formData = new FormData()
                            formData.append('workspace_id', slackIntegration.workspace_id)
                            formData.append('workspace_name', slackIntegration.workspace_name || slackIntegration.workspace_id)

                            const registerResponse = await fetch(`${API_BASE}/integrations/slack/workspace/register`, {
                              method: 'POST',
                              headers: {
                                'Authorization': `Bearer ${authToken}`
                              },
                              body: formData
                            })

                            if (registerResponse.ok) {
                              const registerData = await registerResponse.json()
                              toast.success('✅ Workspace registered! /burnout-survey command should now work. Try the command again.')

                              // Reload Slack integration to update UI
                              await loadSlackPermissions()
                            } else {
                              const errorData = await registerResponse.json()
                              toast.error(`Failed to register workspace: ${errorData.detail || 'Unknown error'}`)
                            }
                          }
                        } catch (error) {
                          console.error('Error checking/fixing workspace:', error)
                          toast.error('Error checking workspace status')
                        }
                      }}
                      className="w-full text-xs"
                    >
                      <svg className="w-3 h-3 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Check & Fix Workspace Registration
                    </Button>
                  </div>
                )}

                <div className="flex items-center justify-between pt-2">
                  <div className="flex items-center space-x-2 text-sm text-gray-500">
                    <Users className="w-4 h-4" />
                    <span>Available to all workspace members</span>
                  </div>
                  <div className="flex items-center space-x-2 text-xs text-gray-400">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                    <span>Secure OAuth authentication</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Team Members for Survey Correlation - NOW IN TABS ABOVE */}
            {false && slackIntegration && selectedOrganization && (
              <Card className="border-2 border-purple-200 bg-purple-50/30" style={{display: 'none'}}>
                <CardHeader className="pb-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                        <Users className="w-6 h-6 text-purple-600" />
                      </div>
                      <div>
                        <CardTitle className="text-lg text-gray-900">Team Members</CardTitle>
                        <p className="text-sm text-gray-600">Users from your organization who can submit surveys</p>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="bg-white rounded-lg border p-4">
                    <div className="mb-4">
                      <h4 className="font-medium text-gray-900 mb-2">Survey Correlation</h4>
                      <p className="text-sm text-gray-600 mb-3">
                        When team members submit a <code className="bg-gray-100 px-1 rounded text-xs">/burnout-survey</code>,
                        we match them to their profile using:
                      </p>
                      <div className="space-y-2 text-sm">
                        <div className="flex items-start space-x-2">
                          <div className="w-5 h-5 bg-purple-100 rounded flex items-center justify-center flex-shrink-0 mt-0.5">
                            <span className="text-purple-600 text-xs">1</span>
                          </div>
                          <div>
                            <span className="font-medium text-gray-900">Slack email</span> matches
                            <span className="font-medium text-gray-900"> Rootly/PagerDuty email</span>
                          </div>
                        </div>
                        <div className="flex items-start space-x-2">
                          <div className="w-5 h-5 bg-purple-100 rounded flex items-center justify-center flex-shrink-0 mt-0.5">
                            <span className="text-purple-600 text-xs">2</span>
                          </div>
                          <div>
                            Survey response is linked to their burnout analysis profile
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="border-t pt-4">
                      <div className="mb-4">
                        <h4 className="font-medium text-gray-900 mb-3">
                          Team Members from {integrations.find(i => i.id.toString() === selectedOrganization)?.name}
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            onClick={fetchTeamMembers}
                            disabled={loadingTeamMembers || !selectedOrganization}
                            size="sm"
                            variant="outline"
                            className="flex items-center space-x-2"
                          >
                            {loadingTeamMembers ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                <span>Loading...</span>
                              </>
                            ) : (
                              <>
                                <RefreshCw className="w-4 h-4" />
                                <span>Load Members</span>
                              </>
                            )}
                          </Button>
                          <Button
                            onClick={syncUsersToCorrelation}
                            disabled={loadingTeamMembers || !selectedOrganization || teamMembers.length === 0}
                            size="sm"
                            variant="default"
                            className="flex items-center space-x-2 bg-purple-600 hover:bg-purple-700"
                          >
                            {loadingTeamMembers ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                <span>Syncing...</span>
                              </>
                            ) : (
                              <>
                                <Database className="w-4 h-4" />
                                <span>Sync to Survey System</span>
                              </>
                            )}
                          </Button>
                          {slackIntegration?.workspace_id && (
                            <Button
                              onClick={syncSlackUserIds}
                              disabled={loadingTeamMembers}
                              size="sm"
                              variant="default"
                              className="flex items-center space-x-2 bg-green-600 hover:bg-green-700"
                            >
                              {loadingTeamMembers ? (
                                <>
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                  <span>Syncing...</span>
                                </>
                              ) : (
                                <>
                                  <MessageSquare className="w-4 h-4" />
                                  <span>Sync Slack IDs</span>
                                </>
                              )}
                            </Button>
                          )}
                          <Button
                            onClick={() => fetchSyncedUsers()}
                            disabled={loadingSyncedUsers}
                            size="sm"
                            variant="outline"
                            className="flex items-center space-x-2"
                          >
                            {loadingSyncedUsers ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                <span>Loading...</span>
                              </>
                            ) : (
                              <>
                                <Users2 className="w-4 h-4" />
                                <span>View Synced Users</span>
                              </>
                            )}
                          </Button>
                          {(userInfo?.role === 'super_admin' || userInfo?.role === 'org_admin') && (
                            <Button
                              onClick={() => setShowManualSurveyModal(true)}
                              size="sm"
                              className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700"
                            >
                              <Send className="w-4 h-4" />
                              <span>Send Survey Now</span>
                            </Button>
                          )}
                        </div>
                      </div>

                      <div className="text-sm text-gray-600">
                        <p className="mb-2">Click "Load Members" to view users from your organization who can submit burnout surveys.</p>
                        <p className="text-xs text-gray-500">
                          After loading, use "Sync to Survey System" to ensure all team members can submit surveys via Slack,
                          even if they haven't been involved in incidents yet.
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
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
              <GitHubIntegrationCard
                onConnect={handleGitHubConnect}
                isConnecting={isConnectingGithub}
              />
            )}

            {/* Slack Sentiment Analysis - OAuth Only */}
            {activeEnhancementTab === 'slack' && !slackIntegration && (
              <Card className="border-purple-200 bg-purple-50/30 max-w-2xl mx-auto">
                <CardHeader>
                  <CardTitle className="text-lg">Slack Sentiment Analysis</CardTitle>
                  <p className="text-sm text-gray-600 mt-2">
                    Sentiment analysis is now configured via the main Slack OAuth flow above.
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="bg-white rounded-lg border p-4">
                      <h4 className="font-medium text-gray-900 mb-3">To enable sentiment analysis:</h4>
                      <ol className="space-y-2 text-sm text-gray-700">
                        <li className="flex items-start space-x-2">
                          <span className="font-semibold text-purple-600">1.</span>
                          <span>Scroll up to the "Slack Survey" section</span>
                        </li>
                        <li className="flex items-start space-x-2">
                          <span className="font-semibold text-purple-600">2.</span>
                          <span>Check the "Enable Sentiment Analysis (Read Messages)" checkbox</span>
                        </li>
                        <li className="flex items-start space-x-2">
                          <span className="font-semibold text-purple-600">3.</span>
                          <span>Click "Add to Slack" to authorize the integration</span>
                        </li>
                      </ol>
                    </div>
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-900">
                      <strong>Note:</strong> You can enable both survey delivery and sentiment analysis together, or choose just one feature.
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Connected GitHub Status */}
            {activeEnhancementTab === 'github' && githubIntegration && (
              <GitHubConnectedCard
                integration={githubIntegration}
                onDisconnect={() => setGithubDisconnectDialogOpen(true)}
                onTest={handleGitHubTest}
                onViewMappings={() => openMappingDrawer('github')}
                loadingMappings={loadingMappingData}
                selectedMappingPlatform={selectedMappingPlatform}
              />
            )}

            {/* Connected Slack Status */}
            {activeEnhancementTab === 'slack' && hasSlackEnhanced && (
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
                  <div className="border-t pt-4 mt-6">
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
      <NewMappingDialog
        open={newMappingDialogOpen}
        onOpenChange={setNewMappingDialogOpen}
        form={newMappingForm}
        onFormChange={setNewMappingForm}
        selectedPlatform={selectedManualMappingPlatform}
        onCreateMapping={createManualMapping}
      />

      {/* GitHub Disconnect Confirmation Dialog */}
      <GitHubDisconnectDialog
        open={githubDisconnectDialogOpen}
        onOpenChange={setGithubDisconnectDialogOpen}
        isDisconnecting={isDisconnectingGithub}
        onConfirmDisconnect={handleGitHubDisconnect}
      />

      {/* Slack Disconnect Confirmation Dialog */}
      <SlackDisconnectDialog
        open={slackDisconnectDialogOpen}
        onOpenChange={setSlackDisconnectDialogOpen}
        isDisconnecting={isDisconnectingSlack}
        onConfirmDisconnect={handleSlackDisconnect}
      />

      {/* Slack Survey Workspace Info & Disconnect Dialog */}
      <Dialog open={slackSurveyDisconnectDialogOpen} onOpenChange={setSlackSurveyDisconnectDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center">
              <Building className="w-5 h-5 mr-2 text-blue-600" />
              Registered Workspace
            </DialogTitle>
            <DialogDescription>
              Your Slack workspace connection details
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-700">Workspace</p>
                <p className="text-sm text-gray-900 mt-1">{slackIntegration?.workspace_name || 'Unknown'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-700">Connection</p>
                <p className="text-sm text-gray-900 mt-1 capitalize">
                  {slackIntegration?.connection_type === 'oauth' ? 'OAuth' : 'Token'}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-700">Connected</p>
                <p className="text-sm text-gray-900 mt-1">
                  {slackIntegration?.connected_at ? new Date(slackIntegration.connected_at).toLocaleDateString() : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-700">Workspace ID</p>
                <p className="text-sm text-gray-900 mt-1 font-mono text-xs">
                  {slackIntegration?.workspace_id || 'N/A'}
                </p>
              </div>
            </div>
            <div className="pt-3 border-t border-gray-200">
              <p className="text-xs text-gray-600">
                💡 The <code className="bg-gray-100 px-1 rounded">/burnout-survey</code> command will only show analyses for your organization
              </p>
            </div>
          </div>
          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => setSlackSurveyDisconnectDialogOpen(false)}
              className="w-full sm:w-auto"
            >
              Close
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                setSlackSurveyDisconnectDialogOpen(false)
                setSlackSurveyConfirmDisconnectOpen(true)
              }}
              className="w-full sm:w-auto"
            >
              Disconnect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Slack Survey Disconnect Confirmation Dialog - Step 2 */}
      <Dialog open={slackSurveyConfirmDisconnectOpen} onOpenChange={setSlackSurveyConfirmDisconnectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center text-red-600">
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Disconnect Slack Survey Integration?
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to disconnect?
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-2">
              <p className="text-sm font-medium text-red-900">This will:</p>
              <ul className="text-sm text-red-800 space-y-1 list-disc list-inside">
                <li>Disable the <code className="bg-red-100 px-1 rounded font-mono text-xs">/burnout-survey</code> command in your Slack workspace</li>
                <li>Stop all automated survey delivery</li>
                <li>Remove access to survey features for all team members</li>
              </ul>
            </div>
            <p className="text-sm text-gray-600">
              You will need to reconnect to re-enable these features.
            </p>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setSlackSurveyConfirmDisconnectOpen(false)}
              disabled={isDisconnectingSlackSurvey}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={async () => {
                setIsDisconnectingSlackSurvey(true)
                try {
                  const authToken = localStorage.getItem('auth_token')
                  if (!authToken) {
                    toast.error('Authentication required')
                    return
                  }

                  const url = `${API_BASE}/integrations/slack/disconnect`

                  const response = await fetch(url, {
                    method: 'DELETE',
                    headers: {
                      'Authorization': `Bearer ${authToken}`
                    }
                  })

                  if (response.ok) {
                    const result = await response.json()

                    // Small delay to ensure backend has processed the disconnect
                    await new Promise(resolve => setTimeout(resolve, 300))

                    // Fetch updated Slack status without showing loading on other cards
                    const slackResponse = await fetch(`${API_BASE}/integrations/slack/status`, {
                      headers: { 'Authorization': `Bearer ${authToken}` }
                    })

                    if (slackResponse.ok) {
                      const slackData = await slackResponse.json()
                      setSlackIntegration(slackData.integration)
                      // Update cache
                      localStorage.setItem('slack_integration', JSON.stringify(slackData))
                      localStorage.setItem('all_integrations_timestamp', Date.now().toString())
                    }

                    // Close dialog and show success after state update
                    setSlackSurveyConfirmDisconnectOpen(false)

                    toast.success('Slack Survey integration disconnected', {
                      description: 'Your workspace has been disconnected successfully.',
                    })
                  } else {
                    const error = await response.json()
                    toast.error(error.detail || 'Failed to disconnect Slack')
                  }
                } catch (error) {
                  toast.error('Failed to disconnect Slack Survey integration')
                } finally {
                  setIsDisconnectingSlackSurvey(false)
                }
              }}
              disabled={isDisconnectingSlackSurvey}
            >
              {isDisconnectingSlackSurvey ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Disconnecting...
                </>
              ) : (
                'Yes, Disconnect'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <DeleteIntegrationDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        integration={integrationToDelete}
        isDeleting={isDeleting}
        onConfirmDelete={deleteIntegration}
        onCancel={() => {
          setDeleteDialogOpen(false)
          setIntegrationToDelete(null)
        }}
      />

      {/* Organization Management Modal */}
      <OrganizationManagementDialog
        open={showInviteModal}
        onOpenChange={setShowInviteModal}
        inviteEmail={inviteEmail}
        onInviteEmailChange={setInviteEmail}
        inviteRole={inviteRole}
        onInviteRoleChange={setInviteRole}
        isInviting={isInviting}
        onInvite={handleInvite}
        loadingOrgData={loadingOrgData}
        orgMembers={orgMembers}
        pendingInvitations={pendingInvitations}
        userInfo={userInfo}
        onRoleChange={handleRoleChange}
        onClose={() => {
          setShowInviteModal(false)
          setInviteEmail("")
          setInviteRole("member")
        }}
      />

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

      {/* Team Members Drawer */}
      <Sheet open={teamMembersDrawerOpen} onOpenChange={setTeamMembersDrawerOpen}>
        <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Team Members</SheetTitle>
            <SheetDescription>
              Users from {integrations.find(i => i.id.toString() === selectedOrganization)?.name || 'your organization'} who can submit burnout surveys
            </SheetDescription>
          </SheetHeader>

          <div className="mt-6 space-y-4">
            {/* Show synced users only */}
            {syncedUsers.length > 0 ? (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-900">
                    Team Members ({syncedUsers.length})
                  </h3>
                  <div className="flex items-center gap-2">
                    {slackIntegration?.workspace_id && (
                      <Button
                        onClick={syncSlackUserIds}
                        disabled={loadingTeamMembers}
                        size="sm"
                        variant="outline"
                        className="flex items-center space-x-2 border-green-300 text-green-700 hover:bg-green-50"
                      >
                        {loadingTeamMembers ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>Syncing...</span>
                          </>
                        ) : (
                          <>
                            <MessageSquare className="w-4 h-4" />
                            <span>Sync Slack IDs</span>
                          </>
                        )}
                      </Button>
                    )}
                    <Badge className="text-xs bg-green-100 text-green-700 border-green-300">
                      Can Submit Surveys
                    </Badge>
                  </div>
                </div>
                <p className="text-xs text-gray-600 mb-3">
                  These users can submit burnout surveys via Slack /burnout-survey command
                </p>
                <div className="space-y-2 max-h-[600px] overflow-y-auto">
                  {syncedUsers.map((user: any) => (
                    <div
                      key={user.id}
                      className="bg-white border border-gray-200 rounded-lg p-3 hover:border-purple-300 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-3">
                          <Avatar className="h-10 w-10">
                            <AvatarFallback className="bg-purple-100 text-purple-700 text-sm font-medium">
                              {user.name?.substring(0, 2).toUpperCase() || user.email?.substring(0, 2).toUpperCase() || '??'}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {user.name || 'Unknown'}
                            </div>
                            <div className="text-xs text-gray-600">
                              {user.email}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-1">
                          {user.platforms?.map((platform: string) => (
                            <Badge key={platform} variant="secondary" className="text-xs">
                              {platform}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      {user.github_username && (
                        <div className="pl-13 text-xs text-gray-500">
                          GitHub: <span className="font-mono">{user.github_username}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                <Users className="w-12 h-12 mx-auto mb-4 opacity-40" />
                <p className="text-sm font-medium mb-2">No team members synced yet</p>
                <p className="text-xs">Close this drawer and click "Sync Members" to add team members who can submit surveys</p>
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>

      {/* Manual Survey Delivery Modal */}
      <ManualSurveyDeliveryModal
        isOpen={showManualSurveyModal}
        onClose={() => setShowManualSurveyModal(false)}
        onSuccess={() => {
          // Refresh notifications or show success message
          toast.success("Survey delivery initiated successfully")
        }}
      />
    </div>
  )
}