"use client"

import { useState, useEffect, useRef } from "react"
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
  UserPlus,
  Search,
  CheckCircle,
  Pencil,
} from "lucide-react"
import * as TeamHandlers from "@/app/integrations/handlers/team-handlers"
import { API_BASE, type Integration } from "@/app/integrations/types"

const TEAM_MEMBERS_PER_PAGE = 20

export default function TeamPage() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // Organization selection state
  const [selectedOrganization, setSelectedOrganization] = useState<string>("")
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loadingIntegrations, setLoadingIntegrations] = useState(true)

  // Team members state
  const [syncedUsers, setSyncedUsers] = useState<any[]>([])
  const [loadingSyncedUsers, setLoadingSyncedUsers] = useState(false)
  const [refreshingOnCall, setRefreshingOnCall] = useState(false)

  // Search state
  const [searchQuery, setSearchQuery] = useState("")

  // Cache to track which integrations have already been loaded
  const syncedUsersCache = useRef<Map<string, any[]>>(new Map())
  const recipientsCache = useRef<Map<string, Set<number>>>(new Map())

  // Survey recipient selection state
  const [selectedRecipients, setSelectedRecipients] = useState<Set<number>>(new Set())
  const [savedRecipients, setSavedRecipients] = useState<Set<number>>(new Set())
  const [savingRecipients, setSavingRecipients] = useState(false)

  // Pagination
  const [currentPage, setCurrentPage] = useState(1)

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

  // Auto-fetch synced users when organization changes
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
        const recipientIds = new Set(users.filter((u: any) => u.is_survey_recipient).map((u: any) => u.id))
        setSelectedRecipients(recipientIds)
        setSavedRecipients(recipientIds)
        recipientsCache.current.set(selectedOrganization, recipientIds)

        if (showToast) {
          toast.success(`Loaded ${users.length} team members`)
        }
      } else {
        toast.error("Failed to load team members")
      }
    } catch (error) {
      console.error("Error fetching synced users:", error)
      toast.error("Error loading team members")
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

      // Clear cache for this organization
      if (selectedOrganization) {
        syncedUsersCache.current.delete(selectedOrganization)
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

      setSyncProgress({
        stage: "Sync Complete!",
        details: "Your team members have been successfully synced",
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
      setTimeout(() => {
        setShowSyncConfirmModal(false)
        setSyncProgress(null)
      }, 2000)
    }
  }

  // Refresh on-call status for team members
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

  // Reset to page 1 when search changes
  useEffect(() => {
    setCurrentPage(1)
  }, [searchQuery])

  // Get integration badges for a user
  const getUserIntegrations = (user: any) => {
    const integrations = []
    if (user.github_username) integrations.push({ name: 'GitHub', color: 'bg-blue-100 text-blue-800' })
    if (user.jira_username) integrations.push({ name: 'Jira', color: 'bg-purple-100 text-purple-800' })
    if (user.linear_username) integrations.push({ name: 'Linear', color: 'bg-indigo-100 text-indigo-800' })
    if (user.slack_user_id) integrations.push({ name: 'Slack', color: 'bg-pink-100 text-pink-800' })
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

          {/* Team Members Section */}
          {selectedOrganization && (
            <div className="bg-white rounded-lg border border-neutral-200 shadow-sm">
              {/* Header with Search and Actions */}
              <div className="p-6 border-b border-neutral-200">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-neutral-900">Team Members</h2>
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
                      <Input
                        type="text"
                        placeholder="Search members..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-9 w-64"
                      />
                    </div>
                    <Button variant="outline" disabled>
                      <UserPlus className="w-4 h-4 mr-2" />
                      Invite
                    </Button>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-3">
                  <Button
                    onClick={() => setShowSyncConfirmModal(true)}
                    disabled={loadingSyncedUsers}
                    className="bg-purple-700 hover:bg-purple-800"
                  >
                    <RefreshCw className={`w-4 h-4 mr-2 ${loadingSyncedUsers ? 'animate-spin' : ''}`} />
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
                  <Button
                    onClick={saveRecipientSelections}
                    disabled={!hasUnsavedChanges() || savingRecipients}
                    variant="outline"
                    className="disabled:opacity-50"
                  >
                    {savingRecipients ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Save Recipients
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {/* Team Members Table */}
              {loadingSyncedUsers ? (
                <div className="flex items-center justify-center h-96">
                  <Loader2 className="w-8 h-8 animate-spin text-purple-700" />
                </div>
              ) : filteredUsers.length === 0 ? (
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    <p className="text-neutral-600">
                      {syncedUsers.length === 0 ? 'No team members synced yet' : 'No members found'}
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
                          <th className="text-left py-3 px-6 text-sm font-semibold text-neutral-700">
                            <input
                              type="checkbox"
                              checked={paginatedUsers.length > 0 && paginatedUsers.every(u => selectedRecipients.has(u.id))}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  const newRecipients = new Set(selectedRecipients)
                                  paginatedUsers.forEach(u => newRecipients.add(u.id))
                                  setSelectedRecipients(newRecipients)
                                } else {
                                  const newRecipients = new Set(selectedRecipients)
                                  paginatedUsers.forEach(u => newRecipients.delete(u.id))
                                  setSelectedRecipients(newRecipients)
                                }
                              }}
                              className="w-4 h-4 cursor-pointer"
                            />
                          </th>
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
                                <input
                                  type="checkbox"
                                  checked={selectedRecipients.has(user.id)}
                                  onChange={(e) => {
                                    const newRecipients = new Set(selectedRecipients)
                                    if (e.target.checked) {
                                      newRecipients.add(user.id)
                                    } else {
                                      newRecipients.delete(user.id)
                                    }
                                    setSelectedRecipients(newRecipients)
                                  }}
                                  className="w-4 h-4 cursor-pointer"
                                />
                              </td>
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
                                <span className="text-sm text-neutral-900">Member</span>
                              </td>
                              <td className="py-4 px-6">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  {integrations.slice(0, 2).map((int, idx) => (
                                    <Badge key={idx} className={`text-xs ${int.color}`}>
                                      {int.name}
                                    </Badge>
                                  ))}
                                  {integrations.length > 2 && (
                                    <span className="text-xs text-neutral-500">
                                      {integrations.length - 2} more
                                    </span>
                                  )}
                                  {integrations.length === 0 && (
                                    <span className="text-xs text-neutral-400">None</span>
                                  )}
                                </div>
                              </td>
                              <td className="py-4 px-6">
                                <button className="text-neutral-400 hover:text-neutral-600" disabled>
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
              <p className="text-neutral-600">Please select an organization to view team members</p>
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
                <DialogTitle>Sync Team Members</DialogTitle>
                <DialogDescription>
                  This will sync all team members from your connected integrations and match them with GitHub, Jira, and Linear accounts
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
    </>
  )
}
