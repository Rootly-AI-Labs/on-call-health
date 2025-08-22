import { z } from "zod"

// Token validation functions
export const isValidRootlyToken = (token: string): boolean => {
  return /^rootly_[a-f0-9]{64}$/.test(token)
}

export const isValidPagerDutyToken = (token: string): boolean => {
  return /^[A-Za-z0-9+_-]{20,32}$/.test(token)
}

// Form schemas
export const rootlyFormSchema = z.object({
  rootlyToken: z.string()
    .min(1, "Token is required")
    .refine(isValidRootlyToken, "Invalid Rootly token format"),
  nickname: z.string().min(1, "Name is required"),
})

export const pagerdutyFormSchema = z.object({
  pagerdutyToken: z.string()
    .min(1, "Token is required")
    .refine(isValidPagerDutyToken, "Invalid PagerDuty token format"),
  nickname: z.string().min(1, "Name is required"),
})

export type RootlyFormData = z.infer<typeof rootlyFormSchema>
export type PagerDutyFormData = z.infer<typeof pagerdutyFormSchema>

// Validation helpers
export const validateGitHubUsername = (username: string): boolean => {
  return /^[a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,38}$/i.test(username)
}

export const validateSlackWebhookUrl = (url: string): boolean => {
  return /^https:\/\/hooks\.slack\.com\/services\//.test(url)
}

export const validateEmail = (email: string): boolean => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

// Connection status helpers
export const getConnectionStatusColor = (status: 'idle' | 'success' | 'error' | 'duplicate'): string => {
  switch (status) {
    case 'success': return 'text-green-600'
    case 'error': return 'text-red-600' 
    case 'duplicate': return 'text-amber-600'
    default: return 'text-gray-600'
  }
}

export const getConnectionStatusMessage = (
  status: 'idle' | 'success' | 'error' | 'duplicate',
  platform: string,
  error?: string
): string => {
  switch (status) {
    case 'success': return `${platform} connection verified successfully`
    case 'error': return error || `Failed to connect to ${platform}`
    case 'duplicate': return `This ${platform} integration already exists`
    default: return ''
  }
}

// Integration status helpers
export const getIntegrationStatusBadge = (status: string) => {
  switch (status.toLowerCase()) {
    case 'active':
      return { color: 'bg-green-100 text-green-800', text: 'Active' }
    case 'inactive':
      return { color: 'bg-gray-100 text-gray-800', text: 'Inactive' }
    case 'error':
      return { color: 'bg-red-100 text-red-800', text: 'Error' }
    case 'syncing':
      return { color: 'bg-blue-100 text-blue-800', text: 'Syncing' }
    default:
      return { color: 'bg-gray-100 text-gray-800', text: status || 'Unknown' }
  }
}

// Platform helpers
export const getPlatformIcon = (platform: string) => {
  switch (platform.toLowerCase()) {
    case 'rootly':
      return '🔥'
    case 'pagerduty':
      return '📟'
    case 'github':
      return '🐙'
    case 'slack':
      return '💬'
    default:
      return '🔗'
  }
}

export const getPlatformColor = (platform: string) => {
  switch (platform.toLowerCase()) {
    case 'rootly':
      return 'border-red-200 bg-red-50'
    case 'pagerduty':
      return 'border-green-200 bg-green-50'
    case 'github':
      return 'border-gray-200 bg-gray-50'
    case 'slack':
      return 'border-purple-200 bg-purple-50'
    default:
      return 'border-gray-200 bg-gray-50'
  }
}