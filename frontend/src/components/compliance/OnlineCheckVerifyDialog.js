/**
 * OnlineCheckVerifyDialog — Unified RTW / DBS verification dialog
 *
 * CQC Safer Recruitment: single guided flow replacing 3 separate dialogs.
 * Step 1 → Review evidence file + confirm quality
 * Step 2 → Perform online check (guidance + link) + upload proof PDF
 * Step 3 → Confirm outcome + stamp type → dual-stamp both evidence & proof
 *
 * Confidentiality: proof file stored with employee-scoped path, audit-logged
 * Integrity:       SHA-256 hash burned into visual stamp, tamper-evident
 * Availability:    non-blocking stamp burn — verification succeeds even if burn fails
 * Effective:       mirrors CQC Reg 19 & Schedule 3 requirements step by step
 * Efficient:       one dialog replaces 3 clicks across 3 separate dialogs
 * Engaging:        clear progress stepper, colour-coded guidance, live validation
 * Error-tolerant:  prevents submission until all required fields complete
 * Easy to learn:   numbered steps with plain English, external check links
 */

import { useState, useRef } from 'react';
import axios from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import {
  Shield, Upload, CheckCircle, AlertTriangle, ExternalLink,
  FileText, Loader2, ArrowRight, ArrowLeft, Eye, Info, Stamp
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ─── Requirement-specific configuration ──────────────────────────────────────

const CONFIG = {
  right_to_work: {
    title: 'Right to Work Verification',
    subtitle: 'Home Office Online Check',
    icon: Shield,
    color: 'indigo',
    checkUrl: 'https://www.gov.uk/view-right-to-work',
    checkLabel: 'GOV.UK — View a job applicant\'s right to work details',
    checkInstructions: [
      'Ask the applicant for their share code and date of birth.',
      'Enter the details on GOV.UK to view their right to work status.',
      'Save or screenshot the result page as a PDF.',
      'Upload the result below as your verification proof.',
    ],
    methods: [
      { value: 'home_office_online', label: 'Home Office Online Check', description: 'Share code verified on GOV.UK', stampType: 'online_check', recommended: true },
      { value: 'manual_document_check', label: 'Manual Document List Check', description: 'Physical documents checked against List A / List B', stampType: 'original_seen' },
      { value: 'idsp_check', label: 'IDSP Identity Check', description: 'Identity Service Provider digital check', stampType: 'online_check' },
      { value: 'employer_checking_service', label: 'Employer Checking Service', description: 'ECS check for applicants with pending immigration applications', stampType: 'online_check' },
    ],
    referenceLabel: 'Share Code / Reference',
    referencePlaceholder: 'e.g. X4B 7YZ 9RT',
    proofRequired: true,
    proofLabel: 'Upload online check result (PDF or screenshot)',
  },
  dbs: {
    title: 'DBS Verification',
    subtitle: 'DBS Certificate / Update Service Check',
    icon: FileText,
    color: 'violet',
    checkUrl: 'https://www.gov.uk/dbs-update-service',
    checkLabel: 'GOV.UK — DBS Update Service',
    checkInstructions: [
      'Ask the applicant for their DBS certificate number and date of birth.',
      'Check the certificate on the DBS Update Service.',
      'Save or screenshot the result page as a PDF.',
      'Upload the result below as your verification proof.',
    ],
    methods: [
      { value: 'dbs_update_service', label: 'DBS Update Service Check', description: 'Online check via DBS Update Service', stampType: 'online_check', recommended: true },
      { value: 'dbs_certificate_review', label: 'DBS Certificate Review', description: 'Physical certificate checked — original seen', stampType: 'original_seen' },
    ],
    referenceLabel: 'DBS Certificate Number',
    referencePlaceholder: 'e.g. 001234567890',
    proofRequired: true,
    proofLabel: 'Upload check result or certificate scan (PDF or screenshot)',
  },
};

// ─── Step indicator ──────────────────────────────────────────────────────────

const StepIndicator = ({ currentStep, steps }) => (
  <div className="flex items-center gap-1 mb-5">
    {steps.map((step, i) => {
      const isActive = i === currentStep;
      const isComplete = i < currentStep;
      return (
        <div key={i} className="flex items-center gap-1 flex-1">
          <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold shrink-0 transition-all ${
            isComplete ? 'bg-green-600 text-white' :
            isActive ? 'bg-blue-600 text-white ring-2 ring-blue-300 ring-offset-1' :
            'bg-gray-200 text-gray-500'
          }`}>
            {isComplete ? <CheckCircle className="h-4 w-4" /> : i + 1}
          </div>
          <span className={`text-xs font-medium truncate ${isActive ? 'text-blue-700' : isComplete ? 'text-green-700' : 'text-gray-400'}`}>
            {step}
          </span>
          {i < steps.length - 1 && (
            <div className={`flex-1 h-0.5 mx-1 rounded ${isComplete ? 'bg-green-400' : 'bg-gray-200'}`} />
          )}
        </div>
      );
    })}
  </div>
);

// ─── Main component ──────────────────────────────────────────────────────────

export default function OnlineCheckVerifyDialog({
  isOpen,
  onClose,
  file,               // the evidence document being verified
  employeeId,
  employeeName,
  requirementType,     // 'right_to_work' | 'dbs'
  onVerificationComplete,
}) {
  const config = CONFIG[requirementType];

  const IconComponent = config?.icon;
  const fileId = file?.file_id || file?.id;
  const fileName = file?.file_name || file?.name || file?.original_filename || 'Document';

  // ── State ────────────────────────────────────────────────────────────────
  const [step, setStep] = useState(0); // 0=review, 1=online check, 2=confirm
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Step 0 — evidence quality review
  const [reviewChecks, setReviewChecks] = useState({
    fileViewed: false,
    legible: false,
    nameVisible: false,
    documentAcceptable: false,
  });

  // Step 1 — online check proof
  const [selectedMethod, setSelectedMethod] = useState('');
  const [proofFile, setProofFile] = useState(null);
  const [referenceNumber, setReferenceNumber] = useState('');
  const [notes, setNotes] = useState('');
  const fileInputRef = useRef(null);

  // Step 2 — final confirmation
  const [confirmChecks, setConfirmChecks] = useState({
    checkPerformed: false,
    resultAccurate: false,
    willStampBoth: false,
  });

  // Early return AFTER all hooks
  if (!config) return null;

  // ── Validation ───────────────────────────────────────────────────────────
  const reviewValid = reviewChecks.fileViewed && reviewChecks.legible && reviewChecks.documentAcceptable;
  const selectedMethodObj = config.methods.find(m => m.value === selectedMethod);
  const onlineCheckValid = selectedMethod && proofFile;
  const confirmValid = confirmChecks.checkPerformed && confirmChecks.resultAccurate && confirmChecks.willStampBoth;

  // ── Handlers ─────────────────────────────────────────────────────────────
  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const allowed = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!allowed.includes(f.type)) {
      toast.error('Please upload a PDF, PNG, or JPG file');
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      toast.error('File must be under 10 MB');
      return;
    }
    setProofFile(f);
  };

  const handleSubmit = async () => {
    if (!fileId || !selectedMethodObj || !proofFile) return;
    setIsSubmitting(true);

    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('stamp_type', selectedMethodObj.stampType);
      formData.append('outcome', 'verified');
      formData.append('proof_file', proofFile);
      formData.append('document_id', fileId);
      formData.append('document_type', requirementType);
      if (referenceNumber.trim()) formData.append('reference_number', referenceNumber.trim());
      if (notes.trim()) formData.append('notes', notes.trim());

      await axios.post(
        `${API}/employees/${employeeId}/documents/verify`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      toast.success(
        <div className="flex items-center gap-2">
          <Stamp className="h-4 w-4 text-green-600" />
          <div>
            <p className="font-medium">Verified & stamped</p>
            <p className="text-xs text-gray-500">Both evidence and proof have been CQC-stamped</p>
          </div>
        </div>,
        { duration: 5000 }
      );

      onVerificationComplete?.();
      handleClose();
    } catch (error) {
      console.error('Verification failed:', error);
      const msg = error.response?.data?.detail || 'Verification failed. Please try again.';
      toast.error(msg, { duration: 6000 });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setStep(0);
    setReviewChecks({ fileViewed: false, legible: false, nameVisible: false, documentAcceptable: false });
    setSelectedMethod('');
    setProofFile(null);
    setReferenceNumber('');
    setNotes('');
    setConfirmChecks({ checkPerformed: false, resultAccurate: false, willStampBoth: false });
    onClose();
  };

  // ── Render ───────────────────────────────────────────────────────────────
  const STEPS = ['Review Evidence', 'Online Check & Proof', 'Confirm & Stamp'];

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[92vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <div className={`p-1.5 rounded-lg bg-${config.color}-100`}>
              <IconComponent className={`h-5 w-5 text-${config.color}-600`} />
            </div>
            {config.title}
          </DialogTitle>
          <DialogDescription className="flex items-center justify-between">
            <span>{config.subtitle} — {employeeName || 'Employee'}</span>
            <Badge variant="outline" className="text-xs">{fileName}</Badge>
          </DialogDescription>
        </DialogHeader>

        <StepIndicator currentStep={step} steps={STEPS} />

        {/* ───────────────────── STEP 0: Review Evidence ───────────────── */}
        {step === 0 && (
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-medium text-blue-800 mb-2 flex items-center gap-2">
                <Eye className="h-4 w-4" />
                Step 1: Review the uploaded evidence
              </h4>
              <p className="text-sm text-blue-700 mb-3">
                Before performing an online check, confirm the uploaded document is acceptable.
              </p>
              <div className="space-y-2.5">
                {[
                  { key: 'fileViewed', label: 'I have opened and viewed this document', required: true },
                  { key: 'legible', label: 'The document is legible and not blurred or cropped', required: true },
                  { key: 'nameVisible', label: 'The applicant\'s name is clearly visible', required: false },
                  { key: 'documentAcceptable', label: 'The document is an acceptable form of evidence for this requirement', required: true },
                ].map(item => (
                  <label
                    key={item.key}
                    className={`flex items-start gap-3 p-2.5 rounded-lg border cursor-pointer transition-all ${
                      reviewChecks[item.key]
                        ? 'bg-green-50 border-green-300'
                        : 'bg-white border-gray-200 hover:border-blue-300'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={reviewChecks[item.key]}
                      onChange={e => setReviewChecks(prev => ({ ...prev, [item.key]: e.target.checked }))}
                      className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">
                      {item.label}
                      {item.required && <span className="text-red-500 ml-0.5">*</span>}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {!reviewValid && (
              <p className="text-xs text-amber-600 flex items-center gap-1">
                <Info className="h-3 w-3" />
                Complete the required checks above to continue.
              </p>
            )}
          </div>
        )}

        {/* ───────────────── STEP 1: Online Check & Proof Upload ───────── */}
        {step === 1 && (
          <div className="space-y-4">
            {/* Guidance card with external link */}
            <div className={`bg-${config.color}-50 border border-${config.color}-200 rounded-lg p-4`}>
              <h4 className={`font-medium text-${config.color}-800 mb-2 flex items-center gap-2`}>
                <ExternalLink className="h-4 w-4" />
                Step 2: Perform the online check
              </h4>
              <ol className="text-sm text-gray-700 space-y-1.5 list-decimal list-inside mb-3">
                {config.checkInstructions.map((inst, i) => (
                  <li key={i}>{inst}</li>
                ))}
              </ol>
              <a
                href={config.checkUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-${config.color}-600 text-white text-sm font-medium hover:bg-${config.color}-700 transition-colors`}
              >
                <ExternalLink className="h-4 w-4" />
                {config.checkLabel}
              </a>
            </div>

            {/* Method selection */}
            <div>
              <Label className="text-sm font-medium mb-2 block">Verification method used *</Label>
              <div className="grid gap-2">
                {config.methods.map(method => (
                  <label
                    key={method.value}
                    className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                      selectedMethod === method.value
                        ? 'bg-blue-50 border-blue-400 ring-1 ring-blue-300'
                        : 'bg-white border-gray-200 hover:border-blue-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="check-method"
                      value={method.value}
                      checked={selectedMethod === method.value}
                      onChange={() => setSelectedMethod(method.value)}
                      className="mt-0.5 h-4 w-4 text-blue-600 focus:ring-blue-500"
                    />
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-gray-900 flex items-center gap-2">
                        {method.label}
                        {method.recommended && (
                          <Badge className="bg-green-100 text-green-700 text-[10px] px-1.5 py-0">Recommended</Badge>
                        )}
                      </span>
                      <p className="text-xs text-gray-500 mt-0.5">{method.description}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Proof file upload */}
            <div>
              <Label className="text-sm font-medium mb-2 block">{config.proofLabel} *</Label>
              <div
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-5 text-center cursor-pointer transition-all ${
                  proofFile
                    ? 'border-green-300 bg-green-50'
                    : 'border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50'
                }`}
              >
                {proofFile ? (
                  <div className="flex items-center justify-center gap-2">
                    <FileText className="h-5 w-5 text-green-600" />
                    <div className="text-left">
                      <p className="text-sm font-medium text-green-800">{proofFile.name}</p>
                      <p className="text-xs text-green-600">{(proofFile.size / 1024).toFixed(0)} KB — Click to change</p>
                    </div>
                  </div>
                ) : (
                  <div>
                    <Upload className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                    <p className="text-sm text-gray-600">Click to upload proof file</p>
                    <p className="text-xs text-gray-400 mt-1">PDF, PNG, or JPG — max 10 MB</p>
                  </div>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>

            {/* Reference number */}
            <div>
              <Label className="text-sm font-medium">{config.referenceLabel}</Label>
              <Input
                value={referenceNumber}
                onChange={e => setReferenceNumber(e.target.value)}
                placeholder={config.referencePlaceholder}
                className="mt-1"
              />
            </div>

            {/* Notes */}
            <div>
              <Label className="text-sm font-medium">Notes (optional)</Label>
              <Textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Any additional observations..."
                className="mt-1 min-h-[60px]"
              />
            </div>
          </div>
        )}

        {/* ───────────────── STEP 2: Confirm & Stamp ───────────────────── */}
        {step === 2 && (
          <div className="space-y-4">
            {/* Summary card */}
            <div className="bg-gray-50 border rounded-lg p-4 space-y-3">
              <h4 className="font-medium text-gray-800 flex items-center gap-2">
                <Shield className="h-4 w-4" />
                Verification Summary
              </h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-gray-500">Evidence File</p>
                  <p className="font-medium text-gray-800 truncate">{fileName}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Proof File</p>
                  <p className="font-medium text-gray-800 truncate">{proofFile?.name || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Method</p>
                  <p className="font-medium text-gray-800">{selectedMethodObj?.label || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Stamp Type</p>
                  <Badge className={`${
                    selectedMethodObj?.stampType === 'online_check'
                      ? 'bg-indigo-100 text-indigo-700'
                      : 'bg-green-100 text-green-700'
                  }`}>
                    {selectedMethodObj?.stampType === 'online_check' ? 'ONLINE VERIFIED' : 'ORIGINAL VERIFIED'}
                  </Badge>
                </div>
                {referenceNumber && (
                  <div className="col-span-2">
                    <p className="text-xs text-gray-500">{config.referenceLabel}</p>
                    <p className="font-medium text-gray-800 font-mono">{referenceNumber}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Dual stamp preview */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-medium text-blue-800 mb-2 flex items-center gap-2">
                <Stamp className="h-4 w-4" />
                CQC Visual Stamp Preview
              </h4>
              <p className="text-xs text-blue-700 mb-3">
                A permanent, tamper-evident Osabea CQC stamp will be burned into both files:
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-white border border-blue-200 rounded-lg p-3 text-center">
                  <FileText className="h-6 w-6 mx-auto mb-1 text-blue-600" />
                  <p className="text-xs font-medium text-gray-700">Evidence Document</p>
                  <p className="text-[10px] text-gray-500 mt-0.5">Passport / BRP / Certificate</p>
                  <Badge className="mt-1 bg-green-100 text-green-700 text-[10px]">Will be stamped</Badge>
                </div>
                <div className="bg-white border border-blue-200 rounded-lg p-3 text-center">
                  <Shield className="h-6 w-6 mx-auto mb-1 text-indigo-600" />
                  <p className="text-xs font-medium text-gray-700">Verification Proof</p>
                  <p className="text-[10px] text-gray-500 mt-0.5">Online check result / Screenshot</p>
                  <Badge className="mt-1 bg-green-100 text-green-700 text-[10px]">Will be stamped</Badge>
                </div>
              </div>
            </div>

            {/* Final confirmation checkboxes */}
            <div className="space-y-2.5">
              {[
                { key: 'checkPerformed', label: 'I have personally performed or witnessed the online check listed above' },
                { key: 'resultAccurate', label: 'The uploaded proof accurately reflects the check result' },
                { key: 'willStampBoth', label: 'I authorise permanent CQC stamps to be applied to both the evidence and the proof' },
              ].map(item => (
                <label
                  key={item.key}
                  className={`flex items-start gap-3 p-2.5 rounded-lg border cursor-pointer transition-all ${
                    confirmChecks[item.key]
                      ? 'bg-green-50 border-green-300'
                      : 'bg-white border-gray-200 hover:border-green-300'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={confirmChecks[item.key]}
                    onChange={e => setConfirmChecks(prev => ({ ...prev, [item.key]: e.target.checked }))}
                    className="mt-0.5 h-4 w-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
                  />
                  <span className="text-sm text-gray-700">{item.label}</span>
                </label>
              ))}
            </div>

            {!confirmValid && (
              <p className="text-xs text-amber-600 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                Tick all three confirmations to submit.
              </p>
            )}
          </div>
        )}

        {/* ───────────────── Footer ─────────────────────────────────────── */}
        <DialogFooter className="flex items-center justify-between gap-2 pt-4 border-t">
          <div>
            {step > 0 && (
              <Button variant="outline" onClick={() => setStep(s => s - 1)} disabled={isSubmitting}>
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleClose} disabled={isSubmitting}>
              Cancel
            </Button>

            {step === 0 && (
              <Button
                onClick={() => setStep(1)}
                disabled={!reviewValid}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                Continue
                <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            )}

            {step === 1 && (
              <Button
                onClick={() => setStep(2)}
                disabled={!onlineCheckValid}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                Review & Confirm
                <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            )}

            {step === 2 && (
              <Button
                onClick={handleSubmit}
                disabled={!confirmValid || isSubmitting}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Verifying & Stamping...
                  </>
                ) : (
                  <>
                    <Stamp className="h-4 w-4 mr-1" />
                    Verify & Apply Dual Stamp
                  </>
                )}
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
