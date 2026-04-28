import { useState } from 'react';
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
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';
import { toast } from 'sonner';
import {
  Eye,
  Download,
  FileCheck,
  FileQuestion,
  Globe,
  Loader2,
  Stamp,
  Trash2
} from 'lucide-react';
import {
import { API_BASE_URL, API_ROOT_URL } from './';
  downloadBlobUrl,
  fetchProtectedFileBlob,
  revokeBlobUrlLater,
} from '../../lib/protectedFiles';

const API = API_BASE_URL;

/**
 * VerificationStampDialog - Apply verification stamps to evidence documents
 * 
 * This is SEPARATE from:
 * - Evidence Review (accept/reject/error) - file quality check
 * - Record Check - formal compliance verification
 * 
 * Verification stamps indicate HOW the document was verified:
 * - Original seen: Physical original document personally verified
 * - Copy verified: Copy verified against original/trusted source
 * - Not verified: Document not yet physically verified
 * - Online check: Verified via official online service
 */
export default function VerificationStampDialog({
  isOpen,
  onClose,
  file,
  employeeId,
  requirementKey,
  requirementLabel,
  onStampApplied
}) {
  const { token } = useAuth();
  const [selectedStamp, setSelectedStamp] = useState('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRemoving, setIsRemoving] = useState(false);

  // Verification stamp options - Osabea Healthcare Solutions branded
  const STAMP_OPTIONS = [
    {
      value: 'document_verified',
      label: 'Document Verified',
      description: 'General document verification (digital docs, online checks)',
      icon: FileCheck,
      iconColor: 'text-sky-600',
      badgeColor: 'bg-sky-100 text-sky-800 border-sky-200'
    },
    {
      value: 'original_seen',
      label: 'Original Document Seen',
      description: 'Admin physically saw and verified the ORIGINAL document',
      icon: Eye,
      iconColor: 'text-purple-600',
      badgeColor: 'bg-purple-100 text-purple-800 border-purple-200'
    },
    {
      value: 'copy_verified',
      label: 'Copy Verified',
      description: 'Verifying a photocopy or scanned copy of an original',
      icon: FileCheck,
      iconColor: 'text-amber-600',
      badgeColor: 'bg-amber-100 text-amber-800 border-amber-200'
    },
    {
      value: 'not_verified',
      label: 'Not Verified',
      description: 'Document has not been physically verified yet',
      icon: FileQuestion,
      iconColor: 'text-gray-500',
      badgeColor: 'bg-gray-100 text-gray-600 border-gray-200'
    }
  ];

  const handleSubmit = async () => {
    if (!selectedStamp) {
      toast.error('Please select a verification stamp');
      return;
    }

    setIsSubmitting(true);
    try {
      // Use file_id (from evidence_files array) or id (from document response)
      const docId = file.file_id || file.id;
      if (!docId) {
        toast.error('Document ID not found');
        return;
      }
      
      await axios.post(
        `${API}/employee-documents/${docId}/verification-stamp`,
        {
          stamp_type: selectedStamp,
          notes: notes.trim() || null
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      const stampOption = STAMP_OPTIONS.find(s => s.value === selectedStamp);
      toast.success(`Verification stamp applied: ${stampOption?.label}`);
      
      if (onStampApplied) {
        onStampApplied(selectedStamp);
      }
      
      handleClose();
    } catch (err) {
      console.error('Error applying verification stamp:', err);
      toast.error(err.response?.data?.detail || 'Failed to apply verification stamp');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setSelectedStamp('');
    setNotes('');
    onClose();
  };

  // Remove existing stamp
  const handleRemoveStamp = async () => {
    const docId = file.file_id || file.id;
    if (!docId) {
      toast.error('Document ID not found');
      return;
    }

    setIsRemoving(true);
    try {
      await axios.delete(
        `${API}/employee-documents/${docId}/verification-stamp`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      toast.success('Verification stamp removed');
      
      if (onStampApplied) {
        onStampApplied(null); // Signal removal
      }
      
      handleClose();
    } catch (err) {
      console.error('Error removing verification stamp:', err);
      toast.error(err.response?.data?.detail || 'Failed to remove verification stamp');
    } finally {
      setIsRemoving(false);
    }
  };

  const handlePreview = async () => {
    if (!file?.file_url) return;
    try {
      const { blobUrl } = await fetchProtectedFileBlob(file.file_url, token);
      downloadBlobUrl(blobUrl, file?.original_filename || file?.document_type_name || 'document');
      revokeBlobUrlLater(blobUrl, 1000);
      toast.info('In-app preview is not available in this dialog. File downloaded for review.');
    } catch (err) {
      toast.error('Failed to download document');
    }
  };

  if (!isOpen || !file) return null;

  // Check if stamp already applied
  const existingStamp = file.verification_stamp;
  const existingStampOption = existingStamp ? STAMP_OPTIONS.find(s => s.value === existingStamp) : null;

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Stamp className="h-5 w-5 text-indigo-600" />
            Document Verification Stamp
          </DialogTitle>
          <DialogDescription>
            Record how this document was verified for audit purposes.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* File Info */}
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {file.original_filename || file.document_type_name || 'Document'}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {requirementLabel} • {file.status}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handlePreview}
                className="text-xs"
                data-testid="preview-document-btn"
              >
                <Download className="h-3 w-3 mr-1" />
                Download
              </Button>
            </div>
            
            {/* Show existing stamp if any */}
            {existingStamp && existingStampOption && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">Current stamp:</span>
                  <Badge className={`text-xs ${existingStampOption.badgeColor}`}>
                    {existingStampOption.label}
                  </Badge>
                </div>
                {file.verification_stamp_by_name && (
                  <p className="text-xs text-gray-500 mt-1">
                    Applied by {file.verification_stamp_by_name}
                    {file.verification_stamp_at && ` on ${new Date(file.verification_stamp_at).toLocaleDateString()}`}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Stamp Selection */}
          <div>
            <Label className="text-sm font-medium mb-3 block">
              Select Verification Stamp {existingStamp && <span className="text-gray-500 font-normal">(will replace current)</span>}
            </Label>
            
            <RadioGroup
              value={selectedStamp}
              onValueChange={setSelectedStamp}
              className="space-y-3"
            >
              {STAMP_OPTIONS.map((option) => {
                const Icon = option.icon;
                const isSelected = selectedStamp === option.value;
                
                return (
                  <div
                    key={option.value}
                    className={`
                      relative flex items-start p-3 rounded-lg border-2 cursor-pointer transition-all
                      ${isSelected 
                        ? 'border-indigo-500 bg-indigo-50' 
                        : 'border-gray-200 hover:border-gray-300 bg-white'
                      }
                    `}
                    onClick={() => setSelectedStamp(option.value)}
                    data-testid={`stamp-option-${option.value}`}
                  >
                    <RadioGroupItem
                      value={option.value}
                      id={option.value}
                      className="mt-1"
                    />
                    <div className="ml-3 flex-1">
                      <div className="flex items-center gap-2">
                        <Icon className={`h-4 w-4 ${option.iconColor}`} />
                        <Label
                          htmlFor={option.value}
                          className="text-sm font-medium cursor-pointer"
                        >
                          {option.label}
                        </Label>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {option.description}
                      </p>
                    </div>
                    <Badge className={`text-[10px] ${option.badgeColor}`}>
                      {option.value === 'document_verified' ? 'DOCUMENT VERIFIED' :
                       option.value === 'original_seen' ? 'ORIGINAL SEEN' :
                       option.value === 'copy_verified' ? 'COPY VERIFIED' : 'NOT VERIFIED'}
                    </Badge>
                  </div>
                );
              })}
            </RadioGroup>
          </div>

          {/* Notes */}
          <div>
            <Label className="text-sm font-medium mb-2 block">
              Notes (optional)
            </Label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any verification notes for the audit trail..."
              className="min-h-[80px]"
              data-testid="stamp-notes-input"
            />
          </div>
        </div>

        <DialogFooter className="flex gap-2">
          {/* Remove Stamp button - only show if stamp exists */}
          {existingStamp && (
            <Button
              variant="outline"
              onClick={handleRemoveStamp}
              disabled={isSubmitting || isRemoving}
              className="text-red-600 border-red-200 hover:bg-red-50 mr-auto"
              data-testid="remove-stamp-btn"
            >
              {isRemoving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Removing...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Remove Stamp
                </>
              )}
            </Button>
          )}
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isSubmitting || isRemoving}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || isRemoving || !selectedStamp}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
            data-testid="apply-stamp-btn"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                {existingStamp ? 'Updating...' : 'Applying...'}
              </>
            ) : (
              <>
                <Stamp className="h-4 w-4 mr-2" />
                {existingStamp ? 'Update Stamp' : 'Apply Stamp'}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

