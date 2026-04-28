import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { toast } from 'sonner';
import { Loader2, Mail, Send, Calendar } from 'lucide-react';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_BASE_URL;

// Agreement types config
const AGREEMENT_TYPES = {
  contract_acceptance: {
    type: 'contract_acceptance',
    title: 'Contract Acceptance',
    defaultVersion: 'Contract-v1',
    description: 'Employment contract acknowledgement'
  },
  handbook_acknowledgement: {
    type: 'handbook_acknowledgement',
    title: 'Handbook Acknowledgement',
    defaultVersion: 'Handbook-2026.01',
    description: 'Company handbook acknowledgement'
  }
};

/**
 * SendAgreementDialog - Dialog for sending an agreement form to employee via secure link
 */
export default function SendAgreementDialog({
  open,
  onClose,
  employeeId,
  employeeEmail,
  employeeName,
  agreementKey,
  agreementTitle,
  onComplete
}) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    version_label: '',
    custom_message: '',
    due_days: 14
  });
  
  const { token } = useAuth();

  // Get agreement config
  const agreementConfig = AGREEMENT_TYPES[agreementKey] || {
    type: agreementKey,
    title: agreementTitle || 'Agreement',
    defaultVersion: 'v1',
    description: 'Agreement form'
  };

  // Set default version on open
  useEffect(() => {
    if (open) {
      setFormData(prev => ({
        ...prev,
        version_label: agreementConfig.defaultVersion
      }));
    }
  }, [open, agreementConfig.defaultVersion]);

  const handleSubmit = async () => {
    if (!formData.version_label) {
      toast.error('Please enter the version label');
      return;
    }

    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/agreements/send`,
        {
          agreement_type: agreementConfig.type,
          version_label: formData.version_label,
          custom_message: formData.custom_message || null,
          due_days: formData.due_days
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      toast.success(`${agreementConfig.title} sent to ${employeeName || 'employee'}`);
      if (onComplete) onComplete();
      handleClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send agreement form');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setFormData({
      version_label: agreementConfig.defaultVersion,
      custom_message: '',
      due_days: 14
    });
    if (onClose) onClose();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-white sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <Mail className="h-5 w-5 text-blue-600" />
            Send {agreementConfig.title}
          </DialogTitle>
          <DialogDescription>
            Send a secure link to the employee to complete the {agreementConfig.title.toLowerCase()}.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Recipient Info */}
          <div className="p-3 bg-blue-50 rounded-lg">
            <div className="flex items-center gap-2">
              <Send className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-900">
                Sending to: {employeeName || 'Employee'}
              </span>
            </div>
            {employeeEmail && (
              <p className="text-xs text-blue-700 mt-1 ml-6">{employeeEmail}</p>
            )}
          </div>

          {/* Version Label */}
          <div className="space-y-2">
            <Label>Version Label *</Label>
            <Input
              value={formData.version_label}
              onChange={(e) => setFormData(prev => ({ ...prev, version_label: e.target.value }))}
              placeholder={agreementConfig.defaultVersion}
              className="rounded-lg"
            />
            <p className="text-xs text-text-muted">
              e.g., "Contract-v3", "Handbook-2026.04"
            </p>
          </div>

          {/* Due Days */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-text-muted" />
              Due in (days)
            </Label>
            <Input
              type="number"
              min="1"
              max="90"
              value={formData.due_days}
              onChange={(e) => setFormData(prev => ({ ...prev, due_days: parseInt(e.target.value) || 14 }))}
              className="rounded-lg w-24"
            />
            <p className="text-xs text-text-muted">
              How many days the employee has to complete the form
            </p>
          </div>

          {/* Custom Message */}
          <div className="space-y-2">
            <Label>Custom Message (optional)</Label>
            <Textarea
              value={formData.custom_message}
              onChange={(e) => setFormData(prev => ({ ...prev, custom_message: e.target.value }))}
              placeholder="Add a personal message to the employee..."
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
            disabled={isSubmitting || !formData.version_label}
            className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Send Form
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

