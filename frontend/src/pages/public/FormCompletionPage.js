import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Checkbox } from '../../components/ui/checkbox';
import { 
  FileText, CheckCircle, XCircle, Loader2, AlertTriangle,
  ArrowLeft, Send, Home, Clock
} from 'lucide-react';
import { toast } from 'sonner';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

export default function FormCompletionPage() {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState(null);
  const [formValues, setFormValues] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    fetchFormData();
  }, [token]);

  const fetchFormData = async () => {
    try {
      const response = await axios.get(`${API}/api/forms/complete/${token}`);
      setFormData(response.data);
      // Pre-fill form with auto-fill data
      setFormValues(response.data.auto_fill_data || {});
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.includes('expired') || detail?.includes('invalid')) {
        setError({ type: 'expired', message: 'This form link has expired or is no longer valid.' });
      } else {
        setError({ type: 'error', message: detail || 'Failed to load form' });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (fieldId, value) => {
    setFormValues(prev => ({ ...prev, [fieldId]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate required fields
    const template = formData?.form_template;
    const missingFields = [];
    
    template?.sections?.forEach(section => {
      section.fields?.forEach(field => {
        if (field.required && !formValues[field.id]) {
          missingFields.push(field.label || field.id);
        }
      });
    });
    
    if (missingFields.length > 0) {
      toast.error(`Please complete required fields: ${missingFields.slice(0, 3).join(', ')}${missingFields.length > 3 ? '...' : ''}`);
      return;
    }
    
    setSubmitting(true);
    try {
      await axios.post(`${API}/api/forms/complete/${token}`, formValues);
      setSubmitted(true);
      toast.success('Form submitted successfully!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit form');
    } finally {
      setSubmitting(false);
    }
  };

  const renderField = (field, sectionId) => {
    const fieldKey = field.id;
    const value = formValues[fieldKey] || '';
    
    // Handle conditional fields
    if (field.conditional_on) {
      const conditionValue = formValues[field.conditional_on];
      if (conditionValue !== field.conditional_value) {
        return null;
      }
    }
    
    // Skip info fields
    if (field.type === 'info') {
      return (
        <div key={fieldKey} className="p-3 bg-blue-50 rounded-lg border border-blue-100 text-sm text-blue-800">
          {field.label}
        </div>
      );
    }
    
    const isRequired = field.required;
    const isPreFilled = formData?.auto_fill_data?.[fieldKey] !== undefined;
    
    return (
      <div key={fieldKey} className="space-y-2">
        <Label className="text-gray-700 font-medium flex items-center gap-1">
          {field.label}
          {isRequired && <span className="text-red-500">*</span>}
          {isPreFilled && (
            <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
              Pre-filled
            </span>
          )}
        </Label>
        
        {field.type === 'text' && (
          <Input
            value={value}
            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
            placeholder={field.placeholder}
            required={isRequired}
            className={`bg-white border-gray-200 ${isPreFilled ? 'border-green-200 bg-green-50/50' : ''}`}
          />
        )}
        
        {field.type === 'textarea' && (
          <Textarea
            value={value}
            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
            placeholder={field.placeholder}
            required={isRequired}
            rows={3}
            className={`bg-white border-gray-200 ${isPreFilled ? 'border-green-200 bg-green-50/50' : ''}`}
          />
        )}
        
        {field.type === 'date' && (
          <Input
            type="date"
            value={value}
            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
            required={isRequired}
            className={`bg-white border-gray-200 ${isPreFilled ? 'border-green-200 bg-green-50/50' : ''}`}
          />
        )}
        
        {field.type === 'select' && (
          <Select value={value} onValueChange={(val) => handleFieldChange(fieldKey, val)}>
            <SelectTrigger className="bg-white border-gray-200">
              <SelectValue placeholder={`Select ${field.label}...`} />
            </SelectTrigger>
            <SelectContent>
              {field.options?.map((option) => (
                <SelectItem key={option} value={option}>{option}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        
        {field.type === 'checkbox' && (
          <div className="flex items-center gap-2">
            <Checkbox
              id={fieldKey}
              checked={!!value}
              onCheckedChange={(checked) => handleFieldChange(fieldKey, checked)}
            />
            <Label htmlFor={fieldKey} className="text-sm text-gray-600 font-normal cursor-pointer">
              {field.label}
            </Label>
          </div>
        )}
        
        {field.type === 'multi_select' && (
          <div className="space-y-2">
            {field.options?.map((option) => (
              <div key={option} className="flex items-center gap-2">
                <Checkbox
                  id={`${fieldKey}-${option}`}
                  checked={(value || []).includes(option)}
                  onCheckedChange={(checked) => {
                    const current = value || [];
                    if (checked) {
                      handleFieldChange(fieldKey, [...current, option]);
                    } else {
                      handleFieldChange(fieldKey, current.filter(v => v !== option));
                    }
                  }}
                />
                <Label htmlFor={`${fieldKey}-${option}`} className="text-sm text-gray-600 font-normal cursor-pointer">
                  {option}
                </Label>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8FAFA] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-text-muted">Loading form...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#F8FAFA] flex items-center justify-center p-4">
        <Card className="max-w-md w-full border-red-200">
          <CardContent className="pt-8 text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              {error.type === 'expired' ? (
                <Clock className="h-8 w-8 text-red-600" />
              ) : (
                <XCircle className="h-8 w-8 text-red-600" />
              )}
            </div>
            <h2 className="text-xl font-heading font-semibold text-gray-900 mb-2">
              {error.type === 'expired' ? 'Link Expired' : 'Something Went Wrong'}
            </h2>
            <p className="text-gray-600 mb-6">{error.message}</p>
            <p className="text-sm text-gray-500">
              Please contact your recruitment team for a new form link.
            </p>
            <Link to="/">
              <Button variant="outline" className="mt-6">
                <Home className="h-4 w-4 mr-2" />
                Go to Homepage
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-[#F8FAFA] flex items-center justify-center p-4">
        <Card className="max-w-md w-full border-green-200">
          <CardContent className="pt-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h2 className="text-xl font-heading font-semibold text-gray-900 mb-2">
              Form Submitted Successfully
            </h2>
            <p className="text-gray-600 mb-6">
              Thank you, {formData?.employee_name}! Your form has been received and will be reviewed by the team.
            </p>
            <p className="text-sm text-gray-500">
              You can close this page now.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const template = formData?.form_template;
  const preFilledCount = formData?.auto_fill_data ? Object.keys(formData.auto_fill_data).length : 0;

  return (
    <div className="min-h-screen bg-[#F8FAFA]">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="font-heading font-semibold text-gray-900">
              {template?.name || 'Form Completion'}
            </h1>
            <p className="text-sm text-gray-500">
              For: {formData?.employee_name}
            </p>
          </div>
        </div>
      </header>

      {/* Form Content */}
      <main className="max-w-3xl mx-auto px-4 py-8">
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            {/* Pre-fill Notice */}
            {preFilledCount > 0 && (
              <Card className="border-green-200 bg-green-50/50">
                <CardContent className="pt-4 flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-green-800">
                      {preFilledCount} field{preFilledCount !== 1 ? 's' : ''} pre-filled from your profile
                    </p>
                    <p className="text-xs text-green-700 mt-1">
                      Fields marked with "Pre-filled" have been automatically populated. Please review and update if needed.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
            
            {/* Intro Card */}
            <Card className="border-blue-100 bg-blue-50/50">
              <CardContent className="pt-4">
                <p className="text-sm text-blue-800">
                  Please complete all required fields marked with <span className="text-red-500">*</span>. 
                  Your information will be securely submitted to Osabea Healthcare Solutions.
                </p>
              </CardContent>
            </Card>

            {/* Form Sections */}
            {template?.sections?.map((section) => (
              <Card key={section.id} className="border-gray-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg font-heading">{section.title}</CardTitle>
                  {section.description && (
                    <CardDescription>{section.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent className="space-y-4">
                  {section.fields?.map((field) => renderField(field, section.id))}
                </CardContent>
              </Card>
            ))}

            {/* Submit Button */}
            <div className="flex justify-end gap-3">
              <Button
                type="submit"
                disabled={submitting}
                className="bg-primary hover:bg-primary-hover text-white px-8"
                data-testid="submit-form-btn"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Submit Form
                  </>
                )}
              </Button>
            </div>
          </div>
        </form>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 px-4 py-4 mt-8">
        <div className="max-w-3xl mx-auto text-center text-sm text-gray-500">
          <p>Osabea Healthcare Solutions - Safer Recruitment</p>
        </div>
      </footer>
    </div>
  );
}

