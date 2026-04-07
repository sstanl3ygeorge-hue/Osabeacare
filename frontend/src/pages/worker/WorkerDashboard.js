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
  Shield, X, PenTool, Lock, Download, ExternalLink, Eye, User, Award
} from 'lucide-react';
import { toast } from 'sonner';
import SignaturePad from '../../components/worker/SignaturePad';
import { Checkbox } from '../../components/ui/checkbox';
import { ScrollArea } from '../../components/ui/scroll-area';
import { Briefcase, GraduationCap, Sparkles, Edit3, Link2, MessageSquare } from 'lucide-react';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';

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
    identity: "Upload your passport photo page or UK driving licence. For driving licence, select BOTH front AND back images at once.",
    proof_of_address: "Upload a utility bill, bank statement, or council tax bill dated within last 3 months. Must show your full name and current address. You can select multiple files if needed.",
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
  // Organization settings for dynamic branding
  const [orgSettings, setOrgSettings] = useState({ organisation_name: 'Osabea Healthcare Solutions' });
  // Document viewer modal state
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerDocument, setViewerDocument] = useState(null);
  const [documentBlobUrl, setDocumentBlobUrl] = useState(null);
  const [documentLoading, setDocumentLoading] = useState(false);
  // CV Extraction states
  const [cvStatus, setCvStatus] = useState(null);
  const [cvStatusLoading, setCvStatusLoading] = useState(false);
  const [showCvVerificationModal, setShowCvVerificationModal] = useState(false);
  const [cvPreview, setCvPreview] = useState(null);
  const [cvPreviewLoading, setCvPreviewLoading] = useState(false);
  const [cvVerifying, setCvVerifying] = useState(false);
  const [cvEditMode, setCvEditMode] = useState(false);
  const [editedEmploymentHistory, setEditedEmploymentHistory] = useState([]);
  const [confirmCvAccuracy, setConfirmCvAccuracy] = useState(false);
  // Reference mismatch explanation states
  const [referenceMismatches, setReferenceMismatches] = useState(null);
  const [showMismatchExplanationModal, setShowMismatchExplanationModal] = useState(false);
  const [selectedMismatch, setSelectedMismatch] = useState(null);
  const [mismatchExplanationType, setMismatchExplanationType] = useState('');
  const [mismatchExplanationText, setMismatchExplanationText] = useState('');
  const [submittingMismatchExplanation, setSubmittingMismatchExplanation] = useState(false);
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
      
      // Fetch org settings for dynamic branding
      try {
        const orgRes = await axios.get(`${API}/org-settings`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setOrgSettings(orgRes.data);
      } catch (err) {
        console.warn('Could not fetch org settings:', err);
      }
      
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

  // Fetch CV extraction status
  const fetchCvStatus = useCallback(async () => {
    setCvStatusLoading(true);
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.get(`${API}/worker/cv-extraction-status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCvStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch CV status:', error);
    } finally {
      setCvStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    if (dashboard) {
      fetchCvStatus();
      fetchReferenceMismatches();
    }
  }, [dashboard, fetchCvStatus]);

  // Fetch reference-employment mismatches
  const fetchReferenceMismatches = async () => {
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.get(`${API}/worker/reference-mismatches`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setReferenceMismatches(response.data);
    } catch (error) {
      console.error('Failed to fetch reference mismatches:', error);
    }
  };

  // Open mismatch explanation modal
  const openMismatchExplanationModal = (mismatch) => {
    setSelectedMismatch(mismatch);
    setMismatchExplanationType('');
    setMismatchExplanationText('');
    setShowMismatchExplanationModal(true);
  };

  // Submit mismatch explanation
  const handleSubmitMismatchExplanation = async () => {
    if (!mismatchExplanationType) {
      toast.error('Please select a reason for the mismatch');
      return;
    }
    if (!mismatchExplanationText || mismatchExplanationText.length < 20) {
      toast.error('Please provide a detailed explanation (at least 20 characters)');
      return;
    }
    
    setSubmittingMismatchExplanation(true);
    try {
      const token = localStorage.getItem('workerToken');
      await axios.post(
        `${API}/worker/reference-mismatches/${selectedMismatch.reference_number}/explain`,
        {
          reference_number: selectedMismatch.reference_number,
          explanation_type: mismatchExplanationType,
          explanation_text: mismatchExplanationText
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Explanation submitted! Admin will review.');
      setShowMismatchExplanationModal(false);
      fetchReferenceMismatches();
      fetchDashboard();
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to submit explanation';
      toast.error(message);
    } finally {
      setSubmittingMismatchExplanation(false);
    }
  };

  // Fetch CV preview for verification
  const fetchCvPreview = async () => {
    setCvPreviewLoading(true);
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.get(`${API}/worker/cv-extraction-preview`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCvPreview(response.data);
      if (response.data.extraction_preview?.employment_history) {
        setEditedEmploymentHistory(response.data.extraction_preview.employment_history);
      }
    } catch (error) {
      console.error('Failed to fetch CV preview:', error);
      toast.error('Failed to load CV extraction preview');
    } finally {
      setCvPreviewLoading(false);
    }
  };

  // Open CV verification modal
  const openCvVerificationModal = () => {
    setShowCvVerificationModal(true);
    setConfirmCvAccuracy(false);
    setCvEditMode(false);
    fetchCvPreview();
  };

  // Verify CV extraction
  const handleVerifyCvExtraction = async () => {
    if (!confirmCvAccuracy) {
      toast.error('Please confirm the information is accurate');
      return;
    }
    
    setCvVerifying(true);
    try {
      const token = localStorage.getItem('workerToken');
      await axios.post(`${API}/worker/cv-extraction-verify`, {
        employment_history: editedEmploymentHistory,
        education: cvPreview?.extraction_preview?.education || [],
        skills: cvPreview?.extraction_preview?.skills || [],
        confirm_accurate: true
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success('CV data verified! Your 10-year employment history form has been pre-filled.');
      setShowCvVerificationModal(false);
      fetchCvStatus();
      fetchDashboard();
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to verify CV extraction';
      toast.error(message);
    } finally {
      setCvVerifying(false);
    }
  };

  // Handle CV file upload
  const handleCvUpload = async (file) => {
    if (!file) return;
    
    setUploading('cv');
    const token = localStorage.getItem('workerToken');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      await axios.post(
        `${API}/worker/upload-document/cv`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      toast.success('CV uploaded! AI is extracting your employment history...');
      // Wait a moment for AI extraction to complete
      setTimeout(() => {
        fetchCvStatus();
        fetchDashboard();
      }, 2000);
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to upload CV';
      toast.error(message);
    } finally {
      setUploading(null);
    }
  };

  // Trigger CV file input
  const triggerCvFileInput = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.doc,.docx';
    input.onchange = (e) => {
      const file = e.target.files?.[0];
      if (file) handleCvUpload(file);
    };
    input.click();
  };
  
  // Clean up blob URL when viewer closes or document changes
  useEffect(() => {
    return () => {
      if (documentBlobUrl) {
        URL.revokeObjectURL(documentBlobUrl);
      }
    };
  }, [documentBlobUrl]);

  // Fetch document as blob with authentication
  const openDocumentViewer = async (doc) => {
    setViewerDocument(doc);
    setViewerOpen(true);
    setDocumentLoading(true);
    setDocumentBlobUrl(null);
    
    if (!doc?.id) {
      setDocumentLoading(false);
      return;
    }
    
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.get(
        `${API}/employee-documents/${doc.id}/file`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      // Create blob URL for the document
      const blobUrl = URL.createObjectURL(response.data);
      setDocumentBlobUrl(blobUrl);
    } catch (error) {
      console.error('Failed to load document:', error);
      toast.error('Failed to load document');
    } finally {
      setDocumentLoading(false);
    }
  };
  
  // Close document viewer and clean up
  const closeDocumentViewer = () => {
    if (documentBlobUrl) {
      URL.revokeObjectURL(documentBlobUrl);
    }
    setDocumentBlobUrl(null);
    setViewerDocument(null);
    setViewerOpen(false);
  };

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

  // Handle multiple file uploads for documents that need both sides (e.g., ID, driving licence)
  const handleMultiFileUpload = async (requirementId, files) => {
    if (!files || files.length === 0) return;
    
    setUploading(requirementId);
    const token = localStorage.getItem('workerToken');
    
    try {
      // Upload each file with a suffix indicator
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        // Add suffix to indicate which part (front/back)
        const suffix = files.length > 1 ? (i === 0 ? '_front' : '_back') : '';
        
        await axios.post(
          `${API}/worker/upload-document/${requirementId}${suffix}`,
          formData,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'multipart/form-data'
            }
          }
        );
      }
      
      toast.success(`${files.length} file${files.length > 1 ? 's' : ''} uploaded successfully! Awaiting admin verification.`);
      fetchDashboard();
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to upload documents';
      toast.error(message);
    } finally {
      setUploading(null);
    }
  };

  // Document types that require/allow multiple files (front + back)
  const MULTI_FILE_DOC_TYPES = ['identity', 'proof_of_address'];

  const triggerFileInput = (requirementId) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.jpg,.jpeg,.png,.webp';
    
    // Allow multiple files for ID documents
    if (MULTI_FILE_DOC_TYPES.includes(requirementId)) {
      input.multiple = true;
    }
    
    input.onchange = (e) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        if (files.length > 1) {
          handleMultiFileUpload(requirementId, Array.from(files));
        } else {
          handleFileUpload(requirementId, files[0]);
        }
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

  const { employee, progress, forms, missing_documents, missing_trainings, completed_documents, completed_trainings, expired_trainings, all_mandatory_trainings, alerts, contract_signed, professional_registration, references, induction, competency_assessments, spot_checks, agreements } = dashboard;
  
  const isActiveEmployee = employee.is_active_employee || employee.employee_status === 'active_employee';

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-800">{orgSettings.organisation_name || 'Healthcare Portal'}</h1>
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

        {/* ========== REFERENCE-EMPLOYMENT MISMATCH ALERT ========== */}
        {!isActiveEmployee && referenceMismatches?.has_mismatches && (
          <Card className="shadow-md border-0 border-l-4 border-l-amber-500 bg-amber-50/50" data-testid="reference-mismatch-alert">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg text-amber-800">
                    <Link2 className="h-5 w-5" />
                    Reference-Employment Mismatch
                  </CardTitle>
                  <p className="text-xs text-amber-700 mt-1">
                    {referenceMismatches.mismatch_count} reference(s) don't match your declared employment history
                  </p>
                </div>
                <Badge className="bg-amber-100 text-amber-700">
                  Action Required
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {referenceMismatches.mismatches.map((mismatch, idx) => (
                  <div 
                    key={idx}
                    className={`p-4 rounded-xl border ${
                      mismatch.explanation_status === 'submitted' ? 'bg-blue-50 border-blue-200' :
                      mismatch.mismatch_admin_decision === 'accepted' ? 'bg-green-50 border-green-200' :
                      mismatch.mismatch_admin_decision === 'rejected' ? 'bg-red-50 border-red-200' :
                      'bg-white border-amber-200'
                    }`}
                    data-testid={`mismatch-ref-${mismatch.reference_number}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                          mismatch.explanation_status === 'submitted' ? 'bg-blue-100' :
                          mismatch.mismatch_admin_decision === 'accepted' ? 'bg-green-100' :
                          'bg-amber-100'
                        }`}>
                          {mismatch.mismatch_admin_decision === 'accepted' ? (
                            <CheckCircle className="h-5 w-5 text-green-600" />
                          ) : mismatch.explanation_status === 'submitted' ? (
                            <Clock className="h-5 w-5 text-blue-600" />
                          ) : (
                            <AlertTriangle className="h-5 w-5 text-amber-600" />
                          )}
                        </div>
                        <div>
                          <p className="font-medium text-slate-800">
                            Reference {mismatch.reference_number}: {mismatch.referee_name}
                          </p>
                          <p className="text-sm text-slate-600">{mismatch.referee_company}</p>
                          <p className="text-xs text-amber-700 mt-1">{mismatch.message}</p>
                          
                          {/* Show existing explanation */}
                          {mismatch.existing_explanation && (
                            <div className="mt-2 p-2 bg-slate-100 rounded-lg">
                              <p className="text-xs text-slate-600">
                                <span className="font-medium">Your explanation:</span> {mismatch.existing_explanation.text}
                              </p>
                            </div>
                          )}
                          
                          {/* Show admin decision */}
                          {mismatch.mismatch_admin_decision && (
                            <p className={`text-xs mt-1 ${
                              mismatch.mismatch_admin_decision === 'accepted' ? 'text-green-600' :
                              mismatch.mismatch_admin_decision === 'rejected' ? 'text-red-600' :
                              'text-blue-600'
                            }`}>
                              Admin decision: {mismatch.mismatch_admin_decision}
                              {mismatch.admin_notes && ` - ${mismatch.admin_notes}`}
                            </p>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex flex-col items-end gap-2">
                        {mismatch.mismatch_admin_decision === 'accepted' ? (
                          <Badge className="bg-green-100 text-green-700 text-xs">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Accepted
                          </Badge>
                        ) : mismatch.explanation_status === 'submitted' ? (
                          <Badge className="bg-blue-100 text-blue-700 text-xs">
                            <Clock className="h-3 w-3 mr-1" />
                            Under Review
                          </Badge>
                        ) : (
                          <Button
                            size="sm"
                            onClick={() => openMismatchExplanationModal(mismatch)}
                            className="gap-1 bg-amber-600 hover:bg-amber-700"
                            data-testid={`explain-mismatch-${mismatch.reference_number}`}
                          >
                            <MessageSquare className="h-4 w-4" />
                            Explain
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              <p className="text-xs text-amber-700 mt-4 p-3 bg-amber-100/50 rounded-lg">
                NHS Safer Recruitment requires that all references are verified against your employment history. 
                Please explain any discrepancies to help us complete your compliance check.
              </p>
            </CardContent>
          </Card>
        )}

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

        {/* ========== CV EXTRACTION & 10-YEAR HISTORY SECTION ========== */}
        {!isActiveEmployee && (
          <Card className={`shadow-md border-0 ${
            cvStatus?.verified ? 'bg-green-50/30' :
            cvStatus?.needs_verification ? 'bg-blue-50/30' :
            'bg-slate-50'
          }`} data-testid="cv-extraction-section">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Briefcase className={`h-5 w-5 ${
                      cvStatus?.verified ? 'text-green-600' :
                      cvStatus?.needs_verification ? 'text-blue-600' :
                      'text-slate-500'
                    }`} />
                    CV & Employment History
                  </CardTitle>
                  <p className="text-xs text-slate-500 mt-1">
                    NHS requires 10-year employment history with gap explanations
                  </p>
                </div>
                {cvStatusLoading && <Loader2 className="h-4 w-4 animate-spin text-slate-400" />}
              </div>
            </CardHeader>
            <CardContent>
              {/* No CV Uploaded */}
              {!cvStatus?.has_cv && (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-amber-100 rounded-lg flex items-center justify-center">
                        <Upload className="h-6 w-6 text-amber-600" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-800">Upload Your CV</p>
                        <p className="text-sm text-slate-600">
                          AI will extract your employment history to auto-fill your 10-year form
                        </p>
                      </div>
                    </div>
                    <Button
                      onClick={triggerCvFileInput}
                      disabled={uploading === 'cv'}
                      className="gap-2 bg-amber-600 hover:bg-amber-700"
                      data-testid="upload-cv-btn"
                    >
                      {uploading === 'cv' ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Upload className="h-4 w-4" />
                      )}
                      Upload CV
                    </Button>
                  </div>
                  <p className="text-xs text-slate-500 mt-3">
                    Accepted formats: PDF, DOC, DOCX (max 10MB)
                  </p>
                </div>
              )}

              {/* CV Uploaded - Needs Verification */}
              {cvStatus?.has_cv && cvStatus?.needs_verification && !cvStatus?.verified && (
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                        <Sparkles className="h-6 w-6 text-blue-600" />
                      </div>
                      <div>
                        <p className="font-medium text-blue-800">Review Your Extracted Data</p>
                        <p className="text-sm text-blue-700">
                          AI found {cvStatus?.employment_history?.jobs_found || 0} jobs in your CV. Please verify the data.
                        </p>
                      </div>
                    </div>
                    <Button
                      onClick={openCvVerificationModal}
                      className="gap-2 bg-blue-600 hover:bg-blue-700"
                      data-testid="review-cv-extraction-btn"
                    >
                      <Eye className="h-4 w-4" />
                      Review & Verify
                    </Button>
                  </div>
                  
                  {/* Preview summary */}
                  <div className="grid grid-cols-3 gap-3 mt-3">
                    <div className="bg-white rounded-lg p-3 text-center">
                      <p className="text-2xl font-bold text-blue-600">{cvStatus?.employment_history?.jobs_found || 0}</p>
                      <p className="text-xs text-slate-500">Jobs Found</p>
                    </div>
                    <div className="bg-white rounded-lg p-3 text-center">
                      <p className="text-2xl font-bold text-amber-600">{cvStatus?.gaps?.total || 0}</p>
                      <p className="text-xs text-slate-500">Gaps Detected</p>
                    </div>
                    <div className="bg-white rounded-lg p-3 text-center">
                      <p className="text-2xl font-bold text-red-600">{cvStatus?.overlaps?.total || 0}</p>
                      <p className="text-xs text-slate-500">Overlaps</p>
                    </div>
                  </div>
                  
                  {(cvStatus?.overlaps?.total > 0 || cvStatus?.gaps?.unexplained > 0) && (
                    <div className="mt-3 p-3 bg-amber-100 rounded-lg">
                      <p className="text-sm text-amber-800 flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4" />
                        {cvStatus?.overlaps?.total > 0 && `${cvStatus.overlaps.total} date overlap(s) detected. `}
                        {cvStatus?.gaps?.unexplained > 0 && `${cvStatus.gaps.unexplained} gap(s) need explanation.`}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* CV Verified */}
              {cvStatus?.verified && (
                <div className="p-4 bg-green-50 border border-green-200 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                        <CheckCircle className="h-6 w-6 text-green-600" />
                      </div>
                      <div>
                        <p className="font-medium text-green-800">CV Data Verified</p>
                        <p className="text-sm text-green-700">
                          {cvStatus?.employment_history?.jobs_found || 0} jobs verified • {formatDate(cvStatus?.verified_at)}
                        </p>
                      </div>
                    </div>
                    <Badge className="bg-green-100 text-green-700">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Verified
                    </Badge>
                  </div>
                  
                  {/* 10-Year Form Status */}
                  {cvStatus?.ten_year_form_status && (
                    <div className="mt-3 pt-3 border-t border-green-200">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-green-600" />
                          <span className="text-sm text-green-800">10-Year Employment History Form</span>
                        </div>
                        {cvStatus.ten_year_form_status.status === 'verified' ? (
                          <Badge className="bg-green-100 text-green-700 text-xs">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Verified
                          </Badge>
                        ) : cvStatus.ten_year_form_status.status === 'submitted' ? (
                          <Badge className="bg-blue-100 text-blue-700 text-xs">
                            <Clock className="h-3 w-3 mr-1" />
                            Submitted
                          </Badge>
                        ) : cvStatus.ten_year_form_status.auto_populated ? (
                          <Badge className="bg-amber-100 text-amber-700 text-xs">
                            <Sparkles className="h-3 w-3 mr-1" />
                            Pre-filled - Complete & Submit
                          </Badge>
                        ) : (
                          <Badge className="bg-slate-100 text-slate-600 text-xs">Not Started</Badge>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
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

        {/* Missing Documents - Show for onboarding OR if there are rejected docs */}
        {((!isActiveEmployee && missing_documents.length > 0) || missing_documents.some(d => d.rejection)) && (
          <Card className="shadow-md border-0" data-testid="missing-documents-section">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Upload className="h-5 w-5 text-red-500" />
                {missing_documents.some(d => d.rejection) ? 'Action Required - Re-upload Documents' : 'Documents Needed'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {missing_documents.map((doc, idx) => (
                  <div 
                    key={idx} 
                    className={`p-4 rounded-xl ${doc.rejection ? 'bg-red-50 border border-red-200' : 'bg-slate-50'}`}
                    data-testid={`missing-doc-${doc.type}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${doc.rejection ? 'bg-red-100' : 'bg-slate-100'}`}>
                          {doc.rejection ? (
                            <AlertTriangle className="h-5 w-5 text-red-500" />
                          ) : (
                            <X className="h-5 w-5 text-slate-400" />
                          )}
                        </div>
                        <div>
                          <span className="font-medium text-slate-800">{doc.name}</span>
                          {doc.rejection && (
                            <p className="text-xs text-red-600 font-medium">
                              Rejected - Re-upload required
                            </p>
                          )}
                        </div>
                      </div>
                      <Button 
                        size="sm" 
                        onClick={() => triggerFileInput(doc.type)}
                        disabled={uploading === doc.type}
                        className={`gap-1 ${doc.rejection ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'}`}
                        data-testid={`upload-${doc.type}`}
                      >
                        {uploading === doc.type ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Upload className="h-4 w-4" />
                        )}
                        {doc.rejection ? 'Re-upload' : 'Upload'}
                      </Button>
                    </div>
                    {/* Show rejection reason */}
                    {doc.rejection && (
                      <div className="ml-13 pl-1 mt-2 p-3 bg-red-100 rounded-lg border border-red-200">
                        <p className="text-sm text-red-700 font-medium mb-1">
                          <AlertTriangle className="h-4 w-4 inline mr-1" />
                          Reason for rejection:
                        </p>
                        <p className="text-sm text-red-600">
                          {doc.rejection.rejection_reason}
                        </p>
                        <p className="text-xs text-red-500 mt-1">
                          Previous file: {doc.rejection.previous_file_name} • 
                          Rejected by: {doc.rejection.rejected_by_name}
                        </p>
                      </div>
                    )}
                    {!doc.rejection && (
                      <>
                        <p className="text-xs text-slate-500 ml-13 pl-1">
                          {getDocumentGuidance(doc.type)}
                        </p>
                        <p className="text-xs text-slate-400 ml-13 pl-1 mt-1">
                          {ACCEPTED_FORMATS}
                        </p>
                      </>
                    )}
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
        {/* Mandatory Training Certificates - Show ALL 6 */}
        {!isActiveEmployee && (
          <Card className="shadow-md border-0">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <FileText className="h-5 w-5 text-blue-500" />
                    Mandatory Training Certificates
                  </CardTitle>
                  <p className="text-xs text-slate-500 mt-1">
                    All 6 NHS mandatory trainings required • AI extracts details from your certificates
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
              <div className="space-y-2">
                {/* Show all 6 mandatory trainings with status */}
                {(all_mandatory_trainings || [
                  { id: 'safeguarding', name: 'Safeguarding', status: 'missing' },
                  { id: 'manual_handling', name: 'Manual Handling', status: 'missing' },
                  { id: 'fire_safety', name: 'Fire Safety', status: 'missing' },
                  { id: 'health_safety', name: 'Health & Safety', status: 'missing' },
                  { id: 'bls', name: 'Basic Life Support', status: 'missing' },
                  { id: 'infection_control', name: 'Infection Control', status: 'missing' }
                ]).map((training, idx) => (
                  <div 
                    key={idx} 
                    className={`p-4 rounded-xl border ${
                      training.status === 'complete' ? 'bg-green-50 border-green-200' :
                      training.status === 'expired' ? 'bg-red-50 border-red-200' :
                      'bg-slate-50 border-slate-200'
                    }`}
                    data-testid={`training-row-${training.id}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          training.status === 'complete' ? 'bg-green-100' :
                          training.status === 'expired' ? 'bg-red-100' :
                          'bg-amber-100'
                        }`}>
                          {training.status === 'complete' ? (
                            <CheckCircle className="h-5 w-5 text-green-600" />
                          ) : training.status === 'expired' ? (
                            <AlertTriangle className="h-5 w-5 text-red-600" />
                          ) : (
                            <Clock className="h-5 w-5 text-amber-600" />
                          )}
                        </div>
                        <div>
                          <span className={`font-medium ${
                            training.status === 'complete' ? 'text-green-800' :
                            training.status === 'expired' ? 'text-red-800' :
                            'text-slate-800'
                          }`}>{training.name}</span>
                          {training.expiry_date && (
                            <p className={`text-xs ${
                              training.status === 'expired' ? 'text-red-600' : 'text-slate-500'
                            }`}>
                              {training.status === 'expired' ? 'Expired: ' : 'Expires: '}
                              {formatDate(training.expiry_date)}
                            </p>
                          )}
                          {training.completion_date && training.status !== 'expired' && (
                            <p className="text-xs text-slate-500">
                              Completed: {formatDate(training.completion_date)}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {training.status === 'complete' ? (
                          <>
                            {training.verified ? (
                              <Badge className="bg-green-100 text-green-700 text-xs">
                                <Shield className="h-3 w-3 mr-1" />
                                Verified
                              </Badge>
                            ) : (
                              <Badge className="bg-amber-100 text-amber-700 text-xs">
                                <Clock className="h-3 w-3 mr-1" />
                                Pending
                              </Badge>
                            )}
                          </>
                        ) : training.status === 'expired' ? (
                          <Badge className="bg-red-100 text-red-700 text-xs">
                            <AlertTriangle className="h-3 w-3 mr-1" />
                            Expired
                          </Badge>
                        ) : (
                          <Badge className="bg-slate-100 text-slate-600 text-xs">
                            <Clock className="h-3 w-3 mr-1" />
                            Required
                          </Badge>
                        )}
                        {training.status !== 'complete' && (
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
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-slate-400 mt-4 text-center">
                {ACCEPTED_FORMATS}
              </p>
            </CardContent>
          </Card>
        )}

        {/* ========== REFERENCES STATUS (P1: Worker Dashboard Sync) ========== */}
        {!isActiveEmployee && references && references.length > 0 && (
          <Card className="shadow-md border-0" data-testid="references-section">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <User className="h-5 w-5 text-purple-500" />
                    References (2 required)
                  </CardTitle>
                  <p className="text-xs text-slate-500 mt-1">
                    Your references will be contacted by our team
                  </p>
                </div>
                <Badge className={`${
                  references.filter(r => r.status === 'verified').length === 2 
                    ? 'bg-green-100 text-green-700' 
                    : 'bg-amber-100 text-amber-700'
                }`}>
                  {references.filter(r => r.status === 'verified').length}/2 Verified
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {references.map((ref, idx) => (
                  <div 
                    key={idx} 
                    className={`p-4 rounded-xl border ${
                      ref.status === 'verified' ? 'bg-green-50 border-green-200' :
                      ref.status === 'rejected' || ref.status === 'needs_new_input' ? 'bg-red-50 border-red-200' :
                      ref.status === 'response_received' ? 'bg-blue-50 border-blue-200' :
                      ref.status === 'sent' ? 'bg-amber-50 border-amber-200' :
                      'bg-slate-50 border-slate-200'
                    }`}
                    data-testid={`reference-${ref.reference_number}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          ref.status === 'verified' ? 'bg-green-100' :
                          ref.status === 'rejected' || ref.status === 'needs_new_input' ? 'bg-red-100' :
                          ref.status === 'response_received' ? 'bg-blue-100' :
                          ref.status === 'sent' ? 'bg-amber-100' :
                          'bg-slate-100'
                        }`}>
                          {ref.status === 'verified' ? (
                            <CheckCircle className="h-5 w-5 text-green-600" />
                          ) : ref.status === 'rejected' || ref.status === 'needs_new_input' ? (
                            <AlertCircle className="h-5 w-5 text-red-600" />
                          ) : ref.status === 'response_received' ? (
                            <Clock className="h-5 w-5 text-blue-600" />
                          ) : ref.status === 'sent' ? (
                            <Clock className="h-5 w-5 text-amber-600" />
                          ) : (
                            <AlertCircle className="h-5 w-5 text-slate-400" />
                          )}
                        </div>
                        <div>
                          <span className="font-medium text-slate-800">Reference {ref.reference_number}</span>
                          {ref.referee_name && (
                            <p className="text-xs text-slate-500">{ref.referee_name}</p>
                          )}
                          {ref.verified_at && ref.verified_by_name && (
                            <p className="text-xs text-green-600">
                              Verified by {ref.verified_by_name} on {formatDate(ref.verified_at)}
                            </p>
                          )}
                          {/* Show rejection reason if reference was rejected */}
                          {ref.rejection_reason && (
                            <p className="text-xs text-red-600 mt-1">
                              Reason: {ref.rejection_reason}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {/* Show "Provide New" button for rejected references */}
                        {ref.can_provide_new && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-xs border-primary text-primary hover:bg-primary hover:text-white"
                            onClick={() => navigate('/worker/forms')}
                            data-testid={`provide-new-ref-${ref.reference_number}`}
                          >
                            Provide New Referee
                          </Button>
                        )}
                        <Badge className={`text-xs ${
                          ref.status === 'verified' ? 'bg-green-100 text-green-700' :
                          ref.status === 'rejected' || ref.status === 'needs_new_input' ? 'bg-red-100 text-red-700' :
                          ref.status === 'response_received' ? 'bg-blue-100 text-blue-700' :
                          ref.status === 'sent' ? 'bg-amber-100 text-amber-700' :
                          ref.status === 'declared' ? 'bg-slate-100 text-slate-600' :
                          'bg-slate-100 text-slate-500'
                        }`}>
                          {ref.status === 'verified' && <CheckCircle className="h-3 w-3 mr-1" />}
                          {(ref.status === 'rejected' || ref.status === 'needs_new_input') && <AlertCircle className="h-3 w-3 mr-1" />}
                          {(ref.status === 'response_received' || ref.status === 'sent') && <Clock className="h-3 w-3 mr-1" />}
                          {ref.status_label}
                        </Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* ========== INDUCTION CHECKLIST (P1: Worker Dashboard Sync) ========== */}
        {!isActiveEmployee && induction && (
          <Card className="shadow-md border-0" data-testid="induction-section">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Shield className="h-5 w-5 text-cyan-500" />
                    Induction Checklist ({induction.total} items)
                  </CardTitle>
                  <p className="text-xs text-slate-500 mt-1">
                    Care Certificate standards - 15 NHS requirements
                  </p>
                </div>
                <Badge className={`${
                  induction.completed === induction.total 
                    ? 'bg-green-100 text-green-700' 
                    : 'bg-amber-100 text-amber-700'
                }`}>
                  {induction.completed}/{induction.total} Complete
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <Progress value={(induction.completed / induction.total) * 100} className="h-2" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {induction.items?.map((item, idx) => (
                  <div 
                    key={idx} 
                    className={`flex items-center gap-2 p-2 rounded-lg text-sm ${
                      item.completed ? 'bg-green-50 text-green-800' : 'bg-slate-50 text-slate-600'
                    }`}
                    data-testid={`induction-item-${item.id}`}
                  >
                    {item.completed ? (
                      <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border-2 border-slate-300 flex-shrink-0" />
                    )}
                    <span className="truncate">{item.name}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-slate-400 mt-4 text-center">
                Items are auto-completed when related training is verified. Some items require manual sign-off by Admin.
              </p>
            </CardContent>
          </Card>
        )}

        {/* ========== COMPETENCY ASSESSMENTS (P1: Worker Dashboard) ========== */}
        {!isActiveEmployee && competency_assessments && competency_assessments.length > 0 && (
          <Card className="shadow-md border-0" data-testid="competency-section">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Award className="h-5 w-5 text-orange-500" />
                    Competency Assessments
                  </CardTitle>
                  <p className="text-xs text-slate-500 mt-1">
                    Your skills assessments and outcomes
                  </p>
                </div>
                <Badge className={`${
                  competency_assessments.filter(c => c.outcome === 'pass' || c.status === 'completed').length === competency_assessments.length
                    ? 'bg-green-100 text-green-700'
                    : 'bg-amber-100 text-amber-700'
                }`}>
                  {competency_assessments.filter(c => c.outcome === 'pass' || c.status === 'completed').length}/{competency_assessments.length} Passed
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {competency_assessments.map((comp, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-xl border ${
                      comp.outcome === 'pass' ? 'bg-green-50 border-green-200' :
                      comp.outcome === 'fail' ? 'bg-red-50 border-red-200' :
                      comp.status === 'scheduled' ? 'bg-blue-50 border-blue-200' :
                      'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          comp.outcome === 'pass' ? 'bg-green-100' :
                          comp.outcome === 'fail' ? 'bg-red-100' :
                          'bg-slate-100'
                        }`}>
                          {comp.outcome === 'pass' ? (
                            <CheckCircle className="h-5 w-5 text-green-600" />
                          ) : comp.outcome === 'fail' ? (
                            <X className="h-5 w-5 text-red-600" />
                          ) : (
                            <Clock className="h-5 w-5 text-slate-400" />
                          )}
                        </div>
                        <div>
                          <span className="font-medium text-slate-800">{comp.competency_name}</span>
                          {comp.area && <p className="text-xs text-slate-500">{comp.area}</p>}
                          {comp.scheduled_date && (
                            <p className="text-xs text-slate-500">
                              {comp.status === 'completed' ? 'Completed' : 'Scheduled'}: {formatDate(comp.completed_date || comp.scheduled_date)}
                            </p>
                          )}
                        </div>
                      </div>
                      <Badge className={`text-xs ${
                        comp.outcome === 'pass' ? 'bg-green-100 text-green-700' :
                        comp.outcome === 'fail' ? 'bg-red-100 text-red-700' :
                        comp.status === 'scheduled' ? 'bg-blue-100 text-blue-700' :
                        'bg-slate-100 text-slate-600'
                      }`}>
                        {comp.outcome === 'pass' ? 'Passed' :
                         comp.outcome === 'fail' ? 'Needs Improvement' :
                         comp.status === 'scheduled' ? 'Scheduled' : 'Pending'}
                      </Badge>
                    </div>
                    {comp.follow_up_required && comp.follow_up_date && (
                      <p className="text-xs text-amber-600 mt-2">
                        Follow-up scheduled: {formatDate(comp.follow_up_date)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* ========== SPOT CHECKS (P1: Worker Dashboard) ========== */}
        {spot_checks && spot_checks.length > 0 && (
          <Card className="shadow-md border-0" data-testid="spot-checks-section">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Eye className="h-5 w-5 text-indigo-500" />
                    Spot Checks
                  </CardTitle>
                  <p className="text-xs text-slate-500 mt-1">
                    Your observation and supervision history
                  </p>
                </div>
                <Badge className="bg-indigo-100 text-indigo-700">
                  {spot_checks.length} Recorded
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {spot_checks.slice(0, 10).map((spot, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-xl border ${
                      spot.outcome === 'pass' ? 'bg-green-50 border-green-200' :
                      spot.outcome === 'needs_improvement' ? 'bg-amber-50 border-amber-200' :
                      spot.outcome === 'fail' ? 'bg-red-50 border-red-200' :
                      'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          spot.outcome === 'pass' ? 'bg-green-100' :
                          spot.outcome === 'needs_improvement' ? 'bg-amber-100' :
                          spot.outcome === 'fail' ? 'bg-red-100' :
                          'bg-slate-100'
                        }`}>
                          {spot.outcome === 'pass' ? (
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          ) : spot.outcome === 'needs_improvement' ? (
                            <AlertCircle className="h-4 w-4 text-amber-600" />
                          ) : spot.outcome === 'fail' ? (
                            <X className="h-4 w-4 text-red-600" />
                          ) : (
                            <Clock className="h-4 w-4 text-slate-400" />
                          )}
                        </div>
                        <div>
                          <span className="font-medium text-slate-700 text-sm">{spot.area || spot.type || 'Observation'}</span>
                          {spot.date && <p className="text-xs text-slate-500">{formatDate(spot.date)}</p>}
                        </div>
                      </div>
                      <Badge className={`text-xs ${
                        spot.outcome === 'pass' ? 'bg-green-100 text-green-700' :
                        spot.outcome === 'needs_improvement' ? 'bg-amber-100 text-amber-700' :
                        spot.outcome === 'fail' ? 'bg-red-100 text-red-700' :
                        'bg-slate-100 text-slate-600'
                      }`}>
                        {spot.outcome === 'pass' ? 'Pass' :
                         spot.outcome === 'needs_improvement' ? 'Needs Work' :
                         spot.outcome === 'fail' ? 'Fail' : 'Pending'}
                      </Badge>
                    </div>
                    {spot.notes && (
                      <p className="text-xs text-slate-600 mt-2 bg-white/50 p-2 rounded">{spot.notes}</p>
                    )}
                  </div>
                ))}
              </div>
              {spot_checks.length > 10 && (
                <p className="text-xs text-slate-400 mt-2 text-center">
                  Showing 10 of {spot_checks.length} spot checks
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* ========== AGREEMENTS (P0: Contract & Handbook Status) ========== */}
        {/* Filter out contract_acceptance since it's covered by Employment Contract section below */}
        {agreements && agreements.filter(a => a.id !== 'contract_acceptance').length > 0 && (
          <Card className="shadow-md border-0" data-testid="agreements-section">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <PenTool className="h-5 w-5 text-purple-500" />
                    Acknowledgements
                  </CardTitle>
                  <p className="text-xs text-slate-500 mt-1">
                    Completed when you sign your employment contract
                  </p>
                </div>
                <Badge className={`${
                  agreements.filter(a => a.id !== 'contract_acceptance').every(a => a.verified) ? 'bg-green-100 text-green-700' :
                  agreements.filter(a => a.id !== 'contract_acceptance').some(a => a.signed || a.verified) ? 'bg-blue-100 text-blue-700' :
                  'bg-slate-100 text-slate-600'
                }`}>
                  {agreements.filter(a => a.id !== 'contract_acceptance' && a.verified).length} of {agreements.filter(a => a.id !== 'contract_acceptance').length} Verified
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {agreements.filter(a => a.id !== 'contract_acceptance').map((agreement) => (
                  <div
                    key={agreement.id}
                    className={`p-4 rounded-xl border ${
                      agreement.verified ? 'bg-green-50 border-green-200' :
                      agreement.signed ? 'bg-blue-50 border-blue-200' :
                      'bg-slate-50 border-slate-200'
                    }`}
                    data-testid={`agreement-${agreement.id}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          agreement.verified ? 'bg-green-100' :
                          agreement.signed ? 'bg-blue-100' :
                          'bg-slate-100'
                        }`}>
                          {agreement.verified ? (
                            <CheckCircle className="h-5 w-5 text-green-600" />
                          ) : agreement.signed ? (
                            <PenTool className="h-5 w-5 text-blue-600" />
                          ) : (
                            <Clock className="h-5 w-5 text-slate-400" />
                          )}
                        </div>
                        <div>
                          <span className="font-medium text-slate-700">{agreement.name}</span>
                          {agreement.verified && agreement.verified_at && (
                            <p className="text-xs text-green-600 mt-0.5">
                              Verified on {formatDate(agreement.verified_at)}
                              {agreement.verified_by_name && ` by ${agreement.verified_by_name}`}
                            </p>
                          )}
                          {!agreement.verified && agreement.signed && agreement.signed_at && (
                            <p className="text-xs text-blue-600 mt-0.5">
                              Signed on {formatDate(agreement.signed_at)} - Awaiting admin verification
                            </p>
                          )}
                          {!agreement.signed && !agreement.verified && (
                            <p className="text-xs text-slate-500 mt-0.5">
                              {agreement.id === 'contract_acceptance' 
                                ? 'Sign contract in the section below' 
                                : agreement.id === 'handbook_acknowledgement'
                                  ? 'Acknowledge during contract signing'
                                  : 'Awaiting completion'}
                            </p>
                          )}
                        </div>
                      </div>
                      <Badge className={`text-xs ${
                        agreement.verified ? 'bg-green-100 text-green-700' :
                        agreement.signed ? 'bg-blue-100 text-blue-700' :
                        'bg-slate-100 text-slate-600'
                      }`}>
                        {agreement.verified ? 'Verified' :
                         agreement.signed ? 'Signed' : 
                         agreement.id === 'contract_acceptance' ? 'See Below ↓' : 'Pending'}
                      </Badge>
                    </div>
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
                Employment Contract & Handbook
              </CardTitle>
              <p className="text-xs text-slate-500 mt-1">
                Signing your contract also acknowledges the Employee Handbook
              </p>
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
                              onClick={() => openDocumentViewer(doc)}
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
                              onClick={() => openDocumentViewer(doc)}
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
          <p>{orgSettings.organisation_name || 'Healthcare Portal'} - Compliance Portal</p>
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
      <Dialog open={viewerOpen} onOpenChange={closeDocumentViewer}>
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
            {documentLoading ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-500">
                <Loader2 className="h-12 w-12 mb-3 animate-spin" />
                <p>Loading document...</p>
              </div>
            ) : documentBlobUrl ? (
              // Use blob URL for secure document viewing
              viewerDocument?.file_url?.match(/\.(jpg|jpeg|png|gif|webp)$/i) ? (
                <div className="flex items-center justify-center p-4 h-full">
                  <img 
                    src={documentBlobUrl}
                    alt={viewerDocument?.name || 'Document'}
                    className="max-w-full max-h-full object-contain rounded shadow-lg"
                    onError={(e) => {
                      console.error('Image load error');
                      e.target.style.display = 'none';
                      e.target.nextSibling.style.display = 'flex';
                    }}
                  />
                  <div className="hidden flex-col items-center justify-center h-full text-gray-500">
                    <FileText className="h-16 w-16 mb-3" />
                    <p>Failed to display image</p>
                  </div>
                </div>
              ) : (
                <iframe
                  src={documentBlobUrl}
                  className="w-full h-full min-h-[500px] rounded"
                  title={viewerDocument?.name || 'Document'}
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
            {documentBlobUrl && (
              <>
                <Button 
                  variant="outline" 
                  onClick={() => {
                    // Open blob URL in new tab
                    window.open(documentBlobUrl, '_blank');
                  }}
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Open in New Tab
                </Button>
                <Button 
                  variant="outline" 
                  onClick={async () => {
                    // Download with auth
                    try {
                      const token = localStorage.getItem('workerToken');
                      const response = await axios.get(
                        `${API}/employee-documents/${viewerDocument.id}/download`,
                        {
                          headers: { Authorization: `Bearer ${token}` },
                          responseType: 'blob'
                        }
                      );
                      const downloadUrl = URL.createObjectURL(response.data);
                      const link = document.createElement('a');
                      link.href = downloadUrl;
                      link.download = viewerDocument?.file_name || viewerDocument?.name || 'document';
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                      URL.revokeObjectURL(downloadUrl);
                    } catch (error) {
                      toast.error('Failed to download document');
                    }
                  }}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download
                </Button>
              </>
            )}
            <Button variant="outline" onClick={closeDocumentViewer}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* CV Extraction Verification Modal */}
      <Dialog open={showCvVerificationModal} onOpenChange={setShowCvVerificationModal}>
        <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-blue-600" />
              Review Your CV Extraction
            </DialogTitle>
            <p className="text-sm text-slate-500">
              Please review the information extracted from your CV. You can edit any incorrect data before confirming.
            </p>
          </DialogHeader>

          {cvPreviewLoading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-10 w-10 animate-spin text-blue-600 mb-4" />
              <p className="text-slate-600">Loading extracted data...</p>
            </div>
          ) : cvPreview?.has_pending_verification ? (
            <ScrollArea className="flex-1 max-h-[60vh] pr-4">
              {/* Employment History */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-slate-800 flex items-center gap-2">
                    <Briefcase className="h-4 w-4 text-blue-600" />
                    Employment History ({cvPreview.extraction_preview?.jobs_found || 0} jobs)
                  </h3>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setCvEditMode(!cvEditMode)}
                    className="gap-1 text-blue-600"
                    data-testid="edit-cv-data-btn"
                  >
                    <Edit3 className="h-4 w-4" />
                    {cvEditMode ? 'Done Editing' : 'Edit'}
                  </Button>
                </div>

                <div className="space-y-3">
                  {editedEmploymentHistory.map((job, idx) => (
                    <div key={idx} className="p-4 bg-slate-50 rounded-xl border border-slate-200" data-testid={`cv-job-${idx}`}>
                      {cvEditMode ? (
                        <div className="space-y-3">
                          <div>
                            <label className="text-xs text-slate-500">Job Title</label>
                            <input
                              type="text"
                              value={job.job_title || ''}
                              onChange={(e) => {
                                const updated = [...editedEmploymentHistory];
                                updated[idx] = { ...updated[idx], job_title: e.target.value };
                                setEditedEmploymentHistory(updated);
                              }}
                              className="w-full mt-1 px-3 py-2 border rounded-lg text-sm"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-slate-500">Employer</label>
                            <input
                              type="text"
                              value={job.employer || ''}
                              onChange={(e) => {
                                const updated = [...editedEmploymentHistory];
                                updated[idx] = { ...updated[idx], employer: e.target.value };
                                setEditedEmploymentHistory(updated);
                              }}
                              className="w-full mt-1 px-3 py-2 border rounded-lg text-sm"
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="text-xs text-slate-500">Start Date</label>
                              <input
                                type="date"
                                value={job.start_date || ''}
                                onChange={(e) => {
                                  const updated = [...editedEmploymentHistory];
                                  updated[idx] = { ...updated[idx], start_date: e.target.value };
                                  setEditedEmploymentHistory(updated);
                                }}
                                className="w-full mt-1 px-3 py-2 border rounded-lg text-sm"
                              />
                            </div>
                            <div>
                              <label className="text-xs text-slate-500">End Date</label>
                              <input
                                type="date"
                                value={job.end_date || ''}
                                onChange={(e) => {
                                  const updated = [...editedEmploymentHistory];
                                  updated[idx] = { ...updated[idx], end_date: e.target.value };
                                  setEditedEmploymentHistory(updated);
                                }}
                                className="w-full mt-1 px-3 py-2 border rounded-lg text-sm"
                                placeholder="Leave empty if current"
                              />
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-medium text-slate-800">{job.job_title || 'Unknown Role'}</p>
                            <p className="text-sm text-slate-600">{job.employer || 'Unknown Employer'}</p>
                            <p className="text-xs text-slate-500 mt-1">
                              {job.start_date ? formatDate(job.start_date) : 'Unknown'} - {job.end_date ? formatDate(job.end_date) : 'Present'}
                            </p>
                          </div>
                          <Badge className="bg-slate-100 text-slate-600 text-xs">
                            {idx + 1}
                          </Badge>
                        </div>
                      )}
                    </div>
                  ))}

                  {editedEmploymentHistory.length === 0 && (
                    <div className="text-center py-6 text-slate-500">
                      <Briefcase className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>No employment history extracted</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Validation Issues */}
              {cvPreview.validation?.has_issues && (
                <div className="mb-6">
                  <h3 className="font-semibold text-slate-800 flex items-center gap-2 mb-3">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    Issues Detected
                  </h3>
                  
                  {/* Overlaps */}
                  {cvPreview.validation?.overlaps?.length > 0 && (
                    <div className="mb-3">
                      <p className="text-sm text-red-700 font-medium mb-2">Date Overlaps:</p>
                      <div className="space-y-2">
                        {cvPreview.validation.overlaps.map((overlap, idx) => (
                          <div key={idx} className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                            <p className="font-medium">{overlap.message}</p>
                            <p className="text-xs mt-1">
                              {overlap.job1_employer} overlaps with {overlap.job2_employer} ({overlap.overlap_days} days)
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Gaps */}
                  {cvPreview.validation?.gaps?.length > 0 && (
                    <div>
                      <p className="text-sm text-amber-700 font-medium mb-2">Employment Gaps (&gt;28 days):</p>
                      <div className="space-y-2">
                        {cvPreview.validation.gaps.filter(g => g.needs_explanation).map((gap, idx) => (
                          <div key={idx} className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700">
                            <p>{gap.message}</p>
                            <p className="text-xs mt-1">
                              {formatDate(gap.start_date)} - {formatDate(gap.end_date)} ({gap.duration_days} days)
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <p className="text-xs text-slate-500 mt-3">
                    You'll be asked to explain gaps when completing the 10-Year Employment History form.
                  </p>
                </div>
              )}

              {/* Education */}
              {cvPreview.extraction_preview?.education?.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-semibold text-slate-800 flex items-center gap-2 mb-3">
                    <GraduationCap className="h-4 w-4 text-purple-600" />
                    Education ({cvPreview.extraction_preview.education.length})
                  </h3>
                  <div className="space-y-2">
                    {cvPreview.extraction_preview.education.map((edu, idx) => (
                      <div key={idx} className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
                        <p className="font-medium text-slate-800">{edu.qualification || edu.degree}</p>
                        <p className="text-sm text-slate-600">{edu.institution}</p>
                        {edu.year && <p className="text-xs text-slate-500">{edu.year}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Confirmation Checkbox */}
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl mt-4">
                <div className="flex items-start gap-3">
                  <Checkbox
                    id="confirm-cv-accuracy"
                    checked={confirmCvAccuracy}
                    onCheckedChange={setConfirmCvAccuracy}
                    className="mt-1"
                    data-testid="confirm-cv-accuracy-checkbox"
                  />
                  <label htmlFor="confirm-cv-accuracy" className="text-sm text-slate-700 cursor-pointer">
                    I confirm that the information shown above is accurate and matches my actual employment history.
                    I understand this data will be used to pre-fill my 10-Year Employment History form.
                  </label>
                </div>
              </div>
            </ScrollArea>
          ) : cvPreview?.already_verified ? (
            <div className="text-center py-12">
              <CheckCircle className="h-16 w-16 text-green-600 mx-auto mb-4" />
              <p className="text-lg font-medium text-green-800">Already Verified</p>
              <p className="text-sm text-slate-600 mt-2">
                Your CV data was verified on {formatDate(cvPreview.verified_at)}
              </p>
            </div>
          ) : (
            <div className="text-center py-12">
              <AlertCircle className="h-16 w-16 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-600">No pending verification found</p>
            </div>
          )}

          <DialogFooter className="gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setShowCvVerificationModal(false)}>
              Cancel
            </Button>
            {cvPreview?.has_pending_verification && (
              <Button
                onClick={handleVerifyCvExtraction}
                disabled={!confirmCvAccuracy || cvVerifying}
                className="gap-2 bg-green-600 hover:bg-green-700"
                data-testid="verify-cv-extraction-btn"
              >
                {cvVerifying ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle className="h-4 w-4" />
                )}
                Verify & Confirm
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reference Mismatch Explanation Modal */}
      <Dialog open={showMismatchExplanationModal} onOpenChange={setShowMismatchExplanationModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Link2 className="h-5 w-5 text-amber-600" />
              Explain Reference Mismatch
            </DialogTitle>
            <p className="text-sm text-slate-500">
              Help us understand why this reference doesn't appear in your employment history
            </p>
          </DialogHeader>

          {selectedMismatch && (
            <div className="space-y-4">
              {/* Mismatch Details */}
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
                <p className="font-medium text-slate-800">
                  Reference {selectedMismatch.reference_number}: {selectedMismatch.referee_name}
                </p>
                <p className="text-sm text-slate-600">{selectedMismatch.referee_company}</p>
                <p className="text-xs text-amber-700 mt-2">{selectedMismatch.message}</p>
              </div>

              {/* Explanation Type */}
              <div>
                <label className="text-sm font-medium text-slate-700 mb-2 block">
                  Why doesn't this referee match your employment history?
                </label>
                <Select value={mismatchExplanationType} onValueChange={setMismatchExplanationType}>
                  <SelectTrigger data-testid="mismatch-explanation-type">
                    <SelectValue placeholder="Select a reason..." />
                  </SelectTrigger>
                  <SelectContent>
                    {referenceMismatches?.explanation_types?.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Explanation Text */}
              <div>
                <label className="text-sm font-medium text-slate-700 mb-2 block">
                  Please provide more details
                </label>
                <Textarea
                  value={mismatchExplanationText}
                  onChange={(e) => setMismatchExplanationText(e.target.value)}
                  placeholder="Explain why this referee is from a different employer than shown in your employment history. For example: 'I worked through ABC Agency who placed me at XYZ Care Home. My referee was from the agency, not the care home.'"
                  className="min-h-[120px]"
                  data-testid="mismatch-explanation-text"
                />
                <p className="text-xs text-slate-500 mt-1">
                  {mismatchExplanationText.length}/20 minimum characters
                </p>
              </div>

              {/* NHS Compliance Note */}
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-xs text-blue-700">
                  <Shield className="h-3 w-3 inline mr-1" />
                  NHS Safer Recruitment requires documented justification for any discrepancies. 
                  Your explanation will be reviewed by admin and recorded for CQC audit purposes.
                </p>
              </div>
            </div>
          )}

          <DialogFooter className="gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setShowMismatchExplanationModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmitMismatchExplanation}
              disabled={!mismatchExplanationType || mismatchExplanationText.length < 20 || submittingMismatchExplanation}
              className="gap-2 bg-amber-600 hover:bg-amber-700"
              data-testid="submit-mismatch-explanation-btn"
            >
              {submittingMismatchExplanation ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <MessageSquare className="h-4 w-4" />
              )}
              Submit Explanation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
