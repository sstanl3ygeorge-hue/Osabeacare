/**
 * requirementCapabilityMap.js
 * 
 * Comprehensive capability map for all compliance requirements.
 * This file is the single source of truth for:
 * - What type each requirement is (evidence, form, hybrid, reference)
 * - What actions are available for each requirement
 * - Delivery mode for sendable requirements (admin_only, employee_sendable, internal_only, hybrid)
 * - Backend endpoint paths for each action
 * 
 * NO placeholder buttons - every action must have a real backend path.
 */

// ============================================================================
// REQUIREMENT TYPES
// ============================================================================
export const REQUIREMENT_TYPES = {
  EVIDENCE: 'evidence',      // Documents uploaded and verified
  FORM: 'form',              // Form filled, saved, verified
  HYBRID: 'hybrid',          // Both form submission AND file attachment
  REFERENCE: 'reference',    // Reference lifecycle workflow
  CHECK: 'check',            // Internal verification check
  AGREEMENT: 'agreement',    // Agreement acknowledgement workflow
  TRAINING: 'training'       // Training certificates
};

// ============================================================================
// DELIVERY / COMPLETION MODES
// ============================================================================
export const DELIVERY_MODES = {
  ADMIN_ONLY: 'admin_only',           // Only admin can fill
  EMPLOYEE_SENDABLE: 'employee_sendable', // Can send to employee to complete
  INTERNAL_ONLY: 'internal_only',     // Internal admin-only process
  HYBRID: 'hybrid'                    // Both admin fill and send options
};

// ============================================================================
// EVIDENCE ACTIONS - For document upload requirements
// ============================================================================
export const EVIDENCE_ACTIONS = {
  REQUEST: 'request',        // Send request to employee
  UPLOAD: 'upload',          // Admin uploads file
  VIEW: 'view',              // View file(s)
  DOWNLOAD: 'download',      // Download file(s)
  VERIFY: 'verify',          // Verify document
  REJECT: 'reject',          // Reject document
  HISTORY: 'history',        // View history
  EXTRACT: 'extract',        // AI extraction
  SUPERSEDE: 'supersede',    // Mark as superseded
  RESEND: 'resend'           // Resend request
};

// ============================================================================
// FORM ACTIONS - For form-type requirements
// ============================================================================
export const FORM_ACTIONS = {
  SEND: 'send',              // Send form to employee
  FILL_FORM: 'fill_form',    // Admin fills form
  VIEW_SUBMISSION: 'view_submission',
  EXPORT_PDF: 'export_pdf',
  VERIFY: 'verify',
  REJECT: 'reject',
  HISTORY: 'history',
  EDIT: 'edit',              // Edit submission
  REOPEN: 'reopen'           // Reopen for editing
};

