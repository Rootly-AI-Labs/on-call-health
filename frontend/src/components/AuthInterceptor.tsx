'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function AuthInterceptor() {
  const router = useRouter()

  useEffect(() => {
    // Intercept all fetch requests and handle 401 errors globally
    const originalFetch = window.fetch

    window.fetch = async (...args) => {
      const response = await originalFetch(...args)

      // If 401 Unauthorized, clear auth and redirect to login
      if (response.status === 401) {
        console.log('🔒 401 Unauthorized - redirecting to login')
        localStorage.clear()
        router.push('/')
      }

      return response
    }

    // Cleanup: restore original fetch on unmount
    return () => {
      window.fetch = originalFetch
    }
  }, [router])

  return null // This component doesn't render anything
}
