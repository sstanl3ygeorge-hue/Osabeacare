import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Progress } from '../../components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { 
  CheckCircle, AlertCircle, Clock, Upload, FileText, 
  LogOut, Loader2, AlertTriangle, Calendar, RefreshCw,
  Shield, X, PenTool, Lock, Download, ExternalLink, Eye, User
} from 'lucide-react';
import { toast } from 'sonner';
import SignaturePad from '../../components/worker/SignaturePad';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Format date helper
const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return dateStr;
  }
};

// NHS-compliant document guidance text
const getDocumentGuidance = (docType) => {
  const guidance = {
    right_to_work: "Upload your UK passport, biometric residence permit, or share code screenshot from GOV.UK. Share code must be valid for at least 30 days.",
    dbs: "Upload your Enhanced DBS certificate (issued within last 3 years). If subscribed to DBS Update Service, please confirm.",
    identity: "Upload a clear photo of your passport photo page or UK driving licence (both sides).",
    proof_of_address: "Upload a utility bill, bank statement, or council tax bill dated within last 3 months. Must show your full name and current address.",
    proof_of_address_2: "Upload a different document from the first. Examples: bank statement, HMRC letter, tenancy agreement, or voter registration.",
    training: "Upload PDF or photo of your training certificate. AI will automatically extract the training name, completion date, and expiry date.",
    nmc_registration: "Upload your NMC PIN card or registration letter. Your registration will be verified online.",
    professional_indemnity: "Upload your professional indemnity insurance certificate. Must be valid for current year."
  };
  return guidance[docType] || "Upload a clear copy of the required document.";
};

// Accepted file formats text
const ACCEPTED_FORMATS = "Accepted formats: PDF, JPG, PNG (max 10MB per file)";

