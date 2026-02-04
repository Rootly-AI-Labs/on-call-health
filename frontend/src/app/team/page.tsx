"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { TopPanel } from "@/components/TopPanel"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ChevronLeft,
  ChevronRight,
  Clock,
  Loader2,
  RefreshCw,
  Users,
  CheckCircle,
} from "lucide-react"
import * as TeamHandlers from "@/app/integrations/handlers/team-handlers"
import { API_BASE, type Integration } from "@/app/integrations/types"

const TEAM_MEMBERS_PER_PAGE = 10

export default function TeamPage() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // Organization selection state
  const [selectedOrganization, setSelectedOrganization] = useState<string>("")
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loadingIntegrations, setLoadingIntegrations] = useState(true)

  // Team members state
  const [teamMembers, setTeamMembers] = useState<any[]>([])
  const [loadingTeamMembers, setLoadingTeamMembers] = useState(false)
  const [teamMembersError, setTeamMembersError] = useState<string | null>(null)
  const [syncedUsers, setSyncedUsers] = useState<any[]>([])
  const [loadingSyncedUsers, setLoadingSyncedUsers] = useState(false)
  const [showSyncedUsers, setShowSyncedUsers] = useState(false)
  const [teamMembersDrawerOpen, setTeamMembersDrawerOpen] = useState(false)
  const [refreshingOnCall, setRefreshingOnCall] = useState(false)
  const [oncallCacheInfo, setOncallCacheInfo] = useState<any>(null)

  // Cache to track which integrations have already been loaded
  const syncedUsersCache = useRef<Map<string, any[]>>(new Map())
  const recipientsCache = useRef<Map<string, Set<number>>>(new Map())

  // Survey recipient selection state
  const [selectedRecipients, setSelectedRecipients] = useState<Set<number>>(new Set())
  const [savedRecipients, setSavedRecipients] = useState<Set<number>>(new Set())
  const [savingRecipients, setSavingRecipients] = useState(false)

  // Team members drawer pagination
  const [teamMembersPage, setTeamMembersPage] = useState(1)

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

  // Fetch team members from selected organization
  const fetchTeamMembers = async (suppressToast?: boolean) => {
    return TeamHandlers.fetchTeamMembers(
      selectedOrganization,
      setLoadingTeamMembers,
      setTeamMembersError,
      setTeamMembers,
      setTeamMembersDrawerOpen,
      suppressToast
    )
  }

  // Sync users to UserCorrelation table
  const syncUsersToCorrelation = async (suppressToast?: boolean) => {
    if (selectedOrganization) {
      syncedUsersCache.current.delete(selectedOrganization)
    }

    return TeamHandlers.syncUsersToCorrelation(
      selectedOrganization,
      setLoadingTeamMembers,
      setTeamMembersError,
      () => fetchTeamMembers(suppressToast),
      () => fetchSyncedUsers(true, true, true),
      undefined,
      suppressToast
    )
  }

  // Perform full team sync with progress tracking
  const performTeamSync = async () => {
    try {
      setSyncProgress({ stage: "Starting sync...", details: "Preparing to sync users", isLoading: true })
      await new Promise(resolve => setTimeout(resolve, 300))

      setSyncProgress({ stage: "Fetching users...", details: "Retrieving users from API with IR role filtering", isLoading: true })
      const syncResults = await TeamHandlers.syncUsersToCorrelation(
        selectedOrganization,
        setLoadingTeamMembers,
        setTeamMembersError,
        fetchTeamMembers,
        () => fetchSyncedUsers(false, false, true),
        (message: string) => {
          setSyncProgress({ stage: "Syncing users...", details: message, isLoading: true })
        },
        true
      )

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
    } catch (error) {
      setSyncProgress({ stage: "Error", details: "Failed to sync. Please try again.", isLoading: false })
      setTimeout(() => {
        setShowSyncConfirmModal(false)
        setSyncProgress(null)
      }, 2000)
    }
  }

  // Fetch synced users from database
  const fetchSyncedUsers = async (showToast = true, autoSync = true, forceRefresh = false, openDrawer = true) => {
    return TeamHandlers.fetchSyncedUsers(
      selectedOrganization,
      setLoadingSyncedUsers,
      setSyncedUsers,
      setShowSyncedUsers,
      setTeamMembersDrawerOpen,
      syncUsersToCorrelation,
      showToast,
      autoSync,
      setSelectedRecipients,
      setSavedRecipients,
      syncedUsersCache.current,
      forceRefresh,
      recipientsCache.current,
      openDrawer
    )
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
        await fetchSyncedUsers(false, false, true, false)
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

  const handleDrawerClose = () => {
    if (hasUnsavedChanges()) {
      if (confirm("You have unsaved changes. Are you sure you want to close?")) {
        setTeamMembersDrawerOpen(false)
        setTeamMembersPage(1)
      }
    } else {
      setTeamMembersDrawerOpen(false)
      setTeamMembersPage(1)
    }
  }

  // Pagination helpers
  const totalPages = Math.ceil(syncedUsers.length / TEAM_MEMBERS_PER_PAGE)
  const startIndex = (teamMembersPage - 1) * TEAM_MEMBERS_PER_PAGE
  const paginatedUsers = syncedUsers.slice(startIndex, startIndex + TEAM_MEMBERS_PER_PAGE)

  return (
    <>
      <TopPanel />
      <main className="min-h-screen bg-neutral-100 p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          {/* Organization Selector */}
          <div className="mb-8">
            <label className="text-sm font-semibold text-neutral-700 mb-2 block">Select Organization</label>
            <Select
              value={selectedOrganization}
              onValueChange={setSelectedOrganization}
              disabled={loadingIntegrations}
            >
              <SelectTrigger className="w-full sm:w-96">
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

          {/* Team Management Section */}
          <div className="mt-16 space-y-8">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-neutral-900 mb-3">Team Management</h2>
              <p className="text-lg text-neutral-600 mb-2">
                Sync and manage your team members for an analysis
              </p>
            </div>

            {/* Team Members Card */}
            <div className="max-w-2xl mx-auto">
              <Card className={`border-2 ${selectedOrganization ? 'border-purple-300 bg-white' : 'border-neutral-300 bg-white'}`}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${selectedOrganization ? 'bg-purple-700' : 'bg-neutral-300'}`}>
                        <Users className={`w-6 h-6 ${selectedOrganization ? 'text-white' : 'text-neutral-500'}`} />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-neutral-900">
                          Team Member Sync
                        </h3>
                        <p className={`text-sm ${selectedOrganization ? 'text-neutral-600' : 'text-neutral-700'}`}>
                          {selectedOrganization ? (
                            <>Sync team members from connected integrations {syncedUsers.length > 0 && `(${syncedUsers.length} synced)`}</>
                          ) : (
                            'Select an organization above to sync team members'
                          )}
                        </p>
                      </div>
                    </div>
                    <Button
                      onClick={() => {
                        if (!selectedOrganization) {
                          toast.error('Please select an organization first')
                          return
                        }

                        setTeamMembersDrawerOpen(true)

                        if (selectedOrganization && syncedUsersCache.current.has(selectedOrganization)) {
                          const cachedUsers = syncedUsersCache.current.get(selectedOrganization)!
                          setSyncedUsers(cachedUsers)
                          setShowSyncedUsers(true)

                          if (recipientsCache.current.has(selectedOrganization)) {
                            const cachedRecipients = recipientsCache.current.get(selectedOrganization)!
                            const validUserIds = new Set(cachedUsers.map(u => u.id))
                            const validCachedRecipients = new Set(
                              Array.from(cachedRecipients).filter(id => validUserIds.has(id))
                            )
                            setSelectedRecipients(validCachedRecipients)
                            setSavedRecipients(validCachedRecipients)
                          }
                        } else {
                          fetchSyncedUsers(false, false)
                        }
                      }}
                      disabled={!selectedOrganization}
                      className="bg-purple-700 hover:bg-purple-800 disabled:bg-neutral-300 disabled:cursor-not-allowed"
                      title={!selectedOrganization ? 'Please select an organization first' : ''}
                    >
                      <Users className="w-4 h-4 mr-2" />
                      Sync Members
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </main>

      {/* Team Members Drawer */}
      <Sheet open={teamMembersDrawerOpen} onOpenChange={handleDrawerClose}>
        <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
          <SheetHeader className="space-y-4 pb-4 border-b">
            <div className="flex items-center justify-between pr-6">
              <div>
                <SheetTitle>Team Members</SheetTitle>
                <SheetDescription>Manage your synced team members and survey recipients</SheetDescription>
              </div>
            </div>
          </SheetHeader>

          {loadingSyncedUsers ? (
            <div className="flex items-center justify-center h-96">
              <Loader2 className="w-8 h-8 animate-spin text-purple-700" />
            </div>
          ) : syncedUsers.length === 0 ? (
            <div className="flex items-center justify-center h-96">
              <div className="text-center">
                <Users className="w-12 h-12 text-neutral-400 mx-auto mb-3" />
                <p className="text-neutral-600">No team members synced yet</p>
                <Button
                  onClick={() => setShowSyncConfirmModal(true)}
                  className="mt-4 bg-purple-700 hover:bg-purple-800"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Sync Now
                </Button>
              </div>
            </div>
          ) : (
            <>
              {/* Team Members List */}
              <div className="space-y-4 py-4">
                {paginatedUsers.map((user) => (
                  <div key={user.id} className="flex items-center gap-3 p-3 bg-neutral-50 rounded-lg">
                    <Avatar className="w-10 h-10">
                      {user.avatar_url && <AvatarImage src={user.avatar_url} alt={user.email} />}
                      <AvatarFallback>
                        {user.email
                          ?.split('@')[0]
                          ?.split('.')
                          .map((p: string) => p[0])
                          .join('')
                          .toUpperCase() || 'U'}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-neutral-900 truncate">{user.email}</p>
                      <div className="flex gap-2 mt-1">
                        {user.on_call && (
                          <Badge variant="secondary" className="text-xs">
                            <Clock className="w-3 h-3 mr-1" />
                            On-call
                          </Badge>
                        )}
                        {user.github_username && (
                          <Badge variant="outline" className="text-xs">GitHub</Badge>
                        )}
                      </div>
                    </div>
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
                      className="w-5 h-5 cursor-pointer"
                    />
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between py-4 border-t">
                  <p className="text-sm text-neutral-600">
                    Page {teamMembersPage} of {totalPages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setTeamMembersPage(p => Math.max(1, p - 1))}
                      disabled={teamMembersPage === 1}
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setTeamMembersPage(p => Math.min(totalPages, p + 1))}
                      disabled={teamMembersPage === totalPages}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4 border-t">
                <Button
                  onClick={refreshOnCallStatus}
                  disabled={refreshingOnCall}
                  variant="outline"
                  className="flex-1"
                >
                  <RefreshCw className={`w-4 h-4 mr-2 ${refreshingOnCall ? 'animate-spin' : ''}`} />
                  Refresh On-Call
                </Button>
                <Button
                  onClick={() => setShowSyncConfirmModal(true)}
                  className="flex-1 bg-purple-700 hover:bg-purple-800"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Sync Again
                </Button>
              </div>

              {/* Save Recipients Button */}
              <div className="pt-4 border-t">
                <Button
                  onClick={saveRecipientSelections}
                  disabled={!hasUnsavedChanges() || savingRecipients}
                  className="w-full bg-purple-700 hover:bg-purple-800 disabled:bg-neutral-300"
                >
                  {savingRecipients ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Save Recipients'
                  )}
                </Button>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

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
