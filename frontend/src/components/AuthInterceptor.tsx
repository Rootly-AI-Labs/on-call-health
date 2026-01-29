'use client'

import { useEffect } from 'react'

// Global flag to prevent multiple fetch overrides
let isInterceptorInstalled = false
let originalFetch: typeof window.fetch | null = null

// Helper to clear only auth-related localStorage items
function clearAuthData() {
  try {
    const keysToRemove = ['auth_token', 'user_id', 'user_email', 'user_name', 'user_role', 'user_avatar', 'user_organization_id']
    keysToRemove.forEach(key => {
      try {
        localStorage.removeItem(key)
      } catch (e) {
        console.error(`Failed to remove ${key}:`, e)
      }
    })
  } catch (error) {
    console.error('Failed to clear auth data:', error)
  }
}

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

    // Validate originalFetch exists
    if (!originalFetch) {
      console.error('Original fetch is not available')
      return
    }

    isInterceptorInstalled = true

    // Intercept all fetch requests and handle 401 errors for AUTH endpoints only
    window.fetch = async (...args) => {
      // Ensure originalFetch is available
      if (!originalFetch) {
        throw new Error('Original fetch is not available')
      }

      try {
        const response = await originalFetch(...args)

        // Only handle 401 for auth-related endpoints (user authentication)
        // Don't interfere with GitHub/Slack/Jira/etc integration auth
        const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || ''
        const isAuthEndpoint = url.includes('/auth/') || url.includes('/user/me')

        // Check for 401 BEFORE consuming the response (auth endpoints only)
        if (response.status === 401 && isAuthEndpoint) {
          console.log('🔒 401 Unauthorized on auth endpoint - redirecting to login')

          // Clear only auth-related data (not all localStorage)
          clearAuthData()

          // Redirect to login with error handling
          try {
            window.location.href = '/auth/login'
          } catch (error) {
            console.error('Failed to redirect:', error)
            // Fallback: try using window.location.replace
            try {
              window.location.replace('/auth/login')
            } catch (replaceError) {
              console.error('Failed to replace location:', replaceError)
            }
          }

          // Return cloned response so calling code can handle it if needed
          // (e.g., display error message before redirect completes)
          return response.clone()
        }

        // Clone response for all responses to prevent "body already consumed" errors
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
