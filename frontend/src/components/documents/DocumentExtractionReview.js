import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';
import API_BASE from '../../utils/apiBase';
import {
  FileSearch, Loader2, CheckCircle, AlertTriangle, AlertCircle, 
  Edit, X, RefreshCw, Eye, FileText
} from 'lucide-react';

const API = API_BASE;

/**
 * DocumentExtractionReview - Component for reviewing AI-extracted document data
 * 
 * Principles:
 * - Extraction is ASSISTIVE only - never auto-verifies
 * - All extracted values require admin review
 * - Canonical structured records remain source of truth
 * 
 * BUGFIX: Now accepts full document context for proper ID resolution
 */
export default function DocumentExtractionReview({ 
  documentId, 
  onClose, 
  onApproved,
  documentName = "Document",
  documentContext = null // Optional: { fileName, requirementName, documentType, uploadedAt }
}) {
  const [extraction, setExtraction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editedValues, setEditedValues] = useState({});
  const [error, setError] = useState(null);
  
  const { token } = useAuth();

  // Validate documentId before any operation
  const validateDocumentId = () => {
    if (!documentId || documentId === 'undefined' || documentId === 'null') {
      return false;
    }
    return true;
  };

  // Fetch existing extraction or trigger new one
  const fetchExtraction = async () => {
    if (!validateDocumentId()) {
      setError('No document selected for extraction. Please select a specific file.');
      setLoading(false);
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API}/documents/${documentId}/extraction`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.data.status === 'not_extracted' || !response.data.has_extraction) {
        // No extraction exists - offer to trigger one
        setExtraction(null);
      } else {
        setExtraction(response.data);
        setEditedValues(response.data.extracted_fields || {});
      }
    } catch (error) {
      console.error('Failed to fetch extraction:', error);
      const errorDetail = error.response?.data?.detail || 'Failed to load extraction data.';
      setError(errorDetail);
    } finally {
      setLoading(false);
    }
  };

  // Trigger new extraction
  const handleTriggerExtraction = async () => {
    if (!validateDocumentId()) {
      toast.error('No document selected for extraction.');
      return;
    }
    
    setIsExtracting(true);
    setError(null);
    try {
      const response = await axios.post(`${API}/documents/${documentId}/extract?force=true`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setExtraction(response.data);
      setEditedValues(response.data.extracted_fields || {});
      
      if (response.data.extraction_status === 'completed') {
        toast.success('Document extracted successfully');
      } else if (response.data.extraction_status === 'needs_review') {
        toast.info('Extraction completed with issues - please review');
      } else {
        toast.error('Extraction failed');
      }
    } catch (error) {
      const errorDetail = error.response?.data?.detail || 'Extraction failed';
      
      // Provide user-friendly error messages
      if (error.response?.status === 404) {
        setError('The selected document could not be found. It may have been moved, removed, or the page may be out of date. Please refresh and try again.');
        toast.error('Document not found. Please refresh the page.');
      } else if (error.response?.status === 409) {
        setError('This document cannot be extracted in its current state.');
        toast.error('Document not extractable');
      } else {
        setError(errorDetail);
        toast.error(errorDetail);
      }
    } finally {
      setIsExtracting(false);
    }
  };

  // Submit review
  const handleReview = async (action) => {
    setIsSubmitting(true);
    try {
      const payload = {
        action,
        approved_field_values: action === 'edit_and_approve' ? editedValues : (action === 'approve' ? extraction.extracted_fields : null),
        review_note: null
      };
      
      const response = await axios.post(
        `${API}/documents/${documentId}/extraction/review`,
        payload,
        { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } }
      );
      
      if (action === 'approve' || action === 'edit_and_approve') {
        toast.success('Extraction approved - values saved to document record');
        if (onApproved) onApproved(response.data);
      } else {
        toast.info('Extraction rejected');
      }
      
      if (onClose) onClose();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Review failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Effect to load extraction on mount
  useEffect(() => {
    fetchExtraction();
  }, []);

  // Source type badge
  const SourceBadge = ({ sourceType }) => {
    const config = {
      explicit: { label: 'Explicit', variant: 'default', className: 'bg-green-100 text-green-700' },
      inferred_policy: { label: 'Inferred from Policy', variant: 'secondary', className: 'bg-blue-100 text-blue-700' },
      derived_text: { label: 'Derived', variant: 'secondary', className: 'bg-gray-100 text-gray-700' },
      not_found: { label: 'Not Found', variant: 'destructive', className: 'bg-red-100 text-red-600' }
    };
    const c = config[sourceType] || config.derived_text;
    return <Badge variant={c.variant} className={`text-xs ${c.className}`}>{c.label}</Badge>;
  };

  // Confidence indicator
  const ConfidenceIndicator = ({ confidence }) => {
    if (confidence == null) return null;
    const pct = Math.round(confidence * 100);
    const color = pct >= 80 ? 'text-green-600' : pct >= 50 ? 'text-amber-600' : 'text-red-600';
    return <span className={`text-xs ${color}`}>{pct}%</span>;
  };

  // Issue badge
  const IssueBadge = ({ issue }) => {
    const config = {
      info: { icon: AlertCircle, className: 'bg-blue-50 text-blue-700 border-blue-200' },
      warning: { icon: AlertTriangle, className: 'bg-amber-50 text-amber-700 border-amber-200' },
      blocker: { icon: AlertTriangle, className: 'bg-red-50 text-red-700 border-red-200' }
    };
    const c = config[issue.severity] || config.info;
    const Icon = c.icon;
    return (
      <div className={`flex items-start gap-2 p-2 rounded-lg border ${c.className}`}>
        <Icon className="h-4 w-4 mt-0.5 flex-shrink-0" />
        <div className="text-sm">
          <span className="font-medium">{issue.code.replace(/_/g, ' ')}</span>
          <span className="text-gray-600 ml-1">— {issue.detail}</span>
        </div>
      </div>
    );
  };

  // Field labels for display
  const fieldLabels = {
    holder_name: 'Name on Document',
    document_title: 'Document Title',
    document_type: 'Document Type',
    document_subtype: 'Document Subtype',
    document_number: 'Document Number',
    certificate_number: 'Certificate Number',
    provider_name: 'Provider/Issuer',
    training_title: 'Training Title',
    issue_date: 'Issue Date',
    completion_date: 'Completion Date',
    expiry_date: 'Expiry Date',
    permission_end_date: 'Permission End Date',
    duration_text: 'Duration',
    address_text: 'Address',
    issuer_name: 'Issuing Authority',
    reference_number: 'Reference Number',
    nationality: 'Nationality',
    disclosure_type: 'Disclosure Type',
    accreditation: 'Accreditation',
    document_date: 'Document Date',
    inferred_training_code: 'Suggested Training Code',
    meets_recency_requirement: 'Meets Recency',
    days_old: 'Days Old'
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="bg-white sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <FileSearch className="h-5 w-5 text-primary" />
            Document Extraction Review
          </DialogTitle>
          <DialogDescription>
            {documentContext ? (
              <div className="space-y-1 text-left">
                <p><strong>File:</strong> {documentContext.fileName || documentName}</p>
                {documentContext.requirementName && (
                  <p><strong>Requirement:</strong> {documentContext.requirementName}</p>
                )}
                {documentContext.documentType && (
                  <p><strong>Type:</strong> {documentContext.documentType}</p>
                )}
                {documentContext.uploadedAt && (
                  <p><strong>Uploaded:</strong> {new Date(documentContext.uploadedAt).toLocaleDateString()}</p>
                )}
              </div>
            ) : (
              documentName
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {/* Error State */}
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-red-800">Extraction Error</p>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                  <div className="mt-3 flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setError(null);
                        fetchExtraction();
                      }}
                      className="rounded-lg border-red-300 text-red-700 hover:bg-red-100"
                    >
                      <RefreshCw className="h-4 w-4 mr-1" />
                      Retry
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={onClose}
                      className="rounded-lg"
                    >
                      Close
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : !extraction ? (
            // No extraction - offer to run one
            <div className="text-center py-8">
              <FileText className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <p className="text-text-muted mb-4">No extraction data available for this document.</p>
              <Button
                onClick={handleTriggerExtraction}
                disabled={isExtracting}
                className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                data-testid="trigger-extraction-btn"
              >
                {isExtracting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Extracting...
                  </>
                ) : (
                  <>
                    <FileSearch className="h-4 w-4 mr-2" />
                    Extract Document Data
                  </>
                )}
              </Button>
            </div>
          ) : (
            // Show extraction results
            <div className="space-y-4">
              {/* Status Header */}
              <div className="flex items-center justify-between p-3 bg-[#F8FAFA] rounded-xl">
                <div className="flex items-center gap-2">
                  {extraction.extraction_status === 'completed' && (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  )}
                  {extraction.extraction_status === 'needs_review' && (
                    <AlertTriangle className="h-5 w-5 text-amber-500" />
                  )}
                  {extraction.extraction_status === 'failed' && (
                    <AlertCircle className="h-5 w-5 text-red-500" />
                  )}
                  <span className="font-medium capitalize">
                    {extraction.extraction_status?.replace(/_/g, ' ')}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {extraction.document_type?.replace(/_/g, ' ')}
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  {extraction.review_status === 'awaiting_review' && (
                    <Badge variant="secondary" className="bg-amber-100 text-amber-700">
                      Awaiting Review
                    </Badge>
                  )}
                  {extraction.review_status === 'approved' && (
                    <Badge variant="default" className="bg-green-100 text-green-700">
                      Approved
                    </Badge>
                  )}
                  {extraction.review_status === 'edited' && (
                    <Badge variant="default" className="bg-blue-100 text-blue-700">
                      Edited & Approved
                    </Badge>
                  )}
                  {extraction.review_status === 'rejected' && (
                    <Badge variant="destructive" className="bg-red-100 text-red-700">
                      Rejected
                    </Badge>
                  )}
                </div>
              </div>

              {/* Issues */}
              {extraction.issues && extraction.issues.length > 0 && (
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Issues Detected</Label>
                  {extraction.issues.map((issue, idx) => (
                    <IssueBadge key={idx} issue={issue} />
                  ))}
                </div>
              )}

              {/* Extracted Fields */}
              {extraction.extracted_fields && Object.keys(extraction.extracted_fields).length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label className="text-sm font-medium">Extracted Fields</Label>
                    {extraction.review_status === 'awaiting_review' && !editMode && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setEditMode(true)}
                        className="rounded-lg text-xs"
                      >
                        <Edit className="h-3 w-3 mr-1" />
                        Edit Values
                      </Button>
                    )}
                    {editMode && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setEditMode(false);
                          setEditedValues(extraction.extracted_fields);
                        }}
                        className="rounded-lg text-xs"
                      >
                        <X className="h-3 w-3 mr-1" />
                        Cancel Edit
                      </Button>
                    )}
                  </div>
                  
                  <div className="border rounded-xl divide-y">
                    {Object.entries(extraction.extracted_fields).map(([key, value]) => {
                      const meta = extraction.field_metadata?.[key] || {};
                      if (value === null || value === undefined) return null;
                      
                      return (
                        <div key={key} className="flex items-center justify-between p-3 hover:bg-gray-50">
                          <div className="flex-1">
                            <p className="text-sm font-medium text-text-primary">
                              {fieldLabels[key] || key.replace(/_/g, ' ')}
                            </p>
                            {editMode ? (
                              <Input
                                value={editedValues[key] || ''}
                                onChange={(e) => setEditedValues({ ...editedValues, [key]: e.target.value })}
                                className="mt-1 h-8 text-sm rounded-lg"
                              />
                            ) : (
                              <p className="text-sm text-text-muted">{String(value)}</p>
                            )}
                          </div>
                          <div className="flex items-center gap-2 ml-4">
                            <SourceBadge sourceType={meta.source_type} />
                            <ConfidenceIndicator confidence={meta.confidence} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Retry button for failed extractions */}
              {extraction.extraction_status === 'failed' && (
                <div className="flex justify-center">
                  <Button
                    variant="outline"
                    onClick={handleTriggerExtraction}
                    disabled={isExtracting}
                    className="rounded-xl"
                  >
                    {isExtracting ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <RefreshCw className="h-4 w-4 mr-2" />
                    )}
                    Retry Extraction
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        {extraction && extraction.review_status === 'awaiting_review' && extraction.extraction_status !== 'failed' && (
          <DialogFooter className="gap-2 flex-wrap">
            <Button
              variant="outline"
              onClick={() => handleReview('reject')}
              disabled={isSubmitting}
              className="rounded-xl border-red-200 text-red-600 hover:bg-red-50"
              data-testid="reject-extraction-btn"
            >
              Reject
            </Button>
            <Button
              onClick={() => handleReview(editMode ? 'edit_and_approve' : 'approve')}
              disabled={isSubmitting}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
              data-testid="approve-extraction-btn"
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4 mr-2" />
              )}
              {editMode ? 'Save Edited Values' : 'Approve Extraction'}
            </Button>
          </DialogFooter>
        )}

        {/* Close button for already reviewed extractions */}
        {extraction && extraction.review_status !== 'awaiting_review' && (
          <DialogFooter>
            <Button variant="outline" onClick={onClose} className="rounded-xl">
              Close
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}

