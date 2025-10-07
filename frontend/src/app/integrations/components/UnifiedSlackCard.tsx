"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle, Loader2 } from "lucide-react"
import { SlackSurveyTabs } from "@/components/SlackSurveyTabs"

interface UnifiedSlackCardProps {
  slackIntegration: any
  loadingSlack: boolean
  isConnectingSlackOAuth: boolean
  isDisconnectingSlackSurvey: boolean
  userInfo: any
  selectedOrganization: string
  integrations: any[]
  teamMembers: any[]
  loadingTeamMembers: boolean
  loadingSyncedUsers: boolean
  fetchTeamMembers: () => void
  syncUsersToCorrelation: () => void
  fetchSyncedUsers: () => void
  setShowManualSurveyModal: (show: boolean) => void
  loadSlackPermissions: () => void
  setSlackSurveyDisconnectDialogOpen: (open: boolean) => void
  setIsConnectingSlackOAuth: (connecting: boolean) => void
  toast: any
}

const SlackIcon = () => (
  <svg className="w-6 h-6" viewBox="0 0 124 124" fill="none">
    <path d="M26.3996 78.2003C26.3996 84.7003 21.2996 89.8003 14.7996 89.8003C8.29961 89.8003 3.19961 84.7003 3.19961 78.2003C3.19961 71.7003 8.29961 66.6003 14.7996 66.6003H26.3996V78.2003Z" fill="#E01E5A"/>
    <path d="M32.2996 78.2003C32.2996 71.7003 37.3996 66.6003 43.8996 66.6003C50.3996 66.6003 55.4996 71.7003 55.4996 78.2003V109.2C55.4996 115.7 50.3996 120.8 43.8996 120.8C37.3996 120.8 32.2996 115.7 32.2996 109.2V78.2003Z" fill="#E01E5A"/>
    <path d="M43.8996 26.4003C37.3996 26.4003 32.2996 21.3003 32.2996 14.8003C32.2996 8.30026 37.3996 3.20026 43.8996 3.20026C50.3996 3.20026 55.4996 8.30026 55.4996 14.8003V26.4003H43.8996Z" fill="#36C5F0"/>
    <path d="M43.8996 32.3003C50.3996 32.3003 55.4996 37.4003 55.4996 43.9003C55.4996 50.4003 50.3996 55.5003 43.8996 55.5003H12.8996C6.39961 55.5003 1.29961 50.4003 1.29961 43.9003C1.29961 37.4003 6.39961 32.3003 12.8996 32.3003H43.8996Z" fill="#36C5F0"/>
    <path d="M95.5996 43.9003C95.5996 37.4003 100.7 32.3003 107.2 32.3003C113.7 32.3003 118.8 37.4003 118.8 43.9003C118.8 50.4003 113.7 55.5003 107.2 55.5003H95.5996V43.9003Z" fill="#2EB67D"/>
    <path d="M89.6996 43.9003C89.6996 50.4003 84.5996 55.5003 78.0996 55.5003C71.5996 55.5003 66.4996 50.4003 66.4996 43.9003V12.9003C66.4996 6.40026 71.5996 1.30026 78.0996 1.30026C84.5996 1.30026 89.6996 6.40026 89.6996 12.9003V43.9003Z" fill="#2EB67D"/>
    <path d="M78.0996 95.6003C84.5996 95.6003 89.6996 100.7 89.6996 107.2C89.6996 113.7 84.5996 118.8 78.0996 118.8C71.5996 118.8 66.4996 113.7 66.4996 107.2V95.6003H78.0996Z" fill="#ECB22E"/>
    <path d="M78.0996 89.7003C71.5996 89.7003 66.4996 84.6003 66.4996 78.1003C66.4996 71.6003 71.5996 66.5003 78.0996 66.5003H109.1C115.6 66.5003 120.7 71.6003 120.7 78.1003C120.7 84.6003 115.6 89.7003 109.1 89.7003H78.0996Z" fill="#ECB22E"/>
  </svg>
)

