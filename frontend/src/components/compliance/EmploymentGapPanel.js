import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../ui/alert-dialog';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Loader2,
  CalendarDays,
  Building2,
  MessageSquare,
  FileText,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  HelpCircle,
  Upload
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { formatBackendDate } from '../../lib/dateUtils';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

// Gap status styling
const GAP_STATUS_STYLES = {
  pending: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', icon: Clock, label: 'Awaiting Explanation' },
  explained: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', icon: MessageSquare, label: 'Awaiting Verification' },
  reopened: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', icon: AlertTriangle, label: 'Reopened' },
  verified: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', icon: CheckCircle2, label: 'Verified' },
  rejected: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', icon: XCircle, label: 'Rejected' },
  needs_more_info: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', icon: HelpCircle, label: 'More Info Needed' }
};

const formatGapBoundary = (value) => {
  if (!value) return 'Not available';
  if (value === 'present') return 'Present';
  return formatBackendDate(value, { format: 'medium' });
};

const getExplanationActionLabel = (gap) => (
  gap?.status === 'pending' ? 'Submit Explanation' : 'Update Explanation'
);

const getGapId = (gap) => gap?.id || gap?.gap_id;

const getGapSourceLabel = (gap) => {
  if (gap?.source === 'cv_review') return 'CV review';
  if (gap?.source) return gap.source.replace(/_/g, ' ');
  return 'Employment history';
};

/**
 * EmploymentGapPanel - Displays and manages employment gap verification
 * 
 * Shows:
 * - Detected employment gaps
 * - Gap explanations and status
 * - Admin actions (verify, reject, request info)
 */
