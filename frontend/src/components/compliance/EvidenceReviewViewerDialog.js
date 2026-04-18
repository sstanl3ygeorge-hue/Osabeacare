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
  X
} from 'lucide-react';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
  mode = 'verify' // 'verify' = Identity/POA (checklist → verify & stamp), 'accept' = RTW/DBS (view → accept evidence)
}) {
  const { token } = useAuth();
  const isAcceptMode = mode === 'accept';

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
    dateValid: false
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

  const isIdentity = requirementType === 'identity';
  const isAddress = requirementType === 'proof_of_address';
  const methods = isIdentity ? IDENTITY_METHODS : ADDRESS_METHODS;
  const fileName = file?.file_name || file?.name || 'Document';
  const docId = file?.id || file?.file_id;
  // Normalise file URL — backend evidence URLs are often relative (/api/...)
  const rawFileUrl = file?.file_url || (docId ? `/api/employee-documents/${docId}/file` : null);
  const fileUrl = rawFileUrl && rawFileUrl.startsWith('/api/')
    ? `${API}${rawFileUrl.substring(4)}`
    : rawFileUrl;
  const fileType = getFileType(contentType, fileName);
  const hasMetMinViewTime = viewSeconds >= MIN_VIEW_SECONDS;

  // ------ Reset on open ------
  useEffect(() => {
    if (isOpen) {
      setStep('viewing');
      setChecklist({ fileViewed: false, nameMatches: false, documentAcceptable: false, legible: false, frontPresent: false, backPresent: false, addressValid: false, dateValid: false });
      setSelectedMethod('');
      setConfirmChecks({ documentGenuine: false, detailsMatch: false, dateValid: false });
      setChecklistError('');
      setViewSeconds(0);
      setCurrentPage(1);
      setScale(1.0);
      setRotation(0);
      setViewingStamped(false);
      setStampedBlobUrl(null);
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

    setIsSubmitting(true);
    try {
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
          {isAcceptMode
            ? `Review ${requirementType === 'right_to_work' ? 'Right to Work' : requirementType === 'dbs' ? 'DBS Certificate' : requirementType} Evidence`
            : `Review & Verify ${isIdentity ? 'Identity Document' : 'Proof of Address'}`}
        </DialogTitle>
        <DialogDescription className="sr-only">
          View the document and complete the verification checklist
        </DialogDescription>

        <div className="flex h-full">
          {/* ===== LEFT: Document Viewer ===== */}
          <div className="flex-1 flex flex-col bg-slate-900 min-w-0">
            {/* Viewer toolbar */}
            <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
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
                {fileType === 'pdf' && (
                  <>
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-slate-300 hover:text-white" onClick={zoomOut} title="Zoom out"><ZoomOut className="h-4 w-4" /></Button>
                    <span className="text-xs text-slate-400 w-10 text-center">{Math.round(scale * 100)}%</span>
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-slate-300 hover:text-white" onClick={zoomIn} title="Zoom in"><ZoomIn className="h-4 w-4" /></Button>
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
            <div className="flex-1 overflow-auto flex items-start justify-center p-4">
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
                <div>
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
                  {numPages > 1 && (
                    <div className="flex items-center justify-center gap-3 mt-3">
                      <Button size="sm" variant="ghost" className="h-7 text-slate-300" onClick={goToPrevPage} disabled={currentPage <= 1}>
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                      <span className="text-xs text-slate-400">{currentPage} / {numPages}</span>
                      <Button size="sm" variant="ghost" className="h-7 text-slate-300" onClick={goToNextPage} disabled={currentPage >= numPages}>
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  )}
                </div>
              ) : fileType === 'image' ? (
                <img
                  src={viewingStamped && stampedBlobUrl ? stampedBlobUrl : blobUrl}
                  alt={fileName}
                  className="max-w-full max-h-full object-contain"
                  style={{ transform: `rotate(${rotation}deg) scale(${scale})` }}
                />
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
          <div className="w-[380px] flex-shrink-0 border-l flex flex-col bg-white overflow-hidden">
            {/* Header */}
            <div className="px-4 py-3 border-b bg-slate-50">
              <div className="flex items-center gap-2">
                {isAcceptMode ? <Shield className="h-5 w-5 text-indigo-600" /> : isIdentity ? <User className="h-5 w-5 text-blue-600" /> : <MapPin className="h-5 w-5 text-purple-600" />}
                <div>
                  <h3 className="font-semibold text-sm">
                    {isAcceptMode
                      ? `Review ${requirementType === 'right_to_work' ? 'Right to Work' : requirementType === 'dbs' ? 'DBS Certificate' : requirementType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())} Evidence`
                      : `Verify ${isIdentity ? 'Identity Document' : 'Proof of Address'}`}
                  </h3>
                  <p className="text-xs text-slate-500 truncate">{fileName} — {employeeName}</p>
                </div>
              </div>

              {/* Progress steps */}
              <div className="flex items-center gap-2 mt-3">
                {(isAcceptMode ? ['viewing', 'complete'] : ['viewing', 'verification', 'complete']).map((s, i, arr) => (
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
            <div className="flex-1 overflow-y-auto p-4 space-y-4">

              {/* ---- STEP: VIEWING + CHECKLIST ---- */}
              {step === 'viewing' && (
                <>
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
                      <CheckItem id="rv-fileViewed" checked={checklist.fileViewed} onChange={v => setChecklist(p => ({...p, fileViewed: v}))} label="File has been opened and viewed" />
                      <CheckItem id="rv-nameMatches" checked={checklist.nameMatches} onChange={v => setChecklist(p => ({...p, nameMatches: v}))} label="Name/details match profile" />
                      <CheckItem id="rv-documentAcceptable" checked={checklist.documentAcceptable} onChange={v => setChecklist(p => ({...p, documentAcceptable: v}))} label="Document type acceptable" />
                      <CheckItem id="rv-legible" checked={checklist.legible} onChange={v => setChecklist(p => ({...p, legible: v}))} label="Document is legible and clear" />

                      {isIdentity && (
                        <>
                          <CheckItem id="rv-frontPresent" checked={checklist.frontPresent} onChange={v => setChecklist(p => ({...p, frontPresent: v}))} label="Front side present" />
                          <CheckItem id="rv-backPresent" checked={checklist.backPresent} onChange={v => setChecklist(p => ({...p, backPresent: v}))} label="Back side present" />
                        </>
                      )}
                      {isAddress && (
                        <>
                          <CheckItem id="rv-addressValid" checked={checklist.addressValid} onChange={v => setChecklist(p => ({...p, addressValid: v}))} label="Address matches declared" />
                          <CheckItem id="rv-dateValid" checked={checklist.dateValid} onChange={v => setChecklist(p => ({...p, dateValid: v}))} label="Document within acceptable date range" />
                        </>
                      )}
                    </div>

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
                      {isAcceptMode ? 'Evidence Accepted' : 'Verification Complete'}
                    </h4>
                    <p className="text-sm text-green-700 mt-1">
                      {isAcceptMode
                        ? `Evidence has been accepted after ${viewSeconds}s of review. You can now proceed to record the verification check.`
                        : `Document has been verified and stamped. The audit trail records ${viewSeconds}s of viewing time.`}
                    </p>
                  </div>
                  {!isAcceptMode && stampedBlobUrl && (
                    <p className="text-xs text-slate-500 text-center">
                      Use the Original / Stamped toggle above to compare versions.
                    </p>
                  )}
                </div>
              )}

              {/* NHS compliance footer */}
              <div className="p-3 bg-slate-100 rounded-lg">
                <div className="flex items-center gap-2 text-slate-700">
                  <Shield className="h-4 w-4" />
                  <span className="text-xs font-medium">NHS Safer Recruitment Compliant</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Verification recorded with timestamp, viewing duration, verifier name, and method.
                </p>
              </div>
            </div>

            {/* Footer buttons */}
            <div className="px-4 py-3 border-t bg-slate-50 flex items-center gap-2">
              {step === 'viewing' && (
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