export function UnifiedSlackCard({
  slackIntegration,
  loadingSlack,
  isConnectingSlackOAuth,
  isDisconnectingSlackSurvey,
  userInfo,
  selectedOrganization,
  integrations,
  teamMembers,
  loadingTeamMembers,
  loadingSyncedUsers,
  fetchTeamMembers,
  syncUsersToCorrelation,
  fetchSyncedUsers,
  setShowManualSurveyModal,
  loadSlackPermissions,
  setSlackSurveyDisconnectDialogOpen,
  setIsConnectingSlackOAuth,
  toast
}: UnifiedSlackCardProps) {
  const [enableSlackSurvey, setEnableSlackSurvey] = useState(true)
  const [enableSlackSentiment, setEnableSlackSentiment] = useState(true)

  const isConnected = !!slackIntegration
  const surveyEnabled = slackIntegration?.survey_enabled ?? false
  const sentimentEnabled = slackIntegration?.sentiment_enabled ?? false

  const handleSlackConnect = () => {
    if (!enableSlackSurvey && !enableSlackSentiment) {
      toast.error('Please select at least one feature to enable')
      return
    }

    const clientId = process.env.NEXT_PUBLIC_SLACK_CLIENT_ID
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL

    if (!backendUrl) {
      toast.error('Backend URL not configured. Please contact support.')
      return
    }

    // Build dynamic scopes based on feature selection
    const scopesArray = []
    if (enableSlackSurvey) {
      scopesArray.push('commands', 'chat:write', 'team:read')
    }
    if (enableSlackSentiment) {
      scopesArray.push('channels:history', 'channels:read', 'users:read', 'users:read.email')
    }
    const scopes = Array.from(new Set(scopesArray)).join(',')

    // Include feature flags in state parameter
    const redirectUri = `${backendUrl}/integrations/slack/oauth/callback`
    const stateData = {
      orgId: userInfo?.organization_id,
      userId: userInfo?.id,
      email: userInfo?.email,
      enableSurvey: enableSlackSurvey,
      enableSentiment: enableSlackSentiment
    }
    const state = userInfo ? btoa(JSON.stringify(stateData)) : ''

    const slackAuthUrl = `https://slack.com/oauth/v2/authorize?client_id=${clientId}&scope=${scopes}&redirect_uri=${encodeURIComponent(redirectUri)}&state=${encodeURIComponent(state)}`

    setIsConnectingSlackOAuth(true)
    localStorage.setItem('slack_oauth_in_progress', 'true')
    toast.info('Redirecting to Slack...')

    window.location.href = slackAuthUrl
  }

  if (loadingSlack) {
    return (
      <Card className="border-2 border-purple-200 bg-purple-50/30">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between animate-pulse">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gray-200 rounded-lg"></div>
              <div className="space-y-2">
                <div className="w-32 h-5 bg-gray-200 rounded"></div>
                <div className="w-64 h-4 bg-gray-200 rounded"></div>
              </div>
            </div>
            <div className="w-24 h-9 bg-gray-200 rounded-lg"></div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-40 bg-gray-100 rounded animate-pulse"></div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-2 border-purple-200 bg-purple-50/30">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <SlackIcon />
            </div>
            <div>
              <CardTitle className="text-lg text-gray-900">Slack</CardTitle>
              <p className="text-sm text-gray-600">
                {isConnected
                  ? slackIntegration.workspace_name || 'Connected to workspace'
                  : 'Connect your Slack workspace for surveys and sentiment analysis'
                }
              </p>
            </div>
          </div>

          {/* Connection Status */}
          {isConnected ? (
            <button
              onClick={() => setSlackSurveyDisconnectDialogOpen(true)}
              disabled={isDisconnectingSlackSurvey}
              className="inline-flex items-center space-x-2 bg-green-100 text-green-800 px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isDisconnectingSlackSurvey ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Disconnecting...</span>
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" />
                  <span>Connected</span>
                </>
              )}
            </button>
          ) : null}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {!isConnected ? (
          <>
            {/* Feature Selection */}
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-3">Choose features to enable:</h4>
              <div className="space-y-3">
                {/* Survey Feature Card */}
                <div
                  className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
                    enableSlackSurvey
                      ? 'border-purple-400 bg-purple-50'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
                  onClick={() => setEnableSlackSurvey(!enableSlackSurvey)}
                >
                  <div className="flex items-start space-x-3">
                    <input
                      type="checkbox"
                      checked={enableSlackSurvey}
                      onChange={(e) => {
                        e.stopPropagation()
                        setEnableSlackSurvey(e.target.checked)
                      }}
                      className="w-5 h-5 text-gray-900 rounded focus:ring-gray-500 mt-0.5"
                    />
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h5 className="font-medium text-gray-900">Survey Delivery</h5>
                      </div>
                      <p className="text-sm text-gray-600">
                        Let team members report burnout via <code className="bg-gray-100 px-1 rounded text-xs">/burnout-survey</code> command and automated DMs
                      </p>
                    </div>
                  </div>
                </div>

                {/* Sentiment Analysis Feature Card */}
                <div
                  className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
                    enableSlackSentiment
                      ? 'border-purple-400 bg-purple-50'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
                  onClick={() => setEnableSlackSentiment(!enableSlackSentiment)}
                >
                  <div className="flex items-start space-x-3">
                    <input
                      type="checkbox"
                      checked={enableSlackSentiment}
                      onChange={(e) => {
                        e.stopPropagation()
                        setEnableSlackSentiment(e.target.checked)
                      }}
                      className="w-5 h-5 text-gray-900 rounded focus:ring-gray-500 mt-0.5"
                    />
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h5 className="font-medium text-gray-900">Sentiment Analysis</h5>
                      </div>
                      <p className="text-sm text-gray-600">
                        Analyze channel messages to detect burnout patterns and communication trends
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Connect Button */}
            {process.env.NEXT_PUBLIC_SLACK_CLIENT_ID ? (
              <div className="flex justify-center pt-2">
                <Button
                  onClick={handleSlackConnect}
                  disabled={isConnectingSlackOAuth || (!enableSlackSurvey && !enableSlackSentiment)}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2.5 text-base"
                  size="lg"
                >
                  {isConnectingSlackOAuth ? (
                    <span className="flex items-center space-x-2">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Connecting...</span>
                    </span>
                  ) : (
                    <span className="flex items-center space-x-2">
                      <SlackIcon />
                      <span>Add to Slack</span>
                    </span>
                  )}
                </Button>
              </div>
            ) : (
              <div className="text-center py-4">
                <div className="inline-flex items-center space-x-2 bg-gray-100 text-gray-500 px-4 py-2 rounded-lg text-sm font-medium">
                  <SlackIcon />
                  <span>Slack App Not Configured</span>
                </div>
              </div>
            )}

            <div className="text-xs text-gray-500 text-center">
              <p>You can enable both features or choose just one. Features can be modified later.</p>
            </div>
          </>
        ) : (
          <>
            {/* Connected State - Show Enabled Features */}
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-3">Enabled Features:</h4>
              <div className="space-y-2">
                {surveyEnabled && (
                  <div className="flex items-center space-x-2 text-sm text-green-700 bg-green-50 px-3 py-2 rounded-lg">
                    <CheckCircle className="w-4 h-4" />
                    <span>Survey Delivery</span>
                  </div>
                )}
                {sentimentEnabled && (
                  <div className="flex items-center space-x-2 text-sm text-green-700 bg-green-50 px-3 py-2 rounded-lg">
                    <CheckCircle className="w-4 h-4" />
                    <span>Sentiment Analysis</span>
                  </div>
                )}
                {!surveyEnabled && !sentimentEnabled && (
                  <div className="text-sm text-gray-500 italic">No features enabled</div>
                )}
              </div>
            </div>

            {/* Survey Tabs - Only show if survey is enabled */}
            {surveyEnabled && (
              <div className="border-t pt-4">
                <SlackSurveyTabs
                  slackIntegration={slackIntegration}
                  selectedOrganization={selectedOrganization}
                  integrations={integrations}
                  teamMembers={teamMembers}
                  loadingTeamMembers={loadingTeamMembers}
                  loadingSyncedUsers={loadingSyncedUsers}
                  userInfo={userInfo}
                  fetchTeamMembers={fetchTeamMembers}
                  syncUsersToCorrelation={syncUsersToCorrelation}
                  fetchSyncedUsers={fetchSyncedUsers}
                  setShowManualSurveyModal={setShowManualSurveyModal}
                  loadSlackPermissions={loadSlackPermissions}
                  toast={toast}
                />
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
