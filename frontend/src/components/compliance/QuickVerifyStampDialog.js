/**
 * QuickVerifyStampDialog - Simplified verification + stamp for Identity & Proof of Address
 * 
 * COMBINES: Record Check + Apply Stamp into ONE atomic action
 * 
 * This ensures:
 * - No document can be stamped without verification recorded
 * - No verification can be recorded without stamp applied
 * - Audit trail is complete
 * 
 * Used for SIMPLE documents (Identity, PoA) - NOT for complex checks (RTW, DBS)
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
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
  User,
  MapPin
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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

export default function QuickVerifyStampDialog({
  isOpen,
  onClose,
  file,
  employeeId,
  employeeName,
  requirementType, // 'identity' or 'proof_of_address'
  aiValidation, // { isValid, message, documentDate, ageInDays }
  onVerificationComplete
}) {
  const { token } = useAuth();
  const [step, setStep] = useState('checklist'); // 'checklist' | 'verification'
  const [minimalChecklist, setMinimalChecklist] = useState({
    fileViewed: false,
    nameMatches: false,
    documentAcceptable: false,
    legible: false,
    frontPresent: false,
    backPresent: false,
    addressValid: false,
    dateValid: false
  });
  const [selectedMethod, setSelectedMethod] = useState('');
  const [confirmChecks, setConfirmChecks] = useState({
    documentGenuine: false,
    detailsMatch: false,
    dateValid: false // For PoA only
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [checklistError, setChecklistError] = useState('');

  const isIdentity = requirementType === 'identity';
  const isAddress = requirementType === 'proof_of_address';
  const methods = isIdentity ? IDENTITY_METHODS : ADDRESS_METHODS;

  // Reset state when dialog opens
  useEffect(() => {
    if (isOpen) {
      setStep('checklist');
      setMinimalChecklist({
        fileViewed: false,
        nameMatches: false,
        documentAcceptable: false,
        legible: false,
        frontPresent: false,
        backPresent: false,
        addressValid: false,
        dateValid: false
      });
      setSelectedMethod('');
      setConfirmChecks({
        documentGenuine: false,
        detailsMatch: false,
        dateValid: false
      });
      setChecklistError('');
    }
  }, [isOpen]);

  const handleSubmit = async () => {
    if (!selectedMethod) {
      toast.error('Please select how you verified the document');
      return;
    }

    if (!confirmChecks.documentGenuine || !confirmChecks.detailsMatch) {
      toast.error('Please confirm all verification checks');
      return;
    }

    if (isAddress && !confirmChecks.dateValid) {
      toast.error('Please confirm the document date is valid');
      return;
    }

    const method = methods.find(m => m.value === selectedMethod);
    if (!method) {
      toast.error('Invalid verification method');
      return;
    }

    setIsSubmitting(true);
    try {
      const docId = file.file_id || file.id;
      if (!docId) {
        toast.error('Document ID not found');
        return;
      }

      // Call unified verify-and-stamp endpoint
      const endpoint = isIdentity 
        ? `${API}/employees/${employeeId}/identity/verify-and-stamp`
        : `${API}/employees/${employeeId}/address/verify-and-stamp`;

      await axios.post(
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
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      toast.success(
        <div className="flex items-center gap-2">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <span>Document verified & stamped</span>
        </div>
      );

      if (onVerificationComplete) {
        onVerificationComplete();
      }
      onClose();
    } catch (err) {
      console.error('Verification failed:', err);
      toast.error(err.response?.data?.detail || 'Failed to verify document');
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedMethodData = methods.find(m => m.value === selectedMethod);

  // Handle review checklist - calls backend /start-review
  const handleStartReview = async () => {
    setChecklistError('');
    
    if (!minimalChecklist.fileViewed) {
      setChecklistError('You must confirm the file was viewed');
      return;
    }
    
    const baseChecks = [minimalChecklist.fileViewed, minimalChecklist.nameMatches, minimalChecklist.documentAcceptable, minimalChecklist.legible];
    if (baseChecks.filter(Boolean).length < 2) {
      setChecklistError('Please confirm at least 2 basic checklist items');
      return;
    }
    
    if (isIdentity && !minimalChecklist.frontPresent) {
      setChecklistError('Please confirm front side is present');
      return;
    }
    
    if (isAddress && !minimalChecklist.addressValid) {
      setChecklistError('Please confirm address is valid');
      return;
    }

    setIsSubmitting(true);
    try {
      const docId = file.file_id || file.id;
      if (!docId) {
        setChecklistError('Document ID not found');
        return;
      }

      await axios.post(
        `${API}/employee-documents/${docId}/start-review`,
        {
          file_viewed: minimalChecklist.fileViewed,
          name_matches: minimalChecklist.nameMatches,
          document_acceptable: minimalChecklist.documentAcceptable,
          legible: minimalChecklist.legible,
          front_present: isIdentity ? minimalChecklist.frontPresent : undefined,
          back_present: isIdentity ? minimalChecklist.backPresent : undefined,
          address_valid: isAddress ? minimalChecklist.addressValid : undefined,
          date_valid: isAddress ? minimalChecklist.dateValid : undefined
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      setStep('verification');
      toast.success('Review checklist recorded. Proceed with verification.');
    } catch (err) {
      console.error('Review checklist failed:', err);
      setChecklistError(err.response?.data?.detail || 'Failed to record review checklist');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-lg" data-testid="quick-verify-stamp-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {isIdentity ? (
              <User className="h-5 w-5 text-blue-600" />
            ) : (
              <MapPin className="h-5 w-5 text-purple-600" />
            )}
            Verify & Stamp {isIdentity ? 'Identity Document' : 'Proof of Address'}
          </DialogTitle>
          <DialogDescription>
            {file?.file_name || file?.name} for {employeeName}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* STEP 1: MINIMAL REVIEW CHECKLIST */}
          {step === 'checklist' && (
            <div className="space-y-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center gap-2 text-blue-900">
                <FileCheck className="h-5 w-5" />
                <h3 className="font-semibold">Review Checklist</h3>
              </div>
              <p className="text-sm text-blue-800">
                Before verification, please confirm you have reviewed this document:
              </p>
              
              <div className="space-y-3 bg-white p-3 rounded border">
                <div className="flex items-start gap-3">
                  <Checkbox 
                    id="fileViewed"
                    checked={minimalChecklist.fileViewed}
                    onCheckedChange={(checked) => setMinimalChecklist(prev => ({...prev, fileViewed: checked}))}
                  />
                  <label htmlFor="fileViewed" className="text-sm cursor-pointer">
                    ✓ File has been opened and viewed
                  </label>
                </div>
                
                <div className="flex items-start gap-3">
                  <Checkbox 
                    id="nameMatches"
                    checked={minimalChecklist.nameMatches}
                    onCheckedChange={(checked) => setMinimalChecklist(prev => ({...prev, nameMatches: checked}))}
                  />
                  <label htmlFor="nameMatches" className="text-sm cursor-pointer">
                    ✓ Name/details match profile
                  </label>
                </div>
                
                <div className="flex items-start gap-3">
                  <Checkbox 
                    id="documentAcceptable"
                    checked={minimalChecklist.documentAcceptable}
                    onCheckedChange={(checked) => setMinimalChecklist(prev => ({...prev, documentAcceptable: checked}))}
                  />
                  <label htmlFor="documentAcceptable" className="text-sm cursor-pointer">
                    ✓ Document type acceptable
                  </label>
                </div>
                
                <div className="flex items-start gap-3">
                  <Checkbox 
                    id="legible"
                    checked={minimalChecklist.legible}
                    onCheckedChange={(checked) => setMinimalChecklist(prev => ({...prev, legible: checked}))}
                  />
                  <label htmlFor="legible" className="text-sm cursor-pointer">
                    ✓ Document is legible and clear
                  </label>
                </div>
                
                {isIdentity && (
                  <>
                    <div className="flex items-start gap-3">
                      <Checkbox 
                        id="frontPresent"
                        checked={minimalChecklist.frontPresent}
                        onCheckedChange={(checked) => setMinimalChecklist(prev => ({...prev, frontPresent: checked}))}
                      />
                      <label htmlFor="frontPresent" className="text-sm cursor-pointer">
                        ✓ Front side present
                      </label>
                    </div>
                    <div className="flex items-start gap-3">
                      <Checkbox 
                        id="backPresent"
                        checked={minimalChecklist.backPresent}
                        onCheckedChange={(checked) => setMinimalChecklist(prev => ({...prev, backPresent: checked}))}
                      />
                      <label htmlFor="backPresent" className="text-sm cursor-pointer">
                        ✓ Back side present
                      </label>
                    </div>
                  </>
                )}
                
                {isAddress && (
                  <>
                    <div className="flex items-start gap-3">
                      <Checkbox 
                        id="addressValid"
                        checked={minimalChecklist.addressValid}
                        onCheckedChange={(checked) => setMinimalChecklist(prev => ({...prev, addressValid: checked}))}
                      />
                      <label htmlFor="addressValid" className="text-sm cursor-pointer">
                        ✓ Address matches declared
                      </label>
                    </div>
                    <div className="flex items-start gap-3">
                      <Checkbox 
                        id="dateValid"
                        checked={minimalChecklist.dateValid}
                        onCheckedChange={(checked) => setMinimalChecklist(prev => ({...prev, dateValid: checked}))}
                      />
                      <label htmlFor="dateValid" className="text-sm cursor-pointer">
                        ✓ Document within acceptable date range
                      </label>
                    </div>
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
          )}

          {/* STEP 2: VERIFICATION CONFIRMED */}
          {step === 'verification' && (
            <div className="text-sm text-green-700 bg-green-50 p-2 rounded flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              Review checklist confirmed. Proceed with verification.
            </div>
          )}

          {/* AI Validation Status for PoA - only show on verification step */}
          {step === 'verification' && isAddress && aiValidation && (
            <div className={`p-3 rounded-lg border ${
              aiValidation.isValid 
                ? 'bg-green-50 border-green-200' 
                : 'bg-amber-50 border-amber-200'
            }`}>
              <div className="flex items-center gap-2">
                {aiValidation.isValid ? (
                  <CheckCircle className="h-4 w-4 text-green-600" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                )}
                <span className={`text-sm font-medium ${
                  aiValidation.isValid ? 'text-green-700' : 'text-amber-700'
                }`}>
                  AI Validation: {aiValidation.message}
                </span>
              </div>
              {aiValidation.documentDate && (
                <p className="text-xs text-slate-600 mt-1 flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  Document dated: {aiValidation.documentDate} ({aiValidation.ageInDays} days ago)
                </p>
              )}
            </div>
          )}

          {/* Verification Method Selection - only on verification step */}
          {step === 'verification' && (
          <div className="space-y-3">
            <Label className="text-sm font-semibold">How did you verify this document?</Label>
            <RadioGroup value={selectedMethod} onValueChange={setSelectedMethod}>
              {methods.map((method) => {
                const Icon = method.icon;
                return (
                  <div 
                    key={method.value}
                    className={`flex items-start space-x-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedMethod === method.value 
                        ? 'border-primary bg-primary/5' 
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                    onClick={() => setSelectedMethod(method.value)}
                    data-testid={`method-${method.value}`}
                  >
                    <RadioGroupItem value={method.value} id={method.value} className="mt-1" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-gray-600" />
                        <Label htmlFor={method.value} className="font-medium cursor-pointer">
                          {method.label}
                        </Label>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">{method.description}</p>
                    </div>
                  </div>
                );
              })}
            </RadioGroup>
          </div>
          )}

          {/* Confirmation Checkboxes - only on verification step */}
          {step === 'verification' && (
          <div className="space-y-3 p-4 bg-slate-50 rounded-lg border">
            <Label className="text-sm font-semibold text-slate-700">
              Confirm verification checks:
            </Label>
            
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <Checkbox 
                  id="documentGenuine"
                  checked={confirmChecks.documentGenuine}
                  onCheckedChange={(checked) => setConfirmChecks(prev => ({...prev, documentGenuine: checked}))}
                  data-testid="check-genuine"
                />
                <label htmlFor="documentGenuine" className="text-sm text-slate-700 cursor-pointer">
                  Document appears genuine with valid security features
                </label>
              </div>

              <div className="flex items-start gap-3">
                <Checkbox 
                  id="detailsMatch"
                  checked={confirmChecks.detailsMatch}
                  onCheckedChange={(checked) => setConfirmChecks(prev => ({...prev, detailsMatch: checked}))}
                  data-testid="check-details"
                />
                <label htmlFor="detailsMatch" className="text-sm text-slate-700 cursor-pointer">
                  {isIdentity 
                    ? 'Name and photo match the applicant' 
                    : 'Name and address match application details'}
                </label>
              </div>

              {isAddress && (
                <div className="flex items-start gap-3">
                  <Checkbox 
                    id="dateValid"
                    checked={confirmChecks.dateValid}
                    onCheckedChange={(checked) => setConfirmChecks(prev => ({...prev, dateValid: checked}))}
                    data-testid="check-date"
                  />
                  <label htmlFor="dateValid" className="text-sm text-slate-700 cursor-pointer">
                    Document is dated within acceptable period (bank statement &lt;6 months, council tax &lt;12 months)
                  </label>
                </div>
              )}
            </div>
          </div>
          )}

          {/* Stamp Preview - only on verification step */}
          {step === 'verification' && selectedMethodData && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center gap-2 text-blue-800">
                <Stamp className="h-4 w-4" />
                <span className="text-sm font-medium">
                  Stamp to apply: {selectedMethodData.stampType === 'original_seen' 
                    ? 'ORIGINAL DOCUMENT SEEN' 
                    : 'COPY VERIFIED'}
                </span>
              </div>
              <p className="text-xs text-blue-600 mt-1">
                This stamp will be permanently burned into the document with your name and timestamp.
              </p>
            </div>
          )}

          {/* NHS Compliance Note */}
          <div className="p-3 bg-slate-100 rounded-lg">
            <div className="flex items-center gap-2 text-slate-700">
              <Shield className="h-4 w-4" />
              <span className="text-xs font-medium">NHS Safer Recruitment Compliant</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              This verification will be recorded in the audit log with timestamp, your name, and method used.
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          
          {/* Checklist Step: Confirm Checklist Button */}
          {step === 'checklist' && (
            <Button 
              onClick={handleStartReview}
              disabled={isSubmitting || !minimalChecklist.fileViewed}
              className="gap-2 bg-blue-600 hover:bg-blue-700"
              data-testid="confirm-checklist-btn"
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4" />
              )}
              Confirm Checklist
            </Button>
          )}
          
          {/* Verification Step: Verify & Apply Stamp Button */}
          {step === 'verification' && (
            <Button 
              onClick={handleSubmit}
              disabled={isSubmitting || !selectedMethod || !confirmChecks.documentGenuine || !confirmChecks.detailsMatch || (isAddress && !confirmChecks.dateValid)}
              className="gap-2 bg-green-600 hover:bg-green-700"
              data-testid="verify-stamp-btn"
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4" />
              )}
              Verify & Apply Stamp
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
