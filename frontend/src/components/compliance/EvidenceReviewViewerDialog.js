/**
 * EvidenceReviewViewerDialog - In-app document viewer with verification controls
 * 
 * GUARANTEES admin has SEEN the document before approving/stamping.
 * CQC-compliant: logs viewed_at, viewing_duration_seconds, and verifier identity.
 * 
 * Layout: Full-screen split — document viewer (left) + review sidebar (right)
 * Flow: View document → Complete checklist → Select method → Verify & Stamp
 * 
 * Replaces QuickVerifyStampDialog for Identity & Proof of Address.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';
import { Checkbox } from '../ui/checkbox';
import { Textarea } from '../ui/textarea';
import { toast } from 'sonner';
import {
  Eye,
  FileCheck,
  Stamp,
  Loader2,
  CheckCircle,
  AlertTriangle,
  Calendar,
  Shield,
  ShieldCheck,
  User,
  MapPin,
  ZoomIn,
  ZoomOut,
  RotateCw,
  ChevronLeft,
  ChevronRight,
  FileText,
  Image as ImageIcon,
  Clock,
  X,
  XCircle
} from 'lucide-react';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { API_BASE_URL, API_ROOT_URL } from './';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const API = API_BASE_URL;

const MIN_VIEW_SECONDS = 5;

const getFileType = (contentType, filename) => {
  if (contentType?.includes('pdf') || filename?.toLowerCase().endsWith('.pdf')) return 'pdf';
  if (contentType?.includes('image') || /\.(jpg|jpeg|png|gif|webp|svg|bmp)$/i.test(filename || '')) return 'image';
  return 'other';
};

// Verification methods for Identity
const IDENTITY_METHODS = [
  {
    value: 'original_seen_interview',
    label: 'Original Seen in Interview',
    description: 'I physically saw the original document during the interview',
    stampType: 'original_seen',
    icon: Eye
  },
  {
    value: 'original_seen_office',
    label: 'Original Seen in Office',
    description: 'Candidate brought original document to office for verification',
    stampType: 'original_seen',
    icon: Eye
  },
  {
    value: 'copy_verified_video',
    label: 'Copy Verified via Video Call',
    description: 'Verified document copy against original shown on video call',
    stampType: 'copy_verified',
    icon: FileCheck
  }
];

// Verification methods for Proof of Address
const ADDRESS_METHODS = [
  {
    value: 'original_seen',
    label: 'Original Document Seen',
    description: 'I physically saw the original document',
    stampType: 'original_seen',
    icon: Eye
  },
  {
    value: 'copy_verified',
    label: 'Digital/Scanned Copy Verified',
    description: 'Verified digital copy - appears genuine',
    stampType: 'copy_verified',
    icon: FileCheck
  }
];

export default function EvidenceReviewViewerDialog({
  isOpen,
  onClose,
  file,
  employeeId,
  employeeName,
  requirementType,
  aiValidation,
  onVerificationComplete,
  mode = 'verify', // 'verify' = Identity/POA (checklist → verify & stamp), 'accept' = RTW/DBS (view → accept evidence), 'form-review' = Form submission (view PDF → approve/reject)
  // form-review mode props
  formSubmissionId,
  formName,
  onFormApproved,
  onFormRejected,
  trainingItem,
  onTrainingAccepted,
  onTrainingRejected,
  trainingAcceptLabel = 'Accept extracted item',
  trainingRejectLabel = 'Reject / needs correction',
  trainingCompletionMessage = 'The extracted training item decision has been recorded. Verification remains a separate step on the canonical training record.',
}) {
  const { token } = useAuth();
  const isAcceptMode = mode === 'accept';
  const isFormReview = mode === 'form-review';
  const isTrainingReview = mode === 'training-review';

  // Viewer state
  const [blobUrl, setBlobUrl] = useState(null);
  const [stampedBlobUrl, setStampedBlobUrl] = useState(null);
  const [viewingStamped, setViewingStamped] = useState(false);
  const [contentType, setContentType] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fileError, setFileError] = useState(null);

  // PDF state
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [rotation, setRotation] = useState(0);

  // Viewing timer
  const viewStartRef = useRef(null);
  const [viewSeconds, setViewSeconds] = useState(0);
  const timerRef = useRef(null);

  // Flow state: 'viewing' → 'verification' → 'complete'
  const [step, setStep] = useState('viewing');

  // Review checklist (step 1)
  const [checklist, setChecklist] = useState({
    fileViewed: false,
    nameMatches: false,
    documentAcceptable: false,
    legible: false,
    frontPresent: false,
    backPresent: false,
    addressValid: false,
    dateValid: false,
    trainingCourseTitleCorrect: false,
    trainingMappingCorrect: false,
    trainingCompletionDateCorrect: false,
    trainingExpiryDateCorrect: false
  });
  const [checklistError, setChecklistError] = useState('');

  // Verification (step 2)
  const [selectedMethod, setSelectedMethod] = useState('');
  const [confirmChecks, setConfirmChecks] = useState({
    documentGenuine: false,
    detailsMatch: false,
    dateValid: false
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form-review mode state
  const [formRejectReason, setFormRejectReason] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [healthOutcome, setHealthOutcome] = useState('');
  const [trainingReviewNotes, setTrainingReviewNotes] = useState('');

  const isIdentity = requirementType === 'identity';
  const isAddress = requirementType === 'proof_of_address';
  const methods = isIdentity ? IDENTITY_METHODS : ADDRESS_METHODS;
  const isHealthQuestionnaireForm =
    isFormReview && /staff health questionnaire|health questionnaire/i.test(formName || '');
  const fileName = isFormReview ? `${(formName || 'Form').replace(/\s+/g, '_')}.pdf` : (file?.file_name || file?.name || 'Document');
  const docId = file?.id || file?.file_id;
  // Normalise file URL — backend evidence URLs are often relative (/api/...)
  const rawFileUrl = isFormReview
    ? (formSubmissionId ? `${API}/form-submissions/${formSubmissionId}/download-pdf` : null)
    : (file?.file_url || (docId ? `/api/employee-documents/${docId}/file` : null));
  const fileUrl = (!isFormReview && rawFileUrl && rawFileUrl.startsWith('/api/'))
    ? `${API}${rawFileUrl.substring(4)}`
    : rawFileUrl;
  const fileType = isFormReview ? 'pdf' : getFileType(contentType, fileName);
  const hasMetMinViewTime = viewSeconds >= MIN_VIEW_SECONDS;

  // ------ Reset on open ------
  useEffect(() => {
    if (isOpen) {
      setStep('viewing');
      setChecklist({
        fileViewed: false,
        nameMatches: false,
        documentAcceptable: false,
        legible: false,
        frontPresent: false,
        backPresent: false,
        addressValid: false,
        dateValid: false,
        trainingCourseTitleCorrect: false,
        trainingMappingCorrect: false,
        trainingCompletionDateCorrect: false,
        trainingExpiryDateCorrect: false
      });
      setSelectedMethod('');
      setConfirmChecks({ documentGenuine: false, detailsMatch: false, dateValid: false });
      setChecklistError('');
      setViewSeconds(0);
      setCurrentPage(1);
      setScale(1.0);
      setRotation(0);
      setViewingStamped(false);
      setStampedBlobUrl(null);
      setFormRejectReason('');
      setShowRejectInput(false);
      setHealthOutcome('');
      setTrainingReviewNotes('');
      viewStartRef.current = Date.now();
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
  }, [isOpen]);

  // ------ Counting timer ------
  useEffect(() => {
    if (isOpen && step !== 'complete') {
      timerRef.current = setInterval(() => {
        if (viewStartRef.current) {
          setViewSeconds(Math.floor((Date.now() - viewStartRef.current) / 1000));
        }
      }, 1000);
      return () => clearInterval(timerRef.current);
    }
  }, [isOpen, step]);

  // ------ Fetch document ------
  useEffect(() => {
    if (!isOpen || !fileUrl) return;
    let isMounted = true;
    setLoading(true);
    setFileError(null);
    setBlobUrl(null);

    const fetchFile = async () => {
      try {
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const response = await fetch(fileUrl, { headers });
        if (!response.ok) throw new Error(`Failed to load file: ${response.status}`);
        const blob = await response.blob();
        if (isMounted) {
          setContentType(response.headers.get('content-type') || blob.type);
          setBlobUrl(URL.createObjectURL(blob));
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setFileError(err.message);
          setLoading(false);
        }
      }
    };
    fetchFile();
    return () => { isMounted = false; };
  }, [isOpen, fileUrl, token]);

  // Cleanup blob URLs
  useEffect(() => {
    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
      if (stampedBlobUrl) URL.revokeObjectURL(stampedBlobUrl);
    };
  }, [blobUrl, stampedBlobUrl]);

  const onDocumentLoadSuccess = useCallback(({ numPages }) => {
    setNumPages(numPages);
  }, []);

  // ------ PDF controls ------
  const goToPrevPage = () => setCurrentPage(prev => Math.max(prev - 1, 1));
  const goToNextPage = () => setCurrentPage(prev => Math.min(prev + 1, numPages || 1));
  const zoomIn = () => setScale(prev => Math.min(prev + 0.25, 3));
  const zoomOut = () => setScale(prev => Math.max(prev - 0.25, 0.5));
  const resetView = () => {
    setScale(1.0);
    setRotation(0);
  };
  const rotate = () => setRotation(prev => (prev + 90) % 360);

  // ------ Step 1: Record review checklist & move to verification ------
  const handleProceedToVerification = async () => {
    setChecklistError('');

    if (!checklist.fileViewed) {
      setChecklistError('You must confirm the file was viewed');
      return;
    }
    const baseChecks = [checklist.fileViewed, checklist.nameMatches, checklist.documentAcceptable, checklist.legible];
    if (baseChecks.filter(Boolean).length < 2) {
      setChecklistError('Please confirm at least 2 basic checklist items');
      return;
    }
    if (isIdentity && !checklist.frontPresent) {
      setChecklistError('Please confirm front side is present');
      return;
    }
    if (isAddress && !checklist.addressValid) {
      setChecklistError('Please confirm address is valid');
      return;
    }
    if (isFormReview && !checklist.dateValid) {
      setChecklistError('Please confirm the declaration is signed and dated');
      return;
    }
    if (isHealthQuestionnaireForm && !healthOutcome) {
      setChecklistError('Select a health outcome before approving this questionnaire');
      return;
    }

    setIsSubmitting(true);
    try {
      if (isFormReview) {
        // Form-review mode: approve the form submission directly
        await handleFormApprove();
        return;
      }

      const docId = file.file_id || file.id;
      if (!docId) { setChecklistError('Document ID not found'); return; }

      if (isAcceptMode) {
        // Accept mode (RTW/DBS): just accept the evidence, no start-review/stamp flow
        await axios.post(
          `${API}/employee-documents/${docId}/verify`,
          {
            notes: `Reviewed in viewer for ${viewSeconds}s. Checklist: file_viewed=${checklist.fileViewed}, legible=${checklist.legible}, acceptable=${checklist.documentAcceptable}, name_matches=${checklist.nameMatches}`
          },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setStep('complete');
        toast.success('Evidence accepted after review');
      } else {
        // Verify mode (Identity/POA): start review then proceed to verification step
        await axios.post(
          `${API}/employee-documents/${docId}/start-review`,
          {
            file_viewed: true,
            name_matches: checklist.nameMatches,
            document_acceptable: checklist.documentAcceptable,
            legible: checklist.legible,
            front_present: isIdentity ? checklist.frontPresent : undefined,
            back_present: isIdentity ? checklist.backPresent : undefined,
            address_valid: isAddress ? checklist.addressValid : undefined,
            date_valid: isAddress ? checklist.dateValid : undefined,
            viewing_duration_seconds: viewSeconds
          },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setStep('verification');
        toast.success('Review recorded. Select verification method.');
      }
    } catch (err) {
      setChecklistError(err.response?.data?.detail || 'Failed to record review');
    } finally {
      setIsSubmitting(false);
    }
  };

  // ------ Step 2: Verify & Stamp ------
  const handleVerifyAndStamp = async () => {
    if (!selectedMethod) { toast.error('Select how you verified the document'); return; }
    if (!confirmChecks.documentGenuine || !confirmChecks.detailsMatch) { toast.error('Please confirm all checks'); return; }
    if (isAddress && !confirmChecks.dateValid) { toast.error('Please confirm the document date is valid'); return; }

    const method = methods.find(m => m.value === selectedMethod);
    if (!method) { toast.error('Invalid verification method'); return; }

    setIsSubmitting(true);
    try {
      const docId = file.file_id || file.id;
      if (!docId) { toast.error('Document ID not found'); return; }

      const endpoint = isIdentity
        ? `${API}/employees/${employeeId}/identity/verify-and-stamp`
        : `${API}/employees/${employeeId}/address/verify-and-stamp`;

      const resp = await axios.post(
        endpoint,
        {
          document_id: docId,
          method: selectedMethod,
          stamp_type: method.stampType,
          checks_confirmed: {
            document_genuine: confirmChecks.documentGenuine,
            details_match: confirmChecks.detailsMatch,
            date_valid: isAddress ? confirmChecks.dateValid : true
          },
          ai_validation: aiValidation
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Fetch stamped version if URL returned
      const stampedUrl = resp.data?.stamped_file_url;
      if (stampedUrl) {
        try {
          const headers = token ? { Authorization: `Bearer ${token}` } : {};
          const stampRes = await fetch(stampedUrl, { headers });
          if (stampRes.ok) {
            const blob = await stampRes.blob();
            setStampedBlobUrl(URL.createObjectURL(blob));
            setViewingStamped(true);
          }
        } catch { /* non-critical — stamped preview is a bonus */ }
      }

      setStep('complete');
      toast.success(
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-green-600" />
          <span>Document verified & stamped successfully</span>
        </div>
      );
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify document');
    } finally {
      setIsSubmitting(false);
    }
  };

  // ------ Form Review: Approve ------
  const handleFormApprove = async () => {
    setIsSubmitting(true);
    setChecklistError('');
    try {
      await axios.post(
        `${API}/form-submissions/${formSubmissionId}/verify`,
        isHealthQuestionnaireForm
          ? { health_outcome: healthOutcome }
          : {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setStep('complete');
      toast.success('Form submission approved');
      if (onFormApproved) onFormApproved();
    } catch (err) {
      setChecklistError(err.response?.data?.detail || 'Failed to approve form');
    } finally {
      setIsSubmitting(false);
    }
  };

  // ------ Form Review: Reject ------
  const handleFormReject = async () => {
    if (!formRejectReason.trim()) {
      setChecklistError('Please provide a reason for rejection');
      return;
    }
    setIsSubmitting(true);
    setChecklistError('');
    try {
      await axios.post(
        `${API}/form-submissions/${formSubmissionId}/reject`,
        null,
        {
          headers: { Authorization: `Bearer ${token}` },
          params: { reason: formRejectReason.trim() }
        }
      );
      setStep('complete');
      toast.success('Form submission rejected');
      if (onFormRejected) onFormRejected();
    } catch (err) {
      setChecklistError(err.response?.data?.detail || 'Failed to reject form');
    } finally {
      setIsSubmitting(false);
    }
  };

  const trainingChecklistComplete = isTrainingReview && [
    checklist.fileViewed,
    checklist.nameMatches,
    checklist.documentAcceptable,
    checklist.legible,
    checklist.trainingCourseTitleCorrect,
    checklist.trainingMappingCorrect,
    checklist.trainingCompletionDateCorrect,
    checklist.trainingExpiryDateCorrect
  ].every(Boolean);

  const handleTrainingAccept = async () => {
    setChecklistError('');
    if (!trainingChecklistComplete) {
      setChecklistError('Complete the training evidence checklist before accepting this extracted item.');
      return;
    }

    setIsSubmitting(true);
    try {
      await onTrainingAccepted?.({
        notes: trainingReviewNotes.trim() || `Accepted after evidence review (${viewSeconds}s viewing).`
      });
      setStep('complete');
    } catch (err) {
      setChecklistError(err.response?.data?.detail || err.message || 'Failed to accept extracted training item');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTrainingReject = async () => {
    setChecklistError('');
    setIsSubmitting(true);
    try {
      await onTrainingRejected?.({
        notes: trainingReviewNotes.trim() || `Rejected after evidence review (${viewSeconds}s viewing).`
      });
      setStep('complete');
    } catch (err) {
      setChecklistError(err.response?.data?.detail || err.message || 'Failed to reject extracted training item');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (step === 'complete' && onVerificationComplete) {
      onVerificationComplete();
    }
    onClose();
  };

  const selectedMethodData = methods.find(m => m.value === selectedMethod);

  // ------ Render ------
  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent
        className="max-w-[95vw] w-[95vw] h-[90vh] max-h-[90vh] p-0 gap-0 overflow-hidden"
        data-testid="evidence-review-viewer-dialog"
      >
        <DialogTitle className="sr-only">
          {isFormReview
            ? `Review ${formName || 'Form'} Submission`
            : isTrainingReview
              ? `Review Training Evidence for ${trainingItem?.mapped_training_title || trainingItem?.raw_course_title || 'Extracted Training Item'}`
            : isAcceptMode
              ? `Review ${requirementType === 'right_to_work' ? 'Right to Work' : requirementType === 'dbs' ? 'DBS Certificate' : requirementType} Evidence`
              : `Review & Verify ${isIdentity ? 'Identity Document' : 'Proof of Address'}`}
        </DialogTitle>
        <DialogDescription className="sr-only">
          View the document and complete the verification checklist
        </DialogDescription>

        <div className="flex h-full min-h-0">
          {/* ===== LEFT: Document Viewer ===== */}
          <div className="flex-1 flex flex-col bg-slate-900 min-w-0 min-h-0">
            {/* Viewer toolbar */}
            <div className="flex items-center justify-between gap-3 px-4 py-2 bg-slate-800 border-b border-slate-700 flex-shrink-0">
              <div className="flex items-center gap-2 min-w-0">
                {fileType === 'pdf' ? <FileText className="h-4 w-4 text-slate-300 flex-shrink-0" /> : <ImageIcon className="h-4 w-4 text-slate-300 flex-shrink-0" />}
                <span className="text-sm text-slate-200 truncate">{fileName}</span>
                {stampedBlobUrl && (
                  <div className="flex items-center gap-1 ml-2">
                    <Button
                      size="sm"
                      variant={!viewingStamped ? 'secondary' : 'ghost'}
                      className={`h-6 px-2 text-xs ${!viewingStamped ? 'bg-white text-slate-900' : 'text-slate-400 hover:text-white'}`}
                      onClick={() => setViewingStamped(false)}
                    >
                      Original
                    </Button>
                    <Button
                      size="sm"
                      variant={viewingStamped ? 'secondary' : 'ghost'}
                      className={`h-6 px-2 text-xs ${viewingStamped ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'}`}
                      onClick={() => setViewingStamped(true)}
                    >
                      <ShieldCheck className="h-3 w-3 mr-1" />
                      Stamped
                    </Button>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-1">
                {(fileType === 'pdf' || fileType === 'image') && (
                  <>
                    {fileType === 'pdf' && (
                      <>
                        <Button size="sm" variant="ghost" className="h-7 px-2 text-slate-300 hover:text-white" onClick={goToPrevPage} disabled={currentPage <= 1} title="Previous page">
                          <ChevronLeft className="h-4 w-4" />
                          Prev
                        </Button>
                        <span className="text-xs text-slate-400 min-w-[72px] text-center">
                          Page {currentPage} of {numPages || '?'}
                        </span>
                        <Button size="sm" variant="ghost" className="h-7 px-2 text-slate-300 hover:text-white" onClick={goToNextPage} disabled={!numPages || currentPage >= numPages} title="Next page">
                          Next
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                        <div className="w-px h-5 bg-slate-600 mx-1" />
                      </>
                    )}
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-slate-300 hover:text-white" onClick={zoomOut} title="Zoom out"><ZoomOut className="h-4 w-4" /></Button>
                    <span className="text-xs text-slate-400 w-10 text-center">{Math.round(scale * 100)}%</span>
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-slate-300 hover:text-white" onClick={zoomIn} title="Zoom in"><ZoomIn className="h-4 w-4" /></Button>
                    <Button size="sm" variant="ghost" className="h-7 px-2 text-slate-300 hover:text-white" onClick={resetView} title="Reset zoom and rotation">Reset</Button>
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-slate-300 hover:text-white" onClick={rotate} title="Rotate"><RotateCw className="h-4 w-4" /></Button>
                    <div className="w-px h-5 bg-slate-600 mx-1" />
                  </>
                )}
                <div className="flex items-center gap-1 text-xs text-slate-400">
                  <Clock className="h-3 w-3" />
                  <span>{viewSeconds}s</span>
                </div>
              </div>
            </div>

            {/* Document content */}
            <div className="flex-1 min-h-0 overflow-auto flex items-start justify-center p-4">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-full gap-3">
                  <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
                  <span className="text-sm text-slate-400">Loading document...</span>
                </div>
              ) : fileError ? (
                <div className="flex flex-col items-center justify-center h-full gap-3 text-red-400">
                  <AlertTriangle className="h-8 w-8" />
                  <span className="text-sm">{fileError}</span>
                </div>
              ) : fileType === 'pdf' ? (
                <div className="min-w-max">
                  <Document
                    file={viewingStamped && stampedBlobUrl ? stampedBlobUrl : blobUrl}
                    onLoadSuccess={onDocumentLoadSuccess}
                    loading={<Loader2 className="h-6 w-6 animate-spin text-slate-400" />}
                    error={<span className="text-red-400 text-sm">Failed to load PDF</span>}
                  >
                    <Page
                      pageNumber={currentPage}
                      scale={scale}
                      rotate={rotation}
                      renderTextLayer={true}
                      renderAnnotationLayer={true}
                    />
                  </Document>
                </div>
              ) : fileType === 'image' ? (
                <div className="min-w-max min-h-max">
                  <img
                    src={viewingStamped && stampedBlobUrl ? stampedBlobUrl : blobUrl}
                    alt={fileName}
                    className="max-w-full max-h-full object-contain"
                    style={{ transform: `rotate(${rotation}deg) scale(${scale})`, transformOrigin: 'top center' }}
                  />
                </div>
              ) : (
                <iframe
                  src={viewingStamped && stampedBlobUrl ? stampedBlobUrl : blobUrl}
                  title={fileName}
                  className="w-full h-full border-0"
                />
              )}
            </div>
          </div>

          {/* ===== RIGHT: Review Sidebar ===== */}
          <div className="w-[420px] max-w-[40vw] min-w-[360px] flex-shrink-0 border-l flex flex-col bg-white overflow-hidden min-h-0">
            {/* Header */}
            <div className="px-4 py-3 border-b bg-slate-50 flex-shrink-0">
              <div className="flex items-center gap-2">
                {isFormReview ? <FileText className="h-5 w-5 text-teal-600" /> : isTrainingReview ? <FileCheck className="h-5 w-5 text-purple-600" /> : isAcceptMode ? <Shield className="h-5 w-5 text-indigo-600" /> : isIdentity ? <User className="h-5 w-5 text-blue-600" /> : <MapPin className="h-5 w-5 text-purple-600" />}
                <div>
                  <h3 className="font-semibold text-sm">
                    {isFormReview
                      ? `Review ${formName || 'Form'}`
                      : isTrainingReview
                        ? 'Review Training Evidence'
                      : isAcceptMode
                        ? `Review ${requirementType === 'right_to_work' ? 'Right to Work' : requirementType === 'dbs' ? 'DBS Certificate' : requirementType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())} Evidence`
                        : `Verify ${isIdentity ? 'Identity Document' : 'Proof of Address'}`}
                  </h3>
                  <p className="text-xs text-slate-500 truncate">{fileName} — {employeeName}</p>
                </div>
              </div>

              {/* Progress steps */}
              <div className="flex items-center gap-2 mt-3">
                {(isFormReview || isAcceptMode || isTrainingReview ? ['viewing', 'complete'] : ['viewing', 'verification', 'complete']).map((s, i, arr) => (
                  <div key={s} className="flex items-center gap-1">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                      step === s ? 'bg-blue-600 text-white' :
                      (arr.indexOf(step) > i) ? 'bg-green-600 text-white' :
                      'bg-slate-200 text-slate-500'
                    }`}>
                      {arr.indexOf(step) > i ? (
                        <CheckCircle className="h-3.5 w-3.5" />
                      ) : (i + 1)}
                    </div>
                    {i < arr.length - 1 && <div className={`w-6 h-0.5 ${
                      arr.indexOf(step) > i ? 'bg-green-400' : 'bg-slate-200'
                    }`} />}
                  </div>
                ))}
                <span className="text-xs text-slate-500 ml-1">
                  {step === 'viewing' ? 'Review' : step === 'verification' ? 'Verify' : 'Done'}
                </span>
              </div>
            </div>

            {/* Scrollable content */}
            <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">

              {/* ---- STEP: VIEWING + CHECKLIST ---- */}
              {step === 'viewing' && (
                <>
                  {isTrainingReview && trainingItem && (
                    <div className="space-y-3 p-3 bg-purple-50 rounded-lg border border-purple-200">
                      <div className="flex items-center gap-2 text-purple-900">
                        <FileCheck className="h-4 w-4" />
                        <h4 className="font-semibold text-sm">Extracted training item</h4>
                      </div>
                      <div className="space-y-2 bg-white p-3 rounded border text-sm">
                        <DetailRow label="Extracted title" value={trainingItem.raw_course_title} />
                        <DetailRow label="Mapped qualification" value={trainingItem.mapped_training_title || trainingItem.mapped_training_code || 'Not mapped'} />
                        <DetailRow label="Completed" value={trainingItem.completed_at || 'Not found'} />
                        <DetailRow label="Expires" value={trainingItem.expires_at || 'Not applicable / not found'} />
                        <DetailRow label="Certificate" value={fileName} />
                      </div>
                    </div>
                  )}

                  {/* Timer notice */}
                  <div className={`p-3 rounded-lg border text-sm flex items-center gap-2 ${
                    hasMetMinViewTime ? 'bg-green-50 border-green-200 text-green-800' : 'bg-amber-50 border-amber-200 text-amber-800'
                  }`}>
                    <Clock className="h-4 w-4 flex-shrink-0" />
                    {hasMetMinViewTime ? (
                      <span>Document viewed for <strong>{viewSeconds}s</strong>. You may proceed.</span>
                    ) : (
                      <span>Please review the document ({MIN_VIEW_SECONDS - viewSeconds}s remaining)</span>
                    )}
                  </div>

                  {/* Checklist */}
                  <div className="space-y-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="flex items-center gap-2 text-blue-900">
                      <FileCheck className="h-4 w-4" />
                      <h4 className="font-semibold text-sm">Review Checklist</h4>
                    </div>

                    <div className="space-y-2.5 bg-white p-3 rounded border">
                      {isTrainingReview ? (
                        <>
                          <CheckItem id="rv-fileViewed" checked={checklist.fileViewed} onChange={v => setChecklist(p => ({...p, fileViewed: v}))} label="Source certificate has been opened and reviewed" />
                          <CheckItem id="rv-nameMatches" checked={checklist.nameMatches} onChange={v => setChecklist(p => ({...p, nameMatches: v}))} label="Worker name matches certificate" />
                          <CheckItem id="rv-courseTitle" checked={checklist.trainingCourseTitleCorrect} onChange={v => setChecklist(p => ({...p, trainingCourseTitleCorrect: v}))} label="Extracted course title is correct" />
                          <CheckItem id="rv-mapping" checked={checklist.trainingMappingCorrect} onChange={v => setChecklist(p => ({...p, trainingMappingCorrect: v}))} label="Mapped qualification/requirement is correct" />
                          <CheckItem id="rv-completed" checked={checklist.trainingCompletionDateCorrect} onChange={v => setChecklist(p => ({...p, trainingCompletionDateCorrect: v}))} label="Completed date is correct" />
                          <CheckItem id="rv-expiry" checked={checklist.trainingExpiryDateCorrect} onChange={v => setChecklist(p => ({...p, trainingExpiryDateCorrect: v}))} label="Expiry date is correct or not applicable" />
                          <CheckItem id="rv-documentAcceptable" checked={checklist.documentAcceptable} onChange={v => setChecklist(p => ({...p, documentAcceptable: v}))} label="Certificate is acceptable evidence" />
                          <CheckItem id="rv-legible" checked={checklist.legible} onChange={v => setChecklist(p => ({...p, legible: v}))} label="Certificate is legible and clear" />
                        </>
                      ) : (
                        <>
                          <CheckItem id="rv-fileViewed" checked={checklist.fileViewed} onChange={v => setChecklist(p => ({...p, fileViewed: v}))} label="File has been opened and viewed" />
                          <CheckItem id="rv-nameMatches" checked={checklist.nameMatches} onChange={v => setChecklist(p => ({...p, nameMatches: v}))} label="Name/details match profile" />
                          {!isFormReview && (
                            <CheckItem id="rv-documentAcceptable" checked={checklist.documentAcceptable} onChange={v => setChecklist(p => ({...p, documentAcceptable: v}))} label="Document type acceptable" />
                          )}
                          <CheckItem id="rv-legible" checked={checklist.legible} onChange={v => setChecklist(p => ({...p, legible: v}))} label={isFormReview ? 'All fields completed and readable' : 'Document is legible and clear'} />
                        </>
                      )}

                      {isFormReview && !isTrainingReview && (
                        <>
                          <CheckItem id="rv-documentAcceptable" checked={checklist.documentAcceptable} onChange={v => setChecklist(p => ({...p, documentAcceptable: v}))} label="Answers appear consistent and reasonable" />
                          <CheckItem id="rv-dateValid" checked={checklist.dateValid} onChange={v => setChecklist(p => ({...p, dateValid: v}))} label="Declaration signed and dated" />
                        </>
                      )}

                      {isIdentity && !isTrainingReview && (
                        <>
                          <CheckItem id="rv-frontPresent" checked={checklist.frontPresent} onChange={v => setChecklist(p => ({...p, frontPresent: v}))} label="Front side present" />
                          <CheckItem id="rv-backPresent" checked={checklist.backPresent} onChange={v => setChecklist(p => ({...p, backPresent: v}))} label="Back side present" />
                        </>
                      )}
                      {isAddress && !isTrainingReview && (
                        <>
                          <CheckItem id="rv-addressValid" checked={checklist.addressValid} onChange={v => setChecklist(p => ({...p, addressValid: v}))} label="Address matches declared" />
                          <CheckItem id="rv-dateValid" checked={checklist.dateValid} onChange={v => setChecklist(p => ({...p, dateValid: v}))} label="Document within acceptable date range" />
                        </>
                      )}
                    </div>

                    {isTrainingReview && (
                      <div className="space-y-2">
                        <Label className="text-sm font-medium">Review notes</Label>
                        <Textarea
                          value={trainingReviewNotes}
                          onChange={(e) => setTrainingReviewNotes(e.target.value)}
                          placeholder="Optional notes for accepting or rejecting this extracted item"
                          rows={3}
                        />
                      </div>
                    )}

                    {isFormReview && isHealthQuestionnaireForm && (
                      <div className="space-y-2">
                        <Label className="text-sm font-medium">Health outcome (required)</Label>
                        <RadioGroup value={healthOutcome} onValueChange={setHealthOutcome}>
                          <div className="flex items-start gap-2">
                            <RadioGroupItem value="fit" id="health-outcome-fit" className="mt-1" />
                            <Label htmlFor="health-outcome-fit" className="cursor-pointer">
                              Fit
                            </Label>
                          </div>
                          <div className="flex items-start gap-2">
                            <RadioGroupItem value="conditional" id="health-outcome-conditional" className="mt-1" />
                            <Label htmlFor="health-outcome-conditional" className="cursor-pointer">
                              Conditional
                            </Label>
                          </div>
                          <div className="flex items-start gap-2">
                            <RadioGroupItem value="requires_review" id="health-outcome-requires-review" className="mt-1" />
                            <Label htmlFor="health-outcome-requires-review" className="cursor-pointer">
                              Requires review
                            </Label>
                          </div>
                          <div className="flex items-start gap-2">
                            <RadioGroupItem value="not_fit" id="health-outcome-not-fit" className="mt-1" />
                            <Label htmlFor="health-outcome-not-fit" className="cursor-pointer">
                              Not fit
                            </Label>
                          </div>
                        </RadioGroup>
                      </div>
                    )}

                    {checklistError && (
                      <div className="text-sm text-red-600 bg-red-50 p-2 rounded flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                        {checklistError}
                      </div>
                    )}
                  </div>
                </>
              )}

              {/* ---- STEP: VERIFICATION ---- */}
              {step === 'verification' && (
                <>
                  <div className="text-sm text-green-700 bg-green-50 p-2 rounded flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" />
                    Review checklist confirmed ({viewSeconds}s viewing). Select verification method.
                  </div>

                  {/* AI Validation for PoA */}
                  {isAddress && aiValidation && (
                    <div className={`p-3 rounded-lg border ${aiValidation.isValid ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'}`}>
                      <div className="flex items-center gap-2">
                        {aiValidation.isValid ? <CheckCircle className="h-4 w-4 text-green-600" /> : <AlertTriangle className="h-4 w-4 text-amber-600" />}
                        <span className={`text-sm font-medium ${aiValidation.isValid ? 'text-green-700' : 'text-amber-700'}`}>
                          AI: {aiValidation.message}
                        </span>
                      </div>
                      {aiValidation.documentDate && (
                        <p className="text-xs text-slate-600 mt-1 flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          Dated: {aiValidation.documentDate} ({aiValidation.ageInDays} days ago)
                        </p>
                      )}
                    </div>
                  )}

                  {/* Method selection */}
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold">How did you verify this document?</Label>
                    <RadioGroup value={selectedMethod} onValueChange={setSelectedMethod}>
                      {methods.map((method) => {
                        const Icon = method.icon;
                        return (
                          <div
                            key={method.value}
                            className={`flex items-start space-x-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                              selectedMethod === method.value ? 'border-primary bg-primary/5' : 'border-gray-200 hover:bg-gray-50'
                            }`}
                            onClick={() => setSelectedMethod(method.value)}
                          >
                            <RadioGroupItem value={method.value} id={`rv-${method.value}`} className="mt-1" />
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <Icon className="h-4 w-4 text-gray-600" />
                                <Label htmlFor={`rv-${method.value}`} className="font-medium cursor-pointer text-sm">{method.label}</Label>
                              </div>
                              <p className="text-xs text-gray-500 mt-0.5">{method.description}</p>
                            </div>
                          </div>
                        );
                      })}
                    </RadioGroup>
                  </div>

                  {/* Confirm checks */}
                  <div className="space-y-2.5 p-3 bg-slate-50 rounded-lg border">
                    <Label className="text-xs font-semibold text-slate-700">Confirm verification checks:</Label>
                    <CheckItem id="rv-genuine" checked={confirmChecks.documentGenuine} onChange={v => setConfirmChecks(p => ({...p, documentGenuine: v}))} label="Document appears genuine with valid security features" />
                    <CheckItem id="rv-details" checked={confirmChecks.detailsMatch} onChange={v => setConfirmChecks(p => ({...p, detailsMatch: v}))} label={isIdentity ? 'Name and photo match the applicant' : 'Name and address match application details'} />
                    {isAddress && (
                      <CheckItem id="rv-datevalid2" checked={confirmChecks.dateValid} onChange={v => setConfirmChecks(p => ({...p, dateValid: v}))} label="Document is dated within acceptable period" />
                    )}
                  </div>

                  {/* Stamp preview */}
                  {selectedMethodData && (
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-center gap-2 text-blue-800">
                        <Stamp className="h-4 w-4" />
                        <span className="text-sm font-medium">
                          Stamp: {selectedMethodData.stampType === 'original_seen' ? 'ORIGINAL DOCUMENT SEEN' : 'COPY VERIFIED'}
                        </span>
                      </div>
                      <p className="text-xs text-blue-600 mt-1">
                        Permanently burned into the document with your name and timestamp.
                      </p>
                    </div>
                  )}
                </>
              )}

              {/* ---- STEP: COMPLETE ---- */}
              {step === 'complete' && (
                <div className="space-y-4">
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-center">
                    <ShieldCheck className="h-10 w-10 text-green-600 mx-auto mb-2" />
                    <h4 className="font-semibold text-green-800">
                      {isFormReview
                        ? (showRejectInput ? 'Form Rejected' : 'Form Approved')
                        : isTrainingReview ? 'Training Review Recorded' : isAcceptMode ? 'Evidence Accepted' : 'Verification Complete'}
                    </h4>
                    <p className="text-sm text-green-700 mt-1">
                      {isFormReview
                        ? (showRejectInput
                          ? `Form submission rejected after ${viewSeconds}s of review.`
                          : `Form submission approved after ${viewSeconds}s of review. The audit trail records your viewing time and checklist.`)
                        : isTrainingReview
                        ? trainingCompletionMessage
                        : isAcceptMode
                        ? `Evidence has been accepted after ${viewSeconds}s of review. You can now proceed to record the verification check.`
                        : `Document verified, stamped, and verification check auto-recorded. The audit trail records ${viewSeconds}s of viewing time.`}
                    </p>
                  </div>
                  {!isAcceptMode && !isFormReview && stampedBlobUrl && (
                    <div className="space-y-2">
                      <p className="text-xs text-slate-500 text-center">
                        Use the Original / Stamped toggle above to compare versions.
                      </p>
                      <p className="text-xs text-emerald-600 text-center font-medium">
                        The stamped document has been saved as proof of verification — no further action needed.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* NHS compliance footer */}
              <div className="p-3 bg-slate-100 rounded-lg">
                <div className="flex items-center gap-2 text-slate-700">
                  <Shield className="h-4 w-4" />
                  <span className="text-xs font-medium">Osabea review record</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {isTrainingReview
                    ? 'Evidence review is recorded with timestamp, viewing duration, reviewer, and decision notes.'
                    : 'Verification recorded with timestamp, viewing duration, verifier name, and method.'}
                </p>
              </div>
            </div>

            {/* Footer buttons */}
            <div className="px-4 py-3 border-t bg-slate-50 flex items-center gap-2 flex-shrink-0 sticky bottom-0 z-10">
              {step === 'viewing' && isTrainingReview && (
                <>
                  <Button variant="outline" size="sm" onClick={handleClose} className="flex-1">Cancel</Button>
                  {onTrainingRejected && trainingRejectLabel && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleTrainingReject}
                      disabled={isSubmitting || !hasMetMinViewTime || !checklist.fileViewed}
                      className="flex-1 gap-1 text-red-700 border-red-200 hover:bg-red-50"
                    >
                      {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}
                      {trainingRejectLabel}
                    </Button>
                  )}
                  <Button
                    size="sm"
                    onClick={handleTrainingAccept}
                    disabled={isSubmitting || !hasMetMinViewTime || !trainingChecklistComplete}
                    className="flex-1 gap-1 bg-green-600 hover:bg-green-700"
                  >
                    {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                    {trainingAcceptLabel}
                  </Button>
                </>
              )}
              {step === 'viewing' && isFormReview && !isTrainingReview && (
                <>
                  <Button variant="outline" size="sm" onClick={handleClose} className="flex-1">Cancel</Button>
                  {!showRejectInput ? (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowRejectInput(true)}
                        disabled={isSubmitting || !hasMetMinViewTime || !checklist.fileViewed}
                        className="gap-1 text-red-700 border-red-200 hover:bg-red-50"
                      >
                        <XCircle className="h-4 w-4" />
                        Reject
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleProceedToVerification}
                        disabled={isSubmitting || !hasMetMinViewTime || !checklist.fileViewed || !checklist.nameMatches}
                        className="flex-1 gap-1 bg-green-600 hover:bg-green-700"
                      >
                        {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                        Approve
                      </Button>
                    </>
                  ) : (
                    <div className="flex-1 flex flex-col gap-2">
                      <Textarea
                        placeholder="Reason for rejection (required)"
                        value={formRejectReason}
                        onChange={(e) => setFormRejectReason(e.target.value)}
                        rows={2}
                        className="text-sm"
                      />
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => { setShowRejectInput(false); setFormRejectReason(''); }} className="flex-1">Back</Button>
                        <Button
                          size="sm"
                          onClick={handleFormReject}
                          disabled={isSubmitting || !formRejectReason.trim()}
                          className="flex-1 gap-1 bg-red-600 hover:bg-red-700"
                        >
                          {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}
                          Confirm Reject
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
              {step === 'viewing' && !isTrainingReview && !isFormReview && (
                <>
                  <Button variant="outline" size="sm" onClick={handleClose} className="flex-1">Cancel</Button>
                  <Button
                    size="sm"
                    onClick={handleProceedToVerification}
                    disabled={isSubmitting || !hasMetMinViewTime || !checklist.fileViewed}
                    className="flex-1 gap-1 bg-blue-600 hover:bg-blue-700"
                  >
                    {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                    {isAcceptMode ? 'Accept Evidence' : 'Proceed to Verify'}
                  </Button>
                </>
              )}
              {step === 'verification' && (
                <>
                  <Button variant="outline" size="sm" onClick={() => setStep('viewing')} disabled={isSubmitting}>Back</Button>
                  <Button
                    size="sm"
                    onClick={handleVerifyAndStamp}
                    disabled={isSubmitting || !selectedMethod || !confirmChecks.documentGenuine || !confirmChecks.detailsMatch || (isAddress && !confirmChecks.dateValid)}
                    className="flex-1 gap-1 bg-green-600 hover:bg-green-700"
                  >
                    {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                    Verify & Stamp
                  </Button>
                </>
              )}
              {step === 'complete' && (
                <Button size="sm" onClick={handleClose} className="w-full gap-1 bg-green-600 hover:bg-green-700">
                  <CheckCircle className="h-4 w-4" />
                  Done
                </Button>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** Reusable checkbox row */
function CheckItem({ id, checked, onChange, label }) {
  return (
    <div className="flex items-start gap-2.5">
      <Checkbox id={id} checked={checked} onCheckedChange={onChange} />
      <label htmlFor={id} className="text-sm cursor-pointer leading-tight">{label}</label>
    </div>
  );
}

function DetailRow({ label, value }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-sm text-slate-900">{value || '-'}</p>
    </div>
  );
}

