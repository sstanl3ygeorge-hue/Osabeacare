import { useMemo } from 'react';

/**
 * useComplianceWorkflow
 *
 * Derives the complete workflow state for a single compliance requirement
 * from raw compliance-file API data. Pure computation — no side-effects,
 * no API calls.
 *
 * @param {Object} params
 * @param {string}  params.requirementKey  'dbs' | 'right_to_work' | 'identity' | 'proof_of_address'
 * @param {Array}   params.evidenceFiles   Active evidence files from the evidence row
 * @param {Object}  params.checkRecord     check_data from check row (or null)
 * @param {boolean} params.isAdminView     Whether rendered in admin context
 */
export function useComplianceWorkflow({
  requirementKey,
  evidenceFiles = [],
  checkRecord = null,
  isAdminView = true,
}) {
  return useMemo(() => {
    const isRTW = requirementKey === 'right_to_work';
    const isDBS = requirementKey === 'dbs';
    const isRTWOrDBS = isRTW || isDBS;
    const hasCheckStage = true;

    // ── Evidence analysis ──────────────────────────────────────────────────
    const hasEvidence = evidenceFiles.length > 0;
    const acceptedFiles = evidenceFiles.filter(
      (f) =>
        f.verified ||
        f.status === 'verified' ||
        f.status === 'accepted' ||
        f.status === 'approved',
    );
    const hasAcceptedEvidence = acceptedFiles.length > 0;
    const hasRejectedEvidence = evidenceFiles.some((f) => f.status === 'rejected');
    const allEvidenceReviewed =
      hasEvidence &&
      evidenceFiles.every(
        (f) =>
          f.verified ||
          f.status === 'verified' ||
          f.status === 'accepted' ||
          f.status === 'rejected' ||
          f.verification_stamp,
      );

    // ── Check record analysis ──────────────────────────────────────────────
    const hasCheck = !!checkRecord;
    const checkVerified = checkRecord?.outcome === 'verified';
    const checkFailed = checkRecord?.outcome === 'failed';

    // ── Proof analysis ─────────────────────────────────────────────────────
    // proof_document_id is the canonical field; evidence_document_id is the legacy alias.
    const proofDocumentId =
      checkRecord?.proof_document_id || checkRecord?.evidence_document_id || null;
    const proofDocument = checkRecord?.evidence_document || null;
    const hasProof = !!proofDocumentId;

    // ── DBS-specific date checks ───────────────────────────────────────────
    const reviewDueAt =
      checkRecord?.review_due_at || checkRecord?.next_recheck_date || null;
    const isOverdue = reviewDueAt ? new Date(reviewDueAt) < new Date() : false;

    // ── RTW-specific date checks ───────────────────────────────────────────
    const isIndefinite = checkRecord?.is_indefinite || false;
    const permissionEndDate = checkRecord?.permission_end_date || null;
    const followUpRequired = checkRecord?.follow_up_required || false;
    const followUpDueAt = checkRecord?.follow_up_due_at || null;
    const isExpired = permissionEndDate
      ? new Date(permissionEndDate) < new Date()
      : false;
    const followUpOverdue =
      followUpRequired && followUpDueAt
        ? new Date(followUpDueAt) < new Date()
        : false;

    // ── Proof requirement ──────────────────────────────────────────────────
    // RTW always requires proof.
    // DBS requires proof only for dbs_update_service_check; certificate review can use either.
    const isUpdateServiceCheck =
      checkRecord?.method === 'dbs_update_service_check';
    const proofRequired = isRTW || (isDBS && isUpdateServiceCheck);
    const hasProofStep = isRTWOrDBS && (proofRequired || hasProof);

    // ── Step computation ───────────────────────────────────────────────────
    let currentStep = 1;
    let stepLabel = 'Upload Evidence';

    if (!hasEvidence) {
      currentStep = 1;
      stepLabel = 'Upload Evidence';
    } else if (!hasAcceptedEvidence) {
      currentStep = 2;
      stepLabel = 'Review Evidence';
    } else if (!hasCheck) {
      currentStep = 3;
      stepLabel = 'Record Check';
    } else if (hasProofStep && !hasProof) {
      currentStep = 4;
      stepLabel = proofRequired
        ? 'Upload Proof of Check'
        : 'Upload Proof (Recommended)';
    } else {
      currentStep = 5;
      stepLabel = 'Final Status';
    }

    // ── Final status (computed, never manual) ─────────────────────────────
    let finalStatus = 'pending';
    let finalStatusLabel = 'Pending';

    if (!hasEvidence) {
      finalStatus = 'pending';
      finalStatusLabel = 'Missing';
    } else if (!hasAcceptedEvidence && hasRejectedEvidence) {
      finalStatus = 'failed';
      finalStatusLabel = 'Rejected / action required';
    } else if (!hasAcceptedEvidence) {
      finalStatus = 'pending';
      finalStatusLabel = 'Awaiting admin review';
    } else if (!hasCheck) {
      finalStatus = 'pending';
      finalStatusLabel = 'Evidence accepted - check required';
    } else if (checkFailed) {
      finalStatus = 'failed';
      finalStatusLabel = 'Rejected / action required';
    } else if (!checkVerified) {
      finalStatus = 'pending';
      finalStatusLabel = 'Awaiting admin review';
    } else if (proofRequired && !hasProof) {
      // SAFEGUARD: verified check + no proof → show incomplete, not verified
      finalStatus = 'incomplete';
      finalStatusLabel = 'Cannot assess - proof missing';
    } else if (isDBS && isOverdue) {
      finalStatus = 'overdue';
      finalStatusLabel = 'Overdue – Recheck Required';
    } else if (isRTW && isExpired) {
      finalStatus = 'expired';
      finalStatusLabel = 'Expired';
    } else if (isRTW && followUpOverdue) {
      finalStatus = 'follow_up_overdue';
      finalStatusLabel = 'Follow-up Overdue';
    } else if (checkVerified && (hasProof || !proofRequired)) {
      finalStatus = 'verified';
      finalStatusLabel = 'Check complete';
    }

    // ── Safeguard flags (used to show warning callouts in FinalStatusSection) ──
    const safeguards = {
      // A check record exists but evidence was removed → never show verified
      noEvidenceButCheckExists: !hasEvidence && hasCheck,
      // Check is verified but required proof is absent → show incomplete
      proofMissingButCheckVerified: checkVerified && proofRequired && !hasProof,
    };

    // ── Primary action (single CTA computed for header) ───────────────────
    let nextAction = null;
    if (!hasEvidence) {
      nextAction = { label: 'Upload Evidence', type: 'upload_evidence' };
    } else if (!hasAcceptedEvidence && isAdminView) {
      nextAction = { label: 'Review Evidence', type: 'review_evidence' };
    } else if (!hasCheck && isAdminView) {
      nextAction = {
        label: 'Record Check',
        type: 'record_check',
        disabled: !hasAcceptedEvidence,
      };
    } else if (hasProofStep && proofRequired && !hasProof && isAdminView) {
      nextAction = { label: 'Upload Proof', type: 'upload_proof' };
    } else if (isRTW && followUpOverdue && isAdminView) {
      nextAction = { label: 'Resolve Follow-up', type: 'resolve_followup' };
    } else if (isDBS && isOverdue && isAdminView) {
      nextAction = { label: 'Record Recheck', type: 'record_check' };
    }

    // ── Step definitions for visual tracker ───────────────────────────────
    const steps = [
      {
        id: 1,
        label: 'Evidence',
        complete: hasEvidence,
        active: currentStep === 1,
        locked: false,
        optional: false,
      },
      {
        id: 2,
        label: 'Review',
        complete: hasAcceptedEvidence,
        active: currentStep === 2,
        locked: !hasEvidence,
        optional: false,
      },
      {
        id: 3,
        label: 'Check',
        complete: hasCheck && checkVerified,
        active: currentStep === 3,
        locked: !hasAcceptedEvidence,
        optional: false,
      },
      {
        id: 4,
        label: 'Proof',
        complete: hasProof,
        active: currentStep === 4,
        locked: !hasCheck,
        optional: !proofRequired,
      },
      {
        id: 5,
        label: 'Status',
        complete: finalStatus === 'verified',
        active: currentStep === 5,
        locked: false,
        optional: false,
      },
    ];

    return {
      // Step tracking
      currentStep,
      stepLabel,
      steps,
      isRTWOrDBS,
      hasCheckStage,
      hasProofStep,
      isRTW,
      isDBS,
      // Evidence state
      hasEvidence,
      hasAcceptedEvidence,
      hasRejectedEvidence,
      allEvidenceReviewed,
      acceptedFiles,
      // Check state
      hasCheck,
      checkVerified,
      checkFailed,
      // Proof state
      proofDocumentId,
      proofDocument,
      hasProof,
      proofRequired,
      // Date state
      reviewDueAt,
      isOverdue,
      permissionEndDate,
      isIndefinite,
      isExpired,
      followUpDueAt,
      followUpOverdue,
      // Computed status
      finalStatus,
      finalStatusLabel,
      // Primary CTA
      nextAction,
      // Safeguard flags
      safeguards,
    };
  }, [requirementKey, evidenceFiles, checkRecord, isAdminView]);
}
