import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

interface PostIntegrationSyncModalProps {
  isOpen: boolean
  onClose: () => void
  onSyncNow: () => void
  integrationType: 'github' | 'slack' | 'jira' | 'linear'
}

const integrationContent = {
  github: {
    title: "Sync your team members",
    message: "We need to match GitHub users with your existing team to include their data in your analyses."
  },
  slack: {
    title: "Sync your team members",
    message: "We need to match Slack users with your existing team to include their data in your analyses."
  },
  jira: {
    title: "Sync your team members",
    message: "We need to match Jira users with your existing team to include their data in your analyses."
  },
  linear: {
    title: "Sync your team members",
    message: "We need to match Linear users with your existing team to include their data in your analyses."
  }
}

export function PostIntegrationSyncModal({
  isOpen,
  onClose,
  onSyncNow,
  integrationType
}: PostIntegrationSyncModalProps) {
  const content = integrationContent[integrationType]

  // Defensive check: return empty dialog if content is undefined
  if (!content) {
    return (
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-center text-2xl">
              Integration Connected
            </DialogTitle>
            <DialogDescription className="text-center text-base mt-2">
              Your integration has been successfully connected.
            </DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-center text-2xl">
            {content.title}
          </DialogTitle>
          <DialogDescription className="text-center text-base mt-2">
            {content.message}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3 mt-6 w-full">
          <Button
            onClick={onSyncNow}
            className="w-full bg-purple-700 hover:bg-purple-800 flex items-center justify-center"
          >
            <span className="mx-auto">Sync Now</span>
          </Button>
          <Button
            variant="outline"
            onClick={onClose}
            className="w-full flex items-center justify-center"
          >
            <span className="mx-auto">Skip</span>
          </Button>
        </div>

        {/* Footer Note */}
        <div className="text-center text-xs text-neutral-500 mt-2">
          You can sync members anytime from the integrations page
        </div>
      </DialogContent>
    </Dialog>
  )
}
