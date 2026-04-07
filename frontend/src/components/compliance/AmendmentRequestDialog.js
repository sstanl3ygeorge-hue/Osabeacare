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
  // General document issues
  {
    code: 'unclear',
    label: 'Document is unclear/unreadable',
    description: 'The document image is blurry, cropped, or difficult to read.',
    applies_to: ['all']
  },
  {
    code: 'wrong_type',
    label: 'Wrong document type',
    description: 'The uploaded document is not an acceptable type for this requirement.',
    applies_to: ['all']
  },
  {
    code: 'name_mismatch',
    label: 'Name doesn\'t match profile',
    description: 'The name on the document doesn\'t match the employee\'s profile.',
    applies_to: ['all']
  },
  
  // Address-specific
  {
    code: 'address_mismatch',
    label: 'Address doesn\'t match profile',
    description: 'The address on the document doesn\'t match the declared address.',
    applies_to: ['proof_of_address']
  },
  {
    code: 'document_too_old',
    label: 'Document is too old',
    description: 'The document is older than required (bank statement >6 months, utility bill >6 months).',
    applies_to: ['proof_of_address']
  },
  
  // RTW-specific issues
  {
    code: 'share_code_invalid',
    label: 'Share code is invalid/expired',
    description: 'The share code entered is invalid, expired, or cannot be verified on GOV.UK.',
    applies_to: ['right_to_work']
  },
  {
    code: 'share_code_mismatch',
    label: 'Share code doesn\'t match this person',
    description: 'The Home Office check shows this share code belongs to a different person.',
    applies_to: ['right_to_work']
  },
  {
    code: 'home_office_check_failed',
    label: 'Home Office online check failed',
    description: 'Unable to verify right to work via the Home Office Employer Checking Service.',
    applies_to: ['right_to_work']
  },
  {
    code: 'passport_photo_mismatch',
    label: 'Passport photo doesn\'t match applicant',
    description: 'The photo in the passport/ID does not appear to match the applicant.',
    applies_to: ['right_to_work', 'identity']
  },
  {
    code: 'document_expired',
    label: 'Document has expired',
    description: 'The passport, visa, or BRP has expired and cannot be accepted.',
    applies_to: ['right_to_work', 'identity']
  },
  {
    code: 'rtw_no_permission',
    label: 'No right to work found',
    description: 'The Home Office check indicates this person does not have permission to work in the UK.',
    applies_to: ['right_to_work']
  },
  
  // Identity-specific
  {
    code: 'id_photo_poor_quality',
    label: 'ID photo is poor quality',
    description: 'The photo on the ID document is obscured, damaged, or too poor quality to verify.',
    applies_to: ['identity']
  },
  
  // DBS-specific
  {
    code: 'dbs_certificate_mismatch',
    label: 'DBS certificate details don\'t match',
    description: 'The name or DOB on the DBS certificate doesn\'t match the employee\'s details.',
    applies_to: ['dbs']
  },
  {
    code: 'dbs_update_service_failed',
    label: 'DBS Update Service check failed',
    description: 'Unable to verify DBS status via the Update Service. A new DBS may be required.',
    applies_to: ['dbs']
  },
  
  // Suspected fraud (serious)
  {
    code: 'suspected_fraud',
    label: '⚠️ Suspected fraudulent document',
    description: 'The document appears to be altered, fake, or fraudulent. This will be flagged for review.',
    applies_to: ['all'],
    severity: 'critical'
  },
  
  // Other
  {
    code: 'other',
    label: 'Other reason',
    description: 'Specify a custom reason below.',
    applies_to: ['all']
  }
];

export default function AmendmentRequestDialog({
  isOpen,
  onClose,
  documentId,
  documentName,
  employeeName,
  requirementType = 'all', // 'right_to_work', 'dbs', 'identity', 'proof_of_address', 'all'
  onAmendmentRequested
}) {
  const [selectedReason, setSelectedReason] = useState('');
  const [customReason, setCustomReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [confirmFraud, setConfirmFraud] = useState(false);
  
  // Filter reasons based on requirement type
  const filteredReasons = AMENDMENT_REASONS.filter(reason => 
    reason.applies_to.includes('all') || reason.applies_to.includes(requirementType)
  );
  
  const selectedReasonData = AMENDMENT_REASONS.find(r => r.code === selectedReason);
  const isFraudSelected = selectedReason === 'suspected_fraud';
  
  const handleSubmit = async () => {
    if (!selectedReason) {
      toast.error('Please select a reason for the amendment request');
      return;
    }
    
    if (selectedReason === 'other' && !customReason.trim()) {
      toast.error('Please provide details for the amendment request');
      return;
    }
    
    if (isFraudSelected && !confirmFraud) {
      toast.error('Please confirm fraud reporting - this is a serious action');
      return;
    }
    
    setSubmitting(true);
    try {
      const response = await axios.post(`${API}/verification/request-amendment`, {
        document_id: documentId,
        reason_code: selectedReason,
        reason_details: selectedReason === 'other' ? customReason : undefined,
        requirement_type: requirementType,
        is_fraud_report: isFraudSelected
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
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg bg-white max-h-[85vh] overflow-y-auto">
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
            <RadioGroup value={selectedReason} onValueChange={(val) => {
              setSelectedReason(val);
              setConfirmFraud(false); // Reset fraud confirmation
            }}>
              {filteredReasons.map(reason => (
                <div 
                  key={reason.code}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedReason === reason.code 
                      ? reason.severity === 'critical' 
                        ? 'border-red-500 bg-red-50' 
                        : 'border-primary bg-primary/5' 
                      : reason.severity === 'critical'
                        ? 'border-red-200 hover:border-red-300 bg-red-50/30'
                        : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => {
                    setSelectedReason(reason.code);
                    setConfirmFraud(false);
                  }}
                >
                  <RadioGroupItem 
                    value={reason.code} 
                    id={reason.code}
                    data-testid={`reason-${reason.code}`}
                  />
                  <div className="flex-1">
                    <Label 
                      htmlFor={reason.code} 
                      className={`text-sm font-medium cursor-pointer ${
                        reason.severity === 'critical' ? 'text-red-700' : ''
                      }`}
                    >
                      {reason.label}
                    </Label>
                    <p className={`text-xs mt-0.5 ${
                      reason.severity === 'critical' ? 'text-red-600' : 'text-gray-500'
                    }`}>
                      {reason.description}
                    </p>
                  </div>
                </div>
              ))}
            </RadioGroup>
          </div>
          
          {/* Fraud Warning */}
          {isFraudSelected && (
            <div className="p-4 bg-red-100 border border-red-300 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="space-y-2">
                  <p className="text-sm font-semibold text-red-800">
                    This is a serious allegation
                  </p>
                  <p className="text-xs text-red-700">
                    Reporting suspected fraud will:
                  </p>
                  <ul className="text-xs text-red-700 list-disc ml-4 space-y-1">
                    <li>Flag this employee for immediate review</li>
                    <li>Create an audit trail for CQC/legal purposes</li>
                    <li>Block their onboarding until resolved</li>
                    <li>May require reporting to authorities</li>
                  </ul>
                  <div className="flex items-center gap-2 mt-3 pt-2 border-t border-red-200">
                    <input 
                      type="checkbox"
                      id="confirm-fraud"
                      checked={confirmFraud}
                      onChange={(e) => setConfirmFraud(e.target.checked)}
                      className="w-4 h-4 text-red-600"
                    />
                    <label htmlFor="confirm-fraud" className="text-xs text-red-800 font-medium cursor-pointer">
                      I confirm this document appears fraudulent and needs investigation
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}
          
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
