"use client"

import { useState, useEffect, useRef, useCallback, Suspense } from "react"
import Image from "next/image"
import { useRouter, useSearchParams } from "next/navigation"
import { TopPanel } from "@/components/TopPanel"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  Search,
  Pencil,
  CheckCircle,
  Users,
} from "lucide-react"
import { API_BASE, type Integration } from "@/app/integrations/types"
import { UserMappingDrawer } from "./components/UserMappingDrawer"
import { OrganizationManagementDialog } from "@/app/integrations/dialogs/OrganizationManagementDialog"
import * as OrganizationHandlers from "@/app/integrations/handlers/organization-handlers"

const TEAM_MEMBERS_PER_PAGE = 10

// Type definition for synced users
interface SyncedUser {
  id: number
  email: string
  name?: string
  avatar_url?: string
  github_username?: string
  jira_account_id?: string
  jira_email?: string
  linear_user_id?: string
  linear_email?: string
  on_call_status?: string
  is_oncall?: boolean
  role?: string
}

function TeamPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // Organization selection state
  const [selectedOrganization, setSelectedOrganization] = useState<string>("")
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loadingIntegrations, setLoadingIntegrations] = useState(true)
  const [viewMode, setViewMode] = useState<'organization' | 'company'>('organization')

  // Connected integrations state (to filter which integrations are currently active)
  const [connectedIntegrations, setConnectedIntegrations] = useState<Set<string>>(new Set())

  // Team management state (for Company tab)
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState("member")
  const [isInviting, setIsInviting] = useState(false)
  const [orgMembers, setOrgMembers] = useState([])
  const [pendingInvitations, setPendingInvitations] = useState([])
  const [receivedInvitations, setReceivedInvitations] = useState([])
  const [loadingOrgData, setLoadingOrgData] = useState(false)
  const [userInfo, setUserInfo] = useState<any>(null)

  // Team members state
  const [syncedUsers, setSyncedUsers] = useState<SyncedUser[]>([])
  const [loadingSyncedUsers, setLoadingSyncedUsers] = useState(false)
  const [lastSyncInfo, setLastSyncInfo] = useState<{synced_at: string; synced_by: {id: number; name: string; email: string}} | null>(null)

  // Search state
  const [searchQuery, setSearchQuery] = useState("")

  // Cache to track which integrations have already been loaded
  const syncedUsersCache = useRef<Map<string, SyncedUser[]>>(new Map())
  const recipientsCache = useRef<Map<string, Set<number>>>(new Map())
  const lastSyncInfoCache = useRef<Map<string, {synced_at: string; synced_by: {id: number; name: string; email: string}} | null>>(new Map())
  const syncTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isMountedRef = useRef(true)

  // Survey recipient selection state
  const [selectedRecipients, setSelectedRecipients] = useState<Set<number>>(new Set())
  const [savedRecipients, setSavedRecipients] = useState<Set<number>>(new Set())
  const [savingRecipients, setSavingRecipients] = useState(false)

  // Pagination
  const [currentPage, setCurrentPage] = useState(1)

  // User mapping drawer state
  const [selectedUserForMapping, setSelectedUserForMapping] = useState<any | null>(null)
  const [mappingDrawerOpen, setMappingDrawerOpen] = useState(false)

  // Sync confirmation modal state
  const [showSyncConfirmModal, setShowSyncConfirmModal] = useState(false)
  const [syncProgress, setSyncProgress] = useState<{
    stage: string
    details: string
    isLoading: boolean
    results?: {
      created?: number
      updated?: number
      github_matched?: number
      jira_matched?: number
      linear_matched?: number
      slack_synced?: number
      slack_skipped?: number
    }
  } | null>(null)

  // Check if there are unsaved changes
  const hasUnsavedChanges = () => {
    if (selectedRecipients.size !== savedRecipients.size) return true
    for (const id of Array.from(selectedRecipients)) {
      if (!savedRecipients.has(id)) return true
    }
    return false
  }

  // Load integrations on mount (both Rootly and PagerDuty)
  useEffect(() => {
    const fetchIntegrations = async () => {
      const authToken = localStorage.getItem("auth_token")
      if (!authToken) {
        setLoadingIntegrations(false)
        return
      }

      try {
        // Fetch both Rootly and PagerDuty integrations in parallel
        const [rootlyResponse, pagerdutyResponse] = await Promise.all([
          fetch(`${API_BASE}/rootly/integrations`, {
            headers: { Authorization: `Bearer ${authToken}` },
          }).catch(() => null),
          fetch(`${API_BASE}/pagerduty/integrations`, {
            headers: { Authorization: `Bearer ${authToken}` },
          }).catch(() => null),
        ])

        let allIntegrations: Integration[] = []

        if (rootlyResponse?.ok) {
          const data = await rootlyResponse.json()
          const rootlyIntegrations = (data.integrations || []).map((i: Integration) => ({ ...i, platform: 'rootly' as const }))
          allIntegrations = [...allIntegrations, ...rootlyIntegrations]
        }

        if (pagerdutyResponse?.ok) {
          const data = await pagerdutyResponse.json()
          const pdIntegrations = (data.integrations || []).map((i: Integration) => ({ ...i, platform: 'pagerduty' as const }))
          allIntegrations = [...allIntegrations, ...pdIntegrations]
        }

        setIntegrations(allIntegrations)

        // Restore selected org, with validation against actual integration IDs
        const urlOrgId = searchParams.get("org")
        const saved = localStorage.getItem("selectedOrganization")
        const matchesIntegration = (id: string) => allIntegrations.some(i => i.id.toString() === id)

        if (urlOrgId && matchesIntegration(urlOrgId)) {
          setSelectedOrganization(urlOrgId)
        } else if (saved && matchesIntegration(saved)) {
          setSelectedOrganization(saved)
        } else if (allIntegrations.length > 0) {
          setSelectedOrganization(allIntegrations[0].id.toString())
        }
      } catch (error) {
        console.error("Failed to load integrations:", error)
      } finally {
        setLoadingIntegrations(false)
      }
    }

    fetchIntegrations()
  }, [searchParams])

  // Handle view parameter from URL
  useEffect(() => {
    const viewParam = searchParams.get("view")
    if (viewParam === "team") {
      setViewMode("company")
    } else if (viewParam === "organization") {
      setViewMode("organization")
    }
  }, [searchParams])

  // Load connected integration statuses
  useEffect(() => {
    const fetchConnectedIntegrations = async () => {
      const authToken = localStorage.getItem("auth_token")
      if (!authToken) return

      try {
        const connected = new Set<string>()

        // Check each integration's status
        const integrationTypes = ['github', 'jira', 'linear', 'slack']

        for (const integrationType of integrationTypes) {
          try {
            const response = await fetch(`${API_BASE}/integrations/${integrationType}/status`, {
              headers: { Authorization: `Bearer ${authToken}` },
            })

            if (response.ok) {
              const data = await response.json()
              if (data.connected) {
                connected.add(integrationType)
              }
            }
          } catch (error) {
            // Continue checking other integrations if one fails
            console.debug(`Failed to check ${integrationType} status:`, error)
          }
        }

        setConnectedIntegrations(connected)
      } catch (error) {
        console.error("Failed to fetch connected integrations:", error)
      }
    }

    fetchConnectedIntegrations()
  }, [])

  // Save selected organization to localStorage
  useEffect(() => {
    if (selectedOrganization) {
      localStorage.setItem("selectedOrganization", selectedOrganization)
    }
  }, [selectedOrganization])

  // Cleanup timeout on unmount and mark component as unmounted
  useEffect(() => {
    return () => {
      isMountedRef.current = false
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current)
        syncTimeoutRef.current = null
      }
    }
  }, [])


  // Auto-open sync modal if redirected from integrations page
  useEffect(() => {
    const syncParam = searchParams.get("sync")
    if (syncParam === "true" && selectedOrganization && !loadingIntegrations) {
      setShowSyncConfirmModal(true)
    }
  }, [searchParams, selectedOrganization, loadingIntegrations])

  // Load user info for team management
  useEffect(() => {
    const userName = localStorage.getItem('user_name')
    const userEmail = localStorage.getItem('user_email')
    const userRole = localStorage.getItem('user_role')
    const userId = localStorage.getItem('user_id')

    if (userName && userEmail) {
      setUserInfo({
        name: userName,
        email: userEmail,
        role: userRole,
        id: userId
      })
    }
  }, [])

  // Load organization data when Company tab is selected
  useEffect(() => {
    if (viewMode === 'company') {
      loadOrganizationData()
    }
  }, [viewMode])

  // Fetch synced users from database (memoized to avoid stale closures)
  const fetchSyncedUsers = useCallback(async (showToast = false, autoSync = false, forceRefresh = false) => {
    if (!selectedOrganization) return

    // Capture current organization to prevent race conditions
    const requestedOrg = selectedOrganization

    // Check cache first
    if (!forceRefresh && syncedUsersCache.current.has(requestedOrg)) {
      const cachedUsers = syncedUsersCache.current.get(requestedOrg)!
      setSyncedUsers(cachedUsers)

      // Restore cached last sync info
      if (lastSyncInfoCache.current.has(requestedOrg)) {
        setLastSyncInfo(lastSyncInfoCache.current.get(requestedOrg)!)
      } else {
        setLastSyncInfo(null)
      }

      if (recipientsCache.current.has(requestedOrg)) {
        const cachedRecipients = recipientsCache.current.get(requestedOrg)!
        const validUserIds = new Set(cachedUsers.map(u => u.id))
        const validCachedRecipients = new Set(
          Array.from(cachedRecipients).filter(id => validUserIds.has(id))
        )
        setSelectedRecipients(validCachedRecipients)
        setSavedRecipients(validCachedRecipients)
      }
      return
    }

    setLoadingSyncedUsers(true)
    const authToken = localStorage.getItem("auth_token")
    if (!authToken) {
      toast.error("Please log in")
      setLoadingSyncedUsers(false)
      return
    }

    try {
      const response = await fetch(
        `${API_BASE}/rootly/synced-users?integration_id=${requestedOrg}`,
        {
          headers: { Authorization: `Bearer ${authToken}` },
        }
      )

      // Ignore stale responses if user switched organizations
      if (requestedOrg !== selectedOrganization) {
        return
      }

      if (response.ok) {
        const data = await response.json()
        const users = data.users || []
        setSyncedUsers(users)
        syncedUsersCache.current.set(requestedOrg, users)

        // Cache last sync info
        const syncInfo = data.last_sync || null
        setLastSyncInfo(syncInfo)
        lastSyncInfoCache.current.set(requestedOrg, syncInfo)

        // Load saved recipients
        const recipientIds = new Set<number>(users.filter((u: any) => u.is_survey_recipient).map((u: any) => u.id as number))
        setSelectedRecipients(recipientIds)
        setSavedRecipients(recipientIds)
        recipientsCache.current.set(requestedOrg, recipientIds)

        if (showToast) {
          toast.success(`Loaded ${users.length} users`)
        }
      } else {
        toast.error("Failed to load users")
      }
    } catch (error) {
      console.error("Error fetching synced users:", error)
      toast.error("Error loading users")
    } finally {
      setLoadingSyncedUsers(false)
    }
  }, [selectedOrganization])

  // Auto-fetch synced users when organization changes (moved after fetchSyncedUsers definition)
  useEffect(() => {
    if (selectedOrganization) {
      fetchSyncedUsers(false, false, false)
    }
  }, [selectedOrganization, fetchSyncedUsers])

  // Perform full team sync with progress tracking
  const performTeamSync = async () => {
    try {
      setSyncProgress({ stage: "Starting sync...", details: "Preparing to sync users", isLoading: true })
      await new Promise(resolve => setTimeout(resolve, 300))

      setSyncProgress({ stage: "Fetching users...", details: "Retrieving users from API with IR role filtering", isLoading: true })

      const authToken = localStorage.getItem("auth_token")
      if (!authToken) {
        throw new Error("Not authenticated")
      }

      const response = await fetch(
        `${API_BASE}/rootly/integrations/${selectedOrganization}/sync-users`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${authToken}` },
        }
      )

      if (!response.ok) {
        throw new Error("Sync failed")
      }

      const syncResults = await response.json()

      // Clear cache only after successful sync
      if (selectedOrganization) {
        syncedUsersCache.current.delete(selectedOrganization)
        lastSyncInfoCache.current.delete(selectedOrganization)
      }

      setSyncProgress({
        stage: "Sync Complete!",
        details: "Your users have been successfully synced",
        isLoading: false,
        results: {
          created: syncResults.created,
          updated: syncResults.updated,
          github_matched: syncResults.github_matched,
          jira_matched: syncResults.jira_matched,
          linear_matched: syncResults.linear_matched,
        }
      })

      // Refresh the user list
      await fetchSyncedUsers(false, false, true)
    } catch (error) {
      setSyncProgress({ stage: "Error", details: "Failed to sync. Please try again.", isLoading: false })
      // Clean up any existing timeout before setting a new one
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current)
      }
      // Only set new timeout if component is still mounted
      if (isMountedRef.current) {
        syncTimeoutRef.current = setTimeout(() => {
          // Check again before setting state to prevent memory leaks
          if (isMountedRef.current) {
            setShowSyncConfirmModal(false)
            setSyncProgress(null)
          }
          syncTimeoutRef.current = null
        }, 2000)
      }
    }
  }


  // Open mapping drawer
  const openMappingDrawer = (user: any) => {
    setSelectedUserForMapping(user)
    setMappingDrawerOpen(true)
  }

  const closeMappingDrawer = () => {
    setSelectedUserForMapping(null)
    setMappingDrawerOpen(false)
  }

  const handleMappingUpdated = async () => {
    // Refresh the user data to show updated mappings
    await fetchSyncedUsers(false, false, true)
  }

  // Team management handlers
  const handleInvite = async () => {
    return OrganizationHandlers.handleInvite(
      inviteEmail,
      inviteRole,
      setIsInviting,
      setInviteEmail,
      setInviteRole,
      () => {}, // No need to close modal since it's inline
      loadOrganizationData
    )
  }

  const handleRoleChange = async (userId: number, newRole: string) => {
    return OrganizationHandlers.handleRoleChange(userId, newRole, loadOrganizationData)
  }

  const loadOrganizationData = async () => {
    return OrganizationHandlers.loadOrganizationData(
      setLoadingOrgData,
      setOrgMembers,
      setPendingInvitations,
      setReceivedInvitations
    )
  }

  // Save recipient selections to database
  const saveRecipientSelections = async () => {
    if (!selectedOrganization) return

    setSavingRecipients(true)
    const authToken = localStorage.getItem("auth_token")
    if (!authToken) {
      toast.error("Please log in")
      setSavingRecipients(false)
      return
    }

    try {
      const recipientIds = Array.from(selectedRecipients)

      // Validate recipient IDs are valid positive integers (not NaN, Infinity, or floats)
      if (!recipientIds.every(id =>
        typeof id === 'number' &&
        Number.isFinite(id) &&
        Number.isInteger(id) &&
        id > 0
      )) {
        toast.error("Invalid recipient IDs")
        setSavingRecipients(false)
        return
      }

      const response = await fetch(
        `${API_BASE}/rootly/integrations/${selectedOrganization}/survey-recipients`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${authToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ recipient_ids: recipientIds }),
        }
      )

      if (response.ok) {
        setSavedRecipients(new Set(selectedRecipients))
        recipientsCache.current.set(selectedOrganization, new Set(selectedRecipients))
        toast.success("Survey recipients saved")
      } else {
        toast.error("Failed to save survey recipients")
      }
    } catch (error) {
      console.error("Error saving survey recipients:", error)
      toast.error("Error saving survey recipients")
    } finally {
      setSavingRecipients(false)
    }
  }

  // Find the currently selected integration (used for context elsewhere on the page)
  const selectedIntegration = selectedOrganization
    ? integrations.find(i => i.id.toString() === selectedOrganization)
    : null

  // Check if any primary integration (Rootly or PagerDuty) exists
  // Since the integrations array only contains Rootly and PagerDuty entries, length > 0 is sufficient
  const hasPrimaryIntegration = integrations.length > 0

  // Filter users based on search query
  const filteredUsers = syncedUsers.filter(user => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      user.email?.toLowerCase().includes(query) ||
      user.github_username?.toLowerCase().includes(query) ||
      user.jira_email?.toLowerCase().includes(query)
    )
  })

  // Pagination
  const totalPages = Math.ceil(filteredUsers.length / TEAM_MEMBERS_PER_PAGE)
  const startIndex = (currentPage - 1) * TEAM_MEMBERS_PER_PAGE
  const paginatedUsers = filteredUsers.slice(startIndex, startIndex + TEAM_MEMBERS_PER_PAGE)

  // Get integration logos for a user (filtered by currently connected integrations)
  const getUserIntegrations = (user: any) => {
    const integrations = []
    if (user.github_username && connectedIntegrations.has('github')) integrations.push('github')
    if (user.jira_account_id && connectedIntegrations.has('jira')) integrations.push('jira')
    if (user.linear_user_id && connectedIntegrations.has('linear')) integrations.push('linear')
    return integrations
  }

  return (
    <>
      <TopPanel />
      <main className="min-h-screen bg-neutral-50 p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header with View Mode Toggle */}
          <div className="mb-8 flex items-end justify-end gap-6">
            {/* View Mode Toggle */}
            <div className="relative flex items-center gap-2 bg-white border border-neutral-200 rounded-lg p-1">
              <button
                onClick={() => setViewMode('organization')}
                className={`relative z-10 px-3 py-2 text-sm font-medium rounded transition-colors duration-200 ${
                  viewMode === 'organization'
                    ? 'text-neutral-900'
                    : 'text-neutral-600 hover:text-neutral-900'
                }`}
              >
                Synced Org
              </button>
              <button
                onClick={() => setViewMode('company')}
                className={`relative z-10 px-3 py-2 text-sm font-medium rounded transition-colors duration-200 ${
                  viewMode === 'company'
                    ? 'text-neutral-900'
                    : 'text-neutral-600 hover:text-neutral-900'
                }`}
              >
                Team Roles
              </button>
              <div
                className={`absolute top-1 bottom-1 bg-neutral-100 rounded transition-all duration-300 ease-in-out ${
                  viewMode === 'organization' ? 'left-1 w-[calc(50%-0.25rem)]' : 'left-[calc(50%+0.125rem)] w-[calc(50%-0.375rem)]'
                }`}
              />
            </div>
          </div>

          {/* Organization Management Section */}
          {(selectedOrganization || !hasPrimaryIntegration) && !loadingIntegrations && (
            <div className="bg-white rounded-lg border border-neutral-200 shadow-sm">
              {viewMode === 'organization' ? (
                <>
                  {/* Organization View */}
                  {/* Header with Search and Actions */}
                  <div className="p-6 border-b border-neutral-200">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h2 className="text-xl font-semibold text-neutral-900">Organization Management</h2>
                        <p className="text-sm text-neutral-600 mt-1">Sync team data, manage incident response integrations, and track on-call status</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <Button
                          onClick={() => setShowSyncConfirmModal(true)}
                          disabled={loadingSyncedUsers || !hasPrimaryIntegration}
                          className="bg-purple-700 hover:bg-purple-800"
                        >
                          Sync Now
                        </Button>
                      </div>
                    </div>

                    {/* Search Bar and Organization Selector - Only show when primary integration exists */}
                    {hasPrimaryIntegration && (
                      <div className="mb-4 flex items-end gap-4">
                        {/* Search Bar - shorter */}
                        <div className="w-80">
                          <label className="text-xs font-semibold text-neutral-700 mb-1.5 block">&nbsp;</label>
                          <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
                            <Input
                              type="text"
                              placeholder="Search members..."
                              value={searchQuery}
                              onChange={(e) => setSearchQuery(e.target.value)}
                              className="pl-9 w-full"
                            />
                          </div>
                        </div>

                        {/* Organization Selector - wider on the right */}
                        <div className="flex-shrink-0">
                          <label className="text-xs font-semibold text-neutral-700 mb-1.5 block">Select Organization</label>
                          <Select
                            value={selectedOrganization}
                            onValueChange={setSelectedOrganization}
                            disabled={loadingIntegrations || !hasPrimaryIntegration}
                          >
                            <SelectTrigger className="w-72">
                              <SelectValue placeholder="Select an organization..." />
                            </SelectTrigger>
                            <SelectContent>
                              {integrations.map((integration) => (
                                <SelectItem key={integration.id} value={integration.id.toString()}>
                                  {integration.name || `Integration #${integration.id}`}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Management Table */}
              {loadingIntegrations ? (
                // LOADING INTEGRATIONS STATE
                <div className="flex items-center justify-center h-96">
                  <Loader2 className="w-8 h-8 animate-spin text-purple-700" />
                </div>
              ) : !hasPrimaryIntegration ? (
                // NO PRIMARY INTEGRATION EMPTY STATE
                <div className="flex items-center justify-center h-96">
                  <div className="text-center max-w-md">
                    <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-4">
                      <div className="flex items-start gap-3">
                        <svg className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                        <div className="text-left flex-1">
                          <h3 className="text-sm font-semibold text-red-800 mb-1">
                            No Primary Integrations Connected
                          </h3>
                          <p className="text-sm text-red-700">
                            To sync members, you need to connect at least one primary integration (Rootly or PagerDuty).
                          </p>
                        </div>
                      </div>
                    </div>
                    <Button
                      onClick={() => router.push('/integrations')}
                      className="bg-purple-700 hover:bg-purple-800"
                    >
                      Go to Integrations
                    </Button>
                  </div>
                </div>
              ) : loadingSyncedUsers ? (
                // LOADING STATE
                <div className="flex items-center justify-center h-96">
                  <Loader2 className="w-8 h-8 animate-spin text-purple-700" />
                </div>
              ) : filteredUsers.length === 0 ? (
                // EMPTY STATE (no users synced)
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    {syncedUsers.length === 0 ? (
                      <>
                        <Users className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
                        <p className="text-neutral-600">No team members synced yet</p>
                      </>
                    ) : (
                      <p className="text-neutral-600">No members found</p>
                    )}
                  </div>
                </div>
              ) : (
                // TABLE
                <>
                  {/* Last Sync Info */}
                  {lastSyncInfo && (
                    <div className="px-6 py-3 bg-neutral-50 border-b border-neutral-200">
                      <p className="text-sm text-neutral-600">
                        Last synced {new Date(lastSyncInfo.synced_at).toLocaleString()}
                      </p>
                    </div>
                  )}

                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-neutral-200 bg-neutral-50">
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Name</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Email</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">On-Call Status</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Integrations</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedUsers.map((user, index) => {
                          const integrations = getUserIntegrations(user)
                          const displayName = user.email?.split('@')[0] || 'Unknown'

                          return (
                            <tr key={user.id} className={`border-b border-neutral-100 hover:bg-neutral-50 ${index === paginatedUsers.length - 1 ? 'border-b-0' : ''}`}>
                              <td className="py-4 px-6">
                                <div className="flex items-center gap-3">
                                  <Avatar className="w-9 h-9">
                                    {user.avatar_url && <AvatarImage src={user.avatar_url} alt={displayName} />}
                                    <AvatarFallback className="text-sm font-medium">
                                      {displayName
                                        .split('.')
                                        .map((p: string) => p[0])
                                        .join('')
                                        .toUpperCase()
                                        .substring(0, 2)}
                                    </AvatarFallback>
                                  </Avatar>
                                  <span className="font-medium text-neutral-900 capitalize">
                                    {displayName.replace(/[._]/g, ' ')}
                                  </span>
                                </div>
                              </td>
                              <td className="py-4 px-6">
                                <span className="text-sm text-neutral-600">{user.email}</span>
                              </td>
                              <td className="py-4 px-6">
                                {user.is_oncall ? (
                                  <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
                                    <span className="w-1.5 h-1.5 bg-green-600 rounded-full mr-1.5"></span>
                                    Active
                                  </Badge>
                                ) : (
                                  <Badge variant="outline" className="border-neutral-300 text-neutral-600">
                                    <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full mr-1.5"></span>
                                    Inactive
                                  </Badge>
                                )}
                              </td>
                              <td className="py-4 px-6">
                                <div className="flex items-center gap-2">
                                  {integrations.length > 0 ? (
                                    integrations.map((integration) => (
                                      <div
                                        key={integration}
                                        className="w-6 h-6 flex items-center justify-center"
                                        title={integration.charAt(0).toUpperCase() + integration.slice(1)}
                                      >
                                        {integration === 'github' && (
                                          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                                          </svg>
                                        )}
                                        {integration === 'jira' && (
                                          <svg className="w-5 h-5 text-blue-600" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M11.571 11.513H0a5.218 5.218 0 0 0 5.232 5.215h2.13v2.057A5.215 5.215 0 0 0 12.575 24V12.518a1.005 1.005 0 0 0-1.005-1.005zm5.723-5.756H5.736a5.215 5.215 0 0 0 5.215 5.214h2.129v2.058a5.218 5.218 0 0 0 5.215 5.214V6.758a1.001 1.001 0 0 0-1.001-1.001zM23.013 0H11.455a5.215 5.215 0 0 0 5.215 5.215h2.129v2.057A5.215 5.215 0 0 0 24 12.483V1.005A1.001 1.001 0 0 0 23.013 0z"/>
                                          </svg>
                                        )}
                                        {integration === 'linear' && (
                                          <Image src="/images/linear-logo.png" alt="Linear" width={20} height={20} />
                                        )}
                                      </div>
                                    ))
                                  ) : (
                                    <span className="text-xs text-neutral-400">None</span>
                                  )}
                                </div>
                              </td>
                              <td className="py-4 px-6">
                                <button
                                  className="text-neutral-400 hover:text-neutral-600 transition-colors"
                                  onClick={() => openMappingDrawer(user)}
                                  title="Edit integration mappings"
                                >
                                  <Pencil className="w-4 h-4" />
                                </button>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between px-6 py-4 border-t border-neutral-200">
                      <p className="text-sm text-neutral-600">
                        Showing {startIndex + 1}-{Math.min(startIndex + TEAM_MEMBERS_PER_PAGE, filteredUsers.length)} of {filteredUsers.length}
                      </p>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                          disabled={currentPage === 1}
                        >
                          <ChevronLeft className="w-4 h-4" />
                        </Button>
                        <span className="text-sm text-neutral-600 px-3">
                          Page {currentPage} of {totalPages}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                          disabled={currentPage === totalPages}
                        >
                          <ChevronRight className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
                </>
              ) : (
                // Team View - Team Management
                <>
                  <OrganizationManagementDialog
                    open={true}
                    onOpenChange={() => {}}
                    inviteEmail={inviteEmail}
                    onInviteEmailChange={setInviteEmail}
                    inviteRole={inviteRole}
                    onInviteRoleChange={setInviteRole}
                    isInviting={isInviting}
                    onInvite={handleInvite}
                    loadingOrgData={loadingOrgData}
                    orgMembers={orgMembers}
                    pendingInvitations={pendingInvitations}
                    receivedInvitations={receivedInvitations}
                    userInfo={userInfo}
                    onRoleChange={handleRoleChange}
                    onRefreshOrgData={loadOrganizationData}
                    onClose={() => {}}
                    asInlineView={true}
                    title="Team Management"
                    subtitle="Add team members, assign roles, manage access permissions, and control who can view and edit team data"
                  />
                </>
              )}
            </div>
          )}

          {!selectedOrganization && !loadingIntegrations && (
            <div className="flex items-center justify-center h-96">
              <p className="text-neutral-600">Please select an organization to view users</p>
            </div>
          )}
        </div>
      </main>

      {/* Sync Confirmation Modal */}
      <Dialog open={showSyncConfirmModal} onOpenChange={setShowSyncConfirmModal}>
        <DialogContent className="max-w-md">
          {!syncProgress ? (
            <>
              <DialogHeader>
                <DialogTitle>Sync Organization Users</DialogTitle>
                <DialogDescription>
                  This will sync all users from your connected integrations and match them with GitHub, Jira, and Linear accounts
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowSyncConfirmModal(false)}>
                  Cancel
                </Button>
                <Button onClick={performTeamSync} className="bg-purple-700 hover:bg-purple-800">
                  Start Sync
                </Button>
              </DialogFooter>
            </>
          ) : (
            <>
              <DialogHeader>
                <DialogTitle>{syncProgress.stage}</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  {syncProgress.isLoading && <Loader2 className="w-5 h-5 animate-spin text-purple-700" />}
                  <p className="text-sm text-neutral-600">{syncProgress.details}</p>
                </div>

                {syncProgress.results && (
                  <div className="space-y-2 pt-4 border-t">
                    <p className="font-semibold text-sm">Sync Results:</p>
                    {syncProgress.results.created !== undefined && syncProgress.results.created > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <span>{syncProgress.results.created} created</span>
                      </div>
                    )}
                    {syncProgress.results.updated !== undefined && syncProgress.results.updated > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <span>{syncProgress.results.updated} updated</span>
                      </div>
                    )}
                    {syncProgress.results.github_matched !== undefined && syncProgress.results.github_matched > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <CheckCircle className="w-4 h-4 text-blue-600" />
                        <span>{syncProgress.results.github_matched} GitHub matched</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
              {!syncProgress.isLoading && (
                <DialogFooter>
                  <Button onClick={() => {
                    setShowSyncConfirmModal(false)
                    setSyncProgress(null)
                  }} className="bg-purple-700 hover:bg-purple-800">
                    Close
                  </Button>
                </DialogFooter>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* User Mapping Drawer */}
      <UserMappingDrawer
        isOpen={mappingDrawerOpen}
        onClose={closeMappingDrawer}
        user={selectedUserForMapping}
        selectedOrganization={selectedOrganization}
        onMappingUpdated={handleMappingUpdated}
        connectedIntegrations={connectedIntegrations}
      />
    </>
  )
}

export default function TeamPage() {
  return (
    <Suspense>
      <TeamPageContent />
    </Suspense>
  )
}
