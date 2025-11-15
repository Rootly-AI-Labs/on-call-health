import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Loader2 } from "lucide-react"

interface JiraDisconnectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  isDisconnecting: boolean
  onConfirmDisconnect: () => void
}

export function JiraDisconnectDialog({
  open,
  onOpenChange,
  isDisconnecting,
  onConfirmDisconnect
}: JiraDisconnectDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Disconnect Jira Integration</DialogTitle>
          <DialogDescription>
            Are you sure you want to disconnect your Jira integration?
            This will remove access to your Jira workload data, issue tracking metrics, and project information.
            You'll need to reconnect to use Jira features again.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isDisconnecting}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirmDisconnect}
            disabled={isDisconnecting}
          >
            {isDisconnecting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Disconnecting...
              </>
            ) : (
              "Disconnect Jira"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
