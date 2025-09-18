import React from 'react'
import { Badge } from '@/components/ui/badge'

interface PriorityBadgeProps {
  priority: 'high' | 'normal' | 'low'
}

export function PriorityBadge({ priority }: PriorityBadgeProps) {
  if (priority === 'high') {
    return (
      <Badge variant="destructive" className="h-4 text-xs ml-2">
        Urgent
      </Badge>
    )
  }

  return null
}

export default PriorityBadge