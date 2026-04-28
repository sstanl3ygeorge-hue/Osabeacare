import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '../ui/sheet';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { 
  Loader2, 
  Download, 
  CheckCircle, 
  XCircle, 
  FileText,
  AlertCircle,
  User,
  Briefcase,
  Phone,
  Mail,
  MapPin,
  Calendar,
  Shield,
  Heart,
  Users,
  Clock,
  FileCheck,
  ChevronDown,
  ChevronUp,
  Printer
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

/**
 * ApplicationFormViewDrawer - Read-only viewer for structured application forms
 * 
 * Unlike FormSubmissionDrawer which requires a template, this drawer renders
 * the structured JSON payload (form_data) from public application submissions.
 * 
 * Sections:
 * - Personal Details
 * - Employment History
 * - References
 * - Declarations
 * - Health Declaration
 * - Criminal Declaration
 * - Right to Work
 */
export default function ApplicationFormViewDrawer({
  isOpen,
  onClose,
  employeeId,
  employeeName,
  submissionId,
  onVerify,
  onReject,
  onRefresh
}) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [submission, setSubmission] = useState(null);
  const [expandedSections, setExpandedSections] = useState({
    personal: true,
    employment: true,
    references: true,
    declarations: false,
    health: false,
    criminal: false,
    right_to_work: false
  });
  const [exportingPdf, setExportingPdf] = useState(false);
  
  // Fetch submission data
  const fetchSubmission = useCallback(async () => {
    if (!submissionId) return;
    
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/form-submissions/${submissionId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSubmission(response.data);
    } catch (err) {
      console.error('Error fetching application form:', err);
      toast.error('Failed to load application form');
    } finally {
      setLoading(false);
    }
  }, [submissionId, token]);
  
  useEffect(() => {
    if (isOpen && submissionId) {
      fetchSubmission();
    }
  }, [isOpen, submissionId, fetchSubmission]);
  
  // Toggle section
  const toggleSection = (key) => {
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));
  };
  
  // Export to PDF
  const handleExportPdf = async () => {
    if (!submissionId) return;
    
    setExportingPdf(true);
    try {
      const response = await axios.get(
        `${API}/form-submissions/${submissionId}/download-pdf`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `application_form_${submissionId}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
      toast.success('Application exported successfully');
    } catch (err) {
      console.error('PDF export error:', err);
      toast.error('Failed to export PDF');
    } finally {
      setExportingPdf(false);
    }
  };
  
  // Print application
  const handlePrint = () => {
    window.print();
  };
  
  // Get status badge
  const getStatusBadge = () => {
    if (!submission) return null;
    
    const status = submission.status;
    
    if (submission.verified || status === 'verified' || status === 'signed_off') {
      return (
        <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200">
          <CheckCircle className="h-3 w-3 mr-1" />
          Verified
        </Badge>
      );
    }
    
    if (status === 'rejected') {
      return (
        <Badge className="bg-red-100 text-red-800 border-red-200">
          <XCircle className="h-3 w-3 mr-1" />
          Rejected
        </Badge>
      );
    }
    
    if (status === 'submitted') {
      return (
        <Badge className="bg-amber-100 text-amber-800 border-amber-200">
          <Clock className="h-3 w-3 mr-1" />
          Awaiting Review
        </Badge>
      );
    }
    
    return (
      <Badge className="bg-blue-100 text-blue-800 border-blue-200">
        <FileText className="h-3 w-3 mr-1" />
        Submitted
      </Badge>
    );
  };
  
  // Render a labeled field
  const renderField = (label, value, icon = null) => {
    if (!value && value !== false && value !== 0) return null;
    
    const displayValue = typeof value === 'boolean' 
      ? (value ? 'Yes' : 'No')
      : value;
    
    return (
      <div className="flex flex-col sm:flex-row sm:items-start gap-1 py-1.5">
        <div className="flex items-center gap-1.5 text-gray-500 text-sm min-w-[140px]">
          {icon}
          <span>{label}:</span>
        </div>
        <span className="text-gray-900 text-sm font-medium">{displayValue}</span>
      </div>
    );
  };
  
  // Collapsible section wrapper
  const Section = ({ id, title, icon, children, defaultExpanded = false }) => {
    const isExpanded = expandedSections[id] ?? defaultExpanded;
    
    return (
      <div className="border rounded-lg overflow-hidden bg-white">
        <button
          onClick={() => toggleSection(id)}
          className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 transition-colors"
        >
          <div className="flex items-center gap-2">
            {icon}
            <span className="font-medium text-gray-900">{title}</span>
          </div>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          )}
        </button>
        {isExpanded && (
          <div className="p-4 border-t border-gray-100">
            {children}
          </div>
        )}
      </div>
    );
  };
  
  // Get form data
  const formData = submission?.form_data || submission?.data || {};
  
  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent 
        className="w-full sm:max-w-2xl overflow-y-auto print:overflow-visible print:max-w-full"
        data-testid="application-form-view-drawer"
      >
        <SheetHeader className="pb-4 border-b print:border-b-2">
          <div className="flex items-center justify-between">
            <div>
              <SheetTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-teal-600" />
                Application Form
              </SheetTitle>
              <SheetDescription>
                {employeeName && <span>{employeeName}</span>}
                {submission?.submitted_at && (
                  <span className="ml-2">
                    • Submitted {submission.submitted_at?.slice(0, 10)}
                  </span>
                )}
              </SheetDescription>
            </div>
            {getStatusBadge()}
          </div>
        </SheetHeader>
        
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
          </div>
        ) : !submission ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-500">
            <AlertCircle className="h-12 w-12 mb-4" />
            <p>Application form not found</p>
          </div>
        ) : (
          <div className="mt-6 space-y-4 print:space-y-2">
            {/* Rejection Notice */}
            {submission?.status === 'rejected' && submission.rejection_reason && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg print:hidden">
                <div className="flex items-start gap-3">
                  <XCircle className="h-5 w-5 text-red-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-red-800">This application was rejected</p>
                    <p className="text-sm text-red-600 mt-1">{submission.rejection_reason}</p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Verification Notice */}
            {(submission?.verified || submission?.status === 'verified') && (
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg print:bg-white print:border-emerald-400">
                <div className="flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-emerald-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-emerald-800">Verified</p>
                    <p className="text-xs text-emerald-600 mt-1">
                      By {submission.verified_by_name || submission.verified_by} on {submission.verified_at?.slice(0, 10)}
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* PERSONAL DETAILS */}
            <Section 
              id="personal" 
              title="Personal Details" 
              icon={<User className="h-4 w-4 text-teal-600" />}
              defaultExpanded
            >
              <div className="space-y-1">
                {renderField('Full Name', [formData.title, formData.first_name, formData.middle_name, formData.last_name].filter(Boolean).join(' '))}
                {renderField('Preferred Name', formData.preferred_name)}
                {renderField('Date of Birth', formData.date_of_birth)}
                {renderField('NI Number', formData.national_insurance)}
                <Separator className="my-2" />
                {renderField('Email', formData.email, <Mail className="h-3.5 w-3.5" />)}
                {renderField('Phone', formData.phone, <Phone className="h-3.5 w-3.5" />)}
                {formData.phone_secondary && renderField('Secondary Phone', formData.phone_secondary)}
                <Separator className="my-2" />
                {renderField('Address', [
                  formData.address_line_1,
                  formData.address_line_2,
                  formData.city,
                  formData.county,
                  formData.postcode
                ].filter(Boolean).join(', '), <MapPin className="h-3.5 w-3.5" />)}
                {renderField('Years at Address', formData.years_at_current_address)}
                <Separator className="my-2" />
                {renderField('Role Applied', formData.role_applied, <Briefcase className="h-3.5 w-3.5" />)}
                {renderField('Availability', formData.availability)}
                {renderField('Earliest Start', formData.earliest_start_date, <Calendar className="h-3.5 w-3.5" />)}
                {renderField('Driving Licence', formData.has_driving_licence)}
                {renderField('Own Transport', formData.has_own_transport)}
              </div>
            </Section>
            
            {/* EMPLOYMENT HISTORY */}
            <Section 
              id="employment" 
              title="Employment History" 
              icon={<Briefcase className="h-4 w-4 text-blue-600" />}
              defaultExpanded
            >
              {formData.employment_history && formData.employment_history.length > 0 ? (
                <div className="space-y-4">
                  {formData.employment_history.map((emp, idx) => (
                    <Card key={idx} className="border-gray-200">
                      <CardHeader className="py-3 px-4 bg-gray-50">
                        <CardTitle className="text-sm font-medium">
                          {emp.job_title || 'Role'} at {emp.employer_name || 'Employer'}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="py-3 px-4 space-y-1 text-sm">
                        {renderField('Period', `${emp.start_date || 'N/A'} - ${emp.is_current ? 'Present' : (emp.end_date || 'N/A')}`)}
                        {renderField('Duties', emp.duties)}
                        {!emp.is_current && renderField('Reason for Leaving', emp.reason_for_leaving)}
                        {renderField('Employer Address', emp.employer_address)}
                        {renderField('Employer Phone', emp.employer_phone)}
                        {renderField('Can Contact', emp.can_contact)}
                      </CardContent>
                    </Card>
                  ))}
                  
                  {formData.has_employment_gaps && (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                      <p className="text-sm font-medium text-amber-800">Employment Gaps Declared</p>
                      {formData.employment_gap_explanation && (
                        <p className="text-sm text-amber-700 mt-1">{formData.employment_gap_explanation}</p>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No employment history provided</p>
              )}
            </Section>
            
            {/* REFERENCES */}
            <Section 
              id="references" 
              title="References" 
              icon={<Users className="h-4 w-4 text-purple-600" />}
              defaultExpanded
            >
              {formData.references && formData.references.length > 0 ? (
                <div className="space-y-4">
                  {formData.references.map((ref, idx) => (
                    <Card key={idx} className="border-gray-200">
                      <CardHeader className="py-3 px-4 bg-gray-50">
                        <CardTitle className="text-sm font-medium">
                          Reference {idx + 1}: {ref.referee_name || 'N/A'}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="py-3 px-4 space-y-1 text-sm">
                        {renderField('Job Title', ref.referee_job_title)}
                        {renderField('Organisation', ref.referee_organisation)}
                        {renderField('Email', ref.referee_email, <Mail className="h-3.5 w-3.5" />)}
                        {renderField('Phone', ref.referee_phone, <Phone className="h-3.5 w-3.5" />)}
                        {renderField('Relationship', ref.relationship)}
                        {renderField('Years Known', ref.years_known)}
                        {renderField('Professional Reference', ref.is_professional)}
                        {renderField('Can Contact Before Offer', ref.can_contact_before_offer)}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No references provided</p>
              )}
            </Section>
            
            {/* DECLARATIONS */}
            <Section 
              id="declarations" 
              title="Declarations & Consent" 
              icon={<FileCheck className="h-4 w-4 text-indigo-600" />}
            >
              {formData.declarations ? (
                <div className="space-y-1">
                  {renderField('Information Accurate', formData.declarations.information_accurate)}
                  {renderField('Understands False Info Consequences', formData.declarations.understands_false_info_consequences)}
                  {renderField('Consents to Reference Checks', formData.declarations.consents_to_reference_checks)}
                  {renderField('Consents to Background Checks', formData.declarations.consents_to_background_checks)}
                  {renderField('Consents to Data Processing', formData.declarations.consents_to_data_processing)}
                  <Separator className="my-2" />
                  {renderField('Has Professional Registration', formData.declarations.has_professional_registration)}
                  {formData.declarations.has_professional_registration && (
                    <>
                      {renderField('Registration Body', formData.declarations.registration_body)}
                      {renderField('Registration Number', formData.declarations.registration_number)}
                      {renderField('Registration Expiry', formData.declarations.registration_expiry)}
                    </>
                  )}
                  {renderField('Has Disciplinary History', formData.declarations.has_disciplinary_history)}
                  {formData.declarations.has_disciplinary_history && renderField('Disciplinary Details', formData.declarations.disciplinary_details)}
                  {renderField('Previously Worked NHS', formData.declarations.previously_worked_nhs)}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No declarations data</p>
              )}
            </Section>
            
            {/* HEALTH DECLARATION */}
            <Section 
              id="health" 
              title="Health Declaration" 
              icon={<Heart className="h-4 w-4 text-red-500" />}
            >
              {formData.health_declaration ? (
                <div className="space-y-1">
                  {renderField('Can Perform Physical Tasks', formData.health_declaration.can_perform_physical_tasks)}
                  {renderField('Has Back Problems', formData.health_declaration.has_back_problems)}
                  {renderField('Has Mobility Issues', formData.health_declaration.has_mobility_issues)}
                  {renderField('Had Recent Infectious Illness', formData.health_declaration.had_recent_infectious_illness)}
                  {formData.health_declaration.had_recent_infectious_illness && 
                    renderField('Illness Details', formData.health_declaration.infectious_illness_details)}
                  <Separator className="my-2" />
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Vaccinations</p>
                  {renderField('Hepatitis B', formData.health_declaration.hepatitis_b_vaccinated)}
                  {renderField('Flu Vaccine', formData.health_declaration.flu_vaccinated)}
                  {renderField('COVID-19', formData.health_declaration.covid_vaccinated)}
                  <Separator className="my-2" />
                  {renderField('Has Condition Affecting Work', formData.health_declaration.has_condition_affecting_work)}
                  {formData.health_declaration.has_condition_affecting_work && 
                    renderField('Condition Details', formData.health_declaration.condition_details)}
                  {renderField('Requires Reasonable Adjustments', formData.health_declaration.requires_reasonable_adjustments)}
                  {formData.health_declaration.requires_reasonable_adjustments && 
                    renderField('Adjustment Details', formData.health_declaration.adjustment_details)}
                  {renderField('Health Declaration Accurate', formData.health_declaration.health_declaration_accurate)}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No health declaration data</p>
              )}
            </Section>
            
            {/* CRIMINAL DECLARATION */}
            <Section 
              id="criminal" 
              title="Criminal Declaration" 
              icon={<Shield className="h-4 w-4 text-orange-600" />}
            >
              {formData.criminal_declaration ? (
                <div className="space-y-1">
                  {renderField('Has Criminal Convictions', formData.criminal_declaration.has_criminal_convictions)}
                  {formData.criminal_declaration.has_criminal_convictions && 
                    renderField('Conviction Details', formData.criminal_declaration.conviction_details)}
                  {renderField('Has Pending Charges', formData.criminal_declaration.has_pending_charges)}
                  {formData.criminal_declaration.has_pending_charges && 
                    renderField('Pending Charges Details', formData.criminal_declaration.pending_charges_details)}
                  {renderField('Has Cautions/Warnings', formData.criminal_declaration.has_cautions_warnings)}
                  {formData.criminal_declaration.has_cautions_warnings && 
                    renderField('Cautions Details', formData.criminal_declaration.cautions_details)}
                  <Separator className="my-2" />
                  {renderField('Understands DBS Required', formData.criminal_declaration.understands_dbs_required)}
                  {renderField('Consents to DBS Check', formData.criminal_declaration.consents_to_dbs_check)}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No criminal declaration data</p>
              )}
            </Section>
            
            {/* RIGHT TO WORK */}
            <Section 
              id="right_to_work" 
              title="Right to Work" 
              icon={<Shield className="h-4 w-4 text-green-600" />}
            >
              {formData.right_to_work ? (
                <div className="space-y-1">
                  {renderField('Has Right to Work UK', formData.right_to_work.has_right_to_work_uk)}
                  {renderField('Citizenship Status', formData.right_to_work.citizenship_status)}
                  {formData.right_to_work.visa_type && renderField('Visa Type', formData.right_to_work.visa_type)}
                  {formData.right_to_work.visa_expiry && renderField('Visa Expiry', formData.right_to_work.visa_expiry)}
                  {formData.right_to_work.share_code && renderField('Share Code', formData.right_to_work.share_code)}
                  {renderField('Requires Sponsorship', formData.right_to_work.requires_sponsorship)}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No right to work data</p>
              )}
            </Section>
            
            {/* Additional Info */}
            {(formData.how_heard || formData.additional_info) && (
              <Section 
                id="additional" 
                title="Additional Information" 
                icon={<FileText className="h-4 w-4 text-gray-500" />}
              >
                <div className="space-y-1">
                  {renderField('How Heard About Us', formData.how_heard)}
                  {renderField('Additional Information', formData.additional_info)}
                </div>
              </Section>
            )}
            
            {/* CV Reference */}
            {formData.cv_file_id && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-3">
                <FileText className="h-5 w-5 text-blue-600" />
                <div>
                  <p className="text-sm font-medium text-blue-800">CV Attached</p>
                  <p className="text-xs text-blue-600">File ID: {formData.cv_file_id}</p>
                </div>
              </div>
            )}
            
            {/* Actions */}
            <Separator className="my-6 print:hidden" />
            
            <div className="flex flex-wrap gap-3 justify-end pb-6 print:hidden">
              {/* Export/Print Actions */}
              <Button
                variant="outline"
                onClick={handleExportPdf}
                disabled={exportingPdf}
                data-testid="export-application-pdf-btn"
              >
                {exportingPdf ? (
                  <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                ) : (
                  <Download className="h-4 w-4 mr-1.5" />
                )}
                Export PDF
              </Button>
              
              <Button
                variant="outline"
                onClick={handlePrint}
                data-testid="print-application-btn"
              >
                <Printer className="h-4 w-4 mr-1.5" />
                Print
              </Button>
              
              {/* Verify/Reject buttons for awaiting review */}
              {submission?.status === 'submitted' && onVerify && (
                <Button
                  variant="outline"
                  className="text-emerald-600 border-emerald-200 hover:bg-emerald-50"
                  onClick={() => onVerify(submission.id)}
                  data-testid="verify-application-btn"
                >
                  <CheckCircle className="h-4 w-4 mr-1.5" />
                  Verify
                </Button>
              )}
              
              {submission?.status === 'submitted' && onReject && (
                <Button
                  variant="outline"
                  className="text-red-600 border-red-200 hover:bg-red-50"
                  onClick={() => onReject(submission.id)}
                  data-testid="reject-application-btn"
                >
                  <XCircle className="h-4 w-4 mr-1.5" />
                  Reject
                </Button>
              )}
              
              <Button variant="ghost" onClick={onClose}>
                Close
              </Button>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

