/**
 * React hook for backend health monitoring with toast notifications
 */

import { useEffect, useState, useCallback } from 'react'
import { useToast } from '@/hooks/use-toast'
import { healthChecker, HealthCheckResult } from '@/lib/health-check'

export function useBackendHealth(options: {
  showToasts?: boolean
  autoStart?: boolean
  onHealthChange?: (isHealthy: boolean) => void
} = {}) {
  const { showToasts = true, autoStart = true, onHealthChange } = options
  const { toast } = useToast()
  const [healthStatus, setHealthStatus] = useState<HealthCheckResult | null>(null)
  const [isMonitoring, setIsMonitoring] = useState(false)

  // Handle health status changes
  const handleHealthChange = useCallback((result: HealthCheckResult) => {
    const previousStatus = healthStatus
    setHealthStatus(result)

    // Call external handler if provided
    onHealthChange?.(result.isHealthy)

    // Show toast notifications if enabled
    if (showToasts && previousStatus) {
      // Backend went down
      if (previousStatus.isHealthy && !result.isHealthy) {
        toast({
          title: "⚠️ Backend Disconnected",
          description: result.message,
          variant: "destructive",
        })
      }
      // Backend came back up
      else if (!previousStatus.isHealthy && result.isHealthy) {
        toast({
          title: "✅ Backend Connected",
          description: result.message,
        })
      }
    }
  }, [healthStatus, showToasts, toast, onHealthChange])

  // Start monitoring
  const startMonitoring = useCallback(() => {
    if (!isMonitoring) {
      setIsMonitoring(true)
      healthChecker.startMonitoring()
      
      // Subscribe to health changes
      const unsubscribe = healthChecker.subscribe(handleHealthChange)
      
      return unsubscribe
    }
  }, [isMonitoring, handleHealthChange])

  // Check health immediately
  const checkNow = useCallback(async () => {
    const result = await healthChecker.checkHealth()
    handleHealthChange(result)
    return result
  }, [handleHealthChange])

  // Auto-start monitoring on mount
  useEffect(() => {
    if (autoStart) {
      const unsubscribe = startMonitoring()
      
      return () => {
        if (unsubscribe) {
          unsubscribe()
        }
        setIsMonitoring(false)
      }
    }
  }, [autoStart, startMonitoring])

  return {
    healthStatus,
    isMonitoring,
    startMonitoring,
    checkNow,
    isHealthy: healthStatus?.isHealthy ?? null,
    lastChecked: healthStatus?.timestamp ?? null,
  }
}

export default useBackendHealth