/**
 * AuditReasonDialog - Reusable dialog to capture reason for admin changes
 * 
 * Used for CQC compliance: Every admin change to employee records must be logged
 * with who, what, when, and why.
 */

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
import { Badge } from '../ui/badge';
import { AlertTriangle, Loader2, FileEdit } from 'lucide-react';

export default function AuditReasonDialog({
  isOpen,
  onClose,
  onConfirm,
  title = "Reason for Change",
  description = "This change will be logged in the audit trail.",
  fieldName = "field",
  oldValue = "",
  newValue = "",
  isLoading = false,
  minReasonLength = 10
}) {
  const [reason, setReason] = useState('');

  const handleConfirm = async () => {
    if (reason.trim().length < minReasonLength) {
      return;
    }
    await onConfirm(reason.trim());
    setReason('');
  };

  const handleClose = () => {
    setReason('');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg" data-testid="audit-reason-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileEdit className="h-5 w-5 text-blue-600" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Change Preview */}
          <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg space-y-3">
            <p className="text-sm font-medium text-gray-700">
              You are changing: <span className="text-gray-900">{fieldName}</span>
            </p>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">From:</p>
                <div className="p-2 bg-red-50 border border-red-100 rounded text-sm text-red-800 break-all">
                  {oldValue || <span className="italic text-gray-400">(empty)</span>}
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">To:</p>
                <div className="p-2 bg-green-50 border border-green-100 rounded text-sm text-green-800 break-all">
                  {newValue || <span className="italic text-gray-400">(empty)</span>}
                </div>
              </div>
            </div>
          </div>

          {/* Reason Input */}
          <div>
            <label className="text-sm font-medium flex items-center gap-1 mb-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Reason for change <span className="text-red-500">*</span>
            </label>
            <Textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explain why this change is being made..."
              rows={3}
              className="resize-none"
              data-testid="audit-reason-input"
            />
            <p className="text-xs text-gray-500 mt-1">
              Minimum {minReasonLength} characters. This will be recorded in the CQC audit trail.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={isLoading || reason.trim().length < minReasonLength}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : null}
            Save Change
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


/**
 * AuditTrailDisplay - Shows audit history for an entity
 */
export function AuditTrailDisplay({ auditEntries = [], maxItems = 10 }) {
  if (!auditEntries || auditEntries.length === 0) {
    return (
      <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-center">
        <p className="text-sm text-gray-500">No audit history available</p>
      </div>
    );
  }

  const formatDate = (dateStr) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden" data-testid="audit-trail-display">
      <div className="bg-gray-100 px-4 py-2 border-b border-gray-200">
        <h4 className="text-sm font-semibold text-gray-700">AUDIT TRAIL</h4>
      </div>
      <div className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
        {auditEntries.slice(0, maxItems).map((entry, idx) => (
          <div key={idx} className="px-4 py-3 hover:bg-gray-50">
            <div className="flex items-start justify-between mb-1">
              <p className="text-sm font-medium text-gray-800">
                {formatDate(entry.created_at || entry.timestamp)}
              </p>
              <Badge variant="outline" className="text-xs">
                {entry.performed_by || entry.user || 'System'}
              </Badge>
            </div>
            
            <div className="space-y-1 text-sm">
              <div className="flex items-start gap-2">
                <span className="text-gray-500 min-w-20">Action:</span>
                <span className="text-gray-800">{entry.action || entry.action_type}</span>
              </div>
              
              {entry.details?.before && (
                <div className="flex items-start gap-2">
                  <span className="text-gray-500 min-w-20">Before:</span>
                  <span className="text-red-700">{String(entry.details.before)}</span>
                </div>
              )}
              
              {entry.details?.after && (
                <div className="flex items-start gap-2">
                  <span className="text-gray-500 min-w-20">After:</span>
                  <span className="text-green-700">{String(entry.details.after)}</span>
                </div>
              )}
              
              {(entry.details?.reason || entry.reason) && (
                <div className="flex items-start gap-2">
                  <span className="text-gray-500 min-w-20">Reason:</span>
                  <span className="text-gray-800 italic">"{entry.details?.reason || entry.reason}"</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      {auditEntries.length > maxItems && (
        <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-center">
          <p className="text-xs text-gray-500">
            Showing {maxItems} of {auditEntries.length} entries
          </p>
        </div>
      )}
    </div>
  );
}
