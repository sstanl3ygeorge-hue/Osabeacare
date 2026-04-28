/**
 * AgreementFormDrawer.js
 * 
 * Multi-section form drawer for completing agreement templates.
 * 
 * Features:
 * - Dynamic form generation from template structure
 * - Multi-section layout with collapsible panels
 * - Read-only legal text sections
 * - Declaration with checkboxes and signature
 * - Completion mode selection (self, admin_assisted, phone_assisted)
 * - PDF export functionality
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Checkbox } from '../ui/checkbox';
import { Badge } from '../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { 
  X, ChevronDown, ChevronUp, Loader2, FileText, CheckCircle, 
  User, Calendar, DollarSign, Building, Send, Download, Eye,
  Phone, UserCheck, PenTool
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

/**
 * Section component for organizing content
 */
function FormSection({ title, description, icon: Icon, children, defaultOpen = true, readOnly = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <div className={`border rounded-xl overflow-hidden ${readOnly ? 'border-gray-200 bg-gray-50/50' : 'border-gray-300'}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 bg-white hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {Icon && <Icon className={`h-5 w-5 ${readOnly ? 'text-gray-400' : 'text-primary'}`} />}
          <div className="text-left">
            <span className="font-medium text-gray-900">{title}</span>
            {readOnly && (
              <Badge className="ml-2 text-xs bg-gray-100 text-gray-600">Read Only</Badge>
            )}
          </div>
        </div>
        {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {isOpen && (
        <div className="p-4 border-t border-gray-200 bg-white">
          {description && (
            <p className="text-sm text-gray-500 mb-4">{description}</p>
          )}
          {children}
        </div>
      )}
    </div>
  );
}

/**
 * Completion mode selector
 */
function CompletionModeSelector({ value, onChange, disabled }) {
  const modes = [
    { value: 'self', label: 'Self Completion', icon: User, description: 'Employee completed independently' },
    { value: 'admin_assisted', label: 'Admin Assisted', icon: UserCheck, description: 'Admin filled on behalf of employee' },
    { value: 'phone_assisted', label: 'Phone Assisted', icon: Phone, description: 'Recorded during phone call with employee' },
  ];
  
  return (
    <div className="space-y-2">
      <Label>Completion Mode</Label>
      <div className="grid grid-cols-3 gap-3">
        {modes.map((mode) => {
          const Icon = mode.icon;
          const isSelected = value === mode.value;
          return (
            <button
              key={mode.value}
              type="button"
              disabled={disabled}
              onClick={() => onChange(mode.value)}
              className={`p-3 rounded-lg border-2 text-left transition-all ${
                isSelected 
                  ? 'border-primary bg-primary/5' 
                  : 'border-gray-200 hover:border-gray-300'
              } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon className={`h-4 w-4 ${isSelected ? 'text-primary' : 'text-gray-400'}`} />
                <span className={`text-sm font-medium ${isSelected ? 'text-primary' : 'text-gray-700'}`}>
                  {mode.label}
                </span>
              </div>
              <p className="text-xs text-gray-500">{mode.description}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function AgreementFormDrawer({
  isOpen,
  onClose,
  employeeId,
  templateId,
  employeeData,
  onSubmitSuccess,
  mode = 'create', // 'create' or 'view'
  existingSubmission = null
}) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [template, setTemplate] = useState(null);
  const [formData, setFormData] = useState({});
  const [completionMode, setCompletionMode] = useState('self');
  const [adminNote, setAdminNote] = useState('');
  const [errors, setErrors] = useState({});
  const [submission, setSubmission] = useState(null);

  // Fetch template on open
  useEffect(() => {
    if (isOpen && templateId) {
      fetchTemplate();
    }
    // Fetch submission when viewing
    if (isOpen && mode === 'view' && existingSubmission?.id) {
      fetchSubmission(existingSubmission.id);
    }
  }, [isOpen, templateId, mode, existingSubmission]);

  // Fetch submission data
  const fetchSubmission = async (submissionId) => {
    try {
      const response = await axios.get(
        `${API}/agreement-submissions/${submissionId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const sub = response.data.submission;
      setSubmission(sub);
      setFormData(sub.form_data || {});
      setCompletionMode(sub.completion_mode || 'self');
      setAdminNote(sub.admin_note || '');
      // Also get template from response
      if (response.data.template) {
        setTemplate(response.data.template);
      }
    } catch (err) {
      toast.error('Failed to load submission');
      console.error(err);
    }
  };

  // Pre-fill form with employee data
  useEffect(() => {
    if (template && employeeData && mode === 'create') {
      const prefilled = {
        employee_name: `${employeeData.first_name || ''} ${employeeData.last_name || ''}`.trim(),
        employee_role: employeeData.job_title || employeeData.role || '',
        job_title: employeeData.job_title || employeeData.role || '',
        start_date: employeeData.start_date || '',
        continuous_service_date: employeeData.continuous_service_date || employeeData.start_date || '',
        signature_date: new Date().toISOString().split('T')[0],
      };
      setFormData(prev => ({ ...prefilled, ...prev }));
    }
  }, [template, employeeData, mode]);

  // Load existing submission data
  useEffect(() => {
    if (existingSubmission && mode === 'view') {
      setFormData(existingSubmission.form_data || {});
      setCompletionMode(existingSubmission.completion_mode || 'self');
      setAdminNote(existingSubmission.admin_note || '');
    }
  }, [existingSubmission, mode]);

  const fetchTemplate = async () => {
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/agreement-templates/${templateId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setTemplate(response.data);
    } catch (err) {
      toast.error('Failed to load agreement template');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
    // Clear error when field is edited
    if (errors[key]) {
      setErrors(prev => ({ ...prev, [key]: null }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    // Check all sections for required fields
    template?.sections?.forEach(section => {
      section.fields?.forEach(field => {
        if (field.required && !formData[field.key]) {
          newErrors[field.key] = `${field.label} is required`;
        }
      });
    });
    
    // Admin note required for assisted modes
    if (completionMode !== 'self' && !adminNote.trim()) {
      newErrors.adminNote = 'Admin note is required for assisted completion modes';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      toast.error('Please complete all required fields');
      return;
    }
    
    setSubmitting(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/agreement-submissions`,
        {
          template_id: templateId,
          form_data: formData,
          completion_mode: completionMode,
          admin_note: completionMode !== 'self' ? adminNote : null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Agreement submitted successfully');
      if (onSubmitSuccess) onSubmitSuccess();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit agreement');
    } finally {
      setSubmitting(false);
    }
  };

  const handleExportPDF = async () => {
    if (!existingSubmission) return;
    
    try {
      const response = await axios.get(
        `${API}/agreement-submissions/${existingSubmission.id}/pdf`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Open HTML content in new window for printing/saving as PDF
      const printWindow = window.open('', '_blank');
      printWindow.document.write(response.data.html_content);
      printWindow.document.close();
      printWindow.print();
    } catch (err) {
      toast.error('Failed to export PDF');
    }
  };

  // Render a form field based on type
  const renderField = (field) => {
    const value = formData[field.key] || '';
    const error = errors[field.key];
    const isReadOnly = mode === 'view' || field.field_type === 'readonly';
    
    switch (field.field_type) {
      case 'text':
      case 'email':
      case 'phone':
        return (
          <div key={field.key} className="space-y-1">
            <Label className={field.required ? 'after:content-["*"] after:text-red-500 after:ml-1' : ''}>
              {field.label}
            </Label>
            <Input
              type={field.field_type === 'email' ? 'email' : 'text'}
              value={value}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              placeholder={field.placeholder}
              disabled={isReadOnly}
              className={error ? 'border-red-500' : ''}
              data-testid={`field-${field.key}`}
            />
            {field.help_text && <p className="text-xs text-gray-500">{field.help_text}</p>}
            {error && <p className="text-xs text-red-500">{error}</p>}
          </div>
        );
      
      case 'date':
        return (
          <div key={field.key} className="space-y-1">
            <Label className={field.required ? 'after:content-["*"] after:text-red-500 after:ml-1' : ''}>
              {field.label}
            </Label>
            <Input
              type="date"
              value={value}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              disabled={isReadOnly}
              className={error ? 'border-red-500' : ''}
              data-testid={`field-${field.key}`}
            />
            {field.help_text && <p className="text-xs text-gray-500">{field.help_text}</p>}
            {error && <p className="text-xs text-red-500">{error}</p>}
          </div>
        );
      
      case 'currency':
      case 'number':
        return (
          <div key={field.key} className="space-y-1">
            <Label className={field.required ? 'after:content-["*"] after:text-red-500 after:ml-1' : ''}>
              {field.label}
            </Label>
            <div className="relative">
              {field.field_type === 'currency' && (
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">£</span>
              )}
              <Input
                type="number"
                step={field.field_type === 'currency' ? '0.01' : '1'}
                value={value}
                onChange={(e) => handleFieldChange(field.key, e.target.value)}
                placeholder={field.placeholder}
                disabled={isReadOnly}
                className={`${field.field_type === 'currency' ? 'pl-7' : ''} ${error ? 'border-red-500' : ''}`}
                data-testid={`field-${field.key}`}
              />
            </div>
            {field.help_text && <p className="text-xs text-gray-500">{field.help_text}</p>}
            {error && <p className="text-xs text-red-500">{error}</p>}
          </div>
        );
      
      case 'checkbox':
        return (
          <div key={field.key} className="flex items-start space-x-3 py-2">
            <Checkbox
              id={field.key}
              checked={!!value}
              onCheckedChange={(checked) => handleFieldChange(field.key, checked)}
              disabled={isReadOnly}
              className={error ? 'border-red-500' : ''}
              data-testid={`field-${field.key}`}
            />
            <div className="space-y-1">
              <Label 
                htmlFor={field.key} 
                className={`cursor-pointer ${field.required ? 'after:content-["*"] after:text-red-500 after:ml-1' : ''}`}
              >
                {field.label}
              </Label>
              {error && <p className="text-xs text-red-500">{error}</p>}
            </div>
          </div>
        );
      
      case 'signature':
        return (
          <div key={field.key} className="space-y-2">
            <Label className={field.required ? 'after:content-["*"] after:text-red-500 after:ml-1' : ''}>
              {field.label}
            </Label>
            <div className="relative">
              <PenTool className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                type="text"
                value={value}
                onChange={(e) => handleFieldChange(field.key, e.target.value)}
                placeholder={field.placeholder}
                disabled={isReadOnly}
                className={`pl-10 font-serif italic text-lg ${error ? 'border-red-500' : ''}`}
                data-testid={`field-${field.key}`}
              />
            </div>
            {field.help_text && <p className="text-xs text-gray-500">{field.help_text}</p>}
            {error && <p className="text-xs text-red-500">{error}</p>}
          </div>
        );
      
      case 'readonly':
        return (
          <div key={field.key} className="space-y-1">
            <Label className="text-gray-500">{field.label}</Label>
            <div className="p-2 bg-gray-100 rounded text-gray-700 text-sm">
              {field.default_value || value || '-'}
            </div>
          </div>
        );
      
      case 'textarea':
        return (
          <div key={field.key} className="space-y-1">
            <Label className={field.required ? 'after:content-["*"] after:text-red-500 after:ml-1' : ''}>
              {field.label}
            </Label>
            <Textarea
              value={value}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              placeholder={field.placeholder}
              disabled={isReadOnly}
              className={error ? 'border-red-500' : ''}
              data-testid={`field-${field.key}`}
            />
            {field.help_text && <p className="text-xs text-gray-500">{field.help_text}</p>}
            {error && <p className="text-xs text-red-500">{error}</p>}
          </div>
        );
      
      default:
        return (
          <div key={field.key} className="space-y-1">
            <Label>{field.label}</Label>
            <Input
              value={value}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              disabled={isReadOnly}
              data-testid={`field-${field.key}`}
            />
          </div>
        );
    }
  };

  // Get icon for section
  const getSectionIcon = (sectionKey) => {
    const icons = {
      employee_details: User,
      pay_and_hours: DollarSign,
      legal_terms: FileText,
      holiday_and_leave: Calendar,
      declaration: CheckCircle,
      handbook_details: FileText,
      handbook_contents: FileText,
      acknowledgements: CheckCircle,
    };
    return icons[sectionKey] || FileText;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" data-testid="agreement-form-drawer">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="relative w-full max-w-2xl bg-white shadow-xl overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <FileText className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  {mode === 'view' ? 'View Submission' : 'Complete Agreement'}
                </h2>
                <p className="text-sm text-gray-500">
                  {template?.template_name || 'Loading...'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {mode === 'view' && existingSubmission && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportPDF}
                  data-testid="export-pdf-btn"
                >
                  <Download className="h-4 w-4 mr-1" />
                  Export PDF
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={onClose}>
                <X className="h-5 w-5" />
              </Button>
            </div>
          </div>
          
          {/* Verification status badge for view mode */}
          {mode === 'view' && submission && (
            <div className="mt-3">
              <Badge className={
                submission.verification_status === 'verified' 
                  ? 'bg-green-100 text-green-700' 
                  : submission.verification_status === 'rejected'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-amber-100 text-amber-700'
              }>
                {submission.verification_status?.replace('_', ' ').toUpperCase()}
              </Badge>
              <span className="ml-2 text-sm text-gray-500">
                Completed: {submission.completed_at?.substring(0, 10)} | 
                Mode: {submission.completion_mode?.replace('_', ' ')}
              </span>
            </div>
          )}
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}

        {/* Form content */}
        {!loading && template && (
          <div className="p-6 space-y-4">
            {/* Company info */}
            <div className="p-4 bg-gray-50 rounded-lg flex items-center gap-3">
              <Building className="h-5 w-5 text-gray-400" />
              <div>
                <p className="font-medium text-gray-900">{template.company_name}</p>
                <p className="text-sm text-gray-500">Version {template.version} | {template.version_date}</p>
              </div>
            </div>

            {/* Completion Mode Selector (only in create mode) */}
            {mode === 'create' && (
              <CompletionModeSelector
                value={completionMode}
                onChange={setCompletionMode}
                disabled={submitting}
              />
            )}

            {/* Admin Note (for assisted modes) */}
            {(mode === 'create' && completionMode !== 'self') && (
              <div className="space-y-2">
                <Label className="after:content-['*'] after:text-red-500 after:ml-1">
                  Admin Note
                </Label>
                <Textarea
                  value={adminNote}
                  onChange={(e) => setAdminNote(e.target.value)}
                  placeholder="Describe how completion was assisted..."
                  className={errors.adminNote ? 'border-red-500' : ''}
                  data-testid="admin-note-input"
                />
                {errors.adminNote && <p className="text-xs text-red-500">{errors.adminNote}</p>}
              </div>
            )}

            {/* View mode admin note */}
            {mode === 'view' && existingSubmission?.admin_note && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm font-medium text-blue-800">Admin Note:</p>
                <p className="text-sm text-blue-700">{existingSubmission.admin_note}</p>
              </div>
            )}

            {/* Form Sections */}
            {template.sections?.map((section) => {
              const SectionIcon = getSectionIcon(section.key);
              
              return (
                <FormSection
                  key={section.key}
                  title={section.title}
                  description={section.description}
                  icon={SectionIcon}
                  defaultOpen={!section.read_only || section.key === 'declaration'}
                  readOnly={section.read_only}
                >
                  {/* Legal text for read-only sections */}
                  {section.read_only && template.legal_text_sections?.[section.key] && (
                    <div className="prose prose-sm max-w-none">
                      <ReactMarkdown>
                        {template.legal_text_sections[section.key]
                          .replace(/\{\{employee_name\}\}/g, formData.employee_name || '[Employee Name]')
                          .replace(/\{\{job_title\}\}/g, formData.job_title || '[Job Title]')
                          .replace(/\{\{start_date\}\}/g, formData.start_date || '[Start Date]')
                          .replace(/\{\{continuous_service_date\}\}/g, formData.continuous_service_date || '[Continuous Service Date]')
                          .replace(/\{\{hourly_rate\}\}/g, formData.hourly_rate || '[Hourly Rate]')
                          .replace(/\{\{sleep_in_rate\}\}/g, formData.sleep_in_rate || '40.00')
                        }
                      </ReactMarkdown>
                    </div>
                  )}
                  
                  {/* Form fields */}
                  {section.fields?.length > 0 && (
                    <div className={`${section.read_only ? 'mt-4 pt-4 border-t' : ''} space-y-4`}>
                      {section.key === 'declaration' && section.fields?.some(f => f.field_type === 'checkbox') && (
                        <div className="space-y-3">
                          {section.fields.filter(f => f.field_type === 'checkbox').map(renderField)}
                        </div>
                      )}
                      
                      <div className="grid grid-cols-2 gap-4">
                        {section.fields.filter(f => f.field_type !== 'checkbox').map(renderField)}
                      </div>
                      
                      {section.key !== 'declaration' && section.fields?.some(f => f.field_type === 'checkbox') && (
                        <div className="space-y-3 mt-4">
                          {section.fields.filter(f => f.field_type === 'checkbox').map(renderField)}
                        </div>
                      )}
                    </div>
                  )}
                </FormSection>
              );
            })}

            {/* Submit Button (only in create mode) */}
            {mode === 'create' && (
              <div className="pt-4 border-t">
                <Button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="w-full"
                  data-testid="submit-agreement-btn"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      Submit Agreement
                    </>
                  )}
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

