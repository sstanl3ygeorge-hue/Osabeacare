import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import { 
  FileText, CheckCircle, Clock, AlertTriangle,
  Eye, Send, RefreshCw, Shield, Download, X, ChevronDown, ChevronUp, Upload as UploadIcon,
  ClipboardCheck
} from 'lucide-react';
import RequirementSectionShell from './RequirementSectionShell';
import RequirementActionBar from './RequirementActionBar';
import EvidenceReviewDialog from './EvidenceReviewDialog';
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
  isAuditor = false
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
      'share_code_online_check': 'Share Code Online',
      'manual_passport_check': 'Manual Passport Check',
      'idsp_check': 'IDSP Check',
      'ecs_check': 'Employer Checking Service',
      'update_service_check': 'DBS Update Service',
      'manual_certificate_review': 'Manual Certificate Review',
      'manual_id_verification': 'Manual ID Verification',
      'digital_id_check': 'Digital ID Check',
      'manual_document_check': 'Manual Document Check'
    };
    return methods[method] || method?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Unknown';
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
                  {hasFiles 
                    ? `${counters.active} file${counters.active !== 1 ? 's' : ''} uploaded`
                    : 'No files uploaded'
                  }
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {counters.active > 0 && (
                <Badge className="text-[10px] px-1.5 py-0 bg-blue-100 text-blue-700 border border-blue-200">
                  {counters.active} active
                </Badge>
              )}
              {counters.pendingReview > 0 && (
                <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border border-amber-200">
                  {counters.pendingReview} pending
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
                          <p className="text-xs text-text-muted">
                            {formatBackendDate(file.uploaded_at, { format: 'medium' })}
                            {file.uploaded_by && ` • ${file.uploaded_by}`}
                          </p>
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

              {/* Request Status */}
              {latestRequest && (
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
                          {checkData.checked_by || 'Admin'}
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
    </RequirementSectionShell>
  );
}
