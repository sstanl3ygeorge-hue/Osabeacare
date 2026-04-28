import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { 
  FileText, User, Briefcase, MapPin, Phone, Mail, Calendar,
  Shield, Heart, AlertTriangle, CheckCircle, Clock, Download,
  Upload, Eye, Loader2, FileUp, Users, GraduationCap
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { toast } from 'sonner';
import { formatBackendDate } from '../../lib/dateUtils';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

// Section component for consistent styling
const Section = ({ title, icon: Icon, children, className = "" }) => (
  <div className={`bg-white border rounded-xl p-4 ${className}`}>
    <h4 className="font-medium text-gray-800 flex items-center gap-2 mb-3 pb-2 border-b">
      {Icon && <Icon className="h-4 w-4 text-primary" />}
      {title}
    </h4>
    {children}
  </div>
);

// Field display component
const Field = ({ label, value, className = "" }) => (
  <div className={className}>
    <p className="text-xs text-gray-500 mb-0.5">{label}</p>
    <p className="text-sm font-medium text-gray-900">{value || <span className="text-gray-400 italic">Not provided</span>}</p>
  </div>
);

// Declaration item component
const DeclarationItem = ({ label, value, details }) => (
  <div className="flex items-start gap-2 py-2 border-b last:border-0">
    {value ? (
      <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
    ) : (
      <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
    )}
    <div>
      <p className="text-sm text-gray-700">{label}</p>
      {details && <p className="text-xs text-gray-500 mt-0.5">{details}</p>}
    </div>
  </div>
);

export default function ApplicationFormViewer({
  employeeId,
  employeeName,
  onClose,
  applicationSubmission = undefined,
  applicationPdfDocument = undefined,
  onApplicationUpdated,
}) {
  const [loading, setLoading] = useState(true);
  const [applicationData, setApplicationData] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [uploading, setUploading] = useState(false);
  const usingProvidedApplicationState =
    applicationSubmission !== undefined || applicationPdfDocument !== undefined;
  const resolvedApplicationData = usingProvidedApplicationState
    ? (applicationSubmission?.form_data || applicationSubmission?.data || null)
    : applicationData;
  const resolvedPdfUrl = usingProvidedApplicationState
    ? (applicationPdfDocument?.file_url || applicationSubmission?.file_url || null)
    : pdfUrl;

  useEffect(() => {
    if (employeeId && !usingProvidedApplicationState) {
      fetchApplicationData();
    }
  }, [employeeId, usingProvidedApplicationState]);

  const fetchApplicationData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      // Fetch form submissions for this employee
      const response = await axios.get(`${API}/form-submissions`, {
        headers: { Authorization: `Bearer ${token}` },
        params: {
          employee_id: employeeId,
          requirement_id: 'application_form'
        }
      });
      
      const forms = response.data.forms || response.data || [];
      const appForm = forms.find(f => f.requirement_id === 'application_form');
      
      if (appForm) {
        setApplicationData(appForm.form_data || appForm.data);
        setPdfUrl(appForm.file_url || null);
      }
      
      // Also check for uploaded PDF application
      const docsResponse = await axios.get(`${API}/employee-documents?employee_id=${employeeId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const docs = docsResponse.data || [];
      const appPdf = docs.find(d => d.requirement_id === 'application_form_pdf');
      if (appPdf?.file_url) {
        setPdfUrl(appPdf.file_url);
      }
      
    } catch (error) {
      console.error('Failed to fetch application data:', error);
      toast.error('Failed to load application data');
    } finally {
      setLoading(false);
    }
  };

  const handlePdfUpload = async (file) => {
    if (!file) return;

    const isPdfFile = file.type === 'application/pdf' || file.name?.toLowerCase().endsWith('.pdf');
    if (!isPdfFile) {
      toast.error('Only PDF application forms are supported here. Please upload a scanned or exported PDF version of the application form.');
      return;
    }
    
    try {
      setUploading(true);
      const token = localStorage.getItem('token');
      
      const formData = new FormData();
      formData.append('file', file);
      formData.append('requirement_id', 'application_form_pdf');
      formData.append('extract_data', 'true');
      
      const response = await axios.post(
        `${API}/employees/${employeeId}/upload-document`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      toast.success('Application form uploaded successfully');
      setShowUploadDialog(false);
      if (onApplicationUpdated) {
        await onApplicationUpdated();
      } else {
        fetchApplicationData();
      }
      
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error('Failed to upload application form');
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!resolvedApplicationData && !resolvedPdfUrl) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-12 text-center">
          <FileText className="h-12 w-12 mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-700 mb-2">No Application Form on File</h3>
          <p className="text-sm text-gray-500 mb-4">
            This employee was created manually or their application form wasn't stored.
          </p>
          <Button onClick={() => setShowUploadDialog(true)} className="rounded-xl">
            <Upload className="h-4 w-4 mr-2" />
            Upload Application Form (PDF)
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Handle both nested structure (personal_details.first_name) and flat structure (first_name)
  const personal = resolvedApplicationData?.personal_details || {
    title: resolvedApplicationData?.title,
    first_name: resolvedApplicationData?.first_name,
    middle_name: resolvedApplicationData?.middle_name,
    last_name: resolvedApplicationData?.last_name,
    preferred_name: resolvedApplicationData?.preferred_name,
    date_of_birth: resolvedApplicationData?.date_of_birth,
    national_insurance: resolvedApplicationData?.national_insurance || resolvedApplicationData?.ni_number,
  };
  
  const contact = resolvedApplicationData?.contact_details || {
    email: resolvedApplicationData?.email,
    phone: resolvedApplicationData?.phone,
    phone_secondary: resolvedApplicationData?.phone_secondary,
  };
  
  const address = resolvedApplicationData?.address || {
    line_1: resolvedApplicationData?.address_line_1,
    line_2: resolvedApplicationData?.address_line_2,
    city: resolvedApplicationData?.city,
    county: resolvedApplicationData?.county,
    postcode: resolvedApplicationData?.postcode,
    country: resolvedApplicationData?.country,
    years_at_address: resolvedApplicationData?.years_at_current_address,
  };
  
  const roleAvail = resolvedApplicationData?.role_availability || {
    role_applied: resolvedApplicationData?.role_applied,
    availability: resolvedApplicationData?.availability,
    earliest_start_date: resolvedApplicationData?.earliest_start_date,
    has_driving_licence: resolvedApplicationData?.has_driving_licence,
    has_own_transport: resolvedApplicationData?.has_own_transport,
  };
  
  const employment = resolvedApplicationData?.employment_history || [];
  const references = resolvedApplicationData?.references || [];
  const qualifications = resolvedApplicationData?.qualifications || {};
  const healthDecl = resolvedApplicationData?.health_declaration || {};
  const criminalDecl = resolvedApplicationData?.criminal_declaration || {};
  const rtwDecl = resolvedApplicationData?.right_to_work || {};
  const declarations = resolvedApplicationData?.declarations || {};
  const emergencyContact = resolvedApplicationData?.emergency_contact || {
    name: resolvedApplicationData?.emergency_contact_name,
    phone: resolvedApplicationData?.emergency_contact_phone,
    relationship: resolvedApplicationData?.emergency_contact_relationship,
    address: resolvedApplicationData?.emergency_contact_address,
  };
  const hasEmergencyContact = Boolean(
    emergencyContact?.name || emergencyContact?.phone || emergencyContact?.relationship || emergencyContact?.address
  );
  const gapExplanation = resolvedApplicationData?.employment_gap_explanation || resolvedApplicationData?.gap_explanation;

  return (
    <>
      <Card className="border-[#E4E8EB]">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              Application Form
              <Badge variant="outline" className="ml-2 bg-green-50 text-green-700">
                Submitted
              </Badge>
            </CardTitle>
            <div className="flex gap-2">
              {resolvedPdfUrl && (
                <Button variant="outline" size="sm" asChild className="rounded-xl">
                  <a href={resolvedPdfUrl} target="_blank" rel="noopener noreferrer">
                    <Eye className="h-4 w-4 mr-1" />
                    View PDF
                  </a>
                </Button>
              )}
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setShowUploadDialog(true)}
                className="rounded-xl"
              >
                <FileUp className="h-4 w-4 mr-1" />
                Upload PDF
              </Button>
            </div>
          </div>
        </CardHeader>
        
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid grid-cols-5 mb-4">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="employment">Employment</TabsTrigger>
              <TabsTrigger value="references">References</TabsTrigger>
              <TabsTrigger value="declarations">Declarations</TabsTrigger>
              <TabsTrigger value="qualifications">Qualifications</TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                {/* Personal Details */}
                <Section title="Personal Details" icon={User}>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Title" value={personal.title} />
                    <Field label="First Name" value={personal.first_name} />
                    <Field label="Middle Name" value={personal.middle_name} />
                    <Field label="Last Name" value={personal.last_name} />
                    <Field label="Preferred Name" value={personal.preferred_name} />
                    <Field label="Date of Birth" value={formatBackendDate(personal.date_of_birth)} />
                    <Field label="NI Number" value={personal.national_insurance} className="col-span-2" />
                  </div>
                </Section>

                {/* Contact Details */}
                <Section title="Contact Details" icon={Phone}>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-gray-400" />
                      <span className="text-sm">{contact.email || 'Not provided'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Phone className="h-4 w-4 text-gray-400" />
                      <span className="text-sm">{contact.phone || 'Not provided'}</span>
                    </div>
                    {contact.phone_secondary && (
                      <div className="flex items-center gap-2">
                        <Phone className="h-4 w-4 text-gray-400" />
                        <span className="text-sm">{contact.phone_secondary} (Secondary)</span>
                      </div>
                    )}
                  </div>
                </Section>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                {/* Address */}
                <Section title="Address" icon={MapPin}>
                  <div className="space-y-1 text-sm">
                    <p>{address.line_1 || address.address_line_1 || address.line1}</p>
                    {(address.line_2 || address.address_line_2 || address.line2) && <p>{address.line_2 || address.address_line_2 || address.line2}</p>}
                    <p>{address.city}{address.county ? `, ${address.county}` : ''}</p>
                    <p className="font-medium">{address.postcode}</p>
                    {address.country && <p className="text-xs text-gray-500">{address.country}</p>}
                    <p className="text-xs text-gray-500 mt-2">
                      Years at address: {address.years_at_address || address.years_at_current_address || 'Not specified'}
                    </p>
                  </div>
                </Section>

                {/* Role & Availability */}
                <Section title="Role & Availability" icon={Briefcase}>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Role Applied" value={roleAvail.role_applied} />
                    <Field label="Availability" value={roleAvail.availability} />
                    <Field label="Earliest Start" value={formatBackendDate(roleAvail.earliest_start_date)} />
                    <Field label="Driving Licence" value={roleAvail.has_driving_licence ? 'Yes' : 'No'} />
                    <Field label="Own Transport" value={roleAvail.has_own_transport ? 'Yes' : 'No'} />
                    {roleAvail.preferred_locations && (
                      <Field label="Preferred Locations" value={roleAvail.preferred_locations} className="col-span-2" />
                    )}
                  </div>
                </Section>
              </div>

              {hasEmergencyContact && (
                <Section title="Emergency Contact" icon={Phone}>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Name" value={emergencyContact.name} />
                    <Field label="Relationship" value={emergencyContact.relationship} />
                    <Field label="Phone" value={emergencyContact.phone} />
                    <Field label="Address" value={emergencyContact.address} className="col-span-2" />
                  </div>
                </Section>
              )}
            </TabsContent>

            {/* Employment Tab */}
            <TabsContent value="employment" className="space-y-4">
              {resolvedApplicationData?.has_employment_gaps && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
                  <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-amber-800">Employment Gaps Declared</p>
                    <p className="text-xs text-amber-700 mt-1">
                      {gapExplanation || 'No explanation provided'}
                    </p>
                  </div>
                </div>
              )}
              
              {employment.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Briefcase className="h-10 w-10 mx-auto mb-2 text-gray-300" />
                  <p>No employment history recorded</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {employment.map((job, index) => (
                    <Section 
                      key={index} 
                      title={`${job.job_title || 'Position'} at ${job.employer_name || 'Company'}`}
                      icon={Briefcase}
                    >
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                        <Field label="Employer" value={job.employer_name} />
                        <Field label="Job Title" value={job.job_title} />
                        <Field label="Start Date" value={formatBackendDate(job.start_date)} />
                        <Field label="End Date" value={job.is_current ? 'Present' : formatBackendDate(job.end_date)} />
                      </div>
                      {job.duties && (
                        <div className="mt-2">
                          <p className="text-xs text-gray-500 mb-1">Main Duties</p>
                          <p className="text-sm text-gray-700 bg-gray-50 p-2 rounded">{job.duties}</p>
                        </div>
                      )}
                      {job.reason_for_leaving && (
                        <div className="mt-2">
                          <p className="text-xs text-gray-500 mb-1">Reason for Leaving</p>
                          <p className="text-sm text-gray-700">{job.reason_for_leaving}</p>
                        </div>
                      )}
                      {(job.employer_address || job.employer_phone || typeof job.can_contact === 'boolean') && (
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-3 mt-3 pt-3 border-t">
                          <Field label="Employer Address" value={job.employer_address} />
                          <Field label="Employer Phone" value={job.employer_phone} />
                          <Field label="Can Contact Employer" value={typeof job.can_contact === 'boolean' ? (job.can_contact ? 'Yes' : 'No') : null} />
                        </div>
                      )}
                    </Section>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* References Tab */}
            <TabsContent value="references" className="space-y-4">
              {references.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Users className="h-10 w-10 mx-auto mb-2 text-gray-300" />
                  <p>No references recorded</p>
                </div>
              ) : (
                <div className="grid md:grid-cols-2 gap-4">
                  {references.map((ref, index) => (
                    <Section key={index} title={`Reference ${index + 1}`} icon={Users}>
                      <div className="space-y-2">
                        <Field label="Name" value={ref.referee_name} />
                        <Field label="Job Title" value={ref.referee_job_title} />
                        <Field label="Organisation" value={ref.referee_organisation} />
                        <Field label="Email" value={ref.referee_email} />
                        <Field label="Phone" value={ref.referee_phone} />
                        <Field label="Relationship" value={ref.relationship} />
                        <Field label="Years Known" value={ref.years_known ? `${ref.years_known} years` : null} />
                        <div className="pt-2 border-t mt-2">
                          <DeclarationItem 
                            label="Professional Reference" 
                            value={ref.is_professional} 
                          />
                          <DeclarationItem 
                            label="Can contact before offer" 
                            value={ref.can_contact_before_offer} 
                          />
                        </div>
                      </div>
                    </Section>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* Declarations Tab */}
            <TabsContent value="declarations" className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                {/* Right to Work */}
                <Section title="Right to Work" icon={Shield}>
                  <DeclarationItem 
                    label="Has right to work in UK" 
                    value={rtwDecl.has_right_to_work_uk}
                  />
                  <Field label="Citizenship Status" value={rtwDecl.citizenship_status} className="mt-2" />
                  {rtwDecl.visa_type && <Field label="Visa Type" value={rtwDecl.visa_type} className="mt-2" />}
                  {rtwDecl.visa_expiry && <Field label="Visa Expiry" value={formatBackendDate(rtwDecl.visa_expiry)} className="mt-2" />}
                  {rtwDecl.share_code && <Field label="Share Code" value={rtwDecl.share_code} className="mt-2" />}
                  <DeclarationItem 
                    label="Requires sponsorship" 
                    value={rtwDecl.requires_sponsorship}
                  />
                </Section>

                {/* Criminal Declaration */}
                <Section title="Criminal Record Declaration" icon={AlertTriangle}>
                  <DeclarationItem 
                    label="Understands DBS required" 
                    value={criminalDecl.understands_dbs_required}
                  />
                  <DeclarationItem 
                    label="Consents to DBS check" 
                    value={criminalDecl.consents_to_dbs_check}
                  />
                  <DeclarationItem 
                    label="Has criminal convictions" 
                    value={criminalDecl.has_criminal_convictions}
                    details={criminalDecl.conviction_details}
                  />
                  <DeclarationItem 
                    label="Has pending charges or investigations" 
                    value={criminalDecl.has_pending_charges}
                    details={criminalDecl.pending_charges_details}
                  />
                  <DeclarationItem 
                    label="Has cautions or warnings" 
                    value={criminalDecl.has_cautions_warnings}
                    details={criminalDecl.cautions_details}
                  />
                </Section>

                {/* Health Declaration */}
                <Section title="Health Declaration" icon={Heart}>
                  <DeclarationItem 
                    label="Can perform physical tasks" 
                    value={healthDecl.can_perform_physical_tasks}
                  />
                  <DeclarationItem 
                    label="Has back problems" 
                    value={healthDecl.has_back_problems}
                  />
                  <DeclarationItem 
                    label="Has mobility issues" 
                    value={healthDecl.has_mobility_issues}
                  />
                  <DeclarationItem 
                    label="Had recent infectious illness" 
                    value={healthDecl.had_recent_infectious_illness}
                    details={healthDecl.infectious_illness_details}
                  />
                  <DeclarationItem 
                    label="Hepatitis B vaccinated" 
                    value={healthDecl.hepatitis_b_vaccinated}
                  />
                  <DeclarationItem 
                    label="Flu vaccinated" 
                    value={healthDecl.flu_vaccinated}
                  />
                  <DeclarationItem 
                    label="COVID-19 vaccinated" 
                    value={healthDecl.covid_vaccinated}
                  />
                  <DeclarationItem 
                    label="Has condition affecting work" 
                    value={healthDecl.has_condition_affecting_work}
                    details={healthDecl.condition_details}
                  />
                  <DeclarationItem 
                    label="Requires reasonable adjustments" 
                    value={healthDecl.requires_reasonable_adjustments}
                    details={healthDecl.adjustment_details}
                  />
                  <DeclarationItem 
                    label="Health declaration accurate" 
                    value={healthDecl.health_declaration_accurate}
                  />
                </Section>

                {/* General Declarations */}
                <Section title="General Declarations" icon={CheckCircle}>
                  <DeclarationItem 
                    label="Information accurate" 
                    value={declarations.information_accurate}
                  />
                  <DeclarationItem 
                    label="Understands false info consequences" 
                    value={declarations.understands_false_info_consequences}
                  />
                  <DeclarationItem 
                    label="Consents to reference checks" 
                    value={declarations.consents_to_reference_checks}
                  />
                  <DeclarationItem 
                    label="Consents to background checks" 
                    value={declarations.consents_to_background_checks}
                  />
                  <DeclarationItem 
                    label="Consents to data processing" 
                    value={declarations.consents_to_data_processing}
                  />
                  {declarations.has_professional_registration && (
                    <>
                      <DeclarationItem 
                        label="Professional registration declared" 
                        value={declarations.has_professional_registration}
                      />
                      <Field label="Registration Body" value={declarations.registration_body} className="mt-2" />
                      <Field label="Registration Number" value={declarations.registration_number} className="mt-2" />
                      <Field label="Registration Expiry" value={formatBackendDate(declarations.registration_expiry)} className="mt-2" />
                    </>
                  )}
                </Section>
              </div>
            </TabsContent>

            {/* Qualifications Tab */}
            <TabsContent value="qualifications" className="space-y-4">
              <Section title="Qualifications & Training" icon={GraduationCap}>
                <div className="grid md:grid-cols-2 gap-4">
                  <Field label="Highest Qualification" value={qualifications.highest_qualification} />
                  <Field label="Relevant Qualifications" value={qualifications.relevant_qualifications} />
                  <DeclarationItem 
                    label="Care Certificate Completed" 
                    value={qualifications.care_certificate_completed}
                  />
                  <DeclarationItem 
                    label="Mandatory Training Completed" 
                    value={qualifications.mandatory_training_completed}
                  />
                </div>
              </Section>

              {resolvedApplicationData?.additional_info && (
                <Section title="Additional Information" icon={FileText}>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">
                    {resolvedApplicationData.additional_info}
                  </p>
                </Section>
              )}

              {resolvedApplicationData?.how_heard && (
                <div className="text-sm text-gray-500">
                  <span className="font-medium">How did they hear about us:</span> {resolvedApplicationData.how_heard}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Upload PDF Dialog */}
      <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload Application Form (PDF)</DialogTitle>
            <DialogDescription>
              Upload a scanned or PDF application form. The system will extract data automatically.
            </DialogDescription>
          </DialogHeader>
          
          <div className="border-2 border-dashed rounded-xl p-8 text-center">
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => handlePdfUpload(e.target.files[0])}
              className="hidden"
              id="pdf-upload"
              disabled={uploading}
            />
            <label htmlFor="pdf-upload" className="cursor-pointer">
              {uploading ? (
                <Loader2 className="h-12 w-12 mx-auto text-primary animate-spin" />
              ) : (
                <FileUp className="h-12 w-12 mx-auto text-gray-400 mb-3" />
              )}
              <p className="text-sm text-gray-600">
                {uploading ? 'Uploading...' : 'Click to select PDF file'}
              </p>
            </label>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

