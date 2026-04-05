import { useState, useEffect } from 'react';
import Header from '../../components/public/Header';
import Footer from '../../components/public/Footer';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Checkbox } from '../../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { toast } from 'sonner';
import { Loader2, CheckCircle, FileText, User, Briefcase, Clock, Shield, Heart, AlertTriangle, Upload, Plus, Trash2, ChevronRight, ChevronLeft, FileCheck } from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const roles = [
  'Healthcare Assistant',
  'Senior Healthcare Assistant',
  'Nurse (Registered)',
  'Senior Nurse',
  'Care Assistant',
  'Senior Care Assistant',
  'Support Worker',
  'Live-in Carer',
  'Night Carer',
  'Team Leader',
  'Care Coordinator'
];

const steps = [
  { id: 1, icon: User, title: 'Personal Details' },
  { id: 2, icon: Briefcase, title: 'Employment History' },
  { id: 3, icon: FileText, title: 'References' },
  { id: 4, icon: Shield, title: 'Declarations' },
  { id: 5, icon: Heart, title: 'Health Screening' },
  { id: 6, icon: FileCheck, title: 'Review & Submit' }
];

const availabilityOptions = [
  { value: 'full_time', label: 'Full-time (35+ hours/week)' },
  { value: 'part_time', label: 'Part-time (16-34 hours/week)' },
  { value: 'flexible', label: 'Flexible / As needed' },
  { value: 'weekends', label: 'Weekends only' },
  { value: 'nights', label: 'Night shifts only' }
];

const citizenshipOptions = [
  { value: 'uk_citizen', label: 'UK Citizen' },
  { value: 'eu_settled', label: 'EU Settled Status' },
  { value: 'eu_pre_settled', label: 'EU Pre-Settled Status' },
  { value: 'visa_holder', label: 'Visa Holder' },
  { value: 'other', label: 'Other' }
];

const referenceRelationships = [
  'Line Manager',
  'Supervisor',
  'HR Department',
  'Director',
  'Colleague (Senior)',
  'Academic Tutor',
  'Other Professional'
];

