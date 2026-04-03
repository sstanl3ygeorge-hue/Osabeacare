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
import { Loader2, Shield, Upload, FileText, X, CheckCircle, AlertTriangle, Info, ExternalLink, RefreshCw } from 'lucide-react';

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
  onComplete,
  // Evidence status props for validation
  hasAcceptedEvidence = false,
  hasStampedEvidence = false,
  acceptedEvidenceCount = 0
}) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [formData, setFormData] = useState({
    method: '',
    checked_at: new Date().toISOString().split('T')[0],
    outcome: 'verified',
    source_status_type: '',
    follow_up_due_at: '',
    review_due_at: '',
    certificate_number: '',
    notes: '',
    // RTW Result Panel fields
    permission_type: '',  // e.g., British Citizen, Skilled Worker, Pre-Settled Status
    permission_start_date: '',
    permission_end_date: '',
    reference_number: '',
    share_code: '',
    restrictions: '',
    hours_limit: '',
    is_indefinite: false,
    follow_up_required: false,
    document_type: '',
    // DBS Result Panel fields
    dbs_level: '',
    certificate_issue_date: '',
    name_on_certificate: '',
    workforce: '',
    update_service_registered: false,
    update_service_status: '',
    last_status_check_date: '',
    update_service_check_result: '',
    recheck_required: true,
    next_recheck_date: '',
    result_status: '',
    information_present: false,
    result_summary: ''
  });
  
  // Extraction state for RTW and DBS
  const [extractionResult, setExtractionResult] = useState(null);
  const [extractionIssues, setExtractionIssues] = useState([]);
  
  // Proof file state - COMPLIANCE CRITICAL
  const [proofFile, setProofFile] = useState(null);
  const [uploadedProofId, setUploadedProofId] = useState(null);
  const [uploadedProofName, setUploadedProofName] = useState(null);
  const fileInputRef = useRef(null);
  
  const { token } = useAuth();

  // Check if RTW check
  const isRTW = checkType === 'right_to_work_check' || checkType === 'right_to_work';
  
  // Check if DBS check
  const isDBS = checkType === 'dbs_status_check' || checkType === 'dbs';

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

  // Handle proof file selection - AUTO-EXTRACT for RTW
  const handleFileSelect = async (e) => {
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
    
    // AUTO-EXTRACT: Automatically extract fields when proof file is selected
    if (isRTW) {
      toast.info('Extracting RTW fields from document...', { duration: 2000 });
      await extractRTWFieldsFromFile(file);
    } else if (isDBS) {
      toast.info('Extracting DBS fields from document...', { duration: 2000 });
      await extractDBSFieldsFromFile(file);
    }
  };

  // Extract DBS fields from a file using AI Vision
  const extractDBSFieldsFromFile = async (file) => {
    setIsExtracting(true);
    setExtractionResult(null);
    setExtractionIssues([]);

    try {
      // Convert file to base64
      const base64Data = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result.split(',')[1]);
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsDataURL(file);
      });

      const response = await axios.post(
        `${API}/dbs/extract`,
        {
          file_base64: base64Data,
          file_type: file.type
        },
        {
          headers: { Authorization: `Bearer ${token}` },
          params: { employee_id: employeeId }
        }
      );

      if (response.data?.success && response.data?.extraction) {
        const { fields, issues } = response.data.extraction;
        setExtractionResult(fields);
        setExtractionIssues(issues || []);
        
        // Log extraction results for debugging
        console.log('DBS Extraction result:', { fields, issues });

        // Auto-populate form fields from extraction
        setFormData(prev => ({
          ...prev,
          certificate_number: fields.certificate_number || prev.certificate_number,
          dbs_level: fields.dbs_level || prev.dbs_level,
          certificate_issue_date: fields.issue_date || prev.certificate_issue_date,
          name_on_certificate: fields.name_on_certificate || prev.name_on_certificate,
          workforce: fields.workforce || prev.workforce,
          result_status: fields.result_status || prev.result_status,
          information_present: fields.result_status === 'information_present' || prev.information_present,
          result_summary: fields.result_summary || fields.information_summary || prev.result_summary,
          update_service_status: fields.update_service_status || prev.update_service_status,
          update_service_registered: fields.update_service_status === 'active' || prev.update_service_registered,
          last_status_check_date: fields.last_status_check_date || prev.last_status_check_date,
          update_service_check_result: fields.update_service_check_result || prev.update_service_check_result
        }));

        // Check for blockers
        const blockers = (issues || []).filter(i => i.severity === 'blocker');
        const hasExtractedData = Object.keys(fields).some(k => fields[k] !== null && fields[k] !== undefined);
        
        if (blockers.length > 0) {
          toast.error(`Issue found: ${blockers[0].detail}`);
        } else if (hasExtractedData) {
          toast.success('DBS fields extracted - please review and confirm before saving');
        } else {
          toast.warning('Could not extract DBS data – please fill fields manually', { duration: 5000 });
          setExtractionIssues([...issues, {
            code: 'no_data_extracted',
            detail: 'No DBS fields could be extracted from this document. Please fill in the form manually.',
            severity: 'warning'
          }]);
        }
      } else {
        console.warn('DBS Extraction failed:', response.data);
        toast.warning('Could not extract DBS data – please fill fields manually', { duration: 5000 });
        setExtractionIssues([{
          code: 'extraction_failed',
          detail: response.data?.error || 'Extraction service unavailable. Please fill in the form manually.',
          severity: 'warning'
        }]);
      }
    } catch (err) {
      console.error('DBS Extraction error:', err);
      toast.info('Auto-extraction unavailable. Please fill in fields manually.');
    } finally {
      setIsExtracting(false);
    }
  };

  // Extract RTW fields from a file using AI Vision
  const extractRTWFieldsFromFile = async (file) => {
    setIsExtracting(true);
    setExtractionResult(null);
    setExtractionIssues([]);

    try {
      // Convert file to base64
      const base64Data = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result.split(',')[1]);
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsDataURL(file);
      });

      const response = await axios.post(
        `${API}/rtw/extract`,
        {
          file_base64: base64Data,
          file_type: file.type
        },
        {
          headers: { Authorization: `Bearer ${token}` },
          params: { employee_id: employeeId }
        }
      );

      if (response.data?.success && response.data?.extraction) {
        const { fields, issues } = response.data.extraction;
        setExtractionResult(fields);
        setExtractionIssues(issues || []);
        
        // Log extraction results for debugging
        console.log('RTW Extraction result:', { fields, issues });

        // Auto-populate form fields from extraction
        setFormData(prev => ({
          ...prev,
          checked_at: fields.check_date || prev.checked_at,
          permission_start_date: fields.permission_start_date || prev.permission_start_date,
          permission_end_date: fields.permission_end_date || prev.permission_end_date,
          reference_number: fields.reference_number || prev.reference_number,
          share_code: fields.share_code || prev.share_code,
          restrictions: fields.restrictions || prev.restrictions,
          hours_limit: fields.hours_limit?.toString() || prev.hours_limit,
          is_indefinite: fields.is_indefinite ?? prev.is_indefinite,
          follow_up_required: fields.requires_followup ?? prev.follow_up_required,
          document_type: fields.document_type || prev.document_type,
          source_status_type: fields.permission_type ? mapPermissionTypeToStatus(fields.permission_type) : prev.source_status_type
        }));

        // Check for blockers
        const blockers = (issues || []).filter(i => i.severity === 'blocker');
        const hasExtractedData = Object.keys(fields).some(k => fields[k] !== null && fields[k] !== undefined);
        
        if (blockers.length > 0) {
          toast.error(`Issue found: ${blockers[0].detail}`);
        } else if (hasExtractedData) {
          toast.success('Fields extracted - please review and confirm before saving');
        } else {
          // No data extracted - show warning
          toast.warning('Could not extract RTW data – please fill fields manually', { duration: 5000 });
          setExtractionIssues([...issues, {
            code: 'no_data_extracted',
            detail: 'No RTW fields could be extracted from this document. Please fill in the form manually.',
            severity: 'warning'
          }]);
        }
      } else {
        // Extraction failed - show clear fallback message
        console.warn('RTW Extraction failed:', response.data);
        toast.warning('Could not extract RTW data – please fill fields manually', { duration: 5000 });
        setExtractionIssues([{
          code: 'extraction_failed',
          detail: response.data?.error || 'Extraction service unavailable. Please fill in the form manually.',
          severity: 'warning'
        }]);
      }
    } catch (err) {
      console.error('Extraction error:', err);
      toast.info('Auto-extraction unavailable. Please fill in fields manually.');
    } finally {
      setIsExtracting(false);
    }
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
    setExtractionResult(null);
    setExtractionIssues([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Re-extract fields (manual trigger for retry) - works for both RTW and DBS
  const handleReExtract = async () => {
    if (!proofFile) return;
    if (isRTW) {
      await extractRTWFieldsFromFile(proofFile);
    } else if (isDBS) {
      await extractDBSFieldsFromFile(proofFile);
    }
  };

  // Map extracted permission type to source_status_type value
  const mapPermissionTypeToStatus = (permissionType) => {
    if (!permissionType) return '';
    const pt = permissionType.toLowerCase();
    if (pt.includes('settled') && !pt.includes('pre')) return 'settled_status';
    if (pt.includes('pre-settled') || pt.includes('presettled')) return 'pre_settled_status';
    if (pt.includes('uk citizen') || pt.includes('british')) return 'uk_citizen';
    if (pt.includes('irish')) return 'irish_citizen';
    if (pt.includes('evisa') || pt.includes('digital')) return 'digital_status';
    if (pt.includes('student')) return 'student_visa';
    if (pt.includes('work visa')) return 'work_visa';
    if (pt.includes('brp')) return 'brp_valid';
    return 'other';
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
      if (checkType === 'right_to_work_check' || checkType === 'right_to_work') {
        // Core RTW fields
        payload.source_status_type = formData.source_status_type || null;
        payload.follow_up_due_at = formData.follow_up_due_at || null;
        
        // RTW Result Panel fields (3-layer model)
        payload.permission_type = formData.permission_type || null;  // e.g., British Citizen, Skilled Worker
        payload.permission_start_date = formData.permission_start_date || null;
        payload.permission_end_date = formData.permission_end_date || null;
        payload.reference_number = formData.reference_number || null;
        payload.share_code = formData.share_code || null;
        payload.restrictions = formData.restrictions || null;
        payload.hours_limit = formData.hours_limit ? parseInt(formData.hours_limit) : null;
        payload.is_indefinite = formData.is_indefinite || false;
        payload.follow_up_required = formData.follow_up_required || false;
        payload.document_type = formData.document_type || null;
        
        // Route based on method
        const methodDef = methods.find(m => m.value === formData.method);
        payload.route = methodDef?.route || formData.method;
      }
      
      if (checkType === 'dbs_status_check' || checkType === 'dbs') {
        // DBS Result Panel fields (3-layer model)
        payload.dbs_level = formData.dbs_level || null;
        payload.certificate_number = formData.certificate_number || null;
        payload.certificate_issue_date = formData.certificate_issue_date || null;
        payload.name_on_certificate = formData.name_on_certificate || null;
        payload.workforce = formData.workforce || null;
        
        // Update Service specific
        payload.update_service_registered = formData.update_service_registered || false;
        payload.update_service_status = formData.update_service_status || null;
        payload.last_status_check_date = formData.last_status_check_date || null;
        payload.update_service_check_result = formData.update_service_check_result || null;
        
        // Recheck tracking
        payload.recheck_required = formData.recheck_required !== false; // Default true
        payload.next_recheck_date = formData.next_recheck_date || formData.review_due_at || null;
        payload.review_due_at = formData.review_due_at || formData.next_recheck_date || null;
        
        // Result details
        payload.result_status = formData.result_status || (formData.information_present ? 'information_present' : 'clear');
        payload.information_present = formData.information_present || false;
        payload.result_summary = formData.result_summary || null;
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
      notes: '',
      // RTW Result Panel fields
      permission_type: '',
      permission_start_date: '',
      permission_end_date: '',
      reference_number: '',
      share_code: '',
      restrictions: '',
      hours_limit: '',
      is_indefinite: false,
      follow_up_required: false,
      document_type: '',
      // DBS Result Panel fields
      dbs_level: '',
      certificate_issue_date: '',
      name_on_certificate: '',
      workforce: '',
      update_service_registered: false,
      update_service_status: '',
      last_status_check_date: '',
      update_service_check_result: '',
      recheck_required: true,
      next_recheck_date: '',
      result_status: '',
      information_present: false,
      result_summary: ''
    });
    setProofFile(null);
    setUploadedProofId(null);
    setUploadedProofName(null);
    setExtractionResult(null);
    setExtractionIssues([]);
    if (onClose) onClose();
  };

  const hasProof = proofFile || uploadedProofId;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-white sm:max-w-xl max-h-[90vh] overflow-y-auto">
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
          {/* EVIDENCE WARNING - Show if no accepted evidence */}
          {!hasAcceptedEvidence && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-red-800">
                  <p className="font-medium">No accepted evidence</p>
                  <p className="text-xs mt-0.5">You should accept at least one evidence file before recording the verification check.</p>
                </div>
              </div>
            </div>
          )}
          
          {/* STAMP WARNING - Show if evidence accepted but not stamped */}
          {hasAcceptedEvidence && !hasStampedEvidence && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-amber-800">
                  <p className="font-medium">No stamped evidence</p>
                  <p className="text-xs mt-0.5">Consider applying a verification stamp (Original Seen, Copy Verified, etc.) to accepted evidence files for audit trail.</p>
                </div>
              </div>
            </div>
          )}
          
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

          {/* Extraction Status & Re-extract Option - RTW and DBS */}
          {(isRTW || isDBS) && hasProof && (
            <div className="space-y-2">
              {/* Extraction in progress */}
              {isExtracting && (
                <div className="flex items-center gap-2 p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
                  <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                  <span className="text-sm text-indigo-700">Extracting {isRTW ? 'RTW' : 'DBS'} fields from document...</span>
                </div>
              )}
              
              {/* Extraction complete indicator */}
              {!isExtracting && extractionResult && Object.keys(extractionResult).some(k => extractionResult[k] !== null) && (
                <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-sm text-green-700">Fields extracted - please review below</span>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleReExtract}
                    disabled={isExtracting}
                    className="h-7 px-2 text-xs text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50"
                    data-testid={`${isRTW ? 'rtw' : 'dbs'}-re-extract-btn`}
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Re-extract
                  </Button>
                </div>
              )}
              
              {/* Manual extract button - only if no extraction yet and not currently extracting */}
              {!isExtracting && !extractionResult && !uploadedProofId && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleReExtract}
                  disabled={isExtracting}
                  className="w-full h-9 text-sm bg-indigo-50 border-indigo-200 text-indigo-700 hover:bg-indigo-100"
                  data-testid={`${isRTW ? 'rtw' : 'dbs'}-auto-extract-btn`}
                >
                  <FileText className="h-4 w-4 mr-2" />
                  Extract {isRTW ? 'RTW' : 'DBS'} Fields
                </Button>
              )}
            </div>
          )}

          {/* Extraction Issues Warning */}
          {extractionIssues.length > 0 && (
            <div className="space-y-2">
              {extractionIssues.filter(i => i.severity === 'blocker').map((issue, idx) => (
                <div key={idx} className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-red-800">
                      <p className="font-medium">Blocker: {issue.code.replace(/_/g, ' ')}</p>
                      <p className="text-xs mt-0.5">{issue.detail}</p>
                    </div>
                  </div>
                </div>
              ))}
              {extractionIssues.filter(i => i.severity === 'warning').map((issue, idx) => (
                <div key={idx} className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-amber-800">
                      <p className="font-medium">Warning: {issue.code.replace(/_/g, ' ')}</p>
                      <p className="text-xs mt-0.5">{issue.detail}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

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

          {/* ============================================== */}
          {/* RTW RESULT PANEL - Permission Details         */}
          {/* 3-Layer Model: Evidence -> Verification -> Result */}
          {/* ============================================== */}
          {isRTW && (
            <div className="space-y-4 p-4 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-slate-600" />
                <h4 className="text-sm font-semibold text-slate-800">Right to Work Result</h4>
                {extractionResult && (
                  <span className="text-[10px] px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded">
                    AI Extracted
                  </span>
                )}
              </div>
              
              {/* Permission Type - Full width, prominent */}
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Permission Type *</Label>
                <Input
                  value={formData.permission_type}
                  onChange={(e) => setFormData(prev => ({ ...prev, permission_type: e.target.value }))}
                  placeholder="e.g., British Citizen, Skilled Worker, Pre-Settled Status"
                  className="h-9 text-sm rounded-lg"
                  data-testid="rtw-permission-type"
                />
                <p className="text-xs text-text-muted">
                  The immigration status or visa type (e.g., British Citizen, Skilled Worker Visa, Pre-Settled Status)
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                {/* Permission Start Date */}
                <div className="space-y-1">
                  <Label className="text-xs">Permission Start</Label>
                  <Input
                    type="date"
                    value={formData.permission_start_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, permission_start_date: e.target.value }))}
                    className="h-8 text-sm rounded-lg"
                    data-testid="rtw-permission-start"
                  />
                </div>
                
                {/* Permission End Date */}
                <div className="space-y-1">
                  <Label className="text-xs">Permission End / Expiry</Label>
                  <Input
                    type="date"
                    value={formData.permission_end_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, permission_end_date: e.target.value }))}
                    className="h-8 text-sm rounded-lg"
                    data-testid="rtw-permission-end"
                  />
                </div>
                
                {/* Reference Number */}
                <div className="space-y-1">
                  <Label className="text-xs">Reference / PVN Number</Label>
                  <Input
                    value={formData.reference_number}
                    onChange={(e) => setFormData(prev => ({ ...prev, reference_number: e.target.value }))}
                    placeholder="e.g., PVN123456"
                    className="h-8 text-sm rounded-lg"
                    data-testid="rtw-reference-number"
                  />
                </div>
                
                {/* Share Code */}
                <div className="space-y-1">
                  <Label className="text-xs">Share Code</Label>
                  <Input
                    value={formData.share_code}
                    onChange={(e) => setFormData(prev => ({ ...prev, share_code: e.target.value.toUpperCase() }))}
                    placeholder="e.g., ABC123DEF"
                    maxLength={9}
                    className="h-8 text-sm rounded-lg font-mono"
                    data-testid="rtw-share-code"
                  />
                </div>
              </div>
              
              {/* Restrictions */}
              <div className="space-y-1">
                <Label className="text-xs">Work Restrictions</Label>
                <Input
                  value={formData.restrictions}
                  onChange={(e) => setFormData(prev => ({ ...prev, restrictions: e.target.value }))}
                  placeholder="e.g., 20 hours per week during term time"
                  className="h-8 text-sm rounded-lg"
                  data-testid="rtw-restrictions"
                />
              </div>
              
              {/* Hours Limit */}
              {formData.restrictions && (
                <div className="space-y-1">
                  <Label className="text-xs">Hours Limit (per week)</Label>
                  <Input
                    type="number"
                    value={formData.hours_limit}
                    onChange={(e) => setFormData(prev => ({ ...prev, hours_limit: e.target.value }))}
                    placeholder="e.g., 20"
                    min={0}
                    max={48}
                    className="h-8 text-sm rounded-lg w-24"
                    data-testid="rtw-hours-limit"
                  />
                </div>
              )}
              
              {/* Checkboxes for status flags */}
              <div className="flex items-center gap-6 pt-2">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_indefinite}
                    onChange={(e) => setFormData(prev => ({ ...prev, is_indefinite: e.target.checked }))}
                    className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                    data-testid="rtw-is-indefinite"
                  />
                  <span className="text-slate-700">Indefinite right to work</span>
                </label>
                
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.follow_up_required}
                    onChange={(e) => setFormData(prev => ({ ...prev, follow_up_required: e.target.checked }))}
                    className="w-4 h-4 rounded border-gray-300 text-amber-500 focus:ring-amber-500"
                    data-testid="rtw-follow-up-required"
                  />
                  <span className="text-slate-700">Follow-up required</span>
                </label>
              </div>
              
              {/* Auto-calculation hint */}
              {formData.permission_end_date && !formData.follow_up_due_at && (
                <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-xs text-amber-700">
                    <AlertTriangle className="h-3 w-3 inline mr-1" />
                    Permission ends {formData.permission_end_date}. Set a follow-up date 28 days before.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* DBS-specific: Certificate Number */}
          {isDBS && (
            <div className="space-y-2">
              <Label>Certificate Number *</Label>
              <Input
                value={formData.certificate_number}
                onChange={(e) => setFormData(prev => ({ ...prev, certificate_number: e.target.value.replace(/\s/g, '') }))}
                placeholder="12-digit certificate number"
                maxLength={12}
                className="rounded-lg font-mono"
                data-testid="dbs-certificate-number"
              />
              {formData.certificate_number && formData.certificate_number.length !== 12 && (
                <p className="text-xs text-amber-600">Certificate number should be 12 digits</p>
              )}
            </div>
          )}

          {/* DBS-specific: Review Due */}
          {isDBS && (
            <div className="space-y-2">
              <Label>Next Recheck Date</Label>
              <Input
                type="date"
                value={formData.review_due_at || formData.next_recheck_date}
                onChange={(e) => setFormData(prev => ({ ...prev, review_due_at: e.target.value, next_recheck_date: e.target.value }))}
                className="rounded-lg"
                data-testid="dbs-review-due"
              />
              <p className="text-xs text-text-muted">
                Internal policy date for next review (DBS certificates don't have a statutory expiry)
              </p>
            </div>
          )}

          {/* ============================================== */}
          {/* DBS RESULT PANEL - Certificate Details         */}
          {/* 3-Layer Model: Evidence -> Verification -> Result */}
          {/* ============================================== */}
          {isDBS && (
            <div className="space-y-4 p-4 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-slate-600" />
                <h4 className="text-sm font-semibold text-slate-800">DBS Result</h4>
                {extractionResult && (
                  <span className="text-[10px] px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded">
                    AI Extracted
                  </span>
                )}
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                {/* DBS Level */}
                <div className="space-y-1">
                  <Label className="text-xs">DBS Level *</Label>
                  <Select 
                    value={formData.dbs_level} 
                    onValueChange={(v) => setFormData(prev => ({ ...prev, dbs_level: v }))}
                  >
                    <SelectTrigger className="h-8 text-sm rounded-lg" data-testid="dbs-level">
                      <SelectValue placeholder="Select level" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="basic">Basic</SelectItem>
                      <SelectItem value="standard">Standard</SelectItem>
                      <SelectItem value="enhanced">Enhanced</SelectItem>
                      <SelectItem value="enhanced_barred">Enhanced with Barred Lists</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Certificate Issue Date */}
                <div className="space-y-1">
                  <Label className="text-xs">Issue Date</Label>
                  <Input
                    type="date"
                    value={formData.certificate_issue_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, certificate_issue_date: e.target.value }))}
                    className="h-8 text-sm rounded-lg"
                    data-testid="dbs-issue-date"
                  />
                </div>
                
                {/* Name on Certificate */}
                <div className="space-y-1">
                  <Label className="text-xs">Name on Certificate</Label>
                  <Input
                    value={formData.name_on_certificate}
                    onChange={(e) => setFormData(prev => ({ ...prev, name_on_certificate: e.target.value }))}
                    placeholder="As shown on certificate"
                    className="h-8 text-sm rounded-lg"
                    data-testid="dbs-name"
                  />
                </div>
                
                {/* Workforce Type */}
                <div className="space-y-1">
                  <Label className="text-xs">Workforce</Label>
                  <Select 
                    value={formData.workforce} 
                    onValueChange={(v) => setFormData(prev => ({ ...prev, workforce: v }))}
                  >
                    <SelectTrigger className="h-8 text-sm rounded-lg" data-testid="dbs-workforce">
                      <SelectValue placeholder="Select workforce" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="adult">Adult Workforce</SelectItem>
                      <SelectItem value="child">Child Workforce</SelectItem>
                      <SelectItem value="adult_and_child">Adult and Child Workforce</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {/* Update Service Section - only show for dbs_update_service_check method */}
              {formData.method === 'dbs_update_service_check' && (
                <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-lg space-y-3">
                  <div className="flex items-center gap-2">
                    <Shield className="h-3 w-3 text-indigo-600" />
                    <span className="text-xs font-semibold text-indigo-800">Update Service Check</span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    {/* Update Service Status */}
                    <div className="space-y-1">
                      <Label className="text-xs">Update Service Status</Label>
                      <Select 
                        value={formData.update_service_status} 
                        onValueChange={(v) => setFormData(prev => ({ 
                          ...prev, 
                          update_service_status: v,
                          update_service_registered: v === 'active'
                        }))}
                      >
                        <SelectTrigger className="h-8 text-sm rounded-lg" data-testid="dbs-update-status">
                          <SelectValue placeholder="Select status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="active">Active (Registered)</SelectItem>
                          <SelectItem value="not_registered">Not Registered</SelectItem>
                          <SelectItem value="expired">Expired</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    {/* Last Status Check Date */}
                    <div className="space-y-1">
                      <Label className="text-xs">Check Date</Label>
                      <Input
                        type="date"
                        value={formData.last_status_check_date}
                        onChange={(e) => setFormData(prev => ({ ...prev, last_status_check_date: e.target.value }))}
                        className="h-8 text-sm rounded-lg"
                        data-testid="dbs-last-check-date"
                      />
                    </div>
                  </div>
                  
                  {/* Update Service Check Result */}
                  <div className="space-y-1">
                    <Label className="text-xs">Check Result</Label>
                    <Select 
                      value={formData.update_service_check_result} 
                      onValueChange={(v) => setFormData(prev => ({ ...prev, update_service_check_result: v }))}
                    >
                      <SelectTrigger className="h-8 text-sm rounded-lg" data-testid="dbs-check-result">
                        <SelectValue placeholder="Select result" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="no_change">No change to disclose</SelectItem>
                        <SelectItem value="changed">Changed - New certificate required</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {/* Warning if changed */}
                  {formData.update_service_check_result === 'changed' && (
                    <div className="p-2 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-xs text-red-700 font-medium">
                        <AlertTriangle className="h-3 w-3 inline mr-1" />
                        Update Service shows changes. Request a new DBS certificate disclosure.
                      </p>
                    </div>
                  )}
                </div>
              )}
              
              {/* Result Status Section */}
              <div className="space-y-3 pt-3 border-t border-slate-200">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-700">Result Status</span>
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  {/* Result Status */}
                  <div className="space-y-1">
                    <Label className="text-xs">Clearance Status</Label>
                    <Select 
                      value={formData.result_status || (formData.information_present ? 'information_present' : 'clear')} 
                      onValueChange={(v) => setFormData(prev => ({ 
                        ...prev, 
                        result_status: v,
                        information_present: v === 'information_present'
                      }))}
                    >
                      <SelectTrigger className="h-8 text-sm rounded-lg" data-testid="dbs-result-status">
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="clear">Clear - No information</SelectItem>
                        <SelectItem value="information_present">Information Present</SelectItem>
                        <SelectItem value="pending_review">Pending Review</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {/* Recheck Required checkbox */}
                  <div className="flex items-end">
                    <label className="flex items-center gap-2 text-sm cursor-pointer pb-2">
                      <input
                        type="checkbox"
                        checked={formData.recheck_required !== false}
                        onChange={(e) => setFormData(prev => ({ ...prev, recheck_required: e.target.checked }))}
                        className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                        data-testid="dbs-recheck-required"
                      />
                      <span className="text-slate-700 text-xs">Recheck required</span>
                    </label>
                  </div>
                </div>
                
                {/* Information Present Warning */}
                {formData.information_present && (
                  <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg">
                    <p className="text-xs text-amber-700">
                      <AlertTriangle className="h-3 w-3 inline mr-1" />
                      Information/disclosures present on certificate. Include details in notes for risk assessment.
                    </p>
                  </div>
                )}
                
                {/* Result Summary */}
                <div className="space-y-1">
                  <Label className="text-xs">Result Summary</Label>
                  <Input
                    value={formData.result_summary}
                    onChange={(e) => setFormData(prev => ({ ...prev, result_summary: e.target.value }))}
                    placeholder="e.g., Clear - no information disclosed"
                    className="h-8 text-sm rounded-lg"
                    data-testid="dbs-result-summary"
                  />
                </div>
              </div>
              
              {/* Policy reminder */}
              <div className="p-2 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-xs text-blue-700">
                  <Info className="h-3 w-3 inline mr-1" />
                  DBS certificates have no statutory expiry. Set a policy-based recheck date (typically 3 years).
                </p>
              </div>
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
            disabled={isSubmitting || isUploading || isExtracting || !formData.method || !hasProof}
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
