import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { toast } from 'sonner';
import { AlertTriangle, FileX } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * SupersedeContractDialog - Reissue an existing contract for re-signature
 * 
 * CQC Compliance:
 * - Never deletes original contract
 * - Marks old contract as "superseded"
 * - Logs reason for reissuing
 * - Immediately creates a new pending-signature contract
 */
export default function SupersedeContractDialog({
  open,
  onClose,
  employeeId,
  employeeName,
  currentContract,
  onSuccess
}) {
  const { token } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  const buildIdempotencyKey = () => {
    const sourceId = currentContract?.id || 'unknown-source';
    if (typeof window !== 'undefined' && window.crypto?.randomUUID) {
      return `contract-reissue:${employeeId}:${sourceId}:${window.crypto.randomUUID()}`;
    }
    return `contract-reissue:${employeeId}:${sourceId}:${Date.now()}`;
  };

  const handleSupersede = async () => {
    if (!reason.trim() || reason.trim().length < 20) {
      setError('Please provide a detailed reason for reissuing this contract (minimum 20 characters)');
      return;
    }

    setIsLoading(true);
    try {
      const payload = {
        reason: reason.trim(),
        idempotency_key: buildIdempotencyKey(),
      };
      if (currentContract?.id) {
        payload.source_contract_id = currentContract.id;
      }
      await axios.post(
        `${API}/employees/${employeeId}/contract/reissue`,
        payload,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      toast.success('Contract reissued for re-signing. Worker can now sign the new contract.');
      if (onSuccess) onSuccess();
      handleClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reissue contract');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setReason('');
    setError('');
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-white sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2 text-amber-600">
            <AlertTriangle className="h-5 w-5" />
            Reissue contract
          </DialogTitle>
          <DialogDescription>
            Reissue the latest contract for {employeeName} so the worker can re-sign
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Warning Banner */}
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <h4 className="font-medium text-amber-800 flex items-center gap-2">
              <FileX className="h-4 w-4" />
              Audit trail notice
            </h4>
            <p className="text-sm text-amber-700 mt-1">
              The existing contract will be marked as <strong>superseded</strong>, not deleted. 
              This keeps the previous contract in the audit trail.
            </p>
          </div>

          {/* Current Contract Info */}
          {currentContract && (
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">
                <strong>Current Contract:</strong>
              </p>
              <p className="text-sm text-gray-700 mt-1">
                Status: {currentContract.status || currentContract.contract_state || 'Unknown'}
              </p>
              {currentContract.id && (
                <p className="text-sm text-gray-700">
                  Contract ID: {currentContract.id}
                </p>
              )}
            </div>
          )}

          {/* Reason for Reissuing */}
          <div className="space-y-2">
            <Label className="font-medium">
              Reason for reissuing *
            </Label>
            <Textarea
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (error) setError('');
              }}
              placeholder="Explain why this contract needs reissue (e.g., 'Rejected signature requires re-sign', 'Contract terms corrected')"
              className="min-h-[100px] rounded-lg"
            />
            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}
            <p className="text-xs text-gray-500">
              Minimum 20 characters. This will be logged in the audit trail.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button 
            onClick={handleSupersede} 
            disabled={isLoading || !reason.trim()}
            className="bg-amber-600 hover:bg-amber-700 text-white"
          >
            {isLoading ? 'Processing...' : 'Reissue contract'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
