/**
 * Enhanced Platform Selector Component
 * Progressive unlock system with core/enhancement platform separation
 */

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { 
  Building, 
  Github, 
  MessageSquare, 
  AlertTriangle,
  CheckCircle,
  Lock,
  Unlock,
  TrendingUp,
  Zap,
  Star,
  ArrowRight,
  Info
} from "lucide-react"
import Image from "next/image"

type Platform = "rootly" | "pagerduty" | "github" | "slack"

interface PlatformConfig {
  id: Platform
  name: string
  description: string
  icon: React.ReactNode
  color: string
  hoverColor: string
  borderColor: string
  connectedColor: string
  category: "core" | "enhancement"
  benefits: string[]
  requirements?: string[]
  enhancementValue?: string
}

interface IntegrationCounts {
  rootly: number
  pagerduty: number
  github: number
  slack: number
}

interface EnhancedPlatformSelectorProps {
  activeTab: Platform | null
  onTabChange: (platform: Platform) => void
  integrationCounts: IntegrationCounts
  loading?: boolean
}

export function EnhancedPlatformSelector({
  activeTab,
  onTabChange,
  integrationCounts,
  loading = false,
}: EnhancedPlatformSelectorProps) {
  const [showUnlockAnimation, setShowUnlockAnimation] = useState(false)
  const [previousCoreCount, setPreviousCoreCount] = useState(0)

  // Calculate connection states
  const coreConnected = (integrationCounts.rootly + integrationCounts.pagerduty) > 0
  const totalCoreConnected = integrationCounts.rootly + integrationCounts.pagerduty
  const enhancementConnected = (integrationCounts.github + integrationCounts.slack) > 0
  const totalEnhancementConnected = integrationCounts.github + integrationCounts.slack

  // Platform configurations
  const platforms: PlatformConfig[] = [
    {
      id: "rootly",
      name: "Rootly",
      description: "Incident management and response",
      icon: (
        <Image
          src="/images/rootly-logo-final.svg"
          alt="Rootly"
          width={48}
          height={48}
          className="h-8 w-auto object-contain"
        />
      ),
      color: "bg-purple-50",
      hoverColor: "hover:bg-purple-100",
      borderColor: "border-purple-200",
      connectedColor: "border-purple-500 bg-purple-50",
      category: "core",
      benefits: [
        "Incident response patterns",
        "Team workload distribution",
        "On-call burnout analysis"
      ],
    },
    {
      id: "pagerduty",
      name: "PagerDuty",
      description: "Incident response and monitoring",
      icon: (
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-green-600 rounded flex items-center justify-center">
            <span className="text-white font-bold text-sm">PD</span>
          </div>
        </div>
      ),
      color: "bg-green-50",
      hoverColor: "hover:bg-green-100",
      borderColor: "border-green-200",
      connectedColor: "border-green-500 bg-green-50",
      category: "core",
      benefits: [
        "Alert fatigue detection",
        "Escalation pattern analysis",
        "Service reliability impact"
      ],
    },
    {
      id: "github",
      name: "GitHub",
      description: "Code activity and development patterns",
      icon: (
        <Image
          src="/images/github-logo.png"
          alt="GitHub"
          width={32}
          height={32}
          className="h-8 w-8 object-contain"
        />
      ),
      color: "bg-gray-50",
      hoverColor: "hover:bg-gray-100",
      borderColor: "border-gray-200",
      connectedColor: "border-gray-500 bg-gray-50",
      category: "enhancement",
      benefits: [
        "After-hours coding patterns",
        "Commit stress indicators",
        "Development velocity impact"
      ],
      requirements: ["Connect Rootly or PagerDuty first"],
      enhancementValue: "+40% more insights",
    },
    {
      id: "slack",
      name: "Slack",
      description: "Communication patterns and sentiment",
      icon: (
        <Image
          src="/images/slack-logo.png"
          alt="Slack"
          width={32}
          height={32}
          className="h-8 w-8 object-contain"
        />
      ),
      color: "bg-purple-50",
      hoverColor: "hover:bg-purple-100",
      borderColor: "border-purple-200",
      connectedColor: "border-purple-500 bg-purple-50",
      category: "enhancement",
      benefits: [
        "Communication burnout signals",
        "Sentiment analysis",
        "Team collaboration health"
      ],
      requirements: ["Connect Rootly or PagerDuty first"],
      enhancementValue: "+25% more insights",
    },
  ]

  // Animation for unlocking enhancement platforms
  useEffect(() => {
    const currentCoreCount = totalCoreConnected
    if (currentCoreCount > previousCoreCount && currentCoreCount === 1) {
      setShowUnlockAnimation(true)
      setTimeout(() => setShowUnlockAnimation(false), 3000)
    }
    setPreviousCoreCount(currentCoreCount)
  }, [totalCoreConnected, previousCoreCount])

  const corePlatforms = platforms.filter(p => p.category === "core")
  const enhancementPlatforms = platforms.filter(p => p.category === "enhancement")

  const getRecommendations = (): string[] => {
    if (integrationCounts.rootly > 0 && integrationCounts.pagerduty > 0) {
      return ["Connect GitHub and Slack for complete 360° analysis"]
    }
    if (integrationCounts.rootly > 0) {
      return ["Add GitHub for code stress patterns", "Add Slack for communication insights"]
    }
    if (integrationCounts.pagerduty > 0) {
      return ["Add GitHub for development impact analysis"]
    }
    return ["Connect Rootly or PagerDuty to get started"]
  }

  if (loading) {
    return <div className="animate-pulse">Loading platforms...</div>
  }

  return (
    <div className="space-y-8">
      {/* Analysis Capabilities Overview */}
      <div className="text-center space-y-4">
        <h2 className="text-2xl font-bold text-gray-900">
          Connect Your Platforms
        </h2>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Start with your incident management platform, then enhance your analysis with additional data sources
        </p>
        
        {/* Progress Indicator */}
        <div className="flex items-center justify-center space-x-4 mt-6">
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${coreConnected ? 'bg-green-500' : 'bg-gray-300'}`} />
            <span className={`text-sm ${coreConnected ? 'text-green-700' : 'text-gray-500'}`}>
              Core Platform {coreConnected ? '✓' : ''}
            </span>
          </div>
          <ArrowRight className="w-4 h-4 text-gray-400" />
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${enhancementConnected ? 'bg-purple-500' : 'bg-gray-300'}`} />
            <span className={`text-sm ${enhancementConnected ? 'text-purple-700' : 'text-gray-500'}`}>
              Enhanced Analysis {enhancementConnected ? '✓' : ''}
            </span>
          </div>
        </div>
      </div>

      {/* Core Platforms Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <Zap className="w-5 h-5 mr-2 text-blue-600" />
            Core Platforms
            <Badge variant="outline" className="ml-2 text-xs">
              Required
            </Badge>
          </h3>
          <div className="text-sm text-gray-600">
            {totalCoreConnected}/2 connected
          </div>
        </div>
        
        <div className="grid md:grid-cols-2 gap-4">
          {corePlatforms.map((platform) => (
            <PlatformCard
              key={platform.id}
              platform={platform}
              isConnected={integrationCounts[platform.id] > 0}
              connectionCount={integrationCounts[platform.id]}
              isActive={activeTab === platform.id}
              onClick={() => onTabChange(platform.id)}
              isLocked={false}
            />
          ))}
        </div>
      </div>

      {/* Enhancement Platforms Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <TrendingUp className="w-5 h-5 mr-2 text-purple-600" />
            Enhancement Platforms
            <Badge variant="outline" className="ml-2 text-xs">
              Optional
            </Badge>
            {showUnlockAnimation && (
              <Badge className="ml-2 bg-green-100 text-green-700 animate-pulse">
                <Unlock className="w-3 h-3 mr-1" />
                Unlocked!
              </Badge>
            )}
          </h3>
          <div className="text-sm text-gray-600">
            {totalEnhancementConnected}/2 connected
          </div>
        </div>
        
        {!coreConnected && (
          <Alert>
            <Lock className="h-4 w-4" />
            <AlertDescription>
              Connect Rootly or PagerDuty first to unlock enhanced analysis features
            </AlertDescription>
          </Alert>
        )}
        
        <div className="grid md:grid-cols-2 gap-4">
          {enhancementPlatforms.map((platform) => (
            <PlatformCard
              key={platform.id}
              platform={platform}
              isConnected={integrationCounts[platform.id] > 0}
              connectionCount={integrationCounts[platform.id]}
              isActive={activeTab === platform.id}
              onClick={() => coreConnected && onTabChange(platform.id)}
              isLocked={!coreConnected}
            />
          ))}
        </div>
      </div>

      {/* Recommendations Section */}
      <div className="bg-blue-50 rounded-lg p-6">
        <h4 className="font-semibold text-blue-900 mb-3 flex items-center">
          <Star className="w-5 h-5 mr-2" />
          Recommended Next Steps
        </h4>
        <ul className="space-y-2">
          {getRecommendations().map((recommendation, index) => (
            <li key={index} className="flex items-start text-blue-800">
              <ArrowRight className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
              {recommendation}
            </li>
          ))}
        </ul>
      </div>

      {/* Analysis Capabilities Preview */}
      <div className="bg-gray-50 rounded-lg p-6">
        <h4 className="font-semibold text-gray-900 mb-4">Analysis Capabilities</h4>
        <div className="grid md:grid-cols-3 gap-4 text-sm">
          <div className="space-y-2">
            <div className="font-medium text-gray-900">📊 Basic Analysis</div>
            <div className="text-gray-600">
              {coreConnected ? "✓ Available" : "Connect core platform"}
            </div>
            <ul className="text-gray-500 space-y-1">
              <li>• Incident response patterns</li>
              <li>• Team workload distribution</li>
              <li>• On-call burnout detection</li>
            </ul>
          </div>
          <div className="space-y-2">
            <div className="font-medium text-gray-900">🚀 Enhanced Analysis</div>
            <div className="text-gray-600">
              {integrationCounts.github > 0 ? "✓ Available" : "Connect GitHub"}
            </div>
            <ul className="text-gray-500 space-y-1">
              <li>• Code stress indicators</li>
              <li>• Development velocity impact</li>
              <li>• After-hours coding patterns</li>
            </ul>
          </div>
          <div className="space-y-2">
            <div className="font-medium text-gray-900">💬 Complete Analysis</div>
            <div className="text-gray-600">
              {integrationCounts.slack > 0 ? "✓ Available" : "Connect Slack"}
            </div>
            <ul className="text-gray-500 space-y-1">
              <li>• Communication burnout signals</li>
              <li>• Sentiment analysis</li>
              <li>• Team collaboration health</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

interface PlatformCardProps {
  platform: PlatformConfig
  isConnected: boolean
  connectionCount: number
  isActive: boolean
  onClick: () => void
  isLocked: boolean
}

function PlatformCard({
  platform,
  isConnected,
  connectionCount,
  isActive,
  onClick,
  isLocked,
}: PlatformCardProps) {
  return (
    <Card
      className={`
        relative cursor-pointer transition-all duration-200 
        ${isLocked ? 'opacity-50 cursor-not-allowed' : ''}
        ${isActive ? 
          `border-2 ${platform.connectedColor} shadow-md` : 
          `border-2 ${platform.borderColor} ${!isLocked ? platform.hoverColor : ''} hover:shadow-sm`
        }
      `}
      onClick={onClick}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="relative">
              {platform.icon}
              {isLocked && (
                <div className="absolute -top-1 -right-1">
                  <Lock className="w-4 h-4 text-gray-400" />
                </div>
              )}
            </div>
            <div>
              <CardTitle className="text-lg">{platform.name}</CardTitle>
              <p className="text-sm text-gray-600">{platform.description}</p>
            </div>
          </div>
          
          <div className="flex flex-col items-end space-y-1">
            {isConnected ? (
              <Badge variant="secondary" className="bg-green-100 text-green-700">
                <CheckCircle className="w-3 h-3 mr-1" />
                Connected
              </Badge>
            ) : (
              <Badge variant="outline" className="text-gray-500">
                {isLocked ? "Locked" : "Available"}
              </Badge>
            )}
            
            {platform.enhancementValue && (
              <Badge variant="outline" className="text-xs text-purple-600">
                {platform.enhancementValue}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="space-y-3">
          {/* Benefits */}
          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Benefits:</div>
            <ul className="space-y-1 text-sm text-gray-600">
              {platform.benefits.map((benefit, index) => (
                <li key={index} className="flex items-start">
                  <CheckCircle className="w-3 h-3 mr-2 mt-0.5 text-green-500 flex-shrink-0" />
                  {benefit}
                </li>
              ))}
            </ul>
          </div>
          
          {/* Requirements */}
          {platform.requirements && (
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2">Requirements:</div>
              <ul className="space-y-1 text-sm text-gray-500">
                {platform.requirements.map((requirement, index) => (
                  <li key={index} className="flex items-start">
                    <Info className="w-3 h-3 mr-2 mt-0.5 text-blue-500 flex-shrink-0" />
                    {requirement}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}