import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { toast } from 'sonner';
import { AlertTriangle, FileX, Send } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * SupersedeContractDialog - Supersede an existing contract and request new signature
 * 
 * CQC Compliance:
 * - Never deletes original contract
 * - Marks old contract as "superseded"
 * - Logs reason for superseding
 * - Sends new contract to worker for signature
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
  const [sendNewContract, setSendNewContract] = useState(true);
  const [error, setError] = useState('');

  const handleSupersede = async () => {
    if (!reason.trim() || reason.trim().length < 20) {
      setError('Please provide a detailed reason for superseding this contract (minimum 20 characters)');
      return;
    }

    setIsLoading(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/contract/supersede`,
        {
          reason: reason.trim(),
          send_new_contract: sendNewContract
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(
        sendNewContract 
          ? 'Contract superseded. New contract sent to worker for signature.'
          : 'Contract superseded. Worker will need to sign a new contract.'
      );
      if (onSuccess) onSuccess();
      handleClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to replace contract');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setReason('');
    setError('');
    setSendNewContract(true);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-white sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2 text-amber-600">
            <AlertTriangle className="h-5 w-5" />
            Replace contract
          </DialogTitle>
          <DialogDescription>
            Replace the existing contract for {employeeName}
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
                Signed: {currentContract.completed_at 
                  ? new Date(currentContract.completed_at).toLocaleDateString('en-GB') 
                  : 'Unknown'}
              </p>
              {currentContract.completion_mode && (
                <p className="text-sm text-gray-700">
                  Method: {currentContract.completion_mode === 'admin_assisted' 
                    ? 'Admin-Assisted (Non-Compliant)' 
                    : currentContract.completion_mode}
                </p>
              )}
            </div>
          )}

          {/* Reason for Superseding */}
          <div className="space-y-2">
            <Label className="font-medium">
              Reason for replacing *
            </Label>
            <Textarea
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (error) setError('');
              }}
              placeholder="Explain why this contract needs to be replaced (e.g., 'Original contract was signed by admin, not worker', 'Contract terms need updating')"
              className="min-h-[100px] rounded-lg"
            />
            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}
            <p className="text-xs text-gray-500">
              Minimum 20 characters. This will be logged in the audit trail.
            </p>
          </div>

          {/* Send New Contract Option */}
          <div className="space-y-2">
            <label className="flex items-center gap-3 cursor-pointer p-3 bg-green-50 border border-green-200 rounded-lg">
              <input
                type="checkbox"
                checked={sendNewContract}
                onChange={(e) => setSendNewContract(e.target.checked)}
                className="rounded border-gray-300"
              />
              <div className="flex-1">
                <span className="text-sm font-medium text-green-800 flex items-center gap-2">
                  <Send className="h-4 w-4" />
                  Send new contract to worker for signature
                </span>
                <p className="text-xs text-green-700 mt-0.5">
                  Worker will receive a notification to sign the new contract
                </p>
              </div>
            </label>
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
            {isLoading ? 'Processing...' : 'Replace contract'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
