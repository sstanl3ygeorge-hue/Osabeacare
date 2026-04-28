import { useState, useEffect } from 'react';
import axios from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { 
  User, MapPin, Briefcase, Users, Phone, 
  CheckCircle, ChevronRight, ChevronLeft, Loader2, AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_BASE_URL;

const WIZARD_STEPS = [
  { id: 'personal', title: 'Personal Details', icon: User, description: 'Basic information about you' },
  { id: 'address', title: 'Address', icon: MapPin, description: 'Your current address' },
  { id: 'references', title: 'References', icon: Users, description: 'Two professional references' },
  { id: 'emergency', title: 'Emergency Contact', icon: Phone, description: 'Who to contact in emergency' },
];

export default function ProfileCompletionWizard({ open, onClose, onComplete }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [completionStatus, setCompletionStatus] = useState(null);
  const [isFromPdfImport, setIsFromPdfImport] = useState(false);
  
  // Form data for each step
  const [formData, setFormData] = useState({
    // Personal Details
    date_of_birth: '',
    ni_number: '',
    phone: '',
    
    // Address
    address_line_1: '',
    address_line_2: '',
    city: '',
    county: '',
    postcode: '',
    
    // Reference 1
    reference_1: {
      name: '',
      email: '',
      phone: '',
      organization: '',
      job_title: '',
      relationship: ''
    },
    
    // Reference 2
    reference_2: {
      name: '',
      email: '',
      phone: '',
      organization: '',
      job_title: '',
      relationship: ''
    },
    
    // Emergency Contact
    emergency_contact: {
      name: '',
      phone: '',
      relationship: '',
      address: ''
    }
  });

  // Fetch completion status and existing profile data on open
  useEffect(() => {
    if (open) {
      fetchCompletionStatus();
      fetchExistingProfileData();
    }
  }, [open]);

  const fetchCompletionStatus = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.get(`${API}/worker/profile-completion-status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCompletionStatus(response.data);
      
      // Find first incomplete step
      const sections = response.data.sections;
      const stepOrder = ['personal_details', 'address', 'references', 'emergency_contacts'];
      const firstIncomplete = stepOrder.findIndex(s => !sections[s]?.complete);
      if (firstIncomplete >= 0) {
        setCurrentStep(firstIncomplete);
      }
    } catch (err) {
      console.error('Failed to fetch completion status:', err);
      toast.error('Failed to load profile status');
    } finally {
      setLoading(false);
    }
  };

  const fetchExistingProfileData = async () => {
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.get(`${API}/worker/profile-data`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Check if this is from a PDF import
      if (response.data.import_source === 'offline_pdf_import') {
        setIsFromPdfImport(true);
      }
      
      const data = response.data.profile_data;
      if (data) {
        // Pre-populate form with existing data from PDF extraction
        setFormData(prev => ({
          ...prev,
          // Personal Details
          date_of_birth: data.personal?.date_of_birth || prev.date_of_birth,
          ni_number: data.personal?.ni_number || prev.ni_number,
          phone: data.personal?.phone || prev.phone,
          
          // Address
          address_line_1: data.address?.line1 || prev.address_line_1,
          address_line_2: data.address?.line2 || prev.address_line_2,
          city: data.address?.city || prev.city,
          county: data.address?.county || prev.county,
          postcode: data.address?.postcode || prev.postcode,
          
          // Reference 1
          reference_1: {
            name: data.reference_1?.name || prev.reference_1.name,
            email: data.reference_1?.email || prev.reference_1.email,
            phone: data.reference_1?.phone || prev.reference_1.phone,
            organization: data.reference_1?.organization || prev.reference_1.organization,
            job_title: data.reference_1?.job_title || prev.reference_1.job_title,
            relationship: data.reference_1?.relationship || prev.reference_1.relationship
          },
          
          // Reference 2
          reference_2: {
            name: data.reference_2?.name || prev.reference_2.name,
            email: data.reference_2?.email || prev.reference_2.email,
            phone: data.reference_2?.phone || prev.reference_2.phone,
            organization: data.reference_2?.organization || prev.reference_2.organization,
            job_title: data.reference_2?.job_title || prev.reference_2.job_title,
            relationship: data.reference_2?.relationship || prev.reference_2.relationship
          },
          
          // Emergency Contact
          emergency_contact: {
            name: data.emergency_contact?.name || prev.emergency_contact.name,
            phone: data.emergency_contact?.phone || prev.emergency_contact.phone,
            relationship: data.emergency_contact?.relationship || prev.emergency_contact.relationship,
            address: data.emergency_contact?.address || prev.emergency_contact.address
          }
        }));
      }
    } catch (err) {
      // Silently fail - existing data is optional
      console.log('No existing profile data to pre-populate');
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleNestedChange = (parent, field, value) => {
    setFormData(prev => ({
      ...prev,
      [parent]: {
        ...prev[parent],
        [field]: value
      }
    }));
  };

  const validateCurrentStep = () => {
    const step = WIZARD_STEPS[currentStep];
    
    switch (step.id) {
      case 'personal':
        if (!formData.date_of_birth) {
          toast.error('Please enter your date of birth');
          return false;
        }
        if (!formData.ni_number || formData.ni_number.replace(/\s/g, '').length < 9) {
          toast.error('Please enter a valid National Insurance number');
          return false;
        }
        if (!formData.phone) {
          toast.error('Please enter your phone number');
          return false;
        }
        return true;
        
      case 'address':
        if (!formData.address_line_1) {
          toast.error('Please enter your address');
          return false;
        }
        if (!formData.city) {
          toast.error('Please enter your city/town');
          return false;
        }
        if (!formData.postcode) {
          toast.error('Please enter your postcode');
          return false;
        }
        return true;
        
      case 'references':
        if (!formData.reference_1.name || !formData.reference_1.email) {
          toast.error('Please provide complete details for Reference 1');
          return false;
        }
        if (!formData.reference_2.name || !formData.reference_2.email) {
          toast.error('Please provide complete details for Reference 2');
          return false;
        }
        return true;
        
      case 'emergency':
        if (!formData.emergency_contact.name || !formData.emergency_contact.phone) {
          toast.error('Please provide emergency contact details');
          return false;
        }
        return true;
        
      default:
        return true;
    }
  };

  const saveCurrentStep = async () => {
    if (!validateCurrentStep()) return false;
    
    setSaving(true);
    try {
      const token = localStorage.getItem('workerToken');
      const step = WIZARD_STEPS[currentStep];
      
      // Prepare data based on current step
      let dataToSave = {};
      switch (step.id) {
        case 'personal':
          dataToSave = {
            date_of_birth: formData.date_of_birth,
            ni_number: formData.ni_number,
            phone: formData.phone
          };
          break;
        case 'address':
          dataToSave = {
            address_line_1: formData.address_line_1,
            address_line_2: formData.address_line_2,
            city: formData.city,
            county: formData.county,
            postcode: formData.postcode
          };
          break;
        case 'references':
          dataToSave = {
            reference_1: formData.reference_1,
            reference_2: formData.reference_2
          };
          break;
        case 'emergency':
          dataToSave = {
            emergency_contact: formData.emergency_contact
          };
          break;
      }
      
      await axios.post(`${API}/worker/profile/update`, dataToSave, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success(`${step.title} saved successfully`);
      return true;
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save');
      return false;
    } finally {
      setSaving(false);
    }
  };

  const handleNext = async () => {
    const saved = await saveCurrentStep();
    if (saved) {
      if (currentStep < WIZARD_STEPS.length - 1) {
        setCurrentStep(prev => prev + 1);
      } else {
        // Completed all steps
        toast.success('Profile completed successfully!');
        onComplete?.();
        onClose();
      }
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const isStepComplete = (stepId) => {
    if (!completionStatus) return false;
    const sectionMap = {
      'personal': 'personal_details',
      'address': 'address',
      'references': 'references',
      'emergency': 'emergency_contacts'
    };
    return completionStatus.sections?.[sectionMap[stepId]]?.complete || false;
  };

  const renderStepContent = () => {
    const step = WIZARD_STEPS[currentStep];
    
    switch (step.id) {
      case 'personal':
        return (
          <div className="space-y-4">
            <div>
              <Label>Date of Birth *</Label>
              <Input
                type="date"
                value={formData.date_of_birth}
                onChange={(e) => handleInputChange('date_of_birth', e.target.value)}
                className="mt-1"
                max={new Date().toISOString().split('T')[0]}
              />
            </div>
            <div>
              <Label>National Insurance Number *</Label>
              <Input
                value={formData.ni_number}
                onChange={(e) => handleInputChange('ni_number', e.target.value.toUpperCase())}
                placeholder="e.g., AB123456C"
                className="mt-1 uppercase"
                maxLength={13}
              />
              <p className="text-xs text-slate-500 mt-1">Format: 2 letters, 6 numbers, 1 letter (e.g., AB123456C)</p>
            </div>
            <div>
              <Label>Phone Number *</Label>
              <Input
                type="tel"
                value={formData.phone}
                onChange={(e) => handleInputChange('phone', e.target.value)}
                placeholder="e.g., 07700 900000"
                className="mt-1"
              />
            </div>
          </div>
        );
        
      case 'address':
        return (
          <div className="space-y-4">
            <div>
              <Label>Address Line 1 *</Label>
              <Input
                value={formData.address_line_1}
                onChange={(e) => handleInputChange('address_line_1', e.target.value)}
                placeholder="House number and street"
                className="mt-1"
              />
            </div>
            <div>
              <Label>Address Line 2</Label>
              <Input
                value={formData.address_line_2}
                onChange={(e) => handleInputChange('address_line_2', e.target.value)}
                placeholder="Apartment, suite, etc. (optional)"
                className="mt-1"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>City/Town *</Label>
                <Input
                  value={formData.city}
                  onChange={(e) => handleInputChange('city', e.target.value)}
                  placeholder="e.g., London"
                  className="mt-1"
                />
              </div>
              <div>
                <Label>County</Label>
                <Input
                  value={formData.county}
                  onChange={(e) => handleInputChange('county', e.target.value)}
                  placeholder="e.g., Greater London"
                  className="mt-1"
                />
              </div>
            </div>
            <div className="w-1/2">
              <Label>Postcode *</Label>
              <Input
                value={formData.postcode}
                onChange={(e) => handleInputChange('postcode', e.target.value.toUpperCase())}
                placeholder="e.g., SW1A 1AA"
                className="mt-1 uppercase"
                maxLength={10}
              />
            </div>
          </div>
        );
        
      case 'references':
        return (
          <div className="space-y-6">
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <h4 className="font-medium text-slate-800 mb-3">Reference 1</h4>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Full Name *</Label>
                  <Input
                    value={formData.reference_1.name}
                    onChange={(e) => handleNestedChange('reference_1', 'name', e.target.value)}
                    placeholder="e.g., John Smith"
                    className="mt-1 h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs">Email *</Label>
                  <Input
                    type="email"
                    value={formData.reference_1.email}
                    onChange={(e) => handleNestedChange('reference_1', 'email', e.target.value)}
                    placeholder="e.g., john@company.com"
                    className="mt-1 h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs">Phone</Label>
                  <Input
                    type="tel"
                    value={formData.reference_1.phone}
                    onChange={(e) => handleNestedChange('reference_1', 'phone', e.target.value)}
                    placeholder="e.g., 07700 900000"
                    className="mt-1 h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs">Organization</Label>
                  <Input
                    value={formData.reference_1.organization}
                    onChange={(e) => handleNestedChange('reference_1', 'organization', e.target.value)}
                    placeholder="e.g., NHS Trust"
                    className="mt-1 h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs">Their Job Title</Label>
                  <Input
                    value={formData.reference_1.job_title}
                    onChange={(e) => handleNestedChange('reference_1', 'job_title', e.target.value)}
                    placeholder="e.g., Ward Manager"
                    className="mt-1 h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs">Relationship to You</Label>
                  <Input
                    value={formData.reference_1.relationship}
                    onChange={(e) => handleNestedChange('reference_1', 'relationship', e.target.value)}
                    placeholder="e.g., Line Manager"
                    className="mt-1 h-9"
                  />
                </div>
              </div>
            </div>
            
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <h4 className="font-medium text-slate-800 mb-3">Reference 2</h4>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Full Name *</Label>
                  <Input
                    value={formData.reference_2.name}
                    onChange={(e) => handleNestedChange('reference_2', 'name', e.target.value)}
                    placeholder="e.g., Jane Doe"
                    className="mt-1 h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs">Email *</Label>
                  <Input
                    type="email"
                    value={formData.reference_2.email}
                    onChange={(e) => handleNestedChange('reference_2', 'email', e.target.value)}
                    placeholder="e.g., jane@company.com"
                    className="mt-1 h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs">Phone</Label>
                  <Input
                    type="tel"
                    value={formData.reference_2.phone}
                    onChange={(e) => handleNestedChange('reference_2', 'phone', e.target.value)}
                    placeholder="e.g., 07700 900000"
                    className="mt-1 h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs">Organization</Label>
                  <Input
                    value={formData.reference_2.organization}
                    onChange={(e) => handleNestedChange('reference_2', 'organization', e.target.value)}
                    placeholder="e.g., Care Home Ltd"
                    className="mt-1 h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs">Their Job Title</Label>
                  <Input
                    value={formData.reference_2.job_title}
                    onChange={(e) => handleNestedChange('reference_2', 'job_title', e.target.value)}
                    placeholder="e.g., Supervisor"
                    className="mt-1 h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs">Relationship to You</Label>
                  <Input
                    value={formData.reference_2.relationship}
                    onChange={(e) => handleNestedChange('reference_2', 'relationship', e.target.value)}
                    placeholder="e.g., Former Manager"
                    className="mt-1 h-9"
                  />
                </div>
              </div>
            </div>
          </div>
        );
        
      case 'emergency':
        return (
          <div className="space-y-4">
            <div className="p-4 bg-amber-50 rounded-lg border border-amber-200 mb-4">
              <p className="text-sm text-amber-800">
                Please provide details of someone we can contact in case of an emergency.
              </p>
            </div>
            <div>
              <Label>Contact Name *</Label>
              <Input
                value={formData.emergency_contact.name}
                onChange={(e) => handleNestedChange('emergency_contact', 'name', e.target.value)}
                placeholder="e.g., Mary Smith"
                className="mt-1"
              />
            </div>
            <div>
              <Label>Phone Number *</Label>
              <Input
                type="tel"
                value={formData.emergency_contact.phone}
                onChange={(e) => handleNestedChange('emergency_contact', 'phone', e.target.value)}
                placeholder="e.g., 07700 900000"
                className="mt-1"
              />
            </div>
            <div>
              <Label>Relationship to You *</Label>
              <Input
                value={formData.emergency_contact.relationship}
                onChange={(e) => handleNestedChange('emergency_contact', 'relationship', e.target.value)}
                placeholder="e.g., Spouse, Parent, Sibling"
                className="mt-1"
              />
            </div>
            <div>
              <Label>Address (optional)</Label>
              <Input
                value={formData.emergency_contact.address}
                onChange={(e) => handleNestedChange('emergency_contact', 'address', e.target.value)}
                placeholder="Their home address"
                className="mt-1"
              />
            </div>
          </div>
        );
        
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="max-w-2xl">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  const currentStepData = WIZARD_STEPS[currentStep];
  const StepIcon = currentStepData.icon;
  const progress = ((currentStep + 1) / WIZARD_STEPS.length) * 100;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader className="pb-2">
          <DialogTitle className="flex items-center gap-2 text-xl">
            <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
              <StepIcon className="h-5 w-5 text-purple-600" />
            </div>
            Complete Your Profile
          </DialogTitle>
          <DialogDescription>
            Please complete all sections to continue with your onboarding.
          </DialogDescription>
        </DialogHeader>
        
        {/* Progress Bar */}
        <div className="py-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-600">
              Step {currentStep + 1} of {WIZARD_STEPS.length}
            </span>
            <span className="text-sm text-slate-500">
              {Math.round(progress)}% complete
            </span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
        
        {/* Step Indicators */}
        <div className="flex justify-between mb-4">
          {WIZARD_STEPS.map((step, index) => {
            const Icon = step.icon;
            const isComplete = isStepComplete(step.id);
            const isCurrent = index === currentStep;
            
            return (
              <div 
                key={step.id} 
                className={cn(
                  "flex flex-col items-center gap-1 cursor-pointer",
                  index <= currentStep ? "opacity-100" : "opacity-50"
                )}
                onClick={() => index < currentStep && setCurrentStep(index)}
              >
                <div className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center border-2 transition-colors",
                  isComplete ? "bg-green-100 border-green-500" :
                  isCurrent ? "bg-purple-100 border-purple-500" :
                  "bg-slate-100 border-slate-300"
                )}>
                  {isComplete ? (
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  ) : (
                    <Icon className={cn(
                      "h-5 w-5",
                      isCurrent ? "text-purple-600" : "text-slate-400"
                    )} />
                  )}
                </div>
                <span className={cn(
                  "text-xs font-medium",
                  isCurrent ? "text-purple-700" : "text-slate-500"
                )}>
                  {step.title}
                </span>
              </div>
            );
          })}
        </div>
        
        {/* Current Step Content */}
        <div className="flex-1 overflow-y-auto py-4 px-1">
          {/* Info banner for PDF imports */}
          {isFromPdfImport && currentStep === 0 && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>Your application form has been imported.</strong> We've pre-filled some information from your paper application. Please review and complete any missing fields.
              </p>
            </div>
          )}
          
          <div className="mb-4">
            <h3 className="font-semibold text-lg text-slate-800">{currentStepData.title}</h3>
            <p className="text-sm text-slate-500">{currentStepData.description}</p>
          </div>
          {renderStepContent()}
        </div>
        
        {/* Footer Buttons */}
        <DialogFooter className="pt-4 border-t border-slate-200 flex justify-between sm:justify-between">
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={currentStep === 0 || saving}
            className="gap-1"
          >
            <ChevronLeft className="h-4 w-4" />
            Back
          </Button>
          <Button
            onClick={handleNext}
            disabled={saving}
            className="gap-1 bg-purple-600 hover:bg-purple-700"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : currentStep === WIZARD_STEPS.length - 1 ? (
              <>
                <CheckCircle className="h-4 w-4" />
                Complete
              </>
            ) : (
              <>
                Save & Continue
                <ChevronRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

