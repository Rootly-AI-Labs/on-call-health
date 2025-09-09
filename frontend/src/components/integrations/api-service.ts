const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Integration {
  id: number
  platform: string
  name: string
  configuration: any
  status: string
  created_at: string
  updated_at: string
  last_sync?: string
  sync_status?: string
  error_message?: string
}

export interface GitHubIntegration {
  id: number
  user_id: number
  github_token_suffix: string
  github_username: string
  github_organization: string
  created_at: string
  status: 'active' | 'inactive' | 'error'
}

export interface SlackIntegration {
  id: number
  user_id: number
  team_id: string
  team_name: string
  webhook_url_suffix: string
  bot_token_suffix: string
  created_at: string
  status: 'active' | 'inactive' | 'error'
}

export interface PreviewData {
  name?: string
  description?: string
  organization?: string
  [key: string]: any
}

export class IntegrationsAPIService {
  private static getAuthHeaders() {
    const authToken = localStorage.getItem('auth_token')
    return {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json'
    }
  }

  // Cache management
  static loadFromCacheSync(): boolean {
    try {
      const cached = localStorage.getItem('all_integrations')
      if (!cached) return false

      const timestamp = localStorage.getItem('all_integrations_timestamp')
      if (!timestamp) return false

      const cacheAge = Date.now() - parseInt(timestamp)
      const maxCacheAge = 5 * 60 * 1000 // 5 minutes
      
      return cacheAge <= maxCacheAge
    } catch (error) {
      
      return false
    }
  }

  static isCacheStale(): boolean {
    const cacheTimestamp = localStorage.getItem('all_integrations_timestamp')
    if (!cacheTimestamp) return true
    
    const cacheAge = Date.now() - parseInt(cacheTimestamp)
    const maxCacheAge = 5 * 60 * 1000 // 5 minutes
    return cacheAge > maxCacheAge
  }

