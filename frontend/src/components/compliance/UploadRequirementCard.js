import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import { 
  FileText, CheckCircle, Clock, AlertTriangle,
  Eye, Send, RefreshCw, Shield, Download, X, ChevronDown, ChevronUp, Upload as UploadIcon,
  ClipboardCheck, Stamp
} from 'lucide-react';
import RequirementSectionShell from './RequirementSectionShell';
import RequirementActionBar from './RequirementActionBar';
import EvidenceReviewDialog from './EvidenceReviewDialog';
import VerificationStampDialog from './VerificationStampDialog';
import { formatBackendDate } from '../../lib/dateUtils';

// eslint-disable-next-line no-unused-vars
const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
  onRefresh,
  isAuditor = false,
  // RTW Status - additive, non-breaking prop
  rtwStatus = null
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

  // Get check data details
  const checkData = authoritativeCheck || {};
  const hasVerificationProof = checkData.evidence_document_id && checkData.evidence_document;

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

  // Get stamp display info
  const getStampDisplay = (stamp) => {
    const stamps = {
      'original_seen': { label: 'ORIGINAL VERIFIED', className: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
      'copy_verified': { label: 'COPY VERIFIED', className: 'bg-blue-100 text-blue-700 border-blue-200' },
      'online_check': { label: 'ONLINE VERIFIED', className: 'bg-indigo-100 text-indigo-700 border-indigo-200' },
      'not_verified': { label: 'NOT VERIFIED', className: 'bg-red-100 text-red-700 border-red-200' }
    };
    return stamps[stamp] || { label: stamp?.toUpperCase()?.replace(/_/g, ' '), className: 'bg-gray-100 text-gray-600 border-gray-200' };
  };

  // Get outcome display
  const getOutcomeDisplay = (outcome) => {
    const outcomes = {
      'verified': 'Verified',
      'failed': 'Failed',
      'follow_up_required': 'Follow-up Required',
      'awaiting_review': 'Awaiting Review'
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
                <h4 className="text-sm font-semibold text-text-primary">Evidence</h4>
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
                            {/* Verification Stamp Badge - ENHANCED */}
                            {file.verification_stamp && (() => {
                              const stampInfo = getStampDisplay(file.verification_stamp);
                              return (
                                <div className="flex flex-col">
                                  <Badge 
                                    className={`text-[9px] px-1.5 py-0.5 font-semibold ${stampInfo.className}`}
                                    data-testid={`${key}-stamp-badge-${file.file_id || file.id}`}
                                  >
                                    <Stamp className="h-2.5 w-2.5 mr-1" />
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
                        {file.verified ? (
                          <Badge className="text-[10px] px-1.5 py-0 bg-green-100 text-green-700 border border-green-200">
                            <CheckCircle className="h-2.5 w-2.5 mr-0.5" />
                            Accepted
                          </Badge>
                        ) : file.status === 'rejected' ? (
                          <Badge className="text-[10px] px-1.5 py-0 bg-red-100 text-red-700 border border-red-200">
                            <X className="h-2.5 w-2.5 mr-0.5" />
                            Rejected
                          </Badge>
                        ) : file.extraction_status?.status === 'awaiting_review' ? (
                          <Badge className="text-[10px] px-1.5 py-0 bg-purple-100 text-purple-700 border border-purple-200">
                            <Clock className="h-2.5 w-2.5 mr-0.5" />
                            Extraction pending
                          </Badge>
                        ) : (
                          <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border border-amber-200">
                            <Clock className="h-2.5 w-2.5 mr-0.5" />
                            Pending Review
                          </Badge>
                        )}
                        
                        {/* Apply Verification Stamp button - show different states */}
                        {!isAuditor && file.verified && (
                          <Button
                            size="sm"
                            variant={file.verification_stamp ? "ghost" : "outline"}
                            className={`h-7 px-2 text-xs ${
                              file.verification_stamp 
                                ? 'text-gray-500 hover:text-gray-700 hover:bg-gray-100' 
                                : 'text-indigo-600 border-indigo-200 hover:bg-indigo-50'
                            }`}
                            onClick={() => setStampDialog({ isOpen: true, file })}
                            title={file.verification_stamp ? "Edit verification stamp" : "Apply verification stamp"}
                            data-testid={`${key}-stamp-btn-${file.file_id || file.id}`}
                          >
                            <Stamp className="h-3 w-3 mr-1" />
                            {file.verification_stamp ? 'Edit Stamp' : 'Stamp'}
                          </Button>
                        )}
                        
                        {/* Review Evidence button - visible for non-verified files */}
                        {!isAuditor && !file.verified && file.status !== 'rejected' && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 px-2 text-xs text-teal-600 border-teal-200 hover:bg-teal-50"
                            onClick={() => setReviewDialog({ isOpen: true, file })}
                            title="Review evidence"
                            data-testid={`${key}-evidence-review-${file.file_id || file.id}`}
                          >
                            <ClipboardCheck className="h-3 w-3 mr-1" />
                            Review
                          </Button>
                        )}
                        
                        {/* View file button */}
                        {onPreviewFile && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 w-7 p-0 text-gray-500 hover:text-blue-600"
                            onClick={() => onPreviewFile({
                              file_url: `/api/employee-documents/${file.file_id || file.id}/file`,
                              file_name: file.file_name || file.original_filename || 'Document'
                            })}
                            title="View file"
                            data-testid={`${key}-evidence-view-${file.file_id || file.id}`}
                          >
                            <Eye className="h-3.5 w-3.5" />
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
                <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={onUpload}
                    className="h-8 text-xs rounded-lg"
                    data-testid={`${key}-evidence-upload-btn`}
                  >
                    <UploadIcon className="h-3.5 w-3.5 mr-1" />
                    Upload
                  </Button>
                  {!hasPendingRequest && !hasFiles && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={onRequest}
                      className="h-8 text-xs rounded-lg"
                      data-testid={`${key}-evidence-request-btn`}
                    >
                      <Send className="h-3.5 w-3.5 mr-1" />
                      Request
                    </Button>
                  )}
                  {hasPendingRequest && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={onResend}
                      className="h-8 text-xs rounded-lg text-amber-600 border-amber-200 hover:bg-amber-50"
                      data-testid={`${key}-evidence-resend-btn`}
                    >
                      <RefreshCw className="h-3.5 w-3.5 mr-1" />
                      Resend
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
        {/* ============================================== */}
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
                <h4 className="text-sm font-semibold text-text-primary">Verification</h4>
                <p className="text-xs text-text-muted">
                  {checkVerified 
                    ? 'Check verified'
                    : hasCheck 
                      ? `Check recorded: ${getOutcomeDisplay(checkData.outcome)}`
                      : 'No check recorded'
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
                          {/* Route / Check Type */}
                          {(checkData.route || checkData.method) && (
                            <div>
                              <p className="text-xs text-text-muted">Route</p>
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
                          
                          {/* Permission End / Expiry */}
                          {checkData.permission_end_date && (
                            <div>
                              <p className="text-xs text-text-muted">Permission Expires</p>
                              <p className="font-medium text-text-primary">{formatBackendDate(checkData.permission_end_date, { format: 'medium' })}</p>
                            </div>
                          )}
                          
                          {/* Reference Number / PVN */}
                          {checkData.reference_number && (
                            <div>
                              <p className="text-xs text-text-muted">Reference / PVN</p>
                              <p className="font-medium text-text-primary font-mono text-xs">{checkData.reference_number}</p>
                            </div>
                          )}
                          
                          {/* Share Code */}
                          {checkData.share_code && (
                            <div>
                              <p className="text-xs text-text-muted">Share Code</p>
                              <p className="font-medium text-text-primary font-mono text-xs">{checkData.share_code}</p>
                            </div>
                          )}
                          
                          {/* Follow-up Date */}
                          {checkData.follow_up_due_at && (
                            <div>
                              <p className="text-xs text-text-muted">Next Follow-up</p>
                              <p className="font-medium text-amber-700">{formatBackendDate(checkData.follow_up_due_at, { format: 'medium' })}</p>
                            </div>
                          )}
                        </div>
                        
                        {/* Restrictions - Full width */}
                        {checkData.restrictions && (
                          <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg">
                            <p className="text-xs text-amber-800 font-medium mb-1">Work Restrictions</p>
                            <p className="text-sm text-amber-700">{checkData.restrictions}</p>
                            {checkData.hours_limit && (
                              <p className="text-xs text-amber-600 mt-1">Hours limit: {checkData.hours_limit} per week</p>
                            )}
                          </div>
                        )}
                        
                        {/* Status flags */}
                        <div className="flex flex-wrap gap-2">
                          {checkData.is_indefinite && (
                            <div className="flex items-center gap-1 px-2 py-1 bg-green-50 border border-green-200 rounded-lg">
                              <CheckCircle className="h-3 w-3 text-green-600" />
                              <span className="text-xs font-medium text-green-700">Indefinite right to work</span>
                            </div>
                          )}
                          {checkData.follow_up_required && (
                            <div className="flex items-center gap-1 px-2 py-1 bg-amber-50 border border-amber-200 rounded-lg">
                              <Clock className="h-3 w-3 text-amber-600" />
                              <span className="text-xs font-medium text-amber-700">Follow-up required</span>
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
                      <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                        <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0" />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-amber-800">No proof file attached</p>
                          <p className="text-xs text-amber-600">
                            Upload proof documentation for compliance audit trail.
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

              {/* Verification Actions */}
              {!isAuditor && (
                <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
                  {/* Record Check / Update Check Button - Primary action that includes proof upload */}
                  {!hasCheck ? (
                    <Button
                      size="sm"
                      variant="default"
                      onClick={() => onRecordCheck && onRecordCheck(key)}
                      className="h-8 text-xs bg-primary hover:bg-primary-hover text-white rounded-lg"
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
                  
                  {/* Manage/View Verification - always available */}
                  {hasCheck && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={onOpenDrawer}
                      className="h-8 text-xs rounded-lg"
                      data-testid={`${key}-verification-manage-btn`}
                    >
                      <Eye className="h-3.5 w-3.5 mr-1" />
                      View Details
                    </Button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

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
    </RequirementSectionShell>
  );
}
