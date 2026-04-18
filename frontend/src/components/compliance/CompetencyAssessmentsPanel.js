import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
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
  Plus, Edit2, History, AlertTriangle, CheckCircle, XCircle,
  Clock, Loader2, FileText, Calendar, User, RefreshCw
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';
import { cn } from '../../lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Competency types available
const COMPETENCY_TYPES = [
  { value: "medication", label: "Medication Administration", is_critical: true },
  // "medication_competency" is the canonical gate key used by engines (nurse readiness).
  // Both values satisfy the readiness check via the alias map in the backend engines.
  { value: "medication_competency", label: "Medication Administration Competency (Nurse)", is_critical: true },
  { value: "manual_handling", label: "Moving & Handling", is_critical: true },
  { value: "safeguarding", label: "Safeguarding Adults", is_critical: true },
  { value: "dementia_care", label: "Dementia Care", is_critical: false },
  { value: "learning_disabilities", label: "Learning Disabilities", is_critical: false },
  { value: "mental_health", label: "Mental Health Awareness", is_critical: false },
  { value: "end_of_life", label: "End of Life Care", is_critical: false },
  { value: "catheter_care", label: "Catheter Care", is_critical: false },
  { value: "stoma_care", label: "Stoma Care", is_critical: false },
  { value: "peg_feeding", label: "PEG Feeding", is_critical: false },
  { value: "wound_care", label: "Wound Care", is_critical: false },
  { value: "diabetes", label: "Diabetes Management", is_critical: false },
  { value: "epilepsy", label: "Epilepsy Management", is_critical: false },
  { value: "parkinsons", label: "Parkinson's Care", is_critical: false },
  { value: "choking", label: "Choking Management", is_critical: false },
  { value: "challenging_behaviour", label: "Challenging Behaviour", is_critical: false },
  { value: "clinical_competency", label: "Clinical Competency", is_critical: true },
  { value: "supervision", label: "Staff Supervision", is_critical: false },
];

// Status options — used in Add / Edit / Record Result form dropdowns
const STATUS_OPTIONS = [
  { value: "competent", label: "Assessed competent", color: "bg-green-100 text-green-700 border-green-200" },
  { value: "not_competent", label: "Not yet competent — action required", color: "bg-red-100 text-red-700 border-red-200" },
  { value: "training_required", label: "Training required — awaiting review", color: "bg-amber-100 text-amber-700 border-amber-200" },
  { value: "scheduled", label: "Assessment scheduled", color: "bg-blue-100 text-blue-700 border-blue-200" },
];

/* ─── Display status config ──────────────────────────────────── *
 * Maps derived display keys to strict CQC-safe labels.           *
 * Covers both derived keys and raw backend keys (for history).   */
const DISPLAY_STATUS = {
  competent:         { label: 'Assessed competent',                  color: 'bg-green-100 text-green-700 border-green-200',  icon: CheckCircle },
  not_competent:     { label: 'Not yet competent — action required', color: 'bg-red-100 text-red-700 border-red-200',      icon: XCircle },
  awaiting_review:   { label: 'Awaiting admin review',               color: 'bg-amber-100 text-amber-700 border-amber-200',  icon: Clock },
  training_required: { label: 'Training required',                   color: 'bg-amber-100 text-amber-700 border-amber-200',  icon: Clock },
  scheduled:         { label: 'Awaiting assessment',                 color: 'bg-blue-100 text-blue-700 border-blue-200',     icon: Calendar },
  reassessment_due:  { label: 'Reassessment due',                    color: 'bg-orange-100 text-orange-700 border-orange-200', icon: AlertTriangle },
  overdue:           { label: 'Overdue',                             color: 'bg-red-100 text-red-700 border-red-200',        icon: AlertTriangle },
  cannot_assess:     { label: 'Cannot assess',                       color: 'bg-gray-200 text-gray-700 border-gray-300',     icon: AlertTriangle },
};

