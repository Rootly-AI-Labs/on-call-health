"use client"

import { Info } from "lucide-react"
import { Tooltip } from "./tooltip"
import { cn } from "@/lib/utils"

interface InfoTooltipProps {
  content: string
  side?: "top" | "bottom" | "left" | "right"
  iconClassName?: string
}

export function InfoTooltip({
  content,
  side = "top",
  iconClassName = ""
}: InfoTooltipProps): React.ReactElement {
  return (
    <Tooltip content={content} side={side}>
      <Info
        className={cn(
          "w-3.5 h-3.5 text-neutral-400 cursor-help hover:text-neutral-600 transition-colors",
          iconClassName
        )}
      />
    </Tooltip>
  )
}
