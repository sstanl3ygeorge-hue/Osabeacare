import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { Loader2, Shield, Upload, FileText, X, CheckCircle, AlertTriangle, Info, ExternalLink } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ==================== AUDIT-READY CHECK METHODS ====================
// These verification methods reflect QA/inspection expectations
// Values are backend enum-compatible, labels are user-friendly
// Organized by requirement type for requirement-aware dropdowns

const CHECK_METHODS = {
  // Right to Work verification methods - UK GOVERNMENT COMPLIANT
  // Values match VALID_RTW_CHECK_METHODS in backend
  right_to_work: [
    { value: 'home_office_online_check', label: 'Home Office Online Check (Share Code)', recommended: true, route: 'home_office_online_check' },
    { value: 'manual_passport_uk_irish', label: 'Manual Check - UK/Irish Passport', route: 'manual_list_a_check' },
    { value: 'manual_list_a_document', label: 'Manual Check - List A Document', route: 'manual_list_a_check' },
    { value: 'manual_list_b_group_1', label: 'Manual Check - List B Group 1 (Time-Limited)', route: 'manual_list_b_group_1_check' },
    { value: 'manual_list_b_group_2_ecs', label: 'Manual Check - List B Group 2 / ECS', route: 'manual_list_b_group_2_check' },
    { value: 'idsp_check', label: 'Digital Verification Service (IDSP)', route: 'digital_verification_service_check' },
    { value: 'ecs_pvn_check', label: 'Employer Checking Service (PVN)', route: 'ecs_pvn_check' }
  ],
  right_to_work_check: [
    { value: 'home_office_online_check', label: 'Home Office Online Check (Share Code)', recommended: true, route: 'home_office_online_check' },
    { value: 'manual_passport_uk_irish', label: 'Manual Check - UK/Irish Passport', route: 'manual_list_a_check' },
    { value: 'manual_list_a_document', label: 'Manual Check - List A Document', route: 'manual_list_a_check' },
    { value: 'manual_list_b_group_1', label: 'Manual Check - List B Group 1 (Time-Limited)', route: 'manual_list_b_group_1_check' },
    { value: 'manual_list_b_group_2_ecs', label: 'Manual Check - List B Group 2 / ECS', route: 'manual_list_b_group_2_check' },
    { value: 'idsp_check', label: 'Digital Verification Service (IDSP)', route: 'digital_verification_service_check' },
    { value: 'ecs_pvn_check', label: 'Employer Checking Service (PVN)', route: 'ecs_pvn_check' }
  ],
  
  // DBS verification methods
  dbs: [
    { value: 'dbs_certificate_review', label: 'DBS Certificate Review' },
    { value: 'dbs_update_service_check', label: 'DBS Update Service Check' },
    { value: 'other', label: 'Other Documented Verification' }
  ],
  dbs_status_check: [
    { value: 'dbs_certificate_review', label: 'DBS Certificate Review' },
    { value: 'dbs_update_service_check', label: 'DBS Update Service Check' },
    { value: 'other', label: 'Other Documented Verification' }
  ],
  
  // Identity verification methods
  identity: [
    { value: 'original_document_seen', label: 'Original Document Seen' },
    { value: 'certified_copy_verified', label: 'Certified Copy Verified' },
    { value: 'digital_id_verification', label: 'Digital ID Verification' },
    { value: 'other', label: 'Other Documented Verification' }
  ],
  identity_verification: [
    { value: 'original_document_seen', label: 'Original Document Seen' },
    { value: 'certified_copy_verified', label: 'Certified Copy Verified' },
    { value: 'digital_id_verification', label: 'Digital ID Verification' },
    { value: 'other', label: 'Other Documented Verification' }
  ],
  
  // Proof of Address verification methods
  proof_of_address: [
    { value: 'original_document_seen', label: 'Original Document Seen' },
    { value: 'uploaded_copy_verified', label: 'Uploaded Copy Verified' },
    { value: 'certified_copy_verified', label: 'Certified Copy Verified' },
    { value: 'other', label: 'Other Documented Verification' }
  ],
  address_verification: [
    { value: 'original_seen', label: 'Original document seen in person' },
    { value: 'uploaded_copy', label: 'Uploaded copy reviewed' },
    { value: 'certified_copy', label: 'Certified copy reviewed' },
    { value: 'other', label: 'Other documented verification' }
  ],
  
  // Reference verification methods
  reference_1: [
    { value: 'email_verified', label: 'Reference verified by email' },
    { value: 'phone_verified', label: 'Reference verified by phone' },
    { value: 'written_reference', label: 'Written reference reviewed' },
    { value: 'employer_portal', label: 'Employer verification portal' },
    { value: 'other', label: 'Other documented verification' }
  ],
  reference_2: [
    { value: 'email_verified', label: 'Reference verified by email' },
    { value: 'phone_verified', label: 'Reference verified by phone' },
    { value: 'written_reference', label: 'Written reference reviewed' },
    { value: 'employer_portal', label: 'Employer verification portal' },
    { value: 'other', label: 'Other documented verification' }
  ],
  
  // Training / Qualifications verification methods
  training: [
    { value: 'certificate_reviewed', label: 'Certificate reviewed' },
    { value: 'provider_portal', label: 'Provider portal checked' },
    { value: 'uploaded_copy', label: 'Uploaded copy reviewed' },
    { value: 'register_checked', label: 'Third-party register checked' },
    { value: 'other', label: 'Other documented verification' }
  ],
  
  // NMC Registration verification (for nurses)
  nmc_registration: [
    { value: 'register_checked', label: 'NMC register checked online' },
    { value: 'pin_verified', label: 'NMC PIN verified' },
    { value: 'certificate_reviewed', label: 'Registration certificate reviewed' },
    { value: 'other', label: 'Other documented verification' }
  ],
  
  // Default fallback for any unrecognized check types
  default: [
    { value: 'original_seen', label: 'Original document seen in person' },
    { value: 'certified_copy', label: 'Certified copy reviewed' },
    { value: 'uploaded_copy', label: 'Uploaded copy reviewed' },
    { value: 'register_checked', label: 'Third-party register checked' },
    { value: 'other', label: 'Other documented verification' }
  ]
};

