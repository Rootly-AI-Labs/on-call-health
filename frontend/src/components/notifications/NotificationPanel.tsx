'use client'

import React, { useState, useEffect } from 'react'
import { Bell, X, Check, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useToast } from '@/hooks/use-toast'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

interface Notification {
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

interface NotificationResponse {
  notifications: Notification[]
  unread_count: number
  total_count: number
}

const NotificationIcon = ({ type }: { type: string }) => {
  const icons = {
    invitation: '🏢',
    survey: '📊',
    integration: '🔗',
    analysis: '📈',
    reminder: '⏰',
    welcome: '🎉'
  }
  return <span className="text-lg">{icons[type as keyof typeof icons] || '📌'}</span>
}

const PriorityBadge = ({ priority }: { priority: string }) => {
  if (priority === 'high') {
    return <Badge variant="destructive" className="h-4 text-xs ml-2">Urgent</Badge>
  }
  return null
}

const NotificationItem = ({
  notification,
  onRead,
  onDismiss,
  onAction
}: {
  notification: Notification
  onRead: (id: number) => void
  onDismiss: (id: number) => void
  onAction: (notification: Notification) => void
}) => {
  const isUnread = notification.is_unread
  const isExpired = notification.is_expired

  return (
    <Card className={`mb-2 transition-all duration-200 ${
      isUnread ? 'bg-blue-50 border-blue-200 shadow-sm' : 'bg-gray-50 border-gray-200'
    } ${isExpired ? 'opacity-60' : ''}`}>
      <CardContent className="p-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {/* Header */}
            <div className="flex items-center mb-1">
              <NotificationIcon type={notification.type} />
              <h4 className="font-medium text-sm ml-2 flex-1">{notification.title}</h4>
              <PriorityBadge priority={notification.priority} />
              {isUnread && (
                <div className="w-2 h-2 bg-blue-500 rounded-full ml-2"></div>
              )}
            </div>

            {/* Message */}
            <p className="text-xs text-gray-600 ml-7 mb-2">{notification.message}</p>

            {/* Organization */}
            {notification.organization_name && (
              <p className="text-xs text-gray-500 ml-7 mb-2">
                {notification.organization_name}
              </p>
            )}

            {/* Timestamp */}
            <p className="text-xs text-gray-400 ml-7 mb-2">
              {new Date(notification.created_at).toLocaleDateString()} at{' '}
              {new Date(notification.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
              })}
            </p>

            {/* Actions */}
            {!isExpired && (
              <div className="flex items-center space-x-2 ml-7">
                {notification.action_url && notification.action_text && (
                  <Button
                    size="sm"
                    onClick={() => onAction(notification)}
                    className="h-7 text-xs"
                  >
                    {notification.action_text}
                    {notification.action_url.startsWith('http') && (
                      <ExternalLink className="h-3 w-3 ml-1" />
                    )}
                  </Button>
                )}

                {isUnread && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onRead(notification.id)}
                    className="h-7 text-xs"
                  >
                    <Check className="h-3 w-3 mr-1" />
                    Mark Read
                  </Button>
                )}

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onDismiss(notification.id)}
                  className="h-7 text-xs"
                >
                  <X className="h-3 w-3 mr-1" />
                  Dismiss
                </Button>
              </div>
            )}

            {/* Expired notice */}
            {isExpired && (
              <p className="text-xs text-gray-400 ml-7 italic">
                This notification has expired
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function NotificationPanel() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const { toast } = useToast()

  // Fetch notifications
  const fetchNotifications = async () => {
    try {
      setIsLoading(true)
      const response = await fetch(`${API_BASE}/api/notifications/`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })

      if (response.ok) {
        const data: NotificationResponse = await response.json()
        setNotifications(data.notifications)
        setUnreadCount(data.unread_count)
      } else {
        console.error('Failed to fetch notifications:', response.status)
      }
    } catch (error) {
      console.error('Error fetching notifications:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Auto-refresh notifications every 30 seconds
  useEffect(() => {
    fetchNotifications()

    const interval = setInterval(fetchNotifications, 30000)
    return () => clearInterval(interval)
  }, [])

  // Mark notification as read
  const handleMarkAsRead = async (notificationId: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/notifications/${notificationId}/read`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })

      if (response.ok) {
        await fetchNotifications() // Refresh notifications
        toast({
          title: "Notification marked as read",
          description: "The notification has been marked as read."
        })
      }
    } catch (error) {
      console.error('Error marking notification as read:', error)
      toast({
        title: "Error",
        description: "Failed to mark notification as read.",
        variant: "destructive"
      })
    }
  }

  // Dismiss notification
  const handleDismiss = async (notificationId: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/notifications/${notificationId}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })

      if (response.ok) {
        await fetchNotifications() // Refresh notifications
        toast({
          title: "Notification dismissed",
          description: "The notification has been dismissed."
        })
      }
    } catch (error) {
      console.error('Error dismissing notification:', error)
      toast({
        title: "Error",
        description: "Failed to dismiss notification.",
        variant: "destructive"
      })
    }
  }

  // Handle notification action (Accept invitation, View results, etc.)
  const handleNotificationAction = async (notification: Notification) => {
    if (!notification.action_url) return

    // If external URL, open in new tab
    if (notification.action_url.startsWith('http')) {
      window.open(notification.action_url, '_blank')
    } else {
      // Internal URL, navigate
      window.location.href = notification.action_url
    }

    // Mark as read when action is taken
    await handleMarkAsRead(notification.id)
    setIsOpen(false)
  }

  // Mark all as read
  const handleMarkAllAsRead = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/notifications/mark-all-read`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })

      if (response.ok) {
        await fetchNotifications() // Refresh notifications
        toast({
          title: "All notifications marked as read",
          description: "All notifications have been marked as read."
        })
      }
    } catch (error) {
      console.error('Error marking all notifications as read:', error)
      toast({
        title: "Error",
        description: "Failed to mark all notifications as read.",
        variant: "destructive"
      })
    }
  }

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="relative p-2 h-9 w-9"
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 text-xs flex items-center justify-center"
            >
              {unreadCount > 99 ? '99+' : unreadCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        className="w-96 p-0 max-h-[80vh]"
        align="end"
        side="bottom"
        sideOffset={8}
        onWheel={(e) => e.stopPropagation()}
      >
        <div className="border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm">Notifications</h3>
            <div className="flex items-center space-x-2">
              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleMarkAllAsRead}
                  className="h-7 text-xs"
                >
                  Mark all read
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsOpen(false)}
                className="h-7 w-7 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {unreadCount > 0 && (
            <p className="text-xs text-gray-500 mt-1">
              {unreadCount} unread notification{unreadCount !== 1 ? 's' : ''}
            </p>
          )}
        </div>

        <div className="max-h-96 overflow-y-auto overflow-x-hidden scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
          <div className="p-4">
            {isLoading ? (
              <div className="text-center text-gray-500 py-8">
                <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Loading notifications...</p>
              </div>
            ) : notifications.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No notifications</p>
                <p className="text-xs mt-1">You're all caught up!</p>
              </div>
            ) : (
              <div className="space-y-2">
                {notifications.map((notification) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onRead={handleMarkAsRead}
                    onDismiss={handleDismiss}
                    onAction={handleNotificationAction}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="border-t border-gray-200 p-3 text-center">
          <Button
            variant="ghost"
            size="sm"
            className="text-xs text-gray-500"
            onClick={() => {
              // Could navigate to full notifications page
              setIsOpen(false)
            }}
          >
            View all notifications
          </Button>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export default NotificationPanel