import { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { AlertTriangle, Edit, Save } from 'lucide-react';

/**
 * EditReasonDialog - Universal dialog for editing any field with reason logging
 * 
 * CQC Compliance: Every edit must have a reason logged
 * Audit Trail: Who, when, old value, new value, reason
 */
export default function EditReasonDialog({
  open,
  onClose,
  title = "Edit Record",
  description = "Make changes to this record. A reason is required for the audit trail.",
  children,  // The form fields to edit
  onSave,
  isLoading = false,
  isCritical = false  // For supersede-type changes
}) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  const handleSave = () => {
    if (!reason.trim() || reason.trim().length < 10) {
      setError('Please provide a reason for this change (minimum 10 characters)');
      return;
    }
    setError('');
    onSave(reason.trim());
  };

  const handleClose = () => {
    setReason('');
    setError('');
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-white sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            {isCritical ? (
              <AlertTriangle className="h-5 w-5 text-amber-500" />
            ) : (
              <Edit className="h-5 w-5 text-primary" />
            )}
            {title}
          </DialogTitle>
          <DialogDescription>
            {description}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Form fields passed as children */}
          {children}

          {/* Reason for change - REQUIRED */}
          <div className="space-y-2 pt-4 border-t border-gray-200">
            <Label className="text-sm font-medium flex items-center gap-1">
              Reason for Change <span className="text-red-500">*</span>
            </Label>
            <Textarea
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (error) setError('');
              }}
              placeholder="Explain why this change is being made (e.g., 'Corrected spelling error in name', 'Updated end date per employee request')"
              className="min-h-[80px] rounded-lg"
              data-testid="edit-reason-input"
            />
            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}
            <p className="text-xs text-gray-500">
              This reason will be logged in the audit trail.
            </p>
          </div>

          {isCritical && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-sm text-amber-800">
                <strong>Note:</strong> This is a critical change. The original record will be preserved for audit purposes.
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button 
            onClick={handleSave} 
            disabled={isLoading || !reason.trim()}
            className="bg-primary hover:bg-primary-hover text-white"
            data-testid="save-edit-btn"
          >
            {isLoading ? (
              <>Saving...</>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
