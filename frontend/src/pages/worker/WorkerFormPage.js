import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { RadioGroup, RadioGroupItem } from '../../components/ui/radio-group';
import { toast } from 'sonner';
import { 
  ArrowLeft, Save, Send, Loader2, CheckCircle, Clock,
  FileText, Heart, User, Briefcase
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Form field definitions for each form type
const FORM_FIELDS = {
  health_questionnaire: {
    icon: Heart,
    sections: [
      {
        title: "General Health",
        fields: [
          { id: "general_health", label: "How would you describe your general health?", type: "select", options: ["Excellent", "Good", "Fair", "Poor"], required: true },
          { id: "current_conditions", label: "Do you have any current medical conditions?", type: "textarea", placeholder: "Please list any conditions or write 'None'" },
          { id: "medications", label: "Are you currently taking any medications?", type: "textarea", placeholder: "Please list medications or write 'None'" },
        ]
      },
      {
        title: "Physical Requirements",
        fields: [
          { id: "lifting_capable", label: "Can you lift and move patients/equipment safely?", type: "radio", options: ["Yes", "No", "With assistance"], required: true },
          { id: "standing_capable", label: "Can you stand for extended periods?", type: "radio", options: ["Yes", "No", "With breaks"], required: true },
          { id: "physical_limitations", label: "Do you have any physical limitations we should know about?", type: "textarea" },
        ]
      },
      {
        title: "Vaccination Status",
        fields: [
          { id: "covid_vaccinated", label: "COVID-19 vaccination status", type: "select", options: ["Fully vaccinated", "Partially vaccinated", "Not vaccinated", "Medical exemption"], required: true },
          { id: "flu_vaccinated", label: "Flu vaccination (this season)", type: "radio", options: ["Yes", "No", "Planning to get"], required: true },
          { id: "hepatitis_b", label: "Hepatitis B vaccination status", type: "select", options: ["Fully vaccinated", "Partial", "Not vaccinated", "Unknown"] },
        ]
      }
    ]
  },
  personal_info: {
    icon: User,
    sections: [
      {
        title: "Personal Details",
        fields: [
          { id: "title", label: "Title", type: "select", options: ["Mr", "Mrs", "Ms", "Miss", "Dr", "Other"], required: true },
          { id: "preferred_name", label: "Preferred Name (if different)", type: "text" },
          { id: "date_of_birth", label: "Date of Birth", type: "date", required: true },
          { id: "national_insurance", label: "National Insurance Number", type: "text", placeholder: "e.g., AB123456C", required: true },
        ]
      },
      {
        title: "Contact Information",
        fields: [
          { id: "address_line1", label: "Address Line 1", type: "text", required: true },
          { id: "address_line2", label: "Address Line 2", type: "text" },
          { id: "city", label: "City/Town", type: "text", required: true },
          { id: "postcode", label: "Postcode", type: "text", required: true },
          { id: "mobile_phone", label: "Mobile Phone", type: "tel", required: true },
          { id: "home_phone", label: "Home Phone", type: "tel" },
        ]
      },
      {
        title: "Emergency Contact",
        fields: [
          { id: "emergency_name", label: "Emergency Contact Name", type: "text", required: true },
          { id: "emergency_relationship", label: "Relationship", type: "text", required: true },
          { id: "emergency_phone", label: "Emergency Contact Phone", type: "tel", required: true },
        ]
      }
    ]
  },
  hmrc_starter: {
    icon: Briefcase,
    sections: [
      {
        title: "Previous Employment",
        fields: [
          { id: "statement", label: "Which statement applies to you?", type: "radio", options: [
            "A: This is my first job since 6 April and I've not received any taxable benefits",
            "B: This is my only job but I've had another job or received benefits since 6 April",
            "C: I have another job or receive a State/Occupational Pension"
          ], required: true },
        ]
      },
      {
        title: "Student Loan",
        fields: [
          { id: "student_loan", label: "Do you have a student loan?", type: "radio", options: ["Yes", "No"], required: true },
          { id: "student_loan_plan", label: "If yes, which plan?", type: "select", options: ["Plan 1", "Plan 2", "Plan 4", "Postgraduate Loan", "Not applicable"] },
        ]
      },
      {
        title: "Bank Details",
        fields: [
          { id: "bank_name", label: "Bank Name", type: "text", required: true },
          { id: "account_name", label: "Account Holder Name", type: "text", required: true },
          { id: "sort_code", label: "Sort Code", type: "text", placeholder: "00-00-00", required: true },
          { id: "account_number", label: "Account Number", type: "text", placeholder: "8 digits", required: true },
        ]
      }
    ]
  },
  equal_opportunities: {
    icon: FileText,
    sections: [
      {
        title: "Diversity Monitoring (Optional)",
        description: "This information helps us monitor equality and diversity. All responses are anonymous.",
        fields: [
          { id: "ethnicity", label: "Ethnic Group", type: "select", options: ["White British", "White Irish", "White Other", "Mixed/Multiple ethnic groups", "Asian/Asian British", "Black/African/Caribbean/Black British", "Other ethnic group", "Prefer not to say"] },
          { id: "disability", label: "Do you consider yourself to have a disability?", type: "radio", options: ["Yes", "No", "Prefer not to say"] },
          { id: "gender", label: "Gender", type: "select", options: ["Male", "Female", "Non-binary", "Other", "Prefer not to say"] },
          { id: "age_range", label: "Age Range", type: "select", options: ["16-24", "25-34", "35-44", "45-54", "55-64", "65+", "Prefer not to say"] },
          { id: "religion", label: "Religion or Belief", type: "select", options: ["No religion", "Christian", "Muslim", "Hindu", "Sikh", "Jewish", "Buddhist", "Other", "Prefer not to say"] },
          { id: "sexual_orientation", label: "Sexual Orientation", type: "select", options: ["Heterosexual/Straight", "Gay/Lesbian", "Bisexual", "Other", "Prefer not to say"] },
        ]
      }
    ]
  },
  emergency_contacts: {
    icon: User,
    sections: [
      {
        title: "Primary Emergency Contact",
        fields: [
          { id: "primary_name", label: "Full Name", type: "text", required: true },
          { id: "primary_relationship", label: "Relationship to You", type: "text", required: true, placeholder: "e.g., Spouse, Parent, Sibling" },
          { id: "primary_phone", label: "Phone Number", type: "tel", required: true },
          { id: "primary_email", label: "Email Address", type: "email" },
          { id: "primary_address", label: "Address", type: "textarea" },
        ]
      },
      {
        title: "Secondary Emergency Contact",
        fields: [
          { id: "secondary_name", label: "Full Name", type: "text" },
          { id: "secondary_relationship", label: "Relationship to You", type: "text" },
          { id: "secondary_phone", label: "Phone Number", type: "tel" },
        ]
      }
    ]
  }
};

export default function WorkerFormPage() {
  const { formId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({});
  const [formMeta, setFormMeta] = useState(null);
  const [lastSaved, setLastSaved] = useState(null);
  const [canEdit, setCanEdit] = useState(true);

  const formDefinition = FORM_FIELDS[formId];

  useEffect(() => {
    fetchFormData();
  }, [formId]);

  const fetchFormData = async () => {
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.get(`${API}/worker/forms/${formId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setFormData(response.data.data || {});
      setFormMeta(response.data.form_definition);
      setLastSaved(response.data.last_saved);
      setCanEdit(response.data.can_edit !== false);
    } catch (error) {
      toast.error('Failed to load form');
      navigate('/worker/dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (fieldId, value) => {
    setFormData(prev => ({
      ...prev,
      [fieldId]: value
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.post(
        `${API}/worker/forms/${formId}/save`,
        { form_data: formData },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setLastSaved(response.data.saved_at);
      toast.success('Progress saved! You can return later to continue.');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleSubmit = async () => {
    // Validate required fields
    const missingFields = [];
    formDefinition?.sections?.forEach(section => {
      section.fields.forEach(field => {
        if (field.required && !formData[field.id]) {
          missingFields.push(field.label);
        }
      });
    });

    if (missingFields.length > 0) {
      toast.error(`Please complete required fields: ${missingFields.slice(0, 3).join(', ')}${missingFields.length > 3 ? '...' : ''}`);
      return;
    }

    setSubmitting(true);
    try {
      const token = localStorage.getItem('workerToken');
      console.log('Submitting form:', formId, 'with data:', formData);
      const response = await axios.post(
        `${API}/worker/forms/${formId}/submit`,
        { form_data: formData },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      console.log('Submit response:', response.data);
      toast.success('Form submitted successfully! Admin has been notified.');
      navigate('/worker/dashboard');
    } catch (error) {
      console.error('Submit error:', error.response?.data || error);
      toast.error(error.response?.data?.detail || 'Failed to submit form. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const renderField = (field) => {
    const value = formData[field.id] || '';

    switch (field.type) {
      case 'text':
      case 'tel':
      case 'email':
      case 'date':
        return (
          <Input
            type={field.type}
            value={value}
            onChange={(e) => handleFieldChange(field.id, e.target.value)}
            placeholder={field.placeholder}
            disabled={!canEdit}
            className="mt-1"
          />
        );
      
      case 'textarea':
        return (
          <Textarea
            value={value}
            onChange={(e) => handleFieldChange(field.id, e.target.value)}
            placeholder={field.placeholder}
            disabled={!canEdit}
            className="mt-1"
            rows={3}
          />
        );
      
      case 'select':
        return (
          <Select
            value={value}
            onValueChange={(v) => handleFieldChange(field.id, v)}
            disabled={!canEdit}
          >
            <SelectTrigger className="mt-1">
              <SelectValue placeholder="Select an option" />
            </SelectTrigger>
            <SelectContent>
              {field.options.map(opt => (
                <SelectItem key={opt} value={opt}>{opt}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      
      case 'radio':
        return (
          <RadioGroup
            value={value}
            onValueChange={(v) => handleFieldChange(field.id, v)}
            disabled={!canEdit}
            className="mt-2 space-y-2"
          >
            {field.options.map(opt => (
              <div key={opt} className="flex items-center space-x-2">
                <RadioGroupItem value={opt} id={`${field.id}-${opt}`} />
                <Label htmlFor={`${field.id}-${opt}`} className="font-normal cursor-pointer">
                  {opt}
                </Label>
              </div>
            ))}
          </RadioGroup>
        );
      
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!formDefinition) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <p className="text-slate-600">Form not found</p>
            <Button onClick={() => navigate('/worker/dashboard')} className="mt-4">
              Back to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const FormIcon = formDefinition.icon;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="sm" onClick={() => navigate('/worker/dashboard')}>
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div className="flex items-center gap-2">
                <FormIcon className="h-5 w-5 text-blue-600" />
                <h1 className="font-semibold text-lg">{formMeta?.name || formId}</h1>
              </div>
            </div>
            {canEdit && (
              <div className="flex items-center gap-2">
                {lastSaved && (
                  <span className="text-xs text-slate-500 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Saved {new Date(lastSaved).toLocaleTimeString()}
                  </span>
                )}
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  <span className="ml-1 hidden sm:inline">Save</span>
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Form Content */}
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {!canEdit && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <p className="text-green-800">This form has been submitted and is awaiting review.</p>
          </div>
        )}

        {formDefinition.sections.map((section, sIdx) => (
          <Card key={sIdx} className="shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">{section.title}</CardTitle>
              {section.description && (
                <CardDescription>{section.description}</CardDescription>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {section.fields.map((field) => (
                <div key={field.id}>
                  <Label className="text-sm font-medium">
                    {field.label}
                    {field.required && <span className="text-red-500 ml-1">*</span>}
                  </Label>
                  {renderField(field)}
                </div>
              ))}
            </CardContent>
          </Card>
        ))}

        {/* Submit Button */}
        {canEdit && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <p className="text-sm text-blue-800 mb-3">
              <strong>Ready to submit?</strong> Once submitted, this form cannot be edited and will be sent to the admin for review.
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={handleSave} disabled={saving}>
                <Save className="h-4 w-4 mr-2" />
                Save Draft
              </Button>
              <Button onClick={handleSubmit} disabled={submitting} className="bg-green-600 hover:bg-green-700">
                {submitting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Send className="h-4 w-4 mr-2" />
                )}
                Submit to Admin
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