export default function EmploymentGapPanel({
  employeeId,
  employeeName,
  initialData,
  isAdmin = false,
  onGapUpdate
}) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(!initialData);
  const [gapData, setGapData] = useState(initialData);
  const [expandedGaps, setExpandedGaps] = useState({});
  
  // Dialog states
  const [explainDialogOpen, setExplainDialogOpen] = useState(false);
  const [verifyDialogOpen, setVerifyDialogOpen] = useState(false);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [requestInfoDialogOpen, setRequestInfoDialogOpen] = useState(false);
  const [reopenDialogOpen, setReopenDialogOpen] = useState(false);
  const [selectedGap, setSelectedGap] = useState(null);
  
  // Form states
  const [explanation, setExplanation] = useState('');
  const [gapReason, setGapReason] = useState('');
  const [gapDocument, setGapDocument] = useState(null);
  const [verifyNotes, setVerifyNotes] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');
  const [infoRequest, setInfoRequest] = useState('');
  const [reopenReason, setReopenReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Fetch gap data
  const fetchGaps = useCallback(async () => {
    if (!employeeId) return;
    
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/employment-gaps`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setGapData(response.data);
    } catch (err) {
      console.error('Error fetching employment gaps:', err);
      if (err.response?.status !== 404) {
        toast.error('Failed to load employment gaps');
      }
    } finally {
      setLoading(false);
    }
  }, [employeeId, token]);
  
  useEffect(() => {
    if (!initialData) {
      fetchGaps();
    }
  }, [fetchGaps, initialData]);
  
  // Toggle gap expansion
  const toggleGap = (gapId) => {
    setExpandedGaps(prev => ({
      ...prev,
      [gapId]: !prev[gapId]
    }));
  };
  
  // Submit explanation
  const handleSubmitExplanation = async () => {
    if (!selectedGap || !explanation.trim() || !gapReason) return;
    
    setIsSubmitting(true);
    try {
      // Build explanation with reason
      const fullExplanation = `[${gapReason.replace('_', ' ').toUpperCase()}] ${explanation.trim()}`;
      
      await axios.post(
        `${API}/employees/${employeeId}/employment-gaps/${getGapId(selectedGap)}/explain`,
        null,
        { 
          params: { 
            explanation: fullExplanation,
            reason_type: gapReason
          },
          headers: { Authorization: `Bearer ${token}` } 
        }
      );
      
      // Upload supporting document if provided
      if (gapDocument) {
        const formData = new FormData();
        formData.append('file', gapDocument);
        formData.append('gap_id', getGapId(selectedGap));
        formData.append('document_type', 'gap_supporting_document');
        
        try {
          await axios.post(
            `${API}/employees/${employeeId}/employment-gaps/${getGapId(selectedGap)}/upload-document`,
            formData,
            { headers: { Authorization: `Bearer ${token}` } }
          );
        } catch (uploadErr) {
          console.error('Failed to upload supporting document:', uploadErr);
          // Don't fail the whole operation if doc upload fails
        }
      }
      
      toast.success('Gap explanation submitted');
      setExplainDialogOpen(false);
      setExplanation('');
      setGapReason('');
      setGapDocument(null);
      setSelectedGap(null);
      fetchGaps();
      onGapUpdate?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit explanation');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Verify gap
  const handleVerifyGap = async () => {
    if (!selectedGap) return;
    
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/employment-gaps/${getGapId(selectedGap)}/verify`,
        null,
        { 
          params: { approved: true, notes: verifyNotes.trim() || null },
          headers: { Authorization: `Bearer ${token}` } 
        }
      );
      
      toast.success('Gap explanation verified');
      setVerifyDialogOpen(false);
      setVerifyNotes('');
      setSelectedGap(null);
      fetchGaps();
      onGapUpdate?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify gap');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Reject gap
  const handleRejectGap = async () => {
    if (!selectedGap || !rejectionReason.trim()) return;
    
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/employment-gaps/${getGapId(selectedGap)}/verify`,
        null,
        { 
          params: { approved: false, rejection_reason: rejectionReason.trim() },
          headers: { Authorization: `Bearer ${token}` } 
        }
      );
      
      toast.success('Gap explanation rejected');
      setRejectDialogOpen(false);
      setRejectionReason('');
      setSelectedGap(null);
      fetchGaps();
      onGapUpdate?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject gap');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Request more info
  const handleRequestInfo = async () => {
    if (!selectedGap || !infoRequest.trim()) return;
    
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/employment-gaps/${getGapId(selectedGap)}/request-info`,
        null,
        { 
          params: { request_message: infoRequest.trim() },
          headers: { Authorization: `Bearer ${token}` } 
        }
      );
      
      toast.success('Information request sent');
      setRequestInfoDialogOpen(false);
      setInfoRequest('');
      setSelectedGap(null);
      fetchGaps();
      onGapUpdate?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send request');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReopenGap = async () => {
    if (!selectedGap || !reopenReason.trim()) return;

    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/employment-gaps/${getGapId(selectedGap)}/reopen`,
        { reason: reopenReason.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      toast.success('Gap reopened for fresh review');
      setReopenDialogOpen(false);
      setReopenReason('');
      setSelectedGap(null);
      fetchGaps();
      onGapUpdate?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reopen gap');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Loading state
  if (loading) {
    return (
      <Card className="border-dashed" data-testid="employment-gap-panel-loading">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="ml-2 text-gray-500">Loading employment gaps...</span>
        </CardContent>
      </Card>
    );
  }
  
  if (!gapData) {
    return null;
  }
  
  const { has_gaps, gaps, evaluation } = gapData;
  
  // No gaps - show success state
  if (!has_gaps || !gaps || gaps.length === 0) {
    return (
      <Card className="border-emerald-200 bg-emerald-50/30" data-testid="employment-gap-panel-no-gaps">
        <CardContent className="p-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          </div>
          <div>
            <p className="font-medium text-emerald-800">No detected gaps in dated employment history</p>
            <p className="text-sm text-emerald-600">
              This confirms gap detection only. 10-year coverage is assessed separately.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <>
      <Card data-testid="employment-gap-panel">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <CalendarDays className="h-5 w-5 text-amber-600" />
                Employment Gap Verification
              </CardTitle>
              <CardDescription>
                {evaluation?.total_gaps || gaps.length} gap(s) detected • {evaluation?.verified_count || 0} verified
              </CardDescription>
            </div>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchGaps}
              disabled={loading}
              data-testid="refresh-gaps-btn"
            >
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            </Button>
          </div>
          
          {/* Summary badges */}
          <div className="flex flex-wrap gap-2 mt-3">
            {evaluation?.pending_count > 0 && (
              <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                {evaluation.pending_count} awaiting explanation
              </Badge>
            )}
            {evaluation?.explained_count > 0 && (
              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                {evaluation.explained_count} awaiting verification
              </Badge>
            )}
            {evaluation?.rejected_count > 0 && (
              <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                {evaluation.rejected_count} rejected
              </Badge>
            )}
            {evaluation?.verified_count > 0 && (
              <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                {evaluation.verified_count} verified
              </Badge>
            )}
            {evaluation?.reopened_count > 0 && (
              <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">
                {evaluation.reopened_count} reopened
              </Badge>
            )}
          </div>
        </CardHeader>
        
        <CardContent className="space-y-3">
          {gaps.map((gap) => {
            const status = gap.status || 'pending';
            const gapId = getGapId(gap);
            const style = GAP_STATUS_STYLES[status] || GAP_STATUS_STYLES.pending;
            const StatusIcon = style.icon;
            const isExpanded = expandedGaps[gapId];
            
            return (
              <div
                key={gapId}
                className={cn(
                  "rounded-lg border p-4 transition-colors",
                  style.bg, style.border
                )}
                data-testid={`gap-card-${gapId}`}
              >
                {/* Gap Header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn("w-8 h-8 rounded-full flex items-center justify-center", style.bg)}>
                      <StatusIcon className={cn("h-4 w-4", style.text)} />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">
                        {gap.duration_months || 0} month gap
                      </p>
                      <p className="text-sm text-gray-600">
                        {gap.gap_start === 'present' 
                          ? 'From present' 
                          : formatBackendDate(gap.gap_start, { format: 'medium' })}
                        {' → '}
                        {gap.gap_end === 'present' 
                          ? 'Present' 
                          : formatBackendDate(gap.gap_end, { format: 'medium' })}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={cn(style.bg, style.text, style.border)}>
                      {style.label}
                    </Badge>
                    <Badge variant="outline" className="bg-white text-gray-600 border-gray-200">
                      Source: {getGapSourceLabel(gap)}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleGap(gapId)}
                      className="h-8 w-8 p-0"
                    >
                      {isExpanded ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
                
                {/* Expanded Details */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-gray-200 space-y-4">
                    {/* Employment context */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="p-3 bg-white rounded border">
                        <p className="text-gray-500 text-xs mb-1">Previous Employment</p>
                        <p className="font-medium">{gap.previous_employment?.company || 'Unknown'}</p>
                        <p className="text-gray-600">{gap.previous_employment?.role}</p>
                        <p className="text-xs text-gray-500">
                          Ended: {formatBackendDate(gap.previous_employment?.end_date, { format: 'short' })}
                        </p>
                      </div>
                      <div className="p-3 bg-white rounded border">
                        <p className="text-gray-500 text-xs mb-1">Next Employment</p>
                        <p className="font-medium">{gap.next_employment?.company || 'Unknown'}</p>
                        <p className="text-gray-600">{gap.next_employment?.role}</p>
                        <p className="text-xs text-gray-500">
                          Started: {formatBackendDate(gap.next_employment?.start_date, { format: 'short' })}
                        </p>
                      </div>
                    </div>
                    
                    {/* Explanation */}
                    {gap.explanation && (
                      <div className="p-3 bg-white rounded border">
                        <p className="text-gray-500 text-xs mb-1">Explanation</p>
                        <p className="text-gray-800">{gap.explanation}</p>
                        {gap.explanation_provided_at && (
                          <p className="text-xs text-gray-500 mt-2">
                            Provided: {formatBackendDate(gap.explanation_provided_at, { format: 'medium' })}
                          </p>
                        )}
                      </div>
                    )}

                    {(gap.evidence_document_id || gap.verification_notes || gap.verified_at) && (
                      <div className="p-3 bg-white rounded border">
                        <p className="text-gray-500 text-xs mb-1">Decision Trail</p>
                        {gap.evidence_document_id && (
                          <p className="text-sm text-gray-800">
                            Evidence attached: {gap.evidence_document_id}
                          </p>
                        )}
                        {gap.verification_notes && (
                          <p className="text-sm text-gray-800">
                            Verification notes: {gap.verification_notes}
                          </p>
                        )}
                        {gap.verified_at && (
                          <p className="text-xs text-gray-500 mt-2">
                            Verified by {gap.verified_by_name || 'admin'} on {formatBackendDate(gap.verified_at, { format: 'medium' })}
                          </p>
                        )}
                      </div>
                    )}
                    
                    {/* Rejection reason */}
                    {status === 'rejected' && gap.rejection_reason && (
                      <div className="p-3 bg-red-50 rounded border border-red-100">
                        <p className="text-red-700 text-xs mb-1">Rejection Reason</p>
                        <p className="text-red-800">{gap.rejection_reason}</p>
                      </div>
                    )}

                    {status === 'reopened' && (
                      <div className="p-3 bg-orange-50 rounded border border-orange-100">
                        <p className="text-orange-700 text-xs mb-1">Reopened For Review</p>
                        {gap.reopen_reason && (
                          <p className="text-orange-900 text-sm">{gap.reopen_reason}</p>
                        )}
                        <p className="text-xs text-orange-800 mt-2">
                          {gap.reopened_by_name || 'Admin'}
                          {gap.reopened_at ? ` reopened this gap on ${formatBackendDate(gap.reopened_at, { format: 'medium' })}` : ' reopened this gap for fresh review.'}
                        </p>
                      </div>
                    )}
                    
                    {/* Info request */}
                    {status === 'needs_more_info' && gap.info_request_message && (
                      <div className="p-3 bg-purple-50 rounded border border-purple-100">
                        <p className="text-purple-700 text-xs mb-1">Information Requested</p>
                        <p className="text-purple-800">{gap.info_request_message}</p>
                      </div>
                    )}
                    
                    {/* Actions */}
                    <div className="flex flex-wrap gap-2">
                      {/* Applicant/Employee actions */}
                      {(status === 'pending' || status === 'rejected' || status === 'needs_more_info' || status === 'reopened') && (
                        <Button
                          size="sm"
                          onClick={() => {
                            setSelectedGap(gap);
                            setExplanation(gap.explanation || '');
                            setGapReason(gap.reason_type || '');
                            setExplainDialogOpen(true);
                          }}
                          data-testid={`explain-gap-btn-${gapId}`}
                        >
                          <MessageSquare className="h-4 w-4 mr-1.5" />
                          {status === 'pending' ? 'Explain Gap' : 'Update Explanation'}
                        </Button>
                      )}
                      
                      {/* Admin actions */}
                      {isAdmin && status === 'explained' && (
                        <>
                          <Button
                            size="sm"
                            className="bg-emerald-600 hover:bg-emerald-700"
                            onClick={() => {
                              setSelectedGap(gap);
                              setVerifyDialogOpen(true);
                            }}
                            data-testid={`verify-gap-btn-${gapId}`}
                          >
                            <CheckCircle2 className="h-4 w-4 mr-1.5" />
                            Verify
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-red-300 text-red-700 hover:bg-red-50"
                            onClick={() => {
                              setSelectedGap(gap);
                              setRejectDialogOpen(true);
                            }}
                            data-testid={`reject-gap-btn-${gapId}`}
                          >
                            <XCircle className="h-4 w-4 mr-1.5" />
                            Reject
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              setSelectedGap(gap);
                              setRequestInfoDialogOpen(true);
                            }}
                            data-testid={`request-info-btn-${gapId}`}
                          >
                            <HelpCircle className="h-4 w-4 mr-1.5" />
                            Request Info
                          </Button>
                        </>
                      )}

                      {isAdmin && status === 'verified' && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-orange-300 text-orange-700 hover:bg-orange-50"
                          onClick={() => {
                            setSelectedGap(gap);
                            setReopenDialogOpen(true);
                          }}
                          data-testid={`reopen-gap-btn-${gapId}`}
                        >
                          <AlertTriangle className="h-4 w-4 mr-1.5" />
                          Reopen
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </CardContent>
      </Card>
      
      {/* Explain Gap Dialog */}
      <Dialog open={explainDialogOpen} onOpenChange={setExplainDialogOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="explain-gap-dialog">
          <DialogHeader>
            <DialogTitle>
              {selectedGap?.status === 'pending' ? 'Explain Employment Gap' : 'Update Employment Gap Explanation'}
            </DialogTitle>
            <DialogDescription>
              Provide a clear explanation for the {selectedGap?.duration_months} month gap in employment history.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4 space-y-4">
            {selectedGap && (
              <div className="space-y-3">
                <div className="rounded-lg border bg-slate-50 p-3">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Gap Period</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">
                    {formatGapBoundary(selectedGap.gap_start)} {' -> '} {formatGapBoundary(selectedGap.gap_end)}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">
                    {selectedGap.duration_months} month gap identified between recorded employments.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border bg-white p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Previous Employment</p>
                    <p className="mt-1 text-sm font-medium text-gray-900">
                      {selectedGap.previous_employment?.company || 'Not available'}
                    </p>
                    <p className="text-sm text-gray-600">
                      {selectedGap.previous_employment?.role || 'Role not recorded'}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      Ended: {formatGapBoundary(selectedGap.previous_employment?.end_date)}
                    </p>
                  </div>

                  <div className="rounded-lg border bg-white p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Next Employment</p>
                    <p className="mt-1 text-sm font-medium text-gray-900">
                      {selectedGap.next_employment?.company || 'Not available'}
                    </p>
                    <p className="text-sm text-gray-600">
                      {selectedGap.next_employment?.role || 'Role not recorded'}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      Started: {formatGapBoundary(selectedGap.next_employment?.start_date)}
                    </p>
                  </div>
                </div>

                {selectedGap.info_request_message && (
                  <div className="rounded-lg border border-purple-200 bg-purple-50 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-purple-700">Information Requested</p>
                    <p className="mt-1 text-sm text-purple-900">{selectedGap.info_request_message}</p>
                  </div>
                )}
              </div>
            )}

            {/* Reason Dropdown */}
            <div>
              <label className="text-sm font-medium block mb-2">
                Reason for gap <span className="text-red-500">*</span>
              </label>
              <select
                value={gapReason}
                onChange={(e) => setGapReason(e.target.value)}
                className="w-full h-10 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                data-testid="gap-reason-select"
              >
                <option value="">Select a reason...</option>
                <option value="career_break">Career break / Personal development</option>
                <option value="education">Education / Training</option>
                <option value="health">Health / Medical reasons</option>
                <option value="travel">Travel / Time abroad</option>
                <option value="unemployed">Unemployed / Job seeking</option>
                <option value="family">Family / Caring responsibilities</option>
                <option value="volunteering">Volunteering / Unpaid work</option>
                <option value="self_employed">Self-employment / Freelance</option>
                <option value="other">Other (please specify)</option>
              </select>
            </div>
            
            {/* Explanation Text */}
            <div>
              <label className="text-sm font-medium block mb-2">
                Explanation <span className="text-red-500">*</span>
              </label>
              <Textarea
                placeholder="Provide details about what you were doing during this period..."
                value={explanation}
                onChange={(e) => setExplanation(e.target.value)}
                rows={4}
                className="resize-none"
                data-testid="gap-explanation-textarea"
              />
              <p className="text-xs text-gray-500 mt-2">
                Explain what you were doing during this period and include enough detail for audit review.
              </p>
            </div>
            
            {/* Supporting Document Upload */}
            <div>
              <label className="text-sm font-medium block mb-2">
                Supporting document (optional)
              </label>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => document.getElementById('gap-doc-upload')?.click()}
                  className="text-xs"
                >
                  <Upload className="h-3.5 w-3.5 mr-1.5" />
                  Upload Document
                </Button>
                {gapDocument && (
                  <span className="text-xs text-gray-600">
                    {gapDocument.name}
                  </span>
                )}
              </div>
              <input
                id="gap-doc-upload"
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={(e) => setGapDocument(e.target.files?.[0] || null)}
                className="hidden"
              />
              <p className="text-xs text-gray-500 mt-1">
                Add evidence only if it supports this explanation, such as a study letter, medical note, travel record, or benefits/job-seeking document.
              </p>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setExplainDialogOpen(false);
              setGapReason('');
              setGapDocument(null);
            }}>
              Cancel
            </Button>
            <Button 
              onClick={handleSubmitExplanation}
              disabled={isSubmitting || !explanation.trim() || !gapReason}
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <MessageSquare className="h-4 w-4 mr-2" />
              )}
              {getExplanationActionLabel(selectedGap)}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={reopenDialogOpen} onOpenChange={setReopenDialogOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="reopen-gap-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-orange-700">
              <AlertTriangle className="h-5 w-5" />
              Reopen Verified Gap
            </DialogTitle>
            <DialogDescription>
              Reopen this gap when the previous verification should no longer stand.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4 space-y-3">
            <label className="text-sm font-medium">Reason for reopening <span className="text-red-500">*</span></label>
            <Textarea
              placeholder="Explain why this verified gap needs fresh review..."
              value={reopenReason}
              onChange={(e) => setReopenReason(e.target.value)}
              rows={4}
            />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setReopenDialogOpen(false);
              setReopenReason('');
            }}>
              Cancel
            </Button>
            <Button
              variant="outline"
              className="border-orange-300 text-orange-700 hover:bg-orange-50"
              onClick={handleReopenGap}
              disabled={isSubmitting || !reopenReason.trim()}
            >
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <AlertTriangle className="h-4 w-4 mr-2" />}
              Reopen Gap
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Verify Gap Dialog */}
      <AlertDialog open={verifyDialogOpen} onOpenChange={setVerifyDialogOpen}>
        <AlertDialogContent data-testid="verify-gap-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-emerald-700">
              <CheckCircle2 className="h-5 w-5" />
              Verify Gap Explanation?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This will approve the applicant's explanation for the {selectedGap?.duration_months} month gap.
            </AlertDialogDescription>
          </AlertDialogHeader>
          
          <div className="py-4">
            <label className="text-sm font-medium">Notes (optional)</label>
            <Textarea
              placeholder="Add any verification notes..."
              value={verifyNotes}
              onChange={(e) => setVerifyNotes(e.target.value)}
              rows={3}
              className="mt-2"
            />
          </div>
          
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleVerifyGap}
              disabled={isSubmitting}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Verify'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      
      {/* Reject Gap Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="reject-gap-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-700">
              <XCircle className="h-5 w-5" />
              Reject Gap Explanation
            </DialogTitle>
            <DialogDescription>
              The applicant will need to provide a revised explanation.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <label className="text-sm font-medium">Rejection Reason <span className="text-red-500">*</span></label>
            <Textarea
              placeholder="Explain why the explanation is not acceptable..."
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              rows={4}
              className="mt-2"
            />
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              variant="destructive"
              onClick={handleRejectGap}
              disabled={isSubmitting || !rejectionReason.trim()}
            >
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Reject Explanation'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Request Info Dialog */}
      <Dialog open={requestInfoDialogOpen} onOpenChange={setRequestInfoDialogOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="request-info-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <HelpCircle className="h-5 w-5 text-purple-600" />
              Request More Information
            </DialogTitle>
            <DialogDescription>
              Ask the applicant for additional details about this gap.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <label className="text-sm font-medium">Information Request <span className="text-red-500">*</span></label>
            <Textarea
              placeholder="What additional information do you need?"
              value={infoRequest}
              onChange={(e) => setInfoRequest(e.target.value)}
              rows={4}
              className="mt-2"
            />
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setRequestInfoDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleRequestInfo}
              disabled={isSubmitting || !infoRequest.trim()}
            >
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Send Request'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

