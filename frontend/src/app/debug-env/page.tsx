'use client'

export default function DebugEnvPage() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Environment Variables Debug</h1>
      <div className="bg-gray-100 p-4 rounded">
        <p><strong>NEXT_PUBLIC_API_BASE_URL:</strong> {process.env.NEXT_PUBLIC_API_BASE_URL || 'UNDEFINED'}</p>
        <p><strong>NEXT_PUBLIC_SLACK_CLIENT_ID:</strong> {process.env.NEXT_PUBLIC_SLACK_CLIENT_ID || 'UNDEFINED'}</p>
        <p><strong>NODE_ENV:</strong> {process.env.NODE_ENV}</p>
      </div>
    </div>
  )
}