"use client"

import dynamic from 'next/dynamic'
import { Suspense } from 'react'
import { Loader2 } from 'lucide-react'

// Dynamic import to reduce initial bundle size
const IntegrationsLayout = dynamic(
  () => import('@/components/integrations/integrations-layout'),
  {
    loading: () => (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          <p className="text-gray-600">Loading integrations...</p>
        </div>
      </div>
    ),
    ssr: false // Client-side only for performance
  }
)

export default function IntegrationsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          <p className="text-gray-600">Initializing...</p>
        </div>
      </div>
    }>
      <IntegrationsLayout />
    </Suspense>
  )
}