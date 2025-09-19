'use client'

import { useState, useEffect } from 'react'
import { useToast } from '@/hooks/use-toast'
import type { Notification, NotificationResponse } from '@/types/notifications'

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const { toast } = useToast()

  // Fetch notifications from API
  const fetchNotifications = async () => {
    try {
      setIsLoading(true)
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/notifications/`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
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

  // Mark notification as read
  const markAsRead = async (notificationId: number) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/notifications/${notificationId}/read`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
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
  const dismiss = async (notificationId: number) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/notifications/${notificationId}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
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

  // Mark all as read
  const markAllAsRead = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/notifications/mark-all-read`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
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

  // Handle notification action (Accept invitation, View results, etc.)
  const handleAction = async (notification: Notification) => {
    if (!notification.action_url) return

    // If external URL, open in new tab
    if (notification.action_url.startsWith('http')) {
      window.open(notification.action_url, '_blank')
    } else {
      // Internal URL, navigate
      window.location.href = notification.action_url
    }

    // Mark as read when action is taken
    await markAsRead(notification.id)
  }

  // Auto-refresh notifications every 30 seconds
  useEffect(() => {
    fetchNotifications()

    const interval = setInterval(fetchNotifications, 30000)
    return () => clearInterval(interval)
  }, [])

  return {
    notifications,
    unreadCount,
    isLoading,
    fetchNotifications,
    markAsRead,
    dismiss,
    markAllAsRead,
    handleAction
  }
}