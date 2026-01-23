"use client"

import { useState, useRef, useEffect } from "react"
import { cn } from "@/lib/utils"

interface TooltipProps {
  children: React.ReactNode
  content: string
  className?: string
  side?: "top" | "bottom" | "left" | "right"
}

export function Tooltip({
  children,
  content,
  className = "",
  side = "top"
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [alignment, setAlignment] = useState<"left" | "center" | "right">("center")
  const containerRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isVisible && containerRef.current && tooltipRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect()
      const tooltipWidth = tooltipRef.current.offsetWidth

      // Check available space on both sides
      const spaceOnRight = window.innerWidth - containerRect.right
      const spaceOnLeft = containerRect.left

      // If close to right edge, align right
      if (spaceOnRight < tooltipWidth / 2 + 20) {
        setAlignment("right")
      }
      // If close to left edge, align left
      else if (spaceOnLeft < tooltipWidth / 2 + 20) {
        setAlignment("left")
      }
      // Otherwise center
      else {
        setAlignment("center")
      }
    }
  }, [isVisible])

  const sideClasses = {
    top: alignment === "left" ? "bottom-full left-0 mb-2" : alignment === "right" ? "bottom-full right-0 mb-2" : "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: alignment === "left" ? "top-full left-0 mt-2" : alignment === "right" ? "top-full right-0 mt-2" : "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2"
  }

  const arrowClasses = {
    top: alignment === "left" ? "top-full left-3 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-900" : alignment === "right" ? "top-full right-3 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-900" : "top-full left-1/2 -translate-x-1/2 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-900",
    bottom: alignment === "left" ? "bottom-full left-3 border-l-4 border-r-4 border-b-4 border-l-transparent border-r-transparent border-b-gray-900" : alignment === "right" ? "bottom-full right-3 border-l-4 border-r-4 border-b-4 border-l-transparent border-r-transparent border-b-gray-900" : "bottom-full left-1/2 -translate-x-1/2 border-l-4 border-r-4 border-b-4 border-l-transparent border-r-transparent border-b-gray-900",
    left: "left-full top-1/2 -translate-y-1/2 border-t-4 border-b-4 border-l-4 border-t-transparent border-b-transparent border-l-gray-900",
    right: "right-full top-1/2 -translate-y-1/2 border-t-4 border-b-4 border-r-4 border-t-transparent border-b-transparent border-r-gray-900"
  }

  return (
    <div
      ref={containerRef}
      className="relative inline-block"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <div
          ref={tooltipRef}
          className={cn(
            "absolute z-50 px-3 py-2 text-sm text-white bg-neutral-900 rounded-lg shadow-lg w-48 break-words",
            sideClasses[side],
            className
          )}
        >
          {content}
          <div className={cn("absolute w-0 h-0", arrowClasses[side])} />
        </div>
      )}
    </div>
  )
}