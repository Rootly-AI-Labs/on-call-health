/**
 * Platform Selector Component
 * Unified interface for all integration platforms
 */

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { 
  Building, 
  Github, 
  MessageSquare, 
  AlertTriangle,
  CheckCircle,
  Clock
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
  connectedCount: number
  isComingSoon?: boolean
}

interface PlatformSelectorProps {
  activeTab: Platform | null
  onTabChange: (platform: Platform) => void
  integrationCounts: Record<Platform, number>
  loading?: boolean
}

export function PlatformSelector({
  activeTab,
  onTabChange,
  integrationCounts,
  loading = false,
}: PlatformSelectorProps) {
  const platforms: PlatformConfig[] = [
    {
      id: "rootly",
      name: "Rootly",
      description: "Incident management and response",
      icon: <Building className="w-8 h-8 text-purple-600" />,
      color: "bg-purple-50",
      hoverColor: "hover:bg-purple-100",
      borderColor: "border-purple-200",
      connectedCount: integrationCounts.rootly || 0,
    },
    {
      id: "pagerduty",
      name: "PagerDuty",
      description: "Incident response and monitoring",
      icon: (
        <div className="w-8 h-8 bg-green-600 rounded flex items-center justify-center">
          <AlertTriangle className="w-5 h-5 text-white" />
        </div>
      ),
      color: "bg-green-50",
      hoverColor: "hover:bg-green-100",
      borderColor: "border-green-200",
      connectedCount: integrationCounts.pagerduty || 0,
    },
    {
      id: "github",
      name: "GitHub",
      description: "Code activity and development patterns",
      icon: (
        <div className="w-8 h-8 bg-gray-900 rounded flex items-center justify-center">
          <Github className="w-5 h-5 text-white" />
        </div>
      ),
      color: "bg-gray-50",
      hoverColor: "hover:bg-gray-100",
      borderColor: "border-gray-200",
      connectedCount: integrationCounts.github || 0,
    },
    {
      id: "slack",
      name: "Slack",
      description: "Communication patterns and sentiment",
      icon: (
        <div className="w-8 h-8 bg-purple-600 rounded flex items-center justify-center">
          <MessageSquare className="w-5 h-5 text-white" />
        </div>
      ),
      color: "bg-purple-50",
      hoverColor: "hover:bg-purple-100",
      borderColor: "border-purple-200",
      connectedCount: integrationCounts.slack || 0,
    },
  ]

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="border-2 border-gray-200 p-6 h-32 animate-pulse">
            <div className="flex items-center justify-center h-full">
              <div className="h-8 w-32 bg-gray-300 rounded"></div>
            </div>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="mb-8">
      <div className="text-center mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Choose a Platform
        </h2>
        <p className="text-gray-600">
          Select a platform to view and manage your integrations
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {platforms.map((platform) => (
          <Card
            key={platform.id}
            className={`
              border-2 cursor-pointer transition-all duration-200 relative
              ${activeTab === platform.id
                ? `${platform.borderColor} ${platform.color} shadow-md`
                : `border-gray-200 ${platform.hoverColor} hover:shadow-sm`
              }
            `}
            onClick={() => onTabChange(platform.id)}
          >
            <CardContent className="p-6">
              <div className="flex flex-col items-center text-center space-y-3">
                {/* Icon */}
                <div className="relative">
                  {platform.icon}
                  
                  {/* Connection Status Badge */}
                  {platform.connectedCount > 0 && (
                    <div className="absolute -top-2 -right-2">
                      <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center">
                        <CheckCircle className="w-3 h-3 text-white" />
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Platform Name */}
                <div>
                  <h3 className="font-semibold text-lg text-gray-900">
                    {platform.name}
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    {platform.description}
                  </p>
                </div>
                
                {/* Connection Count */}
                <div className="flex items-center space-x-2">
                  {platform.connectedCount > 0 ? (
                    <Badge variant="secondary" className="bg-green-100 text-green-700">
                      {platform.connectedCount} connected
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-gray-500">
                      Not connected
                    </Badge>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      
      {/* Platform Description */}
      {activeTab && (
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center space-x-3">
            {platforms.find(p => p.id === activeTab)?.icon}
            <div>
              <h4 className="font-medium text-gray-900">
                {platforms.find(p => p.id === activeTab)?.name} Integration
              </h4>
              <p className="text-sm text-gray-600">
                {activeTab === "rootly" && "Connect your Rootly account to analyze incident response patterns and team workload."}
                {activeTab === "pagerduty" && "Connect your PagerDuty account to analyze on-call schedules and incident response patterns."}
                {activeTab === "github" && "Connect your GitHub account to analyze code activity patterns and development stress indicators."}
                {activeTab === "slack" && "Connect your Slack workspace to analyze communication patterns and sentiment indicators."}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}