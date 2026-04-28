/**
 * DocumentVerificationModal - CQC-compliant document verification
 * 
 * Opens when admin clicks [Verify] or [Verify with Evidence]
 * Requires:
 * - Stamp type selection
 * - Proof upload (screenshot/PDF)
 * - Outcome selection
 * - Optional reference number
 * 
 * All verification actions are logged to audit_logs
 */

import { useState } from 'react';
import axios from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';
import API_BASE from '../../utils/apiBase';
import {
  Loader2, CheckCircle, XCircle, AlertTriangle, Upload, 
  FileCheck, Eye, Globe, Shield
} from 'lucide-react';

const API = API_BASE;

const STAMP_TYPES = [
  {
    id: 'original_seen',
    label: 'ORIGINAL SEEN',
    description: 'I have physically seen the original document',
    icon: Eye
  },
  {
    id: 'copy_verified',
    label: 'COPY VERIFIED',
    description: 'I have compared this copy with the original',
    icon: FileCheck
  },
  {
    id: 'online_check',
    label: 'ONLINE CHECK',
    description: 'Verified via online system (e.g., Home Office, NMC, DBS Update)',
    icon: Globe
  }
];

const VERIFICATION_OUTCOMES = [
  { id: 'verified', label: 'Verified', description: 'Document is valid and complete', color: 'text-green-600' },
  { id: 'information_present', label: 'Information Present', description: 'Information noted but requires follow-up', color: 'text-amber-600' },
  { id: 'not_verified', label: 'Not Verified', description: 'Document could not be verified', color: 'text-red-600' }
];

export default function DocumentVerificationModal({ 
  open, 
  onClose, 
  document, 
  employeeId,
  employeeName,
  onVerified 
}) {
  const { token } = useAuth();
  const [stampType, setStampType] = useState('');
  const [outcome, setOutcome] = useState('');
  const [proofFile, setProofFile] = useState(null);
  const [referenceNumber, setReferenceNumber] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file type
      const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'application/pdf'];
      if (!validTypes.includes(file.type)) {
        toast.error('Please upload a PNG, JPG, or PDF file');
        return;
      }
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        toast.error('File size must be less than 10MB');
        return;
      }
      setProofFile(file);
    }
  };

  const handleSubmit = async () => {
    // Validation
    if (!stampType) {
      toast.error('Please select a stamp type');
      return;
    }
    if (!proofFile) {
      toast.error('Please upload proof of verification');
      return;
    }
    if (!outcome) {
      toast.error('Please select verification outcome');
      return;
    }

    setLoading(true);
    try {
      // Create form data for file upload
      const formData = new FormData();
      formData.append('stamp_type', stampType);
      formData.append('outcome', outcome);
      formData.append('proof_file', proofFile);
      if (referenceNumber) formData.append('reference_number', referenceNumber);
      if (notes) formData.append('notes', notes);
      formData.append('document_id', document.id || document.document_id);
      formData.append('document_type', document.document_type || document.type || document.requirement_id);

      const response = await axios.post(
        `${API}/employees/${employeeId}/documents/verify`,
        formData,
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(progress);
          }
        }
      );

      toast.success('Document verified successfully');
      onVerified?.(response.data);
      handleClose();
    } catch (error) {
      console.error('Verification failed:', error);
      toast.error(error.response?.data?.detail || 'Failed to verify document');
    } finally {
      setLoading(false);
      setUploadProgress(0);
    }
  };

  const handleClose = () => {
    setStampType('');
    setOutcome('');
    setProofFile(null);
    setReferenceNumber('');
    setNotes('');
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg" data-testid="verification-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Verify Document
          </DialogTitle>
          <DialogDescription>
            {document?.document_type || document?.type || 'Document'} for {employeeName}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Stamp Type Selection */}
          <div className="space-y-3">
            <Label className="text-sm font-semibold">Stamp Type *</Label>
            <RadioGroup value={stampType} onValueChange={setStampType}>
              {STAMP_TYPES.map((stamp) => {
                const Icon = stamp.icon;
                return (
                  <div 
                    key={stamp.id}
                    className={`flex items-start space-x-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                      stampType === stamp.id 
                        ? 'border-primary bg-primary/5' 
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                    onClick={() => setStampType(stamp.id)}
                    data-testid={`stamp-${stamp.id}`}
                  >
                    <RadioGroupItem value={stamp.id} id={stamp.id} className="mt-1" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-gray-600" />
                        <Label htmlFor={stamp.id} className="font-medium cursor-pointer">
                          {stamp.label}
                        </Label>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">{stamp.description}</p>
                    </div>
                  </div>
                );
              })}
            </RadioGroup>
          </div>

          {/* Proof of Check Upload */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold">Proof of Check * (required)</Label>
            <div 
              className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
                proofFile ? 'border-green-300 bg-green-50' : 'border-gray-300 hover:border-primary'
              }`}
            >
              {proofFile ? (
                <div className="flex items-center justify-center gap-2 text-green-700">
                  <CheckCircle className="h-5 w-5" />
                  <span className="font-medium">{proofFile.name}</span>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => setProofFile(null)}
                    className="ml-2 text-gray-500"
                  >
                    Remove
                  </Button>
                </div>
              ) : (
                <label className="cursor-pointer block">
                  <Upload className="h-8 w-8 mx-auto text-gray-400 mb-2" />
                  <p className="text-sm text-gray-600">Upload screenshot or PDF</p>
                  <p className="text-xs text-gray-400 mt-1">PNG, JPG, or PDF (max 10MB)</p>
                  <input
                    type="file"
                    accept=".png,.jpg,.jpeg,.pdf"
                    onChange={handleFileChange}
                    className="hidden"
                    data-testid="proof-upload-input"
                  />
                </label>
              )}
            </div>
          </div>

          {/* Outcome Selection */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold">Outcome *</Label>
            <Select value={outcome} onValueChange={setOutcome}>
              <SelectTrigger data-testid="outcome-select">
                <SelectValue placeholder="Select verification outcome" />
              </SelectTrigger>
              <SelectContent>
                {VERIFICATION_OUTCOMES.map((opt) => (
                  <SelectItem key={opt.id} value={opt.id}>
                    <div className="flex items-center gap-2">
                      {opt.id === 'verified' && <CheckCircle className="h-4 w-4 text-green-600" />}
                      {opt.id === 'information_present' && <AlertTriangle className="h-4 w-4 text-amber-600" />}
                      {opt.id === 'not_verified' && <XCircle className="h-4 w-4 text-red-600" />}
                      <span className={opt.color}>{opt.label}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Reference Number (Optional) */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold">Reference Number (optional)</Label>
            <Input
              placeholder="e.g., DBS cert number, Share code, NMC PIN"
              value={referenceNumber}
              onChange={(e) => setReferenceNumber(e.target.value)}
              data-testid="reference-number-input"
            />
          </div>

          {/* Notes (Optional) */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold">Notes (optional)</Label>
            <Textarea
              placeholder="Any additional notes about this verification..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              data-testid="verification-notes"
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={loading || !stampType || !proofFile || !outcome}
            data-testid="save-verification-btn"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                {uploadProgress > 0 ? `Uploading ${uploadProgress}%` : 'Saving...'}
              </>
            ) : (
              <>
                <CheckCircle className="h-4 w-4 mr-2" />
                Save &amp; Apply Stamp
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

