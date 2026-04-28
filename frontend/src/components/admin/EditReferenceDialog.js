import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import EditReasonDialog from './EditReasonDialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

// Referee types per NHS/CQC requirements
const REFEREE_TYPES = [
  { value: 'professional', label: 'Professional (Line Manager/Supervisor)' },
  { value: 'character', label: 'Character Reference' },
  { value: 'personal', label: 'Personal Reference' }
];

/**
 * EditReferenceDialog - Edit a single reference with reason logging
 * 
 * Includes NHS-required fields:
 * - Referee type (Professional/Character/Personal)
 * - Period of supervision
 * - Direct supervisor checkbox
 * - Can contact before offer checkbox
 */
export default function EditReferenceDialog({
  open,
  onClose,
  employeeId,
  referenceId,
  currentData,
  onSuccess
}) {
  const { token } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    referee_name: '',
    referee_email: '',
    referee_phone: '',
    referee_organisation: '',
    referee_position: '',
    referee_relationship: '',
    referee_type: 'professional',
    period_of_supervision: '',
    is_direct_supervisor: false,
    can_contact_before_offer: true
  });

  useEffect(() => {
    if (currentData && open) {
      setFormData({
        referee_name: currentData.referee_name || '',
        referee_email: currentData.referee_email || '',
        referee_phone: currentData.referee_phone || '',
        referee_organisation: currentData.referee_organisation || currentData.organisation || '',
        referee_position: currentData.referee_position || currentData.position || '',
        referee_relationship: currentData.referee_relationship || currentData.relationship || '',
        referee_type: currentData.referee_type || 'professional',
        period_of_supervision: currentData.period_of_supervision || '',
        is_direct_supervisor: currentData.is_direct_supervisor || false,
        can_contact_before_offer: currentData.can_contact_before_offer !== false
      });
    }
  }, [currentData, open]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async (reason) => {
    // Validation
    if (!formData.referee_name.trim()) {
      toast.error('Referee name is required');
      return;
    }
    if (!formData.referee_email.trim()) {
      toast.error('Referee email is required');
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.put(
        `${API}/employees/${employeeId}/references/${referenceId}`,
        {
          ...formData,
          edit_reason: reason
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (onSuccess) {
        try {
          await onSuccess();
        } catch (refreshError) {
          console.error('Failed to refresh reference data after update:', refreshError);
        }
      }

      onClose();
      toast.success(response.data?.message || 'Reference updated');
    } catch (err) {
      const detail = err.response?.data?.detail;
      let msg = 'Failed to update reference';
      if (typeof detail === 'string') msg = detail;
      else if (Array.isArray(detail)) msg = detail.map(e => (typeof e === 'object' ? (e.msg || JSON.stringify(e)) : String(e))).join('; ');
      else if (detail && typeof detail === 'object') msg = detail.msg || JSON.stringify(detail);
      toast.error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <EditReasonDialog
      open={open}
      onClose={onClose}
      title="Edit Reference"
      description="Update referee details. All changes are logged for audit."
      onSave={handleSave}
      isLoading={isLoading}
    >
      <div className="space-y-4">
        {/* Referee Type - NHS Required */}
        <div className="space-y-2">
          <Label>Referee Type *</Label>
          <Select
            value={formData.referee_type}
            onValueChange={(value) => handleChange('referee_type', value)}
          >
            <SelectTrigger className="rounded-lg">
              <SelectValue placeholder="Select type" />
            </SelectTrigger>
            <SelectContent>
              {REFEREE_TYPES.map(type => (
                <SelectItem key={type.value} value={type.value}>
                  {type.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Referee Name *</Label>
            <Input
              value={formData.referee_name}
              onChange={(e) => handleChange('referee_name', e.target.value)}
              className="rounded-lg"
            />
          </div>
          <div className="space-y-2">
            <Label>Email *</Label>
            <Input
              type="email"
              value={formData.referee_email}
              onChange={(e) => handleChange('referee_email', e.target.value)}
              className="rounded-lg"
            />
          </div>
          <div className="space-y-2">
            <Label>Phone</Label>
            <Input
              value={formData.referee_phone}
              onChange={(e) => handleChange('referee_phone', e.target.value)}
              className="rounded-lg"
            />
          </div>
          <div className="space-y-2">
            <Label>Organisation</Label>
            <Input
              value={formData.referee_organisation}
              onChange={(e) => handleChange('referee_organisation', e.target.value)}
              className="rounded-lg"
            />
          </div>
          <div className="space-y-2">
            <Label>Position/Job Title</Label>
            <Input
              value={formData.referee_position}
              onChange={(e) => handleChange('referee_position', e.target.value)}
              className="rounded-lg"
            />
          </div>
          <div className="space-y-2">
            <Label>Relationship to Employee</Label>
            <Input
              value={formData.referee_relationship}
              onChange={(e) => handleChange('referee_relationship', e.target.value)}
              placeholder="e.g., Line Manager, Colleague"
              className="rounded-lg"
            />
          </div>
        </div>

        {/* Period of Supervision - NHS Required for Professional */}
        {formData.referee_type === 'professional' && (
          <div className="space-y-2">
            <Label>Period of Supervision</Label>
            <Input
              value={formData.period_of_supervision}
              onChange={(e) => handleChange('period_of_supervision', e.target.value)}
              placeholder="e.g., January 2022 - December 2023"
              className="rounded-lg"
            />
          </div>
        )}

        {/* NHS Required Checkboxes */}
        <div className="space-y-3 pt-2">
          {formData.referee_type === 'professional' && (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_direct_supervisor}
                onChange={(e) => handleChange('is_direct_supervisor', e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">This referee was a direct supervisor</span>
            </label>
          )}
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.can_contact_before_offer}
              onChange={(e) => handleChange('can_contact_before_offer', e.target.checked)}
              className="rounded border-gray-300"
            />
            <span className="text-sm text-gray-700">We can contact this referee before making an offer</span>
          </label>
        </div>
      </div>
    </EditReasonDialog>
  );
}

