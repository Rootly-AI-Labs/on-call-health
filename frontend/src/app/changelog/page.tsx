"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ArrowLeft, GitCommit, Calendar, User, Tag, ExternalLink } from "lucide-react"
import { useRouter } from "next/navigation"
import { format, parseISO } from "date-fns"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Commit {
  sha: string
  message: string
  author: {
    name: string
    email: string
    date: string
  }
  url: string
  stats?: {
    additions: number
    deletions: number
  }
}

interface ChangelogEntry {
  date: string
  version?: string
  commits: Commit[]
}

export default function Changelog() {
  const router = useRouter()
  const [changelog, setChangelog] = useState<ChangelogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchChangelog()
  }, [])

  const fetchChangelog = async () => {
    try {
      setLoading(true)
      const authToken = localStorage.getItem('auth_token')
      
      if (!authToken) {
        router.push('/auth/login')
        return
      }

      const response = await fetch(`${API_BASE}/api/changelog`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (!response.ok) {
        throw new Error('Failed to fetch changelog')
      }

      const data = await response.json()
      setChangelog(data.entries || [])
    } catch (err) {
      console.error('Error fetching changelog:', err)
      setError('Failed to load changelog')
    } finally {
      setLoading(false)
    }
  }

  const getCommitTypeColor = (message: string): string => {
    const lowerMessage = message.toLowerCase()
    if (lowerMessage.includes('fix')) return 'bg-red-100 text-red-800'
    if (lowerMessage.includes('feat') || lowerMessage.includes('feature')) return 'bg-green-100 text-green-800'
    if (lowerMessage.includes('refactor')) return 'bg-blue-100 text-blue-800'
    if (lowerMessage.includes('docs')) return 'bg-gray-100 text-gray-800'
    if (lowerMessage.includes('style')) return 'bg-purple-100 text-purple-800'
    if (lowerMessage.includes('test')) return 'bg-yellow-100 text-yellow-800'
    return 'bg-gray-100 text-gray-800'
  }

  const getCommitType = (message: string): string => {
    const lowerMessage = message.toLowerCase()
    if (lowerMessage.includes('fix')) return 'Fix'
    if (lowerMessage.includes('feat') || lowerMessage.includes('feature')) return 'Feature'
    if (lowerMessage.includes('refactor')) return 'Refactor'
    if (lowerMessage.includes('docs')) return 'Docs'
    if (lowerMessage.includes('style')) return 'Style'
    if (lowerMessage.includes('test')) return 'Test'
    return 'Update'
  }

  const formatCommitMessage = (message: string): string => {
    // Remove conventional commit prefixes
    return message
      .replace(/^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?:\s*/i, '')
      .split('\n')[0] // Get first line only
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <Button
            variant="ghost"
            onClick={() => router.push('/dashboard')}
            className="mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
          
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Changelog</h1>
          <p className="text-gray-600">Track updates and improvements to the Burnout Detector</p>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-gray-600">Loading changelog...</p>
            </div>
          </div>
        ) : error ? (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <p className="text-red-800">{error}</p>
            </CardContent>
          </Card>
        ) : changelog.length === 0 ? (
          <Card>
            <CardContent className="pt-6">
              <p className="text-gray-600 text-center">No changelog entries available yet.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-8">
            {changelog.map((entry, entryIndex) => (
              <div key={entryIndex}>
                {/* Date Header */}
                <div className="flex items-center gap-4 mb-4">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-gray-500" />
                    <h2 className="text-lg font-semibold text-gray-900">
                      {format(parseISO(entry.date), 'MMMM d, yyyy')}
                    </h2>
                  </div>
                  {entry.version && (
                    <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                      <Tag className="w-3 h-3 mr-1" />
                      {entry.version}
                    </Badge>
                  )}
                </div>

                {/* Commits */}
                <div className="space-y-3">
                  {entry.commits.map((commit) => (
                    <Card key={commit.sha} className="hover:shadow-md transition-shadow">
                      <CardContent className="pt-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-start gap-3">
                              <GitCommit className="w-4 h-4 text-gray-400 mt-1 flex-shrink-0" />
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <Badge 
                                    variant="secondary" 
                                    className={`text-xs ${getCommitTypeColor(commit.message)}`}
                                  >
                                    {getCommitType(commit.message)}
                                  </Badge>
                                </div>
                                <p className="text-gray-900 font-medium">
                                  {formatCommitMessage(commit.message)}
                                </p>
                                <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                                  <div className="flex items-center gap-1">
                                    <User className="w-3 h-3" />
                                    <span>{commit.author.name}</span>
                                  </div>
                                  {commit.stats && (
                                    <div className="flex items-center gap-2">
                                      <span className="text-green-600">+{commit.stats.additions}</span>
                                      <span className="text-red-600">-{commit.stats.deletions}</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                          <a
                            href={commit.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {entryIndex < changelog.length - 1 && (
                  <Separator className="my-8" />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}