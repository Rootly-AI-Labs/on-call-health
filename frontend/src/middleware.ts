import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // Only protect /admin routes
  if (request.nextUrl.pathname.startsWith('/admin')) {
    // Skip if no password configured (allow in dev)
    const adminPassword = process.env.ADMIN_PASSWORD
    if (!adminPassword) {
      return NextResponse.next()
    }

    const authHeader = request.headers.get('authorization')
    const expected = Buffer.from(`admin:${adminPassword}`).toString('base64')

    if (authHeader?.replace('Basic ', '') !== expected) {
      return new NextResponse('Authentication Required', {
        status: 401,
        headers: {
          'WWW-Authenticate': 'Basic realm="Admin Area"',
          'Content-Type': 'text/html',
        },
        // Include a simple login form for browser access
      })
    }
  }
  return NextResponse.next()
}

export const config = {
  matcher: '/admin/:path*',
}
