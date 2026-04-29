import { useState, useEffect } from 'react';
// UI-only: Hide Staff Health Questionnaire from Checks & Evidence
const STAFF_HEALTH_KEY = 'staff_health_questionnaire';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Loader2, AlertTriangle, Shield, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

import EvidenceRow from './EvidenceRow';
import CheckRow from './CheckRow';
import AgreementRow from './AgreementRow';
import ReferenceRow from './ReferenceRow';
import FormRequirementRow from './FormRequirementRow';
import UploadRequirementCard from './UploadRequirementCard';
import EvidenceManageDrawer from './EvidenceManageDrawer';
import RequirementFilesDrawer from './RequirementFilesDrawer';
import RequirementHistoryDrawer from './RequirementHistoryDrawer';
import ReferenceResponseDrawer from './ReferenceResponseDrawer';
import AgreementFormDrawer from './AgreementFormDrawer';
import FormSubmissionDrawer from './FormSubmissionDrawer';
import ApplicationFormViewDrawer from './ApplicationFormViewDrawer';
import RejectFormDialog from './RejectFormDialog';
import { normalizeUploadRequirementSurface } from './surfaceNormalizers';
import { UPLOAD_REQUIREMENT_KEYS } from './complianceRequirementMap';
import { RequirementWorkflowCard } from './workflow';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

const normalizeComplianceSections = (sections) => {
  if (!sections) return {};
  if (Array.isArray(sections)) {
    return sections.reduce((acc, section, index) => {
      const key = section?.key || section?.id || section?.section_key || section?.requirement_id || `section_${index}`;
      if (key) acc[String(key)] = section;
      return acc;
    }, {});
  }
  if (typeof sections === 'object') return sections;
  return {};
};

/**
 * DualRowComplianceSection - Displays the dual-row compliance file structure
 * 
 * Renders paired evidence/check rows for each compliance area:
 * - Right to Work (Evidence + Check)
 * - DBS (Evidence + Check)
 * - Identity (Evidence + Verification)
 * - Proof of Address (Evidence + Verification)
 * - Agreements (Contract Acceptance, Handbook Acknowledgement)
 * 
 * The backend returns serializer_version: "dual_row_v1" with explicit row_type
 * and allowed_actions per row.
 */
