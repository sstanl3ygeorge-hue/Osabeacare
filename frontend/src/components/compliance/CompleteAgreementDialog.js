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
import { Loader2, FileSignature, Phone, Edit } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Agreement types
const AGREEMENT_TYPES = {
  contract_acceptance: {
    type: 'contract_acceptance',
    title: 'Contract Acceptance',
    defaultVersion: 'Contract-v1'
  },
  handbook_acknowledgement: {
    type: 'handbook_acknowledgement',
    title: 'Handbook Acknowledgement',
    defaultVersion: 'Handbook-2026.01'
  }
};

// Completion modes
const COMPLETION_MODES = [
  { value: 'admin_assisted', label: 'Admin-Assisted', description: 'Admin filling on employee\'s behalf', icon: Edit },
  { value: 'phone_assisted', label: 'Phone-Assisted', description: 'Recorded during phone call with employee', icon: Phone }
];

/**
 * CompleteAgreementDialog - Dialog for completing an agreement acknowledgement
 * 
 * Supports:
 * - admin_assisted: Admin fills on employee's behalf (NOT for contracts)
 * - phone_assisted: Admin records during phone call
 * 
 * CQC COMPLIANCE NOTE:
 * - Contracts MUST be signed by the worker themselves (digital signature)
 * - Admin cannot sign contracts on behalf of workers
 * - Only handbook acknowledgements can be admin-assisted
 */
export default function CompleteAgreementDialog({
  open,
  onClose,
  employeeId,
  agreementKey,
  agreementTitle,
  mode = 'admin_assisted', // 'admin_assisted' or 'phone_assisted'
  onComplete
}) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    version_acknowledged: '',
    call_note: ''
  });
  
  const { token } = useAuth();

  // CQC COMPLIANCE: Block admin signing of contracts
  const isContract = agreementKey === 'contract_acceptance';
  
  // Get agreement config
  const agreementConfig = AGREEMENT_TYPES[agreementKey] || {
    type: agreementKey,
    title: agreementTitle || 'Agreement',
    defaultVersion: 'v1'
  };

  // Set default version on open
  useState(() => {
    if (open && !formData.version_acknowledged) {
      setFormData(prev => ({
        ...prev,
        version_acknowledged: agreementConfig.defaultVersion
      }));
    }
  }, [open]);

  const handleSubmit = async () => {
    if (!formData.version_acknowledged) {
      toast.error('Please enter the version being acknowledged');
      return;
    }

    if (mode === 'phone_assisted' && !formData.call_note) {
      toast.error('Please add a call note for phone-assisted completion');
      return;
    }

    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/agreements/complete`,
        {
          agreement_type: agreementConfig.type,
          completion_mode: mode,
          version_acknowledged: formData.version_acknowledged,
          call_note: mode === 'phone_assisted' ? formData.call_note : null
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      toast.success(`${agreementConfig.title} completed`);
      if (onComplete) onComplete();
      handleClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to complete agreement');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setFormData({
      version_acknowledged: agreementConfig.defaultVersion,
      call_note: ''
    });
    if (onClose) onClose();
  };

  const ModeIcon = mode === 'phone_assisted' ? Phone : Edit;

  // CQC COMPLIANCE: Contracts MUST be signed by worker - show warning
  if (isContract) {
    return (
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="bg-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-red-600">
              <FileSignature className="h-5 w-5" />
              Contract Requires Worker Signature
            </DialogTitle>
            <DialogDescription className="text-red-600">
              Worker signature required
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800 font-medium mb-2">
                Contracts cannot be signed by admin on behalf of workers.
              </p>
              <p className="text-sm text-red-700">
                The worker must sign their employment contract themselves using their digital signature in the Worker Portal.
              </p>
              <p className="text-sm text-red-700 mt-2">
                Please send a reminder to the worker to sign their contract.
              </p>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-white sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <ModeIcon className="h-5 w-5 text-primary" />
            Complete {agreementConfig.title}
          </DialogTitle>
          <DialogDescription>
            {mode === 'phone_assisted' 
              ? 'Record agreement acknowledgement from phone call with employee.'
              : 'Complete agreement on behalf of the employee.'
            }
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Completion Mode Display */}
          <div className="p-3 bg-[#F8FAFA] rounded-lg">
            <div className="flex items-center gap-2">
              <ModeIcon className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">
                {mode === 'phone_assisted' ? 'Phone-Assisted Completion' : 'Admin-Assisted Completion'}
              </span>
            </div>
            <p className="text-xs text-text-muted mt-1">
              {mode === 'phone_assisted' 
                ? 'Employee verbally confirmed acknowledgement during call'
                : 'Admin completing on employee\'s behalf with their knowledge'
              }
            </p>
          </div>

          {/* Version */}
          <div className="space-y-2">
            <Label>Version Being Acknowledged *</Label>
            <Input
              value={formData.version_acknowledged}
              onChange={(e) => setFormData(prev => ({ ...prev, version_acknowledged: e.target.value }))}
              placeholder={agreementConfig.defaultVersion}
              className="rounded-lg"
            />
            <p className="text-xs text-text-muted">
              e.g., "Contract-v3", "Handbook-2026.04"
            </p>
          </div>

          {/* Call Note (for phone-assisted) */}
          {mode === 'phone_assisted' && (
            <div className="space-y-2">
              <Label>Call Note *</Label>
              <Textarea
                value={formData.call_note}
                onChange={(e) => setFormData(prev => ({ ...prev, call_note: e.target.value }))}
                placeholder="Record details of the call and verbal confirmation..."
                className="rounded-lg min-h-[100px]"
              />
              <p className="text-xs text-text-muted">
                Document when the call took place and what was confirmed
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleClose} className="rounded-xl">
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !formData.version_acknowledged || (mode === 'phone_assisted' && !formData.call_note)}
            className="bg-primary hover:bg-primary-hover text-white rounded-xl"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <FileSignature className="h-4 w-4 mr-2" />
                Complete Agreement
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
