import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // Only protect /api/admin routes (the actual admin API endpoints)
  // The /admin page has its own login form
  if (request.nextUrl.pathname.startsWith('/api/admin')) {
    // Skip if no password configured (allow in dev)
    const adminPassword = process.env.ADMIN_PASSWORD
    if (!adminPassword) {
      return NextResponse.next()
    }

    // Skip for localhost development (optional - remove for production)
    if (request.nextUrl.hostname === 'localhost' || request.nextUrl.hostname === '127.0.0.1') {
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
      })
    }
  }
  return NextResponse.next()
}

export const config = {
  matcher: '/api/admin/:path*',
}
