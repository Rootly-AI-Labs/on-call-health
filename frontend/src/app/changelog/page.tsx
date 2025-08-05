"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Calendar } from "lucide-react"
import { useRouter } from "next/navigation"
import { format, parseISO } from "date-fns"

interface Change {
  date: string
  title: string
  type: 'fix' | 'feature' | 'improvement'
  description?: string
}

// Major changes in human-readable format
const majorChanges: Change[] = [
  {
    date: "2025-08-04",
    title: "Changelog now loads instantly",
    type: "fix",
    description: "No more spinning wheels - the changelog is now built into the app instead of fetching from GitHub"
  },
  {
    date: "2025-08-04",
    title: "Support for critical P0 incidents",
    type: "feature",
    description: "The most severe incidents (SEV0/P0) now show up in purple in your severity breakdown"
  },
  {
    date: "2025-08-04",
    title: "PagerDuty can now analyze thousands more incidents",
    type: "improvement",
    description: "Removed the 1,000 incident cap - now handles up to 15,000 incidents for longer time periods"
  },
  {
    date: "2025-08-04",
    title: "At-risk member counts are accurate again",
    type: "fix",
    description: "The health trends chart was showing '0 members at risk' even when people had high burnout scores - now fixed"
  },
  {
    date: "2025-08-04",
    title: "More realistic health score ratings",
    type: "improvement",
    description: "86% is now correctly shown as 'Good' not 'Excellent' - only 90%+ gets the top rating"
  },
  {
    date: "2025-08-04",
    title: "OAuth works with custom domains",
    type: "fix",
    description: "Fixed the 404 error when signing in from oncallburnout.com or other custom domains"
  },
  {
    date: "2025-08-04",
    title: "PagerDuty shows incident severity breakdown",
    type: "feature",
    description: "Just like Rootly, PagerDuty analyses now show how many P1s, P2s, etc. your team handled"
  },
  {
    date: "2025-08-04",
    title: "Fixed calculation errors in burnout scores",
    type: "fix",
    description: "No more 'cannot convert NoneType' errors when running analyses with missing data"
  },
  {
    date: "2025-08-03",
    title: "Clearer GitHub integration status",
    type: "improvement",
    description: "Only shows 'No GitHub data' when GitHub was actually enabled for the analysis"
  },
  {
    date: "2025-08-03",
    title: "Removed confusing GitHub warnings",
    type: "improvement",
    description: "The yellow warning about GitHub validation was more scary than helpful - now it's gone"
  },
  {
    date: "2025-08-02",
    title: "Risk levels now include 'Critical'",
    type: "feature",
    description: "Added a fourth risk level for team members with severe burnout indicators (score 7.0+)"
  },
  {
    date: "2025-08-02",
    title: "Fixed member risk calculations",
    type: "fix",
    description: "Dashboard was looking for 'critical' risk but only had 'low/medium/high' - now properly counts all risk levels"
  },
  {
    date: "2025-08-01",
    title: "Faster incident data collection",
    type: "improvement",
    description: "Optimized API calls to Rootly and PagerDuty - analyses complete much faster now"
  },
  {
    date: "2025-08-01",
    title: "Better error messages for API issues",
    type: "improvement",
    description: "When Rootly API permissions are missing, you now get a clear message instead of a cryptic 404"
  },
  {
    date: "2025-07-31",
    title: "Dashboard syntax errors fixed",
    type: "fix",
    description: "Fixed various JSX closing tag issues that were causing the dashboard to crash"
  },
  {
    date: "2025-07-30",
    title: "GitHub-only burnout analysis",
    type: "feature",
    description: "Can now detect burnout in developers who don't handle incidents but show stress in their code patterns"
  },
  {
    date: "2025-07-29",
    title: "Burnout factors chart accuracy",
    type: "fix",
    description: "The radar chart was showing calculated values instead of real data - now shows actual burnout factors"
  },
  {
    date: "2025-07-28",
    title: "Slack integration launched",
    type: "feature",
    description: "Analyze message patterns, response times, and after-hours communication to detect burnout"
  },
  {
    date: "2025-07-27",
    title: "Manual user mapping interface",
    type: "feature",
    description: "No more hardcoded mappings - map team members to their GitHub accounts through the UI"
  },
  {
    date: "2025-07-26",
    title: "Daily incident trends fixed",
    type: "fix",
    description: "Health trends chart now shows actual daily incident patterns instead of aggregated historical data"
  }
]

