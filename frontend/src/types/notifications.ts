export interface Notification {
  id: number
  type: 'invitation' | 'survey' | 'integration' | 'analysis' | 'reminder'
  title: string
  message: string
  action_url?: string
  action_text?: string
  status: 'unread' | 'read' | 'dismissed' | 'acted'
  priority: 'high' | 'normal' | 'low'
  created_at: string
  read_at?: string
  expires_at?: string
  organization_name?: string
  is_expired: boolean
  is_unread: boolean
  icon: string
}

export interface NotificationResponse {
  notifications: Notification[]
  unread_count: number
  total_count: number
}

export interface NotificationActions {
  onRead: (id: number) => void
  onDismiss: (id: number) => void
  onAction: (notification: Notification) => void
}