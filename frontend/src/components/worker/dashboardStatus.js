import { resolveLatestContractState } from '../../lib/contractState';

export function getAgreementDisplay(agreement, options = {}) {
  const contractEligibility = options.contractEligibility || null;
  const canonicalStatus = String(agreement?.status || '').toLowerCase();
  const rawStatus = String(agreement?.raw_status || '').toLowerCase();
  const latestActive = agreement?.latest_active !== false;
  const canonicalCanSign = agreement?.can_sign;
  const canonicalCanAcknowledge = agreement?.can_acknowledge;
  const truncateMessage = (value, max = 160) => {
    const text = String(value || '').trim();
    if (!text) return '';
    if (text.length <= max) return text;
    return `${text.slice(0, max - 1).trimEnd()}…`;
  };
  if (!agreement) {
    return {
      tone: 'neutral',
      badge: 'Not started',
      title: 'Agreement not ready',
      description: 'Osabea will prepare this agreement for you when it is needed.',
      workerActionable: false,
      ctaLabel: null,
    };
  }

  if (
    canonicalStatus === 'fully_executed' ||
    canonicalStatus === 'verified' ||
    canonicalStatus === 'completed' ||
    canonicalStatus === 'signed' ||
    agreement.verified
  ) {
    return {
      tone: 'success',
      badge: agreement.id === 'contract_acceptance' ? 'Fully executed' : 'Verified',
      title: agreement.state_label || (agreement.id === 'contract_acceptance' ? 'Contract complete' : 'Handbook complete'),
      description:
        agreement.id === 'contract_acceptance'
          ? 'Your signed contract is complete and available to view.'
          : 'Your handbook acknowledgement has been recorded and verified.',
      workerActionable: false,
      ctaLabel: agreement.file_url || agreement.download_url ? 'View PDF' : null,
    };
  }

  if (
    agreement.id === 'contract_acceptance' &&
    (
      canonicalStatus === 'awaiting_company_countersignature' ||
      rawStatus === 'awaiting_company_countersignature' ||
      agreement.contract_state === 'awaiting_company_countersignature'
    )
  ) {
    return {
      tone: 'info',
      badge: 'With Osabea',
      title: 'Signed by you',
      description: 'Your contract is with Osabea for the final countersignature.',
      workerActionable: false,
      ctaLabel: agreement.file_url || agreement.download_url ? 'View PDF' : null,
    };
  }

  if (agreement.id === 'contract_acceptance') {
    const contractResolution = resolveLatestContractState(agreement, options);
    const contractState = contractResolution.status;
    const hasWorkerSigned =
      agreement.worker_signed ||
      agreement.signed ||
      Boolean(agreement.worker_signed_at || agreement.signed_at);
    const canSign = typeof canonicalCanSign === 'boolean' ? canonicalCanSign : contractResolution.canSign;
    if (hasWorkerSigned && contractState !== 'fully_executed') {
      return {
        tone: 'info',
        badge: 'With Osabea',
        title: 'Signed by you',
        description: 'Your contract is with Osabea for the final countersignature.',
        workerActionable: false,
        ctaLabel: agreement.file_url || agreement.download_url ? 'View PDF' : null,
      };
    }
    const hasPendingSignableContract = contractResolution.hasPendingSignableContract;
    if (canSign && hasPendingSignableContract) {
      return {
        tone: 'critical',
        badge: 'Ready to sign',
        title: 'Contract signature needed',
        description: 'Review the contract PDF, then add your signature.',
        workerActionable: true,
        ctaLabel: 'Review & sign contract',
      };
    }
    if (latestActive && ['rejected', 'rejected_reopen_required', 'superseded', 'action_required'].includes(contractState) && !canSign) {
      return {
        tone: 'neutral',
        badge: 'Historical',
        title: 'Contract needs reissue',
        description: 'Your contract needs to be reissued by your manager.',
        workerActionable: false,
        ctaLabel: agreement.file_url || agreement.download_url ? 'View PDF' : null,
      };
    }
    return {
      tone: canSign ? 'critical' : 'info',
      badge: canSign ? 'Ready to sign' : 'Locked',
      title: canSign ? 'Contract signature needed' : 'Contract unlocks after earlier steps',
      description: truncateMessage(canSign
        ? 'Review the contract PDF, then add your signature.'
        : 'Complete your earlier onboarding steps and Osabea will unlock contract signing.'),
      workerActionable: Boolean(canSign),
      ctaLabel: canSign ? 'Review and sign' : agreement.file_url || agreement.download_url ? 'View PDF' : null,
    };
  }

  if (agreement.rejected) {
    return {
      tone: 'critical',
      badge: 'Action required',
      title: agreement.id === 'contract_acceptance' ? 'Contract needs attention' : 'Handbook needs attention',
      description: agreement.rejection_reason || 'Osabea has returned this item for you to review.',
      workerActionable: true,
      ctaLabel: agreement.id === 'contract_acceptance' ? 'Review contract' : 'Review handbook',
    };
  }

  if (agreement.id === 'handbook_acknowledgement') {
    if (agreement.system_issue) {
      return {
        tone: 'info',
        badge: 'With Osabea',
        title: 'Employee Handbook',
        description: 'Your handbook is being prepared.',
        workerActionable: false,
        ctaLabel: null,
      };
    }

    if (
      canonicalStatus === 'acknowledged' ||
      canonicalStatus === 'verified' ||
      canonicalStatus === 'completed' ||
      canonicalStatus === 'signed' ||
      agreement.signed ||
      agreement.verified
    ) {
      return {
        tone: 'success',
        badge: 'Completed',
        title: 'Employee Handbook',
        description: 'Completed',
        workerActionable: false,
        ctaLabel: agreement.file_url || agreement.download_url ? 'View handbook' : null,
      };
    }

    return {
      tone: 'critical',
      badge: 'Action required',
      title: 'Employee Handbook',
      description: 'Review and acknowledge your handbook.',
      workerActionable: typeof canonicalCanAcknowledge === 'boolean' ? canonicalCanAcknowledge : true,
      ctaLabel: 'Acknowledge handbook',
    };
  }

  return {
    tone: 'neutral',
    badge: 'Pending',
    title: agreement.state_label || 'Pending',
    description: 'Osabea will let you know when this agreement is ready.',
    workerActionable: false,
    ctaLabel: null,
  };
}

