import React, { useState, useRef, useEffect } from 'react'
import { Bell, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
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

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
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
      </SheetTrigger>

      <SheetContent side="right" className="w-[400px] sm:w-[540px] p-0">
        <SheetHeader className="border-b border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <SheetTitle className="text-lg font-semibold">Notifications</SheetTitle>
              {unreadCount > 0 && (
                <SheetDescription className="text-sm text-gray-500 mt-1">
                  {unreadCount} unread notification{unreadCount !== 1 ? 's' : ''}
                </SheetDescription>
              )}
            </div>
            {unreadCount > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={markAllAsRead}
                className="text-xs"
              >
                Mark all read
              </Button>
            )}
          </div>
        </SheetHeader>

        {/* Notifications List */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6">
          {isLoading && notifications.length === 0 ? (
            <div className="text-center text-gray-500 py-12">
              <Bell className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-sm">Loading notifications...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="text-center text-gray-500 py-12">
              <Bell className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-sm font-medium">No notifications</p>
              <p className="text-xs mt-2">You're all caught up! 🎉</p>
            </div>
          ) : (
            <>
              <div className="space-y-3">
                {notifications.map((notification) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onRead={markAsRead}
                    onDismiss={dismiss}
                    onAction={onAction}
                  />
                ))}
              </div>
              {/* Loading indicator for infinite scroll */}
              {isLoading && (
                <div className="flex justify-center items-center py-4">
                  <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                  <span className="ml-2 text-sm text-gray-500">Loading more...</span>
                </div>
              )}
              {/* End of list indicator */}
              {!hasMore && notifications.length > 0 && (
                <div className="text-center py-4 text-sm text-gray-400">
                  No more notifications
                </div>
              )}
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}

export default NotificationBell