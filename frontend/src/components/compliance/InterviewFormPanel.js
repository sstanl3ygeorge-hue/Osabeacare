import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { 
  ClipboardList, Download, CheckCircle, Clock, AlertTriangle,
  Loader2, RefreshCw, User, Calendar, FileText, ChevronDown,
  ChevronRight
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DECISION_CONFIG = {
  'Hire': { color: 'bg-green-100 text-green-700', icon: CheckCircle },
  'Strong Hire': { color: 'bg-green-100 text-green-700', icon: CheckCircle },
  'Consider': { color: 'bg-amber-100 text-amber-700', icon: Clock },
  'Maybe': { color: 'bg-amber-100 text-amber-700', icon: Clock },
  'Not Suitable': { color: 'bg-red-100 text-red-700', icon: AlertTriangle },
  'Reject': { color: 'bg-red-100 text-red-700', icon: AlertTriangle }
};

export default function InterviewFormPanel({ employeeId, employeeName }) {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
  const [downloading, setDownloading] = useState(null);

  const fetchInterviews = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      // Fetch form submissions with requirement_id = interview_record
      const response = await axios.get(`${API}/employees/${employeeId}/forms`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { requirement_id: 'interview_record' }
      });
      
      setInterviews(response.data.forms || response.data || []);
    } catch (error) {
      console.error('Failed to fetch interview records:', error);
      // Try alternative endpoint
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get(`${API}/form-submissions`, {
          headers: { Authorization: `Bearer ${token}` },
          params: { 
            employee_id: employeeId,
            requirement_id: 'interview_record'
          }
        });
        setInterviews(response.data.submissions || response.data || []);
      } catch (err) {
        // Silently fail - interviews are optional
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

  const handleDownloadPDF = async (submissionId) => {
    try {
      setDownloading(submissionId);
      const token = localStorage.getItem('token');
      
      const response = await axios.get(
        `${API}/form-submissions/${submissionId}/download-pdf`,
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
    <Card className="border-[#E4E8EB] shadow-sm">
      <CardHeader>
        <CardTitle className="font-heading text-lg flex items-center justify-between">
          <span className="flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-primary" />
            Interview Records
          </span>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchInterviews}
            disabled={loading}
            className="rounded-xl"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </CardTitle>
        <p className="text-sm text-gray-500 mt-1">
          Completed interview assessments and decisions
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
                      <div className="text-xs text-gray-400 pt-2 border-t flex items-center gap-4">
                        <span>Submitted: {formatBackendDate(interview.submitted_at || interview.created_at)}</span>
                        {interview.submitted_by_name && (
                          <span>By: {interview.submitted_by_name}</span>
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
  );
}
