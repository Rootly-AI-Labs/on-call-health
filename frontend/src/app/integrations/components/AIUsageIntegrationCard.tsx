import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { HelpCircle, ChevronDown, ExternalLink, Eye, EyeOff, Loader2, Settings2 } from "lucide-react"

interface AIUsageIntegrationCardProps {
  onConnect: (
    openaiKey: string,
    openaiOrgId: string,
    anthropicKey: string,
    anthropicWorkspaceId: string,
  ) => Promise<void>
  isConnecting: boolean
}

export function AIUsageIntegrationCard({ onConnect, isConnecting }: AIUsageIntegrationCardProps) {
  const [showOpenaiInstructions, setShowOpenaiInstructions] = useState(false)
  const [showAnthropicInstructions, setShowAnthropicInstructions] = useState(false)
  const [showOpenaiAdvanced, setShowOpenaiAdvanced] = useState(false)
  const [showAnthropicAdvanced, setShowAnthropicAdvanced] = useState(false)
  const [openaiKey, setOpenaiKey] = useState("")
  const [openaiOrgId, setOpenaiOrgId] = useState("")
  const [anthropicKey, setAnthropicKey] = useState("")
  const [anthropicWorkspaceId, setAnthropicWorkspaceId] = useState("")
  const [showOpenai, setShowOpenai] = useState(false)
  const [showAnthropic, setShowAnthropic] = useState(false)

  const canSubmit = openaiKey.trim() || anthropicKey.trim()

  return (
    <Card className="border-neutral-200 max-w-2xl mx-auto">
      <CardHeader className="p-8">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center">
            <svg viewBox="0 0 24 24" className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z" />
            </svg>
          </div>
          <div>
            <CardTitle>Add AI Usage Tracking</CardTitle>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6 p-8 pt-0">

        {/* ── OpenAI section ── */}
        <div className="space-y-3">
          <label className="text-sm font-medium text-neutral-900">OpenAI Admin API Key</label>

          {/* Instructions dropdown */}
          <button
            type="button"
            onClick={() => setShowOpenaiInstructions(!showOpenaiInstructions)}
            className="flex items-center space-x-2 text-sm text-neutral-600 hover:text-neutral-900"
          >
            <HelpCircle className="w-4 h-4" />
            <span>How to get your OpenAI Admin API key</span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showOpenaiInstructions ? 'rotate-180' : ''}`} />
          </button>

          {showOpenaiInstructions && (
            <Alert className="border-neutral-200 bg-neutral-100">
              <AlertDescription>
                <div className="space-y-3">
                  <p className="text-sm text-neutral-600">
                    The usage API requires an <strong>Admin API key</strong> — not a standard API key. Only Organization Owners can create Admin keys.
                  </p>
                  <div>
                    <h5 className="text-sm font-medium text-neutral-900 mb-1"><strong>Step 1:</strong> Go to Admin Keys settings</h5>
                    <p className="text-sm text-neutral-700 mb-1">Navigate to <strong>OpenAI Platform → Settings → Organization → Admin Keys</strong></p>
                    <a href="https://platform.openai.com/settings/organization/admin-keys" target="_blank" rel="noopener noreferrer" className="inline-flex items-center text-sm text-blue-600 hover:underline">
                      Open Admin Keys settings <ExternalLink className="w-3 h-3 ml-1" />
                    </a>
                  </div>
                  <div>
                    <h5 className="text-sm font-medium text-neutral-900 mb-1"><strong>Step 2:</strong> Create a new Admin API key</h5>
                    <p className="text-sm text-neutral-700">Click <strong>"Create new key"</strong> and give it a name (e.g., "On-Call Health Usage").</p>
                  </div>
                  <div>
                    <h5 className="text-sm font-medium text-neutral-900 mb-1"><strong>Step 3:</strong> Copy the key immediately</h5>
                    <p className="text-sm text-neutral-700">
                      Copy the key — it starts with <code className="bg-neutral-300 px-1 rounded text-xs">sk-admin-</code>. <strong>You won't be able to see it again.</strong>
                    </p>
                  </div>
                  <a href="https://platform.openai.com/docs/api-reference/usage/completions" target="_blank" rel="noopener noreferrer" className="inline-flex items-center text-sm text-blue-600 hover:underline">
                    View Usage API docs <ExternalLink className="w-3 h-3 ml-1" />
                  </a>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Key input */}
          <div className="relative">
            <Input
              type={showOpenai ? "text" : "password"}
              placeholder="sk-admin-..."
              value={openaiKey}
              onChange={e => setOpenaiKey(e.target.value.trim())}
              className="pr-10"
            />
            <Button type="button" variant="ghost" size="sm" className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent" onClick={() => setShowOpenai(v => !v)}>
              {showOpenai ? <EyeOff className="h-4 w-4 text-neutral-500" /> : <Eye className="h-4 w-4 text-neutral-500" />}
            </Button>
          </div>

          {/* Advanced toggle */}
          <button
            type="button"
            onClick={() => setShowOpenaiAdvanced(!showOpenaiAdvanced)}
            className="flex items-center space-x-2 text-xs text-neutral-400 hover:text-neutral-600"
          >
            <Settings2 className="w-3.5 h-3.5" />
            <span>Advanced</span>
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showOpenaiAdvanced ? 'rotate-180' : ''}`} />
          </button>

          {showOpenaiAdvanced && (
            <div className="space-y-1.5">
              <p className="text-xs text-neutral-500">
                <strong>Organization ID</strong> — only needed if your account has access to multiple OpenAI organizations and you want to scope usage data to a specific one. Leave blank in most cases; the key already determines which org is used.
              </p>
              <Input
                type="text"
                placeholder="org-... (leave blank unless multi-org)"
                value={openaiOrgId}
                onChange={e => setOpenaiOrgId(e.target.value.trim())}
              />
            </div>
          )}
        </div>

        <hr className="border-neutral-200" />

        {/* ── Anthropic section ── */}
        <div className="space-y-3">
          <label className="text-sm font-medium text-neutral-900">Anthropic Admin API Key</label>

          {/* Instructions dropdown */}
          <button
            type="button"
            onClick={() => setShowAnthropicInstructions(!showAnthropicInstructions)}
            className="flex items-center space-x-2 text-sm text-neutral-600 hover:text-neutral-900"
          >
            <HelpCircle className="w-4 h-4" />
            <span>How to get your Anthropic Admin API key</span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showAnthropicInstructions ? 'rotate-180' : ''}`} />
          </button>

          {showAnthropicInstructions && (
            <Alert className="border-neutral-200 bg-neutral-100">
              <AlertDescription>
                <div className="space-y-3">
                  <p className="text-sm text-neutral-600">
                    The Anthropic usage report API requires an <strong>Admin API key</strong>. Only workspace admins can create these.
                  </p>
                  <div>
                    <h5 className="text-sm font-medium text-neutral-900 mb-1"><strong>Step 1:</strong> Go to API Keys in the Console</h5>
                    <p className="text-sm text-neutral-700 mb-1">Navigate to <strong>Anthropic Console → Settings → API Keys</strong></p>
                    <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" className="inline-flex items-center text-sm text-blue-600 hover:underline">
                      Open Anthropic Console <ExternalLink className="w-3 h-3 ml-1" />
                    </a>
                  </div>
                  <div>
                    <h5 className="text-sm font-medium text-neutral-900 mb-1"><strong>Step 2:</strong> Create a key with Admin permissions</h5>
                    <p className="text-sm text-neutral-700">
                      Click <strong>"Create Key"</strong> and ensure it has <strong>Admin</strong> role — not Developer. The key starts with <code className="bg-neutral-300 px-1 rounded text-xs">sk-ant-admin-</code>.
                    </p>
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Key input */}
          <div className="relative">
            <Input
              type={showAnthropic ? "text" : "password"}
              placeholder="sk-ant-admin-..."
              value={anthropicKey}
              onChange={e => setAnthropicKey(e.target.value.trim())}
              className="pr-10"
            />
            <Button type="button" variant="ghost" size="sm" className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent" onClick={() => setShowAnthropic(v => !v)}>
              {showAnthropic ? <EyeOff className="h-4 w-4 text-neutral-500" /> : <Eye className="h-4 w-4 text-neutral-500" />}
            </Button>
          </div>

          {/* Advanced toggle */}
          <button
            type="button"
            onClick={() => setShowAnthropicAdvanced(!showAnthropicAdvanced)}
            className="flex items-center space-x-2 text-xs text-neutral-400 hover:text-neutral-600"
          >
            <Settings2 className="w-3.5 h-3.5" />
            <span>Advanced</span>
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showAnthropicAdvanced ? 'rotate-180' : ''}`} />
          </button>

          {showAnthropicAdvanced && (
            <div className="space-y-1.5">
              <p className="text-xs text-neutral-500">
                <strong>Workspace ID</strong> — only needed if your organization uses multiple Anthropic workspaces and you want to scope usage data to a specific one. Leave blank to use the default workspace associated with the key.
              </p>
              <Input
                type="text"
                placeholder="Workspace ID (leave blank unless multi-workspace)"
                value={anthropicWorkspaceId}
                onChange={e => setAnthropicWorkspaceId(e.target.value.trim())}
              />
            </div>
          )}
        </div>

        <Button
          className="bg-indigo-600 hover:bg-indigo-700 text-white w-full"
          onClick={() => onConnect(openaiKey, openaiOrgId, anthropicKey, anthropicWorkspaceId)}
          disabled={!canSubmit || isConnecting}
        >
          {isConnecting ? (
            <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Connecting...</>
          ) : (
            'Connect AI Usage'
          )}
        </Button>

      </CardContent>
    </Card>
  )
}
