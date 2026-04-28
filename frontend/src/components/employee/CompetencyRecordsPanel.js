import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { 
  Award, CheckCircle, AlertCircle, Clock, Loader2, RefreshCw, 
  Plus, Edit, Calendar, AlertTriangle, History
} from 'lucide-react';
import { toast } from 'sonner';
import { formatBackendDate } from '../../lib/dateUtils';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_BASE_URL;

export default function CompetencyRecordsPanel({ employeeId, employeeName, isAuditor = false, onRefresh }) {
  const [competencies, setCompetencies] = useState([]);
  const [competencyTypes, setCompetencyTypes] = useState([]);
  const [missingCompetencies, setMissingCompetencies] = useState({ missing_competencies: [], expiring_soon: [] });
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [selectedCompetency, setSelectedCompetency] = useState(null);
  const [formData, setFormData] = useState({
    competency_type: '',
    competency_name: '',
    status: 'competent',
    review_due_date: '',
    notes: ''
  });
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      const [compRes, missingRes, typesRes] = await Promise.all([
        axios.get(`${API}/employees/${employeeId}/competencies`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/employees/${employeeId}/missing-competencies`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/competency-types`, {
          headers: { Authorization: `Bearer ${token}` }
        }).catch(() => ({ data: { competency_types: [] } }))
      ]);
      
      setCompetencies(compRes.data.competencies || []);
      setMissingCompetencies(missingRes.data || { missing_competencies: [], expiring_soon: [] });
      setCompetencyTypes(typesRes.data.competency_types || []);
    } catch (error) {
      console.error('Failed to fetch competencies:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) {
      fetchData();
    }
  }, [employeeId]);

  const handleSubmit = async () => {
    if (!formData.competency_type) {
      toast.error('Please select a competency type');
      return;
    }
    
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      
      const payload = {
        competency_type: formData.competency_type,
        competency_name: formData.competency_name || formData.competency_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        status: formData.status,
        review_due_date: formData.review_due_date || null,
        notes: formData.notes || null
      };
      
      if (selectedCompetency) {
        await axios.put(
          `${API}/employees/${employeeId}/competencies/${selectedCompetency.id}`,
          payload,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success('Competency updated');
      } else {
        await axios.post(
          `${API}/employees/${employeeId}/competencies`,
          payload,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success('Competency recorded');
      }
      
      setShowAddDialog(false);
      resetForm();
      fetchData();
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save competency');
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setFormData({
      competency_type: '',
      competency_name: '',
      status: 'competent',
      review_due_date: '',
      notes: ''
    });
    setSelectedCompetency(null);
  };

  const openEditDialog = (comp) => {
    setSelectedCompetency(comp);
    setFormData({
      competency_type: comp.competency_type,
      competency_name: comp.competency_name,
      status: comp.status,
      review_due_date: comp.review_due_date?.split('T')[0] || '',
      notes: comp.notes || ''
    });
    setShowAddDialog(true);
  };

  const getStatusConfig = (status) => {
    switch(status) {
      case 'competent':
        return { label: 'Competent', color: 'bg-green-100 text-green-700', icon: CheckCircle };
      case 'not_competent':
        return { label: 'Not Competent', color: 'bg-red-100 text-red-700', icon: AlertCircle };
      case 'training_required':
        return { label: 'Training Required', color: 'bg-amber-100 text-amber-700', icon: AlertTriangle };
      case 'missing':
        return { label: 'Missing', color: 'bg-gray-100 text-gray-600', icon: AlertCircle };
      default:
        return { label: status?.replace(/_/g, ' ') || 'Unknown', color: 'bg-gray-100 text-gray-600', icon: Clock };
    }
  };

  // Get default review date (1 year from now)
  const getDefaultReviewDate = () => {
    const date = new Date();
    date.setFullYear(date.getFullYear() + 1);
    return date.toISOString().split('T')[0];
  };

  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  const hasMissing = missingCompetencies.missing_competencies?.length > 0;
  const hasExpiring = missingCompetencies.expiring_soon?.length > 0;

  return (
    <div className="space-y-4" data-testid="competency-records-panel">
      {/* Missing Competencies Alert */}
      {hasMissing && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h4 className="font-medium text-amber-800">Missing Competencies</h4>
              <p className="text-sm text-amber-700 mb-2">
                The following competencies are required for this role:
              </p>
              <div className="flex flex-wrap gap-2">
                {missingCompetencies.missing_competencies.map((comp, idx) => (
                  <Badge 
                    key={idx} 
                    className={`${comp.is_critical ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}
                  >
                    {comp.competency_name}
                    {comp.is_critical && <span className="ml-1 text-[10px]">CRITICAL</span>}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Expiring Soon Alert */}
      {hasExpiring && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <Clock className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h4 className="font-medium text-blue-800">Reviews Due Soon</h4>
              <p className="text-sm text-blue-700 mb-2">
                These competencies need to be re-assessed:
              </p>
              <div className="space-y-1">
                {missingCompetencies.expiring_soon.map((comp, idx) => (
                  <div key={idx} className="text-sm text-blue-700 flex items-center gap-2">
                    <Calendar className="h-3 w-3" />
                    <span>{comp.competency_name}</span>
                    <span className="text-blue-500">
                      ({comp.days_until_due} days until review)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Competency Records Card */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader className="flex-row items-center justify-between flex-wrap gap-3">
          <div>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Award className="h-5 w-5 text-primary" />
              Competency Assessments
            </CardTitle>
            <p className="text-sm text-gray-500 mt-1">
              CQC requires documented competency assessments for all care staff
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={fetchData}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            {!isAuditor && (
              <Button 
                size="sm" 
                onClick={() => {
                  resetForm();
                  setFormData(prev => ({ ...prev, review_due_date: getDefaultReviewDate() }));
                  setShowAddDialog(true);
                }} 
                className="gap-2"
                data-testid="add-competency-btn"
              >
                <Plus className="h-4 w-4" />
                Add Assessment
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {competencies.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Award className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p>No competency assessments recorded yet</p>
              <p className="text-xs mt-1">Add competency assessments to track staff skills</p>
            </div>
          ) : (
            <div className="space-y-3">
              {competencies.map((comp, idx) => {
                const statusConfig = getStatusConfig(comp.status);
                const StatusIcon = statusConfig.icon;
                
                return (
                  <div 
                    key={comp.id || idx} 
                    className="p-4 bg-gray-50 rounded-lg border border-gray-100 hover:border-gray-200 transition-colors"
                    data-testid={`competency-record-${idx}`}
                  >
                    <div className="flex items-start justify-between flex-wrap gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="font-medium text-gray-900">{comp.competency_name}</h4>
                          <Badge className={statusConfig.color}>
                            <StatusIcon className="h-3 w-3 mr-1" />
                            {statusConfig.label}
                          </Badge>
                        </div>
                        
                        {comp.notes && (
                          <p className="text-sm text-gray-600 mt-1">{comp.notes}</p>
                        )}
                        
                        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500 flex-wrap">
                          <span className="flex items-center gap-1">
                            <CheckCircle className="h-3 w-3" />
                            Assessed by: {comp.assessed_by_name}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatBackendDate(comp.assessed_at)}
                          </span>
                          {comp.review_due_date && (
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              Review due: {formatBackendDate(comp.review_due_date)}
                            </span>
                          )}
                        </div>
                        
                        {/* Assessment History Indicator */}
                        {comp.audit?.assessment_history?.length > 1 && (
                          <div className="mt-2 text-xs text-gray-400 flex items-center gap-1">
                            <History className="h-3 w-3" />
                            {comp.audit.assessment_history.length} assessment records
                          </div>
                        )}
                      </div>
                      
                      {!isAuditor && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => openEditDialog(comp)}
                          className="flex-shrink-0"
                          data-testid={`edit-competency-${idx}`}
                        >
                          <Edit className="h-3 w-3 mr-1" />
                          Update
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* CQC Note */}
          <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-100">
            <p className="text-xs text-blue-700">
              <strong>CQC Requirement:</strong> Competency assessments should be reviewed annually. 
              Critical competencies (medication, manual handling) must be current before an employee can work.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Add/Edit Dialog */}
      <Dialog open={showAddDialog} onOpenChange={(open) => {
        if (!open) resetForm();
        setShowAddDialog(open);
      }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {selectedCompetency ? 'Update Competency Assessment' : 'Record Competency Assessment'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label>Competency Type <span className="text-red-500">*</span></Label>
              <Select 
                value={formData.competency_type} 
                onValueChange={(val) => {
                  const comp = competencyTypes.find(c => c.value === val);
                  setFormData({
                    ...formData,
                    competency_type: val,
                    competency_name: comp?.label || val.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
                  });
                }}
              >
                <SelectTrigger data-testid="competency-type-select">
                  <SelectValue placeholder="Select competency" />
                </SelectTrigger>
                <SelectContent>
                  {competencyTypes.map(comp => (
                    <SelectItem key={comp.value} value={comp.value}>
                      <span className="flex items-center gap-2">
                        {comp.label}
                        {comp.is_critical && (
                          <span className="text-[10px] text-red-500 bg-red-50 px-1 rounded">Critical</span>
                        )}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Assessment Outcome</Label>
              <Select 
                value={formData.status} 
                onValueChange={(val) => setFormData({...formData, status: val})}
              >
                <SelectTrigger data-testid="competency-status-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="competent">
                    <span className="flex items-center gap-2">
                      <CheckCircle className="h-3 w-3 text-green-600" />
                      Competent
                    </span>
                  </SelectItem>
                  <SelectItem value="training_required">
                    <span className="flex items-center gap-2">
                      <AlertTriangle className="h-3 w-3 text-amber-600" />
                      Training Required
                    </span>
                  </SelectItem>
                  <SelectItem value="not_competent">
                    <span className="flex items-center gap-2">
                      <AlertCircle className="h-3 w-3 text-red-600" />
                      Not Competent
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Review Due Date</Label>
              <Input
                type="date"
                value={formData.review_due_date}
                onChange={(e) => setFormData({...formData, review_due_date: e.target.value})}
                data-testid="review-due-date-input"
              />
              <p className="text-xs text-gray-500 mt-1">
                CQC recommends annual competency reviews
              </p>
            </div>

            <div>
              <Label>Assessment Notes</Label>
              <Textarea
                rows={3}
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                placeholder="Assessment observations, areas for improvement, evidence references..."
                data-testid="competency-notes-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleSubmit} 
              disabled={submitting || !formData.competency_type}
              data-testid="save-competency-btn"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              {selectedCompetency ? 'Update Assessment' : 'Save Assessment'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

