/**
 * Backend health check utility
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface HealthCheckResult {
  isHealthy: boolean
  message: string
  timestamp: number
}

export class BackendHealthChecker {
  private static instance: BackendHealthChecker
  private isChecking = false
  private lastCheckTime = 0
  private checkInterval = 10000 // 10 seconds
  private healthStatus: HealthCheckResult | null = null
  private listeners: ((result: HealthCheckResult) => void)[] = []

  static getInstance(): BackendHealthChecker {
    if (!BackendHealthChecker.instance) {
      BackendHealthChecker.instance = new BackendHealthChecker()
    }
    return BackendHealthChecker.instance
  }

  /**
   * Check if backend is healthy
   */
  async checkHealth(): Promise<HealthCheckResult> {
    const now = Date.now()
    
    // Avoid too frequent checks
    if (this.isChecking || (now - this.lastCheckTime) < 5000) {
      return this.healthStatus || { 
        isHealthy: false, 
        message: 'Health check in progress', 
        timestamp: now 
      }
    }

    this.isChecking = true
    this.lastCheckTime = now

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000) // 5 second timeout

      const response = await fetch(`${API_BASE}/health`, {
        method: 'GET',
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
        },
      })

      clearTimeout(timeoutId)

      if (response.ok) {
        const data = await response.json()
        this.healthStatus = {
          isHealthy: true,
          message: data.status === 'healthy' ? 'Backend is running' : 'Backend responded',
          timestamp: now
        }
      } else {
        this.healthStatus = {
          isHealthy: false,
          message: `Backend returned ${response.status}`,
          timestamp: now
        }
      }
    } catch (error) {
      let message = 'Backend is not reachable'
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          message = 'Backend health check timed out'
        } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
          message = 'Backend is not running or not reachable'
        } else {
          message = `Backend error: ${error.message}`
        }
      }

      this.healthStatus = {
        isHealthy: false,
        message,
        timestamp: now
      }
    } finally {
      this.isChecking = false
    }

    // Notify listeners
    this.listeners.forEach(listener => {
      if (this.healthStatus) {
        listener(this.healthStatus)
      }
    })

    return this.healthStatus
  }

  /**
   * Start periodic health checks
   */
  startMonitoring(): void {
    // Initial check
    this.checkHealth()

    // Set up periodic checks
    setInterval(() => {
      this.checkHealth()
    }, this.checkInterval)
  }

  /**
   * Subscribe to health status changes
   */
  subscribe(listener: (result: HealthCheckResult) => void): () => void {
    this.listeners.push(listener)
    
    // Return unsubscribe function
    return () => {
      const index = this.listeners.indexOf(listener)
      if (index > -1) {
        this.listeners.splice(index, 1)
      }
    }
  }

  /**
   * Get current health status without making a new request
   */
  getCurrentStatus(): HealthCheckResult | null {
    return this.healthStatus
  }
}

export const healthChecker = BackendHealthChecker.getInstance()