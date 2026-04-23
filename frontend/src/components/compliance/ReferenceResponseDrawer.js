/**
 * ReferenceResponseDrawer.js
 * 
 * Full-screen drawer for viewing reference details with 5 sections of truth:
 * 1. Declared Referee - What applicant entered
 * 2. Request Details - Request lifecycle (sent, viewed, responded)
 * 3. Submitted Response - What referee actually submitted
 * 4. Integrity Check - Did response match declared referee
 * 5. Review Outcome - What admin concluded
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { Textarea } from '../ui/textarea';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { 
  X, User, Building, Mail, Phone, Calendar, Send, Eye, Clock,
  CheckCircle, XCircle, AlertTriangle, Shield, Briefcase,
  ChevronDown, ChevronUp, Loader2, FileText, History, RefreshCw,
  ThumbsUp, ThumbsDown, MessageSquare, Star, UserCheck, Edit, RotateCcw,
  ExternalLink, Database, TestTube
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Section component for organizing content
 */
function Section({ title, icon: Icon, children, defaultOpen = true, badge, badgeColor = 'gray' }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          {Icon && <Icon className="h-5 w-5 text-gray-600" />}
          <span className="font-medium text-gray-900">{title}</span>
          {badge && (
            <Badge className={`text-xs bg-${badgeColor}-100 text-${badgeColor}-700 border-${badgeColor}-200`}>
              {badge}
            </Badge>
          )}
        </div>
        {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {isOpen && <div className="p-4 bg-white">{children}</div>}
    </div>
  );
}

/**
 * Info row component
 */
function InfoRow({ label, value, icon: Icon }) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-3 py-2">
      {Icon && <Icon className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />}
      <div className="min-w-0 flex-1">
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-sm text-gray-900">{value}</p>
      </div>
    </div>
  );
}

