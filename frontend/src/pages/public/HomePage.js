import Header from '../../components/public/Header';
import Footer from '../../components/public/Footer';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { 
  BadgeCheck, GraduationCap, FileCheck, HeartHandshake, 
  UserPlus, ShieldCheck, ClipboardList, BriefcaseMedical,
  ArrowRight, CheckCircle, ShieldAlert, Users, Clock, Award,
  Building2, Phone, FileText, UserCheck, CalendarCheck, Shield
} from 'lucide-react';

// Trust indicators for care homes
const trustIndicators = [
  { icon: Users, value: '500+', label: 'Staff Placed' },
  { icon: Building2, value: '50+', label: 'Care Homes Served' },
  { icon: Award, value: '10+', label: 'Years Experience' },
  { icon: Shield, value: '100%', label: 'CQC Compliant' }
];

// How it works for care homes
const howItWorks = [
  { 
    step: 1, 
    icon: Phone, 
    title: 'Tell Us Your Needs', 
    description: 'Share your staffing requirements - role, shifts, location and any specific care needs.' 
  },
  { 
    step: 2, 
    icon: UserCheck, 
    title: 'We Find Compliant Staff', 
    description: 'We match you with DBS-checked, trained professionals from our vetted pool.' 
  },
  { 
    step: 3, 
    icon: ClipboardList, 
    title: 'You Review & Approve', 
    description: 'Review candidate profiles and compliance files before confirming placement.' 
  },
  { 
    step: 4, 
    icon: CalendarCheck, 
    title: 'Staff Deployed', 
    description: 'Fully compliant staff start when you need them - no delays, no gaps.' 
  },
  { 
    step: 5, 
    icon: FileCheck, 
    title: 'Ongoing Compliance', 
    description: 'We track expiry dates, handle renewals and keep records audit-ready.' 
  }
];

// Why care homes trust us
const whyTrustUs = [
  {
    icon: FileCheck,
    title: 'Audit-Ready Records',
    description: 'Digital compliance files for every staff member with verification status and expiry tracking.'
  },
  {
    icon: ShieldCheck,
    title: 'Full Compliance',
    description: 'DBS, Right to Work, References and mandatory training verified before any placement.'
  },
  {
    icon: Clock,
    title: 'Fast Placement',
    description: 'Fully vetted, compliant staff ready to deploy when you need them - no waiting.'
  }
];

// Services offered
const services = [
  'Mental Health Support',
  'Learning Disabilities',
  'Complex Care',
  'Supported Living',
  'Live-in Care',
  'Hourly Care',
  'Respite Care',
  'Waking & Overnight Care'
];

// Testimonials from care homes
const testimonials = [
  {
    quote: "Osabea provides us with reliable, fully-vetted staff. Their compliance records are always ready for inspection.",
    author: "Care Home Manager",
    company: "Supported Living Provider, London"
  },
  {
    quote: "The recruitment process is thorough. We've never had compliance issues with any of their staff.",
    author: "Operations Director",
    company: "Care Home Group, Midlands"
  }
];

