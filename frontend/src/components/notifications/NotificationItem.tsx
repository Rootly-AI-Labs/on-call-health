import React from 'react'
import { X, Check, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import type { Notification, NotificationActions } from '@/types/notifications'
import NotificationIcon from './NotificationIcon'
import PriorityBadge from './PriorityBadge'

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

export default NotificationItem