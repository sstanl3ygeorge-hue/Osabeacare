/**
 * AmendmentRequestDialog - Request employee to re-upload/fix document
 * 
 * Part of the Smart Verification System amendment loop.
 * Admin selects a reason, employee gets notified, and can re-upload.
 */

import { useState } from 'react';
import axios from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';
import { toast } from 'sonner';
import { AlertTriangle, Loader2, Send } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AMENDMENT_REASONS = [
  {
    code: 'address_mismatch',
    label: 'Address doesn\'t match profile',
    description: 'The address on the document doesn\'t match the declared address.'
  },
  {
    code: 'document_too_old',
    label: 'Document is too old',
    description: 'The document is older than 6 months. A more recent document is required.'
  },
  {
    code: 'name_mismatch',
    label: 'Name doesn\'t match',
    description: 'The name on the document doesn\'t match the employee\'s profile.'
  },
  {
    code: 'unclear',
    label: 'Document is unclear/unreadable',
    description: 'The document image is blurry, cropped, or difficult to read.'
  },
  {
    code: 'wrong_type',
    label: 'Wrong document type',
    description: 'The uploaded document is not an acceptable type for this requirement.'
  },
  {
    code: 'other',
    label: 'Other reason',
    description: 'Specify a custom reason below.'
  }
];

export default function AmendmentRequestDialog({
  isOpen,
  onClose,
  documentId,
  documentName,
  employeeName,
  onAmendmentRequested
}) {
  const [selectedReason, setSelectedReason] = useState('');
  const [customReason, setCustomReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  
  const handleSubmit = async () => {
    if (!selectedReason) {
      toast.error('Please select a reason for the amendment request');
      return;
    }
    
    if (selectedReason === 'other' && !customReason.trim()) {
      toast.error('Please provide details for the amendment request');
      return;
    }
    
    setSubmitting(true);
    try {
      const response = await axios.post(`${API}/verification/request-amendment`, {
        document_id: documentId,
        reason_code: selectedReason,
        reason_details: selectedReason === 'other' ? customReason : undefined
      });
      
      if (response.data.success) {
        toast.success('Amendment requested', {
          description: `${employeeName} will be notified to re-upload their ${documentName}.`
        });
        onAmendmentRequested?.();
        onClose();
      }
    } catch (error) {
      console.error('Error requesting amendment:', error);
      toast.error('Failed to request amendment', {
        description: error.response?.data?.detail || 'Please try again'
      });
    } finally {
      setSubmitting(false);
    }
  };
  
  const selectedReasonData = AMENDMENT_REASONS.find(r => r.code === selectedReason);
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg bg-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            Request Document Amendment
          </DialogTitle>
          <DialogDescription>
            Request {employeeName} to re-upload their {documentName}. 
            They will receive an email notification with the reason.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-3">
            <Label className="text-sm font-medium">Select Reason *</Label>
            <RadioGroup value={selectedReason} onValueChange={setSelectedReason}>
              {AMENDMENT_REASONS.map(reason => (
                <div 
                  key={reason.code}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedReason === reason.code 
                      ? 'border-primary bg-primary/5' 
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setSelectedReason(reason.code)}
                >
                  <RadioGroupItem 
                    value={reason.code} 
                    id={reason.code}
                    data-testid={`reason-${reason.code}`}
                  />
                  <div className="flex-1">
                    <Label 
                      htmlFor={reason.code} 
                      className="text-sm font-medium cursor-pointer"
                    >
                      {reason.label}
                    </Label>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {reason.description}
                    </p>
                  </div>
                </div>
              ))}
            </RadioGroup>
          </div>
          
          {selectedReason === 'other' && (
            <div className="space-y-2">
              <Label htmlFor="custom-reason" className="text-sm font-medium">
                Specify Reason *
              </Label>
              <Textarea
                id="custom-reason"
                value={customReason}
                onChange={(e) => setCustomReason(e.target.value)}
                placeholder="Please describe what the employee needs to correct..."
                rows={3}
                data-testid="custom-reason-input"
              />
            </div>
          )}
          
          {selectedReasonData && selectedReason !== 'other' && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <p className="text-sm text-yellow-800">
                <strong>Message to employee:</strong><br />
                {selectedReasonData.description}
              </p>
            </div>
          )}
        </div>
        
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting || !selectedReason || (selectedReason === 'other' && !customReason.trim())}
            className="bg-yellow-600 hover:bg-yellow-700"
            data-testid="submit-amendment-btn"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Request Amendment
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
