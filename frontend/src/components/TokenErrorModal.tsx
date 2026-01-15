import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { AlertCircle, RefreshCw } from "lucide-react"

interface TokenErrorModalProps {
  isOpen: boolean
  onClose: () => void
  errorType: 'expired' | 'permissions' | null
  integrationName: string
  missingPermissions?: string[]
}

export function TokenErrorModal({
  isOpen,
  onClose,
  errorType,
  integrationName,
  missingPermissions = []
}: TokenErrorModalProps) {
  const isExpired = errorType === 'expired'
  const isPermissions = errorType === 'permissions'

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-full bg-red-100">
              <AlertCircle className="w-6 h-6 text-red-600" />
            </div>
            <DialogTitle className="text-xl">
              {isExpired ? 'Token Expired' : 'Insufficient Permissions'}
            </DialogTitle>
          </div>
          <DialogDescription className="text-base pt-2">
            {isExpired ? (
              <>
                The API token for <strong>{integrationName}</strong> has expired or is invalid.
              </>
            ) : (
              <>
                The integration <strong>{integrationName}</strong> is missing required permissions.
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {isExpired ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm text-neutral-700">
                Please refresh your API token in the integration settings to continue using this organization.
              </p>
            </div>
          ) : (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-2">
              <p className="text-sm font-medium text-neutral-700">
                Missing access to:
              </p>
              <ul className="list-disc list-inside text-sm text-neutral-600 space-y-1">
                {missingPermissions.map((permission, idx) => (
                  <li key={idx}>{permission}</li>
                ))}
              </ul>
              <p className="text-sm text-neutral-700 pt-2">
                Please update the token permissions and test the connection.
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="flex gap-2">
          <Button
            variant="outline"
            onClick={onClose}
          >
            Close
          </Button>
          <Button
            onClick={() => {
              // Scroll to integrations section
              const integrationsSection = document.getElementById('integrations-section')
              if (integrationsSection) {
                integrationsSection.scrollIntoView({ behavior: 'smooth' })
              }
              onClose()
            }}
            className="bg-purple-600 hover:bg-purple-700 text-white"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Go to Settings
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
