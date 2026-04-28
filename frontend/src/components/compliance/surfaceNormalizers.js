/**
 * Compliance Surface Normalizers
 * 
 * Transforms raw backend data into normalized UI surfaces.
 * All UI rendering should use these normalized surfaces, not raw API data.
 */

import {
  getEvidenceRules,
  isActiveEvidenceFile,
  isHistoricalEvidenceFile,
  hasValidPoADate,
} from './evidenceRules';

// ============================================================================
// UPLOAD REQUIREMENT SURFACE
// ============================================================================

const UPLOAD_LABELS = {
  right_to_work: 'Right to Work',
  dbs: 'DBS Certificate',
  identity: 'Identity',
  proof_of_address: 'Proof of Address'
};

function getUploadRules(requirementKey) {
  return getEvidenceRules(requirementKey);
}

/**
 * Convert method enum values to human-friendly labels
 */
const METHOD_LABELS = {
  // RTW Methods
  'home_office_online_check': 'Home Office Online Check',
  'manual_passport_uk_irish': 'Manual Check - UK/Irish Passport',
  'manual_list_a_document': 'Manual Check - List A Document',
  'manual_list_a_check': 'Manual List A Check',
  'manual_list_b_group_1': 'Manual Check - List B Group 1',
  'manual_list_b_group_1_check': 'Manual List B Group 1 Check',
  'manual_list_b_group_2_ecs': 'Manual Check - List B Group 2 / ECS',
  'manual_list_b_group_2_check': 'Manual List B Group 2 Check',
  'idsp_check': 'Digital Verification Service (IDSP)',
  'digital_verification_service_check': 'Digital Verification Service',
  'ecs_pvn_check': 'Employer Checking Service (PVN)',
  'ecs_check': 'Employer Checking Service',
  // DBS Methods
  'update_service_check': 'DBS Update Service Check',
  'dbs_update_service_check': 'DBS Update Service Check',
  'dbs_certificate_review': 'DBS Certificate Review',
  'manual_certificate_review': 'Manual Certificate Review',
  // Other Methods
  'share_code_online_check': 'Share Code Online Check',
  'manual_passport_check': 'Manual Passport Check',
  'manual_id_verification': 'Manual ID Verification',
  'digital_id_check': 'Digital ID Check',
  'manual_document_check': 'Manual Document Check',
  'original_document_seen': 'Original Document Seen',
  'certified_copy_verified': 'Certified Copy Verified',
  'digital_id_verification': 'Digital ID Verification'
};

