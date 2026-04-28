import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Shield, CheckCircle, AlertCircle, Plus, ExternalLink, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { formatBackendDate } from '../../lib/dateUtils';
import { useAuth } from '../../context/AuthContext';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

const REGISTRATION_BODIES = [
  { value: "NMC", label: "NMC (Nursing & Midwifery Council)", url: "https://www.nmc.org.uk/registration/search/" },
  { value: "GMC", label: "GMC (General Medical Council)", url: "https://www.gmc-uk.org/registration-and-licensing" },
  { value: "HCPC", label: "HCPC (Health & Care Professions Council)", url: "https://www.hcpc-uk.org/check-the-register/" },
  { value: "Social Work England", label: "Social Work England", url: "https://www.socialworkengland.org.uk/register/" }
];

const ROLES_REQUIRING_REGISTRATION = ['nurse', 'social_worker', 'doctor', 'occupational_therapist', 'physiotherapist'];

export default function ProfessionalRegistrationPanel({ 
  employeeId, 
  employeeRole,
  onRefresh 
}) {
  const { token, isAdmin, isAuditor } = useAuth();
  const [loading, setLoading] = useState(true);
  const [registrations, setRegistrations] = useState([]);
  const [registrationRequired, setRegistrationRequired] = useState(false);
  const [requiredBody, setRequiredBody] = useState(null);
  const [checkUrl, setCheckUrl] = useState(null);
  const [showDialog, setShowDialog] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [formData, setFormData] = useState({
    body: '',
    registration_number: '',
    registration_status: 'active',
    registration_expiry_date: '',
    certificate_url: ''
  });

  // Normalize role for comparison
  const normalizedRole = (employeeRole || '').toLowerCase().replace(/\s+/g, '_');
  const needsRegistration = ROLES_REQUIRING_REGISTRATION.some(r => 
    normalizedRole.includes(r) || r.includes(normalizedRole)
  );

  useEffect(() => {
    fetchRegistrations();
  }, [employeeId]);

  const fetchRegistrations = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/professional-registrations`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRegistrations(response.data.registrations || []);
      setRegistrationRequired(response.data.registration_required);
      setRequiredBody(response.data.required_body);
      setCheckUrl(response.data.check_url);
    } catch (error) {
      console.error('Failed to fetch registrations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!formData.body || !formData.registration_number) {
      toast.error('Please fill in required fields');
      return;
    }

    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/professional-registration`,
        formData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Registration added successfully');
      setShowDialog(false);
      setFormData({
        body: requiredBody || '',
        registration_number: '',
        registration_status: 'active',
        registration_expiry_date: '',
        certificate_url: ''
      });
      fetchRegistrations();
      onRefresh?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add registration');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerify = async (body) => {
    setIsVerifying(true);
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/professional-registration/verify?registration_body=${encodeURIComponent(body)}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Registration verified');
      
      if (response.data.can_promote_now) {
        toast.success('All checks passed - employee can now be promoted to Active status!', {
          duration: 5000
        });
      }
      
      fetchRegistrations();
      onRefresh?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify registration');
    } finally {
      setIsVerifying(false);
    }
  };

  const openAddDialog = () => {
    setFormData({
      body: requiredBody || '',
      registration_number: '',
      registration_status: 'active',
      registration_expiry_date: '',
      certificate_url: ''
    });
    setShowDialog(true);
  };

  const hasValidRegistration = registrations.some(r => 
    r.verified && r.registration_status === 'active'
  );

  const getStatusBadge = (reg) => {
    if (reg.registration_status === 'suspended') {
      return <Badge className="bg-red-100 text-red-700 border-red-200">Suspended</Badge>;
    }
    if (reg.registration_status === 'lapsed') {
      return <Badge className="bg-amber-100 text-amber-700 border-amber-200">Lapsed</Badge>;
    }
    if (reg.registration_status === 'applied') {
      return <Badge className="bg-blue-100 text-blue-700 border-blue-200">Applied</Badge>;
    }
    return <Badge className="bg-green-100 text-green-700 border-green-200">Active</Badge>;
  };

  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-6 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  // Don't show panel if role doesn't require registration and none exist
  if (!needsRegistration && !registrationRequired && registrations.length === 0) {
    return null;
  }

  return (
    <Card className="border-[#E4E8EB] shadow-sm" data-testid="professional-registration-panel">
      <CardHeader className="flex-row items-center justify-between flex-wrap gap-3 pb-4">
        <div>
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Professional Registration
          </CardTitle>
          <p className="text-sm text-gray-500 mt-1">
            Required for regulated healthcare roles (NMC, GMC, HCPC, etc.)
          </p>
        </div>
        {!isAuditor() && (needsRegistration || registrationRequired) && (
          <Button 
            size="sm" 
            onClick={openAddDialog} 
            className="gap-2"
            data-testid="add-registration-btn"
          >
            <Plus className="h-4 w-4" />
            Add Registration
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {/* Warning if registration required but not present/verified */}
        {(needsRegistration || registrationRequired) && !hasValidRegistration && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-red-800">
                  Professional registration required
                </p>
                <p className="text-xs text-red-700 mt-1">
                  This role requires a valid, verified professional registration before the employee can be cleared for work.
                  {requiredBody && ` Required: ${requiredBody}`}
                </p>
                {checkUrl && (
                  <a 
                    href={checkUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-xs text-red-700 underline flex items-center gap-1 mt-2"
                  >
                    Verify on register <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            </div>
          </div>
        )}

        {registrations.length === 0 ? (
          <div className="text-center py-6 text-gray-500">
            <Shield className="h-10 w-10 mx-auto mb-2 text-gray-300" />
            <p>No professional registration recorded</p>
            {(needsRegistration || registrationRequired) && (
              <p className="text-xs mt-1 text-amber-600">
                This role requires registration - please add now
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {registrations.map((reg, idx) => (
              <div 
                key={idx} 
                className={`p-4 rounded-lg border ${
                  reg.verified && reg.registration_status === 'active' 
                    ? 'bg-green-50 border-green-200' 
                    : 'bg-gray-50 border-gray-200'
                }`}
                data-testid={`registration-${reg.body}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-gray-900">{reg.body}</span>
                      {getStatusBadge(reg)}
                      {reg.verified ? (
                        <Badge className="bg-green-100 text-green-700 border-green-200 gap-1">
                          <CheckCircle className="h-3 w-3" />
                          Verified
                        </Badge>
                      ) : (
                        <Badge className="bg-amber-100 text-amber-700 border-amber-200">
                          Pending Verification
                        </Badge>
                      )}
                    </div>
                    
                    <p className="text-sm text-gray-600 mt-2">
                      Registration Number: <span className="font-mono font-medium">{reg.registration_number}</span>
                    </p>
                    
                    {reg.registration_expiry_date && (
                      <p className="text-xs text-gray-500 mt-1">
                        Expires: {formatBackendDate(reg.registration_expiry_date)}
                      </p>
                    )}
                    
                    {reg.verified_at && (
                      <p className="text-xs text-green-600 mt-2">
                        Verified by {reg.verified_by_name} on {formatBackendDate(reg.verified_at)}
                      </p>
                    )}
                  </div>
                  
                  <div className="flex flex-col gap-2">
                    {/* External verification link */}
                    {REGISTRATION_BODIES.find(b => b.value === reg.body)?.url && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-xs gap-1"
                        onClick={() => window.open(REGISTRATION_BODIES.find(b => b.value === reg.body).url, '_blank')}
                      >
                        Check Register <ExternalLink className="h-3 w-3" />
                      </Button>
                    )}
                    
                    {/* Verify button (admin only) */}
                    {!isAuditor() && isAdmin() && !reg.verified && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-xs border-green-300 text-green-700 hover:bg-green-50"
                        onClick={() => handleVerify(reg.body)}
                        disabled={isVerifying}
                        data-testid={`verify-registration-${reg.body}`}
                      >
                        {isVerifying ? (
                          <Loader2 className="h-3 w-3 animate-spin mr-1" />
                        ) : (
                          <CheckCircle className="h-3 w-3 mr-1" />
                        )}
                        Verify
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>

      {/* Add Registration Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-md bg-white">
          <DialogHeader>
            <DialogTitle>Add Professional Registration</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Registration Body *</Label>
              <Select 
                value={formData.body} 
                onValueChange={(v) => setFormData({...formData, body: v})}
              >
                <SelectTrigger data-testid="registration-body-select">
                  <SelectValue placeholder="Select regulatory body" />
                </SelectTrigger>
                <SelectContent>
                  {REGISTRATION_BODIES.map(body => (
                    <SelectItem key={body.value} value={body.value}>
                      {body.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Registration Number *</Label>
              <Input
                value={formData.registration_number}
                onChange={(e) => setFormData({...formData, registration_number: e.target.value.toUpperCase()})}
                placeholder="e.g., 00A1234E"
                className="font-mono"
                data-testid="registration-number-input"
              />
            </div>

            <div>
              <Label>Registration Status</Label>
              <Select 
                value={formData.registration_status} 
                onValueChange={(v) => setFormData({...formData, registration_status: v})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="lapsed">Lapsed</SelectItem>
                  <SelectItem value="suspended">Suspended</SelectItem>
                  <SelectItem value="applied">Applied (Pending)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Expiry Date (if applicable)</Label>
              <Input
                type="date"
                value={formData.registration_expiry_date}
                onChange={(e) => setFormData({...formData, registration_expiry_date: e.target.value})}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleSubmit} 
              disabled={isSubmitting}
              data-testid="submit-registration-btn"
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              Add Registration
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

