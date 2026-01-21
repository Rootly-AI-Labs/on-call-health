'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense } from 'react'
import localFont from 'next/font/local'

const ppMori = localFont({
  src: [
    {
      path: "../../../../public/fonts/PPMori/PPMori-Regular.otf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../../../../public/fonts/PPMori/PPMori-Semibold.otf",
      weight: "600",
      style: "normal",
    },
  ],
})

function AuthErrorContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const message = searchParams.get('message')

  return (
    <div className={`${ppMori.className} min-h-screen flex items-center justify-center bg-white`}>
      <div className="text-center max-w-md mx-auto px-4">
        <div className="bg-red-100 rounded-full p-4 mx-auto mb-6 w-20 h-20 flex items-center justify-center">
          <svg className="w-10 h-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h2 className="text-2xl font-semibold text-[#100F12] mb-3 font-display">
          Authentication Failed
        </h2>
        <p className="text-neutral-600 mb-8 text-base leading-relaxed">
          {message || 'An error occurred during authentication. Please try again.'}
        </p>
        <button
          onClick={() => router.push('/')}
          className="inline-flex items-center justify-center rounded-2xl bg-[#7a6db4] hover:bg-[#6b5fa8] text-white px-8 py-3 text-lg font-display font-semibold transition-colors"
        >
          Return to Login
        </button>
      </div>
    </div>
  )
}

export default function AuthErrorPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-center">
          <p className="text-neutral-700">Loading...</p>
        </div>
      </div>
    }>
      <AuthErrorContent />
    </Suspense>
  )
}
