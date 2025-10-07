"use client"

import { UnifiedSlackCard } from "./UnifiedSlackCard"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface SurveyFeedbackSectionProps {
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

export function SurveyFeedbackSection({
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
}: SurveyFeedbackSectionProps) {
  return (
    <div className="mt-16 space-y-8">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-slate-900 mb-3">User-Reported Insights</h2>
        <p className="text-lg text-slate-600 mb-2">
          Enable team members to share their own burnout insights
        </p>
        <p className="text-slate-500">
          Collect direct feedback through Slack commands and sentiment analysis
        </p>
      </div>

      <div className="max-w-2xl mx-auto space-y-6">
        {/* Unified Slack Integration */}
        <UnifiedSlackCard
          slackIntegration={slackIntegration}
          loadingSlack={loadingSlack}
          isConnectingSlackOAuth={isConnectingSlackOAuth}
          isDisconnectingSlackSurvey={isDisconnectingSlackSurvey}
          userInfo={userInfo}
          selectedOrganization={selectedOrganization}
          integrations={integrations}
          teamMembers={teamMembers}
          loadingTeamMembers={loadingTeamMembers}
          loadingSyncedUsers={loadingSyncedUsers}
          fetchTeamMembers={fetchTeamMembers}
          syncUsersToCorrelation={syncUsersToCorrelation}
          fetchSyncedUsers={fetchSyncedUsers}
          setShowManualSurveyModal={setShowManualSurveyModal}
          loadSlackPermissions={loadSlackPermissions}
          setSlackSurveyDisconnectDialogOpen={setSlackSurveyDisconnectDialogOpen}
          setIsConnectingSlackOAuth={setIsConnectingSlackOAuth}
          toast={toast}
        />
      </div>
    </div>
  )
}
