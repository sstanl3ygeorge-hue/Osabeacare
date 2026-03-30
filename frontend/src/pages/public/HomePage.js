import Header from '../../components/public/Header';
import Footer from '../../components/public/Footer';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { 
  BadgeCheck, GraduationCap, FileCheck, HeartHandshake, 
  UserPlus, ShieldCheck, ClipboardList, BriefcaseMedical,
  ArrowRight, CheckCircle, ShieldAlert, Users, Clock, Award
} from 'lucide-react';

const whyChooseUs = [
  {
    icon: ShieldAlert,
    title: 'Safer Recruitment',
    description: 'DBS, right to work, identity verification and reference checks - documented and reviewed before any placement.'
  },
  {
    icon: ClipboardList,
    title: 'Accountable Onboarding',
    description: 'Structured induction, mandatory training records and compliance checks before staff are deployed.'
  },
  {
    icon: FileCheck,
    title: 'Audit-Ready Records',
    description: 'Digital compliance files with verification status, document expiry tracking and policy acknowledgements.'
  },
  {
    icon: HeartHandshake,
    title: 'Quality-Focused Care',
    description: 'We prioritise dignity, professionalism and continuity - supporting both care providers and the people they serve.'
  }
];

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

const recruitmentSteps = [
  { icon: UserPlus, title: 'Application & Screening', description: 'Applications reviewed for experience, suitability and role fit.' },
  { icon: BadgeCheck, title: 'Identity & Eligibility', description: 'Right to work documents verified and identity confirmed.' },
  { icon: ShieldCheck, title: 'DBS & References', description: 'Enhanced DBS checks and professional references obtained and reviewed.' },
  { icon: ClipboardList, title: 'Interview & Assessment', description: 'Structured interviews with competency and values-based questions.' },
  { icon: GraduationCap, title: 'Mandatory Training', description: 'Core training completed: safeguarding, manual handling, infection control.' },
  { icon: FileCheck, title: 'Compliance Review', description: 'Full file reviewed for completeness, verification and audit readiness.' },
  { icon: BriefcaseMedical, title: 'Safe to Deploy', description: 'Only fully compliant staff are cleared for care placements.' }
];

const saferRecruitmentPillars = [
  'Enhanced DBS checks with update service verification',
  'Right to work verification with share code checks',
  'Professional references from care sector employers',
  'Employment history with gap explanations',
  'Structured interviews with competency assessment',
  'Mandatory training before placement'
];

