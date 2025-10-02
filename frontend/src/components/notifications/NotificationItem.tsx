import React from 'react'
import { X, Check, ExternalLink, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { Notification, NotificationActions } from '@/types/notifications'
import NotificationIcon from './NotificationIcon'

interface NotificationItemProps extends NotificationActions {
  notification: Notification
}

export function NotificationItem({
  notification,
  onRead,
  onDismiss,
  onAction
}: NotificationItemProps) {
  const isUnread = notification.is_unread
  const isExpired = notification.is_expired

  return (
    <div
      className={cn(
        "group relative px-6 py-4 transition-colors hover:bg-accent/50",
        isUnread && "bg-accent/30",
        isExpired && "opacity-60"
      )}
    >
      <div className="flex gap-4">
        {/* Icon */}
        <div className="flex-shrink-0">
          <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-gray-200">
            <NotificationIcon type={notification.type} />
          </div>
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-start justify-between gap-4">
            <h3 className="text-lg font-bold text-foreground">{notification.title}</h3>
            {isUnread && <div className="h-2.5 w-2.5 flex-shrink-0 rounded-full bg-black" />}
          </div>
          <p className="text-base leading-relaxed text-gray-600">{notification.message}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {notification.organization_name && (
              <>
                <span>{notification.organization_name}</span>
                <span>•</span>
              </>
            )}
            <span>
              {new Date(notification.created_at).toLocaleDateString()} at{' '}
              {new Date(notification.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
              })}
            </span>
          </div>

          {/* Actions */}
          {!isExpired && (
            <div className="flex items-center gap-3 pt-1">
              {notification.action_url && notification.action_text && (
                <Button
                  variant="default"
                  size="sm"
                  className="h-10 px-5 text-sm font-semibold bg-black hover:bg-gray-800 text-white rounded-lg"
                  onClick={() => onAction(notification)}
                >
                  {notification.action_text}
                  {notification.action_url.startsWith('http') && (
                    <ExternalLink className="h-4 w-4 ml-1.5" />
                  )}
                </Button>
              )}
              {isUnread && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onRead(notification.id)}
                  className="h-10 gap-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-transparent"
                >
                  <Check className="h-4 w-4" />
                  Mark Read
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDismiss(notification.id)}
                className="h-10 gap-2 text-sm font-medium text-gray-500 hover:text-gray-700 hover:bg-transparent"
              >
                <Trash2 className="h-4 w-4" />
                Dismiss
              </Button>
            </div>
          )}

          {/* Expired notice */}
          {isExpired && (
            <p className="text-xs text-muted-foreground italic">
              This notification has expired
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default NotificationItem