// ============================================================================
// REQUIREMENT CAPABILITY MAP
// ============================================================================
export const REQUIREMENT_CAPABILITY_MAP = {
  // ======== EVIDENCE REQUIREMENTS ========
  
  // Right to Work Documents
  right_to_work_documents: {
    id: 'right_to_work_documents',
    name: 'Right to Work Documents',
    type: REQUIREMENT_TYPES.EVIDENCE,
    delivery_mode: DELIVERY_MODES.HYBRID,
    actions: [
      EVIDENCE_ACTIONS.REQUEST,
      EVIDENCE_ACTIONS.UPLOAD,
      EVIDENCE_ACTIONS.VIEW,
      EVIDENCE_ACTIONS.DOWNLOAD,
      EVIDENCE_ACTIONS.VERIFY,
      EVIDENCE_ACTIONS.REJECT,
      EVIDENCE_ACTIONS.HISTORY,
      EVIDENCE_ACTIONS.EXTRACT,
      EVIDENCE_ACTIONS.SUPERSEDE,
      EVIDENCE_ACTIONS.RESEND
    ],
    backend_paths: {
      request: '/api/employees/{id}/requirements/{key}/resend-request',
      upload: '/api/employees/{id}/evidence',
      files: '/api/employees/{id}/requirements/{key}/files',
      history: '/api/employees/{id}/requirements/{key}/unified-history',
      verify: '/api/employees/{id}/documents/{docId}/verify',
      reject: '/api/employees/{id}/documents/{docId}/reject',
      extract: '/api/documents/{docId}/extract'
    },
    affects_readiness: true,
    paired_check: 'right_to_work_check'
  },

  // Right to Work Check (Internal verification)
  right_to_work_check: {
    id: 'right_to_work_check',
    name: 'Right to Work Check',
    type: REQUIREMENT_TYPES.CHECK,
    delivery_mode: DELIVERY_MODES.ADMIN_ONLY,
    actions: ['record_check', 'update_check', 'history'],
    backend_paths: {
      record: '/api/employees/{id}/right-to-work/check',
      history: '/api/employees/{id}/requirements/{key}/unified-history'
    },
    affects_readiness: true
  },

  // DBS Certificate
  dbs_certificate: {
    id: 'dbs_certificate',
    name: 'DBS Certificate',
    type: REQUIREMENT_TYPES.EVIDENCE,
    delivery_mode: DELIVERY_MODES.HYBRID,
    actions: [
      EVIDENCE_ACTIONS.REQUEST,
      EVIDENCE_ACTIONS.UPLOAD,
      EVIDENCE_ACTIONS.VIEW,
      EVIDENCE_ACTIONS.DOWNLOAD,
      EVIDENCE_ACTIONS.VERIFY,
      EVIDENCE_ACTIONS.REJECT,
      EVIDENCE_ACTIONS.HISTORY,
      EVIDENCE_ACTIONS.EXTRACT
    ],
    backend_paths: {
      request: '/api/employees/{id}/requirements/{key}/resend-request',
      upload: '/api/employees/{id}/evidence',
      files: '/api/employees/{id}/requirements/{key}/files',
      history: '/api/employees/{id}/requirements/{key}/unified-history',
      verify: '/api/employees/{id}/documents/{docId}/verify',
      extract: '/api/documents/{docId}/extract'
    },
    affects_readiness: true,
    paired_check: 'dbs_check'
  },

  // DBS Update Service Check
  dbs_check: {
    id: 'dbs_check',
    name: 'DBS Update Service Check',
    type: REQUIREMENT_TYPES.CHECK,
    delivery_mode: DELIVERY_MODES.ADMIN_ONLY,
    actions: ['record_check', 'update_check', 'history'],
    backend_paths: {
      record: '/api/employees/{id}/dbs/check',
      history: '/api/employees/{id}/requirements/{key}/unified-history'
    },
    affects_readiness: true
  },

  // Identity Documents
  identity_documents: {
    id: 'identity_documents',
    name: 'Identity Documents',
    type: REQUIREMENT_TYPES.EVIDENCE,
    delivery_mode: DELIVERY_MODES.HYBRID,
    actions: [
      EVIDENCE_ACTIONS.REQUEST,
      EVIDENCE_ACTIONS.UPLOAD,
      EVIDENCE_ACTIONS.VIEW,
      EVIDENCE_ACTIONS.DOWNLOAD,
      EVIDENCE_ACTIONS.VERIFY,
      EVIDENCE_ACTIONS.REJECT,
      EVIDENCE_ACTIONS.HISTORY,
      EVIDENCE_ACTIONS.EXTRACT
    ],
    backend_paths: {
      request: '/api/employees/{id}/requirements/{key}/resend-request',
      upload: '/api/employees/{id}/evidence',
      files: '/api/employees/{id}/requirements/{key}/files',
      history: '/api/employees/{id}/requirements/{key}/unified-history',
      verify: '/api/employees/{id}/documents/{docId}/verify',
      extract: '/api/documents/{docId}/extract'
    },
    affects_readiness: true
  },

  // Proof of Address
  proof_of_address: {
    id: 'proof_of_address',
    name: 'Proof of Address',
    type: REQUIREMENT_TYPES.EVIDENCE,
    delivery_mode: DELIVERY_MODES.HYBRID,
    min_files: 2,
    actions: [
      EVIDENCE_ACTIONS.REQUEST,
      EVIDENCE_ACTIONS.UPLOAD,
      EVIDENCE_ACTIONS.VIEW,
      EVIDENCE_ACTIONS.DOWNLOAD,
      EVIDENCE_ACTIONS.VERIFY,
      EVIDENCE_ACTIONS.REJECT,
      EVIDENCE_ACTIONS.HISTORY,
      EVIDENCE_ACTIONS.EXTRACT
    ],
    backend_paths: {
      request: '/api/employees/{id}/requirements/{key}/resend-request',
      upload: '/api/employees/{id}/evidence',
      files: '/api/employees/{id}/requirements/{key}/files',
      history: '/api/employees/{id}/requirements/{key}/unified-history',
      verify: '/api/employees/{id}/documents/{docId}/verify',
      extract: '/api/documents/{docId}/extract'
    },
    affects_readiness: true,
    freshness_months: 3
  },

  // CV / Resume
  cv: {
    id: 'cv',
    name: 'CV / Resume',
    type: REQUIREMENT_TYPES.EVIDENCE,
    delivery_mode: DELIVERY_MODES.HYBRID,
    actions: [
      EVIDENCE_ACTIONS.REQUEST,
      EVIDENCE_ACTIONS.UPLOAD,
      EVIDENCE_ACTIONS.VIEW,
      EVIDENCE_ACTIONS.DOWNLOAD,
      EVIDENCE_ACTIONS.HISTORY,
      EVIDENCE_ACTIONS.EXTRACT
    ],
    backend_paths: {
      request: '/api/employees/{id}/requirements/{key}/resend-request',
      upload: '/api/employees/{id}/evidence',
      files: '/api/employees/{id}/requirements/{key}/files',
      history: '/api/employees/{id}/requirements/{key}/unified-history',
      extract: '/api/documents/{docId}/extract'
    },
    affects_readiness: false
  },

  // ======== FORM REQUIREMENTS (Employee Sendable) ========

  // Contract Acceptance
  contract_acceptance: {
    id: 'contract_acceptance',
    name: 'Contract Acceptance',
    type: REQUIREMENT_TYPES.AGREEMENT,
    delivery_mode: DELIVERY_MODES.EMPLOYEE_SENDABLE,
    template_id: 'ZERO_HOUR_CONTRACT_V1',
    actions: [
      FORM_ACTIONS.SEND,
      FORM_ACTIONS.FILL_FORM,
      FORM_ACTIONS.VIEW_SUBMISSION,
      FORM_ACTIONS.EXPORT_PDF,
      FORM_ACTIONS.VERIFY,
      FORM_ACTIONS.REJECT,
      FORM_ACTIONS.HISTORY
    ],
    backend_paths: {
      send: '/api/employees/{id}/send-form',
      submit: '/api/employees/{id}/agreement-submissions',
      view: '/api/agreement-submissions/{submissionId}',
      pdf: '/api/agreement-submissions/{submissionId}/pdf',
      verify: '/api/agreement-submissions/{submissionId}/verify',
      reject: '/api/agreement-submissions/{submissionId}/reject',
      history: '/api/employees/{id}/requirements/{key}/unified-history'
    },
    affects_readiness: true
  },

  // Employee Handbook Acknowledgement
  handbook_acknowledgement: {
    id: 'handbook_acknowledgement',
    name: 'Employee Handbook Acknowledgement',
    type: REQUIREMENT_TYPES.AGREEMENT,
    delivery_mode: DELIVERY_MODES.EMPLOYEE_SENDABLE,
    template_id: 'EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1',
    actions: [
      FORM_ACTIONS.SEND,
      FORM_ACTIONS.FILL_FORM,
      FORM_ACTIONS.VIEW_SUBMISSION,
      FORM_ACTIONS.EXPORT_PDF,
      FORM_ACTIONS.VERIFY,
      FORM_ACTIONS.REJECT,
      FORM_ACTIONS.HISTORY
    ],
    backend_paths: {
      send: '/api/employees/{id}/send-form',
      submit: '/api/employees/{id}/agreement-submissions',
      view: '/api/agreement-submissions/{submissionId}',
      pdf: '/api/agreement-submissions/{submissionId}/pdf',
      verify: '/api/agreement-submissions/{submissionId}/verify',
      reject: '/api/agreement-submissions/{submissionId}/reject',
      history: '/api/employees/{id}/requirements/{key}/unified-history'
    },
    affects_readiness: true
  },

  // Staff Health Questionnaire
  staff_health_questionnaire: {
    id: 'staff_health_questionnaire',
    name: 'Staff Health Questionnaire',
    type: REQUIREMENT_TYPES.FORM,
    delivery_mode: DELIVERY_MODES.EMPLOYEE_SENDABLE,
    form_type: 'staff_health_questionnaire',
    actions: [
      FORM_ACTIONS.SEND,
      FORM_ACTIONS.FILL_FORM,
      FORM_ACTIONS.VIEW_SUBMISSION,
      FORM_ACTIONS.EXPORT_PDF,
      FORM_ACTIONS.VERIFY,
      FORM_ACTIONS.REJECT,
      FORM_ACTIONS.HISTORY
    ],
    backend_paths: {
      send: '/api/employees/{id}/send-form',
      template: '/api/form-submissions/template/staff_health_questionnaire',
      autofill: '/api/form-submissions/auto-fill/staff_health_questionnaire/{id}',
      submit: '/api/form-submissions',
      view: '/api/form-submissions/{submissionId}',
      pdf: '/api/form-submissions/{submissionId}/generate-pdf',
      download_pdf: '/api/form-submissions/{submissionId}/download-pdf',
      verify: '/api/form-submissions/{submissionId}/verify',
      reject: '/api/form-submissions/{submissionId}/unverify',
      history: '/api/employees/{id}/requirements/{key}/unified-history'
    },
    affects_readiness: true
  },

  // HMRC Starter Checklist
  hmrc_starter_checklist: {
    id: 'hmrc_starter_checklist',
    name: 'HMRC Starter Checklist',
    type: REQUIREMENT_TYPES.FORM,
    delivery_mode: DELIVERY_MODES.EMPLOYEE_SENDABLE,
    form_type: 'hmrc_starter_checklist',
    actions: [
      FORM_ACTIONS.SEND,
      FORM_ACTIONS.FILL_FORM,
      FORM_ACTIONS.VIEW_SUBMISSION,
      FORM_ACTIONS.EXPORT_PDF,
      FORM_ACTIONS.VERIFY,
      FORM_ACTIONS.REJECT,
      FORM_ACTIONS.HISTORY
    ],
    backend_paths: {
      send: '/api/employees/{id}/send-form',
      template: '/api/form-submissions/template/hmrc_starter_checklist',
      autofill: '/api/form-submissions/auto-fill/hmrc_starter_checklist/{id}',
      submit: '/api/form-submissions',
      view: '/api/form-submissions/{submissionId}',
      pdf: '/api/form-submissions/{submissionId}/generate-pdf',
      download_pdf: '/api/form-submissions/{submissionId}/download-pdf',
      verify: '/api/form-submissions/{submissionId}/verify',
      history: '/api/employees/{id}/requirements/{key}/unified-history'
    },
    affects_readiness: false,
    conditional_on: 'p45'
  },

  // Equal Opportunities Monitoring
  equal_opportunities: {
    id: 'equal_opportunities',
    name: 'Equal Opportunities Monitoring',
    type: REQUIREMENT_TYPES.FORM,
    delivery_mode: DELIVERY_MODES.EMPLOYEE_SENDABLE,
    form_type: 'equal_opportunities',
    optional: true,
    actions: [
      FORM_ACTIONS.SEND,
      FORM_ACTIONS.FILL_FORM,
      FORM_ACTIONS.VIEW_SUBMISSION,
      FORM_ACTIONS.EXPORT_PDF,
      FORM_ACTIONS.HISTORY
    ],
    backend_paths: {
      send: '/api/employees/{id}/send-form',
      template: '/api/form-submissions/template/equal_opportunities',
      autofill: '/api/form-submissions/auto-fill/equal_opportunities/{id}',
      submit: '/api/form-submissions',
      view: '/api/form-submissions/{submissionId}',
      pdf: '/api/form-submissions/{submissionId}/generate-pdf',
      download_pdf: '/api/form-submissions/{submissionId}/download-pdf',
      history: '/api/employees/{id}/requirements/{key}/unified-history'
    },
    affects_readiness: false
  },

  // Staff Personal Information
  staff_personal_info: {
    id: 'staff_personal_info',
    name: 'Staff Personal Information',
    type: REQUIREMENT_TYPES.FORM,
    delivery_mode: DELIVERY_MODES.EMPLOYEE_SENDABLE,
    form_type: 'staff_personal_info',
    updates_profile: true,
    actions: [
      FORM_ACTIONS.SEND,
      FORM_ACTIONS.FILL_FORM,
      FORM_ACTIONS.VIEW_SUBMISSION,
      FORM_ACTIONS.EXPORT_PDF,
      FORM_ACTIONS.HISTORY,
      FORM_ACTIONS.EDIT
    ],
    backend_paths: {
      send: '/api/employees/{id}/send-form',
      template: '/api/form-submissions/template/staff_personal_info',
      autofill: '/api/form-submissions/auto-fill/staff_personal_info/{id}',
      submit: '/api/form-submissions',
      view: '/api/form-submissions/{submissionId}',
      pdf: '/api/form-submissions/{submissionId}/generate-pdf',
      download_pdf: '/api/form-submissions/{submissionId}/download-pdf',
      history: '/api/employees/{id}/requirements/{key}/unified-history'
    },
    affects_readiness: false
  },

  // ======== FORM REQUIREMENTS (Admin Only) ========

  // Interview Record
  interview_record: {
    id: 'interview_record',
    name: 'Interview Record',
    type: REQUIREMENT_TYPES.FORM,
    delivery_mode: DELIVERY_MODES.ADMIN_ONLY,
    form_type: 'interview_record',
    actions: [
      FORM_ACTIONS.FILL_FORM,
      FORM_ACTIONS.VIEW_SUBMISSION,
      FORM_ACTIONS.EXPORT_PDF,
      FORM_ACTIONS.VERIFY,
      FORM_ACTIONS.HISTORY,
      FORM_ACTIONS.EDIT
    ],
    backend_paths: {
      template: '/api/form-submissions/template/interview_record',
      autofill: '/api/form-submissions/auto-fill/interview_record/{id}',
      submit: '/api/form-submissions',
      view: '/api/form-submissions/{submissionId}',
      pdf: '/api/form-submissions/{submissionId}/generate-pdf',
      download_pdf: '/api/form-submissions/{submissionId}/download-pdf',
      verify: '/api/form-submissions/{submissionId}/verify',
      history: '/api/employees/{id}/requirements/{key}/unified-history'
    },
    affects_readiness: false
  },

  // Recruitment Compliance Checklist
  recruitment_checklist: {
    id: 'recruitment_checklist',
    name: 'Recruitment Compliance Checklist',
    type: REQUIREMENT_TYPES.FORM,
    delivery_mode: DELIVERY_MODES.ADMIN_ONLY,
    form_type: 'recruitment_checklist',
    actions: [
      FORM_ACTIONS.FILL_FORM,
      FORM_ACTIONS.VIEW_SUBMISSION,
      FORM_ACTIONS.EXPORT_PDF,
      FORM_ACTIONS.VERIFY,
      FORM_ACTIONS.HISTORY,
      FORM_ACTIONS.EDIT
    ],
    backend_paths: {
      template: '/api/form-submissions/template/recruitment_checklist',
      autofill: '/api/form-submissions/auto-fill/recruitment_checklist/{id}',
      submit: '/api/form-submissions',
      view: '/api/form-submissions/{submissionId}',
      pdf: '/api/form-submissions/{submissionId}/generate-pdf',
      download_pdf: '/api/form-submissions/{submissionId}/download-pdf',
      verify: '/api/form-submissions/{submissionId}/verify',
      history: '/api/employees/{id}/requirements/{key}/unified-history'
    },
    affects_readiness: false
  },

  // Induction & Competency Assessment
  induction: {
    id: 'induction',
    name: 'Induction & Competency Assessment',
    type: REQUIREMENT_TYPES.FORM,
    delivery_mode: DELIVERY_MODES.ADMIN_ONLY,
    form_type: 'induction',
    actions: [
      FORM_ACTIONS.FILL_FORM,
      FORM_ACTIONS.VIEW_SUBMISSION,
      FORM_ACTIONS.EXPORT_PDF,
      FORM_ACTIONS.VERIFY,
      FORM_ACTIONS.HISTORY,
      FORM_ACTIONS.EDIT
    ],
    backend_paths: {
      template: '/api/form-submissions/template/induction',
      autofill: '/api/form-submissions/auto-fill/induction/{id}',
      submit: '/api/form-submissions',
      view: '/api/form-submissions/{submissionId}',
      pdf: '/api/form-submissions/{submissionId}/generate-pdf',
      download_pdf: '/api/form-submissions/{submissionId}/download-pdf',
      verify: '/api/form-submissions/{submissionId}/verify',
      history: '/api/employees/{id}/requirements/{key}/unified-history'
    },
    affects_readiness: true
  },

  // ======== HYBRID REQUIREMENTS (Form + File Attachment) ========

  // Application Form - Can be uploaded as PDF or filled as form
  application_form: {
    id: 'application_form',
    name: 'Application Form',
    type: REQUIREMENT_TYPES.HYBRID,
    delivery_mode: DELIVERY_MODES.HYBRID,
    form_type: 'application_form',
    actions: [
      FORM_ACTIONS.FILL_FORM,
      FORM_ACTIONS.VIEW_SUBMISSION,
      FORM_ACTIONS.EXPORT_PDF,
      EVIDENCE_ACTIONS.UPLOAD,
      EVIDENCE_ACTIONS.VIEW,
      EVIDENCE_ACTIONS.DOWNLOAD,
      FORM_ACTIONS.HISTORY,
      EVIDENCE_ACTIONS.EXTRACT
    ],
    backend_paths: {
      template: '/api/form-submissions/template/application_form',
      autofill: '/api/form-submissions/auto-fill/application_form/{id}',
      submit: '/api/form-submissions',
      view: '/api/form-submissions/{submissionId}',
      pdf: '/api/form-submissions/{submissionId}/generate-pdf',
      upload: '/api/employees/{id}/evidence',
      files: '/api/employees/{id}/requirements/{key}/files',
      history: '/api/employees/{id}/requirements/{key}/unified-history',
      extract: '/api/documents/{docId}/extract',
      import: '/api/generated-forms/import-application'
    },
    affects_readiness: false
  },

  // ======== REFERENCE REQUIREMENTS ========

  // Reference 1
  reference_1: {
    id: 'reference_1',
    name: 'Reference 1',
    type: REQUIREMENT_TYPES.REFERENCE,
    delivery_mode: DELIVERY_MODES.EMPLOYEE_SENDABLE,
    reference_num: 1,
    actions: [
      'send_request',
      'resend_request',
      'view_response',
      'verify',
      'reject',
      'override_mismatch',
      'request_replacement',
      'change_referee',
      'reset',
      'history'
    ],
    backend_paths: {
      send: '/api/references/{id}/1/send-request',
      resend: '/api/references/{id}/1/resend-request',
      view: '/api/employees/{id}/references-normalized',
      verify: '/api/employees/{id}/verify-reference',
      reject: '/api/references/{id}/1/reject',
      override: '/api/references/{id}/1/override-mismatch',
      replacement: '/api/references/{id}/1/request-replacement',
      change_referee: '/api/references/{id}/1/change-referee',
      reset: '/api/references/{id}/1/reset',
      history: '/api/employees/{id}/requirements/{key}/unified-history'
    },
    affects_readiness: true
  },

  // Reference 2
  reference_2: {
    id: 'reference_2',
    name: 'Reference 2',
    type: REQUIREMENT_TYPES.REFERENCE,
    delivery_mode: DELIVERY_MODES.EMPLOYEE_SENDABLE,
    reference_num: 2,
    actions: [
      'send_request',
      'resend_request',
      'view_response',
      'verify',
      'reject',
      'override_mismatch',
      'request_replacement',
      'change_referee',
      'reset',
      'history'
    ],
    backend_paths: {
      send: '/api/references/{id}/2/send-request',
      resend: '/api/references/{id}/2/resend-request',
      view: '/api/employees/{id}/references-normalized',
      verify: '/api/employees/{id}/verify-reference',
      reject: '/api/references/{id}/2/reject',
      override: '/api/references/{id}/2/override-mismatch',
      replacement: '/api/references/{id}/2/request-replacement',
      change_referee: '/api/references/{id}/2/change-referee',
      reset: '/api/references/{id}/2/reset',
      history: '/api/employees/{id}/requirements/{key}/unified-history'
    },
    affects_readiness: true
  }
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get capability config for a requirement
 */
export function getRequirementCapability(requirementKey) {
  return REQUIREMENT_CAPABILITY_MAP[requirementKey] || null;
}

/**
 * Get all requirements of a specific type
 */
export function getRequirementsByType(type) {
  return Object.values(REQUIREMENT_CAPABILITY_MAP).filter(r => r.type === type);
}

/**
 * Get all sendable requirements (employee_sendable or hybrid delivery mode)
 */
export function getSendableRequirements() {
  return Object.values(REQUIREMENT_CAPABILITY_MAP).filter(
    r => r.delivery_mode === DELIVERY_MODES.EMPLOYEE_SENDABLE || 
         r.delivery_mode === DELIVERY_MODES.HYBRID
  );
}

/**
 * Check if a requirement supports a specific action
 */
export function requirementSupportsAction(requirementKey, action) {
  const cap = REQUIREMENT_CAPABILITY_MAP[requirementKey];
  if (!cap) return false;
  return cap.actions.includes(action);
}

/**
 * Get backend path for a requirement action
 * @param {string} requirementKey - The requirement key
 * @param {string} action - The action (e.g., 'send', 'verify')
 * @param {Object} params - Parameters to substitute (e.g., { id: 'emp123', submissionId: 'sub456' })
 */
export function getBackendPath(requirementKey, action, params = {}) {
  const cap = REQUIREMENT_CAPABILITY_MAP[requirementKey];
  if (!cap || !cap.backend_paths || !cap.backend_paths[action]) {
    return null;
  }
  
  let path = cap.backend_paths[action];
  
  // Substitute parameters
  Object.keys(params).forEach(key => {
    path = path.replace(`{${key}}`, params[key]);
  });
  
  return path;
}

/**
 * Check if requirement is employee-sendable
 */
export function isEmployeeSendable(requirementKey) {
  const cap = REQUIREMENT_CAPABILITY_MAP[requirementKey];
  return cap && (
    cap.delivery_mode === DELIVERY_MODES.EMPLOYEE_SENDABLE || 
    cap.delivery_mode === DELIVERY_MODES.HYBRID
  );
}

/**
 * Check if requirement affects work readiness
 */
export function affectsReadiness(requirementKey) {
  const cap = REQUIREMENT_CAPABILITY_MAP[requirementKey];
  return cap ? cap.affects_readiness : false;
}

/**
 * Get the form type for form-based requirements
 */
export function getFormType(requirementKey) {
  const cap = REQUIREMENT_CAPABILITY_MAP[requirementKey];
  return cap?.form_type || null;
}

/**
 * Get template ID for agreement requirements
 */
export function getTemplateId(requirementKey) {
  const cap = REQUIREMENT_CAPABILITY_MAP[requirementKey];
  return cap?.template_id || null;
}

/**
 * Get available actions based on requirement type and current state
 */
export function getAvailableActions(requirementKey, state = {}) {
  const cap = REQUIREMENT_CAPABILITY_MAP[requirementKey];
  if (!cap) return [];
  
  const { 
    hasSubmission = false, 
    isVerified = false, 
    hasFiles = false,
    hasPendingRequest = false,
    isAdminOnly = cap.delivery_mode === DELIVERY_MODES.ADMIN_ONLY
  } = state;
  
  const actions = [];
  
  switch (cap.type) {
    case REQUIREMENT_TYPES.EVIDENCE:
      // Evidence requirements
      if (!hasFiles && !hasPendingRequest && cap.delivery_mode !== DELIVERY_MODES.ADMIN_ONLY) {
        actions.push('request');
      }
      if (hasPendingRequest) {
        actions.push('resend');
      }
      actions.push('upload');
      if (hasFiles) {
        actions.push('view', 'download');
        if (!isVerified) {
          actions.push('verify', 'reject');
        }
      }
      actions.push('history');
      break;
      
    case REQUIREMENT_TYPES.FORM:
    case REQUIREMENT_TYPES.AGREEMENT:
      // Form/Agreement requirements
      if (!hasSubmission) {
        if (!isAdminOnly && cap.actions.includes(FORM_ACTIONS.SEND)) {
          actions.push('send');
        }
        actions.push('fill_form');
      } else {
        actions.push('view_submission');
        if (cap.actions.includes(FORM_ACTIONS.EXPORT_PDF)) {
          actions.push('export_pdf');
        }
        if (!isVerified) {
          if (cap.actions.includes(FORM_ACTIONS.VERIFY)) {
            actions.push('verify');
          }
          if (cap.actions.includes(FORM_ACTIONS.REJECT)) {
            actions.push('reject');
          }
        }
        if (cap.actions.includes(FORM_ACTIONS.EDIT)) {
          actions.push('edit');
        }
      }
      actions.push('history');
      break;
      
    case REQUIREMENT_TYPES.HYBRID:
      // Hybrid requirements support both
      if (!hasSubmission && !hasFiles) {
        actions.push('fill_form', 'upload');
      } else if (hasSubmission) {
        actions.push('view_submission');
        if (cap.actions.includes(FORM_ACTIONS.EXPORT_PDF)) {
          actions.push('export_pdf');
        }
      }
      if (hasFiles) {
        actions.push('view', 'download');
      }
      actions.push('history');
      break;
      
    case REQUIREMENT_TYPES.REFERENCE:
      // Reference requirements - handled by ReferenceRow
      break;
      
    default:
      break;
  }
  
  return actions;
}

// Export all for convenience
export default {
  REQUIREMENT_TYPES,
  DELIVERY_MODES,
  EVIDENCE_ACTIONS,
  FORM_ACTIONS,
  REQUIREMENT_CAPABILITY_MAP,
  getRequirementCapability,
  getRequirementsByType,
  getSendableRequirements,
  requirementSupportsAction,
  getBackendPath,
  isEmployeeSendable,
  affectsReadiness,
  getFormType,
  getTemplateId,
  getAvailableActions
};
