'use client'

import { useEffect } from 'react'

export default function AuthInterceptor() {
  useEffect(() => {
    // Intercept all fetch requests and handle 401 errors globally
    const originalFetch = window.fetch

    window.fetch = async (...args) => {
      const response = await originalFetch(...args)

      // If 401 Unauthorized, clear auth and redirect to login
      if (response.status === 401) {
        console.log('🔒 401 Unauthorized - redirecting to login')
        localStorage.clear()
        // Use window.location for hard redirect (more reliable than Next.js router)
        window.location.href = '/'
        // Return response even though we're redirecting (prevents errors)
      }

      return response
    }

    // Cleanup: restore original fetch on unmount
    return () => {
      window.fetch = originalFetch
    }
  }, [])

  return null // This component doesn't render anything
}