// Compliance features
const complianceFeatures = [
  'Every candidate DBS checked and verified',
  'Right to Work documented and stamped',
  'Professional references confirmed',
  'Mandatory training completed and tracked',
  'Full compliance file available for inspection',
  'Expiry tracking with automated renewals'
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#F8FAFA]">
      <Header />
      
      {/* Hero Section - Care Home Focused */}
      <section className="relative overflow-hidden bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div>
                {/* CQC Compliant Badge */}
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-50 border border-green-200 text-green-700 text-sm font-medium rounded-full mb-6">
                  <Shield className="h-4 w-4" />
                  CQC Compliant Staffing Agency
                </div>
                <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold text-text-primary tracking-tight leading-tight">
                  Fully Compliant Care Staff - <span className="text-primary">Ready When You Need Them</span>
                </h1>
              </div>
              <p className="text-lg text-text-muted leading-relaxed max-w-xl">
                We provide thoroughly vetted, CQC-ready healthcare professionals to care homes and supported living services across the UK.
              </p>
              
              {/* Trust badges - key compliance points */}
              <div className="grid grid-cols-2 gap-3">
                {complianceFeatures.slice(0, 4).map((feature, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm text-text-primary">
                    <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
                    <span>{feature}</span>
                  </div>
                ))}
              </div>
              
              {/* CTAs - Care Home Primary */}
              <div className="flex flex-col sm:flex-row gap-4">
                <Link to="/contact">
                  <Button size="lg" className="bg-primary hover:bg-primary-hover text-white rounded-full px-8 h-14 text-base" data-testid="hero-staffing-btn">
                    Request Staffing Support
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
                <a href="/compliance-guide.pdf" target="_blank" rel="noopener noreferrer">
                  <Button size="lg" variant="outline" className="border-[#E4E8EB] hover:bg-[#F8FAFA] rounded-full px-8 h-14 text-base" data-testid="hero-guide-btn">
                    <FileText className="mr-2 h-5 w-5" />
                    Download Compliance Guide
                  </Button>
                </a>
              </div>
            </div>
            
            <div className="relative">
              <div className="absolute -top-8 -right-8 w-64 h-64 bg-accent rounded-full blur-3xl opacity-50"></div>
              <div className="absolute -bottom-8 -left-8 w-48 h-48 bg-support-accent rounded-full blur-3xl opacity-50"></div>
              <img
                src="https://images.pexels.com/photos/6129442/pexels-photo-6129442.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                alt="Care professional providing compassionate support"
                className="relative rounded-3xl shadow-lg w-full object-cover aspect-[4/3]"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Trust Indicators - Stats Bar */}
      <section className="py-12 bg-secondary">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {trustIndicators.map((stat, idx) => (
              <div key={idx} className="text-center" data-testid={`stat-${idx}`}>
                <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <stat.icon className="h-6 w-6 text-white" />
                </div>
                <div className="text-3xl font-bold text-white mb-1">{stat.value}</div>
                <div className="text-sm text-white/70">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why Care Homes Trust Us */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
              Why Care Homes Trust Osabea
            </h2>
            <p className="text-lg text-text-muted">
              We understand what CQC inspectors look for. Every placement comes with complete, verified documentation.
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {whyTrustUs.map((item, idx) => (
              <div key={idx} className="card-public group text-center" data-testid={`trust-card-${idx}`}>
                <div className="w-16 h-16 bg-accent rounded-2xl flex items-center justify-center mb-6 mx-auto group-hover:bg-primary transition-colors">
                  <item.icon className="h-8 w-8 text-primary group-hover:text-white transition-colors" />
                </div>
                <h3 className="font-heading text-xl font-semibold text-text-primary mb-3">{item.title}</h3>
                <p className="text-text-muted leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works - For Care Homes */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
              How It Works
            </h2>
            <p className="text-lg text-text-muted">
              From your first call to ongoing compliance management - we handle everything.
            </p>
          </div>
          
          <div className="relative">
            {/* Connection line */}
            <div className="hidden lg:block absolute top-12 left-[10%] right-[10%] h-0.5 bg-[#E4E8EB]"></div>
            
            <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-8 lg:gap-4">
              {howItWorks.map((step, idx) => (
                <div key={idx} className="relative text-center" data-testid={`step-${step.step}`}>
                  {/* Step number */}
                  <div className="relative z-10 w-24 h-24 bg-white border-2 border-[#E4E8EB] rounded-2xl flex flex-col items-center justify-center mx-auto mb-4 group-hover:border-primary transition-colors">
                    <step.icon className="h-8 w-8 text-primary mb-1" />
                    <span className="text-xs font-bold text-primary">STEP {step.step}</span>
                  </div>
                  <h3 className="font-heading font-semibold text-text-primary mb-2">{step.title}</h3>
                  <p className="text-sm text-text-muted">{step.description}</p>
                </div>
              ))}
            </div>
          </div>
          
          <div className="text-center mt-12">
            <Link to="/contact">
              <Button size="lg" className="bg-primary hover:bg-primary-hover text-white rounded-full px-8" data-testid="how-it-works-cta">
                Get Started Today
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Services */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-start">
            <div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
                Care Services We Support
              </h2>
              <p className="text-lg text-text-muted mb-8">
                We provide staffing for a range of care settings - from supported living and complex care to respite and mental health services.
              </p>
              <Link to="/services">
                <Button className="bg-primary hover:bg-primary-hover text-white rounded-full" data-testid="view-services-btn">
                  View All Services
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
            
            <div className="grid sm:grid-cols-2 gap-4">
              {services.map((service, idx) => (
                <div key={idx} className="bg-white rounded-2xl p-5 border border-[#E4E8EB] hover:border-primary/30 hover:shadow-sm transition-all">
                  <h3 className="font-heading font-medium text-text-primary">{service}</h3>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
              What Care Homes Say
            </h2>
          </div>
          
          <div className="grid md:grid-cols-2 gap-8">
            {testimonials.map((testimonial, idx) => (
              <div key={idx} className="bg-[#F8FAFA] rounded-3xl p-8 border border-[#E4E8EB]" data-testid={`testimonial-${idx}`}>
                <p className="text-lg text-text-primary italic mb-6">"{testimonial.quote}"</p>
                <div>
                  <p className="font-semibold text-text-primary">{testimonial.author}</p>
                  <p className="text-sm text-text-muted">{testimonial.company}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Compliance & Documentation Section */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="relative">
              <div className="absolute -top-4 -left-4 w-32 h-32 bg-support-accent rounded-full blur-2xl opacity-60"></div>
              <img
                src="https://images.pexels.com/photos/7511751/pexels-photo-7511751.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                alt="Organised compliance records and documentation"
                className="relative rounded-3xl shadow-lg w-full object-cover aspect-square"
              />
            </div>
            
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Award className="h-6 w-6 text-primary" />
                <span className="text-primary font-medium">CQC Ready Documentation</span>
              </div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-6">
                Inspection-Ready Records for Every Staff Member
              </h2>
              <p className="text-lg text-text-muted mb-8">
                We maintain digital compliance files with clear verification status, document stamps and expiry tracking. Our records are organised for CQC and regulatory review.
              </p>
              
              <ul className="space-y-4 mb-8">
                {complianceFeatures.map((item, idx) => (
                  <li key={idx} className="flex items-center gap-3">
                    <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    </div>
                    <span className="text-text-primary">{item}</span>
                  </li>
                ))}
              </ul>
              
              <Link to="/contact">
                <Button className="bg-primary hover:bg-primary-hover text-white rounded-full" data-testid="compliance-cta-btn">
                  Request a Compliance Pack
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Join Our Team Section - Secondary for Workers */}
      <section className="py-16 bg-[#F8FAFA] border-t border-[#E4E8EB]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white rounded-3xl p-8 lg:p-12 border border-[#E4E8EB] text-center">
            <div className="w-14 h-14 bg-accent rounded-2xl flex items-center justify-center mx-auto mb-6">
              <UserPlus className="h-7 w-7 text-primary" />
            </div>
            <h2 className="font-heading text-2xl sm:text-3xl font-semibold text-text-primary mb-4">
              Looking for Care Work?
            </h2>
            <p className="text-text-muted mb-6 max-w-xl mx-auto">
              We're always looking for dedicated healthcare assistants to join our team. Competitive rates, flexible shifts and full compliance support.
            </p>
            <Link to="/apply">
              <Button variant="outline" className="border-primary text-primary hover:bg-primary hover:text-white rounded-full px-8" data-testid="join-team-btn">
                Apply to Join Our Team
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Final CTA - Care Home Focused */}
      <section className="py-20 lg:py-28 bg-secondary">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-white mb-4">
            Ready for Compliant Care Staffing?
          </h2>
          <p className="text-lg text-white/80 mb-8">
            Get in touch today. We'll discuss your needs and show you how our compliant staff can support your care home.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/contact">
              <Button size="lg" className="bg-white text-secondary hover:bg-white/90 rounded-full px-8 h-14" data-testid="cta-staffing-btn">
                <Phone className="mr-2 h-5 w-5" />
                Request Staffing Support
              </Button>
            </Link>
            <a href="tel:+441onal" className="inline-flex">
              <Button size="lg" variant="outline" className="border-white text-white hover:bg-white/10 rounded-full px-8 h-14" data-testid="cta-call-btn">
                Book a Call
              </Button>
            </a>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
