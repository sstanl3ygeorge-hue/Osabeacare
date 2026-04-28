import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { 
  Briefcase, Calendar, AlertTriangle, CheckCircle, XCircle, 
  Clock, FileText, ChevronDown, ChevronUp, Shield, Heart,
  GraduationCap, Loader2, AlertCircle, Edit
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_BASE_URL;

/**
 * ApplicationDataPanel - Displays application form data in compliance tab
 * Shows: Employment History, Employment Gaps, Declarations, Qualifications
 */
export default function ApplicationDataPanel({ employeeId, onRefresh, onEditDeclarations }) {
  const [employee, setEmployee] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedSections, setExpandedSections] = useState({
    employment: true,
    gaps: true,
    declarations: true,
    qualifications: false
  });

  useEffect(() => {
    fetchEmployeeData();
  }, [employeeId]);

  const fetchEmployeeData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      // Fetch employee data
      const response = await axios.get(`${API}/employees/${employeeId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      let employeeData = response.data;
      
      // If employee doesn't have employment_history, try to fetch from application form submission
      if (!employeeData.employment_history || employeeData.employment_history.length === 0) {
        try {
          const formResponse = await axios.get(`${API}/form-submissions?employee_id=${employeeId}&requirement_id=application_form`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          const appForm = formResponse.data?.[0];
          if (appForm?.form_data?.employment_history) {
            employeeData = {
              ...employeeData,
              employment_history: appForm.form_data.employment_history,
              has_employment_gaps: appForm.form_data.has_employment_gaps,
              employment_gap_explanation: appForm.form_data.employment_gap_explanation,
              // Also get declarations if not present
              declarations: employeeData.declarations || {
                has_criminal_convictions: appForm.form_data.criminal_declaration?.has_criminal_convictions,
                criminal_convictions_details: appForm.form_data.criminal_declaration?.conviction_details,
                dbs_consent_given: appForm.form_data.criminal_declaration?.consents_to_dbs_check,
                has_health_conditions: appForm.form_data.health_declaration?.has_health_conditions,
                health_conditions_details: appForm.form_data.health_declaration?.health_condition_details,
                has_rtw_restrictions: !appForm.form_data.right_to_work?.has_unlimited_right_to_work,
                rtw_restrictions_details: appForm.form_data.right_to_work?.visa_type,
              }
            };
          }
        } catch (formError) {
          console.warn('Could not fetch application form data:', formError);
        }
      }
      
      setEmployee(employeeData);
    } catch (error) {
      console.error('Failed to fetch employee data:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const getGapStatusBadge = (status) => {
    switch (status) {
      case 'verified':
        return <Badge className="bg-green-100 text-green-700 border-green-200"><CheckCircle className="h-3 w-3 mr-1" />Verified</Badge>;
      case 'needs_more_info':
        return <Badge className="bg-amber-100 text-amber-700 border-amber-200"><AlertCircle className="h-3 w-3 mr-1" />Info Requested</Badge>;
      case 'rejected':
        return <Badge className="bg-red-100 text-red-700 border-red-200"><XCircle className="h-3 w-3 mr-1" />Rejected</Badge>;
      default:
        return <Badge className="bg-gray-100 text-gray-600"><Clock className="h-3 w-3 mr-1" />Pending</Badge>;
    }
  };

  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-12 flex justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  if (!employee) {
    return null;
  }

  const employmentHistory = employee.employment_history || [];
  const employmentGaps = employee.employment_gaps || [];
  const hasGaps = employee.has_employment_gaps || employmentGaps.length > 0;
  const cvExtractedRoles = employee.cv_extracted_roles || [];

  return (
    <div className="space-y-4" data-testid="application-data-panel">
      {/* Employment History Section */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader 
          className="cursor-pointer hover:bg-gray-50 transition-colors"
          onClick={() => toggleSection('employment')}
        >
          <div className="flex items-center justify-between">
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Briefcase className="h-5 w-5 text-primary" />
              Employment History
              <Badge variant="outline" className="ml-2">
                {employmentHistory.length} positions
              </Badge>
            </CardTitle>
            <div className="flex items-center gap-2">
              {employee.employment_history_mismatch && (
                <Badge className="bg-amber-100 text-amber-700 border-amber-200">
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  Mismatch Detected
                </Badge>
              )}
              {expandedSections.employment ? (
                <ChevronUp className="h-5 w-5 text-gray-400" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-400" />
              )}
            </div>
          </div>
        </CardHeader>
        
        {expandedSections.employment && (
          <CardContent>
            {employmentHistory.length === 0 ? (
              <div className="text-center py-6 text-gray-500">
                <Briefcase className="h-10 w-10 mx-auto mb-2 text-gray-300" />
                <p>No employment history recorded</p>
                <p className="text-xs mt-1">Employment history should be provided in the application form</p>
              </div>
            ) : (
              <div className="space-y-3">
                {/* Timeline visualization */}
                <div className="relative">
                  {employmentHistory.map((job, index) => (
                    <div key={index} className="flex gap-4 pb-4">
                      {/* Timeline line */}
                      <div className="flex flex-col items-center">
                        <div className={`w-3 h-3 rounded-full ${
                          !job.end_date ? 'bg-green-500' : 'bg-blue-500'
                        }`} />
                        {index < employmentHistory.length - 1 && (
                          <div className="w-0.5 h-full bg-gray-200 mt-1" />
                        )}
                      </div>
                      
                      {/* Job details */}
                      <div className={`flex-1 p-3 rounded-lg border ${
                        !job.end_date ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'
                      }`}>
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-medium text-gray-900">{job.role || 'Unknown Role'}</p>
                            <p className="text-sm text-gray-600">{job.company || 'Unknown Company'}</p>
                          </div>
                          {!job.end_date && (
                            <Badge className="bg-green-100 text-green-700">Current</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                          <Calendar className="h-3 w-3" />
                          <span>
                            {formatBackendDate(job.start_date)} - {job.end_date ? formatBackendDate(job.end_date) : 'Present'}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                
                {/* CV Extracted Roles (if different) */}
                {cvExtractedRoles.length > 0 && employee.employment_history_mismatch && (
                  <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <p className="text-sm font-medium text-amber-800 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" />
                      CV Contains Different Information
                    </p>
                    <p className="text-xs text-amber-700 mt-1">
                      {employee.employment_history_mismatch_count} mismatches detected between application and CV
                    </p>
                    {employee.employment_mismatch_reviewed && (
                      <p className="text-xs text-green-700 mt-2">
                        <CheckCircle className="h-3 w-3 inline mr-1" />
                        Reviewed by {employee.employment_mismatch_reviewed_by} on {formatBackendDate(employee.employment_mismatch_reviewed_at)}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        )}
      </Card>

      {/* Employment Gaps Section */}
      {(hasGaps || employmentGaps.length > 0) && (
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader 
            className="cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => toggleSection('gaps')}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <Clock className="h-5 w-5 text-amber-500" />
                Employment Gaps
                <Badge variant="outline" className="ml-2 border-amber-300 text-amber-700">
                  {employmentGaps.length} gaps
                </Badge>
              </CardTitle>
              <div className="flex items-center gap-2">
                {employee.cv_gaps_all_explained ? (
                  <Badge className="bg-green-100 text-green-700 border-green-200">
                    <CheckCircle className="h-3 w-3 mr-1" />All Explained
                  </Badge>
                ) : (
                  <Badge className="bg-amber-100 text-amber-700 border-amber-200">
                    <AlertTriangle className="h-3 w-3 mr-1" />Requires Review
                  </Badge>
                )}
                {expandedSections.gaps ? (
                  <ChevronUp className="h-5 w-5 text-gray-400" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-400" />
                )}
              </div>
            </div>
          </CardHeader>
          
          {expandedSections.gaps && (
            <CardContent>
              <div className="space-y-3">
                {employmentGaps.map((gap, index) => (
                  <div 
                    key={gap.gap_id || index} 
                    className={`p-4 rounded-lg border ${
                      gap.status === 'verified' ? 'bg-green-50 border-green-200' :
                      gap.status === 'rejected' ? 'bg-red-50 border-red-200' :
                      'bg-amber-50 border-amber-200'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">
                            Gap: {Math.round(gap.duration_months || 0)} months
                          </span>
                          {getGapStatusBadge(gap.status)}
                        </div>
                        <p className="text-sm text-gray-600 mt-1">
                          {formatBackendDate(gap.gap_start)} → {formatBackendDate(gap.gap_end)}
                        </p>
                        {gap.previous_employment && (
                          <p className="text-xs text-gray-500 mt-2">
                            After: {gap.previous_employment.role} at {gap.previous_employment.company}
                          </p>
                        )}
                        {gap.next_employment && (
                          <p className="text-xs text-gray-500">
                            Before: {gap.next_employment.role} at {gap.next_employment.company}
                          </p>
                        )}
                      </div>
                    </div>
                    
                    {gap.explanation && (
                      <div className="mt-3 p-2 bg-white/80 rounded border border-gray-200">
                        <p className="text-xs font-medium text-gray-500 uppercase">Explanation</p>
                        <p className="text-sm text-gray-700 mt-1">{gap.explanation}</p>
                      </div>
                    )}
                    
                    {gap.verified_by && (
                      <p className="text-xs text-gray-500 mt-2">
                        Verified by {gap.verified_by} on {formatBackendDate(gap.verified_at)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          )}
        </Card>
      )}

      {/* Declarations Section */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader 
          className="cursor-pointer hover:bg-gray-50 transition-colors"
          onClick={() => toggleSection('declarations')}
        >
          <div className="flex items-center justify-between">
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Applicant Declarations
            </CardTitle>
            <div className="flex items-center gap-2">
              {onEditDeclarations && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEditDeclarations(employee);
                  }}
                  className="h-7 px-2 text-gray-500 hover:text-primary"
                  data-testid="edit-declarations-btn"
                >
                  <Edit className="h-3.5 w-3.5 mr-1" />
                  Edit
                </Button>
              )}
              {expandedSections.declarations ? (
                <ChevronUp className="h-5 w-5 text-gray-400" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-400" />
              )}
            </div>
          </div>
        </CardHeader>
        
        {expandedSections.declarations && (
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Criminal Convictions */}
              <div className={`p-4 rounded-lg border ${
                (employee.declarations?.has_criminal_convictions || employee.criminal_offence_declared === 'Yes') 
                  ? 'bg-amber-50 border-amber-200' : 'bg-green-50 border-green-200'
              }`}>
                <div className="flex items-center gap-2">
                  <Shield className={`h-5 w-5 ${
                    (employee.declarations?.has_criminal_convictions || employee.criminal_offence_declared === 'Yes') 
                      ? 'text-amber-600' : 'text-green-600'
                  }`} />
                  <span className="font-medium">Criminal Convictions</span>
                </div>
                <p className={`text-sm mt-2 ${
                  (employee.declarations?.has_criminal_convictions || employee.criminal_offence_declared === 'Yes') 
                    ? 'text-amber-700' : 'text-green-700'
                }`}>
                  {(employee.declarations?.has_criminal_convictions || employee.criminal_offence_declared === 'Yes') ? (
                    <>
                      <AlertTriangle className="h-4 w-4 inline mr-1" />
                      Declared - Requires Review
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-4 w-4 inline mr-1" />
                      None Declared
                    </>
                  )}
                </p>
                {(employee.declarations?.criminal_convictions_details || employee.criminal_offence_details) && (
                  <p className="text-xs text-gray-600 mt-2 p-2 bg-white/80 rounded">
                    {employee.declarations?.criminal_convictions_details || employee.criminal_offence_details}
                  </p>
                )}
              </div>

              {/* Health Declaration */}
              <div className={`p-4 rounded-lg border ${
                (employee.declarations?.has_health_conditions || employee.health_issue_declared === 'Yes') 
                  ? 'bg-amber-50 border-amber-200' : 'bg-green-50 border-green-200'
              }`}>
                <div className="flex items-center gap-2">
                  <Heart className={`h-5 w-5 ${
                    (employee.declarations?.has_health_conditions || employee.health_issue_declared === 'Yes') 
                      ? 'text-amber-600' : 'text-green-600'
                  }`} />
                  <span className="font-medium">Health Conditions</span>
                </div>
                <p className={`text-sm mt-2 ${
                  (employee.declarations?.has_health_conditions || employee.health_issue_declared === 'Yes') 
                    ? 'text-amber-700' : 'text-green-700'
                }`}>
                  {(employee.declarations?.has_health_conditions || employee.health_issue_declared === 'Yes') ? (
                    <>
                      <AlertTriangle className="h-4 w-4 inline mr-1" />
                      Declared - May Require Adjustments
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-4 w-4 inline mr-1" />
                      None Declared
                    </>
                  )}
                </p>
                {(employee.declarations?.health_conditions_details || employee.health_issue_details) && (
                  <p className="text-xs text-gray-600 mt-2 p-2 bg-white/80 rounded">
                    {employee.declarations?.health_conditions_details || employee.health_issue_details}
                  </p>
                )}
              </div>

              {/* DBS Consent */}
              <div className={`p-4 rounded-lg border ${
                (employee.declarations?.dbs_consent_given || employee.dbs_update_service_consent || employee.has_dbs_declared) 
                  ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'
              }`}>
                <div className="flex items-center gap-2">
                  <FileText className={`h-5 w-5 ${
                    (employee.declarations?.dbs_consent_given || employee.dbs_update_service_consent || employee.has_dbs_declared) 
                      ? 'text-green-600' : 'text-gray-500'
                  }`} />
                  <span className="font-medium">DBS Check Consent</span>
                </div>
                <p className={`text-sm mt-2 ${
                  (employee.declarations?.dbs_consent_given || employee.dbs_update_service_consent || employee.has_dbs_declared) 
                    ? 'text-green-700' : 'text-gray-600'
                }`}>
                  {(employee.declarations?.dbs_consent_given || employee.dbs_update_service_consent || employee.has_dbs_declared) ? (
                    <>
                      <CheckCircle className="h-4 w-4 inline mr-1" />
                      Consent Given for Enhanced DBS Check
                    </>
                  ) : (
                    'No consent recorded'
                  )}
                </p>
              </div>

              {/* Driving Licence */}
              <div className={`p-4 rounded-lg border ${
                employee.has_driving_licence ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'
              }`}>
                <div className="flex items-center gap-2">
                  <FileText className={`h-5 w-5 ${
                    employee.has_driving_licence ? 'text-blue-600' : 'text-gray-500'
                  }`} />
                  <span className="font-medium">Driving Licence</span>
                </div>
                <p className={`text-sm mt-2 ${
                  employee.has_driving_licence ? 'text-blue-700' : 'text-gray-600'
                }`}>
                  {employee.has_driving_licence ? (
                    <>
                      <CheckCircle className="h-4 w-4 inline mr-1" />
                      {employee.driver_status || 'Has Licence'}
                    </>
                  ) : (
                    'No driving licence'
                  )}
                </p>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Qualifications Section */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader 
          className="cursor-pointer hover:bg-gray-50 transition-colors"
          onClick={() => toggleSection('qualifications')}
        >
          <div className="flex items-center justify-between">
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <GraduationCap className="h-5 w-5 text-primary" />
              Qualifications & Education
            </CardTitle>
            {expandedSections.qualifications ? (
              <ChevronUp className="h-5 w-5 text-gray-400" />
            ) : (
              <ChevronDown className="h-5 w-5 text-gray-400" />
            )}
          </div>
        </CardHeader>
        
        {expandedSections.qualifications && (
          <CardContent>
            {!employee.qualifications && !employee.education ? (
              <div className="text-center py-6 text-gray-500">
                <GraduationCap className="h-10 w-10 mx-auto mb-2 text-gray-300" />
                <p>No qualifications or education recorded</p>
                <p className="text-xs mt-1">Qualifications should be added in the Training tab</p>
              </div>
            ) : (
              <div className="space-y-3">
                {employee.qualifications && (
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="font-medium">Qualifications</p>
                    <p className="text-sm text-gray-600 mt-1">{employee.qualifications}</p>
                  </div>
                )}
                {employee.education && (
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="font-medium">Education</p>
                    <p className="text-sm text-gray-600 mt-1">{employee.education}</p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        )}
      </Card>
    </div>
  );
}