export default function ApplyPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [submissionResult, setSubmissionResult] = useState(null);
  const [cvFile, setCvFile] = useState(null);
  const [cvFileId, setCvFileId] = useState(null);
  const [isUploadingCv, setIsUploadingCv] = useState(false);
  const [validationErrors, setValidationErrors] = useState({});
  
  // CV Extraction Prefill State
  const [isExtractingFromCv, setIsExtractingFromCv] = useState(false);
  const [cvPrefillApplied, setCvPrefillApplied] = useState(false);
  const [cvExtractionConfidence, setCvExtractionConfidence] = useState(null);

  // Form data state
  const [formData, setFormData] = useState({
    // Personal Details
    title: '',
    first_name: '',
    middle_name: '',
    last_name: '',
    preferred_name: '',
    date_of_birth: '',
    national_insurance: '',
    email: '',
    phone: '',
    phone_secondary: '',
    address_line_1: '',
    address_line_2: '',
    city: '',
    county: '',
    postcode: '',
    years_at_current_address: 5,
    previous_addresses: [],
    
    // Role & Availability
    role_applied: '',
    availability: '',
    earliest_start_date: '',
    preferred_locations: [],
    has_driving_licence: false,
    has_own_transport: false,
    
    // Employment History
    employment_history: [
      {
        employer_name: '',
        job_title: '',
        start_date: '',
        end_date: '',
        is_current: false,
        duties: '',
        reason_for_leaving: '',
        employer_address: '',
        employer_phone: '',
        can_contact: true
      }
    ],
    has_employment_gaps: false,
    employment_gap_explanation: '',
    
    // References (minimum 2)
    references: [
      {
        referee_name: '',
        referee_job_title: '',
        referee_organisation: '',
        referee_email: '',
        referee_phone: '',
        relationship: '',
        years_known: 1,
        is_professional: true,
        can_contact_before_offer: true
      },
      {
        referee_name: '',
        referee_job_title: '',
        referee_organisation: '',
        referee_email: '',
        referee_phone: '',
        relationship: '',
        years_known: 1,
        is_professional: true,
        can_contact_before_offer: true
      }
    ],
    
    // Qualifications
    highest_qualification: '',
    relevant_qualifications: [],
    care_certificate_completed: false,
    mandatory_training_completed: [],
    
    // Health Declaration
    health_declaration: {
      can_perform_physical_tasks: false,
      has_back_problems: false,
      has_mobility_issues: false,
      had_recent_infectious_illness: false,
      infectious_illness_details: '',
      hepatitis_b_vaccinated: false,
      flu_vaccinated: false,
      covid_vaccinated: false,
      has_condition_affecting_work: false,
      condition_details: '',
      requires_reasonable_adjustments: false,
      adjustment_details: '',
      health_declaration_accurate: false
    },
    
    // Criminal Declaration
    criminal_declaration: {
      has_criminal_convictions: false,
      conviction_details: '',
      has_pending_charges: false,
      pending_charges_details: '',
      has_cautions_warnings: false,
      cautions_details: '',
      understands_dbs_required: false,
      consents_to_dbs_check: false
    },
    
    // Right to Work
    right_to_work: {
      has_right_to_work_uk: false,
      citizenship_status: '',
      visa_type: '',
      visa_expiry: '',
      share_code: '',
      requires_sponsorship: false
    },
    
    // Declarations
    declarations: {
      information_accurate: false,
      understands_false_info_consequences: false,
      consents_to_reference_checks: false,
      consents_to_background_checks: false,
      consents_to_data_processing: false,
      has_professional_registration: false,
      registration_body: '',
      registration_number: '',
      registration_expiry: '',
      has_disciplinary_history: false,
      disciplinary_details: '',
      previously_worked_nhs: false,
      previous_nhs_employer: '',
      left_nhs_in_good_standing: null
    },
    
    // Additional
    how_heard: '',
    additional_info: ''
  });

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (validationErrors[field]) {
      setValidationErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const handleNestedChange = (section, field, value) => {
    setFormData(prev => ({
      ...prev,
      [section]: { ...prev[section], [field]: value }
    }));
  };

  const handleArrayChange = (arrayName, index, field, value) => {
    setFormData(prev => {
      const newArray = [...prev[arrayName]];
      newArray[index] = { ...newArray[index], [field]: value };
      return { ...prev, [arrayName]: newArray };
    });
  };

  const addEmploymentEntry = () => {
    setFormData(prev => ({
      ...prev,
      employment_history: [...prev.employment_history, {
        employer_name: '',
        job_title: '',
        start_date: '',
        end_date: '',
        is_current: false,
        duties: '',
        reason_for_leaving: '',
        employer_address: '',
        employer_phone: '',
        can_contact: true
      }]
    }));
  };

  const removeEmploymentEntry = (index) => {
    if (formData.employment_history.length > 1) {
      setFormData(prev => ({
        ...prev,
        employment_history: prev.employment_history.filter((_, i) => i !== index)
      }));
    }
  };

  const handleCvUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Please upload a PDF or Word document');
      return;
    }
    
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File too large. Maximum size: 10MB');
      return;
    }
    
    setCvFile(file);
    setIsUploadingCv(true);
    
    try {
      const uploadFormData = new FormData();
      uploadFormData.append('file', file);
      
      const response = await axios.post(`${API}/applications/cv-upload`, uploadFormData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setCvFileId(response.data.file_id);
      toast.success('CV uploaded successfully');
      
      // Trigger employment history extraction from CV
      await extractEmploymentFromCv(response.data.file_id);
      
    } catch (error) {
      toast.error('Failed to upload CV. Please try again.');
      setCvFile(null);
    } finally {
      setIsUploadingCv(false);
    }
  };
  
  // CV Employment History Extraction (Phase 2: Assist Only)
  const extractEmploymentFromCv = async (fileId) => {
    setIsExtractingFromCv(true);
    try {
      const response = await axios.post(`${API}/cv/extract-employment-history?file_id=${fileId}`);
      
      if (response.data.status === 'success' && response.data.extracted_roles?.length > 0) {
        // Convert extracted roles to form format (DO NOT auto-save)
        const extractedHistory = response.data.extracted_roles.map(role => ({
          employer_name: role.employer || '',
          job_title: role.job_title || '',
          start_date: role.start_date || '',
          end_date: role.end_date || '',
          is_current: role.is_current || false,
          duties: role.description || '',
          reason_for_leaving: '',
          employer_address: '',
          employer_phone: '',
          can_contact: true
        }));
        
        // Prefill ONLY if current employment history is empty/default
        const hasUserEnteredData = formData.employment_history.some(emp => 
          emp.employer_name.trim() || emp.job_title.trim()
        );
        
        if (!hasUserEnteredData && extractedHistory.length > 0) {
          setFormData(prev => ({
            ...prev,
            employment_history: extractedHistory
          }));
          setCvPrefillApplied(true);
          setCvExtractionConfidence(response.data.overall_confidence);
          toast.info(`Employment history pre-filled from CV (${extractedHistory.length} roles found). Please review and correct any inaccuracies.`);
        } else if (extractedHistory.length > 0) {
          // User already entered data, don't overwrite but notify
          toast.info(`CV contains ${extractedHistory.length} roles. Your manually entered data has been preserved.`);
        }
      } else {
        toast.info('No employment history could be extracted from CV. Please enter manually.');
      }
    } catch (error) {
      console.error('CV extraction error:', error);
      // Non-critical - just log and continue, user can enter manually
      toast.info('CV processing completed. Please enter your employment history below.');
    } finally {
      setIsExtractingFromCv(false);
    }
  };
  
  // Reset CV prefill status when user modifies employment history
  const handleEmploymentChange = (index, field, value) => {
    handleArrayChange('employment_history', index, field, value);
    // Mark as user-modified if prefill was applied
    if (cvPrefillApplied) {
      setCvPrefillApplied(false);
    }
  };

  const validateStep = (step) => {
    const errors = {};
    
    switch (step) {
      case 1: // Personal Details
        if (!formData.first_name.trim()) errors.first_name = 'First name is required';
        if (!formData.last_name.trim()) errors.last_name = 'Last name is required';
        if (!formData.email.trim()) errors.email = 'Email is required';
        if (!formData.phone.trim()) errors.phone = 'Phone number is required';
        if (!formData.date_of_birth) errors.date_of_birth = 'Date of birth is required';
        if (!formData.address_line_1.trim()) errors.address_line_1 = 'Address is required';
        if (!formData.city.trim()) errors.city = 'City is required';
        if (!formData.postcode.trim()) errors.postcode = 'Postcode is required';
        if (!formData.role_applied) errors.role_applied = 'Role is required';
        if (!formData.availability) errors.availability = 'Availability is required';
        if (!formData.earliest_start_date) errors.earliest_start_date = 'Earliest start date is required';
        break;
        
      case 2: // Employment History
        formData.employment_history.forEach((emp, idx) => {
          if (!emp.employer_name.trim()) errors[`emp_${idx}_name`] = 'Employer name required';
          if (!emp.job_title.trim()) errors[`emp_${idx}_title`] = 'Job title required';
          if (!emp.start_date) errors[`emp_${idx}_start`] = 'Start date required';
          if (!emp.is_current && !emp.end_date) errors[`emp_${idx}_end`] = 'End date required';
        });
        break;
        
      case 3: // References
        formData.references.forEach((ref, idx) => {
          if (!ref.referee_name.trim()) errors[`ref_${idx}_name`] = 'Referee name required';
          if (!ref.referee_organisation.trim()) errors[`ref_${idx}_org`] = 'Organisation required';
          if (!ref.referee_email.trim()) errors[`ref_${idx}_email`] = 'Email required';
          if (!ref.referee_phone.trim()) errors[`ref_${idx}_phone`] = 'Phone required';
          if (!ref.relationship) errors[`ref_${idx}_rel`] = 'Relationship required';
        });
        break;
        
      case 4: // Declarations
        if (!formData.right_to_work.has_right_to_work_uk) errors.rtw = 'You must confirm right to work';
        if (!formData.right_to_work.citizenship_status) errors.citizenship = 'Citizenship status required';
        if (!formData.criminal_declaration.understands_dbs_required) errors.dbs_understand = 'You must acknowledge DBS requirement';
        if (!formData.criminal_declaration.consents_to_dbs_check) errors.dbs_consent = 'DBS consent required';
        if (!formData.declarations.consents_to_reference_checks) errors.ref_consent = 'Reference check consent required';
        if (!formData.declarations.consents_to_background_checks) errors.bg_consent = 'Background check consent required';
        if (!formData.declarations.consents_to_data_processing) errors.data_consent = 'Data processing consent required (GDPR)';
        break;
        
      case 5: // Health
        if (!formData.health_declaration.can_perform_physical_tasks) errors.physical = 'You must confirm physical capability';
        if (!formData.health_declaration.health_declaration_accurate) errors.health_accurate = 'You must confirm health declaration accuracy';
        break;
        
      case 6: // Review
        if (!formData.declarations.information_accurate) errors.info_accurate = 'You must confirm information accuracy';
        if (!formData.declarations.understands_false_info_consequences) errors.false_info = 'You must acknowledge consequences of false information';
        break;
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const nextStep = () => {
    if (validateStep(currentStep)) {
      if (currentStep < 6) setCurrentStep(currentStep + 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      toast.error('Please complete all required fields');
    }
  };

  const prevStep = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateStep(6)) {
      toast.error('Please complete all required declarations');
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      const payload = {
        ...formData,
        cv_file_id: cvFileId
      };
      
      const response = await axios.post(`${API}/applications/structured`, payload);
      setSubmissionResult(response.data);
      setIsSubmitted(true);
      toast.success('Application submitted successfully!');
    } catch (error) {
      console.error('Application submission error:', error.response?.data || error);
      const errorData = error.response?.data;
      let errorMessage = 'Something went wrong. Please try again.';
      
      if (errorData?.detail) {
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          // Pydantic validation errors come as array
          const fieldErrors = errorData.detail.map(e => {
            const field = e.loc?.join('.') || 'unknown';
            return `${field}: ${e.msg}`;
          }).join('; ');
          errorMessage = `Validation error: ${fieldErrors}`;
          console.error('Validation errors:', errorData.detail);
        }
      }
      
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render functions for each step
  const renderPersonalDetails = () => (
    <div className="space-y-6">
      <div>
        <h2 className="font-heading text-xl font-semibold text-text-primary mb-2">Personal Information</h2>
        <p className="text-sm text-text-muted mb-6">Please provide your personal details accurately. This information will be verified.</p>
      </div>
      
      {/* Name */}
      <div className="grid sm:grid-cols-4 gap-4">
        <div className="space-y-2">
          <Label>Title</Label>
          <Select value={formData.title} onValueChange={(v) => handleChange('title', v)}>
            <SelectTrigger><SelectValue placeholder="Title" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="Mr">Mr</SelectItem>
              <SelectItem value="Mrs">Mrs</SelectItem>
              <SelectItem value="Ms">Ms</SelectItem>
              <SelectItem value="Miss">Miss</SelectItem>
              <SelectItem value="Dr">Dr</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>First Name *</Label>
          <Input 
            value={formData.first_name} 
            onChange={(e) => handleChange('first_name', e.target.value)}
            className={validationErrors.first_name ? 'border-red-500' : ''}
            data-testid="apply-firstname"
          />
          {validationErrors.first_name && <p className="text-xs text-red-500">{validationErrors.first_name}</p>}
        </div>
        <div className="space-y-2">
          <Label>Middle Name</Label>
          <Input value={formData.middle_name} onChange={(e) => handleChange('middle_name', e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>Last Name *</Label>
          <Input 
            value={formData.last_name} 
            onChange={(e) => handleChange('last_name', e.target.value)}
            className={validationErrors.last_name ? 'border-red-500' : ''}
            data-testid="apply-lastname"
          />
        </div>
      </div>
      
      {/* DOB and NI */}
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Date of Birth *</Label>
          <Input 
            type="date" 
            value={formData.date_of_birth} 
            onChange={(e) => handleChange('date_of_birth', e.target.value)}
            className={validationErrors.date_of_birth ? 'border-red-500' : ''}
          />
        </div>
        <div className="space-y-2">
          <Label>National Insurance Number</Label>
          <Input 
            value={formData.national_insurance} 
            onChange={(e) => handleChange('national_insurance', e.target.value.toUpperCase())}
            placeholder="e.g. AB123456C"
          />
          <p className="text-xs text-text-muted">Optional but helps expedite identity verification</p>
        </div>
      </div>
      
      {/* Contact */}
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Email Address *</Label>
          <Input 
            type="email" 
            value={formData.email} 
            onChange={(e) => handleChange('email', e.target.value)}
            className={validationErrors.email ? 'border-red-500' : ''}
            data-testid="apply-email"
          />
        </div>
        <div className="space-y-2">
          <Label>Phone Number *</Label>
          <Input 
            type="tel" 
            value={formData.phone} 
            onChange={(e) => handleChange('phone', e.target.value)}
            className={validationErrors.phone ? 'border-red-500' : ''}
            data-testid="apply-phone"
          />
        </div>
      </div>
      
      {/* Address */}
      <div className="space-y-4">
        <h3 className="font-medium text-text-primary">Current Address</h3>
        <div className="space-y-2">
          <Label>Address Line 1 *</Label>
          <Input 
            value={formData.address_line_1} 
            onChange={(e) => handleChange('address_line_1', e.target.value)}
            className={validationErrors.address_line_1 ? 'border-red-500' : ''}
          />
        </div>
        <div className="space-y-2">
          <Label>Address Line 2</Label>
          <Input value={formData.address_line_2} onChange={(e) => handleChange('address_line_2', e.target.value)} />
        </div>
        <div className="grid sm:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label>City *</Label>
            <Input 
              value={formData.city} 
              onChange={(e) => handleChange('city', e.target.value)}
              className={validationErrors.city ? 'border-red-500' : ''}
            />
          </div>
          <div className="space-y-2">
            <Label>County</Label>
            <Input value={formData.county} onChange={(e) => handleChange('county', e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Postcode *</Label>
            <Input 
              value={formData.postcode} 
              onChange={(e) => handleChange('postcode', e.target.value.toUpperCase())}
              className={validationErrors.postcode ? 'border-red-500' : ''}
            />
          </div>
        </div>
        <div className="space-y-2">
          <Label>Years at Current Address</Label>
          <Select value={String(formData.years_at_current_address)} onValueChange={(v) => handleChange('years_at_current_address', parseInt(v))}>
            <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
            <SelectContent>
              {[0, 1, 2, 3, 4, 5].map(y => (
                <SelectItem key={y} value={String(y)}>{y === 5 ? '5 or more years' : `${y} ${y === 1 ? 'year' : 'years'}`}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          {formData.years_at_current_address < 5 && (
            <p className="text-xs text-amber-600">Note: 5-year address history required for DBS check</p>
          )}
        </div>
      </div>
      
      {/* Role & Availability */}
      <div className="space-y-4 pt-4 border-t">
        <h3 className="font-medium text-text-primary">Role & Availability</h3>
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Role Applying For *</Label>
            <Select value={formData.role_applied} onValueChange={(v) => handleChange('role_applied', v)}>
              <SelectTrigger className={validationErrors.role_applied ? 'border-red-500' : ''} data-testid="apply-role">
                <SelectValue placeholder="Select role" />
              </SelectTrigger>
              <SelectContent>
                {roles.map(role => <SelectItem key={role} value={role}>{role}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Availability *</Label>
            <Select value={formData.availability} onValueChange={(v) => handleChange('availability', v)}>
              <SelectTrigger className={validationErrors.availability ? 'border-red-500' : ''}>
                <SelectValue placeholder="Select availability" />
              </SelectTrigger>
              <SelectContent>
                {availabilityOptions.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Earliest Start Date *</Label>
            <Input 
              type="date" 
              value={formData.earliest_start_date} 
              onChange={(e) => handleChange('earliest_start_date', e.target.value)}
              className={validationErrors.earliest_start_date ? 'border-red-500' : ''}
            />
          </div>
          <div className="space-y-2 flex flex-col gap-3 pt-6">
            <div className="flex items-center gap-2">
              <Checkbox 
                id="driving" 
                checked={formData.has_driving_licence} 
                onCheckedChange={(c) => handleChange('has_driving_licence', c)} 
              />
              <Label htmlFor="driving" className="cursor-pointer">I have a valid driving licence</Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox 
                id="transport" 
                checked={formData.has_own_transport} 
                onCheckedChange={(c) => handleChange('has_own_transport', c)} 
              />
              <Label htmlFor="transport" className="cursor-pointer">I have my own transport</Label>
            </div>
          </div>
        </div>
      </div>
      
      {/* CV Upload */}
      <div className="space-y-4 pt-4 border-t">
        <h3 className="font-medium text-text-primary">CV / Resume Upload</h3>
        <div className="border-2 border-dashed border-gray-200 rounded-xl p-6 text-center">
          {cvFile ? (
            <div className="flex items-center justify-center gap-3">
              <FileText className="h-8 w-8 text-green-600" />
              <div className="text-left">
                <p className="font-medium text-text-primary">{cvFile.name}</p>
                <p className="text-sm text-green-600">Uploaded successfully</p>
              </div>
            </div>
          ) : (
            <label className="cursor-pointer">
              <input 
                type="file" 
                accept=".pdf,.doc,.docx" 
                onChange={handleCvUpload} 
                className="hidden" 
              />
              <div className="flex flex-col items-center gap-2">
                {isUploadingCv ? (
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                ) : (
                  <Upload className="h-8 w-8 text-gray-400" />
                )}
                <p className="text-sm text-text-muted">
                  {isUploadingCv ? 'Uploading...' : 'Click to upload your CV (PDF or Word, max 10MB)'}
                </p>
              </div>
            </label>
          )}
        </div>
      </div>
    </div>
  );

  const renderEmploymentHistory = () => (
    <div className="space-y-6">
      <div>
        <h2 className="font-heading text-xl font-semibold text-text-primary mb-2">Employment History</h2>
        <p className="text-sm text-text-muted mb-4">
          Please provide your complete employment history. This will be verified and checked for any unexplained gaps.
        </p>
        
        {/* CV Extraction Loading State */}
        {isExtractingFromCv && (
          <div className="p-4 bg-blue-50 rounded-xl border border-blue-200 mb-4">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
              <p className="text-sm text-blue-700 font-medium">
                Extracting employment history from your CV...
              </p>
            </div>
          </div>
        )}
        
        {/* CV Prefill Notice - CRITICAL for user awareness */}
        {cvPrefillApplied && (
          <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 mb-4" data-testid="cv-prefill-notice">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-800">
                  Employment history has been pre-filled from your CV
                </p>
                <p className="text-xs text-amber-700 mt-1">
                  Please review and correct any inaccuracies before submitting. 
                  {cvExtractionConfidence !== null && (
                    <span className="ml-1">
                      (Extraction confidence: {Math.round(cvExtractionConfidence * 100)}%)
                    </span>
                  )}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {formData.employment_history.map((emp, idx) => (
        <Card key={idx} className="border-border-default">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Employment {idx + 1}</CardTitle>
              {idx > 0 && (
                <Button variant="ghost" size="sm" onClick={() => removeEmploymentEntry(idx)}>
                  <Trash2 className="h-4 w-4 text-red-500" />
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Employer Name *</Label>
                <Input 
                  value={emp.employer_name}
                  onChange={(e) => handleEmploymentChange(idx, 'employer_name', e.target.value)}
                  className={validationErrors[`emp_${idx}_name`] ? 'border-red-500' : ''}
                  data-testid={`employment-${idx}-employer`}
                />
              </div>
              <div className="space-y-2">
                <Label>Job Title *</Label>
                <Input 
                  value={emp.job_title}
                  onChange={(e) => handleEmploymentChange(idx, 'job_title', e.target.value)}
                  className={validationErrors[`emp_${idx}_title`] ? 'border-red-500' : ''}
                  data-testid={`employment-${idx}-title`}
                />
              </div>
            </div>
            
            <div className="grid sm:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Start Date *</Label>
                <Input 
                  type="month" 
                  value={emp.start_date}
                  onChange={(e) => handleEmploymentChange(idx, 'start_date', e.target.value)}
                  className={validationErrors[`emp_${idx}_start`] ? 'border-red-500' : ''}
                  data-testid={`employment-${idx}-start`}
                />
              </div>
              <div className="space-y-2">
                <Label>End Date {emp.is_current ? '' : '*'}</Label>
                <Input 
                  type="month" 
                  value={emp.end_date}
                  onChange={(e) => handleEmploymentChange(idx, 'end_date', e.target.value)}
                  disabled={emp.is_current}
                  className={validationErrors[`emp_${idx}_end`] && !emp.is_current ? 'border-red-500' : ''}
                  data-testid={`employment-${idx}-end`}
                />
              </div>
              <div className="space-y-2 flex items-end pb-2">
                <div className="flex items-center gap-2">
                  <Checkbox 
                    checked={emp.is_current}
                    onCheckedChange={(c) => handleEmploymentChange(idx, 'is_current', c)}
                  />
                  <Label className="cursor-pointer">Current employer</Label>
                </div>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Main Duties & Responsibilities</Label>
              <Textarea 
                value={emp.duties}
                onChange={(e) => handleEmploymentChange(idx, 'duties', e.target.value)}
                rows={3}
                placeholder="Describe your main responsibilities in this role..."
              />
            </div>
            
            {!emp.is_current && (
              <div className="space-y-2">
                <Label>Reason for Leaving</Label>
                <Input 
                  value={emp.reason_for_leaving}
                  onChange={(e) => handleEmploymentChange(idx, 'reason_for_leaving', e.target.value)}
                />
              </div>
            )}
            
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Employer Address</Label>
                <Input 
                  value={emp.employer_address}
                  onChange={(e) => handleArrayChange('employment_history', idx, 'employer_address', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Employer Phone</Label>
                <Input 
                  value={emp.employer_phone}
                  onChange={(e) => handleArrayChange('employment_history', idx, 'employer_phone', e.target.value)}
                />
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <Checkbox 
                checked={emp.can_contact}
                onCheckedChange={(c) => handleArrayChange('employment_history', idx, 'can_contact', c)}
              />
              <Label className="cursor-pointer">You may contact this employer for reference</Label>
            </div>
          </CardContent>
        </Card>
      ))}
      
      <Button type="button" variant="outline" onClick={addEmploymentEntry} className="w-full">
        <Plus className="h-4 w-4 mr-2" /> Add Another Employment
      </Button>
      
      {/* Employment Gaps */}
      <Card className="border-amber-200 bg-amber-50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="space-y-3 flex-1">
              <p className="text-sm text-amber-800">
                Please declare any gaps in your employment history. All gaps will need to be explained for compliance purposes.
              </p>
              <div className="flex items-center gap-2">
                <Checkbox 
                  checked={formData.has_employment_gaps}
                  onCheckedChange={(c) => handleChange('has_employment_gaps', c)}
                />
                <Label className="cursor-pointer text-amber-800">I have gaps in my employment history</Label>
              </div>
              {formData.has_employment_gaps && (
                <Textarea 
                  value={formData.employment_gap_explanation}
                  onChange={(e) => handleChange('employment_gap_explanation', e.target.value)}
                  placeholder="Please explain any gaps in your employment (e.g., education, caring responsibilities, travel, illness)..."
                  rows={3}
                />
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderReferences = () => (
    <div className="space-y-6">
      <div>
        <h2 className="font-heading text-xl font-semibold text-text-primary mb-2">Professional References</h2>
        <p className="text-sm text-text-muted mb-6">
          We require a minimum of 2 professional references. These will be contacted to verify your employment history and suitability.
        </p>
      </div>
      
      {formData.references.map((ref, idx) => (
        <Card key={idx} className="border-border-default">
          <CardHeader>
            <CardTitle className="text-lg">Reference {idx + 1} {idx < 2 && <span className="text-red-500">*</span>}</CardTitle>
            <CardDescription>Professional reference from a previous employer or supervisor</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Referee Full Name *</Label>
                <Input 
                  value={ref.referee_name}
                  onChange={(e) => handleArrayChange('references', idx, 'referee_name', e.target.value)}
                  className={validationErrors[`ref_${idx}_name`] ? 'border-red-500' : ''}
                />
              </div>
              <div className="space-y-2">
                <Label>Job Title</Label>
                <Input 
                  value={ref.referee_job_title}
                  onChange={(e) => handleArrayChange('references', idx, 'referee_job_title', e.target.value)}
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Organisation *</Label>
              <Input 
                value={ref.referee_organisation}
                onChange={(e) => handleArrayChange('references', idx, 'referee_organisation', e.target.value)}
                className={validationErrors[`ref_${idx}_org`] ? 'border-red-500' : ''}
              />
            </div>
            
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Email Address *</Label>
                <Input 
                  type="email"
                  value={ref.referee_email}
                  onChange={(e) => handleArrayChange('references', idx, 'referee_email', e.target.value)}
                  className={validationErrors[`ref_${idx}_email`] ? 'border-red-500' : ''}
                />
              </div>
              <div className="space-y-2">
                <Label>Phone Number *</Label>
                <Input 
                  type="tel"
                  value={ref.referee_phone}
                  onChange={(e) => handleArrayChange('references', idx, 'referee_phone', e.target.value)}
                  className={validationErrors[`ref_${idx}_phone`] ? 'border-red-500' : ''}
                />
              </div>
            </div>
            
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Relationship to You *</Label>
                <Select 
                  value={ref.relationship} 
                  onValueChange={(v) => handleArrayChange('references', idx, 'relationship', v)}
                >
                  <SelectTrigger className={validationErrors[`ref_${idx}_rel`] ? 'border-red-500' : ''}>
                    <SelectValue placeholder="Select relationship" />
                  </SelectTrigger>
                  <SelectContent>
                    {referenceRelationships.map(r => <SelectItem key={r} value={r}>{r}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Years Known</Label>
                <Input 
                  type="number"
                  min="1"
                  value={ref.years_known}
                  onChange={(e) => handleArrayChange('references', idx, 'years_known', parseInt(e.target.value) || 1)}
                />
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <Checkbox 
                checked={ref.can_contact_before_offer}
                onCheckedChange={(c) => handleArrayChange('references', idx, 'can_contact_before_offer', c)}
              />
              <Label className="cursor-pointer">You may contact this referee before a job offer is made</Label>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );

  const renderDeclarations = () => (
    <div className="space-y-6">
      <div>
        <h2 className="font-heading text-xl font-semibold text-text-primary mb-2">Declarations & Consent</h2>
        <p className="text-sm text-text-muted mb-6">
          Please complete all declarations truthfully. False or misleading information may result in dismissal or criminal prosecution.
        </p>
      </div>
      
      {/* Right to Work */}
      <Card className="border-border-default">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="h-5 w-5" /> Right to Work
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Checkbox 
              checked={formData.right_to_work.has_right_to_work_uk}
              onCheckedChange={(c) => handleNestedChange('right_to_work', 'has_right_to_work_uk', c)}
            />
            <Label className="cursor-pointer">I confirm I have the legal right to work in the UK *</Label>
          </div>
          {validationErrors.rtw && <p className="text-xs text-red-500">{validationErrors.rtw}</p>}
          
          <div className="space-y-2">
            <Label>Citizenship Status *</Label>
            <Select 
              value={formData.right_to_work.citizenship_status}
              onValueChange={(v) => handleNestedChange('right_to_work', 'citizenship_status', v)}
            >
              <SelectTrigger className={validationErrors.citizenship ? 'border-red-500' : ''}>
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent>
                {citizenshipOptions.map(opt => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          
          {formData.right_to_work.citizenship_status === 'visa_holder' && (
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Visa Type</Label>
                <Input 
                  value={formData.right_to_work.visa_type}
                  onChange={(e) => handleNestedChange('right_to_work', 'visa_type', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Visa Expiry Date</Label>
                <Input 
                  type="date"
                  value={formData.right_to_work.visa_expiry}
                  onChange={(e) => handleNestedChange('right_to_work', 'visa_expiry', e.target.value)}
                />
              </div>
            </div>
          )}
          
          <div className="flex items-center gap-2">
            <Checkbox 
              checked={formData.right_to_work.requires_sponsorship}
              onCheckedChange={(c) => handleNestedChange('right_to_work', 'requires_sponsorship', c)}
            />
            <Label className="cursor-pointer">I require visa sponsorship to work in the UK</Label>
          </div>
        </CardContent>
      </Card>
      
      {/* Criminal Declaration */}
      <Card className="border-border-default">
        <CardHeader>
          <CardTitle className="text-lg">Criminal Record Declaration</CardTitle>
          <CardDescription>An Enhanced DBS check is required for all care roles</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Checkbox 
              checked={formData.criminal_declaration.understands_dbs_required}
              onCheckedChange={(c) => handleNestedChange('criminal_declaration', 'understands_dbs_required', c)}
            />
            <Label className="cursor-pointer">I understand an Enhanced DBS check is required for this role *</Label>
          </div>
          {validationErrors.dbs_understand && <p className="text-xs text-red-500">{validationErrors.dbs_understand}</p>}
          
          <div className="flex items-center gap-2">
            <Checkbox 
              checked={formData.criminal_declaration.consents_to_dbs_check}
              onCheckedChange={(c) => handleNestedChange('criminal_declaration', 'consents_to_dbs_check', c)}
            />
            <Label className="cursor-pointer">I consent to an Enhanced DBS check being conducted *</Label>
          </div>
          {validationErrors.dbs_consent && <p className="text-xs text-red-500">{validationErrors.dbs_consent}</p>}
          
          <div className="border-t pt-4 space-y-3">
            <div className="flex items-center gap-2">
              <Checkbox 
                checked={formData.criminal_declaration.has_criminal_convictions}
                onCheckedChange={(c) => handleNestedChange('criminal_declaration', 'has_criminal_convictions', c)}
              />
              <Label className="cursor-pointer">I have criminal convictions (including spent convictions)</Label>
            </div>
            {formData.criminal_declaration.has_criminal_convictions && (
              <Textarea 
                value={formData.criminal_declaration.conviction_details}
                onChange={(e) => handleNestedChange('criminal_declaration', 'conviction_details', e.target.value)}
                placeholder="Please provide details of all convictions..."
                rows={3}
              />
            )}
            
            <div className="flex items-center gap-2">
              <Checkbox 
                checked={formData.criminal_declaration.has_pending_charges}
                onCheckedChange={(c) => handleNestedChange('criminal_declaration', 'has_pending_charges', c)}
              />
              <Label className="cursor-pointer">I have pending charges or investigations</Label>
            </div>
            
            <div className="flex items-center gap-2">
              <Checkbox 
                checked={formData.criminal_declaration.has_cautions_warnings}
                onCheckedChange={(c) => handleNestedChange('criminal_declaration', 'has_cautions_warnings', c)}
              />
              <Label className="cursor-pointer">I have received police cautions or warnings</Label>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Consent Declarations */}
      <Card className="border-border-default">
        <CardHeader>
          <CardTitle className="text-lg">Consent & Data Processing</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start gap-2">
            <Checkbox 
              checked={formData.declarations.consents_to_reference_checks}
              onCheckedChange={(c) => handleNestedChange('declarations', 'consents_to_reference_checks', c)}
            />
            <Label className="cursor-pointer text-sm">
              I consent to reference checks being conducted with previous employers *
            </Label>
          </div>
          {validationErrors.ref_consent && <p className="text-xs text-red-500 ml-6">{validationErrors.ref_consent}</p>}
          
          <div className="flex items-start gap-2">
            <Checkbox 
              checked={formData.declarations.consents_to_background_checks}
              onCheckedChange={(c) => handleNestedChange('declarations', 'consents_to_background_checks', c)}
            />
            <Label className="cursor-pointer text-sm">
              I consent to background checks being conducted as part of the recruitment process *
            </Label>
          </div>
          {validationErrors.bg_consent && <p className="text-xs text-red-500 ml-6">{validationErrors.bg_consent}</p>}
          
          <div className="flex items-start gap-2">
            <Checkbox 
              checked={formData.declarations.consents_to_data_processing}
              onCheckedChange={(c) => handleNestedChange('declarations', 'consents_to_data_processing', c)}
            />
            <Label className="cursor-pointer text-sm">
              I consent to my personal data being processed in accordance with GDPR for recruitment purposes *
            </Label>
          </div>
          {validationErrors.data_consent && <p className="text-xs text-red-500 ml-6">{validationErrors.data_consent}</p>}
        </CardContent>
      </Card>
      
      {/* Professional Registration */}
      <Card className="border-border-default">
        <CardHeader>
          <CardTitle className="text-lg">Professional Registration (if applicable)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Checkbox 
              checked={formData.declarations.has_professional_registration}
              onCheckedChange={(c) => handleNestedChange('declarations', 'has_professional_registration', c)}
            />
            <Label className="cursor-pointer">I hold a professional registration (e.g., NMC, HCPC)</Label>
          </div>
          
          {formData.declarations.has_professional_registration && (
            <div className="grid sm:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Registration Body</Label>
                <Input 
                  value={formData.declarations.registration_body}
                  onChange={(e) => handleNestedChange('declarations', 'registration_body', e.target.value)}
                  placeholder="e.g., NMC"
                />
              </div>
              <div className="space-y-2">
                <Label>Registration Number</Label>
                <Input 
                  value={formData.declarations.registration_number}
                  onChange={(e) => handleNestedChange('declarations', 'registration_number', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Expiry Date</Label>
                <Input 
                  type="date"
                  value={formData.declarations.registration_expiry}
                  onChange={(e) => handleNestedChange('declarations', 'registration_expiry', e.target.value)}
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );

  const renderHealthScreening = () => (
    <div className="space-y-6">
      <div>
        <h2 className="font-heading text-xl font-semibold text-text-primary mb-2">Health Declaration</h2>
        <p className="text-sm text-text-muted mb-6">
          This information helps us ensure you can safely perform the role and identify any support you may need.
        </p>
      </div>
      
      <Card className="border-border-default">
        <CardHeader>
          <CardTitle className="text-lg">Physical Capability</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start gap-2">
            <Checkbox 
              checked={formData.health_declaration.can_perform_physical_tasks}
              onCheckedChange={(c) => handleNestedChange('health_declaration', 'can_perform_physical_tasks', c)}
            />
            <Label className="cursor-pointer text-sm">
              I confirm I am physically capable of performing care duties including lifting, moving, and standing for extended periods *
            </Label>
          </div>
          {validationErrors.physical && <p className="text-xs text-red-500 ml-6">{validationErrors.physical}</p>}
          
          <div className="flex items-center gap-2">
            <Checkbox 
              checked={formData.health_declaration.has_back_problems}
              onCheckedChange={(c) => handleNestedChange('health_declaration', 'has_back_problems', c)}
            />
            <Label className="cursor-pointer">I have back problems or a history of back injury</Label>
          </div>
          
          <div className="flex items-center gap-2">
            <Checkbox 
              checked={formData.health_declaration.has_mobility_issues}
              onCheckedChange={(c) => handleNestedChange('health_declaration', 'has_mobility_issues', c)}
            />
            <Label className="cursor-pointer">I have mobility issues that may affect my work</Label>
          </div>
        </CardContent>
      </Card>
      
      <Card className="border-border-default">
        <CardHeader>
          <CardTitle className="text-lg">Vaccinations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Checkbox 
              checked={formData.health_declaration.hepatitis_b_vaccinated}
              onCheckedChange={(c) => handleNestedChange('health_declaration', 'hepatitis_b_vaccinated', c)}
            />
            <Label className="cursor-pointer">Hepatitis B vaccination</Label>
          </div>
          
          <div className="flex items-center gap-2">
            <Checkbox 
              checked={formData.health_declaration.flu_vaccinated}
              onCheckedChange={(c) => handleNestedChange('health_declaration', 'flu_vaccinated', c)}
            />
            <Label className="cursor-pointer">Current flu vaccination</Label>
          </div>
          
          <div className="flex items-center gap-2">
            <Checkbox 
              checked={formData.health_declaration.covid_vaccinated}
              onCheckedChange={(c) => handleNestedChange('health_declaration', 'covid_vaccinated', c)}
            />
            <Label className="cursor-pointer">COVID-19 vaccination</Label>
          </div>
        </CardContent>
      </Card>
      
      <Card className="border-border-default">
        <CardHeader>
          <CardTitle className="text-lg">Health Conditions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Checkbox 
              checked={formData.health_declaration.had_recent_infectious_illness}
              onCheckedChange={(c) => handleNestedChange('health_declaration', 'had_recent_infectious_illness', c)}
            />
            <Label className="cursor-pointer">I have had a recent infectious illness</Label>
          </div>
          {formData.health_declaration.had_recent_infectious_illness && (
            <Textarea 
              value={formData.health_declaration.infectious_illness_details}
              onChange={(e) => handleNestedChange('health_declaration', 'infectious_illness_details', e.target.value)}
              placeholder="Please provide details..."
              rows={2}
            />
          )}
          
          <div className="flex items-center gap-2">
            <Checkbox 
              checked={formData.health_declaration.has_condition_affecting_work}
              onCheckedChange={(c) => handleNestedChange('health_declaration', 'has_condition_affecting_work', c)}
            />
            <Label className="cursor-pointer">I have a health condition that may affect my ability to work</Label>
          </div>
          {formData.health_declaration.has_condition_affecting_work && (
            <Textarea 
              value={formData.health_declaration.condition_details}
              onChange={(e) => handleNestedChange('health_declaration', 'condition_details', e.target.value)}
              placeholder="Please provide details..."
              rows={2}
            />
          )}
          
          <div className="flex items-center gap-2">
            <Checkbox 
              checked={formData.health_declaration.requires_reasonable_adjustments}
              onCheckedChange={(c) => handleNestedChange('health_declaration', 'requires_reasonable_adjustments', c)}
            />
            <Label className="cursor-pointer">I require reasonable adjustments to perform this role</Label>
          </div>
          {formData.health_declaration.requires_reasonable_adjustments && (
            <Textarea 
              value={formData.health_declaration.adjustment_details}
              onChange={(e) => handleNestedChange('health_declaration', 'adjustment_details', e.target.value)}
              placeholder="Please describe the adjustments you require..."
              rows={2}
            />
          )}
        </CardContent>
      </Card>
      
      <Card className="border-amber-200 bg-amber-50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-2">
            <Checkbox 
              checked={formData.health_declaration.health_declaration_accurate}
              onCheckedChange={(c) => handleNestedChange('health_declaration', 'health_declaration_accurate', c)}
            />
            <Label className="cursor-pointer text-sm text-amber-800">
              I declare that the health information provided above is accurate and complete. 
              I understand that providing false information may result in dismissal and could endanger service users. *
            </Label>
          </div>
          {validationErrors.health_accurate && <p className="text-xs text-red-500 ml-6 mt-1">{validationErrors.health_accurate}</p>}
        </CardContent>
      </Card>
    </div>
  );

  const renderReview = () => (
    <div className="space-y-6">
      <div>
        <h2 className="font-heading text-xl font-semibold text-text-primary mb-2">Review & Submit</h2>
        <p className="text-sm text-text-muted mb-6">
          Please review your application carefully before submitting. All information will be verified.
        </p>
      </div>
      
      {/* Summary Cards */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Personal Details</CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-1">
            <p><span className="text-text-muted">Name:</span> {formData.title} {formData.first_name} {formData.last_name}</p>
            <p><span className="text-text-muted">Email:</span> {formData.email}</p>
            <p><span className="text-text-muted">Phone:</span> {formData.phone}</p>
            <p><span className="text-text-muted">Address:</span> {formData.address_line_1}, {formData.city}, {formData.postcode}</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Role & Availability</CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-1">
            <p><span className="text-text-muted">Role:</span> {formData.role_applied}</p>
            <p><span className="text-text-muted">Availability:</span> {availabilityOptions.find(o => o.value === formData.availability)?.label}</p>
            <p><span className="text-text-muted">Start Date:</span> {formData.earliest_start_date}</p>
            <p><span className="text-text-muted">CV:</span> {cvFile ? cvFile.name : 'Not uploaded'}</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Employment History</CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-1">
            {formData.employment_history.map((emp, idx) => (
              <p key={idx}>{emp.job_title} at {emp.employer_name}</p>
            ))}
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">References</CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-1">
            {formData.references.map((ref, idx) => (
              <p key={idx}>{ref.referee_name} ({ref.referee_organisation})</p>
            ))}
          </CardContent>
        </Card>
      </div>
      
      {/* Final Declarations */}
      <Card className="border-red-200 bg-red-50">
        <CardHeader>
          <CardTitle className="text-lg text-red-800">Final Declaration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start gap-2">
            <Checkbox 
              checked={formData.declarations.information_accurate}
              onCheckedChange={(c) => handleNestedChange('declarations', 'information_accurate', c)}
            />
            <Label className="cursor-pointer text-sm text-red-800">
              I declare that all information provided in this application is true, complete, and accurate to the best of my knowledge. *
            </Label>
          </div>
          {validationErrors.info_accurate && <p className="text-xs text-red-600 ml-6">{validationErrors.info_accurate}</p>}
          
          <div className="flex items-start gap-2">
            <Checkbox 
              checked={formData.declarations.understands_false_info_consequences}
              onCheckedChange={(c) => handleNestedChange('declarations', 'understands_false_info_consequences', c)}
            />
            <Label className="cursor-pointer text-sm text-red-800">
              I understand that providing false or misleading information may result in my application being rejected, 
              any offer of employment being withdrawn, or dismissal if I am already employed. 
              It may also result in criminal prosecution. *
            </Label>
          </div>
          {validationErrors.false_info && <p className="text-xs text-red-600 ml-6">{validationErrors.false_info}</p>}
        </CardContent>
      </Card>
      
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
        <h3 className="font-medium text-blue-800 mb-2">What happens next?</h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• Your application will be reviewed by our recruitment team</li>
          <li>• We may contact your references for verification</li>
          <li>• You may be invited for an interview</li>
          <li>• Additional evidence may be requested during the recruitment process</li>
        </ul>
      </div>
    </div>
  );

  const renderSubmitted = () => (
    <div className="text-center py-8">
      <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
        <CheckCircle className="h-10 w-10 text-green-600" />
      </div>
      <h2 className="font-heading text-2xl font-semibold text-text-primary mb-4">
        Application Received
      </h2>
      <p className="text-text-muted mb-6 max-w-md mx-auto">
        Thank you for applying to Osabea Healthcare Solutions. We have received your application and our recruitment team will review it.
      </p>
      
      <div className="bg-[#F8FAFA] rounded-xl p-6 inline-block mb-6">
        <p className="text-sm text-text-muted mb-1">Your application reference:</p>
        <p className="font-heading font-bold text-2xl text-primary">{submissionResult?.reference}</p>
        <p className="text-xs text-text-muted mt-2">Please save this reference for your records</p>
      </div>
      
      {submissionResult?.next_steps && (
        <div className="text-left max-w-md mx-auto bg-white rounded-xl border p-4 mb-6">
          <h3 className="font-medium text-text-primary mb-2">What Happens Next</h3>
          <ul className="text-sm text-text-muted space-y-1">
            {submissionResult.next_steps.map((step, idx) => (
              <li key={idx}>• {step}</li>
            ))}
          </ul>
        </div>
      )}
      
      {submissionResult?.follow_up_items?.length > 0 && (
        <div className="text-left max-w-md mx-auto bg-blue-50 rounded-xl border border-blue-200 p-4 mb-6">
          <h3 className="font-medium text-blue-800 mb-2">Evidence We May Request</h3>
          <p className="text-xs text-blue-600 mb-2">During the recruitment process, you may be asked to provide:</p>
          <ul className="text-sm text-blue-700 space-y-1">
            {submissionResult.follow_up_items.map((item, idx) => (
              <li key={idx}>• {item.description}</li>
            ))}
          </ul>
        </div>
      )}
      
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 max-w-md mx-auto mb-8">
        <p className="text-sm text-gray-600">
          <strong>Please note:</strong> This submission confirms receipt of your application only. 
          All information is subject to verification. You will be contacted if we require additional information.
        </p>
      </div>
      
      {/* Navigation buttons */}
      <div className="flex flex-col sm:flex-row gap-3 justify-center max-w-md mx-auto">
        <a 
          href="/"
          className="inline-flex items-center justify-center px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
        >
          Return to Homepage
        </a>
        <a 
          href="mailto:recruitment@osabeacares.co.uk"
          className="inline-flex items-center justify-center px-6 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Contact Recruitment
        </a>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F8FAFA]">
      <Header />
      
      {/* Hero */}
      <section className="bg-white py-8 lg:py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="font-heading text-3xl sm:text-4xl font-bold text-text-primary mb-4">
            Apply to Join Our Team
          </h1>
          <p className="text-lg text-text-muted">
            Complete your application online. All information will be verified during the recruitment process.
          </p>
        </div>
      </section>

      {/* Application Form */}
      <section className="py-8 lg:py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          {isSubmitted ? (
            <div className="bg-white rounded-3xl border border-[#E4E8EB] p-8 lg:p-12">
              {renderSubmitted()}
            </div>
          ) : (
            <>
              {/* Progress Steps */}
              <div className="mb-8 overflow-x-auto">
                <div className="flex items-center min-w-max">
                  {steps.map((step, idx) => (
                    <div key={step.id} className="flex items-center">
                      <div 
                        className={`flex items-center justify-center w-10 h-10 rounded-xl cursor-pointer transition-colors ${
                          currentStep >= step.id ? 'bg-primary text-white' : 'bg-[#E4E8EB] text-text-muted'
                        }`}
                        onClick={() => currentStep > step.id && setCurrentStep(step.id)}
                      >
                        <step.icon className="h-5 w-5" />
                      </div>
                      <span className={`hidden sm:block ml-2 text-sm font-medium whitespace-nowrap ${
                        currentStep >= step.id ? 'text-text-primary' : 'text-text-muted'
                      }`}>
                        {step.title}
                      </span>
                      {idx < steps.length - 1 && (
                        <div className={`w-8 lg:w-16 h-0.5 mx-2 ${
                          currentStep > step.id ? 'bg-primary' : 'bg-[#E4E8EB]'
                        }`} />
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-3xl border border-[#E4E8EB] p-6 lg:p-10">
                <form onSubmit={handleSubmit}>
                  {currentStep === 1 && renderPersonalDetails()}
                  {currentStep === 2 && renderEmploymentHistory()}
                  {currentStep === 3 && renderReferences()}
                  {currentStep === 4 && renderDeclarations()}
                  {currentStep === 5 && renderHealthScreening()}
                  {currentStep === 6 && renderReview()}

                  {/* Navigation */}
                  <div className="flex justify-between mt-8 pt-6 border-t border-[#E4E8EB]">
                    {currentStep > 1 ? (
                      <Button type="button" variant="outline" onClick={prevStep} className="rounded-full">
                        <ChevronLeft className="h-4 w-4 mr-1" /> Back
                      </Button>
                    ) : (
                      <div />
                    )}
                    
                    {currentStep < 6 ? (
                      <Button type="button" onClick={nextStep} className="bg-primary hover:bg-primary-hover text-white rounded-full">
                        Continue <ChevronRight className="h-4 w-4 ml-1" />
                      </Button>
                    ) : (
                      <Button
                        type="submit"
                        disabled={isSubmitting}
                        className="bg-primary hover:bg-primary-hover text-white rounded-full"
                        data-testid="apply-submit"
                      >
                        {isSubmitting ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Submitting...
                          </>
                        ) : (
                          'Submit Application'
                        )}
                      </Button>
                    )}
                  </div>
                </form>
              </div>
            </>
          )}
        </div>
      </section>

      <Footer />
    </div>
  );
}
