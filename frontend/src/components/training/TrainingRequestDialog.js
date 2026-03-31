import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { Checkbox } from '../../components/ui/checkbox';
import { Input } from '../../components/ui/input';
import { toast } from 'sonner';
import { 
  Mail, Loader2, GraduationCap, Send, Clock, Calendar
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Standard training types
const TRAINING_TYPES = [
  { id: 'safeguarding_training', label: 'Safeguarding of Vulnerable Adults' },
  { id: 'moving_handling_training', label: 'Moving and Handling' },
  { id: 'medication_training', label: 'Medication Administration' },
  { id: 'infection_control_training', label: 'Infection Control and Hygiene' },
  { id: 'first_aid_training', label: 'First Aid / Basic Life Support' },
  { id: 'fire_safety_training', label: 'Fire Safety' },
  { id: 'health_safety_training', label: 'Health and Safety' },
  { id: 'food_hygiene_training', label: 'Food Hygiene' },
  { id: 'dementia_training', label: 'Understanding Dementia' },
  { id: 'mental_health_training', label: 'Mental Health Awareness' }
];

/**
 * TrainingRequestDialog - Send email request for training certificates to employee
 * 
 * Features:
 * - Select specific training types to request
 * - Include renewals option
 * - Custom message
 * - Due date setting
 */
export default function TrainingRequestDialog({ 
  employeeId, 
  employeeName,
  employeeEmail,
  open, 
  onClose,
  onComplete
}) {
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [includeRenewals, setIncludeRenewals] = useState(false);
  const [customMessage, setCustomMessage] = useState('');
  const [dueDays, setDueDays] = useState(14);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [existingRequests, setExistingRequests] = useState([]);
  const [loadingRequests, setLoadingRequests] = useState(false);
  
  const { token } = useAuth();

  // Fetch existing requests
  useEffect(() => {
    if (open && employeeId) {
      fetchExistingRequests();
    }
  }, [open, employeeId]);

  const fetchExistingRequests = async () => {
    setLoadingRequests(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/training/requests`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setExistingRequests(response.data.requests || []);
    } catch (err) {
      console.error('Failed to fetch requests:', err);
    } finally {
      setLoadingRequests(false);
    }
  };

  const toggleType = (typeId) => {
    setSelectedTypes(prev => 
      prev.includes(typeId) 
        ? prev.filter(t => t !== typeId)
        : [...prev, typeId]
    );
  };

  const selectAll = () => {
    setSelectedTypes(TRAINING_TYPES.map(t => t.id));
  };

  const clearAll = () => {
    setSelectedTypes([]);
  };

  const handleSubmit = async () => {
    if (selectedTypes.length === 0 && !includeRenewals) {
      toast.error('Please select at least one training type or include renewals');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/training/request`,
        {
          training_types: selectedTypes.length > 0 ? selectedTypes : null,
          include_renewals: includeRenewals,
          custom_message: customMessage.trim() || null,
          due_days: dueDays
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data.status === 'duplicate') {
        toast.info('A training certificate request was already sent recently');
      } else if (response.data.status === 'success') {
        toast.success(`Training certificate request sent to ${employeeEmail || 'employee'}`);
      } else if (response.data.status === 'email_failed') {
        toast.warning('Request created but email failed to send. Check employee email address.');
      }

      if (onComplete) onComplete(response.data);
      handleClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send request');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setSelectedTypes([]);
    setIncludeRenewals(false);
    setCustomMessage('');
    setDueDays(14);
    if (onClose) onClose();
  };

  // Count pending requests
  const pendingCount = existingRequests.filter(r => r.status === 'pending').length;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-white sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <Mail className="h-5 w-5 text-primary" />
            Request Training Certificates
          </DialogTitle>
          <DialogDescription>
            Send an email to {employeeName || 'the employee'} requesting training certificates.
            {employeeEmail && (
              <span className="block text-xs mt-1">
                Will be sent to: <span className="font-medium">{employeeEmail}</span>
              </span>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          {/* Pending Requests Warning */}
          {pendingCount > 0 && (
            <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
              <div className="flex items-center gap-2 text-sm text-amber-800">
                <Clock className="h-4 w-4" />
                <span>{pendingCount} pending request(s) already sent</span>
              </div>
            </div>
          )}

          {/* Training Types Selection */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Training Certificates Needed</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={selectAll}
                  className="text-xs h-7"
                >
                  Select All
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={clearAll}
                  className="text-xs h-7"
                >
                  Clear
                </Button>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-2 max-h-[200px] overflow-y-auto p-2 border rounded-lg bg-[#F8FAFA]">
              {TRAINING_TYPES.map(type => (
                <div 
                  key={type.id}
                  className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
                    selectedTypes.includes(type.id) 
                      ? 'bg-primary/10 border border-primary/20' 
                      : 'hover:bg-white'
                  }`}
                  onClick={() => toggleType(type.id)}
                >
                  <Checkbox 
                    checked={selectedTypes.includes(type.id)}
                    onCheckedChange={() => toggleType(type.id)}
                    className="h-4 w-4"
                  />
                  <span className="text-xs">{type.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Include Renewals */}
          <div className="flex items-center gap-3 p-3 bg-[#F8FAFA] rounded-lg border">
            <Checkbox 
              id="include-renewals"
              checked={includeRenewals}
              onCheckedChange={setIncludeRenewals}
            />
            <div>
              <Label htmlFor="include-renewals" className="text-sm font-medium cursor-pointer">
                Include expiring/expired training renewals
              </Label>
              <p className="text-xs text-text-muted">
                Automatically request certificates for any training due for renewal
              </p>
            </div>
          </div>

          {/* Due Date */}
          <div className="space-y-2">
            <Label className="text-sm font-medium flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Response Due In
            </Label>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                min={1}
                max={90}
                value={dueDays}
                onChange={(e) => setDueDays(parseInt(e.target.value) || 14)}
                className="w-20 rounded-lg"
              />
              <span className="text-sm text-text-muted">days</span>
            </div>
          </div>

          {/* Custom Message */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Custom Message (Optional)</Label>
            <Textarea
              value={customMessage}
              onChange={(e) => setCustomMessage(e.target.value)}
              placeholder="Add any specific instructions or notes for the employee..."
              className="rounded-lg min-h-[80px]"
              maxLength={500}
            />
            <p className="text-xs text-text-muted text-right">
              {customMessage.length}/500
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleClose} className="rounded-xl">
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || (selectedTypes.length === 0 && !includeRenewals)}
            className="bg-primary hover:bg-primary-hover text-white rounded-xl"
            data-testid="send-training-request-btn"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Send Request
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
