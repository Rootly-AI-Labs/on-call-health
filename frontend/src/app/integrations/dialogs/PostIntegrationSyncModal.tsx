import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

interface PostIntegrationSyncModalProps {
  isOpen: boolean
  onClose: () => void
  onSyncNow: () => void
  integrationType: 'github' | 'slack' | 'jira' | 'linear'
  integrationName: string
}

const integrationContent = {
  github: {
    title: "GitHub Connected Successfully!",
    message: "Your GitHub integration is now connected. To enable GitHub data in your burnout analyses, you'll need to sync your team members."
  },
  slack: {
    title: "Slack Connected Successfully!",
    message: "Your Slack integration is now connected. To enable Slack data in your burnout analyses, you'll need to sync your team members."
  },
  jira: {
    title: "Jira Connected Successfully!",
    message: "Your Jira integration is now connected. To enable Jira data in your burnout analyses, you'll need to sync your team members."
  },
  linear: {
    title: "Linear Connected Successfully!",
    message: "Your Linear integration is now connected. To enable Linear data in your burnout analyses, you'll need to sync your team members."
  }
}

export function PostIntegrationSyncModal({
  isOpen,
  onClose,
  onSyncNow,
  integrationType,
  integrationName
}: PostIntegrationSyncModalProps) {
  const content = integrationContent[integrationType]

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
            <span className="mx-auto">Sync Now (Recommended)</span>
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
