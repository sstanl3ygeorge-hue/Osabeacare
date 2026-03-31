import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Checkbox } from '../../components/ui/checkbox';
import { toast } from 'sonner';
import { FileUploaderInline } from '../../components/ui/file-uploader';
import { formatBackendDate } from '../../lib/dateUtils';
import { 
  Upload, FileSearch, Loader2, CheckCircle, AlertTriangle, 
  GraduationCap, FileText, ChevronRight, ChevronLeft, 
  RefreshCw, Shield, Eye, X, Clock, Calendar
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * TrainingIntakeWizard - Multi-step wizard for training certificate intake
 * 
 * Flow:
 * 1. Upload Certificate (or select existing)
 * 2. AI Extraction (shows spinner while extracting)
 * 3. Review Split Items (multiple training courses from one certificate)
 * 4. Approve/Reject items → Creates canonical training_records
 * 
 * Principles:
 * - Extraction is ASSISTIVE only - never auto-verifies
 * - All extracted values require admin review
 * - Each approved item creates a training_record entry
 */
export default function TrainingIntakeWizard({ 
  employeeId, 
  employeeName,
  open, 
  onClose, 
  onComplete,
  existingDocumentId = null // Optional: use existing document instead of uploading
}) {
  const [step, setStep] = useState(existingDocumentId ? 2 : 1); // 1=Upload, 2=Extract, 3=Review
  const [uploadFile, setUploadFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionResult, setExtractionResult] = useState(null);
  const [proposedItems, setProposedItems] = useState([]);
  const [loadingProposed, setLoadingProposed] = useState(false);
  const [documentId, setDocumentId] = useState(existingDocumentId);
  const [error, setError] = useState(null);
  
  // Review state
  const [reviewDecisions, setReviewDecisions] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { token } = useAuth();

  // Effect: Auto-start extraction if existing document
  useEffect(() => {
    if (existingDocumentId && open) {
      handleTriggerExtraction(existingDocumentId);
    }
  }, [existingDocumentId, open]);

  // Effect: Fetch proposed items when available
  useEffect(() => {
    if (extractionResult?.proposed_items?.length > 0) {
      setProposedItems(extractionResult.proposed_items);
      // Initialize all items as "approve"
      const initialDecisions = {};
      extractionResult.proposed_items.forEach(item => {
        initialDecisions[item.item_id] = { 
          action: 'approve', 
          edited: false,
          values: { ...item }
        };
      });
      setReviewDecisions(initialDecisions);
      setStep(3);
    }
  }, [extractionResult]);

  // Step 1: Upload and Extract
  const handleUploadAndExtract = async () => {
    if (!uploadFile) {
      toast.error('Please select a file to upload');
      return;
    }

    setIsUploading(true);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);

      const response = await axios.post(
        `${API}/employees/${employeeId}/training/intake/from-upload`,
        formData,
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      setDocumentId(response.data.document_id);
      setExtractionResult(response.data.extraction);
      
      if (response.data.extraction?.status === 'error') {
        setError(response.data.extraction.detail || 'Extraction failed');
        setStep(2); // Show error state
      } else if (response.data.extraction?.proposed_items?.length > 0) {
        toast.success(`Found ${response.data.extraction.proposed_items.length} training item(s)`);
        setStep(3);
      } else {
        toast.info('No training items could be extracted. Manual entry may be needed.');
        setStep(2);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
      toast.error(err.response?.data?.detail || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  // Trigger extraction on existing document
  const handleTriggerExtraction = async (docId) => {
    setIsExtracting(true);
    setError(null);
    
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/training/intake`,
        { document_id: docId },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setExtractionResult(response.data);
      
      if (response.data?.status === 'error') {
        setError(response.data.detail || 'Extraction failed');
      } else if (response.data?.proposed_items?.length > 0) {
        toast.success(`Found ${response.data.proposed_items.length} training item(s)`);
      } else {
        toast.info('No training items could be extracted');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Extraction failed');
      toast.error(err.response?.data?.detail || 'Extraction failed');
    } finally {
      setIsExtracting(false);
    }
  };

  // Fetch existing proposed items
  const fetchProposedItems = async () => {
    setLoadingProposed(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/training/proposed-items`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setProposedItems(response.data.proposed_items || []);
      
      // Initialize decisions
      const initialDecisions = {};
      (response.data.proposed_items || []).forEach(item => {
        initialDecisions[item.item_id] = { 
          action: 'approve', 
          edited: false,
          values: { ...item }
        };
      });
      setReviewDecisions(initialDecisions);
    } catch (err) {
      console.error('Failed to fetch proposed items:', err);
    } finally {
      setLoadingProposed(false);
    }
  };

  // Toggle item decision
  const toggleDecision = (itemId, action) => {
    setReviewDecisions(prev => ({
      ...prev,
      [itemId]: { ...prev[itemId], action }
    }));
  };

  // Edit item value
  const editItemValue = (itemId, field, value) => {
    setReviewDecisions(prev => ({
      ...prev,
      [itemId]: {
        ...prev[itemId],
        edited: true,
        values: {
          ...prev[itemId]?.values,
          [field]: value
        }
      }
    }));
  };

  // Submit review
  const handleSubmitReview = async () => {
    const items = Object.entries(reviewDecisions).map(([itemId, decision]) => ({
      item_id: itemId,
      action: decision.action,
      edited_values: decision.edited ? decision.values : null
    }));

    if (items.filter(i => i.action === 'approve').length === 0) {
      toast.error('Please approve at least one training item');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/training/proposed-items/review`,
        { items },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const approved = response.data.approved_count || 0;
      const rejected = response.data.rejected_count || 0;
      
      toast.success(`${approved} training record(s) created${rejected > 0 ? `, ${rejected} rejected` : ''}`);
      
      if (onComplete) onComplete(response.data);
      handleClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Review submission failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Reset and close
  const handleClose = () => {
    setStep(1);
    setUploadFile(null);
    setExtractionResult(null);
    setProposedItems([]);
    setReviewDecisions({});
    setError(null);
    setDocumentId(null);
    if (onClose) onClose();
  };

  // Confidence badge color
  const getConfidenceColor = (confidence) => {
    if (!confidence) return 'bg-gray-100 text-gray-700';
    if (confidence >= 0.8) return 'bg-green-100 text-green-700';
    if (confidence >= 0.5) return 'bg-amber-100 text-amber-700';
    return 'bg-red-100 text-red-700';
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-white sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-primary" />
            Training Certificate Intake
          </DialogTitle>
          <DialogDescription>
            {employeeName && (
              <span className="font-medium text-text-primary">{employeeName}</span>
            )}
            {' — '}
            {step === 1 && 'Upload a training certificate to extract training records'}
            {step === 2 && 'Extracting training data from certificate...'}
            {step === 3 && 'Review and approve extracted training items'}
          </DialogDescription>
        </DialogHeader>

        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-2 py-2">
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm ${
            step >= 1 ? 'bg-primary text-white' : 'bg-gray-100 text-gray-500'
          }`}>
            <Upload className="h-4 w-4" />
            <span>Upload</span>
          </div>
          <ChevronRight className="h-4 w-4 text-gray-400" />
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm ${
            step >= 2 ? 'bg-primary text-white' : 'bg-gray-100 text-gray-500'
          }`}>
            <FileSearch className="h-4 w-4" />
            <span>Extract</span>
          </div>
          <ChevronRight className="h-4 w-4 text-gray-400" />
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm ${
            step >= 3 ? 'bg-primary text-white' : 'bg-gray-100 text-gray-500'
          }`}>
            <CheckCircle className="h-4 w-4" />
            <span>Review</span>
          </div>
        </div>

        <div className="py-4">
          {/* Step 1: Upload */}
          {step === 1 && (
            <div className="space-y-4" data-testid="intake-step-upload">
              <div className="border-2 border-dashed border-gray-200 rounded-xl p-6">
                <FileUploaderInline
                  files={uploadFile ? [uploadFile] : []}
                  setFiles={(files) => setUploadFile(files[0] || null)}
                  accept={{
                    'application/pdf': ['.pdf'],
                    'image/*': ['.png', '.jpg', '.jpeg']
                  }}
                  maxSize={10 * 1024 * 1024}
                  maxFiles={1}
                />
                <p className="text-xs text-text-muted text-center mt-3">
                  Upload a training certificate (PDF or image). Multi-course certificates will be split automatically.
                </p>
              </div>

              {uploadFile && (
                <div className="flex items-center justify-between p-3 bg-[#F8FAFA] rounded-lg border">
                  <div className="flex items-center gap-2">
                    <FileText className="h-5 w-5 text-primary" />
                    <span className="text-sm font-medium">{uploadFile.name}</span>
                    <span className="text-xs text-text-muted">
                      ({(uploadFile.size / 1024).toFixed(1)} KB)
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setUploadFile(null)}
                    className="h-8 w-8 p-0"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Step 2: Extracting / Error */}
          {step === 2 && (
            <div className="space-y-4 text-center py-8" data-testid="intake-step-extract">
              {isExtracting || isUploading ? (
                <>
                  <Loader2 className="h-12 w-12 mx-auto animate-spin text-primary" />
                  <p className="text-text-muted">
                    {isUploading ? 'Uploading and extracting...' : 'Extracting training data...'}
                  </p>
                  <p className="text-xs text-text-muted">
                    AI is scanning the document for training courses, dates, and providers
                  </p>
                </>
              ) : error ? (
                <>
                  <AlertTriangle className="h-12 w-12 mx-auto text-amber-500" />
                  <p className="text-text-primary font-medium">Extraction Issue</p>
                  <p className="text-sm text-text-muted">{error}</p>
                  <div className="flex justify-center gap-3 pt-2">
                    <Button
                      variant="outline"
                      onClick={() => { setStep(1); setError(null); }}
                      className="rounded-lg"
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Try Again
                    </Button>
                    {documentId && (
                      <Button
                        variant="outline"
                        onClick={() => handleTriggerExtraction(documentId)}
                        className="rounded-lg"
                      >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Retry Extraction
                      </Button>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <FileText className="h-12 w-12 mx-auto text-gray-300" />
                  <p className="text-text-muted">No training items could be extracted</p>
                  <p className="text-xs text-text-muted">
                    You can try again with a different file or add training records manually
                  </p>
                  <Button
                    variant="outline"
                    onClick={() => setStep(1)}
                    className="rounded-lg"
                  >
                    <ChevronLeft className="h-4 w-4 mr-1" />
                    Upload Different File
                  </Button>
                </>
              )}
            </div>
          )}

          {/* Step 3: Review Proposed Items */}
          {step === 3 && (
            <div className="space-y-4" data-testid="intake-step-review">
              {loadingProposed ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : proposedItems.length === 0 ? (
                <div className="text-center py-8">
                  <GraduationCap className="h-12 w-12 mx-auto text-gray-300 mb-3" />
                  <p className="text-text-muted">No proposed training items to review</p>
                </div>
              ) : (
                <>
                  {/* Summary */}
                  <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="flex items-center gap-2">
                      <FileSearch className="h-5 w-5 text-blue-600" />
                      <span className="text-sm text-blue-800">
                        {proposedItems.length} training item(s) extracted from certificate
                      </span>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      Review Required
                    </Badge>
                  </div>

                  {/* Items List */}
                  <div className="space-y-3 max-h-[400px] overflow-y-auto">
                    {proposedItems.map((item, idx) => {
                      const decision = reviewDecisions[item.item_id] || {};
                      const isApproved = decision.action === 'approve';
                      const values = decision.values || item;

                      return (
                        <div 
                          key={item.item_id || idx}
                          className={`p-4 rounded-xl border-2 transition-all ${
                            isApproved 
                              ? 'border-green-200 bg-green-50/50' 
                              : 'border-red-200 bg-red-50/50'
                          }`}
                          data-testid={`proposed-item-${item.item_id}`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 space-y-2">
                              {/* Training Title */}
                              <div className="flex items-center gap-2">
                                <GraduationCap className="h-5 w-5 text-primary flex-shrink-0" />
                                {decision.edited ? (
                                  <Input
                                    value={values.training_title || ''}
                                    onChange={(e) => editItemValue(item.item_id, 'training_title', e.target.value)}
                                    className="h-8 text-sm font-medium"
                                    placeholder="Training Title"
                                  />
                                ) : (
                                  <span className="font-medium text-text-primary">
                                    {item.training_title || item.inferred_training_code || 'Unknown Training'}
                                  </span>
                                )}
                                {item.confidence && (
                                  <Badge className={`text-xs ${getConfidenceColor(item.confidence)}`}>
                                    {Math.round(item.confidence * 100)}%
                                  </Badge>
                                )}
                              </div>

                              {/* Details Grid */}
                              <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm pl-7">
                                {/* Completion Date */}
                                <div className="flex items-center gap-2">
                                  <Calendar className="h-4 w-4 text-text-muted" />
                                  <span className="text-text-muted">Completed:</span>
                                  {decision.edited ? (
                                    <Input
                                      type="date"
                                      value={values.completion_date?.split('T')[0] || ''}
                                      onChange={(e) => editItemValue(item.item_id, 'completion_date', e.target.value)}
                                      className="h-7 text-xs w-32"
                                    />
                                  ) : (
                                    <span className="text-text-primary">
                                      {formatBackendDate(item.completion_date, { format: 'medium', fallback: 'Not specified' })}
                                    </span>
                                  )}
                                </div>

                                {/* Expiry Date */}
                                <div className="flex items-center gap-2">
                                  <Clock className="h-4 w-4 text-text-muted" />
                                  <span className="text-text-muted">Expires:</span>
                                  {decision.edited ? (
                                    <Input
                                      type="date"
                                      value={values.expiry_date?.split('T')[0] || ''}
                                      onChange={(e) => editItemValue(item.item_id, 'expiry_date', e.target.value)}
                                      className="h-7 text-xs w-32"
                                    />
                                  ) : (
                                    <span className={item.expiry_date ? 'text-text-primary' : 'text-text-muted'}>
                                      {formatBackendDate(item.expiry_date, { format: 'medium', fallback: 'No expiry' })}
                                    </span>
                                  )}
                                </div>

                                {/* Provider */}
                                {item.provider_name && (
                                  <div className="flex items-center gap-2 col-span-2">
                                    <Shield className="h-4 w-4 text-text-muted" />
                                    <span className="text-text-muted">Provider:</span>
                                    <span className="text-text-primary">{item.provider_name}</span>
                                  </div>
                                )}
                              </div>

                              {/* Name Match Warning */}
                              {item.name_match && !item.name_match.exact_match && (
                                <div className="flex items-start gap-2 mt-2 p-2 bg-amber-50 rounded-lg border border-amber-200">
                                  <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                                  <div className="text-xs text-amber-800">
                                    <span className="font-medium">Name mismatch:</span> Certificate shows "{item.name_match.certificate_name}" 
                                    but employee record has "{item.name_match.employee_name}"
                                    {item.name_match.partial_match && ' (partial match)'}
                                  </div>
                                </div>
                              )}
                            </div>

                            {/* Action Buttons */}
                            <div className="flex flex-col gap-2">
                              <Button
                                size="sm"
                                variant={isApproved ? 'default' : 'outline'}
                                className={`rounded-lg ${isApproved ? 'bg-green-600 hover:bg-green-700' : ''}`}
                                onClick={() => toggleDecision(item.item_id, 'approve')}
                              >
                                <CheckCircle className="h-4 w-4 mr-1" />
                                Approve
                              </Button>
                              <Button
                                size="sm"
                                variant={!isApproved ? 'default' : 'outline'}
                                className={`rounded-lg ${!isApproved ? 'bg-red-600 hover:bg-red-700' : 'text-red-600 border-red-200'}`}
                                onClick={() => toggleDecision(item.item_id, 'reject')}
                              >
                                <X className="h-4 w-4 mr-1" />
                                Reject
                              </Button>
                              {!decision.edited && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="rounded-lg text-xs"
                                  onClick={() => {
                                    setReviewDecisions(prev => ({
                                      ...prev,
                                      [item.item_id]: {
                                        ...prev[item.item_id],
                                        edited: true,
                                        values: { ...item }
                                      }
                                    }));
                                  }}
                                >
                                  Edit
                                </Button>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Summary Footer */}
                  <div className="flex items-center justify-between pt-2 border-t">
                    <div className="text-sm text-text-muted">
                      <span className="text-green-600 font-medium">
                        {Object.values(reviewDecisions).filter(d => d.action === 'approve').length} to approve
                      </span>
                      {' • '}
                      <span className="text-red-600">
                        {Object.values(reviewDecisions).filter(d => d.action === 'reject').length} to reject
                      </span>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleClose} className="rounded-xl">
            Cancel
          </Button>
          
          {step === 1 && (
            <Button
              onClick={handleUploadAndExtract}
              disabled={!uploadFile || isUploading}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
              data-testid="intake-upload-btn"
            >
              {isUploading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload & Extract
                </>
              )}
            </Button>
          )}

          {step === 3 && proposedItems.length > 0 && (
            <Button
              onClick={handleSubmitReview}
              disabled={isSubmitting || Object.values(reviewDecisions).filter(d => d.action === 'approve').length === 0}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
              data-testid="intake-review-btn"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Confirm Review
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
