import { useState } from "react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { CheckCircle, ChevronDown, Loader2, Trash2, Zap } from "lucide-react"

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
    <Card className="border-2 border-green-200 bg-green-50/50 max-w-2xl mx-auto">
      <CardHeader>
        <div className="flex items-center space-x-3">
          <div className="flex items-center gap-1">
            <Image src="/images/openai-logo.svg" alt="OpenAI" width={20} height={20} className="w-5 h-5" />
            <span className="text-slate-300 text-sm">/</span>
            <Image src="/images/anthropic-logo.svg" alt="Anthropic" width={20} height={20} className="w-5 h-5" />
          </div>
          <div>
            <CardTitle className="text-lg flex items-center space-x-2">
              <span>AI Usage</span>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Badge
                    variant="secondary"
                    className="bg-green-100 text-green-700 cursor-pointer hover:bg-green-200 transition-colors"
                  >
                    <CheckCircle className="w-3 h-3 mr-1" />
                    Connected
                    <ChevronDown className="w-3 h-3 ml-1" />
                  </Badge>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                  <DropdownMenuItem onClick={handleTest} disabled={isTesting || isLoading}>
                    {isTesting ? (
                      <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                    ) : (
                      <Zap className="w-3 h-3 mr-2" />
                    )}
                    Test Connection
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </CardTitle>
            <p className="text-sm text-slate-600">Token consumption tracking from OpenAI and/or Anthropic</p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Provider details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="flex items-center space-x-2">
            <Image src="/images/openai-logo.svg" alt="OpenAI" width={16} height={16} className="w-4 h-4" />
            <div>
              <div className="font-medium">OpenAI</div>
              <div className={status.openai_enabled ? "text-green-600" : "text-slate-400"}>
                {status.openai_enabled ? "Connected" : "Not configured"}
              </div>
              {status.openai_enabled && (
                <button
                  onClick={() => onDisconnect("openai")}
                  disabled={isLoading}
                  className="mt-0.5 text-xs text-red-500 hover:text-red-700 underline disabled:opacity-50"
                >
                  Remove
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Image src="/images/anthropic-logo.svg" alt="Anthropic" width={16} height={16} className="w-4 h-4" />
            <div>
              <div className="font-medium">Anthropic</div>
              <div className={status.anthropic_enabled ? "text-green-600" : "text-slate-400"}>
                {status.anthropic_enabled ? "Connected" : "Not configured"}
              </div>
              {status.anthropic_enabled && (
                <button
                  onClick={() => onDisconnect("anthropic")}
                  disabled={isLoading}
                  className="mt-0.5 text-xs text-red-500 hover:text-red-700 underline disabled:opacity-50"
                >
                  Remove
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Test result */}
        {testResult && (
          <div className={`flex items-center gap-2 text-xs rounded-lg px-3 py-2 border ${
            testResult.success
              ? "bg-green-50 text-green-700 border-green-200"
              : "bg-red-50 text-red-700 border-red-200"
          }`}>
            {testResult.success
              ? <CheckCircle className="w-3.5 h-3.5 shrink-0" />
              : <span className="shrink-0">✕</span>}
            {testResult.message}
          </div>
        )}

        {/* Data collection note */}
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-600">
          <div className="font-medium mb-1">Data Collection</div>
          <div>
            We collect daily token consumption and request counts from your connected AI providers.
            Usage data is shown on the dashboard after each analysis run.
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center justify-end pt-4 border-t">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDisconnect()}
            disabled={isLoading || isTesting}
            className="text-red-600 hover:text-red-700 hover:bg-red-50"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Trash2 className="w-4 h-4 mr-2" />
            )}
            Disconnect All
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