/* ─── Derive display status from raw competency record ───────── *
 * A competency should only show as safe/complete when there is   *
 * a proper assessment outcome with assessor and date.            *
 * Missing evidence → cannot assess. Expired → overdue.           */
function deriveDisplayStatus(comp) {
  const now = new Date();
  const reviewDue = comp.review_due_date ? new Date(comp.review_due_date) : null;
  const scheduledDate = comp.scheduled_date ? new Date(comp.scheduled_date) : null;

  // Scheduled assessment
  if (comp.status === 'scheduled') {
    return (scheduledDate && scheduledDate < now) ? 'overdue' : 'scheduled';
  }

  // Training needed / pending review
  if (comp.status === 'training_required') return 'awaiting_review';

  // Not competent
  if (comp.status === 'not_competent') return 'not_competent';

  // Competent — validate evidence and check expiry
  if (comp.status === 'competent') {
    // Missing assessor or date → weak record, cannot confirm competence
    if (!comp.assessed_by_name && !comp.assessed_by) return 'cannot_assess';
    if (!comp.assessed_at && !comp.assessment_date) return 'cannot_assess';
    // Review overdue
    if (reviewDue && reviewDue < now) return 'overdue';
    // Reassessment due within 30 days
    if (reviewDue) {
      const daysUntil = Math.ceil((reviewDue - now) / (1000 * 60 * 60 * 24));
      if (daysUntil <= 30 && daysUntil > 0) return 'reassessment_due';
    }
    return 'competent';
  }

  // Unknown status
  return 'cannot_assess';
}

/**
 * CompetencyAssessmentsPanel - Full competency assessment management
 * 
 * Features:
 * - List all competency assessments with status
 * - Add new assessment
 * - Edit existing assessment
 * - View assessment history
 * - Warning when review due date approaching
 */
