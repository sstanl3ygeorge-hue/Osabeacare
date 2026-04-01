import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { XCircle, Loader2 } from 'lucide-react';

/**
 * RejectFormDialog - Dialog for rejecting a form submission with a reason
 */
export default function RejectFormDialog({
  isOpen,
  onClose,
  onConfirm,
  formName = 'form',
  loading = false
}) {
  const [reason, setReason] = useState('');
  
  const handleConfirm = () => {
    if (!reason.trim()) return;
    onConfirm(reason);
    setReason('');
  };
  
  const handleClose = () => {
    setReason('');
    onClose();
  };
  
  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md" data-testid="reject-form-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <XCircle className="h-5 w-5" />
            Reject {formName}
          </DialogTitle>
          <DialogDescription>
            Please provide a reason for rejecting this submission. The employee will need to resubmit.
          </DialogDescription>
        </DialogHeader>
        
        <div className="py-4">
          <Label htmlFor="rejection-reason" className="text-sm font-medium">
            Rejection Reason <span className="text-red-500">*</span>
          </Label>
          <Textarea
            id="rejection-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Enter the reason for rejection..."
            rows={4}
            className="mt-2"
            data-testid="rejection-reason-input"
          />
        </div>
        
        <DialogFooter className="flex gap-2">
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={!reason.trim() || loading}
            data-testid="confirm-reject-btn"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
            ) : (
              <XCircle className="h-4 w-4 mr-1.5" />
            )}
            Reject Submission
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
