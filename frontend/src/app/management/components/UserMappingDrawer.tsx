"use client"

import { useState, useEffect } from "react"
import { toast } from "sonner"
import { Pencil, Check, Loader2, X } from "lucide-react"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  updateUserCorrelation,
  fetchGithubUsers,
  fetchJiraUsers,
  fetchLinearUsers,
} from "../handlers/user-mapping-handlers"

interface UserMappingDrawerProps {
  isOpen: boolean
  onClose: () => void
  user: {
    id: number
    name?: string
    email: string
    github_username?: string
    jira_account_id?: string
    jira_email?: string
    linear_user_id?: string
    linear_email?: string
    slack_user_id?: string
  } | null
  selectedOrganization: string
  onMappingUpdated: () => void
}

type IntegrationType = "github" | "jira" | "linear"

export function UserMappingDrawer({
  isOpen,
  onClose,
  user,
  selectedOrganization,
  onMappingUpdated,
}: UserMappingDrawerProps) {
  const [editingIntegration, setEditingIntegration] = useState<IntegrationType | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [githubUsers, setGithubUsers] = useState<string[]>([])
  const [jiraUsers, setJiraUsers] = useState<any[]>([])
  const [linearUsers, setLinearUsers] = useState<any[]>([])
  const [loadingOptions, setLoadingOptions] = useState(false)
  const [saving, setSaving] = useState(false)

  // Reset state when drawer opens/closes
  useEffect(() => {
    if (!isOpen) {
      setEditingIntegration(null)
      setSearchQuery("")
    }
  }, [isOpen])

  // Load options when an integration is being edited
  useEffect(() => {
    if (editingIntegration === "github" && githubUsers.length === 0) {
      loadGithubUsers()
    } else if (editingIntegration === "jira" && jiraUsers.length === 0) {
      loadJiraUsers()
    } else if (editingIntegration === "linear" && linearUsers.length === 0) {
      loadLinearUsers()
    }
  }, [editingIntegration])

  const loadGithubUsers = async () => {
    setLoadingOptions(true)
    try {
      const users = await fetchGithubUsers(selectedOrganization)
      setGithubUsers(users)
    } catch (error) {
      toast.error("Failed to load GitHub users")
    } finally {
      setLoadingOptions(false)
    }
  }

  const loadJiraUsers = async () => {
    setLoadingOptions(true)
    try {
      const users = await fetchJiraUsers(selectedOrganization)
      setJiraUsers(users)
    } catch (error) {
      toast.error("Failed to load Jira users")
    } finally {
      setLoadingOptions(false)
    }
  }

  const loadLinearUsers = async () => {
    setLoadingOptions(true)
    try {
      const users = await fetchLinearUsers(selectedOrganization)
      setLinearUsers(users)
    } catch (error) {
      toast.error("Failed to load Linear users")
    } finally {
      setLoadingOptions(false)
    }
  }

  const handleSelectMapping = async (integration: IntegrationType, value: string) => {
    if (!user) return

    setSaving(true)
    try {
      const updates: any = {}
      if (integration === "github") {
        updates.github_username = value
      } else if (integration === "jira") {
        updates.jira_account_id = value
      } else if (integration === "linear") {
        updates.linear_user_id = value
      }

      const success = await updateUserCorrelation(user.id, updates)
      if (success) {
        toast.success(`${integration.charAt(0).toUpperCase() + integration.slice(1)} mapping updated`)
        setEditingIntegration(null)
        setSearchQuery("")
        onMappingUpdated()
      }
    } catch (error) {
      toast.error("Failed to update mapping")
    } finally {
      setSaving(false)
    }
  }

  const handleClearMapping = async (integration: IntegrationType) => {
    if (!user) return

    setSaving(true)
    try {
      const updates: any = {}
      if (integration === "github") {
        updates.github_username = ""
      } else if (integration === "jira") {
        updates.jira_account_id = ""
      } else if (integration === "linear") {
        updates.linear_user_id = ""
      }

      const success = await updateUserCorrelation(user.id, updates)
      if (success) {
        toast.success(`${integration.charAt(0).toUpperCase() + integration.slice(1)} mapping cleared`)
        setEditingIntegration(null)
        setSearchQuery("")
        onMappingUpdated()
      }
    } catch (error) {
      toast.error("Failed to clear mapping")
    } finally {
      setSaving(false)
    }
  }

  const filterGithubOptions = (query: string) => {
    if (!query) return githubUsers
    return githubUsers.filter((username) =>
      username.toLowerCase().includes(query.toLowerCase())
    )
  }

  const filterJiraOptions = (query: string) => {
    if (!query) return jiraUsers
    return jiraUsers.filter((jiraUser) => {
      const displayName = jiraUser.displayName || jiraUser.email || ""
      return displayName.toLowerCase().includes(query.toLowerCase())
    })
  }

  const filterLinearOptions = (query: string) => {
    if (!query) return linearUsers
    return linearUsers.filter((linearUser) => {
      const displayName = linearUser.name || linearUser.email || ""
      return displayName.toLowerCase().includes(query.toLowerCase())
    })
  }

  if (!user) return null

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader className="pb-4 border-b">
          <SheetTitle>Integration Mappings</SheetTitle>
          <SheetDescription>
            Manage integration mappings for {user.email}
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-4 py-6">
          {/* GitHub Integration */}
          <div className="space-y-2">
            <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 flex items-center justify-center">
                  <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium">GitHub</p>
                  <p className="text-xs text-neutral-500">
                    {user.github_username || <em>Not mapped</em>}
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  if (editingIntegration === "github") {
                    setEditingIntegration(null)
                    setSearchQuery("")
                  } else {
                    setEditingIntegration("github")
                    setSearchQuery("")
                  }
                }}
                className="text-neutral-500 hover:text-neutral-700 transition-colors"
                disabled={saving}
              >
                {editingIntegration === "github" ? (
                  <X className="w-4 h-4" />
                ) : (
                  <Pencil className="w-4 h-4" />
                )}
              </button>
            </div>

            {/* GitHub Dropdown Selector */}
            {editingIntegration === "github" && (
              <div className="border rounded-lg p-3 bg-white">
                <Input
                  placeholder="Search GitHub users..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="mb-2"
                />
                {loadingOptions ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="w-5 h-5 animate-spin text-neutral-500" />
                  </div>
                ) : (
                  <div className="max-h-48 overflow-y-auto space-y-1">
                    <button
                      onClick={() => handleClearMapping("github")}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-neutral-100 rounded italic text-neutral-500"
                      disabled={saving}
                    >
                      Clear mapping
                    </button>
                    {filterGithubOptions(searchQuery).map((username) => (
                      <button
                        key={username}
                        onClick={() => handleSelectMapping("github", username)}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-neutral-100 rounded flex items-center justify-between"
                        disabled={saving}
                      >
                        <span>{username}</span>
                        {user.github_username === username && (
                          <Check className="w-4 h-4 text-green-600" />
                        )}
                      </button>
                    ))}
                    {filterGithubOptions(searchQuery).length === 0 && (
                      <p className="text-sm text-neutral-400 py-2 px-3">No users found</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Jira Integration */}
          <div className="space-y-2">
            <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 flex items-center justify-center">
                  <svg className="w-6 h-6 text-blue-600" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M11.571 11.513H0a5.218 5.218 0 0 0 5.232 5.215h2.13v2.057A5.215 5.215 0 0 0 12.575 24V12.518a1.005 1.005 0 0 0-1.005-1.005zm5.723-5.756H5.736a5.215 5.215 0 0 0 5.215 5.214h2.129v2.058a5.218 5.218 0 0 0 5.215 5.214V6.758a1.001 1.001 0 0 0-1.001-1.001zM23.013 0H11.455a5.215 5.215 0 0 0 5.215 5.215h2.129v2.057A5.215 5.215 0 0 0 24 12.483V1.005A1.001 1.001 0 0 0 23.013 0z"/>
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium">Jira</p>
                  <p className="text-xs text-neutral-500">
                    {user.jira_email || <em>Not mapped</em>}
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  if (editingIntegration === "jira") {
                    setEditingIntegration(null)
                    setSearchQuery("")
                  } else {
                    setEditingIntegration("jira")
                    setSearchQuery("")
                  }
                }}
                className="text-neutral-500 hover:text-neutral-700 transition-colors"
                disabled={saving}
              >
                {editingIntegration === "jira" ? (
                  <X className="w-4 h-4" />
                ) : (
                  <Pencil className="w-4 h-4" />
                )}
              </button>
            </div>

            {/* Jira Dropdown Selector */}
            {editingIntegration === "jira" && (
              <div className="border rounded-lg p-3 bg-white">
                <Input
                  placeholder="Search Jira users..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="mb-2"
                />
                {loadingOptions ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="w-5 h-5 animate-spin text-neutral-500" />
                  </div>
                ) : (
                  <div className="max-h-48 overflow-y-auto space-y-1">
                    <button
                      onClick={() => handleClearMapping("jira")}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-neutral-100 rounded italic text-neutral-500"
                      disabled={saving}
                    >
                      Clear mapping
                    </button>
                    {filterJiraOptions(searchQuery).map((jiraUser) => (
                      <button
                        key={jiraUser.accountId}
                        onClick={() => handleSelectMapping("jira", jiraUser.accountId)}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-neutral-100 rounded flex items-center justify-between"
                        disabled={saving}
                      >
                        <span>{jiraUser.displayName || jiraUser.email}</span>
                        {user.jira_account_id === jiraUser.accountId && (
                          <Check className="w-4 h-4 text-green-600" />
                        )}
                      </button>
                    ))}
                    {filterJiraOptions(searchQuery).length === 0 && (
                      <p className="text-sm text-neutral-400 py-2 px-3">No users found</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Linear Integration */}
          <div className="space-y-2">
            <div className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 flex items-center justify-center">
                  <svg className="w-6 h-6 text-purple-600" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M2.5 1.5v21h21v-21h-21zm19.5 19.5h-18v-18h18v18zm-16-2h14v-2h-14v2zm0-4h14v-2h-14v2zm0-4h14v-2h-14v2zm0-4h14v-2h-14v2z"/>
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium">Linear</p>
                  <p className="text-xs text-neutral-500">
                    {user.linear_email || <em>Not mapped</em>}
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  if (editingIntegration === "linear") {
                    setEditingIntegration(null)
                    setSearchQuery("")
                  } else {
                    setEditingIntegration("linear")
                    setSearchQuery("")
                  }
                }}
                className="text-neutral-500 hover:text-neutral-700 transition-colors"
                disabled={saving}
              >
                {editingIntegration === "linear" ? (
                  <X className="w-4 h-4" />
                ) : (
                  <Pencil className="w-4 h-4" />
                )}
              </button>
            </div>

            {/* Linear Dropdown Selector */}
            {editingIntegration === "linear" && (
              <div className="border rounded-lg p-3 bg-white">
                <Input
                  placeholder="Search Linear users..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="mb-2"
                />
                {loadingOptions ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="w-5 h-5 animate-spin text-neutral-500" />
                  </div>
                ) : (
                  <div className="max-h-48 overflow-y-auto space-y-1">
                    <button
                      onClick={() => handleClearMapping("linear")}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-neutral-100 rounded italic text-neutral-500"
                      disabled={saving}
                    >
                      Clear mapping
                    </button>
                    {filterLinearOptions(searchQuery).map((linearUser) => (
                      <button
                        key={linearUser.id}
                        onClick={() => handleSelectMapping("linear", linearUser.id)}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-neutral-100 rounded flex items-center justify-between"
                        disabled={saving}
                      >
                        <span>{linearUser.name || linearUser.email}</span>
                        {user.linear_user_id === linearUser.id && (
                          <Check className="w-4 h-4 text-green-600" />
                        )}
                      </button>
                    ))}
                    {filterLinearOptions(searchQuery).length === 0 && (
                      <p className="text-sm text-neutral-400 py-2 px-3">No users found</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
