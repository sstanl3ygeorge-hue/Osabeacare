import { useState } from 'react';
import Header from '../../components/public/Header';
import Footer from '../../components/public/Footer';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Checkbox } from '../../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import { Loader2, CheckCircle, FileText, User, Briefcase, Clock } from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const roles = [
  'Care Assistant',
  'Senior Care Assistant',
  'Support Worker',
  'Healthcare Assistant',
  'Live-in Carer',
  'Night Carer',
  'Team Leader',
  'Care Coordinator'
];

const steps = [
  { id: 1, icon: User, title: 'Personal details' },
  { id: 2, icon: Briefcase, title: 'Experience' },
  { id: 3, icon: Clock, title: 'Availability' },
  { id: 4, icon: FileText, title: 'Review & submit' }
];

export default function ApplyPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [reference, setReference] = useState('');
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    address: '',
    postcode: '',
    role_applied: '',
    availability: '',
    right_to_work: false,
    has_dbs: false,
    experience_summary: '',
    how_heard: ''
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({ ...formData, [name]: type === 'checkbox' ? checked : value });
  };

  const handleSelectChange = (name, value) => {
    setFormData({ ...formData, [name]: value });
  };

  const handleCheckboxChange = (name, checked) => {
    setFormData({ ...formData, [name]: checked });
  };

  const nextStep = () => {
    if (currentStep < 4) setCurrentStep(currentStep + 1);
  };

  const prevStep = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      const response = await axios.post(`${API}/apply`, formData);
      setReference(response.data.reference);
      setIsSubmitted(true);
      toast.success('Application submitted successfully!');
    } catch (error) {
      toast.error('Something went wrong. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFA]">
      <Header />
      
      {/* Hero */}
      <section className="bg-white py-12 lg:py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="font-heading text-3xl sm:text-4xl font-bold text-text-primary mb-4">
            Start your application
          </h1>
          <p className="text-lg text-text-muted">
            Complete your application online and upload your documents securely.
          </p>
        </div>
      </section>

      {/* Application Form */}
      <section className="py-12 lg:py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          {isSubmitted ? (
            <div className="bg-white rounded-3xl border border-[#E4E8EB] p-8 lg:p-12 text-center">
              <div className="w-20 h-20 bg-support-accent rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="h-10 w-10 text-success" />
              </div>
              <h2 className="font-heading text-2xl font-semibold text-text-primary mb-4">
                Application submitted
              </h2>
              <p className="text-text-muted mb-6">
                Thank you for applying to Osabea Healthcare Solutions. We'll review your application and be in touch.
              </p>
              <div className="bg-[#F8FAFA] rounded-xl p-4 inline-block">
                <p className="text-sm text-text-muted mb-1">Your reference number:</p>
                <p className="font-heading font-semibold text-lg text-primary">{reference}</p>
              </div>
            </div>
          ) : (
            <>
              {/* Progress Steps */}
              <div className="mb-8">
                <div className="flex items-center justify-between">
                  {steps.map((step, idx) => (
                    <div key={step.id} className="flex items-center">
                      <div className={`flex items-center justify-center w-10 h-10 rounded-xl ${
                        currentStep >= step.id ? 'bg-primary text-white' : 'bg-[#E4E8EB] text-text-muted'
                      }`}>
                        <step.icon className="h-5 w-5" />
                      </div>
                      <span className={`hidden sm:block ml-3 text-sm font-medium ${
                        currentStep >= step.id ? 'text-text-primary' : 'text-text-muted'
                      }`}>
                        {step.title}
                      </span>
                      {idx < steps.length - 1 && (
                        <div className={`hidden sm:block w-12 lg:w-24 h-0.5 mx-4 ${
                          currentStep > step.id ? 'bg-primary' : 'bg-[#E4E8EB]'
                        }`}></div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-3xl border border-[#E4E8EB] p-8 lg:p-12">
                <form onSubmit={handleSubmit}>
                  {/* Step 1: Personal Details */}
                  {currentStep === 1 && (
                    <div className="space-y-6">
                      <h2 className="font-heading text-xl font-semibold text-text-primary mb-6">
                        Personal details
                      </h2>
                      
                      <div className="grid sm:grid-cols-2 gap-6">
                        <div className="space-y-2">
                          <Label htmlFor="first_name">First name *</Label>
                          <Input
                            id="first_name"
                            name="first_name"
                            value={formData.first_name}
                            onChange={handleChange}
                            required
                            className="rounded-xl border-[#E4E8EB]"
                            data-testid="apply-firstname"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="last_name">Last name *</Label>
                          <Input
                            id="last_name"
                            name="last_name"
                            value={formData.last_name}
                            onChange={handleChange}
                            required
                            className="rounded-xl border-[#E4E8EB]"
                            data-testid="apply-lastname"
                          />
                        </div>
                      </div>
                      
                      <div className="grid sm:grid-cols-2 gap-6">
                        <div className="space-y-2">
                          <Label htmlFor="email">Email address *</Label>
                          <Input
                            id="email"
                            name="email"
                            type="email"
                            value={formData.email}
                            onChange={handleChange}
                            required
                            className="rounded-xl border-[#E4E8EB]"
                            data-testid="apply-email"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="phone">Phone number *</Label>
                          <Input
                            id="phone"
                            name="phone"
                            type="tel"
                            value={formData.phone}
                            onChange={handleChange}
                            required
                            className="rounded-xl border-[#E4E8EB]"
                            data-testid="apply-phone"
                          />
                        </div>
                      </div>
                      
                      <div className="space-y-2">
                        <Label htmlFor="address">Address</Label>
                        <Input
                          id="address"
                          name="address"
                          value={formData.address}
                          onChange={handleChange}
                          className="rounded-xl border-[#E4E8EB]"
                          data-testid="apply-address"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label htmlFor="postcode">Postcode</Label>
                        <Input
                          id="postcode"
                          name="postcode"
                          value={formData.postcode}
                          onChange={handleChange}
                          className="rounded-xl border-[#E4E8EB] max-w-xs"
                          data-testid="apply-postcode"
                        />
                      </div>
                    </div>
                  )}

                  {/* Step 2: Experience */}
                  {currentStep === 2 && (
                    <div className="space-y-6">
                      <h2 className="font-heading text-xl font-semibold text-text-primary mb-6">
                        Your experience
                      </h2>
                      
                      <div className="space-y-2">
                        <Label>Role you're applying for *</Label>
                        <Select value={formData.role_applied} onValueChange={(value) => handleSelectChange('role_applied', value)}>
                          <SelectTrigger className="rounded-xl border-[#E4E8EB]" data-testid="apply-role">
                            <SelectValue placeholder="Select a role" />
                          </SelectTrigger>
                          <SelectContent>
                            {roles.map((role) => (
                              <SelectItem key={role} value={role}>{role}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div className="space-y-2">
                        <Label htmlFor="experience_summary">Tell us about your care experience</Label>
                        <Textarea
                          id="experience_summary"
                          name="experience_summary"
                          value={formData.experience_summary}
                          onChange={handleChange}
                          rows={5}
                          placeholder="Describe your relevant experience, qualifications and skills..."
                          className="rounded-xl border-[#E4E8EB]"
                          data-testid="apply-experience"
                        />
                      </div>
                      
                      <div className="space-y-4">
                        <div className="flex items-center space-x-3">
                          <Checkbox
                            id="right_to_work"
                            checked={formData.right_to_work}
                            onCheckedChange={(checked) => handleCheckboxChange('right_to_work', checked)}
                            data-testid="apply-rtw"
                          />
                          <Label htmlFor="right_to_work" className="cursor-pointer">
                            I have the right to work in the UK
                          </Label>
                        </div>
                        
                        <div className="flex items-center space-x-3">
                          <Checkbox
                            id="has_dbs"
                            checked={formData.has_dbs}
                            onCheckedChange={(checked) => handleCheckboxChange('has_dbs', checked)}
                            data-testid="apply-dbs"
                          />
                          <Label htmlFor="has_dbs" className="cursor-pointer">
                            I have an enhanced DBS certificate or am registered with the Update Service
                          </Label>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Step 3: Availability */}
                  {currentStep === 3 && (
                    <div className="space-y-6">
                      <h2 className="font-heading text-xl font-semibold text-text-primary mb-6">
                        Your availability
                      </h2>
                      
                      <div className="space-y-2">
                        <Label>When are you available to work?</Label>
                        <Select value={formData.availability} onValueChange={(value) => handleSelectChange('availability', value)}>
                          <SelectTrigger className="rounded-xl border-[#E4E8EB]" data-testid="apply-availability">
                            <SelectValue placeholder="Select your availability" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="full_time">Full-time (35+ hours/week)</SelectItem>
                            <SelectItem value="part_time">Part-time (16-34 hours/week)</SelectItem>
                            <SelectItem value="flexible">Flexible / As needed</SelectItem>
                            <SelectItem value="weekends">Weekends only</SelectItem>
                            <SelectItem value="nights">Night shifts only</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div className="space-y-2">
                        <Label>How did you hear about us?</Label>
                        <Select value={formData.how_heard} onValueChange={(value) => handleSelectChange('how_heard', value)}>
                          <SelectTrigger className="rounded-xl border-[#E4E8EB]" data-testid="apply-howheard">
                            <SelectValue placeholder="Select an option" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="job_board">Job board</SelectItem>
                            <SelectItem value="social_media">Social media</SelectItem>
                            <SelectItem value="referral">Friend or colleague referral</SelectItem>
                            <SelectItem value="website">Company website</SelectItem>
                            <SelectItem value="agency">Another agency</SelectItem>
                            <SelectItem value="other">Other</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  )}

                  {/* Step 4: Review */}
                  {currentStep === 4 && (
                    <div className="space-y-6">
                      <h2 className="font-heading text-xl font-semibold text-text-primary mb-6">
                        Review your application
                      </h2>
                      
                      <div className="bg-[#F8FAFA] rounded-2xl p-6 space-y-4">
                        <div className="grid sm:grid-cols-2 gap-4">
                          <div>
                            <p className="text-sm text-text-muted">Name</p>
                            <p className="font-medium text-text-primary">{formData.first_name} {formData.last_name}</p>
                          </div>
                          <div>
                            <p className="text-sm text-text-muted">Email</p>
                            <p className="font-medium text-text-primary">{formData.email}</p>
                          </div>
                          <div>
                            <p className="text-sm text-text-muted">Phone</p>
                            <p className="font-medium text-text-primary">{formData.phone}</p>
                          </div>
                          <div>
                            <p className="text-sm text-text-muted">Role</p>
                            <p className="font-medium text-text-primary">{formData.role_applied || 'Not specified'}</p>
                          </div>
                          <div>
                            <p className="text-sm text-text-muted">Availability</p>
                            <p className="font-medium text-text-primary">{formData.availability?.replace('_', ' ') || 'Not specified'}</p>
                          </div>
                          <div>
                            <p className="text-sm text-text-muted">Right to work</p>
                            <p className="font-medium text-text-primary">{formData.right_to_work ? 'Yes' : 'Not confirmed'}</p>
                          </div>
                        </div>
                        {formData.experience_summary && (
                          <div>
                            <p className="text-sm text-text-muted">Experience</p>
                            <p className="font-medium text-text-primary">{formData.experience_summary}</p>
                          </div>
                        )}
                      </div>
                      
                      <p className="text-sm text-text-muted">
                        By submitting this application, you confirm that the information provided is accurate and complete.
                      </p>
                    </div>
                  )}

                  {/* Navigation Buttons */}
                  <div className="flex justify-between mt-8 pt-6 border-t border-[#E4E8EB]">
                    {currentStep > 1 ? (
                      <Button type="button" variant="outline" onClick={prevStep} className="rounded-full" data-testid="apply-back">
                        Back
                      </Button>
                    ) : (
                      <div></div>
                    )}
                    
                    {currentStep < 4 ? (
                      <Button type="button" onClick={nextStep} className="bg-primary hover:bg-primary-hover text-white rounded-full" data-testid="apply-continue">
                        Continue
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
                          'Submit application'
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