// Forms Section Component
function FormsSection() {
  const [forms, setForms] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchForms();
  }, []);

  const fetchForms = async () => {
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.get(`${API}/worker/forms`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setForms(response.data.forms || []);
    } catch (error) {
      console.error('Failed to fetch forms:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (form) => {
    switch (form.status) {
      case 'submitted':
        return <Badge className="bg-blue-100 text-blue-700">Submitted</Badge>;
      case 'verified':
        return <Badge className="bg-green-100 text-green-700"><CheckCircle className="h-3 w-3 mr-1" />Verified</Badge>;
      case 'in_progress':
        return <Badge className="bg-amber-100 text-amber-700"><Clock className="h-3 w-3 mr-1" />{form.progress_percentage}% Done</Badge>;
      default:
        return <Badge className="bg-gray-100 text-gray-600">Not Started</Badge>;
    }
  };

  const handleFormClick = (formId) => {
    navigate(`/worker/forms/${formId}`);
  };

  if (loading) {
    return (
      <Card className="shadow-md border-0">
        <CardContent className="py-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        </CardContent>
      </Card>
    );
  }

  const pendingForms = forms.filter(f => f.status !== 'submitted' && f.status !== 'verified');
  const completedForms = forms.filter(f => f.status === 'submitted' || f.status === 'verified');

  if (pendingForms.length === 0 && completedForms.length === 0) {
    return null;
  }

  return (
    <Card className="shadow-md border-0" data-testid="forms-section">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <FileText className="h-5 w-5 text-blue-500" />
          Forms to Complete
          {pendingForms.length > 0 && (
            <Badge className="bg-blue-100 text-blue-700 ml-2">{pendingForms.length} pending</Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {/* Pending Forms */}
          {pendingForms.map((form) => (
            <div 
              key={form.id} 
              className="flex items-center justify-between p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer"
              onClick={() => handleFormClick(form.id)}
              data-testid={`form-${form.id}`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  form.status === 'in_progress' ? 'bg-amber-100' : 'bg-blue-100'
                }`}>
                  <FileText className={`h-5 w-5 ${
                    form.status === 'in_progress' ? 'text-amber-600' : 'text-blue-600'
                  }`} />
                </div>
                <div>
                  <span className="font-medium text-slate-800">{form.name}</span>
                  {form.status === 'in_progress' && form.saved_at && (
                    <p className="text-xs text-slate-500">Last saved: {formatDate(form.saved_at)}</p>
                  )}
                  {!form.required && (
                    <p className="text-xs text-slate-400">Optional</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {getStatusBadge(form)}
                <Button 
                  size="sm"
                  className={form.status === 'in_progress' ? 'bg-amber-600 hover:bg-amber-700' : 'bg-blue-600 hover:bg-blue-700'}
                >
                  {form.status === 'in_progress' ? 'Continue' : 'Start'}
                </Button>
              </div>
            </div>
          ))}

          {/* Completed Forms */}
          {completedForms.length > 0 && pendingForms.length > 0 && (
            <div className="border-t border-slate-200 pt-3 mt-3">
              <p className="text-xs text-slate-500 mb-2">Completed</p>
            </div>
          )}
          {completedForms.map((form) => (
            <div 
              key={form.id} 
              className="flex items-center justify-between p-4 bg-green-50 rounded-xl"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <span className="font-medium text-slate-800">{form.name}</span>
                  {form.submitted_at && (
                    <p className="text-xs text-green-600">Submitted: {formatDate(form.submitted_at)}</p>
                  )}
                </div>
              </div>
              {getStatusBadge(form)}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function WorkerDashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(null);
  const [showSignaturePad, setShowSignaturePad] = useState(false);
  const [contractEligibility, setContractEligibility] = useState(null);
  // Document viewer modal state
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerDocument, setViewerDocument] = useState(null);
  const navigate = useNavigate();

  const fetchDashboard = useCallback(async () => {
    try {
      const token = localStorage.getItem('workerToken');
      if (!token) {
        navigate('/worker/login');
        return;
      }

      const response = await axios.get(`${API}/worker/dashboard`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDashboard(response.data);
      
      // Also check contract eligibility
      const employeeId = response.data?.employee?.id;
      if (employeeId && !response.data?.contract_signed) {
        try {
          const eligibilityRes = await axios.get(`${API}/employees/${employeeId}/can-sign-contract`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          setContractEligibility(eligibilityRes.data);
        } catch (err) {
          console.warn('Could not fetch contract eligibility:', err);
        }
      }
    } catch (error) {
      if (error.response?.status === 401 || error.response?.status === 403) {
        localStorage.removeItem('workerToken');
        localStorage.removeItem('workerEmployee');
        toast.error('Session expired. Please login again.');
        navigate('/worker/login');
      } else {
        toast.error('Failed to load dashboard');
      }
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const handleLogout = () => {
    localStorage.removeItem('workerToken');
    localStorage.removeItem('workerEmployee');
    toast.success('Logged out successfully');
    navigate('/worker/login');
  };

  const handleFileUpload = async (requirementId, file) => {
    if (!file) return;
    
    setUploading(requirementId);
    const token = localStorage.getItem('workerToken');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      await axios.post(
        `${API}/worker/upload-document/${requirementId}`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      toast.success('Document uploaded successfully! Awaiting admin verification.');
      fetchDashboard(); // Refresh data
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to upload document';
      toast.error(message);
    } finally {
      setUploading(null);
    }
  };

  const triggerFileInput = (requirementId) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.jpg,.jpeg,.png,.webp';
    input.onchange = (e) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFileUpload(requirementId, file);
      }
    };
    input.click();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-10 w-10 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-slate-600">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  if (!dashboard) return null;

  const { employee, progress, forms, missing_documents, missing_trainings, completed_documents, completed_trainings, expired_trainings, alerts, contract_signed, professional_registration } = dashboard;
  
  const isActiveEmployee = employee.is_active_employee || employee.employee_status === 'active_employee';

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-800">Osabea Healthcare</h1>
            <p className="text-sm text-slate-500">Welcome, {employee.name}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={fetchDashboard} className="gap-1">
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={handleLogout} className="gap-1 text-slate-600">
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Status Banner - Enhanced with "Cleared to Work" messaging */}
        {isActiveEmployee ? (
          <div className="bg-gradient-to-r from-green-500 to-emerald-600 rounded-2xl p-6 text-white shadow-lg" data-testid="status-banner-active">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center">
                <Shield className="h-8 w-8" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-xl">Cleared to Work</h3>
                  <Badge className="bg-white/20 text-white text-xs">Active Employee</Badge>
                </div>
                <p className="text-green-100 mt-1">
                  All NHS compliance requirements verified. You are authorised to work.
                </p>
              </div>
            </div>
            {/* Mini stats for active employees */}
            {alerts.length === 0 && (
              <div className="mt-4 pt-4 border-t border-white/20 flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                <span className="text-sm text-green-100">All documents current • No renewals due</span>
              </div>
            )}
          </div>
        ) : employee.status === 'READY' ? (
          <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-2xl p-6 text-white shadow-lg" data-testid="status-banner-ready">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center">
                <CheckCircle className="h-8 w-8" />
              </div>
              <div>
                <h3 className="font-bold text-xl">Compliance Complete!</h3>
                <p className="text-blue-100">All requirements submitted. Awaiting admin verification to be cleared for work.</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-gradient-to-r from-amber-500 to-orange-500 rounded-2xl p-6 text-white shadow-lg" data-testid="status-banner-onboarding">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center">
                <AlertCircle className="h-8 w-8" />
              </div>
              <div>
                <h3 className="font-bold text-xl">Onboarding In Progress</h3>
                <p className="text-amber-100">Complete the items below to become work-ready.</p>
              </div>
            </div>
          </div>
        )}

        {/* Progress Card - Only for onboarding */}
        {!isActiveEmployee && (
          <Card className="shadow-md border-0">
            <CardContent className="pt-6">
              <div className="flex justify-between items-center mb-3">
                <span className="text-sm font-medium text-slate-600">Your Compliance Progress</span>
                <span className="text-3xl font-bold text-blue-600">{progress.percentage}%</span>
              </div>
              <Progress value={progress.percentage} className="h-3" />
              <p className="text-sm text-slate-500 mt-3">
                {progress.completed} of {progress.required} requirements completed
              </p>
            </CardContent>
          </Card>
        )}

        {/* Forms Section - Only for onboarding */}
        {!isActiveEmployee && <FormsSection />}

        {/* Professional Registration Status - if applicable */}
        {professional_registration && (
          <Card className={`shadow-md border-0 ${
            professional_registration.status === 'verified' ? 'bg-green-50/30' :
            professional_registration.status === 'pending_verification' ? 'bg-amber-50/30' :
            'bg-red-50/30'
          }`} data-testid="professional-registration-section">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Shield className={`h-5 w-5 ${
                  professional_registration.status === 'verified' ? 'text-green-600' :
                  professional_registration.status === 'pending_verification' ? 'text-amber-600' :
                  'text-red-600'
                }`} />
                Professional Registration ({professional_registration.type})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="p-4 bg-white rounded-xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      professional_registration.status === 'verified' ? 'bg-green-100' :
                      professional_registration.status === 'pending_verification' ? 'bg-amber-100' :
                      'bg-red-100'
                    }`}>
                      <Shield className={`h-5 w-5 ${
                        professional_registration.status === 'verified' ? 'text-green-600' :
                        professional_registration.status === 'pending_verification' ? 'text-amber-600' :
                        'text-red-600'
                      }`} />
                    </div>
                    <div>
                      <p className="font-medium text-slate-800">
                        {professional_registration.type} Registration
                      </p>
                      {professional_registration.number ? (
                        <p className="text-sm text-slate-600">
                          Reg No: {professional_registration.number}
                        </p>
                      ) : (
                        <p className="text-sm text-red-600">
                          Not submitted - Required for your role
                        </p>
                      )}
                      {professional_registration.expiry_date && (
                        <p className="text-xs text-slate-500">
                          Expires: {formatDate(professional_registration.expiry_date)}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {professional_registration.status === 'verified' ? (
                      <Badge className="bg-green-100 text-green-700">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Verified
                      </Badge>
                    ) : professional_registration.status === 'pending_verification' ? (
                      <Badge className="bg-amber-100 text-amber-700">
                        <Clock className="h-3 w-3 mr-1" />
                        Pending Verification
                      </Badge>
                    ) : (
                      <Badge className="bg-red-100 text-red-700">
                        <AlertCircle className="h-3 w-3 mr-1" />
                        Required
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Urgent Alerts with Renewal Upload Buttons */}
        {alerts.length > 0 && (
          <Card className="border-red-200 bg-red-50/50 shadow-md border-0" data-testid="alerts-section">
            <CardHeader className="pb-2">
              <CardTitle className="text-red-800 flex items-center gap-2 text-lg">
                <AlertTriangle className="h-5 w-5" />
                Upcoming Renewals
              </CardTitle>
              <p className="text-xs text-slate-500 mt-1">
                Documents or training expiring soon. Upload renewals before they expire.
              </p>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {alerts.map((alert, idx) => {
                  // Determine severity color: red < 30 days, amber < 60, yellow < 90
                  const getSeverityColors = (days) => {
                    if (days <= 30) return { bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-100 text-red-700', dot: 'bg-red-500' };
                    if (days <= 60) return { bg: 'bg-amber-50', border: 'border-amber-200', badge: 'bg-amber-100 text-amber-700', dot: 'bg-amber-500' };
                    return { bg: 'bg-yellow-50', border: 'border-yellow-200', badge: 'bg-yellow-100 text-yellow-700', dot: 'bg-yellow-500' };
                  };
                  const severity = getSeverityColors(alert.days_left);
                  
                  return (
                    <div key={idx} className={`flex items-center justify-between p-4 ${severity.bg} border ${severity.border} rounded-xl`} data-testid={`alert-${alert.type}`}>
                      <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${severity.dot} animate-pulse`} />
                        <div>
                          <p className="font-medium text-slate-800">{alert.title}</p>
                          <p className="text-xs text-slate-500">Expires: {formatDate(alert.date)}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge className={severity.badge}>
                          {alert.days_left <= 0 ? 'EXPIRED' : `${alert.days_left} days`}
                        </Badge>
                        {/* Upload Renewal Button */}
                        <Button 
                          size="sm" 
                          variant={alert.urgent ? "default" : "outline"}
                          className={`gap-1 ${alert.urgent ? 'bg-red-600 hover:bg-red-700' : ''}`}
                          onClick={() => triggerFileInput(alert.type === 'training' ? `training_renewal_${alert.training_id || 'general'}` : `${alert.type}_renewal`)}
                          disabled={uploading === `${alert.type}_renewal`}
                          data-testid={`upload-renewal-${alert.type}`}
                        >
                          {uploading === `${alert.type}_renewal` ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <RefreshCw className="h-4 w-4" />
                          )}
                          Upload Renewal
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Missing Documents - Only for onboarding */}
        {!isActiveEmployee && missing_documents.length > 0 && (
          <Card className="shadow-md border-0">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Upload className="h-5 w-5 text-red-500" />
                Documents Needed
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {missing_documents.map((doc, idx) => (
                  <div key={idx} className="p-4 bg-slate-50 rounded-xl">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
                          <X className="h-5 w-5 text-red-500" />
                        </div>
                        <span className="font-medium text-slate-800">{doc.name}</span>
                      </div>
                      <Button 
                        size="sm" 
                        onClick={() => triggerFileInput(doc.type)}
                        disabled={uploading === doc.type}
                        className="gap-1 bg-blue-600 hover:bg-blue-700"
                        data-testid={`upload-${doc.type}`}
                      >
                        {uploading === doc.type ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Upload className="h-4 w-4" />
                        )}
                        Upload
                      </Button>
                    </div>
                    <p className="text-xs text-slate-500 ml-13 pl-1">
                      {getDocumentGuidance(doc.type)}
                    </p>
                    <p className="text-xs text-slate-400 ml-13 pl-1 mt-1">
                      {ACCEPTED_FORMATS}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Expired Training */}
        {expired_trainings?.length > 0 && (
          <Card className="shadow-md border-0">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Clock className="h-5 w-5 text-red-500" />
                Expired Training
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {expired_trainings.map((training, idx) => (
                  <div key={idx} className="flex items-center justify-between p-4 bg-red-50 rounded-xl">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
                        <AlertTriangle className="h-5 w-5 text-red-500" />
                      </div>
                      <div>
                        <span className="font-medium text-slate-800">{training.name}</span>
                        <p className="text-xs text-red-600">Expired: {formatDate(training.expiry_date)}</p>
                      </div>
                    </div>
                    <Button 
                      size="sm" 
                      onClick={() => triggerFileInput(`training_${training.id}`)}
                      disabled={uploading === `training_${training.id}`}
                      className="gap-1"
                      data-testid={`upload-training-${training.id}`}
                    >
                      {uploading === `training_${training.id}` ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Upload className="h-4 w-4" />
                      )}
                      Upload Certificate
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Missing Training - Only for onboarding */}
        {!isActiveEmployee && missing_trainings?.length > 0 && (
          <Card className="shadow-md border-0">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <FileText className="h-5 w-5 text-amber-500" />
                    Training Certificates Needed
                  </CardTitle>
                  <p className="text-xs text-slate-500 mt-1">
                    AI will automatically extract training name, completion date, and expiry date from your certificates
                  </p>
                </div>
                <Button 
                  variant="outline"
                  size="sm"
                  onClick={() => triggerFileInput('training_bulk')}
                  disabled={uploading === 'training_bulk'}
                  className="gap-1.5"
                  data-testid="bulk-upload-training-btn"
                >
                  {uploading === 'training_bulk' ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                  Bulk Upload
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {missing_trainings.map((training, idx) => (
                  <div key={idx} className="p-4 bg-slate-50 rounded-xl">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
                          <FileText className="h-5 w-5 text-amber-600" />
                        </div>
                        <span className="font-medium text-slate-800">{training.name}</span>
                      </div>
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => triggerFileInput(`training_${training.id}`)}
                        disabled={uploading === `training_${training.id}`}
                        className="gap-1"
                        data-testid={`upload-training-${training.id}`}
                      >
                        {uploading === `training_${training.id}` ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Upload className="h-4 w-4" />
                        )}
                        Upload
                      </Button>
                    </div>
                    <p className="text-xs text-slate-400 ml-13 pl-1 mt-2">
                      {ACCEPTED_FORMATS}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Contract Status - Only for onboarding */}
        {!isActiveEmployee && !contract_signed && (
          <Card className="shadow-md border-0">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileText className="h-5 w-5 text-red-500" />
                Employment Contract
              </CardTitle>
            </CardHeader>
            <CardContent>
              {contractEligibility?.can_sign ? (
                // CAN sign contract - all checks complete
                <div className="flex items-center justify-between p-4 bg-green-50 rounded-xl border border-green-200">
                  <div>
                    <span className="font-medium text-green-800">Ready to Sign!</span>
                    <p className="text-xs text-green-600">All compliance checks are complete. Please sign your contract to proceed.</p>
                  </div>
                  <Button 
                    onClick={() => setShowSignaturePad(true)}
                    className="gap-2 bg-green-600 hover:bg-green-700"
                    data-testid="sign-contract-btn"
                  >
                    <PenTool className="h-4 w-4" />
                    Sign Contract
                  </Button>
                </div>
              ) : (
                // CANNOT sign contract - blockers remaining
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-4 bg-amber-50 rounded-xl border border-amber-200">
                    <div>
                      <span className="font-medium text-amber-800">Contract Locked</span>
                      <p className="text-xs text-amber-600">
                        Contract signing is the final step. Complete all requirements below first.
                      </p>
                    </div>
                    <Button 
                      disabled
                      className="gap-2 bg-gray-300 cursor-not-allowed"
                      data-testid="sign-contract-btn-locked"
                    >
                      <Lock className="h-4 w-4" />
                      Locked
                    </Button>
                  </div>
                  
                  {/* Show remaining blockers */}
                  {contractEligibility?.blockers?.length > 0 && (
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs font-medium text-gray-600 mb-2">
                        Remaining requirements ({contractEligibility.blockers.length}):
                      </p>
                      <ul className="text-xs text-gray-500 space-y-1">
                        {contractEligibility.blockers.slice(0, 5).map((blocker, idx) => (
                          <li key={idx} className="flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3 text-amber-500" />
                            {blocker}
                          </li>
                        ))}
                        {contractEligibility.blockers.length > 5 && (
                          <li className="text-gray-400">
                            + {contractEligibility.blockers.length - 5} more...
                          </li>
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Completed Items - With Pending Verification & View Document */}
        {(completed_documents?.length > 0 || completed_trainings?.length > 0) && (
          <Card className="shadow-md border-0 bg-green-50/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-green-800 flex items-center gap-2 text-lg">
                <CheckCircle className="h-5 w-5" />
                Submitted Documents
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {completed_documents?.map((doc, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-white rounded-xl" data-testid={`completed-doc-${doc.type}`}>
                    <div className="flex items-center gap-3">
                      <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
                      <div>
                        <span className="text-slate-700 font-medium">{doc.name}</span>
                        {doc.uploaded_at && (
                          <p className="text-xs text-slate-500">Uploaded: {formatDate(doc.uploaded_at)}</p>
                        )}
                        {/* Show verification details if verified */}
                        {doc.verified && doc.verified_by_name && (
                          <p className="text-xs text-green-600 mt-1">
                            Verified by {doc.verified_by_name} on {formatDate(doc.verified_at)}
                            {doc.verification_stamp_label && ` • ${doc.verification_stamp_label}`}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {doc.verified ? (
                        <>
                          <Badge className="bg-green-100 text-green-700 text-xs">
                            <Shield className="h-3 w-3 mr-1" />
                            Verified
                          </Badge>
                          {doc.file_url && (
                            <Button 
                              size="sm" 
                              variant="outline" 
                              className="text-xs h-7"
                              onClick={() => {
                                setViewerDocument(doc);
                                setViewerOpen(true);
                              }}
                              data-testid={`view-doc-${doc.type}`}
                            >
                              <Eye className="h-3 w-3 mr-1" />
                              View
                            </Button>
                          )}
                        </>
                      ) : (
                        <>
                          <Badge className="bg-amber-100 text-amber-700 text-xs" data-testid={`pending-verification-${doc.type}`}>
                            <Clock className="h-3 w-3 mr-1" />
                            Pending Verification
                          </Badge>
                          {doc.file_url && (
                            <Button 
                              size="sm" 
                              variant="ghost" 
                              className="text-xs h-7"
                              onClick={() => {
                                setViewerDocument(doc);
                                setViewerOpen(true);
                              }}
                              data-testid={`view-pending-doc-${doc.type}`}
                            >
                              <Eye className="h-3 w-3 mr-1" />
                              View
                            </Button>
                          )}
                        </>
                      )}
                      {doc.partial && (
                        <Badge className="bg-amber-100 text-amber-700 text-xs">Partial</Badge>
                      )}
                    </div>
                  </div>
                ))}
                {completed_trainings?.map((training, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-white rounded-xl" data-testid={`completed-training-${training.id}`}>
                    <div className="flex items-center gap-3">
                      <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
                      <div>
                        <span className="text-slate-700 font-medium">{training.name}</span>
                        {training.expiry_date && (
                          <p className="text-xs text-slate-500">Expires: {formatDate(training.expiry_date)}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {training.verified ? (
                        <Badge className="bg-green-100 text-green-700 text-xs">
                          <Shield className="h-3 w-3 mr-1" />
                          Verified
                        </Badge>
                      ) : (
                        <Badge className="bg-amber-100 text-amber-700 text-xs">
                          <Clock className="h-3 w-3 mr-1" />
                          Pending Verification
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Footer */}
        <div className="text-center py-6 text-xs text-slate-400">
          <p>Osabea Healthcare Solutions - Compliance Portal</p>
          <p>Employee Code: {employee.code}</p>
        </div>
      </div>

      {/* Contract Signature Dialog */}
      <Dialog open={showSignaturePad} onOpenChange={setShowSignaturePad}>
        <DialogContent className="max-w-xl p-0">
          <SignaturePad
            employeeId={employee.id}
            employeeName={employee.name}
            onSigned={() => {
              setShowSignaturePad(false);
              fetchDashboard(); // Refresh dashboard
              toast.success('Contract signed! Your compliance status has been updated.');
            }}
            onCancel={() => setShowSignaturePad(false)}
          />
        </DialogContent>
      </Dialog>
      
      {/* Document Viewer Modal */}
      <Dialog open={viewerOpen} onOpenChange={setViewerOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              {viewerDocument?.name || 'Document'}
            </DialogTitle>
          </DialogHeader>
          
          {/* Document Metadata */}
          <div className="flex flex-wrap items-center gap-3 py-2 border-b border-gray-200">
            {viewerDocument?.verified ? (
              <Badge className="bg-green-100 text-green-700 flex items-center gap-1">
                <CheckCircle className="h-3 w-3" />
                Verified
              </Badge>
            ) : (
              <Badge className="bg-amber-100 text-amber-700 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Pending Verification
              </Badge>
            )}
            
            {viewerDocument?.verification_stamp_label && (
              <Badge variant="outline" className="flex items-center gap-1">
                <Shield className="h-3 w-3" />
                {viewerDocument.verification_stamp_label}
              </Badge>
            )}
            
            {viewerDocument?.uploaded_at && (
              <span className="text-sm text-gray-500">
                Uploaded: {formatDate(viewerDocument.uploaded_at)}
              </span>
            )}
            
            {viewerDocument?.verified_by_name && (
              <span className="text-sm text-gray-500 flex items-center gap-1">
                <User className="h-3 w-3" />
                Verified by: {viewerDocument.verified_by_name}
              </span>
            )}
          </div>
          
          {/* Document Preview */}
          <div className="flex-1 min-h-[400px] overflow-auto bg-gray-100 rounded-lg">
            {viewerDocument?.file_url ? (
              viewerDocument.file_url.match(/\.(jpg|jpeg|png|gif|webp)$/i) ? (
                <div className="flex items-center justify-center p-4 h-full">
                  <img 
                    src={`${process.env.REACT_APP_BACKEND_URL}${viewerDocument.file_url}`}
                    alt={viewerDocument.name}
                    className="max-w-full max-h-full object-contain rounded shadow-lg"
                  />
                </div>
              ) : (
                <iframe
                  src={`${process.env.REACT_APP_BACKEND_URL}${viewerDocument.file_url}#toolbar=0`}
                  className="w-full h-full min-h-[500px] rounded"
                  title={viewerDocument.name}
                />
              )
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-500">
                <FileText className="h-16 w-16 mb-3" />
                <p>No document available</p>
              </div>
            )}
          </div>
          
          <DialogFooter className="gap-2 pt-4 border-t">
            {viewerDocument?.file_url && (
              <>
                <Button 
                  variant="outline" 
                  onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}${viewerDocument.file_url}`, '_blank')}
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Open in New Tab
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => {
                    const link = document.createElement('a');
                    link.href = `${process.env.REACT_APP_BACKEND_URL}${viewerDocument.file_url}`;
                    link.download = viewerDocument.file_name || viewerDocument.name || 'document';
                    link.click();
                  }}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download
                </Button>
              </>
            )}
            <Button variant="outline" onClick={() => setViewerOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
