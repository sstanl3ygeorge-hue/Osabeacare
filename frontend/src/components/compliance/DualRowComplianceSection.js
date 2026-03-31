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
import RequirementFilesDrawer from './RequirementFilesDrawer';
import RequirementHistoryDrawer from './RequirementHistoryDrawer';

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
  const [expandedSections, setExpandedSections] = useState({
    right_to_work: true,
    dbs: true,
    identity: true,
    proof_of_address: true,
    agreements: true
  });
  
  // Phase D2: Files drawer state
  const [filesDrawer, setFilesDrawer] = useState({
    open: false,
    requirementKey: null,
    requirementTitle: ''
  });
  
  // Phase D3: History drawer state
  const [historyDrawer, setHistoryDrawer] = useState({
    open: false,
    requirementKey: null,
    requirementTitle: ''
  });
  
  const { token } = useAuth();
  
  // Open files drawer for a requirement
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

  // Render a section with paired rows
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
          {/* Right to Work */}
          {sections.right_to_work && renderSection('right_to_work', sections.right_to_work)}
          
          {/* DBS */}
          {sections.dbs && renderSection('dbs', sections.dbs)}
          
          {/* Identity */}
          {sections.identity && renderSection('identity', sections.identity)}
          
          {/* Proof of Address */}
          {sections.proof_of_address && renderSection('proof_of_address', sections.proof_of_address)}
          
          {/* Agreements */}
          {sections.agreements && renderSection('agreements', sections.agreements)}
        </>
      )}
      
      {/* Serializer Version (for debugging) */}
      <div className="text-xs text-text-muted text-right">
        Serializer: {complianceFile.serializer_version}
      </div>
      
      {/* Phase D2: Files Drawer */}
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
    </div>
  );
}
