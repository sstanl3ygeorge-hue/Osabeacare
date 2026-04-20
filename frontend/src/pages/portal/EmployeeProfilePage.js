import { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Progress } from '../../components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '../../components/ui/dropdown-menu';
import { Label } from '../../components/ui/label';
import { Input } from '../../components/ui/input';
import { Checkbox } from '../../components/ui/checkbox';
import { Textarea } from '../../components/ui/textarea';
import { toast } from 'sonner';
import ComplianceOverview from '../../components/portal/ComplianceOverview';
import DocumentPreviewModal from '../../components/portal/DocumentPreviewModal';
import RecurringComplianceSection from '../../components/portal/RecurringComplianceSection';
import DocumentExtractionReview from '../../components/documents/DocumentExtractionReview';
import TrainingIntakeWizard from '../../components/training/TrainingIntakeWizard';
import TrainingRequestDialog from '../../components/training/TrainingRequestDialog';
import AuditReadyTrainingMatrix from '../../components/training/AuditReadyTrainingMatrix';
// EnhancedTrainingTab removed - functionality consolidated into AuditReadyTrainingMatrix
import { DualRowComplianceSection, RecordCheckDialog, WhatsNeededPanel, TrainingSummaryCard, ApplicantStageBanner, ReferencesPanel, AuditTrailPanel, DocumentRequestsPanel, InterviewFormPanel } from '../../components/compliance';
import ConsolidatedStatusPanel from '../../components/compliance/ConsolidatedStatusPanel';
import EmploymentGapPanel from '../../components/compliance/EmploymentGapPanel';
import CompetencyAssessmentsPanel from '../../components/compliance/CompetencyAssessmentsPanel';
import SpotChecksPanel from '../../components/compliance/SpotChecksPanel';
import PendingVerificationBanner from '../../components/compliance/PendingVerificationBanner';
import { SendReminderButton, RequestRenewalButton } from '../../components/admin/AdminActionButtons';
import EditPersonalDetailsDialog from '../../components/admin/EditPersonalDetailsDialog';
import EditEmploymentHistoryDialog from '../../components/admin/EditEmploymentHistoryDialog';
import EditReferenceDialog from '../../components/admin/EditReferenceDialog';
import EditDeclarationsDialog from '../../components/admin/EditDeclarationsDialog';
import SupersedeContractDialog from '../../components/admin/SupersedeContractDialog';
import DocumentVerificationModal from '../../components/admin/DocumentVerificationModal';
import DocumentViewerModal from '../../components/admin/DocumentViewerModal';
import InlineDocumentViewer from '../../components/shared/InlineDocumentViewer';
import ApplicationFormViewer from '../../components/compliance/ApplicationFormViewer';
import EvidenceReviewViewerDialog from '../../components/compliance/EvidenceReviewViewerDialog';
import { 
  InductionChecklistPanel, 
  CompetencyRecordsPanel, 
  PreEmploymentGatesPanel, 
  ReferenceEmploymentComparison,
  PoliciesTabContent,
  TrainingTabContent,
  AuditTabContent,
  ReferencesTabContent
} from '../../components/employee';
import {
  ArrowLeft, Upload, FileText, Mail, Phone, Calendar,
  CheckCircle, Clock, AlertTriangle, AlertCircle, XCircle, Loader2, FileCheck,
  GraduationCap, ClipboardList, History, User, FolderUp, Eye, Shield,
  MoreHorizontal, MoreVertical, Edit, Archive, Trash2, RotateCcw, FileDown, Save,
  Download, RefreshCw, FileArchive, FileSpreadsheet, Printer, FileSearch,
  Camera, Replace, FileX, ClipboardCheck, FormInput, ChevronRight,
  Briefcase, UserCheck, FileWarning, CalendarClock, Send, ExternalLink
} from 'lucide-react';
import { FileUploaderInline } from '../../components/ui/file-uploader';
import { formatBackendDate, formatBackendDateTime, parseBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Form-based requirements (open modal instead of file upload)
const FORM_BASED_REQUIREMENTS = [
  // 'health_screening' - ARCHIVED: replaced by staff_health_questionnaire
  'induction', 
  'interview_record', 
  'recruitment_checklist', 
  'equal_opportunities',
  'hmrc_starter_checklist',
  'staff_personal_info',
  'staff_health_questionnaire',
  // Worker-submittable forms — must open form viewer, not file upload
  'emergency_contacts',
  'conflict_of_interest',
  'pre_interview_questionnaire',
  'fit_proper_persons',
];

const statusIcons = {
  not_started: Clock,
  requested: Mail,
  uploaded: Upload,
  under_review: Clock,
  approved: CheckCircle,
  rejected: XCircle,
  expired: AlertTriangle,
  not_applicable: XCircle
};

const statusColors = {
  not_started: 'status-neutral',
  requested: 'status-info',
  uploaded: 'status-info',
  under_review: 'status-warning',
  approved: 'status-success',
  rejected: 'status-error',
  expired: 'status-error',
  not_applicable: 'status-neutral'
};

const getComplianceFileWorkflowStatus = (complianceFile, sectionKey) => {
  const section = complianceFile?.sections?.[sectionKey];
  if (!section) return null;

  const evidenceRow = section.rows?.find((row) => row.row_type === 'evidence');
  const checkRow = section.rows?.find((row) => row.row_type === 'check');
  const evidenceFiles = evidenceRow?.documents_preview || [];
  const checkRecord = checkRow?.check_data || null;
  const acceptedFiles = evidenceFiles.filter((file) =>
    file.verified ||
    file.status === 'verified' ||
    file.status === 'approved' ||
    file.status === 'accepted'
  );
  const hasEvidence = evidenceFiles.length > 0;
  const hasAcceptedEvidence = acceptedFiles.length > 0;
  const hasCheck = !!checkRecord;
  const checkVerified = checkRecord?.outcome === 'verified';
  const checkFailed = checkRecord?.outcome === 'failed';
  const proofDocumentId = checkRecord?.proof_document_id || checkRecord?.evidence_document_id || null;
  const isDbs = sectionKey === 'dbs';
  const isRtw = sectionKey === 'right_to_work';
  const proofRequired = isRtw || (isDbs && ['dbs_update_service_check', 'update_service_check', 'dbs_update_service'].includes(checkRecord?.method));
  const reviewDueAt = checkRecord?.review_due_at || checkRecord?.next_recheck_date || null;
  const reviewDueDate = reviewDueAt ? parseBackendDate(reviewDueAt) : null;
  const isDbsOverdue = isDbs && reviewDueDate && reviewDueDate < new Date();
  const permissionEndDate = checkRecord?.permission_end_date || null;
  const permissionDate = permissionEndDate ? parseBackendDate(permissionEndDate) : null;
  const isRtwExpired = isRtw && permissionDate && permissionDate < new Date();

  if (!hasEvidence) {
    return { label: 'Missing', tone: 'gray', isBlocking: true };
  }
  if (!hasAcceptedEvidence) {
    return { label: 'Awaiting admin review', tone: 'amber', isBlocking: true };
  }
  if (!hasCheck) {
    return { label: 'Awaiting admin review', tone: 'amber', isBlocking: true };
  }
  if (checkFailed) {
    return { label: 'Rejected / action required', tone: 'red', isBlocking: true };
  }
  if (!checkVerified) {
    return { label: 'Awaiting admin review', tone: 'amber', isBlocking: true };
  }
  if (proofRequired && !proofDocumentId) {
    return { label: 'Awaiting admin review', tone: 'amber', isBlocking: true };
  }
  if (isDbsOverdue) {
    return { label: 'Rejected / action required', tone: 'red', isBlocking: true, reviewDueAt };
  }
  if (isRtwExpired) {
    return { label: 'Rejected / action required', tone: 'red', isBlocking: true, permissionEndDate };
  }

  return { label: 'Verified', tone: 'green', isBlocking: false, reviewDueAt, permissionEndDate };
};

const quickViewToneClasses = {
  red: {
    card: 'border-red-200 bg-red-50',
    icon: 'text-red-600',
    text: 'text-red-700'
  },
  amber: {
    card: 'border-amber-200 bg-amber-50',
    icon: 'text-amber-600',
    text: 'text-amber-700'
  },
  green: {
    card: 'border-green-200 bg-green-50',
    icon: 'text-green-600',
    text: 'text-green-700'
  },
  gray: {
    card: 'border-gray-200 bg-gray-50',
    icon: 'text-gray-500',
    text: 'text-gray-700'
  },
  blue: {
    card: 'border-blue-200 bg-blue-50',
    icon: 'text-blue-600',
    text: 'text-blue-700'
  }
};

export default function EmployeeProfilePage() {
  const { employeeId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Route context detection - determines if viewing from recruitment or employee context
  const isRecruitmentView = location.pathname.startsWith('/portal/recruitment/');
  
  // Initialize active tab from URL for navigation state persistence
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'employment');
  const [employee, setEmployee] = useState(null);
  const isActiveEmployee =
    employee?.is_active_employee ||
    employee?.employee_status === 'active_employee' ||
    employee?.status === 'active_employee' ||
    employee?.status === 'active';
  const isPreEmploymentEmployee =
    !isActiveEmployee && (
      employee?.person_stage === 'employee' ||
      employee?.is_approved ||
      employee?.recruitment_approved ||
      employee?.employee_status === 'onboarding' ||
      employee?.status === 'onboarding'
    );
  const lifecycleStage = isActiveEmployee
    ? 'active'
    : isPreEmploymentEmployee
      ? 'pre_employment'
      : 'recruitment';
  const [documents, setDocuments] = useState([]);
  const [documentTypes, setDocumentTypes] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [training, setTraining] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [generatedForms, setGeneratedForms] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [compliance, setCompliance] = useState(null);
  const [complianceFile, setComplianceFile] = useState(null);
  const [employmentReview, setEmploymentReview] = useState(null);
  const [employmentReviewPersisted, setEmploymentReviewPersisted] = useState(false);
  const [employmentReviewError, setEmploymentReviewError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [bulkUploadOpen, setBulkUploadOpen] = useState(false);
  const [generateFormsOpen, setGenerateFormsOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [archiveDialogOpen, setArchiveDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isRefreshingStatus, setIsRefreshingStatus] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [selectedDocType, setSelectedDocType] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [bulkFiles, setBulkFiles] = useState([]);
  const [bulkDocTypes, setBulkDocTypes] = useState({});
  const [selectedTemplates, setSelectedTemplates] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [importAppOpen, setImportAppOpen] = useState(false);
  const [importAppFile, setImportAppFile] = useState(null);
  const [importCvFile, setImportCvFile] = useState(null);
  const [isImporting, setIsImporting] = useState(false);
  const [complianceRequirements, setComplianceRequirements] = useState(null);
  const [unifiedProgress, setUnifiedProgress] = useState(null);
  const [selectedRequirement, setSelectedRequirement] = useState('');
  const [documentLabel, setDocumentLabel] = useState('');
  
  // Edit dialog states for universal editability
  const [editPersonalOpen, setEditPersonalOpen] = useState(false);
  const [editEmploymentOpen, setEditEmploymentOpen] = useState(false);
  const [editReferenceOpen, setEditReferenceOpen] = useState(false);
  const [editDeclarationsOpen, setEditDeclarationsOpen] = useState(false);
  const [selectedReferenceId, setSelectedReferenceId] = useState(null);
  const [selectedReferenceData, setSelectedReferenceData] = useState(null);
  const [referencesTabRefreshKey, setReferencesTabRefreshKey] = useState(0);
  const [supersedeContractOpen, setSupersedeContractOpen] = useState(false);
  const [currentContract, setCurrentContract] = useState(null);
  
  // Import document dialog states
  const [importDocOpen, setImportDocOpen] = useState(false);
  const [importDocType, setImportDocType] = useState('');
  const [importDocFile, setImportDocFile] = useState(null);
  const [importDocNotes, setImportDocNotes] = useState('');
  
  // Training completion dialog states
  const [trainingDialogOpen, setTrainingDialogOpen] = useState(false);
  const [selectedTrainingReq, setSelectedTrainingReq] = useState(null);
  const [trainingExpiryDate, setTrainingExpiryDate] = useState('');
  const [isCompletingTraining, setIsCompletingTraining] = useState(false);
  
  // Training certificate upload states
  const [trainingCertDialogOpen, setTrainingCertDialogOpen] = useState(false);
  const [trainingCertFile, setTrainingCertFile] = useState(null);
  const [isUploadingCert, setIsUploadingCert] = useState(false);
  
  // Form submissions state
  const [formSubmissions, setFormSubmissions] = useState([]);
  const [formSubmissionsError, setFormSubmissionsError] = useState(false);
  const [viewFormSubmission, setViewFormSubmission] = useState(null);
  const [formReviewViewer, setFormReviewViewer] = useState(null);
  const [formCorrectionDialog, setFormCorrectionDialog] = useState(null);
  const [formCorrectionReason, setFormCorrectionReason] = useState('');
  const [isReopeningFormCorrection, setIsReopeningFormCorrection] = useState(false);
  const [isVerifyingTraining, setIsVerifyingTraining] = useState(false);
  
  // Training correction/history dialog states
  const [trainingCorrectionDialogOpen, setTrainingCorrectionDialogOpen] = useState(false);
  const [editingTrainingRecord, setEditingTrainingRecord] = useState(null);
  const [trainingCorrectionField, setTrainingCorrectionField] = useState('expiry_date');
  const [trainingCorrectionValue, setTrainingCorrectionValue] = useState('');
  const [trainingCorrectionReason, setTrainingCorrectionReason] = useState('');
  
  // Recruitment Checks states (Reference Integrity, CV Gaps, Proof of Address)
  const [recruitmentStatus, setRecruitmentStatus] = useState(null);
  const [loadingRecruitment, setLoadingRecruitment] = useState(false);
  const [verifyRefDialogOpen, setVerifyRefDialogOpen] = useState(false);
  const [selectedRefNum, setSelectedRefNum] = useState(null);
  const [refFromCv, setRefFromCv] = useState(true);
  const [refOverrideReason, setRefOverrideReason] = useState('');
  const [isVerifyingRef, setIsVerifyingRef] = useState(false);
  const [explainGapDialogOpen, setExplainGapDialogOpen] = useState(false);
  const [selectedGap, setSelectedGap] = useState(null);
  const [gapExplanation, setGapExplanation] = useState('');
  const [isExplainingGap, setIsExplainingGap] = useState(false);
  const [trainingHistoryDialogOpen, setTrainingHistoryDialogOpen] = useState(false);
  const [trainingHistory, setTrainingHistory] = useState([]);
  
  // CV Review states (Admin reviews CV, triggers AI extraction)
  const [cvReviewDialogOpen, setCvReviewDialogOpen] = useState(false);
  const [cvReviewLoading, setCvReviewLoading] = useState(false);
  const [cvExtractionResult, setCvExtractionResult] = useState(null);
  const [cvRejectDialogOpen, setCvRejectDialogOpen] = useState(false);
  const [cvRejectReason, setCvRejectReason] = useState('');
  const [cvRejectLoading, setCvRejectLoading] = useState(false);
  const [gapRerunLoading, setGapRerunLoading] = useState(false);

  // Inline document viewer state (replaces window.open / new-tab PDF viewing)
  const [inlineViewerOpen, setInlineViewerOpen] = useState(false);
  const [inlineViewerUrl, setInlineViewerUrl] = useState(null);
  const [inlineViewerTitle, setInlineViewerTitle] = useState('Document');
  const [inlineViewerFilename, setInlineViewerFilename] = useState('document.pdf');
  const [inlineViewerFallback, setInlineViewerFallback] = useState(null);

  // Employment Review sign-off state
  const [employmentSignOffLoading, setEmploymentSignOffLoading] = useState(false);
  const [employmentReviewRebuildLoading, setEmploymentReviewRebuildLoading] = useState(false);
  
  // Delete training record states
  const [deleteTrainingDialogOpen, setDeleteTrainingDialogOpen] = useState(false);
  const [deletingTrainingRecord, setDeletingTrainingRecord] = useState(null);
  const [deleteTrainingReason, setDeleteTrainingReason] = useState('');
  const [isDeletingTraining, setIsDeletingTraining] = useState(false);
  
  // Training evaluation state (canonical evaluator result)
  const [trainingEvaluation, setTrainingEvaluation] = useState(null);
  const [loadingTrainingEvaluation, setLoadingTrainingEvaluation] = useState(false);
  
  // Acknowledgement states (for Contract/Handbook acknowledgement flow)
  const [acknowledgementDialogOpen, setAcknowledgementDialogOpen] = useState(false);
  const [acknowledgingRequirement, setAcknowledgingRequirement] = useState(null);
  const [isAcknowledging, setIsAcknowledging] = useState(false);
  const [acknowledgementConfirmed, setAcknowledgementConfirmed] = useState(false);
  
  // Profile photo upload state
  const [isUploadingPhoto, setIsUploadingPhoto] = useState(false);
  const [profilePhotoBlob, setProfilePhotoBlob] = useState(null);
  const photoInputRef = useRef(null);
  
  // Evidence edit state
  const [editEvidenceOpen, setEditEvidenceOpen] = useState(false);
  const [editEvidenceData, setEditEvidenceData] = useState(null);
  const [editHistory, setEditHistory] = useState([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [isEditingEvidence, setIsEditingEvidence] = useState(false);
  const [editForm, setEditForm] = useState({
    issue_date: '',
    expiry_date: '',
    notes: '',
    file_label: '',
    reason: ''
  });

  const getSafeErrorMessage = async (error, fallbackMessage) => {
    const data = error?.response?.data;

    if (data instanceof Blob) {
      try {
        const text = await data.text();
        if (text) {
          try {
            const parsed = JSON.parse(text);
            return parsed?.detail || parsed?.message || fallbackMessage;
          } catch {
            return text;
          }
        }
      } catch {
        // Ignore blob parsing failures and fall through to fallback handling.
      }
      return fallbackMessage;
    }

    if (typeof data === 'string' && data.trim()) {
      return data;
    }

    const detail = data?.detail;
    if (detail && typeof detail === 'object') {
      return detail.message || detail.msg || JSON.stringify(detail);
    }
    return detail || data?.message || fallbackMessage;
  };
  
  // File management state
  const [removeDialogOpen, setRemoveDialogOpen] = useState(false);
  const [replaceDialogOpen, setReplaceDialogOpen] = useState(false);
  const [requirementHistoryOpen, setRequirementHistoryOpen] = useState(false);
  const [selectedFileForAction, setSelectedFileForAction] = useState(null);
  const [selectedRequirementForAction, setSelectedRequirementForAction] = useState(null);
  const [removeReason, setRemoveReason] = useState('');
  const [replaceReason, setReplaceReason] = useState('');
  const [replaceFile, setReplaceFile] = useState(null);
  const [isRemoving, setIsRemoving] = useState(false);
  const [isReplacing, setIsReplacing] = useState(false);
  const [requirementHistory, setRequirementHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  // Form submission modal state (for structured forms)
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [formTemplate, setFormTemplate] = useState(null);
  const [formData, setFormData] = useState({});
  const [isSubmittingForm, setIsSubmittingForm] = useState(false);
  const [viewFormOpen, setViewFormOpen] = useState(false);
  const [viewFormData, setViewFormData] = useState(null);
  
  // Document request modal state
  const [requestDocDialogOpen, setRequestDocDialogOpen] = useState(false);
  const [requestingRequirement, setRequestingRequirement] = useState(null);
  const [requestDocMessage, setRequestDocMessage] = useState('');
  const [isRequestingDoc, setIsRequestingDoc] = useState(false);
  
  // Send Form state
  const [sendFormDialogOpen, setSendFormDialogOpen] = useState(false);
  const [selectedFormType, setSelectedFormType] = useState('');
  const [sendFormMessage, setSendFormMessage] = useState('');
  const [isSendingForm, setIsSendingForm] = useState(false);
  
  // Reference Request state (NHS-Level Workflow)
  const [referenceStatus, setReferenceStatus] = useState(null);
  const [loadingReferenceStatus, setLoadingReferenceStatus] = useState(false);
  const [requestReferenceDialogOpen, setRequestReferenceDialogOpen] = useState(false);
  const [selectedRefForRequest, setSelectedRefForRequest] = useState(null);
  const [referenceRequestMessage, setReferenceRequestMessage] = useState('');
  const [isRequestingReference, setIsRequestingReference] = useState(false);
  const [reviewReferenceDialogOpen, setReviewReferenceDialogOpen] = useState(false);
  const [selectedRefForReview, setSelectedRefForReview] = useState(null);
  const [reviewMismatchNotes, setReviewMismatchNotes] = useState('');
  const [isReviewingReference, setIsReviewingReference] = useState(false);
  const [isVerifyingReferenceStrict, setIsVerifyingReferenceStrict] = useState(false);
  
  // Profile extraction from application form state
  const [extractionDialogOpen, setExtractionDialogOpen] = useState(false);
  const [extractionResult, setExtractionResult] = useState(null);
  const [extractionFailed, setExtractionFailed] = useState(null); // For graceful failure handling
  const [isExtracting, setIsExtracting] = useState(false);
  const [fieldsToApply, setFieldsToApply] = useState({});
  const [isApplyingExtraction, setIsApplyingExtraction] = useState(false);
  
  // Employment History Mismatch State (CV vs Structured)
  const [employmentMismatch, setEmploymentMismatch] = useState(null);
  const [loadingMismatch, setLoadingMismatch] = useState(false);
  const [mismatchDialogOpen, setMismatchDialogOpen] = useState(false);
  const [mismatchReviewNote, setMismatchReviewNote] = useState('');
  const [isSubmittingMismatchNote, setIsSubmittingMismatchNote] = useState(false);
  const [selectedCvRolesForApply, setSelectedCvRolesForApply] = useState({});
  const [reconcileReason, setReconcileReason] = useState('');
  const [isApplyingReconcile, setIsApplyingReconcile] = useState(false);
  const [isReextractingFromCv, setIsReextractingFromCv] = useState(false);
  
  // Document Correction State (Step 8)
  const [docCorrectionDialogOpen, setDocCorrectionDialogOpen] = useState(false);
  const [docCorrectionType, setDocCorrectionType] = useState(null); // 'uploaded_in_error' | 'supersede' | 'move_category' | 'reopen_review'
  const [docCorrectionTarget, setDocCorrectionTarget] = useState(null);
  const [docCorrectionReason, setDocCorrectionReason] = useState('');
  const [docCorrectionNewCategory, setDocCorrectionNewCategory] = useState('');
  const [isSubmittingDocCorrection, setIsSubmittingDocCorrection] = useState(false);
  
  // Document Extraction Review State (Phase 2 - DBS, RTW, ID)
  const [docExtractionReviewOpen, setDocExtractionReviewOpen] = useState(false);
  const [docExtractionDocumentId, setDocExtractionDocumentId] = useState(null);
  const [docExtractionDocumentName, setDocExtractionDocumentName] = useState('');
  const [docExtractionContext, setDocExtractionContext] = useState(null); // Full context for modal header
  
  // Document Verification & Viewer Modal States (CQC P0 Compliance)
  const [verificationModalOpen, setVerificationModalOpen] = useState(false);
  const [verificationDocument, setVerificationDocument] = useState(null);
  const [viewerModalOpen, setViewerModalOpen] = useState(false);
  const [viewerDocument, setViewerDocument] = useState(null);
  
  const { token, isAuditor, isAdmin, user } = useAuth();
  
  // Document preview modal state
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState(null);
  const [previewFiles, setPreviewFiles] = useState([]); // For multi-file navigation
  
  // Name Mismatch State (Phase 4 - Cross-Document Intelligence)
  const [nameMismatch, setNameMismatch] = useState(null);
  const [loadingNameMismatch, setLoadingNameMismatch] = useState(false);
  const [nameMismatchExpanded, setNameMismatchExpanded] = useState(false);
  
  // Training Intake Wizard State (Step 10)
  const [trainingIntakeOpen, setTrainingIntakeOpen] = useState(false);
  const [trainingRequestOpen, setTrainingRequestOpen] = useState(false);
  const [proposedTrainingItems, setProposedTrainingItems] = useState([]);
  const [loadingProposedItems, setLoadingProposedItems] = useState(false);
  
  // Dual-Row Compliance Model State (Step 11)
  const [recordCheckDialogOpen, setRecordCheckDialogOpen] = useState(false);
  const [recordCheckType, setRecordCheckType] = useState(null);
  
  // Refs for scrolling to compliance sections
  const complianceSectionRef = useRef(null);
  const trainingSectionRef = useRef(null);
  
  // Helper: Map blocker text to section ID and tab
  const mapBlockerToSection = (blockerText) => {
    const text = blockerText.toLowerCase();
    if (text.includes('right to work') || text.includes('rtw')) {
      return { sectionId: 'section-right_to_work', tab: 'checklist' };
    }
    if (text.includes('dbs') || text.includes('disclosure')) {
      return { sectionId: 'section-dbs', tab: 'checklist' };
    }
    if (text.includes('identity') || text.includes('photo id') || text.includes('passport')) {
      return { sectionId: 'section-identity', tab: 'checklist' };
    }
    if (text.includes('address') || text.includes('proof of address') || text.includes('poa')) {
      return { sectionId: 'section-proof_of_address', tab: 'checklist' };
    }
    if (text.includes('training') || text.includes('certificate') || text.includes('qualification')) {
      return { sectionId: text.includes('induction') ? 'section-training-induction' : 'section-training-root', tab: 'training' };
    }
    if (text.includes('reference')) {
      return { sectionId: 'section-references-root', tab: 'references' };
    }
    if (text.includes('interview')) {
      return { sectionId: 'section-forms-interview', tab: 'forms' };
    }
    if (text.includes('declaration')) {
      return { sectionId: 'section-forms-declarations', tab: 'forms' };
    }
    if (text.includes('application') || text.includes('pre-screen') || text.includes('pre screen')) {
      return { sectionId: 'section-forms-pre-screen', tab: 'forms' };
    }
    if (text.includes('form') || text.includes('hmrc') || text.includes('emergency') || text.includes('health questionnaire') || text.includes('personal information')) {
      return { sectionId: 'section-forms-core', tab: 'forms' };
    }
    if (text.includes('contract') || text.includes('handbook')) {
      return { sectionId: 'section-agreements', tab: 'checklist' };
    }
    if (text.includes('employment') || text.includes('gap') || text.includes('cv')) {
      if (text.includes('gap')) return { sectionId: 'section-employment-gaps', tab: 'employment' };
      if (text.includes('qualif') || text.includes('education')) return { sectionId: 'section-employment-qualifications', tab: 'employment' };
      return { sectionId: 'section-employment-cv', tab: 'employment' };
    }
    if (text.includes('spot check')) {
      return { sectionId: 'section-spot-checks-root', tab: 'spot_checks' };
    }
    if (text.includes('competenc')) {
      return { sectionId: 'section-competencies-root', tab: 'competencies' };
    }
    // Default to checklist tab
    return { sectionId: null, tab: 'checklist' };
  };
  
  // Handler: Navigate to blocker section
  const navigateToTabSection = (tab, sectionId = null) => {
    // Switch to the correct tab first
    if (tab !== activeTab) {
      setActiveTab(tab);
      // Use timeout to allow tab content to render before scrolling
      setTimeout(() => {
        if (sectionId) {
          const element = document.querySelector(`[data-testid="${sectionId}"]`);
          if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            // Add highlight effect
            element.classList.add('ring-2', 'ring-primary', 'ring-offset-2');
            setTimeout(() => element.classList.remove('ring-2', 'ring-primary', 'ring-offset-2'), 2000);
          }
        } else if (tab === 'training' && trainingSectionRef.current) {
          trainingSectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 150);
    } else {
      // Already on correct tab, just scroll
      if (sectionId) {
        const element = document.querySelector(`[data-testid="${sectionId}"]`);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' });
          element.classList.add('ring-2', 'ring-primary', 'ring-offset-2');
          setTimeout(() => element.classList.remove('ring-2', 'ring-primary', 'ring-offset-2'), 2000);
        }
      }
    }
  };

  const handleBlockerClick = (blockerText) => {
    const { sectionId, tab } = mapBlockerToSection(blockerText);
    navigateToTabSection(tab, sectionId);
  };
  
  // Fetch recruitment status (Reference Integrity, CV Gaps, Proof of Address)
  const fetchRecruitmentStatus = async () => {
    if (!employeeId) return;
    setLoadingRecruitment(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/recruitment-status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRecruitmentStatus(response.data);
    } catch (err) {
      console.error('Failed to fetch recruitment status:', err);
    } finally {
      setLoadingRecruitment(false);
    }
  };
  
  // Fetch Employment History Mismatch Status (CV vs Structured)
  const fetchEmploymentMismatch = async () => {
    if (!employeeId) return;
    setLoadingMismatch(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/employment-mismatch`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEmploymentMismatch(response.data);
    } catch (err) {
      console.error('Failed to fetch employment mismatch:', err);
    } finally {
      setLoadingMismatch(false);
    }
  };
  
  // Fetch Name Mismatch Status (Phase 4 - Cross-Document Intelligence)
  const fetchNameMismatch = async () => {
    if (!employeeId) return;
    setLoadingNameMismatch(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/name-mismatches`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setNameMismatch(response.data);
    } catch (err) {
      console.error('Failed to fetch name mismatch:', err);
    } finally {
      setLoadingNameMismatch(false);
    }
  };
  
  // Fetch proposed training items (Step 10)
  const fetchProposedTrainingItems = async () => {
    if (!employeeId) return;
    setLoadingProposedItems(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/training/proposed-items`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setProposedTrainingItems(response.data.proposed_items || []);
    } catch (err) {
      console.error('Failed to fetch proposed training items:', err);
    } finally {
      setLoadingProposedItems(false);
    }
  };
  
  // Re-extract employment history from CV (Admin action)
  const handleReextractFromCv = async () => {
    // Find CV document
    const cvDoc = (compliance?.evidence || []).find(e => 
      e.document_type_name?.toLowerCase().includes('cv') || 
      e.document_type_name?.toLowerCase().includes('resume')
    );
    
    if (!cvDoc?.file_id && !cvDoc?.id) {
      toast.error('No CV document found. Please upload a CV first.');
      return;
    }
    
    setIsReextractingFromCv(true);
    try {
      // Step 1: Extract from CV
      const extractResponse = await axios.post(
        `${API}/cv/extract-employment-history?file_id=${cvDoc.file_id || cvDoc.id}&employee_id=${employeeId}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (extractResponse.data.status !== 'success' || !extractResponse.data.extracted_roles?.length) {
        toast.warning('No employment history could be extracted from CV');
        return;
      }
      
      // Step 2: Compare with structured history
      const compareResponse = await axios.post(
        `${API}/employees/${employeeId}/compare-employment-history`,
        extractResponse.data.extracted_roles,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(`CV re-extracted. ${extractResponse.data.extracted_roles.length} roles found.`);
      fetchEmploymentMismatch();
      fetchRecruitmentStatus();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to re-extract from CV');
    } finally {
      setIsReextractingFromCv(false);
    }
  };
  
  // NEW: Admin reviews CV - triggers AI extraction
  const handleReviewCv = async () => {
    setCvReviewLoading(true);
    try {
      const response = await axios.post(
        `${API}/admin/employees/${employeeId}/cv/review`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setCvExtractionResult(response.data.extraction);
      setCvReviewDialogOpen(true);
      
      if (response.data.requires_action) {
        toast.warning(`CV reviewed - ${response.data.extraction.gaps_detected} gaps need explanation`);
      } else {
        toast.success(`CV reviewed - ${response.data.extraction.jobs_found} jobs found, no issues`);
      }
      
      // Refresh data
      await Promise.all([
        fetchEmployee(),
        fetchRecruitmentStatus(),
        fetchCompliance(),
        fetchComplianceFile(),
        fetchEmploymentReview()
      ]);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail === 'No CV uploaded for this employee' || detail === 'No CV document found for this employee') {
        toast.error('No CV uploaded yet. Worker needs to upload their CV first.');
      } else {
        toast.error(detail || 'Failed to review CV');
      }
    } finally {
      setCvReviewLoading(false);
    }
  };

  // Open the active CV PDF in inline viewer (admin view)
  const handleViewCv = () => {
    const docId = employee?.cv_document_id || cvDocument?.id;
    if (!docId) return;
    setInlineViewerUrl(`${API}/employees/${employeeId}/requirements/cv/evidence/${docId}/view`);
    setInlineViewerTitle(cvDocument?.original_filename || cvDocument?.file_name || 'CV / Resume');
    setInlineViewerFilename(cvDocument?.original_filename || 'cv.pdf');
    setInlineViewerFallback(null);
    setInlineViewerOpen(true);
  };

  // Link an existing CV document as the active review CV
  const handleLinkCv = async () => {
    setCvReviewLoading(true);
    try {
      await axios.post(
        `${API}/admin/employees/${employeeId}/cv/link`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('CV linked as review document');
      await Promise.all([fetchEmployee(), fetchCompliance(), fetchComplianceFile(), fetchEmploymentReview()]);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to link CV');
    } finally {
      setCvReviewLoading(false);
    }
  };
  
  // Admin approves CV after review
  const handleApproveCv = async () => {
    setCvReviewLoading(true);
    try {
      await axios.post(
        `${API}/admin/employees/${employeeId}/cv/approve`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('CV approved! Employment history has been verified.');
      setCvReviewDialogOpen(false);
      setCvExtractionResult(null);
      
      // Refresh data
      fetchEmployee();
      fetchRecruitmentStatus();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to approve CV');
    } finally {
      setCvReviewLoading(false);
    }
  };

  // Admin signs off Employment Review
  const handleSignOffEmploymentReview = async () => {
    if (!employmentReadyForSignOff) {
      toast.error('Employment Review cannot be signed off until all blockers are cleared.');
      return;
    }
    setEmploymentSignOffLoading(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/employment-review/sign-off`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Employment review signed off.');
      fetchEmployee();
      fetchEmploymentReview();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Sign-off failed. Check all gaps are resolved.');
    } finally {
      setEmploymentSignOffLoading(false);
    }
  };

  // Admin rejects CV with reason
  const handleRejectCv = async () => {
    if (cvRejectReason.length < 10) {
      toast.error('Please provide a detailed reason (at least 10 characters)');
      return;
    }
    
    setCvRejectLoading(true);
    try {
      await axios.post(
        `${API}/admin/employees/${employeeId}/cv/reject`,
        { reason: cvRejectReason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('CV rejected. Worker has been notified and asked to take action.');
      setCvRejectDialogOpen(false);
      setCvReviewDialogOpen(false);
      setCvRejectReason('');
      setCvExtractionResult(null);
      
      // Refresh data
      fetchEmployee();
      fetchRecruitmentStatus();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject CV');
    } finally {
      setCvRejectLoading(false);
    }
  };
  
  // Add mismatch review note
  const handleAddMismatchNote = async () => {
    if (mismatchReviewNote.length < 5) {
      toast.error('Note must be at least 5 characters');
      return;
    }
    
    setIsSubmittingMismatchNote(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/employment-mismatch/add-note`,
        { note: mismatchReviewNote },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Review note added');
      setMismatchDialogOpen(false);
      setMismatchReviewNote('');
      fetchEmploymentMismatch();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add note');
    } finally {
      setIsSubmittingMismatchNote(false);
    }
  };

  const handleApplyReconcile = async () => {
    const rolesToApply = (employmentMismatch?.cv_extracted_roles || []).filter(
      (_, i) => selectedCvRolesForApply[i]
    );
    if (!rolesToApply.length) { toast.error('Select at least one CV role to apply'); return; }
    if (!reconcileReason || reconcileReason.trim().length < 5) {
      toast.error('Enter a reason (at least 5 characters) before applying');
      return;
    }
    setIsApplyingReconcile(true);
    try {
      const res = (await axios.post(
        `${API}/employees/${employeeId}/employment-history/apply-from-cv`,
        { roles_to_apply: rolesToApply, edit_reason: reconcileReason },
        { headers: { Authorization: `Bearer ${token}` } }
      )).data;
      toast.success(`Applied ${res.applied_count} role(s). Gaps recalculated.${
        res.skipped_duplicates?.length ? ` Skipped ${res.skipped_duplicates.length} duplicate(s).` : ''
      }`);
      setSelectedCvRolesForApply({});
      setReconcileReason('');
      setMismatchDialogOpen(false);
      fetchEmployee();
      fetchComplianceFile();
      fetchEmploymentMismatch();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to apply CV reconciliation');
    } finally {
      setIsApplyingReconcile(false);
    }
  };
  
  // Fetch training evaluation (canonical evaluator)
  const fetchTrainingEvaluation = async () => {
    if (!employeeId) return;
    setLoadingTrainingEvaluation(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/training`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTrainingEvaluation(response.data);
    } catch (err) {
      console.error('Failed to fetch training evaluation:', err);
    } finally {
      setLoadingTrainingEvaluation(false);
    }
  };
  
  // Verify reference with integrity check
  const handleVerifyReference = async () => {
    if (!refFromCv && refOverrideReason.length < 10) {
      toast.error('Override reason must be at least 10 characters');
      return;
    }
    
    setIsVerifyingRef(true);
    try {
      await axios.post(`${API}/employees/${employeeId}/verify-reference`, {
        reference_num: selectedRefNum,
        from_cv: refFromCv,
        override_reason: refFromCv ? null : refOverrideReason
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success(`Reference ${selectedRefNum} verified successfully`);
      setVerifyRefDialogOpen(false);
      setRefFromCv(true);
      setRefOverrideReason('');
      fetchRecruitmentStatus();
      fetchEmployee();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify reference');
    } finally {
      setIsVerifyingRef(false);
    }
  };
  
  // Explain CV gap
  const handleExplainGap = async () => {
    if (gapExplanation.length < 10) {
      toast.error('Explanation must be at least 10 characters');
      return;
    }
    
    setIsExplainingGap(true);
    try {
      await axios.post(`${API}/employees/${employeeId}/explain-cv-gap`, {
        gap_id: selectedGap?.gap_id,
        explanation: gapExplanation
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success('Gap explanation recorded');
      setExplainGapDialogOpen(false);
      setGapExplanation('');
      setSelectedGap(null);
      fetchRecruitmentStatus();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to record explanation');
    } finally {
      setIsExplainingGap(false);
    }
  };
  
  // Fetch reference status (NHS-Level strict workflow)
  const fetchReferenceStatus = async () => {
    if (!employeeId) return;
    setLoadingReferenceStatus(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/reference-status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setReferenceStatus(response.data.references || []);
    } catch (err) {
      console.error('Failed to fetch reference status:', err);
    } finally {
      setLoadingReferenceStatus(false);
    }
  };
  
  // Send reference request to referee (NHS-Level Step 1: Request)
  const handleSendReferenceRequest = async () => {
    if (!selectedRefForRequest) return;
    
    setIsRequestingReference(true);
    try {
      // Detect if this is a resend (reference already sent/requested/awaiting response)
      const isResend = ['sent', 'requested', 'awaiting_response'].includes(selectedRefForRequest.request_status);
      
      const response = await axios.post(
        `${API}/employees/${employeeId}/send-reference-request?reference_num=${selectedRefForRequest.reference_num}&force_resend=${isResend}${referenceRequestMessage ? `&message=${encodeURIComponent(referenceRequestMessage)}` : ''}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data.status === 'duplicate') {
        toast.info('Reference request already sent and awaiting response');
      } else if (response.data.status === 'success') {
        toast.success(`Reference request sent to ${response.data.referee_email}`);
      } else if (response.data.status === 'email_failed') {
        toast.warning('Request created but email failed to send');
      }
      
      setRequestReferenceDialogOpen(false);
      setReferenceRequestMessage('');
      setSelectedRefForRequest(null);
      fetchReferenceStatus();
      fetchEmployee();
      fetchCompliance();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send reference request');
    } finally {
      setIsRequestingReference(false);
    }
  };
  
  // Review reference (NHS-Level Step 2: Review with mismatch documentation)
  const handleReviewReference = async () => {
    if (!selectedRefForReview) return;
    
    // If mismatch detected, require notes
    if (selectedRefForReview.mismatch_detected && reviewMismatchNotes.length < 10) {
      toast.error('Mismatch detected - please provide at least 10 characters explaining the mismatch');
      return;
    }
    
    setIsReviewingReference(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/review-reference?reference_num=${selectedRefForReview.reference_num}${reviewMismatchNotes ? `&mismatch_notes=${encodeURIComponent(reviewMismatchNotes)}` : ''}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(`Reference ${selectedRefForReview.reference_num} reviewed. Ready for final verification.`);
      setReviewReferenceDialogOpen(false);
      setReviewMismatchNotes('');
      setSelectedRefForReview(null);
      fetchReferenceStatus();
      fetchEmployee();
      fetchCompliance();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to review reference');
    } finally {
      setIsReviewingReference(false);
    }
  };
  
  // Verify reference (NHS-Level Step 3: Final Verification - Admin Only)
  const handleVerifyReferenceStrict = async (refNum) => {
    setIsVerifyingReferenceStrict(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/verify-reference-strict?reference_num=${refNum}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(`Reference ${refNum} verified (2-step verification complete)`);
      fetchReferenceStatus();
      fetchEmployee();
      fetchCompliance();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify reference');
    } finally {
      setIsVerifyingReferenceStrict(false);
    }
  };
  
  // Sync tab changes to URL
  const handleTabChange = (value) => {
    setActiveTab(value);
    setSearchParams({ tab: value }, { replace: true });
  };
  
  // Open document in preview modal - supports single file or array
  const handlePreviewDocument = (url, name, filename) => {
    setPreviewFile({ url, name, filename });
    setPreviewFiles([]); // Clear multi-file array
    setPreviewOpen(true);
  };
  
  // Open multiple files in preview modal with navigation
  const handlePreviewMultipleFiles = (files, requirementId) => {
    if (!files || files.length === 0) return;
    
    // Build array of file objects for the modal
    const fileArray = files.map(f => ({
      url: `${API}/employees/${employeeId}/requirements/${requirementId}/evidence/${f.file_id}/view`,
      filename: f.file_label || f.original_filename || 'Document',
      content_type: f.content_type,
      file_id: f.file_id
    }));
    
    setPreviewFiles(fileArray);
    setPreviewFile(fileArray[0]); // Set first file as initial
    setPreviewOpen(true);
  };

  const roles = [
    'Care Assistant',
    'Senior Care Assistant',
    'Support Worker',
    'Healthcare Assistant',
    'Nurse',
    'Live-in Carer',
    'Night Carer',
    'Team Leader',
    'Care Coordinator'
  ];

  const statuses = [
    { value: 'new', label: 'New' },
    { value: 'screening', label: 'Screening' },
    { value: 'interview', label: 'Interview' },
    { value: 'compliance_review', label: 'Compliance Review' },
    { value: 'onboarding', label: 'Onboarding' },
    { value: 'active', label: 'Active' },
    { value: 'inactive', label: 'Inactive' }
  ];

  const onboardingStatuses = [
    'New',
    'Recruitment File: Incomplete',
    'Under Review',
    'Ready for Placement',
    'Active',
    'Archived'
  ];

  const isSuperAdmin = () => user?.role === 'super_admin';

  const fetchData = async () => {
    // Use Promise.allSettled to allow partial success
    const results = await Promise.allSettled([
      axios.get(`${API}/employees/${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/employee-documents?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/document-types`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/policy-assignments?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/training-records?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/audit-logs?entity_id=${employeeId}&compliance_only=true`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/generated-forms?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/templates`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/employees/${employeeId}/compliance-requirements`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/employees/${employeeId}/unified-progress`, { headers: { Authorization: `Bearer ${token}` } })
    ]);
    
    // Process results - extract data or use defaults
    const [empRes, docsRes, typesRes, policiesRes, trainingRes, logsRes, formsRes, templatesRes, compReqRes, unifiedProgressRes] = results;
    
    let hasError = false;
    
    // Employee data is critical - if it fails, show error
    if (empRes.status === 'fulfilled') {
      setEmployee(empRes.value.data);
    } else {
      console.error('Failed to fetch employee:', empRes.reason);
      hasError = true;
    }
    
    // Other data can fail gracefully with defaults
    setDocuments(docsRes.status === 'fulfilled' ? docsRes.value.data : []);
    setDocumentTypes(typesRes.status === 'fulfilled' ? typesRes.value.data : []);
    setPolicies(policiesRes.status === 'fulfilled' ? policiesRes.value.data : []);
    setTraining(trainingRes.status === 'fulfilled' ? trainingRes.value.data : []);
    setAuditLogs(logsRes.status === 'fulfilled' ? logsRes.value.data : []);
    setGeneratedForms(formsRes.status === 'fulfilled' ? formsRes.value.data : []);
    setTemplates(templatesRes.status === 'fulfilled' ? templatesRes.value.data : []);
    setComplianceRequirements(compReqRes.status === 'fulfilled' ? compReqRes.value.data : {});
    setUnifiedProgress(unifiedProgressRes.status === 'fulfilled' ? unifiedProgressRes.value.data : null);
    if (empRes.status === 'fulfilled' && docsRes.status === 'fulfilled') {
      const refreshedEmployee = empRes.value.data || {};
      const refreshedDocuments = docsRes.value.data || [];
      const cvLikeDocuments = refreshedDocuments.filter((document) => {
        const label = [
          document?.requirement_name,
          document?.document_type_name,
          document?.document_label,
          document?.original_filename,
          document?.file_name
        ].filter(Boolean).join(' ').toLowerCase();
        return (
          ['cv', 'resume', 'curriculum_vitae'].includes(document?.requirement_id) ||
          [document?.id, document?.file_id, document?.document_id].filter(Boolean).includes(refreshedEmployee?.cv_document_id) ||
          /\b(cv|resume|curriculum vitae)\b/.test(label)
        );
      });
      console.debug('CV_LINK_DIAGNOSTIC profile_refresh', {
        employeeId,
        cv_document_id: refreshedEmployee?.cv_document_id,
        cv_documents: cvLikeDocuments.map((document) => ({
          id: document?.id,
          file_id: document?.file_id,
          document_id: document?.document_id,
          requirement_id: document?.requirement_id,
          document_type_name: document?.document_type_name,
          requirement_name: document?.requirement_name,
          status: document?.status
        }))
      });
    }
    
    if (hasError) {
      toast.error('Failed to load employee data');
    }
    
    setLoading(false);
  };

  const fetchCompliance = async () => {
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/compliance`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCompliance(response.data);
    } catch (error) {
      console.error('Failed to fetch compliance:', error);
    }
  };

  const fetchEmployee = async () => {
    try {
      const response = await axios.get(`${API}/employees/${employeeId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEmployee(response.data);
    } catch (error) {
      console.error('Failed to fetch employee:', error);
    }
  };

  const fetchComplianceFile = async () => {
    if (!employeeId || !token) {
      console.debug('Skipping compliance-file fetch until employeeId and auth token are available');
      return;
    }

    try {
      const response = await axios.get(`${API}/employees/${employeeId}/compliance-file`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setComplianceFile(response.data);
    } catch (error) {
      console.error('Failed to fetch compliance file:', error);
    }
  };

  const fetchEmploymentReview = async ({ rebuild = false, showToast = false } = {}) => {
    if (!employeeId || !token) {
      console.debug('Skipping employment-review fetch until employeeId and auth token are available');
      return;
    }

    try {
      setEmploymentReviewError(false);
      const response = await axios.get(`${API}/employees/${employeeId}/employment-review`, {
        headers: { Authorization: `Bearer ${token}` },
        params: rebuild ? { rebuild: true } : {}
      });
      setEmploymentReview(response.data?.employment_review || null);
      setEmploymentReviewPersisted(Boolean(response.data?.persisted && response.data?.employment_review));
      if (showToast && response.data?.rebuilt) {
        toast.success('Canonical employment review rebuilt.');
      }
    } catch (error) {
      console.error('Failed to fetch employment review:', error);
      setEmploymentReview(null);
      setEmploymentReviewPersisted(false);
      setEmploymentReviewError(true);
      if (showToast) {
        toast.error(error?.response?.data?.detail || 'Failed to rebuild employment review');
      }
    }
  };

  const handleRebuildEmploymentReview = async () => {
    setEmploymentReviewRebuildLoading(true);
    try {
      await fetchEmploymentReview({ rebuild: true, showToast: true });
    } finally {
      setEmploymentReviewRebuildLoading(false);
    }
  };

  useEffect(() => {
    if (!employeeId || !token) {
      console.debug('Skipping employee profile protected fetches until employeeId and auth token are available');
      return;
    }

    fetchData();
    fetchCompliance();
    fetchComplianceFile();
    fetchEmploymentReview();
    fetchRecruitmentStatus();
    fetchReferenceStatus();
    fetchEmploymentMismatch();
    fetchNameMismatch();
    fetchTrainingEvaluation();
    fetchProposedTrainingItems();
    fetchFormSubmissions();
  }, [employeeId, token]);
  
  // Fetch form submissions for the Forms tab
  const fetchFormSubmissions = async () => {
    try {
      setFormSubmissionsError(false);
      const response = await axios.get(
        `${API}/form-submissions`,
        {
          headers: { Authorization: `Bearer ${token}` },
          params: { employee_id: employeeId }
        }
      );
      setFormSubmissions(response.data.forms || response.data || []);
    } catch {
      setFormSubmissions([]);
      setFormSubmissionsError(true);
    }
  };

  // Handle URL parameters from email action links
  useEffect(() => {
    const action = searchParams.get('action');
    const requirement = searchParams.get('requirement');
    const requestId = searchParams.get('request_id');
    const emailToken = searchParams.get('token');
    
    if (action && employee) {
      // Track that user clicked the email link
      if (requestId && emailToken) {
        trackEmailClick(requestId, emailToken);
      }
      
      // Handle different action types
      if (action.includes('upload') || action === 'upload_document') {
        // Set the requirement if provided, then open upload dialog
        if (requirement) {
          setSelectedDocType(requirement);
          setSelectedRequirement(requirement);
        }
        setUploadDialogOpen(true);
        
        // Clear URL params after handling
        setSearchParams(prev => {
          const newParams = new URLSearchParams(prev);
          newParams.delete('action');
          newParams.delete('requirement');
          newParams.delete('request_id');
          newParams.delete('token');
          return newParams;
        });
      }
    }
  }, [searchParams, employee, setSearchParams]);

  useEffect(() => {
    if (!employee || activeTab !== 'spot_checks' || isActiveEmployee) {
      return;
    }

    setActiveTab('employment');
    setSearchParams({ tab: 'employment' }, { replace: true });
  }, [activeTab, employee, isActiveEmployee, setSearchParams]);

  // Track email click event
  const trackEmailClick = async (requestId, emailToken) => {
    try {
      await axios.post(
        `${API}/email-requests/${requestId}/track-click`,
        { token: emailToken },
        { headers: { Authorization: `Bearer ${token}` } }
      );
    } catch (error) {
      console.error('Failed to track email click:', error);
    }
  };

  // Fetch profile photo when employee has one
  useEffect(() => {
    const fetchProfilePhoto = async () => {
      if (!employee?.profile_photo_url || !token) {
        setProfilePhotoBlob(null);
        return;
      }
      try {
        const response = await axios.get(
          `${API}/employees/${employeeId}/profile-photo/view`,
          { headers: { Authorization: `Bearer ${token}` }, responseType: 'blob' }
        );
        const blobUrl = URL.createObjectURL(response.data);
        setProfilePhotoBlob(blobUrl);
      } catch (error) {
        if (error?.response?.status !== 404) {
          console.error('Failed to fetch profile photo:', error);
        }
        setProfilePhotoBlob(null);
      }
    };
    fetchProfilePhoto();
    // Cleanup blob URL on unmount or when employee changes
    return () => {
      if (profilePhotoBlob) {
        URL.revokeObjectURL(profilePhotoBlob);
      }
    };
  }, [employee?.profile_photo_url, employeeId, token]);

  const handleRefreshStatus = async () => {
    setIsRefreshingStatus(true);
    try {
      const response = await axios.post(`${API}/employees/${employeeId}/refresh-status`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.data.status_changed) {
        toast.success(`Status updated to: ${response.data.new_status}`);
      } else {
        toast.info('Status is already up to date');
      }
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to refresh status');
    } finally {
      setIsRefreshingStatus(false);
    }
  };

  const handleExportFile = async () => {
    setIsExporting(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/export-file`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') 
        || `${employee?.employee_code || employee?.applicant_reference || 'export'}_File.zip`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Employee file exported successfully');
    } catch (error) {
      toast.error(await getSafeErrorMessage(error, 'Failed to export file'));
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportComplianceSummary = async () => {
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/export-compliance-summary`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Convert JSON to downloadable file
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${employee?.employee_code || employee?.applicant_reference || 'export'}_Compliance_Summary.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Compliance summary exported');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to export compliance summary');
    }
  };

  const handleExportCompliancePDF = async () => {
    setIsExporting(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/export-compliance-pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') 
        || `${employee?.employee_code || employee?.applicant_reference || 'export'}_Compliance_Summary.pdf`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Compliance PDF exported successfully');
    } catch (error) {
      toast.error(await getSafeErrorMessage(error, 'Failed to export PDF'));
    } finally {
      setIsExporting(false);
    }
  };

  const handlePrintCompliancePDF = async () => {
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/export-compliance-pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      // Open in new tab for printing
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const printWindow = window.open(url, '_blank');
      if (printWindow) {
        printWindow.onload = () => {
          printWindow.print();
        };
      }
    } catch (error) {
      toast.error('Failed to open PDF for printing');
    }
  };

  // Phase 4A - Unified export handler
  const handleExportComplianceFile = async () => {
    setIsExporting(true);
    try {
      // Default to PDF export
      const response = await axios.get(`${API}/employees/${employeeId}/export-compliance-pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') 
        || `${employee?.employee_code || employee?.applicant_reference || 'export'}_Compliance_File.pdf`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Compliance file exported');
    } catch (error) {
      toast.error(await getSafeErrorMessage(error, 'Failed to export compliance file'));
    } finally {
      setIsExporting(false);
    }
  };

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    if (!selectedRequirement || !uploadFile) {
      toast.error('Please select a requirement and choose a file to upload');
      return;
    }

    if (selectedRequirement === 'cv') {
      const isPdfFile = uploadFile.type === 'application/pdf' || uploadFile.name?.toLowerCase().endsWith('.pdf');
      if (!isPdfFile) {
        toast.error('Only PDF CV files are supported. Please upload the CV as a PDF. Word documents (.doc, .docx) are not accepted.');
        return;
      }
    }
    
    setIsUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      if (documentLabel) {
        formData.append('file_label', documentLabel);
      }
      
      // Use special endpoint for application form with AI extraction
      if (selectedRequirement === 'application_form') {
        formData.append('auto_extract', 'true');
        formData.append('notes', documentLabel || 'Admin uploaded existing application form');
        
        const response = await axios.post(`${API}/employees/${employeeId}/upload-existing-application`, formData, {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        });
        
        if (response.data.extraction) {
          toast.success('Application form uploaded & extraction complete!', {
            duration: 6000,
            description: `${response.data.extraction.fields?.length || 0} fields extracted. Review them in the Profile section.`
          });
        } else if (response.data.extraction_error) {
          toast.warning('Application form uploaded, but extraction failed', {
            duration: 5000,
            description: response.data.extraction_error
          });
        } else {
          toast.success('Application form uploaded successfully');
        }
      } else {
        // Use the unified evidence upload endpoint for other documents
        const uploadResponse = await axios.post(`${API}/employees/${employeeId}/requirements/${selectedRequirement}/evidence`, formData, {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        });
        if (selectedRequirement === 'cv') {
          console.debug('CV_LINK_DIAGNOSTIC upload_response', {
            employeeId,
            requirement_id: selectedRequirement,
            response: uploadResponse.data
          });
        }
        
        // POST-UPLOAD FEEDBACK - Clear guidance on next step
        toast.success('Document uploaded — please review and approve', {
          duration: 5000,
          description: 'Check the document is clear and correct, then mark as approved.'
        });
      }
      
      setUploadDialogOpen(false);
      setSelectedRequirement('');
      setSelectedDocType('');
      setDocumentLabel('');
      setUploadFile(null);
      const refreshTasks = [
        fetchData(),
        fetchCompliance()
      ];
      if (token) {
        refreshTasks.push(fetchComplianceFile());
      } else {
        console.debug('Skipping post-upload compliance-file refresh because auth token is not available');
      }
      await Promise.all(refreshTasks);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Upload failed — please try again');
    } finally {
      setIsUploading(false);
    }
  };

  const openCvRecoveryUpload = () => {
    setSelectedRequirement('cv');
    setSelectedDocType('cv');
    setDocumentLabel(cvFileExists ? 'Replacement PDF CV' : 'PDF CV');
    setUploadFile(null);
    setUploadDialogOpen(true);
  };

  const handleUpdateDocumentStatus = async (docId, status) => {
    try {
      await axios.put(`${API}/employee-documents/${docId}`, { status }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(`Document ${status}`);
      fetchData();
    } catch (error) {
      toast.error('Failed to update document');
    }
  };

  const handleVerifyDocument = async (docId, fileUrl) => {
    try {
      await axios.post(`${API}/employee-documents/${docId}/verify`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Document approved');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify document');
    }
  };

  const handleUnverifyDocument = async (docId) => {
    try {
      await axios.post(`${API}/employee-documents/${docId}/unverify`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Verification removed');
      fetchData();
    } catch (error) {
      toast.error('Failed to remove verification');
    }
  };

  const handleSaveFormAsDocument = async (formId, e) => {
    e.stopPropagation(); // Prevent navigation to form editor
    try {
      toast.loading('Saving form as document...');
      const response = await axios.post(`${API}/generated-forms/${formId}/save-as-document`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.dismiss();
      toast.success(`Saved to ${response.data.folder}`);
      fetchData();
    } catch (error) {
      toast.dismiss();
      toast.error(error.response?.data?.detail || 'Failed to save form as document');
    }
  };

  // Verify all documents under a requirement
  const handleVerifyRequirement = async (requirementId) => {
    try {
      // Get the requirement data
      const req = complianceRequirements?.requirements?.find(r => r.id === requirementId);
      if (!req) {
        toast.error('Requirement not found');
        return;
      }
      
      // Get evidence files
      const evidenceFiles = req.evidence_files || [];
      if (evidenceFiles.length === 0) {
        toast.error('Cannot verify - no evidence file uploaded');
        return;
      }
      
      // Proceed with verification - backend will handle file validation
      await axios.post(`${API}/employees/${employeeId}/requirements/${requirementId}/verify-all`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Requirement approved');
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify requirement');
    }
  };
  
  // Open Document Verification Modal with evidence upload (CQC P0)
  const handleOpenVerificationModal = (document, requirementId = null) => {
    const docData = {
      ...document,
      document_type: document.document_type || document.requirement_id || requirementId,
      id: document.id || document.document_id
    };
    setVerificationDocument(docData);
    setVerificationModalOpen(true);
  };
  
  // Open Document Viewer Modal (CQC P0)
  const handleOpenViewerModal = (document) => {
    setViewerDocument(document);
    setViewerModalOpen(true);
  };
  
  // Handle successful verification from modal
  const handleVerificationComplete = async () => {
    await fetchData();
    await fetchCompliance();
  };

  // Delete a specific document (for multi-file requirements)
  const handleDeleteDocument = async (docId) => {
    try {
      await axios.delete(`${API}/employee-documents/${docId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Document deleted');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete document');
    }
  };

  // Open remove file dialog
  const openRemoveDialog = (file, requirementId) => {
    setSelectedFileForAction(file);
    setSelectedRequirementForAction(requirementId);
    setRemoveReason('');
    setRemoveDialogOpen(true);
  };

  // Handle permanent delete file (removes from active use, keeps audit trail)
  const handleDeleteFile = async () => {
    setIsRemoving(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/requirements/${selectedRequirementForAction}/evidence/${selectedFileForAction.file_id}/delete`,
        { reason: removeReason.trim() || null },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File deleted successfully');
      setRemoveDialogOpen(false);
      setSelectedFileForAction(null);
      setSelectedRequirementForAction(null);
      setRemoveReason('');
      // CRITICAL: await fetchData to ensure UI syncs immediately
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete file');
    } finally {
      setIsRemoving(false);
    }
  };

  // Open replace file dialog
  const openReplaceDialog = (file, requirementId) => {
    setSelectedFileForAction(file);
    setSelectedRequirementForAction(requirementId);
    setReplaceReason('');
    setReplaceFile(null);
    setReplaceDialogOpen(true);
  };

  // Handle replace file
  const handleReplaceFile = async () => {
    if (!replaceReason.trim() || replaceReason.trim().length < 3) {
      toast.error('Please provide a reason (minimum 3 characters)');
      return;
    }
    if (!replaceFile) {
      toast.error('Please select a replacement file');
      return;
    }

    setIsReplacing(true);
    try {
      const formData = new FormData();
      formData.append('file', replaceFile);
      formData.append('reason', replaceReason.trim());
      
      await axios.post(
        `${API}/employees/${employeeId}/requirements/${selectedRequirementForAction}/evidence/${selectedFileForAction.file_id}/replace`,
        formData,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      toast.success('File replaced successfully');
      setReplaceDialogOpen(false);
      setSelectedFileForAction(null);
      setSelectedRequirementForAction(null);
      setReplaceReason('');
      setReplaceFile(null);
      // CRITICAL: await fetchData to ensure UI syncs immediately
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to replace file');
    } finally {
      setIsReplacing(false);
    }
  };

  // Fetch requirement history
  const fetchRequirementHistory = async (requirementId) => {
    setLoadingHistory(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/requirements/${requirementId}/history`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setRequirementHistory(response.data.history || []);
    } catch (error) {
      console.error('Failed to fetch history:', error);
      setRequirementHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Open requirement history dialog
  const openHistoryDialog = (requirementId) => {
    setSelectedRequirementForAction(requirementId);
    setRequirementHistoryOpen(true);
    fetchRequirementHistory(requirementId);
  };

  // ========================================
  // DOCUMENT CORRECTION ACTIONS (Step 8)
  // ========================================
  
  // Mark document as uploaded in error
  const handleMarkUploadedInError = async (documentId, reason) => {
    if (!reason || reason.trim().length < 10) {
      toast.error('Please provide a reason (minimum 10 characters)');
      return false;
    }
    
    try {
      await axios.post(
        `${API}/documents/${documentId}/mark-uploaded-in-error`,
        { reason: reason.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Document marked as uploaded in error');
      await fetchData();
      await fetchCompliance();
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to mark document');
      return false;
    }
  };

  // Supersede document with newer version
  const handleSupersedeDocument = async (documentId, replacementId, reason) => {
    try {
      await axios.post(
        `${API}/documents/${documentId}/supersede`,
        { 
          replacement_document_id: replacementId || null,
          reason: reason || 'Replaced by newer document'
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Document marked as superseded');
      await fetchData();
      await fetchCompliance();
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to supersede document');
      return false;
    }
  };

  // Move document to different requirement category
  const handleMoveDocumentCategory = async (documentId, newRequirementId, reason) => {
    if (!reason || reason.trim().length < 5) {
      toast.error('Please provide a reason (minimum 5 characters)');
      return false;
    }
    
    try {
      await axios.post(
        `${API}/documents/${documentId}/move-category`,
        { 
          new_requirement_id: newRequirementId,
          reason: reason.trim()
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Document moved to new category');
      await fetchData();
      await fetchCompliance();
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to move document');
      return false;
    }
  };

  // Reopen document for review (undo verification/rejection)
  const handleReopenDocumentReview = async (documentId, reason) => {
    if (!reason || reason.trim().length < 10) {
      toast.error('Please provide a reason (minimum 10 characters)');
      return false;
    }
    
    try {
      await axios.post(
        `${API}/documents/${documentId}/reopen-review`,
        { reason: reason.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Document reopened for review');
      await fetchData();
      await fetchCompliance();
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reopen document');
      return false;
    }
  };

  // Open document correction dialog
  const openDocCorrectionDialog = (type, document) => {
    setDocCorrectionType(type);
    setDocCorrectionTarget(document);
    setDocCorrectionReason('');
    setDocCorrectionNewCategory('');
    setDocCorrectionDialogOpen(true);
  };

  // Submit document correction
  const handleSubmitDocCorrection = async () => {
    setIsSubmittingDocCorrection(true);
    try {
      let success = false;
      switch (docCorrectionType) {
        case 'uploaded_in_error':
          success = await handleMarkUploadedInError(docCorrectionTarget.file_id || docCorrectionTarget.id, docCorrectionReason);
          break;
        case 'supersede':
          success = await handleSupersedeDocument(docCorrectionTarget.file_id || docCorrectionTarget.id, null, docCorrectionReason);
          break;
        case 'move_category':
          success = await handleMoveDocumentCategory(docCorrectionTarget.file_id || docCorrectionTarget.id, docCorrectionNewCategory, docCorrectionReason);
          break;
        case 'reopen_review':
          success = await handleReopenDocumentReview(docCorrectionTarget.file_id || docCorrectionTarget.id, docCorrectionReason);
          break;
        default:
          toast.error('Unknown correction type');
      }
      
      if (success) {
        setDocCorrectionDialogOpen(false);
        setDocCorrectionTarget(null);
        setDocCorrectionType(null);
        setDocCorrectionReason('');
        setDocCorrectionNewCategory('');
      }
    } finally {
      setIsSubmittingDocCorrection(false);
    }
  };

  // ========================================
  // DOCUMENT EXTRACTION REVIEW (Phase 2)
  // ========================================
  
  // Requirement IDs that support extraction
  const EXTRACTABLE_REQUIREMENTS = [
    'dbs_certificate', 'dbs_check',
    'right_to_work_documents', 'right_to_work_check',
    'id_document', 'passport', 'driving_licence',
    'proof_of_address', 'proof_of_address_1', 'proof_of_address_2'
  ];
  
  // Check if a requirement supports extraction
  const isExtractableRequirement = (requirementId) => {
    return EXTRACTABLE_REQUIREMENTS.includes(String(requirementId || '').toLowerCase());
  };
  
  // Open document extraction review
  // BUGFIX: Must receive actual document_id, not file_id from evidence_files
  const openDocExtraction = (document, requirementName = '') => {
    // Validate we have a proper document ID
    const documentId = document?.id || document?.document_id;
    
    if (!documentId) {
      toast.error('No document selected for extraction. Please select a specific file.');
      console.error('openDocExtraction called without valid document ID:', document);
      return;
    }
    
    // Build context for modal header
    const context = {
      documentId,
      fileName: document.file_label || document.original_filename || document.file_name || 'Document',
      requirementName: requirementName,
      documentType: document.document_type || document.requirement_id || '',
      uploadedAt: document.uploaded_at
    };
    
    setDocExtractionDocumentId(documentId);
    setDocExtractionDocumentName(context.fileName);
    setDocExtractionContext(context);
    setDocExtractionReviewOpen(true);
  };
  
  // Handle extraction review complete
  const handleDocExtractionComplete = () => {
    setDocExtractionReviewOpen(false);
    setDocExtractionDocumentId(null);
    setDocExtractionDocumentName('');
    setDocExtractionContext(null);
    fetchData();
    fetchCompliance();
    toast.success('Document extraction reviewed successfully');
  };

  const handleBulkUpload = async () => {
    if (bulkFiles.length === 0) {
      toast.error('Please select files to upload');
      return;
    }
    
    // Check all files have doc type assigned
    const missingTypes = bulkFiles.filter((_, i) => !bulkDocTypes[i]);
    if (missingTypes.length > 0) {
      toast.error('Please assign document types to all files');
      return;
    }
    
    setIsUploading(true);
    
    try {
      const formData = new FormData();
      bulkFiles.forEach((file) => formData.append('files', file));
      const typeIds = bulkFiles.map((_, i) => bulkDocTypes[i]).join(',');
      
      const response = await axios.post(
        `${API}/employees/${employeeId}/bulk-upload?document_type_ids=${typeIds}`,
        formData,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      toast.success(`Uploaded ${response.data.successful} documents`);
      if (response.data.errors?.length > 0) {
        response.data.errors.forEach(err => toast.error(err));
      }
      
      setBulkUploadOpen(false);
      setBulkFiles([]);
      setBulkDocTypes({});
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload documents');
    } finally {
      setIsUploading(false);
    }
  };

  const handleGenerateForms = async () => {
    if (selectedTemplates.length === 0) {
      toast.error('Please select at least one template');
      return;
    }
    
    setIsGenerating(true);
    
    try {
      const response = await axios.post(
        `${API}/generated-forms/bulk`,
        null,
        {
          headers: { Authorization: `Bearer ${token}` },
          params: {
            employee_id: employeeId,
            template_ids: selectedTemplates
          },
          paramsSerializer: params => {
            return Object.keys(params).map(key => {
              if (Array.isArray(params[key])) {
                return params[key].map(v => `${key}=${v}`).join('&');
              }
              return `${key}=${params[key]}`;
            }).join('&');
          }
        }
      );
      
      toast.success(`Generated ${response.data.created} forms`);
      if (response.data.errors?.length > 0) {
        response.data.errors.forEach(err => toast.warning(err));
      }
      
      setGenerateFormsOpen(false);
      setSelectedTemplates([]);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate forms');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleImportApplication = async () => {
    if (!importAppFile) {
      toast.error('Please select an application form to upload');
      return;
    }
    
    setIsImporting(true);
    
    try {
      const formData = new FormData();
      formData.append('employee_id', employeeId);
      formData.append('application_file', importAppFile);
      if (importCvFile) {
        formData.append('cv_file', importCvFile);
      }
      
      const response = await axios.post(
        `${API}/generated-forms/import-application`,
        formData,
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      toast.success(response.data.message || 'Application imported successfully');
      setImportAppOpen(false);
      setImportAppFile(null);
      setImportCvFile(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import application');
    } finally {
      setIsImporting(false);
    }
  };

  // Import document for Reference, Health Screening, Contract, etc.
  const handleImportDocument = async () => {
    if (!importDocFile || !importDocType) {
      toast.error('Please select document type and file');
      return;
    }
    
    setIsImporting(true);
    
    try {
      const formData = new FormData();
      formData.append('employee_id', employeeId);
      formData.append('form_type', importDocType);
      formData.append('document_file', importDocFile);
      if (importDocNotes) {
        formData.append('notes', importDocNotes);
      }
      
      const response = await axios.post(
        `${API}/generated-forms/import-document`,
        formData,
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      toast.success(response.data.message || 'Document imported successfully');
      setImportDocOpen(false);
      setImportDocType('');
      setImportDocFile(null);
      setImportDocNotes('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import document');
    } finally {
      setIsImporting(false);
    }
  };

  // Handle completing a training requirement
  const handleCompleteTraining = async () => {
    if (!selectedTrainingReq) {
      toast.error('No training requirement selected');
      return;
    }
    
    setIsCompletingTraining(true);
    
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/complete-training`,
        {
          requirement_id: selectedTrainingReq.id,
          expiry_date: trainingExpiryDate || null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(response.data.message || 'Training marked as complete');
      setTrainingDialogOpen(false);
      setSelectedTrainingReq(null);
      setTrainingExpiryDate('');
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to complete training');
    } finally {
      setIsCompletingTraining(false);
    }
  };
  
  // Open training completion dialog
  const openTrainingDialog = (requirement) => {
    setSelectedTrainingReq(requirement);
    setTrainingExpiryDate('');
    setTrainingDialogOpen(true);
  };
  
  // Open training certificate upload dialog
  const openTrainingCertDialog = (requirement) => {
    setSelectedTrainingReq(requirement);
    setTrainingExpiryDate('');
    setTrainingCertFile(null);
    setTrainingCertDialogOpen(true);
  };
  
  // Handle uploading training certificate
  const handleUploadTrainingCertificate = async () => {
    if (!selectedTrainingReq || !trainingCertFile) {
      toast.error('Please select a certificate file');
      return;
    }
    
    setIsUploadingCert(true);
    
    try {
      const formData = new FormData();
      formData.append('file', trainingCertFile);
      if (trainingExpiryDate) {
        formData.append('expiry_date', trainingExpiryDate);
      }
      
      const response = await axios.post(
        `${API}/employees/${employeeId}/training/${selectedTrainingReq.id}/upload-certificate`,
        formData,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          } 
        }
      );
      
      toast.success(response.data.message || 'Certificate uploaded successfully');
      setTrainingCertDialogOpen(false);
      setSelectedTrainingReq(null);
      setTrainingCertFile(null);
      setTrainingExpiryDate('');
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload certificate');
    } finally {
      setIsUploadingCert(false);
    }
  };
  
  // Handle verifying training
  const handleVerifyTraining = async (trainingId) => {
    setIsVerifyingTraining(true);
    try {
      await axios.post(
        `${API}/training-records/${trainingId}/verify`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Training verified successfully');
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify training');
    } finally {
      setIsVerifyingTraining(false);
    }
  };
  
  // Handle unverifying training
  const handleUnverifyTraining = async (trainingId) => {
    try {
      await axios.post(
        `${API}/training-records/${trainingId}/unverify`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Training verification removed');
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove verification');
    }
  };
  
  // View training certificate
  const handleViewTrainingCertificate = (trainingId, filename) => {
    if (!trainingId) {
      toast.error('Training record not found');
      return;
    }
    const url = `${API}/training-records/${trainingId}/certificate/file`;
    setPreviewFile({ url, name: filename || 'Certificate', filename: filename || 'Certificate' });
    setPreviewOpen(true);
  };
  
  // Download training certificate
  const handleDownloadTrainingCertificate = async (trainingId, filename) => {
    if (!trainingId) {
      toast.error('Training record not found');
      return;
    }
    try {
      const response = await axios.get(
        `${API}/training-records/${trainingId}/certificate/download`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      const blob = new Blob([response.data]);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || 'training_certificate';
      link.click();
      URL.revokeObjectURL(url);
      toast.success('Certificate downloaded');
    } catch (error) {
      console.error('Download error:', error);
      toast.error(error.response?.status === 404 ? 'Certificate file not found' : 'Failed to download certificate');
    }
  };
  
  // Training correction handler
  const handleTrainingCorrection = async () => {
    if (!trainingCorrectionReason || trainingCorrectionReason.trim().length < 3) {
      toast.error('Please provide a reason for this correction (minimum 3 characters)');
      return;
    }
    
    try {
      await axios.post(
        `${API}/training-records/${editingTrainingRecord.id}/correct`,
        {
          field: trainingCorrectionField,
          old_value: editingTrainingRecord[trainingCorrectionField],
          new_value: trainingCorrectionValue,
          reason: trainingCorrectionReason.trim()
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Training record corrected');
      setTrainingCorrectionDialogOpen(false);
      setEditingTrainingRecord(null);
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to correct training record');
    }
  };

  // Delete training record handler
  const handleDeleteTrainingRecord = async () => {
    setIsDeletingTraining(true);
    try {
      await axios.delete(
        `${API}/training-records/${deletingTrainingRecord.id}`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          params: { reason: deleteTrainingReason.trim() || undefined }
        }
      );
      toast.success('Training record deleted');
      setDeleteTrainingDialogOpen(false);
      setDeletingTrainingRecord(null);
      setDeleteTrainingReason('');
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete training record');
    } finally {
      setIsDeletingTraining(false);
    }
  };

  // Open training correction dialog from What's Needed tab
  // This reuses the same dialog as the Training tab for consistency
  const openTrainingCorrectionFromWhatsNeeded = (requirement) => {
    if (!requirement.training?.id) {
      toast.error('No training record found for this requirement');
      return;
    }
    
    // Build a training record object compatible with the correction dialog
    const trainingRecord = {
      id: requirement.training.id,
      training_name: requirement.name,
      status: requirement.training.status,
      expiry_date: requirement.training.expiry_date,
      completion_date: requirement.training.completed_at,
      verified: requirement.training.verified
    };
    
    setEditingTrainingRecord(trainingRecord);
    setTrainingCorrectionField('expiry_date');
    setTrainingCorrectionValue(trainingRecord.expiry_date?.split('T')[0] || '');
    setTrainingCorrectionReason('');
    setTrainingCorrectionDialogOpen(true);
  };

  // Open delete training dialog from What's Needed tab
  const openDeleteTrainingFromWhatsNeeded = (requirement) => {
    if (!requirement.training?.id) {
      toast.error('No training record found for this requirement');
      return;
    }
    
    // Build a training record object compatible with the delete dialog
    const trainingRecord = {
      id: requirement.training.id,
      training_name: requirement.name,
      status: requirement.training.status,
      verified: requirement.training.verified
    };
    
    setDeletingTrainingRecord(trainingRecord);
    setDeleteTrainingReason('');
    setDeleteTrainingDialogOpen(true);
  };

  // Handle requirement acknowledgement (Contract/Handbook)
  const handleAcknowledgeRequirement = async () => {
    if (!acknowledgingRequirement) return;
    
    setIsAcknowledging(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/requirements/${acknowledgingRequirement.id}/acknowledge`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`${acknowledgingRequirement.name} acknowledged and completed`);
      setAcknowledgementDialogOpen(false);
      setAcknowledgingRequirement(null);
      setAcknowledgementConfirmed(false);
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit acknowledgement');
    } finally {
      setIsAcknowledging(false);
    }
  };

  // Profile photo upload handler
  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Only JPG, PNG, and WEBP images are allowed');
      return;
    }
    
    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image must be less than 5MB');
      return;
    }
    
    setIsUploadingPhoto(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      await axios.post(
        `${API}/employees/${employeeId}/profile-photo`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      toast.success('Profile photo uploaded');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload photo');
    } finally {
      setIsUploadingPhoto(false);
      if (photoInputRef.current) photoInputRef.current.value = '';
    }
  };

  // Remove profile photo handler
  const handleRemovePhoto = async () => {
    try {
      await axios.delete(
        `${API}/employees/${employeeId}/profile-photo`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Profile photo removed');
      fetchData();
    } catch (error) {
      toast.error('Failed to remove photo');
    }
  };

  // Open edit evidence modal
  const openEditEvidence = (reqId, fileData) => {
    setEditEvidenceData({ 
      requirementId: reqId, 
      file: fileData 
    });
    setEditForm({
      issue_date: fileData.issue_date || '',
      expiry_date: fileData.expiry_date || '',
      notes: fileData.notes || '',
      file_label: fileData.file_label || fileData.original_filename || '',
      reason: ''
    });
    setEditEvidenceOpen(true);
  };

  // Save evidence edits
  const handleSaveEvidenceEdit = async () => {
    if (!editForm.reason || editForm.reason.trim().length < 3) {
      toast.error('Please provide a reason for this change (min 3 characters)');
      return;
    }
    
    setIsEditingEvidence(true);
    try {
      await axios.put(
        `${API}/employees/${employeeId}/requirements/${editEvidenceData.requirementId}/evidence/${editEvidenceData.file.file_id}`,
        {
          issue_date: editForm.issue_date || null,
          expiry_date: editForm.expiry_date || null,
          notes: editForm.notes || null,
          file_label: editForm.file_label || null,
          reason: editForm.reason
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Document details updated');
      setEditEvidenceOpen(false);
      // Force refresh data immediately after edit to ensure expiry status is recalculated
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update details');
    } finally {
      setIsEditingEvidence(false);
    }
  };

  // Load evidence edit history
  const loadEditHistory = async (reqId, fileId) => {
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/requirements/${reqId}/evidence/${fileId}/history`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setEditHistory(response.data);
      setHistoryOpen(true);
    } catch (error) {
      toast.error('Failed to load history');
    }
  };

  const toggleTemplateSelection = (templateId) => {
    setSelectedTemplates(prev => 
      prev.includes(templateId)
        ? prev.filter(id => id !== templateId)
        : [...prev, templateId]
    );
  };

  const openEditDialog = () => {
    setEditForm({
      first_name: employee?.first_name || '',
      last_name: employee?.last_name || '',
      email: employee?.email || '',
      phone: employee?.phone || '',
      role: employee?.role || '',
      status: employee?.status || '',
      onboarding_status: employee?.onboarding_status || 'New',
      start_date: employee?.start_date || '',
      notes: employee?.notes || ''
    });
    setEditDialogOpen(true);
  };

  const handleSaveEmployee = async () => {
    setIsSaving(true);
    try {
      await axios.put(`${API}/employees/${employeeId}`, editForm, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employee details updated');
      setEditDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update employee');
    } finally {
      setIsSaving(false);
    }
  };

  const handleArchiveEmployee = async () => {
    try {
      await axios.post(`${API}/employees/${employeeId}/archive`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employee archived successfully');
      setArchiveDialogOpen(false);
      navigate(isRecruitmentView ? '/portal/recruitment' : '/portal/employees');
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (detail && typeof detail === 'object') {
        toast.error(detail.message || JSON.stringify(detail));
      } else {
        toast.error(detail || 'Failed to archive employee');
      }
    }
  };

  const handleRestoreEmployee = async () => {
    try {
      await axios.post(`${API}/employees/${employeeId}/restore`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employee restored successfully');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to restore employee');
    }
  };

  const handlePermanentDelete = async () => {
    try {
      await axios.delete(`${API}/employees/${employeeId}/permanent`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employee permanently deleted');
      setDeleteDialogOpen(false);
      navigate(isRecruitmentView ? '/portal/recruitment' : '/portal/employees');
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (detail && typeof detail === 'object') {
        toast.error(detail.message || JSON.stringify(detail));
      } else {
        toast.error(detail || 'Failed to delete employee');
      }
    }
  };

  // ========== Document Request Handlers ==========
  
  // Open request document dialog
  const openRequestDocDialog = (requirement, isResend = false) => {
    setRequestingRequirement(requirement);
    setRequestDocMessage('');
    setIsResendMode(isResend);
    setRequestDocDialogOpen(true);
  };
  
  // State for resend mode
  const [isResendMode, setIsResendMode] = useState(false);
  const [duplicateBlockedInfo, setDuplicateBlockedInfo] = useState(null);
  
  // Send document request email
  const handleRequestDocument = async (forceResend = false) => {
    if (!requestingRequirement) return;
    
    setIsRequestingDoc(true);
    setDuplicateBlockedInfo(null);
    
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/request-document`,
        null,
        {
          headers: { Authorization: `Bearer ${token}` },
          params: {
            requirement_id: requestingRequirement.id,
            message: requestDocMessage || undefined,
            due_days: 14,
            force_resend: forceResend || isResendMode
          }
        }
      );
      
      const status = response.data.status;
      
      if (status === 'sent') {
        toast.success(response.data.message || 'Request sent successfully');
        setRequestDocDialogOpen(false);
        setRequestingRequirement(null);
        setRequestDocMessage('');
        setIsResendMode(false);
      } else if (status === 'resent') {
        toast.success(response.data.message || 'Request resent successfully');
        setRequestDocDialogOpen(false);
        setRequestingRequirement(null);
        setRequestDocMessage('');
        setIsResendMode(false);
      } else if (status === 'duplicate_blocked') {
        // Show duplicate blocked info and offer resend option
        setDuplicateBlockedInfo({
          message: response.data.message,
          existingRequestId: response.data.existing_request_id
        });
        toast.warning('An active request already exists. Click "Resend" to send a new email.');
      } else {
        toast.info(response.data.message || 'Request processed');
        setRequestDocDialogOpen(false);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send request');
    } finally {
      setIsRequestingDoc(false);
    }
  };
  
  // Handle resend action
  const handleResendRequest = () => {
    handleRequestDocument(true);
  };

  // ========== Send Form via Email Handlers ==========
  
  const FORM_OPTIONS = [
    { value: 'staff_health_questionnaire', label: 'Health Questionnaire' },
    { value: 'staff_personal_info', label: 'Personal Details Form' },
    { value: 'hmrc_starter_checklist', label: 'HMRC Starter Checklist' },
    { value: 'interview_record', label: 'Interview Assessment Record (Admin Only)' }
  ];
  
  const openSendFormDialog = (formType) => {
    setSelectedFormType(formType || '');
    setSendFormMessage('');
    setSendFormDialogOpen(true);
  };
  
  const handleSendForm = async () => {
    if (!selectedFormType) {
      toast.error('Please select a form type');
      return;
    }
    
    setIsSendingForm(true);
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/send-form`,
        null,
        {
          headers: { Authorization: `Bearer ${token}` },
          params: {
            form_type: selectedFormType,
            message: sendFormMessage || undefined
          }
        }
      );
      
      if (response.data.status === 'duplicate') {
        toast.info(response.data.message || 'Form request already pending');
      } else {
        toast.success(response.data.message || 'Form request sent');
      }
      
      setSendFormDialogOpen(false);
      setSelectedFormType('');
      setSendFormMessage('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send form request');
    } finally {
      setIsSendingForm(false);
    }
  };

  // ========== Application Form Extraction Handlers ==========
  
  // Start extraction from application form
  const handleExtractFromApplication = async () => {
    setIsExtracting(true);
    setExtractionDialogOpen(true);
    setExtractionResult(null);
    setExtractionFailed(null);
    setFieldsToApply({});
    
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/extract-from-application`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Check if extraction failed gracefully (returns extraction_failed: true)
      if (response.data.extraction_failed) {
        setExtractionFailed(response.data);
        // Don't show error toast - show the options modal instead
      } else {
        setExtractionResult(response.data);
        
        // Initialize fields to apply based on extraction result
        const initialFields = {};
        response.data.fields.forEach(field => {
          // Default: apply if field is empty in profile OR if extracted value differs
          initialFields[field.field_name] = field.apply;
        });
        setFieldsToApply(initialFields);
        
        toast.success(`Extracted ${response.data.fields.length} fields from application form`);
      }
    } catch (error) {
      // Only show toast for actual API errors (not graceful failures)
      const errorDetail = error.response?.data?.detail;
      if (errorDetail && errorDetail.includes('No application form found')) {
        toast.error('No application form found. Please upload an application form first.');
        setExtractionDialogOpen(false);
      } else {
        // For unexpected errors, show failure options
        setExtractionFailed({
          extraction_failed: true,
          message: errorDetail || 'An unexpected error occurred during extraction.',
          options: [
            { action: 'fill_manually', label: 'Fill form manually', description: 'Enter profile data manually' },
            { action: 'retry', label: 'Retry extraction', description: 'Try extracting again' }
          ]
        });
      }
    } finally {
      setIsExtracting(false);
    }
  };
  
  // Handle extraction failure options
  const handleExtractionOption = async (action) => {
    switch (action) {
      case 'fill_manually':
        setExtractionDialogOpen(false);
        setExtractionFailed(null);
        // Switch to forms tab for manual entry
        setActiveTab('forms');
        toast.info('You can manually enter profile data using the forms below.');
        break;
      case 'view_document':
        if (extractionFailed?.file_url) {
          window.open(extractionFailed.file_url, '_blank');
        }
        break;
      case 'retry':
        setExtractionFailed(null);
        await handleExtractFromApplication();
        break;
      default:
        break;
    }
  };
  
  // Toggle a field for applying
  const toggleFieldToApply = (fieldName) => {
    setFieldsToApply(prev => ({
      ...prev,
      [fieldName]: !prev[fieldName]
    }));
  };
  
  // Apply selected extracted fields to profile
  const handleApplyExtraction = async () => {
    if (!extractionResult) return;
    
    const selectedFields = Object.entries(fieldsToApply)
      .filter(([_, apply]) => apply)
      .map(([fieldName]) => fieldName);
    
    if (selectedFields.length === 0) {
      toast.error('Please select at least one field to apply');
      return;
    }
    
    setIsApplyingExtraction(true);
    try {
      const response = await axios.post(
        `${API}/extractions/${extractionResult.extraction_id}/apply`,
        { extraction_id: extractionResult.extraction_id, fields_to_apply: selectedFields },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      const result = response.data;
      
      // Show success with details
      if (result.applied_fields && result.applied_fields.length > 0) {
        toast.success(`Profile updated: ${result.applied_fields.length} field(s) applied`);
      }
      
      // Show warnings for failed fields
      if (result.warnings?.failed_fields?.length > 0) {
        const failedNames = result.warnings.failed_fields.map(f => f.field).join(', ');
        toast.warning(`Some fields could not be applied: ${failedNames}`);
      }
      
      // Show info for unsupported fields
      if (result.unsupported?.fields?.length > 0) {
        const unsupportedNames = result.unsupported.fields.map(f => f.field).join(', ');
        toast.info(`Unsupported fields skipped: ${unsupportedNames}`);
      }
      
      setExtractionDialogOpen(false);
      setExtractionResult(null);
      
      // Refresh employee data
      try {
        await fetchData();
      } catch (refreshError) {
        console.error('Error refreshing data after apply:', refreshError);
        // Don't show error toast - the apply was successful
      }
    } catch (error) {
      const errorDetail = error.response?.data?.detail;
      
      if (typeof errorDetail === 'object') {
        // Structured error response
        const message = errorDetail.message || 'Failed to apply extracted data';
        const failedFields = errorDetail.failed_fields || [];
        const unsupportedFields = errorDetail.unsupported_fields || [];
        
        if (failedFields.length > 0) {
          const failedInfo = failedFields.map(f => `${f.field}: ${f.reason}`).join('\n');
          toast.error(`${message}\n${failedInfo}`);
        } else if (unsupportedFields.length > 0) {
          toast.error(`${message}: ${unsupportedFields.map(f => f.field).join(', ')}`);
        } else {
          toast.error(message);
        }
      } else {
        toast.error(errorDetail || 'Failed to apply extracted data');
      }
    } finally {
      setIsApplyingExtraction(false);
    }
  };
  
  // Discard extraction without applying
  const handleDiscardExtraction = async () => {
    // If there's a failed extraction, just close the dialog
    if (extractionFailed) {
      setExtractionDialogOpen(false);
      setExtractionFailed(null);
      return;
    }
    
    if (!extractionResult) {
      setExtractionDialogOpen(false);
      return;
    }
    
    try {
      await axios.post(
        `${API}/extractions/${extractionResult.extraction_id}/discard`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.info('Extraction discarded');
    } catch (error) {
      // Ignore discard errors
    }
    
    setExtractionDialogOpen(false);
    setExtractionResult(null);
    setExtractionFailed(null);
  };
  
  // Human-readable field name mapping
  const FIELD_LABELS = {
    first_name: 'First Name',
    last_name: 'Last Name',
    email: 'Email Address',
    phone: 'Phone Number',
    address_line_1: 'Address Line 1',
    address_line_2: 'Address Line 2',
    city: 'City',
    county: 'County',
    postcode: 'Postcode',
    country: 'Country',
    ni_number: 'NI Number',
    date_of_birth: 'Date of Birth',
    next_of_kin_name: 'Next of Kin Name',
    next_of_kin_relationship: 'Next of Kin Relationship',
    next_of_kin_phone: 'Next of Kin Phone',
    next_of_kin_address: 'Next of Kin Address',
    emergency_contact_name: 'Emergency Contact Name',
    emergency_contact_phone: 'Emergency Contact Phone',
    emergency_contact_relationship: 'Emergency Contact Relationship',
    reference_1_name: 'Reference 1 Name',
    reference_1_company: 'Reference 1 Company',
    reference_1_phone: 'Reference 1 Phone',
    reference_1_email: 'Reference 1 Email',
    reference_2_name: 'Reference 2 Name',
    reference_2_company: 'Reference 2 Company',
    reference_2_phone: 'Reference 2 Phone',
    reference_2_email: 'Reference 2 Email',
    has_driving_licence: 'Has Driving Licence',
    driving_licence_type: 'Driving Licence Type',
    has_own_vehicle: 'Has Own Vehicle',
    vehicle_registration: 'Vehicle Registration'
  };

  // ========== Form Submission Handlers ==========
  
  // Open form modal for a specific requirement
  const openFormModal = async (requirementId) => {
    try {
      const response = await axios.get(`${API}/form-submissions/template/${requirementId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setFormTemplate(response.data);
      
      // Check if there's an existing submission to pre-fill
      const existingResponse = await axios.get(`${API}/form-submissions?employee_id=${employeeId}&requirement_id=${requirementId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Get today's date in YYYY-MM-DD format for auto-fill
      const today = new Date().toISOString().split('T')[0];
      
      if (existingResponse.data && existingResponse.data.length > 0) {
        // Use existing submission data
        setFormData(existingResponse.data[0].data || {});
      } else {
        // Fetch auto-fill data from backend based on employee profile
        try {
          const autoFillResponse = await axios.get(
            `${API}/form-submissions/auto-fill/${requirementId}/${employeeId}`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          // Add today's date for signature_date if not already set
          const autoFillData = autoFillResponse.data.auto_fill_data || {};
          if (!autoFillData.signature_date) {
            autoFillData.signature_date = today;
          }
          setFormData(autoFillData);
        } catch (autoFillError) {
          // Fallback to basic employee data if auto-fill endpoint fails
          setFormData({
            employee_name: `${employee.first_name} ${employee.last_name}`,
            full_name: `${employee.first_name} ${employee.last_name}`,
            candidate_name: `${employee.first_name} ${employee.last_name}`,
            signature_date: today
          });
        }
      }
      
      setFormModalOpen(true);
    } catch (error) {
      toast.error('Failed to load form template');
    }
  };
  
  // Submit structured form
  const handleFormSubmit = async () => {
    if (!formTemplate) return;
    
    setIsSubmittingForm(true);
    try {
      await axios.post(`${API}/form-submissions`, {
        employee_id: employeeId,
        requirement_id: formTemplate.requirement_id,
        form_type: formTemplate.form_type,
        data: formData
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success(`${formTemplate.name} submitted successfully`);
      setFormModalOpen(false);
      setFormTemplate(null);
      setFormData({});
      fetchData(); // Refresh all data including compliance requirements
    } catch (error) {
      console.error('Form submission error:', error);
      toast.error(error.response?.data?.detail || 'Failed to submit form');
    } finally {
      setIsSubmittingForm(false);
    }
  };
  
  // View submitted form
  const openViewForm = (requirement) => {
    if (requirement.form_submission) {
      setViewFormData({
        ...requirement.form_submission,
        requirementName: requirement.name
      });
      setViewFormOpen(true);
    }
  };
  
  // Verify form submission
  const handleVerifyFormSubmission = async (submissionId) => {
    try {
      await axios.post(`${API}/form-submissions/${submissionId}/verify`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Form verified successfully');
      setViewFormOpen(false);
      fetchData(); // Refresh all data including compliance requirements
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify form');
    }
  };

  // Generate PDF from form submission (Template-Backed Forms Architecture)
  const handleGenerateFormPDF = async (submissionId, formType) => {
    setIsGenerating(true);
    try {
      const response = await axios.post(
        `${API}/form-submissions/${submissionId}/generate-pdf`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data.file_url) {
        // Open the generated PDF in a new tab
        window.open(response.data.file_url, '_blank');
        toast.success('PDF generated successfully');
      }
    } catch (error) {
      console.error('PDF generation error:', error);
      toast.error(error.response?.data?.detail || 'Failed to generate PDF');
    } finally {
      setIsGenerating(false);
    }
  };

  // Download existing PDF export or generate new one
  const handleDownloadFormPDF = async (submissionId) => {
    try {
      // Use responseType: 'blob' to receive the actual PDF file bytes
      const response = await axios.get(
        `${API}/form-submissions/${submissionId}/download-pdf`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      // Extract filename from Content-Disposition header if available
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'form.pdf';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^";\n]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      // Create a blob URL and trigger download
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('PDF downloaded successfully');
    } catch (error) {
      toast.error(await getSafeErrorMessage(error, 'Failed to download PDF'));
    }
  };

  // View PDF in a new tab
  const handleViewFormPDF = async (submissionId) => {
    setInlineViewerUrl(`${API}/form-submissions/${submissionId}/view-pdf`);
    setInlineViewerTitle('Application Form');
    setInlineViewerFilename('application-form.pdf');
    setInlineViewerFallback(null);
    setInlineViewerOpen(true);
  };

  const handleReopenFormForCorrection = async () => {
    const reason = formCorrectionReason.trim();
    if (!formCorrectionDialog?.submission?.id || !reason) {
      toast.error('Correction reason is required');
      return;
    }

    setIsReopeningFormCorrection(true);
    try {
      await axios.post(
        `${API}/form-submissions/${formCorrectionDialog.submission.id}/reopen-for-correction`,
        { reason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Form reopened for worker correction');
      setFormCorrectionDialog(null);
      setFormCorrectionReason('');
      fetchFormSubmissions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reopen form for correction');
    } finally {
      setIsReopeningFormCorrection(false);
    }
  };

  const openFormSubmissionPdfViewer = (submission, form) => {
    if (!submission?.id) {
      setViewFormSubmission({
        isOpen: true,
        formType: form?.key,
        formName: form?.name,
        submissionId: submission?.id,
        data: submission?.data || submission?.form_data
      });
      return;
    }
    setInlineViewerUrl(`${API}/form-submissions/${submission.id}/view-pdf`);
    setInlineViewerTitle(form?.name || 'Form Submission');
    setInlineViewerFilename(`${form?.key || 'form'}_${employee?.first_name || ''}_${employee?.last_name || ''}.pdf`);
    setInlineViewerFallback({
      isOpen: true,
      formType: form?.key,
      formName: form?.name,
      submissionId: submission?.id,
      data: submission?.data || submission?.form_data
    });
    setInlineViewerOpen(true);
  };

  const groupedTemplates = templates.reduce((acc, template) => {
    if (!acc[template.category]) acc[template.category] = [];
    acc[template.category].push(template);
    return acc;
  }, {});

  const groupedDocs = documentTypes.reduce((acc, type) => {
    if (!acc[type.category]) acc[type.category] = [];
    const doc = documents.find(d => d.document_type_id === type.id);
    acc[type.category].push({ ...type, document: doc });
    return acc;
  }, {});
  const applicationSubmission =
    formSubmissions.find((submission) =>
      submission?.requirement_id === 'application_form' || submission?.form_type === 'application_form'
    ) || null;
  const applicationPdfDocument = documents.find((document) => document?.requirement_id === 'application_form_pdf') || null;
  const rtwSummary = complianceRequirements?.rtw_summary || {};
  const isLinkedActiveCvDocument = (document) => Boolean(
    employee?.cv_document_id &&
    [document?.id, document?.file_id, document?.document_id].filter(Boolean).includes(employee.cv_document_id)
  );
  const isCvLikeDocument = (document) => {
    const cvRequirementIds = ['cv', 'resume', 'curriculum_vitae'];
    const label = [
      document?.requirement_name,
      document?.document_type_name,
      document?.document_label,
      document?.original_filename,
      document?.file_name
    ].filter(Boolean).join(' ').toLowerCase();

    return (
      cvRequirementIds.includes(document?.requirement_id) ||
      isLinkedActiveCvDocument(document) ||
      /\b(cv|resume|curriculum vitae)\b/.test(label)
    );
  };
  const cvDocuments = documents.filter(isCvLikeDocument);
  const activeCvDocument = cvDocuments.find(isLinkedActiveCvDocument) || null;
  // If cv_document_id is set but no document matches, do NOT fall back to cvDocuments[0].
  // Opening the wrong file would silently mismatch what the backend's Review CV operates on.
  const cvDocumentIdIsSet = Boolean(employee?.cv_document_id);
  const cvDocument = activeCvDocument || (cvDocumentIdIsSet ? null : cvDocuments[0] || null);
  const complianceEmploymentHistoryGapRow = complianceFile?.sections?.employment_history?.rows?.[0] || null;
  // Canonical admin read source: persisted employment_review first, compliance-file row fallback during rollout.
  const hasPersistedEmploymentReview = Boolean(employmentReviewPersisted && employmentReview?.id);
  const employmentReviewSegments = Array.isArray(employmentReview?.segments) ? employmentReview.segments : [];
  const persistedEmploymentSegments = employmentReviewSegments.filter((segment) => segment?.type === 'employment');
  const persistedGapSegments = employmentReviewSegments.filter((segment) => segment?.type === 'gap');
  const canonicalEmploymentRecords = hasPersistedEmploymentReview
    ? persistedEmploymentSegments.map((segment) => ({
        ...(segment.raw_record || {}),
        id: segment.id,
        employer: segment.employer || segment.organisation,
        employer_name: segment.employer || segment.organisation,
        company: segment.organisation || segment.employer,
        job_title: segment.title || segment.role,
        role: segment.role || segment.title,
        start_date: segment.start_date,
        end_date: segment.end_date === 'present' ? null : segment.end_date,
        source: segment.source,
      }))
    : Array.isArray(complianceEmploymentHistoryGapRow?.employment_records)
      ? complianceEmploymentHistoryGapRow.employment_records
    : [];
  const canonicalEmploymentGaps = hasPersistedEmploymentReview
    ? persistedGapSegments.map((gap) => ({
        ...gap,
        gap_id: gap.gap_id || gap.id,
        gap_start: gap.start_date,
        gap_end: gap.end_date,
        status: gap.raw_status || (gap.status === 'missing' ? 'pending' : gap.status),
        explanation: gap.explanation?.text || gap.explanation?.explanation,
        reason_type: gap.explanation?.reason_type,
        explanation_provided_at: gap.explanation?.submitted_at,
        verified_by: gap.admin_review?.reviewed_by,
        verified_by_name: gap.admin_review?.reviewed_by_name,
        verified_at: gap.admin_review?.reviewed_at,
        rejection_reason: gap.admin_review?.rejection_reason,
      }))
    : Array.isArray(complianceEmploymentHistoryGapRow?.canonical_gaps)
      ? complianceEmploymentHistoryGapRow.canonical_gaps
      : (complianceEmploymentHistoryGapRow?.gaps || []);
  const matchedApplicantGapExplanations = hasPersistedEmploymentReview
    ? persistedGapSegments
        .filter((gap) => gap?.explanation)
        .map((gap) => ({
          ...(gap.explanation || {}),
          explanation: gap.explanation?.text || gap.explanation?.explanation,
          reason_type: gap.explanation?.reason_type,
          gap_id: gap.gap_id || gap.id,
          matched_gap_id: gap.gap_id || gap.id,
          gap_start: gap.start_date,
          gap_end: gap.end_date,
          duration_days: gap.duration_days,
          duration_months: gap.duration_months,
          matched_by: gap.explanation?.matched_by,
        }))
    : (complianceEmploymentHistoryGapRow?.matched_applicant_explanations || []);
  const unmatchedApplicantGapExplanations = hasPersistedEmploymentReview
    ? (employmentReview?.unmatched_applicant_notes || [])
    : (complianceEmploymentHistoryGapRow?.unmatched_applicant_explanations || []);
  const invalidEmploymentEntries = hasPersistedEmploymentReview
    ? (employmentReview?.invalid_entries || [])
    : (complianceEmploymentHistoryGapRow?.invalid_employment_entries || []);
  const employmentGapEvaluation = hasPersistedEmploymentReview
    ? {
        has_gaps: (employmentReview?.top_summary?.gap_segments || 0) > 0,
        total_gaps: employmentReview?.top_summary?.gap_segments || 0,
        verified_count: employmentReview?.top_summary?.verified_gaps || 0,
        pending_count: employmentReview?.top_summary?.missing_gaps || 0,
        explained_count: employmentReview?.top_summary?.explained_gaps || 0,
        rejected_count: employmentReview?.top_summary?.rejected_gaps || 0,
        needs_info_count: 0,
        is_complete: (employmentReview?.top_summary?.gap_segments || 0) === (employmentReview?.top_summary?.verified_gaps || 0),
      }
    : (complianceEmploymentHistoryGapRow?.gap_evaluation || null);
  const gapAnalysisRun = hasPersistedEmploymentReview || Boolean(complianceEmploymentHistoryGapRow?.gap_analysis_run);
  const employmentHistoryGapRow = hasPersistedEmploymentReview
    ? {
        has_gaps: persistedGapSegments.length > 0,
        status_summary: employmentReview?.status_reason,
        gap_evaluation: employmentGapEvaluation,
        gap_analysis_run: true,
        gap_analysis_status: employmentReview?.diagnostics?.analysis_status,
        gap_analysis_error: employmentReview?.diagnostics?.analysis_error,
      }
    : complianceEmploymentHistoryGapRow;
  const applicationAvailable = Boolean(applicationSubmission || applicationPdfDocument);
  const cvFileExists = Boolean(cvDocument);
  const cvDocumentName = cvDocument?.original_filename || cvDocument?.file_name || cvDocument?.file_url || '';
  const cvDocumentMimeType = (cvDocument?.mime_type || cvDocument?.content_type || cvDocument?.file_type || '').toLowerCase();
  const cvIsPdf = Boolean(
    cvDocument && (cvDocumentMimeType === 'application/pdf' || /\.pdf(?:$|\?)/i.test(cvDocumentName))
  );
  const cvLinkedForReview = Boolean(employee?.cv_document_id && activeCvDocument);
  const cvReviewReady = Boolean(cvLinkedForReview && activeCvDocument && cvIsPdf);
  const cvStatusLabel = cvFileExists ? 'On file' : 'Missing';
  const cvStatusBadgeClass =
    cvFileExists
      ? 'bg-green-100 text-green-700 border-green-200'
      : 'bg-gray-100 text-gray-600 border-gray-200';
  const gapVerifiedCount = employmentGapEvaluation?.verified_count;
  const gapNeedsReviewCount = employmentGapEvaluation
    ? (employmentGapEvaluation?.pending_count || 0) +
      (employmentGapEvaluation?.explained_count || 0) +
      (employmentGapEvaluation?.rejected_count || 0) +
      (employmentGapEvaluation?.needs_info_count || 0)
    : null;
  const employmentHistoryExists = Boolean(canonicalEmploymentRecords.length > 0);
  const employmentHistoryHasDatedRows = Boolean(
    canonicalEmploymentRecords.some((job) => job?.start_date)
  );
  const employmentCoverage = hasPersistedEmploymentReview
    ? (employmentReview?.coverage || null)
    : (employmentHistoryGapRow?.employment_coverage || null);
  const coveragePercent = Number(employmentCoverage?.coverage_percent ?? employmentCoverage?.percent);
  const coverageHasNumericPercent = Number.isFinite(coveragePercent);
  const coverageTotalDaysRequired = Number(employmentCoverage?.total_days_required);
  const coverageTotalDaysCovered = Number(employmentCoverage?.total_days_covered);
  const coverageHasUsableSummary = Boolean(
    employmentCoverage &&
    coverageHasNumericPercent &&
    Number.isFinite(coverageTotalDaysRequired) &&
    coverageTotalDaysRequired > 0 &&
    Number.isFinite(coverageTotalDaysCovered)
  );
  const coverageDisplayPercent = coverageHasUsableSummary ? coveragePercent : 0;
  const coverageLooksStaleOrUnusable = Boolean(
    employmentCoverage &&
    employmentHistoryHasDatedRows &&
    coverageHasNumericPercent &&
    coveragePercent === 0 &&
    !employmentCoverage?.earliest_entry_date &&
    !employmentCoverage?.latest_entry_date
  );
  const coverageAssessed = Boolean(coverageHasUsableSummary && !coverageLooksStaleOrUnusable);
  const coverageMet = Boolean(
    employmentCoverage?.meets_10_year_requirement && coverageAssessed
  );
  const employmentCannotAssess = !hasPersistedEmploymentReview && !complianceFile;
  const employmentSignedOff = hasPersistedEmploymentReview
    ? Boolean(employmentReview?.sign_off?.signed_off)
    : Boolean(employee?.employment_review_signed_off);
  const employmentSignedOffBy = hasPersistedEmploymentReview
    ? (employmentReview?.sign_off?.signed_off_by_name || employmentReview?.sign_off?.signed_off_by || null)
    : (employee?.employment_review_signed_off_by_name || employee?.employment_review_signed_off_by || null);
  const employmentSignedOffAt = hasPersistedEmploymentReview
    ? employmentReview?.sign_off?.signed_off_at
    : employee?.employment_review_signed_off_at || null;
  const gapAnalysisFailed = hasPersistedEmploymentReview
    ? employmentReview?.status === 'cannot_assess'
    : employmentHistoryGapRow?.gap_analysis_status === 'failed';
  const gapAnalysisError = employmentHistoryGapRow?.gap_analysis_error;
  const employmentGapsCannotAssess = Boolean(
    hasPersistedEmploymentReview
      ? employmentReview?.status === 'cannot_assess'
      : employmentHistoryExists && (gapAnalysisFailed || !employmentHistoryGapRow || !gapAnalysisRun || !employmentGapEvaluation)
  );
  const allGapsResolved = Boolean(
    hasPersistedEmploymentReview
      ? employmentGapEvaluation?.is_complete
      : employmentHistoryExists &&
        gapAnalysisRun &&
        employmentGapEvaluation &&
        employmentGapEvaluation.is_complete &&
        gapNeedsReviewCount === 0
  );
  // declarationsOnFile: true once EditDeclarationsDialog has been saved (dbs_consent_given is always written)
  const declarationsOnFile = Boolean(
    employee?.declarations && 'dbs_consent_given' in employee.declarations
  );
  const declarationsReviewRecorded = Boolean(
    employee?.declarations_reviewed_at ||
    employee?.declarations_reviewed_by ||
    employee?.declarations?.reviewed_at ||
    employee?.declarations?.reviewed_by ||
    employee?.declarations?.review_status === 'reviewed' ||
    employee?.declarations?.review_status === 'signed_off' ||
    employee?.declarations?.reviewed === true
  );
  const declarationsAdequatelyReviewed = Boolean(
    declarationsOnFile && (declarationsReviewRecorded || employmentSignedOff)
  );
  // CV linkage is supporting evidence, not a sign-off prerequisite.
  // The mandatory chain is: application form + employment history + coverage + gaps + declarations.
  // A CV may not exist (e.g. entry-level workers) and that already does not block sign-off,
  // so an unlinked/non-PDF CV should not block either — it is surfaced as a warning instead.
  const cvLinkBlocksReview = Boolean(cvFileExists && !cvReviewReady && employee?.cv_status !== 'approved');
  // Pre-conditions gate: all data requirements satisfied, ready for admin sign-off
  // Coverage must be met AND all gaps resolved
  const employmentReadyForSignOff = hasPersistedEmploymentReview
    ? Boolean(
        !employmentSignedOff &&
        !employmentCannotAssess &&
        applicationAvailable &&
        declarationsAdequatelyReviewed &&
        employmentHistoryExists &&
        !employmentGapsCannotAssess &&
        employmentReview?.gap_actions?.can_sign_off
      )
    : Boolean(
        !employmentSignedOff &&
        !employmentCannotAssess &&
        applicationAvailable &&
        declarationsAdequatelyReviewed &&
        employmentHistoryExists &&
        coverageAssessed &&
        coverageMet &&
        !employmentGapsCannotAssess &&
        allGapsResolved
      );
  // Final "Complete" requires the persisted sign-off, not just derived conditions
  const employmentComplete = employmentSignedOff;
  const employmentDecisionState = employmentComplete
    ? 'Signed off'
    : employmentCannotAssess || employmentGapsCannotAssess || (!hasPersistedEmploymentReview && !coverageAssessed)
      ? 'Cannot assess'
      : employmentReadyForSignOff
        ? 'Ready for sign-off'
        : 'Blocked';
  const employmentDecisionDisplay = employmentDecisionState === 'Cannot assess'
    ? 'needs review data'
    : employmentDecisionState.toLowerCase();
  const employmentDecisionClasses = employmentDecisionState === 'Signed off'
    ? {
        panel: 'border-green-200 bg-green-50',
        icon: 'text-green-600',
        text: 'text-green-800',
        subtext: 'text-green-700',
      }
    : employmentDecisionState === 'Ready for sign-off'
      ? {
          panel: 'border-blue-200 bg-blue-50',
          icon: 'text-blue-600',
          text: 'text-blue-800',
          subtext: 'text-blue-700',
        }
      : employmentDecisionState === 'Cannot assess'
        ? {
            panel: 'border-red-200 bg-red-50',
            icon: 'text-red-600',
            text: 'text-red-800',
            subtext: 'text-red-700',
          }
        : {
            panel: 'border-amber-200 bg-amber-50',
            icon: 'text-amber-600',
            text: 'text-amber-800',
            subtext: 'text-amber-700',
          };
  const legacyEmploymentStatusBlockers = [
    employmentCannotAssess ? 'Compliance file unavailable' : null,
    !applicationAvailable ? 'Application evidence missing' : null,
    !declarationsAdequatelyReviewed ? 'Declarations not reviewed' : null,
    !employmentHistoryExists ? 'Employment history missing' : null,
    !employmentCoverage ? 'Coverage not assessed — run gap analysis' : null,
    (employmentCoverage && !coverageAssessed) ? 'Cannot assess 10-year coverage from current data' : null,
    (coverageAssessed && !coverageMet) ? '10-year coverage not met' : null,
    employmentGapsCannotAssess ? 'Unable to confirm gaps from the current history' : null,
    (!employmentGapsCannotAssess && employmentHistoryExists && !allGapsResolved) ? 'Detected gaps unresolved' : null,
  ].filter(Boolean);
  const canonicalReviewBlockers = hasPersistedEmploymentReview
    ? (employmentReview?.gap_actions?.blocked_sign_off_reasons || [])
    : [];
  const employmentStatusBlockers = hasPersistedEmploymentReview
    ? [
        employmentReviewError ? 'Canonical employment review unavailable' : null,
        !applicationAvailable ? 'Application evidence missing' : null,
        !declarationsAdequatelyReviewed ? 'Declarations not reviewed' : null,
        !employmentHistoryExists ? 'Employment history missing' : null,
        employmentGapsCannotAssess ? 'Unable to confirm gaps from the current history' : null,
        ...canonicalReviewBlockers,
      ].filter(Boolean)
    : legacyEmploymentStatusBlockers;
  // CV is supporting evidence only — it does not block sign-off.
  // Employment history comes from the application form.
  const employmentStatusWarnings = [].filter(Boolean);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!employee) {
    return (
      <div className="text-center py-12">
        <p className="text-text-muted">{isRecruitmentView ? 'Applicant' : 'Employee'} not found</p>
        <Link to={isRecruitmentView ? '/portal/recruitment' : '/portal/employees'}>
          <Button className="mt-4">{isRecruitmentView ? 'Back to Recruitment Pipeline' : 'Back to Staff'}</Button>
        </Link>
      </div>
    );
  }

  // UCE is the ONLY source of readiness truth. No fallback to the embedded copy.
  const canonicalProgress = unifiedProgress || null;
  const canonicalProgressPct = canonicalProgress?.overall_percentage ?? 0;
  const canonicalBlockers = canonicalProgress?.blockers || [];
  const canonicalBlockerDetails = canonicalProgress?.blocker_details || [];
  const canonicalBlockerObjects = canonicalBlockerDetails.length > 0
    ? canonicalBlockerDetails
    : canonicalBlockers.map((blocker) => (
        typeof blocker === 'string'
          ? { reason: blocker, label: blocker, severity: 'critical' }
          : blocker
      ));
  const canonicalPendingBlockers = canonicalBlockerObjects.filter((blocker) => blocker?.severity === 'pending');
  const canonicalCriticalBlockers = canonicalBlockerObjects.filter((blocker) => blocker?.severity !== 'pending');
  const canonicalIsWorkReady = canonicalProgress?.is_work_ready === true;
  const canonicalCanPromote = canonicalProgress?.can_promote === true;
  const canonicalCompletedRequirements = canonicalProgress?.completed_requirements ?? canonicalProgress?.progress?.completed ?? null;
  const canonicalTotalRequirements = canonicalProgress?.total_requirements ?? canonicalProgress?.progress?.total ?? null;
  const canonicalRequirementCountAvailable = Number.isFinite(canonicalTotalRequirements) && canonicalTotalRequirements > 0;
  const canonicalReadinessLabel = canonicalIsWorkReady
    ? 'Work Ready'
    : canonicalCanPromote
      ? 'Ready for Promotion'
      : 'Not Work Ready';
  const canonicalReadinessClass = canonicalIsWorkReady || canonicalCanPromote
    ? 'bg-green-100 text-green-800'
    : 'bg-red-100 text-red-800';
  const canonicalProgressComplete = canonicalProgressPct === 100;

  return (
    <div className="space-y-6" data-testid="employee-profile">
      {/* Back Link - Returns to correct section based on route context */}
      <button 
        onClick={() => navigate(isRecruitmentView ? '/portal/recruitment' : '/portal/employees')} 
        className="inline-flex items-center gap-2 text-text-muted hover:text-primary transition-colors"
        data-testid="back-link"
      >
        <ArrowLeft className="h-4 w-4" />
        {isRecruitmentView ? 'Back to Recruitment Pipeline' : 'Back to Staff'}
      </button>

      {/* Recruitment Context Banner - Show when viewing applicant from recruitment */}
      {isRecruitmentView && lifecycleStage === 'recruitment' && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
              <User className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="font-medium text-blue-800">Applicant Profile</p>
              <p className="text-sm text-blue-600">Start with employment history, interview, references, and verification before approving.</p>
            </div>
          </div>
          <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-300">
            Recruitment Review
          </Badge>
        </div>
      )}

      {/* Header Card */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-6">
          <div className="flex flex-col lg:flex-row lg:items-start gap-6">
            <div className="flex items-start gap-4 flex-1">
              {/* Profile Photo with Upload */}
              <div className="relative group">
                {profilePhotoBlob ? (
                  <img 
                    src={profilePhotoBlob} 
                    alt={`${employee.first_name} ${employee.last_name}`}
                    className="w-16 h-16 rounded-2xl object-cover border-2 border-[#E4E8EB]"
                    data-testid="profile-photo"
                  />
                ) : (
                  <div className="w-16 h-16 bg-accent rounded-2xl flex items-center justify-center">
                    <span className="text-primary font-heading font-bold text-xl">
                      {employee.first_name?.charAt(0)}{employee.last_name?.charAt(0)}
                    </span>
                  </div>
                )}
                {/* Upload/Edit overlay */}
                {!isAuditor() && (
                  <div className="absolute inset-0 bg-black/50 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <label className="cursor-pointer p-2">
                      <input
                        ref={photoInputRef}
                        type="file"
                        accept="image/jpeg,image/jpg,image/png,image/webp"
                        onChange={handlePhotoUpload}
                        className="hidden"
                        disabled={isUploadingPhoto}
                      />
                      {isUploadingPhoto ? (
                        <Loader2 className="h-5 w-5 text-white animate-spin" />
                      ) : (
                        <Camera className="h-5 w-5 text-white" />
                      )}
                    </label>
                    {employee.profile_photo_url && (
                      <button
                        onClick={handleRemovePhoto}
                        className="p-2 hover:bg-white/20 rounded-lg"
                        title="Remove photo"
                      >
                        <XCircle className="h-4 w-4 text-white" />
                      </button>
                    )}
                  </div>
                )}
              </div>
              <div>
                <h1 className="font-heading text-2xl font-bold text-text-primary">
                  {employee.first_name} {employee.last_name}
                </h1>
                <p className="text-text-muted">
                  {employee.employee_code || employee.applicant_reference || 'No ID assigned'} · {employee.role}
                </p>
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  {/* Person Stage Badge - CLEAR APPLICANT VS STAFF DISTINCTION */}
                  {employee.person_stage === 'applicant' ? (
                    <span className="px-2 py-1 rounded-lg text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
                      Applicant
                    </span>
                  ) : (
                    <span className="px-2 py-1 rounded-lg text-xs font-medium bg-green-100 text-green-800 border border-green-200">
                      Staff
                    </span>
                  )}
                  <span className={`status-chip ${
                    employee.status === 'active' ? 'status-success' :
                    employee.status === 'onboarding' ? 'status-info' :
                    employee.status === 'screening' || employee.status === 'interview' || employee.status === 'compliance_review' ? 'status-warning' :
                    'status-neutral'
                  }`}>
                    {employee.status === 'compliance_review' ? 'Awaiting Approval' : employee.status?.replace('_', ' ')}
                  </span>
                  {/* Simplified Status Flow: Awaiting Approval → Ready → Active Employee */}
                  {(() => {
                    // Active Employee - already promoted
                    if (employee.status === 'active_employee') {
                      return (
                        <span className="px-2 py-1 rounded-lg text-xs font-medium bg-green-100 text-green-800" data-testid="active-employee-badge">
                          Active Employee
                        </span>
                      );
                    }
                    if (canonicalCanPromote) {
                      return (
                        <span className="px-2 py-1 rounded-lg text-xs font-medium bg-green-100 text-green-800" data-testid="ready-badge">
                          Ready for Promotion
                        </span>
                      );
                    }
                    if (canonicalProgressComplete && canonicalIsWorkReady) {
                      return (
                        <span className="px-2 py-1 rounded-lg text-xs font-medium bg-green-100 text-green-800" data-testid="ready-badge">
                          Work Ready
                        </span>
                      );
                    }
                    // Outstanding items remain - 0-99% complete (default for all applicants/onboarding)
                    return (
                      <span className="px-2 py-1 rounded-lg text-xs font-medium bg-amber-100 text-amber-800" data-testid="awaiting-approval-badge">
                        Outstanding items remain
                      </span>
                    );
                  })()}
                  {/* Canonical Work Readiness Status Badge */}
                  {employee.person_stage === 'employee' && (() => {
                    const reasons = canonicalBlockerObjects.map((blocker) => blocker.reason || blocker.message || blocker.label).filter(Boolean);
                    
                    return (
                      <div className="flex flex-col items-start gap-1">
                        <span className={`px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 ${canonicalReadinessClass}`} data-testid="work-readiness-badge">
                          {canonicalIsWorkReady || canonicalCanPromote ? (
                            <Shield className="h-3.5 w-3.5" />
                          ) : (
                            <AlertTriangle className="h-3.5 w-3.5" />
                          )}
                          {canonicalReadinessLabel}
                        </span>
                        {reasons.length > 0 && !canonicalIsWorkReady && !canonicalCanPromote && (
                          <div className="flex flex-wrap gap-1 max-w-md">
                            {reasons.slice(0, 3).map((reason, idx) => (
                              <span 
                                key={idx} 
                                className="text-[10px] px-1.5 py-0.5 rounded bg-red-100 text-red-700"
                              >
                                {reason}
                              </span>
                            ))}
                            {reasons.length > 3 && (
                              <span className="text-[10px] text-gray-500">+{reasons.length - 3} more</span>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>
            </div>

            <div className="flex flex-col items-end gap-4">
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <p className="text-sm text-text-muted">Overall Compliance</p>
                  <p className="text-3xl font-heading font-bold text-text-primary">
                    {canonicalProgressPct}% Complete
                  </p>
                  <p className="text-xs text-text-muted mt-0.5">
                    {canonicalRequirementCountAvailable
                      ? `${canonicalCompletedRequirements ?? 0} of ${canonicalTotalRequirements} requirements`
                      : 'Requirement count unavailable'}
                  </p>
                </div>
                {!isAuditor() && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="outline" size="sm" className="h-10 w-10 p-0 rounded-xl" data-testid="employee-actions-btn">
                        <MoreHorizontal className="h-5 w-5" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                      <DropdownMenuItem onClick={openEditDialog}>
                        <Edit className="h-4 w-4 mr-2" />
                        Edit Details
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={handleRefreshStatus} disabled={isRefreshingStatus}>
                        <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshingStatus ? 'animate-spin' : ''}`} />
                        Refresh Status
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={handleExportFile} disabled={isExporting}>
                        <FileArchive className="h-4 w-4 mr-2" />
                        Export Employee File (ZIP)
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={handleExportCompliancePDF} disabled={isExporting} data-testid="download-compliance-pdf-btn">
                        <FileDown className="h-4 w-4 mr-2" />
                        Download Compliance PDF
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={handlePrintCompliancePDF} data-testid="print-compliance-pdf-btn">
                        <Printer className="h-4 w-4 mr-2" />
                        Print Compliance PDF
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      {employee.status === 'archived' ? (
                        <DropdownMenuItem onClick={handleRestoreEmployee}>
                          <RotateCcw className="h-4 w-4 mr-2" />
                          Restore Employee
                        </DropdownMenuItem>
                      ) : (
                        <DropdownMenuItem 
                          onClick={() => setArchiveDialogOpen(true)}
                          className="text-warning"
                        >
                          <Archive className="h-4 w-4 mr-2" />
                          Archive Employee
                        </DropdownMenuItem>
                      )}
                      {isSuperAdmin() && (
                        <>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem 
                            onClick={() => setDeleteDialogOpen(true)}
                            className="text-error"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete Permanently
                          </DropdownMenuItem>
                        </>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
              <Progress 
                value={canonicalProgressPct}
                className="w-32 h-2" 
              />
            </div>
          </div>

          {/* AUDIT QUICK VIEW - Key compliance items at a glance */}
          {(() => {
            // Extract key compliance data for audit visibility
            const reqs = complianceRequirements?.requirements || [];
            
            // SAFETY ENGINES - USE COMPUTED DATA FROM API (single source of truth)
            const rtwSummary = complianceRequirements?.rtw_summary || {};
            const dbsSummary = complianceRequirements?.dbs_summary || {};
            const pendingReview = canonicalPendingBlockers.length;
            
            // Canonical readiness blocking status — UCE only, no safetyStatus fallback.
            const isBlocking = !canonicalIsWorkReady && !canonicalCanPromote;
            const blockingReasons = canonicalBlockerObjects.map((blocker) => blocker.reason || blocker.message || blocker.label).filter(Boolean);
            
            // DBS info from safety engine
            const dbsExpiry = dbsSummary.review_due_date || dbsSummary.next_dbs_review_due;
            const dbsExpiryDays = dbsSummary.days_remaining;
            const dbsWorkflowStatus = getComplianceFileWorkflowStatus(complianceFile, 'dbs');
            const dbsTone = dbsWorkflowStatus?.tone || (
              dbsSummary.is_blocking || dbsSummary.dbs_status_color === 'red' ? 'red' :
              dbsSummary.status_band === 'urgent' || dbsSummary.status_band === 'due_soon' ? 'amber' :
              dbsSummary.dbs_status_color === 'green' ? 'green' : 'blue'
            );
            const dbsClasses = quickViewToneClasses[dbsTone] || quickViewToneClasses.blue;
            const dbsBlocking = dbsWorkflowStatus ? dbsWorkflowStatus.isBlocking : dbsSummary.is_blocking;
            
            // RTW info from safety engine
            const rtwExpiry = rtwSummary.expiry_date;
            const rtwExpiryDays = rtwSummary.days_remaining;
            const rtwWorkflowStatus = getComplianceFileWorkflowStatus(complianceFile, 'right_to_work');
            const rtwTone = rtwWorkflowStatus?.tone || (
              rtwSummary.rtw_status_color === 'red' || rtwSummary.status_band === 'expired' ? 'red' :
              rtwSummary.rtw_status_color === 'amber' || rtwSummary.status_band === 'urgent' || rtwSummary.status_band === 'due_soon' ? 'amber' :
              rtwSummary.rtw_status_color === 'green' ? 'green' :
              rtwSummary.rtw_status_color === 'gray' || !rtwSummary.is_verified ? 'gray' : 'blue'
            );
            const rtwClasses = quickViewToneClasses[rtwTone] || quickViewToneClasses.blue;
            
            // Category breakdown
            const categoryStats = {};
            reqs.forEach(r => {
              const cat = r.category || 'Other';
              if (!categoryStats[cat]) {
                categoryStats[cat] = { total: 0, complete: 0, verified: 0 };
              }
              categoryStats[cat].total += 1;
              if (r.has_evidence) categoryStats[cat].complete += 1;
              if (r.verified) categoryStats[cat].verified += 1;
            });
            
            // Map categories to display names
            const categoryDisplayNames = {
              '1_Legal_Safety': 'Legal & Safety',
              '2_Core_Training': 'Training',
              '3_Competency_Health': 'Health',
              '4_Recruitment_Record': 'Recruitment',
              '5_Agreements': 'Agreements',
              '6_Admin': 'Admin'
            };
            
            return (
              <div className="mt-6 pt-6 border-t border-[#E4E8EB]">
                {/* Audit Quick View Header */}
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">Audit Quick View</h3>
                  <p className="text-xs text-text-muted">Key compliance items for checker review</p>
                </div>
                
                {/* Quick Status Cards — horizontal scroll so more cards can be added without crowding */}
                <div className="overflow-x-auto -mx-1 px-1 pb-2" data-testid="audit-quick-view">
                  <div className="flex gap-3" style={{ minWidth: 'max-content' }}>
                  {/* DBS Status with Expiry */}
                  <div
                    className={`p-3 rounded-xl border w-52 shrink-0 cursor-pointer hover:shadow-md transition-shadow ${dbsClasses.card}`}
                    data-testid="dbs-status-card"
                    onClick={() => setActiveTab('checklist')}
                    title="Go to Checks & Evidence"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Shield className={`h-4 w-4 ${dbsClasses.icon}`} />
                      <span className="text-xs font-semibold text-text-primary">DBS</span>
                      {dbsBlocking && <span className="text-xs px-1 py-0.5 bg-red-600 text-white rounded">ACTION</span>}
                    </div>
                    <p className={`text-sm font-medium ${dbsClasses.text}`}>
                      {dbsWorkflowStatus?.label || dbsSummary.dbs_status_label || 'Unknown'}
                    </p>
                    {dbsExpiry && (
                      <p className={`text-xs mt-1 ${
                        dbsExpiryDays !== null && dbsExpiryDays < 0 ? 'text-red-600 font-medium' :
                        dbsSummary.status_band === 'urgent' ? 'text-amber-600 font-medium' : 'text-text-muted'
                      }`}>
                        {dbsExpiryDays !== null && dbsExpiryDays < 0 ? 'Overdue: ' : 'Review: '}
                        {formatBackendDate(dbsExpiry)}
                        {dbsExpiryDays !== null && dbsExpiryDays > 0 && dbsExpiryDays <= 60 && (
                          <span className="ml-1">({dbsExpiryDays}d)</span>
                        )}
                      </p>
                    )}
                  </div>
                  
                  {/* RTW Status with Expiry - Dynamic logic based on verification + expiry */}
                  <div
                    className={`p-3 rounded-xl border w-52 shrink-0 cursor-pointer hover:shadow-md transition-shadow ${rtwClasses.card}`}
                    data-testid="rtw-status-card"
                    onClick={() => setActiveTab('checklist')}
                    title="Go to Checks & Evidence"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <FileCheck className={`h-4 w-4 ${rtwClasses.icon}`} />
                      <span className="text-xs font-semibold text-text-primary">Right to Work</span>
                    </div>
                    
                    {rtwWorkflowStatus ? (
                      <>
                        <p className={`text-sm font-semibold ${rtwClasses.text}`}>
                          {rtwWorkflowStatus.label}
                        </p>
                      </>
                    ) : !rtwSummary.is_verified ? (
                      // Not verified = not yet verified
                      <p className="text-sm font-semibold text-gray-700">Not yet verified</p>
                    ) : rtwSummary.status_band === 'expired' || rtwSummary.rtw_status_color === 'red' ? (
                      // Expired
                      <p className="text-sm font-semibold text-red-700">
                        EXPIRED • Not valid to work
                      </p>
                    ) : rtwSummary.is_indefinite || rtwSummary.permission_type === 'permanent' ? (
                      // Verified + No expiry
                      <p className="text-sm font-semibold text-green-700">
                        VERIFIED • No Expiry
                      </p>
                    ) : rtwExpiry ? (
                      // Verified + Has expiry
                      <p className={`text-sm font-semibold ${
                        rtwSummary.status_band === 'urgent' ? 'text-amber-700' : 'text-green-700'
                      }`}>
                        VERIFIED • Expires {formatBackendDate(rtwExpiry)}
                      </p>
                    ) : (
                      // Verified but no expiry info
                      <p className="text-sm font-semibold text-green-700">VERIFIED</p>
                    )}
                    {!rtwWorkflowStatus && (
                      <p className="text-[10px] mt-0.5 text-text-muted">Confirmation pending</p>
                    )}
                    
                    {/* Days countdown for expiring */}
                    {rtwSummary.is_verified && rtwExpiry && rtwExpiryDays !== undefined && rtwExpiryDays !== null && (
                      <p className={`text-xs mt-1 font-medium ${
                        rtwExpiryDays < 0 ? 'text-red-600' :
                        rtwExpiryDays <= 30 ? 'text-red-600' :
                        rtwExpiryDays <= 90 ? 'text-amber-600' : 'text-text-muted'
                      }`}>
                        {rtwExpiryDays < 0 ? `${Math.abs(rtwExpiryDays)} days overdue` :
                         rtwExpiryDays === 0 ? 'Expires today' :
                         `${rtwExpiryDays} days remaining`}
                      </p>
                    )}
                  </div>
                  
                  {/* Alerts Card - Show blocking status prominently */}
                  <div
                    className={`p-3 rounded-xl border w-52 shrink-0 cursor-pointer hover:shadow-md transition-shadow ${
                      isBlocking ? 'border-red-200 bg-red-50' :
                      pendingReview > 0 ? 'border-amber-200 bg-amber-50' : 
                      'border-green-200 bg-green-50'
                    }`}
                    data-testid="alerts-card"
                    onClick={() => setActiveTab(isBlocking || pendingReview > 0 ? 'checklist' : 'training')}
                    title={isBlocking || pendingReview > 0 ? 'Go to Checks & Evidence' : 'Go to Training'}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <AlertTriangle className={`h-4 w-4 ${
                        isBlocking ? 'text-red-600' :
                        pendingReview > 0 ? 'text-amber-600' : 'text-green-600'
                      }`} />
                      <span className="text-xs font-semibold text-text-primary">
                        {isBlocking ? 'Action required' : 'Status'}
                      </span>
                    </div>
                    {isBlocking ? (
                      <div className="space-y-0.5">
                        <p className="text-xs text-red-700 font-semibold">Compliance incomplete</p>
                        {blockingReasons.slice(0, 2).map((reason, idx) => (
                          <p key={idx} className="text-xs text-red-600 line-clamp-1" title={reason}>
                            {reason?.split(' - ')[0] || reason}
                          </p>
                        ))}
                      </div>
                    ) : pendingReview > 0 ? (
                      <div className="space-y-0.5">
                        {pendingReview > 0 && (
                          <p className="text-xs text-amber-700">{pendingReview} awaiting admin review</p>
                        )}
                      </div>
                    ) : canonicalIsWorkReady || canonicalCanPromote ? (
                      <p className="text-sm font-medium text-green-700">All checks passed</p>
                    ) : (
                      <p className="text-sm font-medium text-red-700">Checks incomplete</p>
                    )}
                  </div>
                  
                  {/* Compliance Breakdown Card */}
                  <div
                    className="p-3 rounded-xl border border-slate-200 bg-slate-50 w-52 shrink-0 cursor-pointer hover:shadow-md transition-shadow"
                    data-testid="compliance-breakdown-card"
                    onClick={() => setActiveTab('checklist')}
                    title="Go to Checks & Evidence"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <ClipboardList className="h-4 w-4 text-slate-600" />
                      <span className="text-xs font-semibold text-text-primary">Breakdown</span>
                    </div>
                    <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                      {Object.entries(categoryStats)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .slice(0, 4) // Show top 4 categories
                        .map(([cat, stats]) => {
                          const displayName = categoryDisplayNames[cat] || cat.replace(/^\d+_/, '').replace(/_/g, ' ');
                          const isComplete = stats.complete === stats.total;
                          return (
                            <div key={cat} className="flex items-center justify-between">
                              <span className="text-xs text-text-muted truncate">{displayName}</span>
                              <span className={`text-xs font-medium ${isComplete ? 'text-green-600' : 'text-amber-600'}`}>
                                {stats.complete}/{stats.total}
                              </span>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                </div>{/* end flex row */}
              </div>{/* end overflow-x-auto */}
            </div>
            );
          })()}

          {/* Status Strip - Replaces contact row */}
          <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t border-[#E4E8EB]" data-testid="status-strip">
            {/* Business-facing identifier — label adapts to person stage */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-lg">
              <User className="h-4 w-4 text-slate-500" />
              <span className="text-sm text-slate-500">{employee.person_stage === 'applicant' ? 'Applicant Reference:' : 'Employee ID:'}</span>
              <span className="text-sm font-semibold text-slate-700">{employee.employee_code || employee.applicant_reference || 'Not assigned'}</span>
            </div>
            
            {/* Missing Items */}
            {canonicalCriticalBlockers.length > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-red-100 rounded-lg">
                <XCircle className="h-4 w-4 text-red-600" />
                <span className="text-sm font-medium text-red-700">{canonicalCriticalBlockers.length} Action required</span>
              </div>
            )}
            
            {/* Pending Review — per-row has_evidence/verified are backend-set fields */}
            {canonicalPendingBlockers.length > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-100 rounded-lg">
                <Clock className="h-4 w-4 text-amber-600" />
                <span className="text-sm font-medium text-amber-700">{canonicalPendingBlockers.length} Awaiting admin review</span>
              </div>
            )}
            
            {/* Key Expiry - Show most critical */}
            {(() => {
              const dbsSummary = complianceRequirements?.dbs_summary || {};
              const rtwSummary = complianceRequirements?.rtw_summary || {};
              
              // Check RTW expiry first (more critical)
              if (rtwSummary.expiry_date) {
                const days = rtwSummary.days_until_expiry;
                if (days !== undefined && days <= 30) {
                  return (
                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
                      days <= 0 ? 'bg-red-100' : 'bg-amber-100'
                    }`}>
                      <Calendar className={`h-4 w-4 ${days <= 0 ? 'text-red-600' : 'text-amber-600'}`} />
                      <span className={`text-sm font-medium ${days <= 0 ? 'text-red-700' : 'text-amber-700'}`}>
                        RTW {days <= 0 ? 'Expired' : `Expires ${days}d`}
                      </span>
                    </div>
                  );
                }
              }
              
              // Check DBS expiry — use only backend-computed days_until_review (safety engine).
              // No local date arithmetic: if backend doesn't supply days_until_review, skip rendering.
              if (dbsSummary.next_dbs_review_due && dbsSummary.days_until_review != null) {
                const days = dbsSummary.days_until_review;
                if (days <= 30) {
                  return (
                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
                      days <= 0 ? 'bg-red-100' : 'bg-amber-100'
                    }`}>
                      <Calendar className={`h-4 w-4 ${days <= 0 ? 'text-red-600' : 'text-amber-600'}`} />
                      <span className={`text-sm font-medium ${days <= 0 ? 'text-red-700' : 'text-amber-700'}`}>
                        DBS {days <= 0 ? 'Overdue' : `Review ${days}d`}
                      </span>
                    </div>
                  );
                }
              }
              
              return null;
            })()}
            
          </div>

          {/* Note: Global Upload Document button removed. */}
          {/* All upload actions now live INSIDE each compliance requirement card. */}
          {/* Workflow: See issue → Scroll to section → Upload/Request/Verify there. */}

          {!isAuditor() && (
            <div className="flex flex-wrap gap-3 mt-6">
              {/* Generate Blank Forms Dialog */}
              <Dialog open={generateFormsOpen} onOpenChange={setGenerateFormsOpen}>
                <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col bg-white">
                  <DialogHeader>
                    <DialogTitle className="font-heading">Generate Compliance Forms</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 mt-4 overflow-y-auto flex-1 pr-2">
                    <p className="text-sm text-text-muted">
                      Select templates to generate for <strong>{employee?.first_name} {employee?.last_name}</strong>. 
                      Employee details will be auto-filled.
                    </p>
                    
                    {templates.length === 0 ? (
                      <div className="text-center py-8 text-text-muted">
                        <ClipboardList className="h-10 w-10 mx-auto mb-2 opacity-50" />
                        <p>No templates available. Load templates first.</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {Object.entries(groupedTemplates).map(([category, categoryTemplates]) => (
                          <div key={category} className="space-y-2">
                            <h4 className="font-medium text-text-primary text-sm">{category}</h4>
                            <div className="space-y-2">
                              {categoryTemplates.map((template) => {
                                const existingForm = generatedForms.find(
                                  f => f.template_id === template.id && !['archived', 'signed_off'].includes(f.status)
                                );
                                const isSelected = selectedTemplates.includes(template.id);
                                
                                return (
                                  <div 
                                    key={template.id}
                                    className={`flex items-start gap-3 p-3 rounded-xl border transition-colors ${
                                      existingForm 
                                        ? 'bg-gray-50 border-gray-200 opacity-60' 
                                        : isSelected 
                                          ? 'bg-primary/5 border-primary' 
                                          : 'bg-[#F8FAFA] border-[#E4E8EB] hover:border-primary/30'
                                    }`}
                                  >
                                    <Checkbox
                                      id={template.id}
                                      checked={isSelected}
                                      disabled={!!existingForm}
                                      onCheckedChange={() => toggleTemplateSelection(template.id)}
                                    />
                                    <div className="flex-1 min-w-0">
                                      <label 
                                        htmlFor={template.id}
                                        className={`text-sm font-medium cursor-pointer ${existingForm ? 'text-text-muted' : 'text-text-primary'}`}
                                      >
                                        {template.name}
                                      </label>
                                      {template.description && (
                                        <p className="text-xs text-text-muted mt-0.5 line-clamp-1">{template.description}</p>
                                      )}
                                      {existingForm && (
                                        <div className="flex items-center gap-2 mt-1">
                                          <span className="text-xs text-warning">Form exists ({existingForm.status})</span>
                                          <Button
                                            size="sm"
                                            variant="ghost"
                                            className="h-6 px-2 text-xs"
                                            onClick={() => navigate(`/portal/forms/${existingForm.id}`)}
                                          >
                                            <Eye className="h-3 w-3 mr-1" />
                                            View
                                          </Button>
                                        </div>
                                      )}
                                    </div>
                                    <div className="flex gap-1">
                                      {template.requires_employee_signature && (
                                        <span className="text-xs bg-accent text-primary px-2 py-0.5 rounded">Emp Sign</span>
                                      )}
                                      {template.requires_admin_signature && (
                                        <span className="text-xs bg-secondary/10 text-secondary px-2 py-0.5 rounded">Admin Sign</span>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex justify-between items-center gap-3 pt-4 border-t border-[#E4E8EB] mt-4">
                    <span className="text-sm text-text-muted">
                      {selectedTemplates.length} template{selectedTemplates.length !== 1 ? 's' : ''} selected
                    </span>
                    <div className="flex gap-3">
                      <Button type="button" variant="outline" onClick={() => setGenerateFormsOpen(false)} className="rounded-xl">
                        Cancel
                      </Button>
                      <Button 
                        onClick={handleGenerateForms}
                        disabled={isGenerating || selectedTemplates.length === 0}
                        className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                        data-testid="generate-forms-submit"
                      >
                        {isGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : `Generate ${selectedTemplates.length} Forms`}
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>

              {/* Import Existing Application Dialog */}
              <Dialog open={importAppOpen} onOpenChange={setImportAppOpen}>
                <DialogContent className="max-w-lg bg-white">
                  <DialogHeader>
                    <DialogTitle className="font-heading">Create from Existing Application</DialogTitle>
                    <DialogDescription>
                      Upload a completed application form and optionally a CV. The form will be stored as uploaded evidence and linked to the employee's compliance checklist.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Application Form <span className="text-red-500">*</span>
                      </Label>
                      <FileUploaderInline
                        onFileSelect={(file) => setImportAppFile(file)}
                        selectedFile={importAppFile}
                        onClear={() => setImportAppFile(null)}
                        acceptedTypes={['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']}
                        placeholder="Drop application form here or click to browse"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        CV / Resume <span className="text-text-muted">(optional)</span>
                      </Label>
                      <FileUploaderInline
                        onFileSelect={(file) => {
                          if (file) {
                            const isPdfFile = file.type === 'application/pdf' || file.name?.toLowerCase().endsWith('.pdf');
                            if (!isPdfFile) {
                              toast.error('Only PDF CV files are supported. Please upload the CV as a PDF.');
                              return;
                            }
                          }
                          setImportCvFile(file);
                        }}
                        selectedFile={importCvFile}
                        onClear={() => setImportCvFile(null)}
                        acceptedTypes={['application/pdf']}
                        placeholder="Drop CV here or click to browse"
                      />
                    </div>

                    <div className="bg-[#F8FAFA] rounded-xl p-4 space-y-2">
                      <h4 className="text-sm font-medium text-text-primary">What happens next:</h4>
                      <ul className="text-xs text-text-muted space-y-1">
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Application Form marked as "Completed (Imported)"
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Document stored in employee's A_Application folder
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Checklist item evidence uploaded automatically
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Form fields locked (read-only) unless manually edited
                        </li>
                      </ul>
                    </div>
                  </div>

                  <div className="flex justify-end gap-3 pt-4 border-t border-[#E4E8EB] mt-4">
                    <Button 
                      variant="outline" 
                      onClick={() => { setImportAppOpen(false); setImportAppFile(null); setImportCvFile(null); }} 
                      className="rounded-xl"
                    >
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleImportApplication}
                      disabled={isImporting || !importAppFile}
                      className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                      data-testid="import-application-submit"
                    >
                      {isImporting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Import Application'}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>

              {/* Import Other Document Dialog (Reference, Health Screening, Contract) */}
              <Dialog open={importDocOpen} onOpenChange={setImportDocOpen}>
                <DialogContent className="max-w-lg bg-white">
                  <DialogHeader>
                    <DialogTitle className="font-heading">Import Existing Document</DialogTitle>
                    <DialogDescription>
                      Upload an existing completed document (Reference letter, Health form, Contract, etc.) to add evidence to the corresponding compliance requirement.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Document Type <span className="text-red-500">*</span>
                      </Label>
                      <Select value={importDocType} onValueChange={setImportDocType}>
                        <SelectTrigger className="rounded-xl" data-testid="import-doc-type-select">
                          <SelectValue placeholder="Select document type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="recruitment_checklist">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-primary" />
                              Recruitment Compliance Checklist
                            </div>
                          </SelectItem>
                          <SelectItem value="personal_info">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-info" />
                              Personal Information Form
                            </div>
                          </SelectItem>
                          <SelectItem value="interview_record">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-primary" />
                              Interview Record Form
                            </div>
                          </SelectItem>
                          <SelectItem value="equal_opportunities">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-success" />
                              Equal Opportunities Monitoring
                            </div>
                          </SelectItem>
                          <SelectItem value="reference_1">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-warning" />
                              Reference 1
                            </div>
                          </SelectItem>
                          <SelectItem value="reference_2">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-warning" />
                              Reference 2
                            </div>
                          </SelectItem>
                          <SelectItem value="health_screening">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-info" />
                              Health Screening Questionnaire
                            </div>
                          </SelectItem>
                          <SelectItem value="contract">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-success" />
                              Contract / Offer Letter
                            </div>
                          </SelectItem>
                          <SelectItem value="induction">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-primary" />
                              Induction & Competency
                            </div>
                          </SelectItem>
                          <SelectItem value="handbook">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-gray-400" />
                              Employee Handbook Acknowledgement
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Document File <span className="text-red-500">*</span>
                      </Label>
                      <FileUploaderInline
                        onFileSelect={(file) => setImportDocFile(file)}
                        selectedFile={importDocFile}
                        onClear={() => setImportDocFile(null)}
                        acceptedTypes={['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/jpeg', 'image/jpg', 'image/png']}
                        placeholder="Drop document here or click to browse"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Notes <span className="text-text-muted">(optional)</span>
                      </Label>
                      <Textarea 
                        value={importDocNotes}
                        onChange={(e) => setImportDocNotes(e.target.value)}
                        placeholder="e.g., Reference from John Smith, previous employer at ABC Company"
                        className="rounded-xl resize-none"
                        rows={2}
                      />
                    </div>

                    <div className="bg-[#F8FAFA] rounded-xl p-4 space-y-2">
                      <h4 className="text-sm font-medium text-text-primary">What happens:</h4>
                      <ul className="text-xs text-text-muted space-y-1">
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Form marked as "Completed (Imported)"
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Document stored in employee's compliance folder
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Checklist requirement evidence uploaded
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Ready for verification
                        </li>
                      </ul>
                    </div>
                  </div>

                  <div className="flex justify-end gap-3 pt-4 border-t border-[#E4E8EB] mt-4">
                    <Button 
                      variant="outline" 
                      onClick={() => { setImportDocOpen(false); setImportDocType(''); setImportDocFile(null); setImportDocNotes(''); }} 
                      className="rounded-xl"
                    >
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleImportDocument}
                      disabled={isImporting || !importDocFile || !importDocType}
                      className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                      data-testid="import-document-submit"
                    >
                      {isImporting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Import Document'}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          )}
        </CardContent>
      </Card>

      {/* CONSOLIDATED STATUS PANEL - Single source of truth */}
      <div className={`mb-6 ${lifecycleStage === 'recruitment' ? 'opacity-70' : ''}`}>
        <ConsolidatedStatusPanel
          employeeId={employee?.id}
          employeeName={`${employee?.first_name} ${employee?.last_name}`}
          role={employee?.role}
          personStage={employee?.person_stage}
          recruitmentApproved={employee?.recruitment_approved}
          onNavigateToTab={(tab) => {
            setActiveTab(tab === 'compliance' ? 'checklist' : tab);
          }}
          onNavigateToItem={(tab, sectionId) => {
            const normalizedTab = tab === 'compliance' ? 'checklist' : tab;
            navigateToTabSection(normalizedTab, sectionId || null);
          }}
          onRefresh={() => {
            fetchEmployee();
            fetchComplianceFile();
          }}
          onVerifyWithEvidence={(gateKey, gateData) => {
            // Open verification modal with the relevant document
            const docData = {
              document_type: gateKey,
              requirement_id: gateKey,
              id: gateData?.document_id || gateData?.id
            };
            handleOpenVerificationModal(docData, gateKey);
          }}
          onViewDocument={(gateKey, gateData) => {
            // Open document viewer modal
            const docData = {
              document_type: gateKey,
              requirement_id: gateKey,
              file_url: gateData?.file_url,
              id: gateData?.document_id || gateData?.id
            };
            handleOpenViewerModal(docData);
          }}
        />
      </div>

      {/* Pending Verification Banner - Shows items needing admin attention */}
      {isAuditor() && (
        <PendingVerificationBanner
          employeeId={employeeId}
          employeeName={`${employee?.first_name} ${employee?.last_name}`}
          onNavigateToItem={(tab) => {
            setActiveTab(tab === 'compliance' ? 'work_readiness' : tab);
          }}
        />
      )}

      {/* Tabs - 7 Section Structure */}
      <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-6">
        <TabsList className="bg-white border border-[#E4E8EB] p-1 rounded-xl flex-wrap">
          <TabsTrigger value="employment" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <Briefcase className="h-4 w-4 mr-2" />
            Employment Review
          </TabsTrigger>
          <TabsTrigger value="forms" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <FileText className="h-4 w-4 mr-2" />
            Forms & Interview
          </TabsTrigger>
          <TabsTrigger value="references" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <UserCheck className="h-4 w-4 mr-2" />
            References
          </TabsTrigger>
          <TabsTrigger value="checklist" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <CheckCircle className="h-4 w-4 mr-2" />
            Checks & Evidence
          </TabsTrigger>
          <TabsTrigger value="training" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <GraduationCap className="h-4 w-4 mr-2" />
            Training
          </TabsTrigger>
          <TabsTrigger value="work_readiness" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <User className="h-4 w-4 mr-2" />
            Profile Summary
          </TabsTrigger>
          <TabsTrigger value="competencies" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <ClipboardCheck className="h-4 w-4 mr-2" />
            Competencies
          </TabsTrigger>
          {lifecycleStage === 'active' && (
            <TabsTrigger value="spot_checks" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
              <Eye className="h-4 w-4 mr-2" />
              Spot Checks
            </TabsTrigger>
          )}
          <TabsTrigger value="audit" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <History className="h-4 w-4 mr-2" />
            Audit
          </TabsTrigger>
        </TabsList>

        {/* ========== TAB 1: PROFILE SUMMARY ========== */}
        {/* Stable profile / core-record tab. Readiness logic lives above the tabs only. */}
        <TabsContent value="work_readiness">
          <div className="space-y-6">

            {/* ── Personal Details ── */}
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="font-heading text-lg">Personal Details</CardTitle>
                {!isAuditor() && (
                  <Button variant="outline" size="sm" onClick={() => setEditPersonalOpen(true)} data-testid="edit-personal-btn">
                    <Edit className="h-4 w-4 mr-1" />Edit
                  </Button>
                )}
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div>
                    <p className="text-xs text-text-muted">Full Name</p>
                    <p className="font-medium text-text-primary">{employee?.first_name} {employee?.last_name}</p>
                  </div>
                  <div>
                    <p className="text-xs text-text-muted">{employee?.person_stage === 'applicant' ? 'Applicant Reference' : 'Employee ID'}</p>
                    <p className="font-medium text-text-primary">{employee?.employee_code || employee?.applicant_reference || 'Not assigned'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-text-muted">Role</p>
                    <p className="font-medium text-text-primary">{employee?.role || '—'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-text-muted">Status</p>
                    <Badge className={
                      employee?.status === 'active_employee' ? 'bg-green-100 text-green-700' :
                      employee?.status === 'onboarding' ? 'bg-amber-100 text-amber-700' :
                      'bg-gray-100 text-gray-700'
                    }>
                      {employee?.status === 'active_employee' ? 'Active employee'
                        : employee?.status === 'onboarding' ? 'Onboarding'
                        : employee?.status?.replace(/_/g, ' ') || 'Unknown'}
                    </Badge>
                  </div>
                  {employee?.date_of_birth && (
                    <div>
                      <p className="text-xs text-text-muted">Date of Birth</p>
                      <p className="font-medium text-text-primary">{formatBackendDate(employee.date_of_birth)}</p>
                    </div>
                  )}
                  {employee?.national_insurance_number && (
                    <div>
                      <p className="text-xs text-text-muted">NI Number</p>
                      <p className="font-medium text-text-primary">{employee.national_insurance_number}</p>
                    </div>
                  )}
                  {employee?.nationality && (
                    <div>
                      <p className="text-xs text-text-muted">Nationality</p>
                      <p className="font-medium text-text-primary">{employee.nationality}</p>
                    </div>
                  )}
                  {employee?.start_date && (
                    <div>
                      <p className="text-xs text-text-muted">Start Date</p>
                      <p className="font-medium text-text-primary">{formatBackendDate(employee.start_date)}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* ── Contact Details ── */}
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="font-heading text-lg">Contact Details</CardTitle>
                {!isAuditor() && (
                  <Button variant="outline" size="sm" onClick={() => setEditPersonalOpen(true)} data-testid="edit-contact-btn">
                    <Edit className="h-4 w-4 mr-1" />Edit
                  </Button>
                )}
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  <div>
                    <p className="text-xs text-text-muted">Email</p>
                    <p className="font-medium text-text-primary break-all">{employee?.email || '—'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-text-muted">Phone</p>
                    <p className="font-medium text-text-primary">{employee?.phone || employee?.phone_number || '—'}</p>
                  </div>
                  {employee?.mobile && (
                    <div>
                      <p className="text-xs text-text-muted">Mobile</p>
                      <p className="font-medium text-text-primary">{employee.mobile}</p>
                    </div>
                  )}
                </div>
                {/* Address */}
                {(employee?.address_line_1 || employee?.city || employee?.postcode) && (
                  <div className="mt-4 pt-4 border-t border-[#E4E8EB]">
                    <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Address</p>
                    <address className="not-italic text-sm text-text-primary leading-relaxed">
                      {employee?.address_line_1 && <span className="block">{employee.address_line_1}</span>}
                      {employee?.address_line_2 && <span className="block">{employee.address_line_2}</span>}
                      {(employee?.city || employee?.county) && (
                        <span className="block">{[employee?.city, employee?.county].filter(Boolean).join(', ')}</span>
                      )}
                      {employee?.postcode && <span className="block">{employee.postcode}</span>}
                      {employee?.country && employee?.country !== 'United Kingdom' && (
                        <span className="block">{employee.country}</span>
                      )}
                    </address>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* ── Emergency Contact / Next of Kin ── */}
            {(employee?.emergency_contact_name || employee?.next_of_kin_name) && (
              <Card className="border-[#E4E8EB] shadow-sm">
                <CardHeader>
                  <CardTitle className="font-heading text-lg">Emergency Contact</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    <div>
                      <p className="text-xs text-text-muted">Name</p>
                      <p className="font-medium text-text-primary">
                        {employee?.emergency_contact_name || employee?.next_of_kin_name || '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-text-muted">Relationship</p>
                      <p className="font-medium text-text-primary">
                        {employee?.emergency_contact_relationship || employee?.next_of_kin_relationship || '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-text-muted">Phone</p>
                      <p className="font-medium text-text-primary">
                        {employee?.emergency_contact_phone || employee?.next_of_kin_phone || '—'}
                      </p>
                    </div>
                    {employee?.next_of_kin_address && (
                      <div className="col-span-2 sm:col-span-3">
                        <p className="text-xs text-text-muted">Address</p>
                        <p className="font-medium text-text-primary">{employee.next_of_kin_address}</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* ── Employment History ── */}
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="font-heading text-lg">Employment History</CardTitle>
                {!isAuditor() && (
                  <Button variant="outline" size="sm" onClick={() => setEditEmploymentOpen(true)} data-testid="edit-employment-btn">
                    <Edit className="h-4 w-4 mr-1" />Edit
                  </Button>
                )}
              </CardHeader>
              <CardContent>
                {employee?.employment_history && employee.employment_history.length > 0 ? (
                  <div className="space-y-2">
                    {employee.employment_history.slice(0, 5).map((job, idx) => (
                      <div key={idx} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                        <div>
                          <p className="font-medium text-sm">{job.employer || job.company || job.employer_name}</p>
                          <p className="text-xs text-gray-500">{job.job_title || job.position}</p>
                        </div>
                        <p className="text-xs text-gray-400 shrink-0 ml-2">
                          {formatBackendDate(job.start_date, { format: 'short' })} – {job.end_date ? formatBackendDate(job.end_date, { format: 'short' }) : 'Present'}
                        </p>
                      </div>
                    ))}
                    {employee.employment_history.length > 5 && (
                      <p className="text-xs text-gray-500 text-center">+{employee.employment_history.length - 5} more — see Employment Review tab</p>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No employment history recorded. See the Employment Review tab to add history.</p>
                )}
              </CardContent>
            </Card>

            {/* ── References ── */}
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="font-heading text-lg">References</CardTitle>
                {!isAuditor() && (
                  <Button variant="outline" size="sm" onClick={() => setEditReferenceOpen(true)} data-testid="edit-references-btn">
                    <Edit className="h-4 w-4 mr-1" />Edit
                  </Button>
                )}
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[1, 2].map((n) => {
                    const ref = employee?.[`reference_${n}`] || employee?.references?.[n - 1];
                    const status = employee?.[`reference_${n}_status`]
                      || (employee?.references?.[n - 1]?.verified ? 'Verified' : 'In progress');
                    const isVerified = status === 'verified' || status === 'Verified';
                    return (
                      <div key={n} className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500 mb-1">Reference {n}</p>
                        {ref ? (
                          <>
                            <p className="font-medium text-sm">{ref.name || 'Name not recorded'}</p>
                            {ref.email && <p className="text-xs text-gray-500">{ref.email}</p>}
                            {ref.company && <p className="text-xs text-gray-500">{ref.company}</p>}
                            <Badge className={isVerified ? 'bg-green-100 text-green-700 mt-1' : 'bg-amber-100 text-amber-700 mt-1'}>
                              {isVerified ? 'Verified' : 'Awaiting verification'}
                            </Badge>
                          </>
                        ) : (
                          <p className="text-sm text-gray-500">Not yet provided</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

          </div>
        </TabsContent>

        {/* ========== TAB 3: FORMS ========== */}
        {/* Interview record + worker onboarding forms (health, personal, HMRC, declarations) */}
        <TabsContent value="forms">
          {/* ── Top-level Forms & Interview Summary ── */}
          {(() => {
            // Derive form-level counts — reused in summary banner and form cards
            const FORM_GROUPS = [
              {
                label: 'Pre-Employment Checks',
                sensitive: false,
                forms: [
                  { key: 'staff_health_questionnaire', name: 'Staff Health Questionnaire', description: 'Medical history and health declarations', prefill: true, sensitive: true },
                  { key: 'staff_personal_info', name: 'Staff Personal Information', description: 'Contact details, NI number, bank details', prefill: true },
                  { key: 'hmrc_starter_checklist', name: 'HMRC Starter Checklist', description: 'Tax code and employment status', sensitive: true },
                  { key: 'equal_opportunities', name: 'Equal Opportunities Monitoring', description: 'Equality & diversity monitoring (optional, non-blocking)', sensitive: true, optional: true },
                  { key: 'emergency_contacts', name: 'Emergency Contacts', description: 'Next of kin and emergency contact details', prefill: true },
                ]
              },
              {
                label: 'Declarations',
                sensitive: true,
                forms: [
                  { key: 'conflict_of_interest', name: 'Conflict of Interest Declaration', description: 'Secondary employment, relationships or financial interests (NHS standard)', sensitive: true },
                  ...(/manager|director/i.test(employee?.role || '') ? [{ key: 'fit_proper_persons', name: 'Fit and Proper Persons Declaration', description: 'CQC Regulation 5 — managers and directors only', sensitive: true }] : []),
                ]
              },
            ];
            const allFormDefinitions = FORM_GROUPS.flatMap((g) => g.forms);

            // Status derivation for each form
            const deriveFormStatus = (form) => {
              const submission = formSubmissions?.find(fs =>
                fs.form_type === form.key || fs.requirement_id === form.key
              );
              if (!submission) return { status: 'missing', submission: null };
              const raw = submission?.status || 'not_started';
              if (['returned_for_correction', 'reopened_for_worker_correction', 'amendment_requested'].includes(raw)) return { status: 'returned_for_correction', submission };
              if (raw === 'verified' || raw === 'signed_off' || submission?.verified === true) return { status: 'signed_off', submission };
              if (raw === 'rejected') return { status: 'rejected', submission };
              if (raw === 'approved' || raw === 'reviewed') return { status: 'reviewed', submission };
              if (raw === 'submitted') return { status: 'submitted', submission };
              if (raw === 'draft' || raw === 'in_progress') return { status: 'in_progress', submission };
              return { status: 'missing', submission };
            };

            const formStatuses = allFormDefinitions.map((f) => ({ ...f, ...deriveFormStatus(f) }));

            // Cannot-assess guard
            const cannotAssessForms = Boolean(formSubmissionsError);

            // Counts
            const missingCount = formStatuses.filter((f) => f.status === 'missing').length;
            const inProgressCount = formStatuses.filter((f) => f.status === 'in_progress').length;
            const submittedCount = formStatuses.filter((f) => f.status === 'submitted').length;
            const reviewedCount = formStatuses.filter((f) => f.status === 'reviewed').length;
            const signedOffCount = formStatuses.filter((f) => f.status === 'signed_off').length;
            const rejectedCount = formStatuses.filter((f) => f.status === 'rejected').length;
            const returnedForCorrectionCount = formStatuses.filter((f) => f.status === 'returned_for_correction').length;
            const totalForms = allFormDefinitions.length;
            const allSignedOff = signedOffCount === totalForms && !cannotAssessForms;

            // Interview record status (from formSubmissions — interview submission)
            const interviewSubmission = formSubmissions?.find(fs =>
              fs.form_type === 'interview_record' || fs.requirement_id === 'interview_record'
            );
            const interviewFormStatus = interviewSubmission?.status || null;
            const interviewExists = Boolean(interviewSubmission);
            const interviewDecision = interviewSubmission?.form_data?.decision || interviewSubmission?.data?.decision || interviewSubmission?.form_data?.overall_decision || null;
            const interviewScore = interviewSubmission?.form_data?.total_score || interviewSubmission?.data?.total_score || null;
            const interviewPassed = interviewScore !== null ? interviewScore >= 11 : null;
            const interviewAdminStatus = interviewDecision
              ? (['Reject', 'Not Suitable'].includes(interviewDecision) ? 'reviewed_rejected' : 'reviewed_approved')
              : interviewPassed !== null
                ? (interviewPassed ? 'reviewed_passed' : 'reviewed_failed')
                : interviewFormStatus;

            // Banner colour
            const summaryBorderClass = cannotAssessForms
              ? 'border-red-200 bg-red-50'
              : allSignedOff
                ? 'border-green-200 bg-green-50'
                : (rejectedCount > 0 || returnedForCorrectionCount > 0)
                  ? 'border-red-200 bg-red-50'
                  : 'border-amber-200 bg-amber-50';
            const summaryTextClass = cannotAssessForms
              ? 'text-red-800'
              : allSignedOff
                ? 'text-green-800'
                : (rejectedCount > 0 || returnedForCorrectionCount > 0)
                  ? 'text-red-800'
                  : 'text-amber-800';

            // Status display config
            const STATUS_DISPLAY = {
              missing:     { label: 'Missing',                         color: 'bg-gray-100 text-gray-600',   icon: AlertCircle, iconColor: 'text-gray-400',   cardBorder: 'bg-gray-50 border-gray-200' },
              in_progress: { label: 'Worker in progress',              color: 'bg-amber-100 text-amber-700', icon: Clock,       iconColor: 'text-amber-500',  cardBorder: 'bg-amber-50 border-amber-200' },
              submitted:   { label: 'Submitted, not reviewed',         color: 'bg-blue-100 text-blue-700',   icon: FileText,    iconColor: 'text-blue-500',   cardBorder: 'bg-blue-50 border-blue-200' },
              reviewed:    { label: 'Reviewed',                        color: 'bg-indigo-100 text-indigo-700',icon: Eye,         iconColor: 'text-indigo-500', cardBorder: 'bg-indigo-50 border-indigo-200' },
              signed_off:  { label: 'Signed off',                      color: 'bg-green-100 text-green-700', icon: CheckCircle,  iconColor: 'text-green-600',  cardBorder: 'bg-green-50 border-green-200' },
              rejected:    { label: 'Rejected / action required',      color: 'bg-red-100 text-red-700',     icon: XCircle,     iconColor: 'text-red-500',    cardBorder: 'bg-red-50 border-red-200' },
              returned_for_correction: { label: 'Returned for correction', color: 'bg-red-100 text-red-700', icon: RotateCcw, iconColor: 'text-red-500', cardBorder: 'bg-red-50 border-red-200' },
            };

            const fmtDate = (d) => d ? new Date(d).toLocaleDateString('en-GB', {
              day: 'numeric', month: 'short', year: 'numeric'
            }) : null;

            return (
              <div className="space-y-6">
                {/* ── Summary banner ── */}
                <div className={`rounded-xl border p-4 ${summaryBorderClass}`}>
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {cannotAssessForms
                        ? <AlertTriangle className="h-5 w-5 text-red-600" />
                        : allSignedOff
                          ? <CheckCircle className="h-5 w-5 text-green-600" />
                          : <AlertTriangle className="h-5 w-5 text-amber-600" />}
                    </div>
                    <div className="flex-1">
                      <p className={`font-medium ${summaryTextClass}`}>
                        {cannotAssessForms
                          ? 'Cannot assess forms — submission data unavailable'
                          : allSignedOff
                            ? `All ${totalForms} forms signed off`
                            : `Forms Signed Off: ${signedOffCount} / ${totalForms}`}
                      </p>
                      {!cannotAssessForms && !allSignedOff && (
                        <div className="mt-2 text-sm space-y-0.5">
                          {missingCount > 0 && <p>Missing: {missingCount}</p>}
                          {inProgressCount > 0 && <p>Worker in progress: {inProgressCount}</p>}
                          {submittedCount > 0 && <p>Submitted, not reviewed: {submittedCount}</p>}
                          {reviewedCount > 0 && <p>Reviewed (not yet signed off): {reviewedCount}</p>}
                          {returnedForCorrectionCount > 0 && <p className="text-red-700 font-medium">Returned for correction: {returnedForCorrectionCount}</p>}
                          {rejectedCount > 0 && <p className="text-red-700 font-medium">Rejected / action required: {rejectedCount}</p>}
                        </div>
                      )}
                      {cannotAssessForms && (
                        <div className="mt-2">
                          <Button size="sm" variant="outline" onClick={fetchFormSubmissions}
                            className="text-red-600 border-red-200 hover:bg-red-50">
                            <RefreshCw className="h-3 w-3 mr-1" /> Retry
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* ── Interview Record (distinct recruitment decision) ── */}
                <Card className={`shadow-sm ${
                  cannotAssessForms ? 'border-red-200'
                  : !interviewExists ? 'border-amber-200'
                  : 'border-[#E4E8EB]'
                }`} data-testid="section-forms-interview">
                  <CardHeader>
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <CardTitle className="font-heading text-lg flex items-center gap-2">
                          <ClipboardList className="h-5 w-5 text-primary" />
                          Interview Assessment Record
                        </CardTitle>
                        <p className="text-xs text-text-muted mt-1">
                          Scored recruitment decision record. Must be completed and reviewed before progressing onboarding.
                        </p>
                        <Badge variant="outline" className="mt-1 text-xs bg-slate-50 text-slate-600 border-slate-200">
                          Sensitive recruitment record
                        </Badge>
                      </div>
                      {cannotAssessForms ? (
                        <Badge className="bg-red-100 text-red-700">Cannot assess</Badge>
                      ) : !interviewExists ? (
                        <Badge className="bg-gray-100 text-gray-600">Missing</Badge>
                      ) : interviewDecision ? (
                        <div className="flex flex-col items-end gap-1">
                          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                            {interviewAdminStatus === 'reviewed_rejected' ? 'Reviewed - rejected' : 'Reviewed - approved'}
                          </Badge>
                          <Badge className={
                            ['Approve', 'Hire', 'Strong Hire'].includes(interviewDecision)
                              ? 'bg-green-100 text-green-700'
                              : ['Reject', 'Not Suitable'].includes(interviewDecision)
                                ? 'bg-red-100 text-red-700'
                                : 'bg-amber-100 text-amber-700'
                          }>
                            Outcome: {interviewDecision}
                          </Badge>
                          {interviewPassed !== null && (
                            <span className={`text-xs font-medium ${interviewPassed ? 'text-green-600' : 'text-red-600'}`}>
                              Score: {interviewScore}/24 — {interviewPassed ? 'Passed' : 'Failed'}
                            </span>
                          )}
                        </div>
                      ) : interviewPassed !== null ? (
                        <Badge className={interviewPassed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                          {interviewPassed ? 'Completed — Passed' : 'Completed — Failed'}
                        </Badge>
                      ) : (
                        <Badge className="bg-blue-100 text-blue-700">Record exists — no outcome recorded</Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent>
                    {cannotAssessForms ? (
                      <div className="text-center py-6 text-red-700">
                        <AlertTriangle className="h-6 w-6 mx-auto mb-2 text-red-500" />
                        <p className="text-sm font-medium">Cannot assess interview record</p>
                        <p className="text-xs text-red-600 mt-1">Form submissions unavailable. Review and sign-off actions are disabled.</p>
                      </div>
                    ) : (
                      <InterviewFormPanel
                        employeeId={employeeId}
                        employeeName={`${employee?.first_name} ${employee?.last_name}`}
                        employeeRole={employee?.role || 'Healthcare Assistant'}
                        onComplete={() => {
                          fetchCompliance();
                          fetchFormSubmissions();
                        }}
                      />
                    )}
                  </CardContent>
                </Card>

                {/* ── Worker Onboarding Forms ── */}
                <Card className="border-[#E4E8EB] shadow-sm" data-testid="section-forms-core">
                  <CardHeader>
                    <CardTitle className="font-heading text-lg">Worker Onboarding Forms</CardTitle>
                    <p className="text-xs text-text-muted">
                      Forms submitted by the worker for onboarding and admin review. Sensitive records are marked.
                    </p>
                  </CardHeader>
                  <CardContent>
                    {cannotAssessForms ? (
                      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-center text-red-700">
                        <AlertTriangle className="h-6 w-6 mx-auto mb-2 text-red-500" />
                        <p className="font-medium">Cannot assess forms</p>
                        <p className="text-sm text-red-600 mt-1">
                          Submission data unavailable. All review and sign-off actions are disabled until data loads.
                        </p>
                        <Button size="sm" variant="outline" onClick={fetchFormSubmissions}
                          className="mt-3 text-red-600 border-red-200 hover:bg-red-50">
                          <RefreshCw className="h-3 w-3 mr-1" /> Retry
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-5">
                        {FORM_GROUPS.map(group => (
                          <div key={group.label}>
                            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2 px-1">
                              {group.label}
                              {group.sensitive && (
                                <span className="ml-2 text-slate-400 normal-case font-normal">— sensitive recruitment records</span>
                              )}
                            </p>
                            <div className="space-y-2">
                              {group.forms.map((form) => {
                                const derived = formStatuses.find((f) => f.key === form.key) || { status: 'missing', submission: null };
                                const cfg = STATUS_DISPLAY[derived.status] || STATUS_DISPLAY.missing;
                                const IconEl = cfg.icon;
                                const hasSubmission = Boolean(derived.submission);
                                const submission = derived.submission;

                                const submittedAt = fmtDate(submission?.submitted_at);
                                const reviewedAt = fmtDate(submission?.reviewed_at || submission?.verified_at || submission?.signed_off_at);
                                const reviewedBy = submission?.reviewed_by_name || submission?.signed_off_by_name || submission?.verified_by_name;

                                return (
                                  <div
                                    key={form.key}
                                    className={`p-4 rounded-lg border ${cfg.cardBorder}`}
                                    data-testid={`form-card-${form.key}`}
                                  >
                                    <div className="flex items-start justify-between gap-3">
                                      <div className="flex items-start gap-3 min-w-0">
                                        <IconEl className={`h-5 w-5 mt-0.5 shrink-0 ${cfg.iconColor}`} />
                                        <div className="min-w-0">
                                          <p className="font-medium text-gray-800 text-sm">{form.name}</p>
                                          <p className="text-xs text-gray-500">{form.description}</p>
                                          {form.sensitive && (
                                            <Badge variant="outline" className="mt-0.5 text-xs bg-slate-50 text-slate-500 border-slate-200">
                                              Sensitive
                                            </Badge>
                                          )}
                                          {form.prefill && (
                                            <p className="text-xs text-indigo-500 mt-0.5 italic">
                                              Auto-filled from worker's application
                                            </p>
                                          )}
                                          <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-xs">
                                            {submittedAt && (
                                              <span className="text-gray-400">
                                                Submitted: <span className="text-gray-600">{submittedAt}</span>
                                              </span>
                                            )}
                                            {reviewedAt ? (
                                              <span className="text-gray-400">
                                                Reviewed: <span className="text-gray-600">{reviewedAt}</span>
                                                {reviewedBy && <span className="text-gray-600"> by {reviewedBy}</span>}
                                              </span>
                                            ) : (derived.status === 'submitted' || derived.status === 'reviewed') ? (
                                              <span className="text-gray-400 italic">Not yet reviewed</span>
                                            ) : null}
                                            {derived.status === 'rejected' && submission?.rejection_reason && (
                                              <span className="text-red-600">
                                                Reason: {submission.rejection_reason}
                                              </span>
                                            )}
                                            {derived.status === 'returned_for_correction' && (
                                              <span className="text-red-600">
                                                Correction required: {submission?.correction_reason || submission?.review_reason || 'Worker correction requested'}
                                              </span>
                                            )}
                                          </div>
                                        </div>
                                      </div>

                                      <div className="flex items-center gap-2 shrink-0">
                                        <Badge className={cfg.color}>{cfg.label}</Badge>
                                        <div className="flex gap-1">
                                          {/* Signed off → View */}
                                          {derived.status === 'signed_off' && hasSubmission && (
                                            <>
                                              <Button size="sm" variant="outline"
                                                onClick={() => openFormSubmissionPdfViewer(submission, form)}
                                                className="text-green-700 border-green-200 hover:bg-green-50"
                                                data-testid={`view-submission-${form.key}`}>
                                                <Eye className="h-3.5 w-3.5 mr-1" />View
                                              </Button>
                                              {!isAuditor() && (
                                                <Button size="sm" variant="outline"
                                                  onClick={() => {
                                                    setFormCorrectionDialog({ submission, form });
                                                    setFormCorrectionReason('');
                                                  }}
                                                  className="text-red-600 border-red-200 hover:bg-red-50"
                                                  data-testid={`reopen-correction-${form.key}`}>
                                                  <RotateCcw className="h-3.5 w-3.5 mr-1" />Reopen for correction
                                                </Button>
                                              )}
                                            </>
                                          )}

                                          {/* Reviewed → View + Sign Off */}
                                          {derived.status === 'reviewed' && hasSubmission && (
                                            <>
                                              <Button size="sm" variant="outline"
                                                onClick={() => openFormSubmissionPdfViewer(submission, form)}
                                                className="text-indigo-600 border-indigo-200 hover:bg-indigo-50"
                                                data-testid={`view-submission-${form.key}`}>
                                                <Eye className="h-3.5 w-3.5 mr-1" />View
                                              </Button>
                                              {!isAuditor() && (
                                                <>
                                                  <Button size="sm" variant="outline"
                                                    onClick={async () => {
                                                      try {
                                                        await axios.post(
                                                          `${API}/form-submissions/${submission.id}/verify`, {},
                                                          { headers: { Authorization: `Bearer ${token}` } }
                                                        );
                                                        toast.success('Form signed off');
                                                        fetchFormSubmissions();
                                                      } catch { toast.error('Failed to sign off form'); }
                                                    }}
                                                    className="text-green-600 border-green-200 hover:bg-green-50"
                                                    data-testid={`sign-off-${form.key}`}>
                                                    <CheckCircle className="h-3.5 w-3.5 mr-1" />Sign Off
                                                  </Button>
                                                  <Button size="sm" variant="outline"
                                                    onClick={() => {
                                                      setFormCorrectionDialog({ submission, form });
                                                      setFormCorrectionReason('');
                                                    }}
                                                    className="text-red-600 border-red-200 hover:bg-red-50"
                                                    data-testid={`reopen-correction-${form.key}`}>
                                                    <RotateCcw className="h-3.5 w-3.5 mr-1" />Reopen for correction
                                                  </Button>
                                                </>
                                              )}
                                            </>
                                          )}

                                          {/* Submitted → Review & Approve (forced viewing) */}
                                          {derived.status === 'submitted' && hasSubmission && (
                                            <Button size="sm" variant="outline"
                                              onClick={() => setFormReviewViewer({
                                                isOpen: true,
                                                formName: form.name,
                                                submissionId: submission?.id,
                                              })}
                                              className="text-blue-600 border-blue-200 hover:bg-blue-50"
                                              data-testid={`review-submission-${form.key}`}>
                                              <Eye className="h-3.5 w-3.5 mr-1" />Review Submission
                                            </Button>
                                          )}

                                          {/* Missing / in-progress → passive label */}
                                          {(derived.status === 'missing' || derived.status === 'in_progress') && (
                                            <Badge
                                              className={derived.status === 'in_progress' ? 'bg-amber-50 text-amber-700 text-xs' : 'bg-slate-100 text-slate-600 text-xs'}
                                              data-testid={`form-status-${form.key}`}
                                            >
                                              {derived.status === 'in_progress' ? 'Worker in progress' : 'Missing'}
                                            </Badge>
                                          )}

                                          {/* Rejected → View */}
                                          {derived.status === 'rejected' && hasSubmission && (
                                            <Button size="sm" variant="outline"
                                              onClick={() => openFormSubmissionPdfViewer(submission, form)}
                                              className="text-red-600 border-red-200 hover:bg-red-50">
                                              <Eye className="h-3.5 w-3.5 mr-1" />View
                                            </Button>
                                          )}

                                          {/* Returned for correction → View only until worker resubmits */}
                                          {derived.status === 'returned_for_correction' && hasSubmission && (
                                            <Button size="sm" variant="outline"
                                              onClick={() => openFormSubmissionPdfViewer(submission, form)}
                                              className="text-red-600 border-red-200 hover:bg-red-50">
                                              <Eye className="h-3.5 w-3.5 mr-1" />View
                                            </Button>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            );
          })()}
          
          {/* Form Submission View Dialog */}
          <Dialog open={viewFormSubmission?.isOpen} onOpenChange={(open) => !open && setViewFormSubmission(null)}>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{viewFormSubmission?.formName} - Submission</DialogTitle>
                <DialogDescription>
                  Review the worker's submitted answers
                </DialogDescription>
              </DialogHeader>
              <div className="py-4">
                {viewFormSubmission?.data ? (
                  <div className="space-y-4">
                    {Object.entries(viewFormSubmission.data).map(([key, value]) => (
                      <div key={key} className="border-b pb-2">
                        <p className="text-sm font-medium text-gray-600">
                          {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                        </p>
                        <p className="text-gray-800">
                          {typeof value === 'boolean' ? (value ? 'Yes' : 'No') :
                           typeof value === 'object' ? JSON.stringify(value, null, 2) :
                           value || 'Not provided'}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">No submission data available</p>
                )}
              </div>
              <DialogFooter className="gap-2">
                {/* Download PDF for any form with a submission */}
                {viewFormSubmission?.submissionId && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => {
                      try {
                        let url, filename;
                        if (viewFormSubmission.formType === 'pre_interview_questionnaire') {
                          url = `${API}/employees/${employee?.id}/pre-interview-questionnaire/download-pdf`;
                          filename = `pre_interview_questionnaire_${employee?.first_name || ''}_${employee?.last_name || ''}.pdf`;
                        } else {
                          url = `${API}/form-submissions/${viewFormSubmission.submissionId}/download-pdf`;
                          filename = `${viewFormSubmission.formType || 'form'}_${employee?.first_name || ''}_${employee?.last_name || ''}.pdf`;
                        }
                        const resp = await axios.get(url, {
                          headers: { Authorization: `Bearer ${token}` },
                          responseType: 'blob'
                        });
                        const blob = new Blob([resp.data], { type: 'application/pdf' });
                        const blobUrl = window.URL.createObjectURL(blob);
                        const link = document.createElement('a');
                        link.href = blobUrl;
                        link.download = filename;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        window.URL.revokeObjectURL(blobUrl);
                        toast.success('PDF downloaded');
                      } catch { toast.error('Failed to download PDF'); }
                    }}
                    className="mr-auto"
                  >
                    <Download className="h-4 w-4 mr-1" />
                    Download PDF
                  </Button>
                )}
                <Button variant="outline" onClick={() => setViewFormSubmission(null)}>
                  Close
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* Reopen signed-off/reviewed form for worker correction */}
          <Dialog open={!!formCorrectionDialog} onOpenChange={(open) => {
            if (!open) {
              setFormCorrectionDialog(null);
              setFormCorrectionReason('');
            }
          }}>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Reopen for correction</DialogTitle>
                <DialogDescription>
                  Return {formCorrectionDialog?.form?.name || 'this form'} to the worker for correction. The previous signed-off version is kept in the audit history.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-2 py-2">
                <Label htmlFor="form-correction-reason">Correction reason</Label>
                <Textarea
                  id="form-correction-reason"
                  value={formCorrectionReason}
                  onChange={(event) => setFormCorrectionReason(event.target.value)}
                  placeholder="Explain exactly what the worker needs to correct."
                  rows={4}
                  disabled={isReopeningFormCorrection}
                />
                <p className="text-xs text-text-muted">
                  The worker will be able to edit and resubmit this form. Admin sign-off will be required again.
                </p>
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => {
                    setFormCorrectionDialog(null);
                    setFormCorrectionReason('');
                  }}
                  disabled={isReopeningFormCorrection}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleReopenFormForCorrection}
                  disabled={isReopeningFormCorrection || !formCorrectionReason.trim()}
                  className="bg-red-600 hover:bg-red-700"
                >
                  {isReopeningFormCorrection ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RotateCcw className="h-4 w-4 mr-2" />}
                  Reopen for correction
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* Form Review Viewer (PDF viewer with forced viewing + approve/reject) */}
          <EvidenceReviewViewerDialog
            isOpen={!!formReviewViewer?.isOpen}
            onClose={() => { setFormReviewViewer(null); fetchFormSubmissions(); }}
            mode="form-review"
            formSubmissionId={formReviewViewer?.submissionId}
            formName={formReviewViewer?.formName}
            employeeId={employee?.id}
            employeeName={employee ? `${employee.first_name} ${employee.last_name}` : ''}
            onFormApproved={() => fetchFormSubmissions()}
            onFormRejected={() => fetchFormSubmissions()}
          />
        </TabsContent>

        {/* ========== TAB 6: EMPLOYMENT ========== */}
        {/* Employment history + gap verification + declarations */}
        <TabsContent value="employment">
          <div className="space-y-6">
            <div className={`rounded-xl border p-4 ${employmentDecisionClasses.panel}`}>
              <div className="flex items-start gap-3">
                <div className={`mt-0.5 ${employmentDecisionClasses.icon}`}>
                  {employmentComplete || employmentReadyForSignOff ? <CheckCircle className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
                </div>
                <div className="flex-1">
                  <p className={`font-medium ${employmentDecisionClasses.text}`}>
                    Employment review: {employmentDecisionDisplay}
                  </p>
                  <p className={`mt-1 text-xs ${employmentDecisionClasses.subtext}`}>
                    Source: {hasPersistedEmploymentReview ? `Canonical employment review v${employmentReview?.version || 1}` : 'Compliance-file fallback'}
                    {employmentReviewError ? ' - canonical review unavailable' : ''}
                  </p>
                  {employmentComplete && (
                    <p className="mt-1 text-xs text-green-700">
                      ✓ Signed off by {employmentSignedOffBy || 'admin'}
                      {employmentSignedOffAt ? ` on ${new Date(employmentSignedOffAt).toLocaleDateString('en-GB')}` : ''}
                    </p>
                  )}
                  {employmentReadyForSignOff && !employmentSignedOff && !isAuditor() && (
                    <div className="mt-3 flex items-center gap-3">
                      <Button
                        size="sm"
                        onClick={handleSignOffEmploymentReview}
                        disabled={employmentSignOffLoading}
                        className="bg-green-600 hover:bg-green-700 text-white"
                      >
                        {employmentSignOffLoading
                          ? <Loader2 className="h-4 w-4 animate-spin mr-1" />
                          : <CheckCircle className="h-4 w-4 mr-1" />}
                        Sign off employment review
                      </Button>
                      <p className="text-xs text-blue-700">Confirms application evidence, declarations, coverage, and gap decisions have been reviewed.</p>
                    </div>
                  )}
                  {!employmentReadyForSignOff && !employmentSignedOff && employmentStatusBlockers.length > 0 && (
                    <div className={`mt-2 text-sm ${employmentDecisionClasses.subtext}`}>
                      <p className="font-medium">Items needing attention</p>
                      <ul className="mt-1 list-disc space-y-1 pl-5">
                        {employmentStatusBlockers.map((blocker) => (
                          <li key={blocker}>{blocker}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {!employmentSignedOff && employmentStatusWarnings.length > 0 && (
                    <div className="mt-2 text-sm text-amber-700">
                      <p className="font-medium">Attention</p>
                      <ul className="mt-1 list-disc space-y-1 pl-5">
                        {employmentStatusWarnings.map((warning) => (
                          <li key={warning}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4" data-testid="section-employment-summary-strip">
              <div className="rounded-xl border border-[#E4E8EB] bg-white p-3 shadow-sm">
                <p className="text-xs text-text-muted">Application form</p>
                <Badge variant="outline" className={`mt-2 ${applicationAvailable ? 'bg-green-100 text-green-700 border-green-200' : 'bg-gray-100 text-gray-600 border-gray-200'}`}>
                  {applicationAvailable ? 'Evidence on file' : 'Missing'}
                </Badge>
              </div>
              <div className="rounded-xl border border-[#E4E8EB] bg-white p-3 shadow-sm">
                <p className="text-xs text-text-muted">CV file</p>
                <Badge variant="outline" className={`mt-2 ${cvStatusBadgeClass}`}>
                  {cvStatusLabel}
                </Badge>
              </div>
              {employmentGapEvaluation?.is_complete !== undefined && (
                <div className="rounded-xl border border-[#E4E8EB] bg-white p-3 shadow-sm">
                  <p className="text-xs text-text-muted">10-year coverage</p>
                  <Badge variant="outline" className={`mt-2 ${gapAnalysisRun && employmentGapEvaluation.is_complete && coverageMet && (employmentCoverage?.coverage_percent ?? 0) > 0 ? 'bg-green-100 text-green-700 border-green-200' : 'bg-amber-100 text-amber-700 border-amber-200'}`}>
                    {gapAnalysisRun && employmentGapEvaluation.is_complete && coverageMet && (employmentCoverage?.coverage_percent ?? 0) > 0 ? 'Coverage met' : 'Incomplete'}
                  </Badge>
                </div>
              )}
              {gapAnalysisRun && gapVerifiedCount !== undefined && gapNeedsReviewCount !== null && (
                <div className="rounded-xl border border-[#E4E8EB] bg-white p-3 shadow-sm">
                  <p className="text-xs text-text-muted">Gap review</p>
                  <p className="mt-2 text-sm font-medium text-gray-800">
                    {gapVerifiedCount} verified / {gapNeedsReviewCount} needs review
                  </p>
                </div>
              )}
              <div className="rounded-xl border border-[#E4E8EB] bg-white p-3 shadow-sm">
                <p className="text-xs text-text-muted">Items needing attention</p>
                <p className="mt-2 text-sm font-medium text-gray-800">
                  {employmentDecisionState === 'Cannot assess' ? 'Cannot assess' : employmentStatusBlockers.length}
                </p>
              </div>
            </div>

            {/* 10-Year Coverage Card */}
            {employmentCoverage && coverageAssessed && (
              <Card className={`shadow-sm ${coverageMet ? 'border-green-200 bg-green-50' : 'border-amber-200 bg-amber-50'}`}>
                <CardContent className="py-4">
                  <div className="flex items-start gap-3">
                    {coverageMet ? (
                      <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                    ) : (
                      <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1 space-y-2">
                      <p className={`text-sm font-medium ${coverageMet ? 'text-green-800' : 'text-amber-800'}`}>
                        10-Year Employment Coverage: {coveragePercent}%
                      </p>
                      <p className="text-xs text-slate-600">
                        Required: {employmentCoverage.coverage_start ? new Date(employmentCoverage.coverage_start + 'T00:00:00Z').toLocaleDateString('en-GB', { month: 'short', year: 'numeric' }) : '?'} — Today
                        {' · '}Status: {coverageMet ? 'Coverage met' : 'Coverage incomplete'}
                      </p>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${coverageMet ? 'bg-green-500' : coverageDisplayPercent >= 60 ? 'bg-amber-500' : 'bg-red-500'}`}
                          style={{ width: `${Math.min(coverageDisplayPercent, 100)}%` }}
                        />
                      </div>
                      <p className="text-xs text-slate-500">
                        Applicant-submitted explanations do not add dated employment coverage. They explain gaps but do not extend the covered period.
                      </p>
                      <p className="text-xs text-slate-500">
                        {employmentCoverage.total_days_covered} of {employmentCoverage.total_days_required} days covered
                        {employmentCoverage.earliest_entry_date && ` · Earliest entry: ${new Date(employmentCoverage.earliest_entry_date + 'T00:00:00Z').toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })}`}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
            {employmentCoverage && !coverageAssessed && (
              <Card className="border-red-200 bg-red-50 shadow-sm">
                <CardContent className="py-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-red-800">Unable to confirm 10-year coverage</p>
                      <p className="mt-1 text-xs text-red-700">
                        {coverageLooksStaleOrUnusable
                          ? 'Dated employment history is present, but the stored coverage summary did not count any dated coverage.'
                          : 'The stored coverage summary is missing usable coverage totals.'}
                        {' '}Re-run gap analysis or save the employment history again before sign-off.
                      </p>
                      <p className="mt-1 text-xs text-red-700">
                        Applicant-submitted explanations are visible below as supporting notes but do not count as dated employment coverage.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
            {!employmentCoverage && employmentHistoryExists && (
              <Card className="border-red-200 bg-red-50 shadow-sm">
                <CardContent className="py-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-red-800">Unable to confirm 10-year coverage</p>
                      <p className="mt-1 text-xs text-red-700">
                        Employment history exists, but no usable coverage summary is available yet. Re-run gap analysis to generate coverage data.
                      </p>
                      <p className="mt-1 text-xs text-red-700">
                        Applicant-submitted explanations are supporting notes only and do not count as dated employment coverage.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            <Card className="border-[#E4E8EB] shadow-sm" data-testid="section-employment-evidence">
              <CardHeader>
                <CardTitle className="font-heading text-lg">Application & CV Evidence</CardTitle>
                <p className="text-xs text-text-muted">
                  Source evidence available on this page for employment-history review.
                </p>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-[#E4E8EB] bg-gray-50 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h4 className="font-medium text-gray-800">Application Record</h4>
                        <p className="mt-1 text-xs text-text-muted">Application submission and PDF export where already available.</p>
                      </div>
                      <Badge variant="outline" className={applicationAvailable ? 'bg-green-100 text-green-700 border-green-200' : 'bg-gray-100 text-gray-600 border-gray-200'}>
                        {applicationAvailable ? 'Evidence on file' : 'Missing'}
                      </Badge>
                    </div>

                    {applicationAvailable ? (
                      <div className="mt-4 space-y-3">
                        <div className="grid gap-3 sm:grid-cols-2">
                          <div>
                            <p className="text-xs text-text-muted">Submitted</p>
                            <p className="text-sm font-medium text-gray-800">
                              {applicationSubmission?.submitted_at || applicationSubmission?.updated_at
                                ? formatBackendDateTime(applicationSubmission?.submitted_at || applicationSubmission?.updated_at)
                                : 'Date unavailable'}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-text-muted">Source</p>
                            <p className="text-sm font-medium text-gray-800">
                              {applicationSubmission ? 'Online application' : applicationPdfDocument ? 'Uploaded PDF' : 'Unavailable'}
                            </p>
                          </div>
                        </div>

                        {applicationSubmission?.id ? (
                          <div className="flex flex-wrap gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleViewFormPDF(applicationSubmission.id)}
                            >
                              <Eye className="h-4 w-4 mr-1" />
                              View Application
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleDownloadFormPDF(applicationSubmission.id)}
                            >
                              <Download className="h-4 w-4 mr-1" />
                              Download PDF
                            </Button>
                          </div>
                        ) : (
                          <p className="text-xs text-text-muted">
                            Detailed viewing remains available from Forms & Interview when a structured application submission is stored.
                          </p>
                        )}
                      </div>
                    ) : (
                      <div className="mt-4 rounded-lg border border-dashed border-gray-300 bg-white p-4">
                        <p className="text-sm font-medium text-gray-700">No application form on file</p>
                        <p className="mt-1 text-xs text-text-muted">
                          This profile does not currently have a structured application record or uploaded application PDF.
                        </p>
                      </div>
                    )}

                    <div className="mt-4 border-t pt-4" data-testid="section-employment-declarations">
                      <h4 className="font-medium text-gray-800 mb-1">Applicant Declarations</h4>
                      <p className="text-xs text-gray-500 mb-3">
                        Consent and declaration data from the original application intake. Use this section to review or amend declarations.
                      </p>
                      <div className="p-4 rounded-lg border bg-gray-50 flex items-center justify-between gap-4">
                        <div>
                          <p className="text-sm font-medium text-gray-800">Declarations & Consent</p>
                          <p className="text-xs text-gray-600 mt-1">
                            Includes criminal/health declarations, DBS consent, right-to-work restrictions, and professional declarations.
                          </p>
                          <Badge
                            variant="outline"
                            className={`mt-2 ${
                              declarationsAdequatelyReviewed
                                ? 'bg-green-100 text-green-700 border-green-200'
                                : declarationsOnFile
                                  ? 'bg-amber-100 text-amber-700 border-amber-200'
                                  : 'bg-gray-100 text-gray-600 border-gray-200'
                            }`}
                          >
                            {declarationsAdequatelyReviewed
                              ? 'Reviewed'
                              : declarationsOnFile
                                ? 'Submitted, not reviewed'
                                : 'Missing'}
                          </Badge>
                        </div>
                        {!isAuditor() && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setEditDeclarationsOpen(true)}
                            data-testid="open-declarations-review"
                          >
                            <Edit className="h-4 w-4 mr-1" />
                            Review Declarations
                          </Button>
                        )}
                      </div>
                      {declarationsOnFile ? (
                        <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-0.5 text-xs">
                          {[
                            ['Criminal convictions', employee.declarations?.has_criminal_convictions],
                            ['Health conditions', employee.declarations?.has_health_conditions],
                            ['DBS consent', employee.declarations?.dbs_consent_given],
                            ['RTW restrictions', employee.declarations?.has_rtw_restrictions],
                          ].map(([label, val]) => (
                            <div key={label} className="flex items-center justify-between py-0.5 border-b border-gray-100">
                              <span className="text-gray-500">{label}</span>
                              <span className={val ? 'text-amber-700 font-medium' : 'text-green-700'}>
                                {val ? 'Declared' : 'None declared'}
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-2 text-xs text-gray-400 italic">Declarations not yet recorded.</p>
                      )}
                    </div>
                  </div>

                  <div className="rounded-xl border border-[#E4E8EB] bg-gray-50 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h4 className="font-medium text-gray-800">CV / Resume</h4>
                        <p className="mt-1 text-xs text-text-muted">Supporting evidence — view alongside the structured employment history below.</p>
                      </div>
                      <Badge variant="outline" className={cvFileExists ? 'bg-green-50 text-green-700 border-green-200' : 'bg-slate-50 text-slate-600 border-slate-200'}>
                        {cvFileExists ? 'On file' : 'Missing'}
                      </Badge>
                    </div>

                    {cvFileExists ? (
                      <div className="mt-4">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleViewCv}
                          data-testid="view-cv-btn"
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          View CV
                        </Button>
                        <p className="text-xs text-text-muted mt-2">
                          Compare the CV against the structured employment history from the application form to verify accuracy.
                        </p>
                      </div>
                    ) : (
                      <div className="mt-4 rounded-lg border border-dashed border-gray-300 bg-white p-4">
                        <p className="text-sm font-medium text-gray-700">CV not uploaded</p>
                        <p className="mt-1 text-xs text-text-muted">
                          Worker has not uploaded a CV yet. The CV is supporting evidence — employment history is taken from the application form.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#E4E8EB] shadow-sm" data-testid="section-employment-cv">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="font-heading text-lg">Employment History & Gap Review</CardTitle>
                  <p className="text-xs text-text-muted">
                    Structured employment history from the application form. Compare against the CV (above) to verify accuracy.
                  </p>
                </div>
                <div className="flex gap-2">
                  {!isAuditor() && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleRebuildEmploymentReview}
                      disabled={employmentReviewRebuildLoading}
                      data-testid="rebuild-employment-review-btn"
                    >
                      {employmentReviewRebuildLoading
                        ? <Loader2 className="h-4 w-4 animate-spin mr-1" />
                        : <RefreshCw className="h-4 w-4 mr-1" />}
                      Rebuild canonical review
                    </Button>
                  )}
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => setEditEmploymentOpen(true)}
                    data-testid="edit-employment-btn"
                  >
                    <Edit className="h-4 w-4 mr-1" />
                    Edit History
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
              
              {/* Gap analysis unavailable state */}
              {employmentGapsCannotAssess && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-medium text-red-800">Unable to confirm gaps from the current history</p>
                    <p className="text-sm text-red-600 mt-1">
                      {gapAnalysisFailed
                        ? 'Gap analysis encountered an error during processing. Click "Re-run Gap Analysis" to retry.'
                        : 'Employment gap analysis has not been run yet. Click "Re-run Gap Analysis" to detect gaps from the application form employment history.'}
                    </p>
                    {gapAnalysisError && (
                      <p className="text-xs text-red-500 mt-1 font-mono">{gapAnalysisError}</p>
                    )}
                    {!isAuditor() && employmentHistoryExists && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="mt-3 border-red-300 text-red-700 hover:bg-red-100"
                        disabled={gapRerunLoading}
                        onClick={async () => {
                          setGapRerunLoading(true);
                          try {
                            await axios.post(`${API}/employees/${employeeId}/detect-employment-gaps`, {}, {
                              headers: { Authorization: `Bearer ${token}` }
                            });
                            toast.success('Gap analysis completed — refreshing…');
                            await Promise.all([
                              fetchEmployee(),
                              fetchCompliance(),
                              fetchComplianceFile(),
                              fetchEmploymentReview({ rebuild: true })
                            ]);
                          } catch (err) {
                            toast.error(err?.response?.data?.detail || 'Gap analysis failed');
                          } finally {
                            setGapRerunLoading(false);
                          }
                        }}
                      >
                        {gapRerunLoading
                          ? <Loader2 className="h-4 w-4 animate-spin mr-1" />
                          : <RefreshCw className="h-4 w-4 mr-1" />}
                        Re-run Gap Analysis
                      </Button>
                    )}
                  </div>
                </div>
              )}

              {employmentHistoryExists && employmentHistoryGapRow && !employmentHistoryGapRow.has_gaps && employmentGapEvaluation && gapAnalysisRun && coverageMet && (employmentCoverage?.coverage_percent ?? 0) > 0 && (
                <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-green-800">{employmentHistoryGapRow.status_summary || 'No detected gaps — 10-year coverage met'}</p>
                    <p className="text-sm text-green-600 mt-1">Gap analysis has run and the dated employment history meets the required 10-year period. Admin sign-off is still required to complete the review.</p>
                  </div>
                </div>
              )}
              {employmentHistoryExists && employmentHistoryGapRow && !employmentHistoryGapRow.has_gaps && employmentGapEvaluation && gapAnalysisRun && coverageAssessed && !coverageMet && (
                <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-amber-800">No gaps detected, but 10-year coverage is incomplete</p>
                    <p className="text-sm text-amber-600 mt-1">No gaps were detected in the dated employment history, but sign-off is blocked until the required 10-year coverage period is met.</p>
                  </div>
                </div>
              )}

              {/* Employment Gap Panel */}
              {employmentHistoryGapRow?.has_gaps && (
                <div data-testid="section-employment-gaps">
                  <div className="mb-3">
                    <h4 className="font-medium text-gray-800">10-Year Gap Verification</h4>
                    <p className="mt-1 text-xs text-text-muted">
                      Gap statuses below come from the current employment-gap evaluation already stored on the compliance file.
                    </p>
                  </div>
                  <EmploymentGapPanel
                    employeeId={employeeId}
                    employeeName={`${employee?.first_name} ${employee?.last_name}`}
                    initialData={{
                      has_gaps: true,
                      gaps: canonicalEmploymentGaps,
                      evaluation: employmentHistoryGapRow.gap_evaluation
                    }}
                    isAdmin={!isAuditor() && (user?.role === 'admin' || user?.role === 'super_admin')}
                    onGapUpdate={() => {
                      fetchCompliance();
                      fetchComplianceFile();
                      fetchEmploymentReview();
                    }}
                  />
                </div>
              )}
              
              {/* Matched Applicant Gap Explanations — linked to detected gaps */}
              {matchedApplicantGapExplanations.length > 0 && (
                <div className="mt-4 mb-4" data-testid="section-matched-gap-explanations">
                  <h4 className="font-medium text-gray-800 mb-2">Matched Applicant Gap Explanations</h4>
                  <p className="mb-3 text-xs text-text-muted">
                    These applicant-submitted explanations matched a detected employment gap.
                  </p>
                  <div className="space-y-2">
                    {matchedApplicantGapExplanations.map((expl, idx) => {
                      const hasDateRange = Boolean((expl.gap_start || expl.start_date) && (expl.gap_end || expl.end_date));
                      const gapStart = expl.gap_start || expl.start_date;
                      const gapEnd = expl.gap_end || expl.end_date;
                      const durationDays = expl.duration_days || expl.gap_duration_days;
                      const durationMonths = expl.duration_months || expl.gap_duration_months;
                      const fmtDate = (d) => d ? new Date(d + 'T00:00:00Z').toLocaleDateString('en-GB', { month: 'short', year: 'numeric' }) : '?';
                      const explanationType = expl.reason_type || expl.type || expl.category || 'Applicant declaration';
                      return (
                        <div key={expl.gap_id || idx} className="p-3 bg-green-50 border border-green-200 rounded-lg">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            {hasDateRange ? (
                              <span className="text-xs font-medium text-green-800">
                                {fmtDate(gapStart)} — {fmtDate(gapEnd)}
                              </span>
                            ) : (
                              <span className="text-xs font-medium text-green-800">
                                Undated applicant gap explanation
                              </span>
                            )}
                            {(durationDays || durationMonths) && (
                              <Badge variant="outline" className="text-[10px] bg-green-100 text-green-700 border-green-200">
                                {durationDays ? `${durationDays} days` : `${durationMonths} months`}
                              </Badge>
                            )}
                            {explanationType && (
                              <Badge variant="outline" className="text-[10px] bg-green-100 text-green-600 border-green-200 capitalize">
                                {explanationType.replace(/_/g, ' ')}
                              </Badge>
                            )}
                            <Badge variant="outline" className="text-[10px] bg-green-100 text-green-700 border-green-200">
                              Matched to {expl.matched_gap_id || 'detected gap'}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-700">{expl.explanation || 'No explanation text provided by applicant'}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Unmatched Supporting Notes — NOT linked to any detected gap */}
              {unmatchedApplicantGapExplanations.length > 0 && (
                <div className="mt-4 mb-4" data-testid="section-unmatched-supporting-notes">
                  <h4 className="font-medium text-slate-700 mb-2">Unmatched Supporting Notes</h4>
                  <p className="mb-3 text-xs text-slate-500">
                    These applicant-submitted notes did not match any detected employment gap. They are preserved as supporting context but do not count as verified gap explanations or dated coverage.
                  </p>
                  <div className="space-y-2">
                    {unmatchedApplicantGapExplanations.map((expl, idx) => {
                      const hasDateRange = Boolean((expl.gap_start || expl.start_date) && (expl.gap_end || expl.end_date));
                      const gapStart = expl.gap_start || expl.start_date;
                      const gapEnd = expl.gap_end || expl.end_date;
                      const durationDays = expl.duration_days || expl.gap_duration_days;
                      const durationMonths = expl.duration_months || expl.gap_duration_months;
                      const fmtDate = (d) => d ? new Date(d + 'T00:00:00Z').toLocaleDateString('en-GB', { month: 'short', year: 'numeric' }) : '?';
                      const explanationType = expl.reason_type || expl.type || expl.category || 'Applicant note';
                      return (
                        <div key={expl.gap_id || idx} className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            {hasDateRange ? (
                              <span className="text-xs font-medium text-slate-700">
                                {fmtDate(gapStart)} — {fmtDate(gapEnd)}
                              </span>
                            ) : (
                              <span className="text-xs font-medium text-slate-700">
                                Undated applicant note
                              </span>
                            )}
                            {(durationDays || durationMonths) && (
                              <Badge variant="outline" className="text-[10px] bg-slate-100 text-slate-600 border-slate-200">
                                {durationDays ? `${durationDays} days` : `${durationMonths} months`}
                              </Badge>
                            )}
                            {explanationType && (
                              <Badge variant="outline" className="text-[10px] bg-slate-100 text-slate-500 border-slate-200 capitalize">
                                {explanationType.replace(/_/g, ' ')}
                              </Badge>
                            )}
                            <Badge variant="outline" className="text-[10px] bg-amber-50 text-amber-600 border-amber-200">
                              Not attached to detected gap
                            </Badge>
                          </div>
                          <p className="text-sm text-slate-600">{expl.explanation || 'No explanation text provided by applicant'}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            This note is preserved as applicant evidence only. It does not prove dated 10-year coverage.
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Employment Records */}
              {canonicalEmploymentRecords.length > 0 && (
                <div className="mt-6" data-testid="section-employment-history">
                  <h4 className="font-medium text-gray-800 mb-3">Employment Records</h4>
                  <p className="mb-3 text-xs text-text-muted">
                    Dated employment roles from the compliance-file employment review. These records are the basis for gap detection and 10-year coverage calculation.
                  </p>
                  <div className="space-y-3">
                    {canonicalEmploymentRecords.map((job, idx) => (
                      <div key={idx} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium text-gray-800">{job.employer || job.company || job.employer_name}</p>
                            <p className="text-sm text-gray-600">{job.job_title || job.position}</p>
                          </div>
                          <p className="text-xs text-gray-500">
                            {formatBackendDate(job.start_date, { format: 'short' })} - {job.end_date ? formatBackendDate(job.end_date, { format: 'short' }) : 'Present'}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Invalid Employment Entries */}
              {invalidEmploymentEntries.length > 0 && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg" data-testid="section-employment-invalid-entries">
                  <h4 className="font-medium text-red-800 mb-2">Invalid employment entries</h4>
                  <p className="mb-2 text-xs text-red-700">These rows were not counted toward 10-year coverage.</p>
                  <div className="space-y-2">
                    {invalidEmploymentEntries.map((entry, idx) => (
                      <div key={idx} className="text-xs text-red-700">
                        Row {Number.isFinite(entry?.index) ? entry.index + 1 : idx + 1}: {entry?.reason || 'Invalid employment row'}
                        {entry?.employer ? ` (${entry.employer})` : ''}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!canonicalEmploymentRecords.length && !employmentHistoryGapRow?.has_gaps && (
                <div className="text-center py-8 text-gray-500">
                  <Briefcase className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No employment history recorded</p>
                </div>
              )}

              {/* Qualifications & Education — supporting context, shown last */}
              {(employee?.qualifications || employee?.education) && (
                <div className="mt-6 pt-6 border-t border-gray-200" data-testid="section-employment-qualifications">
                  <h4 className="font-medium text-gray-800 mb-3">Qualifications & Education</h4>
                  <div className="space-y-3">
                    {employee?.qualifications && (
                      <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                        <p className="text-sm font-medium text-gray-700 mb-1">Qualifications</p>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">{employee.qualifications}</p>
                      </div>
                    )}
                    {employee?.education && (
                      <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                        <p className="text-sm font-medium text-gray-700 mb-1">Education</p>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">{employee.education}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        <TabsContent value="checklist">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="font-heading text-lg">Compliance File</CardTitle>
                  <p className="text-xs text-text-muted mt-1">
                    Operational workflow for compliance. Upload evidence, verify checks, manage agreements.
                  </p>
                </div>
                {canonicalProgress && (
                  <div className={`flex items-center gap-2 text-sm px-4 py-2 rounded-xl font-medium ${canonicalReadinessClass}`}>
                    {canonicalIsWorkReady || canonicalCanPromote ? (
                      <Shield className="h-4 w-4" />
                    ) : (
                      <AlertTriangle className="h-4 w-4" />
                    )}
                    {canonicalReadinessLabel}
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {/* ============================================== */}
              {/* COMPLIANCE FILE - Linear Workflow                */}
              {/* All actions live INSIDE each requirement card    */}
              {/* No global actions - see issue → scroll → fix     */}
              {/* ============================================== */}

              {/* Conditional Items - Keep minimal info about items not required */}
              {complianceRequirements?.conditional_not_required?.length > 0 && (
                <div className="mb-4 p-3 bg-gray-50 border border-gray-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-gray-700">Some items not required for this employee:</p>
                      <ul className="mt-1 space-y-0.5">
                        {complianceRequirements.conditional_not_required.map((item, idx) => (
                          <li key={idx} className="text-xs text-gray-600">
                            {item.name} — {item.reason}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {!complianceRequirements ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Employment Gap Verification moved to Employment History tab only */}

                  {/* ============================================ */}
                  {/* DUAL-ROW COMPLIANCE SECTION (Phase 4A) */}
                  {/* Separates evidence from employer checks */}
                  {/* ============================================ */}
                  <div className="mb-6">
                    
                    <DualRowComplianceSection
                      employeeId={employeeId}
                      employeeEmail={employee?.email}
                      employeeName={employee ? `${employee.first_name} ${employee.last_name}` : ''}
                      onUpload={(key) => {
                        // Trigger document upload for the specified requirement
                        setSelectedRequirement(key);
                        setUploadDialogOpen(true);
                      }}
                      onRequest={(key, title) => {
                        // Trigger request document dialog with proper requirement object
                        setRequestingRequirement({ id: key, name: title || key });
                        setRequestDocMessage('');
                        setRequestDocDialogOpen(true);
                      }}
                      onPreviewFile={(fileObj) => {
                        // Handle both old format (doc.file_url) and new format from RequirementFilesDrawer
                        const rawUrl = fileObj?.file_url || fileObj?.url;
                        const name = fileObj?.file_name || fileObj?.name || 'Document';
                        if (rawUrl) {
                          // FIX: Ensure URL is absolute - API already ends with /api
                          let url = rawUrl;
                          if (rawUrl.startsWith('/api/')) {
                            url = `${API}${rawUrl.substring(4)}`; // "/api/foo" -> API + "/foo"
                          }
                          let stampedUrl = fileObj?.stamped_file_url || null;
                          if (stampedUrl && stampedUrl.startsWith('/api/')) {
                            stampedUrl = `${API}${stampedUrl.substring(4)}`;
                          }
                          setPreviewFile({ url, name, filename: name, stampedFileUrl: stampedUrl });
                          setPreviewFiles([]); // Clear multi-file array
                          setPreviewOpen(true);
                        } else {
                          // No URL available - show error toast
                          console.error('No file URL available for preview', fileObj);
                        }
                      }}
                      onExtractReview={(docId) => {
                        setDocExtractionDocumentId(docId);
                        setDocExtractionReviewOpen(true);
                      }}
                      onRecordCheck={(checkType) => {
                        setRecordCheckType(checkType);
                        setRecordCheckDialogOpen(true);
                      }}
                      employeeData={employee}
                      isAuditor={isAuditor()}
                      onRefresh={() => {
                        fetchData();
                        fetchCompliance();
                      }}
                    />
                  </div>

                  {/* TRAINING SUMMARY CARD - Phase 4A */}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Policies Tab - Extracted to PoliciesTabContent */}
        <TabsContent value="policies">
          <PoliciesTabContent
            policies={policies}
            token={token}
            isAuditor={isAuditor()}
            isAdmin={isAdmin()}
            onRefresh={fetchData}
          />
        </TabsContent>

        {/* Training Tab */}
        <TabsContent value="training" ref={trainingSectionRef} data-testid="section-training-root">
          {/* Audit-Ready Training Matrix - Complete training record with tabs */}
          {/* Contains: Mandatory Training, All Qualifications, Certificates tabs */}
          <AuditReadyTrainingMatrix
            employeeId={employeeId}
            employeeName={`${employee?.first_name} ${employee?.last_name}`}
            role={employee?.role}
            onUploadCertificate={() => {
              // Open the training intake wizard
              setTrainingIntakeOpen(true);
            }}
            onViewCertificate={(recordId) => {
              handleViewTrainingCertificate(recordId, 'training_certificate');
            }}
            onRefresh={() => {
              fetchTrainingEvaluation();
              fetchProposedTrainingItems();
            }}
          />
          
          {/* Induction Checklist - 15 Care Certificate Standards */}
          <div className="mt-6" data-testid="section-training-induction">
            <InductionChecklistPanel
              employeeId={employeeId}
              employeeName={`${employee?.first_name} ${employee?.last_name}`}
              isAuditor={isAuditor()}
              onStatusChange={() => {
                fetchTrainingEvaluation();
                fetchComplianceFile();
              }}
            />
          </div>
        </TabsContent>

        {/* Audit Log Tab - Extracted to AuditTabContent */}
        <TabsContent value="audit">
          <AuditTabContent employeeId={employeeId} />
        </TabsContent>

        {/* ========== TAB: COMPETENCIES ========== */}
        <TabsContent value="competencies" data-testid="section-competencies-root">
          <CompetencyAssessmentsPanel
            employeeId={employeeId}
            employeeName={employee ? `${employee.first_name} ${employee.last_name}` : ''}
            onRefresh={() => {
              fetchComplianceFile();
              fetchRecruitmentStatus();
            }}
          />
        </TabsContent>

        {/* ========== TAB: SPOT CHECKS ========== */}
        {lifecycleStage === 'active' && (
          <TabsContent value="spot_checks" data-testid="section-spot-checks-root">
            <SpotChecksPanel
              employeeId={employeeId}
              employeeName={employee ? `${employee.first_name} ${employee.last_name}` : ''}
              onRefresh={() => {
                fetchComplianceFile();
                fetchRecruitmentStatus();
              }}
            />
          </TabsContent>
        )}

        {/* References Tab - Extracted to ReferencesTabContent */}
        <TabsContent value="references" data-testid="section-references-root">
          <ReferencesTabContent 
            key={`references-${employeeId}-${referencesTabRefreshKey}`}
            employeeId={employeeId}
            employee={employee}
            onRefresh={() => {
              fetchComplianceFile();
              fetchRecruitmentStatus();
            }}
            onEditReference={(refNum, refData) => {
              setSelectedReferenceId(refNum);
              setSelectedReferenceData({
                ...refData,
                referee_name: refData.name,
                referee_email: refData.email,
                referee_phone: refData.phone,
                referee_organisation: refData.organisation,
                referee_position: refData.job_title || refData.position,
                referee_relationship: refData.relationship
              });
              setEditReferenceOpen(true);
            }}
          />
        </TabsContent>
      </Tabs>

      {/* Edit Employee Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <Edit className="h-5 w-5 text-teal-600" />
              Edit Employee Details
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">First Name *</Label>
                <Input
                  value={editForm.first_name}
                  onChange={(e) => setEditForm({...editForm, first_name: e.target.value})}
                  className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Last Name *</Label>
                <Input
                  value={editForm.last_name}
                  onChange={(e) => setEditForm({...editForm, last_name: e.target.value})}
                  className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Email *</Label>
              <Input
                type="email"
                value={editForm.email}
                onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
              />
            </div>
            
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Phone</Label>
              <Input
                type="tel"
                value={editForm.phone}
                onChange={(e) => setEditForm({...editForm, phone: e.target.value})}
                className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Role *</Label>
                <Select value={editForm.role} onValueChange={(value) => setEditForm({...editForm, role: value})}>
                  <SelectTrigger className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 focus:ring-2 focus:ring-teal-600 focus:border-teal-600">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-200">
                    {roles.map((role) => (
                      <SelectItem key={role} value={role} className="text-gray-900">{role}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Status</Label>
                <Select value={editForm.status} onValueChange={(value) => setEditForm({...editForm, status: value})}>
                  <SelectTrigger className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 focus:ring-2 focus:ring-teal-600 focus:border-teal-600">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-200">
                    {statuses.map((s) => (
                      <SelectItem key={s.value} value={s.value} className="text-gray-900">{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Onboarding Status</Label>
                <Select value={editForm.onboarding_status} onValueChange={(value) => setEditForm({...editForm, onboarding_status: value})}>
                  <SelectTrigger className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 focus:ring-2 focus:ring-teal-600 focus:border-teal-600">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-200">
                    {onboardingStatuses.map((s) => (
                      <SelectItem key={s} value={s} className="text-gray-900">{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Start Date</Label>
                <Input
                  type="date"
                  value={editForm.start_date}
                  onChange={(e) => setEditForm({...editForm, start_date: e.target.value})}
                  className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Notes</Label>
              <Textarea
                value={editForm.notes}
                onChange={(e) => setEditForm({...editForm, notes: e.target.value})}
                placeholder="Internal notes about this employee..."
                className="rounded-xl min-h-[80px] bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
              />
            </div>
          </div>
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setEditDialogOpen(false)} className="rounded-xl border-gray-300 text-gray-700 hover:bg-gray-50">
              Cancel
            </Button>
            <Button onClick={handleSaveEmployee} disabled={isSaving} className="bg-teal-600 hover:bg-teal-700 text-white rounded-xl">
              {isSaving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Archive Confirmation Dialog */}
      <Dialog open={archiveDialogOpen} onOpenChange={setArchiveDialogOpen}>
        <DialogContent className="bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <Archive className="h-5 w-5 text-amber-500" />
              Archive Employee
            </DialogTitle>
            <DialogDescription className="text-gray-500">
              Are you sure you want to archive <strong className="text-gray-900">{employee?.first_name} {employee?.last_name}</strong>?
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4">
            <p className="text-sm text-gray-600">This will:</p>
            <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
              <li>Hide employee from the active employees list</li>
              <li>Retain all documents, forms, and audit history</li>
              <li>Allow restoration at any time</li>
            </ul>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setArchiveDialogOpen(false)} className="rounded-xl border-gray-300 text-gray-700 hover:bg-gray-50">
              Cancel
            </Button>
            <Button onClick={handleArchiveEmployee} className="bg-amber-500 hover:bg-amber-600 text-white rounded-xl">
              <Archive className="h-4 w-4 mr-2" />
              Archive Employee
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Permanent Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Permanent Deletion
            </DialogTitle>
            <DialogDescription className="text-gray-500">
              Are you sure you want to <strong className="text-gray-900">permanently delete</strong> {employee?.first_name} {employee?.last_name}?
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4 bg-red-50 p-4 rounded-xl border border-red-200">
            <p className="text-sm font-medium text-red-600">This action cannot be undone!</p>
            <p className="text-sm text-gray-600">All of the following will be permanently deleted:</p>
            <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
              <li>Employee record</li>
              <li>All uploaded documents</li>
              <li>All compliance forms</li>
              <li>Training records</li>
              <li>Policy assignments</li>
            </ul>
            <p className="text-xs text-gray-500 mt-2">Only use this for duplicate records, test data, or incorrect entries.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} className="rounded-xl border-gray-300 text-gray-700 hover:bg-gray-50">
              Cancel
            </Button>
            <Button onClick={handlePermanentDelete} className="bg-red-600 hover:bg-red-700 text-white rounded-xl">
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Permanently
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Training Completion Dialog */}
      <Dialog open={trainingDialogOpen} onOpenChange={setTrainingDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-text-primary">
              <GraduationCap className="h-5 w-5 text-primary" />
              Mark Training Complete
            </DialogTitle>
            <DialogDescription className="text-text-muted">
              Mark this training requirement as completed for the employee.
            </DialogDescription>
          </DialogHeader>
          
          {selectedTrainingReq && (
            <div className="space-y-4 py-4">
              <div className="p-4 bg-[#F8FAFA] rounded-xl">
                <p className="font-medium text-text-primary">{selectedTrainingReq.name}</p>
                <p className="text-sm text-text-muted mt-1">
                  Category: {selectedTrainingReq.category?.replace(/_/g, ' ').replace(/^[A-Z]_/, '')}
                </p>
              </div>
              
              <div className="space-y-2">
                <Label className="text-text-primary">Expiry Date (Optional)</Label>
                <Input
                  type="date"
                  value={trainingExpiryDate}
                  onChange={(e) => setTrainingExpiryDate(e.target.value)}
                  className="rounded-xl"
                  placeholder="Leave empty if no expiry"
                />
                <p className="text-xs text-text-muted">
                  Set an expiry date if this training needs to be renewed
                </p>
              </div>
              
              <div className="bg-info/10 border border-info/20 rounded-xl p-3">
                <p className="text-sm text-info font-medium">What happens:</p>
                <ul className="text-xs text-text-muted mt-1 space-y-1">
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Training record created or updated
                  </li>
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Compliance requirement marked complete
                  </li>
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Compliance score updates immediately
                  </li>
                </ul>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setTrainingDialogOpen(false);
                setSelectedTrainingReq(null);
                setTrainingExpiryDate('');
              }} 
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleCompleteTraining}
              disabled={isCompletingTraining}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
              data-testid="confirm-complete-training"
            >
              {isCompletingTraining ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Mark Complete
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Training Certificate Upload Dialog */}
      <Dialog open={trainingCertDialogOpen} onOpenChange={setTrainingCertDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-text-primary">
              <Upload className="h-5 w-5 text-primary" />
              Upload Training Certificate
            </DialogTitle>
            <DialogDescription className="text-text-muted">
              Upload a certificate as evidence for this training requirement.
            </DialogDescription>
          </DialogHeader>
          
          {selectedTrainingReq && (
            <div className="space-y-4 py-4">
              <div className="p-4 bg-[#F8FAFA] rounded-xl">
                <p className="font-medium text-text-primary">{selectedTrainingReq.name}</p>
                <p className="text-sm text-text-muted mt-1">
                  Category: {selectedTrainingReq.category?.replace(/_/g, ' ').replace(/^[A-Z]_/, '')}
                </p>
              </div>
              
              <div className="space-y-2">
                <Label className="text-text-primary">Certificate File *</Label>
                <FileUploaderInline
                  onFileSelect={(file) => setTrainingCertFile(file)}
                  selectedFile={trainingCertFile}
                  onClear={() => setTrainingCertFile(null)}
                  acceptedTypes={['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']}
                  placeholder="Drop certificate here or click to browse"
                  data-testid="training-cert-file-input"
                />
                <p className="text-xs text-text-muted">
                  Accepted formats: PDF, JPG, PNG, DOC, DOCX (max 10MB)
                </p>
              </div>
              
              <div className="space-y-2">
                <Label className="text-text-primary">Certificate Expiry Date (Optional)</Label>
                <Input
                  type="date"
                  value={trainingExpiryDate}
                  onChange={(e) => setTrainingExpiryDate(e.target.value)}
                  className="rounded-xl"
                />
                <p className="text-xs text-text-muted">
                  Set an expiry date if this certificate needs to be renewed
                </p>
              </div>
              
              <div className="bg-success/10 border border-success/20 rounded-xl p-3">
                <p className="text-sm text-success font-medium">Audit-Ready Evidence:</p>
                <ul className="text-xs text-text-muted mt-1 space-y-1">
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Certificate stored with audit trail
                  </li>
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Training marked as complete with evidence
                  </li>
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Certificate can be viewed and downloaded
                  </li>
                  <li className="flex items-center gap-1">
                    <Shield className="h-3 w-3 text-success" />
                    Ready for verification
                  </li>
                </ul>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setTrainingCertDialogOpen(false);
                setSelectedTrainingReq(null);
                setTrainingCertFile(null);
                setTrainingExpiryDate('');
              }} 
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleUploadTrainingCertificate}
              disabled={isUploadingCert || !trainingCertFile}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
              data-testid="confirm-upload-training-cert"
            >
              {isUploadingCert ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload Certificate
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Evidence Details Modal */}
      <Dialog open={editEvidenceOpen} onOpenChange={setEditEvidenceOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">Edit Document Details</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <p className="text-sm text-text-muted">
              Update document metadata. A reason is required for audit trail purposes.
            </p>
            
            <div className="space-y-2">
              <Label>Document Label</Label>
              <Input
                value={editForm.file_label}
                onChange={(e) => setEditForm(prev => ({ ...prev, file_label: e.target.value }))}
                placeholder="e.g., DBS Certificate 2024"
                className="rounded-xl"
              />
            </div>
            
            {/* DBS Update Service Check - Special labels and auto-calculation */}
            {editEvidenceData?.requirementId === 'dbs_check' ? (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Last DBS Check Date</Label>
                  <Input
                    type="date"
                    value={editForm.issue_date}
                    onChange={(e) => {
                      const checkDate = e.target.value;
                      // Auto-calculate Next Review Due = Check Date + 12 months
                      let nextReviewDate = '';
                      if (checkDate) {
                        const date = new Date(checkDate);
                        date.setFullYear(date.getFullYear() + 1);
                        nextReviewDate = date.toISOString().split('T')[0];
                      }
                      setEditForm(prev => ({ 
                        ...prev, 
                        issue_date: checkDate,
                        expiry_date: nextReviewDate
                      }));
                    }}
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Next DBS Review Due</Label>
                  <Input
                    type="date"
                    value={editForm.expiry_date}
                    onChange={(e) => setEditForm(prev => ({ ...prev, expiry_date: e.target.value }))}
                    className="rounded-xl bg-gray-50"
                    title="Auto-calculated as 12 months from Last DBS Check Date"
                  />
                  <p className="text-xs text-text-muted">Auto-calculated (+12 months)</p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Issue Date</Label>
                  <Input
                    type="date"
                    value={editForm.issue_date}
                    onChange={(e) => setEditForm(prev => ({ ...prev, issue_date: e.target.value }))}
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Expiry Date</Label>
                  <Input
                    type="date"
                    value={editForm.expiry_date}
                    onChange={(e) => setEditForm(prev => ({ ...prev, expiry_date: e.target.value }))}
                    className="rounded-xl"
                  />
                </div>
              </div>
            )}
            
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={editForm.notes}
                onChange={(e) => setEditForm(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="Additional notes about this document..."
                className="rounded-xl"
                rows={3}
              />
            </div>
            
            <div className="space-y-2">
              <Label className="text-warning">Reason for Change *</Label>
              <Textarea
                value={editForm.reason}
                onChange={(e) => setEditForm(prev => ({ ...prev, reason: e.target.value }))}
                placeholder="e.g., Wrong expiry year entered, Corrected issue date from certificate..."
                className="rounded-xl border-warning/50 focus:border-warning"
                rows={2}
              />
              <p className="text-xs text-text-muted">
                This will be recorded in the audit trail.
              </p>
            </div>
          </div>
          <DialogFooter className="mt-4">
            <Button 
              variant="outline" 
              onClick={() => setEditEvidenceOpen(false)}
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSaveEvidenceEdit}
              disabled={isEditingEvidence || !editForm.reason}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
            >
              {isEditingEvidence ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit History Modal */}
      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <History className="h-5 w-5 text-primary" />
              Change History
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-4">
            {editHistory.length === 0 ? (
              <div className="text-center py-8">
                <History className="h-10 w-10 mx-auto text-text-muted/50 mb-2" />
                <p className="text-text-muted">No changes recorded</p>
                <p className="text-xs text-text-muted mt-1">
                  Document details have not been modified since upload.
                </p>
              </div>
            ) : (
              editHistory.map((log) => (
                <div 
                  key={log.id} 
                  className="p-3 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-primary" />
                      <span className="font-medium text-text-primary text-sm">
                        {log.changed_by_name}
                      </span>
                    </div>
                    <span className="text-xs text-text-muted">
                      {formatBackendDateTime(log.changed_at)}
                    </span>
                  </div>
                  <div className="text-sm space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-text-muted">Field:</span>
                      <span className="font-medium text-text-primary capitalize">
                        {log.field_changed.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-text-muted">From:</span>
                      <span className="text-error line-through">
                        {log.old_value || '(empty)'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-text-muted">To:</span>
                      <span className="text-success">
                        {log.new_value || '(empty)'}
                      </span>
                    </div>
                    <div className="flex items-start gap-2 mt-2 pt-2 border-t border-[#E4E8EB]">
                      <span className="text-text-muted">Reason:</span>
                      <span className="text-text-primary italic">
                        "{log.reason}"
                      </span>
                    </div>
                    {log.was_verified_before_edit && (
                      <div className="mt-2 px-2 py-1 bg-warning/10 text-warning text-xs rounded-lg inline-block">
                        Changed after approval
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
          <DialogFooter className="mt-4">
            <Button 
              variant="outline" 
              onClick={() => setHistoryOpen(false)}
              className="rounded-xl"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete File Dialog */}
      <Dialog open={removeDialogOpen} onOpenChange={setRemoveDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="h-5 w-5" />
              Delete File
            </DialogTitle>
            <DialogDescription>
              This will permanently remove the file from active use. The file will no longer count towards compliance. An audit record will be kept.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {selectedFileForAction && (
              <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                <p className="text-sm font-medium text-red-800">{selectedFileForAction.file_label || selectedFileForAction.original_filename || 'File'}</p>
                {selectedFileForAction.uploaded_at && (
                  <p className="text-xs text-red-600 mt-1">
                    Uploaded: {formatBackendDate(selectedFileForAction.uploaded_at)}
                  </p>
                )}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="delete-reason">Reason for deletion (optional)</Label>
              <Textarea
                id="delete-reason"
                placeholder="Enter an optional reason for deleting this file"
                value={removeReason}
                onChange={(e) => setRemoveReason(e.target.value)}
                className="min-h-[80px] rounded-xl"
              />
              <p className="text-xs text-text-muted">This reason will be recorded in the audit trail if provided.</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoveDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleDeleteFile}
              disabled={isRemoving}
              className="rounded-xl"
              data-testid="confirm-delete-file"
            >
              {isRemoving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Delete File
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Replace File Dialog */}
      <Dialog open={replaceDialogOpen} onOpenChange={setReplaceDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5 text-primary" />
              Replace File
            </DialogTitle>
            <DialogDescription>
              Uploading a new file will replace the existing one. The old file will be kept in history for audit purposes.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {selectedFileForAction && (
              <div className="p-3 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">Replacing:</p>
                <p className="text-sm font-medium">{selectedFileForAction.file_label || selectedFileForAction.original_filename}</p>
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="replace-file">New File <span className="text-error">*</span></Label>
              <FileUploaderInline
                onFileSelect={(file) => setReplaceFile(file)}
                selectedFile={replaceFile}
                onClear={() => setReplaceFile(null)}
                acceptedTypes={['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'image/webp']}
                placeholder="Drop replacement file here or click to browse"
              />
              <p className="text-xs text-muted-foreground">Upload PDF or photo (JPG, PNG)</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="replace-reason">Reason for replacement <span className="text-error">*</span></Label>
              <Textarea
                id="replace-reason"
                placeholder="Why is this file being replaced? (e.g. clearer scan, updated document)"
                value={replaceReason}
                onChange={(e) => setReplaceReason(e.target.value)}
                className="min-h-[80px]"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReplaceDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleReplaceFile}
              disabled={isReplacing || !replaceReason.trim() || !replaceFile}
              className="bg-primary hover:bg-primary-hover"
            >
              {isReplacing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
              Replace File
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Document Correction Dialog - Step 8 */}
      <Dialog open={docCorrectionDialogOpen} onOpenChange={setDocCorrectionDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {docCorrectionType === 'uploaded_in_error' && <FileWarning className="h-5 w-5 text-amber-500" />}
              {docCorrectionType === 'supersede' && <FileArchive className="h-5 w-5 text-blue-500" />}
              {docCorrectionType === 'move_category' && <FormInput className="h-5 w-5 text-purple-500" />}
              {docCorrectionType === 'reopen_review' && <RotateCcw className="h-5 w-5 text-green-500" />}
              {docCorrectionType === 'uploaded_in_error' && 'Mark as Uploaded in Error'}
              {docCorrectionType === 'supersede' && 'Mark as Superseded'}
              {docCorrectionType === 'move_category' && 'Move to Different Category'}
              {docCorrectionType === 'reopen_review' && 'Reopen for Review'}
            </DialogTitle>
            <DialogDescription>
              {docCorrectionType === 'uploaded_in_error' && 'This document will be marked as uploaded in error. It will not count toward requirements but is preserved for audit.'}
              {docCorrectionType === 'supersede' && 'Mark this document as superseded by a newer version. The original is preserved for audit trail.'}
              {docCorrectionType === 'move_category' && 'Move this document to a different requirement category if it was filed incorrectly.'}
              {docCorrectionType === 'reopen_review' && 'Reopen this document for review, undoing any previous verification or rejection.'}
            </DialogDescription>
          </DialogHeader>
          
          {docCorrectionTarget && (
            <div className="space-y-4 py-4">
              <div className="p-3 bg-muted rounded-lg">
                <p className="font-medium text-sm">{docCorrectionTarget.file_label || docCorrectionTarget.original_filename || 'Document'}</p>
                {docCorrectionTarget.uploaded_at && (
                  <p className="text-xs text-muted-foreground">
                    Uploaded: {formatBackendDate(docCorrectionTarget.uploaded_at, { format: 'medium' })}
                  </p>
                )}
              </div>

              {docCorrectionType === 'move_category' && (
                <div className="space-y-2">
                  <Label>New Category *</Label>
                  <Select 
                    value={docCorrectionNewCategory} 
                    onValueChange={setDocCorrectionNewCategory}
                  >
                    <SelectTrigger className="rounded-xl">
                      <SelectValue placeholder="Select new category" />
                    </SelectTrigger>
                    <SelectContent>
                      {complianceRequirements?.requirements
                        .filter(r => r.type === 'document' && r.id !== selectedRequirementForAction)
                        .map(r => (
                          <SelectItem key={r.id} value={r.id}>
                            {r.name}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              <div className="space-y-2">
                <Label>
                  Reason for Change *
                  <span className="text-xs text-muted-foreground ml-2">
                    ({docCorrectionType === 'move_category' ? 'min 5' : 'min 10'} characters)
                  </span>
                </Label>
                <Textarea
                  placeholder="Explain why this correction is being made..."
                  value={docCorrectionReason}
                  onChange={(e) => setDocCorrectionReason(e.target.value)}
                  className="min-h-[80px] rounded-xl"
                  data-testid="doc-correction-reason"
                />
                <p className="text-xs text-muted-foreground">
                  This reason will be permanently recorded in the audit trail.
                </p>
              </div>

              {docCorrectionTarget.verified && (
                <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <p className="text-sm text-amber-700 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    This document is currently verified. This action will be flagged in the audit log.
                  </p>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setDocCorrectionDialogOpen(false)}
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmitDocCorrection}
              disabled={
                isSubmittingDocCorrection || 
                !docCorrectionReason.trim() ||
                docCorrectionReason.trim().length < (docCorrectionType === 'move_category' ? 5 : 10) ||
                (docCorrectionType === 'move_category' && !docCorrectionNewCategory)
              }
              className={`rounded-xl ${
                docCorrectionType === 'uploaded_in_error' ? 'bg-amber-600 hover:bg-amber-700' :
                docCorrectionType === 'reopen_review' ? 'bg-green-600 hover:bg-green-700' :
                'bg-primary hover:bg-primary-hover'
              }`}
              data-testid="submit-doc-correction"
            >
              {isSubmittingDocCorrection && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Document Extraction Review Modal - Phase 2: DBS, RTW, ID, POA */}
      {docExtractionReviewOpen && docExtractionDocumentId && (
        <DocumentExtractionReview
          documentId={docExtractionDocumentId}
          onClose={() => {
            setDocExtractionReviewOpen(false);
            setDocExtractionDocumentId(null);
            setDocExtractionContext(null);
          }}
          onApproved={handleDocExtractionComplete}
          documentName={docExtractionDocumentName}
          documentContext={docExtractionContext}
        />
      )}

      {/* Training Intake Wizard (Step 10) */}
      <TrainingIntakeWizard
        employeeId={employeeId}
        employeeName={employee ? `${employee.first_name} ${employee.last_name}` : ''}
        open={trainingIntakeOpen}
        onClose={() => setTrainingIntakeOpen(false)}
        onComplete={() => {
          setTrainingIntakeOpen(false);
          fetchData();
          fetchCompliance();
          fetchProposedTrainingItems();
          fetchTrainingEvaluation();
        }}
      />

      {/* Training Request Dialog (Step 10) */}
      <TrainingRequestDialog
        employeeId={employeeId}
        employeeName={employee ? `${employee.first_name} ${employee.last_name}` : ''}
        employeeEmail={employee?.email}
        open={trainingRequestOpen}
        onClose={() => setTrainingRequestOpen(false)}
        onComplete={() => {
          setTrainingRequestOpen(false);
          toast.success('Training certificate request sent');
        }}
      />

      {/* Requirement History Dialog */}
      <Dialog open={requirementHistoryOpen} onOpenChange={setRequirementHistoryOpen}>
        <DialogContent className="sm:max-w-lg max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="h-5 w-5 text-primary" />
              File History
            </DialogTitle>
            <DialogDescription>
              Complete timeline of all file operations for this requirement.
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto py-4">
            {loadingHistory ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : requirementHistory.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No history recorded yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {requirementHistory.map((entry, idx) => (
                  <div key={entry.id || idx} className="p-3 border rounded-lg">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {entry.action === 'replace_evidence' && <RefreshCw className="h-4 w-4 text-blue-500" />}
                        {entry.action === 'remove_evidence' && <Trash2 className="h-4 w-4 text-red-500" />}
                        {entry.action === 'edit_evidence' && <Edit className="h-4 w-4 text-amber-500" />}
                        {entry.action === 'upload_evidence' && <Upload className="h-4 w-4 text-green-500" />}
                        {entry.action === 'verify_evidence' && <Shield className="h-4 w-4 text-green-600" />}
                        {!['replace_evidence', 'remove_evidence', 'edit_evidence', 'upload_evidence', 'verify_evidence'].includes(entry.action) && (
                          <FileText className="h-4 w-4 text-gray-500" />
                        )}
                        <span className="font-medium text-sm capitalize">
                          {entry.action?.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {entry.timestamp ? formatBackendDateTime(entry.timestamp) : 'Unknown'}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      By: {entry.user_name || 'Unknown'}
                    </p>
                    {entry.reason && (
                      <p className="text-sm mt-2 p-2 bg-muted rounded">
                        <span className="font-medium">Reason:</span> {entry.reason}
                      </p>
                    )}
                    {entry.details && Object.keys(entry.details).length > 0 && (
                      <div className="text-xs text-muted-foreground mt-2 space-y-1">
                        {entry.details.old_filename && (
                          <p>Old file: {entry.details.old_filename}</p>
                        )}
                        {entry.details.new_filename && (
                          <p>New file: {entry.details.new_filename}</p>
                        )}
                        {entry.details.filename && (
                          <p>File: {entry.details.filename}</p>
                        )}
                        {entry.details.field && (
                          <p>Changed: {entry.details.field} from "{entry.details.old_value || 'empty'}" to "{entry.details.new_value}"</p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRequirementHistoryOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Document Preview Modal - supports multi-file navigation */}
      <DocumentPreviewModal
        isOpen={previewOpen}
        onClose={() => { setPreviewOpen(false); setPreviewFiles([]); }}
        fileUrl={previewFile?.url}
        fileName={previewFile?.name || previewFile?.filename}
        stampedFileUrl={previewFile?.stampedFileUrl}
        token={token}
        files={previewFiles}
        onDownload={previewFile ? async () => {
          try {
            const downloadUrl = previewFile.url.replace('/view', '/download');
            const response = await axios.get(downloadUrl, {
              headers: { Authorization: `Bearer ${token}` },
              responseType: 'blob'
            });
            const blob = new Blob([response.data]);
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = previewFile.filename || 'document';
            link.click();
            URL.revokeObjectURL(url);
            toast.success('Document downloaded');
          } catch (error) {
            toast.error('Failed to download');
          }
        } : undefined}
      />
      
      {/* Training Correction Dialog */}
      <Dialog open={trainingCorrectionDialogOpen} onOpenChange={setTrainingCorrectionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-heading">Edit Training Record</DialogTitle>
            <DialogDescription>
              Make a correction to this training record. All changes require a reason and are logged for audit purposes.
            </DialogDescription>
          </DialogHeader>
          {editingTrainingRecord && (
            <div className="space-y-4 mt-4">
              <div className="p-3 bg-[#F8FAFA] rounded-lg border border-[#E4E8EB]">
                <p className="font-medium text-text-primary">{editingTrainingRecord.training_name}</p>
              </div>
              
              <div className="space-y-2">
                <Label>Field to Edit</Label>
                <Select value={trainingCorrectionField} onValueChange={(value) => {
                  setTrainingCorrectionField(value);
                  setTrainingCorrectionValue(editingTrainingRecord[value]?.split?.('T')?.[0] || editingTrainingRecord[value] || '');
                }}>
                  <SelectTrigger className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="expiry_date">Expiry Date</SelectItem>
                    <SelectItem value="completion_date">Completion Date</SelectItem>
                    <SelectItem value="status">Status</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Current Value</Label>
                <Input 
                  value={editingTrainingRecord[trainingCorrectionField] || '(not set)'} 
                  disabled 
                  className="rounded-xl bg-gray-100"
                />
              </div>
              
              <div className="space-y-2">
                <Label>New Value *</Label>
                {trainingCorrectionField === 'status' ? (
                  <Select value={trainingCorrectionValue} onValueChange={setTrainingCorrectionValue}>
                    <SelectTrigger className="rounded-xl">
                      <SelectValue placeholder="Select new status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="not_started">Not Started</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="expired">Expired</SelectItem>
                      <SelectItem value="expiring">Expiring</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <Input 
                    type="date" 
                    value={trainingCorrectionValue?.split?.('T')?.[0] || trainingCorrectionValue || ''} 
                    onChange={(e) => setTrainingCorrectionValue(e.target.value)}
                    className="rounded-xl"
                  />
                )}
              </div>
              
              <div className="space-y-2">
                <Label>Reason for Change *</Label>
                <Textarea 
                  placeholder="Explain why this correction is being made (required for audit trail)"
                  value={trainingCorrectionReason}
                  onChange={(e) => setTrainingCorrectionReason(e.target.value)}
                  className="rounded-xl min-h-[80px]"
                />
              </div>
            </div>
          )}
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setTrainingCorrectionDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              onClick={handleTrainingCorrection} 
              disabled={!trainingCorrectionReason || !trainingCorrectionValue}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
            >
              Save Correction
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Training History Dialog */}
      <Dialog open={trainingHistoryDialogOpen} onOpenChange={setTrainingHistoryDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-heading">Training Record History</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 max-h-96 overflow-y-auto mt-4">
            {trainingHistory.length === 0 ? (
              <div className="text-center py-8 text-text-muted">
                <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No correction history</p>
              </div>
            ) : (
              trainingHistory.map((entry, idx) => (
                <div key={entry.id || idx} className="p-3 bg-white rounded-lg border border-[#E4E8EB]">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-text-primary">
                        {entry.action === 'training_correction' ? 'Correction' : entry.action?.replace('_', ' ')}
                      </p>
                      {entry.field_changed && (
                        <p className="text-sm text-text-muted">
                          <span className="font-medium">{entry.field_changed}</span>: {entry.old_value || '(empty)'} → {entry.new_value}
                        </p>
                      )}
                      {entry.reason && (
                        <p className="text-sm text-text-muted mt-1">
                          <span className="font-medium">Reason:</span> {entry.reason}
                        </p>
                      )}
                    </div>
                    <div className="text-right text-xs text-text-muted">
                      <p>{entry.changed_by_name || 'System'}</p>
                      <p>{entry.created_at ? formatBackendDateTime(entry.created_at) : ''}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
      
      {/* Delete Training Record Dialog */}
      <Dialog open={deleteTrainingDialogOpen} onOpenChange={setDeleteTrainingDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="h-5 w-5" />
              Delete Training Record
            </DialogTitle>
            <DialogDescription>
              This will permanently remove this training record. An audit trail will be kept.
            </DialogDescription>
          </DialogHeader>
          {deletingTrainingRecord && (
            <div className="space-y-4 py-4">
              <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                <p className="font-medium text-red-800">{deletingTrainingRecord.training_name}</p>
                <p className="text-sm text-red-600 mt-1">
                  Status: {deletingTrainingRecord.status?.replace('_', ' ')}
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="delete-training-reason">Reason for deletion (optional)</Label>
                <Textarea
                  id="delete-training-reason"
                  placeholder="Enter an optional reason for deleting this record"
                  value={deleteTrainingReason}
                  onChange={(e) => setDeleteTrainingReason(e.target.value)}
                  className="min-h-[80px] rounded-xl"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTrainingDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleDeleteTrainingRecord}
              disabled={isDeletingTraining}
              className="rounded-xl"
            >
              {isDeletingTraining ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Delete Record
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Acknowledgement Dialog - For Contract/Handbook acknowledgements */}
      <Dialog open={acknowledgementDialogOpen} onOpenChange={(open) => {
        setAcknowledgementDialogOpen(open);
        if (!open) {
          setAcknowledgementConfirmed(false);
          setAcknowledgingRequirement(null);
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-5 w-5" />
              Confirm & Complete
            </DialogTitle>
            <DialogDescription>
              Please confirm that this employee has received and understood the document.
            </DialogDescription>
          </DialogHeader>
          {acknowledgingRequirement && (
            <div className="space-y-4 py-4">
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <p className="font-semibold text-green-800">{acknowledgingRequirement.name}</p>
                <p className="text-sm text-green-600 mt-2">
                  {acknowledgingRequirement.description}
                </p>
              </div>
              
              <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border">
                <Checkbox 
                  id="acknowledgement-confirm"
                  checked={acknowledgementConfirmed}
                  onCheckedChange={setAcknowledgementConfirmed}
                  className="mt-0.5"
                  data-testid="acknowledgement-checkbox"
                />
                <label htmlFor="acknowledgement-confirm" className="text-sm cursor-pointer">
                  {acknowledgingRequirement.acknowledgement_text || 
                    `I confirm that this employee has received, read, and understood the ${acknowledgingRequirement.name.replace(' Acknowledgement', '')}.`}
                </label>
              </div>
              
              <p className="text-xs text-text-muted">
                This acknowledgement will be logged with your name and timestamp for audit purposes.
              </p>
            </div>
          )}
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setAcknowledgementDialogOpen(false)} 
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleAcknowledgeRequirement}
              disabled={!acknowledgementConfirmed || isAcknowledging}
              className="rounded-xl bg-green-600 hover:bg-green-700"
              data-testid="submit-acknowledgement-btn"
            >
              {isAcknowledging ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <CheckCircle className="h-4 w-4 mr-2" />
              )}
              Confirm & Complete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Form Submission Modal - Structured forms with sections */}
      <Dialog open={formModalOpen} onOpenChange={(open) => {
        setFormModalOpen(open);
        if (!open) {
          setFormTemplate(null);
          setFormData({});
        }
      }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {/* Branded Header for Staff Health Questionnaire */}
          {formTemplate?.branding?.show_logo && (
            <div className="bg-[#2E7D32] text-white p-4 -m-6 mb-4 rounded-t-lg">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center">
                  <span className="text-[#2E7D32] font-bold text-xl">O</span>
                </div>
                <div>
                  <h2 className="text-lg font-bold">{formTemplate?.branding?.company_name || 'Osabea Healthcare Solutions Ltd'}</h2>
                  <p className="text-sm opacity-90">{formTemplate?.name}</p>
                </div>
              </div>
            </div>
          )}
          
          <DialogHeader className={formTemplate?.branding?.show_logo ? 'pt-0' : ''}>
            {!formTemplate?.branding?.show_logo && (
              <DialogTitle className="font-heading flex items-center gap-2">
                <ClipboardCheck className="h-5 w-5 text-primary" />
                {formTemplate?.name || 'Complete Form'}
              </DialogTitle>
            )}
            {formTemplate?.description && (
              <DialogDescription className="text-sm text-text-muted">
                {formTemplate.description}
              </DialogDescription>
            )}
          </DialogHeader>
          
          {formTemplate && (
            <div className="space-y-6 mt-4">
              {/* Optional form notice */}
              {formTemplate.is_optional && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl">
                  <p className="text-sm text-blue-700 flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs font-medium rounded">Optional</span>
                    This form does not affect compliance percentage or work readiness status.
                  </p>
                </div>
              )}
              
              {/* Auto-fill notice */}
              {formTemplate.auto_fill_fields?.length > 0 && Object.keys(formData).length > 0 && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-xl">
                  <p className="text-sm text-green-700 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" />
                    Some fields have been pre-filled from the employee profile. Please review and update as needed.
                  </p>
                </div>
              )}
              
              {/* Profile update notice */}
              {formTemplate.updates_profile && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl">
                  <p className="text-sm text-amber-700 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    This form can update the employee's profile data when submitted.
                  </p>
                </div>
              )}
              
              {/* Render sections if available, otherwise fallback to flat fields */}
              {formTemplate.sections?.length > 0 ? (
                <div className="space-y-6">
                  {formTemplate.sections.map((section) => {
                    // Skip admin-only sections for non-admins
                    if (section.admin_only && !isAdmin()) return null;
                    
                    // Use green header style if form has branding
                    const sectionHeaderClass = formTemplate?.branding?.header_color 
                      ? 'bg-[#2E7D32] text-white px-4 py-3 border-b border-[#2E7D32]'
                      : 'bg-gray-50 px-4 py-3 border-b border-gray-200';
                    
                    return (
                      <div key={section.id} className="border border-gray-200 rounded-xl overflow-hidden">
                        <div className={sectionHeaderClass}>
                          <h4 className={`font-medium ${formTemplate?.branding?.header_color ? 'text-white' : 'text-text-primary'}`}>
                            {section.title}
                          </h4>
                          {section.description && (
                            <p className={`text-xs mt-0.5 ${formTemplate?.branding?.header_color ? 'text-white/80' : 'text-text-muted'}`}>
                              {section.description}
                            </p>
                          )}
                        </div>
                        <div className="p-4 space-y-4">
                          {section.fields.map((field) => {
                            // Handle conditional fields
                            if (field.conditional_on) {
                              const conditionValue = formData[field.conditional_on];
                              if (conditionValue !== field.conditional_value) {
                                return null;
                              }
                            }
                            
                            return (
                              <div key={field.id} className="space-y-1.5">
                                {field.type === 'info' ? (
                                  <p className="text-sm text-text-muted italic bg-[#F8FAFA] p-3 rounded-lg">
                                    {field.label}
                                  </p>
                                ) : (
                                  <>
                                    <Label className="text-sm font-medium flex items-center gap-2">
                                      {field.label}
                                      {field.required && <span className="text-error">*</span>}
                                      {field.auto_fill && formData[field.id] && (
                                        <span className="text-xs text-green-600 font-normal">(auto-filled)</span>
                                      )}
                                    </Label>
                                    
                                    {field.type === 'text' && (
                                      <Input
                                        value={formData[field.id] || ''}
                                        onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                                        placeholder={field.placeholder || ''}
                                        className="rounded-xl"
                                      />
                                    )}
                                    
                                    {field.type === 'number' && (
                                      <Input
                                        type="number"
                                        value={formData[field.id] || ''}
                                        onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                                        placeholder={field.placeholder || ''}
                                        className="rounded-xl"
                                      />
                                    )}
                                    
                                    {field.type === 'textarea' && (
                                      <Textarea
                                        value={formData[field.id] || ''}
                                        onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                                        placeholder={field.placeholder || ''}
                                        className="rounded-xl"
                                        rows={3}
                                      />
                                    )}
                                    
                                    {field.type === 'date' && (
                                      <Input
                                        type="date"
                                        value={formData[field.id] || ''}
                                        onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                                        className="rounded-xl"
                                      />
                                    )}
                                    
                                    {field.type === 'checkbox' && (
                                      <div className="flex items-center gap-2">
                                        <Checkbox
                                          id={field.id}
                                          checked={formData[field.id] || false}
                                          onCheckedChange={(checked) => setFormData({...formData, [field.id]: checked})}
                                        />
                                        <label htmlFor={field.id} className="text-sm cursor-pointer">Yes</label>
                                      </div>
                                    )}
                                    
                                    {field.type === 'select' && (
                                      <Select 
                                        value={formData[field.id] || ''} 
                                        onValueChange={(v) => setFormData({...formData, [field.id]: v})}
                                      >
                                        <SelectTrigger className="rounded-xl">
                                          <SelectValue placeholder="Select..." />
                                        </SelectTrigger>
                                        <SelectContent>
                                          {field.options?.map((opt) => (
                                            <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                                          ))}
                                        </SelectContent>
                                      </Select>
                                    )}
                                    
                                    {field.type === 'multi_select' && (
                                      <div className="flex flex-wrap gap-2">
                                        {field.options?.map((opt) => (
                                          <label key={opt} className="flex items-center gap-1.5 text-sm">
                                            <Checkbox
                                              checked={(formData[field.id] || []).includes(opt)}
                                              onCheckedChange={(checked) => {
                                                const current = formData[field.id] || [];
                                                if (checked) {
                                                  setFormData({...formData, [field.id]: [...current, opt]});
                                                } else {
                                                  setFormData({...formData, [field.id]: current.filter(v => v !== opt)});
                                                }
                                              }}
                                            />
                                            {opt}
                                          </label>
                                        ))}
                                      </div>
                                    )}
                                  </>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                /* Fallback to flat fields for backward compatibility */
                <div className="grid gap-4">
                  {formTemplate.fields?.map((field) => (
                    <div key={field.id} className="space-y-1.5">
                      {field.type === 'info' ? (
                        <p className="text-sm text-text-muted italic bg-[#F8FAFA] p-3 rounded-lg">
                          {field.label}
                        </p>
                      ) : (
                        <>
                          <Label className="text-sm font-medium">
                            {field.label}
                            {field.required && <span className="text-error ml-1">*</span>}
                          </Label>
                          
                          {field.type === 'text' && (
                            <Input
                              value={formData[field.id] || ''}
                              onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                              placeholder={field.placeholder || ''}
                              className="rounded-xl"
                            />
                          )}
                          
                          {field.type === 'textarea' && (
                            <Textarea
                              value={formData[field.id] || ''}
                              onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                              placeholder={field.placeholder || ''}
                              className="rounded-xl"
                              rows={3}
                            />
                          )}
                          
                          {field.type === 'date' && (
                            <Input
                              type="date"
                              value={formData[field.id] || ''}
                              onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                              className="rounded-xl"
                            />
                          )}
                          
                          {field.type === 'checkbox' && (
                            <div className="flex items-center gap-2">
                              <Checkbox
                                id={field.id}
                                checked={formData[field.id] || false}
                                onCheckedChange={(checked) => setFormData({...formData, [field.id]: checked})}
                              />
                              <label htmlFor={field.id} className="text-sm cursor-pointer">Yes</label>
                            </div>
                          )}
                          
                          {field.type === 'select' && (
                            <Select 
                              value={formData[field.id] || ''} 
                              onValueChange={(v) => setFormData({...formData, [field.id]: v})}
                            >
                              <SelectTrigger className="rounded-xl">
                                <SelectValue placeholder="Select..." />
                              </SelectTrigger>
                              <SelectContent>
                                {field.options?.map((opt) => (
                                  <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
              
              <DialogFooter className="pt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setFormModalOpen(false)} 
                  className="rounded-xl"
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleFormSubmit}
                  disabled={isSubmittingForm}
                  className="rounded-xl bg-primary hover:bg-primary/90"
                  data-testid="submit-form-btn"
                >
                  {isSubmittingForm ? (
                    <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Submitting...</>
                  ) : (
                    'Submit Form'
                  )}
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* View Form Modal - Display submitted form data */}
      <Dialog open={viewFormOpen} onOpenChange={setViewFormOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <ClipboardCheck className="h-5 w-5 text-primary" />
              {viewFormData?.requirementName || 'Form Submission'}
            </DialogTitle>
          </DialogHeader>
          
          {viewFormData && (
            <div className="space-y-4 mt-4">
              {/* Status badges */}
              <div className="flex items-center gap-3 p-3 bg-[#F8FAFA] rounded-xl">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    viewFormData.verified 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-blue-100 text-blue-700'
                  }`}>
                    {viewFormData.verified ? 'Verified' : 'Submitted'}
                  </span>
                </div>
                <div className="text-xs text-text-muted">
                  Submitted: {viewFormData.submitted_at ? formatBackendDateTime(viewFormData.submitted_at) : 'Unknown'}
                </div>
                {viewFormData.submitted_by_name && (
                  <div className="text-xs text-text-muted">
                    By: {viewFormData.submitted_by_name}
                  </div>
                )}
              </div>
              
              {/* Form data display */}
              <div className="space-y-3">
                {Object.entries(viewFormData.data || {}).map(([key, value]) => (
                  <div key={key} className="flex items-start gap-3 p-2 border-b border-[#E4E8EB]">
                    <span className="text-sm font-medium text-text-primary min-w-[180px] capitalize">
                      {key.replace(/_/g, ' ')}:
                    </span>
                    <span className="text-sm text-text-muted flex-1">
                      {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : (value || '-')}
                    </span>
                  </div>
                ))}
              </div>
              
              {/* Verification info if verified */}
              {viewFormData.verified && viewFormData.verified_by_name && (
                <div className="p-3 bg-green-50 rounded-xl border border-green-200">
                  <p className="text-sm text-green-700">
                    <CheckCircle className="h-4 w-4 inline mr-2" />
                    Verified by {viewFormData.verified_by_name} on {formatBackendDateTime(viewFormData.verified_at)}
                  </p>
                </div>
              )}
              
              <DialogFooter className="pt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setViewFormOpen(false)} 
                  className="rounded-xl"
                >
                  Close
                </Button>
                {!viewFormData.verified && isAdmin() && (
                  <Button 
                    onClick={() => handleVerifyFormSubmission(viewFormData.id)}
                    className="rounded-xl bg-green-600 hover:bg-green-700"
                    data-testid="verify-form-btn"
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Verify Form
                  </Button>
                )}
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
      
      {/* Extraction Review Dialog */}
      <Dialog open={extractionDialogOpen} onOpenChange={(open) => {
        if (!open && !isApplyingExtraction) {
          handleDiscardExtraction();
        }
      }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              {extractionFailed ? 'Extraction Options' : 'Review Extracted Data'}
            </DialogTitle>
            <DialogDescription>
              {extractionFailed ? (
                extractionFailed.message
              ) : (
                <>
                  Review the extracted values below. Select which fields to apply to the employee profile.
                  <span className="block mt-2 text-amber-600 font-medium">
                    Note: This updates profile data only. Compliance evidence requirements remain unchanged.
                  </span>
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          
          {isExtracting ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
              <p className="text-text-muted">Extracting data from application form...</p>
              <p className="text-xs text-text-muted mt-1">This may take a few seconds</p>
            </div>
          ) : extractionFailed ? (
            /* Extraction Failed - Show Options */
            <div className="space-y-4">
              {/* Friendly Message */}
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-amber-800">
                    <p className="font-medium mb-1">Don't worry - you can still proceed!</p>
                    <p>Automatic extraction didn't work for this document, but you have options to continue.</p>
                    {extractionFailed.extraction_log && (
                      <p className="text-xs mt-2 text-amber-600">
                        Details: {extractionFailed.extraction_log.file_type} ({Math.round((extractionFailed.extraction_log.file_size_bytes || 0) / 1024)} KB)
                        {extractionFailed.extraction_log.failure_reason && (
                          <span className="block">Reason: {extractionFailed.extraction_log.failure_reason}</span>
                        )}
                      </p>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Options Buttons */}
              <div className="space-y-3">
                {extractionFailed.options?.map((option) => (
                  <button
                    key={option.action}
                    onClick={() => handleExtractionOption(option.action)}
                    className="w-full flex items-center gap-4 p-4 border rounded-lg hover:bg-gray-50 transition-colors text-left"
                    data-testid={`extraction-option-${option.action}`}
                  >
                    <div className="flex-shrink-0">
                      {option.action === 'fill_manually' && (
                        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                          <Edit className="h-5 w-5 text-blue-600" />
                        </div>
                      )}
                      {option.action === 'view_document' && (
                        <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                          <Eye className="h-5 w-5 text-purple-600" />
                        </div>
                      )}
                      {option.action === 'retry' && (
                        <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                          <RefreshCw className="h-5 w-5 text-green-600" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-text-primary">{option.label}</p>
                      <p className="text-sm text-text-muted">{option.description}</p>
                    </div>
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </button>
                ))}
              </div>
              
              <DialogFooter className="pt-4">
                <Button
                  variant="outline"
                  onClick={handleDiscardExtraction}
                  data-testid="close-extraction-dialog"
                >
                  Close
                </Button>
              </DialogFooter>
            </div>
          ) : extractionResult ? (
            <div className="space-y-4">
              {/* Extraction Method & Low Confidence Warning */}
              {extractionResult.low_confidence_fields?.length > 0 && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-red-800">
                      <p className="font-medium">Low Confidence Fields Detected</p>
                      <p>Please review highlighted fields carefully: {extractionResult.low_confidence_fields.map(f => FIELD_LABELS[f] || f).join(', ')}</p>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Extraction Method Badge */}
              {extractionResult.extraction_method && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-text-muted">Extraction method:</span>
                  <span className={`px-2 py-0.5 rounded font-medium ${
                    extractionResult.extraction_method === 'ai' ? 'bg-blue-100 text-blue-700' :
                    extractionResult.extraction_method === 'ai+ocr' ? 'bg-purple-100 text-purple-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {extractionResult.extraction_method === 'ai' ? 'AI Vision' :
                     extractionResult.extraction_method === 'ai+ocr' ? 'AI + OCR' :
                     extractionResult.extraction_method === 'ocr' ? 'OCR' : extractionResult.extraction_method}
                  </span>
                </div>
              )}
              
              {/* Compliance Note */}
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-amber-800">
                    <p className="font-medium">Profile Data Only</p>
                    <p>Extracted values will populate profile fields (e.g., NI Number field). They do NOT complete compliance requirements (e.g., "Proof of NI Number" still needs evidence upload).</p>
                  </div>
                </div>
              </div>
              
              {/* Fields Table */}
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-3 font-medium">Apply</th>
                      <th className="text-left p-3 font-medium">Field</th>
                      <th className="text-left p-3 font-medium">Extracted Value</th>
                      <th className="text-left p-3 font-medium">Current Value</th>
                      <th className="text-left p-3 font-medium">Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {extractionResult.fields.map((field, idx) => {
                      // Handle both numeric confidence and string confidence_label
                      const confidenceScore = typeof field.confidence === 'number' ? field.confidence : null;
                      const confidenceLabel = field.confidence_label || 
                        (typeof field.confidence === 'string' ? field.confidence : 
                         confidenceScore >= 0.8 ? 'high' : confidenceScore >= 0.5 ? 'medium' : 'low');
                      const isLowConfidence = confidenceLabel === 'low' || (confidenceScore !== null && confidenceScore < 0.5);
                      
                      return (
                        <tr 
                          key={field.field_name} 
                          className={`${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'} ${isLowConfidence ? 'bg-red-50/50' : ''}`}
                        >
                          <td className="p-3">
                            <input
                              type="checkbox"
                              checked={fieldsToApply[field.field_name] || false}
                              onChange={() => toggleFieldToApply(field.field_name)}
                              className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                              data-testid={`apply-field-${field.field_name}`}
                            />
                          </td>
                          <td className="p-3 font-medium text-text-primary">
                            {FIELD_LABELS[field.field_name] || field.field_name}
                            {isLowConfidence && (
                              <span className="ml-2 text-red-500" title="Low confidence - please verify">⚠</span>
                            )}
                          </td>
                          <td className="p-3">
                            <span className={`${field.extracted_value ? 'text-text-primary' : 'text-text-muted italic'} ${isLowConfidence ? 'text-red-700' : ''}`}>
                              {field.extracted_value || 'Not found'}
                            </span>
                          </td>
                          <td className="p-3">
                            <span className={`${field.current_value ? 'text-text-primary' : 'text-text-muted italic'}`}>
                              {field.current_value || 'Empty'}
                            </span>
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-1">
                              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                confidenceLabel === 'high' ? 'bg-green-100 text-green-700' :
                                confidenceLabel === 'medium' ? 'bg-amber-100 text-amber-700' :
                                'bg-red-100 text-red-700'
                              }`}>
                                {confidenceLabel}
                              </span>
                              {confidenceScore !== null && (
                                <span className="text-xs text-text-muted">
                                  {Math.round(confidenceScore * 100)}%
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              
              {/* Quick Actions */}
              <div className="flex gap-2 text-xs">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const allSelected = {};
                    extractionResult.fields.forEach(f => { allSelected[f.field_name] = true; });
                    setFieldsToApply(allSelected);
                  }}
                >
                  Select All
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const emptyOnly = {};
                    extractionResult.fields.forEach(f => {
                      emptyOnly[f.field_name] = !f.current_value && !!f.extracted_value;
                    });
                    setFieldsToApply(emptyOnly);
                  }}
                >
                  Select Empty Only
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setFieldsToApply({})}
                >
                  Clear All
                </Button>
              </div>
              
              <DialogFooter className="pt-4">
                <Button
                  variant="outline"
                  onClick={handleDiscardExtraction}
                  disabled={isApplyingExtraction}
                >
                  Discard
                </Button>
                <Button
                  onClick={handleApplyExtraction}
                  disabled={isApplyingExtraction || Object.values(fieldsToApply).filter(Boolean).length === 0}
                  data-testid="apply-extraction-btn"
                >
                  {isApplyingExtraction ? (
                    <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Applying...</>
                  ) : (
                    <>Apply {Object.values(fieldsToApply).filter(Boolean).length} Field(s)</>
                  )}
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <div className="text-center py-8 text-text-muted">
              <p>No extraction data available.</p>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Verify Reference Dialog */}
      <Dialog open={verifyRefDialogOpen} onOpenChange={setVerifyRefDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Verify Reference {selectedRefNum}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-700">
                <strong>Reference Integrity Rule:</strong> References must match the applicant's CV, 
                or you must document why they differ.
              </p>
            </div>
            
            <div className="space-y-3">
              <label className="block text-sm font-medium">Does this reference match the CV?</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="fromCv" 
                    checked={refFromCv === true}
                    onChange={() => setRefFromCv(true)}
                    className="h-4 w-4 text-primary"
                  />
                  <span>Yes, matches CV</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="fromCv" 
                    checked={refFromCv === false}
                    onChange={() => setRefFromCv(false)}
                    className="h-4 w-4 text-primary"
                  />
                  <span>No, different from CV</span>
                </label>
              </div>
            </div>
            
            {refFromCv === false && (
              <div className="space-y-2">
                <label className="block text-sm font-medium text-red-700">
                  ⚠️ Justification Required
                </label>
                <Textarea
                  value={refOverrideReason}
                  onChange={(e) => setRefOverrideReason(e.target.value)}
                  placeholder="Explain why this reference differs from the CV (min 10 characters)..."
                  className="min-h-[100px] rounded-xl"
                />
                <p className="text-xs text-text-muted">
                  {refOverrideReason.length}/10 characters minimum
                </p>
              </div>
            )}
          </div>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setVerifyRefDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              onClick={handleVerifyReference}
              disabled={isVerifyingRef || (!refFromCv && refOverrideReason.length < 10)}
              className="rounded-xl bg-primary hover:bg-primary-hover"
            >
              {isVerifyingRef ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Verify Reference
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Explain CV Gap Dialog */}
      <Dialog open={explainGapDialogOpen} onOpenChange={setExplainGapDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Briefcase className="h-5 w-5 text-purple-600" />
              Explain Employment Gap
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            {selectedGap && (
              <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                <p className="text-sm font-medium text-amber-700">Gap Duration: {selectedGap.gap_duration_days} days</p>
                <p className="text-sm text-amber-600 mt-1">
                  From: {selectedGap.previous_job?.company} ({selectedGap.gap_start})
                </p>
                <p className="text-sm text-amber-600">
                  To: {selectedGap.next_job?.company} ({selectedGap.gap_end})
                </p>
              </div>
            )}
            
            <div className="space-y-2">
              <label className="block text-sm font-medium">
                Explanation for this gap <span className="text-red-500">*</span>
              </label>
              <Textarea
                value={gapExplanation}
                onChange={(e) => setGapExplanation(e.target.value)}
                placeholder="E.g., Career break for family care, further education, travel, etc. (min 10 characters)..."
                className="min-h-[120px] rounded-xl"
              />
              <p className="text-xs text-text-muted">
                {gapExplanation.length}/10 characters minimum
              </p>
            </div>
          </div>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setExplainGapDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              onClick={handleExplainGap}
              disabled={isExplainingGap || gapExplanation.length < 10}
              className="rounded-xl bg-purple-600 hover:bg-purple-700"
            >
              {isExplainingGap ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Save Explanation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Document Request Dialog */}
      <Dialog open={requestDocDialogOpen} onOpenChange={(open) => {
        setRequestDocDialogOpen(open);
        if (!open) {
          setDuplicateBlockedInfo(null);
          setIsResendMode(false);
        }
      }}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <Send className="h-5 w-5 text-blue-600" />
              {isResendMode ? 'Resend Document Request' : 'Request Document'}
            </DialogTitle>
            <DialogDescription>
              Send an email request to {employee?.first_name} for {requestingRequirement?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            {/* Duplicate blocked warning */}
            {duplicateBlockedInfo && (
              <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-amber-800">Active Request Exists</p>
                    <p className="text-sm text-amber-700 mt-1">
                      {duplicateBlockedInfo.message}
                    </p>
                    <p className="text-xs text-amber-600 mt-2">
                      Click "Resend" to supersede the previous request and send a new email.
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {!duplicateBlockedInfo && (
              <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                <p className="text-sm text-blue-800">
                  An email will be sent to <strong>{employee?.email}</strong> requesting them to upload this document.
                  {isResendMode && <span className="block mt-1 text-blue-600">This will supersede any previous active request.</span>}
                </p>
              </div>
            )}
            
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Additional Message (Optional)</Label>
              <Textarea
                value={requestDocMessage}
                onChange={(e) => setRequestDocMessage(e.target.value)}
                placeholder="Add any specific instructions or notes..."
                rows={3}
                className="bg-white border-[#E4E8EB]"
              />
            </div>
          </div>
          <DialogFooter className="flex gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => {
                setRequestDocDialogOpen(false);
                setDuplicateBlockedInfo(null);
                setIsResendMode(false);
              }}
              className="border-[#E4E8EB]"
            >
              Cancel
            </Button>
            
            {duplicateBlockedInfo ? (
              <Button 
                onClick={handleResendRequest}
                disabled={isRequestingDoc}
                className="bg-amber-600 hover:bg-amber-700 text-white"
                data-testid="resend-request-btn"
              >
                {isRequestingDoc ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                Resend Request
              </Button>
            ) : (
              <Button 
                onClick={() => handleRequestDocument(isResendMode)}
                disabled={isRequestingDoc}
                className="bg-blue-600 hover:bg-blue-700 text-white"
                data-testid="send-request-btn"
              >
                {isRequestingDoc ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Send className="h-4 w-4 mr-2" />
                )}
                {isResendMode ? 'Resend Request' : 'Send Request'}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Send Form Dialog */}
      <Dialog open={sendFormDialogOpen} onOpenChange={setSendFormDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <FileText className="h-5 w-5 text-primary" />
              Send Form to Employee
            </DialogTitle>
            <DialogDescription>
              Send a form request to {employee?.first_name} via email. They can complete it without logging in.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
              <p className="text-sm text-blue-800">
                An email will be sent to <strong>{employee?.email}</strong> with a secure link to complete the form.
              </p>
            </div>
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Form Type</Label>
              <Select value={selectedFormType} onValueChange={setSelectedFormType}>
                <SelectTrigger className="bg-white border-[#E4E8EB]">
                  <SelectValue placeholder="Select form to send..." />
                </SelectTrigger>
                <SelectContent>
                  {FORM_OPTIONS.map((form) => (
                    <SelectItem key={form.value} value={form.value}>{form.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Additional Message (Optional)</Label>
              <Textarea
                value={sendFormMessage}
                onChange={(e) => setSendFormMessage(e.target.value)}
                placeholder="Add any specific instructions or context..."
                rows={3}
                className="bg-white border-[#E4E8EB]"
              />
            </div>
          </div>
          <DialogFooter className="flex gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => setSendFormDialogOpen(false)}
              className="border-[#E4E8EB]"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSendForm}
              disabled={isSendingForm || !selectedFormType}
              className="bg-primary hover:bg-primary-hover text-white"
              data-testid="send-form-btn"
            >
              {isSendingForm ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Send Form
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reference Request Dialog (NHS-Level Workflow Step 1) */}
      <Dialog open={requestReferenceDialogOpen} onOpenChange={setRequestReferenceDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <Mail className="h-5 w-5 text-primary" />
              Request Reference from Referee
            </DialogTitle>
            <DialogDescription>
              Send a reference request email directly to the referee. They can complete a secure form without logging in.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            {selectedRefForRequest && (
              <>
                <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                  <p className="text-sm text-blue-800 mb-2">
                    <strong>Referee Details (from application):</strong>
                  </p>
                  <div className="text-sm text-blue-700 space-y-1">
                    <p><strong>Name:</strong> {selectedRefForRequest.declared?.name || 'Not provided'}</p>
                    <p><strong>Email:</strong> {selectedRefForRequest.declared?.email || 'Not provided'}</p>
                    <p><strong>Company:</strong> {selectedRefForRequest.declared?.company || 'Not provided'}</p>
                  </div>
                </div>
                {!selectedRefForRequest.declared?.email && (
                  <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                    <p className="text-sm text-red-800 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" />
                      Referee email is required. Please update the employee profile first.
                    </p>
                  </div>
                )}
              </>
            )}
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Additional Message (Optional)</Label>
              <Textarea
                value={referenceRequestMessage}
                onChange={(e) => setReferenceRequestMessage(e.target.value)}
                placeholder="Add any specific instructions or context for the referee..."
                rows={3}
                className="bg-white border-[#E4E8EB]"
              />
            </div>
          </div>
          <DialogFooter className="flex gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => setRequestReferenceDialogOpen(false)}
              className="border-[#E4E8EB]"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSendReferenceRequest}
              disabled={isRequestingReference || !selectedRefForRequest?.declared?.email}
              className="bg-primary hover:bg-primary-hover text-white"
              data-testid="send-reference-request-btn"
            >
              {isRequestingReference ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Send Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Review Reference Dialog (NHS-Level Workflow Step 2) */}
      <Dialog open={reviewReferenceDialogOpen} onOpenChange={setReviewReferenceDialogOpen}>
        <DialogContent className="sm:max-w-2xl bg-white max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <ClipboardCheck className="h-5 w-5 text-primary" />
              Review Reference {selectedRefForReview?.reference_num}
            </DialogTitle>
            <DialogDescription>
              Compare declared details with returned response. Document any mismatches before verification.
            </DialogDescription>
          </DialogHeader>
          {selectedRefForReview && (
            <div className="space-y-4 mt-4">
              {/* Mismatch Warning */}
              {selectedRefForReview.mismatch_detected && (
                <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <p className="text-sm text-amber-800 flex items-center gap-2 font-medium">
                    <AlertTriangle className="h-4 w-4" />
                    Mismatch Detected - Details in returned response differ from application
                  </p>
                </div>
              )}
              
              {/* Side-by-side comparison */}
              <div className="grid grid-cols-2 gap-4">
                {/* Declared (From Application) */}
                <div className="space-y-2">
                  <h4 className="font-medium text-gray-900 text-sm border-b pb-1">Declared (Application)</h4>
                  <div className="text-sm space-y-1.5">
                    <p><span className="text-gray-500">Name:</span> {selectedRefForReview.declared?.name || '-'}</p>
                    <p><span className="text-gray-500">Company:</span> {selectedRefForReview.declared?.company || '-'}</p>
                    <p><span className="text-gray-500">Email:</span> {selectedRefForReview.declared?.email || '-'}</p>
                    <p><span className="text-gray-500">Phone:</span> {selectedRefForReview.declared?.phone || '-'}</p>
                    <p><span className="text-gray-500">Job Title:</span> {selectedRefForReview.declared?.job_title || '-'}</p>
                    <p><span className="text-gray-500">Relationship:</span> {selectedRefForReview.declared?.relationship || '-'}</p>
                  </div>
                </div>
                
                {/* Returned (From Referee) */}
                <div className="space-y-2">
                  <h4 className="font-medium text-gray-900 text-sm border-b pb-1">Returned (Referee Response)</h4>
                  <div className="text-sm space-y-1.5">
                    <p className={selectedRefForReview.mismatch_detected && selectedRefForReview.declared?.name?.toLowerCase() !== selectedRefForReview.returned?.name?.toLowerCase() ? 'text-amber-600 font-medium' : ''}>
                      <span className="text-gray-500">Name:</span> {selectedRefForReview.returned?.name || '-'}
                    </p>
                    <p className={selectedRefForReview.mismatch_detected && selectedRefForReview.declared?.company?.toLowerCase() !== selectedRefForReview.returned?.company?.toLowerCase() ? 'text-amber-600 font-medium' : ''}>
                      <span className="text-gray-500">Company:</span> {selectedRefForReview.returned?.company || '-'}
                    </p>
                    <p><span className="text-gray-500">Email:</span> {selectedRefForReview.returned?.email || '-'}</p>
                    <p><span className="text-gray-500">Phone:</span> {selectedRefForReview.returned?.phone || '-'}</p>
                    <p><span className="text-gray-500">Job Title:</span> {selectedRefForReview.returned?.job_title || '-'}</p>
                    <p><span className="text-gray-500">Relationship:</span> {selectedRefForReview.returned?.relationship || '-'}</p>
                  </div>
                </div>
              </div>
              
              {/* Full Response Summary */}
              {selectedRefForReview.response_data && (
                <div className="space-y-2 mt-4 pt-4 border-t">
                  <h4 className="font-medium text-gray-900 text-sm">Reference Assessment Summary</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <p><span className="text-gray-500">Performance:</span> {selectedRefForReview.response_data.performance_rating || '-'}</p>
                    <p><span className="text-gray-500">Reliability:</span> {selectedRefForReview.response_data.reliability || '-'}</p>
                    <p><span className="text-gray-500">Professionalism:</span> {selectedRefForReview.response_data.professionalism || '-'}</p>
                    <p><span className="text-gray-500">Care Suitable:</span> {selectedRefForReview.response_data.care_vulnerable_suitable || '-'}</p>
                    <p><span className="text-gray-500">Would Re-employ:</span> {selectedRefForReview.response_data.would_re_employ || '-'}</p>
                    <p><span className="text-gray-500">Safeguarding:</span> {selectedRefForReview.response_data.safeguarding_concerns || '-'}</p>
                  </div>
                </div>
              )}
              
              {/* Mismatch Notes (Required if mismatch detected) */}
              {selectedRefForReview.mismatch_detected && (
                <div className="space-y-2 mt-4 pt-4 border-t">
                  <Label className="text-gray-700 font-medium flex items-center gap-1">
                    Mismatch Explanation <span className="text-red-500">*</span>
                  </Label>
                  <p className="text-xs text-gray-500">
                    Document the discrepancy and explain why it is acceptable for verification.
                  </p>
                  <Textarea
                    value={reviewMismatchNotes}
                    onChange={(e) => setReviewMismatchNotes(e.target.value)}
                    placeholder="Explain the mismatch (e.g., 'Name variation is maiden name vs married name, confirmed via phone call with referee on [date]')"
                    rows={3}
                    className="bg-white border-[#E4E8EB]"
                    required
                  />
                </div>
              )}
            </div>
          )}
          <DialogFooter className="flex gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => setReviewReferenceDialogOpen(false)}
              className="border-[#E4E8EB]"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleReviewReference}
              disabled={isReviewingReference || (selectedRefForReview?.mismatch_detected && reviewMismatchNotes.length < 10)}
              className="bg-amber-600 hover:bg-amber-700 text-white"
              data-testid="review-reference-btn"
            >
              {isReviewingReference ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4 mr-2" />
              )}
              Mark as Reviewed
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Employment History Mismatch Details Dialog */}
      <Dialog open={mismatchDialogOpen} onOpenChange={(v) => { setMismatchDialogOpen(v); if (!v) { setSelectedCvRolesForApply({}); setReconcileReason(''); } }}>
        <DialogContent className="sm:max-w-4xl bg-white max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
              Employment History vs CV Comparison
            </DialogTitle>
            <DialogDescription>
              Review inconsistencies between structured employment history and CV. Structured history is the source of truth for compliance.
            </DialogDescription>
          </DialogHeader>
          
          {employmentMismatch && (
            <div className="space-y-6 mt-4">
              {/* Summary */}
              <div className="p-3 bg-amber-50 rounded-lg border border-amber-100">
                <p className="text-sm text-amber-800">
                  <strong>{employmentMismatch.mismatch_count}</strong> inconsistencies detected | 
                  <span className="ml-2">Structured roles: {employmentMismatch.structured_history?.length || 0}</span> | 
                  <span className="ml-2">CV roles: {employmentMismatch.cv_extracted_roles?.length || 0}</span>
                </p>
                {employmentMismatch.compared_at && (
                  <p className="text-xs text-amber-600 mt-1">
                    Last compared: {new Date(employmentMismatch.compared_at).toLocaleString()}
                  </p>
                )}
              </div>
              
              {/* Mismatch List */}
              <div className="space-y-3">
                <h4 className="font-medium text-gray-900">Detected Mismatches</h4>
                {employmentMismatch.mismatch_summary?.map((mismatch, idx) => (
                  <div key={idx} className={`p-3 rounded-lg border ${
                    mismatch.severity === 'critical' ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200'
                  }`}>
                    <p className={`text-sm font-medium ${
                      mismatch.severity === 'critical' ? 'text-red-800' : 'text-amber-800'
                    }`}>
                      {mismatch.type === 'missing_in_structured' && '⚠️ Role in CV not in structured history'}
                      {mismatch.type === 'missing_in_cv' && '⚠️ Role in structured history not in CV'}
                      {mismatch.type === 'date_inconsistency' && '⚠️ Date mismatch'}
                      {mismatch.type === 'overlap_inconsistency' && '⚠️ Overlap inconsistency'}
                    </p>
                    <p className="text-sm text-gray-700 mt-1">{mismatch.description}</p>
                    
                    {/* Show data comparison */}
                    <div className="grid grid-cols-2 gap-4 mt-2 text-xs">
                      {mismatch.structured_data && (
                        <div className="p-2 bg-white rounded border">
                          <p className="font-medium text-gray-600">Structured:</p>
                          <p>{mismatch.structured_data.employer_name || mismatch.structured_data.company}</p>
                          <p className="text-gray-500">{mismatch.structured_data.start_date} - {mismatch.structured_data.end_date || 'Present'}</p>
                        </div>
                      )}
                      {mismatch.cv_data && (
                        <div className="p-2 bg-white rounded border">
                          <p className="font-medium text-gray-600">CV:</p>
                          <p>{mismatch.cv_data.employer}</p>
                          <p className="text-gray-500">{mismatch.cv_data.start_date} - {mismatch.cv_data.end_date || 'Present'}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Side-by-side View */}
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Structured Employment History (Source of Truth)</h4>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {employmentMismatch.structured_history?.length > 0 ? (
                      employmentMismatch.structured_history.map((job, idx) => (
                        <div key={idx} className="p-2 bg-green-50 rounded border border-green-200 text-sm">
                          <p className="font-medium">{job.employer_name || job.company || job.employer}</p>
                          <p className="text-gray-600">{job.job_title || job.role}</p>
                          <p className="text-xs text-gray-500">{job.start_date} - {job.end_date || 'Present'}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-gray-500">No structured history recorded</p>
                    )}
                  </div>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">CV Extracted Roles</h4>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {employmentMismatch.cv_extracted_roles?.length > 0 ? (
                      employmentMismatch.cv_extracted_roles.map((role, idx) => (
                        <div key={idx} className="p-2 bg-blue-50 rounded border border-blue-200 text-sm">
                          <p className="font-medium">{role.employer}</p>
                          <p className="text-gray-600">{role.job_title}</p>
                          <p className="text-xs text-gray-500">{role.start_date} - {role.end_date || 'Present'}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-gray-500">No roles extracted from CV</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Apply selected CV roles to history */}
              {!isAuditor() && employmentMismatch.cv_extracted_roles?.length > 0 && (
                <div className="pt-4 border-t space-y-3">
                  <h4 className="font-medium text-gray-900">Apply CV Roles to Employment History</h4>
                  <p className="text-xs text-gray-500">
                    Select roles from the CV to append to the canonical employment history.
                    Existing records are never overwritten — only new entries are added.
                    Gaps and coverage will recalculate automatically.
                  </p>
                  <div className="space-y-2">
                    {employmentMismatch.cv_extracted_roles.map((role, idx) => (
                      <label key={idx} className="flex items-start gap-3 p-2 rounded border border-gray-200 cursor-pointer hover:bg-gray-50">
                        <input
                          type="checkbox"
                          className="mt-0.5"
                          checked={!!selectedCvRolesForApply[idx]}
                          onChange={(e) => setSelectedCvRolesForApply(prev => ({ ...prev, [idx]: e.target.checked }))}
                        />
                        <div className="text-sm">
                          <p className="font-medium text-gray-900">{role.employer}</p>
                          <p className="text-gray-600">{role.job_title}</p>
                          <p className="text-xs text-gray-500">{role.start_date} – {role.end_date || 'Present'}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                  {Object.values(selectedCvRolesForApply).some(Boolean) && (
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-gray-700">Reason for applying (required) *</label>
                      <Textarea
                        value={reconcileReason}
                        onChange={(e) => setReconcileReason(e.target.value)}
                        placeholder="e.g. CV confirms role at Joymark Support UK Ltd from Feb 2026 not captured in application form"
                        rows={2}
                        className="bg-white border-[#E4E8EB] text-sm"
                      />
                      <Button
                        onClick={handleApplyReconcile}
                        disabled={isApplyingReconcile || reconcileReason.trim().length < 5}
                        className="bg-blue-600 hover:bg-blue-700 text-white w-full"
                      >
                        {isApplyingReconcile ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <CheckCircle className="h-4 w-4 mr-2" />
                        )}
                        Apply Selected Roles to Employment History
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {/* Add Review Note */}
              {!isAuditor() && (
                <div className="pt-4 border-t space-y-3">
                  <h4 className="font-medium text-gray-900">Add Review Note (acknowledge without applying)</h4>
                  <p className="text-xs text-gray-500">Document your review of this mismatch to proceed with recruitment approval.</p>
                  <Textarea
                    value={mismatchReviewNote}
                    onChange={(e) => setMismatchReviewNote(e.target.value)}
                    placeholder="Explain why this mismatch is acceptable or document actions taken..."
                    rows={3}
                    className="bg-white border-[#E4E8EB]"
                  />
                </div>
              )}
            </div>
          )}
          
          <DialogFooter className="flex gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => setMismatchDialogOpen(false)}
              className="border-[#E4E8EB]"
            >
              Close
            </Button>
            {!isAuditor() && (
              <Button 
                onClick={handleAddMismatchNote}
                disabled={isSubmittingMismatchNote || mismatchReviewNote.length < 5}
                className="bg-amber-600 hover:bg-amber-700 text-white"
                data-testid="add-mismatch-note-btn"
              >
                {isSubmittingMismatchNote ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <CheckCircle className="h-4 w-4 mr-2" />
                )}
                Add Review Note
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* ========== EVIDENCE UPLOAD DIALOG (SUPER ADMIN) ========== */}
      {/* This dialog allows admins to upload evidence for any compliance requirement */}
      <Dialog open={uploadDialogOpen} onOpenChange={(open) => {
        setUploadDialogOpen(open);
        if (!open) {
          setSelectedRequirement('');
          setUploadFile(null);
          setDocumentLabel('');
        }
      }}>
        <DialogContent className="max-w-lg bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Upload className="h-5 w-5 text-blue-600" />
              Upload Document Evidence
            </DialogTitle>
            <DialogDescription>
              Upload evidence for the selected compliance requirement. This will be available for verification.
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleUploadDocument} className="space-y-4 mt-4">
            {/* Requirement Selection */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">
                Requirement <span className="text-red-500">*</span>
              </Label>
              <Select value={selectedRequirement} onValueChange={setSelectedRequirement}>
                <SelectTrigger className="rounded-xl" data-testid="upload-requirement-select">
                  <SelectValue placeholder="Select requirement type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="right_to_work_documents">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-green-500" />
                      Right to Work Documents
                    </div>
                  </SelectItem>
                  <SelectItem value="dbs_certificate">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-blue-500" />
                      DBS Certificate
                    </div>
                  </SelectItem>
                  <SelectItem value="identity_documents">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-purple-500" />
                      Identity (Passport/ID)
                    </div>
                  </SelectItem>
                  <SelectItem value="proof_of_address">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-amber-500" />
                      Proof of Address
                    </div>
                  </SelectItem>
                  <SelectItem value="cv">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-cyan-500" />
                      CV / Resume
                    </div>
                  </SelectItem>
                  <SelectItem value="application_form">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-pink-500" />
                      Application Form (PDF)
                    </div>
                  </SelectItem>
                  <SelectItem value="right_to_work_check">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-teal-500" />
                      Right to Work Check (Internal)
                    </div>
                  </SelectItem>
                  <SelectItem value="dbs_check">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-indigo-500" />
                      DBS Update Service Check (Internal)
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {/* Optional File Label */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">File Label (optional)</Label>
              <Input
                value={documentLabel}
                onChange={(e) => setDocumentLabel(e.target.value)}
                placeholder="e.g., BRP Card Front, DBS Certificate 2024"
                className="rounded-xl"
                data-testid="upload-file-label"
              />
            </div>
            
            {/* File Picker */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">
                File <span className="text-red-500">*</span>
              </Label>
              <FileUploaderInline
                onFileSelect={(file) => {
                  if (selectedRequirement === 'cv' && file) {
                    const isPdfFile = file.type === 'application/pdf' || file.name?.toLowerCase().endsWith('.pdf');
                    if (!isPdfFile) {
                      toast.error('Only PDF CV files are supported. Please upload the CV as a PDF. Word documents (.doc, .docx) are not accepted.');
                      return;
                    }
                  }
                  setUploadFile(file);
                }}
                selectedFile={uploadFile}
                onClear={() => setUploadFile(null)}
                acceptedTypes={selectedRequirement === 'cv' ? ['application/pdf'] : ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'image/webp']}
                maxSizeBytes={10 * 1024 * 1024}
                placeholder="Choose file or drag here"
                className="border-2 border-dashed rounded-xl"
              />
              <p className="text-xs text-gray-500">
                {selectedRequirement === 'cv'
                  ? 'Accepted: PDF only (max 10MB)'
                  : 'Accepted: PDF, JPG, PNG, WebP (max 10MB)'}
              </p>
            </div>
            
            <DialogFooter className="pt-4">
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => setUploadDialogOpen(false)}
                className="border-gray-200"
              >
                Cancel
              </Button>
              <Button 
                type="submit" 
                disabled={!selectedRequirement || !uploadFile || isUploading}
                className="bg-blue-600 hover:bg-blue-700 text-white"
                data-testid="upload-submit-btn"
              >
                {isUploading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4 mr-2" />
                )}
                Upload Evidence
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      
      {/* ========== DUAL-ROW COMPLIANCE MODEL DIALOGS (STEP 11) ========== */}
      
      {/* Record Check Dialog */}
      <RecordCheckDialog
        open={recordCheckDialogOpen}
        onClose={() => {
          setRecordCheckDialogOpen(false);
          setRecordCheckType(null);
        }}
        employeeId={employeeId}
        checkType={recordCheckType}
        onComplete={() => {
          fetchData();
          fetchCompliance();
        }}
        // Evidence status props - computed from complianceFile
        hasAcceptedEvidence={(() => {
          if (!complianceFile || !recordCheckType) return false;
          const sectionKey = recordCheckType?.replace('_check', '').replace('_verification', '');
          const section = complianceFile?.requirements?.[sectionKey];
          if (!section?.rows) return false;
          const evidenceRow = section.rows.find(r => r.row_type === 'evidence');
          return (evidenceRow?.counts?.verified || 0) > 0;
        })()}
        hasStampedEvidence={(() => {
          if (!complianceFile || !recordCheckType) return false;
          const sectionKey = recordCheckType?.replace('_check', '').replace('_verification', '');
          const section = complianceFile?.requirements?.[sectionKey];
          if (!section?.rows) return false;
          const evidenceRow = section.rows.find(r => r.row_type === 'evidence');
          const docs = evidenceRow?.documents_preview || [];
          return docs.some(d => d.verification_stamp);
        })()}
        acceptedEvidenceCount={(() => {
          if (!complianceFile || !recordCheckType) return 0;
          const sectionKey = recordCheckType?.replace('_check', '').replace('_verification', '');
          const section = complianceFile?.requirements?.[sectionKey];
          if (!section?.rows) return 0;
          const evidenceRow = section.rows.find(r => r.row_type === 'evidence');
          return evidenceRow?.counts?.verified || 0;
        })()}
      />

      {/* ========== EDIT DIALOGS FOR UNIVERSAL EDITABILITY ========== */}
      
      {/* Edit Personal Details Dialog */}
      <EditPersonalDetailsDialog
        open={editPersonalOpen}
        onClose={() => setEditPersonalOpen(false)}
        employeeId={employeeId}
        currentData={employee}
        onSuccess={() => {
          fetchEmployee();
          fetchComplianceFile();
          fetchEmploymentReview();
        }}
      />
      
      {/* Edit Employment History Dialog */}
      <EditEmploymentHistoryDialog
        open={editEmploymentOpen}
        onClose={() => setEditEmploymentOpen(false)}
        employeeId={employeeId}
        currentHistory={employee?.employment_history || []}
        onSuccess={() => {
          fetchEmployee();
          fetchComplianceFile();
        }}
      />
      
      {/* Edit Reference Dialog */}
      <EditReferenceDialog
        open={editReferenceOpen}
        onClose={() => {
          setEditReferenceOpen(false);
          setSelectedReferenceId(null);
          setSelectedReferenceData(null);
        }}
        employeeId={employeeId}
        referenceId={selectedReferenceId}
        currentData={selectedReferenceData}
        onSuccess={async () => {
          await Promise.allSettled([
            fetchEmployee(),
            fetchCompliance(),
            fetchComplianceFile(),
            fetchReferenceStatus(),
            fetchRecruitmentStatus(),
          ]);
          setReferencesTabRefreshKey((current) => current + 1);
        }}
      />
      
      {/* Supersede Contract Dialog */}
      <SupersedeContractDialog
        open={supersedeContractOpen}
        onClose={() => {
          setSupersedeContractOpen(false);
          setCurrentContract(null);
        }}
        employeeId={employeeId}
        employeeName={employee ? `${employee.first_name} ${employee.last_name}` : ''}
        currentContract={currentContract}
        onSuccess={() => {
          fetchEmployee();
          fetchComplianceFile();
        }}
      />
      
      {/* Edit Declarations Dialog */}
      <EditDeclarationsDialog
        open={editDeclarationsOpen}
        onClose={() => setEditDeclarationsOpen(false)}
        employeeId={employeeId}
        currentData={employee}
        onSuccess={() => {
          fetchEmployee();
          fetchComplianceFile();
          fetchEmploymentReview();
        }}
      />
      
      {/* Document Verification Modal (CQC P0) */}
      <DocumentVerificationModal
        open={verificationModalOpen}
        onClose={() => {
          setVerificationModalOpen(false);
          setVerificationDocument(null);
        }}
        document={verificationDocument}
        employeeId={employeeId}
        employeeName={employee ? `${employee.first_name} ${employee.last_name}` : ''}
        onVerified={handleVerificationComplete}
      />
      
      {/* Document Viewer Modal (CQC P0) */}
      <DocumentViewerModal
        open={viewerModalOpen}
        onClose={() => {
          setViewerModalOpen(false);
          setViewerDocument(null);
        }}
        document={viewerDocument}
        employeeId={employeeId}
        employeeName={employee ? `${employee.first_name} ${employee.last_name}` : ''}
        onVerify={(doc) => {
          setViewerModalOpen(false);
          handleOpenVerificationModal(doc);
        }}
      />
      
      {/* ========== CV REVIEW DIALOG ========== */}
      <Dialog open={cvReviewDialogOpen} onOpenChange={setCvReviewDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileSearch className="h-5 w-5 text-purple-600" />
              CV Review - AI Extraction Results
            </DialogTitle>
            <DialogDescription>
              Review the extracted employment history from the worker's CV. Approve if accurate, or reject with reason if issues found.
            </DialogDescription>
          </DialogHeader>
          
          {cvExtractionResult && (
            <div className="space-y-4 py-4">
              {/* Summary Stats */}
              <div className="grid grid-cols-4 gap-4">
                <div className="p-3 bg-blue-50 rounded-lg text-center">
                  <p className="text-2xl font-bold text-blue-700">{cvExtractionResult.jobs_found}</p>
                  <p className="text-xs text-blue-600">Jobs Found</p>
                </div>
                <div className="p-3 bg-purple-50 rounded-lg text-center">
                  <p className="text-2xl font-bold text-purple-700">{cvExtractionResult.education_found}</p>
                  <p className="text-xs text-purple-600">Education</p>
                </div>
                <div className="p-3 bg-green-50 rounded-lg text-center">
                  <p className="text-2xl font-bold text-green-700">{cvExtractionResult.skills_found}</p>
                  <p className="text-xs text-green-600">Skills</p>
                </div>
                <div className={`p-3 rounded-lg text-center ${cvExtractionResult.gaps_detected > 0 ? 'bg-red-50' : 'bg-gray-50'}`}>
                  <p className={`text-2xl font-bold ${cvExtractionResult.gaps_detected > 0 ? 'text-red-700' : 'text-gray-700'}`}>
                    {cvExtractionResult.gaps_detected}
                  </p>
                  <p className={`text-xs ${cvExtractionResult.gaps_detected > 0 ? 'text-red-600' : 'text-gray-600'}`}>
                    Gaps Detected
                  </p>
                </div>
              </div>
              
              {/* Employment History */}
              {cvExtractionResult.employment_history?.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-800 mb-2 flex items-center gap-2">
                    <Briefcase className="h-4 w-4" />
                    Employment History
                  </h4>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {cvExtractionResult.employment_history.map((job, idx) => (
                      <div key={idx} className="p-3 bg-gray-50 rounded-lg border border-gray-200 text-sm">
                        <div className="flex justify-between">
                          <div>
                            <p className="font-medium text-gray-800">{job.employer || job.company}</p>
                            <p className="text-gray-600">{job.job_title || job.position}</p>
                          </div>
                          <p className="text-xs text-gray-500">
                            {job.start_date} - {job.end_date || 'Present'}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Gaps Detected */}
              {cvExtractionResult.gaps?.length > 0 && (
                <div>
                  <h4 className="font-medium text-red-800 mb-2 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    Gaps Requiring Explanation
                  </h4>
                  <div className="space-y-2">
                    {cvExtractionResult.gaps.map((gap, idx) => (
                      <div key={idx} className="p-3 bg-red-50 rounded-lg border border-red-200 text-sm">
                        <p className="text-red-700">{gap.message}</p>
                        <p className="text-xs text-red-500 mt-1">
                          {gap.start_date} - {gap.end_date} ({gap.duration_days} days)
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          
          <DialogFooter className="flex gap-2 sm:justify-between">
            <Button variant="outline" onClick={() => setCvRejectDialogOpen(true)} className="text-red-600 border-red-200 hover:bg-red-50">
              <XCircle className="h-4 w-4 mr-1" />
              Reject with Reason
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setCvReviewDialogOpen(false)}>
                Close
              </Button>
              <Button onClick={handleApproveCv} disabled={cvReviewLoading} className="bg-green-600 hover:bg-green-700">
                {cvReviewLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <CheckCircle className="h-4 w-4 mr-1" />}
                Approve CV
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* CV Reject Dialog */}
      <Dialog open={cvRejectDialogOpen} onOpenChange={setCvRejectDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <XCircle className="h-5 w-5" />
              Reject CV
            </DialogTitle>
            <DialogDescription>
              Provide a clear reason for rejection. The worker will be notified and asked to either explain gaps or upload a new CV.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <Label>Rejection Reason</Label>
            <Textarea
              value={cvRejectReason}
              onChange={(e) => setCvRejectReason(e.target.value)}
              placeholder="e.g., Please explain the employment gap between March 2019 and January 2021, or provide documentation for this period."
              className="mt-2 min-h-[100px]"
            />
            <p className="text-xs text-gray-500 mt-1">
              Be specific about what the worker needs to do (explain gap, provide documentation, upload new CV)
            </p>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setCvRejectDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleRejectCv} 
              disabled={cvRejectLoading || cvRejectReason.length < 10}
              className="bg-red-600 hover:bg-red-700"
            >
              {cvRejectLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Send className="h-4 w-4 mr-1" />}
              Send Rejection
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Inline Document Viewer (PDF / image) — replaces window.open */}
      <InlineDocumentViewer
        open={inlineViewerOpen}
        onClose={() => {
          setInlineViewerOpen(false);
          setInlineViewerFallback(null);
        }}
        fetchUrl={inlineViewerUrl}
        title={inlineViewerTitle}
        token={token}
        filename={inlineViewerFilename}
        fallbackLabel={inlineViewerFallback ? 'View submitted answers' : undefined}
        onFallback={inlineViewerFallback ? () => {
          setInlineViewerOpen(false);
          setViewFormSubmission(inlineViewerFallback);
          setInlineViewerFallback(null);
        } : undefined}
      />
    </div>
  );
}
