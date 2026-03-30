import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../ui/dialog';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { 
  Clock, CheckCircle, AlertTriangle, AlertCircle, CalendarClock,
  Users, ClipboardCheck, Eye, Loader2, ChevronDown, ChevronUp, Plus
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const itemTypeLabels = {
  supervision: 'Supervision',
  competency_assessment: 'Competency Assessment',
  spot_check: 'Spot Check',
  training_refresh: 'Training Refresh',
  report_followup: 'Report Follow-up'
};

const itemTypeIcons = {
  supervision: Users,
  competency_assessment: ClipboardCheck,
  spot_check: Eye,
  training_refresh: CalendarClock,
  report_followup: AlertCircle
};

const frequencyLabels = {
  monthly: 'Monthly',
  bi_monthly: 'Bi-Monthly',
  quarterly: 'Quarterly',
  six_monthly: '6 Monthly',
  annual: 'Annual',
  ad_hoc: 'Ad-hoc'
};

const statusConfig = {
  overdue: { color: 'bg-red-100 text-red-800 border-red-200', icon: AlertTriangle, label: 'Overdue' },
  due: { color: 'bg-amber-100 text-amber-800 border-amber-200', icon: Clock, label: 'Due' },
  upcoming: { color: 'bg-blue-100 text-blue-800 border-blue-200', icon: CalendarClock, label: 'Upcoming' },
  scheduled: { color: 'bg-gray-100 text-gray-600 border-gray-200', icon: Clock, label: 'Scheduled' },
  completed: { color: 'bg-green-100 text-green-800 border-green-200', icon: CheckCircle, label: 'Completed' }
};

const outcomeOptions = [
  { value: 'satisfactory', label: 'Satisfactory' },
  { value: 'needs_improvement', label: 'Needs Improvement' },
  { value: 'action_required', label: 'Action Required' },
  { value: 'not_applicable', label: 'Not Applicable' }
];