export function getCvDisplay(cvStatus) {
  if (!cvStatus) {
    return {
      tone: 'neutral',
      badge: 'Loading',
      title: 'CV status',
      description: 'Checking your CV status…',
      hasCv: false,
      canUpload: false,
      primaryLabel: null,
      secondaryLabel: null,
    };
  }

  if (cvStatus.has_cv) {
    const waitingReview = cvStatus.cv_status === 'uploaded' || cvStatus.extraction_status === 'awaiting_admin_review';
    // Admin may have requested a replacement while the existing CV is still
    // on file as historical evidence. Surface that state alongside the
    // "CV on file" confirmation so the worker knows an updated CV is needed.
    if (cvStatus.replacement_required) {
      return {
        tone: 'warning',
        badge: 'Replacement requested',
        title: 'CV on file — replacement requested',
        description: 'Your existing CV is on file. Admin has requested an updated CV; upload a new PDF to replace it.',
        hasCv: true,
        canUpload: true,
        primaryLabel: 'View CV',
        secondaryLabel: 'Upload replacement CV',
      };
    }
    return {
      tone: waitingReview ? 'info' : 'success',
      badge: waitingReview ? 'On file' : 'Verified',
      title: 'CV on file',
      description: waitingReview
        ? 'Your CV has been uploaded and is available for admin review.'
        : 'Your CV is on file and complete.',
      hasCv: true,
      canUpload: true,
      primaryLabel: 'View CV',
      secondaryLabel: 'Replace CV',
    };
  }

  return {
    tone: 'critical',
    badge: cvStatus.replacement_required ? 'Replace CV' : 'Missing',
    title: 'CV needed',
    description:
      cvStatus.extraction_status === 'no_cv_uploaded'
        ? 'Upload your CV so Osabea can build your employment history.'
        : 'Your previous CV needs to be replaced with an updated PDF.',
    hasCv: false,
    canUpload: Boolean(cvStatus.can_upload_cv),
    primaryLabel: 'Upload CV',
    secondaryLabel: null,
  };
}