export default function ReferenceResponseDrawer({
  isOpen,
  onClose,
  employeeId,
  referenceNum,
  referenceData,
  onVerify,
  onReject,
  onOverrideMismatch,
  onRequestReplacement,
  onRefresh,
  isAuditor = false
}) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(referenceData || null);
  const [actionLoading, setActionLoading] = useState(null);
  const [overrideReason, setOverrideReason] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [replacementReason, setReplacementReason] = useState('');
  const [resetReason, setResetReason] = useState('');
  const [showOverrideForm, setShowOverrideForm] = useState(false);
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [showReplacementForm, setShowReplacementForm] = useState(false);
  const [showResetForm, setShowResetForm] = useState(false);
  const [showChangeRefereeForm, setShowChangeRefereeForm] = useState(false);
  const [showAlternativePathForm, setShowAlternativePathForm] = useState(false);
  const [mismatchReasonType, setMismatchReasonType] = useState('');
  const [alternativePathData, setAlternativePathData] = useState({
    attempts: [{ date: '', method: '', notes: '' }],
    reason: '',
    source: ''
  });
  const [changeRefereeData, setChangeRefereeData] = useState({
    name: '',
    job_title: '',
    company: '',
    email: '',
    phone: '',
    relationship: '',
    change_reason: ''
  });

  // Fetch normalized reference data
  useEffect(() => {
    if (isOpen && employeeId && referenceNum) {
      fetchReferenceData();
    }
  }, [isOpen, employeeId, referenceNum]);

  const fetchReferenceData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/references-normalized`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const ref = response.data.references.find(r => r.reference_number === referenceNum);
      setData(ref);
    } catch (err) {
      toast.error('Failed to load reference data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Handle verify action
  const handleVerify = async () => {
    setActionLoading('verify');
    try {
      await axios.post(
        `${API}/employees/${employeeId}/references/${referenceNum}/verify`,
        { action: 'verify' },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Reference ${referenceNum} verified`);
      fetchReferenceData();
      if (onVerify) onVerify(referenceNum);
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify reference');
    } finally {
      setActionLoading(null);
    }
  };

  // Handle reject action
  const handleReject = async () => {
    if (!rejectReason || rejectReason.trim().length < 10) {
      toast.error('Please provide a rejection reason (min 10 characters)');
      return;
    }
    setActionLoading('reject');
    try {
      await axios.post(
        `${API}/employees/${employeeId}/references/${referenceNum}/verify`,
        { action: 'reject', notes: rejectReason.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Reference ${referenceNum} rejected`);
      setShowRejectForm(false);
      setRejectReason('');
      fetchReferenceData();
      if (onReject) onReject(referenceNum);
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject reference');
    } finally {
      setActionLoading(null);
    }
  };

  // Handle override mismatch
  const handleOverrideMismatch = async () => {
    if (!mismatchReasonType) {
      toast.error('Please select a reason for the mismatch');
      return;
    }
    if (mismatchReasonType === 'other' && (!overrideReason || overrideReason.trim().length < 10)) {
      toast.error('Please provide an explanation (min 10 characters)');
      return;
    }
    
    setActionLoading('override');
    try {
      // Build full reason from type and additional notes
      const reasonLabels = {
        'earlier_employment': 'Referee is from earlier employment (not in declared history)',
        'personal_reference': 'Referee is personal/professional reference (not employment)',
        'employer_changed': 'Applicant has changed employers since declaration',
        'agency_reference': 'Reference is from recruitment agency, not direct employer',
        'name_change': 'Organisation has changed name since employment',
        'other': overrideReason.trim()
      };
      
      const fullReason = mismatchReasonType === 'other' 
        ? overrideReason.trim()
        : `${reasonLabels[mismatchReasonType]}${overrideReason.trim() ? '. Notes: ' + overrideReason.trim() : ''}`;
      
      await axios.post(
        `${API}/references/${employeeId}/${referenceNum}/override-mismatch`,
        { 
          override_reason: fullReason,
          reason_type: mismatchReasonType
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Mismatch overridden for Reference ${referenceNum}`);
      setShowOverrideForm(false);
      setOverrideReason('');
      setMismatchReasonType('');
      fetchReferenceData();
      if (onOverrideMismatch) onOverrideMismatch(referenceNum);
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to override mismatch');
    } finally {
      setActionLoading(null);
    }
  };

  // Handle request replacement
  const handleRequestReplacement = async () => {
    if (!replacementReason || replacementReason.trim().length < 10) {
      toast.error('Please provide a replacement reason (min 10 characters)');
      return;
    }
    setActionLoading('replacement');
    try {
      await axios.post(
        `${API}/employees/${employeeId}/references/${referenceNum}/verify`,
        { action: 'request_replacement', notes: replacementReason.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Replacement requested for Reference ${referenceNum}`);
      setShowReplacementForm(false);
      setReplacementReason('');
      fetchReferenceData();
      if (onRequestReplacement) onRequestReplacement(referenceNum);
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to request replacement');
    } finally {
      setActionLoading(null);
    }
  };

  // Handle reset reference
  const handleResetReference = async () => {
    if (!resetReason || resetReason.trim().length < 10) {
      toast.error('Please provide a reset reason (min 10 characters)');
      return;
    }
    setActionLoading('reset');
    try {
      await axios.post(
        `${API}/references/${employeeId}/${referenceNum}/reset`,
        { reset_reason: resetReason.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Reference ${referenceNum} has been reset`);
      setShowResetForm(false);
      setResetReason('');
      fetchReferenceData();
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reset reference');
    } finally {
      setActionLoading(null);
    }
  };

  // Handle change referee
  const handleChangeReferee = async () => {
    if (!changeRefereeData.change_reason || changeRefereeData.change_reason.trim().length < 10) {
      toast.error('Please provide a reason for the change (min 10 characters)');
      return;
    }
    
    // Check if any field changed
    const hasChanges = changeRefereeData.name || changeRefereeData.job_title || 
                       changeRefereeData.company || changeRefereeData.email || 
                       changeRefereeData.phone || changeRefereeData.relationship;
    if (!hasChanges) {
      toast.error('Please update at least one referee field');
      return;
    }
    
    setActionLoading('change_referee');
    try {
      await axios.post(
        `${API}/references/${employeeId}/${referenceNum}/change-referee`,
        changeRefereeData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Referee details updated for Reference ${referenceNum}`);
      setShowChangeRefereeForm(false);
      setChangeRefereeData({
        name: '', job_title: '', company: '', email: '', phone: '', relationship: '', change_reason: ''
      });
      fetchReferenceData();
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update referee details');
    } finally {
      setActionLoading(null);
    }
  };

  // Handle record alternative reference path
  const handleRecordAlternativePath = async () => {
    if (!alternativePathData.reason || alternativePathData.reason.trim().length < 20) {
      toast.error('Please provide a detailed reason (min 20 characters)');
      return;
    }
    if (!alternativePathData.source || alternativePathData.source.trim().length < 5) {
      toast.error('Please specify the alternative reference source');
      return;
    }
    
    // Validate attempts
    const validAttempts = alternativePathData.attempts.filter(a => a.date && a.method);
    if (validAttempts.length === 0) {
      toast.error('Please record at least one attempt to contact the original referee');
      return;
    }
    
    setActionLoading('alternative_path');
    try {
      await axios.post(
        `${API}/references/${employeeId}/${referenceNum}/record-alternative-path`,
        {
          original_referee_attempts: validAttempts.map(a => ({
            date: a.date,
            method: a.method,
            notes: a.notes || ''
          })),
          alternative_reason: alternativePathData.reason.trim(),
          alternative_source: alternativePathData.source.trim()
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Alternative reference path recorded for Reference ${referenceNum}`);
      setShowAlternativePathForm(false);
      setAlternativePathData({
        attempts: [{ date: '', method: '', notes: '' }],
        reason: '',
        source: ''
      });
      fetchReferenceData();
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to record alternative path');
    } finally {
      setActionLoading(null);
    }
  };

  // Add attempt to alternative path form
  const addAttempt = () => {
    setAlternativePathData(prev => ({
      ...prev,
      attempts: [...prev.attempts, { date: '', method: '', notes: '' }]
    }));
  };

  // Remove attempt from alternative path form
  const removeAttempt = (index) => {
    if (alternativePathData.attempts.length > 1) {
      setAlternativePathData(prev => ({
        ...prev,
        attempts: prev.attempts.filter((_, i) => i !== index)
      }));
    }
  };

  // Update attempt in alternative path form
  const updateAttempt = (index, field, value) => {
    setAlternativePathData(prev => ({
      ...prev,
      attempts: prev.attempts.map((a, i) => i === index ? { ...a, [field]: value } : a)
    }));
  };

  if (!isOpen) return null;

  const { 
    declared_referee, 
    request, 
    response, 
    integrity, 
    verification,
    alternative_path,
    lifecycle_status,
    summary_text,
    allowed_actions = [],
    reset_info
  } = data || {};

  // Response source label
  const getResponseSourceLabel = (source) => {
    switch (source) {
      case 'external_submission':
        return { label: 'External Submission', color: 'green', description: 'Submitted by referee via secure form' };
      case 'manual_entry':
        return { label: 'Manual Entry', color: 'blue', description: 'Entered manually by admin' };
      case 'test_data':
        return { label: 'Test Data', color: 'amber', description: 'Test/placeholder data - should be replaced' };
      default:
        return { label: 'Unknown', color: 'gray', description: 'Source not recorded' };
    }
  };

  // Status badge config
  const getStatusConfig = () => {
    switch (lifecycle_status) {
      case 'verified':
        return { label: 'Verified', color: 'green', icon: CheckCircle };
      case 'rejected':
        return { label: 'Rejected', color: 'red', icon: XCircle };
      case 'replacement_requested':
        return { label: 'Replacement Requested', color: 'amber', icon: RefreshCw };
      case 'awaiting_review':
      case 'awaiting_verification':
        return { label: 'Awaiting admin review', color: 'purple', icon: FileText };
      case 'responded':
        return { label: 'Response Received', color: 'blue', icon: FileText };
      case 'viewed':
        return { label: 'Viewed', color: 'blue', icon: Eye };
      case 'sent':
        return { label: 'Sent', color: 'blue', icon: Send };
      default:
        return { label: 'Not Sent', color: 'gray', icon: Clock };
    }
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" data-testid="reference-response-drawer">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="relative w-full max-w-2xl bg-white shadow-xl overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <User className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Reference {referenceNum}
                </h2>
                <p className="text-sm text-gray-500">
                  {declared_referee?.name || 'No referee declared'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge 
                className={`bg-${statusConfig.color}-100 text-${statusConfig.color}-700 border-${statusConfig.color}-200`}
                data-testid="reference-status-badge"
              >
                <StatusIcon className="h-3 w-3 mr-1" />
                {statusConfig.label}
              </Badge>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <X className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}

        {/* Content */}
        {!loading && data && (
          <div className="p-6 space-y-4">
            
            {/* ===== SECTION 1: DECLARED REFEREE ===== */}
            <Section title="Declared Referee" icon={User} defaultOpen={true}>
              {declared_referee ? (
                <div className="grid grid-cols-2 gap-4">
                  <InfoRow label="Full Name" value={declared_referee.name} icon={User} />
                  <InfoRow label="Job Title" value={declared_referee.job_title} icon={Briefcase} />
                  <InfoRow label="Organisation" value={declared_referee.organisation} icon={Building} />
                  <InfoRow label="Email" value={declared_referee.email} icon={Mail} />
                  <InfoRow label="Phone" value={declared_referee.phone} icon={Phone} />
                  <InfoRow label="Relationship" value={declared_referee.relationship} />
                  {declared_referee.employment_start && (
                    <InfoRow 
                      label="Employment Period" 
                      value={`${declared_referee.employment_start} - ${declared_referee.employment_end || 'Present'}`} 
                      icon={Calendar} 
                    />
                  )}
                  {declared_referee.from_cv !== undefined && (
                    <div className="col-span-2">
                      <Badge className={declared_referee.from_cv ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}>
                        {declared_referee.from_cv ? 'Matches CV' : 'Not from CV'}
                      </Badge>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No referee has been declared for this reference.</p>
              )}
            </Section>

            {/* ===== SECTION 2: REQUEST DETAILS ===== */}
            <Section title="Request Details" icon={Send} defaultOpen={true}>
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm text-gray-500">Request Status</span>
                  <Badge className={request?.status === 'not_sent' ? 'bg-gray-100' : 'bg-blue-100 text-blue-700'}>
                    {request?.status?.replace('_', ' ') || 'Not sent'}
                  </Badge>
                </div>
                {request?.sent_at && (
                  <div className="flex items-center justify-between py-2 border-b border-gray-100">
                    <span className="text-sm text-gray-500">Sent At</span>
                    <span className="text-sm text-gray-900">{formatBackendDate(request.sent_at, { format: 'medium' })}</span>
                  </div>
                )}
                {request?.viewed_at && (
                  <div className="flex items-center justify-between py-2 border-b border-gray-100">
                    <span className="text-sm text-gray-500">Viewed At</span>
                    <span className="text-sm text-gray-900">{formatBackendDate(request.viewed_at, { format: 'medium' })}</span>
                  </div>
                )}
                {request?.responded_at && (
                  <div className="flex items-center justify-between py-2 border-b border-gray-100">
                    <span className="text-sm text-gray-500">Response Received</span>
                    <span className="text-sm text-gray-900">{formatBackendDate(request.responded_at, { format: 'medium' })}</span>
                  </div>
                )}
                {request?.resend_count > 0 && (
                  <div className="flex items-center justify-between py-2 border-b border-gray-100">
                    <span className="text-sm text-gray-500">Resend Count</span>
                    <span className="text-sm text-gray-900">{request.resend_count}</span>
                  </div>
                )}
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm text-gray-500">Recipient Email</span>
                  <span className="text-sm text-gray-900">{request?.recipient_email || '-'}</span>
                </div>
              </div>
            </Section>

            {/* ===== SECTION 3: SUBMITTED RESPONSE ===== */}
            {response?.exists && (
              <Section 
                title="Submitted Response" 
                icon={FileText} 
                defaultOpen={true}
                badge="Response Received"
                badgeColor="green"
              >
                <div className="space-y-6">
                  {/* Response Source Indicator */}
                  {(() => {
                    const sourceInfo = getResponseSourceLabel(response.source);
                    const SourceIcon = response.source === 'external_submission' ? ExternalLink : 
                                       response.source === 'manual_entry' ? Database : 
                                       response.source === 'test_data' ? TestTube : Clock;
                    return (
                      <div className={`flex items-center gap-2 p-3 rounded-lg border bg-${sourceInfo.color}-50 border-${sourceInfo.color}-200`}>
                        <SourceIcon className={`h-4 w-4 text-${sourceInfo.color}-600`} />
                        <div>
                          <span className={`text-sm font-medium text-${sourceInfo.color}-800`}>
                            Response Source: {sourceInfo.label}
                          </span>
                          <p className={`text-xs text-${sourceInfo.color}-600`}>{sourceInfo.description}</p>
                        </div>
                      </div>
                    );
                  })()}
                  
                  {/* Responder Info */}
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Responder Details</p>
                    <div className="grid grid-cols-2 gap-4 p-3 bg-gray-50 rounded-lg">
                      <InfoRow label="Full Name" value={response.referee_full_name} icon={User} />
                      <InfoRow label="Email" value={response.referee_email} icon={Mail} />
                      <InfoRow label="Organisation" value={response.organisation} icon={Building} />
                      <InfoRow label="Job Title" value={response.job_title} icon={Briefcase} />
                      <InfoRow label="Relationship" value={response.relationship_to_applicant} />
                    </div>
                  </div>

                  {/* Employment Details */}
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Employment Details</p>
                    <div className="grid grid-cols-2 gap-4 p-3 bg-gray-50 rounded-lg">
                      <InfoRow label="Job Title Held" value={response.job_title_held} icon={Briefcase} />
                      <InfoRow 
                        label="Employment Period" 
                        value={response.employment_start && `${response.employment_start} - ${response.employment_end || 'Present'}`} 
                        icon={Calendar} 
                      />
                      <InfoRow label="Reason for Leaving" value={response.reason_for_leaving} />
                    </div>
                  </div>

                  {/* Performance Assessment */}
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Performance Assessment</p>
                    <div className="space-y-3 p-3 bg-gray-50 rounded-lg">
                      {response.performance_rating && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Performance Rating</span>
                          <div className="flex items-center gap-1">
                            {[1,2,3,4,5].map(i => (
                              <Star 
                                key={i} 
                                className={`h-4 w-4 ${i <= (response.performance_rating || 0) ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'}`} 
                              />
                            ))}
                          </div>
                        </div>
                      )}
                      {response.attendance_reliability && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Attendance & Reliability</span>
                          <Badge className="bg-blue-100 text-blue-700">{response.attendance_reliability}</Badge>
                        </div>
                      )}
                      {response.team_working && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Team Working</span>
                          <Badge className="bg-blue-100 text-blue-700">{response.team_working}</Badge>
                        </div>
                      )}
                      {response.overall_assessment && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Overall Assessment</span>
                          <Badge className="bg-purple-100 text-purple-700">{response.overall_assessment}</Badge>
                        </div>
                      )}
                      {response.would_rehire !== undefined && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Would Rehire?</span>
                          <Badge className={response.would_rehire ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                            {response.would_rehire ? (
                              <><ThumbsUp className="h-3 w-3 mr-1" />Yes</>
                            ) : (
                              <><ThumbsDown className="h-3 w-3 mr-1" />No</>
                            )}
                          </Badge>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Safeguarding */}
                  {(response.disciplinary_actions !== undefined || response.safeguarding_concerns !== undefined || response.suitable_for_vulnerable !== undefined) && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Safeguarding & Conduct</p>
                      <div className="space-y-3 p-3 bg-gray-50 rounded-lg">
                        {response.disciplinary_actions !== undefined && (
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-600">Disciplinary Actions</span>
                            <Badge className={!response.disciplinary_actions ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                              {response.disciplinary_actions ? 'Yes' : 'None'}
                            </Badge>
                          </div>
                        )}
                        {response.safeguarding_concerns !== undefined && (
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-600">Safeguarding Concerns</span>
                            <Badge className={!response.safeguarding_concerns ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                              {response.safeguarding_concerns ? 'Yes' : 'None'}
                            </Badge>
                          </div>
                        )}
                        {response.suitable_for_vulnerable !== undefined && (
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-600">Suitable for Vulnerable Adults</span>
                            <Badge className={response.suitable_for_vulnerable ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                              {response.suitable_for_vulnerable ? 'Yes' : 'No'}
                            </Badge>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Additional Comments */}
                  {response.additional_comments && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Additional Comments</p>
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">{response.additional_comments}</p>
                      </div>
                    </div>
                  )}
                </div>
              </Section>
            )}

            {/* ===== SECTION 4: INTEGRITY CHECK ===== */}
            {response?.exists && (
              <Section 
                title="Integrity Check" 
                icon={Shield}
                defaultOpen={integrity?.mismatch_detected}
                badge={integrity?.mismatch_detected ? (integrity?.override_applied ? 'Overridden' : 'Mismatch') : 'Matched'}
                badgeColor={integrity?.mismatch_detected ? (integrity?.override_applied ? 'blue' : 'amber') : 'green'}
              >
                <div className="space-y-4">
                  {/* Match Status Grid */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-3 bg-gray-50 rounded-lg text-center">
                      <p className="text-xs text-gray-500 mb-1">Email Match</p>
                      {integrity?.email_match === null ? (
                        <Badge className="bg-gray-100 text-gray-600">N/A</Badge>
                      ) : integrity?.email_match ? (
                        <Badge className="bg-green-100 text-green-700"><CheckCircle className="h-3 w-3 mr-1" />Match</Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-700"><XCircle className="h-3 w-3 mr-1" />Mismatch</Badge>
                      )}
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg text-center">
                      <p className="text-xs text-gray-500 mb-1">Name Match</p>
                      {integrity?.name_match === null ? (
                        <Badge className="bg-gray-100 text-gray-600">N/A</Badge>
                      ) : integrity?.name_match ? (
                        <Badge className="bg-green-100 text-green-700"><CheckCircle className="h-3 w-3 mr-1" />Match</Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-700"><XCircle className="h-3 w-3 mr-1" />Mismatch</Badge>
                      )}
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg text-center">
                      <p className="text-xs text-gray-500 mb-1">Organisation Match</p>
                      {integrity?.organisation_match === null ? (
                        <Badge className="bg-gray-100 text-gray-600">N/A</Badge>
                      ) : integrity?.organisation_match ? (
                        <Badge className="bg-green-100 text-green-700"><CheckCircle className="h-3 w-3 mr-1" />Match</Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-700"><XCircle className="h-3 w-3 mr-1" />Mismatch</Badge>
                      )}
                    </div>
                  </div>

                  {/* Mismatch Reasons */}
                  {integrity?.mismatch_reasons?.length > 0 && (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium text-amber-800">Mismatch Detected</p>
                          <ul className="mt-1 text-xs text-amber-700 list-disc ml-4">
                            {integrity.mismatch_reasons.map((reason, i) => (
                              <li key={i}>{reason}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Employment History Mismatch Warning */}
                  {integrity?.employment_mismatches?.length > 0 && (
                    <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg" data-testid="employment-mismatch-warning">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 text-orange-600 mt-0.5 flex-shrink-0" />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-orange-800">Employment History Discrepancy</p>
                          <p className="text-xs text-orange-600 mt-1 mb-2">
                            Reference dates/employer don't match employment records. Please review.
                          </p>
                          <div className="space-y-2">
                            {integrity.employment_mismatches.map((mismatch, i) => (
                              <div key={i} className="p-2 bg-white rounded border border-orange-100">
                                <div className="flex items-center gap-2 mb-1">
                                  <Badge className="text-[10px] bg-orange-100 text-orange-700 border-orange-200">
                                    {mismatch.type === 'reference_vs_application' ? 'Ref vs App' : 
                                     mismatch.type === 'reference_vs_normalized' ? 'Ref vs Record' :
                                     mismatch.type === 'response_vs_declared' ? 'Response vs Declared' : 'Mismatch'}
                                  </Badge>
                                  <span className="text-xs text-orange-700 font-medium">{mismatch.field}</span>
                                </div>
                                <p className="text-xs text-gray-700">{mismatch.message}</p>
                                {mismatch.employer && (
                                  <p className="text-xs text-gray-500 mt-1">Employer: {mismatch.employer}</p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Override Applied */}
                  {integrity?.override_applied && (
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-start gap-2">
                        <UserCheck className="h-4 w-4 text-blue-600 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium text-blue-800">Mismatch Overridden</p>
                          <p className="text-xs text-blue-700 mt-1">
                            Reason: {integrity.override_reason}
                          </p>
                          {integrity.override_by && (
                            <p className="text-xs text-blue-600 mt-1">
                              By {integrity.override_by} {integrity.override_at && `on ${formatBackendDate(integrity.override_at, { format: 'short' })}`}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Override Mismatch Form */}
                  {!isAuditor && integrity?.mismatch_detected && !integrity?.override_applied && allowed_actions.includes('override_mismatch') && (
                    <div>
                      {!showOverrideForm ? (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setShowOverrideForm(true)}
                          className="text-amber-600 border-amber-300 hover:bg-amber-50"
                          data-testid="show-override-form-btn"
                        >
                          <AlertTriangle className="h-4 w-4 mr-1" />
                          Override Mismatch
                        </Button>
                      ) : (
                        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-3">
                          <p className="text-sm font-medium text-amber-800">Reason for Mismatch (required)</p>
                          
                          {/* Mismatch Reason Dropdown */}
                          <div className="space-y-2">
                            <select
                              value={mismatchReasonType}
                              onChange={(e) => setMismatchReasonType(e.target.value)}
                              className="w-full h-9 px-3 text-sm border border-amber-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-amber-200"
                              data-testid="mismatch-reason-select"
                            >
                              <option value="">Select a reason...</option>
                              <option value="earlier_employment">Referee is from earlier employment (not in declared history)</option>
                              <option value="personal_reference">Referee is personal/professional reference (not employment)</option>
                              <option value="employer_changed">Applicant has changed employers since declaration</option>
                              <option value="agency_reference">Reference is from recruitment agency, not direct employer</option>
                              <option value="name_change">Organisation has changed name since employment</option>
                              <option value="other">Other (please specify)</option>
                            </select>
                          </div>
                          
                          <Textarea
                            value={overrideReason}
                            onChange={(e) => setOverrideReason(e.target.value)}
                            placeholder={mismatchReasonType === 'other' ? "Please explain why this mismatch is acceptable..." : "Additional notes (optional)..."}
                            className="min-h-[80px]"
                            data-testid="override-reason-input"
                          />
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              onClick={handleOverrideMismatch}
                              disabled={actionLoading === 'override' || !mismatchReasonType || (mismatchReasonType === 'other' && overrideReason.length < 10)}
                              className="bg-amber-600 hover:bg-amber-700 text-white"
                              data-testid="confirm-override-btn"
                            >
                              {actionLoading === 'override' ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Confirm Override'}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => { setShowOverrideForm(false); setOverrideReason(''); setMismatchReasonType(''); }}
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </Section>
            )}

            {/* ===== SECTION 5: REVIEW OUTCOME ===== */}
            <Section 
              title="Review Outcome" 
              icon={CheckCircle}
              defaultOpen={true}
              badge={verification?.status?.replace('_', ' ')}
              badgeColor={verification?.verified ? 'green' : verification?.rejected ? 'red' : 'gray'}
            >
              <div className="space-y-4">
                {/* Verified */}
                {verification?.verified && (
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-green-100 rounded-full">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      </div>
                      <div>
                        <p className="font-medium text-green-800">Reference Verified</p>
                        <p className="text-sm text-green-600">
                          {formatBackendDate(verification.verified_at, { format: 'medium' })} by {verification.verified_by}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Rejected */}
                {verification?.rejected && (
                  <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-red-100 rounded-full">
                        <XCircle className="h-5 w-5 text-red-600" />
                      </div>
                      <div>
                        <p className="font-medium text-red-800">Reference Rejected</p>
                        {verification.rejected_reason && (
                          <p className="text-sm text-red-700 mt-1">Reason: {verification.rejected_reason}</p>
                        )}
                        <p className="text-sm text-red-600 mt-1">
                          {formatBackendDate(verification.rejected_at, { format: 'medium' })} by {verification.rejected_by}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Replacement Requested */}
                {verification?.replacement_requested && (
                  <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-amber-100 rounded-full">
                        <RefreshCw className="h-5 w-5 text-amber-600" />
                      </div>
                      <div>
                        <p className="font-medium text-amber-800">Replacement Requested</p>
                        {verification.replacement_reason && (
                          <p className="text-sm text-amber-700 mt-1">Reason: {verification.replacement_reason}</p>
                        )}
                        <p className="text-sm text-amber-600 mt-1">
                          {formatBackendDate(verification.replacement_requested_at, { format: 'medium' })} by {verification.replacement_requested_by}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Pending Review */}
                {!verification?.verified && !verification?.rejected && response?.exists && (
                  <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-gray-100 rounded-full">
                        <Clock className="h-5 w-5 text-gray-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-800">Awaiting Review</p>
                        <p className="text-sm text-gray-600">Response received but not yet reviewed by admin</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                {!isAuditor && response?.exists && !verification?.verified && !verification?.rejected && (
                  <div className="flex flex-wrap gap-2 pt-2">
                    {/* Verify Button */}
                    {allowed_actions.includes('verify') && (
                      <Button
                        onClick={handleVerify}
                        disabled={actionLoading === 'verify' || (integrity?.mismatch_detected && !integrity?.override_applied)}
                        className="bg-green-600 hover:bg-green-700 text-white"
                        data-testid="verify-reference-btn"
                      >
                        {actionLoading === 'verify' ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <CheckCircle className="h-4 w-4 mr-1" />}
                        Verify Reference
                      </Button>
                    )}

                    {/* Reject Form */}
                    {allowed_actions.includes('reject') && (
                      <>
                        {!showRejectForm ? (
                          <Button
                            variant="outline"
                            onClick={() => setShowRejectForm(true)}
                            className="text-red-600 border-red-300 hover:bg-red-50"
                            data-testid="show-reject-form-btn"
                          >
                            <XCircle className="h-4 w-4 mr-1" />
                            Reject
                          </Button>
                        ) : (
                          <div className="w-full p-3 bg-red-50 border border-red-200 rounded-lg space-y-3">
                            <p className="text-sm font-medium text-red-800">Reject Reference</p>
                            <Textarea
                              value={rejectReason}
                              onChange={(e) => setRejectReason(e.target.value)}
                              placeholder="Reason for rejection (min 10 characters)..."
                              className="min-h-[80px]"
                              data-testid="reject-reason-input"
                            />
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                onClick={handleReject}
                                disabled={actionLoading === 'reject' || rejectReason.length < 10}
                                className="bg-red-600 hover:bg-red-700 text-white"
                                data-testid="confirm-reject-btn"
                              >
                                {actionLoading === 'reject' ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Confirm Rejection'}
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => { setShowRejectForm(false); setRejectReason(''); }}
                              >
                                Cancel
                              </Button>
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}

                {/* Request Replacement */}
                {!isAuditor && allowed_actions.includes('request_replacement') && (
                  <div className="pt-2 border-t border-gray-200">
                    {!showReplacementForm ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowReplacementForm(true)}
                        className="text-amber-600 border-amber-300 hover:bg-amber-50"
                        data-testid="show-replacement-form-btn"
                      >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Request Replacement Referee
                      </Button>
                    ) : (
                      <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-3">
                        <p className="text-sm font-medium text-amber-800">Request Replacement Referee</p>
                        <p className="text-xs text-amber-700">
                          This will clear the current reference and require the applicant to provide a new referee.
                        </p>
                        <Textarea
                          value={replacementReason}
                          onChange={(e) => setReplacementReason(e.target.value)}
                          placeholder="Reason for requesting replacement (min 10 characters)..."
                          className="min-h-[80px]"
                          data-testid="replacement-reason-input"
                        />
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={handleRequestReplacement}
                            disabled={actionLoading === 'replacement' || replacementReason.length < 10}
                            className="bg-amber-600 hover:bg-amber-700 text-white"
                            data-testid="confirm-replacement-btn"
                          >
                            {actionLoading === 'replacement' ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Confirm Replacement'}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => { setShowReplacementForm(false); setReplacementReason(''); }}
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Reset Reference */}
                {!isAuditor && allowed_actions.includes('reset_reference') && (
                  <div className="pt-2 border-t border-gray-200">
                    {!showResetForm ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowResetForm(true)}
                        className="text-gray-600 border-gray-300 hover:bg-gray-50"
                        data-testid="show-reset-form-btn"
                      >
                        <RotateCcw className="h-4 w-4 mr-1" />
                        Reset Reference
                      </Button>
                    ) : (
                      <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg space-y-3">
                        <p className="text-sm font-medium text-gray-800">Reset Reference</p>
                        <p className="text-xs text-gray-600">
                          This will clear the response, verification status, and request history. Referee details will be preserved.
                        </p>
                        <Textarea
                          value={resetReason}
                          onChange={(e) => setResetReason(e.target.value)}
                          placeholder="Reason for reset (min 10 characters)..."
                          className="min-h-[80px]"
                          data-testid="reset-reason-input"
                        />
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={handleResetReference}
                            disabled={actionLoading === 'reset' || resetReason.length < 10}
                            className="bg-gray-600 hover:bg-gray-700 text-white"
                            data-testid="confirm-reset-btn"
                          >
                            {actionLoading === 'reset' ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Confirm Reset'}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => { setShowResetForm(false); setResetReason(''); }}
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Change Referee Details */}
                {!isAuditor && allowed_actions.includes('change_referee') && (
                  <div className="pt-2 border-t border-gray-200">
                    {!showChangeRefereeForm ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          // Pre-fill with current values
                          setChangeRefereeData({
                            name: declared_referee?.name || '',
                            job_title: declared_referee?.job_title || '',
                            company: declared_referee?.organisation || '',
                            email: declared_referee?.email || '',
                            phone: declared_referee?.phone || '',
                            relationship: declared_referee?.relationship || '',
                            change_reason: ''
                          });
                          setShowChangeRefereeForm(true);
                        }}
                        className="text-blue-600 border-blue-300 hover:bg-blue-50"
                        data-testid="show-change-referee-form-btn"
                      >
                        <Edit className="h-4 w-4 mr-1" />
                        Change Referee Details
                      </Button>
                    ) : (
                      <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg space-y-3">
                        <p className="text-sm font-medium text-blue-800">Change Referee Details</p>
                        <p className="text-xs text-blue-700">
                          Update referee information. Leave fields blank to keep current values.
                        </p>
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <Label className="text-xs">Full Name</Label>
                            <Input
                              value={changeRefereeData.name}
                              onChange={(e) => setChangeRefereeData({...changeRefereeData, name: e.target.value})}
                              placeholder={declared_referee?.name || 'Enter name'}
                              className="h-8 text-sm"
                              data-testid="change-referee-name"
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Job Title</Label>
                            <Input
                              value={changeRefereeData.job_title}
                              onChange={(e) => setChangeRefereeData({...changeRefereeData, job_title: e.target.value})}
                              placeholder={declared_referee?.job_title || 'Enter job title'}
                              className="h-8 text-sm"
                              data-testid="change-referee-job-title"
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Organisation</Label>
                            <Input
                              value={changeRefereeData.company}
                              onChange={(e) => setChangeRefereeData({...changeRefereeData, company: e.target.value})}
                              placeholder={declared_referee?.organisation || 'Enter organisation'}
                              className="h-8 text-sm"
                              data-testid="change-referee-company"
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Email</Label>
                            <Input
                              type="email"
                              value={changeRefereeData.email}
                              onChange={(e) => setChangeRefereeData({...changeRefereeData, email: e.target.value})}
                              placeholder={declared_referee?.email || 'Enter email'}
                              className="h-8 text-sm"
                              data-testid="change-referee-email"
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Phone</Label>
                            <Input
                              value={changeRefereeData.phone}
                              onChange={(e) => setChangeRefereeData({...changeRefereeData, phone: e.target.value})}
                              placeholder={declared_referee?.phone || 'Enter phone'}
                              className="h-8 text-sm"
                              data-testid="change-referee-phone"
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Relationship</Label>
                            <Input
                              value={changeRefereeData.relationship}
                              onChange={(e) => setChangeRefereeData({...changeRefereeData, relationship: e.target.value})}
                              placeholder={declared_referee?.relationship || 'Enter relationship'}
                              className="h-8 text-sm"
                              data-testid="change-referee-relationship"
                            />
                          </div>
                        </div>
                        <div>
                          <Label className="text-xs">Reason for Change *</Label>
                          <Textarea
                            value={changeRefereeData.change_reason}
                            onChange={(e) => setChangeRefereeData({...changeRefereeData, change_reason: e.target.value})}
                            placeholder="Why are you changing these details? (min 10 characters)"
                            className="min-h-[60px]"
                            data-testid="change-referee-reason"
                          />
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={handleChangeReferee}
                            disabled={actionLoading === 'change_referee' || changeRefereeData.change_reason.length < 10}
                            className="bg-blue-600 hover:bg-blue-700 text-white"
                            data-testid="confirm-change-referee-btn"
                          >
                            {actionLoading === 'change_referee' ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save Changes'}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => { 
                              setShowChangeRefereeForm(false); 
                              setChangeRefereeData({
                                name: '', job_title: '', company: '', email: '', phone: '', relationship: '', change_reason: ''
                              }); 
                            }}
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </Section>

            {/* ===== SECTION 6: ALTERNATIVE REFERENCE PATH ===== */}
            {(alternative_path?.is_alternative || allowed_actions.includes('record_alternative_path')) && (
              <Section 
                title="Alternative Reference Path" 
                icon={History}
                defaultOpen={alternative_path?.is_alternative}
                badge={alternative_path?.is_alternative ? 'Alternative' : 'Available'}
                badgeColor={alternative_path?.is_alternative ? 'blue' : 'gray'}
              >
                <div className="space-y-4">
                  {/* Show recorded alternative path */}
                  {alternative_path?.is_alternative && (
                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-blue-100 rounded-full">
                          <History className="h-5 w-5 text-blue-600" />
                        </div>
                        <div className="flex-1">
                          <p className="font-medium text-blue-800">Alternative Reference Used</p>
                          <p className="text-sm text-blue-700 mt-1">
                            <strong>Source:</strong> {alternative_path.alternative_source}
                          </p>
                          <p className="text-sm text-blue-700 mt-1">
                            <strong>Reason:</strong> {alternative_path.alternative_reason}
                          </p>
                          {alternative_path.alternative_recorded_by && (
                            <p className="text-xs text-blue-600 mt-2">
                              Recorded by {alternative_path.alternative_recorded_by} 
                              {alternative_path.alternative_recorded_at && ` on ${formatBackendDate(alternative_path.alternative_recorded_at, { format: 'short' })}`}
                            </p>
                          )}
                          
                          {/* Attempts made to original referee */}
                          {alternative_path.original_referee_attempts?.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-blue-200">
                              <p className="text-xs font-medium text-blue-800 mb-2">Attempts to Contact Original Referee</p>
                              <div className="space-y-2">
                                {alternative_path.original_referee_attempts.map((attempt, i) => (
                                  <div key={i} className="flex items-center gap-2 text-xs text-blue-700">
                                    <span className="font-medium">{attempt.date}</span>
                                    <span>•</span>
                                    <span>{attempt.method}</span>
                                    {attempt.notes && (
                                      <>
                                        <span>•</span>
                                        <span className="text-blue-600">{attempt.notes}</span>
                                      </>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Record Alternative Path Form */}
                  {!isAuditor && !alternative_path?.is_alternative && allowed_actions.includes('record_alternative_path') && (
                    <div>
                      {!showAlternativePathForm ? (
                        <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
                          <p className="text-sm text-gray-600 mb-3">
                            If the original referee is unresponsive after multiple attempts, you can record an alternative reference path.
                          </p>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setShowAlternativePathForm(true)}
                            className="text-blue-600 border-blue-300 hover:bg-blue-50"
                            data-testid="show-alternative-path-form-btn"
                          >
                            <History className="h-4 w-4 mr-1" />
                            Record Alternative Path
                          </Button>
                        </div>
                      ) : (
                        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg space-y-4">
                          <div>
                            <p className="text-sm font-medium text-blue-800 mb-1">Record Alternative Reference Path</p>
                            <p className="text-xs text-blue-600">
                              Document attempts to contact the original referee and record the alternative reference source.
                            </p>
                          </div>

                          {/* Attempts Section */}
                          <div className="space-y-3">
                            <Label className="text-xs font-medium text-blue-800">Attempts to Contact Original Referee *</Label>
                            {alternativePathData.attempts.map((attempt, i) => (
                              <div key={i} className="p-3 bg-white border border-blue-200 rounded-lg space-y-2">
                                <div className="flex items-center justify-between">
                                  <span className="text-xs font-medium text-gray-600">Attempt {i + 1}</span>
                                  {alternativePathData.attempts.length > 1 && (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => removeAttempt(i)}
                                      className="h-6 px-2 text-red-500 hover:text-red-600"
                                    >
                                      Remove
                                    </Button>
                                  )}
                                </div>
                                <div className="grid grid-cols-2 gap-2">
                                  <div>
                                    <Label className="text-xs">Date *</Label>
                                    <Input
                                      type="date"
                                      value={attempt.date}
                                      onChange={(e) => updateAttempt(i, 'date', e.target.value)}
                                      className="h-8 text-sm"
                                      data-testid={`attempt-date-${i}`}
                                    />
                                  </div>
                                  <div>
                                    <Label className="text-xs">Method *</Label>
                                    <select
                                      value={attempt.method}
                                      onChange={(e) => updateAttempt(i, 'method', e.target.value)}
                                      className="w-full h-8 text-sm border border-gray-200 rounded-md px-2"
                                      data-testid={`attempt-method-${i}`}
                                    >
                                      <option value="">Select method...</option>
                                      <option value="Email">Email</option>
                                      <option value="Phone call">Phone call</option>
                                      <option value="Letter">Letter</option>
                                      <option value="Text message">Text message</option>
                                      <option value="In-person visit">In-person visit</option>
                                    </select>
                                  </div>
                                </div>
                                <div>
                                  <Label className="text-xs">Notes (optional)</Label>
                                  <Input
                                    value={attempt.notes}
                                    onChange={(e) => updateAttempt(i, 'notes', e.target.value)}
                                    placeholder="e.g., No response, voicemail left, etc."
                                    className="h-8 text-sm"
                                    data-testid={`attempt-notes-${i}`}
                                  />
                                </div>
                              </div>
                            ))}
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={addAttempt}
                              className="text-blue-600 border-blue-300 hover:bg-blue-100"
                              data-testid="add-attempt-btn"
                            >
                              + Add Another Attempt
                            </Button>
                          </div>

                          {/* Alternative Source */}
                          <div>
                            <Label className="text-xs font-medium text-blue-800">Alternative Reference Source *</Label>
                            <Input
                              value={alternativePathData.source}
                              onChange={(e) => setAlternativePathData(prev => ({ ...prev, source: e.target.value }))}
                              placeholder="e.g., Different employer, HR department, etc."
                              className="h-9 mt-1"
                              data-testid="alternative-source-input"
                            />
                          </div>

                          {/* Reason */}
                          <div>
                            <Label className="text-xs font-medium text-blue-800">Reason for Alternative Path *</Label>
                            <Textarea
                              value={alternativePathData.reason}
                              onChange={(e) => setAlternativePathData(prev => ({ ...prev, reason: e.target.value }))}
                              placeholder="Explain why the alternative reference path was needed (min 20 characters)..."
                              className="min-h-[80px] mt-1"
                              data-testid="alternative-reason-input"
                            />
                            {alternativePathData.reason.length > 0 && alternativePathData.reason.length < 20 && (
                              <p className="text-xs text-amber-600 mt-1">Minimum 20 characters required</p>
                            )}
                          </div>

                          {/* Action Buttons */}
                          <div className="flex gap-2 pt-2">
                            <Button
                              size="sm"
                              onClick={handleRecordAlternativePath}
                              disabled={actionLoading === 'alternative_path'}
                              className="bg-blue-600 hover:bg-blue-700 text-white"
                              data-testid="confirm-alternative-path-btn"
                            >
                              {actionLoading === 'alternative_path' ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                              Record Alternative Path
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setShowAlternativePathForm(false);
                                setAlternativePathData({
                                  attempts: [{ date: '', method: '', notes: '' }],
                                  reason: '',
                                  source: ''
                                });
                              }}
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </Section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
