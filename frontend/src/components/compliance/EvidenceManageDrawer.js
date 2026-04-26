import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { 
  FileText, Upload, Download, Eye, CheckCircle, XCircle, 
  AlertTriangle, Clock, Send, RefreshCw, Loader2, Archive,
  MoreVertical, Trash2, ArrowRight
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';
import ComplianceDrawer, { 
  DrawerSection, 
  DrawerCard, 
  DrawerEmptyState, 
  DrawerStatusChip 
} from './ComplianceDrawer';
import DocumentActionMenu from './DocumentActionMenu';
import {
  getRequirementConfig,
  getAllowedMoveTargets,
  isPreviewableFile,
  normalizeUploadDrawerData,
} from './complianceRequirementMap';
import { getEvidenceRules } from './evidenceRules';
import {
  downloadBlobUrl,
  fetchProtectedFileBlob,
  revokeBlobUrlLater,
} from '../../lib/protectedFiles';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const getProtectedRequestToken = (rawUrl, authToken) => {
  if (!rawUrl || !authToken) return undefined;
  if (typeof rawUrl !== 'string') return undefined;
  if (!rawUrl.startsWith('/api/')) return undefined;

  try {
    const resolvedUrl = new URL(rawUrl, window.location.origin);
    const isSameOriginApi =
      resolvedUrl.origin === window.location.origin &&
      resolvedUrl.pathname.startsWith('/api/');
    return isSameOriginApi ? authToken : undefined;
  } catch {
    return undefined;
  }
};

/**
 * EvidenceManageDrawer - Manages EVIDENCE ONLY (not verification)
 * 
 * For: Right to Work, DBS, Identity, Proof of Address
 * 
 * Structure:
 * - Header: Requirement name, evidence summary, status chips
 * - Tab 1: Active Files (upload, view, download, manage)
 * - Tab 2: Request History (sent, viewed, uploaded, resend)
 * - Tab 3: Historical Files (superseded, deleted, old items)
 * 
 * Primary Actions:
 * - Upload Evidence
 * - Request From Applicant
 * - Resend Latest Request
 * 
 * This drawer does NOT handle verification - that stays in the main card.
 */
export default function EvidenceManageDrawer({
  isOpen,
  onClose,
  employeeId,
  requirementKey,
  onUploadFile,
  onSendRequest,
  onPreviewFile,
  onExtractReview,
  onRefresh,
  isAuditor = false
}) {
  const [loading, setLoading] = useState(false);
  const [filesData, setFilesData] = useState(null);
  const [expandedSection, setExpandedSection] = useState('active'); // 'active' | 'requests' | 'historical'
  const [actionDialog, setActionDialog] = useState({ open: false, type: null, file: null });
  const [actionReason, setActionReason] = useState('');
  const [newRequirementId, setNewRequirementId] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { token } = useAuth();
  const requirementConfig = getRequirementConfig(requirementKey);
  const sharedRules = getEvidenceRules(requirementKey);

  // Fetch files data
  const fetchFiles = useCallback(async () => {
    if (!employeeId || !requirementKey) return;
    
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/requirements/${requirementConfig.evidenceEndpointKey}/files`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setFilesData(normalizeUploadDrawerData(response.data, requirementKey));
    } catch (err) {
      toast.error('Failed to load files');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [employeeId, requirementKey, token, requirementConfig.evidenceEndpointKey]);

  useEffect(() => {
    if (isOpen && employeeId && requirementKey) {
      fetchFiles();
      setExpandedSection('active');
    }
  }, [isOpen, employeeId, requirementKey, fetchFiles]);

  // Refresh after mutation
  const refreshAfterMutation = useCallback(async () => {
    await fetchFiles();
    if (onRefresh) onRefresh();
  }, [fetchFiles, onRefresh]);

  // Handle file view
  const handleOpenFile = async (file) => {
    if (!file) {
      toast.error('File data not available');
      return;
    }
    const rawUrl = file.openUrl || file.file_url || file.downloadUrl;
    let url = rawUrl;
    if (!url && !file.file_available) {
      toast.error('File URL not available');
      return;
    }
    if (url && url.startsWith('/api/')) {
      url = `${API}${url.substring(4)}`;
    }
    // Preview-first logic
    if (isPreviewableFile(file) && onPreviewFile) {
      onPreviewFile({
        file_url: url,
        file_name: file.file_name || file.file_label || 'Document',
        mime_type: file.mime_type || file.content_type || '',
        file_id: file.file_id || file.id
      });
    } else if (url) {
      await handleDownloadFile(file);
    } else {
      handleDownloadFile(file);
    }
  };

  // Handle file download
  const handleDownloadFile = async (file) => {
    const rawUrl = file.downloadUrl || file.download_url || file.file_url;
    let url = rawUrl;
    
    if (!url) {
      toast.error('Download URL not available');
      return;
    }
    
    if (url.startsWith('/api/')) {
      url = `${API}${url.substring(4)}`;
    }
    
    try {
      const requestToken = getProtectedRequestToken(rawUrl, token);
      const { blobUrl } = await fetchProtectedFileBlob(url, requestToken);
      downloadBlobUrl(blobUrl, file.file_name || file.file_label || 'document');
      revokeBlobUrlLater(blobUrl, 1000);
    } catch {
      // Preserve existing UX: no additional toast on download fallback failures.
    }
  };

  // File actions
  const handleVerify = async (fileId) => {
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/employee-documents/${fileId}/verify`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File verified');
      refreshAfterMutation();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify file');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async (fileId) => {
    if (!actionReason.trim()) {
      toast.error('Please provide a rejection reason');
      return;
    }
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/employee-documents/${fileId}/reject`,
        { reason: actionReason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File rejected');
      closeActionDialog();
      refreshAfterMutation();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject file');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRequestReplacement = async (fileId) => {
    if (!actionReason.trim()) {
      toast.error('Please provide a replacement reason');
      return;
    }
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/employee-documents/${fileId}/request-replacement`,
        { reason: actionReason, notify_employee: true },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Replacement requested from worker');
      closeActionDialog();
      refreshAfterMutation();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to request replacement');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleMarkUploadedInError = async (fileId) => {
    if (!actionReason.trim() || actionReason.trim().length < 20) {
      toast.error('Please provide a stronger reason (at least 20 characters)');
      return;
    }
    if (!fileId) {
      toast.error('File ID is missing');
      closeActionDialog();
      return;
    }
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/employee-documents/${fileId}/mark-uploaded-in-error`,
        { reason: actionReason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File marked as uploaded in error');
      closeActionDialog();
      refreshAfterMutation();
    } catch (err) {
      console.error('Mark uploaded in error failed:', err);
      toast.error(err.response?.data?.detail || 'Failed to mark file');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSupersede = async (fileId) => {
    if (!actionReason.trim() || actionReason.trim().length < 10) {
      toast.error('Please provide a reason (at least 10 characters)');
      return;
    }
    if (!fileId) {
      toast.error('File ID is missing');
      closeActionDialog();
      return;
    }
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/employee-documents/${fileId}/supersede`,
        { reason: actionReason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File superseded');
      closeActionDialog();
      refreshAfterMutation();
    } catch (err) {
      console.error('Supersede failed:', err);
      toast.error(err.response?.data?.detail || 'Failed to supersede file');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleMoveCategory = async (fileId) => {
    if (!actionReason.trim() || !newRequirementId) {
      toast.error('Please provide a reason and select new category');
      return;
    }
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/documents/${fileId}/move-category`,
        { reason: actionReason, new_requirement_id: newRequirementId },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File moved to new category');
      closeActionDialog();
      refreshAfterMutation();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to move file');
    } finally {
      setIsSubmitting(false);
    }
  };

  const closeActionDialog = () => {
    setActionDialog({ open: false, type: null, file: null });
    setActionReason('');
    setNewRequirementId('');
  };

  // Get status chips for header
  const getStatusChips = () => {
    if (!filesData) return null;
    
    const chips = [];
    const counts = filesData.counts || {};
    
    if (counts.active > 0) {
      chips.push(
        <DrawerStatusChip key="active" variant="info">
          {counts.active} active
        </DrawerStatusChip>
      );
    }
    if (counts.verified > 0) {
      chips.push(
        <DrawerStatusChip key="verified" variant="success">
          {counts.verified} verified
        </DrawerStatusChip>
      );
    }
    if (counts.pendingReview > 0) {
      chips.push(
        <DrawerStatusChip key="pending" variant="warning">
          {counts.pendingReview} pending
        </DrawerStatusChip>
      );
    }
    if (counts.historical > 0) {
      chips.push(
        <DrawerStatusChip key="historical" variant="default">
          {counts.historical} historical
        </DrawerStatusChip>
      );
    }
    
    return chips.length > 0 ? chips : null;
  };

  // PoA specific logic
  const isPoA = requirementKey === 'proof_of_address';
  const effectiveRules = filesData?.evidence_rules || requirementConfig?.evidenceRules || sharedRules;
  const requiredCount = filesData?.multi_file_config?.required_count || effectiveRules.min_required_files || (isPoA ? 2 : 1);
  const validPoACount = filesData?.counts?.validPoA || 0;
  const needsMoreFiles = isPoA && validPoACount < requiredCount;
  const maxActiveFiles = effectiveRules.max_active_files;
  const activeCount = filesData?.counts?.active || 0;
  const isAtActiveLimit = Boolean(maxActiveFiles && activeCount >= maxActiveFiles);

  const requirementCategories = getAllowedMoveTargets(requirementKey);
  const title = requirementConfig?.label || 'Evidence';

  // Render file status badge
  const renderFileBadge = (file) => {
    if (file.status === 'uploaded_in_error' || file.uploaded_in_error_reason) {
      return <Badge className="bg-red-100 text-red-700 text-[10px] px-1.5 py-0">Error</Badge>;
    }
    if (file.status === 'superseded' || file.superseded_by) {
      return <Badge className="bg-amber-100 text-amber-700 text-[10px] px-1.5 py-0">Superseded</Badge>;
    }
    if (file.rejected) {
      return <Badge className="bg-red-100 text-red-700 text-[10px] px-1.5 py-0">Rejected</Badge>;
    }
    if (file.extraction_status?.status === 'awaiting_review') {
      return <Badge className="bg-purple-100 text-purple-700 text-[10px] px-1.5 py-0">Review Extraction</Badge>;
    }
    if (file.verified) {
      return <Badge className="bg-green-100 text-green-700 text-[10px] px-1.5 py-0">Verified</Badge>;
    }
    return <Badge className="bg-amber-100 text-amber-700 text-[10px] px-1.5 py-0">Pending</Badge>;
  };

  // Render request status badge
  const renderRequestBadge = (request) => {
    const statusConfig = {
      completed: { variant: 'success', label: 'Completed' },
      submitted: { variant: 'success', label: 'Submitted' },
      clicked: { variant: 'info', label: 'Viewed' },
      viewed: { variant: 'info', label: 'Viewed' },
      sent: { variant: 'info', label: 'Sent' },
      requested: { variant: 'info', label: 'Requested' },
      expired: { variant: 'default', label: 'Expired' },
      cancelled: { variant: 'default', label: 'Cancelled' }
    };
    const config = statusConfig[request.status] || { variant: 'default', label: request.status };
    return <DrawerStatusChip variant={config.variant}>{config.label}</DrawerStatusChip>;
  };

  return (
    <>
      <ComplianceDrawer
        isOpen={isOpen}
        onClose={onClose}
        title={`${title} - Evidence`}
        subtitle="Manage candidate/applicant evidence files"
        statusChips={getStatusChips()}
        testId={`evidence-drawer-${requirementKey}`}
        headerActions={
          !isAuditor && (
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => onUploadFile && onUploadFile(requirementKey)}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white h-9"
                data-testid="evidence-upload-btn"
                disabled={isAtActiveLimit}
              >
                <Upload className="h-4 w-4 mr-1.5" />
                {isAtActiveLimit ? `Limit Reached (${maxActiveFiles})` : 'Upload Evidence'}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => onSendRequest && onSendRequest(requirementKey)}
                className="flex-1 h-9"
                data-testid="evidence-request-btn"
              >
                <Send className="h-4 w-4 mr-1.5" />
                Request
              </Button>
            </div>
          )
        }
      >
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : filesData ? (
          <div className="space-y-4">
            {/* PoA Requirements Banner */}
            {isPoA && (
              <div className={`p-4 rounded-xl border ${
                validPoACount >= requiredCount
                  ? 'bg-green-50 border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}>
                <div className="flex items-center gap-3">
                  {validPoACount >= requiredCount ? (
                    <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
                  ) : (
                    <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0" />
                  )}
                  <div>
                    <p className={`font-medium text-sm ${
                      validPoACount >= requiredCount ? 'text-green-800' : 'text-red-800'
                    }`}>
                      {validPoACount}/{requiredCount} valid documents
                    </p>
                    <p className="text-xs text-gray-600 mt-0.5">
                      2 recent documents required (within 12 months)
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Active Files Section */}
            <DrawerSection
              title="Active Files"
              icon={FileText}
              count={filesData.counts?.active || 0}
              variant="success"
              expanded={expandedSection === 'active'}
              onToggle={() => setExpandedSection(expandedSection === 'active' ? null : 'active')}
              testId="active-files-section"
              emptyState={
                <DrawerEmptyState
                  icon={Upload}
                  title="No active files"
                  description="Upload evidence or request from applicant"
                />
              }
            >
              {filesData.active_files?.length > 0 && (
                <div className="space-y-3">
                  {filesData.active_files.map((file) => (
                    <DrawerCard 
                      key={file.file_id} 
                      testId={`active-file-${file.file_id}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
                            <span className="font-medium text-sm text-gray-900 truncate">
                              {file.file_name}
                            </span>
                            {renderFileBadge(file)}
                          </div>
                          <div className="mt-2 text-xs text-gray-500 space-y-0.5 pl-6">
                            <p>
                              Uploaded {formatBackendDate(file.uploaded_at, { format: 'medium' })}
                              {file.uploaded_by && ` by ${file.uploaded_by}`}
                            </p>
                            {file.expiry_date && (
                              <p>Expires: {formatBackendDate(file.expiry_date, { format: 'medium' })}</p>
                            )}
                          </div>
                        </div>
                        
                        {/* File Actions */}
                        <div className="flex items-center gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleOpenFile(file)}
                            className="h-8 w-8 p-0"
                            title="View"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDownloadFile(file)}
                            className="h-8 w-8 p-0"
                            title="Download"
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                          {!isAuditor && (
                            <DocumentActionMenu
                              file={file}
                              onView={() => handleOpenFile(file)}
                              onDownload={() => handleDownloadFile(file)}
                              onVerify={() => handleVerify(file.file_id)}
                              onRequestReplacement={() => setActionDialog({ open: true, type: 'request_replacement', file })}
                              onRejectEvidence={() => setActionDialog({ open: true, type: 'reject', file })}
                              onExtractReview={() => onExtractReview && onExtractReview(file.file_id)}
                              onMarkUploadedInError={() => setActionDialog({ open: true, type: 'uploaded_in_error', file })}
                              onSupersede={() => setActionDialog({ open: true, type: 'supersede', file })}
                              onMoveCategory={() => setActionDialog({ open: true, type: 'move_category', file })}
                              isAuditor={isAuditor}
                              isProcessing={isSubmitting}
                            />
                          )}
                        </div>
                      </div>
                    </DrawerCard>
                  ))}
                </div>
              )}
            </DrawerSection>

            {/* Request History Section */}
            <DrawerSection
              title="Request History"
              icon={Send}
              count={filesData.counts?.requests || 0}
              variant="primary"
              expanded={expandedSection === 'requests'}
              onToggle={() => setExpandedSection(expandedSection === 'requests' ? null : 'requests')}
              testId="request-history-section"
              emptyState={
                <DrawerEmptyState
                  icon={Send}
                  title="No requests sent"
                  description="Request evidence from applicant to see history here"
                />
              }
            >
              {filesData.requests?.length > 0 && (
                <div className="space-y-3">
                  {filesData.requests.map((req, idx) => (
                    <DrawerCard 
                      key={req.request_id || idx}
                      variant={req.status === 'completed' || req.status === 'submitted' ? 'success' : 'default'}
                      testId={`request-${req.request_id || idx}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            {renderRequestBadge(req)}
                            {req.is_replacement && (
                              <DrawerStatusChip variant="warning">Replacement</DrawerStatusChip>
                            )}
                            {(req.reminder_count > 0 || req.resent_count > 0) && (
                              <DrawerStatusChip variant="warning">
                                {req.reminder_count || req.resent_count} reminder{(req.reminder_count || req.resent_count) !== 1 ? 's' : ''}
                              </DrawerStatusChip>
                            )}
                          </div>
                          <div className="text-xs text-gray-500 space-y-0.5">
                            {req.sent_at && (
                              <p>Sent: {formatBackendDate(req.sent_at, { format: 'medium' })}</p>
                            )}
                            {req.viewed_at && (
                              <p className="text-purple-600">
                                Viewed: {formatBackendDate(req.viewed_at, { format: 'medium' })}
                              </p>
                            )}
                            {req.submitted_at && (
                              <p className="text-green-600">
                                Submitted: {formatBackendDate(req.submitted_at, { format: 'medium' })}
                              </p>
                            )}
                            {req.recipient_email && (
                              <p>To: {req.recipient_email}</p>
                            )}
                          </div>
                        </div>
                        
                        {!isAuditor && req.status !== 'completed' && req.status !== 'submitted' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => onSendRequest && onSendRequest(requirementKey)}
                            className="h-8 text-xs"
                          >
                            <RefreshCw className="h-3 w-3 mr-1" />
                            Resend
                          </Button>
                        )}
                      </div>
                    </DrawerCard>
                  ))}
                </div>
              )}
            </DrawerSection>

            {/* Historical Files Section */}
            <DrawerSection
              title="Historical Files"
              icon={Archive}
              count={filesData.counts?.historical || 0}
              variant="muted"
              expanded={expandedSection === 'historical'}
              onToggle={() => setExpandedSection(expandedSection === 'historical' ? null : 'historical')}
              testId="historical-files-section"
              emptyState={
                <DrawerEmptyState
                  icon={Archive}
                  title="No historical files"
                  description="Superseded and deleted files will appear here"
                />
              }
            >
              {filesData.historical_files?.length > 0 && (
                <div className="space-y-3">
                  {filesData.historical_files.map((file) => (
                    <DrawerCard 
                      key={file.file_id}
                      variant="muted"
                      testId={`historical-file-${file.file_id}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
                            <span className="text-sm text-gray-600 truncate">
                              {file.file_name}
                            </span>
                            <Badge className={`text-[10px] px-1.5 py-0 ${
                              file.status === 'superseded' ? 'bg-amber-100 text-amber-700' :
                              file.status === 'uploaded_in_error' || file.status === 'rejected' ? 'bg-red-100 text-red-700' :
                              'bg-gray-100 text-gray-600'
                            }`}>
                              {file.status === 'superseded' ? 'Superseded' :
                               file.status === 'uploaded_in_error' ? 'Error' :
                               file.status === 'rejected' ? 'Rejected' :
                               file.status}
                            </Badge>
                          </div>
                          <div className="mt-1 text-xs text-gray-500 pl-6">
                            <p>{formatBackendDate(file.uploaded_at, { format: 'medium' })}</p>
                            {(file.supersede_reason || file.uploaded_in_error_reason || file.rejection_reason) && (
                              <p className="text-gray-400 mt-0.5">
                                Reason: {file.supersede_reason || file.uploaded_in_error_reason || file.rejection_reason}
                              </p>
                            )}
                          </div>
                        </div>
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleOpenFile(file)}
                            className="h-7 w-7 p-0"
                            title="View"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDownloadFile(file)}
                            className="h-7 w-7 p-0"
                            title="Download"
                          >
                            <Download className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    </DrawerCard>
                  ))}
                </div>
              )}
            </DrawerSection>
          </div>
        ) : (
          <div className="py-16 text-center text-gray-500">
            Failed to load files
          </div>
        )}
      </ComplianceDrawer>

      {/* Action Dialog */}
      <Dialog 
        open={actionDialog.open} 
        onOpenChange={(open) => !open && closeActionDialog()}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {actionDialog.type === 'uploaded_in_error' && 'Mark as Uploaded in Error'}
              {actionDialog.type === 'request_replacement' && 'Request Replacement (Amendment)'}
              {actionDialog.type === 'supersede' && 'Supersede File'}
              {actionDialog.type === 'move_category' && 'Move to Different Category'}
              {actionDialog.type === 'reject' && 'Reject Evidence'}
            </DialogTitle>
            <DialogDescription>
              {actionDialog.file?.file_name}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {actionDialog.type === 'move_category' && (
              <div className="space-y-2">
                <Label>New Category *</Label>
                <Select value={newRequirementId} onValueChange={setNewRequirementId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {requirementCategories.map(cat => (
                      <SelectItem key={cat.id} value={cat.id}>
                        {cat.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-2">
              <Label>Reason *</Label>
              <Textarea
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                placeholder={
                  actionDialog.type === 'uploaded_in_error' ? 'State exactly why this upload is invalid for audit (minimum 20 characters)' :
                  actionDialog.type === 'request_replacement' ? 'Explain what worker must correct before re-upload' :
                  actionDialog.type === 'supersede' ? 'Why is this file being superseded?' :
                  actionDialog.type === 'move_category' ? 'Why is this file being moved?' :
                  actionDialog.type === 'reject' ? 'Explain why this evidence is rejected (wrong/illegible/insufficient)' :
                  'Enter reason...'
                }
                className="min-h-[80px]"
              />
            </div>

            {actionDialog.type === 'uploaded_in_error' && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-xs text-amber-700 flex items-start gap-2">
                  <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                  Admin cleanup only. This removes the file from active evidence but preserves immutable audit history.
                </p>
              </div>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={closeActionDialog}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                const fileId = actionDialog.file?.file_id || actionDialog.file?.id;
                if (!fileId) {
                  toast.error('Cannot perform action: File ID is missing');
                  closeActionDialog();
                  return;
                }
                if (actionDialog.type === 'uploaded_in_error') handleMarkUploadedInError(fileId);
                else if (actionDialog.type === 'request_replacement') handleRequestReplacement(fileId);
                else if (actionDialog.type === 'supersede') handleSupersede(fileId);
                else if (actionDialog.type === 'move_category') handleMoveCategory(fileId);
                else if (actionDialog.type === 'reject') handleReject(fileId);
              }}
              disabled={isSubmitting || !actionReason.trim() || (actionDialog.type === 'move_category' && !newRequirementId)}
              className={
                actionDialog.type === 'reject' || actionDialog.type === 'uploaded_in_error'
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              {actionDialog.type === 'uploaded_in_error' && 'Mark as Error'}
              {actionDialog.type === 'request_replacement' && 'Request Replacement'}
              {actionDialog.type === 'supersede' && 'Supersede'}
              {actionDialog.type === 'move_category' && 'Move File'}
              {actionDialog.type === 'reject' && 'Reject'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
