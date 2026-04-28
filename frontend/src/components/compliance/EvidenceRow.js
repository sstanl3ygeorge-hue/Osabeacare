import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { 
  Upload, FileText, RefreshCw, CheckCircle, XCircle, Eye, Clock, 
  AlertTriangle, ChevronDown, ChevronUp, MoreHorizontal, History,
  FileSearch, Trash2, Archive, Send, Download, Stamp
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '../ui/dropdown-menu';
import { formatBackendDate } from '../../lib/dateUtils';
import RequestLifecycleInline, { RequestLifecycleSummary } from './RequestLifecycleInline';
import DigitalStampDialog from './DigitalStampDialog';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

/**
 * EvidenceRow - Renders an evidence row in the dual-row compliance model
 * 
 * Evidence rows display uploaded/supporting files and provide actions like:
 * - Upload / Add file
 * - Request
 * - Review extraction
 * - Mark uploaded in error
 * - Supersede
 * - View history
 * 
 * Evidence rows do NOT affect readiness directly - they support check rows.
 */
export default function EvidenceRow({
  row,
  employeeId,
  employeeEmail,
  employeeName,
  onRefresh,
  onUpload,
  onRequest,
  onPreviewFile,
  onExtractReview,
  onViewFiles,  // Opens RequirementFilesDrawer
  onViewHistory, // Opens RequirementHistoryDrawer
  isAuditor = false
}) {
  const [expanded, setExpanded] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [stampDialogOpen, setStampDialogOpen] = useState(false);
  const [selectedDocForStamp, setSelectedDocForStamp] = useState(null);
  const { token } = useAuth();

  const {
    key,
    title,
    status,
    status_summary,
    counts = {},
    file_warnings = [],
    documents_preview = [],
    has_more_documents,
    pending_requests = [],
    allowed_actions = [],
    paired_check_key,
    request_lifecycle  // Phase D4: Inline request lifecycle data
  } = row;
  
  // Check if this is a multi-file requirement (like proof of address)
  const isMultiFile = key === 'proof_of_address_evidence' || key === 'proof_of_address';

  // Status colors - NEUTRAL for evidence rows (Phase 4B)
  // Evidence rows should never show green/red - they are supporting documents
  const getStatusColor = () => {
    // All evidence status badges are neutral grey
    if (counts.active_files === 0) return 'bg-gray-100 text-gray-600';
    if (counts.awaiting_extraction_review > 0) return 'bg-gray-100 text-gray-600';
    return 'bg-gray-100 text-gray-600';
  };

  // Mark document as uploaded in error
  const handleMarkUploadedInError = async (docId, fileName) => {
    if (!confirm(`Mark "${fileName}" as uploaded in error? It will be excluded from active counts.`)) return;
    
    setIsProcessing(true);
    try {
      await axios.post(`${API}/documents/${docId}/mark-uploaded-in-error`, {
        reason: 'Marked by admin as uploaded in error'
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Document marked as uploaded in error');
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to mark document');
    } finally {
      setIsProcessing(false);
    }
  };

  // Supersede document
  const handleSupersede = async (docId, fileName) => {
    // In a full implementation, this would open a dialog to select the superseding document
    toast.info('Select the newer document to supersede this one');
  };

  return (
    <div 
      className="border border-gray-200 rounded-xl bg-gray-50/30 overflow-hidden"
      data-testid={`evidence-row-${key}`}
    >
      {/* Row Header */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-100/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Icon - Neutral grey for evidence */}
          <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center flex-shrink-0">
            <FileText className="h-5 w-5 text-gray-500" />
          </div>
          
          {/* Title and Summary */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-medium text-text-primary">{title}</h4>
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-gray-100 text-gray-600 border-gray-300">
                Evidence
              </Badge>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm text-text-muted truncate">{status_summary}</p>
              {/* Request Status Summary - Phase D4 */}
              <RequestLifecycleSummary 
                requestLifecycle={request_lifecycle} 
                requirementKey={key} 
              />
            </div>
          </div>
          
          {/* File Count Badge - Always neutral */}
          <Badge className={`${getStatusColor()} text-xs`}>
            {counts.active_files > 0 ? `${counts.active_files} file${counts.active_files !== 1 ? 's' : ''}` : 'No files'}
          </Badge>
          
          {/* Extraction Awaiting Review Badge - Subtle indicator */}
          {counts.awaiting_extraction_review > 0 && (
            <Badge className="bg-purple-50 text-purple-600 border border-purple-200 text-xs">
              {counts.awaiting_extraction_review} extraction review
            </Badge>
          )}
        </div>
        
        {/* Actions - Simplified to 3 primaries: Upload/Add, Request, View Files */}
        <div className="flex items-center gap-2 ml-4">
          {/* View Files - Always show when there are files */}
          {counts.active_files > 0 && (
            <Button
              size="sm"
              variant="outline"
              onClick={(e) => { e.stopPropagation(); if (onViewFiles) onViewFiles(key, title); }}
              className="h-8 text-xs rounded-lg border-gray-300"
              data-testid={`view-files-${key}`}
            >
              <Eye className="h-3.5 w-3.5 mr-1" />
              View Files
            </Button>
          )}
          
          {!isAuditor && (
            <>
              {/* Upload (no files) or Add (has files) */}
              {allowed_actions.includes('upload') && counts.active_files === 0 && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => { e.stopPropagation(); if (onUpload) onUpload(key); }}
                  className="h-8 text-xs rounded-lg border-gray-300"
                  data-testid={`upload-${key}`}
                >
                  <Upload className="h-3.5 w-3.5 mr-1" />
                  Upload
                </Button>
              )}
              
              {allowed_actions.includes('add_file') && counts.active_files > 0 && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={(e) => { e.stopPropagation(); if (onUpload) onUpload(key); }}
                  className="h-8 text-xs text-gray-600 hover:text-gray-800"
                  data-testid={`add-file-${key}`}
                >
                  <Upload className="h-3.5 w-3.5 mr-1" />
                  Add
                </Button>
              )}
              
              {/* Request - Only show if requestable and has email */}
              {allowed_actions.includes('request') && employeeEmail && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => { e.stopPropagation(); if (onRequest) onRequest(key, title); }}
                  className="h-8 text-xs text-blue-600 border-blue-200 hover:bg-blue-50 rounded-lg"
                  data-testid={`request-${key}`}
                >
                  Request
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
      
      {/* File Warnings */}
      {file_warnings.length > 0 && (
        <div className="px-4 pb-2">
          {file_warnings.map((warning, idx) => (
            <div 
              key={idx}
              className={`flex items-center gap-2 text-xs p-2 rounded-lg ${
                warning.level === 'strong' ? 'bg-amber-50 text-amber-700' : 'bg-blue-50 text-blue-700'
              }`}
            >
              <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
              <span>{warning.message}</span>
            </div>
          ))}
        </div>
      )}
      
      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-gray-100 p-4 bg-gray-50/50">
          {/* Documents List */}
          {documents_preview.length > 0 ? (
            <div className="space-y-2">
              <h5 className="text-xs font-medium text-text-muted uppercase tracking-wide mb-2">
                Evidence ({counts.active_files})
              </h5>
              
              {documents_preview.map((doc, idx) => (
                <div 
                  key={doc.id || idx}
                  className={`flex items-center justify-between p-3 bg-white rounded-lg border ${
                    doc.verification_stamp && doc.verification_stamp !== 'not_verified'
                      ? 'border-green-200 bg-green-50/30'
                      : 'border-gray-100'
                  }`}
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <FileText className="h-5 w-5 text-gray-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-medium text-text-primary truncate">{doc.file_name}</p>
                        {doc.verification_stamp && doc.verification_stamp !== 'not_verified' && (
                          <Badge className={`text-[10px] ${
                            doc.verification_stamp === 'original_seen' ? 'bg-green-100 text-green-700' :
                            doc.verification_stamp === 'copy_verified' ? 'bg-blue-100 text-blue-700' :
                            doc.verification_stamp === 'online_check' ? 'bg-purple-100 text-purple-700' :
                            'bg-gray-100 text-gray-600'
                          }`}>
                            <CheckCircle className="h-2.5 w-2.5 mr-1" />
                            {doc.verification_stamp === 'original_seen' ? 'Original Seen' :
                             doc.verification_stamp === 'copy_verified' ? 'Copy Verified' :
                             doc.verification_stamp === 'online_check' ? 'Online Check' :
                             'Verified'}
                          </Badge>
                        )}
                        {doc.has_visual_stamp && (
                          <Badge className="text-[10px] bg-emerald-100 text-emerald-700">
                            <Stamp className="h-2.5 w-2.5 mr-1" />
                            Stamped
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-text-muted">
                        {formatBackendDate(doc.uploaded_at, { format: 'medium' })}
                        {doc.extraction_status === 'awaiting_review' && ' • Extraction pending'}
                        {doc.verification_stamp_by_name && ` • Verified by ${doc.verification_stamp_by_name}`}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-1">
                    {/* View */}
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0"
                      onClick={() => {
                        if (!doc.file_url && !doc.file_available) {
                          toast.error('File URL not available');
                          return;
                        }
                        if (onPreviewFile) onPreviewFile(doc);
                      }}
                      title="View file"
                      data-testid={`preview-file-${doc.id}`}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    
                    {/* Download */}
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0"
                      onClick={async () => {
                        let downloadUrl = doc.download_url || doc.file_url?.replace('/file', '/download');
                        if (!downloadUrl) {
                          toast.error('Download URL not available');
                          return;
                        }
                        try {
                          // FIX: Handle relative API URLs - API already ends with /api
                          if (downloadUrl.startsWith('/api/')) {
                            downloadUrl = `${API}${downloadUrl.substring(4)}`;
                          }
                          const response = await axios.get(downloadUrl, {
                            headers: { Authorization: `Bearer ${token}` },
                            responseType: 'blob'
                          });
                          const blob = new Blob([response.data]);
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = doc.file_name || doc.original_filename || 'document';
                          a.click();
                          URL.revokeObjectURL(url);
                        } catch (err) {
                          toast.error('Download failed');
                        }
                      }}
                      title="Download file"
                      data-testid={`download-file-${doc.id}`}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                    
                    {/* Extraction Review */}
                    {doc.extraction_status === 'awaiting_review' && onExtractReview && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 w-7 p-0 text-purple-600"
                        onClick={() => onExtractReview(doc.id)}
                        title="Review extraction"
                      >
                        <FileSearch className="h-4 w-4" />
                      </Button>
                    )}
                    
                    {/* More Actions */}
                    {!isAuditor && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button size="sm" variant="ghost" className="h-7 w-7 p-0">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-56">
                          {/* Digital Stamp Action */}
                          {!doc.verification_stamp || doc.verification_stamp === 'not_verified' ? (
                            <DropdownMenuItem 
                              onClick={() => {
                                setSelectedDocForStamp(doc);
                                setStampDialogOpen(true);
                              }}
                              className="text-green-600"
                            >
                              <Stamp className="h-4 w-4 mr-2" />
                              Verify & Apply Digital Stamp
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem disabled className="text-gray-400">
                              <CheckCircle className="h-4 w-4 mr-2 text-green-500" />
                              Already Verified
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => handleMarkUploadedInError(doc.id, doc.file_name)}>
                            <Trash2 className="h-4 w-4 mr-2 text-red-500" />
                            Mark Uploaded in Error
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleSupersede(doc.id, doc.file_name)}>
                            <Archive className="h-4 w-4 mr-2" />
                            Supersede
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </div>
                </div>
              ))}
              
              {has_more_documents && (
                <Button variant="link" className="text-xs text-primary p-0 h-auto">
                  View all {counts.active_files} files
                </Button>
              )}
            </div>
          ) : (
            <div className="text-center py-6 text-text-muted">
              <FileText className="h-8 w-8 mx-auto mb-2 text-gray-300" />
              <p className="text-sm">No files uploaded yet</p>
            </div>
          )}
          
          {/* Request Lifecycle - Phase D4 */}
          {request_lifecycle && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <h5 className="text-xs font-medium text-text-muted uppercase tracking-wide mb-2">
                Request Status
              </h5>
              <RequestLifecycleInline
                requestLifecycle={request_lifecycle}
                employeeId={employeeId}
                employeeEmail={employeeEmail}
                requirementKey={key}
                requirementTitle={title}
                onRequest={onRequest}
                onRefresh={onRefresh}
                isMultiFile={isMultiFile}
                showQuickActions={!isAuditor}
              />
            </div>
          )}
          
          {/* Stats Summary - File counts only (verification status shown on Check row) */}
          <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
            <div className="flex flex-wrap gap-4 text-xs text-text-muted">
              <span>{counts.active_files || 0} active</span>
              <span>{counts.awaiting_verification || 0} pending review</span>
              <span>{counts.superseded || 0} superseded</span>
              <span>{counts.history || 0} in history</span>
            </div>
            {/* History Button - Moved to expanded section */}
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
      
      {/* Digital Stamp Dialog */}
      <DigitalStampDialog
        open={stampDialogOpen}
        onOpenChange={setStampDialogOpen}
        document={selectedDocForStamp}
        employeeName={employeeName}
        onSuccess={() => {
          setSelectedDocForStamp(null);
          if (onRefresh) onRefresh();
        }}
      />
    </div>
  );
}

