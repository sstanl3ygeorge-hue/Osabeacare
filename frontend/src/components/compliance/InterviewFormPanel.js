import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { 
  ClipboardList, Download, CheckCircle, Clock, AlertTriangle,
  Loader2, RefreshCw, User, Calendar, FileText, ChevronDown,
  ChevronRight, Plus, Edit, Save, HelpCircle, Info, Eye
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { formatBackendDate } from '../../lib/dateUtils';
import InlineDocumentViewer from '../shared/InlineDocumentViewer';

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

// Osabea 0-3 scoring scale
const SCORE_OPTIONS = [
  { value: 0, label: '0 - Does not meet criteria', color: 'bg-red-100 text-red-700 border-red-200' },
  { value: 1, label: '1 - Part meets criteria', color: 'bg-amber-100 text-amber-700 border-amber-200' },
  { value: 2, label: '2 - Meets criteria', color: 'bg-blue-100 text-blue-700 border-blue-200' },
  { value: 3, label: '3 - Exceeds criteria', color: 'bg-green-100 text-green-700 border-green-200' }
];

// Score selector component (0-3 scale buttons)
const ScoreSelector = ({ value, onChange, disabled = false }) => (
  <div className="flex gap-1">
    {SCORE_OPTIONS.map(option => (
      <button
        key={option.value}
        type="button"
        onClick={() => !disabled && onChange(option.value)}
        disabled={disabled}
        className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-all ${
          value === option.value 
            ? option.color + ' ring-2 ring-offset-1' 
            : 'bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        {option.value}
      </button>
    ))}
  </div>
);

// Question card with scoring criteria tooltip
const QuestionCard = ({ question, score, onChange, notes, onNotesChange, disabled, workerAnswer }) => {
  const [showCriteria, setShowCriteria] = useState(false);
  
  return (
    <div className="border rounded-lg p-4 bg-white space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
              Q{question.order}
            </span>
            <span className="text-xs text-gray-400 capitalize">
              {question.category?.replace(/_/g, ' ')}
            </span>
          </div>
          <p className="font-medium text-gray-900 text-sm leading-relaxed">
            {question.question}
          </p>
          {question.skills_assessed && (
            <p className="text-xs text-gray-500 mt-1">
              <span className="font-medium">Assessing:</span> {question.skills_assessed}
            </p>
          )}
        </div>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <button 
                type="button"
                onClick={() => setShowCriteria(!showCriteria)}
                className="p-1.5 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600"
              >
                <HelpCircle className="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="left" className="max-w-md p-0">
              <div className="p-3 space-y-2">
                <p className="font-medium text-sm">Scoring Criteria:</p>
                {question.scoring_criteria && Object.entries(question.scoring_criteria).map(([score, text]) => (
                  <div key={score} className="flex gap-2 text-xs">
                    <span className={`px-1.5 py-0.5 rounded font-medium ${
                      score === '0' ? 'bg-red-100 text-red-700' :
                      score === '1' ? 'bg-amber-100 text-amber-700' :
                      score === '2' ? 'bg-blue-100 text-blue-700' :
                      'bg-green-100 text-green-700'
                    }`}>{score}</span>
                    <span className="text-gray-600">{text}</span>
                  </div>
                ))}
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      
      {/* Expanded criteria (toggle) */}
      {showCriteria && question.scoring_criteria && (
        <div className="bg-gray-50 rounded-lg p-3 space-y-1.5 text-xs">
          {Object.entries(question.scoring_criteria).map(([s, text]) => (
            <div key={s} className="flex gap-2">
              <span className={`px-1.5 py-0.5 rounded font-medium shrink-0 ${
                s === '0' ? 'bg-red-100 text-red-700' :
                s === '1' ? 'bg-amber-100 text-amber-700' :
                s === '2' ? 'bg-blue-100 text-blue-700' :
                'bg-green-100 text-green-700'
              }`}>{s}</span>
              <span className="text-gray-600">{text}</span>
            </div>
          ))}
        </div>
      )}
      
      {/* Worker's pre-interview answer (read-only source material) */}
      {workerAnswer && (
        <div className="bg-violet-50 border border-violet-200 rounded-lg p-3">
          <p className="text-xs font-medium text-violet-700 mb-1 flex items-center gap-1">
            <User className="h-3 w-3" />
            Worker's answer:
          </p>
          <p className="text-sm text-violet-900 whitespace-pre-wrap">{workerAnswer}</p>
        </div>
      )}

      <div className="flex items-center justify-between pt-2 border-t">
        <Label className="text-xs text-gray-500">Score:</Label>
        <ScoreSelector value={score} onChange={onChange} disabled={disabled} />
      </div>
      
      <Textarea
        placeholder="Notes for this question (optional)..."
        value={notes || ''}
        onChange={(e) => onNotesChange(e.target.value)}
        disabled={disabled}
        className="min-h-[60px] text-sm"
      />
    </div>
  );
};

export default function InterviewFormPanel({ employeeId, employeeName, employeeRole }) {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
  const [downloading, setDownloading] = useState(null);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerUrl, setViewerUrl] = useState(null);
  const [viewerTitle, setViewerTitle] = useState('Interview Assessment');
  const [viewerFilename, setViewerFilename] = useState('interview_record.pdf');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [saving, setSaving] = useState(false);
  const [interviewConfig, setInterviewConfig] = useState(null);
  const [activeTab, setActiveTab] = useState('part1');
  const [workerAnswers, setWorkerAnswers] = useState(null); // Worker pre-interview data
  const [prefilled, setPrefilled] = useState(false); // Whether form was prefilled from worker answers
  
  // Form state
  const [formData, setFormData] = useState({
    interview_date: new Date().toISOString().split('T')[0],
    interview_method: 'in_person',
    interviewer_name: '',
    candidate_name: employeeName || '',
    vacancy_job_title: 'Care Worker',
    panel_members: '',
    question_scores: {},  // {question_id: score}
    question_notes: {},   // {question_id: notes}
    // Part 2 - Admin questions
    requires_work_permit: '',
    rtw_proof_taken: '',
    hours_wanted: '',
    flexible_working: '',
    has_driving_licence: '',
    annual_leave_booked: '',
    notice_period: '',
    start_date: '',
    // Decision
    decision: '',
    overall_impression: '',
    candidate_questions: '',
    notes: ''
  });
  const [editingId, setEditingId] = useState(null);

  // Fetch interview configuration (questions based on role)
  const fetchInterviewConfig = async () => {
    try {
      const token = localStorage.getItem('token');
      const role = employeeRole || 'support_worker';
      const response = await axios.get(`${API}/interview-config/${role}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setInterviewConfig(response.data);
    } catch (error) {
      console.error('Failed to fetch interview config:', error);
      // Use default config if endpoint fails
      setInterviewConfig({
        questions: [],
        scoring: { scale: { min: 0, max: 3 }, minimum_total_score: 11 },
        administrative_questions: []
      });
    }
  };

  const fetchInterviews = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      const response = await axios.get(`${API}/employees/${employeeId}/interview-records`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setInterviews(response.data.records || []);
    } catch (error) {
      console.error('Failed to fetch interview records:', error);
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
      fetchInterviewConfig();
    }
  }, [employeeId, employeeRole]);

  // Part 2 field mapping: worker admin_q IDs -> admin interview field IDs
  const WORKER_TO_ADMIN_MAP = {
    admin_q1: 'requires_work_permit',
    admin_q2: 'rtw_proof_taken',
    admin_q3: 'hours_wanted',
    admin_q4: 'flexible_working',
    admin_q5: 'has_driving_licence',
    admin_q6: 'annual_leave_booked',
    admin_q7: 'notice_period',
    admin_q8: 'start_date'
  };

  // Normalise yes_no checkbox values from worker form to admin Select values
  const normaliseYesNo = (val) => {
    if (val === true || val === 'true' || val === 'yes' || val === 'Yes') return 'yes';
    if (val === false || val === 'false' || val === 'no' || val === 'No') return 'no';
    return val || '';
  };

  // Fetch worker pre-interview questionnaire and prefill form
  const fetchWorkerPreInterview = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API}/employees/${employeeId}/pre-interview-questionnaire`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const data = response.data;
      if (data.status === 'not_submitted' || !data.form_data) {
        setWorkerAnswers(null);
        setPrefilled(false);
        return;
      }
      const wd = data.form_data;
      setWorkerAnswers(wd);

      // Prefill Part 2 admin fields from worker's admin_q answers
      const part2Updates = {};
      for (const [workerKey, adminKey] of Object.entries(WORKER_TO_ADMIN_MAP)) {
        if (wd[workerKey] !== undefined && wd[workerKey] !== '' && wd[workerKey] !== null) {
          // yes_no fields need normalisation
          if (['admin_q1', 'admin_q4', 'admin_q5'].includes(workerKey)) {
            part2Updates[adminKey] = normaliseYesNo(wd[workerKey]);
          } else {
            part2Updates[adminKey] = String(wd[workerKey]);
          }
        }
      }

      setFormData(prev => ({ ...prev, ...part2Updates }));
      setPrefilled(true);
    } catch (error) {
      console.error('Failed to fetch worker pre-interview:', error);
      // Non-blocking — form stays blank if fetch fails
      setWorkerAnswers(null);
      setPrefilled(false);
    }
  };

  const resetForm = () => {
    setFormData({
      interview_date: new Date().toISOString().split('T')[0],
      interview_method: 'in_person',
      interviewer_name: '',
      candidate_name: employeeName || '',
      vacancy_job_title: 'Care Worker',
      panel_members: '',
      question_scores: {},
      question_notes: {},
      requires_work_permit: '',
      rtw_proof_taken: '',
      hours_wanted: '',
      flexible_working: '',
      has_driving_licence: '',
      annual_leave_booked: '',
      notice_period: '',
      start_date: '',
      decision: '',
      overall_impression: '',
      candidate_questions: '',
      notes: ''
    });
    setEditingId(null);
    setActiveTab('part1');
    setWorkerAnswers(null);
    setPrefilled(false);
  };

  // Calculate total score
  const calculateTotalScore = () => {
    const scores = Object.values(formData.question_scores || {});
    return scores.reduce((sum, s) => sum + (parseInt(s) || 0), 0);
  };

  const getMaxScore = () => {
    return (interviewConfig?.questions?.length || 8) * 3;
  };

  const getPassScore = () => {
    return interviewConfig?.scoring?.minimum_total_score || 11;
  };

  const handleCreateInterview = async (isDraft = false) => {
    if (!formData.decision && !isDraft) {
      toast.error('Please select a decision');
      return;
    }
    
    const totalScore = calculateTotalScore();
    const maxScore = getMaxScore();
    const passScore = getPassScore();
    
    try {
      setSaving(true);
      const token = localStorage.getItem('token');
      
      const payload = {
        ...formData,
        total_score: totalScore,
        max_score: maxScore,
        pass_score: passScore,
        passed: totalScore >= passScore,
        percentage: Math.round((totalScore / maxScore) * 100),
        is_draft: isDraft
      };
      
      if (editingId) {
        await axios.put(
          `${API}/employees/${employeeId}/interview-records/${editingId}`,
          payload,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success(isDraft ? 'Draft saved' : 'Interview record updated');
      } else {
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
      interview_method: data.interview_method || 'in_person',
      interviewer_name: data.interviewer_name || '',
      candidate_name: data.candidate_name || employeeName || '',
      vacancy_job_title: data.vacancy_job_title || 'Care Worker',
      panel_members: data.panel_members || '',
      question_scores: data.question_scores || {},
      question_notes: data.question_notes || {},
      requires_work_permit: data.requires_work_permit || '',
      rtw_proof_taken: data.rtw_proof_taken || '',
      hours_wanted: data.hours_wanted || '',
      flexible_working: data.flexible_working || '',
      has_driving_licence: data.has_driving_licence || '',
      annual_leave_booked: data.annual_leave_booked || '',
      notice_period: data.notice_period || '',
      start_date: data.start_date || '',
      decision: data.decision || '',
      overall_impression: data.overall_impression || '',
      candidate_questions: data.candidate_questions || '',
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
        `${API}/form-submissions/${recordId}/download-pdf`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
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

  const handleViewPDF = (recordId) => {
    if (!recordId) {
      toast.error('Interview record not found');
      return;
    }
    setViewerUrl(`${API}/form-submissions/${recordId}/view-pdf`);
    setViewerTitle('Interview Assessment Record');
    setViewerFilename(`interview_record_${employeeName?.replace(/\s+/g, '_') || 'employee'}.pdf`);
    setViewerOpen(true);
  };

  const getDecisionConfig = (decision) => {
    const key = Object.keys(DECISION_CONFIG).find(k => 
      decision?.toLowerCase().includes(k.toLowerCase())
    );
    return key ? DECISION_CONFIG[key] : { color: 'bg-gray-100 text-gray-600', icon: Clock };
  };

  const totalScore = calculateTotalScore();
  const maxScore = getMaxScore();
  const passScore = getPassScore();
  const isPassing = totalScore >= passScore;

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
            Interview Assessment Records (Admin Only)
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
              onClick={() => { resetForm(); setShowCreateDialog(true); fetchWorkerPreInterview(); }}
              className="rounded-xl bg-primary hover:bg-primary/90"
              data-testid="create-interview-btn"
            >
              <Plus className="h-4 w-4 mr-1" />
              Record Interview
            </Button>
          </div>
        </CardTitle>
        <p className="text-sm text-gray-500 mt-1">
          Osabea Interview Assessment - 8 questions, 0-3 scoring scale, minimum 11 points to pass
        </p>
      </CardHeader>
      <CardContent>
        {interviews.length === 0 ? (
          <div className="rounded-lg border-2 border-dashed border-red-200 bg-red-50 p-6 text-center"
            data-testid="interview-required-banner">
            <AlertTriangle className="h-9 w-9 mx-auto mb-3 text-red-400" />
            <p className="font-semibold text-red-700">Interview Not Conducted</p>
            <p className="text-sm text-red-600 mt-1">
              CQC safer recruitment requires a documented interview before progressing.
            </p>
            <p className="text-xs text-red-400 mt-1">
              Record the interview to clear this blocker.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {interviews.map((interview, index) => {
              const fData = interview.form_data || {};
              const decision = fData.decision || fData.overall_decision;
              const decisionConfig = getDecisionConfig(decision);
              const DecisionIcon = decisionConfig.icon;
              const isExpanded = expandedId === interview.id;
              const score = fData.total_score || 0;
              const max = fData.max_score || 24;
              const adminDisplayStatus = interview.admin_display_status || (
                decision
                  ? (['Reject', 'Not Suitable'].includes(decision) ? 'reviewed_rejected' : 'reviewed_approved')
                  : interview.status
              );
              const adminDisplayLabel = interview.admin_display_label || (
                adminDisplayStatus === 'reviewed_approved' ? 'Reviewed - approved' :
                adminDisplayStatus === 'reviewed_rejected' ? 'Reviewed - rejected' :
                adminDisplayStatus === 'reviewed_passed' ? 'Reviewed - passed' :
                adminDisplayStatus === 'reviewed_failed' ? 'Reviewed - failed' :
                adminDisplayStatus === 'signed_off' || adminDisplayStatus === 'verified' ? 'Reviewed' :
                String(adminDisplayStatus || 'Submitted, not reviewed').replace(/_/g, ' ')
              );
              
              return (
                <div 
                  key={interview.id || index}
                  className="border rounded-xl overflow-hidden"
                  data-testid={`interview-record-${index}`}
                >
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
                          Interview Assessment
                        </p>
                        <div className="flex items-center gap-3 text-xs text-gray-500">
                          {fData.interview_date && (
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {formatBackendDate(fData.interview_date)}
                            </span>
                          )}
                          {fData.interviewer_name && (
                            <span className="flex items-center gap-1">
                              <User className="h-3 w-3" />
                              {fData.interviewer_name}
                            </span>
                          )}
                          <span className={`font-medium ${score >= 11 ? 'text-green-600' : 'text-red-600'}`}>
                            Score: {score}/{max}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {/* Outcome status badge (CQC clarity) */}
                      {decision ? (
                        <Badge className={`${decisionConfig.color} flex items-center gap-1`}>
                          <DecisionIcon className="h-3 w-3" />
                          {decision}
                        </Badge>
                      ) : (
                        <Badge className={score >= passScore ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                          {score >= passScore ? 'Completed – Passed' : 'Completed – Failed'}
                        </Badge>
                      )}
                      {interview.status === 'submitted' && adminDisplayStatus !== 'submitted' && (
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                          {adminDisplayLabel}
                        </Badge>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleViewPDF(interview.id);
                        }}
                        className="rounded-lg"
                        title="View interview PDF"
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
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

                  {isExpanded && (
                    <div className="p-4 border-t bg-white space-y-4">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                        <div className="bg-gray-50 p-3 rounded-lg">
                          <p className="text-xs text-gray-500">Total Score</p>
                          <p className={`font-bold text-lg ${score >= 11 ? 'text-green-600' : 'text-red-600'}`}>
                            {score}/{max}
                          </p>
                        </div>
                        <div className="bg-gray-50 p-3 rounded-lg">
                          <p className="text-xs text-gray-500">Percentage</p>
                          <p className="font-bold text-lg">{fData.percentage || Math.round((score/max)*100)}%</p>
                        </div>
                        <div className="bg-gray-50 p-3 rounded-lg">
                          <p className="text-xs text-gray-500">Pass Threshold</p>
                          <p className="font-medium">{fData.pass_score || 11} points</p>
                        </div>
                        <div className="bg-gray-50 p-3 rounded-lg">
                          <p className="text-xs text-gray-500">Result</p>
                          <Badge className={score >= 11 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                            {score >= 11 ? 'PASSED' : 'FAILED'}
                          </Badge>
                        </div>
                      </div>

                      {fData.overall_impression && (
                        <div>
                          <p className="text-xs font-medium text-gray-500 mb-1">Overall Impression</p>
                          <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg">
                            {fData.overall_impression}
                          </p>
                        </div>
                      )}

                      {fData.notes && (
                        <div>
                          <p className="text-xs font-medium text-gray-500 mb-1">Interviewer Notes</p>
                          <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg">
                            {fData.notes}
                          </p>
                        </div>
                      )}

                      <div className="text-xs text-gray-400 pt-2 border-t flex items-center justify-between">
                        <span>Recorded: {formatBackendDate(interview.submitted_at || interview.created_at)}</span>
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
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-primary" />
            {editingId ? 'Edit Interview Assessment Record' : 'Interview Assessment (Final Scored Admin Record)'}
          </DialogTitle>
          <DialogDescription>
            Osabea Interview Questions – Support Workers | Minimum Score Required: 11 points
          </DialogDescription>
        </DialogHeader>

        {/* Prefill indicator banner */}
        {prefilled && !editingId && (
          <div className="bg-violet-50 border border-violet-200 rounded-lg px-4 py-3 flex items-center gap-2">
            <Info className="h-4 w-4 text-violet-600 shrink-0" />
            <p className="text-sm text-violet-700">
              <span className="font-medium">Prefilled from the worker interview questionnaire.</span>
              {' '}Part 1 shows their written answers. Part 2 admin fields have been pre-populated. All fields remain editable.
            </p>
          </div>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid grid-cols-3 mb-4">
            <TabsTrigger value="part1">Part 1: Assessment</TabsTrigger>
            <TabsTrigger value="part2">Part 2: Admin Questions</TabsTrigger>
            <TabsTrigger value="decision">Decision</TabsTrigger>
          </TabsList>

          {/* Part 1 - Assessment Questions */}
          <TabsContent value="part1" className="space-y-4">
            {/* Interview Info Header */}
            <div className="bg-blue-50 rounded-lg p-4 space-y-3">
              <h4 className="font-medium text-blue-800">Interview Details</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div>
                  <Label className="text-xs">Candidate Name</Label>
                  <Input
                    value={formData.candidate_name}
                    onChange={(e) => setFormData({...formData, candidate_name: e.target.value})}
                    placeholder={employeeName}
                    className="mt-1 bg-white"
                  />
                </div>
                <div>
                  <Label className="text-xs">Job Title</Label>
                  <Input
                    value={formData.vacancy_job_title}
                    onChange={(e) => setFormData({...formData, vacancy_job_title: e.target.value})}
                    className="mt-1 bg-white"
                  />
                </div>
                <div>
                  <Label className="text-xs">Interview Date</Label>
                  <Input
                    type="date"
                    value={formData.interview_date}
                    onChange={(e) => setFormData({...formData, interview_date: e.target.value})}
                    className="mt-1 bg-white"
                  />
                </div>
                <div>
                  <Label className="text-xs">Panel Members</Label>
                  <Input
                    value={formData.panel_members}
                    onChange={(e) => setFormData({...formData, panel_members: e.target.value})}
                    placeholder="Names..."
                    className="mt-1 bg-white"
                  />
                </div>
              </div>
            </div>

            {/* Score Summary */}
            <div className={`p-3 rounded-lg flex items-center justify-between ${isPassing ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'}`}>
              <div className="flex items-center gap-3">
                <Info className={`h-5 w-5 ${isPassing ? 'text-green-600' : 'text-amber-600'}`} />
                <span className="text-sm font-medium">
                  Current Score: <span className={isPassing ? 'text-green-700' : 'text-amber-700'}>{totalScore}/{maxScore}</span>
                </span>
              </div>
              <Badge className={isPassing ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}>
                {isPassing ? 'Passing' : `Need ${passScore - totalScore} more points`}
              </Badge>
            </div>

            {/* Assessment Questions */}
            <div className="space-y-4">
              <h4 className="font-medium text-gray-700 border-b pb-2">
                Assessment Questions (Score each 0-3)
              </h4>
              
              {(interviewConfig?.questions || []).map((question) => (
                <QuestionCard
                  key={question.id}
                  question={question}
                  score={formData.question_scores[question.id] ?? null}
                  onChange={(score) => setFormData({
                    ...formData, 
                    question_scores: {...formData.question_scores, [question.id]: score}
                  })}
                  notes={formData.question_notes[question.id] || ''}
                  onNotesChange={(notes) => setFormData({
                    ...formData,
                    question_notes: {...formData.question_notes, [question.id]: notes}
                  })}
                  workerAnswer={!editingId && workerAnswers ? workerAnswers[question.id] : undefined}
                />
              ))}
            </div>
          </TabsContent>

          {/* Part 2 - Administrative Questions */}
          <TabsContent value="part2" className="space-y-4">
            {prefilled && !editingId && (
              <div className="bg-violet-50 border border-violet-200 rounded-lg px-4 py-2 text-sm text-violet-700 flex items-center gap-2">
                <User className="h-4 w-4 text-violet-600 shrink-0" />
                Fields below were pre-populated from the worker's answers. Review and adjust as needed.
              </div>
            )}
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="font-medium text-gray-700 mb-4">General Interview Questions</h4>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Do you require a Work Permit?</Label>
                    <Select 
                      value={formData.requires_work_permit}
                      onValueChange={(v) => setFormData({...formData, requires_work_permit: v})}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder="Select..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="yes">Yes</SelectItem>
                        <SelectItem value="no">No</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Proof of RTW taken?</Label>
                    <Input
                      value={formData.rtw_proof_taken}
                      onChange={(e) => setFormData({...formData, rtw_proof_taken: e.target.value})}
                      placeholder="e.g., Passport, BRP, Share Code..."
                      className="mt-1"
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>How many hours do you want to work?</Label>
                    <Input
                      value={formData.hours_wanted}
                      onChange={(e) => setFormData({...formData, hours_wanted: e.target.value})}
                      placeholder="e.g., 40 hours/week"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label>Able to participate in flexible working?</Label>
                    <Select 
                      value={formData.flexible_working}
                      onValueChange={(v) => setFormData({...formData, flexible_working: v})}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder="Select..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="yes">Yes</SelectItem>
                        <SelectItem value="no">No</SelectItem>
                        <SelectItem value="limited">Limited</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Full and valid driver's licence?</Label>
                    <Select 
                      value={formData.has_driving_licence}
                      onValueChange={(v) => setFormData({...formData, has_driving_licence: v})}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder="Select..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="yes_full">Yes - Full Licence</SelectItem>
                        <SelectItem value="yes_provisional">Yes - Provisional</SelectItem>
                        <SelectItem value="no">No</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Any annual leave booked?</Label>
                    <Input
                      value={formData.annual_leave_booked}
                      onChange={(e) => setFormData({...formData, annual_leave_booked: e.target.value})}
                      placeholder="e.g., None, 2 weeks in August..."
                      className="mt-1"
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Notice period required?</Label>
                    <Input
                      value={formData.notice_period}
                      onChange={(e) => setFormData({...formData, notice_period: e.target.value})}
                      placeholder="e.g., 2 weeks, 1 month..."
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label>When could you start?</Label>
                    <Input
                      type="date"
                      value={formData.start_date}
                      onChange={(e) => setFormData({...formData, start_date: e.target.value})}
                      className="mt-1"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Pre-Employment Checks */}
            <div className="bg-amber-50 rounded-lg p-4">
              <h4 className="font-medium text-amber-800 mb-2">Pre-Employment Checks to Complete</h4>
              <ul className="text-sm text-amber-700 space-y-1 list-disc list-inside">
                <li>Explore sickness information on application form</li>
                <li>Check references cover past 2 years with gaps accounted for</li>
                <li>Check Rehabilitation of Offenders Act declaration</li>
                <li>Take copy of eligibility to work in UK documents</li>
                <li>Inform of DBS Check requirement</li>
              </ul>
            </div>
          </TabsContent>

          {/* Decision Tab */}
          <TabsContent value="decision" className="space-y-4">
            {/* Final Score Summary */}
            <div className={`p-4 rounded-lg ${isPassing ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
              <div className="flex items-center justify-between mb-3">
                <h4 className={`font-medium ${isPassing ? 'text-green-800' : 'text-red-800'}`}>
                  Assessment Summary
                </h4>
                <Badge className={isPassing ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                  {isPassing ? 'MEETS THRESHOLD' : 'BELOW THRESHOLD'}
                </Badge>
              </div>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold">{totalScore}</p>
                  <p className="text-xs text-gray-500">Total Score</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">{maxScore}</p>
                  <p className="text-xs text-gray-500">Maximum</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">{Math.round((totalScore/maxScore)*100)}%</p>
                  <p className="text-xs text-gray-500">Percentage</p>
                </div>
              </div>
            </div>

            <div>
              <Label>Candidate's Questions</Label>
              <Textarea
                value={formData.candidate_questions}
                onChange={(e) => setFormData({...formData, candidate_questions: e.target.value})}
                placeholder="Record any questions the candidate asked and answers given..."
                className="mt-1 min-h-[80px]"
              />
            </div>

            <div>
              <Label>Overall Impression</Label>
              <Textarea
                value={formData.overall_impression}
                onChange={(e) => setFormData({...formData, overall_impression: e.target.value})}
                placeholder="General comments on candidate's suitability, attitude, professionalism..."
                className="mt-1 min-h-[80px]"
              />
            </div>

            {/* Decision */}
            <div className="bg-blue-50 p-4 rounded-lg">
              <Label className="text-blue-800 font-medium">Interview Decision *</Label>
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
                      <CheckCircle className="h-4 w-4 text-green-500" /> Successful - Approve
                    </span>
                  </SelectItem>
                  <SelectItem value="On Hold">
                    <span className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-amber-500" /> On Hold - Further Review
                    </span>
                  </SelectItem>
                  <SelectItem value="Reject">
                    <span className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-red-500" /> Not Successful - Reject
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Additional Notes</Label>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                placeholder="Any other observations..."
                className="mt-1 min-h-[60px]"
              />
            </div>

            <div>
              <Label>Interviewer Name</Label>
              <Input
                value={formData.interviewer_name}
                onChange={(e) => setFormData({...formData, interviewer_name: e.target.value})}
                placeholder="Your name (for signature)"
                className="mt-1"
              />
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter className="flex gap-2 pt-4 border-t">
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
    <InlineDocumentViewer
      open={viewerOpen}
      onClose={() => setViewerOpen(false)}
      fetchUrl={viewerUrl}
      title={viewerTitle}
      token={localStorage.getItem('token')}
      filename={viewerFilename}
    />
    </>
  );
}
