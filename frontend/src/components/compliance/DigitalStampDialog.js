import { useState } from 'react';
import axios from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import { 
  Stamp, CheckCircle, Eye, Globe, AlertTriangle, 
  Loader2, FileText, Download
} from 'lucide-react';
import { toast } from 'sonner';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

const STAMP_TYPES = [
  { 
    value: 'original_seen', 
    label: 'Original Document Seen', 
    icon: Eye,
    color: 'green', 
    description: 'I have physically seen the original document',
    badge: 'bg-green-100 text-green-700 border-green-200'
  },
  { 
    value: 'copy_verified', 
    label: 'Copy Verified with Original', 
    icon: CheckCircle,
    color: 'blue', 
    description: 'I have compared this copy with the original document',
    badge: 'bg-blue-100 text-blue-700 border-blue-200'
  },
  { 
    value: 'online_check', 
    label: 'Online Check Completed', 
    icon: Globe,
    color: 'purple', 
    description: 'Verified via official online service (Share Code, DBS Update Service, etc.)',
    badge: 'bg-purple-100 text-purple-700 border-purple-200'
  }
];

export default function DigitalStampDialog({ 
  open, 
  onOpenChange, 
  document, 
  onSuccess,
  employeeName 
}) {
  const [stampType, setStampType] = useState('original_seen');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleApplyStamp = async () => {
    if (!document?.id) {
      toast.error('No document selected');
      return;
    }

    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API}/employee-documents/${document.id}/verify-with-digital-stamp`,
        { stamp_type: stampType, notes: notes.trim() || null },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data.success) {
        const stampLabel = STAMP_TYPES.find(s => s.value === stampType)?.label;
        
        if (response.data.has_visual_stamp) {
          toast.success(
            <div>
              <p className="font-medium">Document verified with digital stamp</p>
              <p className="text-xs text-gray-500 mt-1">
                Visual stamp embedded. Verification ID: {response.data.verification_id}
              </p>
            </div>
          );
        } else {
          toast.success(`Document verified: ${stampLabel}`);
        }
        
        onOpenChange(false);
        if (onSuccess) onSuccess(response.data);
      }
    } catch (error) {
      console.error('Failed to apply stamp:', error);
      toast.error(error.response?.data?.detail || 'Failed to apply digital stamp');
    } finally {
      setSubmitting(false);
    }
  };

  const selectedStamp = STAMP_TYPES.find(s => s.value === stampType);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Stamp className="h-5 w-5 text-primary" />
            Verify Document with Digital Stamp
          </DialogTitle>
          <DialogDescription>
            This will add a visible, permanent verification stamp to the document that cannot be removed.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          {/* Document Info */}
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div className="flex items-center gap-3">
              <FileText className="h-8 w-8 text-gray-400" />
              <div>
                <p className="font-medium text-sm text-gray-900">
                  {document?.file_name || document?.original_filename || 'Document'}
                </p>
                <p className="text-xs text-gray-500">
                  {document?.requirement_id?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  {employeeName && ` • ${employeeName}`}
                </p>
              </div>
            </div>
          </div>

          {/* Stamp Type Selection */}
          <div>
            <Label className="mb-3 block">Select Verification Type</Label>
            <div className="space-y-2">
              {STAMP_TYPES.map(stamp => {
                const Icon = stamp.icon;
                const isSelected = stampType === stamp.value;
                
                return (
                  <label
                    key={stamp.value}
                    className={`flex items-start gap-3 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                      isSelected 
                        ? `border-${stamp.color}-500 bg-${stamp.color}-50` 
                        : 'border-gray-200 hover:border-gray-300 bg-white'
                    }`}
                    data-testid={`stamp-option-${stamp.value}`}
                  >
                    <input
                      type="radio"
                      name="stampType"
                      value={stamp.value}
                      checked={isSelected}
                      onChange={(e) => setStampType(e.target.value)}
                      className="mt-1"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Icon className={`h-4 w-4 text-${stamp.color}-600`} />
                        <span className={`font-medium ${isSelected ? `text-${stamp.color}-700` : 'text-gray-900'}`}>
                          {stamp.label}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">{stamp.description}</p>
                    </div>
                    {isSelected && (
                      <Badge className={stamp.badge}>
                        Selected
                      </Badge>
                    )}
                  </label>
                );
              })}
            </div>
          </div>

          {/* Notes */}
          <div>
            <Label htmlFor="stamp-notes">Additional Notes (optional)</Label>
            <Textarea
              id="stamp-notes"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g., Verified in person at office, Share Code checked on gov.uk..."
              className="mt-1.5"
              data-testid="stamp-notes-input"
            />
          </div>

          {/* Warning */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-amber-800">This action is permanent</p>
              <p className="text-xs text-amber-700 mt-0.5">
                Once stamped, the verification mark is embedded into the document and cannot be removed. 
                The stamp will be visible when anyone views or downloads this document.
              </p>
            </div>
          </div>

          {/* Preview */}
          {selectedStamp && (
            <div className="p-3 bg-white rounded-lg border border-gray-200">
              <p className="text-xs text-gray-500 mb-2">Stamp Preview:</p>
              <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border ${selectedStamp.badge}`}>
                <CheckCircle className="h-4 w-4" />
                <span className="font-medium text-sm">{selectedStamp.label.toUpperCase()}</span>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button 
            variant="outline" 
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleApplyStamp} 
            disabled={submitting}
            className="gap-2"
            data-testid="apply-digital-stamp-btn"
          >
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Stamp className="h-4 w-4" />
            )}
            Apply Digital Stamp
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

