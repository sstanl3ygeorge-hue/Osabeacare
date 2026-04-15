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
  MessageSquare, FileText, Plus, Edit, Shield, Eye
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_CONFIG = {
  not_declared: { label: 'Not Declared', color: 'bg-gray-100 text-gray-600', icon: XCircle },
  declared: { label: 'Declared', color: 'bg-blue-100 text-blue-700', icon: Clock },
  sent: { label: 'Request Sent', color: 'bg-amber-100 text-amber-700', icon: Send },
  response_received: { label: 'Response Received', color: 'bg-purple-100 text-purple-700', icon: MessageSquare },
  verified: { label: 'Verified', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-700', icon: XCircle }
};

export default function ReferencesPanel({ employeeId, onRefresh, onEditReference }) {
  const [references, setReferences] = useState(null);
  const [loading, setLoading] = useState(true);
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

  const fetchReferences = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/employees/${employeeId}/references`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setReferences(response.data);
    } catch (error) {
      console.error('Failed to fetch references:', error);
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
      const msg = error.response?.data?.detail || 'Failed to send request';
      toast.error(msg);
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
      const msg = error.response?.data?.detail || `Failed to ${verifyAction} reference`;
      toast.error(msg);
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
      toast.error(err.response?.data?.detail || 'Failed to flag mismatch');
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
      toast.error(err.response?.data?.detail || 'Failed to review explanation');
    } finally {
      setReviewingExplanation(false);
    }
  };

  const openAddDialog = (refNum) => {
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
  
  const handleAddReferee = async () => {
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
      const msg = error.response?.data?.detail || 'Failed to add referee';
      toast.error(msg);
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

  if (!references) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-8 text-center text-gray-500">
          No references data available
        </CardContent>
      </Card>
    );
  }

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
            NHS-level reference verification. Minimum 2 verified professional references required.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Reference Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {[1, 2].map(refNum => {
              const ref = references.references?.[`reference_${refNum}`];
              const declared = ref?.declared || {};
              const request = ref?.request || {};
              const response = ref?.response || {};
              const verification = ref?.verification || {};
              const status = ref?.status || 'not_declared';
              const config = STATUS_CONFIG[status] || STATUS_CONFIG.not_declared;
              const StatusIcon = config.icon;

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

                        {/* Request Status */}
                        {request.sent_at && (
                          <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
                            <p className="text-sm font-medium text-amber-700 flex items-center gap-2">
                              <Send className="h-4 w-4" />
                              Request Sent
                            </p>
                            <p className="text-xs text-amber-600 mt-1">
                              Sent: {formatBackendDate(request.sent_at)}
                            </p>
                            {request.due_at && (
                              <p className="text-xs text-amber-600">
                                Due: {formatBackendDate(request.due_at)}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Response Received - with View Full Response button */}
                        {response && Object.keys(response).length > 0 && (
                          <div className="bg-purple-50 rounded-lg p-3 border border-purple-200">
                            <div className="flex items-center justify-between">
                              <p className="text-sm font-medium text-purple-700 flex items-center gap-2">
                                <MessageSquare className="h-4 w-4" />
                                Response Received
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
                            {response.submitted_at && (
                              <p className="text-xs text-purple-600 mt-1">
                                Received: {formatBackendDate(response.submitted_at)}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Verification Status */}
                        {verification.status === 'verified' && (
                          <div className="bg-green-50 rounded-lg p-3 border border-green-200">
                            <p className="text-sm font-medium text-green-700 flex items-center gap-2">
                              <CheckCircle className="h-4 w-4" />
                              Verified
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

                        {/* Actions */}
                        {status !== 'verified' && declared.email && (
                          <div className="pt-2 border-t space-y-2">
                            {status === 'declared' || status === 'sent' ? (
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
                                {status === 'sent' ? 'Resend Request' : 'Send Request'}
                              </Button>
                            ) : status === 'response_received' ? (
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
                                    Verify
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="destructive"
                                    className="flex-1 rounded-lg"
                                    onClick={() => openVerifyDialog(refNum, 'reject')}
                                    data-testid={`reject-reference-btn-${refNum}`}
                                  >
                                    <XCircle className="h-4 w-4 mr-2" />
                                    Reject
                                  </Button>
                                </div>
                              </>
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

          {/* Summary */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="font-medium text-sm mb-2">Reference Requirements</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>- Minimum 2 professional references required</li>
              <li>- References should cover recent employment history</li>
              <li>- At least one must be from the most recent employer</li>
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
                    Already verified
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
                  Verify Reference
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
                  Verify Reference
                </>
              ) : (
                <>
                  <XCircle className="h-5 w-5 text-red-600" />
                  Reject Reference
                </>
              )}
            </DialogTitle>
            <DialogDescription>
              {verifyAction === 'verify' 
                ? 'Confirm that this reference meets NHS employment standards.'
                : 'Provide a reason for rejecting this reference.'}
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
              {verifyAction === 'verify' ? 'Verify Reference' : 'Reject Reference'}
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
