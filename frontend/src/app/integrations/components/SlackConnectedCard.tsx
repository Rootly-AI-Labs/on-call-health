import Image from "next/image"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Key, Calendar, Building, Clock, Users, Trash2, Loader2, CheckCircle, AlertCircle, RotateCcw } from "lucide-react"
import { SlackIntegration } from "../types"

interface SlackConnectedCardProps {
  integration: SlackIntegration
  slackPermissions: any
  isLoadingPermissions: boolean
  onDisconnect: () => void
  onTest: () => void
  onViewMappings: () => void
  onLoadPermissions: () => void
  loadingMappings: boolean
  selectedMappingPlatform: string | null
}

export function SlackConnectedCard({
  integration,
  slackPermissions,
  isLoadingPermissions,
  onDisconnect,
  onTest,
  onViewMappings,
  onLoadPermissions,
  loadingMappings,
  selectedMappingPlatform
}: SlackConnectedCardProps) {
  return (
    <Card className="border-green-200 bg-green-50 max-w-2xl mx-auto">
      <CardHeader className="p-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center">
              <Image
                src="/images/slack-logo.png"
                alt="Slack"
                width={40}
                height={40}
                className="h-10 w-10 object-contain"
              />
            </div>
            <div>
              <CardTitle>Slack Connected</CardTitle>
              <CardDescription>User ID: {integration.slack_user_id}</CardDescription>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Button
              size="sm"
              variant="outline"
              onClick={onViewMappings}
              disabled={loadingMappings}
              className="bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100 hover:text-purple-800 hover:border-purple-300"
              title="View and manage Slack user mappings"
            >
              {loadingMappings && selectedMappingPlatform === 'slack' ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  <Users className="w-4 h-4 mr-2" />
                  View Mappings
                </>
              )}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={onDisconnect}
              className="h-8 w-8 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-8 pt-0">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div className="flex items-center space-x-2">
              <Key className="w-4 h-4 text-gray-400" />
              <div>
                <div className="font-medium">Webhook URL</div>
                <div className="text-gray-600 font-mono text-xs">
                  {integration.webhook_preview || 'Not configured'}
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Key className="w-4 h-4 text-gray-400" />
              <div>
                <div className="font-medium">Bot Token</div>
                <div className="text-gray-600 font-mono text-xs">
                  {integration.token_preview || 'Not available'}
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Building className="w-4 h-4 text-gray-400" />
              <div>
                <div className="font-medium">Workspace ID</div>
                <div className="text-gray-600 font-mono text-xs">{integration.workspace_id}</div>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Calendar className="w-4 h-4 text-gray-400" />
              <div>
                <div className="font-medium">Connected</div>
                <div className="text-gray-600">{new Date(integration.connected_at).toLocaleDateString()}</div>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Clock className="w-4 h-4 text-gray-400" />
              <div>
                <div className="font-medium">Last Updated</div>
                <div className="text-gray-600">{new Date(integration.last_updated).toLocaleDateString()}</div>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Users className="w-4 h-4 text-gray-400" />
              <div>
                <div className="font-medium">User ID</div>
                <div className="text-gray-600 font-mono text-xs">{integration.slack_user_id}</div>
              </div>
            </div>
          </div>

        {/* Permissions Section */}
        <div className="border-t pt-4 mt-6">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-medium text-sm">Bot Permissions</h4>
            {isLoadingPermissions && (
              <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
            )}
          </div>
          {slackPermissions ? (
            <div className="grid grid-cols-1 gap-2">
              {Object.entries(slackPermissions)
                .filter(([permission]) => ['channels_access', 'users_access', 'channels_history'].includes(permission))
                .map(([permission, hasAccess]) => {
                const isGranted = hasAccess === true
                const permissionLabels: { [key: string]: string } = {
                  'channels_access': 'Channel Access',
                  'users_access': 'User Access',
                  'channels_history': 'Channel History'
                }

                return (
                  <div key={permission} className="flex items-center justify-between text-xs">
                    <span className="text-gray-600">{permissionLabels[permission] || permission}</span>
                    <div className="flex items-center space-x-1">
                      {isGranted ? (
                        <>
                          <CheckCircle className="w-3 h-3 text-green-500" />
                          <span className="text-green-600 font-medium">Granted</span>
                        </>
                      ) : (
                        <>
                          <AlertCircle className="w-3 h-3 text-red-500" />
                          <span className="text-red-600 font-medium">
                            {permission === 'channels_history' && slackPermissions.errors?.includes('not_in_channel')
                              ? 'Bot not in channels'
                              : 'Missing'}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-xs text-gray-500">
              Permissions will be checked automatically from "Check & Fix Workspace Registration"
            </div>
          )}
        </div>

        {/* Bot Channels Section */}
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-medium text-sm">Bot Channels</h4>
          </div>
          {integration?.channel_names && integration.channel_names.length > 0 ? (
            <div className="space-y-1">
              {integration.channel_names.map((channelName: string) => (
                <div key={channelName} className="flex items-center space-x-2 text-xs">
                  <span className="text-gray-400">#</span>
                  <span className="text-gray-700">{channelName}</span>
                  <CheckCircle className="w-3 h-3 text-green-500" />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-gray-500">
              {slackPermissions?.errors?.includes('not_in_channel')
                ? 'Bot is not in any channels. Add it to channels in Slack.'
                : 'No channels found'}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