  // Rootly API
  static async loadRootlyIntegrations(): Promise<Integration[]> {
    try {
      const response = await fetch(`${API_BASE}/rootly/integrations`, {
        headers: this.getAuthHeaders()
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()
      return data.integrations.map((i: any) => ({ ...i, platform: 'rootly' }))
    } catch (error) {
      console.error('Error loading Rootly integrations:', error)
      return []
    }
  }

  // PagerDuty API
  static async loadPagerDutyIntegrations(): Promise<Integration[]> {
    try {
      const response = await fetch(`${API_BASE}/pagerduty/integrations`, {
        headers: this.getAuthHeaders()
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()
      return data.integrations.map((i: any) => ({ ...i, platform: 'pagerduty' }))
    } catch (error) {
      console.error('Error loading PagerDuty integrations:', error)
      return []
    }
  }

  // GitHub API
  static async loadGitHubIntegration(): Promise<{connected: boolean, integration: GitHubIntegration | null}> {
    try {
      const response = await fetch(`${API_BASE}/integrations/github/status`, {
        headers: this.getAuthHeaders()
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error loading GitHub integration:', error)
      return { connected: false, integration: null }
    }
  }

  // Slack API
  static async loadSlackIntegration(): Promise<{integration: SlackIntegration | null}> {
    try {
      const response = await fetch(`${API_BASE}/integrations/slack/status`, {
        headers: this.getAuthHeaders()
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error loading Slack integration:', error)
      return { integration: null }
    }
  }

  // Load all integrations (optimized)
  static async loadAllIntegrations(): Promise<{
    integrations: Integration[]
    githubIntegration: GitHubIntegration | null
    slackIntegration: SlackIntegration | null
  }> {
    try {
      const [rootlyData, pagerdutyData, githubData, slackData] = await Promise.all([
        this.loadRootlyIntegrations(),
        this.loadPagerDutyIntegrations(),
        this.loadGitHubIntegration(),
        this.loadSlackIntegration()
      ])

      const allIntegrations = [...rootlyData, ...pagerdutyData]

      // Update cache
      localStorage.setItem('all_integrations', JSON.stringify(allIntegrations))
      localStorage.setItem('all_integrations_timestamp', Date.now().toString())
      localStorage.setItem('github_integration', JSON.stringify(githubData))
      localStorage.setItem('slack_integration', JSON.stringify(slackData))

      return {
        integrations: allIntegrations,
        githubIntegration: githubData.connected ? githubData.integration : null,
        slackIntegration: slackData.integration
      }
    } catch (error) {
      console.error('Error loading all integrations:', error)
      throw error
    }
  }

  // Background refresh (non-blocking)
  static async backgroundRefresh(): Promise<void> {
    try {
      await this.loadAllIntegrations()
      
    } catch (error) {
      console.error('Background refresh failed:', error)
      throw error
    }
  }

  // Test connection
  static async testConnection(platform: "rootly" | "pagerduty", token: string): Promise<{
    success: boolean
    data?: PreviewData
    error?: string
    duplicate?: any
  }> {
    try {
      const response = await fetch(`${API_BASE}/${platform}/token/test`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ token })
      })

      const data = await response.json()

      if (!response.ok) {
        return {
          success: false,
          error: data.detail || `HTTP ${response.status}`
        }
      }

      return {
        success: true,
        data: data
      }
    } catch (error) {
      console.error(`Error testing ${platform} connection:`, error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  // User info
  static async loadUserInfo(): Promise<{name: string, email: string, avatar?: string} | null> {
    try {
      const response = await fetch(`${API_BASE}/auth/user/me`, {
        headers: this.getAuthHeaders()
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error loading user info:', error)
      return null
    }
  }

  // Create integration
  static async createIntegration(platform: "rootly" | "pagerduty", data: {
    token: string
    nickname: string
  }): Promise<{success: boolean, data?: any, error?: string}> {
    try {
      const response = await fetch(`${API_BASE}/${platform}/integrations`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(data)
      })

      const result = await response.json()

      if (!response.ok) {
        return {
          success: false,
          error: result.detail || `HTTP ${response.status}`
        }
      }

      return {
        success: true,
        data: result
      }
    } catch (error) {
      console.error(`Error creating ${platform} integration:`, error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  // Update integration
  static async updateIntegration(integrationId: number, updates: {
    name?: string
    [key: string]: any
  }): Promise<{success: boolean, error?: string}> {
    try {
      const response = await fetch(`${API_BASE}/integrations/${integrationId}`, {
        method: 'PUT',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(updates)
      })

      if (!response.ok) {
        const error = await response.json()
        return {
          success: false,
          error: error.detail || `HTTP ${response.status}`
        }
      }

      return { success: true }
    } catch (error) {
      console.error('Error updating integration:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  // Delete integration
  static async deleteIntegration(integrationId: number): Promise<{success: boolean, error?: string}> {
    try {
      const response = await fetch(`${API_BASE}/integrations/${integrationId}`, {
        method: 'DELETE',
        headers: this.getAuthHeaders()
      })

      if (!response.ok) {
        const error = await response.json()
        return {
          success: false,
          error: error.detail || `HTTP ${response.status}`
        }
      }

      return { success: true }
    } catch (error) {
      console.error('Error deleting integration:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  // AI/LLM Configuration
  static async loadLlmConfig(): Promise<{has_token: boolean, provider?: string, token_suffix?: string} | null> {
    try {
      const response = await fetch(`${API_BASE}/ai/config`, {
        headers: this.getAuthHeaders()
      })

      if (!response.ok) {
        return null
      }

      return await response.json()
    } catch (error) {
      console.error('Error loading LLM config:', error)
      return null
    }
  }

  static async saveLlmConfig(config: {
    provider: string
    model: string
    token: string
  }): Promise<{success: boolean, error?: string}> {
    try {
      const response = await fetch(`${API_BASE}/ai/config`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(config)
      })

      const result = await response.json()

      if (!response.ok) {
        return {
          success: false,
          error: result.detail || `HTTP ${response.status}`
        }
      }

      return { success: true }
    } catch (error) {
      console.error('Error saving LLM config:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  static async deleteLlmConfig(): Promise<{success: boolean, error?: string}> {
    try {
      const response = await fetch(`${API_BASE}/ai/config`, {
        method: 'DELETE',
        headers: this.getAuthHeaders()
      })

      if (!response.ok) {
        const error = await response.json()
        return {
          success: false,
          error: error.detail || `HTTP ${response.status}`
        }
      }

      return { success: true }
    } catch (error) {
      console.error('Error deleting LLM config:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }
}