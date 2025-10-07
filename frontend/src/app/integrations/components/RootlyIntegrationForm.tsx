import { useState } from "react"
import Image from "next/image"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { HelpCircle, ChevronDown, CheckCircle, AlertCircle, Shield, Plus, Loader2, Eye, EyeOff, Copy, Check } from "lucide-react"
import { UseFormReturn } from "react-hook-form"
import { RootlyFormData, PreviewData } from "../types"

interface RootlyIntegrationFormProps {
  form: UseFormReturn<RootlyFormData>
  onTest: (platform: 'rootly', token: string) => Promise<void>
  onAdd: () => void
  connectionStatus: 'idle' | 'success' | 'error' | 'duplicate'
  previewData: PreviewData | null
  duplicateInfo: any
  isTestingConnection: boolean
  isAdding: boolean
  isValidToken: (token: string) => boolean
  onCopyToken: (token: string) => void
  copied: boolean
}

export function RootlyIntegrationForm({
  form,
  onTest,
  onAdd,
  connectionStatus,
  previewData,
  duplicateInfo,
  isTestingConnection,
  isAdding,
  isValidToken,
  onCopyToken,
  copied
}: RootlyIntegrationFormProps) {
  const [showInstructions, setShowInstructions] = useState(false)
  const [showToken, setShowToken] = useState(false)

  return (
    <Card className="border-purple-200 max-w-2xl mx-auto">
      <CardHeader className="p-8">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
            <Image src="/images/rootly-logo-branded.png" alt="Rootly" width={24} height={24} />
          </div>
          <div>
            <CardTitle>Add Rootly Integration</CardTitle>
            <CardDescription>Connect your Rootly account to analyze incident data</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 p-8 pt-0">
        {/* Instructions */}
        <div>
          <button
            type="button"
            onClick={() => setShowInstructions(!showInstructions)}
            className="flex items-center space-x-2 text-sm text-purple-600 hover:text-purple-700"
          >
            <HelpCircle className="w-4 h-4" />
            <span>How to get your Rootly API token</span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showInstructions ? 'rotate-180' : ''}`} />
          </button>
          {showInstructions && (
            <div className="mt-4">
              <Alert className="border-purple-200 bg-purple-50">
                <AlertDescription>
                  <ol className="space-y-2 text-sm">
                    <li><strong>1.</strong> Log in to your Rootly account</li>
                    <li><strong>2.</strong> Navigate to <code className="bg-purple-100 px-1 rounded">Settings → API Keys</code></li>
                    <li><strong>3.</strong> Click <strong>"Create API Key"</strong></li>
                    <li><strong>4.</strong> Give it a name (e.g., <strong>"Burnout Detector"</strong>)</li>
                    <li><strong>5.</strong> Select appropriate permissions (<strong>required:</strong> read access to incidents and users)</li>
                    <li><strong>6.</strong> Copy the generated token (starts with <strong>"rootly_"</strong>)</li>
                  </ol>
                </AlertDescription>
              </Alert>
            </div>
          )}
        </div>

        {/* Form */}
        <Form {...form}>
          <form onSubmit={form.handleSubmit((data) => onTest('rootly', data.rootlyToken))} className="space-y-4">
            <FormField
              control={form.control}
              name="rootlyToken"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Rootly API Token</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        {...field}
                        type={showToken ? "text" : "password"}
                        placeholder="rootly_********************************"
                        className="pr-20"
                      />
                      <div className="absolute inset-y-0 right-0 flex items-center space-x-1 pr-3">
                        {field.value && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0"
                            onClick={() => onCopyToken(field.value)}
                          >
                            {copied ? (
                              <Check className="h-3 w-3 text-green-600" />
                            ) : (
                              <Copy className="h-3 w-3 text-slate-400" />
                            )}
                          </Button>
                        )}
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0"
                          onClick={() => setShowToken(!showToken)}
                        >
                          {showToken ? (
                            <EyeOff className="h-3 w-3 text-slate-400" />
                          ) : (
                            <Eye className="h-3 w-3 text-slate-400" />
                          )}
                        </Button>
                      </div>
                    </div>
                  </FormControl>
                  <FormDescription>
                    Token should start with "rootly_" followed by 64 hex characters
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Connection Status */}
            {connectionStatus === 'success' && previewData && (
              <>
                <Alert className="border-purple-200 bg-purple-50">
                  <CheckCircle className="h-4 w-4 text-purple-600" />
                  <AlertDescription className="text-purple-800">
                    <div className="space-y-2">
                      <p className="font-semibold">✅ Token validated! Permissions verified.</p>
                      <p className="text-sm text-purple-700">Ready to add this Rootly integration to your dashboard.</p>
                      <div className="space-y-1 text-sm">
                        <p><span className="font-medium">Organization:</span> {previewData.organization_name}</p>
                        <p><span className="font-medium">Users:</span> {previewData.total_users}</p>
                        {previewData.permissions && (
                          <div className="mt-2">
                            <p className="font-medium">Permissions:</p>
                            <div className="grid grid-cols-2 gap-2 mt-1">
                              <div className="flex items-center">
                                {previewData.permissions.users?.access ? (
                                  <CheckCircle className="w-3 h-3 text-green-600 mr-1" />
                                ) : (
                                  <AlertCircle className="w-3 h-3 text-red-600 mr-1" />
                                )}
                                <span className="text-xs">Users</span>
                              </div>
                              <div className="flex items-center">
                                {previewData.permissions.incidents?.access ? (
                                  <CheckCircle className="w-3 h-3 text-green-600 mr-1" />
                                ) : (
                                  <AlertCircle className="w-3 h-3 text-red-600 mr-1" />
                                )}
                                <span className="text-xs">Incidents</span>
                              </div>
                            </div>
                            {(!previewData.permissions.users?.access || !previewData.permissions.incidents?.access) && (
                              <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs">
                                <p className="font-medium text-red-800">Missing permissions:</p>
                                {!previewData.permissions.users?.access && (
                                  <p className="text-red-700">• Users: {previewData.permissions.users?.error}</p>
                                )}
                                {!previewData.permissions.incidents?.access && (
                                  <p className="text-red-700">• Incidents: {previewData.permissions.incidents?.error}</p>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </AlertDescription>
                </Alert>

                <FormField
                  control={form.control}
                  name="nickname"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Integration Name (optional)</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder={previewData.suggested_name || previewData.organization_name}
                        />
                      </FormControl>
                      <FormDescription>
                        Give this integration a custom name
                      </FormDescription>
                    </FormItem>
                  )}
                />
              </>
            )}

            {connectionStatus === 'error' && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  ❌ Invalid API token. Please verify your Rootly token and try again.
                </AlertDescription>
              </Alert>
            )}

            {connectionStatus === 'duplicate' && duplicateInfo && (
              <Alert className="border-yellow-200 bg-yellow-50">
                <AlertCircle className="h-4 w-4 text-yellow-600" />
                <AlertDescription className="text-yellow-800">
                  This Rootly account is already connected as "{duplicateInfo.existing_integration?.name || 'Unknown'}".
                </AlertDescription>
              </Alert>
            )}

            <div className="flex space-x-3">
              <Button
                type="submit"
                disabled={isTestingConnection || !isValidToken(form.watch('rootlyToken') || '')}
                className="bg-purple-600 hover:bg-purple-700"
              >
                {isTestingConnection ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Testing Connection...
                  </>
                ) : (
                  <>
                    <Shield className="w-4 h-4 mr-2" />
                    Test Connection
                  </>
                )}
              </Button>

              {connectionStatus === 'success' && previewData?.can_add && (
                <Button
                  type="button"
                  onClick={onAdd}
                  disabled={isAdding}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {isAdding ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4 mr-2" />
                      Add Integration
                    </>
                  )}
                </Button>
              )}
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  )
}
