"use client"

import { useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'

export default function AcceptInvitationPage() {
  const params = useParams()
  const router = useRouter()
  const invitationId = params.invitationId as string

  // Redirect to management page where invitations are handled
  useEffect(() => {
    if (invitationId) {
      router.push('/integrations?openOrgModal=true')
    }
  }, [invitationId, router])

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex items-center justify-center p-4">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin text-purple-600 mx-auto mb-4" />
        <p className="text-neutral-700">Redirecting to organization management...</p>
      </div>
    </div>
  )
}