export default function RecurringComplianceSection({ employeeId, employeeName }) {
  const { token, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [expandedItem, setExpandedItem] = useState(null);
  
  // Completion modal state
  const [completionModalOpen, setCompletionModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [completionForm, setCompletionForm] = useState({
    completed_date: new Date().toISOString().split('T')[0],
    outcome: '',
    notes: '',
    support_action_required: '',
    follow_up_due_date: ''
  });

  const fetchRecurringCompliance = async () => {
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/recurring-compliance`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setData(response.data);
    } catch (error) {
      console.error('Failed to fetch recurring compliance:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) {
      fetchRecurringCompliance();
    }
  }, [employeeId, token]);

  const handleOpenCompletion = (item) => {
    setSelectedItem(item);
    setCompletionForm({
      completed_date: new Date().toISOString().split('T')[0],
      outcome: '',
      notes: '',
      support_action_required: '',
      follow_up_due_date: ''
    });
    setCompletionModalOpen(true);
  };

  const handleRecordCompletion = async () => {
    if (!completionForm.outcome) {
      toast.error('Please select an outcome');
      return;
    }
    if (!completionForm.notes.trim()) {
      toast.error('Please add notes about this completion');
      return;
    }

    // For action_required competency assessments, require follow-up details
    if (selectedItem?.item_type === 'competency_assessment' && 
        completionForm.outcome === 'action_required' &&
        !completionForm.support_action_required) {
      toast.error('Please specify the support action required');
      return;
    }

    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/recurring-compliance/${selectedItem.id}/complete`,
        completionForm,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Completion recorded successfully');
      setCompletionModalOpen(false);
      fetchRecurringCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record completion');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  const items = data?.items || [];
  const summary = data?.summary || { total: 0, overdue: 0, due: 0, upcoming: 0 };

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className={`${summary.overdue > 0 ? 'border-red-200 bg-red-50' : ''}`}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-muted">Overdue</span>
              <AlertTriangle className={`h-4 w-4 ${summary.overdue > 0 ? 'text-red-600' : 'text-gray-400'}`} />
            </div>
            <p className={`text-2xl font-bold mt-1 ${summary.overdue > 0 ? 'text-red-600' : 'text-gray-400'}`}>
              {summary.overdue}
            </p>
          </CardContent>
        </Card>
        
        <Card className={`${summary.due > 0 ? 'border-amber-200 bg-amber-50' : ''}`}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-muted">Due Now</span>
              <Clock className={`h-4 w-4 ${summary.due > 0 ? 'text-amber-600' : 'text-gray-400'}`} />
            </div>
            <p className={`text-2xl font-bold mt-1 ${summary.due > 0 ? 'text-amber-600' : 'text-gray-400'}`}>
              {summary.due}
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-muted">Upcoming</span>
              <CalendarClock className="h-4 w-4 text-blue-500" />
            </div>
            <p className="text-2xl font-bold mt-1 text-blue-600">{summary.upcoming}</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-muted">Total Active</span>
              <ClipboardCheck className="h-4 w-4 text-gray-500" />
            </div>
            <p className="text-2xl font-bold mt-1">{summary.total}</p>
          </CardContent>
        </Card>
      </div>

      {/* Items List */}
      {items.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <ClipboardCheck className="h-12 w-12 mx-auto text-gray-300 mb-4" />
            <p className="text-text-muted">No recurring compliance items scheduled</p>
            <p className="text-sm text-gray-400 mt-1">
              Add supervision, competency assessments, spot checks, and training refresh schedules
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const StatusIcon = statusConfig[item.computed_status]?.icon || Clock;
            const statusStyle = statusConfig[item.computed_status] || statusConfig.scheduled;
            const ItemIcon = itemTypeIcons[item.item_type] || ClipboardCheck;
            const isExpanded = expandedItem === item.id;
            
            return (
              <Card key={item.id} className="overflow-hidden">
                <div className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1">
                      <div className={`p-2 rounded-lg ${statusStyle.color}`}>
                        <ItemIcon className="h-5 w-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="font-medium text-text-primary">{item.item_name}</h4>
                          <Badge className={statusStyle.color}>
                            <StatusIcon className="h-3 w-3 mr-1" />
                            {statusStyle.label}
                            {item.computed_status === 'overdue' && item.days_overdue > 0 && 
                              ` (${item.days_overdue}d)`}
                            {item.computed_status === 'due' && item.days_until_due > 0 && 
                              ` (${item.days_until_due}d)`}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-4 mt-1 text-sm text-text-muted flex-wrap">
                          <span>{itemTypeLabels[item.item_type]}</span>
                          <span>•</span>
                          <span>{frequencyLabels[item.frequency]}</span>
                          <span>•</span>
                          <span>Due: {formatDate(item.next_due_date)}</span>
                        </div>
                        {item.last_completed_date && (
                          <p className="text-xs text-gray-400 mt-1">
                            Last completed: {formatDate(item.last_completed_date)}
                          </p>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleOpenCompletion(item)}
                        className="bg-primary hover:bg-primary-hover text-white"
                        data-testid={`complete-btn-${item.id}`}
                      >
                        <CheckCircle className="h-4 w-4 mr-1" />
                        Record
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setExpandedItem(isExpanded ? null : item.id)}
                      >
                        {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>
                  
                  {/* Expanded - Completion History */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t">
                      <h5 className="text-sm font-medium text-text-primary mb-3">Completion History</h5>
                      {item.completion_history && item.completion_history.length > 0 ? (
                        <div className="space-y-2">
                          {item.completion_history.slice().reverse().map((record, idx) => (
                            <div 
                              key={record.id || idx} 
                              className="text-sm p-3 bg-gray-50 rounded-lg"
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium">{formatDate(record.completed_date)}</span>
                                <Badge variant="outline" className={
                                  record.outcome === 'satisfactory' ? 'text-green-700 border-green-300' :
                                  record.outcome === 'needs_improvement' ? 'text-amber-700 border-amber-300' :
                                  record.outcome === 'action_required' ? 'text-red-700 border-red-300' :
                                  'text-gray-600 border-gray-300'
                                }>
                                  {record.outcome?.replace('_', ' ')}
                                </Badge>
                              </div>
                              <p className="text-text-muted">{record.notes}</p>
                              <p className="text-xs text-gray-400 mt-1">
                                Recorded by {record.completed_by_name || 'Unknown'}
                              </p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-text-muted">No completions recorded yet</p>
                      )}
                    </div>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Completion Modal */}
      <Dialog open={completionModalOpen} onOpenChange={setCompletionModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Record Completion</DialogTitle>
            <DialogDescription>
              Record completion for: {selectedItem?.item_name}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Completed Date *</Label>
              <Input
                type="date"
                value={completionForm.completed_date}
                onChange={(e) => setCompletionForm(prev => ({ ...prev, completed_date: e.target.value }))}
                max={new Date().toISOString().split('T')[0]}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Outcome *</Label>
              <Select 
                value={completionForm.outcome} 
                onValueChange={(v) => setCompletionForm(prev => ({ ...prev, outcome: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select outcome" />
                </SelectTrigger>
                <SelectContent>
                  {outcomeOptions.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Notes *</Label>
              <Textarea
                value={completionForm.notes}
                onChange={(e) => setCompletionForm(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="Describe what was covered, observed, or discussed..."
                rows={4}
              />
            </div>
            
            {/* Show support action field for competency assessments with action_required */}
            {selectedItem?.item_type === 'competency_assessment' && 
             completionForm.outcome === 'action_required' && (
              <>
                <div className="space-y-2">
                  <Label>Support Action Required *</Label>
                  <Textarea
                    value={completionForm.support_action_required}
                    onChange={(e) => setCompletionForm(prev => ({ ...prev, support_action_required: e.target.value }))}
                    placeholder="Describe the support/training needed..."
                    rows={2}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Follow-up Due Date</Label>
                  <Input
                    type="date"
                    value={completionForm.follow_up_due_date}
                    onChange={(e) => setCompletionForm(prev => ({ ...prev, follow_up_due_date: e.target.value }))}
                    min={new Date().toISOString().split('T')[0]}
                  />
                </div>
              </>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setCompletionModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleRecordCompletion} disabled={isSubmitting}>
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4 mr-2" />
              )}
              Record Completion
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
