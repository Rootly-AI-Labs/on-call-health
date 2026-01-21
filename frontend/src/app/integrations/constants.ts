/**
 * Integration constants to avoid magic numbers and ensure consistency
 */

// Timeout values for different integration operations
export const INTEGRATION_TIMEOUTS = {
  // Token-based integrations (GitHub, Slack) - faster auth
  TOKEN_AUTH_MODAL_DELAY: 500, // ms - time to wait before showing modal after token auth

  // OAuth integrations (Jira, Linear) - slower OAuth flow
  OAUTH_MODAL_DELAY: 1000, // ms - time to wait before showing modal after OAuth callback

  // Connection verification polling
  CONNECTION_POLL_INTERVAL: 500, // ms - how often to poll for connection status
  CONNECTION_MAX_RETRIES: 20, // max number of retry attempts (20 * 500ms = 10 seconds)

  // Background refresh
  REFRESH_DEBOUNCE: 100, // ms - debounce delay for background refresh
  PERMISSION_CHECK_DEBOUNCE: 300, // ms - debounce delay for permission checks
} as const

// Integration types
export const INTEGRATION_TYPES = {
  GITHUB: 'github',
  SLACK: 'slack',
  JIRA: 'jira',
  LINEAR: 'linear',
} as const

export type IntegrationType = typeof INTEGRATION_TYPES[keyof typeof INTEGRATION_TYPES]

/**
 * Get the appropriate modal delay for an integration type
 */
export function getModalDelay(type: IntegrationType): number {
  if (type === INTEGRATION_TYPES.GITHUB || type === INTEGRATION_TYPES.SLACK) {
    return INTEGRATION_TIMEOUTS.TOKEN_AUTH_MODAL_DELAY
  }
  if (type === INTEGRATION_TYPES.JIRA || type === INTEGRATION_TYPES.LINEAR) {
    return INTEGRATION_TIMEOUTS.OAUTH_MODAL_DELAY
  }
  return INTEGRATION_TIMEOUTS.TOKEN_AUTH_MODAL_DELAY // fallback to token auth delay
}
