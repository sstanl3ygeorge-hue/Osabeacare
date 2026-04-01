import { useState, useEffect } from 'react';
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
import UploadRequirementCard from './UploadRequirementCard';
import UploadRequirementDrawer from './UploadRequirementDrawer';
import RequirementFilesDrawer from './RequirementFilesDrawer';
import RequirementHistoryDrawer from './RequirementHistoryDrawer';
import ReferenceResponseDrawer from './ReferenceResponseDrawer';
import { normalizeUploadRequirementSurface } from './surfaceNormalizers';
import { UPLOAD_REQUIREMENT_KEYS } from './complianceRequirementMap';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
  onUpload,
  onRequest,
  onPreviewFile,
  onExtractReview,
  onRecordCheck,
  onSendAgreement,
  onFillAgreement,
  onCompleteByPhone,
  onViewHistory,
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
    references: true  // Added for references
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
    if (!employeeId) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/compliance-file`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Verify it's the dual-row format
      if (response.data.serializer_version !== 'dual_row_v1') {
        console.warn('Unexpected serializer version:', response.data.serializer_version);
      }
      
      setComplianceFile(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load compliance file');
      toast.error('Failed to load compliance file');
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
    if (!section || !section.rows) return null;
    
    const evidenceRow = section.rows.find(r => r.row_type === 'evidence');
    const checkRow = section.rows.find(r => r.row_type === 'check');
    
    if (!evidenceRow) return null;
    
    // Transform documents_preview to files array format
    const files = (evidenceRow.documents_preview || []).map(doc => ({
      file_id: doc.id,
      id: doc.id,
      file_name: doc.file_name,
      original_filename: doc.file_name,
      file_url: doc.file_url,
      uploaded_at: doc.uploaded_at,
      uploaded_by: doc.uploaded_by,
      verified: doc.verified || false,
      status: doc.status || 'active',
      extraction_status: doc.extraction_status ? { status: doc.extraction_status } : null
    }));
    
    // Add remaining files if has_more_documents indicates there are more
    // The counts tell us how many total active files
    const totalActive = evidenceRow.counts?.active_files || files.length;
    const totalHistorical = (evidenceRow.counts?.superseded || 0) + (evidenceRow.counts?.history || 0) - totalActive;
    
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
    const checks = [];
    if (checkRow && checkRow.check_record) {
      const check = checkRow.check_record;
      checks.push({
        id: check.check_id || check.id,
        status: check.outcome || check.status || (checkRow.is_verified ? 'verified' : 'pending'),
        method: check.method || check.check_method,
        checked_at: check.checked_at || check.verified_at || check.updated_at,
        checked_by: check.checked_by || check.verified_by,
        follow_up_date: check.follow_up_date,
        updated_at: check.updated_at
      });
    }
    
    // Use the normalizer with transformed data
    return normalizeUploadRequirementSurface({
      requirementKey: sectionKey,
      files,
      requests,
      checks
    });
  };

  /**
   * Render upload-type requirement using UploadRequirementCard
   */
  const renderUploadSection = (sectionKey, section) => {
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
          isAuditor={isAuditor}
        />
      </div>
    );
  };

  // Render a legacy section with paired rows (for agreements and references)
  const renderSection = (sectionKey, section) => {
    if (!section || !section.rows) return null;
    
    const isExpanded = expandedSections[sectionKey] !== false;
    
    // Count blockers in this section
    const blockers = section.rows.filter(r => r.blocker_text);
    
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
          </div>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
        
        {/* Section Content */}
        {isExpanded && (
          <div className="space-y-3 p-3 bg-white border border-t-0 border-gray-200 rounded-b-xl">
            {section.rows.map((row, idx) => {
              if (row.row_type === 'evidence') {
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
                    onRefresh={handleRefresh}
                    onSendForm={onSendAgreement}
                    onFillInternally={onFillAgreement}
                    onCompleteByPhone={onCompleteByPhone}
                    onViewHistory={handleViewHistory}
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
        <p className="text-text-muted mb-4">{error}</p>
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

  const { summary, sections } = complianceFile;

  return (
    <div className="space-y-6" data-testid="dual-row-compliance-section">
      {/* Summary Panel */}
      {summary && summary.blocking_requirements > 0 && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="h-5 w-5 text-red-600" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-red-900">
                {summary.blocking_requirements} Blocking Requirement{summary.blocking_requirements !== 1 ? 's' : ''}
              </h4>
              <p className="text-sm text-red-700 mb-2">
                These items must be resolved before work readiness can be achieved.
              </p>
              {summary.blocking_items && summary.blocking_items.length > 0 && (
                <ul className="space-y-1">
                  {summary.blocking_items.map((item, idx) => (
                    <li key={idx} className="text-sm text-red-800 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                      {item.message}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Refresh Button */}
      <div className="flex justify-end">
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={handleRefresh}
          className="text-text-muted"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Compliance Sections */}
      {sections && (
        <>
          {/* Right to Work - Uses unified UploadRequirementCard */}
          {sections.right_to_work && renderUploadSection('right_to_work', sections.right_to_work)}
          
          {/* DBS - Uses unified UploadRequirementCard */}
          {sections.dbs && renderUploadSection('dbs', sections.dbs)}
          
          {/* Identity - Uses unified UploadRequirementCard */}
          {sections.identity && renderUploadSection('identity', sections.identity)}
          
          {/* Proof of Address - Uses unified UploadRequirementCard */}
          {sections.proof_of_address && renderUploadSection('proof_of_address', sections.proof_of_address)}
          
          {/* Agreements - Uses legacy section for now */}
          {sections.agreements && renderSection('agreements', sections.agreements)}
          
          {/* References - Uses legacy section for now */}
          {sections.references && sections.references.rows && renderSection('references', sections.references)}
        </>
      )}
      
      {/* Serializer Version (for debugging) */}
      <div className="text-xs text-text-muted text-right">
        Serializer: {complianceFile.serializer_version}
      </div>
      
      {/* Ticket C: Shared Upload Drawer for RTW, DBS, Identity, PoA */}
      <UploadRequirementDrawer
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
    </div>
  );
}
