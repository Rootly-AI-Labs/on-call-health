import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { CheckCircle, Loader2 } from "lucide-react"

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
    message: "Your GitHub integration is now connected. To enable GitHub data in your burnout analyses, you'll need to sync your team members.",
    syncDetails: [
      "Team members from your primary integration (Rootly/PagerDuty) will be matched to GitHub accounts",
      "Automatic matching by email and name",
      "Creates mappings used for analyzing GitHub activity (commits, PRs, code reviews, after-hours work)",
      "Takes 1-2 minutes depending on team size"
    ]
  },
  slack: {
    title: "Slack Connected Successfully!",
    message: "Your Slack integration is now connected. To enable Slack data in your burnout analyses, you'll need to sync your team members.",
    syncDetails: [
      "Team members from your primary integration (Rootly/PagerDuty) will be matched to Slack accounts",
      "Automatic matching by email",
      "Creates mappings used for analyzing communication patterns and message activity",
      "Takes 1-2 minutes depending on team size"
    ]
  },
  jira: {
    title: "Jira Connected Successfully!",
    message: "Your Jira integration is now connected. To enable Jira data in your burnout analyses, you'll need to sync your team members.",
    syncDetails: [
      "Team members from your primary integration (Rootly/PagerDuty) will be matched to Jira accounts",
      "Automatic matching by email and account ID",
      "Creates mappings used for analyzing issue assignments and work tracking",
      "Takes 1-2 minutes depending on team size"
    ]
  },
  linear: {
    title: "Linear Connected Successfully!",
    message: "Your Linear integration is now connected. To enable Linear data in your burnout analyses, you'll need to sync your team members.",
    syncDetails: [
      "Team members from your primary integration (Rootly/PagerDuty) will be matched to Linear accounts",
      "Automatic matching by email",
      "Creates mappings used for analyzing issue tracking and project cycles",
      "Takes 1-2 minutes depending on team size"
    ]
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
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <div className="flex items-center justify-center mb-4">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle className="w-10 h-10 text-green-600" />
            </div>
          </div>
          <DialogTitle className="text-center text-2xl">
            {content.title}
          </DialogTitle>
          <DialogDescription className="text-center text-base mt-2">
            {content.message}
          </DialogDescription>
        </DialogHeader>

        {/* Info Box */}
        <div className="mt-4 px-4 py-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h4 className="font-semibold text-neutral-900 mb-3">What happens during sync:</h4>
          <ul className="space-y-2 text-sm text-neutral-700">
            {content.syncDetails.map((detail, index) => (
              <li key={index} className="flex items-start">
                <span className="mr-2 mt-0.5">•</span>
                <span>{detail}</span>
              </li>
            ))}
          </ul>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-3 mt-6">
          <Button
            variant="outline"
            onClick={onClose}
            className="w-full sm:w-auto order-2 sm:order-1"
          >
            I'll Do This Later
          </Button>
          <Button
            onClick={onSyncNow}
            className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 order-1 sm:order-2"
          >
            Sync Now
          </Button>
        </DialogFooter>

        {/* Footer Note */}
        <div className="text-center text-xs text-neutral-500 mt-2">
          You can sync members anytime from the integrations page
        </div>
      </DialogContent>
    </Dialog>
  )
}
