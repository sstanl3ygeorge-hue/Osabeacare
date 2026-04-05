import Header from '../../components/public/Header';
import Footer from '../../components/public/Footer';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { 
  BadgeCheck, GraduationCap, FileCheck, HeartHandshake, 
  UserPlus, ShieldCheck, ClipboardList, BriefcaseMedical,
  ArrowRight, CheckCircle, ShieldAlert, Users, Clock, Award,
  Building2, Phone, FileText, UserCheck, CalendarCheck, Shield,
  Quote, Star, Monitor, Lock, Eye
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
    description: 'Share your staffing requirements - role, shifts, location and care needs.' 
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
    description: 'Review candidate profiles and compliance files before confirming.' 
  },
  { 
    step: 4, 
    icon: CalendarCheck, 
    title: 'Staff Deployed', 
    description: 'Fully compliant staff start when you need them - within 48 hours.' 
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
    description: 'Digital compliance files for every staff member with verification stamps and expiry tracking.'
  },
  {
    icon: ShieldCheck,
    title: 'Full CQC Compliance',
    description: 'DBS, Right to Work, References and mandatory training verified before any placement.'
  },
  {
    icon: Clock,
    title: 'Fast Placement',
    description: 'Fully vetted, compliant staff ready to deploy within 48 hours - no waiting.'
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
    quote: "Osabea provided us with compliant staff within 48 hours. Their digital compliance system gives us complete peace of mind during CQC inspections.",
    author: "Sarah Thompson",
    role: "Registered Manager",
    company: "Sunrise Care Home, Kent"
  },
  {
    quote: "The compliance records are always organised and ready for inspection. We've never had issues with any of their staff - thoroughly vetted professionals.",
    author: "James Mitchell",
    role: "Operations Director",
    company: "Harmony Living Services, London"
  },
  {
    quote: "Finally, an agency that understands what CQC inspectors look for. Every staff member comes with complete, verified documentation.",
    author: "Maria Santos",
    role: "Care Home Manager",
    company: "Medway Supported Living"
  }
];

// Compliance features for display
const complianceFeatures = [
  'Every candidate DBS checked and verified',
  'Right to Work documented with Home Office check',
  'Professional references confirmed',
  'Mandatory training completed and tracked',
  'Full compliance file available for inspection',
  'Expiry tracking with automated renewals'
];

