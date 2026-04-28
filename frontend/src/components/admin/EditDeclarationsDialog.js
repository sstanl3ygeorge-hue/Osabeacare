import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import EditReasonDialog from './EditReasonDialog';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Checkbox } from '../ui/checkbox';
import { toast } from 'sonner';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

/**
 * EditDeclarationsDialog - Edit declarations with reason logging
 * 
 * NHS/CQC Required Declaration Fields:
 * - Criminal convictions
 * - Health conditions
 * - DBS consent
 * - Right to work restrictions
 * - Driving licence (for roles requiring driving)
 */
export default function EditDeclarationsDialog({
  open,
  onClose,
  employeeId,
  currentData,
  onSuccess
}) {
  const { token, user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    // Criminal Convictions
    has_criminal_convictions: false,
    criminal_convictions_details: '',
    
    // Health Conditions
    has_health_conditions: false,
    health_conditions_details: '',
    
    // DBS Consent
    dbs_consent_given: false,
    dbs_update_service_registered: false,
    dbs_update_service_id: '',
    
    // Right to Work
    has_rtw_restrictions: false,
    rtw_restrictions_details: '',
    rtw_expiry_date: '',
    
    // Driving
    has_driving_licence: false,
    driving_licence_type: '',
    driving_convictions: ''
  });

  useEffect(() => {
    if (currentData && open) {
      const declarations = currentData.declarations || {};
      setFormData({
        has_criminal_convictions: declarations.has_criminal_convictions || false,
        criminal_convictions_details: declarations.criminal_convictions_details || '',
        has_health_conditions: declarations.has_health_conditions || false,
        health_conditions_details: declarations.health_conditions_details || '',
        dbs_consent_given: declarations.dbs_consent_given || false,
        dbs_update_service_registered: declarations.dbs_update_service_registered || false,
        dbs_update_service_id: declarations.dbs_update_service_id || '',
        has_rtw_restrictions: declarations.has_rtw_restrictions || false,
        rtw_restrictions_details: declarations.rtw_restrictions_details || '',
        rtw_expiry_date: declarations.rtw_expiry_date || '',
        has_driving_licence: declarations.has_driving_licence || false,
        driving_licence_type: declarations.driving_licence_type || '',
        driving_convictions: declarations.driving_convictions || ''
      });
    }
  }, [currentData, open]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async (reason) => {
    setIsLoading(true);
    try {
      const reviewedAt = new Date().toISOString();
      const reviewedDeclarations = {
        ...formData,
        reviewed: true,
        reviewed_at: reviewedAt,
        review_status: 'reviewed',
        reviewed_by: user?.user_id || user?.id || user?.email || null,
        reviewed_by_name: user?.name || user?.email || null
      };
      await axios.put(
        `${API}/employees/${employeeId}/declarations`,
        {
          declarations: reviewedDeclarations,
          edit_reason: reason
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Declarations updated');
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update declarations');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <EditReasonDialog
      open={open}
      onClose={onClose}
      title="Edit Declarations"
      description="Review or update employee declarations. All changes are kept in the audit trail."
      onSave={handleSave}
      isLoading={isLoading}
    >
      <div className="space-y-6 max-h-[60vh] overflow-y-auto pr-2">
        {/* Criminal Convictions */}
        <div className="p-4 border border-gray-200 rounded-lg space-y-3">
          <h4 className="font-medium text-gray-800">Criminal Convictions</h4>
          <div className="flex items-center gap-2">
            <Checkbox
              id="has_criminal_convictions"
              checked={formData.has_criminal_convictions}
              onCheckedChange={(checked) => handleChange('has_criminal_convictions', checked)}
            />
            <Label htmlFor="has_criminal_convictions" className="text-sm cursor-pointer">
              Has unspent criminal convictions or cautions
            </Label>
          </div>
          {formData.has_criminal_convictions && (
            <div className="space-y-1">
              <Label className="text-xs text-gray-600">Details (required)</Label>
              <Textarea
                value={formData.criminal_convictions_details}
                onChange={(e) => handleChange('criminal_convictions_details', e.target.value)}
                placeholder="Provide details of conviction(s)..."
                className="rounded-lg text-sm min-h-[80px]"
              />
            </div>
          )}
        </div>

        {/* Health Conditions */}
        <div className="p-4 border border-gray-200 rounded-lg space-y-3">
          <h4 className="font-medium text-gray-800">Health Conditions</h4>
          <div className="flex items-center gap-2">
            <Checkbox
              id="has_health_conditions"
              checked={formData.has_health_conditions}
              onCheckedChange={(checked) => handleChange('has_health_conditions', checked)}
            />
            <Label htmlFor="has_health_conditions" className="text-sm cursor-pointer">
              Has health conditions that may affect ability to work
            </Label>
          </div>
          {formData.has_health_conditions && (
            <div className="space-y-1">
              <Label className="text-xs text-gray-600">Details (for occupational health review)</Label>
              <Textarea
                value={formData.health_conditions_details}
                onChange={(e) => handleChange('health_conditions_details', e.target.value)}
                placeholder="Describe condition and any adjustments needed..."
                className="rounded-lg text-sm min-h-[80px]"
              />
            </div>
          )}
        </div>

        {/* DBS Consent */}
        <div className="p-4 border border-gray-200 rounded-lg space-y-3">
          <h4 className="font-medium text-gray-800">DBS Check Consent</h4>
          <div className="flex items-center gap-2">
            <Checkbox
              id="dbs_consent_given"
              checked={formData.dbs_consent_given}
              onCheckedChange={(checked) => handleChange('dbs_consent_given', checked)}
            />
            <Label htmlFor="dbs_consent_given" className="text-sm cursor-pointer">
              Consent given for Enhanced DBS check
            </Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="dbs_update_service_registered"
              checked={formData.dbs_update_service_registered}
              onCheckedChange={(checked) => handleChange('dbs_update_service_registered', checked)}
            />
            <Label htmlFor="dbs_update_service_registered" className="text-sm cursor-pointer">
              Registered with DBS Update Service
            </Label>
          </div>
          {formData.dbs_update_service_registered && (
            <div className="space-y-1">
              <Label className="text-xs text-gray-600">DBS Update Service ID</Label>
              <input
                type="text"
                value={formData.dbs_update_service_id}
                onChange={(e) => handleChange('dbs_update_service_id', e.target.value)}
                placeholder="Enter Update Service ID..."
                className="w-full h-9 px-3 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
          )}
        </div>

        {/* Right to Work Restrictions */}
        <div className="p-4 border border-gray-200 rounded-lg space-y-3">
          <h4 className="font-medium text-gray-800">Right to Work Restrictions</h4>
          <div className="flex items-center gap-2">
            <Checkbox
              id="has_rtw_restrictions"
              checked={formData.has_rtw_restrictions}
              onCheckedChange={(checked) => handleChange('has_rtw_restrictions', checked)}
            />
            <Label htmlFor="has_rtw_restrictions" className="text-sm cursor-pointer">
              Has restrictions on right to work in UK
            </Label>
          </div>
          {formData.has_rtw_restrictions && (
            <>
              <div className="space-y-1">
                <Label className="text-xs text-gray-600">Restrictions details</Label>
                <Textarea
                  value={formData.rtw_restrictions_details}
                  onChange={(e) => handleChange('rtw_restrictions_details', e.target.value)}
                  placeholder="E.g., Maximum 20 hours per week, specific employer only..."
                  className="rounded-lg text-sm min-h-[60px]"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-gray-600">Visa/Permit expiry date</Label>
                <input
                  type="date"
                  value={formData.rtw_expiry_date}
                  onChange={(e) => handleChange('rtw_expiry_date', e.target.value)}
                  className="w-full h-9 px-3 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </>
          )}
        </div>

        {/* Driving Licence */}
        <div className="p-4 border border-gray-200 rounded-lg space-y-3">
          <h4 className="font-medium text-gray-800">Driving Licence</h4>
          <div className="flex items-center gap-2">
            <Checkbox
              id="has_driving_licence"
              checked={formData.has_driving_licence}
              onCheckedChange={(checked) => handleChange('has_driving_licence', checked)}
            />
            <Label htmlFor="has_driving_licence" className="text-sm cursor-pointer">
              Holds a valid UK driving licence
            </Label>
          </div>
          {formData.has_driving_licence && (
            <>
              <div className="space-y-1">
                <Label className="text-xs text-gray-600">Licence type</Label>
                <select
                  value={formData.driving_licence_type}
                  onChange={(e) => handleChange('driving_licence_type', e.target.value)}
                  className="w-full h-9 px-3 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value="">Select type...</option>
                  <option value="full_uk">Full UK Licence</option>
                  <option value="provisional">Provisional</option>
                  <option value="international">International (converted)</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-gray-600">Driving convictions/endorsements</Label>
                <Textarea
                  value={formData.driving_convictions}
                  onChange={(e) => handleChange('driving_convictions', e.target.value)}
                  placeholder="List any points or convictions (or 'None')..."
                  className="rounded-lg text-sm min-h-[60px]"
                />
              </div>
            </>
          )}
        </div>
      </div>
    </EditReasonDialog>
  );
}

