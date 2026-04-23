import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';
import { toast } from 'sonner';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  FileText,
  Loader2,
  Eye,
  ExternalLink
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * EvidenceReviewDialog - Lightweight modal for reviewing uploaded evidence files
 * 
 * This is the FIRST step in the verification workflow:
 * 1. Evidence Review (this dialog) - Accept/Reject/Mark uploaded in error
 * 2. Record Check - Formal compliance verification with method, date, outcome
 * 
 * Business Rule: A requirement is fully verified when:
 * - At least one evidence file is ACCEPTED
 * - AND a Record Check has been completed
 */
export default function EvidenceReviewDialog({
  isOpen,
  onClose,
  file,
  employeeId,
  requirementKey,
  requirementLabel,
  onReviewComplete,
  onOpenRecordCheck // Optional: callback to open Record Check with this file attached
}) {
  const { token } = useAuth();
  const [reviewDecision, setReviewDecision] = useState('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Review decision options
  const REVIEW_OPTIONS = [
    {
      value: 'accept',
      label: 'Accept File',
      description: 'File meets requirements and is suitable for compliance',
      icon: CheckCircle,
      iconColor: 'text-emerald-600'
    },
    {
      value: 'reject',
      label: 'Reject File',
      description: 'File does not meet requirements (wrong document, unreadable, etc.)',
      icon: XCircle,
      iconColor: 'text-red-600',
      requiresNotes: true
    },
    {
      value: 'uploaded_in_error',
      label: 'Mark Uploaded in Error',
      description: 'File was uploaded by mistake and should be removed from record',
      icon: AlertTriangle,
      iconColor: 'text-amber-600',
      requiresNotes: true
    }
  ];

  const selectedOption = REVIEW_OPTIONS.find(o => o.value === reviewDecision);

  // Handle submit
  const handleSubmit = async () => {
    if (!reviewDecision) {
      toast.error('Please select a review decision');
      return;
    }

    if (selectedOption?.requiresNotes && (!notes.trim() || notes.trim().length < 10)) {
      toast.error('Please provide a reason (at least 10 characters)');
      return;
    }

    if (!file?.file_id) {
      toast.error('File ID is missing');
      return;
    }

    setIsSubmitting(true);
    try {
      let endpoint = '';
      let payload = {};

      switch (reviewDecision) {
        case 'accept':
          endpoint = `${API}/employee-documents/${file.file_id}/verify`;
          payload = { notes: notes.trim() || undefined };
          break;
        case 'reject':
          endpoint = `${API}/employee-documents/${file.file_id}/reject`;
          payload = { reason: notes.trim() };
          break;
        case 'uploaded_in_error':
          endpoint = `${API}/employee-documents/${file.file_id}/mark-uploaded-in-error`;
          payload = { reason: notes.trim() };
          break;
        default:
          throw new Error('Invalid review decision');
      }

      await axios.post(endpoint, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });

      const messages = {
        accept: 'Evidence accepted',
        reject: 'Evidence rejected',
        uploaded_in_error: 'Evidence marked as uploaded in error'
      };
      toast.success(messages[reviewDecision]);

      // Reset form
      setReviewDecision('');
      setNotes('');
      
      // Notify parent
      if (onReviewComplete) {
        onReviewComplete(reviewDecision);
      }
      
      onClose();
    } catch (err) {
      console.error('Evidence review failed:', err);
      toast.error(err.response?.data?.detail || 'Failed to submit review');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Review & Record Check
  const handleReviewAndRecordCheck = async () => {
    // First accept the file
    if (!file?.file_id) {
      toast.error('File ID is missing');
      return;
    }

    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/employee-documents/${file.file_id}/verify`,
        { notes: notes.trim() || 'Accepted as part of Review & Record Check' },
        { headers: { Authorization: `Bearer ${token}` }
      });

      toast.success('Evidence accepted');
      
      // Open Record Check dialog with this file
      if (onOpenRecordCheck) {
        onOpenRecordCheck(file);
      }
      
      onClose();
    } catch (err) {
      console.error('Review & Record Check failed:', err);
      toast.error(err.response?.data?.detail || 'Failed to accept file');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Preview file
  const handlePreview = () => {
    if (file?.file_url) {
      window.open(file.file_url, '_blank');
    }
  };

  // Get file status badge
  const getStatusBadge = () => {
    const status = file?.status || file?.verification_status || 'pending';
    
    const statusConfig = {
      pending: { label: 'Awaiting admin review', className: 'bg-amber-100 text-amber-800 border-amber-200' },
      awaiting_review: { label: 'Awaiting admin review', className: 'bg-amber-100 text-amber-800 border-amber-200' },
      verified: { label: 'Accepted', className: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
      accepted: { label: 'Accepted', className: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
      rejected: { label: 'Rejected', className: 'bg-red-100 text-red-800 border-red-200' },
      uploaded_in_error: { label: 'Uploaded in Error', className: 'bg-gray-100 text-gray-800 border-gray-200' },
      superseded: { label: 'Superseded', className: 'bg-gray-100 text-gray-600 border-gray-200' }
    };

    const config = statusConfig[status] || statusConfig.pending;
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg" data-testid="evidence-review-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-teal-600" />
            Review Evidence
          </DialogTitle>
          <DialogDescription>
            Review the uploaded file for {requirementLabel || requirementKey}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* File Info */}
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {file?.filename || file?.original_filename || 'Unknown file'}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Uploaded {file?.uploaded_at?.slice(0, 10) || 'Unknown date'}
                </p>
              </div>
              <div className="flex items-center gap-2 ml-3">
                {getStatusBadge()}
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handlePreview}
                  className="h-8 px-2"
                  data-testid="preview-file-btn"
                >
                  <Eye className="h-4 w-4 mr-1" />
                  View
                  <ExternalLink className="h-3 w-3 ml-1" />
                </Button>
              </div>
            </div>
          </div>

          {/* Review Decision */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Review Decision *</Label>
            <RadioGroup
              value={reviewDecision}
              onValueChange={setReviewDecision}
              className="space-y-2"
            >
              {REVIEW_OPTIONS.map(option => {
                const Icon = option.icon;
                return (
                  <label
                    key={option.value}
                    className={`
                      flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors
                      ${reviewDecision === option.value 
                        ? 'border-teal-500 bg-teal-50' 
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }
                    `}
                    data-testid={`review-option-${option.value}`}
                  >
                    <RadioGroupItem value={option.value} className="mt-0.5" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Icon className={`h-4 w-4 ${option.iconColor}`} />
                        <span className="font-medium text-sm">{option.label}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">{option.description}</p>
                    </div>
                  </label>
                );
              })}
            </RadioGroup>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">
              Notes {selectedOption?.requiresNotes ? '*' : '(optional)'}
            </Label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={
                selectedOption?.requiresNotes
                  ? 'Please provide a reason for this decision (required)'
                  : 'Add any notes about this review (optional)'
              }
              className="h-20 resize-none rounded-lg"
              data-testid="review-notes-input"
            />
            {selectedOption?.requiresNotes && notes.trim().length > 0 && notes.trim().length < 10 && (
              <p className="text-xs text-amber-600">Minimum 10 characters required</p>
            )}
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          {/* Review & Record Check button for document-heavy requirements */}
          {onOpenRecordCheck && ['right_to_work', 'dbs', 'identity', 'proof_of_address'].includes(requirementKey) && (
            <Button
              variant="outline"
              onClick={handleReviewAndRecordCheck}
              disabled={isSubmitting}
              className="w-full sm:w-auto"
              data-testid="review-and-record-check-btn"
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4 mr-1.5" />
              )}
              Accept & Record Check
            </Button>
          )}
          
          <div className="flex gap-2 w-full sm:w-auto sm:ml-auto">
            <Button
              variant="ghost"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1 sm:flex-none"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting || !reviewDecision}
              className="flex-1 sm:flex-none"
              data-testid="submit-review-btn"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                  Submitting...
                </>
              ) : (
                'Submit Review'
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
