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
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <NotificationIcon type={notification.type} />
          </div>
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-start justify-between gap-4">
            <h3 className="text-sm font-semibold text-foreground">{notification.title}</h3>
            {isUnread && <div className="h-2 w-2 flex-shrink-0 rounded-full bg-primary" />}
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">{notification.message}</p>
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
            <div className="flex items-center gap-2 pt-2">
              {notification.action_url && notification.action_text && (
                <Button
                  variant="default"
                  size="sm"
                  className="h-8 text-xs font-medium"
                  onClick={() => onAction(notification)}
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
                  className="h-8 gap-1.5 text-xs font-medium"
                >
                  <Check className="h-3.5 w-3.5" />
                  Mark Read
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDismiss(notification.id)}
                className="h-8 gap-1.5 text-xs font-medium text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5" />
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