export default function DualRowComplianceSection({
  employeeId,
  employeeEmail,
  employeeName,
  employeeData,  // Full employee data for pre-filling forms
  onUpload,
  onRequest,
  onPreviewFile,
  onExtractReview,
  onRecordCheck,
  onReissueContract,
  isAuditor = false,
  onRefresh
}) {
  const [complianceFile, setComplianceFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // STEP 11E: Centralized open state for all requirement sections
  const [expandedSections, setExpandedSections] = useState({
    right_to_work: true,
    dbs: true,
    identity: true,
    proof_of_address: true,
    agreements: true,
    references: true,
    training: false,
    recruitment_record: false,
    health_competency: false,
    admin_forms: false
  });
  
  // Form submission drawer state (for new form-type requirements)
  const [formDrawer, setFormDrawer] = useState({
    isOpen: false,
    formKey: null,
    formType: null,
    submissionId: null,
    mode: 'create' // 'create', 'view', 'edit'
  });
  
  // Phase D2: Files drawer state (for legacy rows)
  const [filesDrawer, setFilesDrawer] = useState({
    open: false,
    requirementKey: null,
    requirementTitle: ''
  });
  
  // Ticket C: Shared upload drawer state for RTW, DBS, Identity, PoA
  const [uploadDrawer, setUploadDrawer] = useState({
    isOpen: false,
    requirementKey: null
  });
  
  // Phase D3: History drawer state
  const [historyDrawer, setHistoryDrawer] = useState({
    open: false,
    requirementKey: null,
    requirementTitle: ''
  });
  
  // Ticket E: Reference response drawer state
  const [referenceDrawer, setReferenceDrawer] = useState({
    open: false,
    referenceNum: null
  });
  
  // Ticket D: Agreement form drawer state
  const [agreementDrawer, setAgreementDrawer] = useState({
    isOpen: false,
    templateId: null,
    mode: 'create', // 'create' or 'view'
    submissionId: null,
    agreementKey: null,
    agreementTitle: null
  });
  
  // Application Form viewer drawer state (separate from template-based forms)
  const [applicationFormDrawer, setApplicationFormDrawer] = useState({
    isOpen: false,
    submissionId: null
  });
  
  // Reject form dialog state
  const [rejectDialog, setRejectDialog] = useState({
    isOpen: false,
    submissionId: null,
    formName: '',
    formKey: null
  });
  const [rejectLoading, setRejectLoading] = useState(false);
  
  const { token } = useAuth();
  
  // Open upload drawer for upload-type requirements
  const openUploadDrawer = (requirementKey) => {
    setUploadDrawer({ isOpen: true, requirementKey });
  };
  
  const closeUploadDrawer = () => {
    setUploadDrawer({ isOpen: false, requirementKey: null });
  };
  
  // Open files drawer for a requirement (legacy)
  const handleViewFiles = (requirementKey, requirementTitle) => {
    setFilesDrawer({
      open: true,
      requirementKey,
      requirementTitle
    });
  };
  
  // Open history drawer for a requirement
  const handleViewHistory = (requirementKey, requirementTitle) => {
    setHistoryDrawer({
      open: true,
      requirementKey,
      requirementTitle
    });
  };

  // Fetch compliance file data
  const fetchComplianceFile = async () => {
    if (!employeeId || !token) {
      console.debug('Skipping dual-row compliance-file fetch until employeeId and auth token are available');
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/compliance-file`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const payload = (response?.data && typeof response.data === 'object') ? response.data : {};
      const normalizedSections = normalizeComplianceSections(payload.sections);
      
      // Verify it's the dual-row format
      if (payload.serializer_version && payload.serializer_version !== 'dual_row_v1') {
        console.warn('Unexpected serializer version:', payload.serializer_version);
      }
      
      setComplianceFile((prev) => {
        const prevSections = normalizeComplianceSections(prev?.sections);
        const nextHasSections = Object.keys(normalizedSections).length > 0;
        const prevHasSections = Object.keys(prevSections).length > 0;
        if (payload?.serializer_version === 'dual_row_v1' && !nextHasSections && prevHasSections) {
          console.warn('dual_row_v1 returned empty sections; preserving previous valid compliance sections', {
            employeeId,
            previousSectionCount: Object.keys(prevSections).length
          });
          return {
            ...payload,
            sections: prevSections,
            summary: (payload.summary && typeof payload.summary === 'object')
              ? payload.summary
              : { status_unavailable: Boolean(payload.status_unavailable), overall_status: 'unavailable', ready_for_work: false },
          };
        }
        return {
          ...payload,
          sections: normalizedSections,
          summary: (payload.summary && typeof payload.summary === 'object')
            ? payload.summary
            : { status_unavailable: Boolean(payload.status_unavailable), overall_status: 'unavailable', ready_for_work: false },
        };
      });
    } catch (err) {
      const message = err?.response?.data?.message || err?.response?.data?.detail || err?.message || 'Failed to load compliance file';
      setError(message);
      setComplianceFile({
        employee_id: employeeId,
        status_unavailable: true,
        message: 'Compliance temporarily unavailable',
        sections: {},
        summary: { status_unavailable: true, overall_status: 'unavailable', ready_for_work: false },
      });
      toast.error('Compliance temporarily unavailable');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComplianceFile();
  }, [employeeId, token]);

  // Refresh handler
  const handleRefresh = () => {
    fetchComplianceFile();
    if (onRefresh) onRefresh();
  };

  // Toggle section expansion
  const toggleSection = (sectionKey) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionKey]: !prev[sectionKey]
    }));
  };

  /**
   * Transform backend evidence/check rows into a normalized surface for UploadRequirementCard
   */
  const transformToUploadSurface = (sectionKey, section) => {
    if (!section || !Array.isArray(section.rows)) return null;
    
    const evidenceRow = section.rows.find(r => r?.row_type === 'evidence');
    const checkRow = section.rows.find(r => r?.row_type === 'check');
    
    if (!evidenceRow) return null;
    
    // Transform documents_preview to files array format
    const baseActiveDocs = Array.isArray(evidenceRow.active_documents)
      ? evidenceRow.active_documents
      : (Array.isArray(evidenceRow.documents_preview) ? evidenceRow.documents_preview : []);
    const seenDocIds = new Set();
    const dedupedActiveDocs = baseActiveDocs.filter((doc) => {
      const id = doc?.id || doc?.file_id || doc?.document_id;
      if (!id) return true;
      if (seenDocIds.has(id)) return false;
      seenDocIds.add(id);
      return true;
    });
    const files = dedupedActiveDocs.map(doc => ({
      file_id: doc.id,
      id: doc.id,
      file_name: doc.file_name,
      original_filename: doc.file_name,
      file_url: doc.file_url,
      stamped_file_url: doc.stamped_file_url || null,
      uploaded_at: doc.uploaded_at,
      uploaded_by: doc.uploaded_by,
      verified: doc.verified || false,
      verified_by: doc.verified_by,
      verified_by_name: doc.verified_by_name,
      verified_at: doc.verified_at,
      status: doc.status || 'active',
      extraction_status: doc.extraction_status,
      // Verification stamp fields - CRITICAL for stamp UI
      verification_stamp: doc.verification_stamp,
      verification_stamp_label: doc.verification_stamp_label,
      verification_stamp_audit_text: doc.verification_stamp_audit_text,
      verification_stamp_badge_color: doc.verification_stamp_badge_color,
      verification_stamp_by_name: doc.verification_stamp_by_name,
      verification_stamp_at: doc.verification_stamp_at,
      // Rejection fields
      rejected_by: doc.rejected_by,
      rejected_by_name: doc.rejected_by_name,
      rejected_at: doc.rejected_at,
      rejection_reason: doc.rejection_reason
    }));
    
    // Add freshness data for PoA files
    if (sectionKey === 'proof_of_address' && checkRow?.freshness?.documents) {
      const freshnessMap = {};
      checkRow.freshness.documents.forEach(fd => {
        freshnessMap[fd.file_id] = fd;
      });
      
      files.forEach(file => {
        const fd = freshnessMap[file.file_id];
        if (fd) {
          file.freshness_status = fd.status;
          file.freshness_is_valid = fd.is_valid;
          file.freshness_reason = fd.reason;
          file.document_date = fd.document_date;
          file.months_old = fd.months_old;
        }
      });
    }
    
    // Add remaining files if has_more_documents indicates there are more
    // The counts tell us how many total active files
    const totalActive = evidenceRow.counts?.active_files || files.length;
    const historyDocs = Array.isArray(evidenceRow.history_documents)
      ? evidenceRow.history_documents
      : (Array.isArray(evidenceRow.historical_documents) ? evidenceRow.historical_documents : []);
    const totalHistorical = historyDocs.length > 0
      ? historyDocs.length
      : ((evidenceRow.counts?.superseded || 0) + (evidenceRow.counts?.history || 0) - totalActive);
    
    // Transform request_lifecycle to requests array
    const requests = [];
    if (evidenceRow.request_lifecycle?.current_request) {
      const req = evidenceRow.request_lifecycle.current_request;
      requests.push({
        request_id: req.id,
        status: req.status,
        sent_at: req.sent_at,
        viewed_at: req.viewed_at,
        submitted_at: req.submitted_at,
        reminder_count: req.reminder_count || 0,
        is_replacement: req.is_replacement || false
      });
    }
    
    // Transform check row to checks array
    // Backend returns check_data in check rows, not check_record
    const checks = [];
    if (checkRow && (checkRow.check_data || checkRow.has_check)) {
      const check = checkRow.check_data || {};
      checks.push({
        id: check.id,
        status: check.outcome || (checkRow.is_verified ? 'verified' : 'pending'),
        outcome: check.outcome,
        method: check.method,
        checked_at: check.checked_at,
        checked_by: check.checked_by,
        checked_by_name: check.checked_by_name,
        notes: check.notes,
        follow_up_date: checkRow.follow_up_info?.date || check.follow_up_date,
        updated_at: check.updated_at,
        // COMPLIANCE-CRITICAL: Include verification proof document link
        evidence_document_id: check.evidence_document_id,
        evidence_document: check.evidence_document,
        // IDENTITY-SPECIFIC FIELDS
        document_type: check.document_type,
        full_name_on_document: check.full_name_on_document,
        date_of_birth: check.date_of_birth,
        document_number: check.document_number,
        issue_date: check.issue_date,
        expiry_date: check.expiry_date,
        nationality: check.nationality,
        name_matches_application: check.name_matches_application,
        dob_matches_application: check.dob_matches_application,
        photo_match_confirmed: check.photo_match_confirmed,
        identity_status: check.identity_status,
        // RTW-SPECIFIC FIELDS
        permission_type: check.permission_type,
        permission_start_date: check.permission_start_date,
        permission_end_date: check.permission_end_date,
        is_indefinite: check.is_indefinite,
        share_code: check.share_code,
        reference_number: check.reference_number,
        restrictions: check.restrictions,
        hours_limit: check.hours_limit,
        follow_up_required: check.follow_up_required,
        follow_up_due_at: check.follow_up_due_at,
        route: check.route,
        // DBS-SPECIFIC FIELDS
        dbs_level: check.dbs_level,
        certificate_number: check.certificate_number,
        certificate_issue_date: check.certificate_issue_date,
        name_on_certificate: check.name_on_certificate,
        workforce: check.workforce,
        update_service_registered: check.update_service_registered,
        update_service_status: check.update_service_status,
        last_status_check_date: check.last_status_check_date,
        update_service_check_result: check.update_service_check_result,
        result_status: check.result_status,
        information_present: check.information_present,
        result_summary: check.result_summary,
        recheck_required: check.recheck_required,
        next_recheck_date: check.next_recheck_date,
        dbs_status: check.dbs_status,
        // POA-SPECIFIC FIELDS (from address_verification row)
        documents_received_count: check.documents_received_count,
        documents_required_count: check.documents_required_count,
        verified_documents: check.verified_documents,
        extracted_address_line1: check.extracted_address_line1,
        extracted_address_line2: check.extracted_address_line2,
        extracted_city: check.extracted_city,
        extracted_postcode: check.extracted_postcode,
        address_matches_application: check.address_matches_application,
        all_documents_sufficiently_recent: check.all_documents_sufficiently_recent,
        address_status: check.address_status
      });
    }
    
    // Use the normalizer with transformed data
    return normalizeUploadRequirementSurface({
      requirementKey: sectionKey,
      files,
      requests,
      checks,
      freshness: sectionKey === 'proof_of_address' && checkRow ? checkRow.freshness : null,
      serverCounts: evidenceRow.counts || null,
      canonicalStatus: checkRow?.status || evidenceRow.status || null,
      canonicalStatusUnavailable: Boolean(evidenceRow.status_unavailable || checkRow?.status_unavailable),
      canonicalWarnings: [
        ...((Array.isArray(evidenceRow.warnings) ? evidenceRow.warnings : [])),
        ...((Array.isArray(checkRow?.warnings) ? checkRow.warnings : []))
      ],
      canonicalVerified: Boolean(evidenceRow.is_verified || checkRow?.is_verified || evidenceRow.verified || checkRow?.verified),
    });
  };

  // Requirements that use the staged workflow card
  const WORKFLOW_CARD_KEYS = new Set([
    'right_to_work',
    'dbs',
    'identity',
    'proof_of_address',
  ]);

  /**
   * Render upload-type requirement.
   * RTW, DBS, Identity, and PoA use the same staged compliance workflow.
   */
  const renderUploadSection = (sectionKey, section) => {
    // Staged workflow card for compliance-critical evidence and checks
    if (WORKFLOW_CARD_KEYS.has(sectionKey)) {
      return (
        <div key={sectionKey} className="mb-6" data-testid={`section-${sectionKey}`}>
          <RequirementWorkflowCard
            requirementKey={sectionKey}
            sectionData={section}
            employeeId={employeeId}
            employeeName={employeeName}
            onRefresh={handleRefresh}
            isAdminView={!isAuditor}
            onPreviewFile={onPreviewFile}
            onUploadEvidence={() => openUploadDrawer(sectionKey)}
            defaultOpen={expandedSections[sectionKey] !== false}
          />
        </div>
      );
    }

    // Legacy fallback for any future upload-style section not yet workflow-enabled
    const surface = transformToUploadSurface(sectionKey, section);
    if (!surface) return null;
    
    const isExpanded = expandedSections[sectionKey] !== false;
    
    return (
      <div key={sectionKey} className="mb-6" data-testid={`section-${sectionKey}`}>
        <UploadRequirementCard
          surface={surface}
          isOpen={isExpanded}
          onToggle={() => toggleSection(sectionKey)}
          onOpenDrawer={() => openUploadDrawer(sectionKey)}
          onUpload={() => onUpload && onUpload(`${sectionKey}_evidence`)}
          onRequest={() => onRequest && onRequest(`${sectionKey}_evidence`, section.title)}
          onResend={() => onRequest && onRequest(`${sectionKey}_evidence`, section.title)}
          onRecordCheck={() => onRecordCheck && onRecordCheck(sectionKey)}
          onUpdateCheck={() => onRecordCheck && onRecordCheck(sectionKey)}
          onViewHistory={() => handleViewHistory(sectionKey, section.title)}
          onPreviewFile={onPreviewFile}
          employeeId={employeeId}
          employeeName={employeeName}
          onRefresh={handleRefresh}
          isAuditor={isAuditor}
        />
      </div>
    );
  };

  // Render a legacy section with paired rows (for agreements and references)
  const renderSection = (sectionKey, section) => {
    if (!section || !Array.isArray(section.rows)) return null;
    
    const isExpanded = expandedSections[sectionKey] !== false;
    
    // Count blockers in this section
    const blockers = section.rows.filter(r => r?.blocker_text);
    const isAgreementsSection = sectionKey === 'agreements';
    const agreementRows = isAgreementsSection
      ? section.rows
          .filter((row) => row?.row_type === 'form_acknowledgement')
          .filter((row) => row?.latest_active !== false)
          .filter((row, idx, arr) => arr.findIndex((x) => x?.id === row?.id) === idx)
      : [];
    const agreementSatisfiedCount = agreementRows.filter((row) => row.is_verified).length;
    const agreementPendingReviewCount = agreementRows.filter((row) => (
      !row.is_verified && (
        row.has_acknowledgement ||
        row.submission_data ||
        row.acknowledgement_data?.submission_id
      )
    )).length;
    const agreementMissingCount = agreementRows.filter((row) => (
      !row.is_verified &&
      !row.has_acknowledgement &&
      !row.submission_data &&
      !row.acknowledgement_data?.submission_id
    )).length;
    
    const operationalRows = section.rows
      .filter((row) => row?.latest_active !== false)
      .filter((row, idx, arr) => {
        const stableKey = [
          row?.row_type,
          row?.key,
          row?.id,
          row?.requirement_id,
          row?.template_version,
          row?.submission_id,
          row?.reference_num
        ].filter(Boolean).join('::');
        if (!stableKey) return true;
        return arr.findIndex((x) => [
          x?.row_type,
          x?.key,
          x?.id,
          x?.requirement_id,
          x?.template_version,
          x?.submission_id,
          x?.reference_num
        ].filter(Boolean).join('::') === stableKey) === idx;
      });

    return (
      <div key={sectionKey} className="mb-6" data-testid={`section-${sectionKey}`}>
        {/* Section Header */}
        <div 
          className="flex items-center justify-between p-3 bg-gray-50 rounded-t-xl cursor-pointer hover:bg-gray-100 transition-colors"
          onClick={() => toggleSection(sectionKey)}
        >
          <div className="flex items-center gap-3">
            <h3 className="font-heading font-semibold text-text-primary">{section.title}</h3>
            {blockers.length > 0 && (
              <Badge className="bg-red-100 text-red-700 text-xs">
                {blockers.length} blocking
              </Badge>
            )}
            {isAgreementsSection && agreementPendingReviewCount > 0 && (
              <Badge className="bg-amber-100 text-amber-700 text-xs">
                {agreementPendingReviewCount} awaiting admin review
              </Badge>
            )}
            {isAgreementsSection && agreementSatisfiedCount > 0 && (
              <Badge className="bg-emerald-100 text-emerald-700 text-xs">
                {agreementSatisfiedCount} checks complete
              </Badge>
            )}
          </div>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
        
        {/* Section Content */}
        {isExpanded && (
          <div className="space-y-3 p-3 bg-white border border-t-0 border-gray-200 rounded-b-xl">
            {isAgreementsSection && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                <span className="font-medium">Agreements readiness impact:</span>{' '}
                {blockers.length} blocking readiness &nbsp;|&nbsp;
                {agreementPendingReviewCount} awaiting admin review &nbsp;|&nbsp;
                {agreementMissingCount} awaiting worker &nbsp;|&nbsp;
                {agreementSatisfiedCount} checks complete
              </div>
            )}
            {operationalRows.map((row, idx) => {
              if (!row || typeof row !== 'object') return null;
              // CV row is evidence type but should use FormRequirementRow for file display
              if (row.row_type === 'evidence' && row.key !== 'cv') {
                return (
                  <EvidenceRow
                    key={row.key || idx}
                    row={row}
                    employeeId={employeeId}
                    employeeEmail={employeeEmail}
                    onRefresh={handleRefresh}
                    onUpload={onUpload}
                    onRequest={onRequest}
                    onPreviewFile={onPreviewFile}
                    onExtractReview={onExtractReview}
                    onViewFiles={handleViewFiles}
                    onViewHistory={handleViewHistory}
                    onReissueContract={onReissueContract}
                    isAuditor={isAuditor}
                  />
                );
              }
              
              if (row.row_type === 'check') {
                return (
                  <CheckRow
                    key={row.key || idx}
                    row={row}
                    employeeId={employeeId}
                    onRefresh={handleRefresh}
                    onRecordCheck={onRecordCheck}
                    onViewHistory={handleViewHistory}
                    onPreviewFile={onPreviewFile}
                    isAuditor={isAuditor}
                  />
                );
              }
              
              if (row.row_type === 'form_acknowledgement') {
                return (
                  <AgreementRow
                    key={row.key || idx}
                    row={row}
                    employeeId={employeeId}
                    employeeEmail={employeeEmail}
                    employeeData={employeeData}
                    onRefresh={handleRefresh}
                    onOpenForm={(agreementKey, title, templateId, mode) => {
                      setAgreementDrawer({
                        isOpen: true,
                        templateId,
                        mode: 'create',
                        submissionId: null,
                        agreementKey,
                        agreementTitle: title
                      });
                    }}
                    onViewSubmission={(agreementKey, title, templateId, submissionId) => {
                      setAgreementDrawer({
                        isOpen: true,
                        templateId,
                        mode: 'view',
                        submissionId,
                        agreementKey,
                        agreementTitle: title
                      });
                    }}
                    onViewHistory={handleViewHistory}
                    onReissueContract={onReissueContract}
                    isAuditor={isAuditor}
                  />
                );
              }
              
              if (row.row_type === 'reference') {
                return (
                  <ReferenceRow
                    key={row.key || idx}
                    row={row}
                    employeeId={employeeId}
                    onRefresh={handleRefresh}
                    onViewHistory={handleViewHistory}
                    onViewResponse={(refNum) => {
                      // Open reference response drawer
                      setReferenceDrawer({ open: true, referenceNum: refNum });
                    }}
                    onVerify={async (refNum) => {
                      try {
                        // Simple verification - assumes from_cv=true
                        // A more complete implementation would open a dialog asking about CV match
                        await axios.post(
                          `${API}/employees/${employeeId}/verify-reference`,
                          { 
                            reference_num: refNum,
                            from_cv: true
                          },
                          { headers: { Authorization: `Bearer ${token}` } }
                        );
                        toast.success(`Reference ${refNum} verified`);
                        handleRefresh();
                      } catch (err) {
                        toast.error(err.response?.data?.detail || 'Failed to verify reference');
                      }
                    }}
                    onReject={async (refNum) => {
                      try {
                        await axios.post(
                          `${API}/references/${employeeId}/${refNum}/reject`,
                          { rejection_reason: 'Rejected by admin' },
                          { headers: { Authorization: `Bearer ${token}` } }
                        );
                        toast.success(`Reference ${refNum} rejected`);
                        handleRefresh();
                      } catch (err) {
                        toast.error(err.response?.data?.detail || 'Failed to reject reference');
                      }
                    }}
                    isAuditor={isAuditor}
                  />
                );
              }
              
              // Form-type requirement rows
              if (row.row_type === 'form' || row.row_type === 'evidence' && row.key === 'cv') {
                return (
                  <FormRequirementRow
                    key={row.key || idx}
                    row={row}
                    employeeId={employeeId}
                    employeeEmail={employeeEmail}
                    employeeName={employeeName}
                    onRefresh={handleRefresh}
                    onOpenForm={(formKey, formType, submissionId) => {
                      // SPECIAL CASE: Application forms use a dedicated viewer
                      // They don't have an editable template - view only
                      if (formKey === 'application_form') {
                        setApplicationFormDrawer({
                          isOpen: true,
                          submissionId
                        });
                        return;
                      }
                      setFormDrawer({
                        isOpen: true,
                        formKey,
                        formType,
                        submissionId,
                        mode: submissionId ? 'edit' : 'create'
                      });
                    }}
                    onViewSubmission={(formKey, formType, submissionId) => {
                      // SPECIAL CASE: Application forms use a dedicated viewer
                      // because they don't have a template in FORM_BASED_REQUIREMENTS
                      if (formKey === 'application_form') {
                        setApplicationFormDrawer({
                          isOpen: true,
                          submissionId
                        });
                      } else {
                        setFormDrawer({
                          isOpen: true,
                          formKey,
                          formType,
                          submissionId,
                          mode: 'view'
                        });
                      }
                    }}
                    onSendForm={async (formKey, empId, empEmail) => {
                      try {
                        await axios.post(
                          `${API}/employees/${empId}/send-form?form_type=${formKey}`,
                          {},
                          { headers: { Authorization: `Bearer ${token}` } }
                        );
                        toast.success(`Form sent to ${empEmail}`);
                        handleRefresh();
                      } catch (err) {
                        toast.error(err.response?.data?.detail || 'Failed to send form');
                      }
                    }}
                    onExportPdf={async (formKey, formType, submissionId) => {
                      try {
                        const response = await axios.get(
                          `${API}/form-submissions/${submissionId}/download-pdf`,
                          { 
                            headers: { Authorization: `Bearer ${token}` },
                            responseType: 'blob'
                          }
                        );
                        const url = window.URL.createObjectURL(new Blob([response.data]));
                        const link = document.createElement('a');
                        link.href = url;
                        link.download = `${formKey}_${submissionId}.pdf`;
                        link.click();
                        window.URL.revokeObjectURL(url);
                      } catch (err) {
                        toast.error('Failed to download PDF');
                      }
                    }}
                    onVerify={async (submissionId) => {
                      try {
                        await axios.post(
                          `${API}/form-submissions/${submissionId}/verify`,
                          {},
                          { headers: { Authorization: `Bearer ${token}` } }
                        );
                        toast.success('Form verified successfully');
                        handleRefresh();
                      } catch (err) {
                        toast.error(err.response?.data?.detail || 'Failed to verify form');
                      }
                    }}
                    onReject={(submissionId, formName) => {
                      setRejectDialog({
                        isOpen: true,
                        submissionId,
                        formName: formName || row.title,
                        formKey: row.key
                      });
                    }}
                    onViewHistory={(reqKey, title) => handleViewHistory(reqKey, title)}
                    onPreviewFile={onPreviewFile}
                    onUpload={(reqKey) => {
                      // For evidence-type rows (like CV), use the key directly
                      // For form-type rows, add _evidence suffix
                      const uploadKey = row.row_type === 'evidence' ? reqKey : `${reqKey}_evidence`;
                      onUpload && onUpload(uploadKey);
                    }}
                    isAuditor={isAuditor}
                  />
                );
              }
              
              return null;
            })}
          </div>
        )}
      </div>
    );
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-text-muted">Loading compliance file...</span>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="h-12 w-12 mx-auto text-red-400 mb-4" />
        <p className="font-medium text-amber-700">Compliance temporarily unavailable</p>
        <p className="text-sm text-amber-700 mt-1 mb-4">{error}</p>
        <p className="text-xs text-red-500 mb-4">Verification and row actions are unavailable until this source loads.</p>
        <Button variant="outline" onClick={handleRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  if (!complianceFile) {
    return null;
  }

  const hasAnySections =
    complianceFile?.sections &&
    typeof complianceFile.sections === 'object' &&
    Object.keys(complianceFile.sections).length > 0;

  if (complianceFile?.status_unavailable && !hasAnySections) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        <p className="font-medium">Compliance temporarily unavailable</p>
        <p className="mt-1">{complianceFile?.message || 'Some compliance checks are temporarily unavailable.'}</p>
      </div>
    );
  }

  // UI-only: filter out staff_health_questionnaire from all sections before rendering
  const { summary } = complianceFile;
  // Deep clone sections to avoid mutating original
  const filteredSections = (() => {
    if (!complianceFile.sections || typeof complianceFile.sections !== 'object') return {};
    const clone = {};
    for (const [sectionKey, section] of Object.entries(complianceFile.sections)) {
      if (!section || !Array.isArray(section.rows)) {
        clone[sectionKey] = section;
        continue;
      }
      clone[sectionKey] = {
        ...section,
        rows: section.rows.filter(row => row.key !== STAFF_HEALTH_KEY)
      };
    }
    return clone;
  })();
  const sectionRows = Object.values(filteredSections || {}).flatMap((section) => Array.isArray(section?.rows) ? section.rows : []);
  const sectionUnavailableCount = Object.values(filteredSections || {}).filter(
    (section) => Boolean(section?.status_unavailable) || !Array.isArray(section?.rows)
  ).length;
  const blockerCount = sectionRows.filter((row) => row.blocker_text).length;
  const pendingReviewCount = sectionRows.filter((row) => (
    row.status === 'submitted' ||
    row.status === 'awaiting_review' ||
    row.status === 'pending' ||
    row.status === 'response_received' ||
    row.requires_admin_review
  )).length;
  const coreRequirementKeys = ['right_to_work', 'dbs', 'identity', 'proof_of_address'];
  const presentCoreRequirementKeys = coreRequirementKeys.filter((key) => filteredSections?.[key]);
  const coreSatisfiedCount = presentCoreRequirementKeys.filter((key) => {
    const rows = filteredSections[key]?.rows || [];
    const evidenceRow = rows.find((row) => row.row_type === 'evidence');
    const checkRow = rows.find((row) => row.row_type === 'check');
    const evidenceDocs = evidenceRow?.documents_preview || [];
    const hasAcceptedEvidence =
      evidenceRow?.is_verified ||
      evidenceRow?.status === 'verified' ||
      evidenceRow?.status === 'accepted' ||
      evidenceDocs.some((doc) => (
        doc.verified ||
        doc.status === 'verified' ||
        doc.status === 'accepted' ||
        doc.status === 'approved'
      ));
    const checkData = checkRow?.check_data || {};
    const hasVerifiedCheck =
      checkRow?.is_verified ||
      checkData.outcome === 'verified' ||
      checkData.status === 'verified';
    const proofRequired =
      key === 'right_to_work' ||
      (key === 'dbs' && checkData.method === 'dbs_update_service_check');
    const hasProof = Boolean(checkData.proof_document_id || checkData.evidence_document_id);

    return hasAcceptedEvidence && hasVerifiedCheck && (!proofRequired || hasProof);
  }).length;
  const agreementRowsForSummary = Array.isArray(filteredSections?.agreements?.rows)
    ? filteredSections.agreements.rows.filter((row) => row.row_type === 'form_acknowledgement')
    : [];
  const agreementSatisfiedCount = agreementRowsForSummary.filter((row) => row.is_verified).length;
  const agreementBlockingCount = agreementRowsForSummary.filter((row) => row.blocker_text).length;
  const satisfiedRequirementCount = coreSatisfiedCount + agreementSatisfiedCount;
  const totalRequirementCount = presentCoreRequirementKeys.length + agreementRowsForSummary.length;

  const renderUnavailableSection = (sectionKey, sectionTitle, sectionObj) => {
    console.warn('compliance-section-unavailable', {
      employeeId,
      sectionKey,
      status_unavailable: sectionObj?.status_unavailable === true,
      warning_count: Array.isArray(sectionObj?.warnings) ? sectionObj.warnings.length : 0,
    });
    return (
      <div key={sectionKey} className="mb-6" data-testid={`section-${sectionKey}-unavailable`}>
        <Card className="border border-amber-200 bg-amber-50/40">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-amber-900">{sectionTitle}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-amber-800">
            <p>Temporarily unavailable for this section.</p>
            {Array.isArray(sectionObj?.warnings) && sectionObj.warnings.length > 0 && (
              <ul className="mt-2 list-disc pl-5">
                {sectionObj.warnings.slice(0, 3).map((warning, idx) => (
                  <li key={`${sectionKey}-warning-${idx}`}>{String(warning)}</li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <div className="space-y-6" data-testid="dual-row-compliance-section">
      {/* Refresh Button */}
      <div className="flex justify-end">
        <Button 
          variant="ghost"
          onClick={handleRefresh}
          className="text-text-muted"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
        <span className="font-medium">Compliance blockers:</span> {blockerCount} &nbsp;|&nbsp;
        <span className="font-medium">Pending reviews:</span> {pendingReviewCount} &nbsp;|&nbsp;
        <span className="font-medium">Cannot assess:</span> {sectionUnavailableCount} &nbsp;|&nbsp;
        <span className="font-medium">Checks complete:</span> {satisfiedRequirementCount}/{totalRequirementCount}
        {agreementRowsForSummary.length > 0 && (
          <>
            &nbsp;|&nbsp;
            <span className="font-medium">Agreements blocking readiness:</span> {agreementBlockingCount}
          </>
        )}
      </div>

      {/* Compliance Sections */}
      {filteredSections && (
        <>
          {/* Right to Work */}
          {filteredSections.right_to_work && (
            (filteredSections.right_to_work?.status_unavailable || !Array.isArray(filteredSections.right_to_work?.rows))
              ? renderUnavailableSection('right_to_work', 'Right to Work', filteredSections.right_to_work)
              : renderUploadSection('right_to_work', filteredSections.right_to_work)
          )}
          
          {/* DBS */}
          {filteredSections.dbs && (
            (filteredSections.dbs?.status_unavailable || !Array.isArray(filteredSections.dbs?.rows))
              ? renderUnavailableSection('dbs', 'DBS', filteredSections.dbs)
              : renderUploadSection('dbs', filteredSections.dbs)
          )}
          
          {/* Identity */}
          {filteredSections.identity && (
            (filteredSections.identity?.status_unavailable || !Array.isArray(filteredSections.identity?.rows))
              ? renderUnavailableSection('identity', 'Identity', filteredSections.identity)
              : renderUploadSection('identity', filteredSections.identity)
          )}
          
          {/* Proof of Address */}
          {filteredSections.proof_of_address && (
            (filteredSections.proof_of_address?.status_unavailable || !Array.isArray(filteredSections.proof_of_address?.rows))
              ? renderUnavailableSection('proof_of_address', 'Proof of Address', filteredSections.proof_of_address)
              : renderUploadSection('proof_of_address', filteredSections.proof_of_address)
          )}
          
          {/* Agreements - Uses legacy section for now */}
          {filteredSections.agreements && (
            (filteredSections.agreements?.status_unavailable || !Array.isArray(filteredSections.agreements?.rows))
              ? renderUnavailableSection('agreements', 'Agreements', filteredSections.agreements)
              : renderSection('agreements', filteredSections.agreements)
          )}
          
          {/* NOTE: References REMOVED - Now ONLY in dedicated References tab */}
          {/* NOTE: Training REMOVED - Now ONLY in dedicated Training tab */}
          {/* NOTE: Health & Competency REMOVED - Now ONLY in Training tab's HealthCompetencySection */}
          
          {/* NOTE: Recruitment Record moved to Forms tab to avoid duplication */}
        </>
      )}
      
      {/* Serializer Version (for debugging) */}
      <div className="text-xs text-text-muted text-right">
        Serializer: {complianceFile.serializer_version || 'unavailable'}
      </div>
      
      {/* Ticket C: Evidence Management Drawer for RTW, DBS, Identity, PoA */}
      <EvidenceManageDrawer
        isOpen={uploadDrawer.isOpen}
        onClose={closeUploadDrawer}
        employeeId={employeeId}
        requirementKey={uploadDrawer.requirementKey}
        onUploadFile={(key) => onUpload && onUpload(`${key}_evidence`)}
        onSendRequest={(key) => onRequest && onRequest(`${key}_evidence`, UPLOAD_REQUIREMENT_KEYS.includes(key) ? key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : key)}
        onPreviewFile={onPreviewFile}
        onExtractReview={onExtractReview}
        onRefresh={handleRefresh}
        isAuditor={isAuditor}
      />
      
      {/* Phase D2: Files Drawer (for legacy rows) */}
      <RequirementFilesDrawer
        open={filesDrawer.open}
        onClose={() => setFilesDrawer({ open: false, requirementKey: null, requirementTitle: '' })}
        employeeId={employeeId}
        requirementKey={filesDrawer.requirementKey}
        requirementTitle={filesDrawer.requirementTitle}
        onRefresh={handleRefresh}
        onUpload={onUpload}
        onRequest={onRequest}
        onPreviewFile={onPreviewFile}
        onExtractReview={onExtractReview}
        isAuditor={isAuditor}
      />
      
      {/* Phase D3: History Drawer */}
      <RequirementHistoryDrawer
        open={historyDrawer.open}
        onClose={() => setHistoryDrawer({ open: false, requirementKey: null, requirementTitle: '' })}
        employeeId={employeeId}
        requirementKey={historyDrawer.requirementKey}
        requirementTitle={historyDrawer.requirementTitle}
      />
      
      {/* Ticket E: Reference Response Drawer */}
      <ReferenceResponseDrawer
        isOpen={referenceDrawer.open}
        onClose={() => setReferenceDrawer({ open: false, referenceNum: null })}
        employeeId={employeeId}
        referenceNum={referenceDrawer.referenceNum}
        onRefresh={handleRefresh}
        isAuditor={isAuditor}
      />
      
      {/* Ticket D: Agreement Form Drawer */}
      <AgreementFormDrawer
        isOpen={agreementDrawer.isOpen}
        onClose={() => setAgreementDrawer({ 
          isOpen: false, templateId: null, mode: 'create', 
          submissionId: null, agreementKey: null, agreementTitle: null 
        })}
        employeeId={employeeId}
        templateId={agreementDrawer.templateId}
        employeeData={employeeData}
        onSubmitSuccess={handleRefresh}
        mode={agreementDrawer.mode}
        existingSubmission={agreementDrawer.submissionId ? { id: agreementDrawer.submissionId } : null}
      />
      
      {/* Form Submission Drawer for form-type requirements */}
      <FormSubmissionDrawer
        isOpen={formDrawer.isOpen}
        onClose={() => setFormDrawer({
          isOpen: false, formKey: null, formType: null,
          submissionId: null, mode: 'create'
        })}
        employeeId={employeeId}
        employeeName={employeeName}
        formKey={formDrawer.formKey}
        formType={formDrawer.formType}
        submissionId={formDrawer.submissionId}
        mode={formDrawer.mode}
        onSubmitSuccess={handleRefresh}
        onVerify={async (submissionId) => {
          try {
            await axios.post(
              `${API}/form-submissions/${submissionId}/verify`,
              {},
              { headers: { Authorization: `Bearer ${token}` } }
            );
            toast.success('Form verified successfully');
            handleRefresh();
            setFormDrawer(prev => ({ ...prev, isOpen: false }));
          } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to verify form');
          }
        }}
        onReject={(submissionId) => {
          setRejectDialog({
            isOpen: true,
            submissionId,
            formName: formDrawer.formKey?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
            formKey: formDrawer.formKey
          });
        }}
      />
      
      {/* Application Form View Drawer - Special case for structured application submissions */}
      <ApplicationFormViewDrawer
        isOpen={applicationFormDrawer.isOpen}
        onClose={() => setApplicationFormDrawer({ isOpen: false, submissionId: null })}
        employeeId={employeeId}
        employeeName={employeeName}
        submissionId={applicationFormDrawer.submissionId}
        onVerify={async (submissionId) => {
          try {
            await axios.post(
              `${API}/form-submissions/${submissionId}/verify`,
              {},
              { headers: { Authorization: `Bearer ${token}` } }
            );
            toast.success('Application form verified successfully');
            handleRefresh();
            setApplicationFormDrawer({ isOpen: false, submissionId: null });
          } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to verify application');
          }
        }}
        onReject={(submissionId) => {
          setRejectDialog({
            isOpen: true,
            submissionId,
            formName: 'Application Form',
            formKey: 'application_form'
          });
          setApplicationFormDrawer({ isOpen: false, submissionId: null });
        }}
        onRefresh={handleRefresh}
      />
      
      {/* Reject Form Dialog */}
      <RejectFormDialog
        isOpen={rejectDialog.isOpen}
        onClose={() => setRejectDialog({ isOpen: false, submissionId: null, formName: '', formKey: null })}
        formName={rejectDialog.formName}
        loading={rejectLoading}
        onConfirm={async (reason) => {
          setRejectLoading(true);
          try {
            await axios.post(
              `${API}/form-submissions/${rejectDialog.submissionId}/reject`,
              { rejection_reason: reason },
              { headers: { Authorization: `Bearer ${token}` } }
            );
            toast.success('Form rejected');
            handleRefresh();
            setRejectDialog({ isOpen: false, submissionId: null, formName: '', formKey: null });
            setFormDrawer(prev => ({ ...prev, isOpen: false }));
          } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to reject form');
          } finally {
            setRejectLoading(false);
          }
        }}
      />
    </div>
  );
}

