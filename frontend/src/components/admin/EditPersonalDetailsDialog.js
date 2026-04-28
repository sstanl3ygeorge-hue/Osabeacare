import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import EditReasonDialog from './EditReasonDialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { toast } from 'sonner';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_BASE_URL;

/**
 * EditPersonalDetailsDialog - Edit personal information with reason logging
 */
export default function EditPersonalDetailsDialog({
  open,
  onClose,
  employeeId,
  currentData,
  onSuccess
}) {
  const { token } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    date_of_birth: '',
    ni_number: '',
    address_line1: '',
    address_line2: '',
    city: '',
    postcode: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
    emergency_contact_relationship: ''
  });

  useEffect(() => {
    if (currentData && open) {
      setFormData({
        first_name: currentData.first_name || '',
        last_name: currentData.last_name || '',
        email: currentData.email || '',
        phone: currentData.phone || '',
        date_of_birth: currentData.date_of_birth || '',
        ni_number: currentData.ni_number || '',
        address_line1: currentData.address_line1 || currentData.address?.line1 || '',
        address_line2: currentData.address_line2 || currentData.address?.line2 || '',
        city: currentData.city || currentData.address?.city || '',
        postcode: currentData.postcode || currentData.address?.postcode || '',
        emergency_contact_name: currentData.emergency_contact?.name || '',
        emergency_contact_phone: currentData.emergency_contact?.phone || '',
        emergency_contact_relationship: currentData.emergency_contact?.relationship || ''
      });
    }
  }, [currentData, open]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async (reason) => {
    setIsLoading(true);
    try {
      await axios.put(
        `${API}/employees/${employeeId}/personal-details`,
        {
          ...formData,
          edit_reason: reason
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Personal details updated');
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update personal details');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <EditReasonDialog
      open={open}
      onClose={onClose}
      title="Edit Personal Details"
      description="Update employee personal information. All changes are logged."
      onSave={handleSave}
      isLoading={isLoading}
    >
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>First Name</Label>
          <Input
            value={formData.first_name}
            onChange={(e) => handleChange('first_name', e.target.value)}
            className="rounded-lg"
          />
        </div>
        <div className="space-y-2">
          <Label>Last Name</Label>
          <Input
            value={formData.last_name}
            onChange={(e) => handleChange('last_name', e.target.value)}
            className="rounded-lg"
          />
        </div>
        <div className="space-y-2">
          <Label>Email</Label>
          <Input
            type="email"
            value={formData.email}
            onChange={(e) => handleChange('email', e.target.value)}
            className="rounded-lg"
          />
        </div>
        <div className="space-y-2">
          <Label>Phone</Label>
          <Input
            value={formData.phone}
            onChange={(e) => handleChange('phone', e.target.value)}
            className="rounded-lg"
          />
        </div>
        <div className="space-y-2">
          <Label>Date of Birth</Label>
          <Input
            type="date"
            value={formData.date_of_birth}
            onChange={(e) => handleChange('date_of_birth', e.target.value)}
            className="rounded-lg"
          />
        </div>
        <div className="space-y-2">
          <Label>NI Number</Label>
          <Input
            value={formData.ni_number}
            onChange={(e) => handleChange('ni_number', e.target.value.toUpperCase())}
            placeholder="AB123456C"
            className="rounded-lg"
          />
        </div>
      </div>

      <div className="space-y-2 mt-4">
        <Label className="font-medium">Address</Label>
        <Input
          value={formData.address_line1}
          onChange={(e) => handleChange('address_line1', e.target.value)}
          placeholder="Address Line 1"
          className="rounded-lg"
        />
        <Input
          value={formData.address_line2}
          onChange={(e) => handleChange('address_line2', e.target.value)}
          placeholder="Address Line 2 (optional)"
          className="rounded-lg"
        />
        <div className="grid grid-cols-2 gap-4">
          <Input
            value={formData.city}
            onChange={(e) => handleChange('city', e.target.value)}
            placeholder="City"
            className="rounded-lg"
          />
          <Input
            value={formData.postcode}
            onChange={(e) => handleChange('postcode', e.target.value.toUpperCase())}
            placeholder="Postcode"
            className="rounded-lg"
          />
        </div>
      </div>

      <div className="space-y-2 mt-4">
        <Label className="font-medium">Emergency Contact</Label>
        <div className="grid grid-cols-2 gap-4">
          <Input
            value={formData.emergency_contact_name}
            onChange={(e) => handleChange('emergency_contact_name', e.target.value)}
            placeholder="Contact Name"
            className="rounded-lg"
          />
          <Input
            value={formData.emergency_contact_phone}
            onChange={(e) => handleChange('emergency_contact_phone', e.target.value)}
            placeholder="Contact Phone"
            className="rounded-lg"
          />
        </div>
        <Input
          value={formData.emergency_contact_relationship}
          onChange={(e) => handleChange('emergency_contact_relationship', e.target.value)}
          placeholder="Relationship (e.g., Spouse, Parent)"
          className="rounded-lg"
        />
      </div>
    </EditReasonDialog>
  );
}

