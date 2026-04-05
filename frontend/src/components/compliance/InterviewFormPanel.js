import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { 
  ClipboardList, Download, CheckCircle, Clock, AlertTriangle,
  Loader2, RefreshCw, User, Calendar, FileText, ChevronDown,
  ChevronRight, Plus, Edit, Star, Save
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DECISION_CONFIG = {
  'Approve': { color: 'bg-green-100 text-green-700', icon: CheckCircle },
  'Hire': { color: 'bg-green-100 text-green-700', icon: CheckCircle },
  'Strong Hire': { color: 'bg-green-100 text-green-700', icon: CheckCircle },
  'On Hold': { color: 'bg-amber-100 text-amber-700', icon: Clock },
  'Consider': { color: 'bg-amber-100 text-amber-700', icon: Clock },
  'Maybe': { color: 'bg-amber-100 text-amber-700', icon: Clock },
  'Reject': { color: 'bg-red-100 text-red-700', icon: AlertTriangle },
  'Not Suitable': { color: 'bg-red-100 text-red-700', icon: AlertTriangle }
};

const INTERVIEW_METHODS = [
  { value: 'phone', label: 'Phone Call' },
  { value: 'video', label: 'Video Call' },
  { value: 'in_person', label: 'In Person' }
];

const SCORE_OPTIONS = [
  { value: 1, label: '1 - Poor' },
  { value: 2, label: '2 - Below Average' },
  { value: 3, label: '3 - Average' },
  { value: 4, label: '4 - Good' },
  { value: 5, label: '5 - Excellent' }
];

// Rating stars component
const RatingStars = ({ value, onChange, disabled = false }) => (
  <div className="flex gap-1">
    {[1, 2, 3, 4, 5].map(star => (
      <button
        key={star}
        type="button"
        onClick={() => !disabled && onChange(star)}
        disabled={disabled}
        className={`p-1 transition-colors ${disabled ? 'cursor-default' : 'cursor-pointer hover:scale-110'}`}
      >
        <Star 
          className={`h-5 w-5 ${star <= value ? 'fill-amber-400 text-amber-400' : 'text-gray-300'}`}
        />
      </button>
    ))}
    <span className="ml-2 text-sm text-gray-500">
      {SCORE_OPTIONS.find(s => s.value === value)?.label?.split(' - ')[1] || ''}
    </span>
  </div>
);

export default function InterviewFormPanel({ employeeId, employeeName }) {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
  const [downloading, setDownloading] = useState(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    interview_date: new Date().toISOString().split('T')[0],
    interview_method: 'video',
    interviewer_name: '',
    communication_score: 3,
    experience_score: 3,
    values_score: 3,
    availability: '',
    strengths: '',
    areas_for_development: '',
    decision: '',
    notes: ''
  });
  const [editingId, setEditingId] = useState(null);

  const fetchInterviews = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      // Use the new dedicated endpoint for interview records
      const response = await axios.get(`${API}/employees/${employeeId}/interview-records`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setInterviews(response.data.records || []);
    } catch (error) {
      console.error('Failed to fetch interview records:', error);
      // Fallback to form-submissions
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get(`${API}/employees/${employeeId}/forms`, {
          headers: { Authorization: `Bearer ${token}` },
          params: { requirement_id: 'interview_record' }
        });
        setInterviews(response.data.forms || response.data || []);
      } catch (err) {
        setInterviews([]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) {
      fetchInterviews();
    }
  }, [employeeId]);

  const resetForm = () => {
    setFormData({
      interview_date: new Date().toISOString().split('T')[0],
      interview_method: 'video',
      interviewer_name: '',
      communication_score: 3,
      experience_score: 3,
      values_score: 3,
      availability: '',
      strengths: '',
      areas_for_development: '',
      decision: '',
      notes: ''
    });
    setEditingId(null);
  };

  const handleCreateInterview = async (isDraft = false) => {
    if (!formData.decision && !isDraft) {
      toast.error('Please select a decision');
      return;
    }
    
    try {
      setSaving(true);
      const token = localStorage.getItem('token');
      
      const payload = {
        ...formData,
        is_draft: isDraft
      };
      
      if (editingId) {
        // Update existing
        await axios.put(
          `${API}/employees/${employeeId}/interview-records/${editingId}`,
          payload,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success(isDraft ? 'Draft saved' : 'Interview record updated');
      } else {
        // Create new
        await axios.post(
          `${API}/employees/${employeeId}/interview-records`,
          payload,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success(isDraft ? 'Draft saved' : 'Interview record created');
      }
      
      setShowCreateDialog(false);
      resetForm();
      fetchInterviews();
    } catch (error) {
      console.error('Failed to save interview record:', error);
      toast.error('Failed to save interview record');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (interview) => {
    const data = interview.form_data || interview.data || {};
    setFormData({
      interview_date: data.interview_date || new Date().toISOString().split('T')[0],
      interview_method: data.interview_method || 'video',
      interviewer_name: data.interviewer_name || '',
      communication_score: data.communication_score || 3,
      experience_score: data.experience_score || 3,
      values_score: data.values_score || 3,
      availability: data.availability || '',
      strengths: data.strengths || '',
      areas_for_development: data.areas_for_development || '',
      decision: data.decision || '',
      notes: data.notes || ''
    });
    setEditingId(interview.id);
    setShowCreateDialog(true);
  };

  const handleDownloadPDF = async (recordId) => {
    try {
      setDownloading(recordId);
      const token = localStorage.getItem('token');
      
      const response = await axios.get(
        `${API}/employees/${employeeId}/interview-records/${recordId}/download-pdf`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      // Create download link
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `interview_record_${employeeName?.replace(/\s+/g, '_') || 'employee'}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Interview record downloaded');
    } catch (error) {
      console.error('PDF download failed:', error);
      toast.error('Failed to download interview record');
    } finally {
      setDownloading(null);
    }
  };

  const getDecisionConfig = (decision) => {
    const key = Object.keys(DECISION_CONFIG).find(k => 
      decision?.toLowerCase().includes(k.toLowerCase())
    );
    return key ? DECISION_CONFIG[key] : { color: 'bg-gray-100 text-gray-600', icon: Clock };
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

  return (
    <>
    <Card className="border-[#E4E8EB] shadow-sm">
      <CardHeader>
        <CardTitle className="font-heading text-lg flex items-center justify-between">
          <span className="flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-primary" />
            Interview Records
          </span>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={fetchInterviews}
              disabled={loading}
              className="rounded-xl"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            <Button 
              size="sm" 
              onClick={() => { resetForm(); setShowCreateDialog(true); }}
              className="rounded-xl bg-primary hover:bg-primary/90"
              data-testid="create-interview-btn"
            >
              <Plus className="h-4 w-4 mr-1" />
              Record Interview
            </Button>
          </div>
        </CardTitle>
        <p className="text-sm text-gray-500 mt-1">
          Admin-only interview assessments and hiring decisions
        </p>
      </CardHeader>
      <CardContent>
        {interviews.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <ClipboardList className="h-10 w-10 mx-auto mb-3 text-gray-300" />
            <p>No interview records on file</p>
            <p className="text-xs mt-1">Interview records will appear here after completion</p>
          </div>
        ) : (
          <div className="space-y-3">
            {interviews.map((interview, index) => {
              const formData = interview.form_data || {};
              const decision = formData.decision || formData.overall_decision;
              const decisionConfig = getDecisionConfig(decision);
              const DecisionIcon = decisionConfig.icon;
              const isExpanded = expandedId === interview.id;
              
              return (
                <div 
                  key={interview.id || index}
                  className="border rounded-xl overflow-hidden"
                  data-testid={`interview-record-${index}`}
                >
                  {/* Header */}
                  <div 
                    className="flex items-center justify-between p-4 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                    onClick={() => setExpandedId(isExpanded ? null : interview.id)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <ClipboardList className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">
                          Interview {formData.interview_type || 'Record'}
                        </p>
                        <div className="flex items-center gap-3 text-xs text-gray-500">
                          {formData.interview_date && (
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {formatBackendDate(formData.interview_date)}
                            </span>
                          )}
                          {formData.interviewer_name && (
                            <span className="flex items-center gap-1">
                              <User className="h-3 w-3" />
                              {formData.interviewer_name}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {decision && (
                        <Badge className={`${decisionConfig.color} flex items-center gap-1`}>
                          <DecisionIcon className="h-3 w-3" />
                          {decision}
                        </Badge>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDownloadPDF(interview.id);
                        }}
                        disabled={downloading === interview.id}
                        className="rounded-lg"
                      >
                        {downloading === interview.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Download className="h-4 w-4" />
                        )}
                      </Button>
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-gray-400" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-gray-400" />
                      )}
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && (
                    <div className="p-4 border-t bg-white space-y-4">
                      {/* Assessment Summary */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {formData.position_applied && (
                          <div>
                            <p className="text-xs font-medium text-gray-500 mb-1">Position Applied</p>
                            <p className="text-sm text-gray-900">{formData.position_applied}</p>
                          </div>
                        )}
                        {formData.overall_impression && (
                          <div>
                            <p className="text-xs font-medium text-gray-500 mb-1">Overall Impression</p>
                            <p className="text-sm text-gray-900">{formData.overall_impression}</p>
                          </div>
                        )}
                      </div>

                      {/* Strengths */}
                      {formData.strengths && (
                        <div>
                          <p className="text-xs font-medium text-gray-500 mb-1">Strengths</p>
                          <p className="text-sm text-gray-700 bg-green-50 p-3 rounded-lg">
                            {formData.strengths}
                          </p>
                        </div>
                      )}

                      {/* Areas for Development */}
                      {formData.areas_for_development && (
                        <div>
                          <p className="text-xs font-medium text-gray-500 mb-1">Areas for Development</p>
                          <p className="text-sm text-gray-700 bg-amber-50 p-3 rounded-lg">
                            {formData.areas_for_development}
                          </p>
                        </div>
                      )}

                      {/* Notes */}
                      {formData.interviewer_notes && (
                        <div>
                          <p className="text-xs font-medium text-gray-500 mb-1">Interviewer Notes</p>
                          <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg">
                            {formData.interviewer_notes}
                          </p>
                        </div>
                      )}

                      {/* Verification Checks */}
                      <div className="flex flex-wrap gap-2 pt-2 border-t">
                        {formData.right_to_work_verified && (
                          <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            RTW Verified
                          </Badge>
                        )}
                        {formData.references_discussed && (
                          <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            References Discussed
                          </Badge>
                        )}
                        {formData.experience_summary && (
                          <Badge variant="outline" className="text-xs bg-purple-50 text-purple-700 border-purple-200">
                            <FileText className="h-3 w-3 mr-1" />
                            Experience Documented
                          </Badge>
                        )}
                      </div>

                      {/* Submission Info */}
                      <div className="text-xs text-gray-400 pt-2 border-t flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <span>Submitted: {formatBackendDate(interview.submitted_at || interview.created_at)}</span>
                          {interview.submitted_by_name && (
                            <span>By: {interview.submitted_by_name}</span>
                          )}
                        </div>
                        {interview.status === 'draft' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={(e) => { e.stopPropagation(); handleEdit(interview); }}
                            className="rounded-lg"
                          >
                            <Edit className="h-3 w-3 mr-1" />
                            Edit Draft
                          </Button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>

    {/* Create/Edit Interview Dialog */}
    <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-primary" />
            {editingId ? 'Edit Interview Record' : 'Record Interview'}
          </DialogTitle>
          <DialogDescription>
            {employeeName ? `Interview assessment for ${employeeName}` : 'Create interview assessment record'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Interview Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="interview_date">Interview Date *</Label>
              <Input
                id="interview_date"
                type="date"
                value={formData.interview_date}
                onChange={(e) => setFormData({...formData, interview_date: e.target.value})}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="interview_method">Interview Method *</Label>
              <Select 
                value={formData.interview_method}
                onValueChange={(v) => setFormData({...formData, interview_method: v})}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select method" />
                </SelectTrigger>
                <SelectContent>
                  {INTERVIEW_METHODS.map(m => (
                    <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label htmlFor="interviewer_name">Interviewer Name</Label>
            <Input
              id="interviewer_name"
              value={formData.interviewer_name}
              onChange={(e) => setFormData({...formData, interviewer_name: e.target.value})}
              placeholder="Auto-filled from your account if left blank"
              className="mt-1"
            />
          </div>

          {/* Assessment Scores */}
          <div className="bg-gray-50 p-4 rounded-lg space-y-3">
            <h4 className="font-medium text-sm text-gray-700">Assessment Scores</h4>
            
            <div className="flex items-center justify-between">
              <Label className="text-sm">Communication Skills</Label>
              <RatingStars 
                value={formData.communication_score}
                onChange={(v) => setFormData({...formData, communication_score: v})}
              />
            </div>
            
            <div className="flex items-center justify-between">
              <Label className="text-sm">Experience Match</Label>
              <RatingStars 
                value={formData.experience_score}
                onChange={(v) => setFormData({...formData, experience_score: v})}
              />
            </div>
            
            <div className="flex items-center justify-between">
              <Label className="text-sm">Values Alignment</Label>
              <RatingStars 
                value={formData.values_score}
                onChange={(v) => setFormData({...formData, values_score: v})}
              />
            </div>

            <div className="pt-2 border-t text-sm text-gray-500">
              Average Score: {((formData.communication_score + formData.experience_score + formData.values_score) / 3).toFixed(1)} / 5
            </div>
          </div>

          <div>
            <Label htmlFor="availability">Availability</Label>
            <Input
              id="availability"
              value={formData.availability}
              onChange={(e) => setFormData({...formData, availability: e.target.value})}
              placeholder="e.g., Full-time, weekdays only, etc."
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="strengths">Strengths</Label>
            <Textarea
              id="strengths"
              value={formData.strengths}
              onChange={(e) => setFormData({...formData, strengths: e.target.value})}
              placeholder="Key strengths observed during interview..."
              className="mt-1 min-h-[80px]"
            />
          </div>

          <div>
            <Label htmlFor="areas_for_development">Areas for Development</Label>
            <Textarea
              id="areas_for_development"
              value={formData.areas_for_development}
              onChange={(e) => setFormData({...formData, areas_for_development: e.target.value})}
              placeholder="Areas that need improvement or training..."
              className="mt-1 min-h-[80px]"
            />
          </div>

          {/* Decision */}
          <div className="bg-blue-50 p-4 rounded-lg">
            <Label htmlFor="decision" className="text-blue-800 font-medium">Interview Decision *</Label>
            <Select 
              value={formData.decision}
              onValueChange={(v) => setFormData({...formData, decision: v})}
            >
              <SelectTrigger className="mt-2 bg-white">
                <SelectValue placeholder="Select decision" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Approve">
                  <span className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500" /> Approve
                  </span>
                </SelectItem>
                <SelectItem value="On Hold">
                  <span className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-amber-500" /> On Hold
                  </span>
                </SelectItem>
                <SelectItem value="Reject">
                  <span className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-500" /> Reject
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="notes">Additional Notes</Label>
            <Textarea
              id="notes"
              value={formData.notes}
              onChange={(e) => setFormData({...formData, notes: e.target.value})}
              placeholder="Any other observations or notes..."
              className="mt-1 min-h-[60px]"
            />
          </div>
        </div>

        <DialogFooter className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => handleCreateInterview(true)}
            disabled={saving}
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
            Save as Draft
          </Button>
          <Button
            onClick={() => handleCreateInterview(false)}
            disabled={saving || !formData.decision}
            className="bg-primary hover:bg-primary/90"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <CheckCircle className="h-4 w-4 mr-2" />}
            Submit Record
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    </>
  );
}
