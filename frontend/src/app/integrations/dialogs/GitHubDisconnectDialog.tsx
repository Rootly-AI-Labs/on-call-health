import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Loader2 } from "lucide-react"

interface GitHubDisconnectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  isDisconnecting: boolean
  onConfirmDisconnect: () => void
}

export function GitHubDisconnectDialog({
  open,
  onOpenChange,
  isDisconnecting,
  onConfirmDisconnect
}: GitHubDisconnectDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Disconnect GitHub Integration</DialogTitle>
          <DialogDescription>
            Are you sure you want to disconnect your GitHub integration?
            This will remove access to your GitHub data and you'll need to reconnect to use GitHub features again.
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
              "Disconnect GitHub"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
