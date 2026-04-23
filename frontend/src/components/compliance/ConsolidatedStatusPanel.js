/**
 * ConsolidatedStatusPanel - Single source of truth for employee status
 * 
 * Replaces the duplicate:
 * - RecruitmentApprovalPanel (was showing 2x)
 * - WorkReadinessPanel (was showing 2x)
 * - PreEmploymentGatesPanel
 * - Full Compliance card
 * - Blocking Items card
 * 
 * Shows ONE view with:
 * - Status header (BLOCKED/READY)
 * - ONE blocker list with color-coded severity
 * - ONE progress summary
 * - Quick actions
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import {
  AlertTriangle, CheckCircle, XCircle, ChevronRight,
  FileText, Users, GraduationCap, ClipboardCheck,
  Send, Eye, Plus, RefreshCw, Loader2, Shield,
  FileCheck, UserCheck, Briefcase, Heart, Calendar,
  Clock, AlertCircle, Info, Edit
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';


const API = process.env.REACT_APP_BACKEND_URL;

// Blocker icons mapping
const BLOCKER_ICONS = {
  'identity': FileCheck,
  'proof_of_address': FileText,
  'right_to_work': Shield,
  'dbs': Shield,
  'reference': Users,
  'interview': ClipboardCheck,
  'contract': FileText,
  'induction': ClipboardCheck,
  'health': Heart,
  'training': GraduationCap,
  'gaps': Calendar,
  'default': AlertTriangle
};

// Blocker severity classification
// Critical: Missing/unverified required documents
// Pending: Uploaded but awaiting verification
// Complete: Fully verified (not shown in blockers)
const BLOCKER_SEVERITY = {
  CRITICAL: {
    label: 'Critical',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    textColor: 'text-red-700',
    iconColor: 'text-red-600',
    iconBg: 'bg-red-100',
    dot: '🔴'
  },
  PENDING: {
    label: 'Pending',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    textColor: 'text-amber-700',
    iconColor: 'text-amber-600',
    iconBg: 'bg-amber-100',
    dot: '🟡'
  },
  COMPLETE: {
    label: 'Complete',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    textColor: 'text-green-700',
    iconColor: 'text-green-600',
    iconBg: 'bg-green-100',
    dot: '🟢'
  }
};

// Determine blocker severity based on gate status
const getBlockerSeverity = (blocker, gateData) => {
  if (blocker?.severity === 'pending') {
    return 'PENDING';
  }
  if (blocker?.severity === 'critical' || blocker?.severity === 'required') {
    return 'CRITICAL';
  }

  // Check if there's evidence uploaded but not verified
  const hasUploaded = gateData?.has_uploaded || blocker.has_evidence;
  const isPending = gateData?.status === 'pending' || 
                    gateData?.status === 'uploaded' ||
                    gateData?.status === 'under_review' ||
                    blocker.status === 'pending';
  
  if (hasUploaded || isPending) {
    return 'PENDING';
  }
  
  // Default to critical for missing items
  return 'CRITICAL';
};

const getBlockerIcon = (blockerKey) => {
  for (const [key, Icon] of Object.entries(BLOCKER_ICONS)) {
    if (blockerKey?.toLowerCase().includes(key)) {
      return Icon;
    }
  }
  return BLOCKER_ICONS.default;
};

export default function ConsolidatedStatusPanel({
  employeeId,
  employeeName,
  role,
  personStage,
  recruitmentApproved,
  onNavigateToTab,
  onNavigateToItem,
  onRefresh,
  onVerifyWithEvidence,  // NEW: Callback to open verification modal
  onViewDocument         // NEW: Callback to open document viewer
}) {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [gateResult, setGateResult] = useState(null); // structured recruitment gate
  const [gateLoading, setGateLoading] = useState(false);
  const [gateFetchFailed, setGateFetchFailed] = useState(false); // true when gate endpoint errored

  const fetchStatus = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      // Fetch unified progress and pre-employment gates
      const [progressRes, gatesRes] = await Promise.all([
        axios.get(`${API}/api/employees/${employeeId}/unified-progress`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/api/employees/${employeeId}/pre-employment-gates`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      setData({
        progress: progressRes.data,
        gates: gatesRes.data
      });
    } catch (error) {
      console.error('Failed to fetch status:', error);
      setData(null);
      setLoadError(error.response?.data?.detail || error.message || 'Unable to load readiness status');
    } finally {
      setLoading(false);
    }
  };

  const fetchGate = async () => {
    if (!token || !employeeId) return;
    setGateLoading(true);
    try {
      const res = await axios.get(
        `${API}/api/employees/${employeeId}/recruitment-gate`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setGateResult(res.data?.gate ?? null);
      setGateFetchFailed(false);
    } catch (err) {
      console.warn('Could not load recruitment gate:', err.response?.data?.detail || err.message);
      setGateResult(null);
      setGateFetchFailed(true);
    } finally {
      setGateLoading(false);
    }
  };

  useEffect(() => {
    if (token && employeeId) {
      fetchStatus();
      // Only fetch the gate for applicants (not yet recruited)
      if (personStage === 'applicant' && !recruitmentApproved) {
        fetchGate();
      }
    }
  }, [token, employeeId, personStage, recruitmentApproved]);

  const handleSendReminder = async () => {
    setActionLoading('reminder');
    try {
      await axios.post(
        `${API}/api/workers/${employeeId}/send-reminder`,
        { reminder_type: 'general' },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Reminder sent to worker');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send reminder');
    } finally {
      setActionLoading(null);
    }
  };

  const handleApproveRecruitment = async () => {
    setActionLoading('approve');
    try {
      await axios.post(
        `${API}/api/employees/${employeeId}/approve-recruitment`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`${employeeName} approved for recruitment!`);
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to approve');
    } finally {
      setActionLoading(null);
    }
  };

  const handlePromoteToActive = async () => {
    setActionLoading('promote');
    try {
      await axios.post(
        `${API}/api/employees/${employeeId}/promote-to-active`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`${employeeName} promoted to Active Employee!`);
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to promote');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <Card className="border-2 border-gray-200">
        <CardContent className="py-12 flex justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  if (loadError) {
    return (
      <div className="space-y-4" data-testid="consolidated-status-panel">
        <Card className="border-2 border-gray-300 bg-gray-50/40">
          <CardContent className="py-4">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center">
                  <AlertTriangle className="h-6 w-6 text-gray-600" />
                </div>
                <div>
                  <p className="text-lg font-semibold text-gray-800">
                    Readiness status unavailable
                  </p>
                  <p className="text-sm text-gray-600">
                    {employeeName} • {role} • Canonical readiness could not be loaded
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={fetchStatus}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-gray-200 shadow-sm">
          <CardHeader className="py-3 px-4 bg-gray-50/50 border-b border-gray-100">
            <CardTitle className="text-base font-semibold text-gray-700">
              PRE-EMPLOYMENT PROGRESS: unavailable
            </CardTitle>
          </CardHeader>
          <CardContent className="py-4">
            <p className="text-sm text-gray-600">
              Readiness, blockers, and promotion actions are hidden until canonical status loads.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const progress = data?.progress || {};
  const gates = data?.gates || {};
  const progressBlockerDetails = Array.isArray(progress.blocker_details) ? progress.blocker_details : [];
  const progressBlockerStrings = Array.isArray(progress.blockers)
    ? progress.blockers.map((blocker) => (
        typeof blocker === 'string'
          ? { gate: '', label: blocker, reason: blocker, severity: 'critical' }
          : blocker
      ))
    : [];
  const blockers = progressBlockerDetails.length > 0
    ? progressBlockerDetails
    : progressBlockerStrings.length > 0
      ? progressBlockerStrings
      : [];
  const canPromote = progress.can_promote;
  const progressCompleted = progress.completed_requirements;
  const progressTotal = progress.total_requirements;
  const progressCountAvailable = Number.isFinite(progressTotal) && progressTotal > 0;
  
  // Canonical readiness/progression percentage comes from unified-progress.
  const progressPercentage = progress.overall_percentage ?? 0;
  
  // Use categories breakdown from unified-progress for the detailed grid
  const breakdown = progress.categories || {};

  // Determine overall status
  const isBlocked = blockers.length > 0 || (progress.is_work_ready === false && progress.can_promote === false);
  const isApplicant = personStage === 'applicant';
  const isEmployee = personStage === 'employee' || recruitmentApproved;

  // Gate-derived approval readiness (canonical — overrides old isBlocked for the approve CTA)
  const gateAllowed = gateResult?.allowed === true;
  const gateBlockers = gateResult?.blocking_items ?? [];
  const gateWarnings = gateResult?.warning_items ?? [];
  const gatePassed = gateResult?.passed_items ?? [];
  const gateMissing = gateResult?.missing_requirements ?? [];
  const gateHasData = gateResult !== null;
  // Approval CTA guard: gate is the ONLY signal — no fallback to legacy isBlocked
  const canApproveRecruitment = gateAllowed;

  return (
    <div className="space-y-4" data-testid="consolidated-status-panel">
      {/* STATUS HEADER */}
      <Card className={cn(
        "border-2",
        isBlocked ? "border-amber-300 bg-amber-50/30" : "border-green-300 bg-green-50/30"
      )}>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isBlocked ? (
                <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center">
                  <AlertTriangle className="h-6 w-6 text-amber-600" />
                </div>
              ) : (
                <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                  <CheckCircle className="h-6 w-6 text-green-600" />
                </div>
              )}
              <div>
                <p className={cn(
                  "text-lg font-semibold",
                  isBlocked ? "text-amber-800" : "text-green-800"
                )}>
                  {isBlocked ? (
                    <>Not ready to move forward yet</>
                  ) : (
                    <>No current pre-employment blockers</>
                  )}
                </p>
                <p className="text-sm text-gray-600">
                  {employeeName} • {role} • {isApplicant ? 'Applicant' : 'Onboarding'}
                </p>
              </div>
            </div>
            
            {/* Main Action Button */}
            <div>
              {isApplicant && !recruitmentApproved && (
                <div className="flex flex-col items-end gap-1">
                  <Button
                    onClick={handleApproveRecruitment}
                    disabled={actionLoading === 'approve' || gateLoading || !canApproveRecruitment || gateFetchFailed || (!gateHasData && !gateLoading)}
                    className={canApproveRecruitment && !gateFetchFailed
                      ? 'bg-green-600 hover:bg-green-700'
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    }
                    title={
                      gateFetchFailed ? 'Approval check unavailable — reload to retry' :
                      !gateHasData ? 'Approval check not yet loaded' :
                      !canApproveRecruitment ? 'Resolve all blockers before approving' :
                      undefined
                    }
                  >
                    {actionLoading === 'approve' ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <UserCheck className="h-4 w-4 mr-2" />
                    )}
                    Approve for Recruitment
                  </Button>
                  {gateFetchFailed && (
                    <p className="text-[11px] text-red-600 flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" /> Approval check unavailable — approval disabled
                    </p>
                  )}
                  {!gateFetchFailed && !canApproveRecruitment && gateHasData && (
                    <p className="text-[11px] text-red-600">{gateBlockers.length} blocker(s) must be resolved</p>
                  )}
                  {!gateFetchFailed && canApproveRecruitment && gateWarnings.length > 0 && (
                    <p className="text-[11px] text-amber-600">{gateWarnings.length} warning(s) — review before approving</p>
                  )}
                </div>
              )}
              {isEmployee && canPromote && (
                <Button
                  onClick={handlePromoteToActive}
                  disabled={actionLoading === 'promote'}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {actionLoading === 'promote' ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <CheckCircle className="h-4 w-4 mr-2" />
                  )}
                  Promote to Active Employee
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* RECRUITMENT APPROVAL CHECK — canonical gate result, applicants only */}
      {isApplicant && !recruitmentApproved && (
        <Card className={cn(
          "border shadow-sm",
          gateLoading ? "border-gray-200" :
          !gateHasData ? "border-gray-200" :
          !gateAllowed ? "border-red-200" :
          gateWarnings.length > 0 ? "border-amber-200" :
          "border-green-200"
        )}>
          <CardHeader className={cn(
            "py-3 px-4 border-b",
            gateLoading || !gateHasData ? "bg-gray-50/50 border-gray-100" :
            !gateAllowed ? "bg-red-50/60 border-red-100" :
            gateWarnings.length > 0 ? "bg-amber-50/60 border-amber-100" :
            "bg-green-50/60 border-green-100"
          )}>
            <div className="flex items-center justify-between">
              <CardTitle className={cn(
                "text-base font-semibold flex items-center gap-2",
                gateLoading || !gateHasData ? "text-gray-700" :
                !gateAllowed ? "text-red-800" :
                gateWarnings.length > 0 ? "text-amber-800" :
                "text-green-800"
              )}>
                {gateLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : !gateHasData ? (
                  <Info className="h-4 w-4" />
                ) : !gateAllowed ? (
                  <XCircle className="h-4 w-4" />
                ) : gateWarnings.length > 0 ? (
                  <AlertTriangle className="h-4 w-4" />
                ) : (
                  <CheckCircle className="h-4 w-4" />
                )}
                Recruitment Approval Check
              </CardTitle>
              <Button variant="ghost" size="sm" className="h-7 px-2 text-gray-500" onClick={fetchGate} disabled={gateLoading}>
                <RefreshCw className={cn("h-3.5 w-3.5", gateLoading && "animate-spin")} />
              </Button>
            </div>
            {gateHasData && !gateLoading && (
              <p className={cn(
                "text-xs mt-0.5",
                !gateAllowed ? "text-red-600" :
                gateWarnings.length > 0 ? "text-amber-600" :
                "text-green-600"
              )}>
                {!gateAllowed
                  ? `${gateBlockers.length} blocker(s) must be resolved before this applicant can be approved`
                  : gateWarnings.length > 0
                  ? `Ready to approve \u2014 ${gateWarnings.length} item(s) require investigation before or after approval`
                  : "All recruitment gate requirements satisfied \u2014 ready for approval"
                }
              </p>
            )}
            {!gateHasData && !gateLoading && (
              <p className="text-xs text-red-600 mt-0.5 flex items-center gap-1">
                <AlertTriangle className="h-3.5 w-3.5" />
                Approval check unavailable — approval is disabled until this check loads successfully
              </p>
            )}
          </CardHeader>

          {gateHasData && !gateLoading && (
            <CardContent className="py-3 px-4 space-y-3">
              {/* Blockers */}
              {gateBlockers.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-red-700 mb-1.5 flex items-center gap-1">
                    <XCircle className="h-3.5 w-3.5" /> Blockers ({gateBlockers.length})
                  </p>
                  <div className="space-y-1">
                    {gateBlockers.map((item, i) => (
                      <div key={i} className="flex items-start gap-2 p-2 bg-red-50 rounded-lg border border-red-100">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-500 mt-1.5 shrink-0" />
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-red-800">{item.label}</p>
                          <p className="text-[11px] text-red-600 mt-0.5">{item.reason}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Warnings */}
              {gateWarnings.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-amber-700 mb-1.5 flex items-center gap-1">
                    <AlertTriangle className="h-3.5 w-3.5" /> Warnings \u2014 investigate but not blocking ({gateWarnings.length})
                  </p>
                  <div className="space-y-1">
                    {gateWarnings.map((item, i) => (
                      <div key={i} className="flex items-start gap-2 p-2 bg-amber-50 rounded-lg border border-amber-100">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-amber-800">{item.label}</p>
                          <p className="text-[11px] text-amber-600 mt-0.5">{item.reason}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Passed */}
              {gatePassed.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-green-700 mb-1.5 flex items-center gap-1">
                    <CheckCircle className="h-3.5 w-3.5" /> Passed ({gatePassed.length})
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {gatePassed.map((item, i) => (
                      <span key={i} className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-green-100 text-green-800 border border-green-200">
                        <CheckCircle className="h-2.5 w-2.5" />
                        {item.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Missing requirement slots */}
              {gateMissing.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                    <Info className="h-3.5 w-3.5" /> Missing requirement slots ({gateMissing.length})
                  </p>
                  <p className="text-[11px] text-gray-500">{gateMissing.join(', ')}</p>
                </div>
              )}
            </CardContent>
          )}
        </Card>
      )}

      {/* OPEN ITEMS SUMMARY — compact count strip.
          The full grouped-by-owner breakdown lives in the "What's left" panel
          on EmployeeProfilePage. This card is intentionally a summary only to
          avoid rendering the same blocker list twice on the same page. */}
      {blockers.length > 0 && (() => {
        const criticalCount = blockers.filter(b => getBlockerSeverity(b, gates.gates?.[b.gate]) === 'CRITICAL').length;
        const pendingCount = blockers.length - criticalCount;
        return (
          <div
            className="flex items-center gap-3 px-4 py-2.5 rounded-lg border border-red-200 bg-red-50/40"
            data-testid="blocker-summary-strip"
          >
            <XCircle className="h-4 w-4 text-red-500 shrink-0" />
            <span className="text-sm font-medium text-red-800">
              {blockers.length} open item{blockers.length !== 1 ? 's' : ''} remaining
            </span>
            <div className="flex items-center gap-1.5 ml-1">
              {criticalCount > 0 && (
                <span className="text-[11px] font-medium bg-red-100 text-red-700 px-1.5 py-0.5 rounded border border-red-200">
                  {criticalCount} critical
                </span>
              )}
              {pendingCount > 0 && (
                <span className="text-[11px] font-medium bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded border border-amber-200">
                  {pendingCount} awaiting review
                </span>
              )}
            </div>
            <span className="ml-auto text-[11px] text-gray-400">See "What's left" below for details</span>
          </div>
        );
      })()}

      {/* PROGRESS SUMMARY - ONE CARD */}
      <Card className="border border-gray-200 shadow-sm">
        <CardHeader className="py-3 px-4 bg-gray-50/50 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold text-gray-700">
              Submission Progress — {progressCountAvailable
                ? `${progressCompleted ?? 0} of ${progressTotal} items submitted (${progressPercentage}%)`
                : `item count unavailable (${progressPercentage}%)`}
            </CardTitle>
            <p className="text-[11px] text-gray-400 mt-0.5">Tracks document and form submission only — not approval readiness</p>
            <Button variant="ghost" size="sm" onClick={fetchStatus}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="py-4">
          <Progress value={progressPercentage} className="h-3 mb-4" />
          
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
            {[
              { label: 'Documents', key: 'documents', icon: FileText },
              { label: 'Forms', key: 'forms', icon: ClipboardCheck },
              { label: 'Training', key: 'training', icon: GraduationCap },
              { label: 'References', key: 'references', icon: Users },
              { label: 'Agreements', key: 'agreements', icon: FileCheck },
              { label: 'Induction', key: 'induction', icon: Briefcase }
            ].map((cat) => {
              const catData = breakdown[cat.key] || { completed: 0, total: 0 };
              const Icon = cat.icon;
              const isComplete = catData.completed >= catData.total && catData.total > 0;
              
              return (
                <div 
                  key={cat.key}
                  className={cn(
                    "p-2 rounded-lg text-center border",
                    isComplete ? "bg-green-50 border-green-200" : "bg-gray-50 border-gray-200"
                  )}
                >
                  <Icon className={cn(
                    "h-4 w-4 mx-auto mb-1",
                    isComplete ? "text-green-600" : "text-gray-400"
                  )} />
                  <p className={cn(
                    "text-sm font-medium",
                    isComplete ? "text-green-700" : "text-gray-700"
                  )}>
                    {catData.completed}/{catData.total}
                  </p>
                  <p className="text-xs text-gray-500">{cat.label}</p>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* QUICK ACTIONS */}
      <Card className="border border-gray-200 shadow-sm">
        <CardHeader className="py-3 px-4 bg-gray-50/50 border-b border-gray-100">
          <CardTitle className="text-base font-semibold text-gray-700">
            QUICK ACTIONS
          </CardTitle>
        </CardHeader>
        <CardContent className="py-3 px-4">
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSendReminder}
              disabled={actionLoading === 'reminder'}
            >
              {actionLoading === 'reminder' ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1" />
              ) : (
                <Send className="h-4 w-4 mr-1" />
              )}
              Send Reminder to Worker
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onNavigateToTab?.('compliance')}
            >
              <Eye className="h-4 w-4 mr-1" />
              View staff file
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onNavigateToTab?.('training')}
            >
              <GraduationCap className="h-4 w-4 mr-1" />
              View Training
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onNavigateToTab?.('references')}
            >
              <Users className="h-4 w-4 mr-1" />
              View References
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
