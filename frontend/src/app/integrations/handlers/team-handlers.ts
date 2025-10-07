import { toast } from "sonner"
import { API_BASE } from "../types"

/**
 * Fetch team members from selected organization
 */
export async function fetchTeamMembers(
  selectedOrganization: string,
  setLoadingTeamMembers: (loading: boolean) => void,
  setTeamMembersError: (error: string | null) => void,
  setTeamMembers: (members: any[]) => void,
  setTeamMembersDrawerOpen: (open: boolean) => void
): Promise<void> {
  if (!selectedOrganization) {
    toast.error('Please select an organization first')
    return
  }
  setLoadingTeamMembers(true)
  setTeamMembersError(null)

  try {
    const authToken = localStorage.getItem('auth_token')
    if (!authToken) {
      toast.error('Please log in to view team members')
      return
    }

    const response = await fetch(`${API_BASE}/rootly/integrations/${selectedOrganization}/users`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    })

    if (response.ok) {
      const data = await response.json()
      setTeamMembers(data.users || [])
      setTeamMembersDrawerOpen(true)
      toast.success(`Loaded ${data.total_users} team members from ${data.integration_name}`)
    } else {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to fetch team members')
    }
  } catch (error) {
    console.error('Error fetching team members:', error)
    const errorMsg = error instanceof Error ? error.message : 'Failed to fetch team members'
    setTeamMembersError(errorMsg)
    toast.error(errorMsg)
  } finally {
    setLoadingTeamMembers(false)
  }
}

/**
 * Sync users to UserCorrelation table
 */
export async function syncUsersToCorrelation(
  selectedOrganization: string,
  setLoadingTeamMembers: (loading: boolean) => void,
  setTeamMembersError: (error: string | null) => void,
  fetchTeamMembers: () => Promise<void>,
  fetchSyncedUsers: (showToast?: boolean, autoSync?: boolean) => Promise<void>
): Promise<void> {
  if (!selectedOrganization) {
    toast.error('Please select an organization first')
    return
  }
  setLoadingTeamMembers(true)
  setTeamMembersError(null)

  try {
    const authToken = localStorage.getItem('auth_token')
    if (!authToken) {
      toast.error('Please log in to sync users')
      return
    }

    const response = await fetch(`${API_BASE}/rootly/integrations/${selectedOrganization}/sync-users`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    })

    if (response.ok) {
      const data = await response.json()
      const stats = data.stats || data
      toast.success(
        `Synced ${stats.created} new users, updated ${stats.updated} existing users. ` +
        `All team members can now submit burnout surveys via Slack!`
      )
      // Reload the members list and fetch synced users (without showing another toast or auto-syncing again)
      await fetchTeamMembers()
      await fetchSyncedUsers(false, false)
    } else {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to sync users')
    }
  } catch (error) {
    console.error('Error syncing users:', error)
    const errorMsg = error instanceof Error ? error.message : 'Failed to sync users'
    setTeamMembersError(errorMsg)
    toast.error(errorMsg)
  } finally {
    setLoadingTeamMembers(false)
  }
}

/**
 * Sync Slack user IDs to UserCorrelation records
 */
export async function syncSlackUserIds(
  setLoadingTeamMembers: (loading: boolean) => void,
  fetchSyncedUsers: (showToast?: boolean, autoSync?: boolean) => Promise<void>
): Promise<void> {
  setLoadingTeamMembers(true)

  try {
    const authToken = localStorage.getItem('auth_token')
    if (!authToken) {
      toast.error('Please log in to sync Slack user IDs')
      return
    }

    const response = await fetch(`${API_BASE}/integrations/slack/sync-user-ids`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    })

    if (response.ok) {
      const data = await response.json()
      const stats = data.stats || {}
      toast.success(
        `Synced Slack IDs for ${stats.updated} users! ` +
        `${stats.skipped} users skipped (no matching Slack account).`
      )
      // Refresh synced users list
      await fetchSyncedUsers(false)
    } else {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to sync Slack user IDs')
    }
  } catch (error) {
    console.error('Error syncing Slack user IDs:', error)
    const errorMsg = error instanceof Error ? error.message : 'Failed to sync Slack user IDs'
    toast.error(errorMsg)
  } finally {
    setLoadingTeamMembers(false)
  }
}

/**
 * Fetch synced users from database
 */
export async function fetchSyncedUsers(
  selectedOrganization: string,
  setLoadingSyncedUsers: (loading: boolean) => void,
  setSyncedUsers: (users: any[]) => void,
  setShowSyncedUsers: (show: boolean) => void,
  setTeamMembersDrawerOpen: (open: boolean) => void,
  syncUsersToCorrelation: () => Promise<void>,
  showToast: boolean = true,
  autoSync: boolean = true
): Promise<void> {
  if (!selectedOrganization) {
    toast.error('Please select an organization first')
    return
  }

  setLoadingSyncedUsers(true)

  try {
    const authToken = localStorage.getItem('auth_token')
    if (!authToken) {
      toast.error('Please log in to view synced users')
      return
    }

    const response = await fetch(`${API_BASE}/rootly/synced-users?integration_id=${selectedOrganization}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    })

    if (response.ok) {
      const data = await response.json()
      const users = data.users || []
      setSyncedUsers(users)
      setShowSyncedUsers(true)
      setTeamMembersDrawerOpen(true)

      // If no users found, automatically sync them (but not for beta integrations)
      // Only auto-sync once to prevent infinite loops
      if (users.length === 0 && !selectedOrganization.startsWith('beta-') && autoSync) {
        toast.info('No synced users found. Syncing now...')
        setLoadingSyncedUsers(false) // Reset loading state before syncing
        await syncUsersToCorrelation()
        // syncUsersToCorrelation will call fetchSyncedUsers again after syncing
        return
      }

      if (showToast) {
        if (users.length === 0) {
          toast.info('Beta integrations show users from shared access. Use "Sync Members" with your own integration to enable survey submissions.')
        } else {
          toast.success(`Found ${data.total} synced users`)
        }
      }
    } else {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to fetch synced users')
    }
  } catch (error) {
    console.error('Error fetching synced users:', error)
    const errorMsg = error instanceof Error ? error.message : 'Failed to fetch synced users'
    toast.error(errorMsg)
  } finally {
    setLoadingSyncedUsers(false)
  }
}