export function getTrainingDisplay({ missingTrainings = [], expiredTrainings = [], allMandatoryTrainings = [] }) {
  if (expiredTrainings.length > 0) {
    return {
      tone: 'critical',
      badge: 'Expired training',
      title: 'Training renewal needed',
      description: `${expiredTrainings.length} training item${expiredTrainings.length === 1 ? '' : 's'} must be renewed.`,
      actionable: true,
    };
  }

  if (missingTrainings.length > 0) {
    return {
      tone: 'critical',
      badge: 'Missing training',
      title: 'Training evidence needed',
      description: `${missingTrainings.length} training item${missingTrainings.length === 1 ? '' : 's'} still need evidence.`,
      actionable: true,
    };
  }

  const completedCount = (allMandatoryTrainings || []).filter((item) => ['verified', 'due_soon'].includes(item.status)).length;
  return {
    tone: 'success',
    badge: 'Training complete',
    title: 'Mandatory training complete',
    description: `${completedCount} required training item${completedCount === 1 ? '' : 's'} are current.`,
    actionable: false,
  };
}

export function getNextAction(status) {
  const cv = status.cv || null;
  const contract = status.contract || null;
  const handbook = status.handbook || null;
  const induction = status.induction || null;
  const missingDocuments = status.missingDocuments || [];
  const missingTrainings = status.missingTrainings || [];
  const expiredTrainings = status.expiredTrainings || [];
  const referencesNeedAction = Boolean(status.referencesNeedAction);
  const gapsNeedAction = Boolean(status.gapsNeedAction);

  if (cv && !cv.hasCv && cv.canUpload) {
    return {
      key: 'missing_cv',
      title: 'Upload your CV',
      description: 'Your CV is the next step because it unlocks employment history review.',
      primaryLabel: 'Upload CV',
      route: '#documents-cv',
      level: 'critical',
    };
  }

  if (contract && !contract.verified && contract.workerActionable) {
    return {
      key: 'contract',
      title: 'Review and sign your contract',
      description: contract.description,
      primaryLabel: 'Review contract',
      route: '#agreements-contract',
      level: 'critical',
    };
  }

  if (handbook && !handbook.verified && handbook.workerActionable) {
    return {
      key: 'handbook',
      title: 'Read and acknowledge the handbook',
      description: handbook.description,
      primaryLabel: 'Open handbook',
      route: '#agreements-handbook',
      level: 'critical',
    };
  }

  if (induction && induction.state === 'worker_action_required') {
    return {
      key: 'induction',
      title: induction.title || 'Complete your induction item',
      description: induction.description || 'Your induction checklist has a self-assessment to complete.',
      primaryLabel: induction.primaryLabel || 'Open induction',
      route: '#induction',
      level: 'high',
    };
  }

  if (induction && induction.state === 'awaiting_manager_signoff') {
    return {
      key: 'induction_waiting_signoff',
      title: induction.title || 'Induction awaiting manager sign-off',
      description: induction.description || 'Your submitted induction form is waiting for manager review.',
      primaryLabel: induction.primaryLabel || 'View induction',
      route: '#induction',
      level: 'medium',
    };
  }

  if (missingDocuments.length > 0) {
    return {
      key: 'documents',
      title: 'Upload your remaining documents',
      description: `${missingDocuments.length} document${missingDocuments.length === 1 ? '' : 's'} still need to be uploaded or replaced.`,
      primaryLabel: 'Open documents',
      route: '#documents',
      level: 'high',
    };
  }

  if (missingTrainings.length > 0 || expiredTrainings.length > 0) {
    const total = missingTrainings.length + expiredTrainings.length;
    return {
      key: 'training',
      title: 'Update your training evidence',
      description: `${total} training item${total === 1 ? '' : 's'} still need attention.`,
      primaryLabel: 'Open training',
      route: '#training',
      level: 'high',
    };
  }

  if (referencesNeedAction || gapsNeedAction) {
    return {
      key: 'checks',
      title: 'Finish your remaining checks',
      description: 'Osabea still needs your references and employment history checks to close cleanly.',
      primaryLabel: 'Open checks',
      route: '#checks',
      level: 'medium',
    };
  }

  return {
    key: 'ready',
    title: 'You are ready for work',
    description: 'Everything required from you is complete.',
    primaryLabel: 'Review dashboard',
    route: '#ready',
    level: 'success',
  };
}
