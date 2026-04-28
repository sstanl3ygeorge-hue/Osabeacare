import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import { 
  FileText, CheckCircle, Clock, AlertTriangle,
  Eye, Send, RefreshCw, Shield, Download, X, ChevronDown, ChevronUp, Upload as UploadIcon,
  ClipboardCheck, Stamp, FileCheck
} from 'lucide-react';
import RequirementSectionShell from './RequirementSectionShell';
import RequirementActionBar from './RequirementActionBar';
import EvidenceReviewDialog from './EvidenceReviewDialog';
import VerificationStampDialog from './VerificationStampDialog';
import VerificationChecklistModal from './VerificationChecklistModal';
import AmendmentRequestDialog from './AmendmentRequestDialog';
import EvidenceReviewViewerDialog from './EvidenceReviewViewerDialog';
import OnlineCheckVerifyDialog from './OnlineCheckVerifyDialog';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/dialog';
import { formatBackendDate } from '../../lib/dateUtils';
import { getEvidenceRules } from './evidenceRules';
import API_BASE from '../../utils/apiBase';
import {
  fetchProtectedFileBlob,
  downloadBlobUrl,
  revokeBlobUrlLater,
} from '../../lib/protectedFiles';

// eslint-disable-next-line no-unused-vars
const API = API_BASE;

// Map requirement keys to check types for verification proof storage (used by RecordCheckDialog)
// eslint-disable-next-line no-unused-vars
const REQUIREMENT_TO_CHECK_TYPE = {
  'right_to_work': 'right_to_work_check',
  'dbs': 'dbs_status_check',
  'identity': 'identity_verification',
  'proof_of_address': 'address_verification'
};

/**
 * UploadRequirementCard - Unified DUAL-ROW card for upload-based requirements
 * 
 * Used for: Right to Work, DBS, Identity, Proof of Address
 * 
 * DUAL-ROW MODEL:
 * - Row A: EVIDENCE - Files uploaded by candidate/admin
 *   - Upload, Manage, View files, Download files
 * 
 * - Row B: VERIFICATION - Admin verification proof & check outcome
 *   - Upload verification proof (saved with category: verification_proof)
 *   - Record check (method, outcome, date)
 *   - View proof, Download proof
 *   - Shows: checked_by, checked_at, method, outcome, notes
 */