// Dashboard features
const dashboardFeatures = [
  { icon: Eye, title: 'Real-time Visibility', description: 'See who\'s ready to work, who needs training, and when documents expire.' },
  { icon: FileCheck, title: 'Digital Compliance Files', description: 'Access complete staff records anytime - DBS, RTW, training, references.' },
  { icon: Lock, title: 'Audit-Ready Records', description: 'One-click access to verification stamps and compliance history.' }
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#F8FAFA]">
      <Header />
      
      {/* Hero Section - Care Home Focused */}
      <section className="relative overflow-hidden bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-20">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              {/* CQC Compliant Badge - PROMINENT */}
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-50 border-2 border-green-300 text-green-700 text-sm font-semibold rounded-full">
                <Shield className="h-5 w-5" />
                CQC-Compliant Care Staffing
              </div>
              
              <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold text-text-primary tracking-tight leading-tight">
                Fully Vetted, CQC-Ready Staff - <span className="text-primary">When You Need Them</span>
              </h1>
              
              <p className="text-lg text-text-muted leading-relaxed max-w-xl">
                We provide thoroughly vetted healthcare professionals to care homes and supported living services across the UK. Every staff member is audit-ready before placement.
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
                  <Button size="lg" className="bg-primary hover:bg-primary-hover text-white rounded-full px-8 h-14 text-base font-semibold shadow-lg" data-testid="hero-staffing-btn">
                    <Phone className="mr-2 h-5 w-5" />
                    Request Staffing Support
                  </Button>
                </Link>
                <a href="tel:01onal634306000">
                  <Button size="lg" variant="outline" className="border-2 border-primary text-primary hover:bg-primary/5 rounded-full px-8 h-14 text-base font-semibold" data-testid="hero-call-btn">
                    Call: 01634 306 000
                  </Button>
                </a>
              </div>
              
              {/* Trusted by line */}
              <p className="text-sm text-text-muted pt-2">
                Trusted by care homes across Kent, London and the South East
              </p>
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

      {/* CQC Compliance Banner - PROMINENT */}
      <section className="py-8 bg-green-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-4 text-white">
              <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center">
                <ShieldCheck className="h-8 w-8 text-white" />
              </div>
              <div>
                <h3 className="text-xl font-bold">CQC Compliant Staffing</h3>
                <p className="text-white/90">All staff vetted to CQC standards. Audit-ready compliance records for every worker.</p>
              </div>
            </div>
            <Link to="/contact">
              <Button size="lg" className="bg-white text-green-700 hover:bg-green-50 rounded-full px-6 font-semibold">
                Get Compliant Staff
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
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
      <section className="py-20 lg:py-24">
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

      {/* Live Dashboard Preview - SHOW DON'T TELL */}
      <section className="py-20 lg:py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Monitor className="h-6 w-6 text-primary" />
                <span className="text-primary font-medium">Digital Compliance System</span>
              </div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-6">
                See How Our Compliance Dashboard Works
              </h2>
              <p className="text-lg text-text-muted mb-8">
                Every staff member has a digital compliance file you can access anytime. Track who's ready to work, who needs training, and when documents expire - all in real-time.
              </p>
              
              <div className="space-y-4 mb-8">
                {dashboardFeatures.map((feature, idx) => (
                  <div key={idx} className="flex items-start gap-4">
                    <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center flex-shrink-0">
                      <feature.icon className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-text-primary">{feature.title}</h4>
                      <p className="text-sm text-text-muted">{feature.description}</p>
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="flex flex-col sm:flex-row gap-3">
                <Link to="/contact">
                  <Button className="bg-primary hover:bg-primary-hover text-white rounded-full px-6">
                    Request Demo
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
                <Link to="/compliance">
                  <Button variant="outline" className="border-primary text-primary hover:bg-primary/5 rounded-full px-6">
                    Learn More
                  </Button>
                </Link>
              </div>
            </div>
            
            <div className="relative">
              <div className="absolute -top-4 -right-4 w-32 h-32 bg-accent rounded-full blur-2xl opacity-60"></div>
              {/* Dashboard Preview Mock */}
              <div className="relative bg-gray-900 rounded-2xl p-2 shadow-2xl">
                <div className="bg-white rounded-xl overflow-hidden">
                  {/* Mock Dashboard Header */}
                  <div className="bg-secondary px-4 py-3 flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-400"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                    <div className="w-3 h-3 rounded-full bg-green-400"></div>
                    <span className="text-white text-xs ml-2">Osabea Compliance Portal</span>
                  </div>
                  {/* Mock Dashboard Content */}
                  <div className="p-4 space-y-3">
                    <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <span className="text-sm font-medium text-green-700">DBS Certificate</span>
                      </div>
                      <span className="text-xs bg-green-600 text-white px-2 py-1 rounded-full">Verified</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <span className="text-sm font-medium text-green-700">Right to Work</span>
                      </div>
                      <span className="text-xs bg-green-600 text-white px-2 py-1 rounded-full">Stamped</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <span className="text-sm font-medium text-green-700">References (2/2)</span>
                      </div>
                      <span className="text-xs bg-green-600 text-white px-2 py-1 rounded-full">Confirmed</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-amber-50 rounded-lg border border-amber-200">
                      <div className="flex items-center gap-2">
                        <Clock className="h-5 w-5 text-amber-600" />
                        <span className="text-sm font-medium text-amber-700">Training Due</span>
                      </div>
                      <span className="text-xs bg-amber-500 text-white px-2 py-1 rounded-full">14 days</span>
                    </div>
                    <div className="text-center pt-2">
                      <span className="text-xs text-gray-500">Staff Compliance: 94% Ready</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20 lg:py-24 bg-[#F8FAFA]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
              What Care Homes Say About Us
            </h2>
            <p className="text-lg text-text-muted">
              Trusted by care homes and supported living providers across the UK.
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, idx) => (
              <div key={idx} className="bg-white rounded-3xl p-8 border border-[#E4E8EB] shadow-sm" data-testid={`testimonial-${idx}`}>
                <Quote className="h-8 w-8 text-primary/30 mb-4" />
                <p className="text-text-primary mb-6 leading-relaxed">"{testimonial.quote}"</p>
                <div className="border-t border-gray-100 pt-4">
                  <p className="font-semibold text-text-primary">{testimonial.author}</p>
                  <p className="text-sm text-text-muted">{testimonial.role}</p>
                  <p className="text-sm text-primary font-medium">{testimonial.company}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works - For Care Homes */}
      <section className="py-20 lg:py-24 bg-white">
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
                  <div className="relative z-10 w-24 h-24 bg-white border-2 border-[#E4E8EB] rounded-2xl flex flex-col items-center justify-center mx-auto mb-4 hover:border-primary transition-colors">
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
      <section className="py-20 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-start">
            <div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
                Care Services We Support
              </h2>
              <p className="text-lg text-text-muted mb-8">
                We provide staffing for a range of adult care settings - from supported living and complex care to mental health and respite services.
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

      {/* Need Compliant Staff CTA - REPEATED */}
      <section className="py-16 bg-primary">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-heading text-3xl sm:text-4xl font-bold text-white mb-4">
            Need Compliant Staff?
          </h2>
          <p className="text-lg text-white/90 mb-8">
            Tell us your requirements and we'll find fully vetted staff within 48 hours.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/contact">
              <Button size="lg" className="bg-white text-primary hover:bg-white/90 rounded-full px-8 h-14 font-semibold">
                <Phone className="mr-2 h-5 w-5" />
                Request Staffing Support
              </Button>
            </Link>
            <a href="tel:01634306000">
              <Button size="lg" variant="outline" className="border-2 border-white text-white hover:bg-white/10 rounded-full px-8 h-14 font-semibold">
                Call: 01634 306 000
              </Button>
            </a>
          </div>
        </div>
      </section>

      {/* Trust Logos Section */}
      <section className="py-12 bg-white border-t border-[#E4E8EB]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-text-muted mb-6">Aligned with industry standards</p>
          <div className="flex flex-wrap items-center justify-center gap-8 opacity-60">
            {/* Placeholder for logos - using text for now */}
            <div className="px-6 py-3 bg-gray-100 rounded-lg text-gray-500 font-medium">CQC Standards</div>
            <div className="px-6 py-3 bg-gray-100 rounded-lg text-gray-500 font-medium">NHS Employment Check</div>
            <div className="px-6 py-3 bg-gray-100 rounded-lg text-gray-500 font-medium">Skills for Care</div>
            <div className="px-6 py-3 bg-gray-100 rounded-lg text-gray-500 font-medium">ICO Registered</div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