const CHECK_OUTCOMES = [
  { value: 'verified', label: 'Verified', color: 'text-green-600' },
  { value: 'failed', label: 'Failed', color: 'text-red-600' },
  { value: 'follow_up_required', label: 'Follow-up Required', color: 'text-amber-600' }
];

const SOURCE_STATUS_TYPES = [
  { value: 'share_code', label: 'Share Code Check Result' },
  { value: 'digital_status', label: 'Digital Status (eVisa)' },
  { value: 'settled_status', label: 'Settled Status (EU Settlement Scheme)' },
  { value: 'pre_settled_status', label: 'Pre-Settled Status (EU Settlement Scheme)' },
  { value: 'uk_citizen', label: 'UK Citizen (Passport/Birth Certificate)' },
  { value: 'irish_citizen', label: 'Irish Citizen' },
  { value: 'brp_valid', label: 'BRP - Valid (with online check)' },
  { value: 'brp_expired', label: 'BRP - Expired (online check required)' },
  { value: 'passport_endorsement', label: 'Passport Endorsement' },
  { value: 'work_visa', label: 'Work Visa' },
  { value: 'student_visa', label: 'Student Visa (with work permission)' },
  { value: 'other', label: 'Other' }
];

// RTW-SPECIFIC GUIDANCE based on verification method
const RTW_METHOD_GUIDANCE = {
  home_office_online_check: {
    title: 'Home Office Online Check (Share Code)',
    guidance: 'You MUST verify this online via GOV.UK using the applicant\'s share code.',
    steps: [
      'Ask applicant for their 9-character share code',
      'Visit gov.uk/view-right-to-work',
      'Enter share code and applicant\'s date of birth',
      'Save/screenshot the result as proof'
    ],
    proofRequired: true,
    proofLabel: 'Home Office check result (screenshot/PDF)',
    link: 'https://www.gov.uk/view-right-to-work',
    badgeColor: 'bg-blue-100 text-blue-800 border-blue-200',
    route: 'home_office_online_check'
  },
  manual_passport_uk_irish: {
    title: 'Manual Check - UK/Irish Passport',
    guidance: 'Valid for UK/Irish citizens only. This is a List A document - unlimited right to work.',
    steps: [
      'Check passport is genuine (security features)',
      'Verify photo matches the applicant',
      'Check passport is current or expired (both valid for UK/Irish)',
      'Record passport number and any expiry date',
      'Take a clear copy for records',
      'Apply "Original Document Seen" verification stamp'
    ],
    proofRequired: false,
    stampRequired: true,
    stampType: 'original_seen',
    badgeColor: 'bg-green-100 text-green-800 border-green-200',
    route: 'manual_list_a_check',
    unlimited: true
  },
  manual_list_a_document: {
    title: 'Manual Check - List A Document',
    guidance: 'List A documents prove unlimited right to work in the UK.',
    steps: [
      'Verify document is genuine with security features',
      'Check document relates to the applicant',
      'Acceptable documents: UK/Irish passport (current/expired), Birth certificate + NI proof, Certificate of Registration/Naturalisation + NI proof, Indefinite Leave documents',
      'Take a clear copy for records',
      'Apply appropriate verification stamp'
    ],
    proofRequired: false,
    stampRequired: true,
    stampType: 'original_seen',
    badgeColor: 'bg-green-100 text-green-800 border-green-200',
    route: 'manual_list_a_check',
    unlimited: true
  },
  manual_list_b_group_1: {
    title: 'Manual Check - List B Group 1 (Time-Limited)',
    guidance: 'List B Group 1 documents prove time-limited right to work. FOLLOW-UP REQUIRED before expiry.',
    warning: 'You MUST set a follow-up date before the permission expires. The employee cannot work beyond this date without re-verification.',
    steps: [
      'Check document is genuine with security features',
      'Verify visa/permission is current (not expired)',
      'Record the permission END DATE carefully',
      'Check for any work restrictions',
      'Set follow-up date 28 days BEFORE permission expires',
      'Take a clear copy for records'
    ],
    proofRequired: false,
    stampRequired: true,
    stampType: 'original_seen',
    badgeColor: 'bg-amber-100 text-amber-800 border-amber-200',
    route: 'manual_list_b_group_1_check',
    unlimited: false,
    requiresFollowUp: true
  },
  manual_list_b_group_2_ecs: {
    title: 'Manual Check - List B Group 2 / ECS',
    guidance: 'For applicants with pending immigration applications. Requires Employer Checking Service verification.',
    warning: 'You MUST obtain a Positive Verification Notice (PVN) from the Home Office before employing.',
    steps: [
      'Check Certificate of Application or ARC card',
      'Submit request to Employer Checking Service (ECS)',
      'Wait for Positive Verification Notice (PVN)',
      'Record the PVN reference number',
      'Set 6-month follow-up for repeat ECS check',
      'Do NOT employ without valid PVN'
    ],
    proofRequired: true,
    proofLabel: 'Positive Verification Notice (PVN)',
    link: 'https://www.gov.uk/employee-immigration-employment-status',
    badgeColor: 'bg-purple-100 text-purple-800 border-purple-200',
    route: 'manual_list_b_group_2_check',
    unlimited: false,
    requiresFollowUp: true,
    requiresECS: true
  },
  idsp_check: {
    title: 'Digital Verification Service (IDSP)',
    guidance: 'Use an accredited Identity Service Provider for digital verification of British/Irish passports.',
    steps: [
      'Use an accredited IDSP from the government list',
      'IDSP can only verify British or Irish passports/passport cards',
      'Follow their digital verification process',
      'Retain the IDSP verification certificate',
      'Certificate must confirm document validity'
    ],
    proofRequired: true,
    proofLabel: 'IDSP Verification Certificate',
    badgeColor: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    route: 'digital_verification_service_check',
    unlimited: true
  },
  ecs_pvn_check: {
    title: 'Employer Checking Service (PVN)',
    guidance: 'Use when applicant cannot provide acceptable documents or has pending immigration application.',
    warning: 'You MUST NOT employ someone based solely on their word. A valid PVN is required.',
    steps: [
      'Submit request via gov.uk/employee-immigration-employment-status',
      'Wait for Home Office response (usually within 5 working days)',
      'Receive Positive Verification Notice (PVN)',
      'Record the PVN reference number',
      'Set 6-month follow-up for repeat check',
      'Keep the PVN on file'
    ],
    proofRequired: true,
    proofLabel: 'Positive Verification Notice (PVN)',
    link: 'https://www.gov.uk/employee-immigration-employment-status',
    badgeColor: 'bg-purple-100 text-purple-800 border-purple-200',
    route: 'ecs_pvn_check',
    unlimited: false,
    requiresFollowUp: true
  }
};

