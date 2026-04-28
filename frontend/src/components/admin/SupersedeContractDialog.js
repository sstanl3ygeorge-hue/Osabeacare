import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { toast } from 'sonner';
import { AlertTriangle, FileX } from 'lucide-react';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_BASE_URL;

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
  onSuccess,
}) {
  const { token } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [missingFields, setMissingFields] = useState([]);
  const [renderFieldValues, setRenderFieldValues] = useState({
    hourly_rate: '',
    company_address: '',
    contract_start_date: '',
    continuous_service_date: '',
  });

  const reissuePayload = () => {
    const payload = {
      reason: reason.trim(),
      idempotency_key: buildIdempotencyKey(),
    };
    if (currentContract?.id) {
      payload.source_contract_id = currentContract.id;
    }
    return payload;
  };

  const attemptReissue = async () => {
    setMissingFields([]);
    return axios.post(
      `${API}/employees/${employeeId}/contract/reissue`,
      reissuePayload(),
      { headers: { Authorization: `Bearer ${token}` } }
    );
  };

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
      await attemptReissue();

      toast.success('New contract issued. Worker can now sign it.');
      if (onSuccess) {
        await Promise.resolve(onSuccess());
      }
      handleClose();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message =
        (typeof detail === 'string' && detail) ||
        detail?.render_issue ||
        detail?.detail ||
        'Failed to reissue contract';
      const fields = Array.isArray(detail?.missing_fields) ? detail.missing_fields : [];
      const resolved = (detail && typeof detail === 'object' && detail.resolved_fields) ? detail.resolved_fields : {};
      if (resolved && typeof resolved === 'object') {
        setRenderFieldValues((prev) => ({
          ...prev,
          hourly_rate: resolved.hourly_rate || prev.hourly_rate,
          company_address: resolved.company_address || prev.company_address,
          contract_start_date: resolved.contract_start_date || prev.contract_start_date,
          continuous_service_date: resolved.continuous_service_date || prev.continuous_service_date,
        }));
      }
      setMissingFields(fields);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveFieldsAndReissue = async () => {
    if (!reason.trim() || reason.trim().length < 20) {
      setError('Please provide a detailed reason for reissuing this contract (minimum 20 characters)');
      return;
    }
    setIsLoading(true);
    try {
      const payload = {};
      missingFields.forEach((field) => {
        const value = renderFieldValues[field];
        if (typeof value === 'string' && value.trim()) {
          payload[field] = value.trim();
        }
      });

      const stillMissing = missingFields.filter((field) => !payload[field]);
      if (stillMissing.length > 0) {
        setError(`Please complete: ${stillMissing.join(', ')}`);
        setIsLoading(false);
        return;
      }

      await axios.patch(
        `${API}/employees/${employeeId}/contract/render-fields`,
        payload,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      await attemptReissue();

      toast.success('New contract issued. Worker can now sign it.');
      if (onSuccess) {
        await Promise.resolve(onSuccess());
      }
      handleClose();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message =
        (typeof detail === 'string' && detail) ||
        detail?.render_issue ||
        detail?.detail ||
        'Failed to save fields and reissue contract';
      const fields = Array.isArray(detail?.missing_fields) ? detail.missing_fields : [];
      const resolved = (detail && typeof detail === 'object' && detail.resolved_fields) ? detail.resolved_fields : {};
      if (fields.length > 0) {
        setMissingFields(fields);
      }
      if (resolved && typeof resolved === 'object') {
        setRenderFieldValues((prev) => ({
          ...prev,
          hourly_rate: resolved.hourly_rate || prev.hourly_rate,
          company_address: resolved.company_address || prev.company_address,
          contract_start_date: resolved.contract_start_date || prev.contract_start_date,
          continuous_service_date: resolved.continuous_service_date || prev.continuous_service_date,
        }));
      }
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setReason('');
    setError('');
    setMissingFields([]);
    setRenderFieldValues({
      hourly_rate: '',
      company_address: '',
      contract_start_date: '',
      continuous_service_date: '',
    });
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

          {missingFields.length > 0 && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg space-y-3">
              <p className="text-sm font-medium text-red-700">
                Cannot reissue yet. Complete these required contract fields first.
              </p>
              <ul className="text-xs text-red-700 list-disc pl-5">
                {missingFields.map((field) => (
                  <li key={field}>{field}</li>
                ))}
              </ul>
              <div className="grid grid-cols-1 gap-3">
                {missingFields.includes('hourly_rate') && (
                  <div className="space-y-1">
                    <Label htmlFor="render-hourly-rate">Hourly rate</Label>
                    <Input
                      id="render-hourly-rate"
                      type="number"
                      min="0"
                      step="0.01"
                      value={renderFieldValues.hourly_rate}
                      onChange={(e) => setRenderFieldValues((prev) => ({ ...prev, hourly_rate: e.target.value }))}
                      placeholder="e.g. 12.50"
                    />
                  </div>
                )}
                {missingFields.includes('company_address') && (
                  <div className="space-y-1">
                    <Label htmlFor="render-company-address">Company address</Label>
                    <Textarea
                      id="render-company-address"
                      value={renderFieldValues.company_address}
                      onChange={(e) => setRenderFieldValues((prev) => ({ ...prev, company_address: e.target.value }))}
                      placeholder="Registered/business address"
                      className="min-h-[72px]"
                    />
                  </div>
                )}
                {missingFields.includes('contract_start_date') && (
                  <div className="space-y-1">
                    <Label htmlFor="render-contract-start-date">Contract start date</Label>
                    <Input
                      id="render-contract-start-date"
                      type="date"
                      value={renderFieldValues.contract_start_date}
                      onChange={(e) => setRenderFieldValues((prev) => ({ ...prev, contract_start_date: e.target.value }))}
                    />
                  </div>
                )}
                {missingFields.includes('continuous_service_date') && (
                  <div className="space-y-1">
                    <Label htmlFor="render-continuous-service-date">Continuous service date</Label>
                    <Input
                      id="render-continuous-service-date"
                      type="date"
                      value={renderFieldValues.continuous_service_date}
                      onChange={(e) => setRenderFieldValues((prev) => ({ ...prev, continuous_service_date: e.target.value }))}
                    />
                  </div>
                )}
              </div>
              <p className="text-xs text-red-700">
                Fill required fields here, then use <strong>Save fields and reissue</strong>.
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button 
            type="button"
            onClick={handleSupersede} 
            disabled={isLoading || !reason.trim()}
            className="bg-amber-600 hover:bg-amber-700 text-white"
          >
            {isLoading ? 'Processing...' : 'Reissue contract'}
          </Button>
          {missingFields.length > 0 && (
            <Button
              type="button"
              onClick={handleSaveFieldsAndReissue}
              disabled={isLoading || !reason.trim()}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              {isLoading ? 'Saving...' : 'Save fields and reissue'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

