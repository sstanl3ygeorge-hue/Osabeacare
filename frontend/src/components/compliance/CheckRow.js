import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { 
  Shield, CheckCircle, XCircle, Clock, AlertTriangle, 
  ChevronDown, ChevronUp, History, Edit, RefreshCw, 
  FileText, Eye, Download
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';
import API_BASE from '../../utils/apiBase';
import { getStatusLabel } from '../../utils/statusLabels';
import DaysRemainingBadge from './DaysRemainingBadge';

const API = API_BASE;

/**
 * CheckRow - Renders a check row in the dual-row compliance model
 * 
 * Check rows display employer/admin verification outcomes:
 * - RTW Check (share code, passport verification)
 * - DBS Status Check (Update Service, certificate review)
 * - Identity Verification
 * - Address Verification (X/2 format)
 * 
 * Check rows ARE the authoritative source for readiness.
 */
export default function CheckRow({
  row,
  employeeId,
  onRefresh,
  onRecordCheck,
  onViewHistory,
  onPreviewFile,
  isAuditor = false
}) {
  const [expanded, setExpanded] = useState(false);
  const { token } = useAuth();

  const {
    key,
    title,
    status,
    status_summary,
    has_check,
    is_verified,
    check_data,
    follow_up_info,
    counts = {},
    allowed_actions = [],
    blocker_text,
    migration_info,
    paired_evidence_key
  } = row;

  // Status colors for check rows
  const getStatusColor = () => {
    if (is_verified) return 'bg-green-100 text-green-700';
    if (has_check) return 'bg-amber-100 text-amber-700';
    return 'bg-red-100 text-red-700';
  };

  // Background color for the row
  const getRowBgColor = () => {
    if (is_verified) return 'bg-green-50/30';
    if (has_check) return 'bg-amber-50/30';
    return 'bg-red-50/30';
  };

  // Method display name
  const getMethodDisplay = (method) => {
    const methods = {
      'share_code_online_check': 'Share Code Online',
      'manual_passport_check': 'Manual Passport Check',
      'idsp_check': 'IDSP Check',
      'ecs_check': 'Employer Checking Service',
      'update_service_check': 'DBS Update Service',
      'manual_certificate_review': 'Manual Certificate Review',
      'manual_id_verification': 'Manual ID Verification',
      'digital_id_check': 'Digital ID Check'
    };
    return methods[method] || method?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Unknown';
  };

  // Outcome display name — canonicalised via shared statusLabels helper
  // (Tier 2 fix #4). Falls back to the local map for outcomes that are not
  // generic lifecycle states (e.g. "check_in_progress", "proof_required").
  const getOutcomeDisplay = (outcome) => {
    const checkSpecific = {
      'follow_up_required': 'Follow-up Required',
      'check_required': 'Check Required',
      'check_in_progress': 'Check In Progress',
      'proof_required': 'Proof Required',
      'reupload_required': 'Re-upload Required',
      'missing': 'Missing',
      'not_recorded': 'Not Recorded',
      'failed': 'Failed',
    };
    if (checkSpecific[outcome]) return checkSpecific[outcome];
    return getStatusLabel(outcome || 'not_started', 'admin');
  };

  return (
    <div 
      className={`border rounded-xl overflow-hidden ${
        is_verified ? 'border-green-200' : has_check ? 'border-amber-200' : 'border-red-200'
      } ${getRowBgColor()}`}
      data-testid={`check-row-${key}`}
    >
      {/* Row Header */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-white/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Icon */}
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
            is_verified ? 'bg-green-100' : has_check ? 'bg-amber-100' : 'bg-red-100'
          }`}>
            {is_verified ? (
              <CheckCircle className="h-5 w-5 text-green-600" />
            ) : has_check ? (
              <Clock className="h-5 w-5 text-amber-600" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-red-600" />
            )}
          </div>
          
          {/* Title and Summary */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-medium text-text-primary">{title}</h4>
              <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${
                is_verified ? 'bg-green-50 text-green-600 border-green-200' :
                has_check ? 'bg-amber-50 text-amber-600 border-amber-200' :
                'bg-red-50 text-red-600 border-red-200'
              }`}>
                Check
              </Badge>
              {blocker_text && (
                <Badge className="bg-red-100 text-red-700 text-[10px]">
                  Needed before start
                </Badge>
              )}
            </div>
            <p className="text-sm text-text-muted truncate">{status_summary}</p>
          </div>
          
          {/* Status Badge */}
          <Badge className={`${getStatusColor()} text-xs`}>
            {is_verified ? 'Verified' : has_check ? getOutcomeDisplay(check_data?.outcome) : 'Not Recorded'}
          </Badge>
          
          {/* Follow-up countdown — Tier 2 fix #6. Surface days remaining
              consistently; render even when not overdue/due-soon so admin
              and worker dashboards always show the same expiry signal. */}
          {follow_up_info && Number.isFinite(follow_up_info.days_until) && (
            <DaysRemainingBadge
              daysUntil={follow_up_info.days_until}
              label={follow_up_info.label}
            />
          )}
        </div>
        
        {/* Actions */}
        <div className="flex items-center gap-2 ml-4">
          {!isAuditor && (
            <>
              {/* Record Check */}
              {allowed_actions.includes('record_check') && !has_check && (
                <Button
                  size="sm"
                  variant="default"
                  onClick={(e) => { e.stopPropagation(); if (onRecordCheck) onRecordCheck(key); }}
                  className="h-8 text-xs bg-primary hover:bg-primary-hover text-white rounded-lg"
                  data-testid={`record-check-${key}`}
                >
                  <Shield className="h-3.5 w-3.5 mr-1" />
                  Record Check
                </Button>
              )}
              
              {/* Update Check */}
              {allowed_actions.includes('update_check') && has_check && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => { e.stopPropagation(); if (onRecordCheck) onRecordCheck(key); }}
                  className="h-8 text-xs rounded-lg"
                  data-testid={`update-check-${key}`}
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1" />
                  Update
                </Button>
              )}
            </>
          )}
          
          {/* Expand/Collapse */}
          <Button
            size="sm"
            variant="ghost"
            className="h-8 w-8 p-0"
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
      </div>
      
      {/* Expanded Content */}
      {expanded && has_check && check_data && (
        <div className="border-t border-gray-100 p-4 bg-white/50">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            {/* Method */}
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wide">Method</p>
              <p className="font-medium text-text-primary">{getMethodDisplay(check_data.method)}</p>
            </div>
            
            {/* Outcome */}
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wide">Outcome</p>
              <p className={`font-medium ${
                check_data.outcome === 'verified' ? 'text-green-600' :
                check_data.outcome === 'failed' ? 'text-red-600' : 'text-amber-600'
              }`}>
                {getOutcomeDisplay(check_data.outcome)}
              </p>
            </div>
            
            {/* Checked At */}
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wide">Checked</p>
              <p className="font-medium text-text-primary">
                {formatBackendDate(check_data.checked_at, { format: 'medium' })}
              </p>
            </div>
            
            {/* Follow-up / Review Due */}
            {follow_up_info && (
              <div>
                <p className="text-xs text-text-muted uppercase tracking-wide">{follow_up_info.label}</p>
                <p className={`font-medium ${
                  follow_up_info.is_overdue ? 'text-red-600' : 
                  follow_up_info.is_due_soon ? 'text-amber-600' : 'text-text-primary'
                }`}>
                  {formatBackendDate(follow_up_info.date, { format: 'medium' })}
                  {follow_up_info.is_overdue && ' (Overdue)'}
                </p>
              </div>
            )}
          </div>
          
          {/* PROOF FILE SECTION - COMPLIANCE CRITICAL */}
          {check_data.evidence_document_id && check_data.evidence_document && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-xs text-text-muted uppercase tracking-wide mb-2">Proof of Check</p>
              <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                    <FileText className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-green-800">
                      {check_data.evidence_document.filename || 'Check Proof'}
                    </p>
                    <p className="text-xs text-green-600">
                      Uploaded {formatBackendDate(check_data.evidence_document.uploaded_at, { format: 'medium' })}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {/* View */}

                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 w-8 p-0 text-green-600 hover:text-green-700 hover:bg-green-100"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onPreviewFile) {
                        const proofDoc = check_data.evidence_document;
                        const stampedFileUrl = proofDoc && proofDoc.verification_stamp ? proofDoc.verification_stamp : undefined;
                        onPreviewFile({
                          file_url: `/api/employee-documents/${check_data.evidence_document_id}/file`,
                          file_name: proofDoc?.filename || 'Check Proof',
                          ...(stampedFileUrl ? { stamped_file_url: stampedFileUrl } : {})
                        });
                      }
                    }}
                    title="View proof"
                    data-testid={`view-proof-${key}`}
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                  
                  {/* Download */}
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 w-8 p-0 text-green-600 hover:text-green-700 hover:bg-green-100"
                    onClick={async (e) => {
                      e.stopPropagation();
                      try {
                        const url = `${API}/employee-documents/${check_data.evidence_document_id}/download`;
                        const response = await axios.get(url, {
                          headers: { Authorization: `Bearer ${token}` },
                          responseType: 'blob'
                        });
                        const blob = new Blob([response.data]);
                        const link = document.createElement('a');
                        link.href = URL.createObjectURL(blob);
                        link.download = check_data.evidence_document.filename || 'check_proof';
                        link.click();
                        URL.revokeObjectURL(link.href);
                      } catch (err) {
                        toast.error('Download failed');
                      }
                    }}
                    title="Download proof"
                    data-testid={`download-proof-${key}`}
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          )}
          
          {/* Warning if no proof linked (legacy checks) */}
          {check_data.id && !check_data.evidence_document_id && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-amber-800">No proof file linked</p>
                  <p className="text-xs text-amber-600">
                    Update this check to add proof documentation for compliance.
                  </p>
                </div>
              </div>
            </div>
          )}
          
          {/* Notes */}
          {check_data.notes && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-xs text-text-muted uppercase tracking-wide mb-1">Notes</p>
              <p className="text-sm text-text-primary">{check_data.notes}</p>
            </div>
          )}
          
          {/* Migration Info */}
          {migration_info && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <div className="flex items-center gap-2 text-xs text-text-muted">
                <Badge variant="outline" className="text-[10px] bg-purple-50 text-purple-600 border-purple-200">
                  Migrated
                </Badge>
                <span>{migration_info.migration_basis}</span>
                <span>â€¢</span>
                <span>{formatBackendDate(migration_info.migrated_at, { format: 'medium' })}</span>
              </div>
            </div>
          )}
          
          {/* Footer with History */}
          <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
            <span className="text-xs text-text-muted">
              {counts.history > 0 ? `${counts.history} previous check${counts.history !== 1 ? 's' : ''}` : 'First check'}
            </span>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onViewHistory && onViewHistory(key, title)}
              className="h-7 text-xs text-text-muted hover:text-text-primary"
              data-testid={`history-${key}`}
            >
              <History className="h-3.5 w-3.5 mr-1" />
              View History
            </Button>
          </div>
        </div>
      )}
      
      {/* Not Recorded State */}
      {expanded && !has_check && (
        <div className="border-t border-gray-100 p-6 bg-white/50 text-center">
          <AlertTriangle className="h-10 w-10 mx-auto mb-3 text-red-400" />
          <p className="text-sm text-text-muted mb-2">No check has been recorded yet</p>
          <p className="text-xs text-text-muted">
            This requirement blocks work readiness until a check is recorded and verified.
          </p>
          {!isAuditor && onRecordCheck && (
            <Button
              size="sm"
              variant="default"
              onClick={() => onRecordCheck(key)}
              className="mt-4 bg-primary hover:bg-primary-hover text-white rounded-lg"
            >
              <Shield className="h-4 w-4 mr-2" />
              Record Check Now
            </Button>
          )}
        </div>
      )}
    </div>
  );
}


