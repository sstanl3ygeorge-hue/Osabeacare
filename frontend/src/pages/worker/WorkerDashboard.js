import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Progress } from '../../components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { 
  CheckCircle, AlertCircle, Clock, Upload, FileText, 
  LogOut, Loader2, AlertTriangle, Calendar, RefreshCw,
  Shield, X, PenTool, Lock, Download, Eye, User, Award, Bell, ChevronDown, ChevronUp,
  ShieldCheck, Circle, Plus, Trash2
} from 'lucide-react';
import { toast } from 'sonner';
import SignaturePad from '../../components/worker/SignaturePad';
import LifecycleStagePill from '../../components/compliance/LifecycleStagePill';
import { Checkbox } from '../../components/ui/checkbox';
import { ScrollArea } from '../../components/ui/scroll-area';
import { Briefcase, GraduationCap, Sparkles, Edit3, Link2, MessageSquare } from 'lucide-react';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import ProfileCompletionWizard from '../../components/worker/ProfileCompletionWizard';
import CareCertificateInductionPanel from '../../components/worker/CareCertificateInductionPanel';
import WorkerDashboardPage from '../../components/worker/WorkerDashboardPage';
import DashboardHeader from '../../components/worker/DashboardHeader';
import NextActionCard from '../../components/worker/NextActionCard';
import { getAgreementDisplay, getCvDisplay, getTrainingDisplay } from '../../components/worker/dashboardStatus';
import { getCanonicalPersonStage, isActiveLifecycleStatus, normalizeLifecycleStatus } from '../../lib/lifecycle';
import { getLatestActiveAgreementById, getLatestActiveContract, resolveLatestContractState } from '../../lib/contractState';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

// Canonical training status display config — single vocabulary across admin and worker
const TRAINING_STATUS_CONFIG = {
  verified:        { badge: 'Verified',              badgeCls: 'bg-green-100 text-green-700',   cardBg: 'bg-green-50 border-green-200',   Icon: ShieldCheck,   iconCls: 'text-green-600',  iconBg: 'bg-green-100',  showUpload: false },
  completed:       { badge: 'Awaiting Verification', badgeCls: 'bg-blue-100 text-blue-700',     cardBg: 'bg-blue-50 border-blue-200',     Icon: CheckCircle,   iconCls: 'text-blue-600',   iconBg: 'bg-blue-100',   showUpload: false },
  awaiting_review: { badge: 'Awaiting admin review', badgeCls: 'bg-purple-100 text-purple-700', cardBg: 'bg-purple-50 border-purple-200', Icon: Clock,         iconCls: 'text-purple-600', iconBg: 'bg-purple-100', showUpload: false },
  due_soon:        { badge: 'Expiring Soon',         badgeCls: 'bg-amber-100 text-amber-700',   cardBg: 'bg-amber-50 border-amber-200',   Icon: Clock,         iconCls: 'text-amber-600',  iconBg: 'bg-amber-100',  showUpload: true, uploadLabel: 'Renew' },
  expired:         { badge: 'Expired',               badgeCls: 'bg-red-100 text-red-700',       cardBg: 'bg-red-50 border-red-200',       Icon: AlertTriangle, iconCls: 'text-red-600',    iconBg: 'bg-red-100',    showUpload: true, uploadLabel: 'Re-upload' },
  rejected:        { badge: 'Rejected',              badgeCls: 'bg-red-100 text-red-700',       cardBg: 'bg-red-50 border-red-200',       Icon: AlertCircle,   iconCls: 'text-red-600',    iconBg: 'bg-red-100',    showUpload: true, uploadLabel: 'Re-upload' },
  missing:         { badge: 'Required',              badgeCls: 'bg-slate-100 text-slate-600',   cardBg: 'bg-slate-50 border-slate-200',   Icon: Circle,        iconCls: 'text-slate-400',  iconBg: 'bg-slate-100',  showUpload: true, uploadLabel: 'Upload' },
};

// Format date helper — guards against `new Date('bad')` which yields NaN and
// renders literally as "Invalid Date" if passed to toLocaleDateString().
const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '-';
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
};

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '-';
  return date.toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getWorkerIncidentStatusMeta = (status) => {
  switch ((status || 'open').toLowerCase()) {
    case 'closed':
      return { className: 'bg-green-100 text-green-700', label: 'Closed' };
    case 'resolved':
      return { className: 'bg-emerald-100 text-emerald-700', label: 'Resolved' };
    case 'under_review':
    case 'investigating':
      return { className: 'bg-amber-100 text-amber-700', label: 'Under review' };
    default:
      return { className: 'bg-blue-100 text-blue-700', label: 'Submitted' };
  }
};

const getDueState = (dateStr, soonWindowDays = 7) => {
  if (!dateStr) return null;
  const target = new Date(dateStr);
  if (isNaN(target.getTime())) return null;
  const now = new Date();
  const targetStart = new Date(target.getFullYear(), target.getMonth(), target.getDate());
  const nowStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const deltaDays = Math.ceil((targetStart - nowStart) / (1000 * 60 * 60 * 24));
  if (deltaDays < 0) return 'overdue';
  if (deltaDays <= soonWindowDays) return 'due_soon';
  return 'upcoming';
};

// Operational document guidance text
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
const DAILY_NOTE_TAG_OPTIONS = ['nutrition', 'mood', 'incident', 'medication'];

const DOCUMENT_WORKFLOW_UI = {
  missing: { label: 'Missing', className: 'bg-red-100 text-red-700' },
  awaiting_review: { label: 'Awaiting admin review', className: 'bg-amber-100 text-amber-700' },
  reupload_required: { label: 'Re-upload Required', className: 'bg-red-100 text-red-700' },
  check_required: { label: 'Check Required', className: 'bg-orange-100 text-orange-700' },
  check_in_progress: { label: 'Check In Progress', className: 'bg-blue-100 text-blue-700' },
  proof_required: { label: 'Proof Required', className: 'bg-purple-100 text-purple-700' },
  verified: { label: 'Verified', className: 'bg-green-100 text-green-700' },
};

const RECURRING_STATUS_UI = {
  overdue: {
    label: 'Overdue',
    badge: 'bg-red-100 text-red-700'
  },
  due: {
    label: 'Due now',
    badge: 'bg-amber-100 text-amber-700'
  },
  upcoming: {
    label: 'Upcoming',
    badge: 'bg-blue-100 text-blue-700'
  },
  scheduled: {
    label: 'Scheduled',
    badge: 'bg-slate-100 text-slate-700'
  },
};

const RECURRING_TYPE_LABELS = {
  supervision: 'Supervision',
  competency_assessment: 'Competency assessment',
  spot_check: 'Spot check',
  training_refresh: 'Training refresh',
  report_followup: 'Report follow-up',
};

const isCvDocumentRequirement = (doc) => {
  const type = String(doc?.type || doc?.requirement_id || doc?.id || '').trim().toLowerCase();
  const name = String(doc?.name || doc?.label || '').trim().toLowerCase();
  return ['cv', 'resume', 'curriculum_vitae'].includes(type) || /\b(cv|resume|curriculum vitae)\b/.test(name);
};

const getDocumentWorkflowBadgeMeta = (doc) => {
  const status = (doc?.status || '').toLowerCase();
  if (doc?.verified) return DOCUMENT_WORKFLOW_UI.verified;
  return DOCUMENT_WORKFLOW_UI[status] || DOCUMENT_WORKFLOW_UI.awaiting_review;
};

const getCompletedDocumentDisplayStatus = (doc) => {
  const status = String(doc?.status || '').trim().toLowerCase();
  if (status) return status;
  return doc?.verified ? 'verified' : 'awaiting_review';
};

const getCompletedTrainingBadgeMeta = (training) => {
  const status = String(training?.status || '').trim().toLowerCase();
  if (status && TRAINING_STATUS_CONFIG[status]) return TRAINING_STATUS_CONFIG[status];
  return training?.verified ? TRAINING_STATUS_CONFIG.verified : TRAINING_STATUS_CONFIG.awaiting_review;
};

const isFormAdminComplete = (status) =>
  ['verified', 'signed_off', 'reviewed', 'approved'].includes(status);

const isReferenceComplete = (status) => status === 'verified';

const BLOCKER_KEYS_EMPLOYMENT_GAPS = new Set(['employment_gaps']);
const BLOCKER_KEYS_REFERENCES = new Set(['reference_1', 'reference_2', 'references']);

const normalizeBlockerValue = (value) => String(value || '').trim().toLowerCase();

