/**
 * rolePacks.js - Frontend Role Pack Configuration
 * 
 * Single source of truth for role-based requirements on the frontend.
 * Mirrors backend rolePacks.py for consistent behavior.
 */

// =============================================================================
// REQUIREMENT TYPES
// =============================================================================

export const REQUIREMENT_TYPES = {
  document: [
    'right_to_work',
    'identity',
    'proof_of_address',
    'dbs',
    'training_scan'
  ],
  reference: [
    'reference_1',
    'reference_2'
  ],
  form: [
    'application_form',
    'equal_opportunities',
    'induction',
    'clinical_competency'
  ],
  registration: [
    'nmc_registration'
  ],
  system: [
    'cv'
  ]
};

export function getRequirementType(requirementKey) {
  for (const [type, keys] of Object.entries(REQUIREMENT_TYPES)) {
    if (keys.includes(requirementKey)) {
      return type;
    }
  }
  return 'document';
}

// =============================================================================
// REQUIREMENT METADATA
// =============================================================================

export const REQUIREMENT_METADATA = {
  cv: {
    label: 'CV / Resume',
    type: 'system',
    required: true,
    blocking: false,
    extractionEnabled: true
  },
  application_form: {
    label: 'Application Form',
    type: 'form',
    required: true,
    blocking: true
  },
  equal_opportunities: {
    label: 'Equal Opportunities Form',
    type: 'form',
    required: true,
    blocking: false
  },
  reference_1: {
    label: 'Reference 1',
    type: 'reference',
    required: true,
    blocking: true,
    integrityCheck: true
  },
  reference_2: {
    label: 'Reference 2',
    type: 'reference',
    required: true,
    blocking: true,
    integrityCheck: true
  },
  right_to_work: {
    label: 'Right to Work',
    type: 'document',
    required: true,
    blocking: true,
    extractionEnabled: true,
    expiryTracked: true,
    checkRequired: true
  },
  identity: {
    label: 'Identity',
    type: 'document',
    required: true,
    blocking: true,
    extractionEnabled: true,
    checkRequired: true
  },
  proof_of_address: {
    label: 'Proof of Address',
    type: 'document',
    required: true,
    blocking: true,
    extractionEnabled: true,
    checkRequired: true,
    multiFile: true,
    minFiles: 2,
    validityMonths: 12
  },
  dbs: {
    label: 'DBS Certificate',
    type: 'document',
    required: true,
    blocking: true,
    extractionEnabled: true,
    expiryTracked: true,
    checkRequired: true
  },
  nmc_registration: {
    label: 'NMC Registration',
    type: 'registration',
    required: true,
    blocking: true,
    expiryTracked: true,
    verificationRequired: true
  },
  training_scan: {
    label: 'Training Certificates',
    type: 'document',
    required: true,
    blocking: false,
    extractionEnabled: true,
    smartExtraction: true,
    multiFile: true
  },
  clinical_competency: {
    label: 'Clinical Competency Assessment',
    type: 'form',
    required: true,
    blocking: true
  },
  induction: {
    label: 'Induction',
    type: 'form',
    required: true,
    blocking: true
  }
};

export function getRequirementMetadata(requirementKey) {
  return REQUIREMENT_METADATA[requirementKey] || {
    label: requirementKey,
    type: 'document',
    required: true,
    blocking: false
  };
}

// =============================================================================
// ROLE PACKS
// =============================================================================

export const ROLE_PACK_HEALTHCARE_ASSISTANT = {
  role: 'healthcare_assistant',
  label: 'Healthcare Assistant',
  interviewTemplate: 'interview_hca_v1',
  
  requirements: [
    'cv',
    'application_form',
    'equal_opportunities',
    'reference_1',
    'reference_2',
    'right_to_work',
    'identity',
    'proof_of_address',
    'dbs',
    'training_scan',
    'induction'
  ],
  
  policies: {
    dbsRequiredBeforeApproval: true,
    poaValidityMonths: 12,
    minReferences: 2,
    rtwCheckRequired: true
  }
};

export const ROLE_PACK_NURSE = {
  role: 'nurse',
  label: 'Nurse',
  interviewTemplate: 'interview_nurse_v1',
  
  requirements: [
    'cv',
    'application_form',
    'equal_opportunities',
    'reference_1',
    'reference_2',
    'right_to_work',
    'identity',
    'proof_of_address',
    'dbs',
    'nmc_registration',
    'training_scan',
    'clinical_competency',
    'induction'
  ],
  
  policies: {
    dbsRequiredBeforeApproval: true,
    poaValidityMonths: 12,
    minReferences: 2,
    rtwCheckRequired: true,
    nmcRequired: true
  }
};

export const ROLE_PACK_CARE_ASSISTANT = {
  role: 'care_assistant',
  label: 'Care Assistant',
  interviewTemplate: 'interview_ca_v1',
  
  requirements: [
    'cv',
    'application_form',
    'equal_opportunities',
    'reference_1',
    'reference_2',
    'right_to_work',
    'identity',
    'proof_of_address',
    'dbs',
    'training_scan',
    'induction'
  ],
  
  policies: {
    dbsRequiredBeforeApproval: true,
    poaValidityMonths: 12,
    minReferences: 2,
    rtwCheckRequired: true
  }
};