const complianceFeatures = [
  'Digital employee compliance files',
  'Document verification and approval workflow',
  'Expiry tracking with automated alerts',
  'Policy acknowledgement records',
  'Training records with certificate storage',
  'Read-only auditor access for inspections'
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#F8FAFA]">
      <Header />
      
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div>
                <span className="inline-block px-4 py-2 bg-accent text-primary text-sm font-medium rounded-full mb-6">
                  Safer Recruitment & Care Staffing Partner
                </span>
                <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold text-text-primary tracking-tight leading-tight">
                  Safeguarded staffing for <span className="text-primary">quality care delivery</span>
                </h1>
              </div>
              <p className="text-lg text-text-muted leading-relaxed max-w-xl">
                Osabea Healthcare Solutions provides care providers with thoroughly vetted, compliant professionals through a structured safer recruitment process - supporting quality, continuity and accountability in care.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Link to="/apply">
                  <Button size="lg" className="bg-primary hover:bg-primary-hover text-white rounded-full px-8 h-14 text-base" data-testid="hero-apply-btn">
                    Apply to Join Our Team
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
                <Link to="/contact">
                  <Button size="lg" variant="outline" className="border-[#E4E8EB] hover:bg-[#F8FAFA] rounded-full px-8 h-14 text-base" data-testid="hero-contact-btn">
                    Request Staffing Support
                  </Button>
                </Link>
              </div>
              
              {/* Trust badges */}
              <div className="flex flex-wrap gap-4 pt-4">
                {['DBS Verified', 'Right to Work Checked', 'References Confirmed', 'Training Tracked'].map((badge) => (
                  <div key={badge} className="flex items-center gap-2 text-sm text-text-muted">
                    <CheckCircle className="h-4 w-4 text-success" />
                    <span>{badge}</span>
                  </div>
                ))}
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

      {/* Why Choose Us - Repositioned */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
              Why care providers trust Osabea
            </h2>
            <p className="text-lg text-text-muted">
              We deliver staffing support built around governance, safeguarding and accountability - ensuring every placement meets the standards expected in regulated care.
            </p>
          </div>
          
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {whyChooseUs.map((item, idx) => (
              <div key={idx} className="card-public group" data-testid={`why-card-${idx}`}>
                <div className="w-14 h-14 bg-accent rounded-2xl flex items-center justify-center mb-6 group-hover:bg-primary transition-colors">
                  <item.icon className="h-7 w-7 text-primary group-hover:text-white transition-colors" />
                </div>
                <h3 className="font-heading text-xl font-semibold text-text-primary mb-3">{item.title}</h3>
                <p className="text-text-muted leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Safer Recruitment Section - NEW */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <ShieldAlert className="h-6 w-6 text-primary" />
                <span className="text-primary font-medium">Safer Recruitment</span>
              </div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-6">
                Thorough checks before any placement
              </h2>
              <p className="text-lg text-text-muted mb-8">
                Every candidate goes through a structured recruitment process with documented checks at each stage. We do not deploy staff until their compliance file is complete and verified.
              </p>
              
              <ul className="space-y-4 mb-8">
                {saferRecruitmentPillars.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <div className="w-6 h-6 bg-support-accent rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <CheckCircle className="h-4 w-4 text-success" />
                    </div>
                    <span className="text-text-primary">{item}</span>
                  </li>
                ))}
              </ul>
              
              <Link to="/apply">
                <Button className="bg-primary hover:bg-primary-hover text-white rounded-full" data-testid="safer-recruitment-cta">
                  Start Your Application
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
            
            <div className="relative">
              <div className="absolute -top-4 -right-4 w-32 h-32 bg-accent rounded-full blur-2xl opacity-60"></div>
              <img
                src="https://images.pexels.com/photos/7176026/pexels-photo-7176026.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                alt="Document verification and compliance review"
                className="relative rounded-3xl shadow-lg w-full object-cover aspect-square"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Services */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-start">
            <div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
                Care services we support
              </h2>
              <p className="text-lg text-text-muted mb-8">
                We provide staffing for a range of care settings - from supported living and complex care to respite and mental health services. Our focus is on continuity, reliability and quality.
              </p>
              <Link to="/services">
                <Button className="bg-primary hover:bg-primary-hover text-white rounded-full" data-testid="view-services-btn">
                  View all services
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
            
            <div className="grid sm:grid-cols-2 gap-4">
              {services.map((service, idx) => (
                <div key={idx} className="bg-white rounded-2xl p-5 border border-[#E4E8EB] hover:border-primary/30 transition-colors">
                  <h3 className="font-heading font-medium text-text-primary">{service}</h3>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Recruitment Process */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-4">
              Our recruitment and onboarding pathway
            </h2>
            <p className="text-lg text-text-muted">
              Every candidate follows a structured process - reviewed, documented and verified before they are cleared to work.
            </p>
          </div>
          
          <div className="relative">
            {/* Timeline line */}
            <div className="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-[#E4E8EB] -translate-y-1/2"></div>
            
            <div className="grid sm:grid-cols-2 lg:grid-cols-7 gap-6 lg:gap-4">
              {recruitmentSteps.map((step, idx) => (
                <div key={idx} className="relative text-center group">
                  <div className="lg:absolute lg:left-1/2 lg:-translate-x-1/2 bg-white w-16 h-16 rounded-2xl border-2 border-[#E4E8EB] flex items-center justify-center mb-4 mx-auto group-hover:border-primary transition-colors">
                    <step.icon className="h-7 w-7 text-primary" />
                  </div>
                  <div className="lg:pt-24">
                    <h3 className="font-heading font-medium text-text-primary mb-2">{step.title}</h3>
                    <p className="text-sm text-text-muted">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Compliance & Governance Section */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="order-2 lg:order-1 relative">
              <div className="absolute -top-4 -left-4 w-32 h-32 bg-support-accent rounded-full blur-2xl opacity-60"></div>
              <img
                src="https://images.pexels.com/photos/7511751/pexels-photo-7511751.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
                alt="Organised compliance records and documentation"
                className="relative rounded-3xl shadow-lg w-full object-cover aspect-square"
              />
            </div>
            
            <div className="order-1 lg:order-2">
              <div className="flex items-center gap-2 mb-4">
                <Award className="h-6 w-6 text-primary" />
                <span className="text-primary font-medium">Compliance & Governance</span>
              </div>
              <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-text-primary mb-6">
                Audit-ready records for inspection confidence
              </h2>
              <p className="text-lg text-text-muted mb-8">
                We maintain digital compliance files for every staff member with clear verification status, document expiry tracking and policy acknowledgements. Our records are organised for CQC and regulatory review.
              </p>
              
              <ul className="space-y-4 mb-8">
                {complianceFeatures.map((item, idx) => (
                  <li key={idx} className="flex items-center gap-3">
                    <div className="w-6 h-6 bg-support-accent rounded-full flex items-center justify-center flex-shrink-0">
                      <CheckCircle className="h-4 w-4 text-success" />
                    </div>
                    <span className="text-text-primary">{item}</span>
                  </li>
                ))}
              </ul>
              
              <Link to="/contact">
                <Button className="bg-primary hover:bg-primary-hover text-white rounded-full" data-testid="compliance-cta-btn">
                  Speak to our team
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Band */}
      <section className="py-20 lg:py-28 bg-secondary">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-heading text-3xl sm:text-4xl font-semibold text-white mb-4">
            Need compliant care staff or looking to join our team?
          </h2>
          <p className="text-lg text-white/80 mb-8">
            Whether you need dependable, safeguarded care professionals or want to apply for care work with a provider that values quality and governance.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/contact">
              <Button size="lg" className="bg-white text-secondary hover:bg-white/90 rounded-full px-8 h-14" data-testid="cta-staffing-btn">
                Request Staffing Support
              </Button>
            </Link>
            <Link to="/apply">
              <Button size="lg" variant="outline" className="border-white text-white hover:bg-white/10 rounded-full px-8 h-14" data-testid="cta-apply-btn">
                Start Your Application
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
