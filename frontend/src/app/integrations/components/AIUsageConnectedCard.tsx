import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CheckCircle, Loader2, Trash2, Zap } from "lucide-react"

interface AIUsageConnectedCardProps {
  status: {
    connected: boolean
    openai_enabled: boolean
    anthropic_enabled: boolean
  }
  onDisconnect: (provider?: string) => Promise<void>
  onTest: () => Promise<void>
  isLoading: boolean
}

export function AIUsageConnectedCard({ status, onDisconnect, onTest, isLoading }: AIUsageConnectedCardProps) {
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

  const handleTest = async () => {
    setIsTesting(true)
    setTestResult(null)
    try {
      await onTest()
      setTestResult({ success: true, message: "Connection verified successfully" })
    } catch (e: any) {
      setTestResult({ success: false, message: e?.message ?? "Connection test failed" })
    } finally {
      setIsTesting(false)
    }
  }

  return (
    <Card className="border-2 border-green-200 max-w-2xl mx-auto">
      <CardContent className="pt-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <h3 className="text-lg font-semibold text-slate-900">AI Usage Connected</h3>
          </div>
          <Badge variant="secondary" className="bg-green-100 text-green-700 border-green-200">
            Active
          </Badge>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className={`rounded-lg p-3 border ${status.openai_enabled ? 'bg-green-50 border-green-200' : 'bg-neutral-50 border-neutral-200'}`}>
            <div className="text-sm font-medium text-neutral-700">OpenAI</div>
            <div className={`text-xs mt-0.5 ${status.openai_enabled ? 'text-green-600' : 'text-neutral-400'}`}>
              {status.openai_enabled ? "Connected" : "Not configured"}
            </div>
            {status.openai_enabled && (
              <button
                onClick={() => onDisconnect("openai")}
                disabled={isLoading}
                className="mt-2 text-xs text-red-500 hover:text-red-700 underline"
              >
                Remove
              </button>
            )}
          </div>

          <div className={`rounded-lg p-3 border ${status.anthropic_enabled ? 'bg-green-50 border-green-200' : 'bg-neutral-50 border-neutral-200'}`}>
            <div className="text-sm font-medium text-neutral-700">Anthropic</div>
            <div className={`text-xs mt-0.5 ${status.anthropic_enabled ? 'text-green-600' : 'text-neutral-400'}`}>
              {status.anthropic_enabled ? "Connected" : "Not configured"}
            </div>
            {status.anthropic_enabled && (
              <button
                onClick={() => onDisconnect("anthropic")}
                disabled={isLoading}
                className="mt-2 text-xs text-red-500 hover:text-red-700 underline"
              >
                Remove
              </button>
            )}
          </div>
        </div>

        <p className="text-xs text-neutral-500">
          AI usage data will be collected on the next analysis run and shown in the dashboard.
        </p>

        {testResult && (
          <div className={`flex items-center gap-2 text-xs rounded-lg px-3 py-2 ${testResult.success ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
            {testResult.success
              ? <CheckCircle className="w-3.5 h-3.5 shrink-0" />
              : <span className="shrink-0">✕</span>}
            {testResult.message}
          </div>
        )}

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handleTest}
            disabled={isTesting || isLoading}
            className="flex-1 border-indigo-200 text-indigo-600 hover:bg-indigo-50"
          >
            {isTesting ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Testing...</>
            ) : (
              <><Zap className="w-4 h-4 mr-2" />Test Connection</>
            )}
          </Button>

          <Button
            variant="outline"
            onClick={() => onDisconnect()}
            disabled={isLoading || isTesting}
            className="flex-1 border-red-200 text-red-600 hover:bg-red-50"
          >
            {isLoading ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Disconnecting...</>
            ) : (
              <><Trash2 className="w-4 h-4 mr-2" />Disconnect All</>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
