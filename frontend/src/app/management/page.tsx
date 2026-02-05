"use client"

import { useState, useEffect, useRef, Suspense } from "react"
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
  RefreshCw,
  Search,
  Pencil,
  CheckCircle,
} from "lucide-react"
import { API_BASE, type Integration } from "@/app/integrations/types"
import { UserMappingDrawer } from "./components/UserMappingDrawer"

const TEAM_MEMBERS_PER_PAGE = 20

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

  // Team members state
  const [syncedUsers, setSyncedUsers] = useState<SyncedUser[]>([])
  const [loadingSyncedUsers, setLoadingSyncedUsers] = useState(false)
  const [refreshingOnCall, setRefreshingOnCall] = useState(false)

  // Search state
  const [searchQuery, setSearchQuery] = useState("")

  // Cache to track which integrations have already been loaded
  const syncedUsersCache = useRef<Map<string, SyncedUser[]>>(new Map())
  const recipientsCache = useRef<Map<string, Set<number>>>(new Map())
  const syncTimeoutRef = useRef<NodeJS.Timeout | null>(null)

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

  // Load integrations on mount
  useEffect(() => {
    const fetchIntegrations = async () => {
      const authToken = localStorage.getItem("auth_token")
      if (!authToken) {
        setLoadingIntegrations(false)
        return
      }

      try {
        const response = await fetch(`${API_BASE}/rootly/integrations`, {
          headers: { Authorization: `Bearer ${authToken}` },
        })

        if (response.ok) {
          const data = await response.json()
          setIntegrations(data.integrations || [])

          // Try to restore selected organization from URL or localStorage
          const urlOrgId = searchParams.get("org")
          if (urlOrgId) {
            setSelectedOrganization(urlOrgId)
          } else {
            const saved = localStorage.getItem("selectedOrganization")
            if (saved) setSelectedOrganization(saved)
            else if (data.integrations.length > 0) setSelectedOrganization(data.integrations[0].id.toString())
          }
        }
      } catch (error) {
        console.error("Failed to load integrations:", error)
      } finally {
        setLoadingIntegrations(false)
      }
    }

    fetchIntegrations()
  }, [searchParams])

  // Save selected organization to localStorage
  useEffect(() => {
    if (selectedOrganization) {
      localStorage.setItem("selectedOrganization", selectedOrganization)
    }
  }, [selectedOrganization])

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current)
        syncTimeoutRef.current = null
      }
    }
  }, [])

  // Auto-fetch synced users when organization changes
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (selectedOrganization) {
      fetchSyncedUsers(false, false, false)
    }
  }, [selectedOrganization])

  // Fetch synced users from database
  const fetchSyncedUsers = async (showToast = false, autoSync = false, forceRefresh = false) => {
    if (!selectedOrganization) return

    // Check cache first
    if (!forceRefresh && syncedUsersCache.current.has(selectedOrganization)) {
      const cachedUsers = syncedUsersCache.current.get(selectedOrganization)!
      setSyncedUsers(cachedUsers)

      if (recipientsCache.current.has(selectedOrganization)) {
        const cachedRecipients = recipientsCache.current.get(selectedOrganization)!
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
        `${API_BASE}/rootly/synced-users?integration_id=${selectedOrganization}`,
        {
          headers: { Authorization: `Bearer ${authToken}` },
        }
      )

      if (response.ok) {
        const data = await response.json()
        const users = data.users || []
        setSyncedUsers(users)
        syncedUsersCache.current.set(selectedOrganization, users)

        // Load saved recipients
        const recipientIds = new Set<number>(users.filter((u: any) => u.is_survey_recipient).map((u: any) => u.id as number))
        setSelectedRecipients(recipientIds)
        setSavedRecipients(recipientIds)
        recipientsCache.current.set(selectedOrganization, recipientIds)

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
  }

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
      syncTimeoutRef.current = setTimeout(() => {
        setShowSyncConfirmModal(false)
        setSyncProgress(null)
        syncTimeoutRef.current = null
      }, 2000)
    }
  }

  // Refresh on-call status for users
  const refreshOnCallStatus = async () => {
    if (!selectedOrganization) return

    setRefreshingOnCall(true)
    const authToken = localStorage.getItem("auth_token")
    if (!authToken) {
      toast.error("Please log in")
      setRefreshingOnCall(false)
      return
    }

    try {
      const response = await fetch(
        `${API_BASE}/rootly/integrations/${selectedOrganization}/refresh-oncall`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${authToken}` },
        }
      )

      if (response.ok) {
        await fetchSyncedUsers(false, false, true)
        toast.success("On-call status refreshed")
      } else {
        toast.error("Failed to refresh on-call status")
      }
    } catch (error) {
      console.error("Error refreshing on-call status:", error)
      toast.error("Error refreshing on-call status")
    } finally {
      setRefreshingOnCall(false)
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

      // Validate recipient IDs are numbers
      if (!recipientIds.every(id => typeof id === 'number' && id > 0)) {
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

  // Filter users based on search query
  const filteredUsers = syncedUsers.filter(user => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      user.email?.toLowerCase().includes(query) ||
      user.github_username?.toLowerCase().includes(query) ||
      user.jira_username?.toLowerCase().includes(query)
    )
  })

  // Pagination
  const totalPages = Math.ceil(filteredUsers.length / TEAM_MEMBERS_PER_PAGE)
  const startIndex = (currentPage - 1) * TEAM_MEMBERS_PER_PAGE
  const paginatedUsers = filteredUsers.slice(startIndex, startIndex + TEAM_MEMBERS_PER_PAGE)

  // Validate avatar URL to prevent XSS
  const isValidUrl = (url: string): boolean => {
    if (!url) return false
    try {
      const urlObj = new URL(url)
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
    } catch {
      return false
    }
  }

  // Get integration logos for a user
  const getUserIntegrations = (user: any) => {
    const integrations = []
    if (user.github_username) integrations.push('github')
    if (user.jira_account_id) integrations.push('jira')
    if (user.linear_user_id) integrations.push('linear')
    return integrations
  }

  return (
    <>
      <TopPanel />
      <main className="min-h-screen bg-neutral-50 p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header with Organization Selector */}
          <div className="mb-8 flex items-center justify-between">
            <div className="flex-1 max-w-md">
              <label className="text-sm font-semibold text-neutral-700 mb-2 block">Select Organization</label>
              <Select
                value={selectedOrganization}
                onValueChange={setSelectedOrganization}
                disabled={loadingIntegrations}
              >
                <SelectTrigger className="w-full">
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

          {/* Organization Management Section */}
          {selectedOrganization && (
            <div className="bg-white rounded-lg border border-neutral-200 shadow-sm">
              {/* Header with Search and Actions */}
              <div className="p-6 border-b border-neutral-200">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-neutral-900">Organization Management</h2>
                  <div className="flex items-center gap-3">
                    <Button
                      onClick={() => setShowSyncConfirmModal(true)}
                      disabled={loadingSyncedUsers}
                      className="bg-purple-700 hover:bg-purple-800"
                    >
                      Sync Now
                    </Button>
                    <Button
                      onClick={refreshOnCallStatus}
                      disabled={refreshingOnCall}
                      variant="outline"
                    >
                      <RefreshCw className={`w-4 h-4 mr-2 ${refreshingOnCall ? 'animate-spin' : ''}`} />
                      Refresh On-Call
                    </Button>
                  </div>
                </div>

                {/* Search Bar */}
                <div className="mb-4">
                  <div className="relative max-w-md">
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
              </div>

              {/* Management Table */}
              {loadingSyncedUsers ? (
                <div className="flex items-center justify-center h-96">
                  <Loader2 className="w-8 h-8 animate-spin text-purple-700" />
                </div>
              ) : filteredUsers.length === 0 ? (
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    <p className="text-neutral-600">
                      {syncedUsers.length === 0 ? 'No users synced yet' : 'No members found'}
                    </p>
                    {syncedUsers.length === 0 && (
                      <Button
                        onClick={() => setShowSyncConfirmModal(true)}
                        className="mt-4 bg-purple-700 hover:bg-purple-800"
                      >
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Sync Now
                      </Button>
                    )}
                  </div>
                </div>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-neutral-200 bg-neutral-50">
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Name</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Email</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">On-Call Status</th>
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">Role</th>
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
                                    {isValidUrl(user.avatar_url) && <AvatarImage src={user.avatar_url} alt={displayName} />}
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
                                <span className="text-sm text-neutral-900">Member</span>
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
