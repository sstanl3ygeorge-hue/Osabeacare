import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Checkbox } from '../ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { toast } from 'sonner';
import { 
  Plus, Edit2, AlertTriangle, CheckCircle, XCircle,
  Clock, Loader2, ClipboardCheck, Calendar, User, RefreshCw, Eye
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';
import { cn } from '../../lib/utils';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_BASE_URL;

// Spot check types
const SPOT_CHECK_TYPES = [
  { value: "observation", label: "Direct Observation" },
  { value: "document_review", label: "Document Review" },
  { value: "competency_check", label: "Competency Check" },
  { value: "medication_check", label: "Medication Check" }
];

// Areas that can be observed
const SPOT_CHECK_AREAS = [
  { value: "moving_handling", label: "Moving & Handling" },
  { value: "medication", label: "Medication Administration" },
  { value: "record_keeping", label: "Record Keeping" },
  { value: "communication", label: "Communication" },
  { value: "infection_control", label: "Infection Control" },
  { value: "dignity_respect", label: "Dignity & Respect" },
  { value: "safeguarding", label: "Safeguarding" }
];

// Outcome options
const OUTCOME_OPTIONS = [
  { value: "pass", label: "Pass", color: "bg-green-100 text-green-700 border-green-200", icon: CheckCircle },
  { value: "needs_improvement", label: "Needs Improvement", color: "bg-amber-100 text-amber-700 border-amber-200", icon: AlertTriangle },
  { value: "fail", label: "Fail", color: "bg-red-100 text-red-700 border-red-200", icon: XCircle }
];

/**
 * SpotChecksPanel - Full spot check/observation management
 * 
 * Features:
 * - List all spot checks with date, area, outcome
 * - Add new spot check
 * - Edit existing spot check
 * - Highlight failed or needs improvement
 * - Alert when follow-up is due
 */
export default function SpotChecksPanel({ employeeId, employeeName, onRefresh }) {
  const { token, user } = useAuth();
  const [spotChecks, setSpotChecks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  
  // Dialog states
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [recordOutcomeDialogOpen, setRecordOutcomeDialogOpen] = useState(false);
  const [selectedCheck, setSelectedCheck] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    type: '',
    area: '',
    outcome: '',
    notes: '',
    follow_up_required: false,
    follow_up_date: ''
  });
  
  // Schedule form state
  const [scheduleData, setScheduleData] = useState({
    type: '',
    area: '',
    scheduled_date: '',
    notes: ''
  });
  
  // Record outcome form state
  const [outcomeData, setOutcomeData] = useState({
    outcome: '',
    notes: '',
    follow_up_required: false,
    follow_up_date: ''
  });

  useEffect(() => {
    fetchSpotChecks();
  }, [employeeId]);

  const fetchSpotChecks = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/employees/${employeeId}/spot-checks`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSpotChecks(response.data.spot_checks || []);
    } catch (error) {
      console.error('Failed to fetch spot checks:', error);
      toast.error('Failed to load spot checks');
    } finally {
      setLoading(false);
    }
  };

  const handleAddSpotCheck = async () => {
    if (!formData.type || !formData.area || !formData.outcome) {
      toast.error('Please fill in required fields');
      return;
    }

    if (!formData.notes || formData.notes.trim().length < 5) {
      toast.error('Please provide notes (at least 5 characters)');
      return;
    }

    if (formData.follow_up_required && !formData.follow_up_date) {
      toast.error('Please set a follow-up date');
      return;
    }

    setActionLoading('add');
    try {
      await axios.post(
        `${API}/employees/${employeeId}/spot-checks`,
        formData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Spot check recorded');
      setAddDialogOpen(false);
      resetForm();
      fetchSpotChecks();
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record spot check');
    } finally {
      setActionLoading(null);
    }
  };

  const handleEditSpotCheck = async () => {
    if (!selectedCheck) return;

    if (!formData.notes || formData.notes.trim().length < 5) {
      toast.error('Please provide notes (at least 5 characters)');
      return;
    }

    if (formData.follow_up_required && !formData.follow_up_date) {
      toast.error('Please set a follow-up date');
      return;
    }

    setActionLoading('edit');
    try {
      await axios.put(
        `${API}/employees/${employeeId}/spot-checks/${selectedCheck.id}`,
        formData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Spot check updated');
      setEditDialogOpen(false);
      resetForm();
      fetchSpotChecks();
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update spot check');
    } finally {
      setActionLoading(null);
    }
  };

  const resetForm = () => {
    setFormData({
      type: '',
      area: '',
      outcome: '',
      notes: '',
      follow_up_required: false,
      follow_up_date: ''
    });
    setSelectedCheck(null);
  };

  const openEditDialog = (check) => {
    setSelectedCheck(check);
    setFormData({
      type: check.type,
      area: check.area,
      outcome: check.outcome,
      notes: check.notes || '',
      follow_up_required: check.follow_up_required || false,
      follow_up_date: check.follow_up_date?.split('T')[0] || ''
    });
    setEditDialogOpen(true);
  };

  const getOutcomeBadge = (outcome) => {
    const config = OUTCOME_OPTIONS.find(o => o.value === outcome);
    if (!config) return <Badge variant="outline">{outcome}</Badge>;
    
    const Icon = config.icon;
    
    return (
      <Badge className={cn("flex items-center gap-1", config.color)}>
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  const getAreaLabel = (area) => {
    const config = SPOT_CHECK_AREAS.find(a => a.value === area);
    return config?.label || area;
  };

  const getTypeLabel = (type) => {
    const config = SPOT_CHECK_TYPES.find(t => t.value === type);
    return config?.label || type;
  };

  const isFollowUpDue = (followUpDate) => {
    if (!followUpDate) return false;
    return new Date(followUpDate) <= new Date();
  };

  const isFollowUpSoon = (followUpDate) => {
    if (!followUpDate) return false;
    const due = new Date(followUpDate);
    const now = new Date();
    const daysUntilDue = Math.ceil((due - now) / (1000 * 60 * 60 * 24));
    return daysUntilDue <= 7 && daysUntilDue > 0;
  };
  
  // Schedule a future spot check
  const handleScheduleSpotCheck = async () => {
    if (!scheduleData.type || !scheduleData.area || !scheduleData.scheduled_date) {
      toast.error('Please fill in required fields');
      return;
    }

    setActionLoading('schedule');
    try {
      await axios.post(
        `${API}/employees/${employeeId}/spot-checks/schedule`,
        scheduleData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Spot check scheduled');
      setScheduleDialogOpen(false);
      setScheduleData({ type: '', area: '', scheduled_date: '', notes: '' });
      fetchSpotChecks();
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to schedule spot check');
    } finally {
      setActionLoading(null);
    }
  };
  
  // Open record outcome dialog
  const openRecordOutcomeDialog = (check) => {
    setSelectedCheck(check);
    setOutcomeData({ outcome: '', notes: '', follow_up_required: false, follow_up_date: '' });
    setRecordOutcomeDialogOpen(true);
  };
  
  // Record outcome for a scheduled spot check
  const handleRecordOutcome = async () => {
    if (!selectedCheck || !outcomeData.outcome) {
      toast.error('Please select an outcome');
      return;
    }

    setActionLoading('outcome');
    try {
      await axios.put(
        `${API}/employees/${employeeId}/spot-checks/${selectedCheck.id}/record-outcome`,
        outcomeData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Outcome recorded');
      setRecordOutcomeDialogOpen(false);
      setOutcomeData({ outcome: '', notes: '', follow_up_required: false, follow_up_date: '' });
      setSelectedCheck(null);
      fetchSpotChecks();
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record outcome');
    } finally {
      setActionLoading(null);
    }
  };

  const renderFormDialog = (isEdit = false) => (
    <Dialog open={isEdit ? editDialogOpen : addDialogOpen} onOpenChange={isEdit ? setEditDialogOpen : setAddDialogOpen}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Spot Check' : 'Record Spot Check'}</DialogTitle>
          <DialogDescription>
            {isEdit ? 'Update the spot check details.' : 'Record a workplace observation for this employee.'}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          {/* Check Type */}
          <div className="space-y-2">
            <Label>Check Type <span className="text-red-500">*</span></Label>
            <Select
              value={formData.type}
              onValueChange={(v) => setFormData({ ...formData, type: v })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select check type..." />
              </SelectTrigger>
              <SelectContent>
                {SPOT_CHECK_TYPES.map(type => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Area Observed */}
          <div className="space-y-2">
            <Label>Area Observed <span className="text-red-500">*</span></Label>
            <Select
              value={formData.area}
              onValueChange={(v) => setFormData({ ...formData, area: v })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select area..." />
              </SelectTrigger>
              <SelectContent>
                {SPOT_CHECK_AREAS.map(area => (
                  <SelectItem key={area.value} value={area.value}>
                    {area.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Outcome */}
          <div className="space-y-2">
            <Label>Outcome <span className="text-red-500">*</span></Label>
            <Select
              value={formData.outcome}
              onValueChange={(v) => setFormData({ ...formData, outcome: v })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select outcome..." />
              </SelectTrigger>
              <SelectContent>
                {OUTCOME_OPTIONS.map(outcome => (
                  <SelectItem key={outcome.value} value={outcome.value}>
                    <span className="flex items-center gap-2">
                      <outcome.icon className={cn("h-4 w-4", 
                        outcome.value === 'pass' ? 'text-green-600' : 
                        outcome.value === 'fail' ? 'text-red-600' : 'text-amber-600'
                      )} />
                      {outcome.label}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label>Notes <span className="text-red-500">*</span></Label>
            <Textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Describe what was observed, any concerns, and recommendations..."
              rows={4}
            />
            <p className="text-xs text-gray-500">Minimum 5 characters required</p>
          </div>

          {/* Follow-up Required */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="follow_up_required"
              checked={formData.follow_up_required}
              onCheckedChange={(checked) => setFormData({ ...formData, follow_up_required: checked })}
            />
            <Label htmlFor="follow_up_required" className="cursor-pointer">
              Follow-up required
            </Label>
          </div>

          {/* Follow-up Date */}
          {formData.follow_up_required && (
            <div className="space-y-2">
              <Label>Follow-up Date <span className="text-red-500">*</span></Label>
              <Input
                type="date"
                value={formData.follow_up_date}
                onChange={(e) => setFormData({ ...formData, follow_up_date: e.target.value })}
                min={new Date().toISOString().split('T')[0]}
              />
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => {
            isEdit ? setEditDialogOpen(false) : setAddDialogOpen(false);
            resetForm();
          }}>
            Cancel
          </Button>
          <Button
            onClick={isEdit ? handleEditSpotCheck : handleAddSpotCheck}
            disabled={actionLoading === (isEdit ? 'edit' : 'add')}
          >
            {actionLoading === (isEdit ? 'edit' : 'add') ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : null}
            {isEdit ? 'Update Spot Check' : 'Record Spot Check'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );

  if (loading) {
    return (
      <Card className="border-gray-200 shadow-sm">
        <CardContent className="py-12 flex justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  // Group spot checks by outcome for summary
  const passCount = spotChecks.filter(c => c.outcome === 'pass').length;
  const needsImprovementCount = spotChecks.filter(c => c.outcome === 'needs_improvement').length;
  const failCount = spotChecks.filter(c => c.outcome === 'fail').length;
  const followUpsDue = spotChecks.filter(c => c.follow_up_required && isFollowUpDue(c.follow_up_date)).length;
  const followUpsSoon = spotChecks.filter(c => c.follow_up_required && isFollowUpSoon(c.follow_up_date)).length;

  return (
    <div className="space-y-4" data-testid="spot-checks-panel">
      {/* Header with Add Button */}
      <Card className="border-gray-200 shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <ClipboardCheck className="h-5 w-5 text-primary" />
                Spot Checks & Observations
              </CardTitle>
              <CardDescription>
                Record workplace observations for CQC compliance
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={fetchSpotChecks}
                disabled={loading}
              >
                <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setScheduleDialogOpen(true)}
                data-testid="schedule-spot-check-btn"
              >
                <Calendar className="h-4 w-4 mr-1" />
                Schedule
              </Button>
              <Button
                size="sm"
                onClick={() => setAddDialogOpen(true)}
                data-testid="add-spot-check-btn"
              >
                <Plus className="h-4 w-4 mr-1" />
                Record Spot Check
              </Button>
            </div>
          </div>
        </CardHeader>
        
        {/* Summary Stats */}
        <CardContent className="pt-0 pb-4">
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="p-3 bg-green-50 rounded-lg text-center border border-green-100">
              <p className="text-2xl font-bold text-green-700">{passCount}</p>
              <p className="text-xs text-green-600">Pass</p>
            </div>
            <div className="p-3 bg-amber-50 rounded-lg text-center border border-amber-100">
              <p className="text-2xl font-bold text-amber-700">{needsImprovementCount}</p>
              <p className="text-xs text-amber-600">Needs Improvement</p>
            </div>
            <div className="p-3 bg-red-50 rounded-lg text-center border border-red-100">
              <p className="text-2xl font-bold text-red-700">{failCount}</p>
              <p className="text-xs text-red-600">Fail</p>
            </div>
            <div className={cn(
              "p-3 rounded-lg text-center border",
              followUpsSoon > 0 ? "bg-orange-50 border-orange-100" : "bg-gray-50 border-gray-100"
            )}>
              <p className={cn("text-2xl font-bold", followUpsSoon > 0 ? "text-orange-700" : "text-gray-500")}>{followUpsSoon}</p>
              <p className={cn("text-xs", followUpsSoon > 0 ? "text-orange-600" : "text-gray-500")}>Follow-ups Soon</p>
            </div>
            <div className={cn(
              "p-3 rounded-lg text-center border",
              followUpsDue > 0 ? "bg-red-50 border-red-100" : "bg-gray-50 border-gray-100"
            )}>
              <p className={cn("text-2xl font-bold", followUpsDue > 0 ? "text-red-700" : "text-gray-500")}>{followUpsDue}</p>
              <p className={cn("text-xs", followUpsDue > 0 ? "text-red-600" : "text-gray-500")}>Follow-ups Due</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Spot Checks Table */}
      <Card className="border-gray-200 shadow-sm">
        <CardContent className="p-0">
          {spotChecks.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <ClipboardCheck className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No spot checks recorded</p>
              <p className="text-sm text-gray-400 mt-1">Click "Record Spot Check" to add an observation</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Area Observed</TableHead>
                  <TableHead>Outcome</TableHead>
                  <TableHead>Assessed By</TableHead>
                  <TableHead>Follow-up</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {spotChecks.map((check) => {
                  const followUpDue = check.follow_up_required && isFollowUpDue(check.follow_up_date);
                  const followUpSoon = check.follow_up_required && isFollowUpSoon(check.follow_up_date);
                  const isNegative = check.outcome === 'fail' || check.outcome === 'needs_improvement';
                  
                  return (
                    <TableRow 
                      key={check.id} 
                      className={cn(
                        followUpDue && "bg-red-50/50",
                        followUpSoon && !followUpDue && "bg-amber-50/50",
                        isNegative && !followUpDue && !followUpSoon && "bg-orange-50/30"
                      )}
                      data-testid={`spot-check-row-${check.id}`}
                    >
                      <TableCell className="text-sm">
                        {formatBackendDate(check.date, { format: 'short' })}
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {getTypeLabel(check.type)}
                      </TableCell>
                      <TableCell className="font-medium">
                        {getAreaLabel(check.area)}
                      </TableCell>
                      <TableCell>{getOutcomeBadge(check.outcome)}</TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {check.assessed_by_name || 'Unknown'}
                      </TableCell>
                      <TableCell>
                        {check.follow_up_required ? (
                          <div className="flex items-center gap-2">
                            <span className={cn(
                              "text-sm",
                              followUpDue ? "text-red-600 font-medium" : followUpSoon ? "text-amber-600 font-medium" : "text-gray-600"
                            )}>
                              {formatBackendDate(check.follow_up_date, { format: 'short' })}
                            </span>
                            {followUpDue && (
                              <Badge className="bg-red-100 text-red-700 text-[10px] px-1">Due</Badge>
                            )}
                            {followUpSoon && !followUpDue && (
                              <Badge className="bg-amber-100 text-amber-700 text-[10px] px-1">Soon</Badge>
                            )}
                          </div>
                        ) : (
                          <span className="text-sm text-gray-400">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                          onClick={() => openEditDialog(check)}
                          data-testid={`edit-spot-check-${check.id}`}
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Add Dialog */}
      {renderFormDialog(false)}
      
      {/* Edit Dialog */}
      {renderFormDialog(true)}
      
      {/* Schedule Spot Check Dialog */}
      <Dialog open={scheduleDialogOpen} onOpenChange={setScheduleDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" />
              Schedule Spot Check
            </DialogTitle>
            <DialogDescription>
              Schedule a future spot check. Reminders will be sent 7 days before and on the day of the check.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Check Type */}
            <div className="space-y-2">
              <Label>Check Type <span className="text-red-500">*</span></Label>
              <Select
                value={scheduleData.type}
                onValueChange={(v) => setScheduleData({ ...scheduleData, type: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select type..." />
                </SelectTrigger>
                <SelectContent>
                  {SPOT_CHECK_TYPES.map(type => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Area */}
            <div className="space-y-2">
              <Label>Area to Observe <span className="text-red-500">*</span></Label>
              <Select
                value={scheduleData.area}
                onValueChange={(v) => setScheduleData({ ...scheduleData, area: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select area..." />
                </SelectTrigger>
                <SelectContent>
                  {SPOT_CHECK_AREAS.map(area => (
                    <SelectItem key={area.value} value={area.value}>
                      {area.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Scheduled Date */}
            <div className="space-y-2">
              <Label>Scheduled Date <span className="text-red-500">*</span></Label>
              <Input
                type="date"
                value={scheduleData.scheduled_date}
                onChange={(e) => setScheduleData({ ...scheduleData, scheduled_date: e.target.value })}
                min={new Date().toISOString().split('T')[0]}
              />
              <p className="text-xs text-gray-500">
                Reminders: 7 days before and on the day of the check
              </p>
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label>Notes (Optional)</Label>
              <Textarea
                value={scheduleData.notes}
                onChange={(e) => setScheduleData({ ...scheduleData, notes: e.target.value })}
                placeholder="Any specific focus areas..."
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setScheduleDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleScheduleSpotCheck}
              disabled={actionLoading === 'schedule' || !scheduleData.type || !scheduleData.area || !scheduleData.scheduled_date}
            >
              {actionLoading === 'schedule' ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Calendar className="h-4 w-4 mr-2" />
              )}
              Schedule Spot Check
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Record Outcome Dialog */}
      <Dialog open={recordOutcomeDialogOpen} onOpenChange={setRecordOutcomeDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              Record Spot Check Outcome
            </DialogTitle>
            <DialogDescription>
              Record the outcome of the spot check observation.
            </DialogDescription>
          </DialogHeader>
          
          {selectedCheck && (
            <div className="space-y-4 py-4">
              {/* Spot Check Info */}
              <div className="bg-gray-50 p-3 rounded-lg">
                <p className="font-medium">{getAreaLabel(selectedCheck.area)}</p>
                <p className="text-sm text-gray-500">{getTypeLabel(selectedCheck.type)}</p>
                {selectedCheck.scheduled_date && (
                  <p className="text-sm text-gray-500">
                    Scheduled: {formatBackendDate(selectedCheck.scheduled_date)}
                  </p>
                )}
              </div>

              {/* Outcome */}
              <div className="space-y-2">
                <Label>Outcome <span className="text-red-500">*</span></Label>
                <Select
                  value={outcomeData.outcome}
                  onValueChange={(v) => setOutcomeData({ ...outcomeData, outcome: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select outcome..." />
                  </SelectTrigger>
                  <SelectContent>
                    {OUTCOME_OPTIONS.map(outcome => (
                      <SelectItem key={outcome.value} value={outcome.value}>
                        <span className="flex items-center gap-2">
                          <outcome.icon className={cn("h-4 w-4", 
                            outcome.value === 'pass' ? 'text-green-600' : 
                            outcome.value === 'needs_improvement' ? 'text-amber-600' : 'text-red-600'
                          )} />
                          {outcome.label}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Notes */}
              <div className="space-y-2">
                <Label>Observations & Notes</Label>
                <Textarea
                  value={outcomeData.notes}
                  onChange={(e) => setOutcomeData({ ...outcomeData, notes: e.target.value })}
                  placeholder="Describe what was observed, any concerns, and recommendations..."
                  rows={4}
                />
              </div>

              {/* Follow-up Required */}
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="outcome_follow_up_required"
                  checked={outcomeData.follow_up_required}
                  onCheckedChange={(checked) => setOutcomeData({ ...outcomeData, follow_up_required: checked })}
                />
                <Label htmlFor="outcome_follow_up_required" className="cursor-pointer">
                  Follow-up required
                </Label>
              </div>

              {/* Follow-up Date */}
              {outcomeData.follow_up_required && (
                <div className="space-y-2">
                  <Label>Follow-up Date <span className="text-red-500">*</span></Label>
                  <Input
                    type="date"
                    value={outcomeData.follow_up_date}
                    onChange={(e) => setOutcomeData({ ...outcomeData, follow_up_date: e.target.value })}
                    min={new Date().toISOString().split('T')[0]}
                  />
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setRecordOutcomeDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleRecordOutcome}
              disabled={actionLoading === 'outcome' || !outcomeData.outcome}
              className="bg-green-600 hover:bg-green-700"
            >
              {actionLoading === 'outcome' ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4 mr-2" />
              )}
              Record Outcome
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

