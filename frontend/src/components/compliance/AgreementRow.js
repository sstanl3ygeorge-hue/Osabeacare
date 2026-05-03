/**
 * AgreementRow.js - Refactored for template-based submissions
 * 
 * Agreements are real template-driven forms, not simple status toggles:
 * - Zero Hour Contract (ZERO_HOUR_CONTRACT_V1)
 * - Employee Handbook Acknowledgement (EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1)
 * 
 * Real lifecycle states:
 * - not_sent: No action taken
 * - sent: Request sent to employee
 * - in_progress: Employee has viewed but not completed
 * - submitted: Form submitted, awaiting review
 * - verified: Admin verified the submission
 * - rejected: Admin rejected the submission
 * 
 * Completion modes:
 * - self: Employee completed independently
 * - admin_assisted: Admin filled on employee's behalf
 * - phone_assisted: Admin recorded during phone call
 */

import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { 
  FileSignature, CheckCircle, XCircle, Clock, AlertTriangle, 
  ChevronDown, ChevronUp, Mail, Phone, Edit, History, Eye,
  Download, Send, Loader2, FileText, User, UserCheck, RotateCcw
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';
import { resolveLatestContractState } from '../../lib/contractState';
import API_BASE from '../../utils/apiBase';
import AwaitingDaysBadge from './AwaitingDaysBadge';

const API = API_BASE;

// Map agreement keys to template IDs
const AGREEMENT_TEMPLATE_MAP = {
  'contract_acceptance': 'ZERO_HOUR_CONTRACT_V1',
  'handbook_acknowledgement': 'EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1',
};

/**
 * Returns a source contract id only when it is from a known generated-contract field.
 *
 * Why no fallback to row.key / acknowledgement_data.id / agreement id:
 * those identifiers may represent acknowledgement/submission records rather
 * than generated_contracts records, and sending them as source_contract_id can
 * create false 409 conflicts or bind reissue to the wrong context.
 */
const getReissueSourceContractId = (agreement) => {
  const generatedContractId = agreement?.generated_contract_id;
  if (generatedContractId) return generatedContractId;

  const latestContractId = agreement?.latest_contract_id;
  if (latestContractId) return latestContractId;

  // `contract_id` is accepted only when explicitly present on the
  // acknowledgement payload as a contract pointer from backend contract state.
  const contractId = agreement?.contract_id;
  if (contractId) return contractId;

  return null;
};

export default function AgreementRow({
  row,
  employeeId,
  employeeEmail,
  employeeData,
  onRefresh,
  onOpenForm,      // Opens AgreementFormDrawer in create mode
  onViewSubmission, // Opens AgreementFormDrawer in view mode
  onViewHistory,
  onReissueContract,
  isAuditor = false
}) {
  const [expanded, setExpanded] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const { token } = useAuth();

  const {
    key,
    title,
    status,
    status_summary,
    has_acknowledgement,
    is_verified,
    acknowledgement_data,
    pending_requests = [],
    submission_data,  // New: Real template submission
    counts = {},
    allowed_actions = [],
    blocker_text
  } = row;

  // Get template ID for this agreement
  const templateId = AGREEMENT_TEMPLATE_MAP[key];

  // Determine lifecycle status
  // CRITICAL: Only mark 'submitted' when there's actual evidence the worker
  // acted on the agreement. `has_acknowledgement` alone is True even for
  // stub/legacy rows (e.g. an ack row created by ensure_agreement_rendered
  // where the PDF was rendered but no one has signed/acknowledged yet).
  // Trusting it caused admin to show "Awaiting admin review" while the
  // worker dashboard correctly showed "Action required: please acknowledge"
  // for the same employee — exact symptom for Olakunle Alonge / Ramon Akinsanya
  // on the handbook row.
  const getLifecycleStatus = () => {
    if (is_verified) return 'verified';
    if (acknowledgement_data?.latest_active !== false && acknowledgement_data?.verification_status === 'rejected') return 'rejected';
    const workerActed = Boolean(
      acknowledgement_data?.acknowledged ||
      acknowledgement_data?.worker_signed_at ||
      acknowledgement_data?.signed_at ||
      acknowledgement_data?.completed_at ||
      acknowledgement_data?.worker_signed_contract_pdf_url ||
      acknowledgement_data?.executed_contract_pdf_url ||
      acknowledgement_data?.signed_document_url ||
      submission_data?.id ||
      submission_data?.completed_at
    );
    if (workerActed) return 'submitted';
    if (pending_requests.length > 0) return 'sent';
    return 'not_sent';
  };

  const lifecycleStatus = getLifecycleStatus();
  const contractResolution = resolveLatestContractState(acknowledgement_data, {});
  const normalizedContractStatus = contractResolution.status;
  const rowAgreementType = row?.agreement_type || row?.agreementType || row?.type || row?.key || '';
  const isContractRow =
    key === 'contract_acceptance' ||
    String(rowAgreementType || '').toLowerCase() === 'contract_acceptance';
  const isAwaitingWorkerSignature = contractResolution.isAwaitingWorkerSignature;
  const canonicalLifecycleStatus = String(
    acknowledgement_data?.current_lifecycle?.status ||
    row?.current_lifecycle?.status ||
    ''
  ).trim().toLowerCase();
  const canonicalLatestActive = acknowledgement_data?.latest_active === true;
  const canonicalStatus = String(acknowledgement_data?.status || '').trim().toLowerCase();
  const contractNeedsReissue =
    isContractRow &&
    canonicalLatestActive &&
    !isAwaitingWorkerSignature &&
    ['rejected', 'rejected_reopen_required', 'action_required', 'superseded'].includes(normalizedContractStatus);
  const shouldShowReissueButton =
    isContractRow &&
    typeof onReissueContract === 'function' &&
    contractNeedsReissue;
  const contractArtifactUrl =
    acknowledgement_data?.executed_contract_pdf_url ||
    acknowledgement_data?.worker_signed_contract_pdf_url ||
    acknowledgement_data?.rendered_contract_pdf_url;
  const effectiveLifecycleStatus =
    isContractRow && isAwaitingWorkerSignature
      ? 'submitted'
      : (
          !isContractRow && canonicalLifecycleStatus === 'signed' && !is_verified
            ? 'submitted'
            : (canonicalLifecycleStatus || lifecycleStatus)
        );
  const contractDateLabel = isContractRow
    ? (
        acknowledgement_data?.company_signed_at
          ? `Executed ${formatBackendDate(acknowledgement_data.company_signed_at, { format: 'medium' })}`
          : acknowledgement_data?.worker_signed_at
            ? `Worker signed ${formatBackendDate(acknowledgement_data.worker_signed_at, { format: 'medium' })}`
            : (acknowledgement_data?.signed_at || acknowledgement_data?.completed_at)
              ? `Signed ${formatBackendDate(acknowledgement_data?.signed_at || acknowledgement_data?.completed_at, { format: 'medium' })}`
              : null
      )
    : null;
  const hasWorkerSignedArtifact = Boolean(
    acknowledgement_data?.worker_signed_contract_pdf_url ||
    acknowledgement_data?.signed_document_url
  );
  // Lawrence-style edge case:
  // Worker signed a PREVIOUS template version and a newer canonical template
  // now exists. The signature is preserved — admin must reissue before it can
  // be countersigned. We expose this explicitly so admins don't see
  // contradictory phrases like "No contract record found" + "Awaiting company
  // countersignature". Backend marks the ack row with render_issue
  // "legacy_template_signed" via POST /admin/agreements/repair.
  const ackRenderIssue = String(
    acknowledgement_data?.render_issue || row?.render_issue || ''
  ).toLowerCase();
  const ackTemplateVersion = acknowledgement_data?.template_version;
  const ackCanonical = acknowledgement_data?.canonical_contract;
  const workerSignedLegacyTemplate =
    isContractRow &&
    hasWorkerSignedArtifact &&
    (
      ackRenderIssue === 'legacy_template_signed' ||
      // Fallback detection when the repair flag has not been written yet.
      (ackTemplateVersion && ackCanonical === false)
    );
  const contractCountersignReady = isContractRow && hasWorkerSignedArtifact && !workerSignedLegacyTemplate && (
    effectiveLifecycleStatus === 'awaiting_company_countersignature' ||
    normalizedContractStatus === 'awaiting_company_countersignature' ||
    canonicalStatus === 'awaiting_company_countersignature'
  );

  // Status colors and icons
  const getStatusConfig = () => {
    if (workerSignedLegacyTemplate) {
      return {
        color: 'amber',
        bgColor: 'bg-amber-100',
        textColor: 'text-amber-800',
        icon: AlertTriangle,
        label: 'Worker signed previous version — admin must reissue'
      };
    }
    if (key === 'contract_acceptance' && isAwaitingWorkerSignature) {
      return { color: 'blue', bgColor: 'bg-blue-100', textColor: 'text-blue-700', icon: Clock, label: 'Awaiting worker signature' };
    }
    if (contractNeedsReissue) {
      return { color: 'amber', bgColor: 'bg-amber-100', textColor: 'text-amber-700', icon: AlertTriangle, label: 'Contract needs reissue' };
    }
    if (key === 'contract_acceptance' && canonicalStatus === 'pending_signature') {
      return { color: 'blue', bgColor: 'bg-blue-100', textColor: 'text-blue-700', icon: Clock, label: 'Awaiting worker signature' };
    }
    switch (lifecycleStatus) {
      case 'verified':
        return { color: 'green', bgColor: 'bg-green-100', textColor: 'text-green-700', icon: CheckCircle, label: 'Verified' };
      case 'rejected':
        return { color: 'red', bgColor: 'bg-red-100', textColor: 'text-red-700', icon: XCircle, label: 'Rejected / action required' };
      case 'submitted':
        return { color: 'amber', bgColor: 'bg-amber-100', textColor: 'text-amber-700', icon: Clock, label: key === 'contract_acceptance' ? 'Awaiting company countersignature' : 'Awaiting admin review' };
      case 'sent':
        return { color: 'blue', bgColor: 'bg-blue-100', textColor: 'text-blue-700', icon: Mail, label: 'Evidence requested' };
      case 'in_progress':
        return { color: 'purple', bgColor: 'bg-purple-100', textColor: 'text-purple-700', icon: Edit, label: 'Submitted, not reviewed' };
      default:
        return { color: 'gray', bgColor: 'bg-gray-100', textColor: 'text-gray-700', icon: FileSignature, label: 'Awaiting worker' };
    }
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;
  const displaySummary = workerSignedLegacyTemplate
    ? 'Worker signature from a previous template is preserved. Reissue this contract so the worker can sign the current version.'
    : (contractNeedsReissue
      ? 'Worker cannot sign this version.'
      : (key === 'contract_acceptance' && isAwaitingWorkerSignature
        ? (
            row?.contract_signing_unlocked === false
              ? (row?.contract_signing_lock_reason || 'Contract generated, but signing is locked until earlier onboarding steps are complete.')
              : 'Worker can now sign this contract.'
          )
        : status_summary));

  // Completion mode display
  const getCompletionModeDisplay = (mode) => {
    const modes = {
      'self': { label: 'Self-completed', icon: User },
      'self_completed': { label: 'Self-completed', icon: User },
      'admin_assisted': { label: 'Admin-assisted', icon: UserCheck },
      'phone_assisted': { label: 'Phone-assisted', icon: Phone },
    };
    return modes[mode] || { label: mode?.replace(/_/g, ' ') || 'Unknown', icon: User };
  };

  // Handle verify submission
  const handleVerify = async () => {
    const submissionId = submission_data?.id || acknowledgement_data?.submission_id;
    if (!submissionId) {
      // Fallback to legacy verify
      if (acknowledgement_data?.id) {
        setIsProcessing(true);
        try {
          await axios.post(
            `${API}/employees/${employeeId}/agreements/${acknowledgement_data.id}/verify`,
            '"Verified by admin"',
            { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } }
          );
          toast.success(key === 'contract_acceptance' ? 'Contract countersigned' : 'Agreement verified');
          if (onRefresh) onRefresh();
        } catch (err) {
          toast.error(err.response?.data?.detail || 'Failed to verify');
        } finally {
          setIsProcessing(false);
        }
      }
      return;
    }
    
    setIsProcessing(true);
    try {
      await axios.post(
        `${API}/agreement-submissions/${submissionId}/verify`,
        { notes: 'Verified by admin' },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(key === 'contract_acceptance' ? 'Contract countersigned' : 'Agreement verified');
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle reject submission
  const handleReject = async () => {
    const reason = prompt('Enter rejection reason (min 10 characters):');
    if (!reason || reason.length < 10) {
      if (reason) toast.error('Rejection reason must be at least 10 characters');
      return;
    }
    
    const submissionId = submission_data?.id || acknowledgement_data?.submission_id;
    if (!submissionId) {
      // Fallback to legacy reject
      if (acknowledgement_data?.id) {
        setIsProcessing(true);
        try {
          await axios.post(
            `${API}/employees/${employeeId}/agreements/${acknowledgement_data.id}/reject`,
            { reason },
            { headers: { Authorization: `Bearer ${token}` } }
          );
          toast.success('Agreement rejected');
          if (onRefresh) onRefresh();
        } catch (err) {
          toast.error(err.response?.data?.detail || 'Failed to reject');
        } finally {
          setIsProcessing(false);
        }
      }
      return;
    }
    
    setIsProcessing(true);
    try {
      await axios.post(
        `${API}/agreement-submissions/${submissionId}/reject`,
        { reason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Agreement rejected');
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle unverify submission (for error correction)
  const handleUnverify = async () => {
    const reason = prompt('Enter reason for unverifying (min 3 characters):');
    if (!reason || reason.length < 3) {
      if (reason) toast.error('Reason must be at least 3 characters');
      return;
    }
    
    const submissionId = submission_data?.id || acknowledgement_data?.submission_id;
    if (!submissionId) {
      // Fallback to legacy unverify
      if (acknowledgement_data?.id) {
        setIsProcessing(true);
        try {
          await axios.post(
            `${API}/employees/${employeeId}/agreements/${acknowledgement_data.id}/unverify`,
            { reason },
            { headers: { Authorization: `Bearer ${token}` } }
          );
          toast.success('Agreement unverified - now pending re-review');
          if (onRefresh) onRefresh();
        } catch (err) {
          toast.error(err.response?.data?.detail || 'Failed to unverify');
        } finally {
          setIsProcessing(false);
        }
      }
      return;
    }
    
    setIsProcessing(true);
    try {
      await axios.post(
        `${API}/agreement-submissions/${submissionId}/unverify`,
        { reason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Agreement unverified - now pending re-review');
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to unverify');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRegenerate = async () => {
    const acknowledgementId = acknowledgement_data?.id || '__fallback__';
    const submissionId = submission_data?.id || acknowledgement_data?.submission_id || null;

    const reason = prompt('Enter regeneration reason (min 3 characters):');
    if (!reason || reason.trim().length < 3) {
      if (reason) toast.error('Reason must be at least 3 characters');
      return;
    }

    setIsProcessing(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/agreements/${acknowledgementId}/regenerate`,
        {
          reason: reason.trim(),
          agreement_type: key,
          submission_id: submissionId,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Handbook regenerated. Worker can review it again once ready.');
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to regenerate handbook');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRecoverAgreement = async () => {
    const reason = prompt('Enter recovery reason (min 3 characters):');
    if (!reason || reason.trim().length < 3) {
      if (reason) toast.error('Reason must be at least 3 characters');
      return;
    }

    setIsProcessing(true);
    try {
      const payload = {
        agreement_type: key,
        reason: reason.trim(),
      };
      await axios.post(
        `${API}/employees/${employeeId}/agreements/recover`,
        payload,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(
        key === 'contract_acceptance'
          ? 'Agreement recovered. Worker can sign the latest contract.'
          : 'Agreement recovered. Worker can review and acknowledge handbook.'
      );
      if (onRefresh) onRefresh();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message =
        (typeof detail === 'string' && detail) ||
        detail?.render_issue ||
        detail?.detail ||
        'Failed to recover agreement';
      toast.error(message);
    } finally {
      setIsProcessing(false);
    }
  };

  // Admin-side surgical repair: supersedes non-canonical rows, re-renders
  // unsigned contracts with canonical template, mirrors verified handbook
  // submissions into the ack row. Never discards worker signatures.
  // Calls the dedicated repair endpoint (dry run first, then apply on confirmation).
  const handleRepairAgreement = async () => {
    setIsProcessing(true);
    try {
      const dryRun = await axios.post(
        `${API}/admin/agreements/repair`,
        { employee_id: employeeId, apply: false },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const contractAction = dryRun.data?.result?.contract?.action || 'no_change';
      const handbookAction = dryRun.data?.result?.handbook?.action || 'no_change';
      if (contractAction === 'no_change' && handbookAction === 'no_change') {
        toast.info('No repair needed — state is already consistent.');
        return;
      }
      const confirmed = window.confirm(
        `Repair plan for this employee:\n\n` +
        `  • Contract: ${contractAction}\n` +
        `  • Handbook: ${handbookAction}\n\n` +
        `Apply now? (Worker signatures are never discarded.)`
      );
      if (!confirmed) return;
      const applied = await axios.post(
        `${API}/admin/agreements/repair`,
        { employee_id: employeeId, apply: true },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const appliedContract = applied.data?.result?.contract?.action;
      const appliedHandbook = applied.data?.result?.handbook?.action;
      toast.success(`Repair applied — contract: ${appliedContract}, handbook: ${appliedHandbook}`);
      if (onRefresh) onRefresh();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message =
        (typeof detail === 'string' && detail) ||
        detail?.message ||
        'Failed to repair agreement';
      toast.error(message);
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle PDF export
  const handleExportPDF = async () => {
    if (key === 'contract_acceptance' && contractArtifactUrl) {
      window.open(contractArtifactUrl, '_blank', 'noopener,noreferrer');
      return;
    }
    const submissionId = submission_data?.id || acknowledgement_data?.submission_id;
    if (!submissionId) {
      toast.error('No submission to export');
      return;
    }
    
    try {
      const response = await axios.get(
        `${API}/agreement-submissions/${submissionId}/pdf`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Open HTML content in new window for printing
      const printWindow = window.open('', '_blank');
      printWindow.document.write(response.data.html_content);
      printWindow.document.close();
      printWindow.print();
    } catch (err) {
      toast.error('Failed to export PDF');
    }
  };

  // Get completion mode data
  const completionMode = submission_data?.completion_mode || acknowledgement_data?.completion_mode;
  const modeConfig = completionMode ? getCompletionModeDisplay(completionMode) : null;
  const ModeIcon = modeConfig?.icon;

  return (
    <div 
      className={`border rounded-xl overflow-hidden ${
        effectiveLifecycleStatus === 'verified' ? 'border-green-200 bg-green-50/30' : 
        effectiveLifecycleStatus === 'rejected' ? 'border-red-200 bg-red-50/30' :
        effectiveLifecycleStatus === 'submitted' ? 'border-amber-200 bg-amber-50/30' : 
        effectiveLifecycleStatus === 'sent' ? 'border-blue-200 bg-blue-50/30' : 
        'border-gray-200 bg-gray-50/30'
      }`}
      data-testid={`agreement-row-${key}`}
    >
      {/* Row Header */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-white/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Icon */}
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${statusConfig.bgColor}`}>
            <StatusIcon className={`h-5 w-5 ${statusConfig.textColor}`} />
          </div>
          
          {/* Title and Summary */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-medium text-text-primary">{title}</h4>
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-purple-50 text-purple-600 border-purple-200">
                Readiness requirement
              </Badge>
              {blocker_text && (
                <Badge className="bg-red-100 text-red-700 text-[10px]">
                  Needed before start
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <p className="text-sm text-text-muted truncate">{displaySummary}</p>
              {modeConfig && (
                <Badge className="text-[9px] bg-gray-100 text-gray-600 border-gray-200">
                  <ModeIcon className="h-2.5 w-2.5 mr-0.5" />
                  {modeConfig.label}
                </Badge>
              )}
            </div>
            {contractDateLabel && (
              <p className="text-xs text-gray-500 mt-0.5">{contractDateLabel}</p>
            )}
            {/* Specific blockers list (Tier 4 fix) � when a contract is locked
                we MUST show the worker exactly which steps are still
                outstanding. Generic "complete your earlier onboarding steps"
                copy was leaving applicants like Olakunle stranded with
                everything green on screen but the contract still locked. */}
            {key === 'contract_acceptance'
              && row?.contract_signing_unlocked === false
              && Array.isArray(row?.contract_signing_blockers)
              && row.contract_signing_blockers.length > 0 && (
              <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 p-2" data-testid="contract-lock-blockers">
                <p className="text-[11px] font-medium text-amber-800 mb-1">
                  Still needed before this contract can be signed ({row.contract_signing_blockers.length}):
                </p>
                <ul className="text-[11px] text-amber-700 space-y-0.5 list-disc list-inside">
                  {row.contract_signing_blockers.slice(0, 6).map((blocker, idx) => (
                    <li key={idx}>{typeof blocker === 'string' ? blocker : (blocker?.title || blocker?.name || JSON.stringify(blocker))}</li>
                  ))}
                  {row.contract_signing_blockers.length > 6 && (
                    <li className="text-amber-600">+ {row.contract_signing_blockers.length - 6} more�</li>
                  )}
                </ul>
              </div>
            )}
          </div>
          
          {/* Status Badge */}
          <Badge className={`${statusConfig.bgColor} ${statusConfig.textColor} text-xs`}>
            {statusConfig.label}
          </Badge>

          {/* Awaiting-days chase badge — Tier 3 #4. Surfaces how long the
              agreement has been waiting on a counterparty so admins can
              triage chases without opening every row. Only shown while
              the agreement is genuinely awaiting action (not when verified
              or rejected). */}
          {(['sent', 'submitted', 'in_progress'].includes(effectiveLifecycleStatus)
            || (isContractRow && isAwaitingWorkerSignature)
            || contractCountersignReady) && (
            <AwaitingDaysBadge
              sentAt={
                pending_requests?.[0]?.sent_at
                || acknowledgement_data?.requested_at
                || acknowledgement_data?.sent_at
                || acknowledgement_data?.created_at
                || acknowledgement_data?.worker_signed_at
              }
              testId={`agreement-awaiting-${key}`}
            />
          )}
        </div>
        
        {/* Actions */}
        <div className="flex flex-wrap items-center justify-end gap-2 ml-4">
          {!isAuditor && (
            <>
              {/* Agreements are worker-owned. Admin never fills them.
                  When lifecycleStatus === 'not_sent' the admin sees the
                  'Awaiting worker' status badge and no action button. */}

              {/* View Submission - for submitted/verified */}
              {(isContractRow
                ? Boolean(contractArtifactUrl)
                : (effectiveLifecycleStatus === 'submitted' || effectiveLifecycleStatus === 'verified' || effectiveLifecycleStatus === 'rejected')) && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => { 
                    e.stopPropagation(); 
                    if (isContractRow && contractArtifactUrl) {
                      window.open(contractArtifactUrl, '_blank', 'noopener,noreferrer');
                    } else if (onViewSubmission) {
                      const submissionId = submission_data?.id || acknowledgement_data?.submission_id;
                      onViewSubmission(key, title, templateId, submissionId);
                    }
                  }}
                  className="h-8 text-xs rounded-lg"
                  data-testid={`view-submission-${key}`}
                >
                  <Eye className="h-3.5 w-3.5 mr-1" />
                  View
                </Button>
              )}
              
              {shouldShowReissueButton && (
                <Button
                  size="sm"
                  variant="default"
                  onClick={(e) => {
                    e.stopPropagation();
                    const sourceContractId = acknowledgement_data?.source_record_id || getReissueSourceContractId(acknowledgement_data);
                    onReissueContract({
                      id: sourceContractId,
                      status: normalizedContractStatus || null,
                      contract_state: acknowledgement_data?.contract_state || null,
                    });
                  }}
                  disabled={isProcessing}
                  className="h-8 text-xs rounded-lg bg-amber-600 hover:bg-amber-700 text-white"
                >
                  <RotateCcw className="h-3.5 w-3.5 mr-1" />
                  Reissue contract
                </Button>
              )}

              {((key === 'contract_acceptance' && (
                  contractNeedsReissue ||
                  String(status_summary || '').toLowerCase().includes('stale or missing')
                )) ||
                (key === 'handbook_acknowledgement' && ['rejected', 'submitted', 'not_sent'].includes(effectiveLifecycleStatus))) && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRecoverAgreement();
                  }}
                  disabled={isProcessing}
                  className="h-8 text-xs rounded-lg"
                >
                  <RotateCcw className="h-3.5 w-3.5 mr-1" />
                  Recover / rebuild agreement
                </Button>
              )}

              {/* Surgical admin repair button — appears when the row looks
                  inconsistent (stale legacy contract, or admin-worker handbook
                  drift). Dry-runs first, then applies on confirmation. Never
                  discards worker signatures. */}
              {(contractNeedsReissue ||
                (key === 'contract_acceptance' && !contractArtifactUrl && effectiveLifecycleStatus !== 'not_sent') ||
                (key === 'handbook_acknowledgement' && acknowledgement_data?.verification_status && acknowledgement_data?.verification_status !== (is_verified ? 'verified' : acknowledgement_data?.verification_status))
              ) && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => { e.stopPropagation(); handleRepairAgreement(); }}
                  disabled={isProcessing}
                  className="h-8 text-xs rounded-lg border-purple-300 text-purple-700 hover:bg-purple-50"
                  title="Surgical repair — dry-runs first, preserves worker signatures"
                  data-testid={`repair-agreement-${key}`}
                >
                  {isProcessing ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <RotateCcw className="h-3.5 w-3.5 mr-1" />}
                  Repair agreement
                </Button>
              )}

              {/* Verify / Reject for awaiting review */}
              {(
                (!isContractRow && (
                  effectiveLifecycleStatus === 'submitted'
                  || effectiveLifecycleStatus === 'awaiting_review'
                  // Tier 4 safety net: if the row has a real acknowledgement
                  // id and isn't already verified, surface Verify/Reject
                  // regardless of the effective lifecycle string. Prevents
                  // admin from being stuck when status normalization drifts.
                  || (!!(acknowledgement_data?.id || acknowledgement_data?.acknowledgement_id) && !is_verified)
                ))
                || contractCountersignReady
              ) && (
                <>
                  <Button
                    size="sm"
                    variant="default"
                    onClick={(e) => { e.stopPropagation(); handleVerify(); }}
                    disabled={isProcessing}
                    className="h-8 text-xs bg-green-600 hover:bg-green-700 text-white rounded-lg"
                    data-testid={`verify-${key}`}
                  >
                    {isProcessing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5 mr-1" />}
                    {isContractRow ? 'Countersign' : 'Verify'}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => { e.stopPropagation(); handleReject(); }}
                    disabled={isProcessing}
                    className="h-8 text-xs text-red-600 border-red-200 hover:bg-red-50 rounded-lg"
                    data-testid={`reject-${key}`}
                  >
                    <XCircle className="h-3.5 w-3.5 mr-1" />
                    Reject
                  </Button>
                </>
              )}
              
              {/* Export PDF for completed */}
              {(isContractRow
                ? Boolean(contractArtifactUrl)
                : ((effectiveLifecycleStatus === 'submitted' || effectiveLifecycleStatus === 'verified') && (submission_data?.id || acknowledgement_data?.submission_id))) && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={(e) => { e.stopPropagation(); handleExportPDF(); }}
                  className="h-8 text-xs rounded-lg"
                  data-testid={`export-pdf-${key}`}
                >
                  <Download className="h-3.5 w-3.5" />
                </Button>
              )}
              
              {/* Unverify button for verified agreements (error correction) */}
              {effectiveLifecycleStatus === 'verified' && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={(e) => { e.stopPropagation(); handleUnverify(); }}
                  disabled={isProcessing}
                  className="h-8 text-xs text-amber-600 hover:text-amber-700 hover:bg-amber-50 rounded-lg"
                  data-testid={`unverify-${key}`}
                  title="Unverify agreement (for error correction)"
                >
                  {isProcessing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
                </Button>
              )}

              {effectiveLifecycleStatus === 'rejected' && key === 'handbook_acknowledgement' && acknowledgement_data?.id && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => { e.stopPropagation(); handleRegenerate(); }}
                  disabled={isProcessing}
                  className="h-8 text-xs rounded-lg"
                >
                  {isProcessing ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <RotateCcw className="h-3.5 w-3.5 mr-1" />}
                  Regenerate Handbook
                </Button>
              )}

            </>
          )}
          
          {/* History */}
          {onViewHistory && (
            <Button
              size="sm"
              variant="ghost"
              onClick={(e) => { e.stopPropagation(); onViewHistory(key, title); }}
              className="h-8 text-xs rounded-lg"
              data-testid={`history-${key}`}
            >
              <History className="h-3.5 w-3.5" />
            </Button>
          )}
          
          {/* Expand/Collapse */}
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            className="h-8 w-8 p-0"
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-gray-200/50">
          <div className="grid grid-cols-2 gap-4 text-sm">
            {/* Submission Details */}
            {(submission_data || acknowledgement_data) && (
              <>
                <div>
                  <p className="text-gray-500 text-xs">Completed</p>
                  <p className="text-gray-900">
                    {formatBackendDate(submission_data?.completed_at || acknowledgement_data?.completed_at, { format: 'medium' })}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs">Completion Mode</p>
                  <div className="flex items-center gap-1">
                    {modeConfig && <ModeIcon className="h-3.5 w-3.5 text-gray-500" />}
                    <p className="text-gray-900">{modeConfig?.label || 'Unknown'}</p>
                  </div>
                </div>
                {submission_data?.signature_name && (
                  <div>
                    <p className="text-gray-500 text-xs">Signed By</p>
                    <p className="text-gray-900 font-serif italic">{submission_data.signature_name}</p>
                  </div>
                )}
                {submission_data?.admin_note && (
                  <div className="col-span-2">
                    <p className="text-gray-500 text-xs">Admin Note</p>
                    <p className="text-gray-700 text-sm bg-blue-50 p-2 rounded">{submission_data.admin_note}</p>
                  </div>
                )}
              </>
            )}
            
            {/* Verification Details */}
            {effectiveLifecycleStatus === 'verified' && (
              <div className="col-span-2 p-3 bg-green-50 rounded-lg border border-green-200">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span className="font-medium text-green-800">Verified</span>
                </div>
                <p className="text-sm text-green-700 mt-1">
                  {formatBackendDate(submission_data?.verified_at || acknowledgement_data?.verified_at, { format: 'medium' })}
                  {(submission_data?.verified_by || acknowledgement_data?.verified_by) && 
                    ` by ${submission_data?.verified_by || acknowledgement_data?.verified_by}`}
                </p>
              </div>
            )}
            
            {/* Rejection Details */}
            {((effectiveLifecycleStatus === 'rejected' && !(key === 'contract_acceptance' && isAwaitingWorkerSignature)) || contractNeedsReissue) && (
              <div className="col-span-2 p-3 bg-red-50 rounded-lg border border-red-200">
                <div className="flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-red-600" />
                  <span className="font-medium text-red-800">
                    {key === 'contract_acceptance' ? 'Contract needs reissue' : 'Rejected / action required'}
                  </span>
                </div>
                <p className="text-sm text-red-700 mt-1">
                  {key === 'contract_acceptance'
                    ? 'Worker cannot sign this version.'
                    : (submission_data?.rejection_reason || acknowledgement_data?.rejection_reason || 'No reason provided')}
                </p>
              </div>
            )}
            
            {/* No submission yet */}
            {effectiveLifecycleStatus === 'not_sent' && (
              <div className="col-span-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-gray-500" />
                  <span className="font-medium text-gray-700">Missing</span>
                </div>
                <p className="text-sm text-gray-600 mt-1">
                  The {title} agreement has not been submitted.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}