export default function Changelog() {
  const router = useRouter()
  const [displayedChanges, setDisplayedChanges] = useState<Change[]>([])
  const [hasMore, setHasMore] = useState(true)
  const loader = useRef(null)
  const ITEMS_PER_PAGE = 5

  // Initialize with first batch
  useEffect(() => {
    setDisplayedChanges(majorChanges.slice(0, ITEMS_PER_PAGE))
    setHasMore(majorChanges.length > ITEMS_PER_PAGE)
  }, [])

  // Load more items
  const loadMore = useCallback(() => {
    const currentLength = displayedChanges.length
    const moreChanges = majorChanges.slice(currentLength, currentLength + ITEMS_PER_PAGE)
    
    if (moreChanges.length > 0) {
      setDisplayedChanges([...displayedChanges, ...moreChanges])
    }
    
    if (currentLength + moreChanges.length >= majorChanges.length) {
      setHasMore(false)
    }
  }, [displayedChanges])

  // Infinite scroll observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore) {
          loadMore()
        }
      },
      { threshold: 0.1 }
    )

    if (loader.current) {
      observer.observe(loader.current)
    }

    return () => {
      if (loader.current) {
        observer.unobserve(loader.current)
      }
    }
  }, [loadMore, hasMore])

  const getTypeStyles = (type: Change['type']) => {
    switch (type) {
      case 'fix':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'feature':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'improvement':
        return 'text-blue-600 bg-blue-50 border-blue-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  return (
    <div className="min-h-screen bg-white">
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        {/* Header */}
        <div className="mb-12">
          <Button
            variant="ghost"
            onClick={() => router.push('/dashboard')}
            className="mb-6 -ml-2"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
          
          <h1 className="text-3xl font-bold text-gray-900">Changelog</h1>
          <p className="text-gray-600 mt-2">Recent updates and improvements</p>
        </div>

        {/* Changes list */}
        <div className="space-y-6">
          {displayedChanges.map((change, index) => {
            const isNewDate = index === 0 || change.date !== displayedChanges[index - 1].date
            
            return (
              <div key={`${change.date}-${index}`}>
                {isNewDate && (
                  <div className="flex items-center gap-2 mb-4">
                    <Calendar className="w-4 h-4 text-gray-400" />
                    <time className="text-sm font-medium text-gray-500">
                      {format(parseISO(change.date), 'MMMM d, yyyy')}
                    </time>
                  </div>
                )}
                
                <div className="pl-6 border-l-2 border-gray-100 pb-6 last:border-0">
                  <div className="bg-white rounded-lg">
                    <div className="flex items-start gap-3">
                      <span className={`inline-flex items-center justify-center w-24 px-2 py-1 rounded-md text-xs font-medium border ${getTypeStyles(change.type)}`}>
                        {change.type}
                      </span>
                      <div className="flex-1">
                        <h3 className="text-gray-900 font-medium">
                          {change.title}
                        </h3>
                        {change.description && (
                          <p className="text-gray-600 text-sm mt-1">
                            {change.description}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Infinite scroll loader */}
        {hasMore && (
          <div ref={loader} className="flex justify-center py-8">
            <div className="w-8 h-8 border-2 border-gray-300 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        
        {!hasMore && displayedChanges.length > 0 && (
          <div className="text-center py-8 text-gray-500 text-sm">
            You've reached the beginning
          </div>
        )}
      </div>
    </div>
  )
}