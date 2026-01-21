'use client'

import { useEffect, useRef, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { Loader2 } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function LinearCallbackContent() {
  const searchParams = useSearchParams()
  const ranRef = useRef(false)

  useEffect(() => {
    // StrictMode double-invokes effects in dev — guard it
    if (ranRef.current) return
    ranRef.current = true

    const lockKey = 'linear_oauth_processing'
    if (sessionStorage.getItem(lockKey)) return
    sessionStorage.setItem(lockKey, '1')

    const run = async () => {
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const err = searchParams.get('error')
      const errDesc = searchParams.get('error_description') || ''

      if (err) {
        const errorMsg = `${err}${errDesc ? `: ${errDesc}` : ''}`
        sessionStorage.setItem('linear_callback_error', errorMsg)
        window.location.href = `/integrations?linear_error=1`
        sessionStorage.removeItem(lockKey)
        return
      }

      if (!code) {
        const errorMsg = 'Invalid callback parameters - missing code'
        sessionStorage.setItem('linear_callback_error', errorMsg)
        window.location.href = `/integrations?linear_error=1`
        sessionStorage.removeItem(lockKey)
        return
      }

      // State hint only (backend does real verify)
      const stored = sessionStorage.getItem('linear_oauth_state')
      if (stored && state && stored !== state) {
        console.warn('[Linear OAuth] State mismatch (backend will validate).')
      }
      sessionStorage.removeItem('linear_oauth_state')

      try {
        const authToken = typeof window !== 'undefined'
          ? localStorage.getItem('auth_token')
          : null

        const resp = await fetch(`${API_BASE}/integrations/linear/callback`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
          },
          body: JSON.stringify({ code, state }),
          credentials: 'include',
        })

        if (resp.redirected) {
          window.location.href = resp.url
          return
        }

        const text = await resp.text()
        let data: any = {}
        try { data = text ? JSON.parse(text) : {} } catch {}

        if (resp.ok) {
          const redirect = data.redirect_url || '/integrations?linear_connected=1'
          window.location.href = redirect
        } else {
          const msg = (data && (data.detail || data.message)) || text || 'Failed to complete OAuth flow'
          sessionStorage.setItem('linear_callback_error', msg)
          window.location.href = `/integrations?linear_error=1`
        }
      } catch (e: any) {
        const msg = e?.message || 'Network error completing OAuth flow'
        sessionStorage.setItem('linear_callback_error', msg)
        window.location.href = `/integrations?linear_error=1`
      } finally {
        sessionStorage.removeItem(lockKey)
      }
    }

    run()
  }, [searchParams])

  return (
    <div className="flex min-h-screen items-center justify-center bg-white">
      <div className="text-center space-y-4">
        <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
        <h1 className="text-xl font-semibold">Connecting Linear...</h1>
        <p className="text-sm text-muted-foreground">
          Please wait while we complete the integration.
        </p>
      </div>
    </div>
  )
}

export default function LinearCallbackPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-white">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
          <h1 className="text-xl font-semibold">Loading...</h1>
        </div>
      </div>
    }>
      <LinearCallbackContent />
    </Suspense>
  )
}
