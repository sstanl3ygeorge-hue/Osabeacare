import { isPreviewableFile } from '../../compliance/complianceRequirementMap';
import { useState, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../../../context/AuthContext';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../../ui/dialog';
import { toast } from 'sonner';
import {
  Shield,
  FileText,
  Upload,
  Eye,
  Download,
  CheckCircle,
  AlertTriangle,
  Loader2,
  X,
  RefreshCw,
} from 'lucide-react';
import { formatBackendDate } from '../../../lib/dateUtils';
import API_BASE from '../../../utils/apiBase';
import {
  downloadBlobUrl,
  fetchProtectedFileBlob,
  revokeBlobUrlLater,
} from '../../../lib/protectedFiles';

const API = API_BASE;

const PROOF_CHECK_ENDPOINTS = {
  right_to_work: (employeeId) =>
    `${API}/employees/${employeeId}/right-to-work/check`,
  dbs: (employeeId) => `${API}/employees/${employeeId}/dbs/check`,
};

const PROOF_CHECK_TYPE = {
  right_to_work: 'right_to_work_check',
  dbs: 'dbs_status_check',
};

const getProtectedRequestToken = (rawUrl, authToken) => {
  if (!rawUrl || !authToken) return undefined;
  if (typeof rawUrl !== 'string') return undefined;

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
 * Build a re-check payload from an existing check record.
 * Preserves all check fields; only updates proof document references.
 * Pass proofDocId=null to clear the proof reference.
 */
function buildReCheckPayload(checkRecord, proofDocId) {
  if (!checkRecord) return {};

  const base = {
    method: checkRecord.method,
    checked_at: checkRecord.checked_at,
    outcome: checkRecord.outcome,
    notes: checkRecord.notes || null,
    // Both fields are updated together — they both point to the proof file
    evidence_document_id: proofDocId,
    proof_document_id: proofDocId,
  };

  // RTW-specific fields
  if (checkRecord.permission_type !== undefined) {
    Object.assign(base, {
      permission_type: checkRecord.permission_type,
      permission_start_date: checkRecord.permission_start_date,
      permission_end_date: checkRecord.permission_end_date,
      is_indefinite: checkRecord.is_indefinite,
      follow_up_required: checkRecord.follow_up_required,
      follow_up_due_at: checkRecord.follow_up_due_at,
      restrictions: checkRecord.restrictions,
      hours_limit: checkRecord.hours_limit,
      reference_number: checkRecord.reference_number,
      share_code: checkRecord.share_code,
      route: checkRecord.route,
      source_status_type: checkRecord.source_status_type,
      document_type: checkRecord.document_type,
    });
  }

  // DBS-specific fields
  if (
    checkRecord.dbs_level !== undefined ||
    checkRecord.certificate_number !== undefined
  ) {
    Object.assign(base, {
      dbs_level: checkRecord.dbs_level,
      certificate_number: checkRecord.certificate_number,
      certificate_issue_date: checkRecord.certificate_issue_date,
      name_on_certificate: checkRecord.name_on_certificate,
      workforce: checkRecord.workforce,
      update_service_registered: checkRecord.update_service_registered,
      update_service_status: checkRecord.update_service_status,
      last_status_check_date: checkRecord.last_status_check_date,
      update_service_check_result: checkRecord.update_service_check_result,
      recheck_required: checkRecord.recheck_required,
      next_recheck_date: checkRecord.next_recheck_date,
      review_due_at: checkRecord.review_due_at,
      result_status: checkRecord.result_status,
      information_present: checkRecord.information_present,
      result_summary: checkRecord.result_summary,
    });
  }

  return base;
}

/**
 * ProofSection — Step 4: Proof of check document
 *
 * RULES (strictly enforced):
 * - Upload Proof: upload file → re-record check with proof_document_id set
 * - Remove Proof: mark doc as uploaded-in-error → re-record check without proof_document_id
 * - Remove Proof NEVER touches evidence files (separate layer)
 * - Gated: cannot upload proof until check record exists
 *
 * Props:
 *  requirementKey     'dbs' | 'right_to_work'
 *  checkRecord        check_data from compliance-file row (or null)
 *  proofDocumentId    string | null — from check_record.proof_document_id
 *  proofDocument      object | null — full proof doc object if available
 *  hasProof           bool
 *  proofRequired      bool — RTW always true; DBS true for update_service_check
 *  employeeId         string
 *  isAdminView        bool
 *  onProofChanged     () => void — trigger parent refresh
 *  onPreviewFile      (file) => void
 */
export function ProofSection({
  requirementKey,
  checkRecord,
  proofDocumentId,
  proofDocument,
  hasProof,
  proofRequired,
  employeeId,
  isAdminView = true,
  onProofChanged,
  onPreviewFile,
}) {
  const { token } = useAuth();
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [removeProofDialogOpen, setRemoveProofDialogOpen] = useState(false);

  const checkType = PROOF_CHECK_TYPE[requirementKey];
  const checkEndpoint =
    PROOF_CHECK_ENDPOINTS[requirementKey]?.(employeeId);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowed = [
      'application/pdf',
      'image/jpeg',
      'image/jpg',
      'image/png',
    ];
    if (!allowed.includes(file.type)) {
      toast.error('Invalid file type. Please upload PDF, JPG, or PNG.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File too large. Maximum 10 MB.');
      return;
    }

    uploadProof(file);
  };

  const uploadProof = async (file) => {
    if (!file || !checkRecord || !checkEndpoint) return;

    setUploading(true);
    try {
      // Step 1: Upload the proof file
      const fd = new FormData();
      fd.append('file', file);
      fd.append('requirement_id', checkType);
      fd.append('document_type', 'verification_proof');
      fd.append(
        'document_label',
        requirementKey === 'right_to_work'
          ? 'RTW Check Proof'
          : 'DBS Check Proof',
      );

      const uploadResp = await axios.post(
        `${API}/employees/${employeeId}/upload-document`,
        fd,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data',
          },
        },
      );

      const proofDocId =
        uploadResp.data?.id || uploadResp.data?.document_id;
      if (!proofDocId) {
        throw new Error('Upload succeeded but no document ID returned');
      }

      // Step 2: Re-record the check with proof_document_id set
      const payload = buildReCheckPayload(checkRecord, proofDocId);
      await axios.post(checkEndpoint, payload, {
        headers: { Authorization: `Bearer ${token}` },
      });

      toast.success('Proof uploaded and linked to check record');
      if (onProofChanged) onProofChanged();
    } catch (err) {
      console.error('Proof upload failed:', err);
      toast.error(
        err.response?.data?.detail || 'Failed to upload proof document',
      );
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleRemoveProof = async () => {
    if (!proofDocumentId || !checkRecord || !checkEndpoint) return;
    setRemoveProofDialogOpen(true);
  };

  const handleConfirmRemoveProof = async () => {
    if (!proofDocumentId || !checkRecord || !checkEndpoint) return;

    setRemoving(true);
    try {
      // Mark the proof file as uploaded in error (soft-removes it)
      await axios.post(
        `${API}/employee-documents/${proofDocumentId}/mark-uploaded-in-error`,
        { reason: 'Proof document removed by admin — replacement required' },
        { headers: { Authorization: `Bearer ${token}` } },
      );

      // Re-record check without proof reference
      const payload = buildReCheckPayload(checkRecord, null);
      await axios.post(checkEndpoint, payload, {
        headers: { Authorization: `Bearer ${token}` },
      });

      toast.success(
        'Proof removed. Evidence files are unaffected. Upload new proof in Step 4.',
      );
      if (onProofChanged) onProofChanged();
    } catch (err) {
      console.error('Proof removal failed:', err);
      toast.error(
        err.response?.data?.detail || 'Failed to remove proof document',
      );
    } finally {
      setRemoving(false);
      setRemoveProofDialogOpen(false);
    }
  };

  const proofFileName =
    proofDocument?.filename ||
    proofDocument?.file_name ||
    proofDocument?.original_filename ||
    'Proof of Check';
  const proofFileUrl =
    proofDocument?.file_url ||
    (proofDocumentId
      ? `${API}/employee-documents/${proofDocumentId}/file`
      : null);

  const handleOpenProofFile = async () => {
    if (!proofFileUrl) return;
    try {
      const requestToken = getProtectedRequestToken(proofFileUrl, token);
      const { blobUrl } = await fetchProtectedFileBlob(proofFileUrl, requestToken);
      downloadBlobUrl(blobUrl, proofFileName || 'proof-document');
      revokeBlobUrlLater(blobUrl, 1000);
    } catch {
      // Preserve current UX: do not add new error toasts for this action.
    }
  };

  return (
    <div
      className="p-4"
      data-testid={`${requirementKey}-proof-section`}
    >
      {/* ── Section header ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
              hasProof
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-primary/10 text-primary'
            }`}
          >
            {hasProof ? <CheckCircle className="h-3.5 w-3.5" /> : '4'}
          </div>
          <h4 className="text-sm font-semibold text-text-primary">
            Proof of Check
          </h4>
          {proofRequired ? (
            <Badge className="text-[10px] px-1.5 py-0 bg-red-100 text-red-700 border border-red-200">
              Required
            </Badge>
          ) : (
            <Badge className="text-[10px] px-1.5 py-0 bg-gray-100 text-gray-500 border border-gray-200">
              Recommended
            </Badge>
          )}
        </div>
        <p className="text-xs text-text-muted">
          {requirementKey === 'right_to_work'
            ? 'Home Office check / PVN screenshot'
            : 'Update Service screenshot / certificate copy'}
        </p>
      </div>

      {hasProof ? (
        <div className="space-y-2">
          {/* ── Proof document row ───────────────────────────────── */}
          <div className="flex items-center justify-between p-3 bg-white border border-emerald-200 rounded-lg">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center flex-shrink-0">
                <Shield className="h-4 w-4 text-emerald-600" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">
                  {proofFileName}
                </p>
                {proofDocument?.uploaded_at && (
                  <p className="text-xs text-text-muted">
                    Uploaded{' '}
                    {formatBackendDate(proofDocument.uploaded_at, {
                      format: 'medium',
                    })}

                    <Dialog open={removeProofDialogOpen} onOpenChange={setRemoveProofDialogOpen}>
                      <DialogContent className="sm:max-w-md">
                        <DialogHeader>
                          <DialogTitle>Remove Proof Document</DialogTitle>
                        </DialogHeader>
                        <p className="text-sm text-text-muted py-2">
                          This removes the proof link from the check record. Evidence files remain unchanged.
                        </p>
                        <DialogFooter>
                          <Button variant="outline" onClick={() => setRemoveProofDialogOpen(false)}>
                            Cancel
                          </Button>
                          <Button
                            className="bg-red-600 hover:bg-red-700 text-white"
                            onClick={handleConfirmRemoveProof}
                            disabled={removing}
                          >
                            {removing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                            Remove Proof
                          </Button>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              <Badge className="text-[10px] px-1.5 py-0 bg-emerald-100 text-emerald-700 border border-emerald-200">
                <CheckCircle className="h-2.5 w-2.5 mr-0.5" />
                Attached
              </Badge>

              {/* View (preview-first) */}
              <Button
                size="sm"
                variant="ghost"
                className="h-7 w-7 p-0 text-gray-400 hover:text-blue-600"
                onClick={async () => {
                  const stampByName =
                    proofDocument?.verification_stamp_by_name ||
                    proofDocument?.verified_by_name ||
                    (typeof proofDocument?.verification_stamp === 'object' ? proofDocument.verification_stamp?.verified_by_name : null) ||
                    null;
                  const stampAt =
                    proofDocument?.verification_stamp_at ||
                    proofDocument?.verified_at ||
                    (typeof proofDocument?.verification_stamp === 'object' ? proofDocument.verification_stamp?.verified_at : null) ||
                    null;
                  if (isPreviewableFile(proofDocument) && onPreviewFile) {
                    onPreviewFile({
                      file_url: proofFileUrl,
                      file_name: proofFileName,
                      stamped_file_url: proofDocument?.stamped_file_url || null,
                      verification_stamp_by_name: stampByName,
                      verification_stamp_at: stampAt,
                    });
                  } else {
                    // fallback to download
                    try {
                      const requestToken = getProtectedRequestToken(proofFileUrl, token);
                      const { blobUrl } = await fetchProtectedFileBlob(proofFileUrl, requestToken);
                      downloadBlobUrl(blobUrl, proofFileName || 'proof-document');
                      revokeBlobUrlLater(blobUrl, 1000);
                    } catch {
                      // Preserve current UX: do not add new error toasts for this action.
                    }
                  }
                }}
                title="Preview proof document"
              >
                <Eye className="h-3.5 w-3.5" />
              </Button>

              {/* Download */}
              <Button
                size="sm"
                variant="ghost"
                className="h-7 w-7 p-0 text-gray-400 hover:text-green-600"
                onClick={handleOpenProofFile}
                title="Download proof document"
              >
                <Download className="h-3.5 w-3.5" />
              </Button>

              {/* Admin: Replace / Remove */}
              {isAdminView && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                    data-testid={`${requirementKey}-replace-proof-btn`}
                    title="Replace proof document"
                  >
                    {uploading ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <RefreshCw className="h-3 w-3 mr-1" />
                    )}
                    Replace
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 w-7 p-0 text-red-400 hover:text-red-600 hover:bg-red-50"
                    onClick={handleRemoveProof}
                    disabled={removing}
                    data-testid={`${requirementKey}-remove-proof-btn`}
                    title="Remove proof (does not affect evidence files)"
                  >
                    {removing ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <X className="h-3.5 w-3.5" />
                    )}
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* Evidence-safety notice */}
          <p className="text-[10px] text-text-muted bg-gray-50 border border-gray-100 rounded px-2 py-1">
            <Shield className="h-2.5 w-2.5 inline mr-1 text-gray-400" />
            Proof and evidence are stored independently. Removing proof
            does not affect evidence files.
          </p>
        </div>
      ) : (
        /* ── No proof yet ───────────────────────────────────────── */
        <div
          className={`p-3 bg-white border rounded-lg ${
            proofRequired
              ? 'border-dashed border-amber-300'
              : 'border-dashed border-gray-200'
          }`}
        >
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <FileText className="h-4 w-4 text-gray-400" />
                <p
                  className={`text-sm ${
                    proofRequired
                      ? 'text-amber-700 font-medium'
                      : 'text-text-muted'
                  }`}
                >
                  {proofRequired
                    ? 'Proof document required'
                    : 'No proof document attached'}
                </p>
              </div>
              {!checkRecord && (
                <p className="text-xs text-text-muted mt-0.5">
                  <AlertTriangle className="h-3 w-3 inline mr-1 text-amber-500" />
                  Complete Step 3 (Record Check) before uploading proof
                </p>
              )}
            </div>
            {isAdminView && checkRecord && (
              <Button
                size="sm"
                variant={proofRequired ? 'default' : 'outline'}
                className="h-8 text-xs flex-shrink-0"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                data-testid={`${requirementKey}-upload-proof-btn`}
              >
                {uploading ? (
                  <>
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    Uploading…
                  </>
                ) : (
                  <>
                    <Upload className="h-3.5 w-3.5 mr-1" />
                    Upload Proof
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg"
        className="hidden"
        onChange={handleFileSelect}
        data-testid={`${requirementKey}-proof-file-input`}
      />
    </div>
  );
}

