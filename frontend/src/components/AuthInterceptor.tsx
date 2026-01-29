'use client'

import { useEffect } from 'react'

// Global flag to prevent multiple fetch overrides
let isInterceptorInstalled = false
let originalFetch: typeof window.fetch | null = null

export default function AuthInterceptor() {
  useEffect(() => {
    // Prevent multiple instances from overriding fetch
    if (isInterceptorInstalled) {
      return
    }

    // Store the true original fetch (not a wrapped version)
    if (!originalFetch) {
      originalFetch = window.fetch
    }

    isInterceptorInstalled = true

    // Intercept all fetch requests and handle 401 errors globally
    window.fetch = async (...args) => {
      try {
        const response = await originalFetch!(...args)

        // If 401 Unauthorized, clear auth and redirect to login
        if (response.status === 401) {
          console.log('🔒 401 Unauthorized - redirecting to login')

          // Clear localStorage with error handling
          try {
            localStorage.clear()
          } catch (error) {
            console.error('Failed to clear localStorage:', error)
          }

          // Redirect to login with error handling
          try {
            window.location.href = '/auth/login'
          } catch (error) {
            console.error('Failed to redirect:', error)
            // Fallback: try using window.location.replace
            window.location.replace('/auth/login')
          }

          // Return a rejected promise to prevent further processing
          return Promise.reject(new Error('Unauthorized - redirecting to login'))
        }

        // Clone response to prevent "body already consumed" errors
        return response.clone()
      } catch (error) {
        // Re-throw errors to maintain normal error handling
        throw error
      }
    }

    // Cleanup: restore original fetch only if this was the installer
    return () => {
      if (isInterceptorInstalled && originalFetch) {
        window.fetch = originalFetch
        isInterceptorInstalled = false
      }
    }
  }, [])

  return null // This component doesn't render anything
}
