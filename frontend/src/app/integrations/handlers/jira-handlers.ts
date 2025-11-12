import { toast } from "sonner"
import { type JiraIntegration, API_BASE } from "../types"

/**
 * Load Jira integration from API with caching
 */
export async function loadJiraIntegration(
  forceRefresh: boolean,
  setJiraIntegration: (integration: JiraIntegration | null) => void,
  setLoadingJira: (loading: boolean) => void
): Promise<void> {
  if (!forceRefresh) {
    const cached = localStorage.getItem('jira_integration')
    if (cached) {
      try {
        const jiraData = JSON.parse(cached)
        setJiraIntegration(jiraData.connected ? jiraData.integration : null)
        setLoadingJira(false)
        return
      } catch (e) {
        // Cache parse failed, continue to API call
      }
    }
  }

  try {
    const authToken = localStorage.getItem('auth_token')
    if (!authToken) return

    const response = await fetch(`${API_BASE}/integrations/jira/status`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    })

    const jiraData = response.ok ? await response.json() : { connected: false, integration: null }
    setJiraIntegration(jiraData.connected ? jiraData.integration : null)
    localStorage.setItem('jira_integration', JSON.stringify(jiraData))
  } catch (error) {
    console.error('Error loading Jira integration:', error)
  } finally {
    setLoadingJira(false)
  }
}

/**
 * Connect Jira integration via OAuth
 */
export async function handleJiraConnect(
  setIsConnectingJira: (loading: boolean) => void,
  setActiveEnhancementTab: (tab: "github" | "slack" | "jira" | null) => void,
  loadJiraIntegration: () => Promise<void>
): Promise<void> {
  try {
    setIsConnectingJira(true)
    const authToken = localStorage.getItem('auth_token')
    if (!authToken) {
      toast.error('Please log in to connect Jira')
      return
    }

    // Request authorization URL from backend
    const response = await fetch(`${API_BASE}/integrations/jira/connect`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to initiate Jira OAuth')
    }

    const data = await response.json()
    const authUrl = data.authorization_url

    if (!authUrl) {
      throw new Error('No authorization URL received from server')
    }

    // Store state to validate callback
    if (data.state) {
      sessionStorage.setItem('jira_oauth_state', data.state)
    }

    // Redirect to Jira OAuth
    window.location.href = authUrl

  } catch (error) {
    console.error('Error connecting Jira:', error)
    toast.error(error instanceof Error ? error.message : 'Failed to connect Jira')
    setIsConnectingJira(false)
  }
}

/**
 * Disconnect Jira integration
 */
export async function handleJiraDisconnect(
  setIsDisconnectingJira: (loading: boolean) => void,
  setJiraIntegration: (integration: JiraIntegration | null) => void,
  setActiveEnhancementTab: (tab: "github" | "slack" | "jira" | null) => void
): Promise<void> {
  try {
    setIsDisconnectingJira(true)
    const authToken = localStorage.getItem('auth_token')
    if (!authToken) {
      toast.error('Authentication required')
      return
    }

    const response = await fetch(`${API_BASE}/integrations/jira/disconnect`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${authToken}` }
    })

    if (!response.ok) {
      throw new Error('Failed to disconnect Jira')
    }

    setJiraIntegration(null)
    localStorage.removeItem('jira_integration')
    setActiveEnhancementTab(null)
    toast.success('Jira disconnected successfully')

  } catch (error) {
    console.error('Error disconnecting Jira:', error)
    toast.error('Failed to disconnect Jira')
  } finally {
    setIsDisconnectingJira(false)
  }
}

/**
 * Test Jira integration connection
 */
export async function handleJiraTest(
  toast: any
): Promise<void> {
  try {
    const authToken = localStorage.getItem('auth_token')
    if (!authToken) {
      toast.error('Authentication required')
      return
    }

    const response = await fetch(`${API_BASE}/integrations/jira/test`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authToken}` }
    })

    if (!response.ok) {
      throw new Error('Connection test failed')
    }

    const result = await response.json()

    if (result.success) {
      toast.success('Jira connection is working correctly!')

      // Log the data we're collecting
      console.log('[Jira] Test successful, permissions:', result.permissions)
      console.log('[Jira] User info:', result.user_info)
    } else {
      toast.error(result.message || 'Connection test failed')
    }

  } catch (error) {
    console.error('Error testing Jira connection:', error)
    toast.error('Failed to test connection')
  }
}