export default function CompetencyAssessmentsPanel({ employeeId, employeeName, onRefresh }) {
  const { token, user } = useAuth();
  const [competencies, setCompetencies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  
  // Dialog states
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [historyDialogOpen, setHistoryDialogOpen] = useState(false);
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [recordResultDialogOpen, setRecordResultDialogOpen] = useState(false);
  const [selectedCompetency, setSelectedCompetency] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    competency_type: '',
    competency_name: '',
    status: '',
    review_due_date: '',
    notes: ''
  });
  
  // Schedule assessment form
  const [scheduleData, setScheduleData] = useState({
    competency_type: '',
    competency_name: '',
    scheduled_date: '',
    notes: ''
  });
  
  // Record result form
  const [resultData, setResultData] = useState({
    status: '',
    notes: ''
  });

  useEffect(() => {
    fetchCompetencies();
  }, [employeeId]);

  const fetchCompetencies = async () => {
    try {
      setLoading(true);
      setLoadError(false);
      const response = await axios.get(`${API}/employees/${employeeId}/competencies`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCompetencies(response.data.competencies || []);
    } catch (error) {
      console.error('Failed to fetch competencies:', error);
      setCompetencies([]);
      setLoadError(true);
      toast.error('Failed to load competency assessments');
    } finally {
      setLoading(false);
    }
  };

  const handleCompetencyTypeChange = (value) => {
    const type = COMPETENCY_TYPES.find(t => t.value === value);
    const defaultReviewDate = new Date();
    defaultReviewDate.setFullYear(defaultReviewDate.getFullYear() + 1);
    
    setFormData({
      ...formData,
      competency_type: value,
      competency_name: type?.label || value,
      review_due_date: formData.review_due_date || defaultReviewDate.toISOString().split('T')[0]
    });
  };

  const handleAddCompetency = async () => {
    if (!formData.competency_type || !formData.status) {
      toast.error('Please fill in required fields');
      return;
    }

    setActionLoading('add');
    try {
      await axios.post(
        `${API}/employees/${employeeId}/competencies`,
        formData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Competency assessment added');
      setAddDialogOpen(false);
      resetForm();
      fetchCompetencies();
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add competency');
    } finally {
      setActionLoading(null);
    }
  };

  const handleEditCompetency = async () => {
    if (!selectedCompetency) return;

    setActionLoading('edit');
    try {
      await axios.put(
        `${API}/employees/${employeeId}/competencies/${selectedCompetency.id}`,
        formData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Competency assessment updated');
      setEditDialogOpen(false);
      resetForm();
      fetchCompetencies();
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update competency');
    } finally {
      setActionLoading(null);
    }
  };

  const resetForm = () => {
    setFormData({
      competency_type: '',
      competency_name: '',
      status: '',
      review_due_date: '',
      notes: ''
    });
    setSelectedCompetency(null);
  };

  const openEditDialog = (competency) => {
    setSelectedCompetency(competency);
    setFormData({
      competency_type: competency.competency_type,
      competency_name: competency.competency_name,
      status: competency.status,
      review_due_date: competency.review_due_date?.split('T')[0] || '',
      notes: competency.notes || ''
    });
    setEditDialogOpen(true);
  };

  const openHistoryDialog = (competency) => {
    setSelectedCompetency(competency);
    setHistoryDialogOpen(true);
  };
  
  // Schedule a future assessment
  const handleScheduleAssessment = async () => {
    if (!scheduleData.competency_type || !scheduleData.scheduled_date) {
      toast.error('Please fill in required fields');
      return;
    }

    setActionLoading('schedule');
    try {
      await axios.post(
        `${API}/employees/${employeeId}/competencies/schedule`,
        scheduleData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Assessment scheduled');
      setScheduleDialogOpen(false);
      setScheduleData({ competency_type: '', competency_name: '', scheduled_date: '', notes: '' });
      fetchCompetencies();
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to schedule assessment');
    } finally {
      setActionLoading(null);
    }
  };
  
  // Record result for a scheduled assessment
  const handleRecordResult = async () => {
    if (!selectedCompetency || !resultData.status) {
      toast.error('Please select a status');
      return;
    }

    setActionLoading('record');
    try {
      // Calculate next review date (1 year from today)
      const nextReviewDate = new Date();
      nextReviewDate.setFullYear(nextReviewDate.getFullYear() + 1);
      
      await axios.put(
        `${API}/employees/${employeeId}/competencies/${selectedCompetency.id}/record-result`,
        {
          status: resultData.status,
          notes: resultData.notes,
          review_due_date: nextReviewDate.toISOString().split('T')[0]
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Result recorded - Next review set for ' + nextReviewDate.toLocaleDateString());
      setRecordResultDialogOpen(false);
      setResultData({ status: '', notes: '' });
      setSelectedCompetency(null);
      fetchCompetencies();
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record result');
    } finally {
      setActionLoading(null);
    }
  };
  
  // Open record result dialog
  const openRecordResultDialog = (competency) => {
    setSelectedCompetency(competency);
    setResultData({ status: '', notes: '' });
    setRecordResultDialogOpen(true);
  };

  const getStatusBadge = (status) => {
    const config = DISPLAY_STATUS[status];
    if (!config) {
      return (
        <Badge variant="outline" className="bg-gray-100 text-gray-600 flex items-center gap-1">
          <AlertTriangle className="h-3 w-3" />Cannot assess
        </Badge>
      );
    }
    const Icon = config.icon;
    return (
      <Badge className={cn("flex items-center gap-1", config.color)}>
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  const renderFormDialog = (isEdit = false) => (
    <Dialog open={isEdit ? editDialogOpen : addDialogOpen} onOpenChange={isEdit ? setEditDialogOpen : setAddDialogOpen}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Competency Assessment' : 'Add Competency Assessment'}</DialogTitle>
          <DialogDescription>
            {isEdit ? 'Update the competency status and review date.' : 'Record a new competency assessment for this employee.'}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          {/* Competency Type */}
          <div className="space-y-2">
            <Label>Competency Type <span className="text-red-500">*</span></Label>
            <Select
              value={formData.competency_type}
              onValueChange={handleCompetencyTypeChange}
              disabled={isEdit}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select competency type..." />
              </SelectTrigger>
              <SelectContent>
                {COMPETENCY_TYPES.map(type => (
                  <SelectItem key={type.value} value={type.value}>
                    <span className="flex items-center gap-2">
                      {type.label}
                      {type.is_critical && (
                        <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 bg-red-50 text-red-600 border-red-200">
                          Critical
                        </Badge>
                      )}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Status */}
          <div className="space-y-2">
            <Label>Status <span className="text-red-500">*</span></Label>
            <Select
              value={formData.status}
              onValueChange={(v) => setFormData({ ...formData, status: v })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select status..." />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map(status => (
                  <SelectItem key={status.value} value={status.value}>
                    {status.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Assessment Date - Auto-filled as today for new, hidden */}
          
          {/* Review Due Date */}
          <div className="space-y-2">
            <Label>Review Due Date <span className="text-red-500">*</span></Label>
            <Input
              type="date"
              value={formData.review_due_date}
              onChange={(e) => setFormData({ ...formData, review_due_date: e.target.value })}
            />
            <p className="text-xs text-gray-500">Default: 1 year from assessment date</p>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label>Notes</Label>
            <Textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Add any notes about the assessment..."
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => {
            isEdit ? setEditDialogOpen(false) : setAddDialogOpen(false);
            resetForm();
          }}>
            Cancel
          </Button>
          <Button
            onClick={isEdit ? handleEditCompetency : handleAddCompetency}
            disabled={actionLoading === (isEdit ? 'edit' : 'add')}
          >
            {actionLoading === (isEdit ? 'edit' : 'add') ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : null}
            {isEdit ? 'Update Assessment' : 'Add Assessment'}
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

  if (loadError) {
    return (
      <Card className="border-red-200 shadow-sm">
        <CardContent className="py-12 text-center text-red-700">
          <AlertTriangle className="h-10 w-10 mx-auto mb-3 text-red-500" />
          <p className="font-medium">Cannot assess competencies</p>
          <p className="text-sm mt-1">Competency data unavailable. Schedule, add, edit, and result actions are disabled until this source loads.</p>
          <Button variant="outline" size="sm" onClick={fetchCompetencies} className="mt-4">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Enrich each record with derived display status
  const enriched = competencies.map(c => ({ ...c, _ds: deriveDisplayStatus(c) }));

  // Summary counts from derived status
  const counts = {
    competent:        enriched.filter(c => c._ds === 'competent').length,
    not_competent:    enriched.filter(c => c._ds === 'not_competent').length,
    awaiting:         enriched.filter(c => c._ds === 'scheduled' || c._ds === 'awaiting_review').length,
    reassessment_due: enriched.filter(c => c._ds === 'reassessment_due').length,
    overdue:          enriched.filter(c => c._ds === 'overdue').length,
    cannot_assess:    enriched.filter(c => c._ds === 'cannot_assess').length,
  };
  const weaknessCount = counts.cannot_assess + enriched.filter(c =>
    (c._ds === 'not_competent' && !c.notes) ||
    (c._ds === 'competent' && !c.review_due_date)
  ).length;

  return (
    <div className="space-y-4" data-testid="competency-assessments-panel">
      {/* Header with Add Button */}
      <Card className="border-gray-200 shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                Competency Assessments
              </CardTitle>
              <CardDescription>
                Track staff competencies and review dates for CQC compliance
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={fetchCompetencies}
                disabled={loading}
              >
                <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
              </Button>
              <Button 
                variant="outline"
                size="sm"
                onClick={() => setScheduleDialogOpen(true)}
                data-testid="schedule-assessment-btn"
              >
                <Calendar className="h-4 w-4 mr-1" />
                Schedule
              </Button>
              <Button
                size="sm"
                onClick={() => setAddDialogOpen(true)}
                data-testid="add-competency-btn"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Assessment
              </Button>
            </div>
          </div>
        </CardHeader>
        
        {/* Summary Stats */}
        <CardContent className="pt-0 pb-4">
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
            <div className="p-3 bg-green-50 rounded-lg text-center border border-green-100">
              <p className="text-2xl font-bold text-green-700">{counts.competent}</p>
              <p className="text-xs text-green-600">Assessed competent</p>
            </div>
            <div className="p-3 bg-red-50 rounded-lg text-center border border-red-100">
              <p className="text-2xl font-bold text-red-700">{counts.not_competent}</p>
              <p className="text-xs text-red-600">Not yet competent</p>
            </div>
            <div className="p-3 bg-amber-50 rounded-lg text-center border border-amber-100">
              <p className="text-2xl font-bold text-amber-700">{counts.awaiting}</p>
              <p className="text-xs text-amber-600">Awaiting assessment / review</p>
            </div>
            <div className={cn(
              "p-3 rounded-lg text-center border",
              counts.reassessment_due > 0 ? "bg-orange-50 border-orange-100" : "bg-gray-50 border-gray-100"
            )}>
              <p className={cn("text-2xl font-bold", counts.reassessment_due > 0 ? "text-orange-700" : "text-gray-500")}>{counts.reassessment_due}</p>
              <p className={cn("text-xs", counts.reassessment_due > 0 ? "text-orange-600" : "text-gray-500")}>Reassessment due</p>
            </div>
            <div className={cn(
              "p-3 rounded-lg text-center border",
              counts.overdue > 0 ? "bg-red-50 border-red-100" : "bg-gray-50 border-gray-100"
            )}>
              <p className={cn("text-2xl font-bold", counts.overdue > 0 ? "text-red-700" : "text-gray-500")}>{counts.overdue}</p>
              <p className={cn("text-xs", counts.overdue > 0 ? "text-red-600" : "text-gray-500")}>Overdue</p>
            </div>
            <div className={cn(
              "p-3 rounded-lg text-center border",
              counts.cannot_assess > 0 ? "bg-gray-200 border-gray-300" : "bg-gray-50 border-gray-100"
            )}>
              <p className={cn("text-2xl font-bold", counts.cannot_assess > 0 ? "text-gray-700" : "text-gray-400")}>{counts.cannot_assess}</p>
              <p className={cn("text-xs", counts.cannot_assess > 0 ? "text-gray-600" : "text-gray-400")}>Cannot assess</p>
            </div>
          </div>
          <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
            <div className="flex flex-wrap gap-x-6 gap-y-1">
              <span><span className="font-semibold text-red-700">{counts.not_competent + counts.overdue}</span> blockers</span>
              <span><span className="font-semibold text-amber-700">{counts.awaiting + counts.reassessment_due}</span> pending</span>
              <span><span className="font-semibold text-gray-700">{counts.cannot_assess}</span> cannot assess</span>
              <span><span className="font-semibold text-green-700">{counts.competent}</span> assessed competent</span>
            </div>
            {weaknessCount > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1.5 mt-2 w-fit">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                <span className="font-medium">{weaknessCount} audit weakness{weaknessCount !== 1 ? 'es' : ''}</span>
                <span className="text-amber-600">— missing assessor, date, reason, or review schedule</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Competencies Table */}
      <Card className="border-gray-200 shadow-sm">
        <CardContent className="p-0">
          {enriched.length === 0 ? (
            <div className="text-center py-12 text-amber-700">
              <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-amber-400" />
              <p className="font-medium">No competency assessments recorded</p>
              <p className="text-sm text-amber-600 mt-1">Cannot confirm any competency outcomes — add an assessment to begin tracking</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[200px]">Competency</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Assessed Date</TableHead>
                  <TableHead>Review Due</TableHead>
                  <TableHead>Assessor</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {enriched.map((comp) => {
                  const isCritical = COMPETENCY_TYPES.find(t => t.value === comp.competency_type)?.is_critical;
                  const ds = comp._ds;
                  const isWeak = ds === 'cannot_assess'
                    || (ds === 'not_competent' && !comp.notes)
                    || (ds === 'competent' && !comp.review_due_date);
                  
                  return (
                    <TableRow 
                      key={comp.id} 
                      className={cn(
                        (ds === 'overdue' || ds === 'not_competent') && "bg-red-50/50",
                        (ds === 'reassessment_due' || ds === 'awaiting_review') && "bg-amber-50/50",
                        ds === 'cannot_assess' && "bg-gray-100/50"
                      )}
                      data-testid={`competency-row-${comp.id}`}
                    >
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{comp.competency_name}</span>
                          {isCritical && (
                            <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 bg-red-50 text-red-600 border-red-200">
                              Critical
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {getStatusBadge(ds)}
                        {isWeak && (
                          <div className="flex items-center gap-1 text-[10px] text-amber-600 mt-1">
                            <AlertTriangle className="h-3 w-3 shrink-0" />
                            {ds === 'cannot_assess' ? 'Missing assessor or date'
                              : ds === 'not_competent' && !comp.notes ? 'No reason recorded'
                              : 'No review date set'}
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {comp.assessed_at || comp.assessment_date
                          ? formatBackendDate(comp.assessed_at || comp.assessment_date, { format: 'short' })
                          : <span className="text-gray-400 italic">Not recorded</span>}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {comp.review_due_date ? (
                            <>
                              <span className={cn(
                                "text-sm",
                                ds === 'overdue' ? "text-red-600 font-medium" : ds === 'reassessment_due' ? "text-orange-600 font-medium" : "text-gray-600"
                              )}>
                                {formatBackendDate(comp.review_due_date, { format: 'short' })}
                              </span>
                              {ds === 'overdue' && (
                                <Badge className="bg-red-100 text-red-700 text-[10px] px-1">Overdue</Badge>
                              )}
                              {ds === 'reassessment_due' && (
                                <Badge className="bg-orange-100 text-orange-700 text-[10px] px-1">Due</Badge>
                              )}
                            </>
                          ) : (
                            <span className="text-gray-400 italic text-sm">Not set</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm">
                        {comp.assessed_by_name ? (
                          <span className="text-gray-600">{comp.assessed_by_name}</span>
                        ) : (
                          <span className="text-amber-600 italic flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" />Not recorded
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {/* Record Result button for scheduled or overdue assessments */}
                          {(comp.status === 'scheduled' || ds === 'overdue') && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-8 text-green-600 border-green-200 hover:bg-green-50"
                              onClick={() => openRecordResultDialog(comp)}
                              data-testid={`record-result-btn-${comp.id}`}
                            >
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Record Result
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0"
                            onClick={() => openEditDialog(comp)}
                            data-testid={`edit-competency-${comp.id}`}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0"
                            onClick={() => openHistoryDialog(comp)}
                            data-testid={`history-competency-${comp.id}`}
                          >
                            <History className="h-4 w-4" />
                          </Button>
                        </div>
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

      {/* History Dialog */}
      <Dialog open={historyDialogOpen} onOpenChange={setHistoryDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Assessment History</DialogTitle>
            <DialogDescription>
              {selectedCompetency?.competency_name} - {employeeName}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-3 py-4 max-h-[400px] overflow-y-auto">
            {selectedCompetency?.audit?.assessment_history?.map((entry, idx) => (
              <div key={idx} className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                <div className="flex items-center justify-between mb-2">
                  {getStatusBadge(entry.status)}
                  <span className="text-xs text-gray-500">
                    {formatBackendDate(entry.assessed_at, { format: 'full' })}
                  </span>
                </div>
                <p className="text-sm text-gray-600">
                  <User className="h-3 w-3 inline mr-1" />
                  {entry.assessed_by_name || 'Unknown'}
                </p>
                {entry.notes && (
                  <p className="text-sm text-gray-500 mt-2 italic">"{entry.notes}"</p>
                )}
              </div>
            )) || (
              <p className="text-center text-gray-500 py-4">No history available</p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setHistoryDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Schedule Assessment Dialog */}
      <Dialog open={scheduleDialogOpen} onOpenChange={setScheduleDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" />
              Schedule Future Assessment
            </DialogTitle>
            <DialogDescription>
              Schedule a competency assessment for a future date. Reminders will be sent at 60, 30, and 7 days before.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Competency Type */}
            <div className="space-y-2">
              <Label>Competency Type <span className="text-red-500">*</span></Label>
              <Select
                value={scheduleData.competency_type}
                onValueChange={(value) => {
                  const type = COMPETENCY_TYPES.find(t => t.value === value);
                  setScheduleData({
                    ...scheduleData,
                    competency_type: value,
                    competency_name: type?.label || value
                  });
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select competency type..." />
                </SelectTrigger>
                <SelectContent>
                  {COMPETENCY_TYPES.map(type => (
                    <SelectItem key={type.value} value={type.value}>
                      <span className="flex items-center gap-2">
                        {type.label}
                        {type.is_critical && (
                          <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 bg-red-50 text-red-600 border-red-200">
                            Critical
                          </Badge>
                        )}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Scheduled Date */}
            <div className="space-y-2">
              <Label>Assessment Due Date <span className="text-red-500">*</span></Label>
              <Input
                type="date"
                value={scheduleData.scheduled_date}
                onChange={(e) => setScheduleData({ ...scheduleData, scheduled_date: e.target.value })}
                min={new Date().toISOString().split('T')[0]}
              />
              <p className="text-xs text-gray-500">
                Reminders: 60 days, 30 days, and 7 days before due date
              </p>
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label>Notes (Optional)</Label>
              <Textarea
                value={scheduleData.notes}
                onChange={(e) => setScheduleData({ ...scheduleData, notes: e.target.value })}
                placeholder="Any specific areas to assess..."
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setScheduleDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleScheduleAssessment}
              disabled={actionLoading === 'schedule' || !scheduleData.competency_type || !scheduleData.scheduled_date}
            >
              {actionLoading === 'schedule' ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Calendar className="h-4 w-4 mr-2" />
              )}
              Schedule Assessment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Record Result Dialog */}
      <Dialog open={recordResultDialogOpen} onOpenChange={setRecordResultDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              Record Assessment Result
            </DialogTitle>
            <DialogDescription>
              Record the outcome of the competency assessment. Next review will automatically be set to 1 year from today.
            </DialogDescription>
          </DialogHeader>
          
          {selectedCompetency && (
            <div className="space-y-4 py-4">
              {/* Competency Info */}
              <div className="bg-gray-50 p-3 rounded-lg">
                <p className="font-medium">{selectedCompetency.competency_name}</p>
                {selectedCompetency.scheduled_date && (
                  <p className="text-sm text-gray-500">
                    Scheduled: {formatBackendDate(selectedCompetency.scheduled_date)}
                  </p>
                )}
              </div>

              {/* Status */}
              <div className="space-y-2">
                <Label>Result <span className="text-red-500">*</span></Label>
                <Select
                  value={resultData.status}
                  onValueChange={(v) => setResultData({ ...resultData, status: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select outcome..." />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUS_OPTIONS.map(status => (
                      <SelectItem key={status.value} value={status.value}>
                        {status.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Notes */}
              <div className="space-y-2">
                <Label>Notes (Optional)</Label>
                <Textarea
                  value={resultData.notes}
                  onChange={(e) => setResultData({ ...resultData, notes: e.target.value })}
                  placeholder="Observations, areas for improvement..."
                  rows={3}
                />
              </div>
              
              {/* Next Review Notice */}
              <div className="bg-blue-50 p-3 rounded-lg border border-blue-100">
                <p className="text-sm text-blue-700">
                  <Clock className="h-4 w-4 inline mr-1" />
                  Next review will be automatically set to: <strong>{new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toLocaleDateString()}</strong>
                </p>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setRecordResultDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleRecordResult}
              disabled={actionLoading === 'record' || !resultData.status}
              className="bg-green-600 hover:bg-green-700"
            >
              {actionLoading === 'record' ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4 mr-2" />
              )}
              Record Result
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