export const ROLE_PACK_SENIOR_CARE_ASSISTANT = {
  role: 'senior_care_assistant',
  label: 'Senior Care Assistant',
  interviewTemplate: 'interview_sca_v1',
  
  requirements: [
    'cv',
    'application_form',
    'equal_opportunities',
    'reference_1',
    'reference_2',
    'right_to_work',
    'identity',
    'proof_of_address',
    'dbs',
    'training_scan',
    'induction'
  ],
  
  policies: {
    dbsRequiredBeforeApproval: true,
    poaValidityMonths: 12,
    minReferences: 2,
    rtwCheckRequired: true
  }
};

export const ROLE_PACK_SUPPORT_WORKER = {
  role: 'support_worker',
  label: 'Support Worker',
  interviewTemplate: 'interview_sw_v1',
  
  requirements: [
    'cv',
    'application_form',
    'equal_opportunities',
    'reference_1',
    'reference_2',
    'right_to_work',
    'identity',
    'proof_of_address',
    'dbs',
    'training_scan',
    'induction'
  ],
  
  policies: {
    dbsRequiredBeforeApproval: true,
    poaValidityMonths: 12,
    minReferences: 2,
    rtwCheckRequired: true
  }
};

// =============================================================================
// ROLE PACKS REGISTRY
// =============================================================================

export const ROLE_PACKS = {
  healthcare_assistant: ROLE_PACK_HEALTHCARE_ASSISTANT,
  nurse: ROLE_PACK_NURSE,
  care_assistant: ROLE_PACK_CARE_ASSISTANT,
  senior_care_assistant: ROLE_PACK_SENIOR_CARE_ASSISTANT,
  support_worker: ROLE_PACK_SUPPORT_WORKER
};

export function getRolePack(role) {
  return ROLE_PACKS[role] || ROLE_PACK_HEALTHCARE_ASSISTANT;
}

export function getRoleRequirements(role) {
  const pack = getRolePack(role);
  return pack.requirements || [];
}

export function getRolePolicies(role) {
  const pack = getRolePack(role);
  return pack.policies || {};
}

export function getInterviewTemplate(role) {
  const pack = getRolePack(role);
  return pack.interviewTemplate || 'interview_default_v1';
}

// =============================================================================
// RECRUITMENT STAGES
// =============================================================================

export const RECRUITMENT_STAGES = [
  { key: 'new', label: 'New Application', order: 1 },
  { key: 'screening', label: 'Screening', order: 2 },
  { key: 'interview', label: 'Interview', order: 3 },
  { key: 'compliance_review', label: 'Compliance Review', order: 4 },
  { key: 'onboarding', label: 'Onboarding', order: 5 },
  { key: 'active', label: 'Active', order: 6 },
  { key: 'inactive', label: 'Inactive', order: 7 },
  { key: 'archived', label: 'Archived', order: 8 },
  { key: 'withdrawn', label: 'Withdrawn', order: 9 },
  { key: 'superseded', label: 'Superseded', order: 10 }
];

export const APPLICANT_STAGES = ['new', 'screening', 'interview', 'compliance_review'];
export const EMPLOYEE_STAGES = ['onboarding', 'active', 'inactive'];

export function isApplicantStage(stage) {
  return APPLICANT_STAGES.includes(stage);
}

export function isEmployeeStage(stage) {
  return EMPLOYEE_STAGES.includes(stage);
}

export function getStageLabel(stageKey) {
  const stage = RECRUITMENT_STAGES.find(s => s.key === stageKey);
  return stage ? stage.label : stageKey;
}

// =============================================================================
// EXPIRY REMINDER RULES
// =============================================================================

export const EXPIRY_REMINDER_RULES = {
  right_to_work: [90, 60, 30, 7],
  dbs: [90, 60, 30, 7],
  nmc_registration: [90, 60, 30, 7],
  training_scan: [90, 60, 30, 7],
  identity: [90, 60, 30, 7]
};

export function getExpiryReminderDays(requirementKey) {
  return EXPIRY_REMINDER_RULES[requirementKey] || [30, 7];
}

// =============================================================================
// HELPER: Check if role requires NMC
// =============================================================================

export function roleRequiresNMC(role) {
  const policies = getRolePolicies(role);
  return policies.nmcRequired === true;
}

// =============================================================================
// HELPER: Get blocking requirements for a role
// =============================================================================

export function getBlockingRequirements(role) {
  const requirements = getRoleRequirements(role);
  return requirements.filter(reqKey => {
    const metadata = getRequirementMetadata(reqKey);
    return metadata.blocking === true;
  });
}

// =============================================================================
// HELPER: Group requirements by type
// =============================================================================

export function groupRequirementsByType(role) {
  const requirements = getRoleRequirements(role);
  
  const groups = {
    document: [],
    reference: [],
    form: [],
    registration: [],
    system: []
  };
  
  for (const reqKey of requirements) {
    const type = getRequirementType(reqKey);
    if (groups[type]) {
      groups[type].push(reqKey);
    }
  }
  
  return groups;
}