// Map check types to requirement IDs for proof file storage
const CHECK_TYPE_TO_REQUIREMENT = {
  right_to_work_check: 'right_to_work_check',
  dbs_status_check: 'dbs_status_check',
  identity_verification: 'identity_verification',
  address_verification: 'address_verification'
};

/**
 * RecordCheckDialog - Dialog for recording employer verification checks
 * 
 * COMPLIANCE-CRITICAL: Requires proof file upload before check can be saved.
 * 
 * Supports:
 * - Right to Work Check
 * - DBS Status Check
 * - Identity Verification
 * - Address Verification
 */
export default function RecordCheckDialog({
  open,
  onClose,
  employeeId,
  checkType,
  onComplete
}) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [formData, setFormData] = useState({
    method: '',
    checked_at: new Date().toISOString().split('T')[0],
    outcome: 'verified',
    source_status_type: '',
    follow_up_due_at: '',
    review_due_at: '',
    certificate_number: '',
    notes: ''
  });
  
  // Proof file state - COMPLIANCE CRITICAL
  const [proofFile, setProofFile] = useState(null);
  const [uploadedProofId, setUploadedProofId] = useState(null);
  const [uploadedProofName, setUploadedProofName] = useState(null);
  const fileInputRef = useRef(null);
  
  const { token } = useAuth();

  // Get methods for this check type with fallback to default
  const methods = CHECK_METHODS[checkType] || CHECK_METHODS.default;
  
  // Get title based on check type
  const getTitle = () => {
    switch (checkType) {
      case 'right_to_work_check': return 'Record Right to Work Check';
      case 'dbs_status_check': return 'Record DBS Status Check';
      case 'identity_verification': return 'Record Identity Verification';
      case 'address_verification': return 'Record Address Verification';
      default: return 'Record Check';
    }
  };

  // Get endpoint based on check type
  const getEndpoint = () => {
    switch (checkType) {
      case 'right_to_work':
      case 'right_to_work_check': 
        return `${API}/employees/${employeeId}/right-to-work/check`;
      case 'dbs':
      case 'dbs_status_check': 
        return `${API}/employees/${employeeId}/dbs/check`;
      case 'identity':
      case 'identity_verification': 
        return `${API}/employees/${employeeId}/identity/check`;
      case 'proof_of_address':
      case 'address_verification': 
        return `${API}/employees/${employeeId}/address/check`;
      default: 
        console.warn(`Unknown check type: ${checkType}`);
        return null;
    }
  };

  // Handle proof file selection
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Invalid file type. Please upload PDF, JPG, or PNG.');
      return;
    }

    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File too large. Maximum size is 10MB.');
      return;
    }

    setProofFile(file);
  };

  // Upload proof file to employee_documents
  const uploadProofFile = async () => {
    if (!proofFile) return null;

    setIsUploading(true);
    try {
      const formDataUpload = new FormData();
      formDataUpload.append('file', proofFile);
      formDataUpload.append('requirement_id', CHECK_TYPE_TO_REQUIREMENT[checkType] || checkType);
      formDataUpload.append('document_type', 'verification_proof');
      formDataUpload.append('document_label', `${getTitle()} - Proof`);

      const response = await axios.post(
        `${API}/employees/${employeeId}/upload-document`,
        formDataUpload,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      const docId = response.data?.document_id || response.data?.id;
      setUploadedProofId(docId);
      setUploadedProofName(proofFile.name);
      toast.success('Proof file uploaded successfully');
      return docId;
    } catch (err) {
      console.error('Failed to upload proof file:', err);
      toast.error(err.response?.data?.detail || 'Failed to upload proof file');
      return null;
    } finally {
      setIsUploading(false);
    }
  };

  // Remove uploaded proof
  const handleRemoveProof = () => {
    setProofFile(null);
    setUploadedProofId(null);
    setUploadedProofName(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async () => {
    const endpoint = getEndpoint();
    if (!endpoint) {
      toast.error('Invalid check type');
      return;
    }

    // Validation
    if (!formData.method) {
      toast.error('Please select a check method');
      return;
    }

    // RTW-SPECIFIC VALIDATION: Enforce proof upload for online check methods
    const isRTW = checkType === 'right_to_work_check' || checkType === 'right_to_work';
    const onlineCheckMethods = ['home_office_online_check', 'manual_list_b_group_2_ecs', 'ecs_pvn_check', 'idsp_check'];
    const methodGuidance = RTW_METHOD_GUIDANCE[formData.method];
    const requiresProof = isRTW && (onlineCheckMethods.includes(formData.method) || methodGuidance?.proofRequired);
    
    // COMPLIANCE-CRITICAL: Require proof file for online/ECS methods
    if (!proofFile && !uploadedProofId) {
      if (requiresProof) {
        const proofLabel = methodGuidance?.proofLabel || 'verification proof';
        toast.error(`This method requires ${proofLabel}. This is a legal requirement.`);
        return;
      }
      // For manual checks, proof is still required but with different messaging
      toast.error('Upload proof of check before saving. This is required for compliance.');
      return;
    }
    
    // RTW-SPECIFIC: Block expired BRP without online check
    if (isRTW && formData.source_status_type === 'brp_expired') {
      toast.error('Expired BRP is not valid Right to Work evidence. Please use the Home Office Online Check (Share Code) method instead.');
      return;
    }

    setIsSubmitting(true);
    try {
      // Upload proof file first if not already uploaded
      let proofDocId = uploadedProofId;
      if (proofFile && !uploadedProofId) {
        proofDocId = await uploadProofFile();
        if (!proofDocId) {
          setIsSubmitting(false);
          return; // Upload failed, abort
        }
      }

      // Build payload with evidence_document_id linking
      const payload = {
        method: formData.method,
        checked_at: formData.checked_at,
        outcome: formData.outcome,
        notes: formData.notes || null,
        evidence_document_id: proofDocId // CRITICAL: Link check to proof file
      };

      // Add type-specific fields
      if (checkType === 'right_to_work_check') {
        payload.source_status_type = formData.source_status_type || null;
        payload.follow_up_due_at = formData.follow_up_due_at || null;
      }
      
      if (checkType === 'dbs_status_check') {
        payload.review_due_at = formData.review_due_at || null;
        payload.certificate_number = formData.certificate_number || null;
      }

      await axios.post(endpoint, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });

      toast.success('Verification check recorded with proof');
      if (onComplete) onComplete();
      handleClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to record check');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setFormData({
      method: '',
      checked_at: new Date().toISOString().split('T')[0],
      outcome: 'verified',
      source_status_type: '',
      follow_up_due_at: '',
      review_due_at: '',
      certificate_number: '',
      notes: ''
    });
    setProofFile(null);
    setUploadedProofId(null);
    setUploadedProofName(null);
    if (onClose) onClose();
  };

  const hasProof = proofFile || uploadedProofId;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-white sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            {getTitle()}
          </DialogTitle>
          <DialogDescription>
            Record the employer verification check with proof. Both the check record and proof file are required for compliance.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* COMPLIANCE ALERT */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-amber-800">
                <p className="font-medium">Compliance Requirement</p>
                <p className="text-xs mt-0.5">Upload proof of the check (e.g., Home Office screenshot, DBS Update Service result) before saving.</p>
              </div>
            </div>
          </div>

          {/* PROOF FILE UPLOAD - MANDATORY */}
          <div className="space-y-2">
            <Label className="flex items-center gap-1">
              Proof of Check *
              {hasProof && <CheckCircle className="h-4 w-4 text-green-600" />}
            </Label>
            
            {!hasProof ? (
              <div 
                className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-primary cursor-pointer transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-8 w-8 mx-auto text-gray-400 mb-2" />
                <p className="text-sm text-gray-600">Click to upload proof file</p>
                <p className="text-xs text-gray-400 mt-1">PDF, JPG, PNG (max 10MB)</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={handleFileSelect}
                />
              </div>
            ) : (
              <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="text-sm font-medium text-green-800">
                      {uploadedProofName || proofFile?.name}
                    </p>
                    <p className="text-xs text-green-600">
                      {uploadedProofId ? 'Uploaded' : 'Ready to upload'}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRemoveProof}
                  className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>

          {/* Method */}
          <div className="space-y-2">
            <Label>Check Method *</Label>
            <Select 
              value={formData.method} 
              onValueChange={(v) => setFormData(prev => ({ ...prev, method: v }))}
            >
              <SelectTrigger className="rounded-lg">
                <SelectValue placeholder="Select check method" />
              </SelectTrigger>
              <SelectContent>
                {methods.map(method => (
                  <SelectItem key={method.value} value={method.value}>
                    <span className="flex items-center gap-2">
                      {method.label}
                      {method.recommended && (
                        <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">Recommended</span>
                      )}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* RTW-SPECIFIC GUIDANCE BOX - Shows method-specific instructions */}
          {(checkType === 'right_to_work_check' || checkType === 'right_to_work') && formData.method && RTW_METHOD_GUIDANCE[formData.method] && (
            <div className={`p-4 rounded-lg border ${RTW_METHOD_GUIDANCE[formData.method].badgeColor || 'bg-blue-50 border-blue-200'}`}>
              <div className="space-y-3">
                <div className="flex items-start gap-2">
                  <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium text-sm">{RTW_METHOD_GUIDANCE[formData.method].title}</p>
                    <p className="text-xs mt-1">{RTW_METHOD_GUIDANCE[formData.method].guidance}</p>
                  </div>
                </div>
                
                {/* Warning (e.g., BRP expiry) */}
                {RTW_METHOD_GUIDANCE[formData.method].warning && (
                  <div className="p-2 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                      <p className="text-xs text-red-700 font-medium">{RTW_METHOD_GUIDANCE[formData.method].warning}</p>
                    </div>
                  </div>
                )}
                
                {/* Steps */}
                {RTW_METHOD_GUIDANCE[formData.method].steps && (
                  <div className="space-y-1">
                    <p className="text-xs font-medium">Steps:</p>
                    <ol className="text-xs space-y-1 list-decimal list-inside">
                      {RTW_METHOD_GUIDANCE[formData.method].steps.map((step, i) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}
                
                {/* GOV.UK Link */}
                {RTW_METHOD_GUIDANCE[formData.method].link && (
                  <a 
                    href={RTW_METHOD_GUIDANCE[formData.method].link} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-blue-700 hover:text-blue-900 font-medium"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Open GOV.UK verification page
                  </a>
                )}
                
                {/* Proof requirement indicator */}
                {RTW_METHOD_GUIDANCE[formData.method].proofRequired && (
                  <div className="flex items-center gap-2 pt-2 border-t border-current/10">
                    <Upload className="h-3 w-3" />
                    <span className="text-xs font-medium">
                      Required proof: {RTW_METHOD_GUIDANCE[formData.method].proofLabel}
                    </span>
                  </div>
                )}
                
                {/* Stamp requirement indicator */}
                {RTW_METHOD_GUIDANCE[formData.method].stampRequired && (
                  <div className="flex items-center gap-2 pt-2 border-t border-current/10">
                    <CheckCircle className="h-3 w-3" />
                    <span className="text-xs font-medium">
                      Apply verification stamp: "{RTW_METHOD_GUIDANCE[formData.method].stampType === 'original_seen' ? 'Original Document Seen' : 'Copy Verified'}"
                    </span>
                  </div>
                )}
                
                {/* Follow-up requirement indicator */}
                {RTW_METHOD_GUIDANCE[formData.method].requiresFollowUp && (
                  <div className="flex items-center gap-2 pt-2 border-t border-current/10">
                    <AlertTriangle className="h-3 w-3 text-amber-600" />
                    <span className="text-xs font-medium text-amber-700">
                      Time-limited permission - Follow-up date REQUIRED
                    </span>
                  </div>
                )}
                
                {/* Unlimited right indicator */}
                {RTW_METHOD_GUIDANCE[formData.method].unlimited && (
                  <div className="flex items-center gap-2 pt-2 border-t border-current/10">
                    <CheckCircle className="h-3 w-3 text-green-600" />
                    <span className="text-xs font-medium text-green-700">
                      Unlimited right to work - No follow-up required
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Checked At */}
          <div className="space-y-2">
            <Label>Date Checked *</Label>
            <Input
              type="date"
              value={formData.checked_at}
              onChange={(e) => setFormData(prev => ({ ...prev, checked_at: e.target.value }))}
              className="rounded-lg"
            />
          </div>

          {/* Outcome */}
          <div className="space-y-2">
            <Label>Outcome *</Label>
            <Select 
              value={formData.outcome} 
              onValueChange={(v) => setFormData(prev => ({ ...prev, outcome: v }))}
            >
              <SelectTrigger className="rounded-lg">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHECK_OUTCOMES.map(outcome => (
                  <SelectItem key={outcome.value} value={outcome.value}>
                    <span className={outcome.color}>{outcome.label}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* RTW-specific: Source Status Type */}
          {checkType === 'right_to_work_check' && (
            <div className="space-y-2">
              <Label>Source Status Type</Label>
              <Select 
                value={formData.source_status_type} 
                onValueChange={(v) => setFormData(prev => ({ ...prev, source_status_type: v }))}
              >
                <SelectTrigger className="rounded-lg">
                  <SelectValue placeholder="Select status type" />
                </SelectTrigger>
                <SelectContent>
                  {SOURCE_STATUS_TYPES.map(type => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* RTW-specific: Follow-up Due */}
          {checkType === 'right_to_work_check' && (
            <div className="space-y-2">
              <Label>Follow-up Due Date</Label>
              <Input
                type="date"
                value={formData.follow_up_due_at}
                onChange={(e) => setFormData(prev => ({ ...prev, follow_up_due_at: e.target.value }))}
                className="rounded-lg"
              />
              <p className="text-xs text-text-muted">
                For time-limited permissions, set when the next check is due
              </p>
            </div>
          )}

          {/* DBS-specific: Certificate Number */}
          {checkType === 'dbs_status_check' && (
            <div className="space-y-2">
              <Label>Certificate Number</Label>
              <Input
                value={formData.certificate_number}
                onChange={(e) => setFormData(prev => ({ ...prev, certificate_number: e.target.value }))}
                placeholder="12-digit certificate number"
                className="rounded-lg"
              />
            </div>
          )}

          {/* DBS-specific: Review Due */}
          {checkType === 'dbs_status_check' && (
            <div className="space-y-2">
              <Label>Review Due Date</Label>
              <Input
                type="date"
                value={formData.review_due_at}
                onChange={(e) => setFormData(prev => ({ ...prev, review_due_at: e.target.value }))}
                className="rounded-lg"
              />
              <p className="text-xs text-text-muted">
                Internal policy date for next review (DBS certificates don't have a statutory expiry)
              </p>
            </div>
          )}

          {/* Notes */}
          <div className="space-y-2">
            <Label>Notes</Label>
            <Textarea
              value={formData.notes}
              onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
              placeholder="Any additional notes about this check..."
              className="rounded-lg min-h-[80px]"
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleClose} className="rounded-xl">
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || isUploading || !formData.method || !hasProof}
            className="bg-primary hover:bg-primary-hover text-white rounded-xl"
            data-testid="record-check-submit"
          >
            {isSubmitting || isUploading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                {isUploading ? 'Uploading...' : 'Saving...'}
              </>
            ) : (
              <>
                <Shield className="h-4 w-4 mr-2" />
                Record Check
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