function getMethodDisplayLabel(method) {
  if (!method) return '';
  return METHOD_LABELS[method] || method.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Derive request lifecycle state from latest request
 */
function deriveRequestState(latestRequest) {
  if (!latestRequest) return 'not_requested';
  
  const status = latestRequest.status;
  
  if (status === 'completed' || latestRequest.submitted_at) {
    return 'submitted';
  }
  if (status === 'clicked' || latestRequest.viewed_at) {
    return 'viewed';
  }
  if (status === 'sent' || latestRequest.sent_at) {
    return 'requested';
  }
  if (latestRequest.is_replacement) {
    return 'replacement_requested';
  }
  
  return 'not_requested';
}

/**
 * Derive row status from files, request, and check state
 */
function deriveUploadRowStatus({
  activeFiles,
  latestRequest,
  authoritativeCheck,
  requirementKey,
  activeCountOverride,
  validFreshOverride,
}) {
  const rules = getUploadRules(requirementKey);
  const minRequired = rules.min_required_files || 1;
  
  // Check decides readiness
  if (authoritativeCheck?.status === 'verified') {
    return 'verified';
  }
  
  if (authoritativeCheck?.status === 'rejected') {
    return 'rejected';
  }
  
  // Files state
  const activeCount = typeof activeCountOverride === 'number' ? activeCountOverride : activeFiles.length;
  const effectiveCount = (requirementKey === 'proof_of_address' && rules.file_recency_required)
    ? (typeof validFreshOverride === 'number' ? validFreshOverride : activeFiles.filter(f => hasValidPoADate(f, rules.recency_months || 12)).length)
    : activeCount;
  // A file is pending review only if it's NOT verified by any indicator
  const pendingReview = activeFiles.filter(f => 
    !f.verified && 
    f.status !== 'verified' && 
    !f.verification_stamp &&
    (f.extraction_status?.status === 'awaiting_review' || f.status === 'active' || f.status === 'uploaded')
  ).length;
  
  if (pendingReview > 0) {
    return 'awaiting_review';
  }
  
  if (effectiveCount < minRequired) {
    const requestState = deriveRequestState(latestRequest);
    if (requestState === 'requested' || requestState === 'viewed') {
      return 'awaiting_submission';
    }
    if (requestState === 'submitted') {
      return 'awaiting_review';
    }
    if (requestState === 'replacement_requested') {
      return 'replacement_required';
    }
    return 'missing';
  }
  
  return 'awaiting_review';
}

/**
 * Build summary text for upload requirement
 */
function buildUploadSummary({ requirementKey, activeFiles, historicalFiles, latestRequest, authoritativeCheck }) {
  const parts = [];
  const rules = getUploadRules(requirementKey);
  const minRequired = rules.min_required_files || 1;
  const requestState = deriveRequestState(latestRequest);
  
  const activeCount = activeFiles.length;
  const validCount = (requirementKey === 'proof_of_address' && rules.file_recency_required)
    ? activeFiles.filter(f => hasValidPoADate(f, rules.recency_months || 12)).length
    : activeCount;
  const verifiedCount = activeFiles.filter(f => f.verified || f.status === 'verified' || f.verification_stamp).length;
  // A file is pending review only if it's NOT verified by any indicator
  const pendingReview = activeFiles.filter(f => 
    !f.verified && 
    f.status !== 'verified' && 
    !f.verification_stamp &&
    (f.extraction_status?.status === 'awaiting_review' || f.status === 'active' || f.status === 'uploaded')
  ).length;
  
  // Check status (authoritative)
  if (authoritativeCheck?.status === 'verified') {
    parts.push('Verified');
    if (authoritativeCheck.method) {
      // Use human-friendly label instead of raw enum value
      parts.push(getMethodDisplayLabel(authoritativeCheck.method));
    }
    if (authoritativeCheck.follow_up_date) {
      parts.push(`follow-up ${new Date(authoritativeCheck.follow_up_date).toLocaleDateString()}`);
    }
    return parts.join(' • ');
  }
  
  // File counts
  if (activeCount === 0) {
    if (requestState === 'submitted') {
      return 'Submitted • awaiting review';
    }
    if (requestState === 'viewed') {
      return 'Request viewed • awaiting upload';
    }
    if (requestState === 'requested') {
      return 'Requested • awaiting upload';
    }
    if (requestState === 'replacement_requested') {
      return 'Replacement requested';
    }
    if (minRequired > 1) {
      return `No files • ${minRequired} needed`;
    }
    return 'No files uploaded';
  }
  
  // Multi-file special handling
  if (minRequired > 1) {
    if (validCount < minRequired) {
      parts.push(`${validCount}/${minRequired} valid`);
      parts.push(`${Math.max(0, minRequired - validCount)} more needed`);
    } else {
      if (verifiedCount > 0) {
        parts.push(`${verifiedCount}/${activeCount} accepted`);
      } else {
        parts.push(`${activeCount} files`);
      }
      if (pendingReview > 0) {
        parts.push(`${pendingReview} awaiting review`);
      }
    }
  } else {
    // Single file requirement
    if (verifiedCount > 0) {
      parts.push(`${verifiedCount} accepted`);
    } else {
      parts.push(`${activeCount} file${activeCount !== 1 ? 's' : ''}`);
    }
    if (pendingReview > 0) {
      parts.push(`${pendingReview} awaiting review`);
    }
  }
  
  // Historical
  if (historicalFiles.length > 0 && parts.length < 3) {
    parts.push(`${historicalFiles.length} historical`);
  }
  
  return parts.join(' • ') || 'No files';
}

/**
 * Normalize upload requirement data into a UI surface
 */
export function normalizeUploadRequirementSurface({
  requirementKey,
  files = [],
  requests = [],
  checks = [],
  freshness = null,  // PoA freshness data
  serverCounts = null,
}) {
  const rules = getUploadRules(requirementKey);
  const activeFiles = files.filter(isActiveEvidenceFile);
  const historicalFiles = files.filter(isHistoricalEvidenceFile);
  
  // Sort requests by date descending
  const sortedRequests = [...requests].sort((a, b) => 
    new Date(b.sent_at || b.created_at || 0).getTime() - new Date(a.sent_at || a.created_at || 0).getTime()
  );
  const latestRequest = sortedRequests[0] || null;
  
  // Sort checks by date descending
  const sortedChecks = [...checks].sort((a, b) => 
    new Date(b.updated_at || b.checked_at || 0).getTime() - new Date(a.updated_at || a.checked_at || 0).getTime()
  );
  const authoritativeCheck = sortedChecks[0] || null;
  
  const requestState = deriveRequestState(latestRequest);
  const activeCountOverride = typeof serverCounts?.active_files === 'number' ? serverCounts.active_files : undefined;
  const validFreshOverride = requirementKey === 'proof_of_address'
    ? (freshness?.valid_count ?? undefined)
    : undefined;
  const rowStatus = deriveUploadRowStatus({
    activeFiles,
    latestRequest,
    authoritativeCheck,
    requirementKey,
    activeCountOverride,
    validFreshOverride,
  });
  
  // Build counters
  const counters = {
    active: typeof activeCountOverride === 'number' ? activeCountOverride : activeFiles.length,
    pendingReview: activeFiles.filter(f => 
      !f.verified && 
      isActiveEvidenceFile(f) &&
      (f.extraction_status?.status === 'awaiting_review' || 
       f.status === 'active' || 
       f.status === 'uploaded' ||
       f.status === 'pending_review' ||
       f.status === 'under_review' ||
       !f.status)
    ).length,
    verified: activeFiles.filter(f => f.verified || f.status === 'approved' || f.status === 'verified').length,
    superseded: historicalFiles.filter(f => f.status === 'superseded').length,
    rejected: historicalFiles.filter(f => f.status === 'rejected').length,
    uploadedInError: historicalFiles.filter(f => f.status === 'uploaded_in_error').length,
    historical: typeof serverCounts?.history === 'number'
      ? Math.max(0, serverCounts.history - (typeof activeCountOverride === 'number' ? activeCountOverride : activeFiles.length))
      : historicalFiles.length
  };
  
  // Add PoA freshness counters
  if (requirementKey === 'proof_of_address' && freshness) {
    counters.validFresh = freshness.valid_count || 0;
    counters.expired = freshness.expired_count || 0;
    counters.dateUnclear = freshness.unclear_count || 0;
    counters.freshnessRequired = freshness.required_count || (rules.min_required_files || 2);
    counters.freshnessComplete = freshness.is_complete || false;
  } else if (requirementKey === 'proof_of_address') {
    // Derive from file-level freshness data if no aggregate provided
    counters.validFresh = activeFiles.filter(f => f.freshness_is_valid).length;
    counters.expired = activeFiles.filter(f => f.freshness_status === 'expired').length;
    counters.dateUnclear = activeFiles.filter(f => f.freshness_status === 'date_unclear').length;
    counters.freshnessRequired = rules.min_required_files || 2;
    counters.freshnessComplete = counters.validFresh >= (rules.min_required_files || 2);
  }
  
  // Build summary with freshness for PoA
  let summary = buildUploadSummary({
    requirementKey,
    activeFiles,
    historicalFiles,
    latestRequest,
    authoritativeCheck
  });
  
  // Enhance summary for PoA with freshness
  if (requirementKey === 'proof_of_address' && (counters.expired > 0 || counters.dateUnclear > 0)) {
    const parts = [];
    if (counters.validFresh > 0) {
      parts.push(`${counters.validFresh}/${counters.freshnessRequired} valid`);
    }
    if (counters.expired > 0) {
      parts.push(`${counters.expired} expired`);
    }
    if (counters.dateUnclear > 0) {
      parts.push(`${counters.dateUnclear} need date review`);
    }
    if (parts.length > 0) {
      summary = parts.join(' • ');
    }
  }
  
  return {
    key: requirementKey,
    label: UPLOAD_LABELS[requirementKey] || requirementKey,
    activeFiles,
    historicalFiles,
    requests: sortedRequests,
    latestRequest,
    checks: sortedChecks,
    authoritativeCheck,
    summary,
    counters,
    requestState,
    rowStatus,
    rules,
    freshness: requirementKey === 'proof_of_address' ? {
      validCount: counters.validFresh,
      expiredCount: counters.expired,
      unclearCount: counters.dateUnclear,
      requiredCount: counters.freshnessRequired,
      isComplete: counters.freshnessComplete,
      freshnessMonths: 12
    } : null
  };
}

// ============================================================================
// REFERENCE REQUIREMENT SURFACE
// ============================================================================

/**
 * Normalize reference data into UI surface
 */
export function normalizeReferenceItemSurface(referenceData, referenceNum) {
  const prefix = `reference_${referenceNum}_`;
  
  // Extract declared referee
  const declaredReferee = {
    name: referenceData[`${prefix}name`] || null,
    company: referenceData[`${prefix}company`] || null,
    email: referenceData[`${prefix}email`] || null,
    phone: referenceData[`${prefix}phone`] || null,
    jobTitle: referenceData[`${prefix}job_title`] || null,
    relationship: referenceData[`${prefix}relationship`] || null
  };
  
  // Request state
  const requestStatus = referenceData[`${prefix}request_status`];
  const requestSentAt = referenceData[`${prefix}request_sent_at`];
  
  // Response
  const responseData = referenceData[`${prefix}response_data`] || {};
  const responseReceivedAt = referenceData[`${prefix}response_received_at`];
  const hasResponse = !!responseReceivedAt && Object.keys(responseData).length > 0;
  
  // Integrity
  const mismatchDetected = referenceData[`${prefix}mismatch_detected`] || false;
  const mismatchNotes = referenceData[`${prefix}mismatch_notes`] || null;
  
  // Verification
  const verified = referenceData[`${prefix}verified`] || false;
  const verifiedAt = referenceData[`${prefix}verified_at`];
  const verifiedBy = referenceData[`${prefix}verified_by`];
  
  // Derive request status
  let request = {
    status: 'not_sent',
    sentAt: requestSentAt || null,
    viewedAt: null,
    respondedAt: responseReceivedAt || null,
    resentCount: 0,
    recipientEmail: declaredReferee.email
  };
  
  if (hasResponse) {
    request.status = 'responded';
  } else if (requestStatus === 'awaiting_response' || requestSentAt) {
    request.status = 'sent';
  }
  
  // Build summary
  let summary = '';
  if (verified) {
    summary = `Verified • ${declaredReferee.company || 'Referee'}`;
  } else if (hasResponse) {
    summary = mismatchDetected 
      ? 'Response received • identity mismatch • awaiting review'
      : 'Response received • awaiting review';
  } else if (request.status === 'sent') {
    summary = 'Request sent • awaiting response';
  } else if (declaredReferee.name) {
    summary = 'Referee declared • not yet requested';
  } else {
    summary = 'Referee not declared';
  }
  
  return {
    id: `reference_${referenceNum}`,
    label: `Reference ${referenceNum}`,
    declaredReferee,
    request,
    response: {
      exists: hasResponse,
      submittedAt: responseReceivedAt,
      responderName: responseData.referee_full_name || null,
      responderEmail: responseData.referee_work_email || null,
      responderCompany: responseData.referee_organisation || null,
      payload: responseData
    },
    integrity: {
      emailMatch: hasResponse && !mismatchDetected ? true : (mismatchDetected ? false : null),
      identityMatch: hasResponse && !mismatchDetected ? true : (mismatchDetected ? false : null),
      notes: mismatchNotes
    },
    verification: {
      status: verified ? 'verified' : (hasResponse ? 'pending' : 'pending'),
      verifiedAt: verifiedAt || null,
      verifiedBy: verifiedBy || null,
      notes: null
    },
    summary,
    blocking: !verified
  };
}

/**
 * Normalize full references section
 */
export function normalizeReferenceRequirementSurface(employeeData) {
  const items = [
    normalizeReferenceItemSurface(employeeData, 1),
    normalizeReferenceItemSurface(employeeData, 2)
  ];
  
  const verifiedCount = items.filter(i => i.verification.status === 'verified').length;
  
  let summary = '';
  if (verifiedCount === 2) {
    summary = '2/2 references verified';
  } else if (verifiedCount === 1) {
    summary = '1/2 references verified';
  } else {
    const pendingResponses = items.filter(i => i.response.exists && i.verification.status !== 'verified').length;
    const sentRequests = items.filter(i => i.request.status === 'sent').length;
    
    if (pendingResponses > 0) {
      summary = `${pendingResponses} response${pendingResponses !== 1 ? 's' : ''} awaiting review`;
    } else if (sentRequests > 0) {
      summary = `${sentRequests} request${sentRequests !== 1 ? 's' : ''} pending`;
    } else {
      summary = 'References not started';
    }
  }
  
  return {
    key: 'references',
    items,
    summary,
    blocking: verifiedCount < 2
  };
}

// ============================================================================
// AGREEMENT REQUIREMENT SURFACE
// ============================================================================

/**
 * Normalize agreement data into UI surface
 */
export function normalizeAgreementItemSurface(agreementData) {
  const {
    id,
    title,
    template_id,
    template_version,
    status,
    sent_at,
    viewed_at,
    completed_at,
    completed_via,
    submission_id,
    signed_record_url,
    verified,
    verified_at,
    resent_count = 0,
    raw_status,
    can_sign,
    can_acknowledge,
    latest_active,
    source_record_id,
    current_lifecycle,
  } = agreementData;
  
  // Derive send state
  let sendStatus = 'not_sent';
  if (completed_at) {
    sendStatus = 'completed';
  } else if (viewed_at) {
    sendStatus = 'viewed';
  } else if (sent_at) {
    sendStatus = resent_count > 0 ? 'resent' : 'sent';
  }
  
  // Build summary
  let summary = '';
  if (verified) {
    summary = 'Verified';
  } else if (completed_at) {
    summary = 'Completed • awaiting verification';
  } else if (viewed_at) {
    summary = 'Viewed • awaiting completion';
  } else if (sent_at) {
    summary = 'Sent • awaiting completion';
  } else {
    summary = 'Not sent';
  }
  
  return {
    id,
    title: title || 'Agreement',
    templateId: template_id || null,
    templateVersion: template_version || null,
    sendState: {
      status: sendStatus,
      sentAt: sent_at || null,
      viewedAt: viewed_at || null,
      completedAt: completed_at || null,
      resentCount: resent_count
    },
    completion: {
      exists: !!completed_at,
      completedVia: completed_via || null,
      submissionId: submission_id || null,
      signedRecordUrl: signed_record_url || null
    },
    verification: {
      status: verified ? 'verified' : (completed_at ? 'pending' : 'unknown'),
      verifiedAt: verified_at || null,
      notes: null
    },
    canonical: {
      status: status || null,
      rawStatus: raw_status || null,
      canSign: typeof can_sign === 'boolean' ? can_sign : null,
      canAcknowledge: typeof can_acknowledge === 'boolean' ? can_acknowledge : null,
      latestActive: typeof latest_active === 'boolean' ? latest_active : null,
      sourceRecordId: source_record_id || null,
      currentLifecycle: current_lifecycle || null,
    },
    summary,
    blocking: !verified
  };
}

/**
 * Normalize full agreements section
 */
export function normalizeAgreementRequirementSurface(agreementsData = []) {
  const items = agreementsData.map(normalizeAgreementItemSurface);
  
  const verifiedCount = items.filter(i => i.verification.status === 'verified').length;
  const totalRequired = items.length;
  
  let summary = '';
  if (totalRequired === 0) {
    summary = 'No agreements required';
  } else if (verifiedCount === totalRequired) {
    summary = `${verifiedCount}/${totalRequired} agreements verified`;
  } else {
    const pendingVerification = items.filter(i => i.completion.exists && i.verification.status !== 'verified').length;
    const notSent = items.filter(i => i.sendState.status === 'not_sent').length;
    
    if (pendingVerification > 0) {
      summary = `${pendingVerification} awaiting verification`;
    } else if (notSent > 0) {
      summary = `${notSent} agreement${notSent !== 1 ? 's' : ''} not sent`;
    } else {
      summary = `${verifiedCount}/${totalRequired} verified`;
    }
  }
  
  return {
    key: 'agreements',
    items,
    summary,
    blocking: verifiedCount < totalRequired
  };
}

export default {
  normalizeUploadRequirementSurface,
  normalizeReferenceItemSurface,
  normalizeReferenceRequirementSurface,
  normalizeAgreementItemSurface,
  normalizeAgreementRequirementSurface
};
