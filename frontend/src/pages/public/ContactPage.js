import { useState } from 'react';
import Header from '../../components/public/Header';
import Footer from '../../components/public/Footer';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { toast } from 'sonner';
import { Phone, Mail, MapPin, Loader2, CheckCircle } from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ContactPage() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone: '',
    organisation: '',
    subject: '',
    message: ''
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      await axios.post(`${API}/contact`, formData);
      setIsSubmitted(true);
      toast.success('Thank you for your enquiry. We will be in touch soon.');
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
      <section className="bg-white py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <h1 className="font-heading text-4xl sm:text-5xl font-bold text-text-primary mb-6">
              Contact Osabea Healthcare Solutions
            </h1>
            <p className="text-lg text-text-muted leading-relaxed">
              Whether you need staffing support, want to discuss recruitment, or need help with an application, we are here to help.
            </p>
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-3 gap-12">
            {/* Contact Info */}
            <div className="space-y-8">
              <div className="card-public">
                <Phone className="h-6 w-6 text-primary mb-4" />
                <h3 className="font-heading font-semibold text-text-primary mb-2">Call us</h3>
                <a href="tel:08001234567" className="text-text-muted hover:text-primary transition-colors">
                  0800 123 4567
                </a>
              </div>
              
              <div className="card-public">
                <Mail className="h-6 w-6 text-primary mb-4" />
                <h3 className="font-heading font-semibold text-text-primary mb-2">Email us</h3>
                <a href="mailto:info@osabea.care" className="text-text-muted hover:text-primary transition-colors">
                  info@osabea.care
                </a>
              </div>
              
              <div className="card-public">
                <MapPin className="h-6 w-6 text-primary mb-4" />
                <h3 className="font-heading font-semibold text-text-primary mb-2">Visit us</h3>
                <p className="text-text-muted">
                  123 Care Street<br />
                  London, UK<br />
                  EC1A 1BB
                </p>
              </div>
            </div>

            {/* Contact Form */}
            <div className="lg:col-span-2">
              <div className="bg-white rounded-3xl border border-[#E4E8EB] p-8 lg:p-12">
                {isSubmitted ? (
                  <div className="text-center py-12">
                    <div className="w-16 h-16 bg-support-accent rounded-full flex items-center justify-center mx-auto mb-6">
                      <CheckCircle className="h-8 w-8 text-success" />
                    </div>
                    <h3 className="font-heading text-2xl font-semibold text-text-primary mb-4">
                      Thank you for your enquiry
                    </h3>
                    <p className="text-text-muted">
                      We'll review your message and get back to you as soon as possible.
                    </p>
                  </div>
                ) : (
                  <>
                    <h2 className="font-heading text-2xl font-semibold text-text-primary mb-6">
                      Send an enquiry
                    </h2>
                    
                    <form onSubmit={handleSubmit} className="space-y-6">
                      <div className="grid sm:grid-cols-2 gap-6">
                        <div className="space-y-2">
                          <Label htmlFor="full_name">Full name *</Label>
                          <Input
                            id="full_name"
                            name="full_name"
                            value={formData.full_name}
                            onChange={handleChange}
                            required
                            className="rounded-xl border-[#E4E8EB]"
                            data-testid="contact-name"
                          />
                        </div>
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
                            data-testid="contact-email"
                          />
                        </div>
                      </div>
                      
                      <div className="grid sm:grid-cols-2 gap-6">
                        <div className="space-y-2">
                          <Label htmlFor="phone">Phone number</Label>
                          <Input
                            id="phone"
                            name="phone"
                            type="tel"
                            value={formData.phone}
                            onChange={handleChange}
                            className="rounded-xl border-[#E4E8EB]"
                            data-testid="contact-phone"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="organisation">Organisation name</Label>
                          <Input
                            id="organisation"
                            name="organisation"
                            value={formData.organisation}
                            onChange={handleChange}
                            className="rounded-xl border-[#E4E8EB]"
                            data-testid="contact-org"
                          />
                        </div>
                      </div>
                      
                      <div className="space-y-2">
                        <Label htmlFor="subject">Subject *</Label>
                        <Input
                          id="subject"
                          name="subject"
                          value={formData.subject}
                          onChange={handleChange}
                          required
                          className="rounded-xl border-[#E4E8EB]"
                          data-testid="contact-subject"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label htmlFor="message">Message *</Label>
                        <Textarea
                          id="message"
                          name="message"
                          value={formData.message}
                          onChange={handleChange}
                          required
                          rows={5}
                          className="rounded-xl border-[#E4E8EB]"
                          data-testid="contact-message"
                        />
                      </div>
                      
                      <p className="text-sm text-text-muted">
                        We aim to respond as soon as possible.
                      </p>
                      
                      <Button
                        type="submit"
                        disabled={isSubmitting}
                        className="bg-primary hover:bg-primary-hover text-white rounded-full px-8"
                        data-testid="contact-submit"
                      >
                        {isSubmitting ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Sending...
                          </>
                        ) : (
                          'Send enquiry'
                        )}
                      </Button>
                    </form>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
