import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { Loader2, Shield, Calendar, FileText } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Check methods by type
const CHECK_METHODS = {
  right_to_work_check: [
    { value: 'share_code_online_check', label: 'Share Code Online Check', description: 'Online Home Office check using share code' },
    { value: 'manual_passport_check', label: 'Manual Passport Check', description: 'Manual verification of passport/visa' },
    { value: 'idsp_check', label: 'IDSP Check', description: 'Identity Service Provider check' },
    { value: 'ecs_check', label: 'ECS Check', description: 'Employer Checking Service' }
  ],
  dbs_status_check: [
    { value: 'update_service_check', label: 'DBS Update Service', description: 'Online Update Service status check' },
    { value: 'manual_certificate_review', label: 'Manual Certificate Review', description: 'Manual review of DBS certificate' }
  ],
  identity_verification: [
    { value: 'manual_id_verification', label: 'Manual ID Verification', description: 'Manual verification of ID documents' },
    { value: 'digital_id_check', label: 'Digital ID Check', description: 'Digital identity verification service' }
  ]
};

const CHECK_OUTCOMES = [
  { value: 'verified', label: 'Verified', color: 'text-green-600' },
  { value: 'failed', label: 'Failed', color: 'text-red-600' },
  { value: 'follow_up_required', label: 'Follow-up Required', color: 'text-amber-600' }
];

const SOURCE_STATUS_TYPES = [
  { value: 'digital_status', label: 'Digital Status (eVisa)' },
  { value: 'settled_status', label: 'Settled Status' },
  { value: 'pre_settled_status', label: 'Pre-Settled Status' },
  { value: 'passport_endorsement', label: 'Passport Endorsement' },
  { value: 'irish_passport', label: 'Irish Passport' },
  { value: 'other', label: 'Other' }
];

/**
 * RecordCheckDialog - Dialog for recording employer verification checks
 * 
 * Supports:
 * - Right to Work Check
 * - DBS Status Check
 * - Identity Verification
 */
