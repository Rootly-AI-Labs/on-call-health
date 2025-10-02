import React, { useState, useRef, useEffect } from 'react'
import { Bell, Loader2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useNotifications } from '@/hooks/useNotifications'
import NotificationItem from './NotificationItem'

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)
  const {
    notifications,
    unreadCount,
    isLoading,
    hasMore,
    loadMoreNotifications,
    markAsRead,
    dismiss,
    markAllAsRead,
    handleAction
  } = useNotifications()
  const scrollRef = useRef<HTMLDivElement>(null)

  // Handle notification action and close panel
  const onAction = async (notification: any) => {
    await handleAction(notification)
    setIsOpen(false)
  }

  // Handle scroll for infinite loading
  const handleScroll = () => {
    if (!scrollRef.current || isLoading || !hasMore) return

    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current

    // Load more when scrolled to within 100px of bottom
    if (scrollTop + clientHeight >= scrollHeight - 100) {
      loadMoreNotifications()
    }
  }

  useEffect(() => {
    const scrollElement = scrollRef.current
    if (!scrollElement) return

    scrollElement.addEventListener('scroll', handleScroll)
    return () => scrollElement.removeEventListener('scroll', handleScroll)
  }, [isLoading, hasMore])

  if (!isOpen) {
    return (
      <Button
        variant="ghost"
        size="sm"
        className="relative p-2 h-9 w-9"
        onClick={() => setIsOpen(true)}
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
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/20 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl animate-in fade-in slide-in-from-top-4 duration-300">
        <div className="rounded-xl border border-border bg-card shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                <Bell className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-foreground">Notifications</h2>
                <p className="text-sm text-muted-foreground">
                  {unreadCount} {unreadCount === 1 ? "unread notification" : "unread notifications"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={markAllAsRead}
                  className="text-sm font-medium text-muted-foreground hover:text-foreground"
                >
                  Mark all read
                </Button>
              )}
              <Button variant="ghost" size="icon" onClick={() => setIsOpen(false)} className="h-8 w-8 rounded-full">
                <X className="h-4 w-4" />
                <span className="sr-only">Close</span>
              </Button>
            </div>
          </div>

          {/* Notifications List */}
          <div ref={scrollRef} className="max-h-[600px] overflow-y-auto">
            <div className="divide-y divide-border">
              {isLoading && notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                    <Bell className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <p className="text-sm font-medium text-foreground">Loading notifications...</p>
                </div>
              ) : notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                    <Bell className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <p className="text-sm font-medium text-foreground">No notifications</p>
                  <p className="text-sm text-muted-foreground">You're all caught up!</p>
                </div>
              ) : (
                <>
                  {notifications.map((notification) => (
                    <NotificationItem
                      key={notification.id}
                      notification={notification}
                      onRead={markAsRead}
                      onDismiss={dismiss}
                      onAction={onAction}
                    />
                  ))}
                  {/* Loading indicator for infinite scroll */}
                  {isLoading && (
                    <div className="flex justify-center items-center py-4">
                      <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                      <span className="ml-2 text-sm text-gray-500">Loading more...</span>
                    </div>
                  )}
                  {/* End of list indicator */}
                  {!hasMore && notifications.length > 0 && (
                    <div className="border-t border-border px-6 py-3 text-center">
                      <p className="text-xs text-muted-foreground">No more notifications</p>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default NotificationBell