// Employment Gaps Clarification Section
function EmploymentGapsSection() {
  const [gaps, setGaps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasGaps, setHasGaps] = useState(false);
  const [allExplained, setAllExplained] = useState(false);
  const [reasonTypes, setReasonTypes] = useState([]);
  const [editingGap, setEditingGap] = useState(null);
  const [explanation, setExplanation] = useState('');
  const [reasonType, setReasonType] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [coverage, setCoverage] = useState(null);
  const [employmentEntries, setEmploymentEntries] = useState([]);
  const [invalidEntries, setInvalidEntries] = useState([]);
  const [unmatchedNotes, setUnmatchedNotes] = useState([]);

  useEffect(() => {
    fetchGaps();
  }, []);

  const fetchGaps = async () => {
    try {
      const token = localStorage.getItem('workerToken');
      // Use /worker/employment-gaps which reads directly from db.employment_gaps
      // with stable UUIDs — prevents gap lookup failures on resubmit after admin reopen
      const res = await axios.get(`${API}/worker/employment-gaps`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setGaps(res.data.gaps || []);
      setHasGaps(res.data.has_gaps);
      setAllExplained(res.data.all_explained);
      setReasonTypes(res.data.reason_types || []);
      setCoverage(res.data.coverage || null);
      setEmploymentEntries(res.data.employment_entries || []);
      setInvalidEntries(res.data.invalid_entries || []);
      setUnmatchedNotes(res.data.unmatched_notes || []);
    } catch {
      // No gaps or endpoint not available — silently hide section
    } finally {
      setLoading(false);
    }
  };

  const handleExplain = async (gapId) => {
    if (!explanation.trim()) {
      toast.error('Please provide an explanation');
      return;
    }
    setSubmitting(true);
    try {
      const token = localStorage.getItem('workerToken');
      await axios.post(`${API}/worker/employment-gaps/${gapId}/explain`,
        { explanation: explanation.trim(), reason_type: reasonType || null },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Gap explanation submitted');
      setEditingGap(null);
      setExplanation('');
      setReasonType('');
      fetchGaps();
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Failed to submit explanation');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return null;
  if (!hasGaps && !coverage && !invalidEntries.length && !unmatchedNotes.length) return null;

  const unresolvedGaps = gaps.filter(g => {
    const state = g.worker_state || '';
    const s = (g.status || g.verification_status || '').toLowerCase();
    return state !== 'reviewed' && s !== 'verified';
  });
  const verifiedGaps = gaps.filter(g => {
    const state = g.worker_state || '';
    const s = (g.status || g.verification_status || '').toLowerCase();
    return state === 'reviewed' || s === 'verified';
  });

  const formatGapDate = (d) => {
    if (!d) return '?';
    const date = new Date(d);
    if (isNaN(date.getTime())) return '?';
    return date.toLocaleDateString('en-GB', { month: 'short', year: 'numeric' });
  };

  const statusBadge = (gap) => {
    // Prefer worker_state from canonical review; fall back to raw status for legacy gaps
    const workerState = gap.worker_state;
    if (workerState === 'reviewed') return <Badge className="bg-green-100 text-green-700 text-xs"><CheckCircle className="h-3 w-3 mr-1" />Verified</Badge>;
    if (workerState === 'awaiting_admin_review') return <Badge className="bg-blue-100 text-blue-700 text-xs"><Clock className="h-3 w-3 mr-1" />Awaiting review</Badge>;
    if (workerState === 'update_needed') return <Badge className="bg-red-100 text-red-700 text-xs"><AlertCircle className="h-3 w-3 mr-1" />Update needed</Badge>;
    if (workerState === 'action_required') return <Badge className="bg-slate-100 text-slate-600 text-xs">Action required</Badge>;
    // Legacy / direct db fallback
    const s = (gap.status || gap.verification_status || 'pending').toLowerCase();
    if (s === 'verified') return <Badge className="bg-green-100 text-green-700 text-xs"><CheckCircle className="h-3 w-3 mr-1" />Verified</Badge>;
    if (s === 'explained') return <Badge className="bg-blue-100 text-blue-700 text-xs"><Clock className="h-3 w-3 mr-1" />Awaiting review</Badge>;
    if (s === 'reopened') return <Badge className="bg-red-100 text-red-700 text-xs"><AlertCircle className="h-3 w-3 mr-1" />Update needed</Badge>;
    if (s === 'needs_more_info') return <Badge className="bg-amber-100 text-amber-700 text-xs"><AlertTriangle className="h-3 w-3 mr-1" />More info needed</Badge>;
    if (s === 'rejected') return <Badge className="bg-red-100 text-red-700 text-xs"><AlertCircle className="h-3 w-3 mr-1" />Rejected</Badge>;
    return <Badge className="bg-slate-100 text-slate-600 text-xs">Action required</Badge>;
  };

  const reasonLabel = (t) => {
    if (!t) return null;
    return t.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const coveragePct = coverage?.coverage_percent ?? 0;
  const coverageMet = (coverage?.meets_10_year_requirement ?? false) && coveragePct > 0;

  return (
    <div className="space-y-4">
      {/* 10-Year Employment Coverage Summary */}
      {coverage && (
        <Card className={`shadow-md border-0 ${coverageMet ? 'bg-green-50/30' : 'border-l-4 border-l-blue-400'}`} data-testid="employment-coverage-section">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Calendar className="h-5 w-5 text-blue-600" />
                  10-Year Employment History
                </CardTitle>
                <p className="text-xs text-slate-500 mt-1">
                  Osabea needs a clear 10-year work history before your file can move forward
                </p>
              </div>
              {coverageMet ? (
                <Badge className="bg-green-100 text-green-700">
                  <CheckCircle className="h-3 w-3 mr-1" />Complete
                </Badge>
              ) : (
                <Badge className="bg-blue-100 text-blue-700">
                  {Math.round(coveragePct)}% covered
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <div className="flex justify-between text-xs text-slate-500 mb-1">
                <span>{coverage.coverage_start ? formatDate(coverage.coverage_start) : ''}</span>
                <span>{coverage.coverage_end ? formatDate(coverage.coverage_end) : 'Present'}</span>
              </div>
              <Progress value={coveragePct} className="h-2.5" />
              <p className="text-xs text-slate-500 mt-1">
                {coverage.total_days_covered?.toLocaleString() || 0} of {coverage.total_days_required?.toLocaleString() || 0} days accounted for
              </p>
            </div>

            {/* Employment entries summary (read-only — submitted via application form) */}
            <div className="border-t pt-3">
              <p className="text-xs font-medium text-slate-600 mb-2">
                {employmentEntries.length > 0
                  ? `${employmentEntries.length} employment record${employmentEntries.length !== 1 ? 's' : ''} from your application`
                  : 'No employment records on file — these are collected during your application'}
              </p>
              {employmentEntries.length > 0 && (
                <div className="space-y-1.5">
                  {employmentEntries.map((entry) => (
                    <div key={entry.id || entry.employer_name} className="flex items-center justify-between py-1.5 px-3 bg-slate-50 rounded-lg text-sm">
                      <div className="flex items-center gap-2 min-w-0">
                        <Briefcase className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                        <span className="text-slate-800 truncate font-medium">{entry.employer_name}</span>
                        {entry.job_title && <span className="text-slate-500 truncate hidden sm:inline">· {entry.job_title}</span>}
                      </div>
                      <span className="text-xs text-slate-500 flex-shrink-0 ml-2">
                        {formatDate(entry.start_date)} — {entry.is_current ? 'Present' : formatDate(entry.end_date)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {!coverageMet && (
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                {hasGaps
                  ? 'Please explain any gaps below. Osabea will review them before your file can move forward.'
                  : 'Your employment history does not yet cover the full 10-year window. Please contact your recruiter if you need to update your application.'}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Employment Gaps Card */}
      {hasGaps && (
    <Card className={`shadow-md border-0 ${allExplained ? 'bg-green-50/30' : 'border-l-4 border-l-amber-400'}`} data-testid="employment-gaps-section">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Briefcase className={`h-5 w-5 ${allExplained ? 'text-green-600' : 'text-amber-600'}`} />
              Explain Employment Gaps
            </CardTitle>
            <p className="text-xs text-slate-500 mt-1">
              {allExplained
                ? 'All gaps explained — awaiting admin verification'
                : `${unresolvedGaps.length} gap${unresolvedGaps.length !== 1 ? 's' : ''} need${unresolvedGaps.length === 1 ? 's' : ''} your explanation`}
            </p>
          </div>
          {allExplained && (
            <Badge className="bg-green-100 text-green-700">
              <CheckCircle className="h-3 w-3 mr-1" />All explained
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {unresolvedGaps.map(gap => {
          const gapId = gap.id || gap.gap_id;
          const isEditing = editingGap === gapId;
          const months = gap.duration_months || Math.round((gap.duration_days || 0) / 30);
          return (
            <div key={gapId} className="border border-slate-200 rounded-xl p-4 bg-white">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-slate-800">
                      {formatGapDate(gap.gap_start)} — {formatGapDate(gap.gap_end)}
                    </span>
                    {months > 0 && <span className="text-xs text-slate-500">({months} month{months !== 1 ? 's' : ''})</span>}
                    {statusBadge(gap)}
                  </div>
                  {gap.previous_employment?.employer_name && (
                    <p className="text-xs text-slate-500 mt-1">
                      Between: {gap.previous_employment.employer_name} → {gap.next_employment?.employer_name || 'next role'}
                    </p>
                  )}
                  {gap.explanation && !isEditing && (
                    <div className="mt-2 p-2 bg-slate-50 rounded text-sm text-slate-700">
                      {gap.reason_type && <span className="text-xs font-medium text-slate-500 block mb-1">{reasonLabel(gap.reason_type)}</span>}
                      {gap.explanation}
                    </div>
                  )}
                  {gap.admin_notes && (
                    <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded text-sm text-amber-800">
                      <span className="text-xs font-medium block mb-1">Admin feedback</span>
                      {gap.admin_notes || gap.verification_notes}
                    </div>
                  )}
                  {!gap.admin_notes && gap.reopen_reason && (
                    <div className="mt-2 p-2 bg-orange-50 border border-orange-200 rounded text-sm text-orange-800">
                      <span className="text-xs font-medium block mb-1">Reopened for review</span>
                      {gap.reopen_reason}
                    </div>
                  )}
                </div>
                {!isEditing && (gap.status || '').toLowerCase() !== 'verified' && (
                  <Button size="sm" variant="outline" onClick={() => {
                    setEditingGap(gapId);
                    setExplanation(gap.explanation || '');
                    setReasonType(gap.reason_type || '');
                  }}>
                    <Edit3 className="h-3.5 w-3.5 mr-1" />
                    {gap.explanation ? 'Update' : 'Explain'}
                  </Button>
                )}
              </div>
              {isEditing && (
                <div className="mt-3 space-y-3 border-t pt-3">
                  <div>
                    <label className="text-sm font-medium text-slate-700 block mb-1">Reason category</label>
                    <Select value={reasonType} onValueChange={setReasonType}>
                      <SelectTrigger className="w-full"><SelectValue placeholder="Select a category (optional)" /></SelectTrigger>
                      <SelectContent>
                        {reasonTypes.map(rt => (
                          <SelectItem key={rt} value={rt}>{reasonLabel(rt)}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-slate-700 block mb-1">Explanation <span className="text-red-500">*</span></label>
                    <Textarea
                      value={explanation}
                      onChange={e => setExplanation(e.target.value)}
                      placeholder="Please explain what you were doing during this period..."
                      rows={3}
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button size="sm" variant="ghost" onClick={() => { setEditingGap(null); setExplanation(''); setReasonType(''); }}>Cancel</Button>
                    <Button size="sm" onClick={() => handleExplain(gapId)} disabled={submitting} className="bg-blue-600 hover:bg-blue-700">
                      {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                      Submit Explanation
                    </Button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
        {verifiedGaps.length > 0 && (
          <div className="pt-2">
            <p className="text-xs text-slate-500 mb-2">{verifiedGaps.length} verified gap{verifiedGaps.length !== 1 ? 's' : ''}</p>
            {verifiedGaps.map(gap => {
              const gapId = gap.id || gap.gap_id;
              return (
                <div key={gapId} className="flex items-center justify-between py-2 px-3 bg-green-50/50 rounded-lg mb-1">
                  <span className="text-sm text-slate-700">{formatGapDate(gap.gap_start)} — {formatGapDate(gap.gap_end)}</span>
                  {statusBadge(gap)}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
      )}

      {/* Invalid Employment Entries */}
      {invalidEntries.length > 0 && (
        <Card className="shadow-md border-0 border-l-4 border-l-red-400" data-testid="invalid-entries-section">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertCircle className="h-5 w-5 text-red-500" />
              Employment Entry Issues
            </CardTitle>
            <p className="text-xs text-slate-500 mt-1">
              {invalidEntries.length} employment record{invalidEntries.length !== 1 ? 's have' : ' has'} missing or invalid dates. Please contact your recruiter to correct these.
            </p>
          </CardHeader>
          <CardContent className="space-y-2">
            {invalidEntries.map((entry, i) => (
              <div key={entry.id || i} className="py-2 px-3 bg-red-50 border border-red-200 rounded-lg text-sm">
                <div className="flex items-center gap-2">
                  <Badge className="bg-red-100 text-red-700 text-xs">Correction required</Badge>
                  <span className="font-medium text-slate-800">{entry.employer_name || entry.organisation || 'Unknown employer'}</span>
                </div>
                {entry.validation_error && (
                  <p className="text-xs text-red-700 mt-1">{entry.validation_error}</p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Unmatched Applicant Notes */}
      {unmatchedNotes.length > 0 && (
        <Card className="shadow-md border-0 bg-slate-50" data-testid="unmatched-notes-section">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-5 w-5 text-slate-500" />
              Supporting Notes
            </CardTitle>
            <p className="text-xs text-slate-500 mt-1">
              {unmatchedNotes.length} note{unmatchedNotes.length !== 1 ? 's were' : ' was'} submitted during your application but could not be matched to a specific gap. These are kept as supporting context.
            </p>
          </CardHeader>
          <CardContent className="space-y-2">
            {unmatchedNotes.map((note, i) => (
              <div key={note.id || i} className="py-2 px-3 bg-white border border-slate-200 rounded-lg text-sm">
                <Badge className="bg-slate-100 text-slate-600 text-xs mb-1">Supporting note · not counted as accepted coverage</Badge>
                <p className="text-slate-700">{note.explanation || note.text}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

    </div>
  );
}

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
        if (form.type === 'equal_opportunities') {
          return <Badge className="bg-green-100 text-green-700"><CheckCircle className="h-3 w-3 mr-1" />Completed</Badge>;
        }
        return <Badge className="bg-blue-100 text-blue-700">Sent for review</Badge>;
      case 'verified':
        return <Badge className="bg-green-100 text-green-700"><CheckCircle className="h-3 w-3 mr-1" />Verified</Badge>;
      case 'signed_off':
      case 'reviewed':
      case 'approved':
        return <Badge className="bg-green-100 text-green-700"><CheckCircle className="h-3 w-3 mr-1" />Signed off</Badge>;
      case 'returned_for_correction':
      case 'reopened_for_worker_correction':
      case 'amendment_requested':
        return <Badge className="bg-red-100 text-red-700"><AlertCircle className="h-3 w-3 mr-1" />Correction required</Badge>;
      case 'rejected':
        return <Badge className="bg-red-100 text-red-700"><AlertCircle className="h-3 w-3 mr-1" />Action required</Badge>;
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

  const pendingForms = forms.filter((f) => !isFormAdminComplete(f.status));
  const completedForms = forms.filter((f) => isFormAdminComplete(f.status));

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
                  ['returned_for_correction', 'reopened_for_worker_correction', 'amendment_requested', 'rejected'].includes(form.status) ? 'bg-red-100' : form.status === 'in_progress' ? 'bg-amber-100' : 'bg-blue-100'
                }`}>
                  <FileText className={`h-5 w-5 ${
                    ['returned_for_correction', 'reopened_for_worker_correction', 'amendment_requested', 'rejected'].includes(form.status) ? 'text-red-600' : form.status === 'in_progress' ? 'text-amber-600' : 'text-blue-600'
                  }`} />
                </div>
                <div>
                  <span className="font-medium text-slate-800">{form.name}</span>
                  {['returned_for_correction', 'reopened_for_worker_correction', 'amendment_requested'].includes(form.status) && (
                    <p className="text-xs text-red-600">Admin requested a correction. Please update and resubmit.</p>
                  )}
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
                  className={['returned_for_correction', 'reopened_for_worker_correction', 'amendment_requested', 'rejected'].includes(form.status) ? 'bg-red-600 hover:bg-red-700' : form.status === 'in_progress' ? 'bg-amber-600 hover:bg-amber-700' : 'bg-blue-600 hover:bg-blue-700'}
                >
                  {['returned_for_correction', 'reopened_for_worker_correction', 'amendment_requested', 'rejected'].includes(form.status) ? 'Correct' : form.status === 'in_progress' ? 'Continue' : 'Start'}
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
                  {form.submitted_at && !['verified', 'signed_off', 'reviewed', 'approved'].includes(form.status) && (
                    <p className="text-xs text-blue-600">Sent for review: {formatDate(form.submitted_at)}</p>
                  )}
                  {['verified', 'signed_off', 'reviewed', 'approved'].includes(form.status) && form.submitted_at && (
                    <p className="text-xs text-green-600">Submitted {formatDate(form.submitted_at)} · reviewed by admin</p>
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
  // Account settings - password setup
  const [accountStatus, setAccountStatus] = useState({ has_password: false });
  const [showSetPasswordModal, setShowSetPasswordModal] = useState(false);
  const [showReferencesDetails, setShowReferencesDetails] = useState(false);
  const [showAgreementsDetails, setShowAgreementsDetails] = useState(false);
  // Active-employee dashboard tab toggle (Tier 4). Default to 'today' so
  // active staff land on a clean live view; pre-employment / applicants
  // never see the toggle and effectively render with both tabs unioned.
  const [activeWorkerTab, setActiveWorkerTab] = useState('today');
  const [passwordForm, setPasswordForm] = useState({ new_password: '', confirm_password: '', current_password: '' });
  const [settingPassword, setSettingPassword] = useState(false);
  // Notifications
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotificationsPanel, setShowNotificationsPanel] = useState(false);
  // Document viewer modal state
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerDocument, setViewerDocument] = useState(null);
  const [documentBlobUrl, setDocumentBlobUrl] = useState(null);
  const [documentLoading, setDocumentLoading] = useState(false);
  // CV lifecycle states (upload CTA and status only — review/verification is admin-only)
  const [cvStatus, setCvStatus] = useState(null);
  const [cvStatusLoading, setCvStatusLoading] = useState(false);
  // Reference mismatch explanation states
  const [referenceMismatches, setReferenceMismatches] = useState(null);
  const [showMismatchExplanationModal, setShowMismatchExplanationModal] = useState(false);
  const [selectedMismatch, setSelectedMismatch] = useState(null);
    const [provideNewRefNum, setProvideNewRefNum] = useState(null);
    const [provideNewForm, setProvideNewForm] = useState({ name: '', email: '', phone: '', organisation: '', position: '', relationship: '', change_reason: '' });
    const [provideNewLoading, setProvideNewLoading] = useState(false);
  const [mismatchExplanationType, setMismatchExplanationType] = useState('');
  const [mismatchExplanationText, setMismatchExplanationText] = useState('');
  const [submittingMismatchExplanation, setSubmittingMismatchExplanation] = useState(false);
  // Profile completion wizard state
  const [showProfileWizard, setShowProfileWizard] = useState(false);
  const [profileCompletionStatus, setProfileCompletionStatus] = useState(null);
  // Handbook acknowledgement modal state
  const [showHandbookAckModal, setShowHandbookAckModal] = useState(false);
  const [handbookAckAgreement, setHandbookAckAgreement] = useState(null);
  const [handbookPdfViewed, setHandbookPdfViewed] = useState(false);
  const [handbookAckConfirmed, setHandbookAckConfirmed] = useState(false);
  const [submittingHandbookAck, setSubmittingHandbookAck] = useState(false);
  const [showRecurringDetails, setShowRecurringDetails] = useState(false);
  const [workerShifts, setWorkerShifts] = useState([]);
  const [workerShiftsLoading, setWorkerShiftsLoading] = useState(false);
  const [selectedWorkerShift, setSelectedWorkerShift] = useState(null);
  const [workerShiftDetailOpen, setWorkerShiftDetailOpen] = useState(false);
  const [workerShiftResponseOpen, setWorkerShiftResponseOpen] = useState(false);
  const [workerShiftResponseMode, setWorkerShiftResponseMode] = useState('accept');
  const [workerShiftResponseItem, setWorkerShiftResponseItem] = useState(null);
  const [workerShiftResponseNote, setWorkerShiftResponseNote] = useState('');
  const [workerShiftResponding, setWorkerShiftResponding] = useState(false);
  const [workerShiftClocking, setWorkerShiftClocking] = useState(false);
  const [workerDailyNoteText, setWorkerDailyNoteText] = useState('');
  const [workerDailyNoteTags, setWorkerDailyNoteTags] = useState([]);
  const [workerDailyNoteSubmitting, setWorkerDailyNoteSubmitting] = useState(false);
  const [workerIncidents, setWorkerIncidents] = useState([]);
  const [workerIncidentsLoading, setWorkerIncidentsLoading] = useState(false);
  const [incidentDetailOpen, setIncidentDetailOpen] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [incidentModalOpen, setIncidentModalOpen] = useState(false);
  const [incidentSubmitting, setIncidentSubmitting] = useState(false);
  const [incidentForm, setIncidentForm] = useState({
    incident_type: 'incident',
    occurred_at: '',
    location_text: '',
    description: '',
    people_involved: '',
    witnesses: '',
    immediate_actions_taken: '',
    injury_or_harm: '',
    safeguarding_concern: false,
    escalation_required: false,
    escalation_details: '',
    learning_outcome: '',
    prevention_actions: '',
    related_shift_id: '',
    service_user_id: '',
    note: '',
  });
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
      
      // Fetch account status to check if password is set
      try {
        const accountRes = await axios.get(`${API}/worker/account-status`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setAccountStatus(accountRes.data);
      } catch (err) {
        console.warn('Could not fetch account status:', err);
      }
      
      // Fetch notifications
      try {
        const notifRes = await axios.get(`${API}/worker/notifications`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setNotifications(notifRes.data.notifications || []);
        setUnreadCount(notifRes.data.unread_count || 0);
      } catch (err) {
        console.warn('Could not fetch notifications:', err);
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

  // Check if profile completion is needed (for offline PDF imports)
  const checkProfileCompletion = useCallback(async () => {
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.get(`${API}/worker/profile-completion-status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setProfileCompletionStatus(response.data);
      
      // Auto-show wizard if profile needs completion and not already shown
      if (response.data.needs_wizard && !showProfileWizard) {
        setShowProfileWizard(true);
      }
    } catch (error) {
      console.error('Failed to check profile completion:', error);
    }
  }, [showProfileWizard]);

  useEffect(() => {
    if (dashboard) {
      checkProfileCompletion();
    }
  }, [dashboard, checkProfileCompletion]);

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
      const dashboardEmployee = dashboard?.employee || {};
      const workerIsActive =
        typeof dashboard?.is_active_employee === 'boolean'
          ? dashboard.is_active_employee
          : (
              dashboardEmployee?.is_active_employee ||
              isActiveLifecycleStatus(dashboardEmployee?.employee_status) ||
              isActiveLifecycleStatus(dashboardEmployee?.status)
            );
      fetchCvStatus();
      fetchReferenceMismatches();
      if (workerIsActive) {
        fetchWorkerShifts();
        fetchWorkerIncidents();
      } else {
        setWorkerShifts([]);
        setWorkerIncidents([]);
      }
    }
  }, [dashboard, fetchCvStatus]);

  const fetchWorkerShifts = async () => {
    setWorkerShiftsLoading(true);
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.get(`${API}/worker/shifts`, {
        params: { include_completed: true },
        headers: { Authorization: `Bearer ${token}` }
      });
      const rows = response.data?.shifts || [];
      setWorkerShifts(rows);
    } catch (error) {
      console.error('Failed to fetch worker shifts:', error);
    } finally {
      setWorkerShiftsLoading(false);
    }
  };

  const handleOpenWorkerShift = async (shiftId) => {
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.get(`${API}/worker/shifts/${shiftId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSelectedWorkerShift(response.data || null);
      if (response.data?.current_daily_note) {
        setWorkerDailyNoteText(response.data.current_daily_note.note_text || '');
        setWorkerDailyNoteTags(Array.isArray(response.data.current_daily_note.tags) ? response.data.current_daily_note.tags : []);
      } else {
        setWorkerDailyNoteText('');
        setWorkerDailyNoteTags([]);
      }
      setWorkerShiftDetailOpen(true);
    } catch (error) {
      const message = typeof error.response?.data?.detail === 'string'
        ? error.response.data.detail
        : 'Could not load shift detail';
      toast.error(message);
    }
  };

  const openWorkerShiftResponseModal = (item, mode) => {
    setWorkerShiftResponseItem(item || null);
    setWorkerShiftResponseMode(mode);
    setWorkerShiftResponseNote('');
    setWorkerShiftResponseOpen(true);
  };

  const handleWorkerShiftResponse = async () => {
    const shiftId = workerShiftResponseItem?.shift?.id;
    if (!shiftId) {
      toast.error('Shift not found');
      return;
    }
    setWorkerShiftResponding(true);
    try {
      const token = localStorage.getItem('workerToken');
      const endpoint = workerShiftResponseMode === 'reject'
        ? `${API}/worker/shifts/${shiftId}/reject`
        : `${API}/worker/shifts/${shiftId}/accept`;
      await axios.post(
        endpoint,
        { note: workerShiftResponseNote || null },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(workerShiftResponseMode === 'reject' ? 'Shift rejected' : 'Shift accepted');
      setWorkerShiftResponseOpen(false);
      setWorkerShiftResponseItem(null);
      setWorkerShiftResponseNote('');
      fetchWorkerShifts();
      fetchDashboard();
    } catch (error) {
      const message = typeof error.response?.data?.detail === 'string'
        ? error.response.data.detail
        : 'Could not update shift response';
      toast.error(message);
    } finally {
      setWorkerShiftResponding(false);
    }
  };

  const getWorkerShiftAttendanceStatus = (item) => {
    return item?.current_attendance?.status || null;
  };

  const canWorkerClockIn = (item) => {
    const assignmentStatus = item?.assignment_status || item?.assignment?.status;
    const workerResponseStatus = item?.worker_response_status || item?.assignment?.worker_response_status || 'pending';
    const attendanceStatus = getWorkerShiftAttendanceStatus(item);
    return assignmentStatus === 'active'
      && workerResponseStatus === 'accepted'
      && !['open', 'submitted', 'approved'].includes(attendanceStatus || '');
  };

  const canWorkerClockOut = (item) => {
    return getWorkerShiftAttendanceStatus(item) === 'open';
  };

  const handleWorkerShiftClock = async (item, mode) => {
    const shiftId = item?.shift?.id;
    if (!shiftId) {
      toast.error('Shift not found');
      return;
    }
    setWorkerShiftClocking(true);
    try {
      const token = localStorage.getItem('workerToken');
      const endpoint = mode === 'in'
        ? `${API}/worker/shifts/${shiftId}/clock-in`
        : `${API}/worker/shifts/${shiftId}/clock-out`;
      await axios.post(
        endpoint,
        { note: null },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(mode === 'in' ? 'Clocked in successfully' : 'Clocked out successfully');
      await fetchWorkerShifts();
      if (selectedWorkerShift?.shift?.id === shiftId) {
        await handleOpenWorkerShift(shiftId);
      }
    } catch (error) {
      const message = typeof error.response?.data?.detail === 'string'
        ? error.response.data.detail
        : mode === 'in'
          ? 'Could not clock in'
          : 'Could not clock out';
      toast.error(message);
    } finally {
      setWorkerShiftClocking(false);
    }
  };

  const toggleWorkerDailyNoteTag = (tag) => {
    setWorkerDailyNoteTags((prev) => (
      prev.includes(tag) ? prev.filter((item) => item !== tag) : [...prev, tag]
    ));
  };

  const handleSubmitWorkerDailyNote = async () => {
    const shiftId = selectedWorkerShift?.shift?.id;
    if (!shiftId) {
      toast.error('Shift not found');
      return;
    }
    const text = (workerDailyNoteText || '').trim();
    if (text.length < 2) {
      toast.error('Daily note text is required');
      return;
    }
    setWorkerDailyNoteSubmitting(true);
    try {
      const token = localStorage.getItem('workerToken');
      await axios.post(
        `${API}/worker/shifts/${shiftId}/daily-notes`,
        { note_text: text, tags: workerDailyNoteTags },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Daily note saved');
      await fetchWorkerShifts();
      await handleOpenWorkerShift(shiftId);
    } catch (error) {
      const message = typeof error.response?.data?.detail === 'string'
        ? error.response.data.detail
        : 'Could not save daily note';
      toast.error(message);
    } finally {
      setWorkerDailyNoteSubmitting(false);
    }
  };

  const fetchWorkerIncidents = async () => {
    setWorkerIncidentsLoading(true);
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.get(`${API}/worker/incidents`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setWorkerIncidents(response.data?.incidents || []);
    } catch (error) {
      console.error('Failed to fetch worker incidents:', error);
    } finally {
      setWorkerIncidentsLoading(false);
    }
  };

  const handleReportIncidentForShift = () => {
    const shift = selectedWorkerShift?.shift;
    if (!shift?.id) {
      setIncidentModalOpen(true);
      return;
    }
    const now = new Date();
    const localIso = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    setIncidentForm((prev) => ({
      ...prev,
      occurred_at: prev.occurred_at || localIso,
      location_text: prev.location_text || shift.location_text || '',
      related_shift_id: shift.id,
      service_user_id: shift.service_user_id || '',
    }));
    setIncidentModalOpen(true);
  };

  const handleSubmitIncident = async () => {
    if (!incidentForm.occurred_at || !incidentForm.location_text || !incidentForm.description) {
      toast.error('Date/time, location, and description are required');
      return;
    }
    setIncidentSubmitting(true);
    try {
      const token = localStorage.getItem('workerToken');
      await axios.post(
        `${API}/worker/incidents`,
        {
          incident_type: incidentForm.incident_type,
          occurred_at: new Date(incidentForm.occurred_at).toISOString(),
          location_text: incidentForm.location_text,
          description: incidentForm.description,
          people_involved: incidentForm.people_involved || null,
          witnesses: incidentForm.witnesses || null,
          immediate_actions_taken: incidentForm.immediate_actions_taken || null,
          injury_or_harm: incidentForm.injury_or_harm || null,
          safeguarding_concern: !!incidentForm.safeguarding_concern,
          escalation_required: !!incidentForm.escalation_required,
          escalation_details: incidentForm.escalation_required ? (incidentForm.escalation_details || null) : null,
          learning_outcome: incidentForm.learning_outcome || null,
          prevention_actions: incidentForm.prevention_actions || null,
          related_shift_id: incidentForm.related_shift_id || null,
          service_user_id: incidentForm.service_user_id || null,
          note: incidentForm.note || null,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Incident submitted');
      setIncidentModalOpen(false);
      setIncidentForm({
        incident_type: 'incident',
        occurred_at: '',
        location_text: '',
        description: '',
        people_involved: '',
        witnesses: '',
        immediate_actions_taken: '',
        injury_or_harm: '',
        safeguarding_concern: false,
        escalation_required: false,
        escalation_details: '',
        learning_outcome: '',
        prevention_actions: '',
        related_shift_id: '',
        service_user_id: '',
        note: '',
      });
      fetchWorkerIncidents();
    } catch (error) {
      const message = typeof error.response?.data?.detail === 'string'
        ? error.response.data.detail
        : 'Failed to submit incident';
      toast.error(message);
    } finally {
      setIncidentSubmitting(false);
    }
  };

  const openIncidentDetail = (incident) => {
    setSelectedIncident(incident);
    setIncidentDetailOpen(true);
  };

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
    // Worker submits replacement referee after rejection
    const handleProvideNewSubmit = async (refNum) => {
      if (!provideNewForm.name || !provideNewForm.email) {
        toast.error('Name and email are required');
        return;
      }
      if (!provideNewForm.change_reason || provideNewForm.change_reason.trim().length < 10) {
        toast.error('Please explain why you are providing a new referee (at least 10 characters)');
        return;
      }
      setProvideNewLoading(true);
      try {
        await axios.post(
          `${API}/worker/references/${refNum}/provide-new`,
          provideNewForm,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success('Referee details submitted. Your manager will be in touch shortly.');
        setProvideNewRefNum(null);
        setProvideNewForm({ name: '', email: '', phone: '', organisation: '', position: '', relationship: '', change_reason: '' });
        fetchDashboard();
      } catch (err) {
        const detail = err.response?.data?.detail;
        toast.error(typeof detail === 'string' ? detail : 'Failed to submit referee details');
      } finally {
        setProvideNewLoading(false);
      }
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
      const message = typeof error.response?.data?.detail === 'string' ? error.response.data.detail : 'Failed to submit explanation';
      toast.error(message);
    } finally {
      setSubmittingMismatchExplanation(false);
    }
  };

  // Fetch CV preview for verification
  // CV extraction review/verify is admin-only. No worker-side handlers needed.

  // Handle CV file upload
  const handleCvUpload = async (file) => {
    if (!file) return;

    const isPdfFile = file.type === 'application/pdf' || file.name?.toLowerCase().endsWith('.pdf');
    if (!isPdfFile) {
      toast.error('Only PDF CV files are supported. Please upload your CV as a PDF. Word documents (.doc, .docx) are not accepted.');
      return;
    }
    
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
      await fetchCvStatus();
      await fetchDashboard();
    } catch (error) {
      const message = typeof error.response?.data?.detail === 'string' ? error.response.data.detail : 'Failed to upload CV';
      toast.error(message);
    } finally {
      setUploading(null);
    }
  };

  // Trigger CV file input
  const triggerCvFileInput = () => {
    const cvStatusValue = String(cvStatus?.cv_status || '').toLowerCase();
    const replacementAllowed =
      cvStatus?.can_upload_cv === true ||
      cvStatus?.replacement_required === true ||
      ['rejected', 'replacement_requested', 'replacement_required', 'missing'].includes(cvStatusValue);

    // Double-check replacement rules client-side to avoid opening a flow that backend will reject.
    if (cvStatus?.has_cv && !replacementAllowed) {
      toast.error('Your CV is already on file. Wait for admin to request a replacement before uploading a new CV.');
      return;
    }
    
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf';
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

  const getWorkerBlobRequestConfig = (url, workerToken) => {
    const config = { responseType: 'blob' };
    if (!url) return config;

    try {
      const resolvedUrl = new URL(url, window.location.origin);
      const isSameOriginApi = resolvedUrl.origin === window.location.origin && resolvedUrl.pathname.startsWith('/api/');
      if (isSameOriginApi && workerToken) {
        config.headers = { Authorization: `Bearer ${workerToken}` };
      }
    } catch {
      // If URL parsing fails, fall back to no auth headers.
    }

    return config;
  };

  const fetchWorkerBlob = (url, workerToken) => {
    return axios.get(url, getWorkerBlobRequestConfig(url, workerToken));
  };

  // Fetch document as blob with authentication
  const openDocumentViewer = async (doc) => {
    setViewerDocument(doc);
    setViewerOpen(true);
    setDocumentLoading(true);
    setDocumentBlobUrl(null);
    
    if (!doc?.document_id && !doc?.id && !doc?.file_url) {
      setDocumentLoading(false);
      return;
    }
    
    try {
      let response;
      if (doc?.file_url && !doc?.document_id) {
        const token = localStorage.getItem('workerToken');
        response = await fetchWorkerBlob(doc.file_url, token);
      } else {
        const token = localStorage.getItem('workerToken');
        response = await axios.get(
          `${API}/employee-documents/${doc.document_id || doc.id}/file`,
          {
            headers: { Authorization: `Bearer ${token}` },
            responseType: 'blob'
          }
        );
      }
      
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

  const downloadAgreement = async (agreement) => {
    const url = agreement?.download_url || agreement?.file_url;
    if (!url) {
      toast.error('Agreement PDF is not available yet');
      return;
    }
    try {
      const token = localStorage.getItem('workerToken');
      const response = await fetchWorkerBlob(url, token);
      const blobUrl = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `${agreement.name || 'agreement'}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
    } catch {
      toast.error('Failed to download agreement');
    }
  };

  const handleAcknowledgeAgreement = async (agreement) => {
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.post(
        `${API}/worker/agreements/${agreement.id}/acknowledge`,
        {
          signer_name: employee?.name,
          ...(agreement?.source_record_id ? { source_record_id: agreement.source_record_id } : {}),
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const idempotent = Boolean(response?.data?.idempotent);
      toast.success(idempotent ? `${agreement.name} already acknowledged` : `${agreement.name} acknowledged`);
      fetchDashboard();
      return true;
    } catch (error) {
      const payload = error?.response?.data || {};
      const detail = payload?.detail;
      const message =
        (typeof detail === 'string' && detail) ||
        (detail && typeof detail.message === 'string' && detail.message) ||
        (typeof payload?.message === 'string' && payload.message) ||
        'Failed to acknowledge agreement';
      const code =
        (typeof payload?.code === 'string' && payload.code) ||
        (detail && typeof detail === 'object' ? detail.code : null);
      if (error?.response?.status === 409 && (code === 'not_actionable' || code === 'already_acknowledged' || code === 'already_signed')) {
        toast.info(message);
      } else {
        toast.error(message);
      }
      fetchDashboard();
      return false;
    }
  };

  const openHandbookAckModal = (agreement) => {
    if (!agreement?.file_url && !agreement?.download_url) {
      toast.error('Handbook PDF is not available yet. Please try again shortly.');
      return;
    }
    setHandbookAckAgreement(agreement);
    setHandbookPdfViewed(false);
    setHandbookAckConfirmed(false);
    setShowHandbookAckModal(true);
  };

  const closeHandbookAckModal = () => {
    if (submittingHandbookAck) return;
    setShowHandbookAckModal(false);
    setHandbookAckAgreement(null);
    setHandbookPdfViewed(false);
    setHandbookAckConfirmed(false);
  };

  const viewHandbookPdfFromModal = () => {
    if (!handbookAckAgreement) return;
    openDocumentViewer({ ...handbookAckAgreement, name: handbookAckAgreement.name });
    setHandbookPdfViewed(true);
  };

  const submitHandbookAck = async () => {
    if (!handbookAckAgreement) return;
    if (!handbookAckAgreement.file_url && !handbookAckAgreement.download_url) {
      toast.error('Handbook PDF is not available yet. Please try again shortly.');
      return;
    }
    if (!handbookPdfViewed || !handbookAckConfirmed) return;
    setSubmittingHandbookAck(true);
    try {
      const ok = await handleAcknowledgeAgreement(handbookAckAgreement);
      if (ok) {
        setShowHandbookAckModal(false);
        setHandbookAckAgreement(null);
        setHandbookPdfViewed(false);
        setHandbookAckConfirmed(false);
      }
    } finally {
      setSubmittingHandbookAck(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('workerToken');
    localStorage.removeItem('workerEmployee');
    toast.success('Logged out successfully');
    navigate('/worker/login');
  };

  const handleSetPassword = async () => {
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error('Passwords do not match');
      return;
    }
    if (passwordForm.new_password.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    if (!/[A-Z]/.test(passwordForm.new_password)) {
      toast.error('Password must contain at least one uppercase letter');
      return;
    }
    if (!/[0-9]/.test(passwordForm.new_password)) {
      toast.error('Password must contain at least one number');
      return;
    }

    setSettingPassword(true);
    const token = localStorage.getItem('workerToken');
    
    try {
      await axios.post(
        `${API}/worker/set-password`,
        {
          new_password: passwordForm.new_password,
          confirm_password: passwordForm.confirm_password,
          current_password: accountStatus.has_password ? passwordForm.current_password : null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Password set successfully! You can now login with your email and password.');
      setShowSetPasswordModal(false);
      setPasswordForm({ new_password: '', confirm_password: '', current_password: '' });
      setAccountStatus({ ...accountStatus, has_password: true });
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Failed to set password');
    } finally {
      setSettingPassword(false);
    }
  };

  const markNotificationRead = async (notificationId) => {
    const token = localStorage.getItem('workerToken');
    try {
      await axios.post(
        `${API}/worker/notifications/${notificationId}/read`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setNotifications(prev => prev.map(n => 
        n.id === notificationId ? { ...n, read: true } : n
      ));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.warn('Could not mark notification read:', err);
    }
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
      const message = typeof error.response?.data?.detail === 'string' ? error.response.data.detail : 'Failed to upload document';
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
      const message = typeof error.response?.data?.detail === 'string' ? error.response.data.detail : 'Failed to upload documents';
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

  if (!dashboard) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center space-y-4">
          <AlertCircle className="h-10 w-10 text-red-400 mx-auto" />
          <p className="text-slate-600">Could not load your dashboard.</p>
          <Button onClick={fetchDashboard} className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  const {
    employee = {},
    progress = { percentage: 0, completed: 0, required: 0 },
    forms: _forms,
    missing_documents: _missing_documents,
    missing_trainings: _missing_trainings,
    completed_documents: _completed_documents,
    completed_trainings: _completed_trainings,
    expired_trainings: _expired_trainings,
    all_mandatory_trainings: _all_mandatory_trainings,
    recommended_trainings: _recommended_trainings,
    alerts: _alerts,
    contract_signed = false,
    unified_blockers: _unified_blockers,
    legal_blockers: _legal_blockers,
    internal_blockers: _internal_blockers,
    employment_readiness,
    employment_readiness_label,
    employment_readiness_blockers: _employment_readiness_blockers,
    professional_registration,
    references: _references,
    induction,
    competency_assessments,
    spot_checks,
    supervisions: _supervisions,
    recurring_compliance_summary: _recurring_compliance_summary,
    agreements: _agreements,
    worker_tasks: _worker_tasks,
  } = dashboard;

  // Safe array defaults — prevent .length / .map / .filter on undefined
  const forms = _forms || [];
  const missing_documents = _missing_documents || [];
  const visibleMissingDocuments = missing_documents.filter((doc) => !isCvDocumentRequirement(doc));
  const missing_trainings = _missing_trainings || [];
  const completed_documents = _completed_documents || [];
  const completed_trainings = _completed_trainings || [];
  const expired_trainings = _expired_trainings || [];
  const all_mandatory_trainings = _all_mandatory_trainings || [];
  const recommended_trainings = _recommended_trainings || [];
  const alerts = _alerts || [];
  const references = _references || [];
  const supervisions = _supervisions || [];
  const agreements = Array.isArray(_agreements) ? _agreements : [];
  const operationalAgreements = agreements
    .filter((agreement) => agreement?.latest_active !== false)
    .filter((agreement, idx, arr) => arr.findIndex((x) => x?.id === agreement?.id) === idx);
  const worker_tasks = _worker_tasks || [];
  const recurring_compliance_summary = _recurring_compliance_summary || { total: 0, overdue: 0, due: 0, upcoming: 0, scheduled: 0, preview: [] };
  const recurringItems = recurring_compliance_summary.items || recurring_compliance_summary.preview || [];
  const recurringItemsByStatus = {
    overdue: recurringItems.filter((item) => item?.computed_status === 'overdue'),
    due: recurringItems.filter((item) => item?.computed_status === 'due'),
    upcoming: recurringItems.filter((item) => item?.computed_status === 'upcoming'),
    scheduled: recurringItems.filter((item) => item?.computed_status === 'scheduled'),
  };
  const unifiedBlockers = _unified_blockers || [];
  const legalBlockers = _legal_blockers || [];
  const internalBlockers = _internal_blockers || [];
  const canonicalBlockers = [...unifiedBlockers, ...legalBlockers, ...internalBlockers];
  const competencyRecurringItems = recurringItems.filter((item) => item?.item_type === 'competency_assessment');
  const competencyRecurringCounts = {
    overdue: competencyRecurringItems.filter((item) => item?.computed_status === 'overdue').length,
    due: competencyRecurringItems.filter((item) => item?.computed_status === 'due').length,
    upcoming: competencyRecurringItems.filter((item) => item?.computed_status === 'upcoming').length,
  };
  const employment_readiness_blockers = _employment_readiness_blockers || [];
  const hasCanonicalBlockerMatch = (keys, category) => {
    const canonicalMatch = canonicalBlockers.some((blocker) => {
      const blockerId = normalizeBlockerValue(blocker?.id);
      const blockerGate = normalizeBlockerValue(blocker?.gate);
      const blockerCategory = normalizeBlockerValue(blocker?.category);
      const blockerClass = normalizeBlockerValue(blocker?.blocker_class);
      return (
        keys.has(blockerId) ||
        keys.has(blockerGate) ||
        blockerCategory === normalizeBlockerValue(category) ||
        blockerClass === normalizeBlockerValue(category)
      );
    });
    if (canonicalMatch) return true;
    return employment_readiness_blockers.some((blocker) => keys.has(normalizeBlockerValue(blocker?.type)));
  };

  const gapsNeedAction = hasCanonicalBlockerMatch(BLOCKER_KEYS_EMPLOYMENT_GAPS, 'other');
  const referencesNeedActionFromBlockers = hasCanonicalBlockerMatch(BLOCKER_KEYS_REFERENCES, 'references');
  const latestContractAgreement = getLatestActiveContract(operationalAgreements, { contractEligibility });
  const contractAgreement = latestContractAgreement || operationalAgreements.find((agreement) => agreement.id === 'contract_acceptance');
  
  const isActiveEmployee =
    typeof dashboard?.is_active_employee === 'boolean'
      ? dashboard.is_active_employee
      : (
          employee?.is_active_employee ||
          isActiveLifecycleStatus(employee?.employee_status) ||
          isActiveLifecycleStatus(employee?.status)
        );
  const canonicalStage = getCanonicalPersonStage(employee);
  const isPreEmploymentEmployee =
    !isActiveEmployee && (
      canonicalStage === 'employee' ||
      employee?.is_approved ||
      employee?.recruitment_approved ||
      normalizeLifecycleStatus(employee?.employee_status) === 'onboarding' ||
      normalizeLifecycleStatus(employee?.status) === 'onboarding' ||
      employee?.status === 'READY' ||
      contract_signed
    );
  const lifecycleStage = isActiveEmployee
    ? 'active'
    : isPreEmploymentEmployee
      ? 'pre_employment'
      : 'recruitment';
  // Active-employee dashboard split — Tier 4. Olumide-style "Ready for
  // Work" workers have a 30-section onboarding archive that should be
  // tucked away. The "Today" tab keeps live items (shifts, obligations,
  // alerts, incidents); the "Staff File" tab holds the historic record
  // (forms, documents, employment history, training, agreements, etc.).
  // Applicants and pre-employment workers see everything inline (no tabs).
  const showFileSections = !isActiveEmployee || activeWorkerTab === 'file';
  const showTodaySections = !isActiveEmployee || activeWorkerTab === 'today';
  const showOnboardingContractSection = false;
  const handbookAgreement = getLatestActiveAgreementById(operationalAgreements, 'handbook_acknowledgement')
    || getLatestActiveAgreementById(operationalAgreements, 'employee_handbook_acknowledgement')
    || operationalAgreements.find((agreement) => agreement.id === 'handbook_acknowledgement')
    || operationalAgreements.find((agreement) => agreement.id === 'employee_handbook_acknowledgement');
  const effectiveContractEligibility = contractEligibility || {
    can_sign: Boolean(contractAgreement?.can_sign),
    blockers: Array.isArray(contractAgreement?.signing_gate_blockers) ? contractAgreement.signing_gate_blockers : [],
    reason: contractAgreement?.signing_gate_reason || null,
  };
  const contractDisplay = getAgreementDisplay(contractAgreement, { contractEligibility: effectiveContractEligibility });
  const latestContractState = resolveLatestContractState(contractAgreement, { contractEligibility: effectiveContractEligibility });
  const contractLifecycleStatus = latestContractState.status;
  const effectiveContractCanSign = latestContractState.canSign;
  const hasPendingSignableContract = latestContractState.hasPendingSignableContract;
  const contractNeedsReissueMessage = !hasPendingSignableContract && (
    ['rejected', 'superseded', 'action_required'].includes(contractLifecycleStatus) ||
    contractLifecycleStatus !== 'pending_signature'
  );
  const truncateAgreementCardText = (value, max = 160) => {
    const text = String(value || '').trim();
    if (!text) return '';
    if (text.length <= max) return text;
    return `${text.slice(0, max - 1).trimEnd()}…`;
  };
  const handbookDisplay = getAgreementDisplay(handbookAgreement, { contractEligibility });
  const cvDisplay = getCvDisplay(cvStatus);
  const trainingDisplay = getTrainingDisplay({
    missingTrainings: missing_trainings,
    expiredTrainings: expired_trainings,
    allMandatoryTrainings: all_mandatory_trainings,
  });
  const completedReferencesCount = references.filter((reference) => isReferenceComplete(reference?.status)).length;
  const referencesNeedAction = referencesNeedActionFromBlockers || references.some((reference) => !isReferenceComplete(reference?.status));
  const mismatchByRefNum = new Map(
    ((referenceMismatches?.mismatches || []).map((m) => [Number(m?.reference_number), m]))
  );
  const normalizedAgreements = [
    ...operationalAgreements.filter((agreement) => agreement.id !== 'contract_acceptance' && agreement.id !== 'handbook_acknowledgement' && agreement.id !== 'employee_handbook_acknowledgement'),
    ...(handbookAgreement ? [handbookAgreement] : []),
    ...(contractAgreement ? [contractAgreement] : []),
  ].filter((agreement, idx, arr) => arr.findIndex((x) => x?.id === agreement?.id) === idx);
  const agreementDisplays = normalizedAgreements.map((agreement) => ({
    agreement,
    display: getAgreementDisplay(agreement, { contractEligibility: effectiveContractEligibility }),
  }));
  const agreementsActionRequiredCount = agreementDisplays.filter(({ display }) => display.tone === 'critical').length;
  const agreementsCompletedCount = agreementDisplays.filter(({ display }) => display.tone === 'success').length;
  const agreementsHasInProgressState = agreementDisplays.some(({ display }) => display.tone === 'info');
  const activeTrainingExpiringSoon = alerts.filter((entry) => entry?.type === 'training').length;
  const completedCompetencyCount = (competency_assessments || []).filter(
    (item) => item?.outcome === 'pass' || item?.status === 'completed'
  ).length;
  const completedSpotCheckCount = (spot_checks || []).filter(
    (item) => ['pass', 'satisfactory', 'completed'].includes((item?.outcome || '').toLowerCase())
  ).length;
  const completedSupervisionCount = (supervisions || []).filter(
    (item) => (item?.status || '').toLowerCase() === 'completed'
  ).length;
  const pendingWorkerTasks = worker_tasks.filter((task) => String(task?.status || '').toLowerCase() === 'pending');
  const mapWorkerTaskToNextAction = (task) => {
    if (!task) return null;
    return {
      key: task.key || task.type || 'task',
      title: task.title || 'Action required',
      description: task.description || 'Open this task to continue your onboarding.',
      primaryLabel: 'Open task',
      route: task.action_route || '#training',
      level: task.blocking_readiness ? 'critical' : 'high',
    };
  };
  // Synthesize a fallback NextAction from pending agreements (Tier 4 fix).
  // Without this the NextActionCard rendered "You're all caught up" for
  // applicants who still had to sign a contract — contradicting the
  // Readiness Checklist directly above it. Trust the agreement payload so
  // the next-action surface NEVER tells a lie.
  const synthesizeAgreementNextAction = () => {
    const allAgreements = Array.isArray(operationalAgreements) ? operationalAgreements : [];
    const agreementKey = (a) => String(a?.id || a?.agreement_type || a?.key || '').toLowerCase();
    // Contract: actionable when the worker can sign right now.
    const pendingContract = allAgreements.find((a) => {
      if (agreementKey(a) !== 'contract_acceptance') return false;
      const status = String(a?.status || '').toLowerCase();
      // Tier 4 sync fix: same logic as handbook — worker has no further
      // action if the contract is signed/awaiting review/verified.
      const verified = a?.verified === true
        || status === 'verified'
        || status === 'completed'
        || status === 'fully_executed'
        || status === 'signed'
        || status === 'acknowledged'
        || status === 'submitted'
        || status === 'awaiting_review';
      const canSignNow = (a?.can_sign === true) || (effectiveContractEligibility?.can_sign === true);
      return !verified && (canSignNow || a?.lifecycle_status === 'awaiting_worker_signature');
    });
    if (pendingContract) {
      return {
        key: 'sign_contract',
        title: 'Sign your employment contract',
        description: 'Review the contract PDF, then add your signature to complete onboarding.',
        primaryLabel: 'Review & sign contract',
        route: '#agreements-section',
        level: 'critical',
      };
    }
    // Contract locked: show pre-sign progress so the worker knows what's
    // still outstanding (vs being told "all caught up").
    const lockedContract = allAgreements.find((a) => {
      if (agreementKey(a) !== 'contract_acceptance') return false;
      const status = String(a?.status || a?.lifecycle_status || '').toLowerCase();
      const isTerminal = ['verified', 'completed', 'fully_executed', 'signed', 'acknowledged', 'submitted', 'awaiting_review'].includes(status);
      if (isTerminal) return false;
      if (a?.contract_signing_unlocked === false) return true;
      // Safety net: if eligibility explicitly says cannot sign and contract is still pending,
      // never allow "all caught up" to render.
      return effectiveContractEligibility?.can_sign === false && (status === 'pending_signature' || status === 'awaiting_worker_signature');
    });
    if (lockedContract) {
      const blockerCount = Array.isArray(lockedContract.contract_signing_blockers)
        ? lockedContract.contract_signing_blockers.length
        : 0;
      return {
        key: 'contract_locked',
        title: 'Contract awaiting earlier steps',
        description: blockerCount > 0
          ? `${blockerCount} item${blockerCount === 1 ? '' : 's'} still needed before your contract can be signed.`
          : 'Your contract will unlock once the remaining onboarding checks are complete.',
        primaryLabel: 'See what\'s outstanding',
        route: '#agreements-section',
        level: 'high',
      };
    }
    // Handbook: actionable when worker hasn't yet acknowledged it.
    const pendingHandbook = allAgreements.find((a) => {
      const k = agreementKey(a);
      if (k !== 'handbook_acknowledgement' && k !== 'employee_handbook_acknowledgement') return false;
      const status = String(a?.status || '').toLowerCase();
      // Tier 4 sync fix: treat signed/acknowledged/submitted as "done for
      // the worker" even when admin hasn't yet verified — the worker has
      // no further action at that point, admin does.
      const verified = a?.verified === true
        || status === 'verified'
        || status === 'completed'
        || status === 'acknowledged'
        || status === 'signed'
        || status === 'submitted'
        || status === 'awaiting_review';
      return !verified;
    });
    if (pendingHandbook) {
      return {
        key: 'acknowledge_handbook',
        title: 'Acknowledge the Employee Handbook',
        description: 'Review the handbook PDF, then confirm you have read and understood it.',
        primaryLabel: 'Review & acknowledge',
        route: '#agreements-section',
        level: 'high',
      };
    }
    return null;
  };
  const displayedNextAction = mapWorkerTaskToNextAction(pendingWorkerTasks[0])
    || synthesizeAgreementNextAction();

  const scrollToSection = (selector) => {
    const node = document.querySelector(selector);
    if (node) {
      node.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return true;
    }
    return false;
  };

  const handleNextAction = (action) => {
    const route = action?.route || '';
    if (route.startsWith('/worker/dashboard#')) {
      const hashRoute = `#${route.split('#')[1] || ''}`;
      return handleNextAction({ ...action, route: hashRoute });
    }
    if (route.startsWith('/')) {
      navigate(route);
      return;
    }
    switch (action?.route) {
      case '#documents-cv':
        triggerCvFileInput();
        return;
      case '#agreements-contract':
        if (contractDisplay.workerActionable && effectiveContractCanSign) {
          setShowSignaturePad(true);
          return;
        }
        scrollToSection('[data-testid="agreements-section"]');
        return;
      case '#forms':
        scrollToSection('[data-testid="forms-section"]') || scrollToSection('[data-testid="employment-readiness-checklist"]');
        return;
      case '#agreements-handbook':
        if (handbookAgreement && handbookDisplay.workerActionable && (handbookAgreement.file_url || handbookAgreement.download_url)) {
          openHandbookAckModal(handbookAgreement);
          return;
        }
        scrollToSection('[data-testid="agreements-section"]');
        return;
      case '#documents':
        scrollToSection('[data-testid="documents-card"]') || scrollToSection('[data-testid="missing-documents-section"]');
        return;
      case '#training':
        scrollToSection('[data-testid="training-card"]') || scrollToSection('[data-testid="recommended-training-section"]');
        return;
      case '#induction':
        scrollToSection('[data-testid="induction-section"]') || scrollToSection('[data-testid="employment-readiness-checklist"]');
        return;
      case '#checks':
        scrollToSection('[data-testid="checks-card"]') || scrollToSection('[data-testid="references-section"]') || scrollToSection('[data-testid="employment-gaps-section"]');
        return;
      default:
        scrollToSection('[data-testid="employment-readiness-checklist"]');
    }
  };

  const readinessState = (employment_readiness || '').toLowerCase();
  const isReadinessReady = readinessState === 'ready_for_work';
  const readinessTone =
    readinessState === 'system_issue_preventing_completion'
      ? 'red'
      : isReadinessReady
        ? 'green'
        : 'amber';
  const readinessHeadline = employment_readiness_label || (isReadinessReady ? 'Ready for Work' : 'Not ready for work');
  const nextReadinessBlocker = employment_readiness_blockers[0];
  const readinessChecklist = (
    <Card
      className={`border shadow-sm ${
        readinessTone === 'green'
          ? 'border-green-200 bg-green-50/60'
          : readinessTone === 'red'
            ? 'border-red-200 bg-red-50/60'
          : readinessTone === 'amber'
            ? 'border-amber-200 bg-amber-50/60'
            : 'border-blue-200 bg-blue-50/60'
      }`}
      data-testid="employment-readiness-checklist"
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <CardTitle className="text-lg text-slate-900">Readiness checklist</CardTitle>
              <LifecycleStagePill
                status={isActiveEmployee ? 'active' : 'onboarding'}
                stage={isActiveEmployee ? 'employee' : 'applicant'}
              />
            </div>
            <p className="mt-1 text-sm text-slate-600">
              {progress.completed} of {progress.required} required items complete
            </p>
          </div>
          <Badge className={readinessTone === 'green' ? 'bg-green-100 text-green-700' : readinessTone === 'red' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}>
            {readinessHeadline}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <Progress value={progress.percentage} className="h-2.5" />
        {!isReadinessReady && nextReadinessBlocker ? (
          <p className="mt-3 text-sm text-slate-700">
            <span className="font-medium">Next action:</span>{' '}
            {nextReadinessBlocker.label}
          </p>
        ) : null}
        {!isReadinessReady && employment_readiness_blockers.length > 0 ? (
          <ul className="mt-3 space-y-2">
            {employment_readiness_blockers.map((blocker, index) => (
              <li key={`${blocker.label}-${index}`} className="flex items-start gap-2 text-sm text-slate-700">
                <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-500" />
                <span>{blocker.label}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-green-700">Everything required from you is complete.</p>
        )}
      </CardContent>
    </Card>
  );

  const supportCard = (
    <Card className="border border-slate-200 shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-slate-900">Support</CardTitle>
        <p className="mt-1 text-sm text-slate-600">Need help with your file? Refresh your dashboard or contact Osabea.</p>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button variant="outline" className="w-full sm:w-auto" onClick={fetchDashboard}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh dashboard
          </Button>
          <Button variant="outline" className="w-full sm:w-auto" onClick={() => setShowSetPasswordModal(true)}>
            <Lock className="mr-2 h-4 w-4" />
            {accountStatus.has_password ? 'Change password' : 'Set password'}
          </Button>
          <Button variant="outline" className="w-full sm:w-auto" onClick={() => setShowNotificationsPanel((current) => !current)}>
            <Bell className="mr-2 h-4 w-4" />
            Notifications
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <WorkerDashboardPage
      header={(
        <DashboardHeader
          orgName={orgSettings.organisation_name || 'Healthcare Portal'}
          workerName={employee?.name || 'Worker'}
          subtitle={isActiveEmployee ? 'Your staff file and employment record live here.' : 'We will guide you through your onboarding steps one at a time.'}
          progressLabel={`${progress.completed} of ${progress.required} required items complete`}
          unreadCount={unreadCount}
          onRefresh={fetchDashboard}
          onToggleNotifications={() => setShowNotificationsPanel(!showNotificationsPanel)}
          onLogout={handleLogout}
        />
      )}
      nextAction={<NextActionCard action={displayedNextAction} onPrimaryAction={handleNextAction} />}
      readinessChecklist={readinessChecklist}
    >
      {/* Tier 4 active-employee tab toggle — only rendered when the worker
          is fully cleared for work. Applicants/onboarders see the original
          single-stream layout. Today = live work; Staff File = archive. */}
      {isActiveEmployee && (
        <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white p-1 shadow-sm" data-testid="worker-tab-toggle">
          <button
            type="button"
            onClick={() => setActiveWorkerTab('today')}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${activeWorkerTab === 'today' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-50'}`}
            data-testid="worker-tab-today"
          >
            Today
          </button>
          <button
            type="button"
            onClick={() => setActiveWorkerTab('file')}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${activeWorkerTab === 'file' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-50'}`}
            data-testid="worker-tab-file"
          >
            My Staff File
          </button>
        </div>
      )}
      {pendingWorkerTasks.length > 0 ? (
        <Card className="border border-red-200 bg-red-50/60 shadow-sm" data-testid="worker-action-required-section">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg text-slate-900">Action Required</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-2">
              {pendingWorkerTasks.map((task) => (
                <div key={task.key || task.title} className="flex flex-col gap-2 rounded-lg border border-red-100 bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900">{task.title}</p>
                    <p className="text-xs text-slate-600">{task.required ? 'Required before readiness clearance' : 'Action available'}</p>
                  </div>
                  <Button
                    size="sm"
                    className="w-full sm:w-auto"
                    onClick={() => handleNextAction(mapWorkerTaskToNextAction(task))}
                  >
                    Open task
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : null}
      {showNotificationsPanel && (
        <div className="fixed inset-x-4 top-20 z-50 mx-auto max-w-sm rounded-lg border border-slate-200 bg-white shadow-lg">
                  <div className="p-3 border-b border-slate-200 flex items-center justify-between">
                    <h3 className="font-semibold text-slate-800">Notifications</h3>
                    {unreadCount > 0 && (
                      <Badge className="bg-red-100 text-red-700">{unreadCount} unread</Badge>
                    )}
                  </div>
                  <div className="max-h-80 overflow-y-auto">
                    {notifications.length === 0 ? (
                      <div className="p-4 text-center text-slate-500 text-sm">
                        No notifications
                      </div>
                    ) : (
                      notifications.slice(0, 5).map((notif) => (
                        <div 
                          key={notif.id} 
                          className={`p-3 border-b border-slate-100 hover:bg-slate-50 cursor-pointer ${!notif.read ? 'bg-blue-50' : ''}`}
                          onClick={() => {
                            if (!notif.read) markNotificationRead(notif.id);
                          }}
                        >
                          <div className="flex items-start gap-2">
                            {notif.type === 'cv_rejected' ? (
                              <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
                            ) : (
                              <Bell className="h-4 w-4 text-blue-500 flex-shrink-0 mt-0.5" />
                            )}
                            <div className="flex-1 min-w-0">
                              <p className={`text-sm ${!notif.read ? 'font-semibold text-slate-800' : 'text-slate-700'}`}>
                                {notif.title}
                              </p>
                              <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                                {notif.message}
                              </p>
                              <p className="text-xs text-slate-400 mt-1">
                                {formatDate(notif.created_at)}
                              </p>
                            </div>
                            {!notif.read && (
                              <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0" />
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                  {notifications.length > 5 && (
                    <div className="p-2 text-center border-t border-slate-200">
                      <button className="text-sm text-purple-600 hover:underline">
                        View all notifications
                      </button>
                    </div>
                  )}
          </div>
      )}

      {/* Set Password Modal */}
      <Dialog open={showSetPasswordModal} onOpenChange={setShowSetPasswordModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Lock className="h-5 w-5 text-purple-600" />
              {accountStatus.has_password ? 'Change Password' : 'Set Password'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <p className="text-sm text-slate-600">
              {accountStatus.has_password 
                ? 'Update your password for faster login.'
                : 'Set a password for faster login. You can still use magic links if you prefer.'}
            </p>
            
            {accountStatus.has_password && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Current Password</label>
                <input
                  type="password"
                  value={passwordForm.current_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Enter current password"
                />
              </div>
            )}
            
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">New Password</label>
              <input
                type="password"
                value={passwordForm.new_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="Enter new password"
              />
              <p className="text-xs text-slate-500">
                Min 8 characters, 1 uppercase, 1 number
              </p>
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Confirm Password</label>
              <input
                type="password"
                value={passwordForm.confirm_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="Confirm new password"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSetPasswordModal(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleSetPassword} 
              disabled={settingPassword || !passwordForm.new_password || !passwordForm.confirm_password}
              className="bg-purple-600 hover:bg-purple-700"
            >
              {settingPassword ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              {accountStatus.has_password ? 'Update Password' : 'Set Password'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Profile Completion Banner - for offline PDF imports */}
        {profileCompletionStatus?.needs_wizard && !isActiveEmployee && (
          <Card className="border-purple-200 bg-purple-50 shadow-sm" data-testid="profile-completion-banner">
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                    <User className="h-5 w-5 text-purple-600" />
                  </div>
                  <div>
                    <h4 className="font-medium text-purple-900">Complete Your Profile</h4>
                    <p className="text-sm text-purple-700">
                      {profileCompletionStatus.completed_sections}/{profileCompletionStatus.total_sections} sections complete • 
                      Please fill in the remaining information
                    </p>
                  </div>
                </div>
                <Button 
                  onClick={() => setShowProfileWizard(true)}
                  className="bg-purple-600 hover:bg-purple-700"
                  data-testid="complete-profile-btn"
                >
                  <Edit3 className="h-4 w-4 mr-2" />
                  Complete Profile
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {showFileSections && (
        <Card className="border border-slate-200 shadow-sm" data-testid="checks-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg text-slate-900">Checks</CardTitle>
            <p className="mt-1 text-sm text-slate-600">References, employment history, and onboarding forms.</p>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-2 text-sm text-slate-700">
              <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                <span>Forms</span>
                <Badge className="bg-slate-100 text-slate-700">{forms.filter((form) => isFormAdminComplete(form.status)).length}/{forms.length || 0} complete</Badge>
              </div>
              <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                <span>References</span>
                <Badge className={referencesNeedAction ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}>
                  {referencesNeedAction ? 'Needs attention' : 'Complete'}
                </Badge>
              </div>
              <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                <span>Employment history</span>
                <Badge className={gapsNeedAction ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}>
                  {gapsNeedAction ? 'Needs attention' : 'Complete'}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
        )}

        {isActiveEmployee && (
          <Card className="border border-slate-200 shadow-sm" data-testid="active-obligations-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg text-slate-900">Ongoing obligations</CardTitle>
              <p className="mt-1 text-sm text-slate-600">
                Your active workforce compliance schedule and review activity.
              </p>
            </CardHeader>
            <CardContent className="pt-0 space-y-3">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <div className="rounded-lg border border-red-100 bg-red-50 px-3 py-2">
                  <p className="text-xs text-red-700">Overdue</p>
                  <p className="text-lg font-semibold text-red-800">{recurring_compliance_summary.overdue || 0}</p>
                </div>
                <div className="rounded-lg border border-amber-100 bg-amber-50 px-3 py-2">
                  <p className="text-xs text-amber-700">Due now</p>
                  <p className="text-lg font-semibold text-amber-800">{recurring_compliance_summary.due || 0}</p>
                </div>
                <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-2">
                  <p className="text-xs text-blue-700">Upcoming</p>
                  <p className="text-lg font-semibold text-blue-800">{recurring_compliance_summary.upcoming || 0}</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                  <p className="text-xs text-slate-600">Scheduled</p>
                  <p className="text-lg font-semibold text-slate-800">{recurring_compliance_summary.scheduled || 0}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                  <p className="text-xs text-slate-600">Training refresh</p>
                  <p className="text-sm text-slate-800">
                    {expired_trainings.length} expired, {activeTrainingExpiringSoon} expiring soon
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                  <p className="text-xs text-slate-600">Supervision, spot checks, competency</p>
                  <p className="text-sm text-slate-800">
                    Supervisions {completedSupervisionCount}/{supervisions.length}, Spot checks {completedSpotCheckCount}/{spot_checks.length}, Competency {completedCompetencyCount}/{competency_assessments.length}
                  </p>
                </div>
              </div>

              {recurringItems.length > 0 && (
                <div className="rounded-lg border border-slate-200 bg-white">
                  <button
                    type="button"
                    onClick={() => setShowRecurringDetails((prev) => !prev)}
                    className="flex w-full items-center justify-between px-3 py-2 text-left"
                    data-testid="toggle-recurring-details"
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-900">Recurring compliance details</p>
                      <p className="text-xs text-slate-600">Read-only schedule from Osabea compliance records</p>
                    </div>
                    {showRecurringDetails ? <ChevronUp className="h-4 w-4 text-slate-500" /> : <ChevronDown className="h-4 w-4 text-slate-500" />}
                  </button>

                  {showRecurringDetails && (
                    <div className="space-y-3 border-t border-slate-100 px-3 py-3">
                      {['overdue', 'due', 'upcoming', 'scheduled'].map((statusKey) => {
                        const sectionItems = recurringItemsByStatus[statusKey];
                        if (!sectionItems.length) return null;
                        const statusMeta = RECURRING_STATUS_UI[statusKey];
                        return (
                          <div key={statusKey} className="space-y-2">
                            <div className="flex items-center gap-2">
                              <Badge className={statusMeta.badge}>{statusMeta.label}</Badge>
                              <span className="text-xs text-slate-500">{sectionItems.length} item(s)</span>
                            </div>
                            <div className="space-y-1">
                              {sectionItems.map((item) => (
                                <div key={item.id} className="flex items-center justify-between rounded-md bg-slate-50 px-2.5 py-2">
                                  <div>
                                    <p className="text-sm font-medium text-slate-800">{item.item_name || RECURRING_TYPE_LABELS[item.item_type] || 'Recurring item'}</p>
                                    <p className="text-xs text-slate-500">{RECURRING_TYPE_LABELS[item.item_type] || item.item_type || 'Recurring'} • Due {formatDate(item.next_due_date)}</p>
                                  </div>
                                  {(statusKey === 'due' || statusKey === 'upcoming') && typeof item.days_until_due === 'number' && (
                                    <span className="text-xs text-slate-500">in {item.days_until_due}d</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {isActiveEmployee && (
          <Card className="border border-slate-200 shadow-sm" data-testid="worker-my-shifts-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg text-slate-900">My Shifts</CardTitle>
              <p className="mt-1 text-sm text-slate-600">Your assigned shifts and recent shift updates.</p>
            </CardHeader>
            <CardContent className="pt-0">
              {workerShiftsLoading ? (
                <div className="flex items-center justify-center py-6">
                  <Loader2 className="h-5 w-5 animate-spin text-slate-500" />
                </div>
              ) : workerShifts.length === 0 ? (
                <p className="text-sm text-slate-600">No upcoming assigned shifts.</p>
              ) : (
                <div className="space-y-2">
                  {workerShifts.map((item) => {
                    const shift = item.shift || {};
                    const responseStatus = item.worker_response_status || item.assignment?.worker_response_status || 'pending';
                    const assignmentStatus = item.assignment_status || item.assignment?.status || 'active';
                    const attendanceStatus = getWorkerShiftAttendanceStatus(item);
                    const canRespond = (item.assignment_status === 'active') && (responseStatus === 'pending' || !responseStatus);
                    return (
                      <div key={item.assignment_id || shift.id} className="rounded-lg border border-slate-200 bg-white p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="font-medium text-slate-900">{shift.location_text || 'Location pending'}</p>
                            {shift.care_location ? (
                              <p className="mt-1 text-xs text-slate-600">
                                {shift.care_location.name}
                                {shift.care_location.address_line_1 ? `, ${shift.care_location.address_line_1}` : ''}
                                {shift.care_location.city ? `, ${shift.care_location.city}` : ''}
                              </p>
                            ) : null}
                            <p className="mt-1 text-xs text-slate-600">{formatDate(shift.start_at)} • {formatDateTime(shift.start_at).split(', ').pop()} - {formatDateTime(shift.end_at).split(', ').pop()}</p>
                            <p className="mt-1 text-xs text-slate-600">Role: {shift.role_required || '—'}</p>
                            {shift.notes ? <p className="mt-1 text-xs text-slate-500 line-clamp-2">Notes: {shift.notes}</p> : null}
                            {item.worker_response_note ? <p className="mt-1 text-xs text-slate-500 line-clamp-2">Your note: {item.worker_response_note}</p> : null}
                            {item.cancellation_reason ? <p className="mt-1 text-xs text-red-700 line-clamp-2">Cancellation reason: {item.cancellation_reason}</p> : null}
                          </div>
                          <div className="flex shrink-0 flex-col items-end gap-2">
                            <Badge className={
                              assignmentStatus === 'cancelled'
                                ? 'bg-slate-100 text-slate-700'
                                : assignmentStatus === 'completed'
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-amber-100 text-amber-700'
                            }>
                              {assignmentStatus}
                            </Badge>
                            <Badge className={
                              responseStatus === 'accepted'
                                ? 'bg-green-100 text-green-700'
                                : responseStatus === 'rejected'
                                  ? 'bg-red-100 text-red-700'
                                  : 'bg-slate-100 text-slate-700'
                            }>
                              {responseStatus === 'accepted' ? 'Accepted' : responseStatus === 'rejected' ? 'Rejected' : 'Awaiting response'}
                            </Badge>
                            <Badge className={
                              attendanceStatus === 'approved'
                                ? 'bg-green-100 text-green-700'
                                : attendanceStatus === 'submitted'
                                  ? 'bg-blue-100 text-blue-700'
                                  : attendanceStatus === 'open'
                                    ? 'bg-amber-100 text-amber-700'
                                    : attendanceStatus === 'rejected'
                                      ? 'bg-red-100 text-red-700'
                                      : 'bg-slate-100 text-slate-700'
                            }>
                              Attendance: {attendanceStatus || 'not started'}
                            </Badge>
                            {canRespond && (
                              <div className="flex items-center gap-1">
                                <Button variant="outline" size="sm" onClick={() => openWorkerShiftResponseModal(item, 'accept')}>
                                  Accept
                                </Button>
                                <Button variant="destructive" size="sm" onClick={() => openWorkerShiftResponseModal(item, 'reject')}>
                                  Reject
                                </Button>
                              </div>
                            )}
                            <Button variant="outline" size="sm" onClick={() => handleOpenWorkerShift(shift.id)}>
                              <Eye className="mr-1 h-3.5 w-3.5" />
                              View
                            </Button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {isActiveEmployee && (
        <Card className="border border-slate-200 shadow-sm" data-testid="worker-incidents-card">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <CardTitle className="text-lg text-slate-900">Incidents & Concerns</CardTitle>
                <p className="mt-1 text-sm text-slate-600">Report an incident and track review status.</p>
              </div>
              <Button size="sm" onClick={() => setIncidentModalOpen(true)}>
                <Plus className="mr-1 h-4 w-4" />
                Report
              </Button>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            {workerIncidentsLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-slate-500" />
              </div>
            ) : workerIncidents.length === 0 ? (
              <p className="text-sm text-slate-600">No incidents submitted yet.</p>
            ) : (
              <div className="space-y-2">
                {workerIncidents.slice(0, 5).map((incident) => (
                  <div key={incident.id} className="rounded-lg border border-slate-200 bg-white p-3">
                    {(() => {
                      const statusMeta = getWorkerIncidentStatusMeta(incident.status);
                      return (
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-medium text-slate-900">{incident.reference_number || incident.title}</p>
                        <p className="mt-1 text-xs text-slate-600">{formatDateTime(incident.date_occurred)} • {incident.location || 'Location not set'}</p>
                        <p className="mt-1 text-xs text-slate-600 line-clamp-2">{incident.description}</p>
                        <p className="mt-2 text-xs text-slate-700">{incident.progress_summary || 'Your report has been submitted and is awaiting review.'}</p>
                        {incident.outcome_summary ? (
                          <div className="mt-2 rounded-md border border-slate-200 bg-slate-50 p-2">
                            <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Follow-up summary</p>
                            <p className="mt-1 text-xs text-slate-700">{incident.outcome_summary}</p>
                          </div>
                        ) : null}
                        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-500">
                          {incident.reported_at ? <span>Submitted {formatDateTime(incident.reported_at)}</span> : null}
                          {incident.reviewed_at ? <span>Reviewed {formatDateTime(incident.reviewed_at)}</span> : null}
                          {incident.closed_at ? <span>Closed {formatDateTime(incident.closed_at)}</span> : null}
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <Badge className={statusMeta.className}>
                          {incident.status_label || statusMeta.label}
                        </Badge>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openIncidentDetail(incident)}
                        >
                          View
                        </Button>
                      </div>
                    </div>
                      );
                    })()}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
        )}

        {/* Forms Section */}
        {showFileSections && <FormsSection />}

        {/* Employment History & Gaps — visible during onboarding and for active employees */}
        {showFileSections && <EmploymentGapsSection />}

        {/* ========== CV REJECTION ALERT ========== */}
        {notifications.some(n => n.type === 'cv_rejected' && !n.resolved) && (
          <Card className="shadow-md border-0 border-l-4 border-l-red-500 bg-red-50/50" data-testid="cv-rejection-alert">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg text-red-800">
                    <AlertTriangle className="h-5 w-5" />
                    CV Requires Attention
                  </CardTitle>
                  <p className="text-xs text-red-700 mt-1">
                    Your CV was reviewed and requires additional information
                  </p>
                </div>
                <Badge className="bg-red-100 text-red-700">
                  Action Required
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              {notifications.filter(n => n.type === 'cv_rejected' && !n.resolved).map((notif) => (
                <div key={notif.id} className="p-4 bg-white rounded-xl border border-red-200">
                  <p className="text-red-800 font-medium mb-2">{notif.message}</p>
                  <p className="text-sm text-red-600 mb-4">
                    Please either explain any employment gaps or upload an updated CV.
                  </p>
                  <div className="flex gap-2">
                    <Button 
                      size="sm" 
                      className="bg-purple-600 hover:bg-purple-700"
                      onClick={triggerCvFileInput}
                      disabled={uploading === 'cv'}
                      data-testid={`cv-rejection-upload-btn-${notif.id}`}
                    >
                      {uploading === 'cv' ? (
                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      ) : (
                        <Upload className="h-4 w-4 mr-1" />
                      )}
                      {uploading === 'cv' ? 'Uploading…' : 'Upload New CV'}
                    </Button>
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => {
                        const el = document.querySelector('[data-testid="employment-history-section"]')
                          || document.querySelector('[data-testid="employment-gaps-section"]');
                        if (el) {
                          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        } else {
                          toast.info('Please scroll down to Employment History to explain gaps');
                        }
                      }}
                    >
                      <MessageSquare className="h-4 w-4 mr-1" />
                      Explain Gaps
                    </Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {showFileSections && cvStatus && (
          <Card className="shadow-sm border border-slate-200" data-testid="documents-card">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <FileText className="h-5 w-5 text-slate-700" />
                    Documents
                  </CardTitle>
                  <p className="mt-1 text-xs text-slate-500">Your CV and onboarding evidence in one place.</p>
                </div>
                <Badge className={
                  cvDisplay.tone === 'success' ? 'bg-green-100 text-green-700' :
                  cvDisplay.tone === 'critical' ? 'bg-red-100 text-red-700' :
                  'bg-blue-100 text-blue-700'
                }>
                  {cvDisplay.badge}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-medium text-slate-900">CV / Resume</p>
                    <p className="mt-1 text-sm text-slate-600">{cvDisplay.description}</p>
                  </div>
                  <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
                    {cvDisplay.hasCv ? (
                      <>
                        <Button
                          variant="outline"
                          className="w-full sm:w-auto"
                          onClick={() => cvStatus?.cv_document && openDocumentViewer({
                            ...cvStatus.cv_document,
                            name: 'CV / Resume',
                            file_name: cvStatus.cv_document.file_name,
                          })}
                        >
                          <Eye className="mr-2 h-4 w-4" />
                          View CV
                        </Button>
                        {(cvStatus?.can_upload_cv === true || cvStatus?.replacement_required === true || ['rejected', 'replacement_requested', 'replacement_required', 'missing'].includes(String(cvStatus?.cv_status || '').toLowerCase())) && (
                          <Button
                            className="w-full sm:w-auto"
                            onClick={triggerCvFileInput}
                            disabled={uploading === 'cv'}
                          >
                            {uploading === 'cv' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                            Upload replacement CV
                          </Button>
                        )}
                      </>
                    ) : cvDisplay.canUpload ? (
                      <Button className="w-full sm:w-auto" onClick={triggerCvFileInput} disabled={uploading === 'cv'}>
                        {uploading === 'cv' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                        {cvDisplay.primaryLabel}
                      </Button>
                    ) : null}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* ========== REFERENCE-EMPLOYMENT MISMATCH ALERT ========== */}
        {/* CQC: filter out mismatches for references that admin has already
            requested replacement for. Once admin clicks "Request new
            referee" the worker no longer needs to re-explain the previous
            mismatch — they just need to provide fresh details. Cross-check
            against the references list below where can_provide_new=true
            indicates the slot is awaiting a new referee. */}
        {(() => {
          const replacementRefNums = new Set(
            (references || [])
              .filter(r => r?.can_provide_new === true)
              .map(r => r.reference_number)
          );
          const activeMismatches = (referenceMismatches?.mismatches || []).filter(
            m => !replacementRefNums.has(m.reference_number)
          );
          const hasActiveMismatches = !isActiveEmployee && activeMismatches.length > 0;
          if (!hasActiveMismatches) return null;
          return (
          <Card className="shadow-md border-0 border-l-4 border-l-amber-500 bg-amber-50/50" data-testid="reference-mismatch-alert">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg text-amber-800">
                    <Link2 className="h-5 w-5" />
                    Reference-Employment Mismatch
                  </CardTitle>
                  <p className="text-xs text-amber-700 mt-1">
                    {activeMismatches.length} reference(s) don't match your declared employment history
                  </p>
                </div>
                <Badge className="bg-amber-100 text-amber-700">
                  Action Required
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {activeMismatches.map((mismatch, idx) => (
                  <div 
                    key={idx}
                    className={`p-4 rounded-xl border ${
                      mismatch.mismatch_admin_decision === 'accepted' ? 'bg-green-50 border-green-200' :
                      mismatch.mismatch_admin_decision === 'rejected' ? 'bg-red-50 border-red-200' :
                      mismatch.mismatch_admin_decision === 'needs_clarification' ? 'bg-amber-50 border-amber-400' :
                      mismatch.explanation_status === 'submitted' ? 'bg-blue-50 border-blue-200' :
                      'bg-white border-amber-200'
                    }`}
                    data-testid={`mismatch-ref-${mismatch.reference_number}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                          mismatch.mismatch_admin_decision === 'accepted' ? 'bg-green-100' :
                          mismatch.mismatch_admin_decision === 'rejected' ? 'bg-red-100' :
                          mismatch.mismatch_admin_decision === 'needs_clarification' ? 'bg-amber-100' :
                          mismatch.explanation_status === 'submitted' ? 'bg-blue-100' :
                          'bg-amber-100'
                        }`}>
                          {mismatch.mismatch_admin_decision === 'accepted' ? (
                            <CheckCircle className="h-5 w-5 text-green-600" />
                          ) : mismatch.mismatch_admin_decision === 'rejected' ? (
                            <AlertCircle className="h-5 w-5 text-red-600" />
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
                        ) : mismatch.mismatch_admin_decision === 'rejected' ? (
                          <>
                            <Badge className="bg-red-100 text-red-700 text-xs">
                              <AlertCircle className="h-3 w-3 mr-1" />
                              Rejected
                            </Badge>
                            <Button
                              size="sm"
                              onClick={() => openMismatchExplanationModal(mismatch)}
                              className="gap-1 bg-red-600 hover:bg-red-700"
                              data-testid={`re-explain-mismatch-${mismatch.reference_number}`}
                            >
                              <MessageSquare className="h-4 w-4" />
                              Re-explain
                            </Button>
                          </>
                        ) : mismatch.mismatch_admin_decision === 'needs_clarification' ? (
                          <>
                            <Badge className="bg-amber-100 text-amber-700 text-xs">
                              <Clock className="h-3 w-3 mr-1" />
                              More Info Needed
                            </Badge>
                            <Button
                              size="sm"
                              onClick={() => openMismatchExplanationModal(mismatch)}
                              className="gap-1 bg-amber-600 hover:bg-amber-700"
                              data-testid={`clarify-mismatch-${mismatch.reference_number}`}
                            >
                              <MessageSquare className="h-4 w-4" />
                              Respond
                            </Button>
                          </>
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
                Osabea checks references against your work history before your file can move forward.
                Please explain any differences so the team can complete your review.
              </p>
            </CardContent>
          </Card>
          );
        })()}

        {/* Professional Registration Status - if applicable */}
        {showFileSections && professional_registration && (
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
                        Waiting for Osabea review
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
                          onClick={() => triggerFileInput(alert.type === 'training' ? `training_${alert.training_id || 'general'}` : `${alert.type}_renewal`)}
                          disabled={uploading === (alert.type === 'training' ? `training_${alert.training_id || 'general'}` : `${alert.type}_renewal`)}
                          data-testid={`upload-renewal-${alert.type}`}
                        >
                          {uploading === (alert.type === 'training' ? `training_${alert.training_id || 'general'}` : `${alert.type}_renewal`) ? (
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
        {((!isActiveEmployee && visibleMissingDocuments.length > 0) || visibleMissingDocuments.some(d => d.rejection)) && (
          <Card className="shadow-md border-0" data-testid="missing-documents-section">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Upload className="h-5 w-5 text-red-500" />
                {visibleMissingDocuments.some(d => d.rejection)
                  ? 'Action Required - Re-upload Documents'
                  : lifecycleStage === 'recruitment'
                    ? 'Documents for Verification'
                    : 'Documents Needed'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {visibleMissingDocuments.map((doc, idx) => (
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
        {isActiveEmployee && expired_trainings?.length > 0 && (
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

        {/* Required Training Evidence */}
        {!isActiveEmployee && (
          <Card className="shadow-md border-0" data-testid="training-card">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <FileText className="h-5 w-5 text-blue-500" />
                    Required training evidence
                  </CardTitle>
                  <p className="text-xs text-slate-500 mt-1">
                    {(all_mandatory_trainings?.length || 8)} required training items needed before work starts. Osabea extracts details from your certificates.
                  </p>
                </div>
                <Badge className={
                  trainingDisplay.tone === 'success'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-amber-100 text-amber-700'
                }>
                  {trainingDisplay.badge}
                </Badge>
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
                {/* Show all mandatory trainings with canonical status */}
                {all_mandatory_trainings.map((training, idx) => {
                  const cfg = TRAINING_STATUS_CONFIG[training.status] || TRAINING_STATUS_CONFIG.missing;
                  const StatusIcon = cfg.Icon;
                  return (
                  <div 
                    key={idx} 
                    className={`p-4 rounded-xl border ${cfg.cardBg}`}
                    data-testid={`training-row-${training.id}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${cfg.iconBg}`}>
                          <StatusIcon className={`h-5 w-5 ${cfg.iconCls}`} />
                        </div>
                        <div>
                          <span className="font-medium text-slate-800">{training.name}</span>
                          {training.status === 'rejected' && training.rejection_reason && (
                            <p className="text-xs text-red-600">Reason: {training.rejection_reason}</p>
                          )}
                          {training.status === 'due_soon' && training.days_until_expiry != null && (
                            <p className="text-xs text-amber-600">Expires in {training.days_until_expiry} days</p>
                          )}
                          {training.expiry_date && training.status !== 'rejected' && training.status !== 'due_soon' && (
                            <p className={`text-xs ${training.status === 'expired' ? 'text-red-600' : 'text-slate-500'}`}>
                              {training.status === 'expired' ? 'Expired: ' : 'Expires: '}
                              {formatDate(training.expiry_date)}
                            </p>
                          )}
                          {training.completion_date && training.status !== 'expired' && (
                            <p className="text-xs text-slate-500">
                              Completed: {formatDate(training.completion_date)}
                            </p>
                          )}
                          {training.detail && training.status === 'due_soon' && training.expiry_date && (
                            <p className="text-xs text-amber-600">{formatDate(training.expiry_date)}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge className={`text-xs ${cfg.badgeCls}`}>
                          <StatusIcon className="h-3 w-3 mr-1" />
                          {cfg.badge}
                        </Badge>
                        {cfg.showUpload && (
                          <Button 
                            size="sm" 
                            variant={training.status === 'rejected' || training.status === 'expired' ? 'default' : 'outline'}
                            onClick={() => triggerFileInput(`training_${training.id}`)}
                            disabled={uploading === `training_${training.id}`}
                            className={training.status === 'rejected' || training.status === 'expired' ? 'gap-1 bg-red-600 hover:bg-red-700 text-white' : 'gap-1'}
                            data-testid={`upload-training-${training.id}`}
                          >
                            {uploading === `training_${training.id}` ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Upload className="h-4 w-4" />
                            )}
                            {cfg.uploadLabel}
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                  );
                })}
              </div>
              <p className="text-xs text-slate-400 mt-4 text-center">
                {ACCEPTED_FORMATS}
              </p>
            </CardContent>
          </Card>
        )}

        {/* ========== RECOMMENDED TRAINING ========== */}
        {!isActiveEmployee && recommended_trainings?.length > 0 && (
          <Card className="shadow-md border-0" data-testid="recommended-training-section">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <FileText className="h-5 w-5 text-slate-400" />
                    Recommended Training
                  </CardTitle>
                  <p className="text-xs text-slate-500 mt-1">
                    These trainings are beneficial but not required for work readiness
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {recommended_trainings.map((training, idx) => {
                  const cfg = TRAINING_STATUS_CONFIG[training.status] || TRAINING_STATUS_CONFIG.missing;
                  const StatusIcon = cfg.Icon;
                  return (
                  <div 
                    key={idx} 
                    className={`p-3 rounded-xl border ${cfg.cardBg}`}
                    data-testid={`recommended-training-row-${training.id}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${cfg.iconBg}`}>
                          <StatusIcon className={`h-4 w-4 ${cfg.iconCls}`} />
                        </div>
                        <div>
                          <span className="font-medium text-sm text-slate-700">{training.name}</span>
                          {training.status === 'rejected' && training.rejection_reason && (
                            <p className="text-xs text-red-600">Reason: {training.rejection_reason}</p>
                          )}
                          {training.status === 'due_soon' && training.days_until_expiry != null && (
                            <p className="text-xs text-amber-600">Expires in {training.days_until_expiry} days</p>
                          )}
                          {training.expiry_date && training.status !== 'due_soon' && (
                            <p className={`text-xs ${training.status === 'expired' ? 'text-red-600' : 'text-slate-500'}`}>
                              {training.status === 'expired' ? 'Expired: ' : 'Expires: '}{formatDate(training.expiry_date)}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge className={`text-xs ${cfg.badgeCls}`}>
                          <StatusIcon className="h-3 w-3 mr-1" />
                          {training.status === 'missing' ? 'Optional' : cfg.badge}
                        </Badge>
                        {cfg.showUpload && (
                          <Button 
                            size="sm" 
                            variant={training.status === 'rejected' || training.status === 'expired' ? 'default' : 'outline'}
                            onClick={() => triggerFileInput(`training_${training.id}`)}
                            disabled={uploading === `training_${training.id}`}
                            className={training.status === 'rejected' || training.status === 'expired' ? 'gap-1 text-xs bg-red-600 hover:bg-red-700 text-white' : 'gap-1 text-xs'}
                            data-testid={`upload-training-${training.id}`}
                          >
                            {uploading === `training_${training.id}` ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Upload className="h-3 w-3" />
                            )}
                            {cfg.uploadLabel}
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                  );
                })}
              </div>
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
                  completedReferencesCount === 2 
                    ? 'bg-green-100 text-green-700' 
                    : 'bg-amber-100 text-amber-700'
                }`}>
                  {completedReferencesCount}/2 Verified
                </Badge>
              </div>
              <div className="mt-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => setShowReferencesDetails((v) => !v)}
                  data-testid="toggle-references-details"
                >
                  {showReferencesDetails ? 'Hide details' : 'Show details'}
                  {showReferencesDetails ? <ChevronUp className="ml-1 h-4 w-4" /> : <ChevronDown className="ml-1 h-4 w-4" />}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {!showReferencesDetails ? (
                <p className="text-sm text-slate-600">
                  References collapsed to reduce noise. Expand to view referee status and required actions.
                </p>
              ) : (
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
                        {/* Worker mismatch explanation action (primary legal evidence path) */}
                        {(() => {
                          const refNum = Number(ref.reference_number);
                          const mismatch = mismatchByRefNum.get(refNum);
                          const status = String(ref.status || '').toLowerCase();
                          const refHasMismatchFlag =
                            ref?.integrity?.mismatch_detected === true ||
                            ref?.mismatch_detected === true;
                          const statusImpliesMismatchContext =
                            status.includes('mismatch') ||
                            status.includes('response_received') ||
                            status.includes('awaiting_review') ||
                            status.includes('pending_admin_review') ||
                            status.includes('reviewed');
                          const needsExplanation =
                            (Boolean(mismatch) || refHasMismatchFlag) &&
                            statusImpliesMismatchContext &&
                            !ref.replacement_requested_at;
                          if (!needsExplanation) return null;
                          const hasExistingExplanation = Boolean(
                            mismatch?.existing_explanation?.text || mismatch?.existing_explanation
                          );
                          return (
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-xs border-amber-300 text-amber-700 hover:bg-amber-50"
                              onClick={() => {
                                setSelectedMismatch(
                                  mismatch || {
                                    reference_number: ref.reference_number,
                                    referee_name: ref.referee_name,
                                    referee_company: ref.organisation || ref.company,
                                    message: 'Please explain why this reference may not match your declared employment history.',
                                    existing_explanation: hasExistingExplanation
                                      ? mismatch.existing_explanation
                                      : undefined,
                                  }
                                );
                                setMismatchExplanationType('');
                                setMismatchExplanationText('');
                                setShowMismatchExplanationModal(true);
                              }}
                              data-testid={`explain-mismatch-ref-${ref.reference_number}`}
                            >
                              {hasExistingExplanation ? 'Update explanation' : 'Explain mismatch'}
                            </Button>
                          );
                        })()}
                        {/* Show "Provide New" button for rejected references */}
                        {ref.can_provide_new && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-xs border-primary text-primary hover:bg-primary hover:text-white"
                            onClick={() => setProvideNewRefNum(prev => prev === ref.reference_number ? null : ref.reference_number)}
                            data-testid={`provide-new-ref-${ref.reference_number}`}
                          >
                            {provideNewRefNum === ref.reference_number ? 'Cancel' : 'Provide New Referee'}
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
                          {/* Inline replacement-referee form */}
                          {provideNewRefNum === ref.reference_number && (
                            <div className="mt-4 pt-4 border-t border-slate-200 space-y-3">
                              <p className="text-sm font-medium text-slate-700">Enter your new referee's details</p>
                              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                                <div>
                                  <label className="text-xs text-slate-500">Full Name *</label>
                                  <input
                                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
                                    placeholder="Jane Smith"
                                    value={provideNewForm.name}
                                    onChange={e => setProvideNewForm(f => ({ ...f, name: e.target.value }))}
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-slate-500">Email *</label>
                                  <input
                                    type="email"
                                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
                                    placeholder="jane@company.com"
                                    value={provideNewForm.email}
                                    onChange={e => setProvideNewForm(f => ({ ...f, email: e.target.value }))}
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-slate-500">Phone</label>
                                  <input
                                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
                                    placeholder="07700 000000"
                                    value={provideNewForm.phone}
                                    onChange={e => setProvideNewForm(f => ({ ...f, phone: e.target.value }))}
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-slate-500">Organisation</label>
                                  <input
                                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
                                    placeholder="ABC Care Ltd"
                                    value={provideNewForm.organisation}
                                    onChange={e => setProvideNewForm(f => ({ ...f, organisation: e.target.value }))}
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-slate-500">Job Title / Position</label>
                                  <input
                                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
                                    placeholder="Line Manager"
                                    value={provideNewForm.position}
                                    onChange={e => setProvideNewForm(f => ({ ...f, position: e.target.value }))}
                                  />
                                </div>
                                <div>
                                  <label className="text-xs text-slate-500">Relationship</label>
                                  <input
                                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
                                    placeholder="e.g. Line Manager"
                                    value={provideNewForm.relationship}
                                    onChange={e => setProvideNewForm(f => ({ ...f, relationship: e.target.value }))}
                                  />
                                </div>
                              </div>
                              <div className="mt-3">
                                <label className="text-xs text-slate-500">
                                  Reason for providing a new referee <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                  rows={3}
                                  className="w-full mt-1 px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
                                  placeholder="e.g. Original referee no longer at the company / unreachable / declined to provide a reference."
                                  value={provideNewForm.change_reason}
                                  onChange={e => setProvideNewForm(f => ({ ...f, change_reason: e.target.value }))}
                                  data-testid={`provide-new-reason-${ref.reference_number}`}
                                />
                                <p className="text-[10px] text-slate-500 mt-1">
                                  At least 10 characters. Required for CQC audit.
                                </p>
                              </div>
                              <Button
                                size="sm"
                                disabled={provideNewLoading || !provideNewForm.name || !provideNewForm.email || (provideNewForm.change_reason || '').trim().length < 10}
                                onClick={() => handleProvideNewSubmit(ref.reference_number)}
                                className="mt-2"
                              >
                                {provideNewLoading ? 'Submitting…' : 'Submit Referee Details'}
                              </Button>
                            </div>
                          )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* ========== INDUCTION CHECKLIST (P1: Worker Dashboard Sync) ========== */}
        {showFileSections && (
          <div data-testid="induction-section">
            <CareCertificateInductionPanel />
          </div>
        )}

        {/* ========== COMPETENCY ASSESSMENTS (P1: Worker Dashboard) ========== */}
        {showFileSections && isActiveEmployee && competency_assessments && competency_assessments.length > 0 && (
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
              {isActiveEmployee && competencyRecurringItems.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-3">
                  <div className="rounded-lg border border-red-100 bg-red-50 px-3 py-2">
                    <p className="text-xs text-red-700">Overdue reviews</p>
                    <p className="text-sm font-semibold text-red-800">{competencyRecurringCounts.overdue}</p>
                  </div>
                  <div className="rounded-lg border border-amber-100 bg-amber-50 px-3 py-2">
                    <p className="text-xs text-amber-700">Due now</p>
                    <p className="text-sm font-semibold text-amber-800">{competencyRecurringCounts.due}</p>
                  </div>
                  <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-2">
                    <p className="text-xs text-blue-700">Upcoming</p>
                    <p className="text-sm font-semibold text-blue-800">{competencyRecurringCounts.upcoming}</p>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                {competency_assessments.map((comp, idx) => (
                  (() => {
                    const reviewState = comp.review_due_date ? getDueState(comp.review_due_date, 30) : null;
                    const isCompleted = comp.outcome === 'pass' || comp.status === 'completed' || comp.status === 'competent';
                    return (
                      <div
                        key={idx}
                        className={`p-3 rounded-xl border ${
                          reviewState === 'overdue' ? 'bg-red-50 border-red-200' :
                          reviewState === 'due_soon' ? 'bg-amber-50 border-amber-200' :
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
                              {(comp.completed_date || comp.scheduled_date) && (
                                <p className="text-xs text-slate-500">
                                  {isCompleted ? 'Completed' : 'Scheduled'}: {formatDate(comp.completed_date || comp.scheduled_date)}
                                </p>
                              )}
                            </div>
                          </div>
                          <Badge className={`text-xs ${
                            comp.outcome === 'pass' ? 'bg-green-100 text-green-700' :
                            comp.outcome === 'fail' ? 'bg-red-100 text-red-700' :
                            reviewState === 'overdue' ? 'bg-red-100 text-red-700' :
                            reviewState === 'due_soon' ? 'bg-amber-100 text-amber-700' :
                            comp.status === 'scheduled' ? 'bg-blue-100 text-blue-700' :
                            'bg-slate-100 text-slate-600'
                          }`}>
                            {comp.outcome === 'pass' ? 'Current' :
                             comp.outcome === 'fail' ? 'Needs Improvement' :
                             reviewState === 'overdue' ? 'Overdue' :
                             reviewState === 'due_soon' ? 'Due soon' :
                             comp.status === 'scheduled' ? 'Scheduled' : 'Pending'}
                          </Badge>
                        </div>

                        {comp.review_due_date && (
                          <p className={`text-xs mt-2 ${
                            reviewState === 'overdue' ? 'text-red-600' :
                            reviewState === 'due_soon' ? 'text-amber-600' :
                            'text-slate-500'
                          }`}>
                            Review due: {formatDate(comp.review_due_date)}
                          </p>
                        )}

                        {comp.follow_up_required && comp.follow_up_date && (
                          <p className="text-xs text-amber-600 mt-1">
                            Follow-up scheduled: {formatDate(comp.follow_up_date)}
                          </p>
                        )}
                      </div>
                    );
                  })()
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* ========== AGREEMENTS (P0: Contract & Handbook Status) ========== */}
        {showFileSections && agreements && agreements.length > 0 && (
          <Card className="shadow-md border-0" data-testid="agreements-section">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <PenTool className="h-5 w-5 text-purple-500" />
                    Agreements & Acknowledgements
                  </CardTitle>
                    <p className="text-xs text-slate-500 mt-1">
                      Review the exact PDF that is on file, then sign or acknowledge it from your portal.
                    </p>
                </div>
                <Badge className={`${
                  agreementsActionRequiredCount > 0 ? 'bg-red-100 text-red-700' :
                  agreements.length > 0 && agreementsCompletedCount === agreements.length ? 'bg-green-100 text-green-700' :
                  agreementsHasInProgressState || agreementsCompletedCount > 0 ? 'bg-blue-100 text-blue-700' :
                  'bg-slate-100 text-slate-600'
                }`}>
                  {agreementsActionRequiredCount > 0
                    ? `${agreementsActionRequiredCount} action required`
                    : `${agreementsCompletedCount} of ${agreements.length} completed`}
                </Badge>
              </div>
              <div className="mt-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => setShowAgreementsDetails((v) => !v)}
                  data-testid="toggle-agreements-details"
                >
                  {showAgreementsDetails ? 'Hide details' : 'Show details'}
                  {showAgreementsDetails ? <ChevronUp className="ml-1 h-4 w-4" /> : <ChevronDown className="ml-1 h-4 w-4" />}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {!showAgreementsDetails ? (
                <p className="text-sm text-slate-600">
                  Agreements collapsed to reduce noise. Expand to review contract and handbook status/actions.
                </p>
              ) : (
              <div className="space-y-3">
                {agreementDisplays.map(({ agreement, display: agreementDisplay }) => {
                  const agreementContractState = resolveLatestContractState(agreement, { contractEligibility: effectiveContractEligibility }).status;
                  const isHistoricalRejectedContract =
                    agreement.id === 'contract_acceptance' &&
                    (
                      ['rejected', 'rejected_reopen_required', 'superseded', 'action_required'].includes(agreementContractState) ||
                      agreement.rejected
                    ) &&
                    !(agreementContractState === 'pending_signature' && effectiveContractCanSign);
                  const compactDescription = truncateAgreementCardText(agreementDisplay.description, 160);
                  const compactTitle = agreement.id === 'handbook_acknowledgement'
                    ? 'Employee Handbook'
                    : agreement.name;
                  const toneClasses =
                    agreementDisplay.tone === 'critical'
                      ? 'bg-red-50 border-red-200'
                      : agreementDisplay.tone === 'success'
                        ? 'bg-green-50 border-green-200'
                        : agreementDisplay.tone === 'info'
                          ? 'bg-blue-50 border-blue-200'
                          : 'bg-slate-50 border-slate-200';
                  const iconClasses =
                    agreementDisplay.tone === 'critical'
                      ? 'bg-red-100 text-red-600'
                      : agreementDisplay.tone === 'success'
                        ? 'bg-green-100 text-green-600'
                        : agreementDisplay.tone === 'info'
                          ? 'bg-blue-100 text-blue-600'
                          : 'bg-slate-100 text-slate-500';
                  return (
                  <div
                    key={agreement.id}
                    className={`p-4 rounded-xl border ${toneClasses}`}
                    data-testid={`agreement-${agreement.id}`}
                  >
                    {isHistoricalRejectedContract ? (
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0 flex-1 w-full whitespace-normal break-normal [overflow-wrap:normal] [word-break:normal]">
                          <p className="text-sm font-medium text-slate-700">
                            Your contract needs to be reissued by your manager.
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto sm:justify-end">
                          {(agreement.file_url || agreement.download_url) && (
                            <>
                              <Button
                                size="sm"
                                variant="outline"
                                className="gap-1 whitespace-nowrap"
                                onClick={() => openDocumentViewer({ ...agreement, name: agreement.name })}
                              >
                                <Eye className="h-3.5 w-3.5" />
                                {agreement.id === 'handbook_acknowledgement' ? 'View handbook' : 'View PDF'}
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="gap-1 whitespace-nowrap"
                                onClick={() => downloadAgreement(agreement)}
                              >
                                <Download className="h-3.5 w-3.5" />
                                Download PDF
                              </Button>
                            </>
                          )}
                          <Badge className="shrink-0 text-xs bg-slate-100 text-slate-600">
                            Historical
                          </Badge>
                        </div>
                      </div>
                    ) : (
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="flex items-start gap-3 min-w-0 flex-1 w-full">
                        <div className={`w-10 h-10 shrink-0 rounded-lg flex items-center justify-center ${iconClasses.split(' ')[0]}`}>
                          {agreement.verified ? (
                            <CheckCircle className={`h-5 w-5 ${iconClasses.split(' ')[1]}`} />
                          ) : agreement.rejected ? (
                            <AlertCircle className={`h-5 w-5 ${iconClasses.split(' ')[1]}`} />
                          ) : agreementDisplay.workerActionable ? (
                            <PenTool className={`h-5 w-5 ${iconClasses.split(' ')[1]}`} />
                          ) : (
                            <Clock className={`h-5 w-5 ${iconClasses.split(' ')[1]}`} />
                          )}
                        </div>
                        <div className="min-w-0 flex-1 w-full whitespace-normal break-normal [overflow-wrap:normal] [word-break:normal]">
                          <span className="font-medium text-slate-700">{compactTitle}</span>
                          <p className="text-xs text-slate-500 mt-0.5">{compactDescription}</p>
                        </div>
                        </div>
                      <div className="flex flex-wrap items-center justify-start gap-2 w-full sm:w-auto sm:justify-end sm:shrink-0">
                        {(agreement.file_url || agreement.download_url) && (
                          <>
                            <Button
                              size="sm"
                              variant="outline"
                              className="gap-1 whitespace-nowrap"
                              onClick={() => openDocumentViewer({ ...agreement, name: agreement.name })}
                            >
                              <Eye className="h-3.5 w-3.5" />
                              {agreement.id === 'handbook_acknowledgement' ? 'View handbook' : 'View PDF'}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="gap-1 whitespace-nowrap"
                              onClick={() => downloadAgreement(agreement)}
                            >
                              <Download className="h-3.5 w-3.5" />
                              Download PDF
                            </Button>
                          </>
                        )}
                        {agreement.id === 'contract_acceptance' && agreementDisplay.workerActionable && effectiveContractCanSign && (
                          <Button
                            size="sm"
                            className="gap-1 whitespace-nowrap"
                            onClick={() => setShowSignaturePad(true)}
                          >
                            <PenTool className="h-3.5 w-3.5" />
                            Review & sign contract
                          </Button>
                        )}
                        {agreement.id === 'handbook_acknowledgement' && handbookDisplay.workerActionable && agreement.id === handbookAgreement?.id && (
                          <Button
                            size="sm"
                            className="gap-1 whitespace-nowrap"
                            disabled={!agreement.file_url && !agreement.download_url}
                            title={(!agreement.file_url && !agreement.download_url) ? 'Handbook PDF is not available yet' : undefined}
                            onClick={() => openHandbookAckModal(agreement)}
                          >
                            <CheckCircle className="h-3.5 w-3.5" />
                            Acknowledge
                          </Button>
                        )}
                        <Badge className={`shrink-0 text-xs ${
                          agreementDisplay.tone === 'critical' ? 'bg-red-100 text-red-700' :
                          agreementDisplay.tone === 'success' ? 'bg-green-100 text-green-700' :
                          agreementDisplay.tone === 'info' ? 'bg-blue-100 text-blue-700' :
                          'bg-slate-100 text-slate-600'
                        }`}>
                          {agreementDisplay.badge}
                        </Badge>
                      </div>
                    </div>
                    )}
                  </div>
                )})}
              </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Contract Status - Only for onboarding */}
        {showOnboardingContractSection && (
          <Card className="shadow-md border-0">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileText className="h-5 w-5 text-red-500" />
                Contract Review & Signature
              </CardTitle>
                <p className="text-xs text-slate-500 mt-1">
                 Review and sign your contract here. Osabea will countersign before the final version is complete.
                </p>
              </CardHeader>
              <CardContent>
              {contractAgreement?.contract_state === 'awaiting_company_countersignature' ? (
                <div className="flex items-center justify-between p-4 bg-blue-50 rounded-xl border border-blue-200">
                  <div>
                    <span className="font-medium text-blue-800">Awaiting company countersignature</span>
                    <p className="text-xs text-blue-600">Your signed contract is on file. Osabea still needs to countersign it before it becomes the final executed agreement.</p>
                  </div>
                  <Button
                    variant="outline"
                    className="gap-2"
                    onClick={() => openDocumentViewer({ ...contractAgreement, name: contractAgreement.name })}
                  >
                    <Eye className="h-4 w-4" />
                    View current PDF
                  </Button>
                </div>
              ) : contractAgreement?.contract_state === 'fully_executed' ? (
                <div className="flex items-center justify-between p-4 bg-green-50 rounded-xl border border-green-200">
                  <div>
                    <span className="font-medium text-green-800">Contract fully executed</span>
                    <p className="text-xs text-green-600">Your contract has been signed by both you and Osabea. You can continue to view or download the executed PDF above.</p>
                  </div>
                  <Badge className="bg-green-100 text-green-700">Complete</Badge>
                </div>
              ) : effectiveContractEligibility?.can_sign ? (
                <div className="flex items-center justify-between p-4 bg-green-50 rounded-xl border border-green-200">
                  <div>
                    <span className="font-medium text-green-800">Ready to Sign</span>
                    <p className="text-xs text-green-600">Earlier onboarding checks are complete. You can now review and sign your contract.</p>
                  </div>
                  <Button 
                    onClick={() => setShowSignaturePad(true)}
                    className="gap-2 bg-green-600 hover:bg-green-700"
                    data-testid="sign-contract-btn"
                  >
                    <PenTool className="h-4 w-4" />
                    Review & Sign Contract
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-4 bg-amber-50 rounded-xl border border-amber-200">
                    <div>
                      <span className="font-medium text-amber-800">{contractNeedsReissueMessage ? 'Contract not currently signable' : 'Contract not ready yet'}</span>
                      <p className="text-xs text-amber-600">
                        {contractNeedsReissueMessage
                          ? 'This contract is not currently signable. Please contact your manager to reissue it.'
                          : 'Contract signing becomes available once your forms, employment history, documents, references, and training are complete.'}
                      </p>
                    </div>
                    <Button 
                      disabled
                      className="gap-2 bg-gray-300 cursor-not-allowed"
                      data-testid="sign-contract-btn-locked"
                    >
                      <Lock className="h-4 w-4" />
                      Not ready
                    </Button>
                  </div>
                  
                  {effectiveContractEligibility?.blockers?.length > 0 && (
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs font-medium text-gray-600 mb-2">
                        Still needed before you can sign ({effectiveContractEligibility.blockers.length}):
                      </p>
                      <ul className="text-xs text-gray-500 space-y-1">
                        {effectiveContractEligibility.blockers.slice(0, 5).map((blocker, idx) => (
                          <li key={idx} className="flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3 text-amber-500" />
                            {blocker}
                          </li>
                        ))}
                        {effectiveContractEligibility.blockers.length > 5 && (
                          <li className="text-gray-400">
                            + {effectiveContractEligibility.blockers.length - 5} more...
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

        {/* ========== SPOT CHECKS (P1: Worker Dashboard) ========== */}
        {showFileSections && isActiveEmployee && spot_checks && spot_checks.length > 0 && (
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
                  (() => {
                    const followUpState = spot.follow_up_required
                      ? getDueState(spot.follow_up_date, 7)
                      : null;
                    return (
                      <div
                        key={idx}
                        className={`p-3 rounded-xl border ${
                          followUpState === 'overdue' ? 'bg-red-50 border-red-200' :
                          followUpState === 'due_soon' ? 'bg-amber-50 border-amber-200' :
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
                              {spot.assessed_by_name && (
                                <p className="text-xs text-slate-500">By {spot.assessed_by_name}</p>
                              )}
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

                        {spot.follow_up_required && spot.follow_up_date && (
                          <div className="mt-2">
                            <Badge className={
                              followUpState === 'overdue'
                                ? 'bg-red-100 text-red-700'
                                : followUpState === 'due_soon'
                                  ? 'bg-amber-100 text-amber-700'
                                  : 'bg-blue-100 text-blue-700'
                            }>
                              {followUpState === 'overdue'
                                ? `Follow-up overdue (${formatDate(spot.follow_up_date)})`
                                : followUpState === 'due_soon'
                                  ? `Follow-up due soon (${formatDate(spot.follow_up_date)})`
                                  : `Follow-up scheduled (${formatDate(spot.follow_up_date)})`}
                            </Badge>
                          </div>
                        )}

                        {spot.notes && (
                          <p className="text-xs text-slate-600 mt-2 bg-white/50 p-2 rounded">{spot.notes}</p>
                        )}
                      </div>
                    );
                  })()
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

        {showFileSections && isActiveEmployee && supervisions && supervisions.length > 0 && (
          <Card className="shadow-md border-0" data-testid="supervisions-section">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Calendar className="h-5 w-5 text-teal-600" />
                    Supervisions
                  </CardTitle>
                  <p className="text-xs text-slate-500 mt-1">
                    Your supervision schedule and completion history
                  </p>
                </div>
                <Badge className="bg-teal-100 text-teal-700">
                  {supervisions.length} Recorded
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {supervisions.slice(0, 10).map((sv, idx) => {
                  const status = (sv.status || '').toLowerCase();
                  const dueTarget = sv.next_due_at || sv.scheduled_at;
                  const dueState = getDueState(dueTarget, 14);
                  return (
                    <div
                      key={idx}
                      className={`p-3 rounded-xl border ${
                        dueState === 'overdue' ? 'bg-red-50 border-red-200' :
                        dueState === 'due_soon' ? 'bg-amber-50 border-amber-200' :
                        status === 'completed' ? 'bg-green-50 border-green-200' :
                        status === 'cancelled' ? 'bg-slate-50 border-slate-200' :
                        'bg-blue-50 border-blue-200'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="font-medium text-slate-800 text-sm">
                            {(sv.supervision_type || 'supervision').replace(/_/g, ' ')}
                          </p>
                          <p className="text-xs text-slate-500">
                            {sv.completed_at
                              ? `Completed ${formatDate(sv.completed_at)}`
                              : sv.scheduled_at
                                ? `Scheduled ${formatDate(sv.scheduled_at)}`
                                : 'No scheduled date'}
                          </p>
                        </div>
                        <Badge className={
                          status === 'completed'
                            ? 'bg-green-100 text-green-700'
                            : status === 'cancelled'
                              ? 'bg-slate-100 text-slate-600'
                              : status === 'overdue' || dueState === 'overdue'
                                ? 'bg-red-100 text-red-700'
                                : dueState === 'due_soon'
                                  ? 'bg-amber-100 text-amber-700'
                                  : 'bg-blue-100 text-blue-700'
                        }>
                          {status === 'completed'
                            ? 'Completed'
                            : status === 'cancelled'
                              ? 'Cancelled'
                              : status === 'overdue' || dueState === 'overdue'
                                ? 'Overdue'
                                : dueState === 'due_soon'
                                  ? 'Due soon'
                                  : 'Scheduled'}
                        </Badge>
                      </div>

                      {dueTarget && status !== 'completed' && (
                        <p className="text-xs text-slate-600 mt-2">
                          Next due: {formatDate(dueTarget)}
                        </p>
                      )}

                      {sv.notes && (
                        <p className="text-xs text-slate-600 mt-2 bg-white/50 p-2 rounded">{sv.notes}</p>
                      )}
                    </div>
                  );
                })}
              </div>
              {supervisions.length > 10 && (
                <p className="text-xs text-slate-400 mt-2 text-center">
                  Showing 10 of {supervisions.length} supervisions
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Completed Items - With Review Status & View Document */}
        {showFileSections && (completed_documents?.length > 0 || completed_trainings?.length > 0) && (
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
                  (() => {
                    const docDisplayStatus = getCompletedDocumentDisplayStatus(doc);
                    const docBadgeMeta = DOCUMENT_WORKFLOW_UI[docDisplayStatus] || DOCUMENT_WORKFLOW_UI.awaiting_review;
                    const isDocVerifiedDisplay = docDisplayStatus === 'verified';
                    return (
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
                      {isDocVerifiedDisplay ? (
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
                          <Badge className={`${docBadgeMeta.className} text-xs`} data-testid={`pending-verification-${doc.type}`}>
                            <Clock className="h-3 w-3 mr-1" />
                            {docBadgeMeta.label}
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
                    );
                  })()
                ))}
                {completed_trainings?.map((training, idx) => (
                  (() => {
                    const trainingBadgeMeta = getCompletedTrainingBadgeMeta(training);
                    const trainingIsVerifiedDisplay = trainingBadgeMeta === TRAINING_STATUS_CONFIG.verified;
                    return (
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
                      <Badge className={`${trainingBadgeMeta.badgeCls} text-xs`}>
                        {trainingIsVerifiedDisplay ? (
                          <Shield className="h-3 w-3 mr-1" />
                        ) : (
                          <Clock className="h-3 w-3 mr-1" />
                        )}
                        {trainingBadgeMeta.badge}
                      </Badge>
                      {training.source_document_id && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-xs h-7"
                          onClick={() => openDocumentViewer({
                            id: training.source_document_id,
                            document_id: training.source_document_id,
                            name: training.name,
                          })}
                          data-testid={`view-training-evidence-${training.id}`}
                        >
                          <Eye className="h-3 w-3 mr-1" />
                          View evidence
                        </Button>
                      )}
                    </div>
                  </div>
                    );
                  })()
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Footer */}
        <div className="text-center py-6 text-xs text-slate-400">
          <p>{orgSettings.organisation_name || 'Healthcare Portal'} - Compliance Portal</p>
          <p>Employee Code: {employee.employee_code || employee.applicant_reference || '—'}</p>
        </div>

      {/* Contract Signature Dialog */}
      <Dialog open={showSignaturePad} onOpenChange={setShowSignaturePad}>
        <DialogContent className="max-w-xl p-0">
            <SignaturePad
              employeeId={employee.id}
              employeeName={employee.name}
              sourceRecordId={contractAgreement?.source_record_id || null}
              onSigned={() => {
                setShowSignaturePad(false);
                fetchDashboard(); // Refresh dashboard
                toast.success('Contract signed and sent for Osabea countersignature.');
              }}
            onCancel={() => setShowSignaturePad(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Handbook Acknowledgement Dialog */}
      <Dialog open={showHandbookAckModal} onOpenChange={(open) => { if (!open) closeHandbookAckModal(); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              Acknowledge Employee Handbook
            </DialogTitle>
          </DialogHeader>
          {handbookAckAgreement && (
            <div className="space-y-4">
              {(!handbookAckAgreement.file_url && !handbookAckAgreement.download_url) ? (
                <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  The handbook PDF for the version you are being asked to acknowledge is not available yet.
                  You cannot acknowledge until it is ready. Please refresh shortly.
                </div>
              ) : (
                <>
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                    <p className="font-medium text-slate-900 mb-1">Step 1 — Read the handbook</p>
                    <p className="text-xs text-slate-600">
                      Open the full handbook PDF and read it in full before acknowledging.
                      This is the exact version you are signing.
                    </p>
                    <div className="flex flex-wrap gap-2 mt-3">
                      <Button
                        size="sm"
                        className="gap-1"
                        onClick={viewHandbookPdfFromModal}
                      >
                        <Eye className="h-3.5 w-3.5" />
                        View Handbook PDF
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="gap-1"
                        onClick={() => downloadAgreement(handbookAckAgreement)}
                      >
                        <Download className="h-3.5 w-3.5" />
                        Download PDF
                      </Button>
                    </div>
                    {handbookAckAgreement.template_version && (
                      <p className="text-[11px] text-slate-500 mt-2">
                        Version {handbookAckAgreement.template_version}
                        {handbookAckAgreement.rendered_at && ` • prepared ${formatDate(handbookAckAgreement.rendered_at)}`}
                      </p>
                    )}
                  </div>

                  <div className="rounded-md border border-slate-200 p-3 text-sm">
                    <p className="font-medium text-slate-900 mb-1">Step 2 — Confirm</p>
                    <label className={`flex items-start gap-2 ${handbookPdfViewed ? '' : 'opacity-60'}`}>
                      <input
                        type="checkbox"
                        className="mt-1"
                        disabled={!handbookPdfViewed}
                        checked={handbookAckConfirmed}
                        onChange={(e) => setHandbookAckConfirmed(e.target.checked)}
                      />
                      <span className="text-xs text-slate-700">
                        I confirm that I have opened and read the Employee Handbook PDF above
                        (Version {handbookAckAgreement.template_version || '—'}), that I understand its contents,
                        and that I agree to abide by the policies, procedures and expectations set out in it.
                        I am providing this acknowledgement as {employee?.name || 'the named employee'}.
                      </span>
                    </label>
                    {!handbookPdfViewed && (
                      <p className="text-[11px] text-amber-700 mt-2">
                        Open the handbook PDF first — the confirmation is locked until you have viewed it.
                      </p>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={closeHandbookAckModal}
              disabled={submittingHandbookAck}
            >
              Cancel
            </Button>
            <Button
              onClick={submitHandbookAck}
              disabled={
                submittingHandbookAck
                || !handbookAckAgreement
                || (!handbookAckAgreement.file_url && !handbookAckAgreement.download_url)
                || !handbookPdfViewed
                || !handbookAckConfirmed
              }
              className="gap-1"
            >
              {submittingHandbookAck ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <CheckCircle className="h-3.5 w-3.5" />
              )}
              Acknowledge Handbook
            </Button>
          </DialogFooter>
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
                Waiting for Osabea review
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

      {/* CV Extraction Verification Modal — removed. CV review is admin-only. */}
      {false && <Dialog open={false} onOpenChange={() => {}}>
        <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle></DialogTitle>
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
              <p className="text-slate-600">No items waiting for review</p>
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
      </Dialog>}

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

              {/* Review note */}
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-xs text-blue-700">
                  <Shield className="h-3 w-3 inline mr-1" />
                  Osabea needs a clear explanation for any differences before your file can move forward.
                  Your explanation will be reviewed by the team and kept in the audit trail.
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

      {/* Profile Completion Wizard for Offline PDF Imports */}
      <ProfileCompletionWizard
        open={showProfileWizard}
        onClose={() => setShowProfileWizard(false)}
        onComplete={() => {
          setShowProfileWizard(false);
          fetchDashboard(); // Refresh dashboard after completion
          toast.success('Profile completed successfully!');
        }}
      />

      <Dialog open={workerShiftDetailOpen} onOpenChange={setWorkerShiftDetailOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Shift details</DialogTitle>
          </DialogHeader>
          {selectedWorkerShift?.shift ? (
            <div className="space-y-3 text-sm text-slate-700">
              <div>
                <p className="text-xs text-slate-500">Date</p>
                <p className="font-medium">{formatDate(selectedWorkerShift.shift.start_at)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Time</p>
                <p className="font-medium">
                  {formatDateTime(selectedWorkerShift.shift.start_at).split(', ').pop()} - {formatDateTime(selectedWorkerShift.shift.end_at).split(', ').pop()}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Location</p>
                <p className="font-medium">{selectedWorkerShift.shift.location_text || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Role</p>
                <p className="font-medium">{selectedWorkerShift.shift.role_required || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Notes</p>
                <p className="font-medium">{selectedWorkerShift.shift.notes || 'No notes'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Status</p>
                <Badge className={(selectedWorkerShift.shift.status === 'assigned' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-700')}>
                  {selectedWorkerShift.shift.status || selectedWorkerShift.assignment?.status || 'assigned'}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-slate-500">Assignment status</p>
                <p className="font-medium">{selectedWorkerShift.assignment?.status || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Attendance status</p>
                <Badge className={
                  selectedWorkerShift.current_attendance?.status === 'approved'
                    ? 'bg-green-100 text-green-700'
                    : selectedWorkerShift.current_attendance?.status === 'submitted'
                      ? 'bg-blue-100 text-blue-700'
                      : selectedWorkerShift.current_attendance?.status === 'open'
                        ? 'bg-amber-100 text-amber-700'
                        : selectedWorkerShift.current_attendance?.status === 'rejected'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-slate-100 text-slate-700'
                }>
                  {selectedWorkerShift.current_attendance?.status || 'not started'}
                </Badge>
              </div>
              {(selectedWorkerShift.assignment?.unassign_reason || selectedWorkerShift.shift.cancelled_reason) ? (
                <div>
                  <p className="text-xs text-slate-500">Cancellation reason</p>
                  <p className="font-medium text-red-700">
                    {selectedWorkerShift.assignment?.unassign_reason || selectedWorkerShift.shift.cancelled_reason}
                  </p>
                </div>
              ) : null}
              <div className="border-t border-slate-200 pt-3">
                <p className="text-xs text-slate-500 mb-2">Daily note</p>
                {selectedWorkerShift.current_daily_note ? (
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3 space-y-2">
                    <p className="text-sm text-slate-700 whitespace-pre-wrap">{selectedWorkerShift.current_daily_note.note_text}</p>
                    {Array.isArray(selectedWorkerShift.current_daily_note.tags) && selectedWorkerShift.current_daily_note.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {selectedWorkerShift.current_daily_note.tags.map((tag) => (
                          <Badge key={`note-tag-${tag}`} className="bg-slate-200 text-slate-700 text-[11px]">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                    <p className="text-xs text-slate-500">Saved at {formatDateTime(selectedWorkerShift.current_daily_note.timestamp)}</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <Textarea
                      value={workerDailyNoteText}
                      onChange={(e) => setWorkerDailyNoteText(e.target.value)}
                      rows={3}
                      placeholder="Write care delivery note for this shift"
                    />
                    <div className="flex flex-wrap gap-1">
                      {DAILY_NOTE_TAG_OPTIONS.map((tag) => (
                        <Button
                          key={`daily-note-tag-${tag}`}
                          type="button"
                          size="sm"
                          variant={workerDailyNoteTags.includes(tag) ? 'default' : 'outline'}
                          onClick={() => toggleWorkerDailyNoteTag(tag)}
                        >
                          {tag}
                        </Button>
                      ))}
                    </div>
                    <div className="flex justify-end">
                      <Button
                        size="sm"
                        onClick={handleSubmitWorkerDailyNote}
                        disabled={workerDailyNoteSubmitting || (workerDailyNoteText || '').trim().length < 2}
                      >
                        {workerDailyNoteSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                        Save Daily Note
                      </Button>
                    </div>
                  </div>
                )}
              </div>
              {(canWorkerClockIn(selectedWorkerShift) || canWorkerClockOut(selectedWorkerShift)) && (
                <div className="flex items-center gap-2 pt-2">
                  {canWorkerClockIn(selectedWorkerShift) && (
                    <Button
                      size="sm"
                      onClick={() => handleWorkerShiftClock(selectedWorkerShift, 'in')}
                      disabled={workerShiftClocking}
                    >
                      {workerShiftClocking ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                      Clock In
                    </Button>
                  )}
                  {canWorkerClockOut(selectedWorkerShift) && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleWorkerShiftClock(selectedWorkerShift, 'out')}
                      disabled={workerShiftClocking}
                    >
                      {workerShiftClocking ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                      Clock Out
                    </Button>
                  )}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-600">Shift detail unavailable.</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={handleReportIncidentForShift}>
              Report Incident For This Shift
            </Button>
            <Button variant="outline" onClick={() => setWorkerShiftDetailOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={workerShiftResponseOpen} onOpenChange={setWorkerShiftResponseOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{workerShiftResponseMode === 'reject' ? 'Reject shift' : 'Accept shift'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              {workerShiftResponseMode === 'reject'
                ? 'Add an optional note for your manager when rejecting this shift.'
                : 'Add an optional note when accepting this shift.'}
            </p>
            <Textarea
              value={workerShiftResponseNote}
              onChange={(e) => setWorkerShiftResponseNote(e.target.value)}
              rows={3}
              placeholder="Optional note"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setWorkerShiftResponseOpen(false)}>
              Cancel
            </Button>
            <Button
              variant={workerShiftResponseMode === 'reject' ? 'destructive' : 'default'}
              onClick={handleWorkerShiftResponse}
              disabled={workerShiftResponding}
            >
              {workerShiftResponding ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              {workerShiftResponseMode === 'reject' ? 'Reject shift' : 'Accept shift'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={incidentModalOpen} onOpenChange={setIncidentModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Report incident</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>Type</Label>
              <Select
                value={incidentForm.incident_type}
                onValueChange={(v) => setIncidentForm((prev) => ({
                  ...prev,
                  incident_type: v,
                  safeguarding_concern: v === 'safeguarding' ? true : prev.safeguarding_concern,
                }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="incident">Incident</SelectItem>
                  <SelectItem value="near_miss">Near miss</SelectItem>
                  <SelectItem value="concern">Concern</SelectItem>
                  <SelectItem value="safeguarding">Safeguarding concern</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Occurred at</Label>
              <Input
                type="datetime-local"
                value={incidentForm.occurred_at}
                onChange={(e) => setIncidentForm((prev) => ({ ...prev, occurred_at: e.target.value }))}
              />
            </div>
            <div>
              <Label>Location</Label>
              <Input
                value={incidentForm.location_text}
                onChange={(e) => setIncidentForm((prev) => ({ ...prev, location_text: e.target.value }))}
              />
            </div>
            <div>
              <Label>Related shift (optional)</Label>
              <Select
                value={incidentForm.related_shift_id || 'none'}
                onValueChange={(v) => {
                  if (v === 'none') {
                    setIncidentForm((prev) => ({ ...prev, related_shift_id: '', service_user_id: '' }));
                    return;
                  }
                  const selected = workerShifts.find((item) => item.shift?.id === v);
                  setIncidentForm((prev) => ({
                    ...prev,
                    related_shift_id: v,
                    service_user_id: selected?.shift?.service_user_id || '',
                    location_text: prev.location_text || selected?.shift?.location_text || '',
                  }));
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a shift" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  {workerShifts.map((item) => (
                    <SelectItem key={item.shift?.id} value={item.shift?.id}>
                      {formatDate(item.shift?.start_at)} - {item.shift?.location_text || item.shift?.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                rows={4}
                value={incidentForm.description}
                onChange={(e) => setIncidentForm((prev) => ({ ...prev, description: e.target.value }))}
              />
            </div>
            <div>
              <Label>People involved (optional)</Label>
              <Input
                value={incidentForm.people_involved}
                onChange={(e) => setIncidentForm((prev) => ({ ...prev, people_involved: e.target.value }))}
              />
            </div>
            <div>
              <Label>Witnesses (optional)</Label>
              <Input
                value={incidentForm.witnesses}
                onChange={(e) => setIncidentForm((prev) => ({ ...prev, witnesses: e.target.value }))}
              />
            </div>
            <div>
              <Label>Immediate actions taken (optional)</Label>
              <Textarea
                rows={2}
                value={incidentForm.immediate_actions_taken}
                onChange={(e) => setIncidentForm((prev) => ({ ...prev, immediate_actions_taken: e.target.value }))}
              />
            </div>
            <div>
              <Label>Injury or harm (optional)</Label>
              <Textarea
                rows={2}
                value={incidentForm.injury_or_harm}
                onChange={(e) => setIncidentForm((prev) => ({ ...prev, injury_or_harm: e.target.value }))}
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={!!incidentForm.safeguarding_concern}
                onChange={(e) => setIncidentForm((prev) => ({ ...prev, safeguarding_concern: e.target.checked }))}
              />
              Safeguarding concern
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={!!incidentForm.escalation_required}
                onChange={(e) => setIncidentForm((prev) => ({
                  ...prev,
                  escalation_required: e.target.checked,
                  escalation_details: e.target.checked ? prev.escalation_details : '',
                }))}
              />
              Escalation required
            </label>
            {incidentForm.escalation_required ? (
              <div>
                <Label>Escalation details</Label>
                <Textarea
                  rows={2}
                  value={incidentForm.escalation_details}
                  onChange={(e) => setIncidentForm((prev) => ({ ...prev, escalation_details: e.target.value }))}
                />
              </div>
            ) : null}
            <div>
              <Label>Learning outcome (optional)</Label>
              <Textarea
                rows={2}
                value={incidentForm.learning_outcome}
                onChange={(e) => setIncidentForm((prev) => ({ ...prev, learning_outcome: e.target.value }))}
              />
            </div>
            <div>
              <Label>Prevention actions (optional)</Label>
              <Textarea
                rows={2}
                value={incidentForm.prevention_actions}
                onChange={(e) => setIncidentForm((prev) => ({ ...prev, prevention_actions: e.target.value }))}
              />
            </div>
            <div>
              <Label>Note (optional)</Label>
              <Textarea
                rows={2}
                value={incidentForm.note}
                onChange={(e) => setIncidentForm((prev) => ({ ...prev, note: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIncidentModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmitIncident} disabled={incidentSubmitting}>
              {incidentSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              Submit report
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={incidentDetailOpen}
        onOpenChange={(open) => {
          setIncidentDetailOpen(open);
          if (!open) setSelectedIncident(null);
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Incident details</DialogTitle>
          </DialogHeader>
          {selectedIncident ? (
            <div className="space-y-3 text-sm text-slate-700">
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium text-slate-900">{selectedIncident.reference_number || selectedIncident.title || 'Incident'}</p>
                <Badge className={getWorkerIncidentStatusMeta(selectedIncident.status).className}>
                  {selectedIncident.status_label || getWorkerIncidentStatusMeta(selectedIncident.status).label}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-slate-500">Incident type</p>
                <p className="font-medium">{(selectedIncident.incident_type || 'incident').replace(/_/g, ' ')}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Occurred</p>
                <p className="font-medium">{formatDateTime(selectedIncident.date_occurred)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Location</p>
                <p className="font-medium">{selectedIncident.location || 'Location not set'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Description</p>
                <p className="font-medium whitespace-pre-wrap">{selectedIncident.description || '-'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Progress</p>
                <p className="font-medium">{selectedIncident.progress_summary || 'Your report has been submitted and is awaiting review.'}</p>
              </div>
              {selectedIncident.outcome_summary ? (
                <div>
                  <p className="text-xs text-slate-500">Outcome / follow-up summary</p>
                  <p className="font-medium whitespace-pre-wrap">{selectedIncident.outcome_summary}</p>
                </div>
              ) : null}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <p className="text-xs text-slate-500">Submitted</p>
                  <p className="font-medium">{formatDateTime(selectedIncident.reported_at)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Reviewed</p>
                  <p className="font-medium">{formatDateTime(selectedIncident.reviewed_at)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Closed</p>
                  <p className="font-medium">{formatDateTime(selectedIncident.closed_at)}</p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-600">Incident detail unavailable.</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIncidentDetailOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </WorkerDashboardPage>
  );
}