export default function RecordCheckDialog({
  open,
  onClose,
  employeeId,
  checkType,
  onComplete
}) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    method: '',
    checked_at: new Date().toISOString().split('T')[0],
    outcome: 'verified',
    source_status_type: '',
    follow_up_due_at: '',
    review_due_at: '',
    certificate_number: '',
    notes: ''
  });
  
  const { token } = useAuth();

  // Get methods for this check type
  const methods = CHECK_METHODS[checkType] || [];
  
  // Get title based on check type
  const getTitle = () => {
    switch (checkType) {
      case 'right_to_work_check': return 'Record Right to Work Check';
      case 'dbs_status_check': return 'Record DBS Status Check';
      case 'identity_verification': return 'Record Identity Verification';
      default: return 'Record Check';
    }
  };

  // Get endpoint based on check type
  const getEndpoint = () => {
    switch (checkType) {
      case 'right_to_work_check': return `${API}/employees/${employeeId}/right-to-work/check`;
      case 'dbs_status_check': return `${API}/employees/${employeeId}/dbs/check`;
      case 'identity_verification': return `${API}/employees/${employeeId}/identity/check`;
      default: return null;
    }
  };

  const handleSubmit = async () => {
    const endpoint = getEndpoint();
    if (!endpoint) {
      toast.error('Invalid check type');
      return;
    }

    if (!formData.method) {
      toast.error('Please select a check method');
      return;
    }

    setIsSubmitting(true);
    try {
      // Build payload based on check type
      const payload = {
        method: formData.method,
        checked_at: formData.checked_at,
        outcome: formData.outcome,
        notes: formData.notes || null
      };

      // Add type-specific fields
      if (checkType === 'right_to_work_check') {
        payload.source_status_type = formData.source_status_type || null;
        payload.follow_up_due_at = formData.follow_up_due_at || null;
      }
      
      if (checkType === 'dbs_status_check') {
        payload.review_due_at = formData.review_due_at || null;
        payload.certificate_number = formData.certificate_number || null;
      }

      await axios.post(endpoint, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });

      toast.success('Check recorded successfully');
      if (onComplete) onComplete();
      handleClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to record check');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setFormData({
      method: '',
      checked_at: new Date().toISOString().split('T')[0],
      outcome: 'verified',
      source_status_type: '',
      follow_up_due_at: '',
      review_due_at: '',
      certificate_number: '',
      notes: ''
    });
    if (onClose) onClose();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-white sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            {getTitle()}
          </DialogTitle>
          <DialogDescription>
            Record the employer verification check outcome. This is the authoritative record for compliance readiness.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Method */}
          <div className="space-y-2">
            <Label>Check Method *</Label>
            <Select 
              value={formData.method} 
              onValueChange={(v) => setFormData(prev => ({ ...prev, method: v }))}
            >
              <SelectTrigger className="rounded-lg">
                <SelectValue placeholder="Select check method" />
              </SelectTrigger>
              <SelectContent>
                {methods.map(method => (
                  <SelectItem key={method.value} value={method.value}>
                    <div>
                      <div className="font-medium">{method.label}</div>
                      <div className="text-xs text-text-muted">{method.description}</div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Checked At */}
          <div className="space-y-2">
            <Label>Date Checked *</Label>
            <Input
              type="date"
              value={formData.checked_at}
              onChange={(e) => setFormData(prev => ({ ...prev, checked_at: e.target.value }))}
              className="rounded-lg"
            />
          </div>

          {/* Outcome */}
          <div className="space-y-2">
            <Label>Outcome *</Label>
            <Select 
              value={formData.outcome} 
              onValueChange={(v) => setFormData(prev => ({ ...prev, outcome: v }))}
            >
              <SelectTrigger className="rounded-lg">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHECK_OUTCOMES.map(outcome => (
                  <SelectItem key={outcome.value} value={outcome.value}>
                    <span className={outcome.color}>{outcome.label}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* RTW-specific: Source Status Type */}
          {checkType === 'right_to_work_check' && (
            <div className="space-y-2">
              <Label>Source Status Type</Label>
              <Select 
                value={formData.source_status_type} 
                onValueChange={(v) => setFormData(prev => ({ ...prev, source_status_type: v }))}
              >
                <SelectTrigger className="rounded-lg">
                  <SelectValue placeholder="Select status type" />
                </SelectTrigger>
                <SelectContent>
                  {SOURCE_STATUS_TYPES.map(type => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* RTW-specific: Follow-up Due */}
          {checkType === 'right_to_work_check' && (
            <div className="space-y-2">
              <Label>Follow-up Due Date</Label>
              <Input
                type="date"
                value={formData.follow_up_due_at}
                onChange={(e) => setFormData(prev => ({ ...prev, follow_up_due_at: e.target.value }))}
                className="rounded-lg"
              />
              <p className="text-xs text-text-muted">
                For time-limited permissions, set when the next check is due
              </p>
            </div>
          )}

          {/* DBS-specific: Certificate Number */}
          {checkType === 'dbs_status_check' && (
            <div className="space-y-2">
              <Label>Certificate Number</Label>
              <Input
                value={formData.certificate_number}
                onChange={(e) => setFormData(prev => ({ ...prev, certificate_number: e.target.value }))}
                placeholder="12-digit certificate number"
                className="rounded-lg"
              />
            </div>
          )}

          {/* DBS-specific: Review Due (NOT expiry) */}
          {checkType === 'dbs_status_check' && (
            <div className="space-y-2">
              <Label>Review Due Date</Label>
              <Input
                type="date"
                value={formData.review_due_at}
                onChange={(e) => setFormData(prev => ({ ...prev, review_due_at: e.target.value }))}
                className="rounded-lg"
              />
              <p className="text-xs text-text-muted">
                Internal policy date for next review (DBS certificates don't have a statutory expiry)
              </p>
            </div>
          )}

          {/* Notes */}
          <div className="space-y-2">
            <Label>Notes</Label>
            <Textarea
              value={formData.notes}
              onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
              placeholder="Any additional notes about this check..."
              className="rounded-lg min-h-[80px]"
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleClose} className="rounded-xl">
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !formData.method}
            className="bg-primary hover:bg-primary-hover text-white rounded-xl"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Shield className="h-4 w-4 mr-2" />
                Record Check
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
