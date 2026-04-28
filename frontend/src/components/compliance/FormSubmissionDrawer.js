import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '../ui/sheet';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Checkbox } from '../ui/checkbox';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';
import { Separator } from '../ui/separator';
import { 
  Loader2, 
  Download, 
  CheckCircle, 
  XCircle, 
  Send, 
  Save,
  FileText,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

/**
 * FormSubmissionDrawer - Universal drawer for form-type requirements
 * 
 * Modes:
 * - 'create' - Fill out new form
 * - 'view' - View existing submission (read-only)
 * - 'edit' - Edit existing submission
 * 
 * Supports all form types from FORM_BASED_REQUIREMENTS:
 * - staff_health_questionnaire
 * - staff_personal_info
 * - hmrc_starter_checklist
 * - interview_record
 * - equal_opportunities
 * - induction
 * - recruitment_checklist
 */
export default function FormSubmissionDrawer({
  isOpen,
  onClose,
  employeeId,
  employeeName,
  formKey,           // e.g., 'staff_health_questionnaire'
  formType,          // Same as formKey typically
  submissionId,      // For view/edit mode
  mode = 'create',   // 'create', 'view', 'edit'
  onSubmitSuccess,
  onVerify,
  onReject
}) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [template, setTemplate] = useState(null);
  const [formData, setFormData] = useState({});
  const [autoFillData, setAutoFillData] = useState({});
  const [existingSubmission, setExistingSubmission] = useState(null);
  const [expandedSections, setExpandedSections] = useState({});
  const [completionMode, setCompletionMode] = useState('admin_assisted');
  const [validationErrors, setValidationErrors] = useState({});
  
  // Fetch template and auto-fill data
  const fetchFormData = useCallback(async () => {
    if (!formKey || !employeeId) return;
    
    setLoading(true);
    try {
      // Fetch template
      const templateRes = await axios.get(
        `${API}/form-submissions/template/${formKey}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setTemplate(templateRes.data);
      
      // Initialize expanded sections
      const sections = templateRes.data.sections || [];
      const expanded = {};
      sections.forEach((sec, idx) => {
        expanded[sec.key || idx] = idx === 0; // Expand first section by default
      });
      setExpandedSections(expanded);
      
      // Fetch auto-fill data for create/edit
      if (mode === 'create' || mode === 'edit') {
        const autoFillRes = await axios.get(
          `${API}/form-submissions/auto-fill/${formKey}/${employeeId}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setAutoFillData(autoFillRes.data);
        
        // Pre-populate form data with auto-fill
        if (mode === 'create') {
          setFormData(autoFillRes.data);
        }
      }
      
      // Fetch existing submission for view/edit
      if ((mode === 'view' || mode === 'edit') && submissionId) {
        const subRes = await axios.get(
          `${API}/form-submissions/${submissionId}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setExistingSubmission(subRes.data);
        setFormData(subRes.data.data || {});
      }
      
    } catch (err) {
      console.error('Error fetching form data:', err);
      toast.error('Failed to load form');
    } finally {
      setLoading(false);
    }
  }, [formKey, employeeId, submissionId, mode, token]);
  
  useEffect(() => {
    if (isOpen && formKey) {
      fetchFormData();
    }
  }, [isOpen, formKey, fetchFormData]);
  
  // Handle field change
  const handleFieldChange = (fieldId, value) => {
    setFormData(prev => ({
      ...prev,
      [fieldId]: value
    }));
    // Clear validation error for this field
    if (validationErrors[fieldId]) {
      setValidationErrors(prev => {
        const next = { ...prev };
        delete next[fieldId];
        return next;
      });
    }
  };
  
  // Validate form
  const validateForm = () => {
    const errors = {};
    const sections = template?.sections || [];
    
    sections.forEach(section => {
      (section.fields || []).forEach(field => {
        if (field.required && !formData[field.id]) {
          errors[field.id] = 'This field is required';
        }
      });
    });
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };
  
  // Handle form submission
  const handleSubmit = async (status = 'submitted') => {
    if (!validateForm()) {
      toast.error('Please fill in all required fields');
      return;
    }
    
    setSubmitting(true);
    try {
      if (mode === 'edit' && existingSubmission) {
        // Update existing submission
        await axios.put(
          `${API}/form-submissions/${existingSubmission.id}`,
          {
            data: formData,
            status: status
          },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success('Form updated successfully');
      } else {
        // Create new submission
        await axios.post(
          `${API}/form-submissions`,
          {
            employee_id: employeeId,
            requirement_id: formKey,
            form_type: formType || formKey,
            data: formData,
            status: status,
            completion_mode: completionMode
          },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success('Form submitted successfully');
      }
      
      onSubmitSuccess && onSubmitSuccess();
      onClose();
    } catch (err) {
      console.error('Error submitting form:', err);
      toast.error(err.response?.data?.detail || 'Failed to submit form');
    } finally {
      setSubmitting(false);
    }
  };
  
  // Handle PDF export
  const handleExportPdf = async () => {
    if (!existingSubmission?.id) return;
    
    try {
      const response = await axios.get(
        `${API}/form-submissions/${existingSubmission.id}/download-pdf`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `${formKey}_${existingSubmission.id}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      toast.error('Failed to download PDF');
    }
  };
  
  // Render form field based on type
  const renderField = (field) => {
    const value = formData[field.id] || '';
    const isReadOnly = mode === 'view';
    const error = validationErrors[field.id];
    
    switch (field.type) {
      case 'text':
      case 'email':
      case 'tel':
      case 'number':
        return (
          <Input
            type={field.type}
            value={value}
            onChange={(e) => handleFieldChange(field.id, e.target.value)}
            placeholder={field.placeholder || ''}
            disabled={isReadOnly}
            className={cn(error && 'border-red-500')}
          />
        );
        
      case 'textarea':
        return (
          <Textarea
            value={value}
            onChange={(e) => handleFieldChange(field.id, e.target.value)}
            placeholder={field.placeholder || ''}
            disabled={isReadOnly}
            rows={field.rows || 3}
            className={cn(error && 'border-red-500')}
          />
        );
        
      case 'date':
        return (
          <Input
            type="date"
            value={value}
            onChange={(e) => handleFieldChange(field.id, e.target.value)}
            disabled={isReadOnly}
            className={cn(error && 'border-red-500')}
          />
        );
        
      case 'select':
        return (
          <Select
            value={value}
            onValueChange={(val) => handleFieldChange(field.id, val)}
            disabled={isReadOnly}
          >
            <SelectTrigger className={cn(error && 'border-red-500')}>
              <SelectValue placeholder={field.placeholder || 'Select...'} />
            </SelectTrigger>
            <SelectContent>
              {(field.options || []).map(opt => (
                <SelectItem key={opt.value || opt} value={opt.value || opt}>
                  {opt.label || opt}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
        
      case 'checkbox':
        return (
          <div className="flex items-center gap-2">
            <Checkbox
              checked={value === true || value === 'true'}
              onCheckedChange={(checked) => handleFieldChange(field.id, checked)}
              disabled={isReadOnly}
            />
            {field.checkboxLabel && (
              <span className="text-sm">{field.checkboxLabel}</span>
            )}
          </div>
        );
        
      case 'radio':
        return (
          <RadioGroup
            value={value}
            onValueChange={(val) => handleFieldChange(field.id, val)}
            disabled={isReadOnly}
          >
            {(field.options || []).map(opt => (
              <div key={opt.value || opt} className="flex items-center gap-2">
                <RadioGroupItem value={opt.value || opt} />
                <Label>{opt.label || opt}</Label>
              </div>
            ))}
          </RadioGroup>
        );
        
      case 'boolean':
        return (
          <RadioGroup
            value={value === true || value === 'true' || value === 'yes' ? 'yes' : value === false || value === 'false' || value === 'no' ? 'no' : ''}
            onValueChange={(val) => handleFieldChange(field.id, val)}
            disabled={isReadOnly}
            className="flex gap-4"
          >
            <div className="flex items-center gap-2">
              <RadioGroupItem value="yes" />
              <Label>Yes</Label>
            </div>
            <div className="flex items-center gap-2">
              <RadioGroupItem value="no" />
              <Label>No</Label>
            </div>
          </RadioGroup>
        );
        
      default:
        return (
          <Input
            type="text"
            value={value}
            onChange={(e) => handleFieldChange(field.id, e.target.value)}
            placeholder={field.placeholder || ''}
            disabled={isReadOnly}
          />
        );
    }
  };
  
  // Get status badge
  const getStatusBadge = () => {
    if (!existingSubmission) return null;
    
    const status = existingSubmission.status;
    
    if (existingSubmission.verified || status === 'verified' || status === 'signed_off') {
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
        Draft
      </Badge>
    );
  };
  
  const toggleSection = (sectionKey) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionKey]: !prev[sectionKey]
    }));
  };
  
  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent 
        className="w-full sm:max-w-2xl overflow-y-auto"
        data-testid="form-submission-drawer"
      >
        <SheetHeader className="pb-4 border-b">
          <div className="flex items-center justify-between">
            <div>
              <SheetTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-teal-600" />
                {mode === 'view' ? 'View Submission' : mode === 'edit' ? 'Edit Form' : 'Complete Form'}
              </SheetTitle>
              <SheetDescription>
                {template?.name || formKey?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                {employeeName && <span className="ml-2">• {employeeName}</span>}
              </SheetDescription>
            </div>
            {getStatusBadge()}
          </div>
        </SheetHeader>
        
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
          </div>
        ) : !template ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-500">
            <AlertCircle className="h-12 w-12 mb-4" />
            <p>Form template not found</p>
          </div>
        ) : (
          <div className="mt-6 space-y-6">
            {/* Rejection Notice */}
            {existingSubmission?.status === 'rejected' && existingSubmission.rejection_reason && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <XCircle className="h-5 w-5 text-red-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-red-800">This submission was rejected</p>
                    <p className="text-sm text-red-600 mt-1">{existingSubmission.rejection_reason}</p>
                    <p className="text-xs text-red-500 mt-2">
                      Rejected by {existingSubmission.rejected_by_name || existingSubmission.rejected_by} on {existingSubmission.rejected_at?.slice(0, 10)}
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Verification Notice */}
            {(existingSubmission?.verified || existingSubmission?.status === 'verified') && (
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-emerald-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-emerald-800">Verified</p>
                    <p className="text-xs text-emerald-600 mt-1">
                      By {existingSubmission.verified_by_name || existingSubmission.verified_by} on {existingSubmission.verified_at?.slice(0, 10)}
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Completion Mode Selector (for create mode) */}
            {mode === 'create' && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <Label className="text-sm font-medium">Completion Mode</Label>
                <RadioGroup
                  value={completionMode}
                  onValueChange={setCompletionMode}
                  className="flex flex-wrap gap-4 mt-2"
                >
                  <div className="flex items-center gap-2">
                    <RadioGroupItem value="admin_assisted" />
                    <Label className="font-normal">Admin Assisted</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <RadioGroupItem value="phone_assisted" />
                    <Label className="font-normal">Phone Assisted</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <RadioGroupItem value="self" />
                    <Label className="font-normal">Self-Completed</Label>
                  </div>
                </RadioGroup>
              </div>
            )}
            
            {/* Form Sections */}
            {(template.sections || []).map((section, sectionIdx) => {
              const sectionKey = section.key || sectionIdx;
              const isExpanded = expandedSections[sectionKey];
              
              return (
                <div key={sectionKey} className="border rounded-lg overflow-hidden">
                  {/* Section Header */}
                  <button
                    onClick={() => toggleSection(sectionKey)}
                    className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
                  >
                    <span className="font-medium text-gray-900">{section.title || `Section ${sectionIdx + 1}`}</span>
                    {isExpanded ? (
                      <ChevronUp className="h-4 w-4 text-gray-400" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-gray-400" />
                    )}
                  </button>
                  
                  {/* Section Content */}
                  {isExpanded && (
                    <div className="p-4 space-y-4">
                      {section.description && (
                        <p className="text-sm text-gray-500 mb-4">{section.description}</p>
                      )}
                      
                      {(section.fields || []).map(field => (
                        <div key={field.id} className="space-y-1.5">
                          <Label htmlFor={field.id} className="text-sm font-medium">
                            {field.label}
                            {field.required && <span className="text-red-500 ml-1">*</span>}
                          </Label>
                          {renderField(field)}
                          {field.hint && (
                            <p className="text-xs text-gray-500">{field.hint}</p>
                          )}
                          {validationErrors[field.id] && (
                            <p className="text-xs text-red-500">{validationErrors[field.id]}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
            
            {/* Actions */}
            <Separator className="my-6" />
            
            <div className="flex flex-wrap gap-3 justify-end pb-6">
              {mode === 'view' && (
                <>
                  <Button
                    variant="outline"
                    onClick={handleExportPdf}
                    data-testid="export-pdf-btn"
                  >
                    <Download className="h-4 w-4 mr-1.5" />
                    Export PDF
                  </Button>
                  
                  {/* Verify/Reject buttons for awaiting review */}
                  {existingSubmission?.status === 'submitted' && onVerify && (
                    <Button
                      variant="outline"
                      className="text-emerald-600 border-emerald-200 hover:bg-emerald-50"
                      onClick={() => onVerify(existingSubmission.id)}
                      data-testid="verify-form-btn"
                    >
                      <CheckCircle className="h-4 w-4 mr-1.5" />
                      Verify
                    </Button>
                  )}
                  
                  {existingSubmission?.status === 'submitted' && onReject && (
                    <Button
                      variant="outline"
                      className="text-red-600 border-red-200 hover:bg-red-50"
                      onClick={() => onReject(existingSubmission.id)}
                      data-testid="reject-form-btn"
                    >
                      <XCircle className="h-4 w-4 mr-1.5" />
                      Reject
                    </Button>
                  )}
                </>
              )}
              
              {(mode === 'create' || mode === 'edit') && (
                <>
                  <Button
                    variant="outline"
                    onClick={() => handleSubmit('draft')}
                    disabled={submitting}
                  >
                    <Save className="h-4 w-4 mr-1.5" />
                    Save Draft
                  </Button>
                  
                  <Button
                    onClick={() => handleSubmit('submitted')}
                    disabled={submitting}
                    data-testid="submit-form-btn"
                  >
                    {submitting ? (
                      <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4 mr-1.5" />
                    )}
                    Submit
                  </Button>
                </>
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

