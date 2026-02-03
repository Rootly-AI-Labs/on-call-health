/**
 * Authentication utility functions for token management
 */

export interface TokenPayload {
  sub: string
  exp: number
  [key: string]: any
}

/**
 * Get a valid JWT token from localStorage
 * Returns null if token is expired or invalid
 */
export function getValidToken(): string | null {
  const token = localStorage.getItem('auth_token')
  if (!token) return null

  try {
    const payload = parseTokenPayload(token)
    if (!payload) return null

    // Check if token is expired (with 60 second buffer)
    const expiresAt = payload.exp * 1000
    const now = Date.now()
    const bufferMs = 60 * 1000 // 60 seconds

    if (now >= expiresAt - bufferMs) {
      // Token is expired or about to expire
      clearAuthData()
      return null
    }

    return token
  } catch (error) {
    // Invalid token format
    clearAuthData()
    return null
  }
}

/**
 * Parse JWT token payload without verification
 * (Verification happens on backend)
 */
export function parseTokenPayload(token: string): TokenPayload | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null

    const payload = JSON.parse(atob(parts[1]))
    return payload
  } catch {
    return null
  }
}

/**
 * Check if token is expired
 */
export function isTokenExpired(token: string): boolean {
  const payload = parseTokenPayload(token)
  if (!payload || !payload.exp) return true

  const expiresAt = payload.exp * 1000
  return Date.now() >= expiresAt
}

/**
 * Get token expiration time in milliseconds
 */
export function getTokenExpiration(token: string): number | null {
  const payload = parseTokenPayload(token)
  if (!payload || !payload.exp) return null
  return payload.exp * 1000
}

/**
 * Clear all authentication data from localStorage
 */
export function clearAuthData(): void {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('user_name')
  localStorage.removeItem('user_email')
  localStorage.removeItem('user_role')
  localStorage.removeItem('user_id')
}

/**
 * Redirect to login page
 */
export function redirectToLogin(): void {
  window.location.href = '/'
}
