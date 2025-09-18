import React from 'react'

interface NotificationIconProps {
  type: string
  className?: string
}

export function NotificationIcon({ type, className = "text-lg" }: NotificationIconProps) {
  const icons = {
    invitation: '🏢',
    survey: '📊',
    integration: '🔗',
    analysis: '📈',
    reminder: '⏰',
    welcome: '🎉'
  }

  return (
    <span className={className}>
      {icons[type as keyof typeof icons] || '📌'}
    </span>
  )
}

export default NotificationIcon