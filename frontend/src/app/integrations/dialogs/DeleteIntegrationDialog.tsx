import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Loader2 } from "lucide-react"
import { Integration } from "../types"

interface DeleteIntegrationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  integration: Integration | null
  isDeleting: boolean
  onConfirmDelete: () => void
  onCancel: () => void
}

export function DeleteIntegrationDialog({
  open,
  onOpenChange,
  integration,
  isDeleting,
  onConfirmDelete,
  onCancel
}: DeleteIntegrationDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Integration</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete "{integration?.name}"?
            This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={onCancel}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirmDelete}
            disabled={isDeleting}
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Deleting...
              </>
            ) : (
              "Delete Integration"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
