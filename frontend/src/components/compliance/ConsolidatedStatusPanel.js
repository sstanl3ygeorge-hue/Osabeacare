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
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import {
  AlertTriangle,
  FileText, Users, GraduationCap, ClipboardCheck,
  Send, Plus, RefreshCw, Loader2, Shield,
  FileCheck, UserCheck, Briefcase, Heart, Calendar
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import API_BASE from '../../utils/apiBase';


const API = API_BASE;

export default function ConsolidatedStatusPanel({
  employeeId,
  employeeName,
  role,
  personStage,
  recruitmentApproved,
  onRefresh,
  showQuickActions = true,
  complianceFile = null,
  trainingEvaluation = null,
  inductionChecklist = null
}) {
  const { token } = useAuth();
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
      // Fetch unified progress and pre-employment gates independently so one failure does not block panel shell.
      const [progressRes, gatesRes] = await Promise.allSettled([
        axios.get(`${API}/employees/${employeeId}/unified-progress`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/employees/${employeeId}/pre-employment-gates`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      const progressData = progressRes.status === 'fulfilled'
        ? progressRes.value.data
        : { status_unavailable: true, overall_percentage: 0, completed_requirements: 0, total_requirements: 0, categories: {}, blockers: [], blocker_details: [] };
      const gatesData = gatesRes.status === 'fulfilled'
        ? gatesRes.value.data
        : { status_unavailable: true, blockers: [], summary: { pending: 0, completed: 0, total: 0 } };

      setData({
        progress: progressData,
        gates: gatesData
      });
      if (progressRes.status === 'rejected' && gatesRes.status === 'rejected') {
        setLoadError('Unable to load readiness status');
      }
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
        `${API}/employees/${employeeId}/recruitment-gate`,
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
        `${API}/workers/${employeeId}/send-reminder`,
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
        `${API}/employees/${employeeId}/approve-recruitment`,
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
                    {employeeName} â€¢ {role} â€¢ Canonical readiness could not be loaded
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
  const complianceSections =
    complianceFile?.sections && typeof complianceFile.sections === 'object'
      ? complianceFile.sections
      : {};
  const sectionRows = Object.values(complianceSections).flatMap((section) =>
    Array.isArray(section?.rows) ? section.rows.filter((row) => row && typeof row === 'object') : []
  );
  const sectionTotalRows = sectionRows.length;
  const sectionCompletedRows = sectionRows.filter((row) => {
    const s = String(row?.status || '').toLowerCase();
    return row?.is_verified === true || row?.verified === true || ['verified', 'complete', 'completed', 'accepted', 'approved', 'recorded'].includes(s);
  }).length;
  const sectionProgressAvailable = complianceFile?.serializer_version === 'dual_row_v1' && sectionTotalRows > 0;
  const rowsByType = sectionRows.reduce((acc, row) => {
    const t = String(row?.row_type || '').toLowerCase();
    if (!acc[t]) acc[t] = [];
    acc[t].push(row);
    return acc;
  }, {});
  const isCompleteRow = (row) => {
    const s = String(row?.status || '').toLowerCase();
    return row?.is_verified === true || row?.verified === true || ['verified', 'accepted', 'approved', 'completed', 'complete', 'recorded', 'acknowledged'].includes(s);
  };
  const isAgreementCompleteRow = (row) => {
    const s = String(row?.status || row?.contract_state || '').toLowerCase();
    return (
      row?.is_verified === true ||
      row?.verified === true ||
      [
        'verified',
        'complete',
        'completed',
        'accepted',
        'approved',
        'recorded',
        'acknowledged',
        'signed',
        'fully_executed',
      ].includes(s)
    );
  };
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
  const canonicalCompleted = Number(progress?.completed);
  const canonicalTotal = Number(progress?.total);
  const canonicalPercentage = Number(progress?.percentage);
  const canonicalProgressAvailable = Number.isFinite(canonicalCompleted)
    && Number.isFinite(canonicalTotal)
    && canonicalTotal > 0
    && Number.isFinite(canonicalPercentage);

  const fallbackCompleted = sectionProgressAvailable ? sectionCompletedRows : Number(progress?.completed_requirements ?? 0);
  const fallbackTotal = sectionProgressAvailable ? sectionTotalRows : Number(progress?.total_requirements ?? 0);
  const fallbackCountAvailable = Number.isFinite(fallbackTotal) && fallbackTotal > 0;
  const fallbackPercentage = sectionProgressAvailable
    ? Math.round((sectionCompletedRows / sectionTotalRows) * 100)
    : Number(progress?.overall_percentage ?? 0);

  const isApplicant = personStage === 'applicant';
  
  // Use dual-row section breakdown for employee operational view when available.
  const checkRows = rowsByType.check || [];
  const evidenceRows = rowsByType.evidence || [];
  const documentsFromChecks = checkRows.filter((row) => {
    const key = String(
      row?.requirement_id || row?.requirement_key || row?.key || row?.id || row?.check_type || ''
    ).toLowerCase();
    return key.includes('dbs')
      || key.includes('rtw')
      || key.includes('right_to_work')
      || key.includes('identity')
      || key.includes('proof_of_address')
      || key.includes('address');
  });
  const documentsCompletedFromChecks = documentsFromChecks.filter((row) => {
    const s = String(row?.status || '').toLowerCase();
    return row?.is_verified === true || row?.verified === true || ['verified', 'approved', 'complete', 'completed'].includes(s);
  }).length;
  const documentsTotalFromChecks = documentsFromChecks.length;
  const trainingEvalItems = Array.isArray(trainingEvaluation?.items)
    ? trainingEvaluation.items
    : (Array.isArray(complianceSections?.training?.evaluation?.items)
      ? complianceSections.training.evaluation.items
      : []);
  const inductionChecklistItems = Array.isArray(inductionChecklist?.items)
    ? inductionChecklist.items
    : [];
  const trainingItemsCompleted = trainingEvalItems.filter((item) => {
    const s = String(item?.status || '').toLowerCase();
    return item?.completed === true || ['verified', 'current', 'complete', 'completed'].includes(s);
  }).length;
  const inductionUnified = progress?.categories?.induction || progress?.category_details?.induction || {};
  const inductionUnifiedCompleted = Number(inductionUnified?.completed);
  const inductionUnifiedTotal = Number(inductionUnified?.total);
  const activeNoInductionRequired = !isApplicant && (inductionUnified?.required === false || inductionUnified?.not_required === true);
  const inductionChecklistCompleted = inductionChecklistItems.filter((item) => String(item?.status || '').toLowerCase() === 'completed').length;
  const inductionChecklistTotal = inductionChecklistItems.length;

  const sectionBreakdown = {
    documents: {
      completed: documentsTotalFromChecks > 0 ? documentsCompletedFromChecks : evidenceRows.filter(isCompleteRow).length,
      total: documentsTotalFromChecks > 0 ? documentsTotalFromChecks : evidenceRows.length
    },
    forms: {
      completed: (() => {
        const recruitmentFormKeys = new Set(['interview_record', 'application_form', 'recruitment_checklist']);
        const formRows = (rowsByType.form || []).filter((row) => {
          if (isApplicant) return true;
          const key = String(
            row?.requirement_id
            || row?.requirement_key
            || row?.id
            || row?.key
            || ''
          ).toLowerCase();
          return !recruitmentFormKeys.has(key);
        });
        return formRows.filter(isCompleteRow).length;
      })(),
      total: (() => {
        const recruitmentFormKeys = new Set(['interview_record', 'application_form', 'recruitment_checklist']);
        const formRows = (rowsByType.form || []).filter((row) => {
          if (isApplicant) return true;
          const key = String(
            row?.requirement_id
            || row?.requirement_key
            || row?.id
            || row?.key
            || ''
          ).toLowerCase();
          return !recruitmentFormKeys.has(key);
        });
        return formRows.length;
      })()
    },
    training: {
      completed: trainingEvalItems.length > 0
        ? trainingItemsCompleted
        : (rowsByType.training || []).filter(isCompleteRow).length + (rowsByType.training_record || []).filter(isCompleteRow).length,
      total: trainingEvalItems.length > 0
        ? trainingEvalItems.length
        : (rowsByType.training || []).length + (rowsByType.training_record || []).length
    },
    references: {
      completed: (rowsByType.reference || []).filter(isCompleteRow).length,
      total: (rowsByType.reference || []).length
    },
    agreements: {
      completed: (rowsByType.form_acknowledgement || []).filter((r) => r?.latest_active !== false).filter(isAgreementCompleteRow).length,
      total: (rowsByType.form_acknowledgement || []).filter((r) => r?.latest_active !== false).length
    },
    induction: {
      completed: inductionChecklistTotal > 0
        ? inductionChecklistCompleted
        : (Number.isFinite(inductionUnifiedCompleted)
        ? inductionUnifiedCompleted
        : ((rowsByType.induction || []).filter(isCompleteRow).length)),
      total: inductionChecklistTotal > 0
        ? inductionChecklistTotal
        : (Number.isFinite(inductionUnifiedTotal)
        ? inductionUnifiedTotal
        : (activeNoInductionRequired ? 0 : (rowsByType.induction || []).length))
    }
  };
  const breakdown = sectionProgressAvailable ? sectionBreakdown : (progress.categories || {});
  const tileKeys = ['documents', 'forms', 'training', 'references', 'agreements', 'induction'];
  const tileTotals = tileKeys.reduce((acc, key) => {
    const d = breakdown[key] || { completed: 0, total: 0 };
    const total = Number(d.total) || 0;
    const completed = Math.min(Number(d.completed) || 0, total);
    acc.completed += completed;
    acc.total += total;
    return acc;
  }, { completed: 0, total: 0 });
  const progressCompleted = tileTotals.completed;
  const progressTotal = tileTotals.total;
  const progressCountAvailable = progressTotal > 0;
  const progressPercentage = progressCountAvailable ? Math.round((progressCompleted / progressTotal) * 100) : (canonicalProgressAvailable ? canonicalPercentage : fallbackPercentage);
  const usesEstimated = !(sectionProgressAvailable || canonicalProgressAvailable);
  const progressHeadlineLabel = progressCountAvailable
    ? `${progressCompleted} of ${progressTotal} items submitted (${progressPercentage}%)${usesEstimated ? ' [estimated]' : ''}`
    : `item count unavailable (${progressPercentage}%)${usesEstimated ? ' [estimated]' : ''}`;

  // Determine overall status

  // Gate-derived approval readiness (canonical â€” overrides old isBlocked for the approve CTA)
  const gateAllowed = gateResult?.allowed === true;
  const gateHasData = gateResult !== null;
  // Approval CTA guard: gate is the ONLY signal â€” no fallback to legacy isBlocked
  const canApproveRecruitment = gateAllowed;

  return (
    <div className="space-y-4" data-testid="consolidated-status-panel">
      {/* PROGRESS SUMMARY - ONE CARD */}
      <Card className="border border-gray-200 shadow-sm">
        <CardHeader className="py-3 px-4 bg-gray-50/50 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold text-gray-700">
              Submission Progress — {progressHeadlineLabel}
            </CardTitle>
            <p className="text-[11px] text-gray-400 mt-0.5">Tracks document and form submission only â€” not approval readiness</p>
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
      {showQuickActions && <Card className="border border-gray-200 shadow-sm">
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
            {isApplicant && !recruitmentApproved && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleApproveRecruitment}
                disabled={actionLoading === 'approve' || gateLoading || !canApproveRecruitment || gateFetchFailed || (!gateHasData && !gateLoading)}
                title={
                  gateFetchFailed ? 'Approval check unavailable â€” reload to retry' :
                  !gateHasData ? 'Approval check not yet loaded' :
                  !canApproveRecruitment ? 'Resolve all blockers before approving' :
                  undefined
                }
              >
                {actionLoading === 'approve' ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <UserCheck className="h-4 w-4 mr-1" />
                )}
                Approve for Recruitment
              </Button>
            )}
          </div>
        </CardContent>
      </Card>}
    </div>
  );
}


