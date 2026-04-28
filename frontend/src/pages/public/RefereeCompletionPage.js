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
  UserCheck, CheckCircle, XCircle, Loader2, AlertTriangle,
  Send, Home, Clock, Shield, FileText, Info
} from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_ROOT_URL;

export default function RefereeCompletionPage() {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState(null);
  const [formValues, setFormValues] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    fetchRefereeForm();
  }, [token]);

  const fetchRefereeForm = async () => {
    try {
      const response = await axios.get(`${API}/api/referee/complete/${token}`);
      setFormData(response.data);
      // Pre-fill with declared details as hints
      if (response.data.declared_referee_details) {
        setFormValues({
          referee_full_name: response.data.declared_referee_details.name || '',
          referee_organisation: response.data.declared_referee_details.company || '',
        });
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.includes('expired') || detail?.includes('invalid')) {
        setError({ type: 'expired', message: 'This reference link has expired or is no longer valid.' });
      } else if (detail?.includes('already been submitted')) {
        setError({ type: 'submitted', message: 'This reference has already been submitted. Thank you for your response.' });
      } else {
        setError({ type: 'error', message: detail || 'Failed to load reference form' });
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
          // Handle conditional fields
          if (field.conditional_on) {
            const conditionValue = formValues[field.conditional_on];
            if (conditionValue !== field.conditional_value) {
              return; // Skip - condition not met
            }
          }
          missingFields.push(field.label || field.id);
        }
      });
    });
    
    if (missingFields.length > 0) {
      toast.error(`Please complete required fields: ${missingFields.slice(0, 3).join(', ')}${missingFields.length > 3 ? '...' : ''}`);
      return;
    }

    // Validate declarations
    if (!formValues.declaration_accurate || !formValues.declaration_authority) {
      toast.error('Please confirm both declarations before submitting');
      return;
    }
    
    setSubmitting(true);
    try {
      await axios.post(`${API}/api/referee/complete/${token}`, formValues);
      setSubmitted(true);
      toast.success('Reference submitted successfully!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit reference');
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
    
    return (
      <div key={fieldKey} className="space-y-2">
        <Label className="text-gray-700 font-medium flex items-center gap-1">
          {field.label}
          {isRequired && <span className="text-red-500">*</span>}
        </Label>
        
        {field.type === 'text' && (
          <Input
            value={value}
            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
            placeholder={field.placeholder}
            required={isRequired}
            className="bg-white border-gray-200"
            data-testid={`field-${fieldKey}`}
          />
        )}
        
        {field.type === 'textarea' && (
          <Textarea
            value={value}
            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
            placeholder={field.placeholder}
            required={isRequired}
            rows={3}
            className="bg-white border-gray-200"
            data-testid={`field-${fieldKey}`}
          />
        )}
        
        {field.type === 'date' && (
          <Input
            type="date"
            value={value}
            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
            required={isRequired}
            className="bg-white border-gray-200"
            data-testid={`field-${fieldKey}`}
          />
        )}
        
        {field.type === 'select' && (
          <Select value={value} onValueChange={(val) => handleFieldChange(fieldKey, val)}>
            <SelectTrigger className="bg-white border-gray-200" data-testid={`field-${fieldKey}`}>
              <SelectValue placeholder={`Select...`} />
            </SelectTrigger>
            <SelectContent>
              {field.options?.map((option) => (
                <SelectItem key={option} value={option}>{option}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        
        {field.type === 'checkbox' && (
          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
            <Checkbox
              id={fieldKey}
              checked={!!value}
              onCheckedChange={(checked) => handleFieldChange(fieldKey, checked)}
              data-testid={`field-${fieldKey}`}
            />
            <Label htmlFor={fieldKey} className="text-sm text-gray-700 font-normal cursor-pointer leading-relaxed">
              {field.label}
            </Label>
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8FAFA] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-[#0d6c6c] mx-auto mb-4" />
          <p className="text-gray-500">Loading reference form...</p>
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
              ) : error.type === 'submitted' ? (
                <CheckCircle className="h-8 w-8 text-green-600" />
              ) : (
                <XCircle className="h-8 w-8 text-red-600" />
              )}
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              {error.type === 'expired' ? 'Link Expired' : 
               error.type === 'submitted' ? 'Already Submitted' : 'Something Went Wrong'}
            </h2>
            <p className="text-gray-600 mb-6">{error.message}</p>
            {error.type !== 'submitted' && (
              <p className="text-sm text-gray-500">
                Please contact the recruitment team for assistance.
              </p>
            )}
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
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Reference Submitted Successfully
            </h2>
            <p className="text-gray-600 mb-4">
              Thank you for providing a reference for <strong>{formData?.applicant_name}</strong>.
            </p>
            <p className="text-sm text-gray-500 mb-6">
              Your response has been securely submitted and will be reviewed by the recruitment team.
            </p>
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-100 text-sm text-blue-800">
              <Shield className="h-4 w-4 inline mr-1" />
              This reference will be treated as confidential and used solely for employment verification purposes.
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const template = formData?.form_template;

  return (
    <div className="min-h-screen bg-[#F8FAFA]">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <div className="w-10 h-10 bg-[#0d6c6c]/10 rounded-xl flex items-center justify-center">
            <UserCheck className="h-5 w-5 text-[#0d6c6c]" />
          </div>
          <div>
            <h1 className="font-semibold text-gray-900">
              Employment Reference Request
            </h1>
            <p className="text-sm text-gray-500">
              Reference for: <span className="font-medium text-gray-700">{formData?.applicant_name}</span>
            </p>
          </div>
        </div>
      </header>

      {/* Form Content */}
      <main className="max-w-3xl mx-auto px-4 py-8">
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            {/* Context Card */}
            <Card className="border-[#0d6c6c]/20 bg-[#0d6c6c]/5">
              <CardContent className="pt-4">
                <div className="flex items-start gap-3">
                  <Info className="h-5 w-5 text-[#0d6c6c] flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm text-gray-700 mb-2">
                      <strong>{formData?.applicant_name}</strong> has applied for a care position with 
                      Osabea Healthcare Solutions and has provided your details as a referee.
                    </p>
                    <p className="text-sm text-gray-600">
                      Please complete all required fields marked with <span className="text-red-500">*</span>. 
                      Your response will be treated as confidential.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Declared Details Reference (if different from what referee enters, will flag mismatch) */}
            {formData?.declared_referee_details?.name && (
              <Card className="border-amber-200 bg-amber-50/50">
                <CardContent className="pt-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-amber-900 mb-1">Details Provided by Applicant</p>
                      <p className="text-sm text-amber-800">
                        The applicant declared your details as:{' '}
                        <strong>{formData.declared_referee_details.name}</strong>
                        {formData.declared_referee_details.company && (
                          <> at <strong>{formData.declared_referee_details.company}</strong></>
                        )}
                      </p>
                      <p className="text-xs text-amber-700 mt-1">
                        If your details differ, please enter your correct information below.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Form Sections */}
            {template?.sections?.map((section) => (
              <Card key={section.id} className="border-gray-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">{section.title}</CardTitle>
                  {section.description && (
                    <CardDescription>{section.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent className="space-y-4">
                  {section.fields?.map((field) => renderField(field, section.id))}
                </CardContent>
              </Card>
            ))}

            {/* Data Protection Notice */}
            <Card className="border-gray-200 bg-gray-50">
              <CardContent className="pt-4">
                <div className="flex items-start gap-3">
                  <Shield className="h-5 w-5 text-gray-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-1">Data Protection Notice</p>
                    <p className="text-xs text-gray-600">
                      The information you provide will be used solely for employment verification purposes 
                      and handled in accordance with data protection regulations. This reference will be 
                      treated as confidential and shared only with relevant recruitment personnel.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Submit Button */}
            <div className="flex justify-end gap-3 pt-4">
              <Button
                type="submit"
                disabled={submitting}
                className="bg-[#0d6c6c] hover:bg-[#0a5a5a] text-white px-8"
                data-testid="submit-reference-btn"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Submit Reference
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
          <p className="text-xs mt-1">This link is unique to you and expires after 30 days or upon submission.</p>
        </div>
      </footer>
    </div>
  );
}

