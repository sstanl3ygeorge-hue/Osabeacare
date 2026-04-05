import { useState } from 'react';
import axios from 'axios';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { Textarea } from '../ui/textarea';
import { toast } from 'sonner';
import { Loader2, Mail, RefreshCw, Send } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Send Reminder Button
 * Sends a magic link email to the worker with their outstanding compliance items
 */
export function SendReminderButton({ employeeId, employeeName, onSuccess, variant = "outline", size = "sm" }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [customMessage, setCustomMessage] = useState('');

  const handleSend = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      const response = await axios.post(
        `${API}/workers/${employeeId}/send-reminder`,
        { custom_message: customMessage || null },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(response.data.message || 'Reminder sent successfully');
      setOpen(false);
      setCustomMessage('');
      onSuccess?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send reminder');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Button 
        variant={variant} 
        size={size} 
        onClick={() => setOpen(true)}
        data-testid={`send-reminder-${employeeId}`}
      >
        <Mail className="h-4 w-4 mr-1" />
        Send Reminder
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send Compliance Reminder</DialogTitle>
            <DialogDescription>
              Send a reminder email to {employeeName || 'this employee'} with a link to complete their outstanding compliance items.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <label className="text-sm font-medium text-gray-700 mb-2 block">
              Custom Message (Optional)
            </label>
            <Textarea
              placeholder="e.g., Please complete your outstanding items by Friday..."
              value={customMessage}
              onChange={(e) => setCustomMessage(e.target.value)}
              rows={3}
            />
            <p className="text-xs text-gray-500 mt-1">
              This message will be included in the email along with their outstanding items.
            </p>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={loading}>
              Cancel
            </Button>
            <Button onClick={handleSend} disabled={loading}>
              {loading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Send Reminder
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

/**
 * Request Renewal Button
 * Sends a renewal request email to the worker for an expiring/expired item
 */
export function RequestRenewalButton({ 
  employeeId, 
  employeeName, 
  renewalType, 
  itemName,
  trainingId = null,
  onSuccess, 
  variant = "outline", 
  size = "sm" 
}) {
  const [loading, setLoading] = useState(false);

  const handleRequest = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      const body = trainingId ? { training_id: trainingId } : {};
      
      const response = await axios.post(
        `${API}/employees/${employeeId}/request-renewal/${renewalType}`,
        body,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(response.data.message || 'Renewal request sent');
      onSuccess?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send renewal request');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button 
      variant={variant} 
      size={size} 
      onClick={handleRequest}
      disabled={loading}
      data-testid={`request-renewal-${renewalType}-${employeeId}`}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
      ) : (
        <RefreshCw className="h-4 w-4 mr-1" />
      )}
      Request Renewal
    </Button>
  );
}

/**
 * Combined action buttons for employee list/dashboard
 */
export function EmployeeActionButtons({ employee, onRefresh }) {
  const isNotReady = employee.work_readiness_3tier?.status === 'NOT_READY' || 
                     !employee.work_readiness_3tier?.status;

  if (!isNotReady) return null;

  return (
    <div className="flex gap-2">
      <SendReminderButton 
        employeeId={employee.id}
        employeeName={`${employee.first_name} ${employee.last_name}`}
        onSuccess={onRefresh}
        size="sm"
      />
    </div>
  );
}

export default SendReminderButton;
