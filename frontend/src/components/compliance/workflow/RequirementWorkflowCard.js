import { useState, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../../context/AuthContext';
import { Card, CardContent } from '../../ui/card';
import { Badge } from '../../ui/badge';
import { Button } from '../../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../../ui/dialog';
import { toast } from 'sonner';
import {
  ChevronDown,
  ChevronUp,
  CheckCircle,
  Clock,
  AlertTriangle,
  XCircle,
  ShieldCheck,
} from 'lucide-react';
import { useComplianceWorkflow } from './useComplianceWorkflow';
import { EvidenceSection } from './EvidenceSection';
import { CheckSection } from './CheckSection';
import { ProofSection } from './ProofSection';
import { FinalStatusSection } from './FinalStatusSection';
import RecordCheckDialog from '../RecordCheckDialog';
import EvidenceReviewDialog from '../EvidenceReviewDialog';
import EvidenceReviewViewerDialog from '../EvidenceReviewViewerDialog';
import API_BASE from '../../../utils/apiBase';

const API = API_BASE;

// Map requirement key → check type string used by RecordCheckDialog
const REQUIREMENT_TO_CHECK_TYPE = {
  right_to_work: 'right_to_work_check',
  dbs: 'dbs_status_check',
  identity: 'identity_verification',
  proof_of_address: 'address_verification',
};

const STATUS_CONFIG = {
  verified: { icon: CheckCircle, color: 'emerald' },
  pending: { icon: Clock, color: 'amber' },
  incomplete: { icon: AlertTriangle, color: 'orange' },
  failed: { icon: XCircle, color: 'red' },
  overdue: { icon: AlertTriangle, color: 'red' },
  expired: { icon: AlertTriangle, color: 'red' },
  follow_up_overdue: { icon: AlertTriangle, color: 'amber' },
};

const COLOR_CLASSES = {
  emerald: {
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    header: 'border-emerald-200 bg-gradient-to-r from-emerald-50/60 to-white',
    iconBg: 'bg-emerald-100',
    iconText: 'text-emerald-600',
  },
  amber: {
    badge: 'bg-amber-100 text-amber-800 border-amber-200',
    header: 'border-amber-200 bg-gradient-to-r from-amber-50/40 to-white',
    iconBg: 'bg-amber-100',
    iconText: 'text-amber-600',
  },
  orange: {
    badge: 'bg-orange-100 text-orange-800 border-orange-200',
    header: 'border-orange-200 bg-gradient-to-r from-orange-50/40 to-white',
    iconBg: 'bg-orange-100',
    iconText: 'text-orange-600',
  },
  red: {
    badge: 'bg-red-100 text-red-800 border-red-200',
    header: 'border-red-200 bg-gradient-to-r from-red-50/40 to-white',
    iconBg: 'bg-red-100',
    iconText: 'text-red-600',
  },
};

/**
 * RequirementWorkflowCard
 *
 * Structured 5-step compliance workflow card for RTW, DBS, Identity, and PoA.
 *
 * Consumes raw section data from GET /api/employees/{id}/compliance-file
 * (serializer_version: dual_row_v1).  Does NOT call any backend endpoint
 * directly except for evidence accept/reject actions.  Check recording and
 * proof management are delegated to RecordCheckDialog and ProofSection.
 *
 * Props:
 *   requirementKey  'dbs' | 'right_to_work' | 'identity' | 'proof_of_address'
 *   sectionData     Raw section object from compliance-file API
 *   employeeId      string
 *   employeeName    string
 *   onRefresh       () => void  — called after any mutation
 *   isAdminView     bool (default true)
 *   onPreviewFile   (fileObj) => void
 *   onUploadEvidence () => void  — delegated to parent for upload drawer
 *   defaultOpen     bool (default true)
 */
export default function RequirementWorkflowCard({
  requirementKey,
  sectionData,
  employeeId,
  employeeName,
  onRefresh,
  isAdminView = true,
  onPreviewFile,
  onUploadEvidence,
  defaultOpen = true,
}) {
  const { token } = useAuth();
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [reviewDialog, setReviewDialog] = useState({ open: false, file: null });
  const [viewerDialog, setViewerDialog] = useState({ open: false, file: null });
  const [checkDialog, setCheckDialog] = useState({ open: false });
  const [invalidateDialog, setInvalidateDialog] = useState({ open: false, reason: '', loading: false });

  // Identity and PoA use the full evidence review viewer (verify mode)
  const isIdentityOrPOA = requirementKey === 'identity' || requirementKey === 'proof_of_address';
  // RTW and DBS use the evidence review viewer in accept-only mode
  const isRTWOrDBS = requirementKey === 'right_to_work' || requirementKey === 'dbs';
  const usesEvidenceViewer = isIdentityOrPOA || isRTWOrDBS;

  // ── Extract rows from section data ────────────────────────────────────
  const sectionRows = Array.isArray(sectionData?.rows) ? sectionData.rows : [];
  const evidenceRow = sectionRows.find((r) => r?.row_type === 'evidence');
  const checkRow = sectionRows.find((r) => r?.row_type === 'check');
  const evidenceFiles = evidenceRow?.documents_preview || [];
  const rawCheckRecord = checkRow?.check_data || null;
  const checkRecord = rawCheckRecord
    ? {
        ...rawCheckRecord,
        outcome:
          rawCheckRecord.outcome ||
          rawCheckRecord.status ||
          (checkRow?.is_verified ? 'verified' : undefined),
      }
    : checkRow?.has_check
      ? { outcome: checkRow?.is_verified ? 'verified' : 'pending' }
      : null;
  const sectionTitle = sectionData?.title || requirementKey;
  const checkType = REQUIREMENT_TO_CHECK_TYPE[requirementKey] || requirementKey;
  const rowUnavailable = Boolean(
    sectionData?.status_unavailable ||
    evidenceRow?.status_unavailable ||
    checkRow?.status_unavailable
  );

  // ── Derived workflow state ─────────────────────────────────────────────
  const workflow = useComplianceWorkflow({
    requirementKey,
    evidenceFiles,
    checkRecord,
    canonicalStatus: checkRow?.status || sectionData?.status || evidenceRow?.status || null,
    statusUnavailable: rowUnavailable,
    isAdminView,
  });
  const displaySteps = workflow.hasProofStep
    ? workflow.steps
    : workflow.steps.filter((step) => step.id !== 4);
  const canInvalidateCheck =
    !rowUnavailable && (requirementKey === 'right_to_work' || requirementKey === 'dbs');

  const handleRefresh = useCallback(() => {
    if (onRefresh) onRefresh();
  }, [onRefresh]);

  // ── Evidence actions (evidence layer only; never touch check or proof) ──
  const handleAcceptFile = async (docId, notes = '') => {
    try {
      await axios.post(
        `${API}/employee-documents/${docId}/verify`,
        { notes },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      toast.success('Evidence accepted');
      handleRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to accept evidence');
    }
  };

  const handleRejectFile = async (docId, reason) => {
    try {
      await axios.post(
        `${API}/employee-documents/${docId}/reject`,
        { reason },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      toast.success('Evidence rejected');
      handleRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject evidence');
    }
  };

  const handleRemoveFile = async (docId, reason) => {
    try {
      await axios.post(
        `${API}/employee-documents/${docId}/mark-uploaded-in-error`,
        { reason },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      toast.success('Document removed from active records');
      handleRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to remove document');
    }
  };

  const handleRequestReplacement = async (docId) => {
    try {
      await axios.post(
        `${API}/employee-documents/${docId}/request-replacement`,
        {},
        { headers: { Authorization: `Bearer ${token}` } },
      );
      toast.success('Replacement requested');
      handleRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to request replacement');
    }
  };

  // ── Check record actions ───────────────────────────────────────────────
  // "Edit Check" re-opens RecordCheckDialog prefilled (existing behaviour).
  // "Invalidate" opens a separate confirm+reason dialog that calls the invalidate endpoint.
  const handleInvalidateCheck = () => {
    setInvalidateDialog({ open: true, reason: '', loading: false });
  };

  const submitInvalidate = async () => {
    if (!canInvalidateCheck) {
      toast.error('Invalidate is not available for this requirement yet.');
      return;
    }
    if (!invalidateDialog.reason.trim()) {
      toast.error('Please provide a reason for invalidating this check.');
      return;
    }
    setInvalidateDialog((d) => ({ ...d, loading: true }));
    const isRTW = requirementKey === 'right_to_work';
    const url = isRTW
      ? `${API}/employees/${employeeId}/right-to-work/check/invalidate`
      : `${API}/employees/${employeeId}/dbs/check/invalidate`;
    try {
      await axios.post(url, { reason: invalidateDialog.reason }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Check record invalidated. Please re-record the check.');
      setInvalidateDialog({ open: false, reason: '', loading: false });
      handleRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to invalidate check');
      setInvalidateDialog((d) => ({ ...d, loading: false }));
    }
  };

  // ── Status display ─────────────────────────────────────────────────────
  const cfg = STATUS_CONFIG[workflow.finalStatus] || STATUS_CONFIG.pending;
  const StatusIcon = cfg.icon;
  const colors = COLOR_CLASSES[cfg.color] || COLOR_CLASSES.amber;

  return (
    <Card
      className={`overflow-hidden border ${colors.header}`}
      data-testid={`requirement-workflow-${requirementKey}`}
    >
      {/* ── Card header ──────────────────────────────────────────────── */}
      <div
        className={`flex items-center justify-between p-4 cursor-pointer ${colors.header}`}
        onClick={() => setIsOpen((o) => !o)}
      >
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <div
            className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${colors.iconBg}`}
          >
            <StatusIcon className={`h-5 w-5 ${colors.iconText}`} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-heading font-semibold text-text-primary text-sm">
                {sectionTitle}
              </h3>
              <Badge className={`text-[10px] px-1.5 py-0 border ${colors.badge}`}>
                {workflow.finalStatusLabel}
              </Badge>
              {workflow.finalStatus === 'verified' && (
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-500 opacity-80" />
              )}
            </div>
            {workflow.nextAction && isAdminView && (
              <p className="text-xs text-text-muted mt-0.5">
                Next: {workflow.nextAction.label}
              </p>
            )}
            {workflow.reviewDueAt && requirementKey === 'dbs' && (
              <p
                className={`text-xs mt-0.5 ${
                  workflow.isOverdue ? 'text-red-600 font-medium' : 'text-text-muted'
                }`}
              >
                Recheck due:{' '}
                {new Date(workflow.reviewDueAt).toLocaleDateString('en-GB')}
                {workflow.isOverdue && ' (OVERDUE)'}
              </p>
            )}
            {workflow.permissionEndDate &&
              requirementKey === 'right_to_work' &&
              !workflow.isIndefinite && (
                <p
                  className={`text-xs mt-0.5 ${
                    workflow.isExpired
                      ? 'text-red-600 font-medium'
                      : 'text-text-muted'
                  }`}
                >
                  Permission ends:{' '}
                  {new Date(workflow.permissionEndDate).toLocaleDateString(
                    'en-GB',
                  )}
                  {workflow.isExpired && ' (EXPIRED)'}
                </p>
              )}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Single primary CTA — only shown in collapsed header */}
          {workflow.nextAction && isAdminView && !isOpen && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              onClick={(e) => {
                e.stopPropagation();
                if (
                  workflow.nextAction.type === 'record_check' ||
                  workflow.nextAction.type === 'resolve_followup'
                ) {
                  setCheckDialog({ open: true });
                } else {
                  setIsOpen(true);
                }
              }}
              disabled={workflow.nextAction.disabled}
              data-testid={`${requirementKey}-primary-action-btn`}
            >
              {workflow.nextAction.label}
            </Button>
          )}
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            {isOpen ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* ── Step tracker ─────────────────────────────────────────────── */}
      {isOpen && workflow.hasCheckStage && (
        <div className="px-4 pt-3 pb-2 border-b border-gray-100 bg-white/80">
          <div className="flex items-center justify-between">
            {displaySteps.map((step, idx) => (
              <div key={step.id} className="flex items-center flex-1">
                <div className="flex flex-col items-center">
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-colors ${
                      step.complete
                        ? 'bg-emerald-500 text-white'
                        : step.active
                          ? 'bg-primary text-white ring-2 ring-primary/30'
                          : step.locked
                            ? 'bg-gray-100 text-gray-400'
                            : 'bg-gray-200 text-gray-500'
                    }`}
                    data-testid={`${requirementKey}-step-${step.id}`}
                  >
                    {step.complete ? (
                      <CheckCircle className="h-3.5 w-3.5" />
                    ) : (
                      step.id
                    )}
                  </div>
                  <span
                    className={`text-[9px] mt-1 font-medium ${
                      step.active
                        ? 'text-primary'
                        : step.complete
                          ? 'text-emerald-600'
                          : 'text-gray-400'
                    }`}
                  >
                    {step.label}
                    {step.optional && (
                      <span className="text-gray-400"> *</span>
                    )}
                  </span>
                </div>
                {/* Connector line */}
                {idx < displaySteps.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 mx-1 mb-4 rounded-full transition-colors ${
                      idx + 1 < workflow.currentStep || displaySteps[idx + 1].complete
                        ? 'bg-emerald-500'
                        : 'bg-gray-200'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Section content ───────────────────────────────────────────── */}
      {isOpen && (
        <CardContent className="p-0 divide-y divide-gray-100">
          {rowUnavailable && (
            <div className="p-4 bg-gray-50 text-sm text-gray-700" data-testid={`${requirementKey}-status-unavailable`}>
              Compliance status for this section is temporarily unavailable. Please refresh and try again.
            </div>
          )}
          {/* Steps 1 + 2: Evidence */}
          <EvidenceSection
            requirementKey={requirementKey}
            files={rowUnavailable ? [] : evidenceFiles}
            pendingRequests={evidenceRow?.pending_requests || []}
            counts={evidenceRow?.counts || {}}
            isAdminView={isAdminView}
            onAccept={rowUnavailable ? null : handleAcceptFile}
            onReject={rowUnavailable ? null : handleRejectFile}
            onRemove={rowUnavailable ? null : handleRemoveFile}
            onRequestReplacement={rowUnavailable ? null : handleRequestReplacement}
            onReviewFile={rowUnavailable ? null : ((file) => setReviewDialog({ open: true, file }))}
            onViewAndApprove={rowUnavailable ? null : (usesEvidenceViewer ? (file) => setViewerDialog({ open: true, file }) : null)}
            onPreviewFile={onPreviewFile}
            onUpload={rowUnavailable ? null : (onUploadEvidence || (() => {}))}
            workflow={workflow}
          />

          {/* Step 3: Check record */}
          {workflow.hasCheckStage && (
            <CheckSection
              requirementKey={requirementKey}
              checkRecord={rowUnavailable ? null : checkRecord}
              hasAcceptedEvidence={workflow.hasAcceptedEvidence}
              isAdminView={isAdminView}
              onRecordCheck={rowUnavailable ? null : (() => setCheckDialog({ open: true }))}
              onInvalidate={canInvalidateCheck ? handleInvalidateCheck : null}
            />
          )}

          {/* Step 4: Proof of check, where applicable */}
          {workflow.hasProofStep && (
            <ProofSection
              requirementKey={requirementKey}
              checkRecord={checkRecord}
              proofDocumentId={workflow.proofDocumentId}
              proofDocument={workflow.proofDocument}
              hasProof={workflow.hasProof}
              proofRequired={workflow.proofRequired}
              employeeId={employeeId}
              isAdminView={isAdminView}
              onProofChanged={handleRefresh}
              onPreviewFile={onPreviewFile}
            />
          )}

          {/* Step 5: Final status */}
          <FinalStatusSection
            workflow={workflow}
            requirementKey={requirementKey}
            checkRecord={rowUnavailable ? null : checkRecord}
            statusUnavailable={rowUnavailable}
          />
        </CardContent>
      )}

      {/* ── Dialogs ───────────────────────────────────────────────────── */}
      <EvidenceReviewDialog
        isOpen={reviewDialog.open}
        onClose={() => setReviewDialog({ open: false, file: null })}
        file={reviewDialog.file}
        employeeId={employeeId}
        requirementKey={requirementKey}
        requirementLabel={sectionTitle}
        onReviewComplete={() => {
          setReviewDialog({ open: false, file: null });
          handleRefresh();
        }}
        onPreviewFile={onPreviewFile}
      />

      {/* Full evidence review viewer for Identity/POA/RTW/DBS */}
      {usesEvidenceViewer && (
        <EvidenceReviewViewerDialog
          isOpen={viewerDialog.open}
          onClose={() => setViewerDialog({ open: false, file: null })}
          file={viewerDialog.file}
          employeeId={employeeId}
          employeeName={employeeName}
          requirementType={requirementKey}
          mode={isRTWOrDBS ? 'accept' : 'verify'}
          aiValidation={viewerDialog.file?.ai_extraction?.date_validation || null}
          onVerificationComplete={() => {
            setViewerDialog({ open: false, file: null });
            handleRefresh();
          }}
        />
      )}

      <RecordCheckDialog
        open={checkDialog.open}
        onClose={() => setCheckDialog({ open: false })}
        employeeId={employeeId}
        checkType={checkType}
        onComplete={() => {
          setCheckDialog({ open: false });
          handleRefresh();
        }}
        hasAcceptedEvidence={workflow.hasAcceptedEvidence}
        acceptedEvidenceCount={workflow.acceptedFiles.length}
      />

      {/* ── Invalidate check dialog ──────────────────────────────────── */}
      <Dialog
        open={invalidateDialog.open}
        onOpenChange={(open) => !invalidateDialog.loading && setInvalidateDialog((d) => ({ ...d, open }))}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-red-600">Invalidate Check Record</DialogTitle>
            <DialogDescription>
              This will mark the current {requirementKey === 'right_to_work' ? 'Right to Work' : 'DBS'} check
              as invalid. The check record will be preserved for audit purposes but compliance status will
              drop until a new check is recorded.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <label className="text-sm font-medium text-gray-700">Reason (required)</label>
            <textarea
              className="w-full border border-gray-300 rounded-md p-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-red-400"
              rows={3}
              placeholder="e.g. Document found to be fraudulent, worker left the organisation…"
              value={invalidateDialog.reason}
              onChange={(e) => setInvalidateDialog((d) => ({ ...d, reason: e.target.value }))}
              disabled={invalidateDialog.loading}
            />
          </div>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={invalidateDialog.loading}
              onClick={() => setInvalidateDialog({ open: false, reason: '', loading: false })}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              variant="destructive"
              disabled={invalidateDialog.loading || !invalidateDialog.reason.trim()}
              onClick={submitInvalidate}
            >
              {invalidateDialog.loading ? 'Invalidating…' : 'Confirm Invalidate'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

