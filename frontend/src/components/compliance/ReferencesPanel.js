import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../ui/dialog';
import { Textarea } from '../ui/textarea';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { 
  User, Mail, Phone, Building, Briefcase, Clock, CheckCircle, 
  XCircle, Send, AlertTriangle, Loader2, RefreshCw, Calendar,
  MessageSquare, FileText, Plus, Edit, Shield, Eye, Download
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_CONFIG = {
  not_declared: { label: 'Missing', color: 'bg-gray-100 text-gray-600', icon: XCircle },
  declared: { label: 'Referee declared', color: 'bg-blue-100 text-blue-700', icon: Clock },
  sent: { label: 'Awaiting response', color: 'bg-amber-100 text-amber-700', icon: Send },
  response_received: { label: 'Response received — awaiting admin review', color: 'bg-purple-100 text-purple-700', icon: MessageSquare },
  verified: { label: 'Satisfactory', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  rejected: { label: 'Unsatisfactory / action required', color: 'bg-red-100 text-red-700', icon: XCircle },
  legacy_unverified: { label: 'Declared referee on file — response evidence not found', color: 'bg-amber-100 text-amber-700', icon: AlertTriangle },
};

/**
 * Derive the display status for a reference, accounting for legacy data.
 * A reference is only "satisfactory" if it has:
 *  1. A real response on file (response object with at least one key beyond submitted_at)
 *  2. An admin verification stamp (verified_by or verified_at)
 *  3. Status === 'verified'
 * Legacy employee-level "verified" flags without canonical evidence are downgraded.
 */
function deriveDisplayStatus(ref) {
  const status = ref?.status || 'not_declared';
  const response = ref?.response;
  const verification = ref?.verification || {};
  const hasCanonicalResponse = Boolean(
    response && typeof response === 'object' && Object.keys(response).length > 0
  );
  const hasAdminStamp = Boolean(verification.verified_by || verification.verified_at);

  if (status === 'verified') {
    if (!hasCanonicalResponse && !hasAdminStamp) {
      return 'legacy_unverified';
    }
    if (!hasCanonicalResponse) {
      return 'legacy_unverified';
    }
  }
  return status;
}

export default function ReferencesPanel({ employeeId, employee, onRefresh, onEditReference }) {
  const [references, setReferences] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [sendingRequest, setSendingRequest] = useState(null);
  const [sendDialogOpen, setSendDialogOpen] = useState(false);
  const [selectedRef, setSelectedRef] = useState(null);
  const [customMessage, setCustomMessage] = useState('');
  
  // Add referee dialog state
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [addRefNum, setAddRefNum] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [refereeForm, setRefereeForm] = useState({
    name: '',
    email: '',
    phone: '',
    organisation: '',
    position: '',
    relationship: ''
  });
  
  // Review Response modal state
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [reviewRefNum, setReviewRefNum] = useState(null);
  
  // Verify/Reject state
  const [verifyDialogOpen, setVerifyDialogOpen] = useState(false);
  const [verifyRefNum, setVerifyRefNum] = useState(null);
  const [verifyAction, setVerifyAction] = useState('verify'); // 'verify' or 'reject'
  const [verifyNotes, setVerifyNotes] = useState('');
  const [mismatchReason, setMismatchReason] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);

  // Recent-employer mismatch flag state
  const [flaggingMismatch, setFlaggingMismatch] = useState(null); // ref_num being flagged

  // Mismatch explanation review state (admin reviews worker explanation)
  const [reviewExplanationOpen, setReviewExplanationOpen] = useState(false);
  const [reviewExplanationRef, setReviewExplanationRef] = useState(null);
  const [reviewDecision, setReviewDecision] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');
  const [reviewingExplanation, setReviewingExplanation] = useState(false);

  // PDF download state
  const [downloadingPdf, setDownloadingPdf] = useState(null);

  const fetchReferences = async () => {
    try {
      setLoading(true);
      setLoadError(false);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/employees/${employeeId}/references`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setReferences(response.data);
    } catch (error) {
      console.error('Failed to fetch references:', error);
      setReferences(null);
      setLoadError(true);
      toast.error('Failed to load references');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) {
      fetchReferences();
    }
  }, [employeeId]);

  const handleSendRequest = async (refNum) => {
    try {
      setSendingRequest(refNum);
      const token = localStorage.getItem('token');
      const currentRef = references?.references?.[`reference_${refNum}`] || {};
      const isResend = ['sent', 'requested', 'awaiting_response'].includes(currentRef?.status);
      const response = await axios.post(
        `${API}/employees/${employeeId}/send-reference-request?reference_num=${refNum}&force_resend=${isResend}${customMessage ? `&message=${encodeURIComponent(customMessage)}` : ''}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data.status === 'duplicate') {
        toast.info(response.data.message);
      } else {
        toast.success(`Reference request sent to referee ${refNum}`);
      }
      
      setSendDialogOpen(false);
      setCustomMessage('');
      fetchReferences();
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error(extractErrorMessage(error, 'Failed to send request'));
    } finally {
      setSendingRequest(null);
    }
  };

  const openSendDialog = (refNum) => {
    setSelectedRef(refNum);
    setCustomMessage('');
    setSendDialogOpen(true);
  };
  
  // Open review response modal
  const openReviewDialog = (refNum) => {
    setReviewRefNum(refNum);
    setReviewDialogOpen(true);
  };

  // Download reference response as PDF
  const handleDownloadReferencePdf = async (refNum) => {
    try {
      setDownloadingPdf(refNum);
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API}/references/${employeeId}/${refNum}/download-pdf`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const empName = `${employee?.first_name || ''}_${employee?.last_name || ''}`.replace(/\s+/g, '_');
      link.download = `reference_${refNum}_${empName}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success('Reference PDF downloaded');
    } catch (error) {
      console.error('PDF download failed:', error);
      toast.error('Failed to download reference PDF');
    } finally {
      setDownloadingPdf(null);
    }
  };
  
  // Open verify/reject modal
  const openVerifyDialog = (refNum, action = 'verify') => {
    setVerifyRefNum(refNum);
    setVerifyAction(action);
    setVerifyNotes('');
    setMismatchReason('');
    setVerifyDialogOpen(true);
  };
  
  // Handle verify/reject
  const handleVerifyReference = async () => {
    setVerifyLoading(true);

    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/employees/${employeeId}/references/${verifyRefNum}/verify`,
        {
          action: verifyAction,
          notes: verifyNotes,
          mismatch_reason: mismatchReason || null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const nextStatus = verifyAction === 'verify' ? 'verified' : 'rejected';

      setReferences(prev => {
        if (!prev?.references) return prev;

        const key = `reference_${verifyRefNum}`;
        const currentRef = prev.references[key] || {};

        return {
          ...prev,
          references: {
            ...prev.references,
            [key]: {
              ...currentRef,
              status: nextStatus,
              request: {
                ...(currentRef.request || {}),
                status: nextStatus
              },
              verification: {
                ...(currentRef.verification || {}),
                status: nextStatus,
                verified: verifyAction === 'verify',
                verified_at:
                  verifyAction === 'verify'
                    ? new Date().toISOString()
                    : currentRef.verification?.verified_at,
                rejected_at:
                  verifyAction === 'reject'
                    ? new Date().toISOString()
                    : currentRef.verification?.rejected_at,
                rejection_reason:
                  verifyAction === 'reject'
                    ? verifyNotes
                    : currentRef.verification?.rejection_reason,
                notes:
                  verifyAction === 'verify'
                    ? verifyNotes
                    : currentRef.verification?.notes
              },
              ...(verifyAction === 'reject'
                ? {
                    declared: {},
                    response: {},
                    review: {},
                    mismatch: {}
                  }
                : {})
            }
          }
        };
      });

      toast.success(
        verifyAction === 'verify'
          ? 'Reference verified successfully'
          : 'Reference rejected'
      );

      setReviewDialogOpen(false);
      setVerifyDialogOpen(false);
      setVerifyRefNum(null);
      setVerifyNotes('');
      setMismatchReason('');

      await fetchReferences();
      if (onRefresh) {
        await onRefresh();
      }
    } catch (error) {
      toast.error(extractErrorMessage(error, `Failed to ${verifyAction} reference`));
    } finally {
      setVerifyLoading(false);
    }
  };

  // Flag reference as not from most recent employer
  const handleFlagRecentEmployer = async (refNum) => {
    setFlaggingMismatch(refNum);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/employees/${employeeId}/references/${refNum}/flag-recent-employer-mismatch`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Mismatch flagged — worker will see an explanation task on their dashboard.');
      fetchReferences();
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Failed to flag mismatch'));
    } finally {
      setFlaggingMismatch(null);
    }
  };

  // Admin reviews worker's mismatch explanation
  const openReviewExplanation = (refNum) => {
    setReviewExplanationRef(refNum);
    setReviewDecision('');
    setReviewNotes('');
    setReviewExplanationOpen(true);
  };

  const handleReviewExplanation = async () => {
    if (!reviewDecision) {
      toast.error('Please select a decision');
      return;
    }
    setReviewingExplanation(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/references/${employeeId}/${reviewExplanationRef}/review-mismatch-explanation`,
        { decision: reviewDecision, admin_notes: reviewNotes },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Explanation ${reviewDecision}.`);
      setReviewExplanationOpen(false);
      fetchReferences();
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Failed to review explanation'));
    } finally {
      setReviewingExplanation(false);
    }
  };

  const openAddDialog = (refNum) => {
    setAddRefNum(refNum);
    setRefereeForm({
      name: '',
      email: '',
      phone: '',
      organisation: '',
      position: '',
      relationship: ''
    });
    setAddDialogOpen(true);
  };
  
  // Safely extract a displayable error message from axios/FastAPI errors
  const extractErrorMessage = (error, fallback = 'An error occurred') => {
    const detail = error.response?.data?.detail;
    if (!detail) return fallback;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map(e => (typeof e === 'object' ? (e.msg || JSON.stringify(e)) : String(e))).join('; ');
    }
    if (typeof detail === 'object') return detail.msg || JSON.stringify(detail);
    return String(detail);
  };

  const handleAddReferee = async () => {
    // Validate ref num
    if (!addRefNum || ![1, 2].includes(addRefNum)) {
      toast.error('Invalid reference number. Please close and try again.');
      return;
    }

    // Validate
    if (!refereeForm.name.trim() || !refereeForm.email.trim()) {
      toast.error('Name and email are required');
      return;
    }
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(refereeForm.email)) {
      toast.error('Please enter a valid email address');
      return;
    }
    
    setIsSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/employees/${employeeId}/references/${addRefNum}`,
        refereeForm,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(`Referee ${addRefNum} details added successfully`);
      setAddDialogOpen(false);
      fetchReferences();
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error(extractErrorMessage(error, 'Failed to add referee'));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-12 flex justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  if (loadError || !references) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-8 text-center text-red-700">
          <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-red-500" />
          <p className="font-medium">Cannot assess references</p>
          <p className="text-sm text-red-600 mt-1">Reference data unavailable. Verification actions are disabled until this source loads.</p>
          <Button variant="outline" size="sm" onClick={fetchReferences} className="mt-4 rounded-lg">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  const referenceValues = [1, 2].map((refNum) => references.references?.[`reference_${refNum}`] || {});
  const displayStatuses = referenceValues.map(deriveDisplayStatus);

  // ── Readiness counts ──
  // A reference only counts toward readiness when: response received + admin reviewed + satisfactory (verified)
  // AND it truly has canonical response evidence (not legacy shortcut)
  const satisfactoryCount = displayStatuses.filter((s) => s === 'verified').length;
  const missingCount = displayStatuses.filter((s) => s === 'not_declared').length;
  const requestNotSentCount = displayStatuses.filter((s) => s === 'declared').length;
  const awaitingResponseCount = displayStatuses.filter((s) => s === 'sent').length;
  const awaitingAdminReviewCount = displayStatuses.filter((s) => s === 'response_received').length;
  const rejectedCount = displayStatuses.filter((s) => s === 'rejected').length;
  const legacyUnverifiedCount = displayStatuses.filter((s) => s === 'legacy_unverified').length;
  const cannotAssessCount = legacyUnverifiedCount;
  const hasBlockers = satisfactoryCount < 2;

  // Summary banner colour
  const summaryBorderClass = satisfactoryCount >= 2
    ? 'border-green-200 bg-green-50'
    : (rejectedCount > 0 || cannotAssessCount > 0)
      ? 'border-red-200 bg-red-50'
      : 'border-amber-200 bg-amber-50';
  const summaryTextClass = satisfactoryCount >= 2
    ? 'text-green-800'
    : (rejectedCount > 0 || cannotAssessCount > 0)
      ? 'text-red-800'
      : 'text-amber-800';

  return (
    <>
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <CardTitle className="font-heading text-lg flex items-center justify-between">
            <span className="flex items-center gap-2">
              <User className="h-5 w-5 text-primary" />
              Employment References
            </span>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={fetchReferences}
              disabled={loading}
              className="rounded-xl"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </CardTitle>
          <p className="text-sm text-gray-500 mt-1">
            CQC safer recruitment. Minimum 2 satisfactory professional references required before readiness.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* ── Top summary banner ── */}
          <div className={`rounded-xl border p-4 ${summaryBorderClass}`}>
            <div className="flex items-start gap-3">
              <div className="mt-0.5">
                {satisfactoryCount >= 2
                  ? <CheckCircle className="h-5 w-5 text-green-600" />
                  : <AlertTriangle className="h-5 w-5 text-amber-600" />}
              </div>
              <div className="flex-1">
                <p className={`font-medium ${summaryTextClass}`}>
                  Satisfactory References: {satisfactoryCount} / 2
                </p>
                {hasBlockers && (
                  <div className="mt-2 text-sm space-y-0.5">
                    {missingCount > 0 && <p>Missing referees: {missingCount}</p>}
                    {requestNotSentCount > 0 && <p>Request not sent: {requestNotSentCount}</p>}
                    {awaitingResponseCount > 0 && <p>Awaiting response: {awaitingResponseCount}</p>}
                    {awaitingAdminReviewCount > 0 && <p>Response received — awaiting admin review: {awaitingAdminReviewCount}</p>}
                    {rejectedCount > 0 && <p className="text-red-700 font-medium">Unsatisfactory / action required: {rejectedCount}</p>}
                    {cannotAssessCount > 0 && <p className="text-red-700 font-medium">Cannot assess (legacy data, no response evidence): {cannotAssessCount}</p>}
                  </div>
                )}
              </div>
            </div>
          </div>
          {/* Reference Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {[1, 2].map(refNum => {
              const ref = references.references?.[`reference_${refNum}`];
              const declared = ref?.declared || {};
              const request = ref?.request || {};
              const response = ref?.response || {};
              const verification = ref?.verification || {};
              const rawStatus = ref?.status || 'not_declared';
              const displayStatus = deriveDisplayStatus(ref);
              const config = STATUS_CONFIG[displayStatus] || STATUS_CONFIG.not_declared;
              const StatusIcon = config.icon;
              const hasCanonicalResponse = Boolean(
                ref?.response && typeof ref.response === 'object' && Object.keys(ref.response).length > 0
              );

              return (
                <div 
                  key={refNum} 
                  className="border rounded-xl overflow-hidden"
                  data-testid={`reference-${refNum}-card`}
                >
                  {/* Header */}
                  <div className="bg-gray-50 px-4 py-3 flex items-center justify-between border-b">
                    <h3 className="font-medium flex items-center gap-2">
                      Reference {refNum}
                    </h3>
                    <div className="flex items-center gap-2">
                      {declared.name && onEditReference && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onEditReference(refNum, declared)}
                          className="h-7 px-2 text-gray-500 hover:text-primary"
                          data-testid={`edit-reference-btn-${refNum}`}
                        >
                          <Edit className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      <Badge className={`${config.color} flex items-center gap-1`}>
                        <StatusIcon className="h-3 w-3" />
                        {config.label}
                      </Badge>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="p-4 space-y-4">
                    {/* Declared Info */}
                    {declared.name ? (
                      <div className="space-y-3">
                        <div className="flex items-start gap-3">
                          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                            <User className="h-5 w-5 text-primary" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-gray-900">{declared.name}</p>
                            {declared.job_title && (
                              <p className="text-sm text-gray-600 flex items-center gap-1">
                                <Briefcase className="h-3 w-3" />
                                {declared.job_title}
                              </p>
                            )}
                            {declared.organisation && (
                              <p className="text-sm text-gray-600 flex items-center gap-1">
                                <Building className="h-3 w-3" />
                                {declared.organisation}
                              </p>
                            )}
                          </div>
                        </div>

                        {/* Contact Details */}
                        <div className="bg-gray-50 rounded-lg p-3 space-y-1">
                          {declared.email && (
                            <p className="text-sm flex items-center gap-2 text-gray-600">
                              <Mail className="h-3.5 w-3.5 text-gray-400" />
                              <a href={`mailto:${declared.email}`} className="hover:text-primary">
                                {declared.email}
                              </a>
                            </p>
                          )}
                          {declared.phone && (
                            <p className="text-sm flex items-center gap-2 text-gray-600">
                              <Phone className="h-3.5 w-3.5 text-gray-400" />
                              {declared.phone}
                            </p>
                          )}
                          {declared.relationship && (
                            <p className="text-sm text-gray-500">
                              Relationship: {declared.relationship}
                            </p>
                          )}
                          {declared.years_known && (
                            <p className="text-sm text-gray-500">
                              Known for: {declared.years_known} years
                            </p>
                          )}
                          {declared.is_professional !== undefined && (
                            <Badge variant="outline" className="text-xs mt-1">
                              {declared.is_professional ? 'Professional Reference' : 'Personal Reference'}
                            </Badge>
                          )}
                        </div>

                        {/* ── Stage Pipeline ── */}
                        <div className="space-y-1.5">
                          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Evidence stages</p>
                          {/* Stage 1: Referee declared */}
                          <div className="flex items-center gap-2 text-xs">
                            <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0" />
                            <span className="text-gray-700">Referee declared</span>
                          </div>
                          {/* Stage 2: Request sent */}
                          <div className="flex items-center gap-2 text-xs">
                            {request.sent_at
                              ? <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0" />
                              : <Clock className="h-3.5 w-3.5 text-gray-300 shrink-0" />}
                            <span className={request.sent_at ? 'text-gray-700' : 'text-gray-400'}>
                              {request.sent_at
                                ? `Request sent ${formatBackendDate(request.sent_at)}`
                                : 'Request not sent'}
                            </span>
                          </div>
                          {/* Stage 3: Response received */}
                          <div className="flex items-center gap-2 text-xs">
                            {hasCanonicalResponse
                              ? <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0" />
                              : <Clock className="h-3.5 w-3.5 text-gray-300 shrink-0" />}
                            <span className={hasCanonicalResponse ? 'text-gray-700' : 'text-gray-400'}>
                              {hasCanonicalResponse
                                ? `Response received${ref?.response_submitted_at || ref?.response?.submitted_at ? ` ${formatBackendDate(ref.response_submitted_at || ref.response.submitted_at)}` : ''}`
                                : 'No response yet'}
                            </span>
                          </div>
                          {/* Stage 4: Admin reviewed */}
                          <div className="flex items-center gap-2 text-xs">
                            {(displayStatus === 'verified' || displayStatus === 'rejected')
                              ? <CheckCircle className={`h-3.5 w-3.5 shrink-0 ${displayStatus === 'verified' ? 'text-green-500' : 'text-red-500'}`} />
                              : <Clock className="h-3.5 w-3.5 text-gray-300 shrink-0" />}
                            <span className={(displayStatus === 'verified' || displayStatus === 'rejected') ? 'text-gray-700' : 'text-gray-400'}>
                              {displayStatus === 'verified'
                                ? `Satisfactory${verification.verified_by ? ` — ${verification.verified_by}` : ''}${verification.verified_at ? ` on ${formatBackendDate(verification.verified_at)}` : ''}`
                                : displayStatus === 'rejected'
                                  ? 'Unsatisfactory / action required'
                                  : 'Awaiting admin review'}
                            </span>
                          </div>
                        </div>

                        {/* Legacy data warning */}
                        {displayStatus === 'legacy_unverified' && (
                          <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
                            <p className="text-sm font-medium text-amber-700 flex items-center gap-2">
                              <AlertTriangle className="h-4 w-4" />
                              Cannot assess — response evidence not found
                            </p>
                            <p className="text-xs text-amber-600 mt-1">
                              Legacy employee record shows this reference as verified, but no canonical response trail exists. Re-request or manually record the response source before marking satisfactory.
                            </p>
                          </div>
                        )}

                        {/* Response detail view (only when canonical response exists) */}
                        {hasCanonicalResponse && displayStatus !== 'verified' && (
                          <div className="bg-purple-50 rounded-lg p-3 border border-purple-200">
                            <div className="flex items-center justify-between">
                              <p className="text-sm font-medium text-purple-700 flex items-center gap-2">
                                <MessageSquare className="h-4 w-4" />
                                Response received — awaiting admin review
                              </p>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 px-2 text-purple-700 hover:text-purple-900 hover:bg-purple-100"
                                onClick={() => openReviewDialog(refNum)}
                                data-testid={`view-response-btn-${refNum}`}
                              >
                                <Eye className="h-3.5 w-3.5 mr-1" />
                                View Full Response
                              </Button>
                            </div>
                          </div>
                        )}

                        {/* Verification status (satisfactory) */}
                        {displayStatus === 'verified' && (
                          <div className="bg-green-50 rounded-lg p-3 border border-green-200">
                            <p className="text-sm font-medium text-green-700 flex items-center gap-2">
                              <CheckCircle className="h-4 w-4" />
                              Satisfactory
                            </p>
                            {verification.verified_by && (
                              <p className="text-xs text-green-600 mt-1">
                                By: {verification.verified_by}
                              </p>
                            )}
                            {verification.verified_at && (
                              <p className="text-xs text-green-600">
                                On: {formatBackendDate(verification.verified_at)}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Actions — guard verify/reject behind canonical response */}
                        {displayStatus !== 'verified' && declared.email && (
                          <div className="pt-2 border-t space-y-2">
                            {displayStatus === 'declared' || displayStatus === 'sent' || displayStatus === 'legacy_unverified' ? (
                              <Button
                                size="sm"
                                className="w-full rounded-lg"
                                onClick={() => openSendDialog(refNum)}
                                disabled={sendingRequest === refNum}
                                data-testid={`send-request-btn-${refNum}`}
                              >
                                {sendingRequest === refNum ? (
                                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                ) : (
                                  <Send className="h-4 w-4 mr-2" />
                                )}
                                {displayStatus === 'sent' ? 'Resend Request'
                                  : displayStatus === 'legacy_unverified' ? 'Re-request Reference'
                                  : 'Send Request'}
                              </Button>
                            ) : displayStatus === 'response_received' && hasCanonicalResponse ? (
                              <>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="w-full rounded-lg"
                                  onClick={() => openReviewDialog(refNum)}
                                  data-testid={`review-response-btn-${refNum}`}
                                >
                                  <Eye className="h-4 w-4 mr-2" />
                                  Review Response
                                </Button>
                                <div className="flex gap-2">
                                  <Button
                                    size="sm"
                                    className="flex-1 rounded-lg bg-green-600 hover:bg-green-700"
                                    onClick={() => openVerifyDialog(refNum, 'verify')}
                                    data-testid={`verify-reference-btn-${refNum}`}
                                  >
                                    <CheckCircle className="h-4 w-4 mr-2" />
                                    Mark Satisfactory
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="destructive"
                                    className="flex-1 rounded-lg"
                                    onClick={() => openVerifyDialog(refNum, 'reject')}
                                    data-testid={`reject-reference-btn-${refNum}`}
                                  >
                                    <XCircle className="h-4 w-4 mr-2" />
                                    Unsatisfactory
                                  </Button>
                                </div>
                              </>
                            ) : displayStatus === 'response_received' && !hasCanonicalResponse ? (
                              <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
                                <p className="text-xs text-amber-700">
                                  Response status set but no canonical response data found. Re-request or manually set response source before review.
                                </p>
                              </div>
                            ) : null}
                          </div>
                        )}

                        {/* ── Mismatch panel ── */}
                        {ref?.integrity?.mismatch_detected && (
                          <div className="mt-3 space-y-2">
                            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                              <p className="text-xs font-semibold text-amber-800 flex items-center gap-1 mb-1">
                                <AlertTriangle className="h-3.5 w-3.5" />
                                Mismatch Detected
                              </p>
                              <p className="text-xs text-amber-700">
                                {ref.integrity.mismatch_notes ||
                                  (ref.integrity.mismatch_reasons || []).join(' · ') ||
                                  'Reference discrepancy detected.'}
                              </p>
                            </div>

                            {/* Worker explanation (if submitted) */}
                            {ref.integrity.mismatch_explanation && (
                              <div className={`p-3 border rounded-lg ${
                                ref.integrity.mismatch_admin_decision === 'accepted'
                                  ? 'bg-green-50 border-green-200'
                                  : ref.integrity.mismatch_admin_decision === 'rejected'
                                  ? 'bg-red-50 border-red-200'
                                  : 'bg-blue-50 border-blue-200'
                              }`}>
                                <p className="text-xs font-semibold text-slate-700 mb-1">
                                  Worker Explanation{' '}
                                  <span className="text-slate-400 font-normal">
                                    ({ref.integrity.mismatch_explanation_type || 'other'})
                                  </span>
                                </p>
                                <p className="text-xs text-slate-600 mb-2">{ref.integrity.mismatch_explanation}</p>

                                {ref.integrity.mismatch_admin_decision ? (
                                  <p className={`text-xs font-medium ${
                                    ref.integrity.mismatch_admin_decision === 'accepted'
                                      ? 'text-green-700'
                                      : 'text-red-700'
                                  }`}>
                                    Decision: {ref.integrity.mismatch_admin_decision}
                                    {ref.integrity.mismatch_admin_notes && ` — ${ref.integrity.mismatch_admin_notes}`}
                                  </p>
                                ) : (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="text-xs h-7"
                                    onClick={() => openReviewExplanation(refNum)}
                                    data-testid={`review-explanation-btn-${refNum}`}
                                  >
                                    <MessageSquare className="h-3 w-3 mr-1" />
                                    Review Explanation
                                  </Button>
                                )}
                              </div>
                            )}

                            {!ref.integrity.mismatch_explanation && (
                              <p className="text-xs text-amber-600 italic">
                                Awaiting worker explanation via dashboard task.
                              </p>
                            )}
                          </div>
                        )}

                        {/* Flag: not from most recent employer (only if no mismatch already) */}
                        {declared.name && !ref?.integrity?.mismatch_detected && (
                          <div className="pt-2">
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-xs text-slate-500 hover:text-amber-600 w-full justify-start"
                              onClick={() => handleFlagRecentEmployer(refNum)}
                              disabled={flaggingMismatch === refNum}
                              data-testid={`flag-recent-employer-btn-${refNum}`}
                            >
                              {flaggingMismatch === refNum ? (
                                <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                              ) : (
                                <AlertTriangle className="h-3.5 w-3.5 mr-1" />
                              )}
                              Flag: not from most recent employer
                            </Button>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-6">
                        <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-amber-400" />
                        <p className="text-gray-600 font-medium">No referee declared for Reference {refNum}</p>
                        <p className="text-xs text-gray-500 mt-1 mb-4">Add referee details manually or extract from application form</p>
                        <Button
                          size="sm"
                          onClick={() => openAddDialog(refNum)}
                          className="rounded-lg"
                          data-testid={`add-referee-btn-${refNum}`}
                        >
                          <Plus className="h-4 w-4 mr-2" />
                          Add Referee Details
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Readiness Requirements */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="font-medium text-sm mb-2">Reference Readiness Criteria</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>- Minimum 2 satisfactory professional references required</li>
              <li>- Each must have a canonical response on file (not just declared or legacy-verified)</li>
              <li>- Each must be reviewed and marked satisfactory by an admin</li>
              <li>- At least one should be from the most recent employer</li>
              <li>- Declared referee details alone do not count as a satisfactory reference</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Send Request Dialog */}
      <Dialog open={sendDialogOpen} onOpenChange={setSendDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle>Send Reference Request</DialogTitle>
            <DialogDescription>
              Send an email to the referee requesting them to complete the reference form.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {selectedRef && references.references?.[`reference_${selectedRef}`]?.declared && (
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="font-medium">{references.references[`reference_${selectedRef}`].declared.name}</p>
                <p className="text-sm text-gray-600">{references.references[`reference_${selectedRef}`].declared.email}</p>
              </div>
            )}
            <div>
              <label className="text-sm font-medium">Custom Message (Optional)</label>
              <Textarea
                value={customMessage}
                onChange={(e) => setCustomMessage(e.target.value)}
                placeholder="Add a personalized message to the referee..."
                className="mt-1"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSendDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={() => handleSendRequest(selectedRef)}
              disabled={sendingRequest === selectedRef}
            >
              {sendingRequest === selectedRef ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Send Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Add Referee Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle>Add Referee Details</DialogTitle>
            <DialogDescription>
              Enter the referee's contact information. You can then send them a reference request.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Full Name *</Label>
              <Input
                value={refereeForm.name}
                onChange={(e) => setRefereeForm({...refereeForm, name: e.target.value})}
                placeholder="e.g., Jane Smith"
                data-testid="referee-name-input"
              />
            </div>
            
            <div>
              <Label>Email Address *</Label>
              <Input
                type="email"
                value={refereeForm.email}
                onChange={(e) => setRefereeForm({...refereeForm, email: e.target.value})}
                placeholder="e.g., jane.smith@company.com"
                data-testid="referee-email-input"
              />
            </div>
            
            <div>
              <Label>Phone Number</Label>
              <Input
                value={refereeForm.phone}
                onChange={(e) => setRefereeForm({...refereeForm, phone: e.target.value})}
                placeholder="e.g., 01234 567890"
              />
            </div>
            
            <div>
              <Label>Organisation</Label>
              <Input
                value={refereeForm.organisation}
                onChange={(e) => setRefereeForm({...refereeForm, organisation: e.target.value})}
                placeholder="e.g., Previous Care Home Ltd"
              />
            </div>
            
            <div>
              <Label>Job Title / Position</Label>
              <Input
                value={refereeForm.position}
                onChange={(e) => setRefereeForm({...refereeForm, position: e.target.value})}
                placeholder="e.g., Care Manager"
              />
            </div>
            
            <div>
              <Label>Relationship to Applicant</Label>
              <Input
                value={refereeForm.relationship}
                onChange={(e) => setRefereeForm({...refereeForm, relationship: e.target.value})}
                placeholder="e.g., Line Manager"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleAddReferee}
              disabled={isSubmitting}
              data-testid="submit-referee-btn"
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Plus className="h-4 w-4 mr-2" />
              )}
              Add Referee
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Review Response Dialog - Enhanced with categorized fields */}
      <Dialog open={reviewDialogOpen} onOpenChange={setReviewDialogOpen}>
        <DialogContent className="sm:max-w-3xl bg-white max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-primary" />
              Full Reference Response - Referee {reviewRefNum}
            </DialogTitle>
            <DialogDescription>
              Complete response submitted by the referee for verification review.
            </DialogDescription>
          </DialogHeader>
          {reviewRefNum && references?.references?.[`reference_${reviewRefNum}`]?.response && (() => {
            const response = references.references[`reference_${reviewRefNum}`].response;
            const declared = references.references[`reference_${reviewRefNum}`].declared;
            
            // Categorize fields for better organization
            const refereeFields = ['referee_full_name', 'referee_organisation', 'referee_job_title', 'referee_work_email', 'referee_phone'];
            const relationshipFields = ['relationship_type', 'known_from_date', 'known_to_date', 'employment_dates_confirm', 'job_title_held', 'reason_for_leaving'];
            const performanceFields = ['performance_rating', 'reliability', 'professionalism', 'teamwork'];
            const suitabilityFields = ['safeguarding_concerns', 'disciplinary_record', 'would_re_employ', 're_employ_notes', 'care_vulnerable_suitable', 'care_suitability_notes'];
            const declarationFields = ['declaration_accurate', 'declaration_authority'];
            const skipFields = ['submitted_at', 'ip_address', 'user_agent'];
            
            const getRatingColor = (value) => {
              const v = String(value).toLowerCase();
              if (v.includes('excellent') || v === 'yes' || v.includes('suitable')) return 'text-green-700 bg-green-50';
              if (v.includes('good') || v.includes('reliable') || v.includes('professional')) return 'text-blue-700 bg-blue-50';
              if (v.includes('no concern') || v.includes('no issue')) return 'text-green-700 bg-green-50';
              if (v.includes('concern') || v === 'no') return 'text-red-700 bg-red-50';
              return 'text-gray-700 bg-gray-50';
            };
            
            const formatFieldName = (key) => key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            
            const renderField = (key, value) => {
              if (skipFields.includes(key) || value === null || value === undefined) return null;
              const isRating = performanceFields.includes(key) || suitabilityFields.includes(key);
              const displayValue = typeof value === 'boolean' ? (value ? 'Yes' : 'No') : (value || 'N/A');
              
              return (
                <div key={key} className={`rounded-lg p-3 ${isRating ? getRatingColor(displayValue) : 'bg-gray-50'}`}>
                  <p className="text-xs font-medium text-gray-500 mb-0.5">{formatFieldName(key)}</p>
                  <p className="text-sm font-medium">{displayValue}</p>
                </div>
              );
            };
            
            return (
              <div className="space-y-6 py-4">
                {/* Declared vs Returned Comparison */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                    <h4 className="font-medium text-blue-800 mb-2 text-sm">Declared by Applicant</h4>
                    <p className="text-sm"><span className="text-blue-600">Name:</span> {declared?.name || 'N/A'}</p>
                    <p className="text-sm"><span className="text-blue-600">Organisation:</span> {declared?.organisation || 'N/A'}</p>
                    <p className="text-sm"><span className="text-blue-600">Email:</span> {declared?.email || 'N/A'}</p>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                    <h4 className="font-medium text-purple-800 mb-2 text-sm">Returned by Referee</h4>
                    <p className="text-sm"><span className="text-purple-600">Name:</span> {response.referee_full_name || 'N/A'}</p>
                    <p className="text-sm"><span className="text-purple-600">Organisation:</span> {response.referee_organisation || 'N/A'}</p>
                    <p className="text-sm"><span className="text-purple-600">Email:</span> {response.referee_work_email || 'N/A'}</p>
                  </div>
                </div>
                
                {/* Employment Period */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                    <Briefcase className="h-4 w-4 text-gray-500" />
                    Employment Details
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {relationshipFields.map(key => response[key] !== undefined && renderField(key, response[key]))}
                  </div>
                </div>
                
                {/* Performance Ratings */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-gray-500" />
                    Performance Assessment
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {performanceFields.map(key => response[key] !== undefined && renderField(key, response[key]))}
                  </div>
                </div>
                
                {/* Suitability & Safeguarding */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                    <Shield className="h-4 w-4 text-gray-500" />
                    Suitability & Safeguarding
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {suitabilityFields.map(key => response[key] !== undefined && renderField(key, response[key]))}
                  </div>
                </div>
                
                {/* Additional Comments - Full Width */}
                {response.additional_comments && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Additional Comments</h4>
                    <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 italic">
                      "{response.additional_comments}"
                    </div>
                  </div>
                )}
                
                {/* Declaration Confirmations */}
                <div className="border-t pt-4">
                  <h4 className="font-medium text-gray-900 mb-3">Referee Declarations</h4>
                  <div className="flex gap-4">
                    {response.declaration_accurate && (
                      <Badge className="bg-green-100 text-green-700">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Information Accurate
                      </Badge>
                    )}
                    {response.declaration_authority && (
                      <Badge className="bg-green-100 text-green-700">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Has Authority to Provide
                      </Badge>
                    )}
                  </div>
                </div>
                
                {/* Submission Timestamp */}
                {response.submitted_at && (
                  <p className="text-xs text-gray-500 text-center border-t pt-3">
                    Response submitted: {formatBackendDate(response.submitted_at)}
                  </p>
                )}
              </div>
            );
          })()}
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setReviewDialogOpen(false)}>
              Close
            </Button>

            {/* Download PDF button */}
            {reviewRefNum && (
              <Button
                variant="outline"
                onClick={() => handleDownloadReferencePdf(reviewRefNum)}
                disabled={downloadingPdf === reviewRefNum}
              >
                {downloadingPdf === reviewRefNum ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                Download PDF
              </Button>
            )}

            {reviewRefNum && (() => {
              const currentRef = references?.references?.[`reference_${reviewRefNum}`];

              const isVerified =
                currentRef?.status === 'verified' ||
                currentRef?.verification?.status === 'verified' ||
                currentRef?.verification?.verified === true;

              if (isVerified) {
                return (
                  <div className="inline-flex items-center px-3 py-2 rounded-lg bg-green-50 text-green-700 border border-green-200 text-sm font-medium">
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Already satisfactory
                  </div>
                );
              }

              return (
                <Button
                  className="bg-green-600 hover:bg-green-700"
                  onClick={() => {
                    setReviewDialogOpen(false);
                    openVerifyDialog(reviewRefNum, 'verify');
                  }}
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Mark Satisfactory
                </Button>
              );
            })()}
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Verify/Reject Dialog */}
      <Dialog open={verifyDialogOpen} onOpenChange={setVerifyDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {verifyAction === 'verify' ? (
                <>
                  <Shield className="h-5 w-5 text-green-600" />
                  Mark Reference Satisfactory
                </>
              ) : (
                <>
                  <XCircle className="h-5 w-5 text-red-600" />
                  Mark Reference Unsatisfactory
                </>
              )}
            </DialogTitle>
            <DialogDescription>
              {verifyAction === 'verify' 
                ? 'Confirm that this reference meets CQC safer recruitment standards. Response evidence and admin review will be recorded.'
                : 'Provide a reason for marking this reference unsatisfactory.'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Mismatch Handling */}
            {verifyAction === 'verify' && (
              <div>
                <Label>Organisation Mismatch Reason (if applicable)</Label>
                <Select value={mismatchReason || 'none'} onValueChange={(value) => setMismatchReason(value === 'none' ? '' : value)}>
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder="Select if referee not in employment history" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No mismatch</SelectItem>
                    <SelectItem value="earlier_employment">Referee is from earlier employment</SelectItem>
                    <SelectItem value="personal_reference">Referee is personal/professional reference</SelectItem>
                    <SelectItem value="changed_employers">Applicant changed employers since declaration</SelectItem>
                    <SelectItem value="other">Other (specify in notes)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
            
            <div>
              <Label>{verifyAction === 'verify' ? 'Notes (Optional)' : 'Reason for Rejection *'}</Label>
              <Textarea
                value={verifyNotes}
                onChange={(e) => setVerifyNotes(e.target.value)}
                placeholder={verifyAction === 'verify' 
                  ? 'Any additional notes...'
                  : 'Explain why this reference is being rejected...'}
                className="mt-1"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setVerifyDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleVerifyReference}
              disabled={verifyLoading || (verifyAction === 'reject' && !verifyNotes)}
              className={verifyAction === 'verify' ? 'bg-green-600 hover:bg-green-700' : ''}
              variant={verifyAction === 'reject' ? 'destructive' : 'default'}
            >
              {verifyLoading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : verifyAction === 'verify' ? (
                <CheckCircle className="h-4 w-4 mr-2" />
              ) : (
                <XCircle className="h-4 w-4 mr-2" />
              )}
              {verifyAction === 'verify' ? 'Mark Satisfactory' : 'Mark Unsatisfactory'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Review Mismatch Explanation Dialog */}
      <Dialog open={reviewExplanationOpen} onOpenChange={setReviewExplanationOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-amber-600" />
              Review Worker Explanation
            </DialogTitle>
            <DialogDescription>
              Review the worker's explanation for the reference mismatch. Accepting will clear the readiness block.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Decision *</Label>
              <Select value={reviewDecision} onValueChange={setReviewDecision}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select a decision..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="accepted">Accept — explanation satisfactory</SelectItem>
                  <SelectItem value="needs_clarification">Needs Clarification</SelectItem>
                  <SelectItem value="rejected">Reject — insufficient justification</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Admin Notes (Optional)</Label>
              <Textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Any notes for the audit trail..."
                className="mt-1"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReviewExplanationOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleReviewExplanation}
              disabled={!reviewDecision || reviewingExplanation}
              className={reviewDecision === 'accepted' ? 'bg-green-600 hover:bg-green-700' : ''}
              variant={reviewDecision === 'rejected' ? 'destructive' : 'default'}
              data-testid="confirm-review-explanation-btn"
            >
              {reviewingExplanation ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4 mr-2" />
              )}
              Confirm Decision
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
