'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { usePathname } from 'next/navigation'

import { useToast } from '@/hooks/use-toast'
import type { Notification, NotificationResponse } from '@/types/notifications'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const LIMIT = 20
const POLLING_INTERVAL_MS = 300000 // 5 minutes

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const { toast } = useToast()
  const pathname = usePathname()
  const previousPathnameRef = useRef<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const offsetRef = useRef(0)

  const fetchNotifications = useCallback(async (loadMore = false) => {
    // Cancel any in-flight request
    abortControllerRef.current?.abort()
    abortControllerRef.current = new AbortController()

    try {
      setIsLoading(true)
      const currentOffset = loadMore ? offsetRef.current : 0
      const response = await fetch(`${API_BASE}/api/notifications/?limit=${LIMIT}&offset=${currentOffset}`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        signal: abortControllerRef.current.signal
      })

      if (response.ok) {
        const data: NotificationResponse = await response.json()
        if (loadMore) {
          setNotifications(prev => [...prev, ...data.notifications])
        } else {
          setNotifications(data.notifications)
          offsetRef.current = 0
        }
        setUnreadCount(data.unread_count)
        setHasMore(data.has_more || false)
        offsetRef.current = currentOffset + data.notifications.length
      }
      // Silently fail on non-ok responses - notifications are not critical
    } catch (error) {
      // Ignore abort errors, silently fail on others - notifications are not critical
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  async function loadMoreNotifications(): Promise<void> {
    if (!isLoading && hasMore) {
      await fetchNotifications(true)
    }
  }

  async function markAsRead(notificationId: number): Promise<void> {
    try {
      const response = await fetch(`${API_BASE}/api/notifications/${notificationId}/read`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      })

      if (response.ok) {
        await fetchNotifications()
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

  async function dismiss(notificationId: number): Promise<void> {
    try {
      const response = await fetch(`${API_BASE}/api/notifications/${notificationId}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      })

      if (response.ok) {
        await fetchNotifications()
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

  async function markAllAsRead(): Promise<void> {
    try {
      const response = await fetch(`${API_BASE}/api/notifications/mark-all-read`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      })

      if (response.ok) {
        await fetchNotifications()
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

  async function clearAll(): Promise<void> {
    try {
      const response = await fetch(`${API_BASE}/api/notifications/clear-all`, {
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      })

      if (response.ok) {
        await fetchNotifications()
        toast({
          title: "All notifications cleared",
          description: "All notifications have been dismissed."
        })
      }
    } catch (error) {
      console.error('Error clearing all notifications:', error)
      toast({
        title: "Error",
        description: "Failed to clear all notifications.",
        variant: "destructive"
      })
    }
  }

  async function handleAction(notification: Notification): Promise<void> {
    if (!notification.action_url) return

    // Check if it's an invitation action - navigate to integrations page with org modal open
    const invitationMatch = notification.action_url.match(/\/invitations\/accept\/(\d+)/)
    if (invitationMatch) {
      // Navigate to integrations page which will show org management modal with invitations
      window.location.href = '/integrations?openOrgModal=true'
      // Mark as read when navigating
      await markAsRead(notification.id)
      return
    }

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

  // Fetch on mount, when tab becomes visible, and poll as fallback
  // fetchNotifications is stable (empty deps) so we use empty array for mount-only effect
  useEffect(() => {
    fetchNotifications()

    const interval = setInterval(fetchNotifications, POLLING_INTERVAL_MS)

    function handleVisibilityChange(): void {
      if (document.visibilityState === 'visible') {
        fetchNotifications()
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      clearInterval(interval)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      abortControllerRef.current?.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Fetch when navigating between pages (skip initial render)
  useEffect(() => {
    if (previousPathnameRef.current === null) {
      // First render - just record the pathname, don't fetch (already done by mount effect)
      previousPathnameRef.current = pathname
      return
    }

    if (pathname !== previousPathnameRef.current) {
      previousPathnameRef.current = pathname
      fetchNotifications()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname])

  return {
    notifications,
    unreadCount,
    isLoading,
    hasMore,
    fetchNotifications,
    loadMoreNotifications,
    markAsRead,
    dismiss,
    markAllAsRead,
    clearAll,
    handleAction
  }
}