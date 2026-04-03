import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import { Loader2, Send, FileText, CheckSquare, Square } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

/**
 * BatchRequestModal - Modal for selecting and sending batch document requests
 * 
 * Features:
 * - Shows checklist of missing items
 * - Admin selects items to request
 * - Sends ONE consolidated email with all selected requirements
 */
export default function BatchRequestModal({
  open,
  onClose,
  employeeId,
  employeeName,
  employeeEmail,
  missingItems = [],
  onSuccess
}) {
  const { token } = useAuth();
  const [selectedItems, setSelectedItems] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [customMessage, setCustomMessage] = useState('');

  // Reset selection when modal opens
  useEffect(() => {
    if (open) {
      // Default to all items selected
      setSelectedItems(missingItems.map(item => item.id || item.key));
      setCustomMessage('');
    }
  }, [open, missingItems]);

  const handleToggleItem = (itemId) => {
    setSelectedItems(prev => 
      prev.includes(itemId) 
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId]
    );
  };

  const handleSelectAll = () => {
    if (selectedItems.length === missingItems.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(missingItems.map(item => item.id || item.key));
    }
  };

  const handleSendRequest = async () => {
    if (selectedItems.length === 0) {
      toast.error('Please select at least one item to request');
      return;
    }

    if (!employeeEmail) {
      toast.error('Employee email not available');
      return;
    }

    setIsSending(true);
    try {
      // Get full item details for selected items
      const selectedRequirements = missingItems.filter(
        item => selectedItems.includes(item.id || item.key)
      );

      // Send batch request to backend
      const response = await axios.post(
        `${API}/employees/${employeeId}/request-documents/batch`,
        {
          requirement_ids: selectedItems,
          requirements: selectedRequirements.map(r => ({
            id: r.id || r.key,
            name: r.name || r.title,
            description: r.description || r.instructions || '',
            category: r.category || 'document'
          })),
          custom_message: customMessage.trim() || null
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      if (response.data?.success) {
        toast.success(`Request sent for ${selectedItems.length} item(s)`);
        if (onSuccess) onSuccess();
        onClose();
      } else {
        throw new Error(response.data?.error || 'Failed to send request');
      }
    } catch (err) {
      console.error('Batch request error:', err);
      toast.error(err.response?.data?.detail || err.message || 'Failed to send request');
    } finally {
      setIsSending(false);
    }
  };

  const allSelected = selectedItems.length === missingItems.length;
  const noneSelected = selectedItems.length === 0;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-white sm:max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Send className="h-5 w-5 text-primary" />
            Request Missing Documents
          </DialogTitle>
          <DialogDescription>
            Select the documents you want to request from <span className="font-medium">{employeeName}</span>.
            A single email will be sent with instructions for all selected items.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          {/* Select All / None */}
          <div className="flex items-center justify-between pb-2 border-b border-gray-200">
            <button
              type="button"
              onClick={handleSelectAll}
              className="flex items-center gap-2 text-sm text-primary hover:text-primary-hover"
            >
              {allSelected ? (
                <>
                  <CheckSquare className="h-4 w-4" />
                  Deselect All
                </>
              ) : (
                <>
                  <Square className="h-4 w-4" />
                  Select All ({missingItems.length})
                </>
              )}
            </button>
            <span className="text-sm text-text-muted">
              {selectedItems.length} of {missingItems.length} selected
            </span>
          </div>

          {/* Items Checklist */}
          <div className="space-y-2">
            {missingItems.map((item) => {
              const itemId = item.id || item.key;
              const isSelected = selectedItems.includes(itemId);
              
              return (
                <label
                  key={itemId}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                    isSelected 
                      ? 'bg-primary/5 border-primary/30' 
                      : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                  }`}
                >
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => handleToggleItem(itemId)}
                    className="mt-0.5"
                  />
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium ${isSelected ? 'text-primary' : 'text-text-primary'}`}>
                      {item.name || item.title}
                    </p>
                    {(item.description || item.instructions) && (
                      <p className="text-xs text-text-muted mt-0.5 truncate">
                        {item.description || item.instructions}
                      </p>
                    )}
                    {item.category && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded mt-1 inline-block">
                        {item.category}
                      </span>
                    )}
                  </div>
                  <FileText className={`h-4 w-4 flex-shrink-0 ${isSelected ? 'text-primary' : 'text-gray-400'}`} />
                </label>
              );
            })}
          </div>

          {/* Custom Message */}
          <div className="pt-2">
            <label className="block text-sm font-medium text-text-primary mb-1">
              Additional Message (optional)
            </label>
            <textarea
              value={customMessage}
              onChange={(e) => setCustomMessage(e.target.value)}
              placeholder="Add any specific instructions or notes for the applicant..."
              rows={3}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            />
          </div>
        </div>

        <DialogFooter className="border-t border-gray-200 pt-4">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isSending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSendRequest}
            disabled={isSending || noneSelected || !employeeEmail}
            className="bg-primary hover:bg-primary-hover text-white"
          >
            {isSending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Send Request ({selectedItems.length})
              </>
            )}
          </Button>
        </DialogFooter>

        {!employeeEmail && (
          <p className="text-xs text-red-600 text-center pb-2">
            Cannot send request - employee email not available
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}
