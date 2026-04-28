import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Switch } from '../../components/ui/switch';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';
import { 
import { API_BASE_URL, API_ROOT_URL } from './';
  Calendar, Clock, Play, Pause, Plus, Loader2, 
  AlertTriangle, CheckCircle, FileText, GraduationCap,
  History, Edit, Trash2, RefreshCw, Mail
} from 'lucide-react';

const API = API_BASE_URL;

export default function ScheduledRequestsPage() {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState(null);
  const [historyDialogOpen, setHistoryDialogOpen] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState(null);
  const [runHistory, setRunHistory] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRunning, setIsRunning] = useState({});
  
  const [isQuickSetupRunning, setIsQuickSetupRunning] = useState(false);
  const [expiringSummary, setExpiringSummary] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    target_type: 'documents',
    days_before_expiry: 60,
    due_days: 14,
    custom_message: '',
    is_enabled: true
  });
  
  const { token } = useAuth();

  useEffect(() => {
    fetchSchedules();
    fetchExpiringSummary();
  }, [token]);

  const fetchSchedules = async () => {
    try {
      const response = await axios.get(`${API}/bulk/schedules?include_disabled=true`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSchedules(response.data.schedules || []);
    } catch (error) {
      toast.error('Failed to fetch schedules');
    } finally {
      setLoading(false);
    }
  };

  const fetchExpiringSummary = async () => {
    try {
      const response = await axios.get(`${API}/training/expiring-summary?days=60`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setExpiringSummary(response.data);
    } catch (error) {
      console.error('Failed to fetch expiring summary:', error);
    }
  };

  const handleQuickSetupTrainingReminders = async () => {
    setIsQuickSetupRunning(true);
    try {
      const response = await axios.post(`${API}/bulk/schedules/quick-setup-training-reminders`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.data.status === 'already_configured') {
        toast.info('Training renewal reminders are already configured');
      } else {
        const created = response.data.schedules.filter(s => s.status === 'created').length;
        toast.success(`Created ${created} training reminder schedule(s)`);
      }
      
      fetchSchedules();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to set up training reminders');
    } finally {
      setIsQuickSetupRunning(false);
    }
  };

  const handleCreateSchedule = async () => {
    if (!formData.name.trim()) {
      toast.error('Schedule name is required');
      return;
    }
    
    setIsSubmitting(true);
    try {
      const payload = {
        name: formData.name,
        description: formData.description || null,
        is_enabled: formData.is_enabled,
        target_type: formData.target_type,
        trigger_type: 'days_before_expiry',
        days_before_expiry: formData.days_before_expiry,
        target_rules: {
          employee_statuses: ['onboarding', 'active'],
          document_types: formData.target_type === 'documents' ? [] : [],
          training_codes: formData.target_type === 'training' ? [] : [],
          only_expiring: true
        },
        request_payload: {
          due_days: formData.due_days,
          custom_message: formData.custom_message || null
        }
      };
      
      if (editingSchedule) {
        await axios.put(`${API}/bulk/schedules/${editingSchedule.id}`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        toast.success('Schedule updated');
      } else {
        await axios.post(`${API}/bulk/schedules`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        toast.success('Schedule created');
      }
      
      setCreateDialogOpen(false);
      resetForm();
      fetchSchedules();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save schedule');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleEnabled = async (schedule) => {
    try {
      const endpoint = schedule.is_enabled ? 'disable' : 'enable';
      await axios.post(`${API}/bulk/schedules/${schedule.id}/${endpoint}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(`Schedule ${schedule.is_enabled ? 'disabled' : 'enabled'}`);
      fetchSchedules();
    } catch (error) {
      toast.error('Failed to update schedule');
    }
  };

  const handleRunNow = async (schedule) => {
    setIsRunning(prev => ({ ...prev, [schedule.id]: true }));
    try {
      const response = await axios.post(`${API}/bulk/schedules/${schedule.id}/run-now`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const result = response.data;
      if (result.created_requests > 0) {
        toast.success(`Created ${result.created_requests} document requests`);
      } else if (result.skipped_ineligible > 0) {
        toast.info(`No items due for renewal (${result.skipped_ineligible} employees checked)`);
      } else if (result.skipped_duplicates > 0) {
        toast.info(`${result.skipped_duplicates} requests already pending`);
      } else {
        toast.info('Run complete - no new requests needed');
      }
      
      fetchSchedules();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to run schedule');
    } finally {
      setIsRunning(prev => ({ ...prev, [schedule.id]: false }));
    }
  };

  const handleViewHistory = async (schedule) => {
    setSelectedSchedule(schedule);
    setHistoryDialogOpen(true);
    
    try {
      const response = await axios.get(`${API}/bulk/schedules/${schedule.id}/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRunHistory(response.data.runs || []);
    } catch (error) {
      toast.error('Failed to fetch run history');
    }
  };

  const handleEdit = (schedule) => {
    setEditingSchedule(schedule);
    setFormData({
      name: schedule.name,
      description: schedule.description || '',
      target_type: schedule.target_type,
      days_before_expiry: schedule.days_before_expiry,
      due_days: schedule.request_payload?.due_days || 14,
      custom_message: schedule.request_payload?.custom_message || '',
      is_enabled: schedule.is_enabled
    });
    setCreateDialogOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      target_type: 'documents',
      days_before_expiry: 60,
      due_days: 14,
      custom_message: '',
      is_enabled: true
    });
    setEditingSchedule(null);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { 
      day: '2-digit', 
      month: 'short', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="scheduled-requests-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
            Scheduled Requests
          </h1>
          <p className="text-text-muted mt-1">
            Automate renewal reminders for documents and training
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            onClick={handleQuickSetupTrainingReminders}
            disabled={isQuickSetupRunning}
            variant="outline"
            className="rounded-xl border-purple-200 text-purple-700 hover:bg-purple-50"
            data-testid="quick-setup-training-btn"
          >
            {isQuickSetupRunning ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <GraduationCap className="h-4 w-4 mr-2" />
            )}
            Quick Setup Training Reminders
          </Button>
          <Button 
            onClick={() => { resetForm(); setCreateDialogOpen(true); }}
            className="bg-primary hover:bg-primary-hover text-white rounded-xl"
            data-testid="create-schedule-btn"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Schedule
          </Button>
        </div>
      </div>

      {/* Expiring Training Alert */}
      {expiringSummary && expiringSummary.total > 0 && (
        <Card className="border-amber-200 bg-amber-50/50 shadow-sm">
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center">
                  <AlertTriangle className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <h3 className="font-heading font-semibold text-amber-800">
                    Training Certificates Expiring Soon
                  </h3>
                  <p className="text-sm text-amber-700">
                    {expiringSummary.total} training record(s) expiring in the next 60 days across {expiringSummary.total_employees || 'multiple'} employee(s)
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4 text-sm">
                {expiringSummary.critical?.count > 0 && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 bg-red-100 text-red-700 rounded-lg">
                    <AlertTriangle className="h-4 w-4" />
                    <span className="font-medium">{expiringSummary.critical.count}</span>
                    <span>within 7 days</span>
                  </div>
                )}
                {expiringSummary.warning?.count > 0 && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-100 text-amber-700 rounded-lg">
                    <Clock className="h-4 w-4" />
                    <span className="font-medium">{expiringSummary.warning.count}</span>
                    <span>within 30 days</span>
                  </div>
                )}
                {expiringSummary.upcoming?.count > 0 && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-100 text-blue-700 rounded-lg">
                    <Calendar className="h-4 w-4" />
                    <span className="font-medium">{expiringSummary.upcoming.count}</span>
                    <span>within 60 days</span>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Schedule Cards */}
      {schedules.length === 0 ? (
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="py-12 text-center">
            <Calendar className="h-12 w-12 mx-auto text-gray-300 mb-4" />
            <h3 className="font-heading text-lg font-semibold text-text-primary mb-2">
              No Scheduled Requests
            </h3>
            <p className="text-text-muted mb-4 max-w-md mx-auto">
              Create a schedule to automatically send renewal reminders before documents or training expire.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Button 
                onClick={handleQuickSetupTrainingReminders}
                disabled={isQuickSetupRunning}
                className="bg-purple-600 hover:bg-purple-700 text-white rounded-xl"
                data-testid="empty-quick-setup-btn"
              >
                {isQuickSetupRunning ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <GraduationCap className="h-4 w-4 mr-2" />
                )}
                Quick Setup Training Reminders
              </Button>
              <span className="text-text-muted text-sm">or</span>
              <Button 
                onClick={() => { resetForm(); setCreateDialogOpen(true); }}
                variant="outline"
                className="rounded-xl"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create Custom Schedule
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {schedules.map(schedule => (
            <Card 
              key={schedule.id} 
              className={`border-[#E4E8EB] shadow-sm ${!schedule.is_enabled ? 'opacity-60' : ''}`}
              data-testid={`schedule-card-${schedule.id}`}
            >
              <CardContent className="p-6">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  {/* Schedule Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                        schedule.target_type === 'documents' ? 'bg-blue-100' : 'bg-purple-100'
                      }`}>
                        {schedule.target_type === 'documents' ? (
                          <FileText className="h-5 w-5 text-blue-600" />
                        ) : (
                          <GraduationCap className="h-5 w-5 text-purple-600" />
                        )}
                      </div>
                      <div>
                        <h3 className="font-heading font-semibold text-text-primary">
                          {schedule.name}
                        </h3>
                        <div className="flex items-center gap-2">
                          <Badge variant={schedule.is_enabled ? 'default' : 'secondary'} className="text-xs">
                            {schedule.is_enabled ? 'Active' : 'Disabled'}
                          </Badge>
                          <span className="text-sm text-text-muted">
                            {schedule.days_before_expiry} days before expiry
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    {schedule.description && (
                      <p className="text-sm text-text-muted mb-2 ml-13">
                        {schedule.description}
                      </p>
                    )}
                    
                    {/* Last Run Info */}
                    <div className="flex flex-wrap items-center gap-4 text-sm text-text-muted ml-13">
                      <div className="flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5" />
                        <span>Last run: {formatDate(schedule.last_run_at)}</span>
                      </div>
                      {schedule.last_run_result && (
                        <>
                          <div className="flex items-center gap-1">
                            <Mail className="h-3.5 w-3.5 text-green-500" />
                            <span>{schedule.last_run_result.created_requests} sent</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <CheckCircle className="h-3.5 w-3.5 text-gray-400" />
                            <span>{schedule.last_run_result.skipped_duplicates} skipped</span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleViewHistory(schedule)}
                      className="rounded-lg"
                      data-testid={`view-history-${schedule.id}`}
                    >
                      <History className="h-4 w-4 mr-1.5" />
                      History
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRunNow(schedule)}
                      disabled={isRunning[schedule.id]}
                      className="rounded-lg"
                      data-testid={`run-now-${schedule.id}`}
                    >
                      {isRunning[schedule.id] ? (
                        <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                      ) : (
                        <Play className="h-4 w-4 mr-1.5" />
                      )}
                      Run Now
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEdit(schedule)}
                      className="rounded-lg"
                      data-testid={`edit-schedule-${schedule.id}`}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Switch
                      checked={schedule.is_enabled}
                      onCheckedChange={() => handleToggleEnabled(schedule)}
                      data-testid={`toggle-schedule-${schedule.id}`}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); setCreateDialogOpen(open); }}>
        <DialogContent className="bg-white sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" />
              {editingSchedule ? 'Edit Schedule' : 'Create Schedule'}
            </DialogTitle>
            <DialogDescription>
              {editingSchedule ? 'Update the scheduled request settings.' : 'Set up automatic renewal reminders for your staff.'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Name */}
            <div className="space-y-2">
              <Label>Schedule Name *</Label>
              <Input
                placeholder="e.g., DBS Renewal Reminders"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="rounded-xl"
                data-testid="schedule-name-input"
              />
            </div>
            
            {/* Description */}
            <div className="space-y-2">
              <Label>Description</Label>
              <Input
                placeholder="Optional description..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="rounded-xl"
              />
            </div>
            
            {/* Target Type */}
            <div className="space-y-2">
              <Label>What to Monitor</Label>
              <Select 
                value={formData.target_type} 
                onValueChange={(v) => setFormData({ ...formData, target_type: v })}
              >
                <SelectTrigger className="rounded-xl" data-testid="target-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="documents">Documents (DBS, Right to Work, ID)</SelectItem>
                  <SelectItem value="training">Training Certificates</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {/* Days Before Expiry */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Send Reminder</Label>
                <Select 
                  value={String(formData.days_before_expiry)} 
                  onValueChange={(v) => setFormData({ ...formData, days_before_expiry: Number(v) })}
                >
                  <SelectTrigger className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="30">30 days before</SelectItem>
                    <SelectItem value="60">60 days before</SelectItem>
                    <SelectItem value="90">90 days before</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Due in (days)</Label>
                <Select 
                  value={String(formData.due_days)} 
                  onValueChange={(v) => setFormData({ ...formData, due_days: Number(v) })}
                >
                  <SelectTrigger className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="7">7 days</SelectItem>
                    <SelectItem value="14">14 days</SelectItem>
                    <SelectItem value="21">21 days</SelectItem>
                    <SelectItem value="30">30 days</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            {/* Custom Message */}
            <div className="space-y-2">
              <Label>Custom Message (optional)</Label>
              <Textarea
                placeholder="Add a personal note to include in the request email..."
                value={formData.custom_message}
                onChange={(e) => setFormData({ ...formData, custom_message: e.target.value })}
                className="rounded-xl resize-none"
                rows={3}
              />
            </div>
            
            {/* Enabled Toggle */}
            <div className="flex items-center justify-between p-3 bg-[#F8FAFA] rounded-xl">
              <div>
                <p className="font-medium text-text-primary">Enable Schedule</p>
                <p className="text-sm text-text-muted">Run automatically every hour</p>
              </div>
              <Switch
                checked={formData.is_enabled}
                onCheckedChange={(checked) => setFormData({ ...formData, is_enabled: checked })}
              />
            </div>
          </div>
          
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => { resetForm(); setCreateDialogOpen(false); }} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              onClick={handleCreateSchedule} 
              disabled={isSubmitting || !formData.name.trim()}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
              data-testid="save-schedule-btn"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                editingSchedule ? 'Update Schedule' : 'Create Schedule'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Run History Dialog */}
      <Dialog open={historyDialogOpen} onOpenChange={setHistoryDialogOpen}>
        <DialogContent className="bg-white sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <History className="h-5 w-5 text-primary" />
              Run History: {selectedSchedule?.name}
            </DialogTitle>
          </DialogHeader>
          
          <div className="max-h-96 overflow-y-auto">
            {runHistory.length === 0 ? (
              <div className="py-8 text-center text-text-muted">
                <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No run history yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {runHistory.map((run, idx) => (
                  <div 
                    key={run.id} 
                    className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Badge variant={run.status === 'completed' ? 'default' : 'destructive'} className="text-xs">
                          {run.status}
                        </Badge>
                        <span className="text-sm text-text-muted">
                          {run.triggered_by === 'manual' ? 'Manual run' : 'Scheduled'}
                        </span>
                      </div>
                      <span className="text-sm text-text-muted">
                        {formatDate(run.started_at)}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-4 gap-3 text-center">
                      <div className="p-2 bg-white rounded-lg">
                        <p className="text-lg font-semibold text-text-primary">{run.matched_employees}</p>
                        <p className="text-xs text-text-muted">Employees</p>
                      </div>
                      <div className="p-2 bg-green-50 rounded-lg">
                        <p className="text-lg font-semibold text-green-700">{run.created_requests}</p>
                        <p className="text-xs text-green-600">Sent</p>
                      </div>
                      <div className="p-2 bg-gray-50 rounded-lg">
                        <p className="text-lg font-semibold text-gray-700">{run.skipped_duplicates}</p>
                        <p className="text-xs text-gray-600">Duplicates</p>
                      </div>
                      <div className="p-2 bg-amber-50 rounded-lg">
                        <p className="text-lg font-semibold text-amber-700">{run.skipped_ineligible}</p>
                        <p className="text-xs text-amber-600">Not Due</p>
                      </div>
                    </div>
                    
                    {run.errors > 0 && (
                      <div className="mt-2 p-2 bg-red-50 rounded-lg">
                        <p className="text-sm text-red-600">
                          <AlertTriangle className="h-3.5 w-3.5 inline mr-1" />
                          {run.errors} error{run.errors !== 1 ? 's' : ''}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setHistoryDialogOpen(false)} className="rounded-xl">
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