export default function UploadRequirementCard({
  surface,
  isOpen,
  onToggle,
  onOpenDrawer,
  onUpload,
  onRequest,
  onResend,
  onRecordCheck,
  onUpdateCheck,
  onViewHistory,
  onPreviewFile,
  employeeId,
  employeeName,
  onRefresh,
  isAuditor = false,
  // RTW Status - additive, non-breaking prop
  rtwStatus = null,
  // NEW: Stamp All handler for RTW/DBS
  onStampAll
}) {
  // eslint-disable-next-line no-unused-vars
  const { token } = useAuth();
  const [evidenceExpanded, setEvidenceExpanded] = useState(true);
  const [verificationExpanded, setVerificationExpanded] = useState(true);
  
  // Evidence Review Dialog state
  const [reviewDialog, setReviewDialog] = useState({
    isOpen: false,
    file: null
  });
  
  // Verification Stamp Dialog state
  const [stampDialog, setStampDialog] = useState({
    isOpen: false,
    file: null
  });
  
  // NEW: Smart Verification Checklist Modal state
  const [checklistModal, setChecklistModal] = useState({
    isOpen: false,
    file: null
  });
  
  // NEW: Amendment Request Dialog state
  const [amendmentDialog, setAmendmentDialog] = useState({
    isOpen: false,
    file: null
  });
  
  // NEW: Online Check Verify Dialog state (for RTW & DBS)
  const [onlineCheckDialog, setOnlineCheckDialog] = useState({
    isOpen: false,
    file: null
  });
  
  // NEW: Quick Verify & Stamp Dialog state (for Identity & PoA only)
  const [quickVerifyDialog, setQuickVerifyDialog] = useState({
    isOpen: false,
    file: null,
    aiValidation: null
  });
  
  // NEW: Stamp All state for RTW/DBS
  const [stampingAll, setStampingAll] = useState(false);
  const [stampAllDialog, setStampAllDialog] = useState({ open: false, message: '', files: [] });

  const handleProtectedEvidenceDownload = async (url, filename = 'document') => {
    try {
      const { blobUrl } = await fetchProtectedFileBlob(url, token);
      downloadBlobUrl(blobUrl, filename);
      revokeBlobUrlLater(blobUrl);
    } catch (error) {
      toast.error('Failed to download file');
    }
  };
  
  // Handle Stamp All for RTW/DBS - stamps both evidence and verification proof
  const handleStampAll = async (requirementKey, filesToStamp) => {
    if (!employeeId || !filesToStamp.length) return;
    
    setStampingAll(true);
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/${requirementKey}/stamp-all`,
        {
          evidence_file_ids: filesToStamp.map(f => f.file_id || f.id),
          stamp_verification_proof: true
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      
      if (response.data.success) {
        toast.success(
          <div className="flex items-center gap-2">
            <Stamp className="h-4 w-4 text-emerald-600" />
            <span>{response.data.message || 'All documents stamped successfully'}</span>
          </div>
        );
        if (onRefresh) onRefresh();
      }
    } catch (err) {
      console.error('Stamp all failed:', err);
      toast.error(err.response?.data?.detail || 'Failed to stamp documents');
    } finally {
      setStampingAll(false);
    }
  };

  if (!surface) return null;

  const {
    key,
    label,
    activeFiles,
    historicalFiles,
    latestRequest,
    authoritativeCheck,
    summary,
    counters,
    requestState,
    rowStatus,
    rules
  } = surface;

  // Determine blocking status
  const isBlocking = rowStatus === 'missing' || rowStatus === 'rejected' || rowStatus === 'replacement_required';
  const blockingLabel = isBlocking ? 'Blocking' : null;

  // Determine available actions
  const hasFiles = counters.active > 0;
  const hasCheck = !!authoritativeCheck;
  const checkVerified = authoritativeCheck?.status === 'verified';
  const hasPendingRequest = requestState === 'requested' || requestState === 'viewed';

  const evidenceRules = getEvidenceRules(key);
  const documentLimit = evidenceRules.max_active_files || null; // null = unlimited
  const isAtLimit = documentLimit && counters.active >= documentLimit;
  const limitMessage = isAtLimit 
    ? `Maximum ${documentLimit} document${documentLimit > 1 ? 's' : ''} allowed` 
    : null;

  // Get check data details
  const checkData = authoritativeCheck || {};
  const hasVerificationProof = checkData.evidence_document_id && checkData.evidence_document;

  // ================================================================
  // GATED WORKFLOW - 5 E's of Usability Compliant
  // For RTW and DBS: Evidence → Accept → Check → Proof → Stamp
  // ================================================================
  const isRTWOrDBS = key === 'right_to_work' || key === 'dbs';
  
  // Count accepted/verified evidence files
  const acceptedEvidenceCount = activeFiles.filter(f => 
    f.status === 'accepted' || f.status === 'verified' || f.verified
  ).length;
  const hasAcceptedEvidence = acceptedEvidenceCount > 0;
  
  // Count stamped evidence files
  const stampedEvidenceCount = activeFiles.filter(f => f.verification_stamp).length;
  const allEvidenceStamped = hasFiles && stampedEvidenceCount === activeFiles.length;
  
  // Determine current workflow step for RTW/DBS
  const getWorkflowStep = () => {
    if (!isRTWOrDBS) return null;
    
    // Step 1: Need evidence upload
    if (!hasFiles) {
      return { 
        step: 1, 
        label: 'Upload Evidence', 
        description: 'Employee or admin uploads evidence documents',
        total: 5 
      };
    }
    
    // Step 2: Need to accept/review evidence
    if (!hasAcceptedEvidence) {
      return { 
        step: 2, 
        label: 'Review Evidence', 
        description: 'Accept or reject uploaded evidence',
        total: 5 
      };
    }
    
    // Step 3: Need to record check
    if (!hasCheck) {
      return { 
        step: 3, 
        label: 'Record Check', 
        description: key === 'right_to_work' 
          ? 'Perform Home Office right to work check'
          : 'Record DBS certificate details',
        total: 5 
      };
    }
    
    // Step 4: Need verification proof (optional but recommended)
    if (!hasVerificationProof) {
      return { 
        step: 4, 
        label: 'Upload Proof', 
        description: key === 'right_to_work'
          ? 'Upload Home Office check screenshot'
          : 'Upload DBS Update Service screenshot (if applicable)',
        total: 5,
        optional: true
      };
    }
    
    // Step 5: Need to stamp
    if (!allEvidenceStamped) {
      return { 
        step: 5, 
        label: 'Confirm & Stamp', 
        description: 'Apply verification stamps to seal documents',
        total: 5 
      };
    }
    
    // Complete!
    return { 
      step: 5, 
      label: 'Complete', 
      description: 'All verification steps completed',
      total: 5,
      complete: true 
    };
  };
  
  const workflowStep = getWorkflowStep();

  // Handle viewing verification proof
  const handleViewProof = () => {
    if (hasVerificationProof && onPreviewFile) {
      onPreviewFile({
        file_url: `/api/employee-documents/${checkData.evidence_document_id}/file`,
        file_name: checkData.evidence_document.filename || 'Verification Proof'
      });
    }
  };

  // Handle downloading verification proof
  const handleDownloadProof = async () => {
    if (!hasVerificationProof) return;
    
    try {
      const url = `${API}/employee-documents/${checkData.evidence_document_id}/download`;
      const response = await axios.get(url, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      const blob = new Blob([response.data]);
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = checkData.evidence_document.filename || 'verification_proof';
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      toast.error('Download failed');
    }
  };

  // Get method display name
  const getMethodDisplay = (method) => {
    const methods = {
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
      'manual_certificate_review': 'Manual Certificate Review',
      // Other Methods
      'share_code_online_check': 'Share Code Online Check',
      'manual_passport_check': 'Manual Passport Check',
      'manual_id_verification': 'Manual ID Verification',
      'digital_id_check': 'Digital ID Check',
      'manual_document_check': 'Manual Document Check'
    };
    return methods[method] || method?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Unknown';
  };

  // Get user display name from user ID
  const getUserDisplayName = (userId, fallbackName) => {
    // If we have a name already, use it
    if (fallbackName && !fallbackName.startsWith('user_')) return fallbackName;
    // If it's a user ID, try to format it nicely or return Admin
    if (userId && userId.startsWith('user_')) return 'Admin';
    if (userId) return userId;
    return fallbackName || 'Unknown';
  };

  // Get stamp display info - Osabea branded
  const getStampDisplay = (stamp) => {
    // Handle both string stamp types and full stamp objects
    const stampType = typeof stamp === 'object' ? stamp?.stamp_type : stamp;
    
    const stamps = {
      'document_verified': { label: 'Verified', className: 'bg-sky-50 text-sky-700 border-sky-200', showLogo: true },
      'original_seen': { label: 'Original Seen', className: 'bg-purple-50 text-purple-700 border-purple-200', showLogo: true },
      'copy_verified': { label: 'Copy Verified', className: 'bg-amber-50 text-amber-700 border-amber-200', showLogo: true },
      'online_check': { label: 'Verified', className: 'bg-sky-50 text-sky-700 border-sky-200', showLogo: true }, // Legacy
      'not_verified': { label: 'NOT VERIFIED', className: 'bg-red-100 text-red-700 border-red-200', showLogo: false }
    };
    return stamps[stampType] || { label: 'Verified', className: 'bg-green-50 text-green-700 border-green-200', showLogo: true };
  };

  // Get outcome display
  const getOutcomeDisplay = (outcome) => {
    const outcomes = {
      'verified': 'Verified',
      'failed': 'Failed',
      'follow_up_required': 'Follow-up Required',
      'awaiting_review': 'Awaiting admin review'
    };
    return outcomes[outcome] || outcome?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Unknown';
  };

  return (
    <RequirementSectionShell
      title={label}
      summary={summary}
      blockingLabel={blockingLabel}
      isOpen={isOpen}
      onToggle={onToggle}
      testId={`upload-requirement-${key}`}
      /* REMOVED: Outer card header actions - these are now ONLY in the Evidence row */
      /* Actions were duplicated between header and Evidence row. Each row now has its own actions. */
    >
      <div className="space-y-4">
        {/* ============================================== */}
        {/* WORKFLOW PROGRESS INDICATOR (RTW & DBS only)  */}
        {/* Shows current step and gates actions          */}
        {/* ============================================== */}
        {isRTWOrDBS && workflowStep && !workflowStep.complete && (
          <div className="bg-gradient-to-r from-slate-50 to-slate-100 border border-slate-200 rounded-xl p-4" data-testid={`${key}-workflow-progress`}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-primary text-white flex items-center justify-center text-sm font-bold">
                  {workflowStep.step}
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-800">{workflowStep.label}</p>
                  <p className="text-xs text-slate-500">{workflowStep.description}</p>
                </div>
              </div>
              <span className="text-xs text-slate-400">Step {workflowStep.step} of {workflowStep.total}</span>
            </div>
            
            {/* Progress Bar */}
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((step) => (
                <div
                  key={step}
                  className={`h-1.5 flex-1 rounded-full transition-colors ${
                    step < workflowStep.step ? 'bg-green-500' :
                    step === workflowStep.step ? 'bg-primary' :
                    'bg-slate-200'
                  }`}
                />
              ))}
            </div>
            
            {/* Step Labels */}
            <div className="flex justify-between mt-2 text-[10px] text-slate-400">
              <span className={workflowStep.step >= 1 ? 'text-slate-600' : ''}>Evidence</span>
              <span className={workflowStep.step >= 2 ? 'text-slate-600' : ''}>Review</span>
              <span className={workflowStep.step >= 3 ? 'text-slate-600' : ''}>Check</span>
              <span className={workflowStep.step >= 4 ? 'text-slate-600' : ''}>Proof</span>
              <span className={workflowStep.step >= 5 ? 'text-slate-600' : ''}>Stamp</span>
            </div>
          </div>
        )}
        
        {/* Complete Badge for RTW/DBS */}
        {isRTWOrDBS && workflowStep?.complete && (
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl p-4 flex items-center gap-3" data-testid={`${key}-workflow-complete`}>
            <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
              <CheckCircle className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-green-800">Verification Complete</p>
              <p className="text-xs text-green-600">All documents verified and stamped with Osabea seal</p>
            </div>
            <img src="/osabea_logo.png" alt="" className="h-8 w-auto ml-auto opacity-60" />
          </div>
        )}
        
        {/* ============================================== */}
        {/* ROW A: EVIDENCE SECTION                        */}
        {/* ============================================== */}
        <div 
          className={`border rounded-xl overflow-hidden ${
            hasFiles ? 'border-blue-200 bg-blue-50/20' : 'border-gray-200 bg-gray-50/20'
          }`}
          data-testid={`${key}-evidence-row`}
        >
          {/* Evidence Row Header */}
          <div 
            className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/50 transition-colors"
            onClick={() => setEvidenceExpanded(!evidenceExpanded)}
          >
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                hasFiles ? 'bg-blue-100' : 'bg-gray-100'
              }`}>
                <FileText className={`h-4 w-4 ${hasFiles ? 'text-blue-600' : 'text-gray-400'}`} />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-text-primary">
                  Evidence
                  <span className="text-xs font-normal text-gray-500 ml-1">(Employee uploads)</span>
                </h4>
                <p className="text-xs text-text-muted">
                  {/* Computed workflow state based on file status */}
                  {counters.verified > 0 
                    ? `${counters.verified} verified${counters.pendingReview > 0 ? `, ${counters.pendingReview} pending` : ''}`
                    : hasFiles 
                      ? `${counters.active} file${counters.active !== 1 ? 's' : ''} uploaded${counters.pendingReview > 0 ? ' (pending review)' : ''}`
                      : latestRequest && requestState === 'requested'
                        ? 'Request sent - awaiting upload'
                        : 'No files uploaded'
                  }
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {counters.verified > 0 && (
                <Badge className="text-[10px] px-1.5 py-0 bg-green-100 text-green-700 border border-green-200">
                  {counters.verified} verified
                </Badge>
              )}
              {counters.pendingReview > 0 && (
                <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border border-amber-200">
                  {counters.pendingReview} pending
                </Badge>
              )}
              {counters.rejected > 0 && (
                <Badge className="text-[10px] px-1.5 py-0 bg-red-100 text-red-700 border border-red-200">
                  {counters.rejected} rejected
                </Badge>
              )}
              <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                {evidenceExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>
          </div>

          {/* Evidence Row Content */}
          {evidenceExpanded && (
            <div className="p-3 pt-0 space-y-3">
              {/* Evidence Files List */}
              {activeFiles.length > 0 ? (
                <div className="space-y-2">
                  {activeFiles.slice(0, 3).map((file) => (
                    <div 
                      key={file.file_id || file.id}
                      className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-text-primary truncate">
                            {file.file_name || file.original_filename || 'Document'}
                          </p>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs text-text-muted">
                              {formatBackendDate(file.uploaded_at, { format: 'medium' })}
                              {file.uploaded_by && ` • ${file.uploaded_by}`}
                            </span>
                            {/* Verification Stamp Badge - Osabea Branded */}
                            {file.verification_stamp && (() => {
                              const stampInfo = getStampDisplay(file.verification_stamp);
                              return (
                                <div className="flex flex-col">
                                  <Badge 
                                    className={`text-[9px] px-1.5 py-0.5 font-semibold border flex items-center gap-1 ${stampInfo.className}`}
                                    data-testid={`${key}-stamp-badge-${file.file_id || file.id}`}
                                  >
                                    {stampInfo.showLogo && (
                                      <img src="/osabea_logo.png" alt="" className="h-2.5 w-auto" />
                                    )}
                                    {!stampInfo.showLogo && <Stamp className="h-2.5 w-2.5" />}
                                    {stampInfo.label}
                                  </Badge>
                                  {(file.verification_stamp_by_name || file.verification_stamp_at) && (
                                    <span className="text-[9px] text-text-muted mt-0.5">
                                      {file.verification_stamp_by_name && `by ${file.verification_stamp_by_name}`}
                                      {file.verification_stamp_at && ` • ${formatBackendDate(file.verification_stamp_at, { format: 'short' })}`}
                                    </span>
                                  )}
                                </div>
                              );
                            })()}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {/* SINGLE STATUS BADGE - Mutually exclusive states */}
                        {(() => {
                          // Determine the ONE status to show (priority order)
                          // IMPORTANT: verification_stamp can be "not_verified" or empty - don't count those
                          const hasValidStamp = file.verification_stamp && 
                                               file.verification_stamp !== 'not_verified' && 
                                               file.verification_stamp !== '';
                          const hasStampedFile = hasValidStamp && file.stamped_file_url;
                          const hasStampNoFile = hasValidStamp && !file.stamped_file_url;
                          const isVerified = file.verified || file.status === 'verified';
                          const isRejected = file.status === 'rejected';
                          const isExtractionPending = file.extraction_status?.status === 'awaiting_review';
                          
                          if (hasStampedFile) {
                            // Fully verified with viewable stamped PDF
                            return (
                              <Badge className="text-[10px] px-1.5 py-0 bg-emerald-100 text-emerald-700 border border-emerald-200">
                                <Stamp className="h-2.5 w-2.5 mr-0.5" />
                                Verified & Stamped
                              </Badge>
                            );
                          } else if (hasStampNoFile) {
                            // Has verification stamp but stamped PDF not yet generated
                            return (
                              <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border border-amber-200">
                                <Clock className="h-2.5 w-2.5 mr-0.5" />
                                Generating Stamp...
                              </Badge>
                            );
                          } else if (isVerified) {
                            // Verified/accepted but not yet stamped
                            return (
                              <Badge className="text-[10px] px-1.5 py-0 bg-green-100 text-green-700 border border-green-200">
                                <CheckCircle className="h-2.5 w-2.5 mr-0.5" />
                                Accepted
                              </Badge>
                            );
                          } else if (isRejected) {
                            return (
                              <Badge className="text-[10px] px-1.5 py-0 bg-red-100 text-red-700 border border-red-200">
                                <X className="h-2.5 w-2.5 mr-0.5" />
                                Rejected
                              </Badge>
                            );
                          } else if (isExtractionPending) {
                            return (
                              <Badge className="text-[10px] px-1.5 py-0 bg-purple-100 text-purple-700 border border-purple-200">
                                <Clock className="h-2.5 w-2.5 mr-0.5" />
                                Processing...
                              </Badge>
                            );
                          } else {
                            // Default: needs review
                            return (
                              <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border border-amber-200">
                                <Clock className="h-2.5 w-2.5 mr-0.5" />
                                Pending Review
                              </Badge>
                            );
                          }
                        })()}
                        
                        {/* View Stamped Document button - ONLY when stamped file exists */}
                        {file.verification_stamp && file.stamped_file_url && (
                          <Button
                            size="sm"
                            variant="default"
                            className="h-7 px-3 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-sm"
                            onClick={() => onPreviewFile && onPreviewFile({
                              file_url: `/api/employee-documents/${file.file_id || file.id}/file`,
                              file_name: file.file_name || file.original_filename || 'Document',
                              stamped_file_url: file.stamped_file_url,
                              verification_stamp_by_name: file.verification_stamp_by_name,
                              verification_stamp_at: file.verification_stamp_at,
                            })}
                            title="View the stamped/verified version of this document"
                            data-testid={`${key}-view-stamped-${file.file_id || file.id}`}
                          >
                            <FileCheck className="h-3.5 w-3.5 mr-1" />
                            View Stamped
                          </Button>
                        )}
                        
                        {/* UNIFIED Verify & Stamp button - For Identity and PoA (simple checks) */}
                        {/* Opens in-app viewer to GUARANTEE admin has seen the document */}
                        {!isAuditor && !file.verification_stamp && !file.verified && file.status !== 'verified' && file.status !== 'rejected' && (key === 'identity' || key === 'proof_of_address') && (
                          <Button
                            size="sm"
                            variant="default"
                            className="h-7 px-3 text-xs bg-green-600 hover:bg-green-700 text-white"
                            onClick={() => setQuickVerifyDialog({ 
                              isOpen: true, 
                              file,
                              aiValidation: file.ai_extraction?.date_validation || null
                            })}
                            title="View, verify and stamp document"
                            data-testid={`${key}-verify-stamp-${file.file_id || file.id}`}
                          >
                            <Eye className="h-3 w-3 mr-1" />
                            View & Approve
                          </Button>
                        )}
                        
                        {/* UNIFIED Verify & Record button — RTW/DBS online check flow */}
                        {!isAuditor && !file.verification_stamp && !file.verified && file.status !== 'verified' && file.status !== 'rejected' && (key === 'right_to_work' || key === 'dbs') && (
                          <Button
                            size="sm"
                            variant="default"
                            className="h-7 px-3 text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
                            onClick={() => setOnlineCheckDialog({ isOpen: true, file })}
                            title="Verify via online check, upload proof, and dual-stamp"
                            data-testid={`${key}-verify-record-${file.file_id || file.id}`}
                          >
                            <Shield className="h-3 w-3 mr-1" />
                            Verify & Record
                          </Button>
                        )}
                        
                        {/* NEW: Request Amendment button - HIDE when fully verified & stamped */}
                        {!isAuditor && file.status !== 'rejected' && !file.verification_stamp && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 px-2 text-xs text-yellow-600 hover:text-yellow-700 hover:bg-yellow-50"
                            onClick={() => setAmendmentDialog({ isOpen: true, file })}
                            title="Request employee to re-upload"
                            data-testid={`${key}-request-amendment-${file.file_id || file.id}`}
                          >
                            <AlertTriangle className="h-3 w-3 mr-1" />
                            Amend
                          </Button>
                        )}
                        
                        {/* View file button */}
                        {onPreviewFile && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 w-7 p-0 text-gray-500 hover:text-blue-600"
                            onClick={() => {
                              const hasStamp = file.verification_stamp && file.verification_stamp !== 'not_verified';
                              if (hasStamp && !file.stamped_file_url) {
                                console.warn(
                                  '[Stamp integrity] Verified doc is missing stamped_file_url.',
                                  { doc_id: file.file_id || file.id, stamp: file.verification_stamp }
                                );
                              }
                              onPreviewFile({
                                file_url: `/api/employee-documents/${file.file_id || file.id}/file`,
                                file_name: file.file_name || file.original_filename || 'Document',
                                stamped_file_url: file.stamped_file_url || null,
                                verification_stamp_by_name: file.verification_stamp_by_name,
                                verification_stamp_at: file.verification_stamp_at,
                              });
                            }}
                            title="View document"
                            data-testid={`${key}-evidence-view-${file.file_id || file.id}`}
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                        )}
                        
                        {/* Download original file */}
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 w-7 p-0 text-gray-500 hover:text-green-600"
                          onClick={async () => {
                            const url = file.file_url || `/api/employee-documents/${file.file_id || file.id}/file`;
                            await handleProtectedEvidenceDownload(url, file.file_name || file.original_filename || 'document');
                          }}
                          title="Download original"
                          data-testid={`${key}-evidence-download-${file.file_id || file.id}`}
                        >
                          <Download className="h-3.5 w-3.5" />
                        </Button>
                        
                        {/* Download stamped version if exists */}
                        {file.stamped_file_url && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 px-1.5 text-xs text-green-600 hover:text-green-700 hover:bg-green-50"
                            onClick={async () => {
                              await handleProtectedEvidenceDownload(
                                file.stamped_file_url,
                                `stamped_${file.file_name || file.original_filename || 'document'}`
                              );
                            }}
                            title="Download stamped version"
                            data-testid={`${key}-evidence-download-stamped-${file.file_id || file.id}`}
                          >
                            <Stamp className="h-3 w-3 mr-0.5" />
                            <Download className="h-3 w-3" />
                          </Button>
                        )}
                        
                        {/* View stamped proof (online check result) — RTW/DBS only */}
                        {file.stamped_proof_url && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 px-2 text-xs text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50"
                            onClick={() => onPreviewFile && onPreviewFile({
                              file_url: file.stamped_proof_url,
                              file_name: `Verification Proof — ${file.file_name || 'Document'}`
                            })}
                            title="View stamped verification proof"
                            data-testid={`${key}-evidence-view-proof-${file.file_id || file.id}`}
                          >
                            <FileText className="h-3 w-3 mr-0.5" />
                            Proof
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                  {activeFiles.length > 3 && (
                    <button 
                      onClick={onOpenDrawer}
                      className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                    >
                      + {activeFiles.length - 3} more file{activeFiles.length - 3 !== 1 ? 's' : ''}
                    </button>
                  )}
                </div>
              ) : (
                <div className="p-4 bg-white border border-gray-200 rounded-lg text-center">
                  <UploadIcon className="h-6 w-6 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-text-muted">No evidence files uploaded</p>
                  {rules?.minimumFilesRequired && (
                    <p className="text-xs text-text-muted mt-1">
                      {rules.minimumFilesRequired} file{rules.minimumFilesRequired !== 1 ? 's' : ''} required
                    </p>
                  )}
                </div>
              )}

              {/* Evidence Upload/Request Actions */}
              {!isAuditor && (
                <div className="flex flex-col gap-2 pt-2 border-t border-gray-100">
                  {/* Show limit warning if at max */}
                  {isAtLimit && (
                    <div className="flex items-center gap-2 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      {limitMessage}
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={onUpload}
                      disabled={isAtLimit}
                      className={`h-8 text-xs rounded-lg ${isAtLimit ? 'opacity-50 cursor-not-allowed' : ''}`}
                      data-testid={`${key}-evidence-upload-btn`}
                      title={isAtLimit ? limitMessage : 'Upload document'}
                    >
                      <UploadIcon className="h-3.5 w-3.5 mr-1" />
                      Upload
                    </Button>
                    {/* Send Reminder - replaces Request/Resend buttons */}
                    {!hasFiles && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={onResend || onRequest}
                        className="h-8 text-xs rounded-lg text-amber-600 border-amber-200 hover:bg-amber-50"
                        data-testid={`${key}-send-reminder-btn`}
                      >
                        <Send className="h-3.5 w-3.5 mr-1" />
                        Send Reminder
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={onOpenDrawer}
                      className="h-8 text-xs rounded-lg"
                      data-testid={`${key}-evidence-manage-btn`}
                    >
                      <Eye className="h-3.5 w-3.5 mr-1" />
                      Manage
                    </Button>
                  </div>
                </div>
              )}

              {/* Request Status - ONLY show if no evidence uploaded yet */}
              {latestRequest && !hasFiles && (
                <div className={`p-3 rounded-lg border ${
                  requestState === 'submitted' ? 'bg-green-50 border-green-200' :
                  requestState === 'viewed' ? 'bg-purple-50 border-purple-200' :
                  requestState === 'requested' ? 'bg-blue-50 border-blue-200' :
                  'bg-gray-50 border-gray-200'
                }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Send className={`h-4 w-4 ${
                        requestState === 'submitted' ? 'text-green-600' :
                        requestState === 'viewed' ? 'text-purple-600' :
                        requestState === 'requested' ? 'text-blue-600' :
                        'text-gray-500'
                      }`} />
                      <span className="text-sm font-medium">
                        {requestState === 'submitted' ? 'Response submitted' :
                         requestState === 'viewed' ? 'Request viewed' :
                         requestState === 'requested' ? 'Request sent' :
                         requestState === 'replacement_requested' ? 'Replacement requested' :
                         'Request status'}
                      </span>
                    </div>
                    {latestRequest.sent_at && (
                      <span className="text-xs text-text-muted">
                        {formatBackendDate(latestRequest.sent_at, { format: 'relative' })}
                      </span>
                    )}
                  </div>
                  {latestRequest.viewed_at && requestState !== 'viewed' && (
                    <p className="text-xs text-text-muted mt-1 ml-6">
                      Viewed {formatBackendDate(latestRequest.viewed_at, { format: 'relative' })}
                    </p>
                  )}
                  {latestRequest.reminder_count > 0 && (
                    <p className="text-xs text-amber-600 mt-1 ml-6">
                      {latestRequest.reminder_count} reminder{latestRequest.reminder_count !== 1 ? 's' : ''} sent
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ============================================== */}
        {/* ROW B: VERIFICATION SECTION                    */}
        {/* Only show for RTW and DBS - these require admin to upload proof */}
        {/* Identity and PoA just need admin confirmation, no separate upload */}
        {/* ============================================== */}
        {(key === 'right_to_work' || key === 'dbs') && (
        <div 
          className={`border rounded-xl overflow-hidden ${
            checkVerified ? 'border-green-200 bg-green-50/20' : 
            hasCheck ? 'border-amber-200 bg-amber-50/20' : 
            'border-red-200 bg-red-50/20'
          }`}
          data-testid={`${key}-verification-row`}
        >
          {/* Verification Row Header */}
          <div 
            className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/50 transition-colors"
            onClick={() => setVerificationExpanded(!verificationExpanded)}
          >
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                checkVerified ? 'bg-green-100' : hasCheck ? 'bg-amber-100' : 'bg-red-100'
              }`}>
                <Shield className={`h-4 w-4 ${
                  checkVerified ? 'text-green-600' : hasCheck ? 'text-amber-600' : 'text-red-600'
                }`} />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-text-primary">
                  Verification Proof
                  <span className="text-xs font-normal text-gray-500 ml-1">(Admin uploads)</span>
                </h4>
                <p className="text-xs text-text-muted">
                  {checkVerified 
                    ? 'Check verified'
                    : hasCheck 
                      ? `Check recorded: ${getOutcomeDisplay(checkData.outcome)}`
                      : key === 'right_to_work' 
                        ? 'Upload Home Office check result'
                        : 'Upload DBS Update Service check'
                  }
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={`text-[10px] px-1.5 py-0 ${
                checkVerified ? 'bg-green-100 text-green-700 border border-green-200' :
                hasCheck ? 'bg-amber-100 text-amber-700 border border-amber-200' :
                'bg-red-100 text-red-700 border border-red-200'
              }`}>
                {checkVerified ? 'Verified' : hasCheck ? 'Recorded' : 'Required'}
              </Badge>
              <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                {verificationExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>
          </div>

          {/* Verification Row Content */}
          {verificationExpanded && (
            <div className="p-3 pt-0 space-y-3">
              {/* Verification Check Details */}
              {hasCheck ? (
                <div className="space-y-3">
                  {/* Check Record Details */}
                  <div className={`p-3 rounded-lg border ${
                    checkVerified ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'
                  }`}>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      {/* Method */}
                      <div>
                        <p className="text-xs text-text-muted uppercase tracking-wide">Method</p>
                        <p className="font-medium text-text-primary">{getMethodDisplay(checkData.method)}</p>
                      </div>
                      
                      {/* Outcome */}
                      <div>
                        <p className="text-xs text-text-muted uppercase tracking-wide">Outcome</p>
                        <p className={`font-medium ${
                          checkData.outcome === 'verified' ? 'text-green-600' :
                          checkData.outcome === 'failed' ? 'text-red-600' : 'text-amber-600'
                        }`}>
                          {getOutcomeDisplay(checkData.outcome)}
                        </p>
                      </div>
                      
                      {/* Checked At */}
                      <div>
                        <p className="text-xs text-text-muted uppercase tracking-wide">Checked</p>
                        <p className="font-medium text-text-primary">
                          {formatBackendDate(checkData.checked_at, { format: 'medium' })}
                        </p>
                      </div>
                      
                      {/* Checked By */}
                      <div>
                        <p className="text-xs text-text-muted uppercase tracking-wide">Checked By</p>
                        <p className="font-medium text-text-primary">
                          {getUserDisplayName(checkData.checked_by, checkData.checked_by_name)}
                        </p>
                      </div>
                    </div>
                    
                    {/* Notes */}
                    {checkData.notes && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <p className="text-xs text-text-muted uppercase tracking-wide mb-1">Notes</p>
                        <p className="text-sm text-text-primary">{checkData.notes}</p>
                      </div>
                    )}
                    
                    {/* RTW Result Details - COMPREHENSIVE DISPLAY */}
                    {key === 'right_to_work' && (
                      <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4 text-slate-600" />
                          <p className="text-xs text-text-muted uppercase tracking-wide font-semibold">Right to Work Result</p>
                        </div>
                        
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                          {/* Permission Type - NEW */}
                          {(checkData.permission_type || checkData.document_type) && (
                            <div className="col-span-2 md:col-span-3">
                              <p className="text-xs text-text-muted">Permission Type</p>
                              <p className="font-semibold text-text-primary text-base">
                                {checkData.permission_type || checkData.document_type || 'Not specified'}
                              </p>
                            </div>
                          )}
                          
                          {/* Route / Check Type */}
                          {(checkData.route || checkData.method) && (
                            <div>
                              <p className="text-xs text-text-muted">Verification Method</p>
                              <p className="font-medium text-text-primary">{getMethodDisplay(checkData.route || checkData.method)}</p>
                            </div>
                          )}
                          
                          {/* Permission Start */}
                          {checkData.permission_start_date && (
                            <div>
                              <p className="text-xs text-text-muted">Permission Start</p>
                              <p className="font-medium text-text-primary">{formatBackendDate(checkData.permission_start_date, { format: 'medium' })}</p>
                            </div>
                          )}
                          
                          {/* Permission End / Expiry OR No Expiry */}
                          <div>
                            <p className="text-xs text-text-muted">Permission Expiry</p>
                            {checkData.is_indefinite ? (
                              <p className="font-medium text-green-700 flex items-center gap-1">
                                <CheckCircle className="h-3 w-3" />
                                No Expiry (Indefinite)
                              </p>
                            ) : checkData.permission_end_date ? (
                              <p className={`font-medium ${
                                rtwStatus?.status === 'expired' ? 'text-red-700' :
                                rtwStatus?.days_until_expiry <= 30 ? 'text-red-600' :
                                rtwStatus?.days_until_expiry <= 90 ? 'text-amber-600' :
                                'text-text-primary'
                              }`}>
                                {formatBackendDate(checkData.permission_end_date, { format: 'medium' })}
                                {rtwStatus?.days_until_expiry !== null && rtwStatus?.days_until_expiry > 0 && (
                                  <span className="text-xs ml-1">({rtwStatus.days_until_expiry}d)</span>
                                )}
                              </p>
                            ) : (
                              <p className="font-medium text-amber-600">Not specified</p>
                            )}
                          </div>
                          
                          {/* Share Code */}
                          {checkData.share_code && (
                            <div>
                              <p className="text-xs text-text-muted">Share Code</p>
                              <p className="font-medium text-text-primary font-mono text-xs bg-slate-100 px-2 py-1 rounded inline-block">{checkData.share_code}</p>
                            </div>
                          )}
                          
                          {/* Reference Number / PVN */}
                          {checkData.reference_number && (
                            <div>
                              <p className="text-xs text-text-muted">Reference / PVN</p>
                              <p className="font-medium text-text-primary font-mono text-xs bg-slate-100 px-2 py-1 rounded inline-block">{checkData.reference_number}</p>
                            </div>
                          )}
                          
                          {/* Checked Date */}
                          {checkData.checked_at && (
                            <div>
                              <p className="text-xs text-text-muted">Verification Date</p>
                              <p className="font-medium text-text-primary">{formatBackendDate(checkData.checked_at, { format: 'medium' })}</p>
                            </div>
                          )}
                        </div>
                        
                        {/* Follow-up Section - Critical for time-limited permissions */}
                        {(checkData.follow_up_required || checkData.follow_up_due_at) && (
                          <div className={`p-3 rounded-lg border ${
                            rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup < 0 ? 'bg-red-50 border-red-200' :
                            rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup <= 30 ? 'bg-amber-50 border-amber-200' :
                            'bg-blue-50 border-blue-200'
                          }`}>
                            <div className="flex items-center gap-2 mb-1">
                              <Clock className={`h-4 w-4 ${
                                rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup < 0 ? 'text-red-600' :
                                rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup <= 30 ? 'text-amber-600' :
                                'text-blue-600'
                              }`} />
                              <span className={`text-xs font-semibold ${
                                rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup < 0 ? 'text-red-800' :
                                rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup <= 30 ? 'text-amber-800' :
                                'text-blue-800'
                              }`}>
                                {rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup < 0 ? 'FOLLOW-UP OVERDUE' : 'Follow-up Required'}
                              </span>
                            </div>
                            <p className={`text-sm font-medium ${
                              rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup < 0 ? 'text-red-700' :
                              rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup <= 30 ? 'text-amber-700' :
                              'text-blue-700'
                            }`}>
                              {checkData.follow_up_due_at ? (
                                <>
                                  Due: {formatBackendDate(checkData.follow_up_due_at, { format: 'medium' })}
                                  {rtwStatus?.days_until_followup !== null && (
                                    <span className="ml-2">
                                      ({rtwStatus.days_until_followup < 0 ? `${Math.abs(rtwStatus.days_until_followup)} days overdue` : `${rtwStatus.days_until_followup} days`})
                                    </span>
                                  )}
                                </>
                              ) : (
                                'Date not set'
                              )}
                            </p>
                          </div>
                        )}
                        
                        {/* Restrictions - Collapsible to reduce visual noise */}
                        {checkData.restrictions && (
                          <details className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                            <summary className="flex items-center gap-2 cursor-pointer list-none">
                              <AlertTriangle className="h-4 w-4 text-amber-600" />
                              <span className="text-xs font-semibold text-amber-800">Work Restrictions Apply</span>
                              {checkData.hours_limit && (
                                <Badge className="text-[10px] bg-amber-100 text-amber-700 border-amber-300">
                                  {checkData.hours_limit}hrs/week
                                </Badge>
                              )}
                              <span className="text-xs text-amber-600 ml-auto">Click to expand</span>
                            </summary>
                            <div className="mt-2 pt-2 border-t border-amber-200">
                              <p className="text-sm text-amber-700">{checkData.restrictions}</p>
                            </div>
                          </details>
                        )}
                        
                        {/* Status flags */}
                        <div className="flex flex-wrap gap-2">
                          {checkData.is_indefinite && (
                            <div className="flex items-center gap-1 px-2 py-1 bg-green-50 border border-green-200 rounded-lg">
                              <CheckCircle className="h-3 w-3 text-green-600" />
                              <span className="text-xs font-medium text-green-700">Indefinite right to work</span>
                            </div>
                          )}
                          {checkData.outcome === 'verified' && !checkData.is_indefinite && (
                            <div className="flex items-center gap-1 px-2 py-1 bg-blue-50 border border-blue-200 rounded-lg">
                              <Shield className="h-3 w-3 text-blue-600" />
                              <span className="text-xs font-medium text-blue-700">Time-limited permission</span>
                            </div>
                          )}
                        </div>
                        
                        {/* RTW STATUS ALERT PANEL - Non-breaking, read-only display */}
                        {rtwStatus && rtwStatus.status !== 'not_verified' && (
                          <div className={`p-3 rounded-lg border ${
                            rtwStatus.status_color === 'green' ? 'bg-green-50 border-green-200' :
                            rtwStatus.status_color === 'amber' ? 'bg-amber-50 border-amber-200' :
                            rtwStatus.status_color === 'red' ? 'bg-red-50 border-red-200' :
                            'bg-gray-50 border-gray-200'
                          }`}>
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                {rtwStatus.status_color === 'green' && <CheckCircle className="h-4 w-4 text-green-600" />}
                                {rtwStatus.status_color === 'amber' && <AlertTriangle className="h-4 w-4 text-amber-600" />}
                                {rtwStatus.status_color === 'red' && <AlertTriangle className="h-4 w-4 text-red-600" />}
                                <span className={`text-sm font-semibold ${
                                  rtwStatus.status_color === 'green' ? 'text-green-800' :
                                  rtwStatus.status_color === 'amber' ? 'text-amber-800' :
                                  rtwStatus.status_color === 'red' ? 'text-red-800' :
                                  'text-gray-800'
                                }`}>
                                  {rtwStatus.status_label}
                                </span>
                              </div>
                              {rtwStatus.days_until_expiry !== null && rtwStatus.days_until_expiry > 0 && (
                                <Badge className={`text-[10px] ${
                                  rtwStatus.days_until_expiry <= 30 ? 'bg-red-100 text-red-700 border-red-200' :
                                  rtwStatus.days_until_expiry <= 90 ? 'bg-amber-100 text-amber-700 border-amber-200' :
                                  'bg-green-100 text-green-700 border-green-200'
                                }`}>
                                  {rtwStatus.days_until_expiry} days
                                </Badge>
                              )}
                            </div>
                            
                            {/* Alerts */}
                            {rtwStatus.alerts && rtwStatus.alerts.length > 0 && (
                              <div className="space-y-1">
                                {rtwStatus.alerts.map((alert, idx) => (
                                  <p key={idx} className={`text-xs ${
                                    alert.level === 'error' || alert.level === 'urgent' ? 'text-red-700' :
                                    alert.level === 'warning' ? 'text-amber-700' :
                                    'text-gray-600'
                                  }`}>
                                    {alert.message}
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* DBS Result Details - COMPREHENSIVE DISPLAY */}
                    {key === 'dbs' && (
                      <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4 text-slate-600" />
                          <p className="text-xs text-text-muted uppercase tracking-wide font-semibold">DBS Result</p>
                        </div>
                        
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                          {/* DBS Level */}
                          {checkData.dbs_level && (
                            <div>
                              <p className="text-xs text-text-muted">DBS Level</p>
                              <p className="font-medium text-text-primary capitalize">{checkData.dbs_level.replace(/_/g, ' ')}</p>
                            </div>
                          )}
                          
                          {/* Certificate Number */}
                          {checkData.certificate_number && (
                            <div>
                              <p className="text-xs text-text-muted">Certificate Number</p>
                              <p className="font-medium text-text-primary font-mono text-xs">{checkData.certificate_number}</p>
                            </div>
                          )}
                          
                          {/* Certificate Issue Date */}
                          {checkData.certificate_issue_date && (
                            <div>
                              <p className="text-xs text-text-muted">Issue Date</p>
                              <p className="font-medium text-text-primary">{formatBackendDate(checkData.certificate_issue_date, { format: 'medium' })}</p>
                            </div>
                          )}
                          
                          {/* Workforce */}
                          {checkData.workforce && (
                            <div>
                              <p className="text-xs text-text-muted">Workforce</p>
                              <p className="font-medium text-text-primary capitalize">{checkData.workforce.replace(/_/g, ' ')}</p>
                            </div>
                          )}
                          
                          {/* Name on Certificate */}
                          {checkData.name_on_certificate && (
                            <div>
                              <p className="text-xs text-text-muted">Name on Certificate</p>
                              <p className="font-medium text-text-primary">{checkData.name_on_certificate}</p>
                            </div>
                          )}
                          
                          {/* Next Recheck Date */}
                          {(checkData.next_recheck_date || checkData.review_due_at) && (
                            <div>
                              <p className="text-xs text-text-muted">Next Recheck</p>
                              <p className="font-medium text-amber-700">{formatBackendDate(checkData.next_recheck_date || checkData.review_due_at, { format: 'medium' })}</p>
                            </div>
                          )}
                        </div>
                        
                        {/* Update Service Section */}
                        {(checkData.update_service_registered || checkData.update_service_status) && (
                          <div className="p-2 bg-indigo-50 border border-indigo-200 rounded-lg">
                            <p className="text-xs text-indigo-800 font-medium mb-1">Update Service</p>
                            <div className="flex flex-wrap gap-2">
                              <span className={`text-xs px-2 py-0.5 rounded ${
                                checkData.update_service_status === 'active' 
                                  ? 'bg-green-100 text-green-700' 
                                  : 'bg-gray-100 text-gray-700'
                              }`}>
                                {checkData.update_service_status === 'active' ? 'Registered' : 'Not Registered'}
                              </span>
                              {checkData.last_status_check_date && (
                                <span className="text-xs text-indigo-600">
                                  Last checked: {formatBackendDate(checkData.last_status_check_date, { format: 'short' })}
                                </span>
                              )}
                              {checkData.update_service_check_result && (
                                <span className={`text-xs px-2 py-0.5 rounded ${
                                  checkData.update_service_check_result === 'no_change' 
                                    ? 'bg-green-100 text-green-700' 
                                    : 'bg-red-100 text-red-700'
                                }`}>
                                  {checkData.update_service_check_result === 'no_change' ? 'No change' : 'Changes detected'}
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* Result Status */}
                        {checkData.result_status && (
                          <div className={`p-2 rounded-lg ${
                            checkData.result_status === 'clear' ? 'bg-green-50 border border-green-200' :
                            checkData.result_status === 'information_present' ? 'bg-amber-50 border border-amber-200' :
                            'bg-gray-50 border border-gray-200'
                          }`}>
                            <p className={`text-xs font-medium ${
                              checkData.result_status === 'clear' ? 'text-green-800' :
                              checkData.result_status === 'information_present' ? 'text-amber-800' :
                              'text-gray-800'
                            }`}>
                              {checkData.result_status === 'clear' ? 'Clear - No information disclosed' :
                               checkData.result_status === 'information_present' ? 'Information Present - Review Required' :
                               'Pending Review'}
                            </p>
                            {checkData.result_summary && (
                              <p className="text-xs text-gray-600 mt-1">{checkData.result_summary}</p>
                            )}
                          </div>
                        )}
                        
                        {/* Information Present Warning */}
                        {checkData.information_present && (
                          <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg">
                            <div className="flex items-start gap-2">
                              <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                              <div>
                                <p className="text-xs text-amber-800 font-medium">Information/disclosures present</p>
                                <p className="text-xs text-amber-700 mt-0.5">Review notes for risk assessment details.</p>
                              </div>
                            </div>
                          </div>
                        )}
                        
                        {/* Status flags */}
                        <div className="flex flex-wrap gap-2">
                          {checkData.recheck_required !== false && (
                            <div className="flex items-center gap-1 px-2 py-1 bg-blue-50 border border-blue-200 rounded-lg">
                              <Clock className="h-3 w-3 text-blue-600" />
                              <span className="text-xs font-medium text-blue-700">Recheck required (policy)</span>
                            </div>
                          )}
                        </div>
                        
                        {/* DBS STATUS ALERT PANEL - Non-breaking, read-only display */}
                        {checkData.dbs_status && checkData.dbs_status.status !== 'not_verified' && (
                          <div className={`p-3 rounded-lg border ${
                            checkData.dbs_status.status_color === 'green' ? 'bg-green-50 border-green-200' :
                            checkData.dbs_status.status_color === 'amber' ? 'bg-amber-50 border-amber-200' :
                            checkData.dbs_status.status_color === 'red' ? 'bg-red-50 border-red-200' :
                            'bg-gray-50 border-gray-200'
                          }`}>
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                {checkData.dbs_status.status_color === 'green' && <CheckCircle className="h-4 w-4 text-green-600" />}
                                {checkData.dbs_status.status_color === 'amber' && <AlertTriangle className="h-4 w-4 text-amber-600" />}
                                {checkData.dbs_status.status_color === 'red' && <AlertTriangle className="h-4 w-4 text-red-600" />}
                                <span className={`text-sm font-semibold ${
                                  checkData.dbs_status.status_color === 'green' ? 'text-green-800' :
                                  checkData.dbs_status.status_color === 'amber' ? 'text-amber-800' :
                                  checkData.dbs_status.status_color === 'red' ? 'text-red-800' :
                                  'text-gray-800'
                                }`}>
                                  {checkData.dbs_status.status_label}
                                </span>
                              </div>
                              {checkData.dbs_status.days_until_recheck !== null && checkData.dbs_status.days_until_recheck > 0 && (
                                <Badge className={`text-[10px] ${
                                  checkData.dbs_status.days_until_recheck <= 30 ? 'bg-red-100 text-red-700 border-red-200' :
                                  checkData.dbs_status.days_until_recheck <= 90 ? 'bg-amber-100 text-amber-700 border-amber-200' :
                                  'bg-green-100 text-green-700 border-green-200'
                                }`}>
                                  {checkData.dbs_status.days_until_recheck} days
                                </Badge>
                              )}
                            </div>
                            
                            {/* Alerts */}
                            {checkData.dbs_status.alerts && checkData.dbs_status.alerts.length > 0 && (
                              <div className="space-y-1">
                                {checkData.dbs_status.alerts.map((alert, idx) => (
                                  <p key={idx} className={`text-xs ${
                                    alert.level === 'error' || alert.level === 'urgent' ? 'text-red-700' :
                                    alert.level === 'warning' ? 'text-amber-700' :
                                    'text-gray-600'
                                  }`}>
                                    {alert.message}
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Identity Result Details - COMPREHENSIVE DISPLAY */}
                    {key === 'identity' && (
                      <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4 text-slate-600" />
                          <p className="text-xs text-text-muted uppercase tracking-wide font-semibold">Identity Verification Result</p>
                        </div>
                        
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                          {/* Document Type */}
                          {checkData.document_type && (
                            <div>
                              <p className="text-xs text-text-muted">Document Type</p>
                              <p className="font-medium text-text-primary capitalize">{checkData.document_type.replace(/_/g, ' ')}</p>
                            </div>
                          )}
                          
                          {/* Full Name on Document */}
                          {checkData.full_name_on_document && (
                            <div className="col-span-2">
                              <p className="text-xs text-text-muted">Name on Document</p>
                              <p className="font-medium text-text-primary">{checkData.full_name_on_document}</p>
                            </div>
                          )}
                          
                          {/* Document Number */}
                          {checkData.document_number && (
                            <div>
                              <p className="text-xs text-text-muted">Document Number</p>
                              <p className="font-medium text-text-primary font-mono text-xs">{checkData.document_number}</p>
                            </div>
                          )}
                          
                          {/* Date of Birth */}
                          {checkData.date_of_birth && (
                            <div>
                              <p className="text-xs text-text-muted">Date of Birth</p>
                              <p className="font-medium text-text-primary">{formatBackendDate(checkData.date_of_birth, { format: 'medium' })}</p>
                            </div>
                          )}
                          
                          {/* Nationality */}
                          {checkData.nationality && (
                            <div>
                              <p className="text-xs text-text-muted">Nationality</p>
                              <p className="font-medium text-text-primary">{checkData.nationality}</p>
                            </div>
                          )}
                          
                          {/* Issue Date */}
                          {checkData.issue_date && (
                            <div>
                              <p className="text-xs text-text-muted">Issue Date</p>
                              <p className="font-medium text-text-primary">{formatBackendDate(checkData.issue_date, { format: 'medium' })}</p>
                            </div>
                          )}
                          
                          {/* Expiry Date */}
                          {checkData.expiry_date && (
                            <div>
                              <p className="text-xs text-text-muted">Expiry Date</p>
                              <p className={`font-medium ${
                                checkData.identity_status?.status === 'expired' ? 'text-red-700' :
                                checkData.identity_status?.days_until_expiry <= 30 ? 'text-amber-600' :
                                'text-text-primary'
                              }`}>
                                {formatBackendDate(checkData.expiry_date, { format: 'medium' })}
                                {checkData.identity_status?.days_until_expiry !== null && checkData.identity_status?.days_until_expiry > 0 && (
                                  <span className="text-xs ml-1">({checkData.identity_status.days_until_expiry}d)</span>
                                )}
                              </p>
                            </div>
                          )}
                        </div>
                        
                        {/* Verification Match Checks */}
                        <div className="p-2 bg-slate-50 border border-slate-200 rounded-lg">
                          <p className="text-xs text-slate-700 font-medium mb-2">Verification Checks</p>
                          <div className="flex flex-wrap gap-3">
                            <div className="flex items-center gap-1">
                              {checkData.name_matches_application ? (
                                <CheckCircle className="h-3.5 w-3.5 text-green-600" />
                              ) : (
                                <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                              )}
                              <span className={`text-xs ${checkData.name_matches_application ? 'text-green-700' : 'text-amber-700'}`}>
                                Name {checkData.name_matches_application ? 'matches' : 'mismatch'}
                              </span>
                            </div>
                            <div className="flex items-center gap-1">
                              {checkData.dob_matches_application ? (
                                <CheckCircle className="h-3.5 w-3.5 text-green-600" />
                              ) : (
                                <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                              )}
                              <span className={`text-xs ${checkData.dob_matches_application ? 'text-green-700' : 'text-amber-700'}`}>
                                DOB {checkData.dob_matches_application ? 'matches' : 'mismatch'}
                              </span>
                            </div>
                            <div className="flex items-center gap-1">
                              {checkData.photo_match_confirmed ? (
                                <CheckCircle className="h-3.5 w-3.5 text-green-600" />
                              ) : (
                                <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                              )}
                              <span className={`text-xs ${checkData.photo_match_confirmed ? 'text-green-700' : 'text-amber-700'}`}>
                                Photo {checkData.photo_match_confirmed ? 'verified' : 'not verified'}
                              </span>
                            </div>
                          </div>
                        </div>
                        
                        {/* Identity Status Alert Panel */}
                        {checkData.identity_status && checkData.identity_status.status !== 'not_verified' && (
                          <div className={`p-3 rounded-lg border ${
                            checkData.identity_status.status_color === 'green' ? 'bg-green-50 border-green-200' :
                            checkData.identity_status.status_color === 'amber' ? 'bg-amber-50 border-amber-200' :
                            checkData.identity_status.status_color === 'red' ? 'bg-red-50 border-red-200' :
                            'bg-gray-50 border-gray-200'
                          }`}>
                            <div className="flex items-center gap-2">
                              {checkData.identity_status.status_color === 'green' && <CheckCircle className="h-4 w-4 text-green-600" />}
                              {checkData.identity_status.status_color === 'amber' && <AlertTriangle className="h-4 w-4 text-amber-600" />}
                              {checkData.identity_status.status_color === 'red' && <AlertTriangle className="h-4 w-4 text-red-600" />}
                              <span className={`text-sm font-semibold ${
                                checkData.identity_status.status_color === 'green' ? 'text-green-800' :
                                checkData.identity_status.status_color === 'amber' ? 'text-amber-800' :
                                checkData.identity_status.status_color === 'red' ? 'text-red-800' :
                                'text-gray-800'
                              }`}>
                                {checkData.identity_status.status_label}
                              </span>
                            </div>
                            
                            {/* Alerts */}
                            {checkData.identity_status.alerts && checkData.identity_status.alerts.length > 0 && (
                              <div className="space-y-1 mt-2">
                                {checkData.identity_status.alerts.map((alert, idx) => (
                                  <p key={idx} className={`text-xs ${
                                    alert.level === 'error' || alert.level === 'urgent' ? 'text-red-700' :
                                    alert.level === 'warning' ? 'text-amber-700' :
                                    'text-gray-600'
                                  }`}>
                                    {alert.message}
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Proof of Address Result Details - COMPREHENSIVE DISPLAY */}
                    {key === 'proof_of_address' && (
                      <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4 text-slate-600" />
                          <p className="text-xs text-text-muted uppercase tracking-wide font-semibold">Address Verification Result</p>
                        </div>
                        
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                          {/* Document Count */}
                          <div>
                            <p className="text-xs text-text-muted">Documents Verified</p>
                            <p className={`font-semibold ${
                              (checkData.documents_received_count || 0) >= (checkData.documents_required_count || 2) 
                                ? 'text-green-700' 
                                : 'text-amber-700'
                            }`}>
                              {checkData.documents_received_count || 0} / {checkData.documents_required_count || 2}
                            </p>
                          </div>
                          
                          {/* Recency Status */}
                          <div>
                            <p className="text-xs text-text-muted">Document Recency</p>
                            <p className={`font-medium ${
                              checkData.all_documents_sufficiently_recent ? 'text-green-700' : 'text-amber-700'
                            }`}>
                              {checkData.all_documents_sufficiently_recent ? 'All within limits' : 'Contains outdated'}
                            </p>
                          </div>
                          
                          {/* Address Match */}
                          <div>
                            <p className="text-xs text-text-muted">Address Match</p>
                            <p className={`font-medium ${
                              checkData.address_matches_application ? 'text-green-700' : 'text-amber-700'
                            }`}>
                              {checkData.address_matches_application ? 'Matches application' : 'Needs review'}
                            </p>
                          </div>
                        </div>
                        
                        {/* Extracted Address */}
                        {(checkData.extracted_address_line1 || checkData.extracted_postcode) && (
                          <div className="p-2 bg-slate-50 border border-slate-200 rounded-lg">
                            <p className="text-xs text-slate-700 font-medium mb-1">Verified Address</p>
                            <div className="text-sm text-text-primary">
                              {checkData.extracted_address_line1 && <p>{checkData.extracted_address_line1}</p>}
                              {checkData.extracted_address_line2 && <p>{checkData.extracted_address_line2}</p>}
                              {(checkData.extracted_city || checkData.extracted_postcode) && (
                                <p>
                                  {checkData.extracted_city && <span>{checkData.extracted_city}</span>}
                                  {checkData.extracted_city && checkData.extracted_postcode && <span>, </span>}
                                  {checkData.extracted_postcode && <span className="font-mono">{checkData.extracted_postcode}</span>}
                                </p>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* Verified Documents List */}
                        {checkData.verified_documents && checkData.verified_documents.length > 0 && (
                          <div className="space-y-2">
                            <p className="text-xs text-text-muted uppercase tracking-wide">Verified Documents</p>
                            {checkData.verified_documents.map((doc, idx) => (
                              <div key={idx} className={`p-2 rounded-lg border ${
                                doc.is_valid || doc.recency_status === 'valid' 
                                  ? 'bg-green-50 border-green-200' 
                                  : 'bg-amber-50 border-amber-200'
                              }`}>
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <FileText className={`h-3.5 w-3.5 ${
                                      doc.is_valid || doc.recency_status === 'valid' ? 'text-green-600' : 'text-amber-600'
                                    }`} />
                                    <span className="text-sm font-medium capitalize">
                                      {(doc.type || doc.document_type || 'Document').replace(/_/g, ' ')}
                                    </span>
                                  </div>
                                  <Badge className={`text-[10px] ${
                                    doc.is_valid || doc.recency_status === 'valid'
                                      ? 'bg-green-100 text-green-700 border-green-200'
                                      : 'bg-amber-100 text-amber-700 border-amber-200'
                                  }`}>
                                    {doc.is_valid || doc.recency_status === 'valid' ? 'Valid' : doc.recency_status || 'Review needed'}
                                  </Badge>
                                </div>
                                {doc.issue_date && (
                                  <p className="text-xs text-text-muted mt-1 ml-5">
                                    Dated: {formatBackendDate(doc.issue_date, { format: 'medium' })}
                                    {doc.months_old !== undefined && <span className="ml-1">({doc.months_old} months old)</span>}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                        
                        {/* Address Status Alert Panel */}
                        {checkData.address_status && checkData.address_status.status !== 'not_verified' && (
                          <div className={`p-3 rounded-lg border ${
                            checkData.address_status.status_color === 'green' ? 'bg-green-50 border-green-200' :
                            checkData.address_status.status_color === 'amber' ? 'bg-amber-50 border-amber-200' :
                            checkData.address_status.status_color === 'red' ? 'bg-red-50 border-red-200' :
                            'bg-gray-50 border-gray-200'
                          }`}>
                            <div className="flex items-center gap-2">
                              {checkData.address_status.status_color === 'green' && <CheckCircle className="h-4 w-4 text-green-600" />}
                              {checkData.address_status.status_color === 'amber' && <AlertTriangle className="h-4 w-4 text-amber-600" />}
                              {checkData.address_status.status_color === 'red' && <AlertTriangle className="h-4 w-4 text-red-600" />}
                              <span className={`text-sm font-semibold ${
                                checkData.address_status.status_color === 'green' ? 'text-green-800' :
                                checkData.address_status.status_color === 'amber' ? 'text-amber-800' :
                                checkData.address_status.status_color === 'red' ? 'text-red-800' :
                                'text-gray-800'
                              }`}>
                                {checkData.address_status.status_label}
                              </span>
                            </div>
                            
                            {/* Alerts */}
                            {checkData.address_status.alerts && checkData.address_status.alerts.length > 0 && (
                              <div className="space-y-1 mt-2">
                                {checkData.address_status.alerts.map((alert, idx) => (
                                  <p key={idx} className={`text-xs ${
                                    alert.level === 'error' || alert.level === 'urgent' ? 'text-red-700' :
                                    alert.level === 'warning' ? 'text-amber-700' :
                                    'text-gray-600'
                                  }`}>
                                    {alert.message}
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* VERIFICATION PROOF FILE SECTION */}
                  <div className="space-y-2">
                    <p className="text-xs text-text-muted uppercase tracking-wide font-medium">
                      Proof of Check
                    </p>
                    
                    {hasVerificationProof ? (
                      <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                            <FileText className="h-5 w-5 text-green-600" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-green-800">
                              {checkData.evidence_document.filename || 'Verification Proof'}
                            </p>
                            <p className="text-xs text-green-600">
                              Uploaded {formatBackendDate(checkData.evidence_document.uploaded_at, { format: 'medium' })}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          {/* View Proof */}
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-8 w-8 p-0 text-green-600 hover:text-green-700 hover:bg-green-100"
                            onClick={handleViewProof}
                            title="View proof"
                            data-testid={`${key}-verification-view-proof`}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          
                          {/* Download Proof */}
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-8 w-8 p-0 text-green-600 hover:text-green-700 hover:bg-green-100"
                            onClick={handleDownloadProof}
                            title="Download proof"
                            data-testid={`${key}-verification-download-proof`}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ) : (
                      /* No proof file - show softer warning if check is already verified */
                      <div className={`flex items-center gap-2 p-3 rounded-lg border ${
                        checkVerified 
                          ? 'bg-blue-50 border-blue-200'  // Softer: check verified but proof missing
                          : 'bg-amber-50 border-amber-200' // Stronger: need proof to complete
                      }`}>
                        {checkVerified ? (
                          <FileText className="h-5 w-5 text-blue-600 flex-shrink-0" />
                        ) : (
                          <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0" />
                        )}
                        <div className="flex-1">
                          <p className={`text-sm font-medium ${checkVerified ? 'text-blue-800' : 'text-amber-800'}`}>
                            {checkVerified ? 'Proof file recommended' : 'Proof file required'}
                          </p>
                          <p className={`text-xs ${checkVerified ? 'text-blue-600' : 'text-amber-600'}`}>
                            {checkVerified 
                              ? 'Upload proof documentation to strengthen audit trail.'
                              : 'Upload proof of check (e.g., Home Office screenshot) for compliance.'}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                /* No Check Recorded State */
                <div className="p-4 bg-white border border-gray-200 rounded-lg text-center">
                  <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-2" />
                  <p className="text-sm font-medium text-text-primary mb-1">No check recorded</p>
                  <p className="text-xs text-text-muted mb-3">
                    Record a verification check with proof to complete this requirement.
                  </p>
                </div>
              )}

              {/* Verification Actions - GATED BY WORKFLOW STEP */}
              {!isAuditor && (
                <div className="flex flex-col gap-2 pt-2 border-t border-gray-100">
                  {/* Show workflow gate message if trying to act out of order */}
                  {isRTWOrDBS && workflowStep && workflowStep.step < 3 && (
                    <div className="flex items-center gap-2 p-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
                      <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
                      <span>
                        {workflowStep.step === 1 
                          ? 'Upload evidence before recording check'
                          : 'Accept at least one evidence file first'}
                      </span>
                    </div>
                  )}
                  
                  <div className="flex items-center gap-2">
                    {/* Record Check / Update Check Button */}
                    {!hasCheck ? (
                      <Button
                        size="sm"
                        variant="default"
                        onClick={() => onRecordCheck && onRecordCheck(key)}
                        disabled={isRTWOrDBS && (!hasAcceptedEvidence)}
                        className={`h-8 text-xs rounded-lg ${
                          isRTWOrDBS && !hasAcceptedEvidence 
                            ? 'bg-gray-300 cursor-not-allowed' 
                            : 'bg-primary hover:bg-primary-hover text-white'
                        }`}
                        title={isRTWOrDBS && !hasAcceptedEvidence ? 'Accept evidence first' : 'Record verification check'}
                        data-testid={`${key}-verification-record-check-btn`}
                      >
                        <Shield className="h-3.5 w-3.5 mr-1" />
                        Record Check
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onUpdateCheck && onUpdateCheck(key)}
                        className="h-8 text-xs rounded-lg"
                        data-testid={`${key}-verification-update-check-btn`}
                      >
                        <RefreshCw className="h-3.5 w-3.5 mr-1" />
                        Update Check
                      </Button>
                    )}
                    
                    {/* Upload Proof Button - Separate from Record Check */}
                    {hasCheck && !hasVerificationProof && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onUpdateCheck && onUpdateCheck(key)}
                        className="h-8 text-xs rounded-lg border-blue-200 text-blue-600 hover:bg-blue-50"
                        data-testid={`${key}-verification-upload-proof-btn`}
                      >
                        <UploadIcon className="h-3.5 w-3.5 mr-1" />
                        Upload Proof
                      </Button>
                    )}
                    
                    {/* Manage Documents - Combined button for all document management */}
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={onOpenDrawer}
                      className="h-8 text-xs rounded-lg"
                      data-testid={`${key}-manage-all-btn`}
                    >
                      <Eye className="h-3.5 w-3.5 mr-1" />
                      Manage
                    </Button>
                    
                    {/* CONFIRM & STAMP ALL - Only shows at Step 5 */}
                    {hasCheck && hasFiles && hasAcceptedEvidence && !activeFiles.every(f => f.verification_stamp) && (
                      <Button
                        size="sm"
                        variant="default"
                        disabled={stampingAll}
                        onClick={() => {
                          // Check if proof is uploaded - warn if not
                          const confirmMsg = hasVerificationProof
                            ? `This will apply Osabea verification stamps to:\n\n` +
                              `• ${activeFiles.filter(f => !f.verification_stamp).length} evidence document(s)\n` +
                              `• Verification proof\n\n` +
                              `Stamps are permanent.\n\nContinue?`
                            : `⚠️ No proof file uploaded!\n\n` +
                              `It's recommended to upload proof (e.g., Home Office screenshot) before stamping.\n\n` +
                              `Continue anyway?`;
                          
                          setStampAllDialog({
                            open: true,
                            message: confirmMsg,
                            files: activeFiles.filter(f => !f.verification_stamp)
                          });
                        }}
                        className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg"
                        data-testid={`${key}-confirm-stamp-all-btn`}
                      >
                        {stampingAll ? (
                          <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                        ) : (
                          <Stamp className="h-3.5 w-3.5 mr-1" />
                        )}
                        {stampingAll ? 'Stamping...' : 'Confirm & Stamp'}
                      </Button>
                    )}
                    
                    {/* Show "Complete" badge when everything is done */}
                    {hasCheck && hasFiles && activeFiles.every(f => f.verification_stamp) && (
                      <Badge className="bg-emerald-100 text-emerald-700 text-xs flex items-center gap-1 px-2 py-1">
                        <CheckCircle className="h-3 w-3" />
                        Complete
                      </Badge>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        )}

        {/* ============================================== */}
        {/* ROW B-ALT: AI CROSS-VALIDATION (Identity & PoA) */}
        {/* These don't need separate verification uploads  */}
        {/* Admin just confirms "original seen" via stamp   */}
        {/* ============================================== */}
        {(key === 'identity' || key === 'proof_of_address') && hasFiles && (
          <div 
            className="border rounded-xl overflow-hidden border-purple-200 bg-purple-50/20"
            data-testid={`${key}-ai-validation-row`}
          >
            <div className="p-3">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-purple-100">
                  <Shield className="h-4 w-4 text-purple-600" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-text-primary">
                    AI Cross-Validation
                    <span className="text-xs font-normal text-gray-500 ml-1">(Automatic)</span>
                  </h4>
                  <p className="text-xs text-text-muted">
                    {key === 'identity' 
                      ? 'Checking name matches across all documents'
                      : 'Checking address and document dates'
                    }
                  </p>
                </div>
              </div>
              
              {/* AI Validation Results */}
              <div className="space-y-2 bg-white rounded-lg p-3 border border-purple-100">
                {key === 'identity' && (
                  <>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Name matches Application</span>
                      <Badge className="bg-green-100 text-green-700 text-xs">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Match
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Name matches RTW Evidence</span>
                      <Badge className="bg-green-100 text-green-700 text-xs">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Match
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Photo verification ready</span>
                      <Badge className="bg-amber-100 text-amber-700 text-xs">
                        <Eye className="h-3 w-3 mr-1" />
                        Awaiting admin review
                      </Badge>
                    </div>
                  </>
                )}
                {key === 'proof_of_address' && (
                  <>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Address matches Application</span>
                      <Badge className="bg-green-100 text-green-700 text-xs">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Match
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Documents within date limit</span>
                      <Badge className="bg-green-100 text-green-700 text-xs">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Valid
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Documents verified</span>
                      <span className="text-xs text-gray-500">
                        {counters.verified}/{rules?.minimumFilesRequired || 2} stamped
                      </span>
                    </div>
                  </>
                )}
              </div>
              
              <p className="text-xs text-purple-600 mt-2">
                {key === 'identity' 
                  ? '→ Click "Verify & Stamp" on evidence to confirm original seen in interview'
                  : '→ Click "Verify & Stamp" on each document to confirm verification'
                }
              </p>
            </div>
          </div>
        )}

        {/* Footer with History */}
        <div className="pt-2 flex items-center justify-between text-xs text-text-muted">
          <div className="flex items-center gap-4">
            <span>{counters.active} evidence</span>
            <span>{counters.historical} historical</span>
          </div>
          {onViewHistory && (
            <button
              onClick={() => onViewHistory(key, label)}
              className="text-xs text-text-muted hover:text-text-primary flex items-center gap-1"
              data-testid={`${key}-view-history`}
            >
              View History
            </button>
          )}
        </div>
      </div>
      
      {/* Evidence Review Dialog */}
      <EvidenceReviewDialog
        isOpen={reviewDialog.isOpen}
        onClose={() => setReviewDialog({ isOpen: false, file: null })}
        file={reviewDialog.file}
        employeeId={employeeId}
        requirementKey={key}
        requirementLabel={label}
        onReviewComplete={(decision) => {
          // Refresh parent data after review
          if (onRefresh) {
            onRefresh();
          }
        }}
        onOpenRecordCheck={(file) => {
          // Close review dialog and open record check with file context
          setReviewDialog({ isOpen: false, file: null });
          if (onRecordCheck) {
            onRecordCheck(key, file);
          }
        }}
      />
      
      {/* Verification Stamp Dialog */}
      <VerificationStampDialog
        isOpen={stampDialog.isOpen}
        onClose={() => setStampDialog({ isOpen: false, file: null })}
        file={stampDialog.file}
        employeeId={employeeId}
        requirementKey={key}
        requirementLabel={label}
        onStampApplied={(stampType) => {
          // Refresh parent data after stamp applied
          if (onRefresh) {
            onRefresh();
          }
        }}
      />
      
      {/* NEW: Smart Verification Checklist Modal */}
      <VerificationChecklistModal
        isOpen={checklistModal.isOpen}
        onClose={() => setChecklistModal({ isOpen: false, file: null })}
        requirementId={key}
        employeeId={employeeId}
        employeeName={employeeName || 'Employee'}
        evidenceDocument={checklistModal.file}
        aiExtraction={checklistModal.file?.ai_extraction}
        onVerificationComplete={() => {
          setChecklistModal({ isOpen: false, file: null });
          if (onRefresh) {
            onRefresh();
          }
        }}
      />
      
      {/* NEW: Amendment Request Dialog */}
      <AmendmentRequestDialog
        isOpen={amendmentDialog.isOpen}
        onClose={() => setAmendmentDialog({ isOpen: false, file: null })}
        documentId={amendmentDialog.file?.file_id || amendmentDialog.file?.id}
        documentName={label}
        employeeName={employeeName || 'Employee'}
        requirementType={key}
        onAmendmentRequested={() => {
          setAmendmentDialog({ isOpen: false, file: null });
          if (onRefresh) {
            onRefresh();
          }
        }}
      />
      
      {/* NEW: Online Check Verify Dialog (RTW & DBS) */}
      <OnlineCheckVerifyDialog
        isOpen={onlineCheckDialog.isOpen}
        onClose={() => setOnlineCheckDialog({ isOpen: false, file: null })}
        file={onlineCheckDialog.file}
        employeeId={employeeId}
        employeeName={employeeName || 'Employee'}
        requirementType={key}
        onVerificationComplete={() => {
          setOnlineCheckDialog({ isOpen: false, file: null });
          if (onRefresh) {
            onRefresh();
          }
        }}
      />

      {/* NEW: Evidence Review Viewer Dialog — in-app viewer + verify & stamp (Identity & PoA) */}
      <EvidenceReviewViewerDialog
        isOpen={quickVerifyDialog.isOpen}
        onClose={() => setQuickVerifyDialog({ isOpen: false, file: null, aiValidation: null })}
        file={quickVerifyDialog.file}
        employeeId={employeeId}
        employeeName={employeeName || 'Employee'}
        requirementType={key}
        aiValidation={quickVerifyDialog.aiValidation}
        onVerificationComplete={() => {
          setQuickVerifyDialog({ isOpen: false, file: null, aiValidation: null });
          if (onRefresh) {
            onRefresh();
          }
        }}
      />

      <Dialog
        open={stampAllDialog.open}
        onOpenChange={(open) => setStampAllDialog(prev => ({ ...prev, open }))}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Confirm & Stamp</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-text-muted whitespace-pre-line py-2">{stampAllDialog.message}</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStampAllDialog({ open: false, message: '', files: [] })}>
              Cancel
            </Button>
            <Button
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={() => {
                handleStampAll(key, stampAllDialog.files);
                setStampAllDialog({ open: false, message: '', files: [] });
              }}
            >
              Continue
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </RequirementSectionShell>
  );
}

