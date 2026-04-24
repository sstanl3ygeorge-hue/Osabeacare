import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';

export default function LifecycleReasonDialog({
  open,
  onOpenChange,
  actionLabel,
  subjectLabel,
  minLength = 5,
  isSubmitting = false,
  onConfirm
}) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) {
      setReason('');
      setError('');
    }
  }, [open]);

  const handleSubmit = async () => {
    const trimmed = reason.trim();
    if (trimmed.length < minLength) {
      setError(`Please provide a reason of at least ${minLength} characters`);
      return;
    }
    setError('');
    await onConfirm(trimmed);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{actionLabel}</DialogTitle>
          <DialogDescription>
            {subjectLabel ? `Provide a reason for ${actionLabel.toLowerCase()} ${subjectLabel}.` : `Provide a reason for ${actionLabel.toLowerCase()}.`}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2 py-2">
          <Label>Reason</Label>
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Enter reason"
            className="min-h-[100px]"
            disabled={isSubmitting}
          />
          {error ? <p className="text-xs text-red-600">{error}</p> : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            Confirm
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
